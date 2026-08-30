"""Persistent in-process investigation sessions and their live event stream."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import queue
import threading
import time
import uuid
from typing import Optional

from harness.investigator import AutonomousInvestigator, InvestigatorConfig
from harness.models.events import EventSeverity, HarnessEvent, HarnessEventType
from harness.orchestration.run_manager import RunManager, default_run_manager


class InvestigationStatus(str, Enum):
    """Lifecycle state exposed to API and streaming clients."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class InvestigationEventSubscription:
    """Queue plus history snapshot captured atomically at subscription time."""

    events: tuple[HarnessEvent, ...]
    queue: queue.Queue[HarnessEvent]


class InvestigationSession:
    """Own one investigation's state, worker, audit events, and subscribers."""

    def __init__(
        self,
        config: InvestigatorConfig,
        run_manager: Optional[RunManager] = None,
        investigation_id: Optional[str] = None,
    ) -> None:
        self.config = config
        self.investigation_id = investigation_id or f"investigation_{uuid.uuid4().hex[:8]}"
        self.run_manager = run_manager or default_run_manager
        self.status = InvestigationStatus.CREATED
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.error: Optional[str] = None
        self._investigator: Optional[AutonomousInvestigator] = None
        self._events: list[HarnessEvent] = []
        self._subscribers: set[queue.Queue[HarnessEvent]] = set()
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._publish(
            HarnessEventType.INVESTIGATION_CREATED,
            {"investigation_id": self.investigation_id, "objective": config.objective},
        )

    def _publish(
        self,
        event_type: HarnessEventType,
        payload: dict[str, object],
        severity: EventSeverity = EventSeverity.INFO,
    ) -> HarnessEvent:
        """Append an event and fan it out to current subscribers."""
        event = HarnessEvent(
            evaluation_id=self.investigation_id,
            run_id="",
            episode_id="",
            sim_time=0.0,
            source="harness.investigation_session",
            type=event_type,
            severity=severity,
            payload=payload,
            investigation_id=self.investigation_id,
        )
        with self._lock:
            self._events.append(event)
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)
        return event

    def _on_investigator_event(self, event: HarnessEvent) -> None:
        """Forward investigator events into this session's ordered event log."""
        with self._lock:
            self._events.append(event)
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)

    def start(self) -> None:
        """Start the investigation exactly once in a daemon worker thread."""
        with self._lock:
            if self.status != InvestigationStatus.CREATED:
                raise RuntimeError(f"Investigation '{self.investigation_id}' has already started")
            self.status = InvestigationStatus.RUNNING
            self.started_at = time.time()
            self._publish(
                HarnessEventType.INVESTIGATION_STARTED,
                {"investigation_id": self.investigation_id, "budget": self.config.budget},
            )
            self._thread = threading.Thread(
                target=self._run,
                name=f"investigation-{self.investigation_id}",
                daemon=True,
            )
            self._thread.start()

    def _run(self) -> None:
        """Execute the deterministic investigator and close the session lifecycle."""
        try:
            investigator = AutonomousInvestigator(
                self.config,
                run_manager=self.run_manager,
                event_callback=self._on_investigator_event,
                investigation_id=self.investigation_id,
            )
            with self._lock:
                self._investigator = investigator
            investigator.run()
        except Exception as exc:
            with self._lock:
                self.status = InvestigationStatus.FAILED
                self.error = f"{type(exc).__name__}: {exc}"
                self.finished_at = time.time()
            self._publish(
                HarnessEventType.INVESTIGATION_FAILED,
                {"investigation_id": self.investigation_id, "error": self.error},
                severity=EventSeverity.ERROR,
            )
            return

        with self._lock:
            self.status = InvestigationStatus.COMPLETED
            self.finished_at = time.time()
        self._publish(
            HarnessEventType.INVESTIGATION_COMPLETED,
            {
                "investigation_id": self.investigation_id,
                "experiments_completed": (
                    self._investigator.completed_run_count if self._investigator else 0
                ),
            },
        )

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for completion and return whether the worker has stopped."""
        thread = self._thread
        if thread is None:
            return self.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
        thread.join(timeout)
        return not thread.is_alive()

    def subscribe(self) -> InvestigationEventSubscription:
        """Subscribe without losing events emitted during the history snapshot."""
        subscriber: queue.Queue[HarnessEvent] = queue.Queue()
        with self._lock:
            history = tuple(self._events)
            self._subscribers.add(subscriber)
        return InvestigationEventSubscription(events=history, queue=subscriber)

    def unsubscribe(self, subscriber: queue.Queue[HarnessEvent]) -> None:
        """Remove one streaming subscriber."""
        with self._lock:
            self._subscribers.discard(subscriber)

    def events(self) -> tuple[HarnessEvent, ...]:
        """Return an immutable event history snapshot."""
        with self._lock:
            return tuple(self._events)

    def snapshot(self) -> dict[str, object]:
        """Return the frontend/API representation of current session state."""
        with self._lock:
            investigator = self._investigator
            status = self.status
            error = self.error
            created_at = self.created_at
            started_at = self.started_at
            finished_at = self.finished_at
            event_count = len(self._events)
        result = investigator.to_dict() if investigator else None
        return {
            "investigation_id": self.investigation_id,
            "status": status.value,
            "objective": self.config.objective,
            "scenario_id": self.config.scenario_id,
            "hardware_preset_id": self.config.hardware_preset_id,
            "seed": self.config.seed,
            "budget": self.config.budget,
            "created_at": created_at,
            "started_at": started_at,
            "finished_at": finished_at,
            "event_count": event_count,
            "error": error,
            "result": result,
        }


class InvestigationSessionStore:
    """Thread-safe process store for active and completed investigation sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, InvestigationSession] = {}
        self._lock = threading.RLock()

    def create(
        self,
        config: InvestigatorConfig,
        run_manager: Optional[RunManager] = None,
    ) -> InvestigationSession:
        """Create and retain a new session without starting its worker."""
        session = InvestigationSession(config, run_manager=run_manager)
        with self._lock:
            self._sessions[session.investigation_id] = session
        return session

    def get(self, investigation_id: str) -> Optional[InvestigationSession]:
        """Look up a session by its stable public identifier."""
        with self._lock:
            return self._sessions.get(investigation_id)

    def list(self) -> tuple[InvestigationSession, ...]:
        """Return all retained sessions in creation order."""
        with self._lock:
            return tuple(self._sessions.values())


default_investigation_store = InvestigationSessionStore()

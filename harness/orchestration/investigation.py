"""Persistent in-process investigation sessions and their live event stream."""

from __future__ import annotations

from concurrent.futures import Executor, Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import queue
import threading
import time
import uuid
from typing import Callable, Optional

from harness.investigator import AutonomousInvestigator, InvestigatorConfig
from harness.models.events import EventSeverity, HarnessEvent, HarnessEventType
from harness.orchestration.run_manager import RunManager, default_run_manager


class InvestigationStatus(str, Enum):
    """Lifecycle state exposed to API and streaming clients."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


_DEFAULT_EXECUTOR: Executor = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="investigation"
)


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
        self.config: InvestigatorConfig = config
        self.investigation_id: str = investigation_id or f"investigation_{uuid.uuid4()}"
        self.run_manager: RunManager = run_manager or default_run_manager
        self.status: InvestigationStatus = InvestigationStatus.CREATED
        self.created_at: float = time.time()
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.error: Optional[str] = None
        self._investigator: Optional[AutonomousInvestigator] = None
        self._events: list[HarnessEvent] = []
        self._subscribers: set[queue.Queue[HarnessEvent]] = set()
        self._lock = threading.RLock()
        self._future: Optional[Future[None]] = None
        self._on_finished: Optional[Callable[[], None]] = None
        self._result_snapshot: Optional[dict[str, object]] = None
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
            if self._investigator is not None:
                try:
                    self._result_snapshot = deepcopy(self._investigator.to_dict())
                except Exception:
                    pass
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)

    def start(
        self,
        executor: Optional[Executor] = None,
        on_finished: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Start the investigation exactly once on a bounded executor."""
        with self._lock:
            if self.status != InvestigationStatus.CREATED:
                raise RuntimeError(f"Investigation '{self.investigation_id}' has already started")
            self._on_finished = on_finished
            self.status = InvestigationStatus.RUNNING
            self.started_at = time.time()
            self._publish(
                HarnessEventType.INVESTIGATION_STARTED,
                {"investigation_id": self.investigation_id, "budget": self.config.budget},
            )
            try:
                self._future = (executor or _DEFAULT_EXECUTOR).submit(self._run)
            except Exception as exc:
                self._mark_failed_locked(f"{type(exc).__name__}: {exc}")
                return False
        return True

    def fail(self, error: str) -> None:
        """Record a deterministic failure for work rejected before execution."""
        with self._lock:
            if self.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}:
                return
            self._mark_failed_locked(error)

    def _mark_failed_locked(self, error: str) -> None:
        """Transition to failed state; caller must hold the session lock."""
        self.status = InvestigationStatus.FAILED
        self.error = error
        self.finished_at = time.time()
        self._publish(
            HarnessEventType.INVESTIGATION_FAILED,
            {"investigation_id": self.investigation_id, "error": error},
            severity=EventSeverity.ERROR,
        )

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
                self._mark_failed_locked(f"{type(exc).__name__}: {exc}")
        else:
            with self._lock:
                if self._investigator is not None:
                    self._result_snapshot = deepcopy(self._investigator.to_dict())
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
        finally:
            if self._on_finished is not None:
                self._on_finished()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for completion and return whether the worker has stopped."""
        future = self._future
        if future is None:
            return self.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
        try:
            future.result(timeout=timeout)
        except TimeoutError:
            return False
        return True

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
            status = self.status
            error = self.error
            created_at = self.created_at
            started_at = self.started_at
            finished_at = self.finished_at
            event_count = len(self._events)
            result = deepcopy(self._result_snapshot)
        planner: dict[str, object] = (
            result.get("planner", {})
            if result and isinstance(result.get("planner", {}), dict)
            else {}
        )
        runs: list[dict[str, object]] = (
            result.get("runs", [])
            if result and isinstance(result.get("runs", []), list)
            else []
        )
        hypothesis_state = result.get("hypotheses", {}) if result else {}
        hypotheses: list[dict[str, object]] = (
            hypothesis_state.get("hypotheses", [])
            if isinstance(hypothesis_state, dict)
            and isinstance(hypothesis_state.get("hypotheses", []), list)
            else []
        )
        traces: list[dict[str, object]] = (
            result.get("decision_trace", [])
            if result and isinstance(result.get("decision_trace", []), list)
            else []
        )
        pending = planner.get("pending_experiment")
        leading = max(
            hypotheses,
            key=lambda item: (
                float(item.get("confidence", 0.0)),
                str(item.get("hypothesis_id", "")),
            ),
            default=None,
        )
        latest_failure = next(
            (
                run.get("outcome")
                for run in reversed(runs)
                if isinstance(run.get("outcome"), dict)
                and not run["outcome"].get("passed", False)
            ),
            None,
        )
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
            "current_phase": pending.get("phase") if isinstance(pending, dict) else None,
            "current_experiment": pending.get("experiment_id") if isinstance(pending, dict) else None,
            "completed_experiments": len(runs),
            "budget_remaining": planner.get("remaining_budget"),
            "active_hypothesis": leading.get("hypothesis_id") if leading else None,
            "leading_hypothesis": leading,
            "latest_decision": traces[-1] if traces else None,
            "latest_failure": latest_failure,
            "result": result,
        }

    def evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluation IDs retained by this session for cleanup."""
        with self._lock:
            result = deepcopy(self._result_snapshot)
        if not result:
            return ()
        return tuple(
            str(run["evaluation_id"])
            for run in result.get("runs", [])
            if isinstance(run, dict) and run.get("evaluation_id")
        )


class InvestigationSessionStore:
    """Thread-safe process store for active and completed investigation sessions."""

    def __init__(
        self,
        max_workers: int = 2,
        max_queued: int = 8,
        retention_seconds: float = 3600.0,
        max_sessions: int = 256,
    ) -> None:
        if max_workers < 1 or max_queued < 0 or retention_seconds <= 0 or max_sessions < 1:
            raise ValueError("invalid investigation store capacity or retention settings")
        self._sessions: dict[str, InvestigationSession] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="investigation"
        )
        self._admission = threading.BoundedSemaphore(max_workers + max_queued)
        self._retention_seconds = retention_seconds
        self._max_sessions = max_sessions

    def _release_slot(self) -> None:
        """Release one admitted worker or queued job slot."""
        self._admission.release()

    def _discard_evaluations(self, session: InvestigationSession) -> None:
        """Remove session-owned evaluations when a session leaves retention."""
        remover = getattr(session.run_manager, "remove_evaluation", None)
        if remover is None:
            return
        for evaluation_id in session.evaluation_ids():
            remover(evaluation_id)

    def _evict_locked(self) -> None:
        """Apply terminal-session TTL and LRU bounds; caller holds the store lock."""
        now = time.time()
        expired = [
            session
            for session in self._sessions.values()
            if session.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
            and session.finished_at is not None
            and now - session.finished_at >= self._retention_seconds
        ]
        for session in expired:
            self._sessions.pop(session.investigation_id, None)
            self._discard_evaluations(session)
        terminal = sorted(
            (
                session
                for session in self._sessions.values()
                if session.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
            ),
            key=lambda session: session.finished_at or session.created_at,
        )
        for session in terminal[: max(0, len(self._sessions) - self._max_sessions)]:
            self._sessions.pop(session.investigation_id, None)
            self._discard_evaluations(session)

    def create(
        self,
        config: InvestigatorConfig,
        run_manager: Optional[RunManager] = None,
    ) -> InvestigationSession:
        """Create and retain a new session without starting its worker."""
        with self._lock:
            self._evict_locked()
            for _ in range(3):
                investigation_id = f"investigation_{uuid.uuid4()}"
                if investigation_id not in self._sessions:
                    session = InvestigationSession(
                        config,
                        run_manager=run_manager,
                        investigation_id=investigation_id,
                    )
                    self._sessions[investigation_id] = session
                    return session
        raise RuntimeError("could not allocate a unique investigation ID")

    def start(self, session: InvestigationSession) -> bool:
        """Admit a session to bounded execution or record explicit overload failure."""
        if not self._admission.acquire(blocking=False):
            session.fail("investigation execution capacity exhausted")
            return False
        started = session.start(executor=self._executor, on_finished=self._release_slot)
        if not started:
            self._release_slot()
        return started

    def get(self, investigation_id: str) -> Optional[InvestigationSession]:
        """Look up a session by its stable public identifier."""
        with self._lock:
            self._evict_locked()
            return self._sessions.get(investigation_id)

    def list(self) -> tuple[InvestigationSession, ...]:
        """Return all retained sessions in creation order."""
        with self._lock:
            self._evict_locked()
            return tuple(self._sessions.values())

    def delete(self, investigation_id: str) -> bool:
        """Delete a terminal session and its retained evaluations."""
        with self._lock:
            session = self._sessions.get(investigation_id)
            if session is None:
                return False
            if session.status == InvestigationStatus.RUNNING:
                raise RuntimeError("cannot delete a running investigation")
            del self._sessions[investigation_id]
            self._discard_evaluations(session)
            return True


default_investigation_store: InvestigationSessionStore = InvestigationSessionStore()

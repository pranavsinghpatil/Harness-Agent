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
        self.last_accessed_at: float = self.created_at
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
        event: HarnessEvent = HarnessEvent(
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
            subscribers: tuple[queue.Queue[HarnessEvent], ...] = tuple(self._subscribers)
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
            subscribers: tuple[queue.Queue[HarnessEvent], ...] = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)

    def start(
        self,
        executor: Optional[Executor] = None,
        on_finished: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Start the investigation exactly once on a bounded executor.

        Args:
            executor: Optional executor used for the worker submission.
            on_finished: Optional callback invoked after the worker reaches a
                terminal state.

        Returns:
            `True` when the worker was submitted, or `False` when submission
            failed and the session was marked failed.

        Raises:
            RuntimeError: If this session has already started or terminated.
        """
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
        """Record a deterministic pre-execution failure.

        Running workers own their terminal transition; rejecting a call to
        `fail()` after execution has started therefore raises instead of
        allowing a later worker completion to publish a contradictory state.
        """
        with self._lock:
            if self.status != InvestigationStatus.CREATED:
                raise RuntimeError("cannot fail an investigation after execution starts")
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
            investigator: AutonomousInvestigator = AutonomousInvestigator(
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
                if self.status == InvestigationStatus.RUNNING:
                    self._mark_failed_locked(f"{type(exc).__name__}: {exc}")
        else:
            with self._lock:
                if self.status != InvestigationStatus.RUNNING:
                    return
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
        future: Optional[Future[None]] = self._future
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
            history: tuple[HarnessEvent, ...] = tuple(self._events)
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
            status: InvestigationStatus = self.status
            error: Optional[str] = self.error
            created_at: float = self.created_at
            started_at: Optional[float] = self.started_at
            finished_at: Optional[float] = self.finished_at
            event_count: int = len(self._events)
            result: Optional[dict[str, object]] = deepcopy(self._result_snapshot)
        state: dict[str, object] = self._derive_snapshot_state(result)
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
            **state,
            "result": result,
        }

    @staticmethod
    def _snapshot_collections(
        result: Optional[dict[str, object]],
    ) -> tuple[
        dict[str, object],
        list[dict[str, object]],
        list[dict[str, object]],
        list[dict[str, object]],
    ]:
        """Normalize result collections before deriving control-plane state."""
        planner_value: object = result.get("planner", {}) if result else {}
        planner: dict[str, object] = planner_value if isinstance(planner_value, dict) else {}
        runs_value: object = result.get("runs", []) if result else []
        runs: list[dict[str, object]] = (
            [item for item in runs_value if isinstance(item, dict)]
            if isinstance(runs_value, list)
            else []
        )
        hypothesis_value: object = result.get("hypotheses", {}) if result else {}
        hypothesis_state: dict[str, object] = (
            hypothesis_value if isinstance(hypothesis_value, dict) else {}
        )
        hypothesis_list: object = hypothesis_state.get("hypotheses", [])
        hypotheses: list[dict[str, object]] = (
            [item for item in hypothesis_list if isinstance(item, dict)]
            if isinstance(hypothesis_list, list)
            else []
        )
        trace_value: object = result.get("decision_trace", []) if result else []
        traces: list[dict[str, object]] = (
            [item for item in trace_value if isinstance(item, dict)]
            if isinstance(trace_value, list)
            else []
        )
        return planner, runs, hypotheses, traces

    @staticmethod
    def _derive_snapshot_state(
        result: Optional[dict[str, object]],
    ) -> dict[str, object]:
        """Derive compact control-plane fields from an immutable result."""
        planner: dict[str, object]
        runs: list[dict[str, object]]
        hypotheses: list[dict[str, object]]
        traces: list[dict[str, object]]
        planner, runs, hypotheses, traces = InvestigationSession._snapshot_collections(result)
        pending_value: object = planner.get("pending_experiment")
        pending: Optional[dict[str, object]] = (
            pending_value if isinstance(pending_value, dict) else None
        )
        leading: Optional[dict[str, object]] = max(
            hypotheses,
            key=lambda item: (
                float(item.get("confidence", 0.0)),
                str(item.get("hypothesis_id", "")),
            ),
            default=None,
        )
        latest_failure: Optional[dict[str, object]] = None
        for run in reversed(runs):
            outcome_value: object = run.get("outcome")
            if isinstance(outcome_value, dict) and not outcome_value.get("passed", False):
                latest_failure = outcome_value
                break
        return {
            "current_phase": pending.get("phase") if pending else None,
            "current_experiment": pending.get("experiment_id") if pending else None,
            "completed_experiments": len(runs),
            "budget_remaining": planner.get("remaining_budget"),
            "active_hypothesis": leading.get("hypothesis_id") if leading else None,
            "leading_hypothesis": leading,
            "latest_decision": traces[-1] if traces else None,
            "latest_failure": latest_failure,
        }

    def touch(self) -> None:
        """Record a successful store lookup for terminal-session LRU retention."""
        with self._lock:
            self.last_accessed_at = time.time()

    def evaluation_ids(self) -> tuple[str, ...]:
        """Return evaluation IDs retained by this session for cleanup."""
        with self._lock:
            result: Optional[dict[str, object]] = deepcopy(self._result_snapshot)
            investigator: Optional[AutonomousInvestigator] = self._investigator
        owned: set[str] = set(investigator.evaluation_ids if investigator else ())
        if result:
            owned.update(
                str(run["evaluation_id"])
                for run in result.get("runs", [])
                if isinstance(run, dict) and run.get("evaluation_id")
            )
        return tuple(sorted(owned))


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
        self._retention_seconds: float = retention_seconds
        self._max_sessions: int = max_sessions

    def _release_slot(self) -> None:
        """Release one admitted worker or queued job slot."""
        self._admission.release()

    def _discard_evaluations(self, session: InvestigationSession) -> None:
        """Remove session-owned evaluations when a session leaves retention."""
        remover: Optional[Callable[[str], None]] = getattr(session.run_manager, "remove_evaluation", None)
        if remover is None:
            return
        for evaluation_id in session.evaluation_ids():
            remover(evaluation_id)

    def _evict_locked(self, reserved_slots: int = 0) -> None:
        """Apply terminal-session TTL and LRU bounds; caller holds the store lock."""
        now: float = time.time()
        expired: list[InvestigationSession] = [
            session
            for session in self._sessions.values()
            if session.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
            and session.finished_at is not None
            and now - session.finished_at >= self._retention_seconds
        ]
        for session in expired:
            self._sessions.pop(session.investigation_id, None)
            self._discard_evaluations(session)
        terminal: list[InvestigationSession] = sorted(
            (
                session
                for session in self._sessions.values()
                if session.status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}
            ),
            key=lambda session: session.last_accessed_at,
        )
        excess: int = max(
            0,
            len(self._sessions) + reserved_slots - self._max_sessions,
        )
        for session in terminal[:excess]:
            self._sessions.pop(session.investigation_id, None)
            self._discard_evaluations(session)

    def create(
        self,
        config: InvestigatorConfig,
        run_manager: Optional[RunManager] = None,
    ) -> InvestigationSession:
        """Create and retain a new session without starting its worker.

        Args:
            config: Investigation configuration settings.
            run_manager: Optional execution manager adapter.

        Returns:
            The created and retained InvestigationSession instance.

        Raises:
            RuntimeError: If the store reaches maximum capacity with active sessions
                or fails to allocate a unique ID.
        """
        with self._lock:
            self._evict_locked(reserved_slots=1)
            if len(self._sessions) >= self._max_sessions:
                raise RuntimeError(
                    f"Investigation session store reached capacity ({self._max_sessions}) with active sessions"
                )
            for _ in range(3):
                investigation_id: str = f"investigation_{uuid.uuid4()}"
                if investigation_id not in self._sessions:
                    session: InvestigationSession = InvestigationSession(
                        config,
                        run_manager=run_manager,
                        investigation_id=investigation_id,
                    )
                    self._sessions[investigation_id] = session
                    return session
        raise RuntimeError("could not allocate a unique investigation ID")

    def start(self, session: InvestigationSession) -> bool:
        """Admit one session to bounded execution.

        Args:
            session: Created investigation session to submit to the worker pool.

        Returns:
            `True` when the session was submitted, or `False` when capacity is
            exhausted or executor submission fails. Failed submissions publish
            an explicit session failure event.
        """
        if session.status != InvestigationStatus.CREATED:
            raise RuntimeError(f"Investigation '{session.investigation_id}' has already started")
        if not self._admission.acquire(blocking=False):
            session.fail("investigation execution capacity exhausted")
            return False
        try:
            started: bool = session.start(executor=self._executor, on_finished=self._release_slot)
        except Exception:
            self._release_slot()
            raise
        if not started:
            self._release_slot()
        return started

    def get(self, investigation_id: str) -> Optional[InvestigationSession]:
        """Look up a session by its stable public identifier."""
        with self._lock:
            self._evict_locked()
            session: Optional[InvestigationSession] = self._sessions.get(investigation_id)
            if session is not None:
                session.touch()
            return session

    def list(self) -> tuple[InvestigationSession, ...]:
        """Return all retained sessions in creation order."""
        with self._lock:
            self._evict_locked()
            return tuple(self._sessions.values())

    def delete(self, investigation_id: str) -> bool:
        """Delete one retained terminal session and its owned evaluations.

        Args:
            investigation_id: Stable public ID of the retained session.

        Returns:
            `True` when a session was deleted, or `False` when no session with
            that ID is retained. Owned evaluations are removed on success.

        Raises:
            RuntimeError: If the requested session is still running.
        """
        with self._lock:
            session: Optional[InvestigationSession] = self._sessions.get(investigation_id)
            if session is None:
                return False
            if session.status == InvestigationStatus.RUNNING:
                raise RuntimeError("cannot delete a running investigation")
            del self._sessions[investigation_id]
            self._discard_evaluations(session)
            return True


default_investigation_store: InvestigationSessionStore = InvestigationSessionStore()

"""Tests for persistent investigation lifecycle and event delivery."""

from __future__ import annotations

import queue
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from harness.investigator import InvestigatorConfig
from harness.models.evaluation import EvaluationRequest, HarnessRun, HarnessRunStatus
from harness.models.events import HarnessEvent, HarnessEventType
from harness.orchestration.investigation import (
    InvestigationEventSubscription,
    InvestigationSession,
    InvestigationSessionStore,
    InvestigationStatus,
)


class FakeRunManager:
    """Deterministic execution adapter for session lifecycle tests."""

    def __init__(self) -> None:
        self.requests: dict[str, EvaluationRequest] = {}
        self.counter: int = 0

    def create_evaluation(self, request: EvaluationRequest) -> SimpleNamespace:
        self.counter += 1
        evaluation_id: str = f"fake_eval_{self.counter}"
        self.requests[evaluation_id] = request
        return SimpleNamespace(evaluation_id=evaluation_id)

    def execute_baseline(self, evaluation_id: str) -> HarnessRun:
        return HarnessRun(
            run_id=f"fake_run_{evaluation_id}",
            evaluation_id=evaluation_id,
            status=HarnessRunStatus.COMPLETED,
            task_completed=True,
            trace_hash=f"trace_{evaluation_id}",
            metrics={"min_clearance": 2.0},
        )


class BlockingRunManager(FakeRunManager):
    """Hold one worker so store admission behavior can be tested deterministically."""

    def __init__(self) -> None:
        super().__init__()
        self.started: threading.Event = threading.Event()
        self.release: threading.Event = threading.Event()

    def execute_baseline(self, evaluation_id: str) -> HarnessRun:
        self.started.set()
        self.release.wait(timeout=5.0)
        return super().execute_baseline(evaluation_id)


def test_investigation_session_runs_in_background_and_replays_events() -> None:
    session: InvestigationSession = InvestigationSession(
        InvestigatorConfig(objective="Prove baseline execution is healthy.", budget=1),
        run_manager=FakeRunManager(),
    )
    subscription: InvestigationEventSubscription = session.subscribe()

    session.start()

    assert session.wait(timeout=5.0) is True
    assert session.status == InvestigationStatus.COMPLETED
    events: tuple[HarnessEvent, ...] = session.events()
    event_types: list[HarnessEventType] = [event.type for event in events]

    assert event_types[0] == HarnessEventType.INVESTIGATION_CREATED
    assert HarnessEventType.INVESTIGATION_STARTED in event_types
    assert HarnessEventType.EXPERIMENT_PLANNED in event_types
    assert HarnessEventType.EXPERIMENT_STARTED in event_types
    assert HarnessEventType.EXPERIMENT_COMPLETED in event_types
    assert HarnessEventType.EVIDENCE_CAPTURED in event_types
    assert HarnessEventType.HYPOTHESIS_UPDATED in event_types
    assert HarnessEventType.DECISION_RECORDED in event_types
    assert event_types[-1] == HarnessEventType.INVESTIGATION_COMPLETED
    assert all(event.investigation_id == session.investigation_id for event in events)

    replayed_types: list[HarnessEventType] = [event.type for event in subscription.events]
    live_types: list[HarnessEventType] = []
    while not subscription.queue.empty():
        live_types.append(subscription.queue.get_nowait().type)
    assert replayed_types == event_types[:1]
    assert live_types == event_types[1:]


def test_session_snapshot_exposes_live_investigation_state() -> None:
    session: InvestigationSession = InvestigationSession(
        InvestigatorConfig(objective="Expose structured state.", budget=1),
        run_manager=FakeRunManager(),
    )
    session.start()
    assert session.wait(timeout=5.0) is True

    snapshot: dict[str, Any] = session.snapshot()
    assert snapshot["status"] == "COMPLETED"
    assert snapshot["completed_experiments"] == 1
    assert "current_phase" in snapshot
    assert "budget_remaining" in snapshot
    assert "latest_decision" in snapshot
    assert "latest_failure" in snapshot


def test_store_rejects_over_capacity_without_starting_unbounded_work() -> None:
    store: InvestigationSessionStore = InvestigationSessionStore(max_workers=1, max_queued=0)
    manager: BlockingRunManager = BlockingRunManager()
    first: InvestigationSession = store.create(InvestigatorConfig(objective="first", budget=1), manager)
    second: InvestigationSession = store.create(InvestigatorConfig(objective="second", budget=1), manager)

    assert store.start(first) is True
    assert manager.started.wait(timeout=5.0) is True
    assert store.start(second) is False
    assert second.status == InvestigationStatus.FAILED
    assert "capacity exhausted" in (second.error or "")
    manager.release.set()
    assert first.wait(timeout=5.0) is True


def test_duplicate_start_does_not_consume_an_admission_permit() -> None:
    store: InvestigationSessionStore = InvestigationSessionStore(max_workers=1, max_queued=0)
    manager: BlockingRunManager = BlockingRunManager()
    first: InvestigationSession = store.create(InvestigatorConfig(objective="first", budget=1), manager)
    second: InvestigationSession = store.create(InvestigatorConfig(objective="second", budget=1), manager)

    assert store.start(first) is True
    assert manager.started.wait(timeout=5.0) is True
    with pytest.raises(RuntimeError):
        store.start(first)
    manager.release.set()
    assert first.wait(timeout=5.0) is True
    assert store.start(second) is True
    assert second.wait(timeout=5.0) is True


def test_terminal_session_lru_updates_on_successful_lookup() -> None:
    store: InvestigationSessionStore = InvestigationSessionStore(max_workers=1, max_queued=0, max_sessions=2)
    first: InvestigationSession = store.create(InvestigatorConfig(objective="first", budget=1), FakeRunManager())
    second: InvestigationSession = store.create(InvestigatorConfig(objective="second", budget=1), FakeRunManager())
    first.fail("test failure")
    second.fail("test failure")
    first.last_accessed_at = 2.0
    second.last_accessed_at = 1.0
    assert store.get(first.investigation_id) is first

    third: InvestigationSession = store.create(InvestigatorConfig(objective="third", budget=1), FakeRunManager())

    assert store.get(first.investigation_id) is first
    assert store.get(second.investigation_id) is None
    assert store.get(third.investigation_id) is third


def test_create_enforces_max_sessions_when_sessions_active() -> None:
    store: InvestigationSessionStore = InvestigationSessionStore(max_workers=1, max_queued=0, max_sessions=2)
    first: InvestigationSession = store.create(InvestigatorConfig(objective="first", budget=1), FakeRunManager())
    second: InvestigationSession = store.create(InvestigatorConfig(objective="second", budget=1), FakeRunManager())
    with pytest.raises(RuntimeError, match="reached capacity"):
        store.create(InvestigatorConfig(objective="third", budget=1), FakeRunManager())

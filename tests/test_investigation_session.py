"""Tests for persistent investigation lifecycle and event delivery."""

from __future__ import annotations

from types import SimpleNamespace

from harness.investigator import InvestigatorConfig
from harness.models.evaluation import EvaluationRequest, HarnessRun, HarnessRunStatus
from harness.models.events import HarnessEventType
from harness.orchestration.investigation import InvestigationSession, InvestigationStatus


class FakeRunManager:
    """Deterministic execution adapter for session lifecycle tests."""

    def __init__(self) -> None:
        self.requests: dict[str, EvaluationRequest] = {}
        self.counter: int = 0

    def create_evaluation(self, request: EvaluationRequest) -> SimpleNamespace:
        self.counter += 1
        evaluation_id = f"fake_eval_{self.counter}"
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


def test_investigation_session_runs_in_background_and_replays_events() -> None:
    session = InvestigationSession(
        InvestigatorConfig(objective="Prove baseline execution is healthy.", budget=1),
        run_manager=FakeRunManager(),
    )
    subscription = session.subscribe()

    session.start()

    assert session.wait(timeout=5.0) is True
    assert session.status == InvestigationStatus.COMPLETED
    events = session.events()
    event_types = [event.type for event in events]

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

    replayed_types = [event.type for event in subscription.events]
    live_types = []
    while not subscription.queue.empty():
        live_types.append(subscription.queue.get_nowait().type)
    assert replayed_types == event_types[:1]
    assert live_types == event_types[1:]

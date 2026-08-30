"""Focused tests for the investigation repair approval and regression boundary."""

from __future__ import annotations

from types import SimpleNamespace
import time

from harness.investigator import InvestigatorConfig
from harness.models.evaluation import EvaluationRequest, HarnessRun, HarnessRunStatus
from harness.models.investigation import InvestigationPhase, PatchApproval
from harness.orchestration.investigation import InvestigationSession
from sandbox.safety.properties import SafetyViolation, Severity


class FailingRunManager:
    """Minimal retained-evaluation adapter for close-loop lifecycle tests."""

    def __init__(self) -> None:
        self.evaluations: dict[str, SimpleNamespace] = {}
        self.counter = 0

    def create_evaluation(self, request: EvaluationRequest) -> SimpleNamespace:
        self.counter += 1
        evaluation_id = f"eval_{self.counter}"
        evaluation = SimpleNamespace(evaluation_id=evaluation_id, request=request)
        self.evaluations[evaluation_id] = evaluation
        return evaluation

    def get_evaluation(self, evaluation_id: str) -> SimpleNamespace:
        return self.evaluations[evaluation_id]

    def execute_baseline(self, evaluation_id: str, **_: object) -> HarnessRun:
        run = HarnessRun(
            run_id=f"run_{evaluation_id}",
            evaluation_id=evaluation_id,
            status=HarnessRunStatus.SAFETY_VIOLATION,
            task_completed=False,
            violations=[
                SafetyViolation(
                    rule_name="COLLISION_AVOIDANCE",
                    timestamp=0.1,
                    severity=Severity.FATAL,
                    description="test breach",
                    details={"obstacle_id": "wall", "threshold": 0.8},
                )
            ],
        )
        self.evaluations[evaluation_id].baseline_run = run
        return run

    def execute_verification(
        self,
        evaluation_id: str,
        patched_code: str,
        **_: object,
    ) -> HarnessRun:
        assert patched_code
        return HarnessRun(
            run_id=f"verify_{evaluation_id}",
            evaluation_id=evaluation_id,
            status=HarnessRunStatus.COMPLETED,
            task_completed=True,
            distance_traveled_m=1.0,
            trace_hash=f"verified_{evaluation_id}",
        )


def test_failed_investigation_waits_for_approval_then_regresses() -> None:
    """The session owns diagnosis, human approval, verification, and regression."""
    manager = FailingRunManager()
    session = InvestigationSession(
        InvestigatorConfig(objective="Find and repair the failing controller", budget=1),
        run_manager=manager,
    )

    assert session.start() is True
    assert session.wait(timeout=5.0) is True
    pending = session.snapshot()
    assert pending["phase"] == InvestigationPhase.AWAITING_APPROVAL.value
    assert pending["diagnosis"]
    assert pending["patch"]["patch_id"]

    approval = PatchApproval(
        investigation_id=session.investigation_id,
        patch_id=str(pending["patch"]["patch_id"]),
        decision="APPROVE",
        reviewed_by="test-reviewer",
    )
    session.approve_patch(approval)
    deadline = time.time() + 5.0
    while session.status.value == "RUNNING" and time.time() < deadline:
        time.sleep(0.01)

    result = session.snapshot()
    assert result["status"] == "COMPLETED", result["error"]
    assert result["phase"] == InvestigationPhase.COMPLETED.value
    assert result["verification"]
    assert result["regression"]
    assert result["conclusion"]["outcome"] == "PROVEN_REPAIRED"
    event_types = [event.type.value for event in session.events()]
    assert "PATCH_APPROVAL_REQUESTED" in event_types
    assert "REGRESSION_COMPLETED" in event_types
    assert event_types[-1] == "INVESTIGATION_COMPLETED"

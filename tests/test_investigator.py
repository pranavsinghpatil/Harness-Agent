"""Tests for the executable System 1/System 2 investigation loop."""

from __future__ import annotations

from typing import Any
from types import SimpleNamespace

import pytest

from backend.routes.harness import InvestigationPayload
from harness.investigator import AutonomousInvestigator, InvestigatorConfig
from harness.planning import ExperimentOutcome
from harness.models.evaluation import ControllerHealth, EvaluationRequest, HarnessRun, HarnessRunStatus
from mcp_server.server import MCPServerHandler


class FakeRunManager:
    """Small deterministic adapter proving orchestration without a simulator run."""

    def __init__(self) -> None:
        self.requests: dict[str, EvaluationRequest] = {}
        self.counter: int = 0

    def create_evaluation(self, request: EvaluationRequest) -> SimpleNamespace:
        self.counter += 1
        evaluation_id = f"fake_eval_{self.counter}"
        self.requests[evaluation_id] = request
        return SimpleNamespace(evaluation_id=evaluation_id)

    def execute_baseline(self, evaluation_id: str) -> HarnessRun:
        request: EvaluationRequest = self.requests[evaluation_id]
        failed: bool = bool(request.chaos_fault_overrides)
        return HarnessRun(
            run_id=f"fake_run_{evaluation_id}",
            status=HarnessRunStatus.SAFETY_VIOLATION if failed else HarnessRunStatus.COMPLETED,
            trace_hash=f"trace_{evaluation_id}",
            task_completed=not failed,
            violations=[object()] if failed else [],
            metrics={"min_clearance": 0.0 if failed else 2.0},
        )


def test_investigator_executes_candidates_and_preserves_evidence() -> None:
    fake_manager = FakeRunManager()
    investigator = AutonomousInvestigator(
        InvestigatorConfig(
            objective="Find the smallest hardware perturbation that violates clearance.",
            budget=5,
            max_boundary_steps=0,
        ),
        run_manager=fake_manager,
    )

    result = investigator.run().to_dict()

    assert result["status"] == "BUDGET_EXHAUSTED"
    assert len(result["runs"]) == 5
    assert result["runs"][0]["experiment"]["phase"] == "BASELINE"
    assert result["runs"][1]["experiment"]["phase"] == "SCREEN"
    assert result["evidence"]["failed_experiments"] == 4
    assert result["evidence"]["tested_dimensions"]


def test_investigator_limits_a_short_run_without_spending_remaining_budget() -> None:
    investigator = AutonomousInvestigator(
        InvestigatorConfig(objective="Measure baseline only.", budget=10),
        run_manager=FakeRunManager(),
    )

    result = investigator.run(max_experiments=1).to_dict()

    assert len(result["runs"]) == 1
    assert result["runs"][0]["experiment"]["phase"] == "BASELINE"
    assert result["planner"]["budget"] == 10
    assert result["status"] == "PARTIAL"

    repeated_result: dict[str, Any] = investigator.run(max_experiments=1).to_dict()
    assert repeated_result["status"] == "PARTIAL"


def test_noop_limit_does_not_downgrade_exhausted_investigation() -> None:
    investigator: AutonomousInvestigator = AutonomousInvestigator(
        InvestigatorConfig(objective="Exhaust the configured budget.", budget=1),
        run_manager=FakeRunManager(),
    )
    investigator.run()

    result: dict[str, Any] = investigator.run(max_experiments=1).to_dict()

    assert result["status"] == "BUDGET_EXHAUSTED"


def test_exact_lower_limit_is_complete_when_planner_has_no_next_candidate() -> None:
    investigator: AutonomousInvestigator = AutonomousInvestigator(
        InvestigatorConfig(
            objective="Finish the finite no-boundary search.",
            budget=10,
            max_boundary_steps=0,
        ),
        run_manager=FakeRunManager(),
    )

    result: dict[str, Any] = investigator.run(max_experiments=5).to_dict()

    assert len(result["runs"]) == 5
    assert result["status"] == "COMPLETE"


def test_investigation_payload_rejects_whitespace_objective() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        InvestigationPayload(objective="   \t")

    with pytest.raises(ValueError, match="must be a string"):
        InvestigationPayload(objective=None)


def test_incomplete_completed_run_is_not_passing_evidence() -> None:
    run: HarnessRun = HarnessRun(
        status=HarnessRunStatus.COMPLETED,
        controller_health=ControllerHealth.HEALTHY,
        task_completed=False,
    )

    outcome: ExperimentOutcome = AutonomousInvestigator._to_outcome(run)

    assert outcome.passed is False


def test_rejected_run_limit_does_not_mutate_investigation_status() -> None:
    investigator: AutonomousInvestigator = AutonomousInvestigator(
        InvestigatorConfig(objective="Reject invalid limits."),
        run_manager=FakeRunManager(),
    )

    try:
        investigator.run(max_experiments=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid experiment limit to fail")

    result: dict[str, Any] = investigator.to_dict()
    assert result["run_limit"] is None


def test_mcp_manifest_exposes_autonomous_investigation() -> None:
    tool = next(
        tool for tool in MCPServerHandler.TOOLS_MANIFEST
        if tool["name"] == "investigate_reliability"
    )

    assert "objective" in tool["inputSchema"]["required"]
    assert "budget" in tool["inputSchema"]["properties"]

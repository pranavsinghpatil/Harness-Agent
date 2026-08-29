"""Tests for the executable System 1/System 2 investigation loop."""

from __future__ import annotations

from types import SimpleNamespace

from harness.investigator import AutonomousInvestigator, InvestigatorConfig
from harness.models.evaluation import HarnessRun, HarnessRunStatus
from mcp_server.server import MCPServerHandler


class FakeRunManager:
    """Small deterministic adapter proving orchestration without a simulator run."""

    def __init__(self) -> None:
        self.requests = {}
        self.counter = 0

    def create_evaluation(self, request):
        self.counter += 1
        evaluation_id = f"fake_eval_{self.counter}"
        self.requests[evaluation_id] = request
        return SimpleNamespace(evaluation_id=evaluation_id)

    def execute_baseline(self, evaluation_id: str) -> HarnessRun:
        request = self.requests[evaluation_id]
        failed = bool(request.chaos_fault_overrides)
        return HarnessRun(
            run_id=f"fake_run_{evaluation_id}",
            status=HarnessRunStatus.SAFETY_VIOLATION if failed else HarnessRunStatus.COMPLETED,
            trace_hash=f"trace_{evaluation_id}",
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


def test_mcp_manifest_exposes_autonomous_investigation() -> None:
    tool = next(
        tool for tool in MCPServerHandler.TOOLS_MANIFEST
        if tool["name"] == "investigate_reliability"
    )

    assert "objective" in tool["inputSchema"]["required"]
    assert "budget" in tool["inputSchema"]["properties"]

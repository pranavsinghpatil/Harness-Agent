"""Executable autonomous investigation loop joining System 1 and System 2."""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from typing import Any, Optional

from harness.models.evaluation import (
    ControllerHealth,
    EvaluationRequest,
    HarnessRun,
    HarnessRunStatus,
)
from harness.orchestration.run_manager import RunManager, default_run_manager
from harness.planning import (
    ExperimentCandidate,
    ExperimentOutcome,
    ExperimentPlanner,
    PlannerDimension,
)
from sandbox.experiments import PerturbationSpace, default_perturbation_space


@dataclass(frozen=True)
class InvestigatorConfig:
    """User-owned investigation objective and execution constraints."""

    objective: str
    scenario_id: str = "showcase_normal_baseline"
    hardware_preset_id: str = "RDK_X5"
    controller_code: Optional[str] = None
    seed: int = 1337
    budget: int = 12
    max_boundary_steps: int = 3
    perturbation_space: PerturbationSpace = field(default_factory=default_perturbation_space)

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("investigation objective must not be empty")
        if self.budget < 1:
            raise ValueError("investigation budget must be at least 1")
        if self.max_boundary_steps < 0:
            raise ValueError("max_boundary_steps must not be negative")


@dataclass(frozen=True)
class InvestigationRun:
    """Link between a planner candidate, RunManager evaluation, and evidence."""

    candidate: ExperimentCandidate
    evaluation_id: str
    outcome: ExperimentOutcome

    def to_dict(self) -> dict[str, Any]:
        """Serialize one investigation step for REST, MCP, and audit logs."""
        return {
            "evaluation_id": self.evaluation_id,
            "experiment": self.candidate.to_dict(),
            "outcome": self.outcome.to_dict(),
        }


class AutonomousInvestigator:
    """Run a bounded, evidence-backed experiment search against System 1."""

    def __init__(
        self,
        config: InvestigatorConfig,
        run_manager: Optional[RunManager] = None,
    ) -> None:
        self.config = config
        self.run_manager = run_manager or default_run_manager
        self.investigation_id = f"investigation_{uuid.uuid4().hex[:8]}"
        self.planner = ExperimentPlanner(
            dimensions=[
                PlannerDimension(
                    id=dimension.id,
                    baseline=dimension.baseline,
                    minimum=dimension.minimum,
                    maximum=dimension.maximum,
                    higher_is_worse=dimension.higher_is_worse,
                    unit=dimension.unit,
                )
                for dimension in config.perturbation_space.dimensions
            ],
            budget=config.budget,
            seed=config.seed,
            max_boundary_steps=config.max_boundary_steps,
        )
        self._runs: list[InvestigationRun] = []

    @staticmethod
    def _to_outcome(run: HarnessRun) -> ExperimentOutcome:
        """Convert the existing run contract into planner evidence."""
        passed = (
            run.status == HarnessRunStatus.COMPLETED
            and run.controller_health == ControllerHealth.HEALTHY
            and not run.violations
        )
        return ExperimentOutcome(
            passed=passed,
            violation_count=len(run.violations),
            min_clearance=float(run.metrics.get("min_clearance", 0.0)),
            trace_hash=run.trace_hash,
            details={
                "run_id": run.run_id,
                "status": run.status.value,
                "controller_health": run.controller_health.value,
                "task_completed": run.task_completed,
                "metrics": dict(run.metrics),
            },
        )

    def _execute_candidate(self, candidate: ExperimentCandidate) -> InvestigationRun:
        """Compile and execute one candidate while preserving structured failures."""
        evaluation_id = ""
        try:
            overrides = self.config.perturbation_space.build_fault_overrides(
                values=dict(candidate.values),
                experiment_id=candidate.experiment_id,
            )
            request = EvaluationRequest(
                hardware_preset_id=self.config.hardware_preset_id,
                scenario_id=self.config.scenario_id,
                controller_code=self.config.controller_code,
                seed=self.config.seed,
                chaos_fault_overrides=overrides,
                metadata={
                    "investigation_id": self.investigation_id,
                    "experiment_id": candidate.experiment_id,
                    "experiment_phase": candidate.phase.value,
                },
            )
            evaluation = self.run_manager.create_evaluation(request)
            evaluation_id = evaluation.evaluation_id
            run = self.run_manager.execute_baseline(evaluation_id)
            outcome = self._to_outcome(run)
        except Exception as exc:
            outcome = ExperimentOutcome(
                passed=False,
                violation_count=1,
                details={
                    "execution_error": type(exc).__name__,
                    "message": str(exc),
                },
            )

        self.planner.observe(candidate.experiment_id, outcome)
        result = InvestigationRun(
            candidate=candidate,
            evaluation_id=evaluation_id,
            outcome=outcome,
        )
        self._runs.append(result)
        return result

    def run(self, max_experiments: Optional[int] = None) -> AutonomousInvestigator:
        """Execute candidates until the configured budget or optional limit."""
        limit = self.config.budget
        if max_experiments is not None:
            if max_experiments < 1:
                raise ValueError("max_experiments must be at least 1")
            limit = min(limit, max_experiments)

        while self.planner.planned_count < limit:
            candidate = self.planner.plan_next()
            if candidate is None:
                break
            self._execute_candidate(candidate)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete investigation, including explicit unknowns."""
        planner_status = self.planner.status()
        records = self.planner.ledger.records
        if self.planner.planned_count >= self.config.budget:
            status = "BUDGET_EXHAUSTED"
        elif len(records) < self.planner.planned_count:
            status = "IN_PROGRESS"
        else:
            status = "COMPLETE"

        return {
            "investigation_id": self.investigation_id,
            "objective": self.config.objective,
            "scenario_id": self.config.scenario_id,
            "hardware_preset_id": self.config.hardware_preset_id,
            "seed": self.config.seed,
            "status": status,
            "runs": [run.to_dict() for run in self._runs],
            "planner": planner_status,
            "evidence": planner_status["summary"],
        }

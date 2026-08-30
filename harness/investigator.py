"""Executable autonomous investigation loop joining System 1 and System 2."""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from typing import Any, Optional

from harness.models.evaluation import (
    ControllerHealth,
    EvaluationRequest,
    HarnessEvaluation,
    HarnessRun,
    HarnessRunStatus,
)
from harness.hypotheses import FalsificationPlan, Hypothesis, HypothesisEngine
from harness.orchestration.run_manager import RunManager, default_run_manager
from harness.reasoning.decision_trace import DecisionTrace, DecisionTraceBuilder
from harness.planning import (
    ExperimentCandidate,
    EvidenceRecord,
    ExperimentOutcome,
    ExperimentPlanner,
    PlannerDimension,
)
from sandbox.experiments import PerturbationSpace, default_perturbation_space
from sandbox.telemetry.evidence import EvidenceSnapshot, build_evidence_snapshot


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
    evidence: Optional[EvidenceSnapshot] = None
    decision_trace: Optional[DecisionTrace] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize one investigation step for REST, MCP, and audit logs."""
        return {
            "evaluation_id": self.evaluation_id,
            "experiment": self.candidate.to_dict(),
            "outcome": self.outcome.to_dict(),
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "decision_trace": self.decision_trace.to_dict() if self.decision_trace else None,
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
        self.hypothesis_engine: HypothesisEngine = HypothesisEngine()
        self._falsification_plans: list[FalsificationPlan] = []
        self._decision_traces: list[DecisionTrace] = []
        self._last_run_limit: Optional[int] = None
        self._last_run_was_caller_limited: bool = False

    @staticmethod
    def _to_outcome(run: HarnessRun) -> ExperimentOutcome:
        """Convert the existing run contract into planner evidence."""
        passed = (
            run.status == HarnessRunStatus.COMPLETED
            and run.controller_health == ControllerHealth.HEALTHY
            and run.task_completed
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
        run: Optional[HarnessRun] = None
        stage: str = "fault override construction"
        try:
            overrides: list[dict[str, Any]] = self.config.perturbation_space.build_fault_overrides(
                values=dict(candidate.values),
                experiment_id=candidate.experiment_id,
            )
            stage = "evaluation creation"
            request: EvaluationRequest = EvaluationRequest(
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
            evaluation: HarnessEvaluation = self.run_manager.create_evaluation(request)
            evaluation_id = evaluation.evaluation_id
            stage = "System 1 execution"
            run = self.run_manager.execute_baseline(evaluation_id)
            outcome: ExperimentOutcome = self._to_outcome(run)
        except Exception as exc:
            outcome = ExperimentOutcome(
                passed=False,
                violation_count=0,
                details={
                    "execution_error": type(exc).__name__,
                    "execution_stage": stage,
                    "message": str(exc),
                },
            )

        try:
            result: InvestigationRun = self._finalize_candidate(
                candidate, evaluation_id, outcome, run
            )
        except Exception:
            if self.planner.ledger.get(candidate.experiment_id) is None:
                self.planner.release(candidate.experiment_id)
            raise
        self._runs.append(result)
        return result

    def _finalize_candidate(
        self,
        candidate: ExperimentCandidate,
        evaluation_id: str,
        outcome: ExperimentOutcome,
        run: Optional[HarnessRun],
    ) -> InvestigationRun:
        """Record outcome, update beliefs, and create the run's audit trace."""
        evidence: Optional[EvidenceSnapshot] = self._build_evidence(run)
        pre_execution_hypotheses: tuple[Hypothesis, ...] = self.hypothesis_engine.hypotheses
        record: EvidenceRecord = self.planner.observe(candidate.experiment_id, outcome)
        self.hypothesis_engine.observe(record, self.planner.dimensions)
        if not outcome.passed:
            plan: Optional[FalsificationPlan] = self.hypothesis_engine.propose_falsification(
                record, self.planner.dimensions
            )
            if plan is not None:
                self._falsification_plans.append(plan)
        decision_trace: DecisionTrace = DecisionTraceBuilder.build(
            candidate=candidate,
            outcome=outcome,
            pre_execution_hypotheses=pre_execution_hypotheses,
            post_observation_hypotheses=self.hypothesis_engine.hypotheses,
            next_candidate=self.planner.peek_next(),
        )
        self._decision_traces.append(decision_trace)
        return InvestigationRun(
            candidate=candidate,
            evaluation_id=evaluation_id,
            outcome=outcome,
            evidence=evidence,
            decision_trace=decision_trace,
        )

    @staticmethod
    def _build_evidence(run: Optional[HarnessRun]) -> Optional[EvidenceSnapshot]:
        """Build provenance evidence when System 1 returned a concrete run."""
        if run is None:
            return None
        return build_evidence_snapshot(
            run_id=run.run_id,
            trace_hash=run.trace_hash,
            frames=run.telemetry_frames,
            events=[event.to_dict() for event in run.events],
        )

    def run(self, max_experiments: Optional[int] = None) -> AutonomousInvestigator:
        """Execute candidates until the configured budget or optional lower limit.

        Args:
            max_experiments: Optional absolute experiment count at which this call
                should stop. Values at or above the configured budget do not create
                a caller-limited result.

        Returns:
            This investigator instance after all runnable candidates for this call
            have been executed.

        Raises:
            ValueError: If ``max_experiments`` is provided and is less than one.
        """
        initial_planned_count: int = self.planner.planned_count
        limit: int = self.config.budget
        if max_experiments is not None:
            if max_experiments < 1:
                raise ValueError("max_experiments must be at least 1")
            limit = min(limit, max_experiments)
        self._last_run_limit = max_experiments

        while self.planner.planned_count < limit:
            candidate = self.planner.plan_next()
            if candidate is None:
                break
            self._execute_candidate(candidate)
        if max_experiments is not None and initial_planned_count < limit:
            reached_limit: bool = self.planner.planned_count >= limit
            natural_stop: bool = reached_limit and not self.planner.has_next_candidate()
            self._last_run_was_caller_limited = (
                max_experiments < self.config.budget
                and reached_limit
                and not natural_stop
            )
        elif max_experiments is None:
            self._last_run_was_caller_limited = False
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete investigation and its evidence-backed state.

        Returns:
            A dictionary containing objective metadata, execution status, run
            evidence, planner state, competing hypotheses, falsification plans, and
            ordered decision traces showing actual planner transitions.
            ``PARTIAL`` means the caller stopped before the configured budget;
            ``BUDGET_EXHAUSTED`` means no more budget remains; ``COMPLETE`` means
            the finite planner has no next candidate.
        """
        planner_status: dict[str, Any] = self.planner.status()
        records: tuple[EvidenceRecord, ...] = self.planner.ledger.records
        caller_limited: bool = self._last_run_was_caller_limited
        if caller_limited:
            status: str = "PARTIAL"
        elif self.planner.planned_count >= self.config.budget:
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
            "run_limit": self._last_run_limit,
            "runs": [run.to_dict() for run in self._runs],
            "planner": planner_status,
            "evidence": planner_status["summary"],
            "hypotheses": self.hypothesis_engine.to_dict(),
            "falsification_plans": [plan.to_dict() for plan in self._falsification_plans],
            "decision_trace": [trace.to_dict() for trace in self._decision_traces],
        }

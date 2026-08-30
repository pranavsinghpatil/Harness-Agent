"""Structured, non-sensitive decision traces for autonomous investigations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from harness.hypotheses import Hypothesis, HypothesisStatus
from harness.planning import ExperimentCandidate, ExperimentOutcome, ExperimentPhase


@dataclass(frozen=True)
class DecisionTrace:
    """Auditable record of an experiment decision and its observed consequence."""

    experiment_id: str
    phase: ExperimentPhase
    action: str
    pre_execution_hypothesis_ids: tuple[str, ...]
    post_observation_hypothesis_ids: tuple[str, ...]
    refuted_hypothesis_ids: tuple[str, ...]
    post_observation_leading_hypothesis_id: Optional[str]
    information_gain_estimate: float
    outcome_classification: str
    observation: str
    rationale: str
    next_experiment_id: Optional[str]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize a safe decision trace for REST, MCP, and UI consumers."""
        return {
            "experiment_id": self.experiment_id,
            "phase": self.phase.value,
            "action": self.action,
            "pre_execution_hypothesis_ids": list(self.pre_execution_hypothesis_ids),
            "post_observation_hypothesis_ids": list(self.post_observation_hypothesis_ids),
            "refuted_hypothesis_ids": list(self.refuted_hypothesis_ids),
            "post_observation_leading_hypothesis_id": self.post_observation_leading_hypothesis_id,
            "information_gain_estimate": self.information_gain_estimate,
            "outcome_classification": self.outcome_classification,
            "observation": self.observation,
            "rationale": self.rationale,
            "next_experiment_id": self.next_experiment_id,
            "next_action": self.next_action,
        }


class DecisionTraceBuilder:
    """Convert experiment evidence into an auditable, truthful action trace."""

    _ACTIONS: dict[ExperimentPhase, str] = {
        ExperimentPhase.BASELINE: "ESTABLISH_BASELINE",
        ExperimentPhase.SCREEN: "TEST_SINGLE_DIMENSION",
        ExperimentPhase.BOUNDARY: "NARROW_FAILURE_BOUNDARY",
        ExperimentPhase.INTERACTION: "TEST_INTERACTION",
    }
    _INFORMATION_VALUE: dict[ExperimentPhase, float] = {
        ExperimentPhase.BASELINE: 0.5,
        ExperimentPhase.SCREEN: 0.6,
        ExperimentPhase.BOUNDARY: 0.8,
        ExperimentPhase.INTERACTION: 1.0,
    }

    @classmethod
    def build(
        cls,
        candidate: ExperimentCandidate,
        outcome: ExperimentOutcome,
        pre_execution_hypotheses: tuple[Hypothesis, ...],
        post_observation_hypotheses: tuple[Hypothesis, ...],
        next_candidate: Optional[ExperimentCandidate],
    ) -> DecisionTrace:
        """Build a trace that separates selection context from belief updates.

        Args:
            candidate: Immutable experiment selected by the bounded planner.
            outcome: Structured System 1 result for the experiment.
            pre_execution_hypotheses: Selectable hypotheses available before execution.
            post_observation_hypotheses: Hypotheses after consuming this outcome.
            next_candidate: Planner preview of the candidate that will actually run next.

        Returns:
            DecisionTrace containing safe, user-visible decision metadata.

        Raises:
            ValueError: If ``candidate.phase`` is unsupported.
        """
        action: Optional[str] = cls._ACTIONS.get(candidate.phase)
        if action is None:
            raise ValueError(f"unsupported experiment phase: {candidate.phase}")
        pre_ids: tuple[str, ...] = cls._selectable_ids(pre_execution_hypotheses)
        post_ids: tuple[str, ...] = cls._selectable_ids(post_observation_hypotheses)
        refuted_ids: tuple[str, ...] = cls._refuted_ids(post_observation_hypotheses)
        leading_id: Optional[str] = cls._leading_id(post_observation_hypotheses)
        outcome_classification: str = cls._classify_outcome(outcome)
        next_experiment_id: Optional[str] = next_candidate.experiment_id if next_candidate else None
        next_action: str = cls._next_action(next_candidate)
        return DecisionTrace(
            experiment_id=candidate.experiment_id,
            phase=candidate.phase,
            action=action,
            pre_execution_hypothesis_ids=pre_ids,
            post_observation_hypothesis_ids=post_ids,
            refuted_hypothesis_ids=refuted_ids,
            post_observation_leading_hypothesis_id=leading_id,
            information_gain_estimate=cls._information_value(candidate.phase, len(pre_ids)),
            outcome_classification=outcome_classification,
            observation=cls._observation(outcome_classification),
            rationale=(
                f"{candidate.rationale} Selection basis: bounded planner progression; "
                "post-observation hypotheses are recorded separately."
            ),
            next_experiment_id=next_experiment_id,
            next_action=next_action,
        )

    @staticmethod
    def _selectable_ids(hypotheses: tuple[Hypothesis, ...]) -> tuple[str, ...]:
        """Return active and supported hypotheses in deterministic confidence order."""
        selectable: list[Hypothesis] = [
            hypothesis
            for hypothesis in hypotheses
            if hypothesis.status in (HypothesisStatus.ACTIVE, HypothesisStatus.SUPPORTED)
        ]
        selectable.sort(key=lambda item: (-item.confidence, item.hypothesis_id))
        return tuple(hypothesis.hypothesis_id for hypothesis in selectable)

    @staticmethod
    def _refuted_ids(hypotheses: tuple[Hypothesis, ...]) -> tuple[str, ...]:
        """Return refuted hypotheses as historical context, never selectable belief."""
        return tuple(sorted(
            hypothesis.hypothesis_id
            for hypothesis in hypotheses
            if hypothesis.status == HypothesisStatus.REFUTED
        ))

    @classmethod
    def _leading_id(cls, hypotheses: tuple[Hypothesis, ...]) -> Optional[str]:
        """Return the strongest current hypothesis for post-observation reporting."""
        selectable_ids: tuple[str, ...] = cls._selectable_ids(hypotheses)
        return selectable_ids[0] if selectable_ids else None

    @classmethod
    def _information_value(cls, phase: ExperimentPhase, hypothesis_count: int) -> float:
        """Estimate information value without presenting it as probability."""
        base_value: float = cls._INFORMATION_VALUE[phase]
        return min(1.0, base_value + 0.1) if hypothesis_count > 1 else base_value

    @staticmethod
    def _classify_outcome(outcome: ExperimentOutcome) -> str:
        """Classify an outcome before generating any causal interpretation."""
        details: dict[str, Any] = dict(outcome.details)
        if details.get("execution_error"):
            return "EXECUTION_ERROR"
        if outcome.violation_count > 0:
            return "SAFETY_VIOLATION"
        if details.get("status") and details["status"] != "COMPLETED":
            return "RUN_FAILURE"
        if details.get("controller_health") and details["controller_health"] != "HEALTHY":
            return "CONTROLLER_UNHEALTHY"
        if details.get("task_completed") is False:
            return "TASK_INCOMPLETE"
        return "PASS" if outcome.passed else "UNCLASSIFIED_FAILURE"

    @staticmethod
    def _observation(classification: str) -> str:
        """Render a precise, structured observation for consumers."""
        messages: dict[str, str] = {
            "SAFETY_VIOLATION": "System 1 reported a safety violation.",
            "EXECUTION_ERROR": "System 1 reported an execution error.",
            "RUN_FAILURE": "System 1 reported a failed run status.",
            "CONTROLLER_UNHEALTHY": "System 1 reported an unhealthy controller.",
            "TASK_INCOMPLETE": "System 1 reported an incomplete task.",
            "PASS": "System 1 reported a passing run.",
            "UNCLASSIFIED_FAILURE": "System 1 reported an unclassified failed run.",
        }
        return messages[classification]

    @staticmethod
    def _next_action(next_candidate: Optional[ExperimentCandidate]) -> str:
        """Describe the planner's actual next candidate or its terminal state."""
        if next_candidate is None:
            return "STOP: no further experiment is scheduled."
        return (
            f"SCHEDULED: run {next_candidate.experiment_id} "
            f"({next_candidate.phase.value}) - {next_candidate.rationale}"
        )

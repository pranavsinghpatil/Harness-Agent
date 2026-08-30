"""Structured, non-sensitive decision traces for autonomous investigations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from harness.hypotheses import Hypothesis
from harness.planning import ExperimentCandidate, ExperimentOutcome, ExperimentPhase


@dataclass(frozen=True)
class DecisionTrace:
    """Auditable record of why an experiment was selected and what follows."""

    experiment_id: str
    phase: ExperimentPhase
    action: str
    hypothesis_ids: tuple[str, ...]
    selected_hypothesis_id: Optional[str]
    information_gain_estimate: float
    observation: str
    rationale: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize a safe decision trace for REST, MCP, and UI consumers."""
        return {
            "experiment_id": self.experiment_id,
            "phase": self.phase.value,
            "action": self.action,
            "hypothesis_ids": list(self.hypothesis_ids),
            "selected_hypothesis_id": self.selected_hypothesis_id,
            "information_gain_estimate": self.information_gain_estimate,
            "observation": self.observation,
            "rationale": self.rationale,
            "next_action": self.next_action,
        }


class DecisionTraceBuilder:
    """Convert structured experiment evidence into an auditable action trace."""

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
        hypotheses: tuple[Hypothesis, ...],
    ) -> DecisionTrace:
        """Build a decision trace from one candidate, outcome, and belief state.

        Args:
            candidate: Immutable experiment selected by the bounded planner.
            outcome: Structured System 1 result for the experiment.
            hypotheses: Current competing hypotheses after observing the result.

        Returns:
            DecisionTrace containing user-visible decision metadata only.

        Raises:
            ValueError: If ``candidate.phase`` is unsupported.
        """
        action: Optional[str] = cls._ACTIONS.get(candidate.phase)
        if action is None:
            raise ValueError(f"unsupported experiment phase: {candidate.phase}")
        ordered_hypotheses: tuple[Hypothesis, ...] = tuple(
            sorted(hypotheses, key=lambda item: (-item.confidence, item.hypothesis_id))
        )
        hypothesis_ids: tuple[str, ...] = tuple(item.hypothesis_id for item in ordered_hypotheses)
        selected_hypothesis_id: Optional[str] = (
            ordered_hypotheses[0].hypothesis_id if ordered_hypotheses else None
        )
        information_gain_estimate: float = cls._information_value(candidate.phase, len(hypothesis_ids))
        observation: str = (
            "System 1 reported a passing run."
            if outcome.passed
            else "System 1 reported a safety failure."
        )
        rationale: str = cls._rationale(candidate, selected_hypothesis_id, len(hypothesis_ids))
        next_action: str = cls._next_action(outcome, candidate.phase, selected_hypothesis_id)
        return DecisionTrace(
            experiment_id=candidate.experiment_id,
            phase=candidate.phase,
            action=action,
            hypothesis_ids=hypothesis_ids,
            selected_hypothesis_id=selected_hypothesis_id,
            information_gain_estimate=information_gain_estimate,
            observation=observation,
            rationale=rationale,
            next_action=next_action,
        )

    @classmethod
    def _information_value(cls, phase: ExperimentPhase, hypothesis_count: int) -> float:
        """Estimate information value without presenting it as probability."""
        base_value: float = cls._INFORMATION_VALUE[phase]
        return min(1.0, base_value + 0.1) if hypothesis_count > 1 else base_value

    @staticmethod
    def _rationale(
        candidate: ExperimentCandidate,
        selected_hypothesis_id: Optional[str],
        hypothesis_count: int,
    ) -> str:
        """Describe the bounded decision basis without private model reasoning."""
        if selected_hypothesis_id:
            belief_context: str = (
                f"Current evidence ranks {selected_hypothesis_id} highest among "
                f"{hypothesis_count} competing hypotheses."
            )
        else:
            belief_context = "No causal hypothesis is established yet; this experiment builds the evidence baseline."
        return f"{candidate.rationale} {belief_context}"

    @staticmethod
    def _next_action(
        outcome: ExperimentOutcome,
        phase: ExperimentPhase,
        selected_hypothesis_id: Optional[str],
    ) -> str:
        """Choose the next auditable action description from current evidence."""
        if selected_hypothesis_id and not outcome.passed:
            return f"Run a controlled counterfactual for {selected_hypothesis_id}."
        if selected_hypothesis_id and outcome.passed:
            return f"Use this safe result to challenge {selected_hypothesis_id}."
        if phase == ExperimentPhase.BASELINE:
            return "Screen each perturbation dimension independently."
        return "Collect another structured observation before selecting a causal explanation."

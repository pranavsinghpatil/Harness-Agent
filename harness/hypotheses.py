"""Deterministic hypothesis tracking for evidence-driven investigations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Mapping, Optional

from harness.planning import EvidenceRecord, ExperimentPhase, PlannerDimension


class HypothesisStatus(str, Enum):
    """Current evidence state of a causal explanation."""

    ACTIVE = "ACTIVE"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"


@dataclass(frozen=True)
class Hypothesis:
    """An auditable explanation with supporting and contradicting experiments."""

    hypothesis_id: str
    statement: str
    variables: tuple[str, ...]
    supporting_experiment_ids: tuple[str, ...] = ()
    contradicting_experiment_ids: tuple[str, ...] = ()
    confidence: float = 0.5
    predicted_outcome: str = ""
    status: HypothesisStatus = HypothesisStatus.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        """Serialize the explanation and its evidence links."""
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": self.statement,
            "variables": list(self.variables),
            "supporting_experiment_ids": list(self.supporting_experiment_ids),
            "contradicting_experiment_ids": list(self.contradicting_experiment_ids),
            "confidence": round(self.confidence, 4),
            "predicted_outcome": self.predicted_outcome,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class FalsificationPlan:
    """A reproducible counterfactual intended to test one hypothesis."""

    hypothesis_id: str
    values: Mapping[str, float]
    rationale: str
    expected_outcome: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the next information-seeking experiment."""
        return {
            "hypothesis_id": self.hypothesis_id,
            "values": dict(self.values),
            "rationale": self.rationale,
            "expected_outcome": self.expected_outcome,
        }


def _slug(value: str) -> str:
    """Create a stable identifier fragment from a dimension ID."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class HypothesisEngine:
    """Maintain competing causal explanations from immutable planner evidence."""

    def __init__(self) -> None:
        self._hypotheses: dict[str, Hypothesis] = {}
        self._observed: set[str] = set()

    @property
    def hypotheses(self) -> tuple[Hypothesis, ...]:
        """Return hypotheses in deterministic identifier order."""
        return tuple(self._hypotheses[key] for key in sorted(self._hypotheses))

    def _changed_variables(
        self, record: EvidenceRecord, dimensions: tuple[PlannerDimension, ...]
    ) -> tuple[str, ...]:
        """Identify dimensions changed from their declared baseline."""
        return tuple(
            dimension.id
            for dimension in dimensions
            if record.candidate.values.get(dimension.id, dimension.baseline) != dimension.baseline
        )

    def _make_hypothesis(self, variables: tuple[str, ...]) -> Hypothesis:
        """Create a neutral hypothesis for a variable or interaction."""
        key = "+".join(_slug(variable) for variable in variables)
        subject = " and ".join(variables)
        interaction = len(variables) > 1
        statement = (
            f"Failure emerges from the interaction between {subject}."
            if interaction
            else f"Failure is caused by degradation in {subject}."
        )
        return Hypothesis(
            hypothesis_id=f"H-{key}",
            statement=statement,
            variables=variables,
            predicted_outcome=f"Restoring {subject} should remove the failure.",
        )

    def _update_hypothesis(self, hypothesis: Hypothesis, record: EvidenceRecord, supports: bool) -> Hypothesis:
        """Apply one supporting or contradicting observation and recalculate confidence."""
        supporting = (*hypothesis.supporting_experiment_ids, record.candidate.experiment_id) if supports else hypothesis.supporting_experiment_ids
        contradicting = hypothesis.contradicting_experiment_ids if supports else (*hypothesis.contradicting_experiment_ids, record.candidate.experiment_id)
        total = len(supporting) + len(contradicting)
        confidence = 0.5 + (0.5 * (len(supporting) - len(contradicting)) / total) if total else 0.5
        status = HypothesisStatus.SUPPORTED if confidence >= 0.6 else HypothesisStatus.REFUTED if confidence <= 0.4 else HypothesisStatus.ACTIVE
        return Hypothesis(
            hypothesis_id=hypothesis.hypothesis_id,
            statement=hypothesis.statement,
            variables=hypothesis.variables,
            supporting_experiment_ids=supporting,
            contradicting_experiment_ids=contradicting,
            confidence=confidence,
            predicted_outcome=hypothesis.predicted_outcome,
            status=status,
        )

    def observe(self, record: EvidenceRecord, dimensions: tuple[PlannerDimension, ...]) -> tuple[Hypothesis, ...]:
        """Update causal explanations from one completed experiment.

        Args:
            record: Immutable experiment and System 1 outcome evidence.
            dimensions: Planner dimensions and their healthy baselines.

        Returns:
            All hypotheses after this observation, sorted by stable ID.

        Raises:
            ValueError: If the same experiment is observed twice.
        """
        experiment_id = record.candidate.experiment_id
        if experiment_id in self._observed:
            raise ValueError(f"Experiment '{experiment_id}' already observed")
        self._observed.add(experiment_id)
        variables = self._changed_variables(record, dimensions)
        if not variables or record.candidate.phase == ExperimentPhase.BASELINE:
            return self.hypotheses
        key_variables = variables if not record.outcome.passed else variables[:1]
        hypothesis = self._hypotheses.get("H-" + "+".join(_slug(value) for value in key_variables))
        if hypothesis is None:
            hypothesis = self._make_hypothesis(key_variables)
        self._hypotheses[hypothesis.hypothesis_id] = self._update_hypothesis(hypothesis, record, not record.outcome.passed)
        return self.hypotheses

    def strongest(self) -> Optional[Hypothesis]:
        """Return the highest-confidence explanation, or ``None`` if no failures exist."""
        return max(self.hypotheses, key=lambda item: (item.confidence, item.hypothesis_id), default=None)

    def propose_falsification(
        self, record: EvidenceRecord, dimensions: tuple[PlannerDimension, ...]
    ) -> Optional[FalsificationPlan]:
        """Propose restoring one variable while preserving the observed failure context."""
        if record.outcome.passed:
            return None
        changed = self._changed_variables(record, dimensions)
        if not changed:
            return None
        variable = changed[0]
        hypothesis_id = "H-" + _slug(variable)
        values = dict(record.candidate.values)
        values[variable] = next(d.baseline for d in dimensions if d.id == variable)
        return FalsificationPlan(
            hypothesis_id=hypothesis_id,
            values=values,
            rationale=f"Falsify {hypothesis_id} by restoring '{variable}' while holding other conditions constant.",
            expected_outcome=f"A safe result would weaken {hypothesis_id}; a failure would support interaction or another cause.",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the current hypothesis set for APIs, MCP, and audit logs."""
        return {"hypotheses": [hypothesis.to_dict() for hypothesis in self.hypotheses]}

"""Deterministic experiment planning and evidence tracking for System 2.

The planner is intentionally model-agnostic. It chooses experiments from a
bounded perturbation space and consumes structured run outcomes; a future LLM
can explain or prioritize hypotheses without being trusted to enforce budget,
ordering, or evidence integrity.
"""

from __future__ import annotations

from copy import copy
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional


def _freeze_value(value: object) -> object:
    """Recursively convert mutable containers into immutable snapshots."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    return deepcopy(value)


def _thaw_value(value: object) -> object:
    """Convert immutable evidence containers back to JSON-compatible values."""
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return sorted((_thaw_value(item) for item in value), key=repr)
    return deepcopy(value)


class ExperimentPhase(str, Enum):
    """Stage of the adaptive investigation search."""

    BASELINE = "BASELINE"
    SCREEN = "SCREEN"
    BOUNDARY = "BOUNDARY"
    INTERACTION = "INTERACTION"


@dataclass(frozen=True)
class PlannerDimension:
    """Bounded dimension understood by the planner.

    ``higher_is_worse`` lets the same search logic handle latency and CPU
    availability without hardcoding domain-specific direction assumptions.
    """

    id: str
    baseline: float
    minimum: float
    maximum: float
    higher_is_worse: bool = True
    unit: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("dimension id must not be empty")
        if self.minimum > self.maximum:
            raise ValueError("dimension minimum must be <= maximum")
        if not self.minimum <= self.baseline <= self.maximum:
            raise ValueError("dimension baseline must be within its bounds")

    def stress_value(self) -> float:
        """Return the adverse endpoint for a screening experiment."""
        return self.maximum if self.higher_is_worse else self.minimum


@dataclass(frozen=True)
class ExperimentCandidate:
    """A fully specified experiment waiting for execution by System 1."""

    experiment_id: str
    values: Mapping[str, float]
    phase: ExperimentPhase
    rationale: str
    parent_experiment_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _freeze_value(self.values))

    def to_dict(self) -> dict[str, Any]:
        """Serialize a candidate for APIs, MCP, and audit logs."""
        return {
            "experiment_id": self.experiment_id,
            "values": dict(self.values),
            "phase": self.phase.value,
            "rationale": self.rationale,
            "parent_experiment_ids": list(self.parent_experiment_ids),
        }


@dataclass(frozen=True)
class ExperimentOutcome:
    """Structured result returned by a System 1 execution."""

    passed: bool
    violation_count: int = 0
    min_clearance: float = 0.0
    trace_hash: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.violation_count < 0:
            raise ValueError("violation_count must not be negative")
        object.__setattr__(self, "details", _freeze_value(self.details))

    def to_dict(self) -> dict[str, Any]:
        """Serialize outcome without losing quantitative evidence."""
        return {
            "passed": self.passed,
            "violation_count": self.violation_count,
            "min_clearance": self.min_clearance,
            "trace_hash": self.trace_hash,
            "details": _thaw_value(self.details),
        }


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable link between the exact experiment and its observed result."""

    candidate: ExperimentCandidate
    outcome: ExperimentOutcome

    def to_dict(self) -> dict[str, Any]:
        """Serialize an auditable evidence record."""
        return {"experiment": self.candidate.to_dict(), "outcome": self.outcome.to_dict()}


class EvidenceLedger:
    """Append-only evidence store preventing duplicate experiment results."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []
        self._experiment_ids: set[str] = set()

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        """Return evidence in deterministic execution order."""
        return tuple(self._records)

    def append(self, candidate: ExperimentCandidate, outcome: ExperimentOutcome) -> EvidenceRecord:
        """Record one completed experiment exactly once.

        Args:
            candidate: Planned experiment whose immutable values identify the run.
            outcome: Observed System 1 result and its immutable diagnostic details.

        Returns:
            The defensive ``EvidenceRecord`` snapshot stored by the ledger.

        Raises:
            ValueError: If evidence for the candidate's experiment ID already exists.
        """
        if candidate.experiment_id in self._experiment_ids:
            raise ValueError(f"Experiment '{candidate.experiment_id}' already has evidence")
        candidate_snapshot: ExperimentCandidate = ExperimentCandidate(
            experiment_id=candidate.experiment_id,
            values=dict(candidate.values),
            phase=candidate.phase,
            rationale=candidate.rationale,
            parent_experiment_ids=candidate.parent_experiment_ids,
        )
        outcome_snapshot: ExperimentOutcome = ExperimentOutcome(
            passed=outcome.passed,
            violation_count=outcome.violation_count,
            min_clearance=outcome.min_clearance,
            trace_hash=outcome.trace_hash,
            details=_thaw_value(outcome.details),
        )
        record: EvidenceRecord = EvidenceRecord(candidate=candidate_snapshot, outcome=outcome_snapshot)
        self._records.append(record)
        self._experiment_ids.add(candidate.experiment_id)
        return record

    def get(self, experiment_id: str) -> Optional[EvidenceRecord]:
        """Return evidence for an experiment if it has completed."""
        for record in self._records:
            if record.candidate.experiment_id == experiment_id:
                return record
        return None

    def has_failed(self) -> bool:
        """Return whether any observed experiment violated its safety policy."""
        return any(not record.outcome.passed for record in self._records)

    def summary(self, dimensions: list[PlannerDimension]) -> dict[str, Any]:
        """Produce a compact status summary suitable for a UI or agent.

        Args:
            dimensions: Planner dimensions used to calculate tested and unproven IDs.

        Returns:
            A mapping containing counts, tested/unproven dimension IDs, and serialized
            evidence records. The ledger is not modified and no exceptions are raised.
        """
        dimension_ids: list[str] = [dimension.id for dimension in dimensions]
        baselines: dict[str, float] = {dimension.id: dimension.baseline for dimension in dimensions}
        tested: set[str] = {
            dimension_id
            for record in self._records
            for dimension_id in dimension_ids
            if record.candidate.phase != ExperimentPhase.BASELINE
            and record.candidate.values.get(dimension_id) != baselines[dimension_id]
        }
        return {
            "total_experiments": len(self._records),
            "passed_experiments": sum(record.outcome.passed for record in self._records),
            "failed_experiments": sum(not record.outcome.passed for record in self._records),
            "tested_dimensions": sorted(tested),
            "unproven_dimensions": sorted(set(dimension_ids).difference(tested)),
            "evidence": [record.to_dict() for record in self._records],
        }


class ExperimentPlanner:
    """Budgeted, deterministic planner for high-signal perturbation search."""

    def __init__(
        self,
        dimensions: list[PlannerDimension],
        budget: int = 20,
        seed: int = 1337,
        max_boundary_steps: int = 3,
    ) -> None:
        """Create a deterministic, budgeted planner for bounded experiments.

        Args:
            dimensions: Unique bounded perturbation dimensions to screen and refine.
            budget: Maximum number of experiments that may be reserved.
            seed: Stable seed recorded with the planner for reproducible decisions.
            max_boundary_steps: Maximum binary refinements per failed dimension.

        Returns:
            None. Initializes an empty evidence ledger and planner state.

        Raises:
            ValueError: If dimensions are empty or duplicate, budget is less than one,
                or the boundary-step limit is negative.
        """
        if not dimensions:
            raise ValueError("at least one planner dimension is required")
        if len({dimension.id for dimension in dimensions}) != len(dimensions):
            raise ValueError("planner dimension IDs must be unique")
        if budget < 1:
            raise ValueError("experiment budget must be at least 1")
        if max_boundary_steps < 0:
            raise ValueError("max_boundary_steps must not be negative")

        self.dimensions: tuple[PlannerDimension, ...] = tuple(dimensions)
        self.budget: int = budget
        self.seed: int = seed
        self.max_boundary_steps: int = max_boundary_steps
        self.ledger: EvidenceLedger = EvidenceLedger()
        self._planned: dict[str, ExperimentCandidate] = {}
        self._next_sequence: int = 1

    @property
    def planned_count(self) -> int:
        """Return the number of reserved or completed experiments."""
        return len(self._planned)

    def _new_candidate(
        self,
        values: Mapping[str, float],
        phase: ExperimentPhase,
        rationale: str,
        parent_ids: tuple[str, ...] = (),
    ) -> ExperimentCandidate:
        """Reserve a candidate with a stable monotonic identifier."""
        experiment_id = f"exp_{self._next_sequence:03d}"
        self._next_sequence += 1
        candidate = ExperimentCandidate(
            experiment_id=experiment_id,
            values=dict(values),
            phase=phase,
            rationale=rationale,
            parent_experiment_ids=parent_ids,
        )
        self._planned[experiment_id] = candidate
        return candidate

    def _baseline_values(self) -> dict[str, float]:
        return {dimension.id: dimension.baseline for dimension in self.dimensions}

    def _has_unobserved_plan(self) -> bool:
        return any(self.ledger.get(experiment_id) is None for experiment_id in self._planned)

    def _screen_record(self, dimension: PlannerDimension) -> Optional[EvidenceRecord]:
        for record in self.ledger.records:
            if record.candidate.phase == ExperimentPhase.SCREEN:
                if record.candidate.values.get(dimension.id) == dimension.stress_value():
                    return record
        return None

    def _boundary_bracket(self, dimension: PlannerDimension) -> tuple[float, float, int]:
        """Return safe value, failing value, and observed refinement count."""
        safe_value = dimension.baseline
        failing_value = dimension.stress_value()
        steps = 0
        for record in self.ledger.records:
            if record.candidate.phase != ExperimentPhase.BOUNDARY:
                continue
            changed_value = record.candidate.values.get(dimension.id)
            if changed_value is None or changed_value == dimension.baseline:
                continue
            steps += 1
            if record.outcome.passed:
                safe_value = changed_value
            else:
                failing_value = changed_value
        return safe_value, failing_value, steps

    def _next_boundary_candidate(self) -> Optional[ExperimentCandidate]:
        for dimension in self.dimensions:
            screen = self._screen_record(dimension)
            if not screen or screen.outcome.passed:
                continue
            safe_value, failing_value, steps = self._boundary_bracket(dimension)
            if steps >= self.max_boundary_steps:
                continue
            midpoint = (safe_value + failing_value) / 2.0
            if midpoint == safe_value or midpoint == failing_value:
                continue
            values = self._baseline_values()
            values[dimension.id] = midpoint
            return self._new_candidate(
                values=values,
                phase=ExperimentPhase.BOUNDARY,
                rationale=(
                    f"Narrow the failure boundary for '{dimension.id}' between "
                    f"{safe_value:g} and {failing_value:g}."
                ),
                parent_ids=(screen.candidate.experiment_id,),
            )
        return None

    def _screens_complete(self) -> bool:
        return all(
            self._screen_record(dimension) is not None
            for dimension in self.dimensions
        )

    def _interaction_candidate(self) -> Optional[ExperimentCandidate]:
        if len(self.dimensions) < 2:
            return None
        failed = [
            dimension
            for dimension in self.dimensions
            if self._screen_record(dimension)
            and not self._screen_record(dimension).outcome.passed
        ]
        selected = failed[:2]
        if len(selected) < 2:
            selected.extend(
                dimension for dimension in self.dimensions if dimension not in selected
            )
        selected = selected[:2]
        screens = tuple(
            self._screen_record(dimension).candidate.experiment_id for dimension in selected
        )
        if any(
            record.candidate.phase == ExperimentPhase.INTERACTION
            and all(
                record.candidate.values.get(dimension.id) == dimension.stress_value()
                for dimension in selected
            )
            for record in self.ledger.records
        ):
            return None
        values = self._baseline_values()
        for dimension in selected:
            values[dimension.id] = dimension.stress_value()
        return self._new_candidate(
            values=values,
            phase=ExperimentPhase.INTERACTION,
            rationale=(
                f"Test interaction between '{selected[0].id}' and "
                f"'{selected[1].id}' after independent screening."
            ),
            parent_ids=screens,
        )

    def plan_next(self) -> Optional[ExperimentCandidate]:
        """Reserve the next experiment, or return ``None`` when waiting/stopped."""
        if self.planned_count >= self.budget or self._has_unobserved_plan():
            return None

        if not self._planned:
            return self._new_candidate(
                values=self._baseline_values(),
                phase=ExperimentPhase.BASELINE,
                rationale="Measure healthy behavior before applying perturbations.",
            )

        baseline = self.ledger.get("exp_001")
        if baseline is None:
            return None

        if not self._screens_complete():
            for dimension in self.dimensions:
                if self._screen_record(dimension) is None:
                    values = self._baseline_values()
                    values[dimension.id] = dimension.stress_value()
                    return self._new_candidate(
                        values=values,
                        phase=ExperimentPhase.SCREEN,
                        rationale=f"Screen adverse endpoint of '{dimension.id}'.",
                        parent_ids=(baseline.candidate.experiment_id,),
                    )

        if baseline.outcome.passed:
            boundary = self._next_boundary_candidate()
            if boundary is not None:
                return boundary

        return self._interaction_candidate()

    def has_next_candidate(self) -> bool:
        """Return whether another candidate exists without reserving it."""
        return self.peek_next() is not None

    def peek_next(self) -> Optional[ExperimentCandidate]:
        """Preview the exact next candidate without changing planner state.

        Returns:
            The candidate that a subsequent ``plan_next`` call will reserve, or
            ``None`` when the planner is waiting, exhausted, or stopped.
        """
        preview: ExperimentPlanner = copy(self)
        preview._planned = dict(self._planned)
        return preview.plan_next()

    def observe(self, experiment_id: str, outcome: ExperimentOutcome) -> EvidenceRecord:
        """Attach an execution outcome and unlock the next planner decision."""
        candidate = self._planned.get(experiment_id)
        if candidate is None:
            raise KeyError(f"Unknown planned experiment '{experiment_id}'")
        return self.ledger.append(candidate, outcome)

    def release(self, experiment_id: str) -> ExperimentCandidate:
        """Release an unobserved reservation so the candidate can be retried.

        A candidate is reserved before System 1 execution. If finalization fails
        before evidence is appended, retaining that reservation would block the
        planner permanently. Reusing the latest sequence slot keeps retry output
        deterministic and preserves the planner's baseline invariants.
        """
        candidate = self._planned.get(experiment_id)
        if candidate is None:
            raise KeyError(f"Unknown planned experiment '{experiment_id}'")
        if self.ledger.get(experiment_id) is not None:
            raise ValueError(f"Cannot release observed experiment '{experiment_id}'")

        del self._planned[experiment_id]
        latest_id = f"exp_{self._next_sequence - 1:03d}"
        if experiment_id == latest_id:
            self._next_sequence -= 1
        return candidate

    def status(self) -> dict[str, Any]:
        """Return an audit-friendly planner snapshot."""
        pending = next(
            (
                candidate
                for experiment_id, candidate in self._planned.items()
                if self.ledger.get(experiment_id) is None
            ),
            None,
        )
        return {
            "budget": self.budget,
            "remaining_budget": self.budget - self.planned_count,
            "seed": self.seed,
            "pending_experiment": pending.to_dict() if pending else None,
            "summary": self.ledger.summary(list(self.dimensions)),
        }

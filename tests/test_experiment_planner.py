"""Tests for deterministic adaptive experiment planning and evidence tracking."""

from __future__ import annotations

import pytest

from harness.planning import (
    ExperimentCandidate,
    ExperimentOutcome,
    ExperimentPhase,
    ExperimentPlanner,
    PlannerDimension,
)


def _planner() -> ExperimentPlanner:
    return ExperimentPlanner(
        dimensions=[
            PlannerDimension("camera_latency", 0.0, 0.0, 500.0),
            PlannerDimension("cpu_availability", 1.0, 0.1, 1.0, higher_is_worse=False),
            PlannerDimension("brake_effectiveness", 1.0, 0.2, 1.0, higher_is_worse=False),
        ],
        budget=12,
        max_boundary_steps=1,
    )


def _observe(
    planner: ExperimentPlanner, passed: bool, violations: int = 0
) -> ExperimentCandidate:
    candidate: ExperimentCandidate | None = planner.plan_next()
    assert candidate is not None
    planner.observe(candidate.experiment_id, ExperimentOutcome(passed, violations))
    return candidate


def test_planner_is_baseline_first_then_screens_each_dimension() -> None:
    planner = _planner()

    baseline = _observe(planner, passed=True)
    assert baseline.phase == ExperimentPhase.BASELINE

    first = _observe(planner, passed=True)
    second = _observe(planner, passed=False, violations=2)
    third = _observe(planner, passed=True)

    assert first.phase == ExperimentPhase.SCREEN
    assert second.phase == ExperimentPhase.SCREEN
    assert third.phase == ExperimentPhase.SCREEN
    assert list(first.values) == ["camera_latency", "cpu_availability", "brake_effectiveness"]
    assert second.values["cpu_availability"] == 0.1
    assert third.values["brake_effectiveness"] == 0.2


def test_failed_screen_triggers_bounded_boundary_search_then_interaction() -> None:
    planner = _planner()

    _observe(planner, passed=True)
    camera = _observe(planner, passed=False, violations=1)
    cpu = _observe(planner, passed=False, violations=1)
    _observe(planner, passed=True)

    boundary = planner.plan_next()
    assert boundary is not None
    assert boundary.phase == ExperimentPhase.BOUNDARY
    assert boundary.values["camera_latency"] == 250.0
    planner.observe(boundary.experiment_id, ExperimentOutcome(passed=False, violation_count=1))

    cpu_boundary = planner.plan_next()
    assert cpu_boundary is not None
    assert cpu_boundary.phase == ExperimentPhase.BOUNDARY
    assert cpu_boundary.values["cpu_availability"] == 0.55
    planner.observe(cpu_boundary.experiment_id, ExperimentOutcome(passed=False, violation_count=1))

    interaction = planner.plan_next()
    assert interaction is not None
    assert interaction.phase == ExperimentPhase.INTERACTION
    assert interaction.values["camera_latency"] == 500.0
    assert interaction.values["cpu_availability"] == 0.1
    assert interaction.parent_experiment_ids == (camera.experiment_id, cpu.experiment_id)


def test_ledger_rejects_duplicate_evidence_and_reports_unproven_dimensions() -> None:
    planner = _planner()
    candidate = planner.plan_next()
    assert candidate is not None
    planner.observe(candidate.experiment_id, ExperimentOutcome(passed=True))

    with pytest.raises(ValueError, match="already has evidence"):
        planner.observe(candidate.experiment_id, ExperimentOutcome(passed=True))

    summary = planner.ledger.summary(list(planner.dimensions))
    assert summary["tested_dimensions"] == []
    assert set(summary["unproven_dimensions"]) == {
        "camera_latency",
        "cpu_availability",
        "brake_effectiveness",
    }


def test_ledger_snapshots_nested_candidate_and_outcome_mappings() -> None:
    planner: ExperimentPlanner = _planner()
    candidate: ExperimentCandidate | None = planner.plan_next()
    assert candidate is not None
    values: dict[str, float] = {"camera_latency": 42.0}
    details: dict[str, dict[str, int]] = {"telemetry": {"sample": 1}}
    candidate = ExperimentCandidate(
        experiment_id=candidate.experiment_id,
        values=values,
        phase=candidate.phase,
        rationale=candidate.rationale,
    )
    outcome: ExperimentOutcome = ExperimentOutcome(passed=True, details=details)

    record = planner.ledger.append(candidate, outcome)
    values["camera_latency"] = 99.0
    details["telemetry"]["sample"] = 99

    assert record.candidate.values["camera_latency"] == 42.0
    assert record.outcome.details["telemetry"]["sample"] == 1
    assert record.outcome.to_dict()["details"] == {"telemetry": {"sample": 1}}

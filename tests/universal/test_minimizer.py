"""Tests for failure-condition minimization and boundary search."""

from __future__ import annotations

from universal_harness.case.schema import (
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)
from universal_harness.search.minimizer import FailureMinimizer


def test_minimizer_removes_unnecessary_perturbations() -> None:
    # cart_total_present=False + discount_path=True are the required causes.
    # timeout_ms=500 and latency_ms=100 are non-essential for the TypeError.
    case = FailureCase(
        id="minimizer-test",
        name="Minimizer Delta Test",
        source=SourceSpec(system="test"),
        execution=ExecutionSpec(command="python -m examples.fixtures.payment_service"),
        perturbations={
            "discount_path": True,
            "cart_total_present": False,
            "extra_param_unused": "random_value",
        },
        expected=ExpectedOutcomeSpec(outcome="failure", error_match="TypeError"),
    )

    minimizer = FailureMinimizer()
    report = minimizer.minimize(case)

    assert report.reproduced_with_minimal is True
    assert "extra_param_unused" in report.removed_parameters
    assert report.minimized_perturbations["discount_path"] is True
    assert report.minimized_perturbations["cart_total_present"] is False
    assert report.confidence >= 0.90

"""Tests for candidate verification and regression suite."""

from __future__ import annotations

from universal_harness.case.schema import (
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)
from universal_harness.verify.comparator import VerificationEngine


def test_verification_engine_verifies_candidate_fix() -> None:
    case = FailureCase(
        id="verification-test",
        name="Verification Payment Test",
        source=SourceSpec(system="test"),
        execution=ExecutionSpec(command="python -m examples.fixtures.payment_service"),
        perturbations={"discount_path": True, "cart_total_present": False},
        expected=ExpectedOutcomeSpec(outcome="failure", error_match="TypeError"),
    )

    candidate_cmd = "python -m examples.fixtures.payment_service_fixed"

    verifier = VerificationEngine()
    report = verifier.verify(case, candidate_command=candidate_cmd)

    assert report.baseline_outcome == "failure"
    assert report.candidate_outcome == "success"
    assert report.failure_resolved is True
    assert report.regressions_detected is False
    assert report.overall_verdict == "VERIFIED"
    assert report.regression_passed >= 1


def test_verification_engine_detects_failed_candidate() -> None:
    case = FailureCase(
        id="verification-fail-test",
        name="Verification Defect Test",
        source=SourceSpec(system="test"),
        execution=ExecutionSpec(command="python -m examples.fixtures.payment_service"),
        perturbations={"discount_path": True, "cart_total_present": False},
        expected=ExpectedOutcomeSpec(outcome="failure", error_match="TypeError"),
    )

    # Re-running the broken script as candidate should fail
    broken_candidate_cmd = "python -m examples.fixtures.payment_service"

    verifier = VerificationEngine()
    report = verifier.verify(case, candidate_command=broken_candidate_cmd)

    assert report.failure_resolved is False
    assert report.overall_verdict == "FIX_FAILED"

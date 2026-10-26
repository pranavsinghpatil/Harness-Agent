"""Candidate fix verification and regression comparator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from universal_harness.case.schema import FailureCase
from universal_harness.runner.executor import ExecutionResult
from universal_harness.runner.sandbox import ExecutionSandbox


@dataclass(frozen=True)
class VerificationReport:
    """Consolidated verification verdict for a candidate fix."""

    case_id: str
    baseline_outcome: str
    candidate_outcome: str
    failure_resolved: bool
    regression_total: int
    regression_passed: int
    regressions_detected: bool
    overall_verdict: str  # "VERIFIED", "FIX_FAILED", "REGRESSION_DETECTED", "BASELINE_NOT_FAILING"
    baseline_result: ExecutionResult
    candidate_result: ExecutionResult
    regression_details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "baseline_outcome": self.baseline_outcome,
            "candidate_outcome": self.candidate_outcome,
            "failure_resolved": self.failure_resolved,
            "regression_total": self.regression_total,
            "regression_passed": self.regression_passed,
            "regressions_detected": self.regressions_detected,
            "overall_verdict": self.overall_verdict,
            "baseline_result": self.baseline_result.to_dict(),
            "candidate_result": self.candidate_result.to_dict(),
            "regression_details": self.regression_details,
        }


class VerificationEngine:
    """Compares baseline vs candidate execution and runs regression verification suites."""

    def __init__(self, sandbox: Optional[ExecutionSandbox] = None):
        self.sandbox = sandbox or ExecutionSandbox()

    def verify(
        self,
        case: FailureCase,
        candidate_command: str,
        regression_cases: Optional[List[FailureCase]] = None,
        perturbation_overrides: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """Verify that a candidate command resolves the failure without introducing regressions."""
        # 1. Baseline trial
        baseline_res = self.sandbox.run(case, perturbation_overrides=perturbation_overrides)
        baseline_failed = (baseline_res.outcome == "failure" or baseline_res.outcome == "timeout")

        # 2. Candidate trial under identical failure condition
        candidate_res = self.sandbox.run(
            case,
            command_override=candidate_command,
            perturbation_overrides=perturbation_overrides,
        )
        candidate_passed = (candidate_res.outcome == "success")

        failure_resolved = baseline_failed and candidate_passed

        # 3. Regression test suite
        regression_total = 0
        regression_passed = 0
        regression_details: List[Dict[str, Any]] = []

        # If explicit regression cases are provided, execute them with candidate command
        active_regression_cases = regression_cases or []

        # If none provided, construct a nominal (zero-perturbation) control case
        if not active_regression_cases:
            nominal_case = FailureCase(
                id=f"{case.id}-nominal-control",
                name=f"Nominal Control for {case.name}",
                source=case.source,
                environment=case.environment,
                execution=case.execution,
                perturbations={},  # clean nominal conditions
                expected={"outcome": "success"},
            )
            active_regression_cases = [nominal_case]

        for reg_case in active_regression_cases:
            regression_total += 1
            reg_res = self.sandbox.run(
                reg_case,
                command_override=candidate_command,
            )
            is_pass = (reg_res.outcome == "success")
            if is_pass:
                regression_passed += 1

            regression_details.append({
                "case_id": reg_case.id,
                "name": reg_case.name,
                "outcome": reg_res.outcome,
                "passed": is_pass,
                "duration_ms": reg_res.duration_ms,
            })

        regressions_detected = (regression_passed < regression_total)

        # Overall verdict
        if not baseline_failed:
            overall_verdict = "BASELINE_NOT_FAILING"
        elif not candidate_passed:
            overall_verdict = "FIX_FAILED"
        elif regressions_detected:
            overall_verdict = "REGRESSION_DETECTED"
        else:
            overall_verdict = "VERIFIED"

        return VerificationReport(
            case_id=case.id,
            baseline_outcome=baseline_res.outcome,
            candidate_outcome=candidate_res.outcome,
            failure_resolved=failure_resolved,
            regression_total=regression_total,
            regression_passed=regression_passed,
            regressions_detected=regressions_detected,
            overall_verdict=overall_verdict,
            baseline_result=baseline_res,
            candidate_result=candidate_res,
            regression_details=regression_details,
        )

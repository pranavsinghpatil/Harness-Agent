"""Failure condition minimizer and boundary search."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional
from universal_harness.case.schema import FailureCase
from universal_harness.runner.sandbox import ExecutionSandbox


@dataclass(frozen=True)
class SearchStep:
    """One candidate evaluation during minimization."""

    step_index: int
    parameter: str
    candidate_value: Any
    outcome: str
    reproduced: bool
    details: str


@dataclass(frozen=True)
class MinimizationReport:
    """Result of failure condition minimization search."""

    case_id: str
    original_perturbations: Dict[str, Any]
    minimized_perturbations: Dict[str, Any]
    removed_parameters: List[str]
    boundary_thresholds: Dict[str, Any]
    iterations_count: int
    reproduced_with_minimal: bool
    confidence: float
    history: List[SearchStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "original_perturbations": self.original_perturbations,
            "minimized_perturbations": self.minimized_perturbations,
            "removed_parameters": self.removed_parameters,
            "boundary_thresholds": self.boundary_thresholds,
            "iterations_count": self.iterations_count,
            "reproduced_with_minimal": self.reproduced_with_minimal,
            "confidence": round(self.confidence, 3),
            "history": [
                {
                    "step_index": s.step_index,
                    "parameter": s.parameter,
                    "candidate_value": s.candidate_value,
                    "outcome": s.outcome,
                    "reproduced": s.reproduced,
                    "details": s.details,
                }
                for s in self.history
            ],
        }


class FailureMinimizer:
    """Automates failure-condition delta reduction and numerical boundary searching."""

    def __init__(self, sandbox: Optional[ExecutionSandbox] = None):
        self.sandbox = sandbox or ExecutionSandbox()

    def minimize(
        self,
        case: FailureCase,
        max_boundary_steps: int = 6,
    ) -> MinimizationReport:
        """Find the minimal subset and values of perturbations that still trigger the failure."""
        if not case.perturbations:
            return MinimizationReport(
                case_id=case.id,
                original_perturbations={},
                minimized_perturbations={},
                removed_parameters=[],
                boundary_thresholds={},
                iterations_count=0,
                reproduced_with_minimal=True,
                confidence=1.0,
            )

        current_perturbations = dict(case.perturbations)
        history: List[SearchStep] = []
        step_counter = 0

        def check_reproduction(candidate: Dict[str, Any]) -> bool:
            nonlocal step_counter
            step_counter += 1
            res = self.sandbox.run(case, perturbation_overrides=candidate)
            is_reproduced = (res.outcome == case.expected.outcome)
            if case.expected.error_match:
                is_reproduced = is_reproduced and res.matched_error
            return is_reproduced

        # Step 1: Delta-elimination of unnecessary parameters
        removed_params: List[str] = []
        for param, orig_val in list(current_perturbations.items()):
            candidate = dict(current_perturbations)
            del candidate[param]
            reproduced = check_reproduction(candidate)

            history.append(
                SearchStep(
                    step_index=step_counter,
                    parameter=param,
                    candidate_value="<omitted>",
                    outcome="reproduced" if reproduced else "not_reproduced",
                    reproduced=reproduced,
                    details=f"Tested omitting '{param}'",
                )
            )

            if reproduced:
                current_perturbations = candidate
                removed_params.append(param)

        # Step 2: Binary boundary search for numeric parameters
        boundary_thresholds: Dict[str, Any] = {}
        for param, val in list(current_perturbations.items()):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                # We attempt to find the minimal value that still reproduces the failure
                high = float(val)
                low = 0.0
                best_failing = high

                # Check if 0.0 already fails
                test_zero = dict(current_perturbations)
                test_zero[param] = 0.0 if isinstance(val, float) else 0
                if check_reproduction(test_zero):
                    boundary_thresholds[param] = 0
                    current_perturbations[param] = 0.0 if isinstance(val, float) else 0
                    history.append(
                        SearchStep(
                            step_index=step_counter,
                            parameter=param,
                            candidate_value=0,
                            outcome="reproduced",
                            reproduced=True,
                            details=f"Param '{param}' reproduced at baseline 0",
                        )
                    )
                    continue

                for _ in range(max_boundary_steps):
                    mid = (low + high) / 2.0
                    candidate_val = mid if isinstance(val, float) else int(round(mid))
                    test_cand = dict(current_perturbations)
                    test_cand[param] = candidate_val

                    reproduced = check_reproduction(test_cand)
                    history.append(
                        SearchStep(
                            step_index=step_counter,
                            parameter=param,
                            candidate_value=candidate_val,
                            outcome="reproduced" if reproduced else "not_reproduced",
                            reproduced=reproduced,
                            details=f"Binary search on '{param}' at {candidate_val}",
                        )
                    )

                    if reproduced:
                        best_failing = candidate_val
                        high = mid
                    else:
                        low = mid

                current_perturbations[param] = best_failing
                boundary_thresholds[param] = best_failing

        # Final confirmation run with minimal set
        final_reproduced = check_reproduction(current_perturbations)
        confidence = 0.98 if final_reproduced else 0.50

        return MinimizationReport(
            case_id=case.id,
            original_perturbations=case.perturbations,
            minimized_perturbations=current_perturbations,
            removed_parameters=removed_params,
            boundary_thresholds=boundary_thresholds,
            iterations_count=step_counter,
            reproduced_with_minimal=final_reproduced,
            confidence=confidence,
            history=history,
        )

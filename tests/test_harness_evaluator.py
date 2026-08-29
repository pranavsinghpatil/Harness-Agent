"""End-to-end closed-loop reliability evaluation test on the golden perturbed showcase scenario."""

from __future__ import annotations
from harness.models.evaluation import EvaluationRequest, HarnessRunStatus
from harness.evaluator.loop import ReliabilityEvaluationLoop
from harness.orchestration.run_manager import RunManager


def test_closed_loop_evaluation_golden_showcase() -> None:
    """Verify that ReliabilityEvaluationLoop takes the failing showcase and auto-hardens it into a 100% passing run."""
    run_manager = RunManager()
    eval_loop = ReliabilityEvaluationLoop(run_manager=run_manager)

    request = EvaluationRequest(
        hardware_preset_id="RDK_X5",
        scenario_id="showcase_perturbed_failure",
        seed=1337,
    )

    evaluation = eval_loop.run_full_evaluation(request)

    # 1. Baseline failed
    assert evaluation.baseline_run is not None
    assert evaluation.baseline_run.status == HarnessRunStatus.SAFETY_VIOLATION
    assert len(evaluation.baseline_run.violations) > 0

    # 2. Diagnosis generated
    assert evaluation.diagnosis is not None
    assert evaluation.diagnosis.primary_root_cause != ""

    # 3. Patch generated
    assert evaluation.patch is not None
    assert evaluation.patch.patched_code != ""

    # 4. Verification run executed on same seed 1337
    assert evaluation.verification_run is not None
    assert evaluation.verification_run.status == HarnessRunStatus.COMPLETED
    assert len(evaluation.verification_run.violations) == 0

    # 5. Final result certifies safety under modeled conditions
    assert evaluation.final_result is not None
    assert evaluation.final_result.is_safe_under_test_conditions is True
    assert evaluation.final_result.verification_violations_count == 0
    assert evaluation.final_result.min_clearance_verified > 0.8

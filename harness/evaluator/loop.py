"""Automated closed-loop reliability evaluation orchestrator."""

from __future__ import annotations
from typing import Optional

from harness.models.evaluation import (
    HarnessEvaluation,
    EvaluationRequest,
    HarnessEvaluationResult,
    HarnessRunStatus,
)
from harness.orchestration.run_manager import RunManager, default_run_manager
from harness.diagnostics.analyzer import CausalTelemetryAnalyzer
from harness.patcher.engine import AutoCodePatcher


class ReliabilityEvaluationLoop:
    """Orchestrates the full closed-loop workflow: Run -> Diagnose -> Patch -> Verify -> Report."""

    def __init__(self, run_manager: Optional[RunManager] = None) -> None:
        self.run_manager = run_manager or default_run_manager

    def run_full_evaluation(self, request: EvaluationRequest) -> HarnessEvaluation:
        """Execute the end-to-end evaluation, failure diagnosis, auto-patching, and verification.

        Args:
            request: EvaluationRequest specifying target board, scenario, controller code, and seed.

        Returns:
            Fully populated HarnessEvaluation containing baseline, diagnosis, patch, verification run, and result.
        """
        # Step 1: Initialize Evaluation
        evaluation = self.run_manager.create_evaluation(request)

        # Step 2: Execute Baseline Run
        baseline_run = self.run_manager.execute_baseline(evaluation.evaluation_id)

        # Step 3: If Baseline Passed (No Invariant Breaches and completed successfully), Finalize Result
        if not baseline_run.violations and baseline_run.status == HarnessRunStatus.COMPLETED:
            min_clearance = baseline_run.metrics.get("min_clearance", 2.0)
            evaluation.final_result = HarnessEvaluationResult(
                evaluation_id=evaluation.evaluation_id,
                is_safe_under_test_conditions=True,
                baseline_passed=True,
                verification_passed=True,
                baseline_violations_count=0,
                verification_violations_count=0,
                min_clearance_baseline=min_clearance,
                min_clearance_verified=min_clearance,
                improvement_summary="Baseline controller operated with zero safety violations.",
            )
            return evaluation

        # Step 4: Causal Failure Diagnosis
        diagnostic_report = CausalTelemetryAnalyzer.analyze_run(baseline_run)
        diagnostic_report.evaluation_id = evaluation.evaluation_id
        evaluation.diagnosis = diagnostic_report

        # Step 5: Autonomous Code Patching
        original_code = request.controller_code or ""
        patch_result = AutoCodePatcher.generate_patch(
            original_code=original_code, diagnostic_report=diagnostic_report
        )
        evaluation.patch = patch_result

        # Step 6: Execute Verification on Identical Seed & Fault Schedule
        self.run_manager.execute_verification(
            evaluation_id=evaluation.evaluation_id,
            patched_code=patch_result.patched_code,
            agent_id="verified_hardened_target",
        )

        return evaluation

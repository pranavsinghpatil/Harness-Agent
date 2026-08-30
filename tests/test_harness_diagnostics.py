"""Unit tests for CausalTelemetryAnalyzer and causal failure graph synthesis."""

from __future__ import annotations
from harness.orchestration.run_manager import RunManager
from harness.models.evaluation import EvaluationRequest, HarnessRun, HarnessRunStatus
from harness.diagnostics.analyzer import CausalTelemetryAnalyzer
from harness.models.diagnostics import CausalDiagnosticReport, FailureTriggerType


def test_causal_diagnosis_on_perturbed_showcase() -> None:
    """Verify that causal analyzer identifies the exact root cause of failure on showcase_perturbed."""
    manager = RunManager()
    req = EvaluationRequest(
        hardware_preset_id="RDK_X5",
        scenario_id="showcase_perturbed_failure",
        seed=1337,
    )
    eval_obj = manager.create_evaluation(req)
    baseline_run = manager.execute_baseline(eval_obj.evaluation_id)

    # Must detect safety violations in perturbed scenario
    assert len(baseline_run.violations) > 0

    # Analyze failure
    report = CausalTelemetryAnalyzer.analyze_run(baseline_run)
    assert report.report_id.startswith("diag_")
    assert report.failure_trigger is not None
    assert report.failure_trigger.trigger_type in (
        FailureTriggerType.COLLISION,
        FailureTriggerType.UNSAFE_STOPPING_DISTANCE,
        FailureTriggerType.STALE_OBSERVATION_ACTION,
    )
    assert len(report.causal_nodes) >= 3
    assert len(report.causal_links) >= 2
    assert len(report.patch_recommendations) >= 2
    assert "Causal Failure Diagnostic Report" in report.markdown_summary


def test_runtime_failure_is_not_reported_as_safe() -> None:
    """Violation-free timeout runs remain unproven instead of becoming safe evidence."""
    run: HarnessRun = HarnessRun(status=HarnessRunStatus.TIMEOUT, task_completed=False)

    report: CausalDiagnosticReport = CausalTelemetryAnalyzer.analyze_run(run)

    assert report.primary_root_cause == "Execution ended with run status TIMEOUT."
    assert "Execution Safe" not in report.markdown_summary

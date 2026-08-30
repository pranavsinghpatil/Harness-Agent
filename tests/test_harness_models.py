"""Unit tests for Harness domain models, event serialization, and evaluation state."""

from __future__ import annotations
from harness.models.events import HarnessEvent, HarnessEventType, EventSeverity
from harness.models.diagnostics import (
    FailureTrigger,
    FailureTriggerType,
    CausalChainNode,
    CausalLink,
    CausalDiagnosticReport,
)
from harness.models.patch import PatchResult, PatchStrategyType, PatchValidationStatus
from harness.models.evaluation import (
    HarnessEvaluation,
    HarnessRun,
    HarnessRunStatus,
    EvaluationRequest,
    HarnessEvaluationResult,
    VerificationVerdict,
    RunConfigFingerprint,
)


def test_harness_event_serialization() -> None:
    """Verify HarnessEvent serialization and schema completeness."""
    evt = HarnessEvent(
        evaluation_id="eval_123",
        run_id="run_456",
        episode_id="ep_789",
        sim_time=4.125,
        source="transport.camera",
        type=HarnessEventType.PACKET_DELIVERED,
        severity=EventSeverity.INFO,
        payload={"latency_ms": 310.0},
    )
    d = evt.to_dict()
    assert d["evaluation_id"] == "eval_123"
    assert d["sim_time"] == 4.125
    assert d["type"] == "PACKET_DELIVERED"
    assert d["payload"]["latency_ms"] == 310.0


def test_causal_diagnostic_report_serialization() -> None:
    """Verify CausalDiagnosticReport data structure."""
    trigger = FailureTrigger(
        trigger_type=FailureTriggerType.COLLISION,
        timestamp=4.12,
        entity_id="crossing_pedestrian",
        vehicle_speed=3.8,
        clearance=0.0,
    )
    report = CausalDiagnosticReport(
        run_id="run_test",
        primary_root_cause="Sensor staleness induced collision.",
        failure_trigger=trigger,
        causal_nodes=[
            CausalChainNode("n1", 2.0, "FAULT", "Latency injected"),
            CausalChainNode("n2", 4.12, "SAFETY", "Collision detected"),
        ],
        causal_links=[CausalLink("n1", "n2", "INDUCED_DELAY", confidence=0.95)],
    )
    d = report.to_dict()
    assert d["primary_root_cause"] == "Sensor staleness induced collision."
    assert len(d["causal_nodes"]) == 2
    assert d["causal_links"][0]["confidence"] == 0.95
    assert d["failure_trigger"]["trigger_type"] == "COLLISION"


def test_harness_evaluation_result_metrics() -> None:
    """Verify comparison metrics inside HarnessEvaluationResult."""
    res = HarnessEvaluationResult(
        evaluation_id="eval_abc",
        verdict=VerificationVerdict.VERIFIED_SAFE,
        is_safe_under_test_conditions=True,
        safety_pillar_passed=True,
        behavior_pillar_passed=True,
        runtime_health_pillar_passed=True,
        baseline_passed=False,
        verification_passed=True,
        baseline_violations_count=3,
        verification_violations_count=0,
        min_clearance_baseline=0.0,
        min_clearance_verified=1.84,
        improvement_summary="Successfully eliminated all violations.",
    )
    d = res.to_dict()
    assert d["verdict"] == "VERIFIED_SAFE"
    assert d["is_safe_under_test_conditions"] is True
    assert d["safety_pillar_passed"] is True
    assert d["baseline_violations_count"] == 3
    assert d["verification_violations_count"] == 0
    assert d["min_clearance_verified"] == 1.84


def test_harness_run_telemetry_frames_serialization() -> None:
    """Verify HarnessRun serializes full telemetry frames including dynamic obstacles and violations."""
    from sandbox.telemetry.recorder import TelemetryFrame
    frame = TelemetryFrame(
        sim_time=1.5,
        step=75,
        vehicle_state={"x": 10.0, "y": 20.0, "velocity": 2.5, "heading": 0.5},
        actuator_command={"throttle": 0.5, "brake": 0.0, "steering": 0.1, "emergency_stop": False},
        min_clearance=0.45,
        active_faults=["camera_latency"],
        sensor_queue_depths={"camera": 3},
        hardware_metrics={"cpu_utilization": 0.65, "temperature_celsius": 52.0, "is_throttled": False, "deadline_misses": 1},
        dynamic_obstacles=[{"id": "dyn_obs_1", "x": 12.0, "y": 20.5, "velocity": 1.2, "heading": -1.5}],
        new_violations=[{"rule_name": "MIN_CLEARANCE_BREACH", "description": "Clearance below 0.8m"}],
    )
    run = HarnessRun(
        run_id="run_frames_test",
        telemetry_frames=[frame],
    )
    d = run.to_dict(include_frames=True)
    assert len(d["telemetry_frames"]) == 1
    tf = d["telemetry_frames"][0]
    assert tf["sim_time"] == 1.5
    assert tf["step"] == 75
    assert len(tf["dynamic_obstacles"]) == 1
    assert tf["dynamic_obstacles"][0]["id"] == "dyn_obs_1"
    assert len(tf["new_violations"]) == 1
    assert tf["new_violations"][0]["rule_name"] == "MIN_CLEARANCE_BREACH"
    assert tf["hardware_metrics"]["cpu_utilization"] == 0.65


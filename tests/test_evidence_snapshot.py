from sandbox.telemetry.evidence import build_evidence_snapshot
from sandbox.telemetry.recorder import TelemetryFrame


def _frame(step: int, sim_time: float, clearance: float) -> TelemetryFrame:
    return TelemetryFrame(
        sim_time=sim_time,
        step=step,
        vehicle_state={"x": 1.0, "y": 2.0, "velocity": 3.0, "heading": 0.0},
        actuator_command={"throttle": 0.0, "brake": 0.5, "steering": 0.0},
        min_clearance=clearance,
        active_faults=["camera_latency"],
        sensor_queue_depths={"camera": 1},
        hardware_metrics={
            "cpu_utilization": 0.65,
            "temperature_celsius": 54.0,
            "deadline_misses": step,
        },
        dynamic_obstacles=[],
        new_violations=[],
    )


def test_snapshot_preserves_signal_provenance_and_event_order() -> None:
    snapshot = build_evidence_snapshot(
        "run_1",
        "trace_1",
        [_frame(4, 0.04, 1.2), _frame(5, 0.05, 0.7)],
        [
            {"type": "INVARIANT_BREACHED", "source": "oracle", "sim_time": 0.05},
            {"type": "FAULT_INJECTED", "source": "faults", "sim_time": 0.01},
        ],
    )

    clearance = snapshot.signals_named("min_clearance")
    assert [signal.frame_index for signal in clearance] == [0, 1]
    assert clearance[1].sim_time == 0.05
    assert [link.event_type for link in snapshot.event_links] == ["FAULT_INJECTED", "INVARIANT_BREACHED"]
    assert snapshot.to_dict()["signals"][0]["source"] == "safety.oracle"


def test_snapshot_rejects_invalid_event_time() -> None:
    try:
        build_evidence_snapshot("run_1", "trace_1", [], [{"sim_time": "later"}])
    except ValueError as exc:
        assert str(exc) == "event sim_time must be numeric"
    else:
        raise AssertionError("invalid event time should be rejected")

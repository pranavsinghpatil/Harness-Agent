from sandbox.telemetry.evidence import EvidenceSignal, EvidenceSnapshot, build_evidence_snapshot
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
    snapshot: EvidenceSnapshot = build_evidence_snapshot(
        "run_1",
        "trace_1",
        [_frame(4, 0.04, 1.2), _frame(5, 0.05, 0.7)],
        [
            {"type": "INVARIANT_BREACHED", "source": "oracle", "sim_time": 0.05},
            {"type": "FAULT_INJECTED", "source": "faults", "sim_time": 0.01},
        ],
    )

    clearance: tuple[EvidenceSignal, ...] = snapshot.signals_named("min_clearance")
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

    for invalid_time in ("nan", float("inf")):
        try:
            build_evidence_snapshot("run_1", "trace_1", [], [{"sim_time": invalid_time}])
        except ValueError as exc:
            assert "finite" in str(exc)
        else:
            raise AssertionError("non-finite event time should be rejected")


def test_snapshot_omits_missing_or_nonfinite_measurements() -> None:
    frame: TelemetryFrame = _frame(1, 0.01, float("inf"))
    frame.hardware_metrics = {"cpu_utilization": float("nan")}
    snapshot: EvidenceSnapshot = build_evidence_snapshot("run_1", "trace_1", [frame])

    assert snapshot.signals_named("min_clearance") == ()
    assert snapshot.signals_named("hardware.cpu_utilization") == ()
    assert snapshot.signals_named("hardware.temperature") == ()


def test_snapshot_freezes_nested_event_payload() -> None:
    payload: dict[str, object] = {"details": {"faults": ["camera"]}}
    snapshot: EvidenceSnapshot = build_evidence_snapshot(
        "run_1", "trace_1", [], [{"type": "FAULT", "sim_time": 0.1, "payload": payload}]
    )
    payload["details"] = {"faults": ["changed"]}

    assert snapshot.event_links[0].to_dict()["payload"] == {"details": {"faults": ["camera"]}}
    try:
        snapshot.event_links[0].payload["new"] = True  # type: ignore[index]
    except TypeError:
        pass
    else:
        raise AssertionError("event payload should be immutable")

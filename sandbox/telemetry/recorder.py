"""Telemetry frame recorder, JSONL persistence, and deterministic trace hashing."""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Callable, Optional


@dataclass
class TelemetryFrame:
    """A point-in-time snapshot of the complete simulation state."""
    sim_time: float
    step: int
    vehicle_state: dict[str, float]
    actuator_command: dict[str, float | bool | int]
    min_clearance: float
    active_faults: list[str]
    sensor_queue_depths: dict[str, int]
    hardware_metrics: dict[str, Any]
    dynamic_obstacles: list[dict[str, Any]]
    new_violations: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelemetryRecorder:
    """Captures and serializes episode execution traces and verifies determinism."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.frames: list[TelemetryFrame] = []
        self._streaming_callbacks: list[Callable[[TelemetryFrame], None]] = []

    def add_streaming_callback(self, callback: Callable[[TelemetryFrame], None]) -> None:
        self._streaming_callbacks.append(callback)

    def record_frame(self, frame: TelemetryFrame) -> None:
        self.frames.append(frame)
        for cb in self._streaming_callbacks:
            try:
                cb(frame)
            except Exception:
                pass

    def compute_trace_hash(self) -> str:
        """Computes a SHA256 checksum over all recorded vehicle positions and speeds."""
        hasher = hashlib.sha256()
        for f in self.frames:
            # Deterministic representation of physical trajectory
            state_str = (
                f"{f.sim_time:.4f}:{f.vehicle_state['x']:.4f}:{f.vehicle_state['y']:.4f}:"
                f"{f.vehicle_state['velocity']:.4f}:{f.vehicle_state['heading']:.4f}:"
                f"{f.min_clearance:.4f}"
            )
            hasher.update(state_str.encode("utf-8"))
        return hasher.hexdigest()

    def export_jsonl(self, filepath: str) -> None:
        """Write trace frames to JSON Lines file."""
        with open(filepath, "w", encoding="utf-8") as f:
            for frame in self.frames:
                f.write(json.dumps(frame.to_dict()) + "\n")

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self.frames]

    def reset(self, run_id: str) -> None:
        self.run_id = run_id
        self.frames.clear()

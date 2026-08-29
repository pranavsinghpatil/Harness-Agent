"""Deterministic, provenance-rich evidence summaries for System 1 runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from sandbox.telemetry.recorder import TelemetryFrame


@dataclass(frozen=True)
class EvidenceSignal:
    """One measured signal with the exact frame that produced it."""

    name: str
    value: float
    unit: str
    sim_time: float
    frame_index: int
    step: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize a signal while retaining its frame-level provenance."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "sim_time": self.sim_time,
            "frame_index": self.frame_index,
            "step": self.step,
            "source": self.source,
        }


@dataclass(frozen=True)
class EvidenceLink:
    """A causal-looking event link anchored to simulation time and source."""

    event_id: str
    evaluation_id: str
    episode_id: str
    event_type: str
    source: str
    sim_time: float
    severity: str
    wall_time: float
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize an event link for reports and MCP responses."""
        return {
            "event_id": self.event_id,
            "evaluation_id": self.evaluation_id,
            "episode_id": self.episode_id,
            "event_type": self.event_type,
            "source": self.source,
            "sim_time": self.sim_time,
            "severity": self.severity,
            "wall_time": self.wall_time,
            "payload": _thaw_payload(self.payload),
        }


@dataclass(frozen=True)
class EvidenceSnapshot:
    """Immutable compact evidence index for one deterministic simulation run."""

    run_id: str
    trace_hash: str
    signals: tuple[EvidenceSignal, ...]
    event_links: tuple[EvidenceLink, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot without exposing mutable internal collections."""
        return {
            "run_id": self.run_id,
            "trace_hash": self.trace_hash,
            "signals": [signal.to_dict() for signal in self.signals],
            "event_links": [link.to_dict() for link in self.event_links],
        }

    def signals_named(self, name: str) -> tuple[EvidenceSignal, ...]:
        """Return signals with a stable name in original simulation order."""
        return tuple(signal for signal in self.signals if signal.name == name)


def _numeric_signals(frame: TelemetryFrame, frame_index: int) -> Iterable[EvidenceSignal]:
    """Yield high-signal numeric observations from one telemetry frame."""
    try:
        frame_time: float = float(frame.sim_time)
    except (TypeError, ValueError):
        return
    if not math.isfinite(frame_time):
        return
    metrics: Mapping[str, Any] = frame.hardware_metrics
    vehicle: Mapping[str, Any] = frame.vehicle_state
    values: tuple[tuple[str, Any, str, str], ...] = (
        ("min_clearance", frame.min_clearance, "m", "safety.oracle"),
        ("vehicle.velocity", vehicle.get("velocity"), "m/s", "physics.vehicle"),
        ("hardware.cpu_utilization", metrics.get("cpu_utilization"), "ratio", "hardware.scheduler"),
        ("hardware.temperature", metrics.get("temperature_celsius"), "C", "hardware.scheduler"),
        ("hardware.deadline_misses", metrics.get("deadline_misses"), "count", "hardware.scheduler"),
    )
    for name, value, unit, source in values:
        if isinstance(value, (int, float)):
            numeric_value: float = float(value)
            if not math.isfinite(numeric_value):
                continue
            yield EvidenceSignal(
                name=name,
                value=numeric_value,
                unit=unit,
                sim_time=frame_time,
                frame_index=frame_index,
                step=frame.step,
                source=source,
            )


def build_evidence_snapshot(
    run_id: str,
    trace_hash: str,
    frames: Iterable[TelemetryFrame],
    events: Iterable[Mapping[str, Any]] = (),
) -> EvidenceSnapshot:
    """Build an immutable evidence index from deterministic System 1 outputs.

    Args:
        run_id: Stable identifier of the simulation run.
        trace_hash: SHA-256 hash of the recorded trace.
        frames: Telemetry frames in execution order.
        events: Canonical event dictionaries containing identity, type, source,
            simulation and wall timestamps, severity, and an optional payload.

    Returns:
        EvidenceSnapshot containing frame-level numeric signals and event links.

    Raises:
        ValueError: If an event is missing canonical identity fields, has a
            non-numeric or non-finite timestamp, or has a non-mapping payload.
    """
    signal_list: list[EvidenceSignal] = []
    for frame_index, frame in enumerate(frames):
        signal_list.extend(_numeric_signals(frame, frame_index))

    links: list[EvidenceLink] = []
    for event in events:
        required_fields: tuple[str, ...] = (
            "event_id", "evaluation_id", "episode_id", "type", "source",
            "sim_time", "severity", "wall_time",
        )
        missing_fields: list[str] = [field for field in required_fields if field not in event]
        if missing_fields:
            raise ValueError(f"event is missing required fields: {', '.join(missing_fields)}")
        try:
            sim_time: float = float(event.get("sim_time", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("event sim_time must be numeric") from exc
        if not math.isfinite(sim_time):
            raise ValueError("event sim_time must be finite")
        try:
            wall_time: float = float(event.get("wall_time"))
        except (TypeError, ValueError) as exc:
            raise ValueError("event wall_time must be numeric") from exc
        if not math.isfinite(wall_time):
            raise ValueError("event wall_time must be finite")
        event_payload: object = event.get("payload", {})
        if not isinstance(event_payload, Mapping):
            raise ValueError("event payload must be a mapping")
        links.append(
            EvidenceLink(
                event_id=str(event["event_id"]),
                evaluation_id=str(event["evaluation_id"]),
                episode_id=str(event["episode_id"]),
                event_type=str(event.get("type", "UNKNOWN")),
                source=str(event.get("source", "unknown")),
                sim_time=sim_time,
                severity=str(event["severity"]),
                wall_time=wall_time,
                payload=_freeze_payload(event_payload),
            )
        )
    links.sort(key=lambda link: (link.sim_time, link.event_type, link.source))
    return EvidenceSnapshot(
        run_id=run_id,
        trace_hash=trace_hash,
        signals=tuple(signal_list),
        event_links=tuple(links),
    )


def _freeze_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Deep-copy and freeze nested event payload containers."""
    def freeze(value: object) -> object:
        if isinstance(value, Mapping):
            return MappingProxyType({key: freeze(item) for key, item in value.items()})
        if isinstance(value, list):
            return tuple(freeze(item) for item in value)
        if isinstance(value, tuple):
            return tuple(freeze(item) for item in value)
        if isinstance(value, set):
            return frozenset(freeze(item) for item in value)
        return deepcopy(value)

    frozen: object = freeze(payload)
    if not isinstance(frozen, Mapping):
        raise ValueError("event payload must be a mapping")
    return frozen


def _thaw_payload(payload: object) -> object:
    """Convert frozen payload containers into JSON-compatible values."""
    if isinstance(payload, Mapping):
        return {key: _thaw_payload(value) for key, value in payload.items()}
    if isinstance(payload, tuple):
        return [_thaw_payload(value) for value in payload]
    if isinstance(payload, frozenset):
        return sorted((_thaw_payload(value) for value in payload), key=repr)
    return deepcopy(payload)

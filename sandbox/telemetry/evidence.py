"""Deterministic, provenance-rich evidence summaries for System 1 runs."""

from __future__ import annotations

from dataclasses import dataclass
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

    event_type: str
    source: str
    sim_time: float
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize an event link for reports and MCP responses."""
        return {
            "event_type": self.event_type,
            "source": self.source,
            "sim_time": self.sim_time,
            "payload": dict(self.payload),
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
    metrics = frame.hardware_metrics
    vehicle = frame.vehicle_state
    values = (
        ("min_clearance", frame.min_clearance, "m", "safety.oracle"),
        ("vehicle.velocity", vehicle.get("velocity", 0.0), "m/s", "physics.vehicle"),
        ("hardware.cpu_utilization", metrics.get("cpu_utilization", 0.0), "ratio", "hardware.scheduler"),
        ("hardware.temperature", metrics.get("temperature_celsius", 0.0), "C", "hardware.scheduler"),
        ("hardware.deadline_misses", metrics.get("deadline_misses", 0), "count", "hardware.scheduler"),
    )
    for name, value, unit, source in values:
        if isinstance(value, (int, float)):
            yield EvidenceSignal(
                name=name,
                value=float(value),
                unit=unit,
                sim_time=frame.sim_time,
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
        events: Event dictionaries containing ``type``, ``source``, ``sim_time``,
            and optional ``payload`` fields.

    Returns:
        EvidenceSnapshot containing frame-level numeric signals and event links.

    Raises:
        ValueError: If an event has a non-numeric simulation timestamp.
    """
    signal_list: list[EvidenceSignal] = []
    for frame_index, frame in enumerate(frames):
        signal_list.extend(_numeric_signals(frame, frame_index))

    links: list[EvidenceLink] = []
    for event in events:
        try:
            sim_time = float(event.get("sim_time", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("event sim_time must be numeric") from exc
        links.append(
            EvidenceLink(
                event_type=str(event.get("type", "UNKNOWN")),
                source=str(event.get("source", "unknown")),
                sim_time=sim_time,
                payload=dict(event.get("payload", {})),
            )
        )
    links.sort(key=lambda link: (link.sim_time, link.event_type, link.source))
    return EvidenceSnapshot(
        run_id=run_id,
        trace_hash=trace_hash,
        signals=tuple(signal_list),
        event_links=tuple(links),
    )

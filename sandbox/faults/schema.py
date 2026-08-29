"""Declarative fault injection schemas and fault taxonomy."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


SUPPORTED_FAULT_PARAMETERS: dict[tuple[str, str], frozenset[str]] = {
    ("sensor.lidar", "noise_burst"): frozenset({"scale"}),
    ("sensor.lidar", "bias_offset"): frozenset({"offset"}),
    ("sensor.lidar", "sector_loss"): frozenset({"min_angle_rad", "max_angle_rad"}),
    ("sensor.lidar", "phantom_returns"): frozenset({"rate"}),
    ("sensor.camera", "frame_drop"): frozenset({"rate"}),
    ("sensor.camera", "confidence_degradation"): frozenset({"degradation"}),
    ("sensor.position", "position_jump"): frozenset({"offset_x", "offset_y"}),
    ("transport.camera", "added_latency"): frozenset({"latency_ms"}),
    ("transport.camera", "packet_loss"): frozenset({"loss_rate"}),
    ("transport.camera", "jitter"): frozenset({"jitter_ms"}),
    ("hardware.compute", "overload"): frozenset({"compute_units"}),
    ("hardware.compute", "thermal_spike"): frozenset({"temp_increase"}),
    ("hardware.compute", "cpu_availability"): frozenset({"factor"}),
    ("actuator.brake", "reduced_effectiveness"): frozenset({"factor"}),
    ("actuator.brake", "extra_delay"): frozenset({"delay_ms"}),
    ("actuator.brake", "dropped_command"): frozenset({"drop_prob"}),
    ("actuator.steering", "stuck_value"): frozenset({"angle_rad"}),
    ("actuator.steering", "extra_delay"): frozenset({"delay_ms"}),
    ("actuator.throttle", "reduced_effectiveness"): frozenset({"factor"}),
}


def is_supported_fault_parameter(target: str, fault_type: str, parameter_name: str) -> bool:
    """Return whether a single-parameter perturbation is supported at runtime."""
    return parameter_name in SUPPORTED_FAULT_PARAMETERS.get((target, fault_type), frozenset())


class FaultDefinition(BaseModel):
    """Declarative specification of a reproducible system perturbation."""
    id: str = Field(..., description="Unique identifier for the fault")
    target: str = Field(..., description="Target boundary e.g. sensor.lidar, transport.camera, actuator.brake")
    type: str = Field(..., description="Perturbation type e.g. dropout, added_latency, reduced_effectiveness")
    start_time: float = Field(..., ge=0.0, description="Simulation time when fault begins")
    duration: float = Field(..., gt=0.0, description="Duration in seconds of the active fault")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Fault-specific configuration parameters")

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration

    def is_active_at(self, sim_time: float) -> bool:
        return self.start_time <= sim_time < self.end_time

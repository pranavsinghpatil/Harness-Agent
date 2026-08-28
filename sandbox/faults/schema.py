"""Declarative fault injection schemas and fault taxonomy."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


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

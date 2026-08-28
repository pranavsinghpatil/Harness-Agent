"""Actuator command data structure and parameters."""

from __future__ import annotations
from dataclasses import dataclass, asdict


@dataclass
class ActuatorCommand:
    """Control command dispatched from target agent to vehicle actuators."""
    throttle: float = 0.0  # [0.0, 1.0]
    brake: float = 0.0     # [0.0, 1.0]
    steering: float = 0.0  # radians [-max_steer, +max_steer]
    emergency_stop: bool = False
    command_id: int = 0
    sim_sent_time: float = 0.0

    def to_dict(self) -> dict[str, float | bool | int]:
        return asdict(self)

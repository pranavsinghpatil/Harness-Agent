"""Base interface for System-Under-Test (SUT) autonomous agents."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from sandbox.sensors.packet import SensorPacket
from sandbox.actuators.command import ActuatorCommand


class BaseTargetAgent(ABC):
    """Abstract interface that all autonomous control policies must implement."""

    def __init__(self, agent_id: str = "target_agent_v1") -> None:
        self.agent_id = agent_id

    @abstractmethod
    def reset(
        self,
        goal_x: float,
        goal_y: float,
        initial_x: float = 0.0,
        initial_y: float = 0.0,
        initial_heading: float = 0.0,
    ) -> None:
        """Reset internal memory, estimators, and targets with initial position coordinates."""
        pass

    @abstractmethod
    def receive_sensor_packets(self, packets: list[SensorPacket], current_sim_time: float) -> None:
        """Process incoming hardware sensor packets delivered by the transport layer."""
        pass

    @abstractmethod
    def step(self, current_sim_time: float) -> ActuatorCommand:
        """Execute control loop tick and output an ActuatorCommand."""
        pass

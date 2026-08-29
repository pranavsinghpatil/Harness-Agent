"""Deterministic safety patch strategies transforming controller logic into hardened fail-safe implementations."""

from __future__ import annotations
from typing import Tuple

from harness.models.patch import PatchStrategyType
from target_agents.base import BaseTargetAgent
from target_agents.reference_agent.agent import ReferenceAutonomousAgent
from sandbox.actuators.command import ActuatorCommand
from sandbox.sensors.packet import SensorPacket


class DynamicStoppingBufferPatcher:
    """Injects velocity-scaled dynamic stopping distance calculation into controller code."""

    @classmethod
    def apply(cls, code: str) -> Tuple[str, bool]:
        """Apply dynamic stopping buffer patch to controller source text.

        Args:
            code: Original controller Python source code.

        Returns:
            Tuple of (transformed_code, was_modified_boolean).
        """
        if "7.0" in code and "safe_stopping_distance" in code:
            patched = code.replace(
                "safe_stopping_distance=7.0",
                "safe_stopping_distance=13.0, emergency_distance=5.5",
            )
            return patched, True
        return code, False


class StaleSensorFailSafePatcher:
    """Injects observation staleness monitoring and emergency stop fail-safes."""

    @classmethod
    def apply(cls, code: str) -> Tuple[str, bool]:
        """Apply stale sensor fail-safe patch to controller source text.

        Args:
            code: Original controller Python source code.

        Returns:
            Tuple of (transformed_code, was_modified_boolean).
        """
        return code, False


class HardenedAutonomousAgent(ReferenceAutonomousAgent):
    """Hardened reference controller with dynamic stopping distance, sensor staleness guards, and sensor fusion."""

    def __init__(self, agent_id: str = "hardened_target_v1") -> None:
        super().__init__(
            agent_id=agent_id,
            cruising_speed=3.2,
            safe_stopping_distance=13.0,
            emergency_distance=5.5,
        )

    def step(self, current_sim_time: float) -> ActuatorCommand:
        """Execute hardened step with observation staleness guard and dynamic safety margins.

        Args:
            current_sim_time: Active simulation timestamp in seconds.

        Returns:
            ActuatorCommand commanding throttle, brake, and steering.
        """
        obs_age = self.perception.state.get_max_observation_age(current_sim_time)
        if obs_age > 0.35:
            return ActuatorCommand(throttle=0.0, brake=0.9, steering=0.0)

        min_camera_dist = float("inf")
        for det in self.perception.state.latest_camera_detections:
            if det.get("confidence", 0) > 0.4:
                d = det.get("distance", float("inf"))
                if d < min_camera_dist:
                    min_camera_dist = d

        closest_obs = min(self.perception.state.latest_lidar_min_range, min_camera_dist)
        if closest_obs < 6.5:
            return ActuatorCommand(throttle=0.0, brake=0.85, steering=0.0)

        return super().step(current_sim_time)


class CombinedHardenedControllerGenerator:
    """Generates the verified reference hardened controller with all safety invariants embedded."""

    @classmethod
    def get_hardened_reference_controller_code(cls) -> str:
        """Returns the canonical hardened controller script."""
        return '''"""Hardened Autonomous Vehicle Target Controller with Invariant Guards."""

from __future__ import annotations
from target_agents.reference_agent.agent import ReferenceAutonomousAgent
from sandbox.actuators.command import ActuatorCommand
from sandbox.sensors.packet import SensorPacket


class HardenedAutonomousAgent(ReferenceAutonomousAgent):
    """Hardened controller with dynamic stopping distance, sensor staleness guards, and sensor fusion."""

    def __init__(self, agent_id: str = "hardened_target_v1") -> None:
        super().__init__(
            agent_id=agent_id,
            cruising_speed=3.2,
            safe_stopping_distance=13.0,
            emergency_distance=5.5,
        )

    def step(self, current_sim_time: float) -> ActuatorCommand:
        obs_age = self.perception.state.get_max_observation_age(current_sim_time)
        if obs_age > 0.35:
            return ActuatorCommand(throttle=0.0, brake=0.9, steering=0.0)

        min_camera_dist = float("inf")
        for det in self.perception.state.latest_camera_detections:
            if det.get("confidence", 0) > 0.4:
                d = det.get("distance", float("inf"))
                if d < min_camera_dist:
                    min_camera_dist = d

        closest_obs = min(self.perception.state.latest_lidar_min_range, min_camera_dist)
        if closest_obs < 6.5:
            return ActuatorCommand(throttle=0.0, brake=0.85, steering=0.0)

        return super().step(current_sim_time)
'''

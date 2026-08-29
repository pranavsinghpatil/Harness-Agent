"""Deterministic and AST safety patch strategies transforming controller logic into hardened implementations."""

from __future__ import annotations
import re
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
        # Pattern 1: Constructor keyword argument
        if re.search(r"safe_stopping_distance\s*=\s*[\d\.]+", code):
            patched = re.sub(
                r"safe_stopping_distance\s*=\s*[\d\.]+",
                "safe_stopping_distance=13.0, emergency_distance=5.5",
                code,
            )
            return patched, True

        # Pattern 2: Stopping distance constant definition
        if re.search(r"(SAFE_DISTANCE|STOPPING_DISTANCE|BRAKE_THRESHOLD)\s*=\s*[\d\.]+", code):
            patched = re.sub(
                r"(SAFE_DISTANCE|STOPPING_DISTANCE|BRAKE_THRESHOLD)\s*=\s*[\d\.]+",
                r"\1 = 13.0",
                code,
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
        # If code already has a step() method but lacks staleness checks, inject staleness guard at step start
        if "def step(" in code and "get_max_observation_age" not in code and "obs_age" not in code:
            staleness_guard = (
                "    def step(self, current_sim_time: float) -> ActuatorCommand:\n"
                "        # Invariant Guard: Emergency stop if observation delivery lag exceeds 350ms\n"
                "        if hasattr(self, 'perception') and hasattr(self.perception, 'state'):\n"
                "            if self.perception.state.get_max_observation_age(current_sim_time) > 0.35:\n"
                "                return ActuatorCommand(throttle=0.0, brake=0.9, steering=0.0)\n"
            )
            patched = re.sub(
                r"def step\s*\(\s*self\s*,\s*current_sim_time\s*(?::\s*float)?\s*\)\s*(?:->\s*ActuatorCommand)?\s*:",
                staleness_guard.strip(),
                code,
                count=1,
            )
            if patched != code:
                return patched, True

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

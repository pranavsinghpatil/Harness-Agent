"""Position estimate sensor (GPS/Odometry/SLAM) with drift and jump errors."""

from __future__ import annotations
import math
from typing import Any
import numpy as np
from sandbox.sensors.base import BaseSensor
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState


class PositionSensor(BaseSensor):
    """Position / localization sensor operating typically at 10 Hz."""

    def __init__(
        self,
        sensor_id: str = "sensor.position",
        sample_rate_hz: float = 10.0,
        rng: np.random.Generator | None = None,
        position_noise_std: float = 0.1,  # 10 cm noise
        heading_noise_std: float = 0.02,  # ~1.1 degrees
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            sample_rate_hz=sample_rate_hz,
            rng=rng if rng is not None else np.random.default_rng(45),
        )
        self.position_noise_std = position_noise_std
        self.heading_noise_std = heading_noise_std
        self.drift_offset_x: float = 0.0
        self.drift_offset_y: float = 0.0
        self.jump_offset_x: float = 0.0
        self.jump_offset_y: float = 0.0

    def trigger_jump(self, offset_x: float, offset_y: float) -> None:
        """Inject a sudden position localization jump."""
        self.jump_offset_x = offset_x
        self.jump_offset_y = offset_y

    def _generate_payload(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> dict[str, Any]:
        # Slowly drifting bias
        self.drift_offset_x += float(self.rng.normal(0.0, 0.001))
        self.drift_offset_y += float(self.rng.normal(0.0, 0.001))

        noise_x = float(self.rng.normal(0.0, self.position_noise_std * self.noise_scale))
        noise_y = float(self.rng.normal(0.0, self.position_noise_std * self.noise_scale))
        noise_heading = float(self.rng.normal(0.0, self.heading_noise_std * self.noise_scale))

        est_x = state.position.x + noise_x + self.drift_offset_x + self.jump_offset_x + self.bias_offset
        est_y = state.position.y + noise_y + self.drift_offset_y + self.jump_offset_y + self.bias_offset
        est_heading = state.heading + noise_heading

        return {
            "x": round(float(est_x), 4),
            "y": round(float(est_y), 4),
            "heading": round(float(est_heading), 4),
            "estimated_speed": round(float(state.velocity), 4),
        }

    def reset(self) -> None:
        super().reset()
        self.drift_offset_x = 0.0
        self.drift_offset_y = 0.0
        self.jump_offset_x = 0.0
        self.jump_offset_y = 0.0

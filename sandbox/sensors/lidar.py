"""2D LiDAR range scanner with raycasting, Gaussian noise, sector dropout, and phantom returns."""

from __future__ import annotations
import math
from typing import Any
import numpy as np
from sandbox.sensors.base import BaseSensor
from sandbox.sensors.packet import SensorPacket
from sandbox.world.geometry import Vec2D
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState


class LidarSensor(BaseSensor):
    """2D LiDAR range sensor operating typically at 10 Hz."""

    def __init__(
        self,
        sensor_id: str = "sensor.lidar",
        sample_rate_hz: float = 10.0,
        rng: np.random.Generator | None = None,
        num_rays: int = 36,
        fov_deg: float = 180.0,
        max_range: float = 20.0,
        min_range: float = 0.1,
        noise_std: float = 0.03,  # 3 cm range standard deviation
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            sample_rate_hz=sample_rate_hz,
            rng=rng if rng is not None else np.random.default_rng(42),
        )
        self.num_rays = num_rays
        self.fov_rad = math.radians(fov_deg)
        self.max_range = max_range
        self.min_range = min_range
        self.noise_std = noise_std
        self.dropped_sectors: list[tuple[float, float]] = []  # Angle ranges (rad) to drop
        self.phantom_return_rate: float = 0.0

    def _generate_payload(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> dict[str, Any]:
        origin = state.position
        heading = state.heading
        start_angle = heading - self.fov_rad / 2.0
        angle_step = self.fov_rad / max(1, self.num_rays - 1)

        ranges: list[float] = []
        angles: list[float] = []
        hit_objects: list[str | None] = []

        for i in range(self.num_rays):
            angle = start_angle + i * angle_step
            rel_angle = angle - heading
            angles.append(round(rel_angle, 4))

            # Check for sector dropout perturbation
            is_dropped = False
            for min_a, max_a in self.dropped_sectors:
                if min_a <= rel_angle <= max_a:
                    is_dropped = True
                    break

            if is_dropped:
                ranges.append(float("inf"))
                hit_objects.append(None)
                continue

            ray_dir = Vec2D(math.cos(angle), math.sin(angle))
            hit_dist, hit_id = world_map.raycast(origin, ray_dir, self.max_range)

            if hit_dist is not None:
                # Add Gaussian range noise & bias
                noise = self.rng.normal(0.0, self.noise_std * self.noise_scale)
                measured_dist = hit_dist + noise + self.bias_offset
                measured_dist = max(self.min_range, min(self.max_range, measured_dist))
                ranges.append(round(float(measured_dist), 4))
                hit_objects.append(hit_id)
            else:
                # Phantom return injection
                if self.phantom_return_rate > 0 and self.rng.uniform(0.0, 1.0) < self.phantom_return_rate:
                    phantom_dist = self.rng.uniform(1.0, 5.0)
                    ranges.append(round(float(phantom_dist), 4))
                    hit_objects.append("phantom_reflection")
                else:
                    ranges.append(float("inf"))
                    hit_objects.append(None)

        return {
            "num_rays": self.num_rays,
            "max_range": self.max_range,
            "fov_rad": round(self.fov_rad, 4),
            "angles": angles,
            "ranges": ranges,
            "hit_objects": hit_objects,
            "closest_range": min([r for r in ranges if not math.isinf(r)], default=float("inf")),
        }

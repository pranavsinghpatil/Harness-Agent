"""Camera abstraction sensor with semantic object detections, occlusion, and confidence modeling."""

from __future__ import annotations
import math
from typing import Any
import numpy as np
from sandbox.sensors.base import BaseSensor
from sandbox.world.geometry import Vec2D
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState


class CameraSensor(BaseSensor):
    """Camera perception abstraction operating typically at 30 Hz."""

    def __init__(
        self,
        sensor_id: str = "sensor.camera",
        sample_rate_hz: float = 30.0,
        rng: np.random.Generator | None = None,
        fov_deg: float = 90.0,
        max_detection_range: float = 30.0,
        base_confidence: float = 0.95,
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            sample_rate_hz=sample_rate_hz,
            rng=rng if rng is not None else np.random.default_rng(46),
        )
        self.fov_rad = math.radians(fov_deg)
        self.max_detection_range = max_detection_range
        self.base_confidence = base_confidence
        self.is_occluded: bool = False
        self.frame_drop_rate: float = 0.0
        self.confidence_degradation: float = 0.0

    def _generate_payload(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> dict[str, Any]:
        # Handle frame drop
        if self.frame_drop_rate > 0 and self.rng.uniform(0.0, 1.0) < self.frame_drop_rate:
            return {"detections": [], "frame_dropped": True}

        if self.is_occluded:
            return {"detections": [], "is_occluded": True}

        detections: list[dict[str, Any]] = []
        origin = state.position
        heading = state.heading

        for obs in world_map.get_all_obstacles():
            to_obs = obs.position - origin
            dist = to_obs.magnitude
            if dist > self.max_detection_range:
                continue

            angle_to_obs = math.atan2(to_obs.y, to_obs.x)
            rel_angle = (angle_to_obs - heading + math.pi) % (2 * math.pi) - math.pi

            if abs(rel_angle) <= self.fov_rad / 2.0:
                # Inside FOV
                confidence = max(
                    0.1,
                    min(
                        1.0,
                        (self.base_confidence - self.confidence_degradation)
                        * (1.0 - (dist / (self.max_detection_range * 1.5))),
                    ),
                )
                detections.append(
                    {
                        "entity_id": obs.id,
                        "class_label": "dynamic_obstacle" if hasattr(obs, "target_speed") else "static_obstacle",
                        "distance": round(float(dist), 4),
                        "relative_angle": round(float(rel_angle), 4),
                        "estimated_position": {
                            "x": round(float(obs.position.x), 4),
                            "y": round(float(obs.position.y), 4),
                        },
                        "confidence": round(float(confidence), 3),
                    }
                )

        return {
            "num_detections": len(detections),
            "detections": detections,
            "fov_rad": round(self.fov_rad, 4),
            "frame_dropped": False,
        }

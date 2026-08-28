"""Perception module managing asynchronous packet arrivals and measuring data staleness."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from sandbox.sensors.packet import SensorPacket


@dataclass
class PerceptionState:
    latest_lidar_min_range: float = float("inf")
    latest_camera_detections: list[dict[str, Any]] = field(default_factory=list)
    latest_imu_yaw_rate: float = 0.0
    latest_imu_accel_x: float = 0.0
    latest_encoder_speed: float = 0.0
    latest_pos_x: float = 0.0
    latest_pos_y: float = 0.0
    latest_pos_heading: float = 0.0
    last_measurement_times: dict[str, float] = field(default_factory=dict)

    def get_max_observation_age(self, current_sim_time: float) -> float:
        """Returns the age in seconds of the oldest active sensor stream."""
        if not self.last_measurement_times:
            return 0.0
        oldest_time = min(self.last_measurement_times.values())
        return max(0.0, current_sim_time - oldest_time)


class PerceptionAggregator:
    """Consumes asynchronous sensor packets and provides clean state representation to planner."""

    def __init__(self) -> None:
        self.state = PerceptionState()

    def reset(self) -> None:
        self.state = PerceptionState()

    def update(self, packets: list[SensorPacket], current_sim_time: float) -> PerceptionState:
        for packet in packets:
            if not packet.validity:
                continue

            sid = packet.sensor_id
            self.state.last_measurement_times[sid] = packet.measurement_timestamp
            payload = packet.payload

            if sid == "sensor.lidar":
                self.state.latest_lidar_min_range = payload.get("closest_range", float("inf"))
            elif sid == "sensor.camera":
                self.state.latest_camera_detections = payload.get("detections", [])
            elif sid == "sensor.imu":
                self.state.latest_imu_yaw_rate = payload.get("angular_velocity_z", 0.0)
                self.state.latest_imu_accel_x = payload.get("linear_acceleration_x", 0.0)
            elif sid == "sensor.encoder":
                self.state.latest_encoder_speed = payload.get("estimated_speed", 0.0)
            elif sid == "sensor.position":
                self.state.latest_pos_x = payload.get("x", self.state.latest_pos_x)
                self.state.latest_pos_y = payload.get("y", self.state.latest_pos_y)
                self.state.latest_pos_heading = payload.get("heading", self.state.latest_pos_heading)

        return self.state

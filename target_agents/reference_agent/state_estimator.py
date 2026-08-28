"""State estimator fusing IMU, wheel encoder, and GPS observations."""

from __future__ import annotations
import math
from dataclasses import dataclass
from target_agents.reference_agent.perception import PerceptionState


@dataclass
class EstimatedPose:
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    speed: float = 0.0


class StateEstimator:
    """Complementary / Kalman filter fusion of localization, IMU, and odometry."""

    def __init__(self) -> None:
        self.pose = EstimatedPose()

    @property
    def x(self) -> float:
        return self.pose.x

    @property
    def y(self) -> float:
        return self.pose.y

    @property
    def heading(self) -> float:
        return self.pose.heading

    @property
    def speed(self) -> float:
        return self.pose.speed

    def reset(self, initial_x: float = 0.0, initial_y: float = 0.0, initial_heading: float = 0.0) -> None:
        self.pose = EstimatedPose(x=initial_x, y=initial_y, heading=initial_heading, speed=0.0)

    def update(self, p_state: PerceptionState, dt: float) -> EstimatedPose:
        # Fuse speed: 70% encoder, 30% integrated IMU accel
        imu_speed_estimate = self.pose.speed + p_state.latest_imu_accel_x * dt
        self.pose.speed = 0.8 * p_state.latest_encoder_speed + 0.2 * imu_speed_estimate

        # Fuse heading: position GPS heading with IMU gyro integration
        gyro_heading = self.pose.heading + p_state.latest_imu_yaw_rate * dt
        gps_heading = p_state.latest_pos_heading
        # Angular difference
        heading_diff = (gps_heading - gyro_heading + math.pi) % (2 * math.pi) - math.pi
        self.pose.heading = (gyro_heading + 0.1 * heading_diff + math.pi) % (2 * math.pi) - math.pi

        # Fuse position: GPS anchor + dead reckoning
        dr_x = self.pose.x + self.pose.speed * math.cos(self.pose.heading) * dt
        dr_y = self.pose.y + self.pose.speed * math.sin(self.pose.heading) * dt
        self.pose.x = 0.85 * dr_x + 0.15 * p_state.latest_pos_x
        self.pose.y = 0.85 * dr_y + 0.15 * p_state.latest_pos_y

        return self.pose

"""Inertial Measurement Unit (IMU) with linear acceleration, gyro yaw-rate, and bias drift."""

from __future__ import annotations
import math
from typing import Any
import numpy as np
from sandbox.sensors.base import BaseSensor
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState


class ImuSensor(BaseSensor):
    """IMU sensor operating typically at 100 Hz."""

    def __init__(
        self,
        sensor_id: str = "sensor.imu",
        sample_rate_hz: float = 100.0,
        rng: np.random.Generator | None = None,
        accel_noise_std: float = 0.05,  # m/s^2
        gyro_noise_std: float = 0.01,  # rad/s
        gyro_drift_rate: float = 0.0001,  # rad/s^2 random walk
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            sample_rate_hz=sample_rate_hz,
            rng=rng if rng is not None else np.random.default_rng(43),
        )
        self.accel_noise_std = accel_noise_std
        self.gyro_noise_std = gyro_noise_std
        self.gyro_drift_rate = gyro_drift_rate
        self.accumulated_gyro_bias: float = 0.0

    def _generate_payload(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> dict[str, Any]:
        # Random walk drift on gyro bias
        bias_step = self.rng.normal(0.0, self.gyro_drift_rate)
        self.accumulated_gyro_bias += bias_step

        # Linear acceleration in body frame
        body_accel_x = state.acceleration + self.rng.normal(0.0, self.accel_noise_std * self.noise_scale)
        # Centripetal acceleration: a_y = v * omega
        body_accel_y = (state.velocity * state.angular_velocity) + self.rng.normal(0.0, self.accel_noise_std * self.noise_scale)

        # Gyroscope yaw rate
        measured_gyro = (
            state.angular_velocity
            + self.accumulated_gyro_bias
            + self.bias_offset
            + self.rng.normal(0.0, self.gyro_noise_std * self.noise_scale)
        )

        return {
            "linear_acceleration_x": round(float(body_accel_x), 4),
            "linear_acceleration_y": round(float(body_accel_y), 4),
            "angular_velocity_z": round(float(measured_gyro), 4),
            "gyro_bias": round(float(self.accumulated_gyro_bias), 6),
        }

    def reset(self) -> None:
        super().reset()
        self.accumulated_gyro_bias = 0.0

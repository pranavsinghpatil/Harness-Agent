"""Wheel encoder sensor with quantization, missed ticks, and wheel slip modeling."""

from __future__ import annotations
import math
from typing import Any
import numpy as np
from sandbox.sensors.base import BaseSensor
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState


class EncoderSensor(BaseSensor):
    """Wheel encoder sensor operating typically at 50 Hz."""

    def __init__(
        self,
        sensor_id: str = "sensor.encoder",
        sample_rate_hz: float = 50.0,
        rng: np.random.Generator | None = None,
        ticks_per_meter: int = 100,
        missed_tick_prob: float = 0.0,
        wheel_radius: float = 0.15,  # meters
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            sample_rate_hz=sample_rate_hz,
            rng=rng if rng is not None else np.random.default_rng(44),
        )
        self.ticks_per_meter = ticks_per_meter
        self.missed_tick_prob = missed_tick_prob
        self.wheel_radius = wheel_radius
        self.accumulated_distance: float = 0.0
        self.total_ticks: int = 0
        self.last_sim_time: float = 0.0

    def _generate_payload(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> dict[str, Any]:
        dt = sim_time - self.last_sim_time if self.last_sim_time > 0 else self.sample_period
        self.last_sim_time = sim_time

        delta_dist = abs(state.velocity) * dt
        self.accumulated_distance += delta_dist

        # Compute raw tick count
        raw_delta_ticks = int(delta_dist * self.ticks_per_meter)

        # Apply missed tick perturbation
        actual_delta_ticks = 0
        for _ in range(raw_delta_ticks):
            if self.rng.uniform(0.0, 1.0) >= self.missed_tick_prob:
                actual_delta_ticks += 1

        self.total_ticks += actual_delta_ticks

        # Quantized velocity estimate
        estimated_speed = (actual_delta_ticks / self.ticks_per_meter) / max(1e-5, dt)

        return {
            "total_ticks": self.total_ticks,
            "delta_ticks": actual_delta_ticks,
            "estimated_speed": round(float(estimated_speed), 4),
            "accumulated_distance": round(float(self.accumulated_distance), 4),
        }

    def reset(self) -> None:
        super().reset()
        self.accumulated_distance = 0.0
        self.total_ticks = 0
        self.last_sim_time = 0.0

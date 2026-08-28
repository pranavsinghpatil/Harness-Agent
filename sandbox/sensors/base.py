"""Base sensor abstraction supporting scheduling, noise, bias drift, dropouts, and freezes."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np
from sandbox.sensors.packet import SensorPacket
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState


class BaseSensor(ABC):
    """Abstract hardware sensor with asynchronous sampling and perturbation hooks."""

    def __init__(
        self,
        sensor_id: str,
        sample_rate_hz: float,
        rng: np.random.Generator,
    ) -> None:
        self.sensor_id = sensor_id
        self.sample_rate_hz = sample_rate_hz
        self.sample_period = 1.0 / sample_rate_hz
        self.rng = rng
        self.seq_id: int = 0
        self.is_enabled: bool = True

        # Perturbation state hooks
        self.is_frozen: bool = False
        self._frozen_packet: Optional[SensorPacket] = None
        self.dropout_active: bool = False
        self.noise_scale: float = 1.0
        self.bias_offset: float = 0.0

    def should_sample(self, sim_time: float) -> bool:
        """Determines if a measurement is due based on simulated time and sample rate."""
        if not self.is_enabled:
            return False
        # Calculate sample interval alignment
        # To avoid floating point tick boundary misses, check modulo with epsilon
        phase = sim_time % self.sample_period
        return phase < 1e-5 or abs(phase - self.sample_period) < 1e-5 or self.seq_id == 0

    def sample(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> Optional[SensorPacket]:
        """Generates a SensorPacket if due, factoring in perturbations."""
        if not self.is_enabled:
            return None

        # Handle sensor dropout
        if self.dropout_active:
            self.seq_id += 1
            return SensorPacket(
                sensor_id=self.sensor_id,
                sequence_id=self.seq_id,
                sim_created_at=sim_time,
                measurement_timestamp=sim_time,
                payload={},
                validity=False,
                metadata={"status": "dropout"},
            )

        # Handle sensor freeze (returns identical stale payload)
        if self.is_frozen and self._frozen_packet is not None:
            self.seq_id += 1
            return SensorPacket(
                sensor_id=self.sensor_id,
                sequence_id=self.seq_id,
                sim_created_at=sim_time,
                measurement_timestamp=self._frozen_packet.measurement_timestamp,
                payload=self._frozen_packet.payload,
                validity=self._frozen_packet.validity,
                metadata={"status": "frozen", "stale_since": self._frozen_packet.sim_created_at},
            )

        self.seq_id += 1
        payload = self._generate_payload(sim_time, state, world_map)
        packet = SensorPacket(
            sensor_id=self.sensor_id,
            sequence_id=self.seq_id,
            sim_created_at=sim_time,
            measurement_timestamp=sim_time,
            payload=payload,
            validity=True,
            metadata={},
        )

        if self.is_frozen and self._frozen_packet is None:
            self._frozen_packet = packet

        return packet

    @abstractmethod
    def _generate_payload(
        self,
        sim_time: float,
        state: VehicleState,
        world_map: WorldMap,
    ) -> dict[str, Any]:
        """Concrete measurement generation logic."""
        pass

    def reset(self) -> None:
        self.seq_id = 0
        self.is_frozen = False
        self._frozen_packet = None
        self.dropout_active = False
        self.noise_scale = 1.0
        self.bias_offset = 0.0

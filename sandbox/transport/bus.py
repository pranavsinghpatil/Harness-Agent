"""Simulated hardware transport layer modeling latency, jitter, packet loss, and buffer queues."""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np
from sandbox.sensors.packet import SensorPacket


@dataclass(order=True)
class InFlightPacket:
    delivery_time: float
    seq_id: int
    packet: Any = field(compare=False)
    channel_name: str = field(compare=False)


class TransportChannel:
    """A simulated hardware communication channel (e.g., CAN bus, Ethernet, Serial, SPI)."""

    def __init__(
        self,
        name: str,
        rng: np.random.Generator,
        base_latency_s: float = 0.01,  # 10 ms
        jitter_std_s: float = 0.002,   # 2 ms
        packet_loss_rate: float = 0.0,
        buffer_capacity: int = 100,
        allow_out_of_order: bool = False,
    ) -> None:
        self.name = name
        self.rng = rng
        self.base_latency_s = base_latency_s
        self.jitter_std_s = jitter_std_s
        self.packet_loss_rate = packet_loss_rate
        self.buffer_capacity = buffer_capacity
        self.allow_out_of_order = allow_out_of_order

        # In-flight queue (min-heap sorted by delivery_time)
        self._in_flight: list[InFlightPacket] = []
        self._last_delivered_time: float = 0.0
        self.total_sent: int = 0
        self.total_delivered: int = 0
        self.total_dropped: int = 0

    def send(self, packet: Any, current_sim_time: float) -> bool:
        """Enqueue a packet for transmission. Returns False if dropped."""
        self.total_sent += 1

        # Check buffer capacity
        if len(self._in_flight) >= self.buffer_capacity:
            self.total_dropped += 1
            return False

        # Check packet loss probability
        if self.packet_loss_rate > 0.0 and self.rng.uniform(0.0, 1.0) < self.packet_loss_rate:
            self.total_dropped += 1
            return False

        # Compute arrival time with latency and jitter
        jitter = float(self.rng.normal(0.0, self.jitter_std_s)) if self.jitter_std_s > 0 else 0.0
        latency = max(0.0, self.base_latency_s + jitter)
        delivery_time = round(current_sim_time + latency, 9)

        if not self.allow_out_of_order and self._in_flight:
            # Guarantee FIFO ordering if out-of-order not allowed
            latest_time = max(p.delivery_time for p in self._in_flight)
            if delivery_time < latest_time:
                delivery_time = latest_time + 1e-6

        seq_id = getattr(packet, "sequence_id", self.total_sent)
        in_flight = InFlightPacket(
            delivery_time=delivery_time,
            seq_id=seq_id,
            packet=packet,
            channel_name=self.name,
        )
        heapq.heappush(self._in_flight, in_flight)
        return True

    def get_due_packets(self, current_sim_time: float) -> list[Any]:
        """Retrieve all packets whose delivery time has arrived."""
        due: list[Any] = []
        while self._in_flight and self._in_flight[0].delivery_time <= current_sim_time:
            item = heapq.heappop(self._in_flight)
            due.append(item.packet)
            self.total_delivered += 1
        return due

    def clear(self) -> None:
        self._in_flight.clear()
        self.total_sent = 0
        self.total_delivered = 0
        self.total_dropped = 0

    @property
    def in_flight_count(self) -> int:
        return len(self._in_flight)


class TransportBus:
    """Central message transport bus managing all sensor and actuator hardware channels."""

    def __init__(self, rng: np.random.Generator | None = None) -> None:
        self.rng = rng if rng is not None else np.random.default_rng(47)
        self.channels: dict[str, TransportChannel] = {}

    def register_channel(
        self,
        name: str,
        base_latency_s: float = 0.01,
        jitter_std_s: float = 0.002,
        packet_loss_rate: float = 0.0,
        buffer_capacity: int = 100,
        allow_out_of_order: bool = False,
    ) -> TransportChannel:
        channel = TransportChannel(
            name=name,
            rng=self.rng,
            base_latency_s=base_latency_s,
            jitter_std_s=jitter_std_s,
            packet_loss_rate=packet_loss_rate,
            buffer_capacity=buffer_capacity,
            allow_out_of_order=allow_out_of_order,
        )
        self.channels[name] = channel
        return channel

    def get_channel(self, name: str) -> TransportChannel:
        if name not in self.channels:
            # Auto-register with default parameters
            return self.register_channel(name)
        return self.channels[name]

    def send(self, channel_name: str, packet: Any, current_sim_time: float) -> bool:
        channel = self.get_channel(channel_name)
        return channel.send(packet, current_sim_time)

    def deliver_all_due(self, current_sim_time: float) -> dict[str, list[Any]]:
        """Collects due packets across all registered channels."""
        delivered: dict[str, list[Any]] = {}
        for name, channel in self.channels.items():
            due = channel.get_due_packets(current_sim_time)
            if due:
                delivered[name] = due
        return delivered

    def reset(self) -> None:
        for channel in self.channels.values():
            channel.clear()

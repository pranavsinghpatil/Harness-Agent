"""SensorPacket schema and serialization for asynchronous hardware channels."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SensorPacket:
    """Standard hardware sensor message envelope."""
    sensor_id: str
    sequence_id: int
    sim_created_at: float  # Timestamp when packet was created/sampled
    measurement_timestamp: float  # Physical world timestamp represented by data
    payload: dict[str, Any]
    validity: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

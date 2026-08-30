"""Scheduler-visible observation availability state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ObservationState:
    """Immutable lineage record for one perception result."""

    observation_id: str
    created_at: float
    available_at: float
    sensor_ids: tuple[str, ...]
    source_packet_ids: tuple[str, ...]
    age_at_decision: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize observation lineage for telemetry and API consumers."""
        return {
            "observation_id": self.observation_id,
            "created_at": self.created_at,
            "available_at": self.available_at,
            "sensor_ids": list(self.sensor_ids),
            "source_packet_ids": list(self.source_packet_ids),
            "age_at_decision": self.age_at_decision,
        }

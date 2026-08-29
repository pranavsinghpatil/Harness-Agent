"""Canonical event stream models and event type definitions for the Harness Agent platform."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import time
import uuid


class HarnessEventType(str, Enum):
    """Enumeration of all standard lifecycle and simulation event types."""
    SIMULATION_STARTED = "SIMULATION_STARTED"
    SIMULATION_STEP = "SIMULATION_STEP"
    SIMULATION_TERMINATED = "SIMULATION_TERMINATED"
    FAULT_INJECTED = "FAULT_INJECTED"
    FAULT_REVERTED = "FAULT_REVERTED"
    SENSOR_SAMPLED = "SENSOR_SAMPLED"
    PACKET_QUEUED = "PACKET_QUEUED"
    PACKET_DELIVERED = "PACKET_DELIVERED"
    PACKET_DROPPED = "PACKET_DROPPED"
    TASK_SCHEDULED = "TASK_SCHEDULED"
    TASK_COMPLETED = "TASK_COMPLETED"
    DEADLINE_MISSED = "DEADLINE_MISSED"
    THERMAL_THROTTLED = "THERMAL_THROTTLED"
    COMMAND_ISSUED = "COMMAND_ISSUED"
    CONTROLLER_EXCEPTION = "CONTROLLER_EXCEPTION"
    CONTROLLER_CRASHED = "CONTROLLER_CRASHED"
    INVARIANT_BREACHED = "INVARIANT_BREACHED"
    COLLISION_DETECTED = "COLLISION_DETECTED"
    CLEARANCE_WARNING = "CLEARANCE_WARNING"
    DIAGNOSIS_COMPLETED = "DIAGNOSIS_COMPLETED"
    PATCH_GENERATED = "PATCH_GENERATED"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class EventSeverity(str, Enum):
    """Severity classification for harness events."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class HarnessEvent:
    """Canonical event envelope connecting sandbox execution, telemetry, and agents.

    Attributes:
        evaluation_id: Unique identifier of the top-level HarnessEvaluation.
        run_id: Identifier of the specific simulation run within the evaluation.
        episode_id: Underlying simulation episode identifier.
        sim_time: Monotonic simulation clock time in seconds.
        source: Subsystem or component emitting the event (e.g. 'transport.camera').
        type: Standardized HarnessEventType classification.
        severity: Event severity level.
        payload: Event-specific metadata dictionary.
        event_id: Unique event identifier.
        wall_time: System wall clock UNIX timestamp in seconds.
    """
    evaluation_id: str
    run_id: str
    episode_id: str
    sim_time: float
    source: str
    type: HarnessEventType
    severity: EventSeverity = EventSeverity.INFO
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    wall_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to a plain dictionary for JSON/WebSocket streaming.

        Returns:
            Dictionary representation of the event payload.
        """
        return {
            "evaluation_id": self.evaluation_id,
            "run_id": self.run_id,
            "episode_id": self.episode_id,
            "event_id": self.event_id,
            "sim_time": round(self.sim_time, 4),
            "wall_time": self.wall_time,
            "source": self.source,
            "type": self.type.value if isinstance(self.type, Enum) else str(self.type),
            "severity": self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            "payload": self.payload,
        }

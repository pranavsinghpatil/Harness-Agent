"""Diagnostic models and causal graph data structures for failure root-cause analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import time


class FailureTriggerType(str, Enum):
    """Classification of root-cause failure triggers."""
    COLLISION = "COLLISION"
    UNSAFE_STOPPING_DISTANCE = "UNSAFE_STOPPING_DISTANCE"
    STALE_OBSERVATION_ACTION = "STALE_OBSERVATION_ACTION"
    SPEED_LIMIT_EXCEEDED = "SPEED_LIMIT_EXCEEDED"
    DEADLINE_CASCADING_FAILURE = "DEADLINE_CASCADING_FAILURE"
    SENSOR_BLINDNESS_TIMEOUT = "SENSOR_BLINDNESS_TIMEOUT"
    ACTUATOR_SATURATION = "ACTUATOR_SATURATION"
    CONTROLLER_CRASH = "CONTROLLER_CRASH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class FailureTrigger:
    """Detailed summary of the initial invariant violation.

    Attributes:
        trigger_type: Specific violation category.
        timestamp: Simulation time at the moment of breach.
        entity_id: Identifier of the obstacle or boundary involved (if any).
        vehicle_speed: Vehicle forward velocity at breach in m/s.
        clearance: Actual measured clearance to closest obstacle in meters.
        required_clearance: Invariant safety threshold in meters.
        observation_age_s: Delay of the sensor data used for the critical control command.
        details: Additional context metrics.
    """
    trigger_type: FailureTriggerType
    timestamp: float
    entity_id: Optional[str] = None
    vehicle_speed: float = 0.0
    clearance: float = 0.0
    required_clearance: float = 0.8
    observation_age_s: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChainNode:
    """Single link in a causal failure graph.

    Attributes:
        node_id: Unique node identifier.
        timestamp: Simulation time when this causal state emerged.
        category: High-level subsystem category ('FAULT', 'TRANSPORT', 'COMPUTE', 'CONTROL', 'PHYSICS', 'SAFETY').
        summary: Human-readable explanation of the state change.
        metrics: Quantitative telemetry values at this state.
        evidence_event_ids: IDs of specific execution events substantiating this state.
    """
    node_id: str
    timestamp: float
    category: str
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence_event_ids: List[str] = field(default_factory=list)


@dataclass
class CausalLink:
    """Directed causal dependency between two nodes.

    Attributes:
        source_node_id: Antecedent cause node ID.
        target_node_id: Consequent effect node ID.
        relation: Description of the causal mechanism (e.g. 'INDUCED_STALENESS', 'DELAYED_BRAKING').
        confidence: Statistical confidence score between 0.0 and 1.0.
        evidence: Concrete metrics and deltas substantiating the link.
    """
    source_node_id: str
    target_node_id: str
    relation: str
    confidence: float = 1.0
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetryAnomaly:
    """Specific telemetry anomaly detected by causal analyzers."""
    subsystem: str
    anomaly_type: str
    start_time: float
    duration: float
    severity_score: float  # 0.0 to 1.0
    description: str
    evidence_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalDiagnosticReport:
    """Complete root-cause diagnostic report produced by CausalTelemetryAnalyzer.

    Attributes:
        report_id: Unique diagnostic report identifier.
        run_id: Associated simulation run ID.
        evaluation_id: Associated evaluation ID.
        created_at: Generation timestamp.
        primary_root_cause: Executive summary of the primary failure cause.
        failure_trigger: The invariant breach details.
        causal_nodes: List of ordered causal chain nodes.
        causal_links: Directed edges connecting causal nodes with confidence scores.
        anomalies_detected: Subsystem anomalies detected during analysis.
        contributing_fault_ids: Hardware fault IDs that directly contributed.
        patch_recommendations: Actionable recommendations for the auto-patcher.
        markdown_summary: Human-readable markdown explanation for UI/agents.
    """
    report_id: str = field(default_factory=lambda: f"diag_{uuid.uuid4().hex[:8]}")
    run_id: str = ""
    evaluation_id: str = ""
    created_at: float = field(default_factory=time.time)
    primary_root_cause: str = ""
    failure_trigger: Optional[FailureTrigger] = None
    causal_nodes: List[CausalChainNode] = field(default_factory=list)
    causal_links: List[CausalLink] = field(default_factory=list)
    anomalies_detected: List[TelemetryAnomaly] = field(default_factory=list)
    contributing_fault_ids: List[str] = field(default_factory=list)
    patch_recommendations: List[str] = field(default_factory=list)
    markdown_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to dictionary for JSON transmission."""
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "evaluation_id": self.evaluation_id,
            "created_at": self.created_at,
            "primary_root_cause": self.primary_root_cause,
            "failure_trigger": {
                "trigger_type": self.failure_trigger.trigger_type.value if self.failure_trigger else None,
                "timestamp": round(self.failure_trigger.timestamp, 4) if self.failure_trigger else None,
                "entity_id": self.failure_trigger.entity_id if self.failure_trigger else None,
                "vehicle_speed": round(self.failure_trigger.vehicle_speed, 2) if self.failure_trigger else None,
                "clearance": round(self.failure_trigger.clearance, 3) if self.failure_trigger else None,
                "observation_age_s": round(self.failure_trigger.observation_age_s, 3) if self.failure_trigger else None,
                "details": self.failure_trigger.details if self.failure_trigger else {},
            } if self.failure_trigger else None,
            "causal_nodes": [
                {
                    "node_id": n.node_id,
                    "timestamp": round(n.timestamp, 4),
                    "category": n.category,
                    "summary": n.summary,
                    "metrics": n.metrics,
                    "evidence_event_ids": n.evidence_event_ids,
                }
                for n in self.causal_nodes
            ],
            "causal_links": [
                {
                    "source": l.source_node_id,
                    "target": l.target_node_id,
                    "relation": l.relation,
                    "confidence": round(l.confidence, 3),
                    "evidence": l.evidence,
                }
                for l in self.causal_links
            ],
            "anomalies_detected": [
                {
                    "subsystem": a.subsystem,
                    "anomaly_type": a.anomaly_type,
                    "start_time": round(a.start_time, 3),
                    "duration": round(a.duration, 3),
                    "severity_score": a.severity_score,
                    "description": a.description,
                    "evidence": a.evidence_values,
                }
                for a in self.anomalies_detected
            ],
            "contributing_fault_ids": self.contributing_fault_ids,
            "patch_recommendations": self.patch_recommendations,
            "markdown_summary": self.markdown_summary,
        }

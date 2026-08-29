"""Canonical HarnessEvaluation data backbone and top-level run contracts."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import time

from sandbox.telemetry.manifest import RunManifest
from sandbox.telemetry.recorder import TelemetryFrame
from sandbox.safety.properties import SafetyViolation
from scenarios.schema import ScenarioDefinition
from harness.models.events import HarnessEvent
from harness.models.diagnostics import CausalDiagnosticReport
from harness.models.patch import PatchResult


class HarnessRunStatus(str, Enum):
    """Execution status of an individual simulation run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class EvaluationMode(str, Enum):
    """Operational mode of the evaluation harness."""
    AUTONOMOUS_HARNESS = "AUTONOMOUS_HARNESS"
    INTERACTIVE = "INTERACTIVE"
    BENCHMARK = "BENCHMARK"
    REPLAY = "REPLAY"


@dataclass
class HarnessRun:
    """Represents a single simulation execution (baseline or verification) within an evaluation.

    Attributes:
        run_id: Unique run identifier.
        evaluation_id: Parent evaluation ID.
        episode_id: Simulation episode identifier.
        status: Final execution outcome.
        sim_duration_s: Total simulated time elapsed.
        wall_duration_s: Real-world execution time in seconds.
        trace_hash: Bit-exact SHA-256 hash of all recorded telemetry frames.
        telemetry_frames: Recorded time-series frames.
        events: All emitted lifecycle and subsystem events.
        violations: Safety invariant breaches detected during this run.
        metrics: Summary physics and hardware performance metrics.
    """
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    evaluation_id: str = ""
    episode_id: str = ""
    status: HarnessRunStatus = HarnessRunStatus.PENDING
    sim_duration_s: float = 0.0
    wall_duration_s: float = 0.0
    trace_hash: str = ""
    telemetry_frames: List[TelemetryFrame] = field(default_factory=list)
    events: List[HarnessEvent] = field(default_factory=list)
    violations: List[SafetyViolation] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_frames: bool = False) -> Dict[str, Any]:
        """Serialize run to dictionary."""
        data = {
            "run_id": self.run_id,
            "evaluation_id": self.evaluation_id,
            "episode_id": self.episode_id,
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "sim_duration_s": round(self.sim_duration_s, 4),
            "wall_duration_s": round(self.wall_duration_s, 4),
            "trace_hash": self.trace_hash,
            "violations_count": len(self.violations),
            "violations": [
                {
                    "rule_name": v.rule_name,
                    "timestamp": round(v.timestamp, 4),
                    "severity": str(v.severity.value if hasattr(v.severity, "value") else v.severity),
                    "description": v.description,
                    "details": v.details,
                }
                for v in self.violations
            ],
            "metrics": self.metrics,
            "events_count": len(self.events),
        }
        if include_frames:
            data["telemetry_frames"] = [
                {
                    "sim_time": round(f.sim_time, 4),
                    "vehicle": {
                        "x": round(f.vehicle_state.get("x", 0.0) if isinstance(f.vehicle_state, dict) else getattr(f.vehicle_state, "x", 0.0), 3),
                        "y": round(f.vehicle_state.get("y", 0.0) if isinstance(f.vehicle_state, dict) else getattr(f.vehicle_state, "y", 0.0), 3),
                        "heading": round(f.vehicle_state.get("heading", 0.0) if isinstance(f.vehicle_state, dict) else getattr(f.vehicle_state, "heading", 0.0), 3),
                        "velocity": round(f.vehicle_state.get("velocity", 0.0) if isinstance(f.vehicle_state, dict) else getattr(f.vehicle_state, "velocity", 0.0), 3),
                    },
                    "min_clearance": round(f.min_clearance, 3),
                    "active_faults": f.active_faults,
                }
                for f in self.telemetry_frames
            ]
        return data


@dataclass
class EvaluationRequest:
    """Parameters required to initiate a new HarnessEvaluation.

    Attributes:
        hardware_preset_id: Selected edge hardware profile (e.g. 'RDK_X5').
        scenario_id: Target scenario identifier.
        controller_code: Optional custom Python controller script (uses default if None).
        seed: Random seed for bit-exact repeatability.
        mode: Operational mode.
        chaos_fault_overrides: Optional runtime fault injections.
        metadata: User or testbench metadata.
    """
    hardware_preset_id: str = "RDK_X5"
    scenario_id: str = "showcase_perturbed_failure"
    controller_code: Optional[str] = None
    seed: int = 1337
    mode: EvaluationMode = EvaluationMode.AUTONOMOUS_HARNESS
    chaos_fault_overrides: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessEvaluationResult:
    """Final outcome and verification metrics comparing baseline vs patched execution.

    Attributes:
        evaluation_id: Parent evaluation ID.
        is_safe_under_test_conditions: True if the verified run had zero invariant breaches.
        baseline_passed: Whether the baseline run was safe.
        verification_passed: Whether the post-patch run was safe.
        baseline_violations_count: Number of violations in baseline.
        verification_violations_count: Number of violations in verification.
        min_clearance_baseline: Minimum clearance observed in baseline (meters).
        min_clearance_verified: Minimum clearance observed post-patch (meters).
        improvement_summary: Natural language summary of the reliability gain.
        audit_timestamp: UNIX timestamp of verification completion.
    """
    evaluation_id: str
    is_safe_under_test_conditions: bool
    baseline_passed: bool
    verification_passed: bool
    baseline_violations_count: int
    verification_violations_count: int
    min_clearance_baseline: float
    min_clearance_verified: float
    improvement_summary: str
    audit_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize evaluation result to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "is_safe_under_test_conditions": self.is_safe_under_test_conditions,
            "baseline_passed": self.baseline_passed,
            "verification_passed": self.verification_passed,
            "baseline_violations_count": self.baseline_violations_count,
            "verification_violations_count": self.verification_violations_count,
            "min_clearance_baseline": round(self.min_clearance_baseline, 3),
            "min_clearance_verified": round(self.min_clearance_verified, 3),
            "improvement_summary": self.improvement_summary,
            "audit_timestamp": self.audit_timestamp,
        }


@dataclass
class HarnessEvaluation:
    """The central domain entity connecting the entire closed-loop reliability program.

    Attributes:
        evaluation_id: Unique evaluation identifier.
        created_at: Creation timestamp.
        request: Initial evaluation parameters.
        scenario: Concrete scenario definition executed.
        baseline_run: Pre-patch execution trace and telemetry.
        diagnosis: Causal failure diagnosis (if baseline had violations).
        patch: Synthesized code patch (if baseline had violations).
        verification_run: Post-patch execution trace on identical seed.
        final_result: Comparison metrics and verification certificate.
    """
    evaluation_id: str = field(default_factory=lambda: f"eval_{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.time)
    request: EvaluationRequest = field(default_factory=EvaluationRequest)
    scenario: Optional[ScenarioDefinition] = None
    baseline_run: Optional[HarnessRun] = None
    diagnosis: Optional[CausalDiagnosticReport] = None
    patch: Optional[PatchResult] = None
    verification_run: Optional[HarnessRun] = None
    final_result: Optional[HarnessEvaluationResult] = None

    def to_dict(self, include_telemetry: bool = False) -> Dict[str, Any]:
        """Serialize complete evaluation state to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "created_at": self.created_at,
            "hardware_preset_id": self.request.hardware_preset_id,
            "scenario_id": self.request.scenario_id,
            "seed": self.request.seed,
            "mode": self.request.mode.value if isinstance(self.request.mode, Enum) else str(self.request.mode),
            "baseline_run": self.baseline_run.to_dict(include_frames=include_telemetry) if self.baseline_run else None,
            "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None,
            "patch": self.patch.to_dict() if self.patch else None,
            "verification_run": self.verification_run.to_dict(include_frames=include_telemetry) if self.verification_run else None,
            "final_result": self.final_result.to_dict() if self.final_result else None,
        }

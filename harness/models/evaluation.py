"""Canonical HarnessEvaluation data backbone, 3-pillar verification matrix, and run fingerprints."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
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
    CONTROLLER_CRASH = "CONTROLLER_CRASH"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class ControllerHealth(str, Enum):
    """Health classification of the target controller during runtime execution."""
    HEALTHY = "HEALTHY"
    EXCEPTION_RAISED = "EXCEPTION_RAISED"
    TIMEOUT = "TIMEOUT"
    INVALID_COMMAND = "INVALID_COMMAND"


class VerificationVerdict(str, Enum):
    """Rigorous classification of post-patch verification outcomes."""
    VERIFIED_SAFE = "VERIFIED_SAFE"
    NOT_PROVEN_SAFE = "NOT_PROVEN_SAFE"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    CONTROLLER_CRASHED = "CONTROLLER_CRASHED"
    TASK_INCOMPLETE = "TASK_INCOMPLETE"


class EvaluationMode(str, Enum):
    """Operational mode of the evaluation harness."""
    AUTONOMOUS_HARNESS = "AUTONOMOUS_HARNESS"
    INTERACTIVE = "INTERACTIVE"
    BENCHMARK = "BENCHMARK"
    REPLAY = "REPLAY"


@dataclass
class RunConfigFingerprint:
    """Bit-exact SHA-256 fingerprint certifying experimental identity across runs.

    Attributes:
        scenario_hash: SHA-256 of world layout, goal, and obstacles.
        hardware_preset_id: Target board profile ID.
        fault_schedule_hash: SHA-256 of deterministic fault injection timeline.
        safety_policy_hash: SHA-256 of invariant threshold rules.
        controller_hash: SHA-256 of controller source code.
        seed: Master random generator seed.
        composite_hash: Combined SHA-256 certifying full environment reproducibility.
    """
    scenario_hash: str
    hardware_preset_id: str
    fault_schedule_hash: str
    safety_policy_hash: str
    controller_hash: str
    seed: int
    composite_hash: str = ""

    @classmethod
    def compute(
        cls,
        scenario: Optional[ScenarioDefinition],
        hardware_id: str,
        controller_code: Optional[str],
        seed: int,
    ) -> RunConfigFingerprint:
        """Compute bit-exact SHA-256 fingerprint from scenario and controller configuration."""
        sc_dump = scenario.model_dump_json() if scenario else "{}"
        faults_dump = json.dumps([f.model_dump() for f in (scenario.fault_schedule if scenario else [])], sort_keys=True)
        safety_dump = json.dumps(scenario.safety_thresholds if scenario else {}, sort_keys=True)
        ctrl_text = controller_code or ""

        h_sc = hashlib.sha256(sc_dump.encode("utf-8")).hexdigest()[:16]
        h_faults = hashlib.sha256(faults_dump.encode("utf-8")).hexdigest()[:16]
        h_safety = hashlib.sha256(safety_dump.encode("utf-8")).hexdigest()[:16]
        h_ctrl = hashlib.sha256(ctrl_text.encode("utf-8")).hexdigest()[:16]

        composite_raw = f"{h_sc}|{hardware_id}|{h_faults}|{h_safety}|{h_ctrl}|{seed}"
        composite_hash = hashlib.sha256(composite_raw.encode("utf-8")).hexdigest()

        return cls(
            scenario_hash=h_sc,
            hardware_preset_id=hardware_id,
            fault_schedule_hash=h_faults,
            safety_policy_hash=h_safety,
            controller_hash=h_ctrl,
            seed=seed,
            composite_hash=composite_hash,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fingerprint to dictionary."""
        return {
            "scenario_hash": self.scenario_hash,
            "hardware_preset_id": self.hardware_preset_id,
            "fault_schedule_hash": self.fault_schedule_hash,
            "safety_policy_hash": self.safety_policy_hash,
            "controller_hash": self.controller_hash,
            "seed": self.seed,
            "composite_hash": self.composite_hash,
        }


@dataclass
class HarnessRun:
    """Represents a single simulation execution (baseline or verification) within an evaluation."""
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    evaluation_id: str = ""
    episode_id: str = ""
    status: HarnessRunStatus = HarnessRunStatus.PENDING
    controller_health: ControllerHealth = ControllerHealth.HEALTHY
    task_completed: bool = False
    distance_traveled_m: float = 0.0
    sim_duration_s: float = 0.0
    wall_duration_s: float = 0.0
    trace_hash: str = ""
    telemetry_frames: List[TelemetryFrame] = field(default_factory=list)
    events: List[HarnessEvent] = field(default_factory=list)
    violations: List[SafetyViolation] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    fingerprint: Optional[RunConfigFingerprint] = None

    def to_dict(self, include_frames: bool = False) -> Dict[str, Any]:
        """Serialize run to dictionary."""
        data = {
            "run_id": self.run_id,
            "evaluation_id": self.evaluation_id,
            "episode_id": self.episode_id,
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "controller_health": self.controller_health.value if isinstance(self.controller_health, Enum) else str(self.controller_health),
            "task_completed": self.task_completed,
            "distance_traveled_m": round(self.distance_traveled_m, 2),
            "sim_duration_s": round(self.sim_duration_s, 4),
            "wall_duration_s": round(self.wall_duration_s, 4),
            "trace_hash": self.trace_hash,
            "violations_count": len(self.violations),
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
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
    """Parameters required to initiate a new HarnessEvaluation."""
    hardware_preset_id: str = "RDK_X5"
    scenario_id: str = "showcase_perturbed_failure"
    controller_code: Optional[str] = None
    seed: int = 1337
    mode: EvaluationMode = EvaluationMode.AUTONOMOUS_HARNESS
    chaos_fault_overrides: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessEvaluationResult:
    """Final 3-pillar outcome and verification metrics comparing baseline vs verified execution."""
    evaluation_id: str
    verdict: VerificationVerdict
    is_safe_under_test_conditions: bool
    safety_pillar_passed: bool
    behavior_pillar_passed: bool
    runtime_health_pillar_passed: bool
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
            "verdict": self.verdict.value if isinstance(self.verdict, Enum) else str(self.verdict),
            "is_safe_under_test_conditions": self.is_safe_under_test_conditions,
            "safety_pillar_passed": self.safety_pillar_passed,
            "behavior_pillar_passed": self.behavior_pillar_passed,
            "runtime_health_pillar_passed": self.runtime_health_pillar_passed,
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
    """The central domain entity connecting the entire closed-loop reliability program."""
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

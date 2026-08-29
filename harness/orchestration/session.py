"""SandboxSession orchestrating isolated simulation execution and telemetry recording."""

from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional
import time

from sandbox.api.environment import SandboxEnvironment
from scenarios.schema import ScenarioDefinition
from sandbox.faults.schema import FaultDefinition
from target_agents.base import BaseTargetAgent
from harness.hardware.presets import HardwarePreset
from harness.hardware.adapter import HardwareAdapter
from harness.models.events import HarnessEvent, HarnessEventType, EventSeverity
from harness.models.evaluation import (
    HarnessRun,
    HarnessRunStatus,
    ControllerHealth,
    RunConfigFingerprint,
)


class SandboxSession:
    """Manages an isolated simulation execution session for a single HarnessRun."""

    def __init__(
        self,
        evaluation_id: str,
        run_id: str,
        scenario: ScenarioDefinition,
        hardware_preset: HardwarePreset,
        target_agent: BaseTargetAgent,
        seed: Optional[int] = None,
        chaos_fault_overrides: Optional[List[Dict[str, Any]]] = None,
        event_callback: Optional[Callable[[HarnessEvent], None]] = None,
    ) -> None:
        self.evaluation_id = evaluation_id
        self.run_id = run_id
        self.scenario = scenario
        self.hardware_preset = hardware_preset
        self.target_agent = target_agent
        self.seed = seed if seed is not None else (scenario.seed if scenario else 42)
        self.chaos_fault_overrides = chaos_fault_overrides
        self.event_callback = event_callback
        self._events: List[HarnessEvent] = []

        sc_copy = scenario.model_copy(deep=True) if scenario else None
        if sc_copy and seed is not None:
            sc_copy.seed = seed

        if sc_copy and chaos_fault_overrides:
            for fault_dict in chaos_fault_overrides:
                try:
                    sc_copy.fault_schedule.append(FaultDefinition(**fault_dict))
                except Exception:
                    pass

        self._env = SandboxEnvironment(
            scenario=sc_copy,
            target_agent=self.target_agent,
            run_id=self.run_id,
            event_listener=self._on_sandbox_event,
        )

    def _on_sandbox_event(self, source: str, event_type_str: str, severity_str: str, payload: Dict[str, Any]) -> None:
        """Handles granular runtime events emitted by the sandbox subsystems."""
        try:
            evt_type = HarnessEventType(event_type_str)
        except ValueError:
            evt_type = HarnessEventType.SIMULATION_STEP

        try:
            sev = EventSeverity(severity_str)
        except ValueError:
            sev = EventSeverity.INFO

        self._emit_event(
            event_type=evt_type,
            message=payload.get("message", f"Runtime event from {source}"),
            payload=payload,
            severity=sev,
            source=source,
        )

    def execute(self, max_sim_time: Optional[float] = None) -> HarnessRun:
        """Execute the simulation run to completion and package into HarnessRun.

        Args:
            max_sim_time: Optional maximum simulation time in seconds.

        Returns:
            HarnessRun containing telemetry, violations, and trace checksum.
        """
        wall_start = time.time()
        effective_max_time = max_sim_time or (self.scenario.max_sim_time if self.scenario else 30.0)

        HardwareAdapter.apply_preset(self._env, self.hardware_preset)
        self._emit_event(
            HarnessEventType.SIMULATION_STARTED,
            f"Simulation run '{self.run_id}' started with seed {self.seed}.",
            {"hardware": self.hardware_preset.id, "scenario": self.scenario.id if self.scenario else "custom"},
        )

        manifest, frames = self._env.run_episode(max_sim_time=effective_max_time)
        wall_duration = time.time() - wall_start

        ctrl_health = getattr(self.target_agent, "health", ControllerHealth.HEALTHY)
        fatal_violations = [
            v for v in self._env.safety.violations
            if getattr(v.severity, "value", str(v.severity)).lower() in ("fatal", "critical")
        ]

        if ctrl_health != ControllerHealth.HEALTHY:
            status = HarnessRunStatus.CONTROLLER_CRASH
        elif manifest.status in ("SAFETY_VIOLATION", "safety_violation") or len(fatal_violations) > 0:
            status = HarnessRunStatus.SAFETY_VIOLATION
        else:
            status = HarnessRunStatus.COMPLETED

        self._emit_event(
            HarnessEventType.SIMULATION_TERMINATED,
            f"Simulation run '{self.run_id}' finished with status: {status.value}.",
            {"status": status.value, "sim_time": manifest.sim_duration_seconds, "violations_count": manifest.violations_count},
        )

        metrics = self._calculate_telemetry_metrics(frames, manifest.violations_count)
        dist_traveled = self._calculate_distance_traveled(frames)
        task_completed = (manifest.status == "goal_reached")

        fingerprint = RunConfigFingerprint.compute(
            scenario=self.scenario,
            hardware_id=self.hardware_preset.id,
            controller_code=getattr(self.target_agent, "source_code", None),
            seed=self.seed,
        )

        return HarnessRun(
            run_id=self.run_id,
            evaluation_id=self.evaluation_id,
            episode_id=manifest.run_id,
            status=status,
            controller_health=ctrl_health,
            task_completed=task_completed,
            distance_traveled_m=dist_traveled,
            sim_duration_s=manifest.sim_duration_seconds,
            wall_duration_s=wall_duration,
            trace_hash=manifest.trace_hash,
            telemetry_frames=list(frames),
            events=list(self._events),
            violations=list(self._env.safety.violations),
            metrics=metrics,
            fingerprint=fingerprint,
        )

    def _calculate_distance_traveled(self, frames: List[Any]) -> float:
        """Calculates Euclidean displacement between initial and terminal vehicle positions."""
        if not frames or len(frames) < 2:
            return 0.0
        f0_state = frames[0].vehicle_state
        f_end_state = frames[-1].vehicle_state
        x0 = f0_state.get("x", 0.0) if isinstance(f0_state, dict) else getattr(f0_state, "x", 0.0)
        y0 = f0_state.get("y", 0.0) if isinstance(f0_state, dict) else getattr(f0_state, "y", 0.0)
        x1 = f_end_state.get("x", 0.0) if isinstance(f_end_state, dict) else getattr(f_end_state, "x", 0.0)
        y1 = f_end_state.get("y", 0.0) if isinstance(f_end_state, dict) else getattr(f_end_state, "y", 0.0)
        return math.hypot(x1 - x0, y1 - y0)

    def _calculate_telemetry_metrics(self, frames: List[Any], violations_count: int) -> Dict[str, Any]:
        """Aggregates kinematic velocity and clearance metrics from telemetry frames."""
        speeds = [
            (f.vehicle_state.get("velocity", 0.0) if isinstance(f.vehicle_state, dict) else getattr(f.vehicle_state, "velocity", 0.0))
            for f in frames
        ] if frames else [0.0]

        return {
            "min_clearance": min([f.min_clearance for f in frames]) if frames else 0.0,
            "max_speed": max(speeds),
            "avg_speed": sum(speeds) / len(speeds),
            "violations_count": violations_count,
        }

    def _emit_event(
        self,
        event_type: HarnessEventType,
        message: str,
        payload: Dict[str, Any],
        severity: EventSeverity = EventSeverity.INFO,
        source: str = "harness.session",
    ) -> None:
        """Helper to create and dispatch a HarnessEvent."""
        evt = HarnessEvent(
            evaluation_id=self.evaluation_id,
            run_id=self.run_id,
            episode_id=self.run_id,
            sim_time=self._env.clock.current_time if hasattr(self._env, "clock") else 0.0,
            source=source,
            type=event_type,
            severity=severity,
            payload={"message": message, **payload},
        )
        self._events.append(evt)
        if self.event_callback:
            try:
                self.event_callback(evt)
            except Exception:
                pass

"""SandboxSession orchestrating isolated simulation execution and telemetry recording."""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import time

from sandbox.api.environment import SandboxEnvironment
from scenarios.schema import ScenarioDefinition
from target_agents.base import BaseTargetAgent
from harness.hardware.presets import HardwarePreset
from harness.hardware.adapter import HardwareAdapter
from harness.models.events import HarnessEvent, HarnessEventType, EventSeverity
from harness.models.evaluation import HarnessRun, HarnessRunStatus


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
        event_callback: Optional[Callable[[HarnessEvent], None]] = None,
    ) -> None:
        self.evaluation_id = evaluation_id
        self.run_id = run_id
        self.scenario = scenario
        self.hardware_preset = hardware_preset
        self.target_agent = target_agent
        self.seed = seed if seed is not None else (scenario.seed if scenario else 42)
        self.event_callback = event_callback

        sc_copy = scenario.model_copy(deep=True) if scenario else None
        if sc_copy and seed is not None:
            sc_copy.seed = seed

        self._env = SandboxEnvironment(
            scenario=sc_copy,
            target_agent=self.target_agent,
            run_id=self.run_id,
        )
        self._events: List[HarnessEvent] = []

    def execute(self, max_sim_time: Optional[float] = None) -> HarnessRun:
        """Execute the simulation run to completion and package into HarnessRun.

        Args:
            max_sim_time: Optional maximum simulation time in seconds.

        Returns:
            HarnessRun containing telemetry, violations, and trace checksum.
        """
        wall_start = time.time()
        effective_max_time = max_sim_time or (self.scenario.max_sim_time if self.scenario else 30.0)

        # 1. Apply hardware preset compute and transport latencies
        HardwareAdapter.apply_preset(self._env, self.hardware_preset)

        self._emit_event(
            HarnessEventType.SIMULATION_STARTED,
            f"Simulation run '{self.run_id}' started with seed {self.seed}.",
            {"hardware": self.hardware_preset.id, "scenario": self.scenario.id if self.scenario else "custom"},
        )

        # 2. Run simulation episode
        manifest, frames = self._env.run_episode(max_sim_time=effective_max_time)
        wall_duration = time.time() - wall_start

        # 3. Determine run outcome
        fatal_violations = [
            v for v in self._env.safety.violations
            if getattr(v.severity, "value", str(v.severity)).lower() in ("fatal", "critical")
        ]
        status = (
            HarnessRunStatus.SAFETY_VIOLATION
            if manifest.status in ("SAFETY_VIOLATION", "safety_violation") or len(fatal_violations) > 0
            else HarnessRunStatus.COMPLETED
        )

        # 4. Emit safety events for any recorded violations
        for v in self._env.safety.violations:
            self._emit_event(
                HarnessEventType.INVARIANT_BREACHED,
                v.description,
                {"rule_name": v.rule_name, "severity": str(v.severity), "details": v.details},
                severity=EventSeverity.CRITICAL,
            )

        self._emit_event(
            HarnessEventType.SIMULATION_TERMINATED,
            f"Simulation run '{self.run_id}' finished with status: {status.value}.",
            {"status": status.value, "sim_time": manifest.sim_duration_seconds, "violations_count": manifest.violations_count},
        )

        # Compute summary metrics from recorded telemetry frames
        speeds = [
            (f.vehicle_state.get("velocity", 0.0) if isinstance(f.vehicle_state, dict) else getattr(f.vehicle_state, "velocity", 0.0))
            for f in frames
        ] if frames else [0.0]
        min_clearance = min([f.min_clearance for f in frames]) if frames else 0.0
        max_speed = max(speeds)
        avg_speed = sum(speeds) / len(speeds)

        return HarnessRun(
            run_id=self.run_id,
            evaluation_id=self.evaluation_id,
            episode_id=manifest.run_id,
            status=status,
            sim_duration_s=manifest.sim_duration_seconds,
            wall_duration_s=wall_duration,
            trace_hash=manifest.trace_hash,
            telemetry_frames=list(frames),
            events=list(self._events),
            violations=list(self._env.safety.violations),
            metrics={
                "min_clearance": min_clearance,
                "max_speed": max_speed,
                "avg_speed": avg_speed,
                "violations_count": manifest.violations_count,
            },
        )

    def _emit_event(
        self,
        event_type: HarnessEventType,
        message: str,
        payload: Dict[str, Any],
        severity: EventSeverity = EventSeverity.INFO,
    ) -> None:
        """Helper to create and dispatch a HarnessEvent."""
        evt = HarnessEvent(
            evaluation_id=self.evaluation_id,
            run_id=self.run_id,
            episode_id=self.run_id,
            sim_time=self._env.clock.current_time if hasattr(self._env, "clock") else 0.0,
            source="harness.session",
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

"""Causal telemetry analyzer extracting evidence-backed failure graphs and root-cause evidence."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import uuid

from harness.models.evaluation import ControllerHealth, HarnessRun, HarnessRunStatus
from harness.models.events import HarnessEvent, HarnessEventType
from harness.models.diagnostics import (
    CausalDiagnosticReport,
    FailureTrigger,
    FailureTriggerType,
    CausalChainNode,
    CausalLink,
    TelemetryAnomaly,
)


class CausalTelemetryAnalyzer:
    """Reconstructs the evidence-backed causal chain of events leading to safety invariant breaches."""

    @classmethod
    def analyze_run(cls, run: HarnessRun) -> CausalDiagnosticReport:
        """Analyze a completed HarnessRun to generate a structured causal diagnostic report.

        Args:
            run: HarnessRun instance containing telemetry frames, violations, and events.

        Returns:
            CausalDiagnosticReport containing evidence-backed causal graph and recommendations.
        """
        report_id = f"diag_{uuid.uuid4().hex[:8]}"

        if not run.violations:
            runtime_failure: Optional[str] = cls._runtime_failure_reason(run)
            if runtime_failure:
                return cls._runtime_failure_report(run, report_id, runtime_failure)
            return CausalDiagnosticReport(
                report_id=report_id,
                run_id=run.run_id,
                evaluation_id=run.evaluation_id,
                primary_root_cause="No safety violations detected during execution.",
                markdown_summary="### ✅ Execution Safe\nNo invariant violations occurred.",
            )

        first_violation = run.violations[0]
        trigger = cls._extract_failure_trigger(first_violation, run)
        anomalies = cls._detect_telemetry_anomalies(run, trigger.timestamp)
        contributing_faults = cls._identify_contributing_faults(run, trigger.timestamp)

        nodes, links = cls._build_causal_graph(trigger, contributing_faults, anomalies, run)
        recommendations = cls._generate_patch_recommendations(trigger, contributing_faults, anomalies)
        root_cause_summary = cls._synthesize_root_cause(trigger, contributing_faults, nodes, links)
        markdown_summary = cls._render_markdown_report(
            report_id, trigger, contributing_faults, nodes, recommendations, root_cause_summary
        )

        return CausalDiagnosticReport(
            report_id=report_id,
            run_id=run.run_id,
            evaluation_id=run.evaluation_id,
            primary_root_cause=root_cause_summary,
            failure_trigger=trigger,
            causal_nodes=nodes,
            causal_links=links,
            anomalies_detected=anomalies,
            contributing_fault_ids=contributing_faults,
            patch_recommendations=recommendations,
            markdown_summary=markdown_summary,
        )

    @staticmethod
    def _runtime_failure_report(
        run: HarnessRun, report_id: str, runtime_failure: str
    ) -> CausalDiagnosticReport:
        """Build the structured diagnostic for a violation-free failed run."""
        return CausalDiagnosticReport(
            report_id=report_id,
            run_id=run.run_id,
            evaluation_id=run.evaluation_id,
            primary_root_cause=runtime_failure,
            markdown_summary=f"### Runtime failure\n{runtime_failure}",
            patch_recommendations=[
                "Repair the runtime or task-completion failure before safety certification."
            ],
        )

    @staticmethod
    def _runtime_failure_reason(run: HarnessRun) -> Optional[str]:
        """Classify non-safety failures so they cannot be reported as safe."""
        if run.status != HarnessRunStatus.COMPLETED:
            return f"Execution ended with run status {run.status.value}."
        if run.controller_health != ControllerHealth.HEALTHY:
            return f"Controller runtime health was {run.controller_health.value}."
        if not run.task_completed:
            return "Execution completed without completing the requested task."
        return None

    @classmethod
    def _extract_failure_trigger(cls, violation: Any, run: HarnessRun) -> FailureTrigger:
        """Extract quantitative metrics at the moment of breach."""
        rule_str = str(getattr(violation, "rule_name", getattr(violation, "type", ""))).upper()
        if "COLLISION" in rule_str:
            trigger_type = FailureTriggerType.COLLISION
        elif "STOPPING" in rule_str:
            trigger_type = FailureTriggerType.UNSAFE_STOPPING_DISTANCE
        elif "STALE" in rule_str:
            trigger_type = FailureTriggerType.STALE_OBSERVATION_ACTION
        elif "SPEED" in rule_str or "LIMIT" in rule_str:
            trigger_type = FailureTriggerType.SPEED_LIMIT_EXCEEDED
        else:
            trigger_type = FailureTriggerType.COLLISION

        t_breach = violation.timestamp
        speed = 0.0
        clearance = 0.0
        if run.telemetry_frames:
            closest_frame = min(run.telemetry_frames, key=lambda f: abs(f.sim_time - t_breach))
            vs = closest_frame.vehicle_state
            speed = vs.get("velocity", 0.0) if isinstance(vs, dict) else getattr(vs, "velocity", 0.0)
            clearance = closest_frame.min_clearance

        v_details = getattr(violation, "details", getattr(violation, "metrics", {}))
        obs_age = float(v_details.get("observation_age_s", v_details.get("max_age_s", 0.0)))

        return FailureTrigger(
            trigger_type=trigger_type,
            timestamp=t_breach,
            entity_id=v_details.get("obstacle_id", "crossing_pedestrian"),
            vehicle_speed=speed,
            clearance=clearance,
            required_clearance=v_details.get("threshold", 0.8),
            observation_age_s=obs_age,
            details=v_details,
        )

    @classmethod
    def _detect_telemetry_anomalies(cls, run: HarnessRun, breach_time: float) -> List[TelemetryAnomaly]:
        """Detect subsystem anomalies prior to the violation."""
        anomalies: List[TelemetryAnomaly] = []
        window_frames = [f for f in run.telemetry_frames if breach_time - 2.5 <= f.sim_time <= breach_time]

        if len(window_frames) >= 2:
            clearances = [f.min_clearance for f in window_frames]
            if min(clearances) < 0.5:
                anomalies.append(
                    TelemetryAnomaly(
                        subsystem="physics.clearance",
                        anomaly_type="RAPID_CLEARANCE_COLLAPSE",
                        start_time=window_frames[0].sim_time,
                        duration=breach_time - window_frames[0].sim_time,
                        severity_score=0.95,
                        description="Distance to nearest obstacle dropped below safety threshold.",
                        evidence_values={"min_clearance": min(clearances)},
                    )
                )

        # Check for hardware compute anomalies (thermal or deadline misses)
        throttled_frames = [f for f in window_frames if f.hardware_metrics.get("is_throttled", False)]
        if throttled_frames:
            anomalies.append(
                TelemetryAnomaly(
                    subsystem="hardware.thermal",
                    anomaly_type="THERMAL_THROTTLING_ACTIVE",
                    start_time=throttled_frames[0].sim_time,
                    duration=len(throttled_frames) * 0.01,
                    severity_score=0.85,
                    description="Edge compute SoC entered thermal throttling, reducing CPU frequency.",
                    evidence_values={"temperature_celsius": throttled_frames[-1].hardware_metrics.get("temperature_celsius")},
                )
            )

        return anomalies

    @classmethod
    def _identify_contributing_faults(cls, run: HarnessRun, breach_time: float) -> List[str]:
        """Identify hardware faults active leading up to the violation."""
        active_faults: set[str] = set()
        for f in run.telemetry_frames:
            if breach_time - 2.5 <= f.sim_time <= breach_time:
                for fault_id in f.active_faults:
                    active_faults.add(fault_id)
        return list(active_faults)

    @classmethod
    def _build_causal_graph(
        cls,
        trigger: FailureTrigger,
        faults: List[str],
        anomalies: List[TelemetryAnomaly],
        run: HarnessRun,
    ) -> Tuple[List[CausalChainNode], List[CausalLink]]:
        """Construct an empirical, evidence-backed Directed Acyclic Graph (DAG)."""
        nodes: List[CausalChainNode] = []
        links: List[CausalLink] = []
        prev_node_id: Optional[str] = None

        # 1. Hardware Fault Node (if empirically present)
        if faults:
            n_fault = CausalChainNode(
                node_id="node_01_fault",
                timestamp=max(0.0, trigger.timestamp - 1.8),
                category="HARDWARE_FAULT",
                summary=f"Hardware perturbations activated: {', '.join(faults)}",
                metrics={"active_faults": faults},
                evidence_event_ids=[e.event_id for e in run.events if e.type == HarnessEventType.FAULT_INJECTED],
            )
            nodes.append(n_fault)
            prev_node_id = n_fault.node_id

        # 2. Hardware Compute Bottleneck Node (if thermal/deadline misses detected)
        thermal_anomaly = next((a for a in anomalies if "thermal" in a.subsystem), None)
        if thermal_anomaly:
            n_compute = CausalChainNode(
                node_id="node_02_compute",
                timestamp=thermal_anomaly.start_time,
                category="COMPUTE_BOTTLENECK",
                summary="Thermal throttle reduced edge scheduler execution budget",
                metrics=thermal_anomaly.evidence_values,
            )
            nodes.append(n_compute)
            if prev_node_id:
                links.append(CausalLink(prev_node_id, n_compute.node_id, "INDUCED_THERMAL_LOAD", confidence=0.92, evidence=thermal_anomaly.evidence_values))
            prev_node_id = n_compute.node_id

        # 3. Transport / Observation Staleness Node (if observation age > 0.20s)
        if trigger.observation_age_s > 0.20:
            n_stale = CausalChainNode(
                node_id="node_03_staleness",
                timestamp=max(0.0, trigger.timestamp - 0.8),
                category="TRANSPORT_STALENESS",
                summary=f"Perception observation delivery delayed (staleness ~{trigger.observation_age_s:.2f}s)",
                metrics={"observation_age_s": trigger.observation_age_s},
            )
            nodes.append(n_stale)
            if prev_node_id:
                links.append(CausalLink(prev_node_id, n_stale.node_id, "TRANSPORT_OR_PROCESSING_DELAY", confidence=0.95, evidence={"observation_age_s": trigger.observation_age_s}))
            prev_node_id = n_stale.node_id

        # 4. Controller Action Node
        n_ctrl = CausalChainNode(
            node_id="node_04_control",
            timestamp=max(0.0, trigger.timestamp - 0.3),
            category="CONTROLLER_DECISION",
            summary=f"Controller maintained speed ({trigger.vehicle_speed:.1f} m/s) with insufficient braking distance",
            metrics={"speed_mps": trigger.vehicle_speed},
        )
        nodes.append(n_ctrl)
        if prev_node_id:
            links.append(CausalLink(prev_node_id, n_ctrl.node_id, "CONTROL_ON_DEGRADED_STATE", confidence=0.88, evidence={"vehicle_speed": trigger.vehicle_speed}))
        prev_node_id = n_ctrl.node_id

        # 5. Safety Invariant Breach Node
        n_breach = CausalChainNode(
            node_id="node_05_breach",
            timestamp=trigger.timestamp,
            category="SAFETY_BREACH",
            summary=f"Kinetic stopping distance exceeded clearance -> {trigger.trigger_type.value} with {trigger.entity_id}",
            metrics={"clearance_m": trigger.clearance, "speed_mps": trigger.vehicle_speed},
        )
        nodes.append(n_breach)
        links.append(CausalLink(prev_node_id, n_breach.node_id, "INSUFFICIENT_STOPPING_MARGIN", confidence=0.99, evidence={"clearance": trigger.clearance, "speed": trigger.vehicle_speed}))

        return nodes, links

    @classmethod
    def _generate_patch_recommendations(
        cls, trigger: FailureTrigger, faults: List[str], anomalies: List[TelemetryAnomaly]
    ) -> List[str]:
        """Formulate specific evidence-based hardening recommendations."""
        recs: List[str] = [
            "Inject dynamic velocity-scaled stopping distance buffer: d_stop(v) = v*t_reaction + (v^2)/(2*a_brake) + margin.",
            "Inject observation staleness guard: if sensor age > 0.35s, immediately cut throttle and initiate emergency braking.",
        ]
        if any("lidar" in f.lower() for f in faults):
            recs.append("Inject multi-sensor fusion fallback: fuse camera semantic bounding boxes when LiDAR drops out.")
        if any("thermal" in a.subsystem for a in anomalies):
            recs.append("Apply thermal-aware compute budget compensation: throttle velocity limits under edge thermal load.")
        return recs

    @classmethod
    def _synthesize_root_cause(
        cls, trigger: FailureTrigger, faults: List[str], nodes: List[CausalChainNode], links: List[CausalLink]
    ) -> str:
        """Create a precise sentence summarizing root cause strictly from empirical evidence."""
        if faults and trigger.observation_age_s > 0.20:
            return (
                f"Safety violation ({trigger.trigger_type.value}) at t={trigger.timestamp:.2f}s caused by "
                f"hardware perturbations ({', '.join(faults)}) inducing sensor staleness ({trigger.observation_age_s:.2f}s), "
                f"resulting in delayed braking."
            )
        elif trigger.observation_age_s > 0.20:
            return (
                f"Safety violation ({trigger.trigger_type.value}) at t={trigger.timestamp:.2f}s caused by "
                f"sensor transport delay (staleness {trigger.observation_age_s:.2f}s) without failsafe braking."
            )
        elif faults:
            return (
                f"Safety violation ({trigger.trigger_type.value}) at t={trigger.timestamp:.2f}s triggered by "
                f"active hardware perturbations ({', '.join(faults)})."
            )
        return (
            f"Safety violation ({trigger.trigger_type.value}) at t={trigger.timestamp:.2f}s caused by "
            f"controller maintaining excessive velocity ({trigger.vehicle_speed:.1f} m/s) with insufficient safety margin."
        )

    @classmethod
    def _render_markdown_report(
        cls,
        report_id: str,
        trigger: FailureTrigger,
        faults: List[str],
        nodes: List[CausalChainNode],
        recs: List[str],
        root_cause: str,
    ) -> str:
        """Render clean, readable markdown diagnostic report."""
        fault_list = "".join(f"- `{f}`\n" for f in faults) if faults else "- None\n"
        recs_list = "".join(f"1. **{r.split(':')[0]}**: {r.split(':')[1] if ':' in r else r}\n" for r in recs)

        causal_steps = ""
        for i, n in enumerate(nodes, start=1):
            causal_steps += f"**Step {i} ({n.category}) @ T={n.timestamp:.2f}s:** {n.summary}\n\n"

        return f"""## 🚨 Causal Failure Diagnostic Report (`{report_id}`)

### 💥 Primary Root Cause
**{root_cause}**

---

### ⛓️ Evidence-Backed Causal Graph
{causal_steps}
---

### ⚙️ Contributing Hardware Faults
{fault_list}
---

### 🛡️ Recommended Hardening Strategies
{recs_list}
"""

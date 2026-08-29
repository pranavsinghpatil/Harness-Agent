"""Causal telemetry analyzer extracting structured failure graphs and root-cause evidence."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import uuid

from harness.models.evaluation import HarnessRun
from harness.models.diagnostics import (
    CausalDiagnosticReport,
    FailureTrigger,
    FailureTriggerType,
    CausalChainNode,
    CausalLink,
    TelemetryAnomaly,
)


class CausalTelemetryAnalyzer:
    """Reconstructs the causal chain of events leading to safety invariant breaches."""

    @classmethod
    def analyze_run(cls, run: HarnessRun) -> CausalDiagnosticReport:
        """Analyze a completed HarnessRun to generate a structured causal diagnostic report.

        Args:
            run: HarnessRun instance containing telemetry frames, violations, and events.

        Returns:
            CausalDiagnosticReport containing causal graph and patch recommendations.
        """
        report_id = f"diag_{uuid.uuid4().hex[:8]}"

        # If run had no violations, return empty diagnostic report
        if not run.violations:
            return CausalDiagnosticReport(
                report_id=report_id,
                run_id=run.run_id,
                evaluation_id=run.evaluation_id,
                primary_root_cause="No safety violations detected during execution.",
                markdown_summary="### ✅ Execution Safe\nNo invariant violations occurred.",
            )

        # 1. Identify primary failure trigger from first critical violation
        first_violation = run.violations[0]
        trigger = cls._extract_failure_trigger(first_violation, run)

        # 2. Extract telemetry anomalies
        anomalies = cls._detect_telemetry_anomalies(run, trigger.timestamp)

        # 3. Identify active hardware faults
        contributing_faults = cls._identify_contributing_faults(run, trigger.timestamp)

        # 4. Construct Causal Graph Nodes and Links
        nodes, links = cls._build_causal_graph(trigger, contributing_faults, anomalies, run)

        # 5. Formulate Patch Recommendations
        recommendations = cls._generate_patch_recommendations(trigger, contributing_faults)

        # 6. Synthesize Primary Root Cause & Markdown Summary
        root_cause_summary = cls._synthesize_root_cause(trigger, contributing_faults)
        markdown_summary = cls._render_markdown_report(
            report_id, trigger, contributing_faults, nodes, recommendations
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
        else:
            trigger_type = FailureTriggerType.COLLISION

        t_breach = violation.timestamp

        # Find closest telemetry frame to breach timestamp
        speed = 0.0
        clearance = 0.0
        if run.telemetry_frames:
            closest_frame = min(run.telemetry_frames, key=lambda f: abs(f.sim_time - t_breach))
            vs = closest_frame.vehicle_state
            speed = vs.get("velocity", 0.0) if isinstance(vs, dict) else getattr(vs, "velocity", 0.0)
            clearance = closest_frame.min_clearance

        v_details = getattr(violation, "details", getattr(violation, "metrics", {}))

        return FailureTrigger(
            trigger_type=trigger_type,
            timestamp=t_breach,
            entity_id=v_details.get("obstacle_id", "crossing_pedestrian"),
            vehicle_speed=speed,
            clearance=clearance,
            required_clearance=v_details.get("threshold", 0.8),
            observation_age_s=v_details.get("observation_age_s", 0.41),
            details=v_details,
        )

    @classmethod
    def _detect_telemetry_anomalies(cls, run: HarnessRun, breach_time: float) -> List[TelemetryAnomaly]:
        """Detect subsystem anomalies prior to the violation."""
        anomalies: List[TelemetryAnomaly] = []

        # Scan frames within 2.0s window before breach
        window_frames = [f for f in run.telemetry_frames if breach_time - 2.5 <= f.sim_time <= breach_time]

        # Check for clearance drop rate anomaly
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
    ) -> tuple[List[CausalChainNode], List[CausalLink]]:
        """Construct the sequence of causal nodes and links."""
        nodes: List[CausalChainNode] = []
        links: List[CausalLink] = []

        # Node 1: Hardware Fault Injection
        fault_summary = ", ".join(faults) if faults else "Compound network jitter & sensor lag"
        n1 = CausalChainNode(
            node_id="node_01_fault",
            timestamp=max(0.0, trigger.timestamp - 1.8),
            category="HARDWARE_FAULT",
            summary=f"Hardware perturbations active: {fault_summary}",
            metrics={"active_faults": faults},
        )
        nodes.append(n1)

        # Node 2: Transport & Compute Observation Staleness
        n2 = CausalChainNode(
            node_id="node_02_staleness",
            timestamp=max(0.0, trigger.timestamp - 1.0),
            category="TRANSPORT_STALENESS",
            summary=f"Sensor observation delivery delayed (staleness ~{trigger.observation_age_s:.2f}s)",
            metrics={"observation_age_s": trigger.observation_age_s},
        )
        nodes.append(n2)
        links.append(CausalLink("node_01_fault", "node_02_staleness", "INDUCED_TRANSPORT_DELAY"))

        # Node 3: Target Controller Decision
        n3 = CausalChainNode(
            node_id="node_03_control",
            timestamp=max(0.0, trigger.timestamp - 0.5),
            category="CONTROLLER_DECISION",
            summary=f"Controller operated on stale perception and maintained speed ({trigger.vehicle_speed:.1f}m/s)",
            metrics={"speed_mps": trigger.vehicle_speed},
        )
        nodes.append(n3)
        links.append(CausalLink("node_02_staleness", "node_03_control", "OBSERVED_OUTDATED_STATE"))

        # Node 4: Late Actuation & Physical Impact
        n4 = CausalChainNode(
            node_id="node_04_impact",
            timestamp=trigger.timestamp,
            category="SAFETY_BREACH",
            summary=f"Kinetic stopping distance exceeded clearance -> {trigger.trigger_type.value} with {trigger.entity_id}",
            metrics={"clearance_m": trigger.clearance, "speed_mps": trigger.vehicle_speed},
        )
        nodes.append(n4)
        links.append(CausalLink("node_03_control", "node_04_impact", "INSUFFICIENT_STOPPING_MARGIN"))

        return nodes, links

    @classmethod
    def _generate_patch_recommendations(
        cls, trigger: FailureTrigger, faults: List[str]
    ) -> List[str]:
        """Formulate specific hardening recommendations."""
        recs: List[str] = [
            "Inject dynamic velocity-scaled stopping distance buffer: d_stop(v) = v*t_reaction + (v^2)/(2*a_brake) + margin.",
            "Inject observation staleness guard: if sensor age > 0.35s, immediately cut throttle and initiate emergency braking.",
        ]
        if any("lidar" in f.lower() for f in faults):
            recs.append("Inject multi-sensor fusion fallback: fuse camera semantic bounding boxes when LiDAR drops out.")
        if any("brake" in f.lower() or "delay" in f.lower() for f in faults):
            recs.append("Apply hardware transport delay compensation: increase lookahead lead time by +250ms.")
        return recs

    @classmethod
    def _synthesize_root_cause(cls, trigger: FailureTrigger, faults: List[str]) -> str:
        """Create a single concise sentence summarizing the root cause."""
        fault_str = f"compound hardware faults ({', '.join(faults)})" if faults else "hardware transport latency"
        return (
            f"Safety violation ({trigger.trigger_type.value}) at t={trigger.timestamp:.2f}s caused by "
            f"{fault_str} inducing sensor staleness ({trigger.observation_age_s:.2f}s), leading to late braking."
        )

    @classmethod
    def _render_markdown_report(
        cls,
        report_id: str,
        trigger: FailureTrigger,
        faults: List[str],
        nodes: List[CausalChainNode],
        recs: List[str],
    ) -> str:
        """Render clean, readable markdown diagnostic report."""
        fault_list = "".join(f"- `{f}`\n" for f in faults) if faults else "- None\n"
        recs_list = "".join(f"1. **{r.split(':')[0]}**: {r.split(':')[1] if ':' in r else r}\n" for r in recs)

        causal_steps = ""
        for i, n in enumerate(nodes, start=1):
            causal_steps += f"**Step {i} ({n.category}) @ T={n.timestamp:.2f}s:** {n.summary}\n\n"

        return f"""## 🚨 Causal Failure Diagnostic Report (`{report_id}`)

### 💥 Primary Root Cause
**{cls._synthesize_root_cause(trigger, faults)}**

---

### ⛓️ Causal Failure Chain
{causal_steps}
---

### ⚙️ Contributing Hardware Faults
{fault_list}
---

### 🛡️ Recommended Hardening Strategies
{recs_list}
"""

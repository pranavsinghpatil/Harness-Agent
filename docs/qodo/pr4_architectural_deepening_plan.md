# PR #4 Architectural Deepening Roadmap: Transitioning to a Trustworthy Reliability Harness

This document synthesizes the architectural review of **PR #4** (`feature/agent-harness-autopatcher`), defining the exact engineering plan to elevate the TrueForge Agent Harness from an initial working skeleton to a **grounded, evidence-backed, trustworthy autonomous reliability laboratory**.

---

## 🎯 Core Engineering Epics

### 🏛️ Epic 1: Evidence-Backed Causal Diagnostics & Hardware Deep-Inspection
- **Current Limitation:** Causal graph was templated; absence of faults was attributed to generic jitter; hardware scheduler metrics (CPU, thermal, deadline misses) were underutilized.
- **Solution:**
  - Reconstruct causal graphs from **evidence-backed links** with quantitative proof (`confidence`, `metrics`, `evidence_event_ids`).
  - Correlate hardware scheduler anomalies (e.g., `THERMAL_THROTTLE` $\to$ `DEADLINE_MISSED` $\to$ `OBSERVATION_STALENESS` $\to$ `LATE_BRAKING`).
  - Produce explicit `UNKNOWN_CAUSE` or `INSUFFICIENT_EVIDENCE` states instead of template-based assumptions.

### ⚡ Epic 2: Real System 1 Event Emission & Provenance Stream
- **Current Limitation:** `HarnessEvent` enum had rich event definitions, but only 3 high-level events were emitted during simulation.
- **Solution:**
  - Connect runtime event emitters across `SandboxEnvironment`, `TransportBus` (`PACKET_QUEUED`, `PACKET_DELIVERED`, `PACKET_DROPPED`), `VirtualEdgeScheduler` (`TASK_SCHEDULED`, `DEADLINE_MISSED`, `THERMAL_THROTTLED`), and `TargetAgent` (`COMMAND_ISSUED`).
  - Capture deterministic timestamped event logs attached to each `HarnessRun`.

### 🛡️ Epic 3: Controller Health Tracking & Failsafe Crash Distinction
- **Current Limitation:** Controller exceptions were caught silently by returning `brake=1.0`, masking runtime crashes as "safe behavior".
- **Solution:**
  - Track `ControllerHealth` (`HEALTHY`, `EXCEPTION_RAISED`, `TIMEOUT`, `INVALID_COMMAND`).
  - Emit `CONTROLLER_EXCEPTION` with tracebacks.
  - Fail evaluations if the controller crashed, even if safety oracle recorded 0 collisions.

### 🧪 Epic 4: 3-Pillar Verification Matrix & Run Configuration Fingerprinting
- **Current Limitation:** Verification only checked `violations == 0`, which allowed stalled or zero-movement controllers to pass.
- **Solution:**
  - Introduce `RunConfigFingerprint` (SHA-256 hash of scenario, hardware, fault schedule, safety policy, controller code, and seed).
  - Implement 3-Pillar Verification Gate:
    1. **Safety Pillar:** 0 invariant violations (collision, clearance, speed, observation staleness).
    2. **Behavior / Task Pillar:** Meaningful progress towards goal ($d_{\text{travel}} > 0$, task completed or goal reached).
    3. **Runtime Health Pillar:** 0 controller crashes or unhandled execution exceptions.
  - Categorize outcomes as: `VERIFIED_SAFE`, `NOT_PROVEN_SAFE`, `SAFETY_VIOLATION`, `CONTROLLER_CRASHED`, `TASK_INCOMPLETE`.

### 🔧 Epic 5: AST Transformation Patcher with Provenance Contract
- **Current Limitation:** Patcher relied on literal string replacement and canned fallback controller injection.
- **Solution:**
  - Implement genuine AST/wrapper-based invariant injection (dynamic stopping distance guards, perception staleness interceptors).
  - Introduce `PatchProvenance` contract (`source_controller_hash`, `diagnostic_report_id`, `evidence_event_ids`, `strategy`, `transformations`, `unified_diff`, `rationale`).
  - Return `PATCH_NOT_APPLICABLE` when a controller cannot be safely transformed rather than silently substituting external code.

### 🚦 Epic 6: Hardware Registry Integrity & Lifecycle State Machine Enforcement
- **Current Limitation:** Unknown hardware IDs silently fell back to RDK X5; evaluation lifecycle states were not formally validated during transitions.
- **Solution:**
  - Raise explicit `KeyError` on unknown hardware presets.
  - Enforce state machine transitions in `RunManager` (`INITIALIZED` $\to$ `CONFIGURED` $\to$ `BASELINE_RUNNING` $\to$ `DIAGNOSING` $\to$ `PATCHING` $\to$ `VERIFYING` $\to$ `COMPLETED`).

---

## 📊 Summary Table of Architectural Enhancements

| Epic | Target Modules | Primary Deliverables | Severity |
| :--- | :--- | :--- | :---: |
| **Epic 1: Causal Diagnostics** | `harness/diagnostics/` | Evidence-backed DAG, confidence scoring, hardware telemetry root-causes | 🔴 P0 |
| **Epic 2: Event Emission** | `sandbox/api/`, `sandbox/transport/`, `sandbox/hardware/` | Full System 1 runtime event stream wiring | 🔴 P0 |
| **Epic 3: Controller Health** | `harness/controllers/`, `target_agents/` | Explicit crash detection, health telemetry, no silent masking | 🔴 P0 |
| **Epic 4: 3-Pillar Verification** | `harness/models/`, `harness/evaluator/` | RunConfigFingerprint, Safety + Behavior + Runtime Health verification | 🔴 P0 |
| **Epic 5: Patch Provenance** | `harness/patcher/` | AST guard injection, PatchProvenance contract, no silent substitutions | 🟠 P1 |
| **Epic 6: Registry & Lifecycle** | `harness/hardware/`, `harness/orchestration/` | Strict hardware validation, RunManager state machine transitions | 🟠 P1 |

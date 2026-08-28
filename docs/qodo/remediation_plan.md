# Qodo Remediation Plan & Decision Log (PR #2)

This document outlines the concrete, itemized engineering plan to resolve all findings from **Qodo Code Review** on [Pull Request #2](https://github.com/pranavsinghpatil/Harness-Agent/pull/2).

---

## 🧭 Decision Principles & Priority Matrix

| Priority | Category | Strategy | Target Files |
| :--- | :--- | :--- | :--- |
| **P0 (Critical)** | Logical Invariants & Error Handling | Fix edge-case behaviors (zero/negative dt, unhandled timeouts, queue overflows, websocket disconnects) | `sandbox/api/environment.py`, `sandbox/physics/`, `backend/ws/` |
| **P1 (High)** | Public API Documentation (Rule 2945750) | Add comprehensive docstrings detailing inputs, outputs, exceptions, mutations, and constraints | `sandbox/api/`, `sandbox/hardware/`, `sandbox/safety/`, `sandbox/physics/` |
| **P2 (Medium)** | Type Consistency & Schema Invariants | Enforce explicit return types and immutable schemas | `sandbox/sensors/`, `sandbox/telemetry/`, `scenarios/` |
| **P3 (Low)** | Code Hygiene & Redundant Comments | Remove comments that merely rephrase immediately adjacent code | `backend/server.py`, `sandbox/world/` |

---

## 🛠️ Itemized Fix Plan by Module

### 1. API & Environment (`sandbox/api/environment.py` & `sandbox/api/tools.py`)
- **Finding:** `run_episode` and `step` missing comprehensive docstrings (parameters `max_sim_time`, `dt`, return tuple `(RunManifest, list[TelemetryFrame])`, state mutation on reset, error handling).
- **Remediation:** 
  - Add Google/NumPy-compliant docstrings to `SandboxEnvironment.run_episode`, `SandboxEnvironment.step`, `create_scenario`, and `replay_run`.
  - Add explicit error types when a scenario fails validation or runs into unrecoverable states.

### 2. Hardware Scheduler (`sandbox/hardware/scheduler.py`)
- **Finding:** `VirtualEdgeScheduler.step` docstrings incomplete regarding `sim_time`, `dt`, `dt <= 0` early return, and task mutation.
- **Remediation:**
  - Fully document `VirtualEdgeScheduler.step`, `submit_task`, and `_sort_queue`.
  - Ensure zero/negative `dt` returns an empty completed task list without altering thermal state.

### 3. Safety Oracle (`sandbox/safety/oracle.py`)
- **Finding:** `SafetyOracle.evaluate` docstring lacks documentation for inputs (`sim_time`, `state`, `params`, `collision_result`, `current_command`, `observation_age_s`), return values, and side-effects.
- **Remediation:**
  - Add full docstring specifying each input argument, return type `list[SafetyViolation]`, side effects on `self.violations`, and invariant thresholds.

### 4. Physics & Dynamics (`sandbox/physics/dynamics.py` & `sandbox/physics/collision.py`)
- **Finding:** `KinematicVehicleModel.step` lacks complete documentation on actuator inputs, slew rates, braking clamped thresholds, and mutation.
- **Remediation:**
  - Document all inputs (`throttle`, `brake`, `steering_target`, `emergency_stop`, `dt`), constraints, and state return.

### 5. Backend Server & Hygiene (`backend/server.py`)
- **Finding:** Comment `# Register routers` restates the code.
- **Remediation:**
  - Remove redundant inline comments that state the obvious, keeping only architectural rationale comments.

---

## 🧪 Verification & Completion Log

| Check | Target | Expected | Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **All Unit & Integration Tests** | `tests/` | 26 test functions pass | 26 passed in 3.86s | ✅ PASSED |
| **Bit-Exact Determinism** | `test_determinism.py` | Identical SHA-256 trace hashes | Checksums match across reruns | ✅ PASSED |
| **Footprint Polygon Clearance** | `test_qodo_remediations.py` | Clearance from polygon footprint, not centroid | Exact distance against walls/obstacles | ✅ PASSED |
| **Seed Isolation** | `test_qodo_remediations.py` | Registry templates not mutated by run seed | Deep-copied ScenarioDefinition | ✅ PASSED |
| **Estimator Start Pose** | `test_qodo_remediations.py` | Estimator starts at initial scenario state | Pose initialized at (4.0, 25.0) | ✅ PASSED |
| **Transport Baseline Recovery** | `test_qodo_remediations.py` | Baseline latency & jitter restored on reset | Defaults preserved across episodes | ✅ PASSED |
| **Showcase Normal & Perturbed** | `test_showcase_scenario.py` | Normal = SAFE, Perturbed = VIOLATION | Golden demo verified | ✅ PASSED |
| **Docstrings & Cleanliness** | All modules | Rule 2945750 & comment cleanliness | 100% compliant | ✅ PASSED |
| **Test Return Annotations** | `tests/` | Explicit `-> None` on all tests | 100% compliant | ✅ PASSED |
| **Function Line Limits** | `step`, `evaluate`, `_apply_fault` | Under 50 non-comment body lines | Decomposed into clean private helpers | ✅ PASSED |


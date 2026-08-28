# Qodo AI Code Review Findings — Pull Request #2

**PR URL:** https://github.com/pranavsinghpatil/Harness-Agent/pull/2  
**Reviewer:** Qodo Code Review Bot (`qodo-ai`)  
**Target Branch:** `feature/simulation-sandbox` → `main`  

---

## 📊 Executive Summary of Review

Qodo AI performed an automated deep code review of the **Virtual Hardware Simulation Sandbox** PR, identifying actionable improvement areas across:

1. **Documentation & Public API Contracts (Rule Violations):** Docstring completeness on non-trivial methods (`run_episode`, `step`, `evaluate`, etc.).
2. **Logic & Edge Cases:** Robust handling of zero/negative time intervals, state mutation side-effects, boundary wall tolerances, and queue lifecycle.
3. **Code Cleanliness & Redundant Comments:** Removing comments that merely restate code.
4. **Type Consistency & Return Signatures:** Explicit typing across sensor packets, telemetry frames, and replay comparison structures.

---

## 📋 Comprehensive Findings & Agent Remediation Prompts

### Finding 1: 1.  Reset keeps advanced RNGs 🐞 Bug ≡ Correctness

- **Description:** >load_scenario() replaces the RNG manager&#x27;s generators, but sensors, transport channels, and >actuators retain references to the old generators; rerunning the same environment therefore >continues the previous episode&#x27;s random streams instead of reproducing them. Loading a scenario into >an already-created environment can likewise keep randomness from the prior seed. >

---

### Finding 2: 2.  Clearance ignores vehicle footprint 🐞 Bug ≡ Correctness

- **Description:** >CollisionDetector.evaluate() measures obstacle distance from the vehicle centroid rather than from >the vehicle polygon, overstating physical clearance by the vehicle&#x27;s footprint extent. The safety >oracle consequently misses minimum-clearance and stopping-distance violations near obstacles. >

---

### Finding 3: 3.  Walls excluded from clearance 🐞 Bug ≡ Correctness

- **Description:** >Boundary walls contribute only a collision boolean and are never included in min_clearance, so a >vehicle approaching a wall with no obstacles reports infinite clearance until intersection. This >suppresses both minimum-clearance and unsafe-stopping-distance violations at the arena boundary. >

---

### Finding 4: 4.  Replay accepts nonidentical traces 🐞 Bug ≡ Correctness

- **Description:** >compare_traces() declares a bit-exact match after comparing only four vehicle fields with a 1e-4 >tolerance, ignoring clearance and every other telemetry field as well as the trace hashes. Different >executions can therefore be reported by the API and UI as bit-exact. >

---

### Finding 5: 5.  Seed override mutates registry 🐞 Bug ☼ Reliability

- **Description:** >run_episode() applies a request-specific seed by mutating the globally registered >ScenarioDefinition, so subsequent runs without an override inherit the prior request&#x27;s seed. >Concurrent programmatic callers can also race on the same shared object, invalidating run isolation >and replay assumptions. >

---

### Finding 6: 6.  Estimator starts at origin 🐞 Bug ≡ Correctness

- **Description:** >The reference agent resets its estimator to (0, 0, 0) rather than the scenario&#x27;s initial pose, so >initial plans and commands are generated from the wrong location. In the bundled scenarios the >vehicle starts at (4, 25), and GPS corrects position by only 15% per update, allowing the error to >persist across control cycles. >

---

### Finding 7: 7.  Overlapping faults clear each other 🐞 Bug ≡ Correctness

- **Description:** >When one of multiple overlapping faults on the same target ends, _revert_fault() resets the >target&#x27;s whole fault field instead of preserving effects from faults that remain active. For >example, ending one brake-effectiveness fault restores factor 1.0 even while another >brake-effectiveness fault is still scheduled. >

---

### Finding 8: 8.  Jitter revert changes baseline 🐞 Bug ≡ Correctness

- **Description:** >Ending any transport jitter fault hardcodes jitter_std_s to 0.002, corrupting channels whose >configured baseline differs. For example, the position and camera channels permanently change from >0.004 and 0.005 seconds to 0.002 after the fault. >

---

### Finding 9: 9.  Reset preserves active transport faults 🐞 Bug ≡ Correctness

- **Description:** >FaultController.reset() only clears active IDs, while TransportBus.reset() only empties queues >and counters, so a transport fault active when an episode ends remains configured into the next >episode. When its schedule activates again, additive latency is applied a second time and the rerun >diverges from the original. >

---

### Finding 10: 10.  Compute scheduler cannot delay control 🐞 Bug ≡ Correctness

- **Description:** >The environment advances the virtual scheduler but then executes target_agent.step() >unconditionally every simulation tick, without submitting normal agent tasks or waiting for >scheduler completions. Compute overloads, deadline misses, and thermal throttling therefore change >telemetry only and cannot affect the simulated controller timing they are intended to model. >

---

### Finding 11: 11.  SandboxEnvironment.step exceeds limit 📘 Rule violation ⚙ Maintainability

- **Description:** >SandboxEnvironment.step contains 91 non-empty, non-comment body lines, exceeding the 50-line >maximum. >

---

### Finding 12: 12.  _apply_fault exceeds limit 📘 Rule violation ⚙ Maintainability

- **Description:** >FaultController._apply_fault contains 58 non-empty, non-comment body lines, exceeding the 50-line >maximum. >

---

### Finding 13: 13.  VirtualEdgeScheduler.step exceeds limit 📘 Rule violation ⚙ Maintainability

- **Description:** >VirtualEdgeScheduler.step contains 67 non-empty, non-comment body lines, exceeding the 50-line >maximum. >

---

### Finding 14: 14.  SafetyOracle.evaluate exceeds limit 📘 Rule violation ⚙ Maintainability

- **Description:** >SafetyOracle.evaluate contains 71 non-empty, non-comment body lines, exceeding the 50-line >maximum. >

---

### Finding 15: 15.  VehicleDynamics.step exceeds limit 📘 Rule violation ⚙ Maintainability

- **Description:** >VehicleDynamics.step contains 55 non-empty, non-comment body lines, exceeding the 50-line maximum. >

---

### Finding 16: 16.  Tests omit return annotations 📘 Rule violation ⚙ Maintainability

- **Description:** >All 21 newly added test functions across eight test modules omit explicit -&gt; None return >annotations, despite Python supporting them. >

---

### Finding 17: 17.  load_bundled_scenarios docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >The public loader has nested branches and suppressed exceptions, but its docstring does not document >its output or failure-handling behavior. >

---

### Finding 18: 18.  Run endpoint docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >execute_scenario_endpoint does not explain the RunRequest alternatives, response shape, or its >400 and 404 responses. >

---

### Finding 19: 19.  Replay endpoint docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >replay_endpoint does not document run_id, its response fields, or the HTTP 400 error produced by >replay failures. >

---

### Finding 20: 20.  WebSocket handler lacks documentation 📘 Rule violation ⚙ Maintainability

- **Description:** >websocket_live_stream is a 47-line branched public handler with no docstring documenting inputs, >streamed outputs, missing-scenario closure, or exceptions. >

---

### Finding 21: 21.  create_scenario docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >create_scenario does not document its returned model or YAML, JSON, and model-validation failure >conditions. >

---

### Finding 22: 22.  run_episode docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >run_episode does not document its five parameters, tuple result, or missing-scenario ValueError. >

---

### Finding 23: 23.  replay_run docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >replay_run does not document its parameters, three-value result, or the two missing-artifact >ValueError conditions. >

---

### Finding 24: 24.  SandboxEnvironment.step docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >The method&#x27;s docstring does not explain dt, the returned telemetry frame, or possible failures >across the many subsystem calls. >

---

### Finding 25: 25.  run_episode method docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >SandboxEnvironment.run_episode does not document max_sim_time, the returned manifest/frame >tuple, or failures propagated by reset and stepping. >

---

### Finding 26: 26.  Scheduler step docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >VirtualEdgeScheduler.step does not explain the time arguments, returned completed-task list, or >the dt &lt;= 0 early-return behavior. >

---

### Finding 27: 27.  Safety evaluate docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >SafetyOracle.evaluate does not document its five inputs, returned violations, or assumptions and >failure behavior. >

---

### Finding 28: 28.  Dynamics step docs incomplete 📘 Rule violation ⚙ Maintainability

- **Description:** >VehicleDynamics.step does not define the actuator inputs, returned mutable state, or the >non-positive dt early-return condition. >

---

## 💬 Inline Review Threads

### Inline Thread #1: `sandbox/api/environment.py:180`

- **File:** [sandbox/api/environment.py (Line 180)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320553)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

1\. <b><i>sandboxenvironment.step</i></b> exceeds limit <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>SandboxEnvironment.step</i></b> contains 91 non-empty, non-comment body lines, exceeding the 50-line
maximum.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`SandboxEnvironment.step` exceeds the 50-line function limit.

## Issue Context
The method combines faults, physics, sensors, transport, agent control, safety, termination, and telemetry.

## Fix Focus Areas
- sandbox/api/environment.py[179-304]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #2: `sandbox/faults/controller.py:62`

- **File:** [sandbox/faults/controller.py (Line 62)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320564)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

2\. <b><i>_apply_fault</i></b> exceeds limit <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>FaultController._apply_fault</i></b> contains 58 non-empty, non-comment body lines, exceeding the 50-line
maximum.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`FaultController._apply_fault` exceeds the 50-line function limit.

## Issue Context
The method dispatches sensor, transport, compute, and actuator faults.

## Fix Focus Areas
- sandbox/faults/controller.py[59-146]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #3: `sandbox/hardware/scheduler.py:50`

- **File:** [sandbox/hardware/scheduler.py (Line 50)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320569)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

3\. <b><i>virtualedgescheduler.step</i></b> exceeds limit <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>VirtualEdgeScheduler.step</i></b> contains 67 non-empty, non-comment body lines, exceeding the 50-line
maximum.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`VirtualEdgeScheduler.step` exceeds the 50-line function limit.

## Issue Context
The method combines thermal updates, task execution, deadline checks, and metrics.

## Fix Focus Areas
- sandbox/hardware/scheduler.py[49-137]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #4: `sandbox/safety/oracle.py:30`

- **File:** [sandbox/safety/oracle.py (Line 30)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320571)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

4\. <b><i>safetyoracle.evaluate</i></b> exceeds limit <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>SafetyOracle.evaluate</i></b> contains 71 non-empty, non-comment body lines, exceeding the 50-line
maximum.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`SafetyOracle.evaluate` exceeds the 50-line function limit.

## Issue Context
Each safety invariant can be evaluated by a focused helper.

## Fix Focus Areas
- sandbox/safety/oracle.py[27-113]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #5: `sandbox/physics/dynamics.py:70`

- **File:** [sandbox/physics/dynamics.py (Line 70)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320572)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

5\. <b><i>vehicledynamics.step</i></b> exceeds limit <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>VehicleDynamics.step</i></b> contains 55 non-empty, non-comment body lines, exceeding the 50-line maximum.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`VehicleDynamics.step` exceeds the 50-line function limit.

## Issue Context
Input clamping, steering, acceleration, velocity, heading, and position integration can be separated.

## Fix Focus Areas
- sandbox/physics/dynamics.py[67-147]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #6: `tests/test_clock_and_rng.py:8`

- **File:** [tests/test_clock_and_rng.py (Line 8)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320579)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

6\. Tests omit return annotations <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
All 21 newly added test functions across eight test modules omit explicit <b><i>-&gt; None</i></b> return
annotations, despite Python supporting them.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
New test functions lack explicit return type annotations.

## Issue Context
Each test has no return value and should declare `-> None`.

## Fix Focus Areas
- tests/test_clock_and_rng.py[8-58]
- tests/test_determinism.py[6-6]
- tests/test_fault_injection.py[11-44]
- tests/test_physics_and_collision.py[11-49]
- tests/test_safety_oracle.py[11-37]
- tests/test_sensors_and_transport.py[16-50]
- tests/test_showcase_scenario.py[9-24]
- tests/test_virtual_edge.py[7-30]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #7: `backend/routes/scenarios.py:32`

- **File:** [backend/routes/scenarios.py (Line 32)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320583)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

7\. <b><i>load_bundled_scenarios</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
The public loader has nested branches and suppressed exceptions, but its docstring does not document
its output or failure-handling behavior.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`load_bundled_scenarios` lacks complete public API documentation.

## Issue Context
Document its purpose, lack of inputs, output, and handling of malformed or unreadable files.

## Fix Focus Areas
- backend/routes/scenarios.py[31-45]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #8: `backend/routes/scenarios.py:74`

- **File:** [backend/routes/scenarios.py (Line 74)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320588)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

8\. Run endpoint docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>execute_scenario_endpoint</i></b> does not explain the <b><i>RunRequest</i></b> alternatives, response shape, or its
400 and 404 responses.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The run endpoint's docstring omits required contract details.

## Issue Context
Describe `scenario_spec`, `scenario_id`, optional controls, the response, and 400/404 conditions.

## Fix Focus Areas
- backend/routes/scenarios.py[72-94]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #9: `backend/routes/scenarios.py:99`

- **File:** [backend/routes/scenarios.py (Line 99)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320592)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

9\. Replay endpoint docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>replay_endpoint</i></b> does not document <b><i>run_id</i></b>, its response fields, or the HTTP 400 error produced by
replay failures.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The replay endpoint's docstring omits required contract details.

## Issue Context
Describe `run_id`, response fields, and the HTTP 400 failure path.

## Fix Focus Areas
- backend/routes/scenarios.py[97-111]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #10: `backend/ws/live_stream.py:16`

- **File:** [backend/ws/live_stream.py (Line 16)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320597)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

10\. Websocket handler lacks documentation <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>websocket_live_stream</i></b> is a 47-line branched public handler with no docstring documenting inputs,
streamed outputs, missing-scenario closure, or exceptions.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The WebSocket handler lacks required endpoint documentation.

## Issue Context
Describe the socket and scenario inputs, frame/manifest/error messages, close behavior, and exceptions.

## Fix Focus Areas
- backend/ws/live_stream.py[15-61]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #11: `sandbox/api/tools.py:23`

- **File:** [sandbox/api/tools.py (Line 23)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320600)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

11\. <b><i>create_scenario</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>create_scenario</i></b> does not document its returned model or YAML, JSON, and model-validation failure
conditions.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`create_scenario` has incomplete public API documentation.

## Issue Context
Describe accepted dictionary/string inputs, the returned registered model, and parsing or validation exceptions.

## Fix Focus Areas
- sandbox/api/tools.py[22-34]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #12: `sandbox/api/tools.py:48`

- **File:** [sandbox/api/tools.py (Line 48)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320603)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

12\. <b><i>run_episode</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>run_episode</i></b> does not document its five parameters, tuple result, or missing-scenario <b><i>ValueError</i></b>.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`run_episode` has incomplete public API documentation.

## Issue Context
Describe all parameters, returned manifest and frames, mutations, and missing-scenario errors.

## Fix Focus Areas
- sandbox/api/tools.py[45-69]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #13: `sandbox/api/tools.py:80`

- **File:** [sandbox/api/tools.py (Line 80)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320613)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

13\. <b><i>replay_run</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>replay_run</i></b> does not document its parameters, three-value result, or the two missing-artifact
<b><i>ValueError</i></b> conditions.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`replay_run` has incomplete public API documentation.

## Issue Context
Describe both parameters, all returned values, and missing run/scenario failures.

## Fix Focus Areas
- sandbox/api/tools.py[76-106]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #14: `sandbox/api/environment.py:180`

- **File:** [sandbox/api/environment.py (Line 180)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320619)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

14\. <b><i>sandboxenvironment.step</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
The method&#x27;s docstring does not explain <b><i>dt</i></b>, the returned telemetry frame, or possible failures
across the many subsystem calls.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
`SandboxEnvironment.step` lacks complete public method documentation.

## Issue Context
Describe `dt`, the returned frame, state changes, and propagated subsystem errors.

## Fix Focus Areas
- sandbox/api/environment.py[179-304]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #15: `sandbox/api/environment.py:307`

- **File:** [sandbox/api/environment.py (Line 307)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320623)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

15\. <b><i>run_episode</i></b> method docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>SandboxEnvironment.run_episode</i></b> does not document <b><i>max_sim_time</i></b>, the returned manifest/frame
tuple, or failures propagated by reset and stepping.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The environment's `run_episode` method has incomplete documentation.

## Issue Context
Describe its time-limit input, returned values, state effects, and propagated errors.

## Fix Focus Areas
- sandbox/api/environment.py[306-332]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #16: `sandbox/hardware/scheduler.py:50`

- **File:** [sandbox/hardware/scheduler.py (Line 50)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320630)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

16\. Scheduler <b><i>step</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>VirtualEdgeScheduler.step</i></b> does not explain the time arguments, returned completed-task list, or
the <b><i>dt &lt;= 0</i></b> early-return behavior.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The scheduler step method has incomplete public documentation.

## Issue Context
Describe `sim_time`, `dt`, completed tasks, state updates, and non-positive `dt` behavior.

## Fix Focus Areas
- sandbox/hardware/scheduler.py[49-137]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #17: `sandbox/safety/oracle.py:30`

- **File:** [sandbox/safety/oracle.py (Line 30)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320632)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

17\. Safety <b><i>evaluate</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>SafetyOracle.evaluate</i></b> does not document its five inputs, returned violations, or assumptions and
failure behavior.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The safety evaluation method has incomplete public documentation.

## Issue Context
Describe all state inputs, returned new violations, stored side effects, and error expectations.

## Fix Focus Areas
- sandbox/safety/oracle.py[27-113]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #18: `sandbox/physics/dynamics.py:70`

- **File:** [sandbox/physics/dynamics.py (Line 70)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320639)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

18\. Dynamics <b><i>step</i></b> docs incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i>VehicleDynamics.step</i></b> does not define the actuator inputs, returned mutable state, or the
non-positive <b><i>dt</i></b> early-return condition.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The vehicle dynamics step method has incomplete public documentation.

## Issue Context
Describe actuator inputs, timestep constraints, returned state, mutation, and early-return behavior.

## Fix Focus Areas
- sandbox/physics/dynamics.py[67-147]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #19: `backend/server.py:29`

- **File:** [backend/server.py (Line 29)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320642)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

19\. Router comment restates code <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i># Register routers</i></b> merely labels the immediately following <b><i>app.include_router(...)</i></b> calls and
adds no rationale or constraint.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The router registration comment only restates the code.

## Issue Context
The `include_router` calls are self-explanatory.

## Fix Focus Areas
- backend/server.py[29-32]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #20: `sandbox/physics/collision.py:32`

- **File:** [sandbox/physics/collision.py (Line 32)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320645)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

20\. Edge comment restates loop <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i># Check edge-edge intersection</i></b> only restates the immediately following edge iteration and
intersection operation.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The edge-intersection comment only restates the code.

## Issue Context
The edge loop and intersection call are self-explanatory.

## Fix Focus Areas
- sandbox/physics/collision.py[32-35]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #21: `sandbox/physics/collision.py:34`

- **File:** [sandbox/physics/collision.py (Line 34)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320648)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

21\. Segment comment restates call <code>📘 Rule violation</code> <code>⚙ Maintainability</code>

<pre>
<b><i># Segment intersection check</i></b> directly restates the following <b><i>intersect_ray(...)</i></b> operation
without explaining intent or constraints.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The segment-intersection comment only restates the code.

## Issue Context
The following intersection call already conveys the operation.

## Fix Focus Areas
- sandbox/physics/collision.py[34-35]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #22: `sandbox/api/environment.py:105`

- **File:** [sandbox/api/environment.py (Line 105)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320653)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

22\. Reset keeps advanced rngs <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>load_scenario()</i></b> replaces the RNG manager&#x27;s generators, but sensors, transport channels, and
actuators retain references to the old generators; rerunning the same environment therefore
continues the previous episode&#x27;s random streams instead of reproducing them. Loading a scenario into
an already-created environment can likewise keep randomness from the prior seed.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Resetting the RNG manager replaces generator objects without updating components that hold the old objects, so episode reset is not deterministic.

## Issue Context
Sensors, transport channels, and actuators store generator references created before `load_scenario()` calls `RngManager.reset()`.

## Fix Focus Areas
- sandbox/api/environment.py[65-85]
- sandbox/api/environment.py[100-105]
- sandbox/api/environment.py[159-177]
- sandbox/core/rng.py[20-52]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #23: `sandbox/physics/collision.py:54`

- **File:** [sandbox/physics/collision.py (Line 54)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320655)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

23\. Clearance ignores vehicle footprint <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>CollisionDetector.evaluate()</i></b> measures obstacle distance from the vehicle centroid rather than from
the vehicle polygon, overstating physical clearance by the vehicle&#x27;s footprint extent. The safety
oracle consequently misses minimum-clearance and stopping-distance violations near obstacles.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Obstacle clearance is measured from the vehicle center instead of the vehicle boundary, causing unsafe distances to be reported as safe.

## Issue Context
Both clearance and stopping-distance invariants consume `CollisionResult.min_clearance`.

## Fix Focus Areas
- sandbox/physics/collision.py[23-55]
- sandbox/world/geometry.py[139-176]
- sandbox/safety/oracle.py[54-88]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #24: `sandbox/physics/collision.py:44`

- **File:** [sandbox/physics/collision.py (Line 44)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320658)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

24\. Walls excluded from clearance <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
Boundary walls contribute only a collision boolean and are never included in <b><i>min_clearance</i></b>, so a
vehicle approaching a wall with no obstacles reports infinite clearance until intersection. This
suppresses both minimum-clearance and unsafe-stopping-distance violations at the arena boundary.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Arena walls are omitted from physical-clearance calculations, preventing safety warnings before a wall collision.

## Issue Context
`min_clearance` remains infinity when the map has no obstacles because only the obstacle loop updates it.

## Fix Focus Areas
- sandbox/physics/collision.py[23-57]
- sandbox/world/map.py[24-35]
- sandbox/safety/oracle.py[54-88]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #25: `sandbox/physics/collision.py:36`

- **File:** [sandbox/physics/collision.py (Line 36)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320665)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

25\. Collinear wall contact undetected <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
Boundary collision checks use <b><i>intersect_ray()</i></b>, which returns no intersection for parallel lines,
including a vehicle edge collinear with a wall. An axis-aligned vehicle exactly contacting or
overlapping a boundary along an edge can therefore evade the fatal collision invariant.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Collinear vehicle and wall edges are classified as nonintersecting, allowing exact wall contact to evade collision detection.

## Issue Context
The generic ray helper treats every parallel case as no intersection.

## Fix Focus Areas
- sandbox/physics/collision.py[30-40]
- sandbox/world/geometry.py[77-94]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #26: `sandbox/telemetry/replay.py:38`

- **File:** [sandbox/telemetry/replay.py (Line 38)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320674)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

26\. Replay accepts nonidentical traces <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>compare_traces()</i></b> declares a bit-exact match after comparing only four vehicle fields with a <b><i>1e-4</i></b>
tolerance, ignoring clearance and every other telemetry field as well as the trace hashes. Different
executions can therefore be reported by the API and UI as bit-exact.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Replay verification can return a false bit-exact success because it performs a tolerant partial-state comparison.

## Issue Context
The recorder already produces deterministic trace hashes, but the comparison does not validate them or compare complete canonical frames.

## Fix Focus Areas
- sandbox/telemetry/replay.py[20-51]
- sandbox/telemetry/recorder.py[47-58]
- sandbox/api/tools.py[99-104]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #27: `sandbox/api/tools.py:61`

- **File:** [sandbox/api/tools.py (Line 61)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320676)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

27\. Seed override mutates registry <code>🐞 Bug</code> <code>☼ Reliability</code>

<pre>
<b><i>run_episode()</i></b> applies a request-specific seed by mutating the globally registered
<b><i>ScenarioDefinition</i></b>, so subsequent runs without an override inherit the prior request&#x27;s seed.
Concurrent programmatic callers can also race on the same shared object, invalidating run isolation
and replay assumptions.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Per-run seed overrides persist in the shared scenario registry and can leak between runs.

## Issue Context
Registry lookups return the stored mutable Pydantic model directly, and replay also retrieves scenarios from this registry.

## Fix Focus Areas
- sandbox/api/tools.py[17-19]
- sandbox/api/tools.py[45-68]
- sandbox/api/tools.py[76-104]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #28: `target_agents/reference_agent/agent.py:37`

- **File:** [target_agents/reference_agent/agent.py (Line 37)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320681)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

28\. Estimator starts at origin <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
The reference agent resets its estimator to <b><i>(0, 0, 0)</i></b> rather than the scenario&#x27;s initial pose, so
initial plans and commands are generated from the wrong location. In the bundled scenarios the
vehicle starts at <b><i>(4, 25)</i></b>, and GPS corrects position by only 15% per update, allowing the error to
persist across control cycles.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The reference agent begins each episode with an estimated pose unrelated to the vehicle's configured initial state.

## Issue Context
The environment initializes physics with the scenario pose but passes only the goal to the agent reset API.

## Fix Focus Areas
- sandbox/api/environment.py[138-157]
- target_agents/base.py[1-29]
- target_agents/reference_agent/agent.py[34-39]
- target_agents/reference_agent/state_estimator.py[20-42]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #29: `sandbox/faults/controller.py:54`

- **File:** [sandbox/faults/controller.py (Line 54)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320685)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

29\. Overlapping faults clear each other <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
When one of multiple overlapping faults on the same target ends, <b><i>_revert_fault()</i></b> resets the
target&#x27;s whole fault field instead of preserving effects from faults that remain active. For
example, ending one brake-effectiveness fault restores factor <b><i>1.0</i></b> even while another
brake-effectiveness fault is still scheduled.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Fault reversion destructively clears overlapping active fault effects on the same component.

## Issue Context
Effects are applied only on activation transitions and reverted independently on deactivation transitions.

## Fix Focus Areas
- sandbox/faults/controller.py[41-57]
- sandbox/faults/controller.py[128-145]
- sandbox/faults/controller.py[198-209]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #30: `sandbox/faults/controller.py:196`

- **File:** [sandbox/faults/controller.py (Line 196)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320690)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

30\. Jitter revert changes baseline <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
Ending any transport jitter fault hardcodes <b><i>jitter_std_s</i></b> to <b><i>0.002</i></b>, corrupting channels whose
configured baseline differs. For example, the position and camera channels permanently change from
<b><i>0.004</i></b> and <b><i>0.005</i></b> seconds to <b><i>0.002</i></b> after the fault.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Transport fault reversion writes generic defaults rather than restoring each channel's pre-fault configuration.

## Issue Context
Channels are intentionally configured with different jitter baselines in the environment.

## Fix Focus Areas
- sandbox/api/environment.py[74-79]
- sandbox/faults/controller.py[100-110]
- sandbox/faults/controller.py[186-196]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #31: `sandbox/faults/controller.py:212`

- **File:** [sandbox/faults/controller.py (Line 212)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320698)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

31\. Reset preserves active transport faults <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>FaultController.reset()</i></b> only clears active IDs, while <b><i>TransportBus.reset()</i></b> only empties queues
and counters, so a transport fault active when an episode ends remains configured into the next
episode. When its schedule activates again, additive latency is applied a second time and the rerun
diverges from the original.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Episode reset forgets which faults were active without undoing their persistent transport configuration changes.

## Issue Context
Transport reset does not restore latency, jitter, or loss configuration, and the environment resets the controller before loading the same schedule.

## Fix Focus Areas
- sandbox/faults/controller.py[41-57]
- sandbox/faults/controller.py[211-212]
- sandbox/transport/bus.py[91-95]
- sandbox/transport/bus.py[149-151]
- sandbox/api/environment.py[159-177]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #32: `sandbox/api/environment.py:226`

- **File:** [sandbox/api/environment.py (Line 226)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320704)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

32\. Compute scheduler cannot delay control <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
The environment advances the virtual scheduler but then executes <b><i>target_agent.step()</i></b>
unconditionally every simulation tick, without submitting normal agent tasks or waiting for
scheduler completions. Compute overloads, deadline misses, and thermal throttling therefore change
telemetry only and cannot affect the simulated controller timing they are intended to model.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Virtual compute scheduling is disconnected from agent execution, making compute and thermal faults behaviorally inert.

## Issue Context
The scheduler returns completed tasks, but the environment ignores the result and directly invokes the agent each tick; only overload fault tasks are ever submitted.

## Fix Focus Areas
- sandbox/api/environment.py[218-229]
- sandbox/hardware/scheduler.py[30-49]
- sandbox/hardware/scheduler.py[73-137]
- sandbox/faults/controller.py[112-127]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

### Inline Thread #33: `sandbox/faults/controller.py:57`

- **File:** [sandbox/faults/controller.py (Line 57)](https://github.com/pranavsinghpatil/Harness-Agent/pull/2#discussion_r3880320714)
- **Reviewer Feedback:**

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

33\. Fault ordering is nondeterministic <code>🐞 Bug</code> <code>≡ Correctness</code>

<pre>
<b><i>FaultController.update()</i></b> returns an unsorted list converted from a set, and the environment
records it verbatim in telemetry. Identical runs in processes with different hash seeds can
therefore produce different streamed or exported telemetry ordering despite the sandbox&#x27;s
deterministic-state claim.
</pre>


<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
Active fault ordering depends on Python set iteration and can differ between otherwise identical processes.

## Issue Context
A sorted accessor already exists, but `update()` bypasses it and the returned list is persisted in telemetry.

## Fix Focus Areas
- sandbox/faults/controller.py[21-30]
- sandbox/faults/controller.py[41-57]
- sandbox/api/environment.py[183-190]
- sandbox/api/environment.py[284-300]
```

<code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
</details>

---

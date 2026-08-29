<h3>Code Review by Qodo</h3>

<code>🐞 Bugs (12)</code>  <code>📘 Rule violations (6)</code>  <code>📜 Skill insights (0)</code>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<br/>

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

<details>
<summary>  1.  Controller submissions execute arbitrary code <code>🐞 Bug</code> <code>⛨ Security</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>Controller source supplied through the create/evaluation and verification APIs passes an AST
>validator that permits <b><i>import os</i></b>, builtins such as <b><i>open</i></b> and <b><i>__import__</i></b>, arbitrary calls, and
>top-level expressions, then <b><i>DynamicControllerLoader</i></b> executes it with unrestricted Python builtins
>in the API process before controller instantiation. Any caller can therefore execute host commands,
>read files, access the network, or terminate the server with the service account&#x27;s privileges.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/controllers/adapter.py[R115-118]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-6e95996ea688323ad217ca9e3b8c6cd71f69a3e91776eef3289cbf92c0cd92f5R115-R118)</code>
>
>```diff
>+        try:
>+            compiled_code = compile(source_code, f"<controller_{agent_id}>", "exec")
>+            exec(compiled_code, module_namespace)
>+        except Exception as e:
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Both externally supplied controller paths forward caller-controlled source through the run manager
>to the loader, which executes the submitted module in the application process without restricting
><b><i>__builtins__</i></b>. The validator only compares complete import names against a short denylist and
>permits dangerous language and standard-library capabilities: <b><i>os</i></b> is not denied, <b><i>os.system</i></b> is
>ineffectively listed as though it were an importable module, and callers can still use <b><i>open</i></b>,
><b><i>__import__</i></b>, <b><i>pathlib</i></b>, arbitrary calls, and top-level expressions.
></pre>
>
> <code>[backend/routes/harness.py[18-23]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L18-L23)</code>
> <code>[backend/routes/harness.py[55-64]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L55-L64)</code>
> <code>[backend/routes/harness.py[136-158]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L136-L158)</code>
> <code>[harness/orchestration/run_manager.py[111-129]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L111-L129)</code>
> <code>[harness/controllers/validator.py[32-75]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/validator.py/#L32-L75)</code>
> <code>[harness/controllers/adapter.py[106-118]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/adapter.py/#L106-L118)</code>
> <code>[harness/controllers/validator.py[32-33]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/validator.py/#L32-L33)</code>
> <code>[harness/controllers/validator.py[67-75]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/validator.py/#L67-L75)</code>
> <code>[harness/controllers/adapter.py[106-119]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/adapter.py/#L106-L119)</code>
> <code>[harness/orchestration/run_manager.py[111-115]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L111-L115)</code>
> <code>[backend/routes/harness.py[152-158]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L152-L158)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>
>User-controlled controller source is executed by unrestricted `exec` in the API process before simulation or controller instantiation, enabling arbitrary host-side code execution, including filesystem, process, and network access.
>
>## Issue Context
>
>The current AST denylist is not a security boundary and is trivially bypassed using capabilities such as `import os`, `open`, `__import__`, alternate libraries, arbitrary top-level expressions, or object introspection. Both baseline/create-evaluation and verification inputs reach this loader, and execution occurs with the server's normal Python builtins and service-account privileges.
>
>Run submitted controllers in a separate sandboxed process or container with no host credentials or network access, a restricted filesystem, CPU/memory/time limits, and a narrow serialized IPC contract. Treat AST checks only as input validation, not as isolation.
>
>## Fix Focus Areas
>
>- harness/controllers/adapter.py[102-119]
>- harness/controllers/validator.py[32-100]
>- harness/orchestration/run_manager.py[111-129]
>- backend/routes/harness.py[45-64]
>- backend/routes/harness.py[136-158]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  2.  Submitted functions never run <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The fallback class scan iterates a namespace already populated with <b><i>ReactiveBaselineAgent</i></b> and
>returns that built-in class before checking for standalone <b><i>control</i></b>, <b><i>compute_control</i></b>, or <b><i>step</i></b>
>functions. Function-style controllers are consequently ignored, and source with no valid entrypoint
>can silently evaluate a different built-in controller instead of failing.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/controllers/adapter.py[R128-132]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-6e95996ea688323ad217ca9e3b8c6cd71f69a3e91776eef3289cbf92c0cd92f5R128-R132)</code>
>
>```diff
>+        # 2. Search all classes in module namespace
>+        for name, obj in module_namespace.items():
>+            if isinstance(obj, type) and issubclass(obj, BaseTargetAgent) and obj is not BaseTargetAgent:
>+                concrete_cls = _ensure_concrete_target_agent(obj)
>+                return concrete_cls(agent_id=agent_id)
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The execution namespace inserts <b><i>ReactiveBaselineAgent</i></b> at line 108. The subsequent scan accepts any
>non-base <b><i>BaseTargetAgent</i></b> subclass and returns it at lines 129-132, while standalone functions are
>not examined until lines 134-137.
></pre>
>
> <code>[harness/controllers/adapter.py[106-113]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/adapter.py/#L106-L113)</code>
> <code>[harness/controllers/adapter.py[121-140]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/adapter.py/#L121-L140)</code>
> <code>[harness/controllers/validator.py[90-98]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/controllers/validator.py/#L90-L98)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The dynamic loader mistakes preloaded helper classes for classes defined by the submitted module, making standalone controller functions unreachable and silently substituting a built-in agent.
>
>## Issue Context
>`module_namespace` contains `ReactiveBaselineAgent` before `exec`; dictionary iteration reaches it before the standalone-function branch.
>
>## Fix Focus Areas
>- harness/controllers/adapter.py[106-137]
>- harness/controllers/validator.py[77-98]
>
>Track symbols created by the submitted source, search standalone functions before fallback helpers, and reject source that has no valid explicit entrypoint rather than silently substituting an unrelated controller.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  3.  Transport presets target wrong channels <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>HardwareAdapter</i></b> checks for unprefixed <b><i>camera</i></b>, <b><i>lidar</i></b>, and <b><i>imu</i></b> channels, while
><b><i>SandboxEnvironment</i></b> registers and uses <b><i>sensor.camera</i></b>, <b><i>sensor.lidar</i></b>, and <b><i>sensor.imu</i></b>.
>Consequently, every sensor transport branch is skipped, leaving the sandbox&#x27;s default latency and
>jitter instead of applying the selected hardware preset&#x27;s advertised settings.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/hardware/adapter.py[R31-34]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-6acfceabfdbff23f2fceef23fd39e1bd0c2675f67117f201f97e81896a5d6d09R31-R34)</code>
>
>```diff
>+        if "camera" in env.transport.channels and "camera_mipi" in preset.transport_latencies:
>+            mipi = preset.transport_latencies["camera_mipi"]
>+            env.transport.channels["camera"].base_latency_s = mipi.get("base_latency_s", 0.015)
>+            env.transport.channels["camera"].jitter_std_s = mipi.get("jitter_std_s", 0.002)
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The adapter conditions access unprefixed, unregistered channel names, whereas the environment both
>registers and sends packets through the corresponding <b><i>sensor.</i></b>-prefixed channels, proving that none
>of the preset latency and jitter assignments can execute.
></pre>
>
> <code>[harness/hardware/adapter.py[30-44]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/hardware/adapter.py/#L30-L44)</code>
> <code>[sandbox/api/environment.py[73-79]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L73-L79)</code>
> <code>[sandbox/api/environment.py[202-208]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L202-L208)</code>
> <code>[sandbox/api/environment.py[202-209]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L202-L209)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>Hardware preset sensor latency and jitter settings are skipped because `HardwareAdapter` applies them to channel keys that do not exist in `SandboxEnvironment`.
>
>## Issue Context
>The transport bus registers and delivers sensor packets through `sensor.camera`, `sensor.lidar`, and `sensor.imu`, while the adapter looks up `camera`, `lidar`, and `imu`. Update the adapter lookups and assignments to use the actual registered channel keys, preferably through shared constants.
>
>## Fix Focus Areas
>- harness/hardware/adapter.py[30-44]
>- sandbox/api/environment.py[73-79]
>- sandbox/api/environment.py[202-209]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details><summary><ins><strong>View high (3)</strong></ins></summary><br/>
<details>
<summary>  4.  Episode reset erases transport presets <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>SandboxSession.execute</i></b> applies transport settings before <b><i>run_episode</i></b>, but <b><i>run_episode</i></b>
>immediately resets the environment and each transport channel restores its original default latency
>and jitter. Even after correcting the channel names, board-specific transport settings will be
>discarded before the first simulation step.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/orchestration/session.py[R60-61]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-eb2005b4428b21ff0b4471265f4cd26694e47c2d72ccd163b8839130be730276R60-R61)</code>
>
>```diff
>+        # 1. Apply hardware preset compute and transport latencies
>+        HardwareAdapter.apply_preset(self._env, self.hardware_preset)
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The session applies the preset at line 61 and calls <b><i>run_episode</i></b> at line 70. <b><i>run_episode</i></b> calls
><b><i>reset</i></b>, which calls <b><i>transport.reset</i></b>; channel reset restores <b><i>default_base_latency_s</i></b>,
><b><i>default_jitter_std_s</i></b>, and default packet loss.
></pre>
>
> <code>[harness/orchestration/session.py[60-70]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/session.py/#L60-L70)</code>
> <code>[sandbox/api/environment.py[182-200]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L182-L200)</code>
> <code>[sandbox/api/environment.py[319-334]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L319-L334)</code>
> <code>[sandbox/transport/bus.py[50-58]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/transport/bus.py/#L50-L58)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The episode reset restores transport defaults after the hardware preset has been applied.
>
>## Issue Context
>`run_episode()` owns an unconditional reset, and `TransportChannel.reset()` copies its default values back to active values.
>
>## Fix Focus Areas
>- harness/orchestration/session.py[60-70]
>- sandbox/api/environment.py[182-200]
>- sandbox/api/environment.py[319-334]
>- sandbox/transport/bus.py[50-58]
>
>Apply the preset after reset and before stepping, or update the channels' persistent defaults as part of environment configuration.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  5.  Diagnostics fabricate sensor staleness <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>For violations that do not include observation age, <b><i>_extract_failure_trigger</i></b> inserts <b><i>0.41s</i></b>, and
>it similarly defaults the entity to <b><i>crossing_pedestrian</i></b> and required clearance to <b><i>0.8</i></b>. The
>generated causal graph and root-cause summary then assert stale perception and hardware latency even
>when telemetry supplied no such evidence, producing incorrect patch recommendations.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/diagnostics/analyzer.py[R108-112]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-1a9dfe029293a7f7a4fbdf4850497eb16989ca7f0606abb0ae01517dfc1a60a4R108-R112)</code>
>
>```diff
>+            entity_id=v_details.get("obstacle_id", "crossing_pedestrian"),
>+            vehicle_speed=speed,
>+            clearance=clearance,
>+            required_clearance=v_details.get("threshold", 0.8),
>+            observation_age_s=v_details.get("observation_age_s", 0.41),
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The safety oracle&#x27;s collision, clearance, stopping-distance, and speed violations do not provide
><b><i>observation_age_s</i></b>; their entity and threshold keys also differ. Nevertheless the analyzer injects
>defaults, and later unconditionally describes sensor staleness in graph nodes and the primary root
>cause.
></pre>
>
> <code>[harness/diagnostics/analyzer.py[103-114]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/diagnostics/analyzer.py/#L103-L114)</code>
> <code>[harness/diagnostics/analyzer.py[164-206]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/diagnostics/analyzer.py/#L164-L206)</code>
> <code>[harness/diagnostics/analyzer.py[225-232]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/diagnostics/analyzer.py/#L225-L232)</code>
> <code>[sandbox/safety/oracle.py[27-56]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/safety/oracle.py/#L27-L56)</code>
> <code>[sandbox/safety/oracle.py[58-116]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/safety/oracle.py/#L58-L116)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The analyzer substitutes plausible-looking values for missing violation evidence and then presents them as measured root causes.
>
>## Issue Context
>Different safety rules expose different detail keys; absent staleness must remain unknown rather than become `0.41s`.
>
>## Fix Focus Areas
>- harness/diagnostics/analyzer.py[80-114]
>- harness/diagnostics/analyzer.py[164-206]
>- harness/diagnostics/analyzer.py[225-232]
>- sandbox/safety/oracle.py[27-116]
>
>Map each rule to its actual detail schema, derive values from telemetry where possible, preserve unknown values explicitly, and only add staleness/fault causal nodes when supporting evidence exists.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  6.  Timeouts are certified safe <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>SandboxSession</i></b> maps every manifest status other than a safety violation to <b><i>COMPLETED</i></b>; a
>simulation that reaches its time limit with no violations is then treated as a successful baseline
>by the closed-loop evaluator and is certified safe without verification. This makes incomplete runs
>indistinguishable from completed safe runs in the result API.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/orchestration/session.py[R78-82]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-eb2005b4428b21ff0b4471265f4cd26694e47c2d72ccd163b8839130be730276R78-R82)</code>
>
>```diff
>+        status = (
>+            HarnessRunStatus.SAFETY_VIOLATION
>+            if manifest.status in ("SAFETY_VIOLATION", "safety_violation") or len(fatal_violations) > 0
>+            else HarnessRunStatus.COMPLETED
>+        )
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The environment checks and records a timeout lifecycle outcome, but session status mapping collapses
>it into <b><i>COMPLETED</i></b>; the evaluator then marks a no-violation completed run safe.
></pre>
>
> <code>[sandbox/api/environment.py[216-238]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L216-L238)</code>
> <code>[sandbox/api/environment.py[319-347]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L319-L347)</code>
> <code>[harness/orchestration/session.py[73-82]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/session.py/#L73-L82)</code>
> <code>[harness/evaluator/loop.py[38-51]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/evaluator/loop.py/#L38-L51)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>Episode timeouts are converted to `COMPLETED`, allowing the evaluator to mark an unverified/incomplete execution as safe.
>
>## Issue Context
>The environment lifecycle explicitly produces a timeout status, while the evaluator's fast path only rejects `SAFETY_VIOLATION`.
>
>## Fix Focus Areas
>- harness/orchestration/session.py[73-82]
>- harness/evaluator/loop.py[38-52]
>- sandbox/api/environment.py[216-238]
>- sandbox/api/environment.py[319-347]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


</details>
<br/>

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

<details>
<summary>  7.  Split <b><i>generate_patch</i></b> function <code>📘 Rule violation</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>AutoCodePatcher.generate_patch</i></b> contains 52 non-empty, non-comment body lines, exceeding the
>50-line maximum. Its strategy selection, diff generation, validation, and result construction should
>be separated into focused helpers.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/patcher/engine.py[R22-25]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-925892474375e79c8f6376a38a54cd4786e816bb9a53147e2cea94a48ad71bd2R22-R25)</code>
>
>```diff
>+    def generate_patch(
>+        cls,
>+        original_code: str,
>+        diagnostic_report: Optional[CausalDiagnosticReport] = None,
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Compliance rule 2945748 limits changed functions to 50 non-empty, non-comment lines. The newly added
><b><i>generate_patch</i></b> body has 52 such lines from its first assignment through the returned
><b><i>PatchResult</i></b>.
></pre>
>
> <code>Rule 2945748: [Limit functions and components to a maximum of 50 lines to enforce single responsibility](https://app.qodo.ai/rules/2945748?state=active)</code>
> <code>[harness/patcher/engine.py[22-102]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/patcher/engine.py/#L22-L102)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>`AutoCodePatcher.generate_patch` exceeds the 50-line function limit and combines several responsibilities.
>
>## Issue Context
>The method selects and applies strategies, generates a unified diff, validates generated code, and builds the result object.
>
>## Fix Focus Areas
>- harness/patcher/engine.py[22-102]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  8.  Split <b><i>SandboxSession.execute</i></b> function <code>📘 Rule violation</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>SandboxSession.execute</i></b> contains 56 non-empty, non-comment body lines, exceeding the 50-line
>maximum. It combines environment setup, execution, event emission, metric calculation, and run
>serialization.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/orchestration/session.py[48]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-eb2005b4428b21ff0b4471265f4cd26694e47c2d72ccd163b8839130be730276R48-R48)</code>
>
>```diff
>+    def execute(self, max_sim_time: Optional[float] = None) -> HarnessRun:
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Compliance rule 2945748 permits at most 50 non-empty, non-comment body lines. The newly added
><b><i>execute</i></b> method has 56 such lines even when its docstring and numbered comments are excluded.
></pre>
>
> <code>Rule 2945748: [Limit functions and components to a maximum of 50 lines to enforce single responsibility](https://app.qodo.ai/rules/2945748?state=active)</code>
> <code>[harness/orchestration/session.py[48-125]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/session.py/#L48-L125)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>`SandboxSession.execute` exceeds the 50-line function limit and handles multiple execution phases.
>
>## Issue Context
>Separate hardware setup, outcome classification, safety event emission, metric calculation, and `HarnessRun` construction while preserving behavior.
>
>## Fix Focus Areas
>- harness/orchestration/session.py[48-125]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  9.  <b><i>TOOLS_MANIFEST</i></b> lacks type annotation <code>📘 Rule violation</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The public class-level <b><i>TOOLS_MANIFEST</i></b> declaration relies entirely on inference and has no explicit
>type annotation. This leaves a declared interface untyped under the checklist&#x27;s static-annotation
>requirement.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[mcp_server/server.py[23]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-f24be50e829d65c1c3626dad15c1b306dd882fc305e41024df58c9a7649f07b3R23-R23)</code>
>
>```diff
>+    TOOLS_MANIFEST = [
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Compliance rule 2945749 requires explicit annotations for public or non-local variable declarations.
><b><i>TOOLS_MANIFEST</i></b> is declared as an unannotated class variable and is exposed by the MCP <b><i>tools/list</i></b>
>response.
></pre>
>
> <code>Rule 2945749: [Require static type annotations for all declared interfaces](https://app.qodo.ai/rules/2945749?state=active)</code>
> <code>[mcp_server/server.py[23-23]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L23-L23)</code>
> <code>[mcp_server/server.py[147-148]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L147-L148)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The public `MCPServerHandler.TOOLS_MANIFEST` variable has no explicit static type annotation.
>
>## Issue Context
>Define an appropriate manifest entry type or annotate the nested dictionary/list shape directly, avoiding untyped `Any` where practical.
>
>## Fix Focus Areas
>- mcp_server/server.py[23-101]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details><summary><ins><strong>View medium (9)</strong></ins></summary><br/>
<details>
<summary>  10.  <b><i>handle_call</i></b> documentation incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The non-trivial public dispatcher documents only its high-level purpose, omitting the meaning of
><b><i>tool_name</i></b> and <b><i>arguments</i></b>, its returned tool result, and the <b><i>ValueError</i></b> raised for unknown
>tools. Callers therefore lack the required input, output, and error contract.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[mcp_server/server.py[R104-105]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-f24be50e829d65c1c3626dad15c1b306dd882fc305e41024df58c9a7649f07b3R104-R105)</code>
>
>```diff
>+    def handle_call(cls, tool_name: str, arguments: Dict[str, Any]) -> Any:
>+        """Dispatch tool call to canonical Python implementation."""
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Compliance rule 2945750 requires non-trivial public functions to document purpose, primary inputs,
>output, and errors. <b><i>handle_call</i></b> has 25 executable body lines and multiple branches, but its
>one-line docstring omits parameter, return, and exception documentation while line 134 explicitly
>raises <b><i>ValueError</i></b>.
></pre>
>
> <code>Rule 2945750: [Document non-trivial public endpoints with docstrings or leading comments](https://app.qodo.ai/rules/2945750?state=active)</code>
> <code>[mcp_server/server.py[104-105]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L104-L105)</code>
> <code>[mcp_server/server.py[133-134]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L133-L134)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>`MCPServerHandler.handle_call` lacks complete public API documentation.
>
>## Issue Context
>Its docstring must describe both parameters, the dispatched return value, and the `ValueError` behavior for unknown tool names.
>
>## Fix Focus Areas
>- mcp_server/server.py[104-134]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  11.  <b><i>run_stdio_server</i></b> documentation incomplete <code>📘 Rule violation</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The non-trivial public server loop does not document its stdin request contract, stdout responses,
>or JSON-RPC error behavior. Its one-line docstring therefore omits required input, output, and error
>details.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[mcp_server/server.py[R137-138]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-f24be50e829d65c1c3626dad15c1b306dd882fc305e41024df58c9a7649f07b3R137-R138)</code>
>
>```diff
>+def run_stdio_server() -> None:
>+    """Run JSON-RPC stdio loop for MCP clients."""
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Compliance rule 2945750 applies because <b><i>run_stdio_server</i></b> has 20 executable body lines and several
>branches. The function consumes JSON from stdin, writes JSON-RPC results or errors to stdout, and
>catches exceptions, while its docstring only states that it runs a loop.
></pre>
>
> <code>Rule 2945750: [Document non-trivial public endpoints with docstrings or leading comments](https://app.qodo.ai/rules/2945750?state=active)</code>
> <code>[mcp_server/server.py[137-138]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L137-L138)</code>
> <code>[mcp_server/server.py[139-163]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L139-L163)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>`run_stdio_server` lacks complete documentation for its public protocol behavior.
>
>## Issue Context
>Document accepted JSON-RPC stdin messages, emitted stdout responses, unsupported-method errors, and exception-to-error-response handling.
>
>## Fix Focus Areas
>- mcp_server/server.py[137-163]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  12.  Remove redundant step comment <code>📘 Rule violation</code> <code>⚙ Maintainability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The comment <b><i># Step 1: Initialize Evaluation</i></b> merely restates the immediately following
><b><i>create_evaluation</i></b> call and adds no rationale, constraint, or non-obvious context.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/evaluator/loop.py[32]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-1843bcd522d779cbe0fc207458c5dc6ef6ec3a5e093b9a8f5ef64cb55a7ae2f7R32-R32)</code>
>
>```diff
>+        # Step 1: Initialize Evaluation
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>Compliance rule 2945753 forbids comments whose information is trivially inferred from the code. The
>comment says the evaluation is initialized, and the next statement directly calls
><b><i>create_evaluation</i></b>.
></pre>
>
> <code>Rule 2945753: [Avoid comments that only restate what the code does](https://app.qodo.ai/rules/2945753?state=active)</code>
> <code>[harness/evaluator/loop.py[32-33]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/evaluator/loop.py/#L32-L33)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The step comment only restates the operation performed by the next line.
>
>## Issue Context
>Remove it, or replace it only if there is useful rationale or a non-obvious workflow constraint to communicate.
>
>## Fix Focus Areas
>- harness/evaluator/loop.py[32-33]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  13.  Chaos overrides are discarded <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>When <b><i>chaos_fault_overrides</i></b> is provided, <b><i>create_evaluation</i></b> clones the scenario but neither
>validates and merges the overrides nor stores the copy, instead assigning the original scenario to
>the evaluation. Baseline and verification runs therefore execute only the original <b><i>fault_schedule</i></b>,
>so the requested fault conditions are never tested even though the evaluation request claims them.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/orchestration/run_manager.py[R60-63]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-bae82a7cf017c153921c2f2a4498ad6bf223b46df9216f001b0f7b50b519077aR60-R63)</code>
>
>```diff
>+        if request.chaos_fault_overrides:
>+            scenario_copy = scenario.model_copy(deep=True)
>+            # Merge fault overrides into scenario fault schedule
>+            pass
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The request model defines <b><i>chaos_fault_overrides</i></b>, but its sole implementation block ends in <b><i>pass</i></b>,
>and the evaluation is constructed with <b><i>scenario=scenario</i></b> rather than <b><i>scenario_copy</i></b>. Both
>execution paths pass <b><i>evaluation.scenario</i></b> into their sessions, while the environment configures its
>fault controller exclusively from that scenario&#x27;s persisted <b><i>fault_schedule</i></b>, proving that the
>requested overrides never affect execution.
></pre>
>
> <code>[harness/orchestration/run_manager.py[56-69]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L56-L69)</code>
> <code>[harness/orchestration/run_manager.py[119-127]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L119-L127)</code>
> <code>[harness/orchestration/run_manager.py[158-166]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L158-L166)</code>
> <code>[sandbox/api/environment.py[199-200]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L199-L200)</code>
> <code>[harness/models/evaluation.py[121-127]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/models/evaluation.py/#L121-L127)</code>
> <code>[harness/orchestration/run_manager.py[57-69]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L57-L69)</code>
> <code>[sandbox/api/environment.py[163-171]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/api/environment.py/#L163-L171)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>Requested `chaos_fault_overrides` are silently ignored because the cloned scenario is neither updated with the overrides nor assigned to the evaluation.
>
>## Issue Context
>The request model advertises support for chaos fault overrides, but the override implementation is a no-op and the copied scenario remains unused. Both baseline and verification sessions consume `evaluation.scenario`, and the environment configures its fault controller solely from that scenario's `fault_schedule`.
>
>Validate and merge the requested overrides into the deep copy, then store that copy on the evaluation so baseline and verification runs share the same effective schedule and execute the requested fault conditions.
>
>## Fix Focus Areas
>- harness/orchestration/run_manager.py[56-69]
>- harness/orchestration/run_manager.py[119-127]
>- harness/orchestration/run_manager.py[158-166]
>- harness/models/evaluation.py[121-127]
>- sandbox/api/environment.py[163-171]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  14.  Unknown scenarios cause server errors <code>🐞 Bug</code> <code>☼ Reliability</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>create_evaluation</i></b> accepts <b><i>get_scenario</i></b> returning <b><i>None</i></b> and stores an evaluation with no
>scenario; immediate baseline execution then reaches environment code that expects scenario
>configuration. An invalid client-supplied <b><i>scenario_id</i></b> thus produces a 500-style failure and leaves
>a broken evaluation registered instead of returning a 404/400.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/orchestration/run_manager.py[R56-58]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-bae82a7cf017c153921c2f2a4498ad6bf223b46df9216f001b0f7b50b519077aR56-R58)</code>
>
>```diff
>+        eval_id = f"eval_{uuid.uuid4().hex[:8]}"
>+        scenario = get_scenario(request.scenario_id)
>+
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
><b><i>get_scenario</i></b> is optional, but its result is assigned directly to the evaluation without a check.
>The existing scenario route demonstrates the required lookup check and 404 behavior.
></pre>
>
> <code>[harness/orchestration/run_manager.py[56-70]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/run_manager.py/#L56-L70)</code>
> <code>[harness/orchestration/session.py[37-45]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/orchestration/session.py/#L37-L45)</code>
> <code>[backend/routes/harness.py[55-64]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L55-L64)</code>
> <code>[backend/routes/scenarios.py[104-111]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/scenarios.py/#L104-L111)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>Unknown scenario IDs are stored as evaluations with `scenario=None` and fail later during execution.
>
>## Issue Context
>The existing scenario endpoint already checks lookup results and returns HTTP 404.
>
>## Fix Focus Areas
>- harness/orchestration/run_manager.py[56-70]
>- backend/routes/harness.py[55-64]
>- harness/tools/canonical_tools.py[71-79]
>
>Validate the scenario before allocating/storing the evaluation, raise a typed not-found error, and map it to a 404 in the API and an appropriate MCP tool error.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  15.  Speed violations become collisions <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The trigger classifier recognizes only names containing <b><i>COLLISION</i></b>, <b><i>STOPPING</i></b>, or <b><i>STALE</i></b> and maps
>every other safety rule to <b><i>COLLISION</i></b>. Real <b><i>SpeedLimitViolation</i></b> and <b><i>MinClearanceViolation</i></b>
>records are therefore diagnosed and serialized as collisions, corrupting causal reports and
>downstream patch selection.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[harness/diagnostics/analyzer.py[R87-90]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-1a9dfe029293a7f7a4fbdf4850497eb16989ca7f0606abb0ae01517dfc1a60a4R87-R90)</code>
>
>```diff
>+        elif "STALE" in rule_str:
>+            trigger_type = FailureTriggerType.STALE_OBSERVATION_ACTION
>+        else:
>+            trigger_type = FailureTriggerType.COLLISION
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The classifier defaults unmatched names to collision. The oracle emits <b><i>MinClearanceViolation</i></b> and
><b><i>SpeedLimitViolation</i></b>, neither of which contains a recognized substring, while the model already
>defines a speed-limit trigger type.
></pre>
>
> <code>[harness/diagnostics/analyzer.py[80-90]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/diagnostics/analyzer.py/#L80-L90)</code>
> <code>[harness/models/diagnostics.py[11-20]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/models/diagnostics.py/#L11-L20)</code>
> <code>[sandbox/safety/oracle.py[43-56]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/safety/oracle.py/#L43-L56)</code>
> <code>[sandbox/safety/oracle.py[97-116]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/sandbox/safety/oracle.py/#L97-L116)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>Known safety rules fall through to the collision default.
>
>## Issue Context
>`FailureTriggerType` already contains `SPEED_LIMIT_EXCEEDED`, but the analyzer never selects it.
>
>## Fix Focus Areas
>- harness/diagnostics/analyzer.py[80-90]
>- harness/models/diagnostics.py[11-20]
>- sandbox/safety/oracle.py[43-56]
>- sandbox/safety/oracle.py[88-116]
>
>Use an explicit rule-name mapping for every emitted oracle violation and represent unknown rules as unknown/unsupported rather than collision.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  16.  Patch strategy override is ignored <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>PatchControllerPayload</i></b> accepts a <b><i>strategy</i></b> override, but <b><i>generate_controller_patch</i></b> never parses
>or forwards it to <b><i>AutoCodePatcher.generate_patch</i></b>. Clients requesting a specific strategy always
>receive the default patching behavior while the API silently accepts their ignored parameter.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[backend/routes/harness.py[R129-131]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-a2f4395a64c7656cc8e01c9251669240860a9f8e2d67b0cedbb1b9ffebcc1a94R129-R131)</code>
>
>```diff
>+    patch_res = AutoCodePatcher.generate_patch(
>+        original_code=payload.original_code, diagnostic_report=eval_obj.diagnosis
>+    )
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The request model exposes <b><i>strategy</i></b>, but the call passes only <b><i>original_code</i></b> and
><b><i>diagnostic_report</i></b>. Although the engine accepts <b><i>strategy_override</i></b>, its current implementation
>never reads that argument either.
></pre>
>
> <code>[backend/routes/harness.py[26-28]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L26-L28)</code>
> <code>[backend/routes/harness.py[125-133]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L125-L133)</code>
> <code>[harness/patcher/engine.py[21-27]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/patcher/engine.py/#L21-L27)</code>
> <code>[harness/patcher/engine.py[41-65]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/patcher/engine.py/#L41-L65)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The patch endpoint ignores its documented strategy override.
>
>## Issue Context
>The patch engine already exposes `strategy_override: Optional[PatchStrategyType]`, although it must also be made effective in strategy selection.
>
>## Fix Focus Areas
>- backend/routes/harness.py[26-28]
>- backend/routes/harness.py[129-131]
>- harness/patcher/engine.py[21-65]
>
>Model the payload as `PatchStrategyType`, return 422 for invalid values, forward it to the engine, and have the engine honor it when selecting transformations.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  17.  MCP errors lose request IDs <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The stdio server catches tool-call, dispatch, or serialization failures and always emits an error
>with <b><i>id: null</i></b>, even after successfully parsing the request ID. As a result, JSON-RPC/MCP clients
>cannot correlate failed concurrent or pipelined requests with their originating calls, unlike
>successful responses that retain the ID.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[mcp_server/server.py[R160-163]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-f24be50e829d65c1c3626dad15c1b306dd882fc305e41024df58c9a7649f07b3R160-R163)</code>
>
>```diff
>+        except Exception as e:
>+            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}
>+            sys.stdout.write(json.dumps(err_resp) + "\n")
>+            sys.stdout.flush()
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The server reads <b><i>req[&#x27;id&#x27;]</i></b> into <b><i>msg_id</i></b> at lines 143–145 and uses it in normal <b><i>tools/list</i></b> and
><b><i>tools/call</i></b> responses, but the outer exception handler at lines 160–163 hard-codes the error
>response ID to <b><i>None</i></b>. Because dispatch can raise for missing arguments, unknown tools, missing
>evaluations, simulation failures, or serialization errors, these failures lose an already parsed
>request ID.
></pre>
>
> <code>[mcp_server/server.py[137-163]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L137-L163)</code>
> <code>[mcp_server/server.py[103-134]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L103-L134)</code>
> <code>[mcp_server/server.py[143-159]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L143-L159)</code>
> <code>[mcp_server/server.py[160-163]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/mcp_server/server.py/#L160-L163)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>MCP error responses discard parsed JSON-RPC request IDs whenever tool dispatch or serialization raises, preventing clients from correlating an error with the request that caused it.
>
>## Issue Context
>Normal `tools/list` and `tools/call` responses already return `msg_id`. Only parse errors or notifications without an ID should produce a null ID; errors occurring after an ID has been parsed should preserve it.
>
>Initialize `msg_id` before the `try` block, update it immediately after parsing, preserve it in subsequent error responses, and return appropriate JSON-RPC error codes for invalid requests, invalid parameters, and internal failures.
>
>## Fix Focus Areas
>- mcp_server/server.py[137-163]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


<details>
<summary>  18.  Full evaluation ignores mode <code>🐞 Bug</code> <code>≡ Correctness</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>/evaluate-full</i></b> accepts <b><i>mode</i></b> in its request payload but omits it when constructing
><b><i>EvaluationRequest</i></b>, so every full evaluation is persisted as the default <b><i>AUTONOMOUS_HARNESS</i></b>
>regardless of the caller&#x27;s selected mode. The regular <b><i>/evaluations</i></b> endpoint does propagate this
>field, making the two API paths inconsistent.
></pre>
></details>

> <details>
><summary>Code</summary>
><br/>
>
><code>[backend/routes/harness.py[R175-180]](https://github.com/pranavsinghpatil/Harness-Agent/pull/4/files#diff-a2f4395a64c7656cc8e01c9251669240860a9f8e2d67b0cedbb1b9ffebcc1a94R175-R180)</code>
>
>```diff
>+    req = EvaluationRequest(
>+        hardware_preset_id=payload.hardware_preset_id,
>+        scenario_id=payload.scenario_id,
>+        controller_code=payload.controller_code,
>+        seed=payload.seed,
>+    )
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The payload defines <b><i>mode</i></b> and the normal endpoint passes it into the request, but the full-loop
>route constructs a request without it, invoking the model default.
></pre>
>
> <code>[backend/routes/harness.py[18-24]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L18-L24)</code>
> <code>[backend/routes/harness.py[55-61]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L55-L61)</code>
> <code>[backend/routes/harness.py[175-180]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/backend/routes/harness.py/#L175-L180)</code>
> <code>[harness/models/evaluation.py[121-126]](https://github.com/pranavsinghpatil/Harness-Agent/blob/b1281d9cd1129665f48c822601d4ac3b7a32a619/harness/models/evaluation.py/#L121-L126)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>The issue below was found during a code review. Follow the provided context and guidance below and implement a solution
>
>## Issue description
>The full-evaluation endpoint drops `CreateEvaluationPayload.mode`, causing modes such as `BENCHMARK` or `REPLAY` to be recorded and run as the default mode.
>
>## Issue Context
>The sibling endpoint already converts and forwards the mode.
>
>## Fix Focus Areas
>- backend/routes/harness.py[55-61]
>- backend/routes/harness.py[175-180]
>- harness/models/evaluation.py[121-126]
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

<hr/>
</details>


</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">


<!-- qodo-context:start -->
<details><summary><strong>Context sources</strong></summary>

<div>&#x2705; Compliance rules (platform): <a href="https://app.qodo.ai/rules?state=active&amp;scopes=/pranavsinghpatil/Harness-Agent/"><code>5 rules</code></a></div>
<div>Review mode: <code>🧠 Deep</code>: This is a broad, behavior-heavy harness spanning runtime code, security-sensitive dynamic execution, APIs, simulation orchestration, patch generation, MCP integration, and many independent logic paths where multiple subtle defects are plausible.</div>
<!-- qodo-context:end -->
</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">



<!-- qodo-daily-tip:start -->

<details>
<summary><strong>Tip of the day</strong></summary>

<br/>

<pre>💡 Did you know, you can group findings by type and pick your Finding display, from Minimal to Full</pre>

<a href="https://docs.qodo.ai/tips-and-tricks">More tips ↗</a> | <a href="https://app.qodo.ai/configurations?tab=display-preferences">Customize Qodo ↗</a> | <a href="https://docs.qodo.ai">Qodo docs ↗</a>

</details>

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">
<!-- qodo-daily-tip:end -->


<!-- https://github.com/pranavsinghpatil/Harness-Agent/commit/b1281d9cd1129665f48c822601d4ac3b7a32a619 -->

<a href="https://www.qodo.ai"><img src="https://www.qodo.ai/wp-content/uploads/2025/03/qodo-logo.svg" width="80" alt="Qodo Logo"></a>
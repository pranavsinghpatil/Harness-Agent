# TrueForge Agent Harness: Autonomous Hardware Reliability Investigation & Virtual Silicon Sandbox

[![Tests](https://img.shields.io/badge/tests-98%20passed-emerald.svg)](https://github.com/pranavsinghpatil/Harness-Agent/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2+-black.svg)](https://nextjs.org/)
[![Determinism](https://img.shields.io/badge/determinism-100%25%20bit--exact-indigo.svg)]()
[![MCP](https://img.shields.io/badge/MCP-8%20Tools%20Exposed-orange.svg)](https://modelcontextprotocol.io/)

Welcome to the **TrueForge Agent Harness & Virtual Hardware Sandbox** repository! 🚀

TrueForge is a **dual-system Software-in-the-Loop (SIL) platform** engineered for autonomous robotics and AI edge systems. It bridges the critical reliability gap between idealized AI simulations and physical deployment by combining a **deterministic 100 Hz hardware-physics sandbox (System 1)** with an **autonomous Bayesian reliability investigation harness (System 2)**.

---

## 🌟 Executive Overview

Autonomous agents frequently succeed in idealized simulations but experience catastrophic failures in physical environments due to non-ideal hardware effects:
- **Asynchronous Transport Latencies & Jitter:** Network packet loss, FIFO queues, and sensor delivery delays.
- **Compute Starvation & Thermal Throttling:** CPU task scheduling overloads, deadline misses, and thermal dissipation drop-offs ($85^\circ\text{C}$ throttle curves).
- **Actuator Mechanical Degradation:** Mechanical lag, steering slew rate constraints, and temperature-induced brake fading.
- **Nonlinear Compound Interactions:** Perturbations that remain completely safe in isolation (e.g. $+150\text{ ms}$ sensor lag alone or $+100\text{ ms}$ actuator delay alone) create sudden, fatal collisions when combined.

TrueForge autonomously discovers, diagnoses, causal-traces, patches, and verifies agent behavior across complex multi-dimensional perturbation spaces.

---

## 🏗️ Dual-System Architecture

TrueForge operates as two tightly coupled, deterministic subsystems:

```
+───────────────────────────────────────────────────────────────────────────────────────────+
│                                  TRUEFORGE DUAL-SYSTEM SIL                                │
│                                                                                           │
│  +─────────────────────────────────────────────────────────────────────────────────────+  │
│  │                    SYSTEM 2: AUTONOMOUS INVESTIGATION HARNESS                       │  │
│  │                                                                                     │  │
│  │   [Investigation Goal / Budget] ──► Deterministic 4-Phase Experiment Planner        │  │
│  │                                                │                                    │  │
│  │   [Causal DAG Telemetry Analyzer] ◄────────────┼──────────► [Hypothesis Engine]     │  │
│  │                 │                              │           (Bayesian Evidence)      │  │
│  │                 ▼                              ▼                    │               │  │
│  │   [AST Hardening Auto-Patcher] ──► [3-Pillar Verification Gate] ◄───┘               │  │
│  │                                                │                                    │  │
│  │   [Persistent Session Store (LRU/TTL)] ◄───────┴──────► [WebSocket Live Stream /    │  │
│  │                                                          REST API / MCP Server]     │  │
│  +─────────────────────────────────────────────────────────────────────────────────────+  │
│                                           │                                               │
│                         Declarative Experiments / Perturbations                           │
│                                           ▼                                               │
│  +─────────────────────────────────────────────────────────────────────────────────────+  │
│  │                      SYSTEM 1: VIRTUAL HARDWARE SANDBOX                             │  │
│  │                                                                                     │  │
│  │   Scenario & World Map (50m x 50m Arena, Static Walls, Dynamic Obstacles)           │  │
│  │         │                                                                           │  │
│  │         ▼                                                                           │  │
│  │   2D Kinematics & SAT Collision ──► Asynchronous Sensors (LiDAR, Camera, IMU, etc.) │  │
│  │         ▲                                    │                                      │  │
│  │         │                                    ▼                                      │  │
│  │   Actuator Pipeline ◄────────────── Hardware Transport Bus (Latency, Loss, Jitter)  │  │
│  │   (Lag, Slew, Fade)                          │                                      │  │
│  │         ▲                                    ▼                                      │  │
│  │   Command Queue ◄────────────────── Virtual Edge Scheduler (Deadlines & Thermal)    │  │
│  │         ▲                                    │                                      │  │
│  │         │                                    ▼                                      │  │
│  │         └────────────────────────── Target AI Controller (Perception -> PID)        │  │
│  │                                                                                     │  │
│  │   Ground-Truth Safety Oracle & High-Rate Bit-Exact SHA-256 Telemetry Recorder       │  │
│  +─────────────────────────────────────────────────────────────────────────────────────+  │
+───────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 🔬 Core System Components

### System 1: Virtual Hardware Physics Sandbox
- **Discrete Monotonic Clock:** Advances in fixed $100\text{ Hz}$ ticks ($\Delta t = 0.01\text{s}$) with deterministic priority-queue event resolution.
- **2D Kinematic Physics & SAT Collision:** Symplectic Euler integration of vehicle kinematics coupled with Separating Axis Theorem (SAT) convex polygon collision detection, raycasting, and obstacle clearance evaluation.
- **Asynchronous Sensor Transport Bus:** Simulates physical transport channels (LiDAR at $20\text{ Hz}$, Camera at $30\text{ Hz}$, IMU at $100\text{ Hz}$, Wheel Encoders, GPS) with independent latency distributions, buffer capacities, jitter, and packet dropouts.
- **Virtual Edge Compute Scheduler:** FIFO and Priority-based CPU task scheduler modeling compute execution time, deadline misses, and thermal throttling:
  $$\Delta T = \left( k_{\text{heat}} \cdot \text{busy\_factor} \cdot 100 - k_{\text{cool}} \cdot (T_{\text{current}} - T_{\text{ambient}}) \right) \cdot \Delta t$$
  When $T \ge 85^\circ\text{C}$, compute throughput dynamically drops to $0.4\times$ capacity.
- **Mechanical Actuator Pipeline:** Models physical steering slew limits ($|\Delta \delta| \le \dot{\delta}_{\max} \cdot \Delta t$), throttle lag, and progressive brake pad fade.
- **Cryptographic Determinism:** Seed-isolated PRNG domains (`sensors`, `transport`, `hardware`, `actuators`) generating bit-exact execution traces validated by cryptographic SHA-256 run hashes.

### System 2: Autonomous Investigation Harness
- **Deterministic 4-Phase Experiment Planner:**
  1. *Phase 0 (Baseline):* Confirms nominal safety and performance under zero perturbations.
  2. *Phase 1 (Screening):* Systematically isolates each perturbation dimension at maximum boundary values.
  3. *Phase 2 (Boundary Search):* Executes binary search along vulnerable dimensions to isolate precise failure thresholds.
  4. *Phase 3 (Interaction Discovery):* Probes multi-fault combinations to discover compound failure modes where single faults appear safe.
- **Competing Hypothesis Engine:** Maintains Bayesian belief states across single-variable and interaction hypotheses, automatically applying supporting and refuting evidence.
- **Auditable Decision Trace:** Emits formal decision records at each experiment transition:
  $$\text{PLAN} \longrightarrow \text{RUN} \longrightarrow \text{OBSERVE} \longrightarrow \text{HYPOTHESIZE} \longrightarrow \text{EXPLAIN} \longrightarrow \text{TEST NEXT}$$
- **Causal DAG Telemetry Analyzer:** Traverses execution events backwards from safety violations across the timeline to isolate root-cause failure mechanisms (e.g., *Transport Stagnation $\to$ Stale Observation $\to$ Delayed Braking $\to$ Boundary Collision*).
- **AST Hardening Auto-Patcher & 3-Pillar Verification:** Automatically parses target controller Python AST, injects fallback and safety guardrails, and enforces a strict 3-Pillar Gate:
  1. **Safety Pillar:** $0$ safety oracle invariant breaches.
  2. **Behavioral Pillar:** Proves active progress ($\Delta \text{distance} > 0.5\text{m}$) to reject trivial static stops.
  3. **Runtime Health Pillar:** Clean execution with zero unhandled exceptions (`ControllerHealth.HEALTHY`).
- **Persistent Investigation Sessions:** Thread-safe, bounded in-process session manager with LRU and TTL eviction, atomic snapshot replay, and live event fanout.

---

## 📡 API & Protocol Reference

### REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/harness/investigations` | Initiates asynchronous investigation session (`202 Accepted`) |
| `GET` | `/api/harness/investigations/{id}` | Retrieves session snapshot, leading hypothesis, and decision trace |
| `POST` | `/api/harness/investigations/{id}/approval` | Bearer-authenticated approval or rejection; approval resumes verification and regression |
| `GET` | `/api/harness/investigations/{id}/events` | Retrieves full audit log of canonical lifecycle & System 1 events |
| `GET` | `/api/harness/investigations` | Lists all active and retained investigation sessions |
| `DELETE` | `/api/harness/investigations/{id}` | Removes session and cleans up owned evaluation artifacts |
| `POST` | `/api/harness/evaluate-full` | Executes synchronous closed-loop: Run $\to$ Diagnose $\to$ Patch $\to$ Verify |
| `GET` | `/api/scenarios` | Lists available scenario configurations |
| `GET` | `/api/hardware/presets` | Lists hardware profiles (e.g. `RDK_X5`, `JETSON_ORIN`, `RASPBERRY_PI_4`) |
| `POST` | `/api/sim/run` | Runs a single deterministic simulation episode |
| `POST` | `/api/sim/replay` | Replays a previous run from its `RunManifest` |

### WebSocket Streaming

- **Investigation Stream (`/ws/investigations/{investigation_id}`):** Atomically replays prior event history upon connection, then streams live System 1 & System 2 events in real time, including diagnosis, patch approval, verification, regression, and conclusion events. The delivery implementation is tracked independently in PR #21 and remains broker-free.
- **Live Frame Stream (`/ws/live`):** Broadcasts high-rate vehicle state, obstacle telemetry, sensor queues, and safety oracle statuses.

### Model Context Protocol (MCP) Server

TrueForge exposes 8 native tools for autonomous AI agent clients via `mcp_server/server.py`:
1. `list_hardware_presets`: Inspect CPU, memory, transport, and thermal profiles.
2. `inspect_scenario`: Retrieve 50m arena maps, waypoints, obstacles, and baseline parameters.
3. `create_evaluation`: Initialize an evaluation workspace.
4. `run_baseline`: Execute unperturbed nominal baseline simulation.
5. `diagnose_failure`: Run Causal DAG Analyzer on a failed run.
6. `generate_patch`: Generate AST-hardened controller candidate code.
7. `verify_patch`: Execute 3-Pillar verification on patched code.
8. `investigate_reliability`: Execute autonomous multi-experiment investigation loop.

---

## 💻 Interactive Frontend Dashboard

The platform includes a **Next.js 14 / Tailwind CSS** dashboard (`client/`) and a lightweight 2D canvas visualizer (`frontend/`):

- **2D Live Simulation Canvas:** Real-time rendering of the 50m arena, vehicle bounding box, LiDAR raycasts, dynamic obstacles, and safety distance rings.
- **Investigation Progress Matrix:** Live hypothesis confidence rankings, support/contradiction counters, and remaining experiment budget.
- **Causal DAG Graph:** Visual node-edge causal path illustrating root causes behind invariant breaches.
- **AST Patch Diff Viewer:** Interactive side-by-side comparison of baseline vs. hardened controller source code.

---

## 📁 Repository Structure

```
├── sandbox/                      # System 1: Virtual Hardware Simulation Sandbox
│   ├── api/                     # Master environment coordinator & tools (environment.py, tools.py)
│   ├── core/                    # Discrete clock, event queue, PRNG manager, lifecycle
│   ├── world/                   # 2D geometry (SAT polygons, vectors, rays), maps, obstacles
│   ├── physics/                 # Kinematic bicycle model, Symplectic Euler integration
│   ├── sensors/                 # Sensor models (LiDAR, Camera, IMU, Encoder, Position, Observation)
│   ├── transport/               # Hardware message bus with latency, jitter, queues, loss
│   ├── hardware/                # Virtual edge compute scheduler, deadlines, thermal ODE
│   ├── actuators/               # Actuator pipeline with mechanical lag, slew limiting, fade
│   ├── faults/                  # Declarative fault injection engine and perturbation space
│   ├── safety/                  # Ground-truth safety oracle and invariant validators
│   └── telemetry/               # High-rate frame recorder, RunManifest, deterministic replayer
├── harness/                      # System 2: Autonomous Reliability Investigation Harness
│   ├── investigator.py          # AutonomousInvestigator execution loop
│   ├── planning.py              # 4-Phase deterministic experiment planner & evidence ledger
│   ├── hypotheses.py            # Bayesian hypothesis evaluation engine
│   ├── diagnostics.py           # Causal DAG telemetry analyzer
│   ├── patcher.py               # AST-based controller hardening synthesizer
│   ├── evaluator.py             # ReliabilityEvaluationLoop runner
│   ├── models/                  # Evaluation requests, runs, events, and reports
│   └── orchestration/           # Session management (InvestigationSession, Store, RunManager)
├── backend/                     # FastAPI Backend Server & Streaming WebSockets
│   ├── server.py                # FastAPI application entrypoint
│   ├── routes/                  # REST endpoints (harness, simulation, scenarios, hardware)
│   └── ws/                      # WebSocket streaming handlers (live_stream.py)
├── mcp_server/                  # Model Context Protocol (MCP) Server (8 Tools)
│   └── server.py                # Stdio JSON-RPC 2.0 MCP server implementation
├── client/                      # Next.js 14 / React / Tailwind frontend application
├── target_agents/               # Autonomous agent implementations (reference_agent, baseline)
├── scenarios/                   # Declarative YAML/JSON scenario definitions
├── docs/                        # Specifications, contracts, and Qodo audit trails
└── tests/                       # 98 Unit, integration, determinism, and E2E contract tests
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites & Installation

- Python 3.11+
- Node.js 18+ (for frontend dashboard)

```bash
# Clone the repository
git clone https://github.com/pranavsinghpatil/Harness-Agent.git
cd Harness-Agent

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install Python package in editable mode with dependencies
pip install -e .
```

### 2. Run Automated Test Suite

Execute the 98 unit, integration, determinism, and contract tests:
```bash
pytest tests/ -v
```

### 3. Start the Backend API & Visualizer

Launch the FastAPI server:
```bash
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger): **[http://localhost:8000/docs](http://localhost:8000/docs)**
- Health Check: **[http://localhost:8000/health](http://localhost:8000/health)**

### 4. Launch the Next.js Frontend

```bash
cd client
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser to view the interactive investigation dashboard.

### 5. Run the MCP Server

```bash
python -m mcp_server.server
```

---

## 🎯 Showcase Scenarios

1. **Nominal Baseline (`showcase_normal_baseline`):**
   - Crossing dynamic obstacle enters the rover's path in the 50m arena.
   - Healthy sensing, on-time compute, and responsive actuation allow the agent to maintain safe clearance ($> 1.5\text{ m}$) $\to$ **SAFE**.

2. **Compound Hardware Perturbation (`showcase_perturbed_failure`):**
   - Injected multi-fault perturbation: $+310\text{ ms}$ camera transport delay, $0.7\text{ s}$ LiDAR dropout, and $+250\text{ ms}$ brake delay with $60\%$ brake fading.
   - Agent receives stale perception, misses braking window, and triggers collision $\to$ **SAFETY VIOLATION**.
   - System 2 isolates the root cause, synthesizes an AST patch with speed-scaled lookahead, and proves safety recovery via the 3-Pillar Verification Gate with **100% bit-exact replay determinism**.

---

## 🛡️ Engineering Standards & Verification

- **Strict Static Typing:** Full static type annotations across all modules and tests.
- **Architectural Modularity:** Strict separation between System 1 physical execution and System 2 cognitive decision planning.
- **Qodo Quality Gate:** Automated PR reviews, complete docstrings (`Args`, `Returns`, `Raises`), and 50-line method bounds.

---

## 📄 License & Attribution

Developed for the **WeMakeDevs Trueforge Hackathon**. Licensed under the Apache-2.0 License.

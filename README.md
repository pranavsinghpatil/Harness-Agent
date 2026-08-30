# Harness Agent - Virtual Hardware Simulation Sandbox

[![Tests](https://img.shields.io/badge/tests-21%20passed-emerald)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)]()
[![Determinism](https://img.shields.io/badge/determinism-100%25%20bit--exact-indigo)]()

Welcome to the **Harness-Agent Virtual Hardware Simulation Sandbox** repository for the [WeMakeDevs Trueforge Hackathon](https://www.wemakedevs.org/hackathons/trueforge)! 🚀

This repository provides a **zero-budget, deterministic, hardware-semantic software-in-the-loop (SIL) testbed** designed to evaluate how AI-controlled physical systems behave when sensing, communication, compute, and actuation diverge from ideal conditions.

---

## 🏗️ System Architecture

```
+-----------------------------------------------------------------------------------+
|                            VIRTUAL HARDWARE SANDBOX                               |
|                                                                                   |
|  Scenario + World Map (50m x 50m)                                                 |
|        │                                                                          |
|        ▼                                                                          |
|  2D Kinematic Physics ──► Asynchronous Sensors (10-100 Hz)                        |
|        ▲                    │ (LiDAR, IMU, Encoder, GPS, Camera)                  |
|        │                    ▼                                                     |
|  Actuator Pipeline     Hardware Transport Bus (Latency, Jitter, Drops)            |
|  (Delay, Slew, Lag)         │                                                     |
|        ▲                    ▼                                                     |
|        │               Virtual Edge Hardware (CPU Scheduler, Deadlines, Thermal)  |
|        │                    │                                                     |
|  Command Queue              ▼                                                     |
|        ▲               Target AI Agent (Perception -> Estimator -> Planner -> PID)|
|        │                    │                                                     |
|        └────────────────────┘                                                     |
|                                                                                   |
|  Declarative Fault Controller (Target: sensors, transport, compute, actuators)    |
|  Ground-Truth Safety Oracle (Collisions, Clearance, Stopping Distance, Stale Fix)|
|  Deterministic Telemetry & RunManifest Replayer (SHA-256 Bit-Exact Verification)  |
+-----------------------------------------------------------------------------------+
```

---

## 📁 Repository Structure

```
├── sandbox/                  # Core simulation engine package
│   ├── core/                # Discrete clock, priority event queue, seeded RNG manager, episode lifecycle
│   ├── world/               # 2D geometry (SAT polygons, rays, vectors), entities, 50m arena maps
│   ├── physics/             # Kinematic bicycle model, Symplectic Euler integration, SAT collision
│   ├── sensors/             # Asynchronous sensor models (LiDAR, IMU, Encoder, Position, Camera)
│   ├── transport/           # Simulated hardware message bus with latency, jitter, buffer queues, loss
│   ├── hardware/            # Virtual edge compute scheduler, deadline tracking, thermal throttling
│   ├── actuators/           # Actuator command pipeline with mechanical lag, slew, and brake fade
│   ├── faults/              # Declarative fault injection framework and runtime controller
│   ├── safety/              # Ground-truth safety oracle and invariant properties
│   ├── telemetry/           # High-rate recorder, JSONL logs, RunManifest, deterministic replayer
│   └── api/                 # Programmatic sandbox API and tools (create, run, step, replay)
├── target_agents/           # System-Under-Test (SUT) autonomous agents
│   ├── baseline/            # Reactive threshold-based baseline agent
│   └── reference_agent/     # Full modular autonomous ground agent (Perception, Fusion, Planner, PID)
├── scenarios/               # Declarative scenario definitions (YAML/JSON)
│   ├── templates/           # Reusable scenario templates (e.g. empty track)
│   └── generated/           # Curated testbeds (Showcase Safe Baseline vs Perturbed Hardware Failure)
├── backend/                 # FastAPI REST API & WebSocket server for live telemetry streaming
├── frontend/                # Interactive 2D canvas visualizer & telemetry dashboard
├── tests/                   # Comprehensive unit, integration, determinism, and showcase tests
├── .ai/                     # AI agent operational guidelines (`agents.md`)
└── .cursorrules             # Cursor IDE rules and architectural constraints
```

---

## 🚀 Getting Started

### 1. Installation & Environment

Clone the repository and install dependencies:
```bash
git clone https://github.com/pranavsinghpatil/Harness-Agent.git
cd Harness-Agent
pip install -e .
```

### 2. Running Automated Tests

Run the complete test suite verifying determinism, physics, sensors, compute, faults, safety, and showcase scenarios:
```bash
pytest tests/ -v
```

### 3. Launching the Backend API & Interactive Visualizer

Start the FastAPI server:
```bash
uvicorn backend.server:app --port 8000 --reload
```
Open your browser at **[http://localhost:8000](http://localhost:8000)** to launch the visualizer dashboard.

---

## 🎯 The Showcase Demo Scenario

The sandbox includes the benchmark moving-obstacle scenario specified in the development plan:

1. **Safe Baseline (`showcase_normal_baseline`):**
   - A crossing dynamic obstacle enters the rover's path.
   - Fresh sensor observations and healthy actuation allow the autonomous agent to smoothly brake and maintain a safe clearance margin ($> 1.5\text{ m}$) $\to$ **SAFE**.

2. **Perturbed Hardware Failure (`showcase_perturbed_failure`):**
   - Same obstacle trajectory with compound hardware perturbations injected:
     - $+310\text{ ms}$ camera transport latency
     - $0.7\text{ s}$ temporary LiDAR dropout
     - $+250\text{ ms}$ brake actuator delay and $60\%$ brake fading
   - Stale perception reaches the motion planner $\to$ delayed braking $\to$ **SAFETY VIOLATION**.
   - The entire failure sequence is captured in a `RunManifest` and verified to reproduce with **100% bit-exact determinism** on replay.

---

## 🤝 Contributing & Team Guidelines

- Follow [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming (`feature/*`, `fix/*`, `t/*`) and PR rules.
- Review [.ai/agents.md](.ai/agents.md) for detailed AI harness context, coding conventions, and testing protocols.

## Agentic Investigation Layer

The sandbox is System 1: it executes one declarative experiment deterministically.
The Harness is System 2: it chooses bounded experiments, records evidence,
maintains competing hypotheses, and decides what to test next.

The investigator emits an auditable decision trace for every experiment:

```text
PLAN -> RUN -> OBSERVE -> HYPOTHESIZE -> EXPLAIN DECISION -> TEST NEXT
```

Each trace contains the experiment phase, action class, hypotheses available
before execution, post-observation belief updates, refuted historical beliefs,
information-value estimate, outcome classification, rationale, and the planner's
actual next experiment or stop state. It gives frontend and TrueForge MCP
consumers a concrete investigation story without exposing private model
reasoning.

The project differentiator is interaction discovery: independent sensor and
compute perturbations can remain safe while their combined condition crosses a
failure boundary. The harness preserves the seed, scenario, hardware profile,
fault values, telemetry, and evidence needed to reproduce that result.

The `investigate_reliability` MCP tool returns the experiment history,
provenance-backed evidence, competing hypotheses, falsification plans, and the
decision trace so the agent's observable actions are inspectable end to end.

### Persistent Investigation Sessions

The HTTP investigation endpoint is asynchronous: `POST /api/harness/investigations`
returns `202 Accepted` with an `investigation_id`. Read the current session from
`GET /api/harness/investigations/{investigation_id}`, inspect its ordered event
history at `/events`, or subscribe to
`WS /ws/investigations/{investigation_id}` for replay plus live lifecycle and
System 1 execution events. Every streamed event includes an `event_id` and
stable investigation context; experiment execution events also expose
`experiment_id`, `evaluation_id`, `run_id`, and `episode_id` for direct
evidence tracing. This gives the frontend a stable session contract while
System 2 continues executing deterministic System 1 experiments in the
background.

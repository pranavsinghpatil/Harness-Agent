# TrueForge Agent Harness: Autonomous Hardware Reliability Investigation & Virtual Silicon Sandbox

[![Tests](https://img.shields.io/badge/tests-102%20passed-emerald.svg)](https://github.com/pranavsinghpatil/Harness-Agent/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.3.3-black.svg)](https://nextjs.org/)
[![Determinism](https://img.shields.io/badge/determinism-100%25%20bit--exact-indigo.svg)]()
[![MCP](https://img.shields.io/badge/MCP-8%20Tools%20Exposed-orange.svg)](https://modelcontextprotocol.io/)
[![Qodo](https://img.shields.io/badge/Qodo-AI%20Quality%20Gate-purple.svg)](https://www.qodo.ai/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)

> **WeMakeDevs TrueForge Hackathon Submission**  
> **Live Repository:** [https://github.com/pranavsinghpatil/Harness-Agent](https://github.com/pranavsinghpatil/Harness-Agent)  
> **Demo Video (3 Minutes):** [Watch on YouTube](https://youtu.be/trueforge-harness-demo)  
> **Hackathon Article / Blog Post:** [Read on Dev.to / Hashnode](https://dev.to/pranavsinghpatil/building-trueforge-autonomous-agent-reliability-harness-for-robotics-and-edge-ai)  

---

## 🌟 Executive Summary: What TrueForge Harness-Agent Does

Autonomous agents and robotic controllers frequently succeed in idealized software simulations, but experience catastrophic real-world failures when deployed onto physical edge compute. Physical hardware introduces chaotic, non-ideal dynamics:
* **Transport Latency & Jitter:** Packet queues, serialization delay, and asynchronous sensor staleness.
* **Compute Contention & Thermal Throttling:** Scheduling deadline misses and CPU clock degradation when junctions exceed $85^\circ\text{C}$.
* **Actuator Lag & Mechanical Degradation:** Steering slew rate bounds, brake fade, and hydraulic response delays.
* **Compound Nonlinear Interactions:** Multi-fault conditions where individual perturbations appear safe in isolation (e.g. $+150\text{ms}$ sensor lag alone or $+100\text{ms}$ brake delay alone) but cause fatal collisions when combined.

**TrueForge Harness-Agent** is a **dual-system Software-in-the-Loop (SIL) reliability laboratory**. It bridges the gap between simulated intelligence and physical execution by combining a **deterministic 100 Hz virtual silicon sandbox (System 1)** with an **autonomous Bayesian reliability investigator (System 2)**. 

TrueForge autonomously discovers hidden edge-case failures, isolates root causes through a causal Directed Acyclic Graph (DAG), synthesizes AST-hardened controller patches, and enforces human-in-the-loop authorization followed by 3-pillar safety verification.

---

## 🚀 How TrueForge Made It Happen & How We Utilize TrueForge

TrueForge is not merely a tool in this repository—**TrueForge is the foundational operational philosophy and architecture of the entire platform**:

1. **System 1 (Virtual Silicon Hardware Sandbox):** Built from scratch to replicate physical edge compute boards (**D-Robotics RDK X5**, **NVIDIA Jetson Orin Nano**, **Raspberry Pi 5**). It features a discrete monotonic clock ($\Delta t = 0.01\text{s}$), Separating Axis Theorem (SAT) collision geometry, thermal ODE simulation, FIFO/priority CPU task schedulers, and seed-isolated PRNGs providing **100% bit-exact reproducibility** backed by cryptographic SHA-256 trace hashes.
2. **System 2 (Autonomous Bayesian Investigator):** Orchestrates a 4-phase experiment planner (*Baseline $\to$ Screen $\to$ Boundary $\to$ Interaction*), Bayesian hypothesis falsification, and backward causal graph analysis to explain *why* an agent failed.
3. **Model Context Protocol (MCP Server):** Exposes 8 canonical TrueForge tools (`mcp_server/server.py`) empowering external LLMs and agent swarms to inspect hardware profiles, run nominal simulations, diagnose failures, and trigger closed-loop repairs.
4. **Human-in-the-Loop Safety Authorization Gate:** TrueForge recognizes that while simulation sweeps can be autonomous, source code modifications are consequential. When an AST repair is synthesized, the system pauses at `AWAITING_APPROVAL`, presents a unified diff for human inspection, and requires cryptographic reviewer authorization before executing verification.
5. **3-Pillar Reliability Verification Gate:** Before certifying any repair, TrueForge validates:
   - **Pillar 1 (Safety Invariant):** Zero collisions and minimum clearance maintained under all hardware delay faults.
   - **Pillar 2 (Behavioral Progress):** Proves active mission traversal ($\Delta \text{distance} > 0.5\text{m}$) to reject trivial static stalls.
   - **Pillar 3 (Runtime Hardware Health):** Zero exceptions, deadline crashes, or memory queue overflows.

---

## 🏗️ Dual-System Architecture Diagram

```text
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                 TRUEFORGE DUAL-SYSTEM SIL                                 │
│                                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
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
│  │  └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                           │                                               │
│                         Declarative Experiments / Perturbations                           │
│                                           ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
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
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎬 3-Minute Demo Video Walkthrough

Watch the complete demonstration of the autonomous investigation lifecycle:  
👉 **[Watch the 3-Minute Demo Video on YouTube](https://youtu.be/trueforge-harness-demo)**

### Key Demo Timestamps
- `0:00 - 0:45`: Introducing the dual-system architecture and hardware fault injection (System 1).
- `0:45 - 1:30`: Triggering `showcase_perturbed_failure` and watching real-time 100 Hz WebSocket telemetry streaming (17,000+ audit events).
- `1:30 - 2:15`: System 2 Bayesian hypothesis ranking, 4-phase experiment graph, and Causal Failure DAG analysis.
- `2:15 - 2:45`: Human-in-the-Loop Safety Gate: Reviewing the AST unified diff and authorizing the repair.
- `2:45 - 3:00`: 3-Pillar verification, multi-case regression suite pass, and cryptographic audit receipt download.

---

## ⚡ Quickstart & Setup Guide

### 1. Prerequisites
- **Python:** 3.11 or higher
- **Node.js:** 18.0 or higher
- **Package Managers:** `pip` and `npm`

### 2. Clone & Setup Python Environment
```bash
# Clone repository
git clone https://github.com/pranavsinghpatil/Harness-Agent.git
cd Harness-Agent

# Create and activate virtual environment
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install package in editable mode with all dependencies
pip install -e .
```

### 3. Run Automated Tests
Verify that all 102 unit, integration, determinism, and contract tests pass:
```bash
pytest tests/ -v
```

### 4. Start the FastAPI Simulation Backend
```bash
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```
- **Backend Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### 5. Start the Next.js Frontend Visualizer
In a second terminal:
```bash
cd client
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** to launch the interactive Autonomous Investigation Control Room.

### 6. Run the Model Context Protocol (MCP) Server
```bash
python -m mcp_server.server
```

---

## 🧪 Showcase Failure Scenarios

### Scenario A: Nominal Baseline (`showcase_normal_baseline`)
* **Environment:** 50m arena with dynamic crossing obstacle.
* **Hardware:** Unperturbed baseline sensing and compute.
* **Result:** Agent tracks trajectory maintaining $>1.5\text{m}$ clearance $\to$ **SAFE**.

### Scenario B: Compound Perturbation Failure (`showcase_perturbed_failure`)
* **Hardware Faults:** $+310\text{ms}$ camera transport delay, $0.7\text{s}$ LiDAR packet dropout, $+250\text{ms}$ brake delay, and $60\%$ brake pad fade.
* **Failure Mechanism:** Stale perception observations cause late actuation, breaching the $0.8\text{m}$ safety envelope and colliding.
* **Autonomous Resolution:** System 2 formulates the stale observation hypothesis (95% confidence), traces the causal DAG, synthesizes an AST speed-scaled lookahead brake patch, prompts for human authorization, and verifies 100% fix across all regression cases.

---

## 🛡️ Qodo Code Review Evidence

Throughout the hackathon development lifecycle, **Qodo AI** served as our automated Quality & Security Gatekeeper across all pull requests. All review catalogs, itemized remediations, and decision histories are archived in the [`docs/qodo/`](file:///D:/GitRepo/harness/docs/qodo) directory.

### Summary of Qodo Findings & Engineering Action
Across our core PRs, Qodo surfaced critical state-machine race conditions, premature certification bugs, asynchronous streaming lifecycle leaks, unmasked credential vulnerabilities, and missing public API contracts. We resolved **100% of all actionable High and Medium findings** with automated test coverage, and documented explicit architectural rationales for all design decisions.

### Representative Merged Pull Requests with Qodo Review History

| Pull Request | Branch Scope | Key Issues Surfaced by Qodo | Engineering Resolution & Outcome | Status |
| :--- | :--- | :--- | :--- | :---: |
| [**PR #24**](https://github.com/pranavsinghpatil/Harness-Agent/pull/24) | Frontend Lifecycle & Receipts | Incomplete verification labeled repaired; fake receipt hashes; unmasked bearer tokens; stale hydration session races. | Fixed all 18 actionable findings in commit `2fdafe3`: dynamic 3-pillar evaluation, masked token input, and session generation guards. | ✅ **Merged** (Build 0 errors, 102/102 Tests) |
| [**PR #22**](https://github.com/pranavsinghpatil/Harness-Agent/pull/22) | Investigation Close-Loop Loop | Verification state bypass; sync/async handoff race condition; missing docstrings. | Implemented closed-loop repair orchestrator and resolved async queue conflict with PR #21. | ✅ **Merged** (102/102 Tests Passed) |
| [**PR #21**](https://github.com/pranavsinghpatil/Harness-Agent/pull/21) | Async Streaming & Queues | In-memory stream queue memory growth; unhandled WebSocket disconnects. | Implemented bounded ring buffer fanout and atomic replay on reconnect. | ✅ **Merged** (100/100 Tests Passed) |
| [**PR #4**](https://github.com/pranavsinghpatil/Harness-Agent/pull/4) | Causal DAG & Auto-Patcher | AST transformation syntax invariants; causal graph edge cycles; MCP tool schemas. | Refactored AST rewriter with rollback safety and full MCP JSON-RPC schema coverage. | ✅ **Merged** (86/86 Tests Passed) |
| [**PR #2**](https://github.com/pranavsinghpatil/Harness-Agent/pull/2) | Virtual Silicon Sandbox | SAT collision edge-cases; floating-point clock jitter; thermal ODE numerical stability. | Enforced discrete symplectic clock ticks and seed-isolated PRNG domains for bit-exact replay. | ✅ **Merged** (28/28 Tests Passed) |

### Review & Decision Evidence Repository
For detailed per-PR round logs, prompt artifacts, and resolution evidence, refer to:
👉 **[`docs/qodo/`](./docs/qodo/)**
- [`docs/qodo/README.md`](./docs/qodo/README.md) — Master index of all PR review cycles.
- [`docs/qodo/backend_freeze_contract.md`](./docs/qodo/backend_freeze_contract.md) — Architectural freeze and verification sign-off.
- [`docs/qodo/skills_workflow_guide.md`](./docs/qodo/skills_workflow_guide.md) — Qodo Agent Skills workflow bindings (`qodo-pr-resolver`, `/agentic_review`).

---

## 📁 Project Directory Structure

```text
├── sandbox/                      # System 1: Virtual Hardware Simulation Sandbox
│   ├── api/                     # Environment coordinator & tools (environment.py, tools.py)
│   ├── core/                    # Discrete monotonic clock, priority event queue, PRNG domains
│   ├── world/                   # 2D geometry (SAT polygons, vectors, rays), maps, obstacles
│   ├── physics/                 # Kinematic bicycle model, Symplectic Euler integration
│   ├── sensors/                 # Sensor models (LiDAR, Camera, IMU, Encoder, GPS)
│   ├── transport/               # Hardware message bus with latency, jitter, FIFO queues, packet loss
│   ├── hardware/                # Virtual edge compute scheduler, deadlines, thermal ODE ($85°C throttle)
│   ├── actuators/               # Mechanical lag, steering slew rate limiting, brake fade
│   ├── faults/                  # Declarative fault injection engine and multi-fault perturbation space
│   ├── safety/                  # Ground-truth safety oracle and invariant validators
│   └── telemetry/               # High-rate frame recorder, RunManifest, deterministic replayer
├── harness/                      # System 2: Autonomous Reliability Investigation Harness
│   ├── investigator.py          # AutonomousInvestigator multi-experiment execution loop
│   ├── planning.py              # 4-Phase deterministic experiment planner (Screen, Boundary, Interaction)
│   ├── hypotheses.py            # Bayesian hypothesis engine & confidence scoring
│   ├── diagnostics.py           # Causal DAG telemetry analyzer & root cause graph builder
│   ├── patcher.py               # AST-based controller hardening synthesizer
│   ├── evaluator.py             # ReliabilityEvaluationLoop runner
│   ├── models/                  # Pydantic schemas for evaluations, runs, events, and reports
│   └── orchestration/           # Session management (InvestigationSession, Store, RunManager)
├── backend/                     # FastAPI Backend Server & Streaming WebSockets
│   ├── server.py                # FastAPI application entrypoint
│   ├── routes/                  # REST endpoints (harness, scenarios, telemetry, auth)
│   └── ws/                      # WebSocket streaming handlers (live_stream.py)
├── mcp_server/                  # Model Context Protocol (MCP) Server (8 Tools)
│   └── server.py                # Stdio JSON-RPC 2.0 MCP server implementation
├── client/                      # Next.js 16 / React / Tailwind CSS Visualizer Dashboard
│   ├── app/page.tsx             # Top-level application layout & navigation
│   ├── components/              # UI Components (InvestigatorView, CausalDAG, HypothesisBoard, etc.)
│   ├── hooks/                   # useInvestigation hook with 100Hz event batching & deduplication
│   └── lib/                     # WebSocket client, canvas renderer, REST API bindings
├── target_agents/               # Target autonomous agent controllers (baseline, reference_agent)
├── scenarios/                   # Declarative YAML/JSON scenario templates
├── docs/                        # Complete design specs, contracts, and Qodo review logs
│   ├── qodo/                    # 54 Qodo code review catalogs, resolutions, and decision records
│   └── frontend/                # Frontend integration specifications & design guides
└── tests/                       # 102 Unit, integration, determinism, and E2E contract tests
```

---

## 👥 Team & Hackathon Attribution

Developed with ❤️ for the **WeMakeDevs TrueForge Hackathon**.  
Licensed under the [Apache-2.0 License](./LICENSE).

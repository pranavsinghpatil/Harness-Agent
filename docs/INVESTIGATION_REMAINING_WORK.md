# TrueForge Harness-Agent: Autonomous Investigator Remaining Work Specification

This document provides a **complete, modular roadmap** of the remaining work required to finalize the frontend and close-loop integration with the persistent backend architecture. 

Each **Work Package (Area)** below is structured as an **isolated, context-rich task** that you can copy and paste directly into a new agent chat.

---

## Table of Contents
1. [Architecture Overview & Current State](#architecture-overview--current-state)
2. [Area 1: Event Stream Reducer & High-Throughput Batching Performance](#area-1-event-stream-reducer--high-throughput-batching-performance)
3. [Area 2: 2D Canvas Live Frame Hydration & Historical Scrubbing Replay](#area-2-2d-canvas-live-frame-hydration--historical-scrubbing-replay)
4. [Area 3: UI Architecture Convergence & Legacy Workbench Cleanup](#area-3-ui-architecture-convergence--legacy-workbench-cleanup)
5. [Area 4: Human-in-the-Loop Auto-Approval Modal & Lifecycle Flow](#area-4-human-in-the-loop-auto-approval-modal--lifecycle-flow)
6. [Area 5: Audit Receipt Export & Final Certification Polishing](#area-5-audit-receipt-export--final-certification-polishing)

---

## Architecture Overview & Current State

### Backend Canonical Flow (PR #20 on `main`)
```text
POST /api/harness/investigations (Returns 202 Accepted + investigation_id)
        ↓
Background Worker (InvestigationSession)
        ↓
WebSocket (/ws/investigations/{investigation_id})
        ↓
Phases: INVESTIGATING → DIAGNOSING → PATCH_PROPOSED → AWAITING_APPROVAL → VERIFYING → REGRESSING → COMPLETED
```

### Why 13,000+ Events Are Emitted in Step 1
- System 1 simulation runs at **100 Hz (`dt = 0.01s`)**.
- In every 10 ms tick, System 1 emits ~11 granular events (`ACTUATOR_APPLIED`, `SENSOR_SAMPLED` $\times 5$, `PACKET_DELIVERED` $\times 5$, `TASK_SCHEDULED`, `COMPUTE_STARTED`, `COMMAND_ISSUED`).
- A 12-second experiment generates $1,200 \times 11 \approx \mathbf{13,200\text{ events}}$.
- **Root Problem**: The frontend event reducer was processing each event individually with an $O(N)$ linear scan, choking the React event loop.

---

## Area 1: Event Stream Reducer & High-Throughput Batching Performance

> **Context for New Agent Chat**:
> The backend streams ~13,000 low-level System 1 events per simulation experiment over `/ws/investigations/{id}`. `client/hooks/useInvestigation.ts` currently runs an $O(N)$ linear deduplication scan (`prev.events.some(...)`) and triggers an unbatched `setState` for every single message. This freezes the React UI thread during live execution.

### Target Files
- `client/hooks/useInvestigation.ts`
- `client/components/LiveEventStream.tsx`

### Problem & Root Cause
1. **$O(N^2)$ Complexity**: Scanning `prev.events` on each of the 13,000 events causes $\sim 84.5\text{M}$ array comparisons per experiment.
2. **Unbatched React Re-renders**: Triggering 1,000+ `setState` calls per second floods the React scheduler.
3. **Unbounded Memory Growth**: `prev.events` keeps all 100,000+ events in React state across multiple experiments.

### Exact Changes Needed
1. **$O(1)$ Event ID Deduplication**:
   - Maintain a `useRef<Set<string>>(new Set())` to check `seenEventIds.has(event.event_id)` in $O(1)$ time.
2. **Event Queue & RequestAnimationFrame Batching**:
   - High-frequency System 1 physics/sensor events (`SIMULATION_STEP`, `SENSOR_SAMPLED`, `COMMAND_ISSUED`, `PACKET_DELIVERED`, `TASK_SCHEDULED`, `COMPUTE_STARTED`, `ACTUATOR_APPLIED`) should be pushed to an incoming queue and flushed to React state in batches every **50 ms** or using `requestAnimationFrame`.
   - Critical System 2 milestone events (`EXPERIMENT_PLANNED`, `EXPERIMENT_COMPLETED`, `HYPOTHESIS_UPDATED`, `DECISION_RECORDED`, `PATCH_APPROVAL_REQUESTED`, `INVESTIGATION_COMPLETED`, `INVESTIGATION_FAILED`) should flush immediately.
3. **Fixed-Size Ring Buffer for Display Events**:
   - Limit `state.events` in React state to the latest **500–1,000 events** to keep DOM rendering fast.
4. **Optimized Filtering in `LiveEventStream.tsx`**:
   - Memoize category checks and avoid re-JSON-stringifying payloads on every render pass.

### Verification Steps
```bash
# 1. Start backend:
uvicorn backend.server:app --port 8000
# 2. Run frontend in client/:
npm run dev
# 3. Start an investigation with budget=5.
# 4. Confirm zero UI lag, smooth scrolling in LiveEventStream, and instant tab responsiveness across 50,000+ streamed events.
```

---

## Area 2: 2D Canvas Live Frame Hydration & Historical Scrubbing Replay

> **Context for New Agent Chat**:
> During investigation execution, the 2D canvas visualizer needs to show vehicle movement and allow the user to click any completed experiment in the experiment graph to scrub and replay its simulation run.

### Target Files
- `client/hooks/useInvestigation.ts`
- `client/components/InvestigatorView.tsx`
- `client/components/SimulationCanvas.tsx`
- `client/lib/api.ts`

### Problem & Root Cause
1. **Missing Coordinate Data in Live Events**: Granular events (`COMMAND_ISSUED`, `SENSOR_SAMPLED`) do not carry full `vehicle_state: { x, y, heading, velocity }`. The fallback in `useInvestigation.ts` defaults to `(0, 0)`.
2. **Empty History Cache on Experiment Select**: When an operator selects a past experiment from the dropdown or experiment graph, `allExperimentFrames[experiment_id]` is empty because frames are recorded inside `HarnessRun.telemetry_frames` on the backend, not in the event payload.

### Exact Changes Needed
1. **Hydrate Frames on Experiment Completion**:
   - When `EXPERIMENT_COMPLETED` arrives (which carries `evaluation_id` and `experiment_id`), make a fast background call to `getEvaluation(apiBase, evaluation_id)`.
   - Extract `evaluation.baseline_run.telemetry_frames` and store them in `allExperimentFrames[experiment_id]`.
2. **Seamless Canvas Scrubbing in `InvestigatorView.tsx`**:
   - When `selectedExperimentId` is chosen, immediately set `playbackFrames` to `allExperimentFrames[selectedExperimentId]`.
   - Reset scrubber `currentFrameIdx = 0` and allow Play/Pause at 1x, 2x, 4x speeds.
3. **Live Indicator on Canvas**:
   - When viewing the active live stream, render a live pulse badge on the canvas (`🔴 LIVE EXPERIMENT EXP-003`) and show the active obstacle/hazard state.

### Verification Steps
```bash
# 1. Run investigation.
# 2. As experiments 1, 2, 3 complete, click on EXP-001 or EXP-002 in the graph.
# 3. Verify that 2D canvas displays the vehicle driving smoothly along the trajectory and scrubber responds to play/pause.
```

---

## Area 3: UI Architecture Convergence & Legacy Workbench Cleanup

> **Context for New Agent Chat**:
> `client/app/page.tsx` currently maintains two separate mental models: the legacy "⚡ Evaluation Workbench" (calling synchronous `POST /evaluate-full`) and the new "🔬 Autonomous Investigator Studio". We must converge into one unified "Investigation Control Room".

### Target Files
- `client/app/page.tsx`
- `client/components/Header.tsx`
- `client/components/HarnessView.tsx`

### Problem & Root Cause
- The old workbench tab confuses the product story by promoting synchronous evaluation instead of the autonomous persistent investigation lifecycle.

### Exact Changes Needed
1. **Single Source of Truth**:
   - Set `"investigator"` as the default active view.
   - Refactor `page.tsx` so the top navigation presents:
     - **🔬 Investigation Control Room** (Primary default view).
     - **⚡ Ad-Hoc Evaluation Debugger** (Secondary/optional tab for single-run debugging).
2. **Unified Session Header**:
   - Ensure the header status indicator reflects the active investigation session ID, phase (`INVESTIGATING`, `AWAITING_APPROVAL`, `VERIFYING`, `COMPLETED`), and connection state.
3. **Remove Redundant Polling & Dead Code**:
   - Clean up unneeded legacy states in `page.tsx`.

### Verification Steps
```bash
# 1. Open http://localhost:3000
# 2. Confirm the page directly opens into the Control Room Launchpad / Active Session.
# 3. Verify zero console errors and clean navigation.
```

---

## Area 4: Human-in-the-Loop Auto-Approval Modal & Lifecycle Flow

> **Context for New Agent Chat**:
> When an autonomous investigation detects a reliability failure, System 2 generates an AST code patch and transitions the backend into `AWAITING_APPROVAL`. The UI must prominently present the approval gate, show the unified diff, accept reviewer authorization, and transition through Verification and Multi-Case Regression.

### Target Files
- `client/hooks/useInvestigation.ts`
- `client/components/InvestigatorView.tsx`
- `client/components/PatchApprovalModal.tsx`
- `client/components/ControlRoomHeader.tsx`

### Problem & Root Cause
- Currently, when `PATCH_APPROVAL_REQUESTED` arrives, `phase` becomes `AWAITING_APPROVAL`, but the operator must manually click "Review Patch" in the header to open the modal. If unattended, the session remains waiting without visual prominence.

### Exact Changes Needed
1. **Auto-Trigger Approval Modal**:
   - In `InvestigatorView.tsx`, add an effect: when `investigation.phase === "AWAITING_APPROVAL"` and `investigation.patch !== null`, automatically set `isApprovalModalOpen = true`.
2. **Prominent Control Room Banner**:
   - Add a high-visibility amber pulse banner across the top of the Control Room when awaiting approval:
     `⚠️ SAFETY FAULT DETECTED & HARDENED PATCH GENERATED — HUMAN REVIEW REQUIRED`.
3. **Approval API Call**:
   - Ensure `approveInvestigationPatch` sends `Authorization: Bearer test-reviewer-token` and payload `{ patch_id, decision: "APPROVE", reason }`.
4. **Live Transition to Verifying & Regressing**:
   - When approved, observe phase transition: `VERIFYING` $\to$ `REGRESSING` $\to$ `COMPLETED`.
   - Update the progress indicator in real-time as regression cases execute.

### Verification Steps
```bash
# 1. Start investigation with scenario `showcase_perturbed_failure` and budget 6.
# 2. Wait for failure detection (e.g. EXP-002 / EXP-003).
# 3. Verify Patch Approval Modal auto-pops with AST unified diff.
# 4. Click "Approve & Trigger Verification".
# 5. Observe Verification (dual-run diff) and Regression suite executing and completing with 3-Pillar Certification.
```

---

## Area 5: Audit Receipt Export & Final Certification Polishing

> **Context for New Agent Chat**:
> Once an investigation completes with outcome `PROVEN_REPAIRED` or `PROVEN_SAFE`, the operator needs to view the 3-pillar safety matrix and export an immutable audit receipt containing SHA-256 bit-exact trace hashes.

### Target Files
- `client/components/CloseLoopCertification.tsx`
- `client/components/HypothesisBoard.tsx`
- `client/types/simulation.ts`

### Problem & Root Cause
- The certification view renders the table and badges, but lacks a one-click export button to generate the compliance audit receipt for demonstration or archiving.

### Exact Changes Needed
1. **Export Audit Receipt Action**:
   - In `CloseLoopCertification.tsx`, add an **"📥 Export Audit Receipt (Markdown / JSON)"** button.
   - Generate a downloadable `.md` or `.json` file containing:
     - Investigation ID & Objective.
     - Leading Hypothesis Statement & Confidence.
     - Baseline Failure Root Cause & Causal Path.
     - Hardened Controller AST Unified Diff.
     - Reviewer Identity & Approval Timestamp.
     - 3-Pillar Verification Results (Safety, Behavior, Health).
     - Full Regression Matrix with deterministic trace hashes.
2. **Confidence Bar Polish**:
   - Add smooth CSS transitions to `HypothesisBoard.tsx` confidence bars when updated by incoming `HYPOTHESIS_UPDATED` events.

### Verification Steps
```bash
# 1. Run investigation to completion.
# 2. Open "🛡️ Certificate" tab.
# 3. Click "Export Audit Receipt".
# 4. Verify downloaded file is formatted correctly with valid cryptographic trace hashes.
```

---

## Summary Checklist for Task Execution

| Area | Focus | Primary Files | Estimated Complexity |
| :--- | :--- | :--- | :--- |
| **Area 1** | Event stream batching & $O(1)$ reducer | `useInvestigation.ts`, `LiveEventStream.tsx` | Medium |
| **Area 2** | Canvas live frame sync & historical scrubbing | `useInvestigation.ts`, `InvestigatorView.tsx` | Medium |
| **Area 3** | Single Control Room UI convergence | `page.tsx`, `Header.tsx` | Low |
| **Area 4** | Human-in-the-loop auto-approval gate | `InvestigatorView.tsx`, `PatchApprovalModal.tsx` | Low–Medium |
| **Area 5** | Audit receipt export & certification UI | `CloseLoopCertification.tsx` | Low |


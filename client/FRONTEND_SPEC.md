# Frontend Specification: User Journeys, Design & Layout

> The complete specification is maintained at [docs/FRONTEND_USER_JOURNEY_AND_DESIGN.md](../docs/FRONTEND_USER_JOURNEY_AND_DESIGN.md).

## Quick Summary

### Primary Flows:
1. **Flow A (The Closed-Loop Evaluation):**
   - User chooses hardware preset + fault scenario + seed $\to$ clicks **"⚡ Run Full Closed-Loop Evaluation"** (`POST /api/harness/evaluate-full`).
   - Frontend loads baseline failure frames into 2D Canvas $\to$ plays collision.
   - User toggles to "Patched Run" $\to$ watches rover safely brake and avoid collision.
   - User inspects 3-Pillars gate, Causal Root Cause DAG, and Monaco code diff patcher.

2. **Flow B (The Autonomous Investigator):**
   - User inputs objective $\to$ clicks **"🚀 Launch Autonomous Investigation"** (`POST /api/harness/investigations`).
   - System 2 schedules bounded System 1 experiments (Baseline $\to$ Screening $\to$ Boundary $\to$ Interaction).
   - Frontend displays Hypothesis Confidence Board and Chronological Decision Trace Audit Timeline.

### Components Directory:
- `client/components/Header.tsx`
- `client/components/ScenarioControls.tsx`
- `client/components/SimulationCanvas.tsx`
- `client/components/PlaybackControls.tsx`
- `client/components/VehicleHUD.tsx`
- `client/components/HardwareHUD.tsx`
- `client/components/ManifestCard.tsx`
- `client/components/HarnessView.tsx`
- `client/components/InvestigatorView.tsx`


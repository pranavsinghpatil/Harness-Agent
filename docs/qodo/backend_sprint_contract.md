# Backend Sprint Quality Contract

This short backend sprint keeps the TrueForge submission path bounded and
reviewable. Changes are split into independent branches and pull requests:

- The investigation close-loop branch owns diagnosis, patch approval,
  verification, regression, and the structured conclusion.
- The investigation stream branch owns immediate canonical WebSocket delivery.

Both branches start from the latest merged `main`. Every PR must receive a
Qodo review, archive all findings under `docs/qodo/`, apply or justify every
finding, run the required tests, and post the resolver summary before merge.

The implementation intentionally uses the existing bounded worker pool,
in-process queues, deterministic RunManager, and TrueForge sandbox. A message
broker or high-rate telemetry platform is outside the submission-time scope.

The completion bar for the backend is an observable chain:

`PLAN -> RUN -> OBSERVE -> HYPOTHESIZE -> DIAGNOSE -> PATCH -> APPROVE -> VERIFY -> REGRESS -> CONCLUDE`

Frontend clients should consume the investigation snapshot and canonical
investigation WebSocket. The legacy `/ws/live/{scenario_id}` stream remains
available for standalone sandbox visualization.

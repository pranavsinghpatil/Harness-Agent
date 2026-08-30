# Investigation Session Contract

The backend exposes one persistent in-process session per autonomous
investigation. `POST /api/harness/investigations` returns `202 Accepted` with an
`investigation_id` immediately; the deterministic System 2 investigator then
runs in a background worker.

## Lifecycle API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/harness/investigations` | Create and start an investigation session. |
| `GET /api/harness/investigations/{investigation_id}` | Read current status, result, and error state. |
| `POST /api/harness/investigations/{investigation_id}/approval` | Approve or reject the pending patch and resume the close loop. |
| `GET /api/harness/investigations/{investigation_id}/events` | Poll the ordered canonical event history. |
| `WS /ws/investigations/{investigation_id}` | Replay existing events, then stream new events until terminal state. |

## Canonical Events

Session lifecycle events are represented by `HarnessEvent` and include:

`INVESTIGATION_CREATED`, `INVESTIGATION_STARTED`, `EXPERIMENT_PLANNED`,
`EXPERIMENT_STARTED`, `EXPERIMENT_COMPLETED`, `EVIDENCE_CAPTURED`,
`HYPOTHESIS_UPDATED`, `FALSIFICATION_PROPOSED`, `DECISION_RECORDED`,
`NEXT_EXPERIMENT_SELECTED`, `INVESTIGATION_COMPLETED`, and
`INVESTIGATION_FAILED`. Repair sessions additionally emit
`DIAGNOSIS_COMPLETED`, `PATCH_GENERATED`, `PATCH_APPROVAL_REQUESTED`,
`PATCH_APPROVED` or `PATCH_REJECTED`, verification, regression, and conclusion
events.

Every event carries the stable `investigation_id`, source, severity, unique
`event_id`, and structured payload. Experiment lifecycle and execution events
carry first-class `experiment_id`, `evaluation_id`, `run_id`, and `episode_id`
fields; events for a failed pre-evaluation setup may leave those execution
identifiers empty. The WebSocket stream includes the scheduler, perception,
compute, observation, controller, command, and actuator events emitted by
System 1, not only the System 2 lifecycle events. The current store is
process-local and thread-safe; the event and session contracts are deliberately
independent of persistence technology so a database-backed repository can
replace it later.

## Session State

`GET /api/harness/investigations/{investigation_id}` exposes both lifecycle
metadata and a compact control-plane view for the dashboard:

- `current_phase` and `current_experiment` identify the planner's pending work.
- `completed_experiments` and `budget_remaining` expose progress and admission
  to the configured experiment budget.
- `active_hypothesis` and `leading_hypothesis` expose the current belief state.
- `latest_decision` and `latest_failure` expose the newest decision trace and
  failed experiment outcome without requiring clients to parse the full result.
- `phase` reports the close-loop state; repair snapshots include `diagnosis`,
  `patch`, `approval`, `verification`, `regression`, and `conclusion`.

The snapshot is serialized from an immutable investigator result snapshot under
the session lock. This prevents concurrent REST polling from observing a
half-mutated investigator result while a worker publishes an event.

## Execution Capacity and Retention

The process-local store uses a bounded worker pool and bounded admission queue.
When capacity is exhausted, a newly created session is explicitly marked
`FAILED` with an overload error rather than creating an unbounded thread or
silently dropping work. Completed and failed sessions are retained for a
configurable TTL and LRU session bound. Eviction also releases evaluations
owned by the session from `RunManager`.

LRU recency is updated whenever a retained session is successfully read through
the store. Evaluation ownership is recorded immediately after creation, so a
candidate that fails during execution or finalization is cleaned up as well.

The WebSocket subscription snapshots history and registers its live queue under
one lock. Terminal events are therefore replayed or delivered exactly once
from the session event history, even when completion races with connection
setup.

Clients may provide `max_sim_time` in the creation request to bound each
experiment's simulation duration in seconds. The default remains the duration
declared by the selected scenario.

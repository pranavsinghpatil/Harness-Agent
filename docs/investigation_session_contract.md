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
| `GET /api/harness/investigations/{investigation_id}/events` | Poll the ordered canonical event history. |
| `WS /ws/investigations/{investigation_id}` | Replay existing events, then stream new events until terminal state. |

## Canonical Events

Session lifecycle events are represented by `HarnessEvent` and include:

`INVESTIGATION_CREATED`, `INVESTIGATION_STARTED`, `EXPERIMENT_PLANNED`,
`EXPERIMENT_STARTED`, `EXPERIMENT_COMPLETED`, `EVIDENCE_CAPTURED`,
`HYPOTHESIS_UPDATED`, `FALSIFICATION_PROPOSED`, `DECISION_RECORDED`,
`NEXT_EXPERIMENT_SELECTED`, `INVESTIGATION_COMPLETED`, and
`INVESTIGATION_FAILED`.

Every event carries the stable `investigation_id`, source, severity, event ID,
and structured payload. The current store is process-local and thread-safe;
the event and session contracts are deliberately independent of persistence
technology so a database-backed repository can replace it later.

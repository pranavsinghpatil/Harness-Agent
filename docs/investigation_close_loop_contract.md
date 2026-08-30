# Investigation Close-Loop Contract

The investigation session is the System 2 owner of the bounded
Discover -> Diagnose -> Repair -> Approve -> Verify -> Regress workflow. The
virtual hardware sandbox remains the execution substrate and emits the same
canonical `HarnessEvent` records used by the investigator.

## Session phases

`INVESTIGATING` runs the planner. A failed retained baseline moves through
`DIAGNOSING`, `PATCH_PROPOSED`, and `AWAITING_APPROVAL`. The approval endpoint
accepts `APPROVE` or `REJECT`; approval runs `VERIFYING` and `REGRESSING` in a
bounded in-process worker. Safe investigations skip repair and complete with a
`PROVEN_SAFE` conclusion.

## Approval API

`POST /api/harness/investigations/{investigation_id}/approval`

```json
{
  "patch_id": "patch_1234",
  "decision": "APPROVE",
  "reviewed_by": "frontend-or-agent-id",
  "reason": "Evidence supports the proposed failsafe"
}
```

The response is the same session snapshot returned by the status endpoint. The
snapshot includes `diagnosis`, `patch`, `approval`, `verification`,
`regression`, and a structured `conclusion` with limitations and evidence
links. A stale patch ID returns `422`; a session outside the approval phase
returns `409`.

## Streaming events

The canonical investigation WebSocket streams the approval and repair events:
`DIAGNOSIS_COMPLETED`, `PATCH_GENERATED`, `PATCH_APPROVAL_REQUESTED`,
`PATCH_APPROVED`, `PATCH_REJECTED`, `VERIFICATION_PASSED`,
`VERIFICATION_FAILED`, `REGRESSION_STARTED`, `REGRESSION_COMPLETED`, and
`CONCLUSION_RECORDED`, along with all System 1 execution events. The stream
waits asynchronously on the in-process subscription queue; it does not require
Kafka, Redis, or a polling loop.

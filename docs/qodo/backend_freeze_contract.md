# Backend Freeze Contract

This document records the final backend gate before frontend integration.

## Scope

- System 2 creates a bounded investigation asynchronously.
- System 2 plans an experiment and invokes System 1.
- System 1 scheduler, perception, compute, observation, controller, command,
  actuator, and safety events are forwarded into the investigation stream.
- System 2 captures evidence, updates hypotheses, records a decision, and
  selects the next experiment.
- REST event history and WebSocket replay/live delivery expose the same ordered
  canonical events.

## Provenance Invariant

Every event has a unique `event_id` and `investigation_id`. Events emitted for
an experiment have first-class `experiment_id`, `evaluation_id`, `run_id`, and
`episode_id` values so a frontend or TrueForge MCP consumer can trace a
decision back to the physical simulation execution.

## Verification

`tests/test_backend_investigation_e2e.py` exercises the real FastAPI REST and
WebSocket endpoints, validates the scheduler-to-actuator ordering, checks
provenance identity, and compares streamed history with the polling endpoint.

Qodo review findings for the resulting pull request must be archived here or
in a PR-specific document under `docs/qodo/` before that pull request is
merged.

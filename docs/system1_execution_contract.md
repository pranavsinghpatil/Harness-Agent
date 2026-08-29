# System 1: Virtual Hardware Sandbox Contract

System 1 is the deterministic execution laboratory for the TrueForge agent
harness. It executes a supplied experiment against a virtual hardware and
world configuration; it does not choose what to investigate or interpret the
result.

## Responsibilities

- Execute the same experiment reproducibly from a seed and scenario.
- Model world state, sensing, transport, compute scheduling, and actuation.
- Emit timestamped telemetry, safety events, and a replayable run manifest.
- Evaluate ground-truth safety invariants independently of the target agent.

## Boundary

System 1 accepts a declarative experiment containing a baseline scenario and a
set of perturbation values. It returns an immutable run result containing the
manifest identifier, safety verdict, telemetry references, and replay data.
System 1 must not contain planner logic, hypothesis selection, or repair
decisions; those belong to System 2.

## Initial perturbation dimensions

The first end-to-end investigation path should use three dimensions:

- sensor observation latency
- virtual CPU availability and scheduling delay
- actuator effectiveness or delay

Additional fault dimensions can be added behind the same experiment contract
after the PLAN -> RUN -> OBSERVE -> VERIFY loop is working end to end.

## Invariants

- A fixed seed and identical input produce a bit-equivalent replay result.
- Safety verdicts use ground truth, not the target agent's own observations.
- Every emitted event identifies its experiment and simulation timestamp.
- Failed execution is represented as structured evidence, never as an opaque
  exception string at the API boundary.

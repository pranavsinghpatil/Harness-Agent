# System 2: Autonomous Investigator Contract

System 2 is the decision-making layer of the TrueForge agent harness. It
receives an objective, safety invariants, a perturbation space, and an
experiment budget. It decides what to run next, interprets System 1 evidence,
and drives the investigation loop.

## Investigation loop

```text
PLAN -> RUN -> OBSERVE -> HYPOTHESIZE -> TEST -> DIAGNOSE -> REPAIR -> VERIFY
```

The first implementation should prove this loop with a small search space:
sensor latency, CPU availability, and actuator effectiveness or delay.

## Responsibilities

- Select experiments from declared perturbation dimensions rather than from a
  hardcoded scenario list.
- Compare baseline and perturbed runs using safety verdicts and telemetry.
- Track hypotheses, supporting evidence, disproving evidence, and confidence.
- Request a repair only when the causal evidence supports an intervention.
- Replay the original experiments after repair and report what is proven and
  what remains untested.

## Boundary

System 2 owns planning, causal interpretation, repair proposals, and
verification policy. It must call System 1 through an explicit experiment
contract and must not reach into sandbox internals to change state directly.

Every investigation result should be inspectable as structured data containing
the objective, experiments, evidence links, hypothesis history, diagnosis,
repair result, and verification summary.

Each executed experiment also emits a safe decision trace. It records the
experiment phase, action class, hypotheses available before execution,
post-observation belief updates, refuted historical hypotheses, estimated
information value, outcome classification, evidence observation, decision
rationale, and the planner's actual next candidate or terminal state. This is an
audit record for frontend and MCP consumers, not private model reasoning.

## Reliability rules

- Baseline behavior is measured before perturbation search begins.
- The configured experiment budget is enforced by the orchestrator.
- A failed or unavailable run is evidence with a status, not an implicit pass.
- A repair is never reported as proven without replaying the relevant failing
  conditions and checking the safety invariants again.
- Conditions outside the executed perturbation space remain explicitly
  unproven.

# System 1 Execution Provenance

System 1 now exposes the scheduler-controlled execution chain through the
canonical `HarnessEvent` callback:

```text
sensor sample
  -> packet delivery
  -> perception task scheduled
  -> compute started
  -> perception completed
  -> observation available
  -> controller task scheduled
  -> controller completed
  -> controller command issued
  -> actuator command applied
```

Controller and perception work are represented as `ComputeTask` instances and
are admitted, started, completed, or deadline-missed by the virtual edge
scheduler. Packets remain pending until their perception task completes; the
target agent cannot consume them early. Each completed perception task creates
an immutable `ObservationState` with an observation ID, creation and
availability timestamps, sensor IDs, source packet IDs, and age at the next
controller decision.

Every task carries `input_timestamp`, `deadline`, `started_at`, and
`completed_at` where applicable. Queue admission failure is represented by
`TASK_REJECTED`; it is distinct from `DEADLINE_MISSED`, which is emitted only
when the scheduler marks a specific task late. A controller task that misses
its deadline produces no new command.

`ACTUATOR_APPLIED` is emitted once per command newly removed from the actuator
queue, rather than once per simulation tick while the command remains active.

This keeps scheduler pressure, transport timing, controller decisions, and
physical actuation distinguishable in the evidence stream used by System 2.

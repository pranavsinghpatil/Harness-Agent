# System 1 Execution Provenance

System 1 now exposes the scheduler-controlled execution chain through the
canonical `HarnessEvent` callback:

```text
sensor sample
  -> packet delivery
  -> compute task scheduled
  -> compute started
  -> compute completed
  -> controller command issued
  -> actuator command applied
```

Controller and perception work are represented as `ComputeTask` instances. The
virtual edge scheduler controls whether each task completes in the current
simulation slice. Every task carries `input_timestamp`, `deadline`,
`started_at`, and `completed_at` where applicable. A controller task that does
not complete in its deadline emits `DEADLINE_MISSED` and no new command is
issued for that tick.

This keeps scheduler pressure, transport timing, controller decisions, and
physical actuation distinguishable in the evidence stream used by System 2.

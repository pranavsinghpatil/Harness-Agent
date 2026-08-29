# Qodo Review Findings - PR #9 - Round 1

- PR: https://github.com/pranavsinghpatil/Harness-Agent/pull/9
- Branch: `feature/system-1-perturbation-space`
- Review: `qodo-code-review[bot]`, 2026-08-29
- Test evidence: `pytest tests/ -v` could not run in this environment because Python and pytest are unavailable; `git diff --check` is used as static verification.

## Findings

1. **Experiment locals lack annotations** - Added explicit annotations for the new experiment-model locals.
2. **Test locals lack annotations** - Added explicit annotations for test fixtures and serialized override data.
3. **`build_fault_overrides` docs omit contract** - Documented inputs, output ordering/shape, baseline omission, and validation errors.
4. **CPU utilization is overstated** - Scheduler telemetry now records compute consumed over nominal effective capacity, so idle reduced availability reports zero utilization.
5. **Removed fault remains applied** - Added active-fault cleanup and call it before replacing a scenario schedule.
6. **Invalid dimensions silently no-op** - Added a shared runtime fault-parameter registry and validate perturbation dimensions against it.
7. **Infinite bounds bypass validation** - Reject non-finite bounds, timing values, and selected values.

All seven findings are addressed in the remediation commit for this round, with focused regression tests for the behavioral fixes.

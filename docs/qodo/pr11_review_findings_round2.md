# Qodo Review Findings - PR #11 - Round 2

- PR: https://github.com/pranavsinghpatil/Harness-Agent/pull/11
- Branch: `feature/integration-autonomous-investigator`
- Review: `qodo-code-review[bot]`, 2026-08-29
- Test evidence: `pytest tests/ -v` could not run in this environment because Python and pytest are unavailable; `git diff --check` is used as static verification.

## Findings

1. **Unavailable CPU counts as used** - Integrated the consumed-compute scheduler correction from System 1.
2. **Hardware faults survive replacement** - Active overload tasks and thermal spikes are reverted before schedule replacement.
3. **New locals lack annotations** - Added explicit annotations for request normalization, investigator status state, scheduler results, ledger records, and regression-test locals.
4. **Registry rejects valid transports** - Transport fault validation now uses the runtime's `transport.*` target family.
5. **Rejected limit corrupts status** - Invalid run limits are rejected before investigator state is updated.

All second-pass findings are addressed in this remediation commit, with focused regression tests for hardware cleanup and rejected limits. The existing findings for task completion, boundary isolation, whitespace objectives, and short-run status remain covered by the first remediation round.

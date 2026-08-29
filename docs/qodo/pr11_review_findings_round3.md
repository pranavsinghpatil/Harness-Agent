# Qodo Review Findings - PR #11 - Round 3

- PR: https://github.com/pranavsinghpatil/Harness-Agent/pull/11
- Branch: `feature/integration-autonomous-investigator`
- Review: `qodo-code-review[bot]`, 2026-08-29
- Test evidence: `pytest tests/ -v` could not run in this environment because Python and pytest are unavailable; `git diff --check` is used as static verification.

## Findings

1. **Unavailable CPU counts as used** - Scheduler utilization now accumulates only compute applied to queued work; unavailable capacity is not treated as consumption.
2. **No-op limit downgrades completion** - Investigator status now records whether the latest accepted limit actually stopped work, preserving the existing status on no-op calls.

Both third-pass findings are addressed in this remediation commit with idle scheduler and repeated-limit regression coverage.

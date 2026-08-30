# PR #22 Qodo Review Findings - Round 2

- **PR:** https://github.com/pranavsinghpatil/Harness-Agent/pull/22
- **Branch:** `feature/investigation-close-loop`
- **Findings:** 11 total; all resolved in this remediation pass.
- **Verification:** `uv run --no-sync pytest tests/ -q` -> 100 passed, 1 existing warning.

## Resolutions

1. **Approval locals lack annotations**, **Close-loop locals lack annotations**,
   **Test locals lack annotations**, and **`approve_patch` documentation omits
   contract**: added explicit local types and complete public method contracts.
2. **Incomplete runs declared safe** and **Incomplete regressions pass**: use
   the canonical completed, healthy, task-completed, zero-violation predicate.
   Bounded incomplete runs now conclude `NOT_PROVEN_SAFE`.
3. **Verification failures reported passed**: use the stored three-pillar
   verification verdict instead of checking violations alone.
4. **Conclusion drops repair evidence**: final conclusions now retain the
   causal boundary, causal chain, patch, approval, verification, regression,
   and limitations.
5. **Approval work bypasses capacity**: the session keeps its store admission
   slot through approval and schedules repair work on the same bounded executor.
6. **Approval identity is forgeable**: approval now requires a Bearer token,
   derives identity from `HARNESS_REVIEWER_ID`, and ignores client identity
   claims. Configure `HARNESS_APPROVAL_TOKEN` before enabling the route.
7. **Runtime failures misdiagnosed safe**: the causal analyzer emits a runtime
   or task-completion diagnosis for violation-free failed runs.

# Qodo PR #16 Review Findings — Round 3 Resolution

## Addressed Findings

1. **Rule 2945749 (Static Typing in Store and Tests):**
   - Added explicit static type annotations to local variables in `harness/orchestration/investigation.py` (`investigator`, `started`, `session`, `now`, `expired`, `terminal`).
   - Annotated all declared local test variables in `tests/test_investigation_session.py`.
2. **Active Sessions Store Capacity Bound:**
   - Updated `InvestigationSessionStore.create()` to guard `_max_sessions` capacity when non-terminal (`CREATED`/`RUNNING`) sessions saturate the store.
   - Added regression test `test_create_enforces_max_sessions_when_sessions_active()`.

## Verification
- Test Suite: 93/93 passing (`pytest tests/ -v`).

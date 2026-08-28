# Qodo Quality Governance & Engineering Protocols (`.ai/qodo.md`)

This document is the **immutable, permanent rule set and engineering protocol** governing all code reviews, automated quality checks, remediation workflows, coding standards, and documentation procedures powered by **Qodo AI** for the **Harness-Agent** project.

---

## 📜 Core Quality Invariants & Protocols

### Protocol 1: Zero-Omission Review Ingestion & Archiving
1. Whenever a Pull Request is opened or reviewed by Qodo AI, **all findings, rule violations, and inline review comments must be immediately ingested and archived in `docs/qodo/`**.
2. Never silently ignore or dismiss a Qodo finding. Every single finding must either have:
   - An explicit **Code Fix Implementation** verified with automated unit/regression tests, OR
   - A documented **Engineering Justification** in `docs/qodo/pr<N>_resolution.md`.
3. Every resolution document must include an explicit **Metadata Header** linking it directly to the corresponding GitHub PR URL, branch name, and test run evidence.

---

### Protocol 2: Public API & Docstring Completeness (Rule 2945750)
Every non-trivial public class, function, method, endpoint, and simulator step handler **must** contain comprehensive, structured docstrings formatted with:
- **Summary:** Single-sentence high-level purpose.
- **Parameters (`Args`):** Explicit type and physical semantic meaning of every parameter (units, ranges, constraints).
- **Return Values (`Returns`):** Exact return type, tuple unpacking breakdown, and state meanings.
- **Side Effects / State Mutations:** Explicitly state if internal state, clocks, queues, or hardware metrics are mutated.
- **Error Modes / Exceptions (`Raises`):** Document all thrown exceptions and early-return conditions (e.g. non-positive $\Delta t \le 0$).

---

### Protocol 3: Function Length Limit & Modularity Standard (50-Line Rule)
1. **Strict 50-Line Maximum:** No method or function body (excluding comments and docstrings) may exceed **50 lines**.
2. **Single Responsibility Decomposition:** Complex methods performing multiple pipeline steps (e.g., physics integration, sensor sampling, fault routing, safety evaluation) must be decomposed into private helper methods (e.g., `_update_steering`, `_process_task_queue`, `_check_collision`).

---

### Protocol 4: Code Cleanliness & Zero Redundant Comments
1. **No Redundant Comments:** Never write comments that merely rephrase immediately following code (e.g., `# Register routers` above `app.include_router()`).
2. **"Why", Not "What":** Comments must only explain non-obvious design rationales, mathematical approximations, physical constraints, or edge-case handling.

---

### Protocol 5: Pre-Commit Automated Verification Gate
No remediation commit or feature push may occur without passing the full verification test suite:
```bash
# 1. Run all unit and integration tests
pytest tests/ -v

# 2. Verify bit-exact trace determinism
pytest tests/test_determinism.py -v

# 3. Verify showcase safety scenarios
pytest tests/test_showcase_scenario.py -v
```

---

### Protocol 6: Qodo Agent Skills & PR Remediation Flow
When fixing review issues:
1. **Install Skills (One-time):**
   ```bash
   npx skills add qodo-ai/qodo-skills/skills
   ```
2. **Invoke Remediation:**
   ```bash
   $qodo-pr-resolver Resolve the Qodo findings for the PR on my current branch.
   ```
3. **Execute Agent Prompts:**
   Implement fixes by following the exact `Agent Prompt` specifications provided in Qodo's review findings.
4. **Oscillation Guard:**
   Track previous review decisions across rounds to prevent contradictory flip-flops.
5. **Post Fix Summary & Reply:**
   Post `## Qodo Fix Summary — Round N` on the PR and resolve inline threads.
6. **Push & Trigger Re-Review:**
   ```bash
   git push origin <branch-name>
   gh pr comment <PR_NUMBER> --body "/agentic_review"
   ```

---

## 📁 Repository Documentation Index (`docs/qodo/`)

All review logs, findings catalogs, remediation proofs, and skill guides are stored in `docs/qodo/`:

- [`docs/qodo/README.md`](file:///D:/GitRepo/harness/docs/qodo/README.md) — Master PR Index & Quality Governance Overview
- [`docs/qodo/pr2_resolution.md`](file:///D:/GitRepo/harness/docs/qodo/pr2_resolution.md) — PR #2: Complete Resolution Evidence & Test Logs
- [`docs/qodo/pr2_review_findings.md`](file:///D:/GitRepo/harness/docs/qodo/pr2_review_findings.md) — PR #2: Catalog of 28 Findings & 33 Inline Threads
- [`docs/qodo/remediation_plan.md`](file:///D:/GitRepo/harness/docs/qodo/remediation_plan.md) — PR #2: Itemized Engineering Fix Plan
- [`docs/qodo/skills_workflow_guide.md`](file:///D:/GitRepo/harness/docs/qodo/skills_workflow_guide.md) — Qodo Agent Skills Installation & Workflow Guide

# Qodo Quality Governance & Engineering Protocols (`.ai/qodo.md`)

This document is the **immutable, permanent rule set and protocol** governing all code reviews, automated quality checks, remediation workflows, and documentation standards powered by **Qodo AI** for the **Harness-Agent** project.

---

## 📜 Core Quality Invariants & Protocols

### Protocol 1: Zero-Omission Review Ingestion
1. Whenever a PR is opened or reviewed by Qodo AI, **all findings, rule violations, and inline review comments must be immediately ingested and documented in `.ai/qodo/`**.
2. Never silently ignore or dismiss a Qodo finding. Every finding must either have an explicit **Fix Implementation** or a **Documented Engineering Justification** in `.ai/qodo/decisions/`.

---

### Protocol 2: Public API & Docstring Completeness (Rule 2945750)
Every non-trivial public class, function, method, endpoint, and simulator step handler **must** contain comprehensive, structured docstrings formatted with:
- **Summary:** Single-sentence purpose.
- **Parameters (`Args`):** Explicit type and physical semantic meaning of every parameter (units, ranges, constraints).
- **Return Values (`Returns`):** Exact return type, tuple unpacking breakdown, and state meanings.
- **Side Effects / State Mutations:** Explicitly state if internal state, clocks, queues, or hardware metrics are mutated.
- **Error Modes / Exceptions (`Raises`):** Document all thrown exceptions and early-return conditions (e.g. non-positive $\Delta t \le 0$).

---

### Protocol 3: Code Cleanliness & Comment Hygiene
1. **No Redundant Comments:** Never write comments that merely rephrase immediately following code (e.g., `# Register routers` above `app.include_router()`).
2. **"Why", Not "What":** Comments must only explain non-obvious design rationales, mathematical approximations, physical constraints, or edge-case handling.

---

### Protocol 4: Pre-Commit Automated Verification Gate
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

### Protocol 5: Qodo Agent Skills & PR Remediation Flow
When fixing review issues:
1. **Install Skills (One-time):**
   ```bash
   npx skills add qodo-ai/qodo-skills/skills
   ```
2. **Invoke Remediation:**
   ```bash
   $qodo-pr-resolver Resolve the Qodo findings for the PR on my current branch.
   ```
3. **Push Remediation Commits:**
   ```bash
   git push origin <branch-name>
   ```
4. **Trigger Follow-Up Review:**
   Post a comment on the PR:
   ```
   /agentic_review
   ```
5. **Update Knowledge Base:**
   Archive all resolved threads and update `.ai/qodo/` tracking files.

---

## 📁 Modular Directory Map (`docs/qodo/`)

- [`docs/qodo/README.md`](file:///D:/GitRepo/harness/docs/qodo/README.md) — Review Governance & Archives Overview
- [`docs/qodo/pr2_review_findings.md`](file:///D:/GitRepo/harness/docs/qodo/pr2_review_findings.md) — Comprehensive PR #2 Findings & Agent Prompts
- [`docs/qodo/remediation_plan.md`](file:///D:/GitRepo/harness/docs/qodo/remediation_plan.md) — Itemized Engineering Fix Plan & Decision Log
- [`docs/qodo/skills_workflow_guide.md`](file:///D:/GitRepo/harness/docs/qodo/skills_workflow_guide.md) — Qodo Agent Skills Installation & Workflow Guide


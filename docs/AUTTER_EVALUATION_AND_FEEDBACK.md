# Autter Exploration, Technical Evaluation & Feedback

**Candidate:** Pranav Patil  
**Role:** Backend Engineer (Autter Harbor)  
**Date:** October 2026  
**Artifact Repository:** `harness` (`reimagine/universal-failure-harness`)

---

## 1. Product Experience & Onboarding (`app.autter.dev`)

### Exploration Summary
Autter approaches code intelligence and software reliability with a distinctive angle: closing the loop between AI coding agent provenance at write time (`autter-cli`), runtime failure signals in production (`autter-runtime`), and automated sandbox verification with self-repairing test suites.

Connecting a repository via the Autter GitHub App creates an immediate link between PR diffs, test missions, and runtime error telemetry.

### Two Things to Do Differently or Improve

#### 1. Explicit Local-First Sandbox Verification Before Opening Fix PRs
* **Current Experience:** When Autter Runtime maps an exception or failing test, it orchestrates an automated fix flow. However, developers frequently experience anxiety over automated PRs opened without an inspectable, reproducible test artifact attached to the PR description.
* **Suggested Improvement:** Introduce a **Portable Failure Reproducer Artifact**. Before opening a fix PR, generate a deterministic repro test fixture (e.g. `repro_incident_xxx.json` or standalone test script) that developers can execute locally in one command (`autter test --reproduce <id>`). If the developer can replay the exact failure locally with 100% determinism, confidence in the fix PR surges.

#### 2. Granular Telemetry Scoping & Environment Noise Decoupling in Repository Onboarding
* **Current Experience:** When connecting a repository, onboarding focuses heavily on repository-level permissions and broad webhook listeners. For teams running microservices or monorepos, noise from high-frequency non-critical client warnings can flood the failure triage view.
* **Suggested Improvement:** Add an interactive **Incident Telemetry Filter & Blast-Radius Rulebook** during onboarding. Allow engineering leads to set minimum error frequency gates, distinct service boundaries, and PII masking presets upfront before ingesting live traffic into ClickHouse.

---

## 2. Technical Evaluation: `autter-cli` & `autter-runtime`

### A. Autter CLI (`autter-cli`)
* **Architecture:** Written in Rust (~93%), fast execution, binary footprint ~4 MB. Uses `git notes` (`refs/notes/autter`) to attach line-level AI attribution (agent, model, prompt) without modifying Git commit SHAs or history.
* **What Stood Out & DX Observations:**
  1. **Git Notes Push Ergonomics:** By default, standard `git push` does not push `refs/notes/*` unless explicitly configured via `git push origin refs/notes/autter` or adding `remote.origin.push = refs/notes/*:refs/notes/*` to `.git/config`. If developers or CI runners forget this configuration, AI authorship attribution is lost when moving between machines.  
     *Recommendation:* In `autter onboard`, offer an automatic opt-in git config helper (`autter config --sync-notes`) or a pre-push hook that ensures notes refs are synced seamlessly alongside commits.
  2. **Rebase & Interactive Squash Edge Cases:** While Git Notes survive standard commits, complex interactive rebases (`git rebase -i` with line-level conflict resolution or squashes) can cause attribution orphan drift where notes remain attached to rewritten or dropped commit SHAs. Adding a background reconciler during `autter checkpoint` makes authorship tracking impervious to rebases.

### B. Autter Runtime (`autter-runtime`)
* **Architecture:** Composed of lightweight packages:
  - `@autter/runtime-browser`: Zero-dependency, <5 KB client tracker.
  - `@autter/runtime-node`: OTel auto-instrumentation with PII attribute scrubbing.
  - `@autter/runtime-next`: Unified server/client tracker using same-origin relay endpoints to safeguard API ingest keys.
  - `@autter/otlp-ingester`: Ingestion collector pipeline writing normalized events into ClickHouse.
* **What Stood Out & DX Observations:**
  1. **Correlating OTel Traces with Deterministic Reproduction:** Runtime telemetry captures rich contextual metadata (request path, status code, exception type, stack trace, OTel spans). However, transforming that raw span into an executable test case requires guessing environment parameters and state.
  2. **Minimal Failure Condition Isolation:** Production failures often happen under multi-variable noise (e.g., latency spikes, payload flags, cache misses). Having a backend engine that systematically delta-reduces the perturbation space to find the *minimal causal conditions* (e.g., `cart_total == undefined AND discount_path == true`) turns vague production traces into precise unit test assertions.

---

## 3. What I Built Today: Universal Failure Harness

To test this thesis hands-on, I reimagined my `harness` repository into **Universal Failure Harness**: a local-first engine that ingests external runtime signals (like Autter Runtime incidents), deterministically replays them, minimizes failure conditions via coordinate search, and proves fixes using cryptographic evidence bundles.

* **Replay Engine:** `harness replay case.yaml` verifies failure repeatability (e.g., 5/5 runs, 100% determinism) with SHA-256 trace verification.
* **Condition Minimizer:** `harness minimize case.yaml` searches multi-dimensional parameter spaces to isolate the exact minimal failure boundary.
* **Verification Engine:** `harness verify case.yaml --candidate <fix>` proves that a fix resolves the target defect while preventing regressions across nominal suites.
* **Autter Adapter:** Ingests Autter Runtime error payloads directly into deterministic failure cases (`harness import --source autter incident.json`).

---

## 4. Short Note for the Autter Harbor Team

```text
Hi Capt. Patch and the Autter Team,

I spent time exploring Autter, walking through onboarding at app.autter.dev, connecting repositories, and inspecting the architecture of autter-cli (Rust + git notes) and autter-runtime (OTel + Next.js relay + ClickHouse ingester).

Two immediate observations on the product and runtime flow:
1. Product/Onboarding: The bridge between runtime incidents and automated fix PRs becomes significantly more trustworthy if each fix PR links a deterministic, downloadable failure reproducer that developers can execute and verify locally with a single CLI command before merging.
2. CLI/Runtime DX: Using git notes for AI authorship is an elegant, non-invasive choice that preserves commit SHAs, but managing note synchronization across remotes (`refs/notes/autter`) and rebasing workflows needs automated git hook ergonomics to prevent attribution loss. Furthermore, turning OTel production error traces into minimal, reproducible test fixtures requires stripping away non-essential runtime variables.

Where I could help you on the backend team:
I would love to help build and scale the automated reproduction and verification pipeline: specifically taking incoming OTel error events from autter-runtime, delta-reducing noisy runtime parameters down to minimal failure conditions, and generating self-contained sandbox tests that mechanically prove an automated fix works before a PR is opened.

Looking forward to discussing this on a call!

Cheers,
Pranav Patil
```

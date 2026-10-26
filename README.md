# Harness: Universal Failure Reproduction & Verification Engine

[![Tests](https://img.shields.io/badge/tests-15%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)]()

A local-first, domain-independent reliability and failure analysis platform. Given an unexpected software exception, AI agent failure, or simulation breach, Harness turns that failure into a portable, content-addressed experiment artifact, isolates the minimal failure conditions, and cryptographically proves whether a candidate fix removes the failure without regression.

> [!NOTE]
> **Branch Architecture & Historical Preservation:**  
> This branch (`reimagine/universal-failure-harness`) is a research-grade re-architecture that abstracts the core determinism and fault-injection capabilities of the project into a universal, domain-agnostic engine. The original hackathon hardware-simulation codebase remains fully preserved on `main`.

---

## The Core Problem

When an incident occurs in production, CI, or an AI agent task, teams face three hard questions:
1. **Can I reproduce the failure deterministically?** (Or is it flaky, timing-dependent, or unrepeatable?)
2. **What is the smallest condition required to cause it?** (Or is the failure buried in hundreds of noisy environment variables?)
3. **Can I prove that a proposed fix actually works without introducing regressions?**

Harness transforms messy failures into portable, verifiable proof objects:

```text
Any System (AI Agent, Backend API, Simulation, Pipeline)
                        │
                        ▼
            ┌───────────────────────┐
            │ Universal FailureCase │ (SHA-256 content-addressed)
            └───────────┬───────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    [harness replay]        [harness minimize]
  Deterministic Replay      Delta & Boundary Search
  (e.g., 5/5 trials)        (removes non-essential noise)
            │                       │
            └───────────┬───────────┘
                        ▼
                [harness verify]
           Baseline vs Candidate Proof
          + Zero-Regression Evaluation
                        │
                        ▼
            ┌───────────────────────┐
            │    Evidence Bundle    │
            │  manifest.json (SHA)  │
            │  report.md (Markdown) │
            └───────────────────────┘
```

---

## Key Capabilities

### 1. Universal FailureCase Contract
Domain-agnostic specification defining execution commands, environment parameters, injected perturbations, and expected failure signatures. Every case generates an immutable SHA-256 digest:

```yaml
version: "1.0"
id: "checkout-type-error"
name: "Checkout Service TypeError on Missing Cart Total"
source:
  system: "autter_runtime"
  reference: "commit-8f3c2a1"
execution:
  command: "python -m examples.fixtures.payment_service"
  timeout_seconds: 10.0
perturbations:
  discount_path: true
  cart_total_present: false
  timeout_ms: 500
  latency_ms: 120
expected:
  outcome: "failure"
  exit_code: 1
  error_match: "TypeError: Cannot read properties of undefined"
```

### 2. Deterministic Replay Engine (`harness replay`)
Runs multiple trials in an isolated process sandbox to confirm repeatability and calculate bit-exact execution trace hashes:

```bash
$ harness replay examples/cases/checkout_case.yaml --trials 5

[1/2] Loading FailureCase: checkout-type-error ('Checkout Service TypeError on Missing Cart Total')
      Source: autter_runtime (digest: 73730b89c066...)
[2/2] Running 5 deterministic replay trials...

============================================================
REPLAY VERDICT: DETERMINISTIC_REPRODUCTION
============================================================
Reproduction:    5/5 (100%)
Deterministic:   True
Dominant Hash:   575a374d35744d24127e...
Mean Duration:   112.4 ms
------------------------------------------------------------
  Trial #01 (seed=42): [REPRODUCED] [failure] in 121.0ms
  Trial #02 (seed=42): [REPRODUCED] [failure] in 108.2ms
  Trial #03 (seed=42): [REPRODUCED] [failure] in 109.5ms
  Trial #04 (seed=42): [REPRODUCED] [failure] in 111.1ms
  Trial #05 (seed=42): [REPRODUCED] [failure] in 112.3ms
============================================================
```

### 3. Failure Condition Minimization (`harness minimize`)
Automates delta reduction and binary coordinate search over the perturbation space, discarding irrelevant variables and discovering the exact numerical boundary where the system flips from PASS to FAIL:

```bash
$ harness minimize examples/cases/checkout_case.yaml

[1/3] Loading FailureCase: checkout-type-error
[2/3] Searching parameter space (4 perturbations)...

============================================================
FAILURE CONDITION MINIMIZED
============================================================
Search Iterations: 5
Confidence:        98%
Removed Params:    timeout_ms, latency_ms
------------------------------------------------------------
Minimal Perturbation Boundary:
  discount_path       : True (essential)
  cart_total_present  : False (essential)
============================================================
```

### 4. Candidate Fix Verification & Regression Gate (`harness verify`)
Executes the baseline against candidate fixed code under identical failure conditions and runs nominal regression suites:

```bash
$ harness verify examples/cases/checkout_case.yaml --candidate "python -m examples.fixtures.payment_service_fixed"

[1/3] Evaluating Baseline: python -m examples.fixtures.payment_service
[2/3] Evaluating Candidate: python -m examples.fixtures.payment_service_fixed

============================================================
[OK] VERIFICATION: VERIFIED
============================================================
Original Failure:  Baseline=FAILURE  ->  Candidate=SUCCESS
Failure Resolved:  YES
Regression Suite:  1/1 PASSED
------------------------------------------------------------
  [PASS] checkout-type-error-nominal-control: success (115.4ms)
============================================================
```

### 5. Portable Cryptographic Evidence Bundles (`harness report`)
Produces an audited, self-contained evidence directory anchored by `manifest.json` with SHA-256 checksums:

```bash
$ harness report examples/cases/checkout_case.yaml --candidate "python -m examples.fixtures.payment_service_fixed"

[+] Portable evidence bundle generated at:
  ./artifacts/evidence/evidence-c05ca1c9/
```

Bundle directory layout:
```text
artifacts/evidence/evidence-c05ca1c9/
├── case.yaml           # Canonical FailureCase contract
├── manifest.json       # Cryptographic hashes of all artifacts
├── replay.json         # Trial timings, seeds, trace hashes
├── minimized.json      # Minimal boundary and search history
├── verification.json   # Baseline vs candidate execution logs
└── report.md           # Markdown verification report
```

### 6. External Telemetry Ingestion (Autter Runtime & TrueForge)
Ingest real-world error incidents directly from telemetry SDKs:

```bash
# Ingest an Autter Runtime OpenTelemetry incident JSON
$ harness import --source autter examples/cases/autter_incident.json --out ./cases/imported_autter.yaml
```

---

## Interactive Streamlit Laboratory

Harness includes an interactive visual control room for exploring failure cases, live replaying trials, and inspecting parameter boundaries:

```bash
streamlit run universal_harness/ui/lab.py
```

Features:
- **Case Explorer:** Select from library cases or inspect JSON specifications.
- **Trial Visualizer:** View latency histograms and SHA-256 trace consistency.
- **Boundary Inspector:** Interactive side-by-side view of original vs minimal parameters.
- **Export Control:** Download cryptographic evidence bundles with one click.

---

## Quickstart

### Installation
```bash
# Clone and checkout the re-imagined branch
git clone https://github.com/pranavsinghpatil/harness-agent.git
git checkout reimagine/universal-failure-harness

# Install editable package
pip install -e .
```

### Run Tests
```bash
python -m pytest tests/universal
```

---

## Technical Evaluation & Autter Integration
Detailed observations on Autter onboarding, `autter-cli` (Rust/git-notes AI attribution), and `autter-runtime` (OTel collector integration) can be found in:
- [docs/AUTTER_EVALUATION_AND_FEEDBACK.md](docs/AUTTER_EVALUATION_AND_FEEDBACK.md)

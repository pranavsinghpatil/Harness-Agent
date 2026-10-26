"""Streamlit Failure Reproduction & Verification Laboratory."""

from __future__ import annotations

import json
from pathlib import Path
import streamlit as st

from universal_harness.case.loader import load_failure_case
from universal_harness.evidence.report import EvidencePackager
from universal_harness.replay.replayer import DeterministicReplayer
from universal_harness.search.minimizer import FailureMinimizer
from universal_harness.verify.comparator import VerificationEngine


def run_lab() -> None:
    st.set_page_config(
        page_title="Universal Failure Reproduction Lab",
        page_icon="🔬",
        layout="wide",
    )

    st.title("🔬 Universal Failure Reproduction & Verification Engine")
    st.caption("A domain-agnostic reliability laboratory for deterministic failure replay, boundary minimization, and candidate fix verification.")

    # Sidebar: Case Selection
    st.sidebar.header("📁 Failure Case Selection")
    cases_dir = Path("examples/cases")
    available_cases = list(cases_dir.glob("*.yaml")) + list(cases_dir.glob("*.yml"))

    case_options = {p.stem: p for p in available_cases}
    selected_name = st.sidebar.selectbox("Select Benchmark Case", list(case_options.keys()))

    if not selected_name:
        st.warning("No cases found in examples/cases.")
        return

    selected_path = case_options[selected_name]
    case = load_failure_case(selected_path)

    # Overview Card
    st.subheader(f"📌 Case: {case.name}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Case ID", case.id)
    with col2:
        st.metric("Source System", case.source.system)
    with col3:
        st.metric("Seed", str(case.environment.seed))
    with col4:
        st.metric("Perturbations", str(len(case.perturbations)))

    with st.expander("🔍 Inspect FailureCase Specification (YAML/JSON)"):
        st.code(json.dumps(case.model_dump(), indent=2), language="json")

    # Tabs for the 3 main actions
    tab_replay, tab_minimize, tab_verify = st.tabs([
        "🔁 Deterministic Replay",
        "📉 Failure Minimization",
        "🛡️ Candidate Verification",
    ])

    # Tab 1: Replay
    with tab_replay:
        st.markdown("### Deterministic Execution & Repeatability Proof")
        col_r1, col_r2 = st.columns([1, 3])
        with col_r1:
            trials_num = st.slider("Replay Trials", min_value=1, max_value=20, value=5)
            vary_seeds = st.checkbox("Vary PRNG Seeds", value=False)
            btn_replay = st.button("▶️ Execute Replay Trials", key="btn_run_replay")

        if btn_replay:
            with st.spinner("Executing replay trials in isolated sandbox..."):
                replayer = DeterministicReplayer()
                report = replayer.replay(case, trials=trials_num, vary_seeds=vary_seeds)

            if report.reproduction_rate == 1.0:
                st.success(f"✅ **FAILURE DETERMINISTICALLY REPRODUCED** ({report.reproduced_count}/{report.trials_count})")
            elif report.reproduction_rate > 0.0:
                st.warning(f"⚠️ **FLAKY / INTERMITTENT REPRODUCTION** ({report.reproduced_count}/{report.trials_count})")
            else:
                st.error("❌ **FAILURE NOT REPRODUCED**")

            c_met1, c_met2, c_met3 = st.columns(3)
            c_met1.metric("Reproduction Rate", f"{int(report.reproduction_rate * 100)}%")
            c_met2.metric("Mean Latency", f"{report.mean_duration_ms:.1f} ms")
            c_met3.metric("Dominant Hash", report.trace_hash[:16] + "...")

            # Trials table
            trial_rows = [
                {
                    "Trial": t.trial_index,
                    "Seed": t.seed,
                    "Reproduced": "✓ Yes" if t.reproduced else "✗ No",
                    "Outcome": t.result.outcome,
                    "Exit Code": t.result.exit_code,
                    "Duration (ms)": round(t.result.duration_ms, 1),
                    "Trace Hash": t.result.trace_hash[:12],
                }
                for t in report.trials
            ]
            st.table(trial_rows)

    # Tab 2: Minimization
    with tab_minimize:
        st.markdown("### Search Minimal Parameter Boundary")
        st.write("Isolate the exact subset and numerical thresholds required to trigger the failure.")
        btn_minimize = st.button("🔍 Search Minimal Failure Boundary", key="btn_run_minimize")

        if btn_minimize:
            with st.spinner("Running delta elimination & binary boundary search..."):
                minimizer = FailureMinimizer()
                min_report = minimizer.minimize(case)

            st.success(f"🎉 **Failure Minimized in {min_report.iterations_count} iterations** (Confidence: {int(min_report.confidence * 100)}%)")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("#### Original Perturbations")
                st.json(case.perturbations)
            with col_m2:
                st.markdown("#### Minimal Reproducer")
                st.json(min_report.minimized_perturbations)

            if min_report.removed_parameters:
                st.info(f"Omitted non-essential parameters: `{', '.join(min_report.removed_parameters)}`")

    # Tab 3: Verification
    with tab_verify:
        st.markdown("### Fix Verification & Regression Gate")
        default_candidate = "python -m examples.fixtures.payment_service_fixed"
        if "robot" in case.id:
            default_candidate = "python -m examples.fixtures.robot_nav_fixed"

        candidate_cmd = st.text_input("Candidate Command / Patched Build", value=default_candidate)
        btn_verify = st.button("🛡️ Verify Candidate Fix", key="btn_run_verify")

        if btn_verify:
            with st.spinner("Executing Baseline vs Candidate and running regression suites..."):
                verifier = VerificationEngine()
                v_report = verifier.verify(case, candidate_command=candidate_cmd)

            if v_report.overall_verdict == "VERIFIED":
                st.success("✅ **CANDIDATE FIX VERIFIED — Zero Regressions Detected**")
            else:
                st.error(f"❌ **VERIFICATION FAILED: {v_report.overall_verdict}**")

            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.markdown("#### Baseline Outcome")
                st.code(f"Outcome: {v_report.baseline_outcome}\nExit Code: {v_report.baseline_result.exit_code}\nOutput: {v_report.baseline_result.stderr.strip() or v_report.baseline_result.stdout.strip()}")
            with col_v2:
                st.markdown("#### Candidate Outcome")
                st.code(f"Outcome: {v_report.candidate_outcome}\nExit Code: {v_report.candidate_result.exit_code}\nOutput: {v_report.candidate_result.stdout.strip() or v_report.candidate_result.stderr.strip()}")

            st.markdown("#### Regression Results")
            st.table(v_report.regression_details)

            # Export button
            if st.button("📦 Export Portable Evidence Bundle", key="btn_export"):
                out_path = EvidencePackager.package(
                    case=case,
                    output_dir=Path("./artifacts/evidence"),
                    verification_report=v_report,
                )
                st.success(f"Exported evidence bundle to `{out_path}`")


if __name__ == "__main__":
    run_lab()

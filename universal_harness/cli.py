"""Command-line interface for Universal Failure Harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import List, Optional

from universal_harness.case.loader import load_failure_case, save_failure_case
from universal_harness.adapters.autter import import_autter_incident, emit_autter_telemetry
from universal_harness.evidence.report import EvidencePackager
from universal_harness.replay.replayer import DeterministicReplayer
from universal_harness.search.minimizer import FailureMinimizer
from universal_harness.verify.comparator import VerificationEngine


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def format_status(success: bool) -> str:
    return "[PASS]" if success else "[FAIL]"


def handle_replay(args: argparse.Namespace) -> int:
    case_path = Path(args.case)
    if not case_path.exists():
        sys.stderr.write(f"Error: FailureCase file '{case_path}' not found.\n")
        return 1

    case = load_failure_case(case_path)
    if not args.json:
        print(f"\n[1/2] Loading FailureCase: {case.id} ('{case.name}')")
        print(f"      Source: {case.source.system} (digest: {case.digest[:12]}...)")
        print(f"[2/2] Running {args.trials} deterministic replay trials...")

    replayer = DeterministicReplayer()
    report = replayer.replay(case, trials=args.trials, vary_seeds=args.vary_seeds)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print("\n" + "=" * 60)
    print("REPLAY VERDICT: " + report.verdict.upper())
    print("=" * 60)
    print(f"Reproduction:    {report.reproduced_count}/{report.trials_count} ({int(report.reproduction_rate * 100)}%)")
    print(f"Deterministic:   {report.is_deterministic}")
    print(f"Dominant Hash:   {report.trace_hash[:20]}...")
    print(f"Mean Duration:   {report.mean_duration_ms:.1f} ms")
    print("-" * 60)
    for t in report.trials:
        mark = "[REPRODUCED]" if t.reproduced else "[MISMATCH]"
        print(f"  Trial #{t.trial_index:02d} (seed={t.seed}): {mark} [{t.result.outcome}] in {t.result.duration_ms:.1f}ms")
    print("=" * 60 + "\n")

    return 0 if report.reproduction_rate > 0.0 else 1


def handle_minimize(args: argparse.Namespace) -> int:
    case_path = Path(args.case)
    if not case_path.exists():
        sys.stderr.write(f"Error: FailureCase file '{case_path}' not found.\n")
        return 1

    case = load_failure_case(case_path)
    if not args.json:
        print(f"\n[1/3] Loading FailureCase: {case.id}")
        print(f"[2/3] Searching parameter space ({len(case.perturbations)} perturbations)...")

    minimizer = FailureMinimizer()
    report = minimizer.minimize(case, max_boundary_steps=args.boundary_steps)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print("\n" + "=" * 60)
    print("FAILURE CONDITION MINIMIZED")
    print("=" * 60)
    print(f"Search Iterations: {report.iterations_count}")
    print(f"Confidence:        {report.confidence * 100:.0f}%")
    print(f"Removed Params:    {', '.join(report.removed_parameters) if report.removed_parameters else 'None'}")
    print("-" * 60)
    print("Minimal Perturbation Boundary:")
    for k, v in report.minimized_perturbations.items():
        orig = case.perturbations.get(k)
        if orig != v:
            print(f"  {k:20s}: {orig} -> {v}")
        else:
            print(f"  {k:20s}: {v} (essential)")
    print("=" * 60 + "\n")

    return 0


def handle_verify(args: argparse.Namespace) -> int:
    case_path = Path(args.case)
    if not case_path.exists():
        sys.stderr.write(f"Error: FailureCase file '{case_path}' not found.\n")
        return 1

    case = load_failure_case(case_path)
    if not args.json:
        print(f"\n[1/3] Evaluating Baseline: {case.execution.command}")
        print(f"[2/3] Evaluating Candidate: {args.candidate}")

    regression_cases = []
    if args.regression:
        for reg_file in args.regression:
            regression_cases.append(load_failure_case(reg_file))

    verifier = VerificationEngine()
    report = verifier.verify(case, candidate_command=args.candidate, regression_cases=regression_cases)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print("\n" + "=" * 60)
    status_icon = "[OK]" if report.overall_verdict == "VERIFIED" else "[FAIL]"
    print(f"{status_icon} VERIFICATION: {report.overall_verdict}")
    print("=" * 60)
    print(f"Original Failure:  Baseline={report.baseline_outcome.upper()}  ->  Candidate={report.candidate_outcome.upper()}")
    print(f"Failure Resolved:  {'YES' if report.failure_resolved else 'NO'}")
    print(f"Regression Suite:  {report.regression_passed}/{report.regression_total} PASSED")
    print("-" * 60)
    for r in report.regression_details:
        res_icon = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"  {res_icon} {r['case_id']}: {r['outcome']} ({r['duration_ms']:.1f}ms)")
    print("=" * 60 + "\n")

    return 0 if report.overall_verdict == "VERIFIED" else 1


def handle_report(args: argparse.Namespace) -> int:
    case_path = Path(args.case)
    if not case_path.exists():
        sys.stderr.write(f"Error: FailureCase file '{case_path}' not found.\n")
        return 1

    case = load_failure_case(case_path)
    out_dir = Path(args.out_dir)

    print(f"\nGenerating complete verification evidence bundle for {case.id}...")

    # Run replay
    replayer = DeterministicReplayer()
    replay_report = replayer.replay(case, trials=3)

    # Run minimization
    minimizer = FailureMinimizer()
    min_report = minimizer.minimize(case)

    # Run verification if candidate provided
    ver_report = None
    if args.candidate:
        verifier = VerificationEngine()
        ver_report = verifier.verify(case, candidate_command=args.candidate)

    bundle_dir = EvidencePackager.package(
        case=case,
        output_dir=out_dir,
        replay_report=replay_report,
        minimization_report=min_report,
        verification_report=ver_report,
    )

    print(f"\n[+] Portable evidence bundle generated at:")
    print(f"  {bundle_dir.resolve()}\n")
    return 0


def handle_import(args: argparse.Namespace) -> int:
    source_type = args.source.lower()
    input_path = Path(args.input_file)
    if not input_path.exists():
        sys.stderr.write(f"Error: Input file '{input_path}' not found.\n")
        return 1

    if source_type in ("autter", "autter_runtime"):
        case = import_autter_incident(
            input_path,
            reproduce_command=args.command or "python -m examples.fixtures.autter_service_mock",
        )
    else:
        sys.stderr.write(f"Error: Unsupported source type '{source_type}'. Supported: autter\n")
        return 1

    out_path = Path(args.out) if args.out else Path(f"{case.id}.yaml")
    save_failure_case(case, out_path, format="yaml")
    print(f"\n[+] Successfully imported {source_type} incident into FailureCase:")
    print(f"  ID:     {case.id}")
    print(f"  Output: {out_path.resolve()}\n")
    return 0


def handle_emit(args: argparse.Namespace) -> int:
    case_path = Path(args.case)
    if not case_path.exists():
        sys.stderr.write(f"Error: FailureCase file '{case_path}' not found.\n")
        return 1

    case = load_failure_case(case_path)
    print(f"\n[1/2] Loading FailureCase: {case.id}")
    print(f"[2/2] Emitting telemetry event to Autter Runtime endpoint...")

    result = emit_autter_telemetry(case, ingest_key=args.key, endpoint=args.endpoint)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("\n" + "=" * 60)
    status_mark = "[OK]" if result.get("success") else "[WARN]"
    print(f"{status_mark} AUTTER TELEMETRY EMISSION: {result.get('status_code', 0)}")
    print("=" * 60)
    print(f"Target Endpoint: {result.get('endpoint')}")
    print(f"Incident ID:     {result.get('incident_id')}")
    if result.get("error"):
        print(f"Response Info:   {result.get('error')}")
    else:
        print(f"Response:        Telemetry accepted by Autter collector")
    print("=" * 60 + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Universal Failure Reproduction & Verification Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # replay
    p_replay = subparsers.add_parser("replay", help="Replay a FailureCase deterministically")
    p_replay.add_argument("case", help="Path to FailureCase YAML or JSON")
    p_replay.add_argument("--trials", type=int, default=5, help="Number of replay trials (default: 5)")
    p_replay.add_argument("--vary-seeds", action="store_true", help="Vary seeds across trials to test flakiness")
    p_replay.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_replay.set_defaults(func=handle_replay)

    # minimize
    p_min = subparsers.add_parser("minimize", help="Search for minimal failure conditions")
    p_min.add_argument("case", help="Path to FailureCase YAML or JSON")
    p_min.add_argument("--boundary-steps", type=int, default=6, help="Binary search boundary depth")
    p_min.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_min.set_defaults(func=handle_minimize)

    # verify
    p_ver = subparsers.add_parser("verify", help="Verify candidate fix against baseline and regression suite")
    p_ver.add_argument("case", help="Path to FailureCase YAML or JSON")
    p_ver.add_argument("--candidate", required=True, help="Candidate execution command or patched build")
    p_ver.add_argument("--regression", nargs="*", help="Optional additional regression FailureCase files")
    p_ver.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_ver.set_defaults(func=handle_verify)

    # report
    p_rep = subparsers.add_parser("report", help="Package a cryptographic evidence bundle and Markdown report")
    p_rep.add_argument("case", help="Path to FailureCase YAML or JSON")
    p_rep.add_argument("--candidate", help="Optional candidate command to verify and include in report")
    p_rep.add_argument("--out-dir", default="./artifacts/evidence", help="Output directory for evidence bundle")
    p_rep.set_defaults(func=handle_report)

    # import
    p_imp = subparsers.add_parser("import", help="Import external telemetry or incident into a FailureCase")
    p_imp.add_argument("--source", required=True, help="Source format (e.g. autter)")
    p_imp.add_argument("input_file", help="Path to input incident file")
    p_imp.add_argument("--command", help="Target reproduction command")
    p_imp.add_argument("--out", help="Output YAML destination path")
    p_imp.set_defaults(func=handle_import)

    # emit
    p_emit = subparsers.add_parser("emit", help="Emit a FailureCase event to Autter Runtime telemetry endpoint")
    p_emit.add_argument("case", help="Path to FailureCase YAML or JSON")
    p_emit.add_argument("--key", help="Autter Runtime Ingest Key (default from AUTTER_INGEST_KEY)")
    p_emit.add_argument("--endpoint", help="Autter Runtime ingest URL endpoint")
    p_emit.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_emit.set_defaults(func=handle_emit)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

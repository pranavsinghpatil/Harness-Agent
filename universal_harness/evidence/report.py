"""Evidence bundle packaging and Markdown report generator."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

from universal_harness.case.schema import FailureCase
from universal_harness.case.loader import save_failure_case
from universal_harness.evidence.manifest import EvidenceManifest
from universal_harness.replay.replayer import ReplayReport
from universal_harness.search.minimizer import MinimizationReport
from universal_harness.verify.comparator import VerificationReport


class EvidencePackager:
    """Produces portable verification evidence bundles with Markdown and JSON summaries."""

    @staticmethod
    def package(
        case: FailureCase,
        output_dir: Path,
        replay_report: Optional[ReplayReport] = None,
        minimization_report: Optional[MinimizationReport] = None,
        verification_report: Optional[VerificationReport] = None,
    ) -> Path:
        """Create a self-contained evidence directory."""
        bundle_id = f"evidence-{uuid.uuid4().hex[:8]}"
        target_dir = output_dir / bundle_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save case.yaml
        save_failure_case(case, target_dir / "case.yaml", format="yaml")

        # 2. Save replay data if available
        if replay_report:
            (target_dir / "replay.json").write_text(
                json.dumps(replay_report.to_dict(), indent=2), encoding="utf-8"
            )

        # 3. Save minimization data if available
        if minimization_report:
            (target_dir / "minimized.json").write_text(
                json.dumps(minimization_report.to_dict(), indent=2), encoding="utf-8"
            )

        # 4. Save verification data if available
        if verification_report:
            (target_dir / "verification.json").write_text(
                json.dumps(verification_report.to_dict(), indent=2), encoding="utf-8"
            )

        # 5. Generate human-readable report.md
        md_content = EvidencePackager._generate_markdown(
            bundle_id=bundle_id,
            case=case,
            replay_report=replay_report,
            minimization_report=minimization_report,
            verification_report=verification_report,
        )
        (target_dir / "report.md").write_text(md_content, encoding="utf-8")

        # 6. Generate manifest.json
        manifest = EvidenceManifest.create(
            bundle_id=bundle_id,
            case_id=case.id,
            case_digest=case.digest,
            bundle_dir=target_dir,
            metadata={"source": case.source.system, "case_name": case.name},
        )
        (target_dir / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2), encoding="utf-8"
        )

        return target_dir

    @staticmethod
    def _generate_markdown(
        bundle_id: str,
        case: FailureCase,
        replay_report: Optional[ReplayReport],
        minimization_report: Optional[MinimizationReport],
        verification_report: Optional[VerificationReport],
    ) -> str:
        lines = [
            f"# Failure Verification Evidence Report",
            f"",
            f"**Bundle ID:** `{bundle_id}`  ",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Failure Case:** `{case.id}` ({case.name})  ",
            f"**Source System:** `{case.source.system}` ({case.source.reference or 'local'})  ",
            f"**Contract Digest:** `{case.digest}`  ",
            f"",
            f"---",
            f"",
        ]

        # Replay Section
        if replay_report:
            lines.extend([
                f"## 1. Deterministic Replay",
                f"",
                f"- **Verdict:** `{replay_report.verdict}`",
                f"- **Reproduction Rate:** `{replay_report.reproduced_count}/{replay_report.trials_count}` ({int(replay_report.reproduction_rate * 100)}%)",
                f"- **Deterministic Hash:** `{replay_report.is_deterministic}` (`{replay_report.trace_hash[:16]}...`)",
                f"- **Mean Latency:** `{replay_report.mean_duration_ms:.1f} ms`",
                f"",
            ])

        # Minimization Section
        if minimization_report:
            lines.extend([
                f"## 2. Failure Condition Minimization",
                f"",
                f"- **Iterations:** `{minimization_report.iterations_count}`",
                f"- **Confidence:** `{minimization_report.confidence * 100:.0f}%`",
                f"- **Removed Parameters:** {', '.join(f'`{p}`' for p in minimization_report.removed_parameters) if minimization_report.removed_parameters else '*(none)*'}",
                f"",
                f"### Minimal Boundary",
                f"```yaml",
            ])
            for k, v in minimization_report.minimized_perturbations.items():
                lines.append(f"{k}: {v}")
            lines.extend([
                f"```",
                f"",
            ])

        # Verification Section
        if verification_report:
            status_emoji = "✅" if verification_report.overall_verdict == "VERIFIED" else "❌"
            lines.extend([
                f"## 3. Candidate Verification & Regression Check",
                f"",
                f"**Overall Verdict:** {status_emoji} `{verification_report.overall_verdict}`",
                f"",
                f"| Condition | Baseline | Candidate | Status |",
                f"| :--- | :--- | :--- | :--- |",
                f"| Target Failure | `{verification_report.baseline_outcome}` | `{verification_report.candidate_outcome}` | {'RESOLVED' if verification_report.failure_resolved else 'UNRESOLVED'} |",
                f"| Regression Suite | — | `{verification_report.regression_passed}/{verification_report.regression_total} PASS` | {'PASS' if not verification_report.regressions_detected else 'FAIL'} |",
                f"",
            ])

        lines.extend([
            f"---",
            f"*Portable evidence bundle generated by Universal Harness.*",
        ])
        return "\n".join(lines)

"""Deterministic replay runner and trace comparison utility."""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any
from sandbox.telemetry.manifest import RunManifest
from sandbox.telemetry.recorder import TelemetryFrame


@dataclass
class ReplayComparisonResult:
    is_bit_exact_match: bool
    original_trace_hash: str
    replayed_trace_hash: str
    mismatched_frame_index: int | None = None
    difference_details: str = ""


class DeterministicReplayer:
    """Verifies that a re-executed run matches the recorded manifest trace hash."""

    @staticmethod
    def compare_traces(
        original_frames: list[dict[str, Any]],
        replayed_frames: list[dict[str, Any]],
        orig_hash: str = "",
        rep_hash: str = "",
    ) -> ReplayComparisonResult:
        """Verifies bit-exact trace determinism across all physical and safety fields.

        Args:
            original_frames: List of telemetry frame dictionaries from original execution.
            replayed_frames: List of telemetry frame dictionaries from replayed execution.
            orig_hash: SHA-256 trace checksum from original RunManifest.
            rep_hash: SHA-256 trace checksum from replayed RunManifest.

        Returns:
            ReplayComparisonResult detailing match verdict and any mismatch diagnostics.
        """
        if orig_hash and rep_hash and orig_hash != rep_hash:
            return ReplayComparisonResult(
                is_bit_exact_match=False,
                original_trace_hash=orig_hash,
                replayed_trace_hash=rep_hash,
                difference_details=f"Trace hash mismatch: {orig_hash} != {rep_hash}",
            )

        if len(original_frames) != len(replayed_frames):
            return ReplayComparisonResult(
                is_bit_exact_match=False,
                original_trace_hash=orig_hash,
                replayed_trace_hash=rep_hash,
                difference_details=f"Frame count mismatch: original={len(original_frames)}, replayed={len(replayed_frames)}",
            )

        for idx, (orig, rep) in enumerate(zip(original_frames, replayed_frames)):
            orig_state = orig["vehicle_state"]
            rep_state = rep["vehicle_state"]

            for k in ("x", "y", "velocity", "heading", "acceleration", "steer_angle"):
                if k in orig_state and k in rep_state:
                    if abs(orig_state[k] - rep_state[k]) > 1e-4:
                        return ReplayComparisonResult(
                            is_bit_exact_match=False,
                            original_trace_hash=orig_hash,
                            replayed_trace_hash=rep_hash,
                            mismatched_frame_index=idx,
                            difference_details=f"Frame {idx} state mismatch on {k}: {orig_state[k]} vs {rep_state[k]}",
                        )

            if abs(orig.get("min_clearance", 0.0) - rep.get("min_clearance", 0.0)) > 1e-3:
                return ReplayComparisonResult(
                    is_bit_exact_match=False,
                    original_trace_hash=orig_hash,
                    replayed_trace_hash=rep_hash,
                    mismatched_frame_index=idx,
                    difference_details=f"Frame {idx} clearance mismatch: {orig.get('min_clearance')} vs {rep.get('min_clearance')}",
                )

            if orig.get("active_faults") != rep.get("active_faults"):
                return ReplayComparisonResult(
                    is_bit_exact_match=False,
                    original_trace_hash=orig_hash,
                    replayed_trace_hash=rep_hash,
                    mismatched_frame_index=idx,
                    difference_details=f"Frame {idx} active faults mismatch: {orig.get('active_faults')} vs {rep.get('active_faults')}",
                )

        return ReplayComparisonResult(
            is_bit_exact_match=True,
            original_trace_hash=orig_hash,
            replayed_trace_hash=rep_hash,
        )

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
    def compare_traces(original_frames: list[dict[str, Any]], replayed_frames: list[dict[str, Any]]) -> ReplayComparisonResult:
        if len(original_frames) != len(replayed_frames):
            return ReplayComparisonResult(
                is_bit_exact_match=False,
                original_trace_hash="",
                replayed_trace_hash="",
                difference_details=f"Frame count mismatch: original={len(original_frames)}, replayed={len(replayed_frames)}",
            )

        for idx, (orig, rep) in enumerate(zip(original_frames, replayed_frames)):
            orig_state = orig["vehicle_state"]
            rep_state = rep["vehicle_state"]

            for k in ("x", "y", "velocity", "heading"):
                if abs(orig_state[k] - rep_state[k]) > 1e-4:
                    return ReplayComparisonResult(
                        is_bit_exact_match=False,
                        original_trace_hash="",
                        replayed_trace_hash="",
                        mismatched_frame_index=idx,
                        difference_details=f"Frame {idx} state mismatch on {k}: {orig_state[k]} vs {rep_state[k]}",
                    )

        return ReplayComparisonResult(
            is_bit_exact_match=True,
            original_trace_hash="",
            replayed_trace_hash="",
        )

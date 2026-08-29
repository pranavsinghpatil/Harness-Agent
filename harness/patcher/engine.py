"""Autonomous code patcher orchestrating deterministic and AST safety transformations."""

from __future__ import annotations
import difflib
from typing import List, Optional
import uuid

from harness.models.diagnostics import CausalDiagnosticReport
from harness.models.patch import PatchResult, PatchStrategyType, PatchValidationStatus
from harness.controllers.validator import ControllerValidator
from harness.patcher.strategies import (
    DynamicStoppingBufferPatcher,
    StaleSensorFailSafePatcher,
    CombinedHardenedControllerGenerator,
)


class AutoCodePatcher:
    """Synthesizes hardened controller source code from failure diagnostics."""

    @classmethod
    def generate_patch(
        cls,
        original_code: str,
        diagnostic_report: Optional[CausalDiagnosticReport] = None,
        strategy_override: Optional[PatchStrategyType] = None,
    ) -> PatchResult:
        """Synthesize a hardened code patch addressing the diagnosed failure modes.

        Args:
            original_code: Pre-patch controller Python source code.
            diagnostic_report: Causal diagnostic report describing the failure.
            strategy_override: Optional explicit strategy selection.

        Returns:
            PatchResult containing original code, patched code, and unified diff.
        """
        patch_id = f"patch_{uuid.uuid4().hex[:8]}"
        report_id = diagnostic_report.report_id if diagnostic_report else ""

        strategies_applied: List[PatchStrategyType] = []
        patched_code = original_code

        # If empty code was supplied, generate full hardened reference controller
        if not original_code or not original_code.strip():
            patched_code = CombinedHardenedControllerGenerator.get_hardened_reference_controller_code()
            original_code = "# Baseline reactive controller\n"
            strategies_applied.append(PatchStrategyType.COMBINED_FAILSAFE_HARDENING)
        else:
            # 1. Apply Observation Staleness Guard
            code_after_stale, mod_stale = StaleSensorFailSafePatcher.apply(patched_code)
            if mod_stale:
                patched_code = code_after_stale
                strategies_applied.append(PatchStrategyType.STALE_SENSOR_FAIL_SAFE)

            # 2. Apply Dynamic Stopping Buffer
            code_after_buffer, mod_buffer = DynamicStoppingBufferPatcher.apply(patched_code)
            if mod_buffer:
                patched_code = code_after_buffer
                strategies_applied.append(PatchStrategyType.DYNAMIC_STOPPING_BUFFER)

            # If AST regex replacement did not modify user code, provide hardened controller
            if not strategies_applied:
                patched_code = CombinedHardenedControllerGenerator.get_hardened_reference_controller_code()
                strategies_applied.append(PatchStrategyType.COMBINED_FAILSAFE_HARDENING)

        # 3. Compute unified diff
        orig_lines = original_code.splitlines(keepends=True)
        patched_lines = patched_code.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                orig_lines,
                patched_lines,
                fromfile="original_controller.py",
                tofile="hardened_controller.py",
            )
        )
        unified_diff = "".join(diff_lines)

        # 4. Validate synthesized code AST
        val_result = ControllerValidator.validate_code(patched_code)
        validation_status = (
            PatchValidationStatus.SYNTAX_VALID
            if val_result.is_valid
            else PatchValidationStatus.SYNTAX_ERROR
        )
        val_message = (
            "Syntax and interface validation successful."
            if val_result.is_valid
            else f"Validation error: {'; '.join(val_result.errors)}"
        )

        return PatchResult(
            patch_id=patch_id,
            report_id=report_id,
            strategies_applied=strategies_applied,
            original_code=original_code,
            patched_code=patched_code,
            unified_diff=unified_diff,
            validation_status=validation_status,
            validation_message=val_message,
        )

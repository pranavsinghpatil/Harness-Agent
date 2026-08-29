"""Autonomous code patcher orchestrating deterministic and AST safety transformations."""

from __future__ import annotations
import difflib
from typing import List, Optional, Tuple
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

        effective_original = original_code if original_code and original_code.strip() else "# Baseline reactive controller\n"
        patched_code, strategies = cls._synthesize_hardened_code(
            original_code=original_code,
            strategy_override=strategy_override,
            diagnostic_report=diagnostic_report,
        )

        unified_diff = cls._generate_diff(effective_original, patched_code)
        val_status, val_message = cls._validate_patch_syntax(patched_code)

        return PatchResult(
            patch_id=patch_id,
            report_id=report_id,
            strategies_applied=strategies,
            original_code=effective_original,
            patched_code=patched_code,
            unified_diff=unified_diff,
            validation_status=val_status,
            validation_message=val_message,
        )

    @classmethod
    def _synthesize_hardened_code(
        cls,
        original_code: str,
        strategy_override: Optional[PatchStrategyType],
        diagnostic_report: Optional[CausalDiagnosticReport],
    ) -> Tuple[str, List[PatchStrategyType]]:
        """Applies transformation passes to produce the hardened source code.

        Args:
            original_code: Raw input source code.
            strategy_override: Optional explicit strategy constraint.
            diagnostic_report: Diagnostic report context.

        Returns:
            Tuple of (synthesized_code, applied_strategies_list).
        """
        if not original_code or not original_code.strip():
            return CombinedHardenedControllerGenerator.get_hardened_reference_controller_code(), [PatchStrategyType.COMBINED_FAILSAFE_HARDENING]

        if strategy_override == PatchStrategyType.COMBINED_FAILSAFE_HARDENING:
            return CombinedHardenedControllerGenerator.get_hardened_reference_controller_code(), [PatchStrategyType.COMBINED_FAILSAFE_HARDENING]

        patched = original_code
        strategies: List[PatchStrategyType] = []

        if strategy_override in (None, PatchStrategyType.STALE_SENSOR_FAIL_SAFE):
            code_after_stale, mod_stale = StaleSensorFailSafePatcher.apply(patched)
            if mod_stale:
                patched = code_after_stale
                strategies.append(PatchStrategyType.STALE_SENSOR_FAIL_SAFE)

        if strategy_override in (None, PatchStrategyType.DYNAMIC_STOPPING_BUFFER):
            code_after_buffer, mod_buffer = DynamicStoppingBufferPatcher.apply(patched)
            if mod_buffer:
                patched = code_after_buffer
                strategies.append(PatchStrategyType.DYNAMIC_STOPPING_BUFFER)

        if not strategies:
            patched = CombinedHardenedControllerGenerator.get_hardened_reference_controller_code()
            strategies.append(PatchStrategyType.COMBINED_FAILSAFE_HARDENING)

        return patched, strategies

    @classmethod
    def _generate_diff(cls, original_code: str, patched_code: str) -> str:
        """Computes a unified diff string between original and patched code.

        Args:
            original_code: Pre-patch source text.
            patched_code: Hardened source text.

        Returns:
            Unified diff formatted string.
        """
        orig_lines = original_code.splitlines(keepends=True)
        patched_lines = patched_code.splitlines(keepends=True)
        diff_lines = difflib.unified_diff(
            orig_lines,
            patched_lines,
            fromfile="original_controller.py",
            tofile="hardened_controller.py",
        )
        return "".join(diff_lines)

    @classmethod
    def _validate_patch_syntax(cls, patched_code: str) -> Tuple[PatchValidationStatus, str]:
        """Validates that synthesized code is syntactically correct and structurally compliant.

        Args:
            patched_code: Synthesized Python source code to test.

        Returns:
            Tuple of (PatchValidationStatus, descriptive_status_message).
        """
        val_result = ControllerValidator.validate_code(patched_code)
        if val_result.is_valid:
            return PatchValidationStatus.SYNTAX_VALID, "Syntax and interface validation successful."
        return PatchValidationStatus.SYNTAX_ERROR, f"Validation error: {'; '.join(val_result.errors)}"

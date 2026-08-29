"""Unit tests for AutoCodePatcher and deterministic safety code hardening."""

from __future__ import annotations
from harness.patcher.engine import AutoCodePatcher
from harness.models.patch import PatchValidationStatus, PatchStrategyType


def test_auto_patcher_synthesizes_valid_hardened_code() -> None:
    """Verify AutoCodePatcher generates valid syntax and diff."""
    original_script = """
from target_agents.base import BaseTargetAgent
from sandbox.actuators.command import ActuatorCommand

class SimpleRover(BaseTargetAgent):
    def step(self, observations, sim_time):
        stop_distance = 7.0
        return ActuatorCommand(throttle=0.5, steering=0.0)
"""
    patch_res = AutoCodePatcher.generate_patch(original_code=original_script)

    assert patch_res.validation_status == PatchValidationStatus.SYNTAX_VALID
    assert len(patch_res.strategies_applied) > 0
    assert "def step(" in patch_res.patched_code
    assert "diff" in patch_res.unified_diff or "original_controller.py" in patch_res.unified_diff

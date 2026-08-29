"""Unit tests for RunManager, hardware presets, and controller ingestion."""

from __future__ import annotations
from harness.hardware.registry import default_hardware_registry
from harness.orchestration.run_manager import RunManager
from harness.models.evaluation import EvaluationRequest, HarnessRunStatus
from harness.controllers.validator import ControllerValidator
from harness.controllers.adapter import DynamicControllerLoader


def test_hardware_registry_and_rdk_x5() -> None:
    """Verify hardware preset lookup defaults to D-Robotics RDK X5."""
    preset = default_hardware_registry.get("RDK_X5")
    assert preset.name == "D-Robotics RDK X5"
    assert preset.profile.cpu_capacity_units_per_sec == 150.0
    assert preset.profile.thermal_throttle_temp == 85.0
    assert preset.bpu_acceleration_factor == 2.2

    # Verify fallback for unknown boards
    unknown = default_hardware_registry.get("UNKNOWN_BOARD_XYZ")
    assert unknown.name == "D-Robotics RDK X5"


def test_controller_validation_and_loading() -> None:
    """Verify AST validation and dynamic instantiation of custom controller code."""
    valid_code = """
from target_agents.base import BaseTargetAgent
from sandbox.actuators.command import ActuatorCommand

class CustomDeliveryRover(BaseTargetAgent):
    def step(self, sim_time):
        return ActuatorCommand(throttle=0.4, steering=0.0)
"""
    val_res = ControllerValidator.validate_code(valid_code)
    assert val_res.is_valid is True
    assert val_res.has_base_agent_class is True
    assert val_res.entrypoint_class_name == "CustomDeliveryRover"

    agent = DynamicControllerLoader.load_from_code(valid_code, agent_id="test_rover")
    cmd = agent.step(0.0)
    assert cmd.throttle == 0.4


def test_run_manager_baseline_execution() -> None:
    """Verify RunManager creates evaluation and executes baseline run."""
    manager = RunManager()
    req = EvaluationRequest(
        hardware_preset_id="RDK_X5",
        scenario_id="showcase_normal",
        seed=42,
    )
    eval_obj = manager.create_evaluation(req)
    assert eval_obj.evaluation_id.startswith("eval_")

    run_res = manager.execute_baseline(eval_obj.evaluation_id)
    assert run_res.status == HarnessRunStatus.COMPLETED
    assert run_res.trace_hash != ""
    assert len(run_res.telemetry_frames) > 0

"""Canonical TrueForge Agent tool contracts for inspecting, configuring, evaluating, diagnosing, and patching."""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from harness.hardware.registry import default_hardware_registry
from harness.orchestration.run_manager import default_run_manager
from harness.models.evaluation import EvaluationRequest, EvaluationMode
from harness.diagnostics.analyzer import CausalTelemetryAnalyzer
from harness.patcher.engine import AutoCodePatcher
from harness.investigator import AutonomousInvestigator, InvestigatorConfig
from sandbox.api.tools import list_scenarios, get_scenario


def list_hardware_profiles() -> List[Dict[str, Any]]:
    """List all available target edge hardware presets (e.g. D-Robotics RDK X5, Jetson Orin Nano, Pi 5).

    Returns:
        List of hardware profiles with compute, memory, and bus latency metadata.
    """
    return [p.to_dict() for p in default_hardware_registry.list_presets()]


def inspect_scenario(scenario_id: str) -> Dict[str, Any]:
    """Inspect the world layout, obstacles, and default fault schedule for a scenario.

    Args:
        scenario_id: Identifier of the target scenario.

    Returns:
        Dictionary detailing world dimensions, initial state, goal, and faults.

    Raises:
        ValueError: If scenario_id is not found in the scenario registry.
    """
    sc = get_scenario(scenario_id)
    if not sc:
        raise ValueError(f"Scenario '{scenario_id}' not found.")
    return sc.model_dump()


def inspect_safety_policy(policy_id: str = "default") -> Dict[str, Any]:
    """Inspect invariant safety thresholds (minimum clearance, speed limit, max observation age).

    Args:
        policy_id: Identifier of the safety policy.

    Returns:
        Dictionary of safety threshold parameters.
    """
    return {
        "policy_id": policy_id,
        "min_clearance_m": 0.8,
        "speed_limit_mps": 6.5,
        "max_observation_age_s": 0.40,
        "description": "Physical safety policy ensuring collision-free navigation under sensor latency.",
    }


def create_experiment(
    hardware_preset_id: str = "RDK_X5",
    scenario_id: str = "showcase_perturbed_failure",
    controller_code: Optional[str] = None,
    seed: int = 1337,
) -> Dict[str, Any]:
    """Create a new evaluation experiment binding target hardware, scenario, and controller.

    Args:
        hardware_preset_id: Target board profile (e.g. 'RDK_X5').
        scenario_id: Target scenario ID.
        controller_code: Optional custom Python controller script.
        seed: Random seed for deterministic execution.

    Returns:
        Created evaluation experiment metadata dictionary.

    Raises:
        ValueError: If scenario_id is not found.
    """
    sc = get_scenario(scenario_id)
    if not sc:
        raise ValueError(f"Scenario '{scenario_id}' not found.")

    req = EvaluationRequest(
        hardware_preset_id=hardware_preset_id,
        scenario_id=scenario_id,
        controller_code=controller_code,
        seed=seed,
        mode=EvaluationMode.AUTONOMOUS_HARNESS,
    )
    eval_obj = default_run_manager.create_evaluation(req)
    return eval_obj.to_dict()


def run_experiment(evaluation_id: str) -> Dict[str, Any]:
    """Execute the baseline simulation run for an experiment and record telemetry.

    Args:
        evaluation_id: Unique evaluation identifier.

    Returns:
        Dictionary containing run status, violations, and trace hash.

    Raises:
        KeyError: If evaluation_id is not found.
    """
    run_res = default_run_manager.execute_baseline(evaluation_id)
    return run_res.to_dict()


def diagnose_failure(evaluation_id: str) -> Dict[str, Any]:
    """Perform causal telemetry analysis on a failed baseline run.

    Args:
        evaluation_id: Unique evaluation identifier.

    Returns:
        Causal diagnostic report with root causes, causal graph, and patch recommendations.

    Raises:
        KeyError: If evaluation_id or baseline run is not found.
    """
    eval_obj = default_run_manager.get_evaluation(evaluation_id)
    if not eval_obj or not eval_obj.baseline_run:
        raise KeyError(f"Evaluation '{evaluation_id}' or baseline run not found.")

    report = CausalTelemetryAnalyzer.analyze_run(eval_obj.baseline_run)
    report.evaluation_id = evaluation_id
    eval_obj.diagnosis = report
    return report.to_dict()


def auto_patch_controller(
    original_code: str, evaluation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Synthesize hardened controller source code addressing diagnosed failure modes.

    Args:
        original_code: Python source code of the baseline controller.
        evaluation_id: Optional associated evaluation ID for diagnostic context.

    Returns:
        Dictionary containing patched code, unified diff, and validation status.
    """
    diag_report = None
    if evaluation_id:
        eval_obj = default_run_manager.get_evaluation(evaluation_id)
        if eval_obj:
            diag_report = eval_obj.diagnosis

    patch_res = AutoCodePatcher.generate_patch(
        original_code=original_code, diagnostic_report=diag_report
    )
    if evaluation_id:
        eval_obj = default_run_manager.get_evaluation(evaluation_id)
        if eval_obj:
            eval_obj.patch = patch_res
    return patch_res.to_dict()


def verify_patch(evaluation_id: str, patched_code: str) -> Dict[str, Any]:
    """Re-execute the simulation with patched code on the identical seed and fault schedule.

    Args:
        evaluation_id: Unique evaluation identifier.
        patched_code: Hardened controller Python source code.

    Returns:
        Dictionary containing verification run metrics and comparison verdict.

    Raises:
        KeyError: If evaluation_id is not found.
    """
    verify_run = default_run_manager.execute_verification(
        evaluation_id=evaluation_id, patched_code=patched_code
    )
    eval_obj = default_run_manager.get_evaluation(evaluation_id)
    return {
        "verification_run": verify_run.to_dict(),
        "final_result": eval_obj.final_result.to_dict() if eval_obj and eval_obj.final_result else None,
    }


def investigate_reliability(
    objective: str,
    hardware_preset_id: str = "RDK_X5",
    scenario_id: str = "showcase_normal_baseline",
    controller_code: Optional[str] = None,
    seed: int = 1337,
    budget: int = 12,
    max_boundary_steps: int = 3,
) -> Dict[str, Any]:
    """Run autonomous baseline, perturbation, boundary, and interaction experiments."""
    if not get_scenario(scenario_id):
        raise ValueError(f"Scenario '{scenario_id}' not found.")
    investigator = AutonomousInvestigator(
        InvestigatorConfig(
            objective=objective,
            hardware_preset_id=hardware_preset_id,
            scenario_id=scenario_id,
            controller_code=controller_code,
            seed=seed,
            budget=budget,
            max_boundary_steps=max_boundary_steps,
        )
    )
    return investigator.run().to_dict()

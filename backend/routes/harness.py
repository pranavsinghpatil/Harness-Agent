"""FastAPI routes for TrueForge Agent Harness evaluation, diagnostics, and auto-patching."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException

from harness.hardware.registry import default_hardware_registry
from harness.orchestration.run_manager import default_run_manager
from harness.models.evaluation import EvaluationRequest, EvaluationMode
from harness.models.patch import PatchStrategyType
from harness.evaluator.loop import ReliabilityEvaluationLoop
from harness.diagnostics.analyzer import CausalTelemetryAnalyzer
from harness.patcher.engine import AutoCodePatcher
from harness.investigator import AutonomousInvestigator, InvestigatorConfig
from sandbox.api.tools import get_scenario

router = APIRouter(prefix="/api/harness", tags=["harness"])


class CreateEvaluationPayload(BaseModel):
    hardware_preset_id: str = Field(default="RDK_X5", description="Target hardware board preset ID")
    scenario_id: str = Field(default="showcase_perturbed_failure", description="Target scenario identifier")
    controller_code: Optional[str] = Field(default=None, description="Optional custom controller Python code")
    seed: int = Field(default=1337, description="Random seed for repeatable execution")
    mode: str = Field(default="AUTONOMOUS_HARNESS", description="Operational mode")


class PatchControllerPayload(BaseModel):
    original_code: str = Field(description="Original baseline controller Python code")
    strategy: Optional[str] = Field(default=None, description="Optional strategy override")


class VerifyPatchPayload(BaseModel):
    patched_code: str = Field(description="Hardened controller Python source code to verify")


class InvestigationPayload(BaseModel):
    objective: str = Field(min_length=1, description="Reliability question the harness must investigate")
    hardware_preset_id: str = Field(default="RDK_X5", description="Target hardware board preset ID")
    scenario_id: str = Field(default="showcase_normal_baseline", description="Healthy baseline scenario")
    controller_code: Optional[str] = Field(default=None, description="Optional custom controller Python code")
    seed: int = Field(default=1337, description="Random seed for repeatable experiments")
    budget: int = Field(default=12, ge=1, le=100, description="Maximum number of experiments")
    max_boundary_steps: int = Field(default=3, ge=0, le=10, description="Maximum binary refinements per failed dimension")

    @field_validator("objective", mode="before")
    @classmethod
    def validate_objective(cls, value: object) -> str:
        """Reject blank objectives as a client validation error."""
        if not isinstance(value, str):
            raise ValueError("objective must be a string")
        normalized: str = value.strip()
        if not normalized:
            raise ValueError("objective must not be blank")
        return normalized


@router.get("/hardware-presets")
def get_hardware_presets() -> List[Dict[str, Any]]:
    """Retrieve all available edge compute hardware presets (e.g. D-Robotics RDK X5, Jetson Orin Nano, Pi 5).

    Returns:
        List of serialized HardwarePreset dictionaries.
    """
    return [p.to_dict() for p in default_hardware_registry.list_presets()]


@router.post("/evaluations")
def create_and_run_evaluation(payload: CreateEvaluationPayload) -> Dict[str, Any]:
    """Create a new evaluation, run baseline simulation, and return execution results.

    Args:
        payload: Evaluation parameters including hardware, scenario, code, and seed.

    Returns:
        Dictionary representing the created HarnessEvaluation state.

    Raises:
        HTTPException: 404 if scenario_id is not found.
    """
    sc = get_scenario(payload.scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario '{payload.scenario_id}' not found.")

    req = EvaluationRequest(
        hardware_preset_id=payload.hardware_preset_id,
        scenario_id=payload.scenario_id,
        controller_code=payload.controller_code,
        seed=payload.seed,
        mode=EvaluationMode(payload.mode) if payload.mode in EvaluationMode.__members__ else EvaluationMode.AUTONOMOUS_HARNESS,
    )
    eval_obj = default_run_manager.create_evaluation(req)
    default_run_manager.execute_baseline(eval_obj.evaluation_id)
    return eval_obj.to_dict(include_telemetry=True)


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str) -> Dict[str, Any]:
    """Retrieve state and telemetry of an existing HarnessEvaluation.

    Args:
        evaluation_id: Unique evaluation identifier.

    Returns:
        Serialized HarnessEvaluation dictionary.

    Raises:
        HTTPException: 404 if evaluation is not found.
    """
    eval_obj = default_run_manager.get_evaluation(evaluation_id)
    if not eval_obj:
        raise HTTPException(status_code=404, detail=f"Evaluation '{evaluation_id}' not found.")
    return eval_obj.to_dict(include_telemetry=True)


@router.post("/evaluations/{evaluation_id}/diagnose")
def diagnose_evaluation_failure(evaluation_id: str) -> Dict[str, Any]:
    """Execute causal telemetry analysis on an evaluation's baseline failure.

    Args:
        evaluation_id: Unique evaluation identifier.

    Returns:
        CausalDiagnosticReport dictionary containing causal graph and recommendations.

    Raises:
        HTTPException: 404 if evaluation or baseline run is missing.
    """
    eval_obj = default_run_manager.get_evaluation(evaluation_id)
    if not eval_obj or not eval_obj.baseline_run:
        raise HTTPException(status_code=404, detail=f"Baseline run for '{evaluation_id}' not found.")

    report = CausalTelemetryAnalyzer.analyze_run(eval_obj.baseline_run)
    report.evaluation_id = evaluation_id
    eval_obj.diagnosis = report
    return report.to_dict()


@router.post("/evaluations/{evaluation_id}/patch")
def generate_controller_patch(
    evaluation_id: str, payload: PatchControllerPayload
) -> Dict[str, Any]:
    """Synthesize a hardened code patch addressing diagnosed failure modes.

    Args:
        evaluation_id: Unique evaluation identifier.
        payload: Original controller code and optional strategy.

    Returns:
        PatchResult dictionary with patched code, diff, and validation status.

    Raises:
        HTTPException: 404 if evaluation is not found.
    """
    eval_obj = default_run_manager.get_evaluation(evaluation_id)
    if not eval_obj:
        raise HTTPException(status_code=404, detail=f"Evaluation '{evaluation_id}' not found.")

    strategy_override = None
    if payload.strategy:
        try:
            strategy_override = PatchStrategyType(payload.strategy)
        except ValueError:
            pass

    patch_res = AutoCodePatcher.generate_patch(
        original_code=payload.original_code,
        diagnostic_report=eval_obj.diagnosis,
        strategy_override=strategy_override,
    )
    eval_obj.patch = patch_res
    return patch_res.to_dict()


@router.post("/evaluations/{evaluation_id}/verify")
def verify_patched_controller(
    evaluation_id: str, payload: VerifyPatchPayload
) -> Dict[str, Any]:
    """Re-execute simulation on identical seed and fault schedule to verify patched code safety.

    Args:
        evaluation_id: Unique evaluation identifier.
        payload: Patched controller source code.

    Returns:
        Dictionary containing verification run trace and final result comparison.

    Raises:
        HTTPException: 404 if evaluation is not found.
    """
    eval_obj = default_run_manager.get_evaluation(evaluation_id)
    if not eval_obj:
        raise HTTPException(status_code=404, detail=f"Evaluation '{evaluation_id}' not found.")

    verify_run = default_run_manager.execute_verification(
        evaluation_id=evaluation_id, patched_code=payload.patched_code
    )
    return {
        "verification_run": verify_run.to_dict(include_frames=True),
        "final_result": eval_obj.final_result.to_dict() if eval_obj.final_result else None,
    }


@router.post("/evaluate-full")
def run_end_to_end_closed_loop(payload: CreateEvaluationPayload) -> Dict[str, Any]:
    """Execute complete automated closed loop: Run -> Diagnose -> Patch -> Verify -> Report.

    Args:
        payload: Evaluation parameters.

    Returns:
        Complete HarnessEvaluation dictionary with baseline, diagnosis, patch, and verification proof.

    Raises:
        HTTPException: 404 if scenario is not found.
    """
    sc = get_scenario(payload.scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario '{payload.scenario_id}' not found.")

    req = EvaluationRequest(
        hardware_preset_id=payload.hardware_preset_id,
        scenario_id=payload.scenario_id,
        controller_code=payload.controller_code,
        seed=payload.seed,
        mode=EvaluationMode(payload.mode) if payload.mode in EvaluationMode.__members__ else EvaluationMode.AUTONOMOUS_HARNESS,
    )
    loop = ReliabilityEvaluationLoop(run_manager=default_run_manager)
    eval_res = loop.run_full_evaluation(req)
    return eval_res.to_dict(include_telemetry=True)


@router.post("/investigations")
def run_autonomous_investigation(payload: InvestigationPayload) -> Dict[str, Any]:
    """Let System 2 choose and execute bounded System 1 experiments."""
    if not get_scenario(payload.scenario_id):
        raise HTTPException(status_code=404, detail=f"Scenario '{payload.scenario_id}' not found.")

    investigator = AutonomousInvestigator(
        InvestigatorConfig(
            objective=payload.objective,
            hardware_preset_id=payload.hardware_preset_id,
            scenario_id=payload.scenario_id,
            controller_code=payload.controller_code,
            seed=payload.seed,
            budget=payload.budget,
            max_boundary_steps=payload.max_boundary_steps,
        )
    )
    return investigator.run().to_dict()

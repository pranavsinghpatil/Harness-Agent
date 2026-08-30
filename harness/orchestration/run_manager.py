"""RunManager singleton orchestrating HarnessEvaluations, execution sessions, and event multiplexing."""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Mapping, Optional
import uuid
import copy

from scenarios.schema import ScenarioDefinition
from sandbox.api.tools import get_scenario
from harness.models.evaluation import (
    HarnessEvaluation,
    HarnessRun,
    EvaluationRequest,
    HarnessEvaluationResult,
    HarnessRunStatus,
    ControllerHealth,
    VerificationVerdict,
)
from harness.models.events import HarnessEvent, HarnessEventType, EventSeverity
from harness.hardware.registry import default_hardware_registry
from harness.controllers.adapter import DynamicControllerLoader
from harness.orchestration.session import SandboxSession
from target_agents.reference_agent.agent import ReferenceAutonomousAgent


class RunManager:
    """Central orchestrator managing the full lifecycle of HarnessEvaluations and execution sessions."""

    def __init__(self) -> None:
        self._evaluations: Dict[str, HarnessEvaluation] = {}
        self._event_listeners: List[Callable[[HarnessEvent], None]] = []

    def add_event_listener(self, listener: Callable[[HarnessEvent], None]) -> None:
        """Register an event listener for live event streaming.

        Args:
            listener: Callback function accepting HarnessEvent.
        """
        self._event_listeners.append(listener)

    def _broadcast_event(self, event: HarnessEvent) -> None:
        """Broadcast event to all registered listeners."""
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception:
                pass

    def create_evaluation(self, request: EvaluationRequest) -> HarnessEvaluation:
        """Initialize a new HarnessEvaluation.

        Args:
            request: EvaluationRequest parameters.

        Returns:
            Initialized HarnessEvaluation instance.
        """
        eval_id = f"eval_{uuid.uuid4().hex[:8]}"
        scenario = get_scenario(request.scenario_id)

        evaluation = HarnessEvaluation(
            evaluation_id=eval_id,
            request=request,
            scenario=scenario,
        )
        self._evaluations[eval_id] = evaluation
        return evaluation

    def get_evaluation(self, evaluation_id: str) -> Optional[HarnessEvaluation]:
        """Retrieve an evaluation by ID.

        Args:
            evaluation_id: Unique evaluation identifier.

        Returns:
            HarnessEvaluation or None if not found.
        """
        return self._evaluations.get(evaluation_id)

    def remove_evaluation(self, evaluation_id: str) -> bool:
        """Release one retained evaluation when its owning session expires."""
        return self._evaluations.pop(evaluation_id, None) is not None

    def list_evaluations(self) -> List[HarnessEvaluation]:
        """List all tracked evaluations.

        Returns:
            List of all HarnessEvaluation records.
        """
        return list(self._evaluations.values())

    @staticmethod
    def _execution_context(evaluation: HarnessEvaluation) -> tuple[str, str]:
        """Read validated investigation context from an evaluation request."""
        metadata: Mapping[str, Any] = evaluation.request.metadata
        investigation_value: object = metadata.get("investigation_id", "")
        experiment_value: object = metadata.get("experiment_id", "")
        investigation_id: str = investigation_value if isinstance(investigation_value, str) else ""
        experiment_id: str = experiment_value if isinstance(experiment_value, str) else ""
        return investigation_id, experiment_id

    def _event_sink(
        self, event_callback: Optional[Callable[[HarnessEvent], None]]
    ) -> Callable[[HarnessEvent], None]:
        """Combine the global event bus with an optional owning-session sink."""
        def publish(event: HarnessEvent) -> None:
            self._broadcast_event(event)
            if event_callback is not None:
                event_callback(event)

        return publish

    def execute_baseline(
        self,
        evaluation_id: str,
        event_callback: Optional[Callable[[HarnessEvent], None]] = None,
        max_sim_time: Optional[float] = None,
        run_id: Optional[str] = None,
    ) -> HarnessRun:
        """Execute the baseline simulation run for an evaluation.

        Args:
            evaluation_id: Identifier of the target HarnessEvaluation.
            event_callback: Optional per-execution sink for forwarding events to
                an owning investigation session.
            max_sim_time: Optional upper bound for the simulation episode in seconds.
            run_id: Optional preallocated run identifier for trace lifecycle events.

        Returns:
            Executed baseline HarnessRun.

        Raises:
            KeyError: If evaluation_id does not exist.
        """
        evaluation = self.get_evaluation(evaluation_id)
        if not evaluation:
            raise KeyError(f"Evaluation '{evaluation_id}' not found.")

        run_id = run_id or f"run_{uuid.uuid4().hex}_base"
        hardware = default_hardware_registry.get(evaluation.request.hardware_preset_id)
        investigation_id: str
        experiment_id: str
        investigation_id, experiment_id = self._execution_context(evaluation)

        if evaluation.request.controller_code:
            target_agent = DynamicControllerLoader.load_from_code(
                evaluation.request.controller_code, agent_id="baseline_target"
            )
        else:
            target_agent = ReferenceAutonomousAgent(agent_id="reference_baseline")

        session = SandboxSession(
            evaluation_id=evaluation.evaluation_id,
            run_id=run_id,
            scenario=evaluation.scenario,
            hardware_preset=hardware,
            target_agent=target_agent,
            seed=evaluation.request.seed,
            chaos_fault_overrides=evaluation.request.chaos_fault_overrides,
            event_callback=self._event_sink(event_callback),
            investigation_id=investigation_id,
            experiment_id=experiment_id,
        )

        run_result = session.execute(max_sim_time=max_sim_time)
        evaluation.baseline_run = run_result
        return run_result

    def execute_verification(
        self,
        evaluation_id: str,
        patched_code: str,
        agent_id: str = "verified_target",
        event_callback: Optional[Callable[[HarnessEvent], None]] = None,
    ) -> HarnessRun:
        """Execute the post-patch verification run on the identical seed and fault schedule.

        Args:
            evaluation_id: Identifier of the target HarnessEvaluation.
            patched_code: Python source code of the patched hardened controller.
            agent_id: Assigned agent identifier.
            event_callback: Optional per-execution sink for forwarding events to
                an owning investigation session.

        Returns:
            Executed verification HarnessRun.

        Raises:
            KeyError: If evaluation_id does not exist.
        """
        evaluation = self.get_evaluation(evaluation_id)
        if not evaluation:
            raise KeyError(f"Evaluation '{evaluation_id}' not found.")

        run_id = f"run_{uuid.uuid4().hex[:8]}_verify"
        hardware = default_hardware_registry.get(evaluation.request.hardware_preset_id)
        investigation_id: str
        experiment_id: str
        investigation_id, experiment_id = self._execution_context(evaluation)

        patched_agent = DynamicControllerLoader.load_from_code(patched_code, agent_id=agent_id)

        session = SandboxSession(
            evaluation_id=evaluation.evaluation_id,
            run_id=run_id,
            scenario=evaluation.scenario,
            hardware_preset=hardware,
            target_agent=patched_agent,
            seed=evaluation.request.seed,
            chaos_fault_overrides=evaluation.request.chaos_fault_overrides,
            event_callback=self._event_sink(event_callback),
            investigation_id=investigation_id,
            experiment_id=experiment_id,
        )

        verify_run: HarnessRun = session.execute()
        evaluation.verification_run = verify_run

        evaluation.final_result = self._build_verification_result(evaluation, verify_run)
        return verify_run

    @staticmethod
    def _build_verification_result(
        evaluation: HarnessEvaluation, verify_run: HarnessRun
    ) -> HarnessEvaluationResult:
        """Build the three-pillar verification result from baseline and verify runs."""
        baseline_run: Optional[HarnessRun] = evaluation.baseline_run
        base_violations: int = len(baseline_run.violations) if baseline_run else 0
        verify_violations: int = len(verify_run.violations)
        base_clearance: float = (
            baseline_run.metrics.get("min_clearance", 0.0) if baseline_run else 0.0
        )
        verify_clearance: float = verify_run.metrics.get("min_clearance", 0.0)
        safety_passed: bool = (
            verify_violations == 0
            and verify_run.status != HarnessRunStatus.SAFETY_VIOLATION
        )
        health_passed: bool = (
            verify_run.controller_health == ControllerHealth.HEALTHY
            and verify_run.status != HarnessRunStatus.CONTROLLER_CRASH
        )
        behavior_passed: bool = (
            verify_run.distance_traveled_m > 0.5 or verify_run.task_completed
        )

        verdict: VerificationVerdict
        if not safety_passed:
            verdict = VerificationVerdict.SAFETY_VIOLATION
        elif not health_passed:
            verdict = VerificationVerdict.CONTROLLER_CRASHED
        elif not behavior_passed:
            verdict = VerificationVerdict.TASK_INCOMPLETE
        else:
            verdict = VerificationVerdict.VERIFIED_SAFE
        is_safe: bool = verdict == VerificationVerdict.VERIFIED_SAFE
        return HarnessEvaluationResult(
            evaluation_id=evaluation.evaluation_id,
            verdict=verdict,
            is_safe_under_test_conditions=is_safe,
            safety_pillar_passed=safety_passed,
            behavior_pillar_passed=behavior_passed,
            runtime_health_pillar_passed=health_passed,
            baseline_passed=(base_violations == 0),
            verification_passed=is_safe,
            baseline_violations_count=base_violations,
            verification_violations_count=verify_violations,
            min_clearance_baseline=base_clearance,
            min_clearance_verified=verify_clearance,
            improvement_summary=(
                f"3-Pillar Verification: {verdict.value} (Safety: {'PASS' if safety_passed else 'FAIL'}, "
                f"Behavior: {'PASS' if behavior_passed else 'FAIL'}, Runtime Health: {'PASS' if health_passed else 'FAIL'}). "
                f"Violations reduced from {base_violations} to {verify_violations}. "
                f"Min clearance improved from {base_clearance:.2f}m to {verify_clearance:.2f}m."
            ),
        )


# Global RunManager singleton
default_run_manager = RunManager()

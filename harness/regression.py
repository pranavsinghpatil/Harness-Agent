"""Small deterministic regression suite for approved investigation patches."""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from harness.models.evaluation import ControllerHealth, HarnessRun, HarnessRunStatus
from harness.models.events import HarnessEvent
from harness.orchestration.run_manager import RunManager


class RegressionSuiteRunner:
    """Replay discovered experiment schedules against an approved controller patch."""

    def __init__(self, run_manager: RunManager) -> None:
        self.run_manager = run_manager

    @staticmethod
    def _passed(run: HarnessRun) -> bool:
        """Apply the same safety, health, and progress gate used by verification."""
        return (
            not run.violations
            and run.status not in {HarnessRunStatus.SAFETY_VIOLATION, HarnessRunStatus.CONTROLLER_CRASH}
            and run.controller_health == ControllerHealth.HEALTHY
            and (run.task_completed or run.distance_traveled_m > 0.5)
        )

    @classmethod
    def _case(cls, evaluation_id: str, run: HarnessRun) -> dict[str, Any]:
        """Build a compact regression result without duplicating telemetry frames."""
        return {
            "evaluation_id": evaluation_id,
            "run_id": run.run_id,
            "passed": cls._passed(run),
            "status": run.status.value,
            "violations_count": len(run.violations),
            "trace_hash": run.trace_hash,
        }

    def run(
        self,
        evaluation_ids: Iterable[str],
        patched_code: str,
        event_callback: Optional[Callable[[HarnessEvent], None]] = None,
        max_sim_time: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Replay each retained experiment evaluation with the approved patch.

        Args:
            evaluation_ids: Evaluation IDs produced by the investigation planner.
            patched_code: Controller source code approved for regression testing.
            event_callback: Optional canonical event sink for live session streaming.
            max_sim_time: Optional deterministic simulation bound per replay.

        Returns:
            Compact ordered regression case results.

        Raises:
            KeyError: If an evaluation was evicted before regression started.
        """
        cases: list[dict[str, Any]] = []
        for evaluation_id in evaluation_ids:
            run: HarnessRun = self.run_manager.execute_verification(
                evaluation_id=evaluation_id,
                patched_code=patched_code,
                agent_id="regression_target",
                event_callback=event_callback,
                max_sim_time=max_sim_time,
            )
            cases.append(self._case(evaluation_id, run))
        return cases

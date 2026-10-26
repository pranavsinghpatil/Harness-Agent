"""Deterministic replay engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from universal_harness.case.schema import FailureCase
from universal_harness.runner.executor import ExecutionResult
from universal_harness.runner.sandbox import ExecutionSandbox


@dataclass(frozen=True)
class ReplayTrial:
    """One replay trial iteration."""

    trial_index: int
    seed: int
    result: ExecutionResult
    reproduced: bool


@dataclass(frozen=True)
class ReplayReport:
    """Consolidated summary of deterministic replay trials."""

    case_id: str
    trials_count: int
    reproduced_count: int
    reproduction_rate: float
    is_deterministic: bool
    trace_hash: str
    mean_duration_ms: float
    verdict: str  # "deterministic_reproduction", "flaky_reproduction", "unreproduced"
    trials: List[ReplayTrial] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "trials_count": self.trials_count,
            "reproduced_count": self.reproduced_count,
            "reproduction_rate": round(self.reproduction_rate, 3),
            "is_deterministic": self.is_deterministic,
            "trace_hash": self.trace_hash,
            "mean_duration_ms": round(self.mean_duration_ms, 2),
            "verdict": self.verdict,
            "trials": [
                {
                    "trial_index": t.trial_index,
                    "seed": t.seed,
                    "reproduced": t.reproduced,
                    "duration_ms": t.result.duration_ms,
                    "trace_hash": t.result.trace_hash,
                    "outcome": t.result.outcome,
                }
                for t in self.trials
            ],
        }


class DeterministicReplayer:
    """Executes multiple deterministic replay trials to prove failure repeatability."""

    def __init__(self, sandbox: Optional[ExecutionSandbox] = None):
        self.sandbox = sandbox or ExecutionSandbox()

    def replay(
        self,
        case: FailureCase,
        trials: int = 5,
        vary_seeds: bool = False,
        perturbation_overrides: Optional[Dict[str, Any]] = None,
        command_override: Optional[str] = None,
    ) -> ReplayReport:
        """Run multiple trials to confirm deterministic reproduction."""
        if trials < 1:
            raise ValueError("trials must be >= 1")

        recorded_trials: List[ReplayTrial] = []
        hashes: List[str] = []
        durations: List[float] = []
        reproduced_count = 0

        base_seed = case.environment.seed

        for i in range(trials):
            current_seed = (base_seed + i) if vary_seeds else base_seed
            res = self.sandbox.run(
                case,
                perturbation_overrides=perturbation_overrides,
                command_override=command_override,
                seed_override=current_seed,
            )

            # Check if observed matches expected outcome
            is_reproduced = (res.outcome == case.expected.outcome)
            if case.expected.error_match:
                is_reproduced = is_reproduced and res.matched_error

            if is_reproduced:
                reproduced_count += 1

            trial = ReplayTrial(
                trial_index=i + 1,
                seed=current_seed,
                result=res,
                reproduced=is_reproduced,
            )
            recorded_trials.append(trial)
            hashes.append(res.trace_hash)
            durations.append(res.duration_ms)

        reproduction_rate = reproduced_count / trials
        unique_hashes = set(hashes)
        is_deterministic = (len(unique_hashes) == 1) if not vary_seeds else (reproduction_rate == 1.0)
        dominant_hash = hashes[0] if hashes else ""
        mean_duration = sum(durations) / len(durations) if durations else 0.0

        if reproduction_rate == 1.0:
            verdict = "deterministic_reproduction"
        elif reproduction_rate > 0.0:
            verdict = "flaky_reproduction"
        else:
            verdict = "unreproduced"

        return ReplayReport(
            case_id=case.id,
            trials_count=trials,
            reproduced_count=reproduced_count,
            reproduction_rate=reproduction_rate,
            is_deterministic=is_deterministic,
            trace_hash=dominant_hash,
            mean_duration_ms=mean_duration,
            verdict=verdict,
            trials=recorded_trials,
        )

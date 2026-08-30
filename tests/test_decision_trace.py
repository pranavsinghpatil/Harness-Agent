from harness.hypotheses import Hypothesis, HypothesisStatus
from harness.planning import ExperimentCandidate, ExperimentOutcome, ExperimentPhase
from harness.reasoning.decision_trace import DecisionTrace, DecisionTraceBuilder


def test_decision_trace_ranks_hypotheses_and_describes_counterfactual() -> None:
    candidate: ExperimentCandidate = ExperimentCandidate(
        experiment_id="exp_004",
        values={"camera.latency_ms": 180.0, "compute.availability": 0.67},
        phase=ExperimentPhase.INTERACTION,
        rationale="Test the suspected sensor and compute interaction.",
    )
    hypotheses: tuple[Hypothesis, ...] = (
        Hypothesis("H-camera", "Camera delay contributes to failure.", ("camera.latency_ms",), confidence=0.62),
        Hypothesis("H-interaction", "The combined delay causes failure.", ("camera.latency_ms", "compute.availability"), confidence=0.83, status=HypothesisStatus.SUPPORTED),
    )

    trace: DecisionTrace = DecisionTraceBuilder.build(
        candidate,
        ExperimentOutcome(passed=False, violation_count=1),
        hypotheses,
    )

    assert trace.action == "TEST_INTERACTION"
    assert trace.selected_hypothesis_id == "H-interaction"
    assert trace.hypothesis_ids == ("H-interaction", "H-camera")
    assert trace.information_gain_estimate == 1.0
    assert trace.next_action == "Run a controlled counterfactual for H-interaction."


def test_baseline_trace_has_no_hypothesis_and_sets_screening_action() -> None:
    candidate: ExperimentCandidate = ExperimentCandidate(
        experiment_id="exp_001",
        values={"camera.latency_ms": 0.0},
        phase=ExperimentPhase.BASELINE,
        rationale="Measure healthy behavior.",
    )

    trace: DecisionTrace = DecisionTraceBuilder.build(
        candidate,
        ExperimentOutcome(passed=True),
        (),
    )

    assert trace.selected_hypothesis_id is None
    assert trace.next_action == "Screen each perturbation dimension independently."

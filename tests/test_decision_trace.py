from harness.hypotheses import Hypothesis, HypothesisStatus
from harness.planning import ExperimentCandidate, ExperimentOutcome, ExperimentPhase
from harness.reasoning.decision_trace import DecisionTrace, DecisionTraceBuilder


def test_decision_trace_separates_beliefs_and_previews_scheduled_candidate() -> None:
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

    next_candidate: ExperimentCandidate = ExperimentCandidate(
        experiment_id="exp_005",
        values={"camera.latency_ms": 90.0},
        phase=ExperimentPhase.BOUNDARY,
        rationale="Narrow the observed boundary.",
    )
    trace: DecisionTrace = DecisionTraceBuilder.build(
        candidate=candidate,
        outcome=ExperimentOutcome(passed=False, violation_count=1),
        pre_execution_hypotheses=(hypotheses[0],),
        post_observation_hypotheses=hypotheses,
        next_candidate=next_candidate,
    )

    assert trace.action == "TEST_INTERACTION"
    assert trace.pre_execution_hypothesis_ids == ("H-camera",)
    assert trace.post_observation_hypothesis_ids == ("H-interaction", "H-camera")
    assert trace.post_observation_leading_hypothesis_id == "H-interaction"
    assert trace.information_gain_estimate == 1.0
    assert trace.next_experiment_id == "exp_005"
    assert trace.next_action.startswith("SCHEDULED: run exp_005")


def test_baseline_trace_has_no_hypothesis_and_sets_screening_action() -> None:
    candidate: ExperimentCandidate = ExperimentCandidate(
        experiment_id="exp_001",
        values={"camera.latency_ms": 0.0},
        phase=ExperimentPhase.BASELINE,
        rationale="Measure healthy behavior.",
    )

    trace: DecisionTrace = DecisionTraceBuilder.build(
        candidate=candidate,
        outcome=ExperimentOutcome(passed=True),
        pre_execution_hypotheses=(),
        post_observation_hypotheses=(),
        next_candidate=None,
    )

    assert trace.post_observation_leading_hypothesis_id is None
    assert trace.outcome_classification == "PASS"
    assert trace.next_experiment_id is None
    assert trace.next_action == "STOP: no further experiment is scheduled."


def test_decision_trace_preserves_non_safety_failure_classification() -> None:
    candidate: ExperimentCandidate = ExperimentCandidate(
        experiment_id="exp_error",
        values={},
        phase=ExperimentPhase.SCREEN,
        rationale="Run a screen.",
    )
    trace: DecisionTrace = DecisionTraceBuilder.build(
        candidate=candidate,
        outcome=ExperimentOutcome(
            passed=False,
            details={"execution_error": "TimeoutError", "execution_stage": "evaluation creation"},
        ),
        pre_execution_hypotheses=(),
        post_observation_hypotheses=(),
        next_candidate=None,
    )

    assert trace.outcome_classification == "EXECUTION_ERROR"
    assert trace.observation == "Investigator reported an execution error during evaluation creation."


def test_decision_trace_keeps_refuted_hypotheses_historical() -> None:
    candidate: ExperimentCandidate = ExperimentCandidate(
        experiment_id="exp_refuted",
        values={"camera.latency_ms": 100.0},
        phase=ExperimentPhase.SCREEN,
        rationale="Run an independent screen.",
    )
    refuted: Hypothesis = Hypothesis(
        "H-camera",
        "Camera delay is causal.",
        ("camera.latency_ms",),
        confidence=0.2,
        status=HypothesisStatus.REFUTED,
    )

    trace: DecisionTrace = DecisionTraceBuilder.build(
        candidate=candidate,
        outcome=ExperimentOutcome(passed=True),
        pre_execution_hypotheses=(refuted,),
        post_observation_hypotheses=(refuted,),
        next_candidate=None,
    )

    assert trace.post_observation_hypothesis_ids == ()
    assert trace.refuted_hypothesis_ids == ("H-camera",)
    assert trace.post_observation_leading_hypothesis_id is None

from harness.hypotheses import FalsificationPlan, Hypothesis, HypothesisEngine, HypothesisStatus
from harness.planning import EvidenceRecord, ExperimentCandidate, ExperimentOutcome, ExperimentPhase, PlannerDimension


DIMENSIONS: tuple[PlannerDimension, ...] = (
    PlannerDimension("camera.latency_ms", 0.0, 0.0, 400.0),
    PlannerDimension("compute.availability", 1.0, 0.4, 1.0, higher_is_worse=False),
)


def _record(experiment_id: str, values: dict[str, float], passed: bool, phase: ExperimentPhase = ExperimentPhase.SCREEN) -> EvidenceRecord:
    return EvidenceRecord(
        ExperimentCandidate(experiment_id, values, phase, "test"),
        ExperimentOutcome(passed=passed),
    )


def test_engine_tracks_support_and_falsification() -> None:
    engine: HypothesisEngine = HypothesisEngine()
    engine.observe(_record("exp_001", {"camera.latency_ms": 400.0, "compute.availability": 1.0}, False), DIMENSIONS)
    hypothesis: Hypothesis | None = engine.strongest()
    assert hypothesis is not None
    assert hypothesis.hypothesis_id == "H-camera_latency_ms"
    assert hypothesis.status == HypothesisStatus.SUPPORTED

    plan: FalsificationPlan | None = engine.propose_falsification(
        _record("exp_002", {"camera.latency_ms": 400.0, "compute.availability": 0.4}, False, ExperimentPhase.INTERACTION),
        DIMENSIONS,
    )
    assert plan is not None
    assert plan.values["camera.latency_ms"] == 0.0
    assert plan.values["compute.availability"] == 0.4


def test_safe_result_contradicts_single_variable_hypothesis() -> None:
    engine: HypothesisEngine = HypothesisEngine()
    engine.observe(_record("exp_001", {"camera.latency_ms": 400.0, "compute.availability": 1.0}, False), DIMENSIONS)
    engine.observe(_record("exp_002", {"camera.latency_ms": 100.0, "compute.availability": 1.0}, True), DIMENSIONS)
    hypothesis: Hypothesis | None = engine.strongest()
    assert hypothesis is not None
    assert hypothesis.contradicting_experiment_ids == ("exp_002",)
    assert hypothesis.status == HypothesisStatus.ACTIVE


def test_baseline_does_not_create_hypothesis() -> None:
    engine: HypothesisEngine = HypothesisEngine()
    engine.observe(_record("exp_001", {"camera.latency_ms": 0.0, "compute.availability": 1.0}, True, ExperimentPhase.BASELINE), DIMENSIONS)
    assert engine.hypotheses == ()


def test_safe_only_screen_does_not_create_refuted_hypothesis() -> None:
    engine: HypothesisEngine = HypothesisEngine()
    engine.observe(_record("exp_001", {"camera.latency_ms": 100.0, "compute.availability": 1.0}, True), DIMENSIONS)

    assert engine.hypotheses == ()
    assert engine.strongest() is None


def test_safe_interaction_contradicts_matching_interaction_hypothesis() -> None:
    engine: HypothesisEngine = HypothesisEngine()
    failed: EvidenceRecord = _record(
        "exp_001",
        {"camera.latency_ms": 400.0, "compute.availability": 0.4},
        False,
        ExperimentPhase.INTERACTION,
    )
    safe: EvidenceRecord = _record(
        "exp_002",
        {"camera.latency_ms": 400.0, "compute.availability": 0.4},
        True,
        ExperimentPhase.INTERACTION,
    )

    engine.observe(failed, DIMENSIONS)
    engine.observe(safe, DIMENSIONS)

    hypothesis: Hypothesis | None = engine.strongest()
    assert hypothesis is not None
    assert hypothesis.hypothesis_id == "H-camera_latency_ms+compute_availability"
    assert hypothesis.contradicting_experiment_ids == ("exp_002",)

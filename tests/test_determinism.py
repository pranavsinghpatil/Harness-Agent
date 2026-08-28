"""Tests for deterministic simulation execution and bit-exact trace reproducibility."""

from sandbox.api.tools import create_scenario, run_episode, replay_run


def test_bit_exact_determinism() -> None:
    spec = {
        "id": "det_test_scenario",
        "name": "Determinism Verification",
        "seed": 8888,
        "max_sim_time": 4.0,
        "world": {
            "width": 50.0,
            "height": 50.0,
            "goal": [30.0, 25.0],
            "initial_state": {"x": 5.0, "y": 25.0, "heading": 0.0, "velocity": 0.0},
            "obstacles": [
                {"id": "obs_1", "type": "static", "x": 20.0, "y": 25.0, "width": 1.5, "length": 1.5}
            ],
        },
        "fault_schedule": [],
    }

    sc = create_scenario(spec)

    # Run 1
    manifest_1, frames_1 = run_episode(scenario=sc, seed=8888)
    # Run 2
    manifest_2, frames_2 = run_episode(scenario=sc, seed=8888)

    # Hashes must be identical
    assert manifest_1.trace_hash != ""
    assert manifest_1.trace_hash == manifest_2.trace_hash
    assert manifest_1.sim_duration_seconds == manifest_2.sim_duration_seconds
    assert manifest_1.total_steps == manifest_2.total_steps
    assert len(frames_1) == len(frames_2)

    # Replay test
    replayed_manifest, _, comparison = replay_run(manifest_1.run_id)
    assert comparison.is_bit_exact_match is True

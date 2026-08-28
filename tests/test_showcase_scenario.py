"""Tests for the Golden Showcase Scenario (Safe Baseline vs Perturbed Hardware Failure)."""

import yaml
from pathlib import Path
from sandbox.api.tools import create_scenario, run_episode, replay_run
from sandbox.core.episode import EpisodeStatus


def test_showcase_normal_baseline():
    with open("scenarios/generated/showcase_normal.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    sc = create_scenario(spec)
    manifest, frames = run_episode(scenario=sc, seed=1337)

    # In the safe baseline, there should be no collisions
    fatal_violations = [
        v for f in frames for v in f.new_violations if v["severity"] == "fatal"
    ]
    assert len(fatal_violations) == 0
    assert manifest.status in ("completed_safe", "timeout", "goal_reached")


def test_showcase_perturbed_safety_violation_and_replay():
    with open("scenarios/generated/showcase_perturbed.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    sc = create_scenario(spec)
    manifest, frames = run_episode(scenario=sc, seed=1337)

    # In the perturbed run, compound perception and actuation faults trigger violations
    all_violations = [v for f in frames for v in f.new_violations]
    assert len(all_violations) > 0, "Perturbed scenario must detect safety violations"

    # Replay must reproduce the exact same trace
    replayed_manifest, _, comparison = replay_run(manifest.run_id)
    assert comparison.is_bit_exact_match is True, "Unsafe run must be replayable with 100% determinism"
    assert replayed_manifest.violations_count == manifest.violations_count

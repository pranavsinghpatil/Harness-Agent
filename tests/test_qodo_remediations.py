"""Regression and invariant tests for Qodo AI review remediations."""

import pytest
from sandbox.world.geometry import Vec2D, Polygon2D, Segment2D
from sandbox.world.map import WorldMap
from sandbox.world.entities import StaticObstacle
from sandbox.physics.collision import CollisionDetector
from sandbox.api.tools import create_scenario, run_episode, replay_run
from sandbox.telemetry.replay import DeterministicReplayer
from target_agents.reference_agent.agent import ReferenceAutonomousAgent
from sandbox.transport.bus import TransportBus
from sandbox.core.rng import RngManager
from sandbox.faults.controller import FaultController
from sandbox.faults.schema import FaultDefinition
from sandbox.actuators.pipeline import ActuatorPipeline
from sandbox.hardware.scheduler import VirtualEdgeScheduler
from sandbox.hardware.profile import HardwareProfile


def test_footprint_clearance_and_boundary_walls() -> None:
    """Verifies that clearance accounts for vehicle footprint and walls rather than only centroid."""
    world: WorldMap = WorldMap(width=50.0, height=50.0)
    # Vehicle near west boundary wall (x=0)
    # Vehicle box: center=(1.5, 25.0), width=1.0, length=2.0 (half-length = 1.0)
    # Minimum distance from vehicle edge (x=0.5) to wall (x=0) should be 0.5m, not 1.5m
    v_poly = Polygon2D.from_box(center=Vec2D(1.5, 25.0), width=1.0, length=2.0, heading=0.0)
    res = CollisionDetector.evaluate(v_poly, world)

    assert not res.is_collision
    assert abs(res.min_clearance - 0.5) < 1e-4
    assert res.closest_entity_id == "boundary_wall_3"  # West wall


def test_crossing_wall_collision_detected() -> None:
    """Verifies that a wall bisecting/crossing the vehicle polygon returns 0 distance and collision."""
    world: WorldMap = WorldMap(width=50.0, height=50.0)
    # Vehicle centered at (0.0, 25.0), straddling the West boundary wall at x=0
    v_poly = Polygon2D.from_box(center=Vec2D(0.0, 25.0), width=2.0, length=4.0, heading=0.0)
    res = CollisionDetector.evaluate(v_poly, world)

    assert res.is_collision
    assert res.min_clearance == 0.0
    assert res.collided_entity_id == "boundary_wall_3"


def test_scenario_seed_override_isolation() -> None:
    """Verifies that overriding the seed in run_episode does not mutate registered template."""
    raw_spec = {
        "id": "seed_isolation_test",
        "name": "Seed Isolation Test",
        "seed": 42,
        "world": {
            "width": 50.0,
            "height": 50.0,
            "initial_state": {"x": 4.0, "y": 25.0, "heading": 0.0, "velocity": 0.0},
            "goal": [40.0, 25.0],
            "obstacles": [],
        },
    }
    sc = create_scenario(raw_spec)
    assert sc.seed == 42

    # Run with override seed 999
    manifest, _ = run_episode("seed_isolation_test", seed=999, max_sim_time=0.5)
    assert manifest.seed == 999

    # Check that registered scenario is still 42
    sc_after = create_scenario(raw_spec)
    assert sc_after.seed == 42


def test_reference_agent_estimator_initial_pose() -> None:
    """Verifies that the reference agent estimator resets to true starting pose."""
    agent = ReferenceAutonomousAgent()
    agent.reset(goal_x=45.0, goal_y=25.0, initial_x=10.0, initial_y=20.0, initial_heading=0.5)

    assert agent.estimator.x == 10.0
    assert agent.estimator.y == 20.0
    assert agent.estimator.heading == 0.5


def test_transport_bus_baseline_recovery() -> None:
    """Verifies that TransportBus channels restore default latency and jitter on reset."""
    rng_mgr = RngManager(master_seed=123)
    bus = TransportBus(rng=rng_mgr.get("transport"))
    ch = bus.register_channel("sensor.lidar", base_latency_s=0.015, jitter_std_s=0.002)

    # Corrupt/mutate channel
    ch.base_latency_s = 0.300
    ch.jitter_std_s = 0.050
    ch.packet_loss_rate = 0.8

    bus.reset()
    assert ch.base_latency_s == 0.015
    assert ch.jitter_std_s == 0.002
    assert ch.packet_loss_rate == 0.0


def test_replay_comparison_detects_hash_and_clearance_mismatch() -> None:
    """Verifies that DeterministicReplayer flags mismatches on hash or clearance."""
    orig_frames = [
        {"vehicle_state": {"x": 1.0, "y": 2.0, "velocity": 3.0, "heading": 0.0, "acceleration": 0.0, "steer_angle": 0.0}, "min_clearance": 5.0, "active_faults": []}
    ]
    rep_frames = [
        {"vehicle_state": {"x": 1.0, "y": 2.0, "velocity": 3.0, "heading": 0.0, "acceleration": 0.0, "steer_angle": 0.0}, "min_clearance": 2.0, "active_faults": []}
    ]

    res = DeterministicReplayer.compare_traces(orig_frames, rep_frames, orig_hash="aaa", rep_hash="bbb")
    assert not res.is_bit_exact_match
    assert "Trace hash mismatch" in res.difference_details


def test_overlapping_faults_preservation() -> None:
    """Verifies that ending an earlier overlapping fault preserves active effects from remaining faults."""
    controller = FaultController()
    # Fault 1: brake reduced to 0.5 from t=1.0 to t=3.0
    f1 = FaultDefinition(id="fault_1", target="actuator.brake", type="reduced_effectiveness", start_time=1.0, duration=2.0, parameters={"factor": 0.5})
    # Fault 2: brake reduced to 0.2 from t=2.0 to t=5.0
    f2 = FaultDefinition(id="fault_2", target="actuator.brake", type="reduced_effectiveness", start_time=2.0, duration=3.0, parameters={"factor": 0.2})
    controller.set_faults([f1, f2])

    rng_mgr = RngManager(master_seed=42)
    actuators = ActuatorPipeline(rng=rng_mgr.get("actuator"))
    transport = TransportBus(rng=rng_mgr.get("transport"))
    hardware = VirtualEdgeScheduler(HardwareProfile())
    sensors: dict[str, Any] = {}

    # At t=1.5: only f1 is active -> factor = 0.5
    controller.update(1.5, sensors, transport, hardware, actuators)
    assert actuators.brake_effectiveness_factor == 0.5

    # At t=2.5: both f1 and f2 are active -> factor = 0.2
    controller.update(2.5, sensors, transport, hardware, actuators)
    assert actuators.brake_effectiveness_factor == 0.2

    # At t=3.5: f1 has ended, f2 is STILL active -> factor must remain 0.2, NOT reset to 1.0!
    controller.update(3.5, sensors, transport, hardware, actuators)
    assert actuators.brake_effectiveness_factor == 0.2

    # At t=5.5: both faults ended -> factor restored to 1.0
    controller.update(5.5, sensors, transport, hardware, actuators)
    assert actuators.brake_effectiveness_factor == 1.0

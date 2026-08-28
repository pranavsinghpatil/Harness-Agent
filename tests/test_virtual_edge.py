"""Tests for virtual edge compute scheduling, task deadlines, and thermal throttling."""

from sandbox.hardware.profile import HardwareProfile, ComputeTask, SchedulerPolicy
from sandbox.hardware.scheduler import VirtualEdgeScheduler


def test_edge_scheduler_deadline_miss():
    profile = HardwareProfile(cpu_capacity_units_per_sec=100.0)
    scheduler = VirtualEdgeScheduler(profile)

    # Task requiring 50 units (0.5s of compute), but deadline is at t = 0.2s
    task = ComputeTask(
        task_id="heavy_perception",
        name="perception_yolo",
        compute_cost_units=50.0,
        deadline=0.20,
    )
    scheduler.submit_task(task)

    # Step for 0.1s (provides 10 units of compute)
    scheduler.step(sim_time=0.10, dt=0.10)
    assert not task.is_completed

    # Step to 0.3s (provides 20 units of compute -> total 30, still not done, sim_time > deadline)
    scheduler.step(sim_time=0.30, dt=0.20)
    assert task.is_deadline_missed is True
    assert scheduler.metrics.total_deadline_misses >= 1


def test_thermal_throttling_curve():
    profile = HardwareProfile(
        cpu_capacity_units_per_sec=100.0,
        thermal_ambient_temp=35.0,
        thermal_throttle_temp=75.0,
        thermal_heat_coeff=0.2,  # Faster heating for test
    )
    scheduler = VirtualEdgeScheduler(profile)

    # Submit many tasks to keep CPU 100% loaded
    for i in range(10):
        scheduler.submit_task(ComputeTask(task_id=f"t_{i}", name="load", compute_cost_units=500.0))

    # Run for 15 seconds of high load
    for step_i in range(150):
        scheduler.step(sim_time=step_i * 0.1, dt=0.1)

    assert scheduler.metrics.temperature_celsius >= 75.0
    assert scheduler.profile.is_throttled is True
    assert scheduler.profile.effective_cpu_ratio < 1.0

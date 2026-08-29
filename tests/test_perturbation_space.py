"""Tests for bounded experiment compilation and CPU availability perturbations."""

from __future__ import annotations

from typing import Any

import pytest

from sandbox.experiments import PerturbationDimension, PerturbationSpace, default_perturbation_space
from sandbox.faults.controller import FaultController
from sandbox.faults.schema import FaultDefinition
from sandbox.api.environment import SandboxEnvironment


def test_default_space_compiles_sorted_non_baseline_faults() -> None:
    space: PerturbationSpace = default_perturbation_space()

    overrides: list[dict[str, Any]] = space.build_fault_overrides(
        {
            "actuator.brake.effectiveness": 0.4,
            "sensor.camera.latency_ms": 310.0,
            "hardware.compute.availability": 0.6,
        },
        experiment_id="exp_007",
    )

    assert [fault["id"] for fault in overrides] == [
        "exp_007:actuator.brake.effectiveness",
        "exp_007:hardware.compute.availability",
        "exp_007:sensor.camera.latency_ms",
    ]
    assert overrides[1]["parameters"] == {"factor": 0.6}


def test_baseline_values_are_not_injected() -> None:
    space: PerturbationSpace = default_perturbation_space()

    assert space.build_fault_overrides(
        {
            "sensor.camera.latency_ms": 0.0,
            "hardware.compute.availability": 1.0,
        },
        experiment_id="baseline",
    ) == []


def test_dimension_rejects_out_of_range_values() -> None:
    dimension: PerturbationDimension = PerturbationDimension(
        id="camera_latency",
        target="transport.camera",
        fault_type="added_latency",
        parameter_name="latency_ms",
        minimum=0.0,
        maximum=100.0,
        baseline=0.0,
    )

    with pytest.raises(ValueError, match="outside"):
        dimension.to_fault(101.0, "exp_bad")


def test_dimension_rejects_unknown_runtime_fault_parameter() -> None:
    with pytest.raises(ValueError, match="Unsupported fault parameter"):
        PerturbationDimension(
            id="unknown_fault",
            target="transport.camera",
            fault_type="added_latency",
            parameter_name="ignored_parameter",
            minimum=0.0,
            maximum=1.0,
            baseline=0.0,
        )


@pytest.mark.parametrize(
    ("target", "fault_type", "parameter_name"),
    [
        ("sensor.lidar", "sector_loss", "min_angle_rad"),
        ("sensor.position", "position_jump", "offset_x"),
    ],
)
def test_dimension_rejects_coupled_faults_without_atomic_parameters(
    target: str, fault_type: str, parameter_name: str
) -> None:
    with pytest.raises(ValueError, match="Unsupported fault parameter"):
        PerturbationDimension(
            id="coupled_fault",
            target=target,
            fault_type=fault_type,
            parameter_name=parameter_name,
            minimum=0.0,
            maximum=1.0,
            baseline=0.0,
        )


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf"), float("nan")])
def test_dimension_rejects_non_finite_bounds_and_values(bad_value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        PerturbationDimension(
            id="non_finite",
            target="transport.camera",
            fault_type="added_latency",
            parameter_name="latency_ms",
            minimum=0.0,
            maximum=100.0,
            baseline=bad_value,
        )

    dimension: PerturbationDimension = PerturbationDimension(
        id="finite_dimension",
        target="transport.camera",
        fault_type="added_latency",
        parameter_name="latency_ms",
        minimum=0.0,
        maximum=100.0,
        baseline=0.0,
    )
    with pytest.raises(ValueError, match="finite"):
        dimension.validate_value(bad_value)


def test_cpu_availability_fault_changes_scheduler_capacity_and_reverts() -> None:
    env: SandboxEnvironment = SandboxEnvironment()
    controller: FaultController = FaultController()
    fault: FaultDefinition = default_perturbation_space().get_dimension(
        "hardware.compute.availability"
    ).to_fault(0.4, "exp_cpu")

    controller.set_faults([fault])
    controller.update(2.0, env.sensors, env.transport, env.hardware, env.actuators)
    assert env.hardware.profile.cpu_availability_ratio == 0.4

    controller.update(6.0, env.sensors, env.transport, env.hardware, env.actuators)
    assert env.hardware.profile.cpu_availability_ratio == 1.0


def test_replacing_schedule_reverts_active_hardware_fault() -> None:
    env: SandboxEnvironment = SandboxEnvironment()
    controller: FaultController = env.faults
    fault: FaultDefinition = default_perturbation_space().get_dimension(
        "hardware.compute.availability"
    ).to_fault(0.4, "exp_replace")
    controller.set_faults([fault])
    controller.update(2.0, env.sensors, env.transport, env.hardware, env.actuators)
    assert env.hardware.profile.cpu_availability_ratio == 0.4

    controller.clear_active_faults(env.sensors, env.transport, env.hardware, env.actuators)
    controller.set_faults([])
    assert env.hardware.profile.cpu_availability_ratio == 1.0


def test_idle_reduced_compute_availability_does_not_report_utilization() -> None:
    env: SandboxEnvironment = SandboxEnvironment()
    env.hardware.profile.cpu_availability_ratio = 0.4

    env.hardware.step(sim_time=0.0, dt=0.1)

    assert env.hardware.metrics.cpu_utilization == 0.0

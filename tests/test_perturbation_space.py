"""Tests for bounded experiment compilation and CPU availability perturbations."""

from __future__ import annotations

import pytest

from sandbox.experiments import PerturbationDimension, default_perturbation_space
from sandbox.faults.controller import FaultController
from sandbox.api.environment import SandboxEnvironment


def test_default_space_compiles_sorted_non_baseline_faults() -> None:
    space = default_perturbation_space()

    overrides = space.build_fault_overrides(
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
    space = default_perturbation_space()

    assert space.build_fault_overrides(
        {
            "sensor.camera.latency_ms": 0.0,
            "hardware.compute.availability": 1.0,
        },
        experiment_id="baseline",
    ) == []


def test_dimension_rejects_out_of_range_values() -> None:
    dimension = PerturbationDimension(
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


def test_cpu_availability_fault_changes_scheduler_capacity_and_reverts() -> None:
    env = SandboxEnvironment()
    controller = FaultController()
    fault = default_perturbation_space().get_dimension(
        "hardware.compute.availability"
    ).to_fault(0.4, "exp_cpu")

    controller.set_faults([fault])
    controller.update(2.0, env.sensors, env.transport, env.hardware, env.actuators)
    assert env.hardware.profile.cpu_availability_ratio == 0.4

    controller.update(6.0, env.sensors, env.transport, env.hardware, env.actuators)
    assert env.hardware.profile.cpu_availability_ratio == 1.0

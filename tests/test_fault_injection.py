"""Tests for declarative fault injection across sensors, transport, and actuators."""

from sandbox.faults.schema import FaultDefinition
from sandbox.faults.controller import FaultController
from sandbox.sensors.lidar import LidarSensor
from sandbox.transport.bus import TransportBus
from sandbox.hardware.scheduler import VirtualEdgeScheduler
from sandbox.actuators.pipeline import ActuatorPipeline


def test_fault_lifecycle() -> None:
    controller = FaultController()
    f1 = FaultDefinition(
        id="f_dropout",
        target="sensor.lidar",
        type="dropout",
        start_time=1.0,
        duration=2.0,
    )
    controller.add_fault(f1)

    lidar = LidarSensor()
    sensors = {"lidar": lidar}
    transport = TransportBus()
    hardware = VirtualEdgeScheduler()
    actuators = ActuatorPipeline()

    # At t = 0.5s -> Fault not active
    controller.update(0.5, sensors, transport, hardware, actuators)
    assert not lidar.dropout_active
    assert "f_dropout" not in controller.get_active_fault_ids()

    # At t = 1.5s -> Fault active
    controller.update(1.5, sensors, transport, hardware, actuators)
    assert lidar.dropout_active is True
    assert "f_dropout" in controller.get_active_fault_ids()

    # At t = 3.5s -> Fault ended and reverted
    controller.update(3.5, sensors, transport, hardware, actuators)
    assert lidar.dropout_active is False
    assert "f_dropout" not in controller.get_active_fault_ids()


def test_actuator_brake_fault() -> None:
    controller = FaultController()
    f_brake = FaultDefinition(
        id="f_brake_fade",
        target="actuator.brake",
        type="reduced_effectiveness",
        start_time=0.5,
        duration=1.0,
        parameters={"factor": 0.25},
    )
    controller.add_fault(f_brake)

    sensors = {}
    transport = TransportBus()
    hardware = VirtualEdgeScheduler()
    actuators = ActuatorPipeline()

    controller.update(0.7, sensors, transport, hardware, actuators)
    assert actuators.brake_effectiveness_factor == 0.25

    controller.update(2.0, sensors, transport, hardware, actuators)
    assert actuators.brake_effectiveness_factor == 1.0

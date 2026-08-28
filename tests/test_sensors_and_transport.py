"""Tests for asynchronous sensor models and transport message buses."""

import numpy as np
from sandbox.world.geometry import Vec2D
from sandbox.world.entities import StaticObstacle
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState
from sandbox.sensors.lidar import LidarSensor
from sandbox.sensors.imu import ImuSensor
from sandbox.sensors.encoder import EncoderSensor
from sandbox.sensors.position import PositionSensor
from sandbox.sensors.camera import CameraSensor
from sandbox.transport.bus import TransportBus


def test_lidar_sensor_raycast() -> None:
    world_map = WorldMap(width=50.0, height=50.0)
    # Obstacle 5 meters directly in front (+X) of rover at (10, 25)
    world_map.add_static_obstacle(StaticObstacle(id="wall_1", position=Vec2D(15.0, 25.0), width=1.0, length=2.0))

    state = VehicleState(position=Vec2D(10.0, 25.0), heading=0.0)
    lidar = LidarSensor(num_rays=19, fov_deg=180.0, max_range=20.0, noise_std=0.0)

    packet = lidar.sample(sim_time=0.1, state=state, world_map=world_map)
    assert packet is not None
    assert packet.validity is True
    # Center ray should detect the obstacle roughly ~4.0 - 5.0 meters away
    assert packet.payload["closest_range"] < 5.0


def test_transport_latency_and_delivery() -> None:
    bus = TransportBus()
    # Register channel with 50 ms latency
    bus.register_channel("sensor.lidar", base_latency_s=0.050, jitter_std_s=0.0)

    payload = {"data": "test_scan"}
    # Send packet at t = 1.00s
    bus.send("sensor.lidar", payload, current_sim_time=1.00)

    # At t = 1.02s, packet should NOT be delivered yet
    due_early = bus.deliver_all_due(current_sim_time=1.02)
    assert "sensor.lidar" not in due_early

    # At t = 1.05s, packet should be delivered
    due_ontime = bus.deliver_all_due(current_sim_time=1.05)
    assert "sensor.lidar" in due_ontime
    assert due_ontime["sensor.lidar"][0] == payload


def test_transport_packet_loss() -> None:
    rng = np.random.default_rng(42)
    bus = TransportBus(rng=rng)
    channel = bus.register_channel("sensor.lossy", base_latency_s=0.01, packet_loss_rate=1.0)  # 100% loss

    sent = bus.send("sensor.lossy", {"seq": 1}, current_sim_time=0.0)
    assert sent is False
    assert channel.total_dropped == 1

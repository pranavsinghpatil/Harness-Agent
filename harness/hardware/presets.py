"""Declarative edge compute hardware presets for D-Robotics RDK X5, Jetson Orin Nano, and Raspberry Pi 5."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict
from sandbox.hardware.profile import HardwareProfile, SchedulerPolicy


@dataclass
class HardwarePreset:
    """Complete declarative configuration of a physical target hardware board.

    Attributes:
        id: Unique machine-readable preset identifier (e.g. 'RDK_X5').
        name: Human-readable display name.
        vendor: Board manufacturer (e.g. 'D-Robotics', 'NVIDIA', 'Raspberry Pi').
        description: Architecture details (cores, frequency, memory, NPU/BPU).
        profile: VirtualEdgeScheduler resource constraints and thermal model.
        transport_latencies: Baseline latencies (seconds) for hardware buses.
        sensor_bandwidth_limits: Maximum polling frequencies and buffer sizes.
        bpu_acceleration_factor: Compute speedup for perception tasks if NPU/BPU present.
    """
    id: str
    name: str
    vendor: str
    description: str
    profile: HardwareProfile
    transport_latencies: Dict[str, Dict[str, float]] = field(default_factory=dict)
    sensor_bandwidth_limits: Dict[str, float] = field(default_factory=dict)
    bpu_acceleration_factor: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize hardware preset for UI dropdowns and API clients."""
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "description": self.description,
            "cpu_capacity": self.profile.cpu_capacity_units_per_sec,
            "memory_mb": self.profile.memory_total_mb,
            "scheduler_policy": self.profile.scheduler_policy.value,
            "thermal_ambient": self.profile.thermal_ambient_temp,
            "thermal_throttle_temp": self.profile.thermal_throttle_temp,
            "bpu_acceleration": self.bpu_acceleration_factor,
            "transport_latencies": self.transport_latencies,
        }


# ============================================================================
# 1. D-Robotics RDK X5 (Primary Flagship Edge Preset)
# ============================================================================
# Specs: Quad-core ARM Cortex-A55 @ 1.5GHz, 8GB LPDDR4x, 10 TOPS BPU (Bayes Processing Unit)
# Thermal: 12W TDP, throttle threshold 85°C.
RDK_X5_PRESET = HardwarePreset(
    id="RDK_X5",
    name="D-Robotics RDK X5",
    vendor="D-Robotics",
    description="Quad-Core ARM Cortex-A55 @ 1.5GHz, 10 TOPS BPU, 8GB LPDDR4x, 12W TDP",
    profile=HardwareProfile(
        cpu_capacity_units_per_sec=150.0,
        memory_total_mb=8192.0,
        scheduler_policy=SchedulerPolicy.FIFO,
        max_queue_depth=30,
        thermal_ambient_temp=32.0,
        thermal_throttle_temp=85.0,
        thermal_heat_coeff=0.045,
        thermal_cool_coeff=0.022,
    ),
    transport_latencies={
        "can_bus": {"base_latency_s": 0.0012, "jitter_std_s": 0.0002, "packet_loss": 0.0},
        "camera_mipi": {"base_latency_s": 0.015, "jitter_std_s": 0.002, "packet_loss": 0.0},
        "lidar_serial": {"base_latency_s": 0.005, "jitter_std_s": 0.001, "packet_loss": 0.0},
        "imu_i2c": {"base_latency_s": 0.0008, "jitter_std_s": 0.0001, "packet_loss": 0.0},
    },
    sensor_bandwidth_limits={"lidar_max_hz": 15.0, "camera_max_hz": 30.0, "imu_max_hz": 100.0},
    bpu_acceleration_factor=2.2,  # BPU accelerates perception inference
)

# ============================================================================
# 2. NVIDIA Jetson Orin Nano
# ============================================================================
# Specs: 6-core ARM Cortex-A78AE @ 1.5GHz, 8GB LPDDR5, 40 TOPS Ampere GPU
JETSON_ORIN_NANO_PRESET = HardwarePreset(
    id="JETSON_ORIN_NANO",
    name="NVIDIA Jetson Orin Nano",
    vendor="NVIDIA",
    description="6-Core ARM Cortex-A78AE @ 1.5GHz, 40 TOPS Ampere GPU, 8GB LPDDR5, 15W TDP",
    profile=HardwareProfile(
        cpu_capacity_units_per_sec=260.0,
        memory_total_mb=8192.0,
        scheduler_policy=SchedulerPolicy.EDF,
        max_queue_depth=50,
        thermal_ambient_temp=35.0,
        thermal_throttle_temp=80.0,
        thermal_heat_coeff=0.075,
        thermal_cool_coeff=0.018,
    ),
    transport_latencies={
        "can_bus": {"base_latency_s": 0.0010, "jitter_std_s": 0.0001, "packet_loss": 0.0},
        "camera_mipi": {"base_latency_s": 0.012, "jitter_std_s": 0.0015, "packet_loss": 0.0},
        "lidar_serial": {"base_latency_s": 0.004, "jitter_std_s": 0.0008, "packet_loss": 0.0},
        "imu_i2c": {"base_latency_s": 0.0005, "jitter_std_s": 0.0001, "packet_loss": 0.0},
    },
    sensor_bandwidth_limits={"lidar_max_hz": 20.0, "camera_max_hz": 60.0, "imu_max_hz": 200.0},
    bpu_acceleration_factor=3.0,
)

# ============================================================================
# 3. Raspberry Pi 5
# ============================================================================
# Specs: Quad-core ARM Cortex-A76 @ 2.4GHz, 4GB/8GB LPDDR4x, VideoCore VII GPU (No NPU)
RASPBERRY_PI_5_PRESET = HardwarePreset(
    id="RASPBERRY_PI_5",
    name="Raspberry Pi 5",
    vendor="Raspberry Pi",
    description="Quad-Core ARM Cortex-A76 @ 2.4GHz, VideoCore VII GPU, 4GB LPDDR4x, 12W TDP",
    profile=HardwareProfile(
        cpu_capacity_units_per_sec=180.0,
        memory_total_mb=4096.0,
        scheduler_policy=SchedulerPolicy.FIFO,
        max_queue_depth=20,
        thermal_ambient_temp=35.0,
        thermal_throttle_temp=80.0,
        thermal_heat_coeff=0.085,
        thermal_cool_coeff=0.015,
    ),
    transport_latencies={
        "can_bus": {"base_latency_s": 0.0025, "jitter_std_s": 0.0005, "packet_loss": 0.001},
        "camera_mipi": {"base_latency_s": 0.025, "jitter_std_s": 0.004, "packet_loss": 0.0},
        "lidar_serial": {"base_latency_s": 0.008, "jitter_std_s": 0.002, "packet_loss": 0.0},
        "imu_i2c": {"base_latency_s": 0.0015, "jitter_std_s": 0.0003, "packet_loss": 0.0},
    },
    sensor_bandwidth_limits={"lidar_max_hz": 10.0, "camera_max_hz": 30.0, "imu_max_hz": 100.0},
    bpu_acceleration_factor=1.0,
)

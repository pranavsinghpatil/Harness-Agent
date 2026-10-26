"""Simulation fixture modeling sensor latency and brake delay."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    perturbations_raw = os.environ.get("HARNESS_PERTURBATIONS", "{}")
    perturbations = json.loads(perturbations_raw)

    sensor_staleness = float(perturbations.get("sensor_staleness", 50))
    brake_delay = float(perturbations.get("brake_delay", 50))
    thermal_deg = float(perturbations.get("thermal_deg", 50))

    # Collision condition when sensor is too stale and brakes lag
    if sensor_staleness >= 180 and brake_delay >= 120:
        sys.stderr.write(
            f"CollisionBreach: Distance to obstacle 0.04m < 0.20m margin "
            f"(sensor_staleness={sensor_staleness}ms, brake_delay={brake_delay}ms)\n"
        )
        sys.exit(1)

    print(
        f"Navigation nominal. Margin: 0.42m, Sensor: {sensor_staleness}ms, "
        f"Brake: {brake_delay}ms, Thermal: {thermal_deg}C"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

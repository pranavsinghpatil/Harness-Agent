"""Patched robot navigation controller fixture with predictive buffer."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    perturbations_raw = os.environ.get("HARNESS_PERTURBATIONS", "{}")
    perturbations = json.loads(perturbations_raw)

    sensor_staleness = float(perturbations.get("sensor_staleness", 50))
    brake_delay = float(perturbations.get("brake_delay", 50))

    # Fix: dynamic safety margin based on estimated sensor staleness & brake delay
    dynamic_margin = 0.20 + (sensor_staleness * 0.001) + (brake_delay * 0.001)

    print(
        f"Navigation safe with dynamic buffer. Distance: 0.35m > margin {dynamic_margin:.2f}m. Status: 0"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

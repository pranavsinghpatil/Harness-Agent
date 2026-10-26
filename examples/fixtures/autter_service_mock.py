"""Mock service matching Autter Runtime incident telemetry."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    perturbations_raw = os.environ.get("HARNESS_PERTURBATIONS", "{}")
    perturbations = json.loads(perturbations_raw)

    db_query_timeout = perturbations.get("db_query_timeout", False)
    latency_ms = float(perturbations.get("latency_ms", 50))

    if db_query_timeout or latency_ms >= 300:
        sys.stderr.write(
            "RuntimeError: Database pool connection timed out waiting for checkout transaction lock\n"
        )
        sys.exit(1)

    print(f"Checkout completed successfully in {latency_ms}ms.")
    sys.exit(0)


if __name__ == "__main__":
    main()

"""Sample backend payment service fixture with an edge-case defect.

Used to test deterministic failure reproduction, minimization, and verification.
"""

from __future__ import annotations

import json
import os
import sys
import time


def main() -> None:
    # Read perturbations from environment injected by harness sandbox
    perturbations_raw = os.environ.get("HARNESS_PERTURBATIONS", "{}")
    perturbations = json.loads(perturbations_raw)

    timeout_ms = float(perturbations.get("timeout_ms", 500))
    latency_ms = float(perturbations.get("latency_ms", 100))
    discount_path = bool(perturbations.get("discount_path", False))
    cart_total_present = bool(perturbations.get("cart_total_present", True))
    network_drop_rate = float(perturbations.get("network_drop_rate", 0.0))

    # Read stdin payload if provided
    request_data = {}
    if not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                request_data = json.loads(stdin_content)
        except Exception:
            pass

    # Simulate network latency
    if latency_ms > timeout_ms:
        sys.stderr.write(
            f"TransactionTimeoutError: Gateway call exceeded configured timeout ({latency_ms}ms > {timeout_ms}ms)\n"
        )
        sys.exit(1)

    # Defect: If discount_path is enabled and cart_total_present is False, crashes with undefined property access
    if discount_path and not cart_total_present:
        sys.stderr.write(
            "TypeError: Cannot read properties of undefined (reading 'total') in calculate_discount()\n"
        )
        sys.exit(1)

    # Nominal success
    print(f"Payment processed successfully. Latency: {latency_ms}ms, Status: 200 OK")
    sys.exit(0)


if __name__ == "__main__":
    main()

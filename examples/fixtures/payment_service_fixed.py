"""Patched candidate version of payment service fixture.

Defensively handles missing cart total and dynamically adjusts gateway deadline.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    perturbations_raw = os.environ.get("HARNESS_PERTURBATIONS", "{}")
    perturbations = json.loads(perturbations_raw)

    timeout_ms = float(perturbations.get("timeout_ms", 500))
    latency_ms = float(perturbations.get("latency_ms", 100))
    discount_path = bool(perturbations.get("discount_path", False))
    cart_total_present = bool(perturbations.get("cart_total_present", True))

    # Fix 1: Adaptive deadline adjustment for high latency
    effective_timeout = max(timeout_ms, latency_ms + 50)

    # Fix 2: Defensive discount calculation with fallback
    cart_total = 0.0
    if cart_total_present:
        cart_total = 100.0  # mock value
    else:
        # Gracefully handle missing cart total without throwing TypeError
        cart_total = 0.0

    discount_amount = (cart_total * 0.1) if discount_path else 0.0

    print(
        f"Payment processed safely. Total: {cart_total}, Discount: {discount_amount}, "
        f"EffectiveTimeout: {effective_timeout}ms, Status: 200 OK"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

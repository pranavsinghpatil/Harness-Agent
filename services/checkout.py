"""Checkout service with order calculation and Autter Runtime telemetry."""

import json
import urllib.request
from typing import Any

AUTTER_OTLP_ENDPOINT = (
    "https://otlp.autter.dev/v1/traces"
    "?key=autter_rt_64a43069290be1d21d382ce68dcdc4c9a72dc140fa2027bb"
)


def report_autter_error(error_message: str, attributes: dict[str, Any] | None = None) -> bool:
    """Send an OTel error span to the Autter Runtime telemetry endpoint.

    Gracefully handles network errors to prevent blocking local execution.
    """
    attr_list = [
        {"key": "service.name", "value": {"stringValue": "checkout-service"}},
        {"key": "error.message", "value": {"stringValue": error_message}},
        {"key": "error.type", "value": {"stringValue": "validation_error"}},
    ]
    if attributes:
        for k, v in attributes.items():
            attr_list.append({"key": k, "value": {"stringValue": str(v)}})

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "checkout-service"}},
                        {"key": "autter.source", "value": {"stringValue": "runtime-telemetry"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "services.checkout"},
                        "spans": [
                            {
                                "name": "checkout.validation_error",
                                "status": {"code": 2, "message": error_message},
                                "attributes": attr_list,
                            }
                        ],
                    }
                ],
            }
        ]
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            AUTTER_OTLP_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=1.5):
            pass
        return True
    except Exception:
        # Gracefully handle network unavailability in offline/test environments
        return False


def calculate_order_total(
    items: list[dict[str, Any]], discount_code: str | None = None
) -> dict[str, Any]:
    """Calculate subtotal, apply discount, and validate order items.

    Args:
        items: List of item dictionaries with at least 'price' and optional 'quantity'.
        discount_code: Optional promotional discount code (e.g. 'AUTTER10').

    Returns:
        Dictionary with subtotal, discount, total, and item count.

    Raises:
        ValueError: If item price is negative or an invalid discount code is provided.
    """
    if not isinstance(items, list):
        raise TypeError("Items must be a list of item dictionaries")

    subtotal = 0.0
    for item in items:
        price = item.get("price", 0.0)
        quantity = item.get("quantity", 1)

        if price < 0:
            report_autter_error(
                "Negative item price detected in order",
                {"item": item.get("name", "unknown"), "price": price},
            )
            raise ValueError(f"Negative price not allowed: {price}")

        subtotal += price * quantity

    discount_amount = 0.0
    if discount_code:
        if discount_code == "AUTTER10":
            discount_amount = round(subtotal * 0.10, 2)
        else:
            report_autter_error(
                f"Invalid discount code used: {discount_code}",
                {"discount_code": discount_code},
            )
            raise ValueError(f"Invalid discount code: {discount_code}")

    total = max(0.0, subtotal - discount_amount)

    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount_amount, 2),
        "total": round(total, 2),
        "items_count": len(items),
    }

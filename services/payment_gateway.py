"""Payment gateway and refund processing service with Autter telemetry."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional


def emit_runtime_telemetry(event_name: str, attributes: Dict[str, Any]) -> None:
    """Send runtime trace to Autter OTLP collector if configured."""
    key = os.environ.get("AUTTER_INGEST_KEY")
    if not key:
        return

    endpoint = os.environ.get("AUTTER_INGEST_ENDPOINT", "https://otlp.autter.dev/v1/traces")
    url = f"{endpoint}?key={key}" if "?key=" not in endpoint else endpoint

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "payment-gateway"}},
                        {"key": "event.name", "value": {"stringValue": event_name}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "autter-payment-gateway", "version": "1.0.0"},
                        "spans": [
                            {
                                "name": event_name,
                                "attributes": [
                                    {"key": k, "value": {"stringValue": str(v)}}
                                    for k, v in attributes.items()
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3.0)
    except Exception:
        # Avoid crashing payment pipeline on telemetry network blips
        pass


def process_refund(
    order: Dict[str, Any],
    refund_amount: float,
    reason: str = "customer_request",
) -> Dict[str, Any]:
    """Process an order refund.

    Args:
        order: Order dictionary with 'id', 'total_paid', and optional 'already_refunded'.
        refund_amount: Desired refund amount in currency units.
        reason: Justification for the refund.

    Returns:
        Processed refund confirmation summary.
    """
    if refund_amount <= 0:
        raise ValueError(f"Refund amount must be positive, got {refund_amount}")

    total_paid = float(order.get("total_paid", 0.0))
    already_refunded = float(order.get("already_refunded", 0.0))
    available_balance = total_paid - already_refunded

    # Edge Case: Missing check for refund_amount exceeding available_balance!
    # If refund_amount > available_balance, balance goes negative without raising an error.
    new_already_refunded = already_refunded + refund_amount
    remaining_balance = total_paid - new_already_refunded

    emit_runtime_telemetry(
        "payment.refund_processed",
        {
            "order_id": order.get("id", "unknown"),
            "refund_amount": refund_amount,
            "remaining_balance": remaining_balance,
            "reason": reason,
        },
    )

    return {
        "order_id": order.get("id"),
        "status": "refunded" if remaining_balance == 0 else "partially_refunded",
        "refunded_amount": refund_amount,
        "total_refunded": new_already_refunded,
        "remaining_balance": remaining_balance,
    }

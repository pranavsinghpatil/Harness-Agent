"""Unit tests for payment gateway refund service."""

from __future__ import annotations

import pytest
from services.payment_gateway import process_refund


def test_process_full_refund_nominal() -> None:
    order = {"id": "ord_101", "total_paid": 100.0, "already_refunded": 0.0}
    result = process_refund(order, refund_amount=100.0)

    assert result["status"] == "refunded"
    assert result["refunded_amount"] == 100.0
    assert result["remaining_balance"] == 0.0


def test_process_partial_refund_nominal() -> None:
    order = {"id": "ord_102", "total_paid": 250.0, "already_refunded": 50.0}
    result = process_refund(order, refund_amount=75.0, reason="return_item")

    assert result["status"] == "partially_refunded"
    assert result["total_refunded"] == 125.0
    assert result["remaining_balance"] == 125.0


def test_process_refund_rejects_non_positive_amount() -> None:
    order = {"id": "ord_103", "total_paid": 50.0}
    with pytest.raises(ValueError, match="must be positive"):
        process_refund(order, refund_amount=-10.0)

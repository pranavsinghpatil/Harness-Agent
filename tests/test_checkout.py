"""Unit tests for checkout order calculation and telemetry error paths."""

import logging
import os
from unittest.mock import patch
import pytest
from services.checkout import (
    calculate_order_total,
    get_autter_otlp_endpoint,
    report_autter_error,
)


def test_calculate_order_total_nominal():
    items = [
        {"name": "Widget A", "price": 25.0, "quantity": 2},
        {"name": "Widget B", "price": 15.5, "quantity": 1},
    ]
    result = calculate_order_total(items)

    assert result["subtotal"] == 65.5
    assert result["discount"] == 0.0
    assert result["total"] == 65.5
    assert result["items_count"] == 2


def test_calculate_order_total_with_valid_discount():
    items = [
        {"name": "Pro License", "price": 100.0, "quantity": 1},
        {"name": "Support Addon", "price": 50.0, "quantity": 1},
    ]
    result = calculate_order_total(items, discount_code="AUTTER10")

    assert result["subtotal"] == 150.0
    assert result["discount"] == 15.0
    assert result["total"] == 135.0
    assert result["items_count"] == 2


def test_calculate_order_total_invalid_input_and_telemetry():
    # Test negative item price triggers ValueError and telemetry reporting
    items_with_negative_price = [{"name": "Corrupt Item", "price": -10.0}]
    with patch("services.checkout.report_autter_error") as mock_report:
        with pytest.raises(ValueError, match="Negative price not allowed"):
            calculate_order_total(items_with_negative_price)
        assert mock_report.called
        assert "Negative item price detected" in mock_report.call_args[0][0]

    # Test invalid discount code triggers ValueError and telemetry reporting
    valid_items = [{"name": "Item", "price": 20.0}]
    with patch("services.checkout.report_autter_error") as mock_report:
        with pytest.raises(ValueError, match="Invalid discount code"):
            calculate_order_total(valid_items, discount_code="BAD_CODE")
        assert mock_report.called
        assert "Invalid discount code" in mock_report.call_args[0][0]


def test_telemetry_environment_and_error_handling(caplog):
    # Missing env key skips cleanly
    with patch.dict(os.environ, {}, clear=True):
        assert get_autter_otlp_endpoint() is None
        assert report_autter_error("test error") is False

    # Configured key returns proper URL and logs warning on network error
    with patch.dict(os.environ, {"AUTTER_INGEST_KEY": "sample_secret_key"}):
        endpoint = get_autter_otlp_endpoint()
        assert endpoint is not None
        assert "key=sample_secret_key" in endpoint

        with patch("urllib.request.urlopen", side_effect=OSError("Network failure")):
            with caplog.at_level(logging.WARNING):
                delivered = report_autter_error("test exception")
                assert delivered is False
                assert "Failed to deliver Autter runtime telemetry span" in caplog.text

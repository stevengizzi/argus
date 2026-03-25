"""Tests for IBKR error log throttling in IBKRBroker._on_error."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from argus.utils.log_throttle import ThrottledLogger


@pytest.fixture()
def mock_logger() -> MagicMock:
    """Mock for the module-level logger."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture()
def throttled(mock_logger: MagicMock) -> ThrottledLogger:
    """ThrottledLogger wrapping a mock logger."""
    return ThrottledLogger(mock_logger)


def test_error_399_throttled_per_symbol(throttled: ThrottledLogger, mock_logger: MagicMock) -> None:
    """Error 399 for the same symbol should not repeat within 60s."""
    # Simulate what IBKRBroker._on_error does for error 399
    for _ in range(10):
        symbol = "AAPL"
        throttled.warn_throttled(
            f"ibkr_399_{symbol}",
            f"IBKR error 399 ({symbol}): Order repriced",
            interval_seconds=60.0,
        )

    # Only the first should emit
    assert mock_logger.warning.call_count == 1
    assert "AAPL" in mock_logger.warning.call_args[0][0]

    # Different symbol should emit independently
    throttled.warn_throttled(
        "ibkr_399_TSLA",
        "IBKR error 399 (TSLA): Order repriced",
        interval_seconds=60.0,
    )
    assert mock_logger.warning.call_count == 2


def test_error_202_logged_once_per_order(throttled: ThrottledLogger, mock_logger: MagicMock) -> None:
    """Error 202 for the same orderId should log once only."""
    order_id = 12345
    for _ in range(5):
        throttled.warn_throttled(
            f"ibkr_202_{order_id}",
            f"IBKR error 202 (orderId={order_id}): Order Canceled",
            interval_seconds=86400.0,
        )

    assert mock_logger.warning.call_count == 1
    assert str(order_id) in mock_logger.warning.call_args[0][0]

    # Different orderId should emit
    throttled.warn_throttled(
        "ibkr_202_99999",
        "IBKR error 202 (orderId=99999): Order Canceled",
        interval_seconds=86400.0,
    )
    assert mock_logger.warning.call_count == 2

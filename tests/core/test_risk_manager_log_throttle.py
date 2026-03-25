"""Tests for Risk Manager log throttling on rejection warnings."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import AccountRiskConfig, CrossStrategyRiskConfig, PDTConfig, RiskConfig
from argus.core.event_bus import EventBus
from argus.core.events import OrderRejectedEvent, Side, SignalEvent
from argus.core.risk_manager import RiskManager, _throttled


def _make_signal(
    symbol: str = "AAPL",
    entry_price: float = 100.0,
    stop_price: float = 99.0,
    share_count: int = 100,
) -> SignalEvent:
    """Create a minimal SignalEvent for testing."""
    return SignalEvent(
        strategy_id="test_strategy",
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=[101.0, 102.0],
        share_count=share_count,
        rationale="test",
    )


@pytest.fixture()
def risk_config() -> RiskConfig:
    """Create a RiskConfig with tight limits to trigger rejections."""
    return RiskConfig(
        account=AccountRiskConfig(
            daily_loss_limit_pct=0.03,
            weekly_loss_limit_pct=0.05,
            cash_reserve_pct=0.20,
            max_concurrent_positions=0,
            min_position_risk_dollars=100.0,
        ),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(enabled=False),
    )


@pytest.fixture()
def mock_broker() -> AsyncMock:
    """Create a mock broker returning account state."""
    broker = AsyncMock()
    account = MagicMock()
    account.equity = 100000.0
    account.cash = 0.0  # No cash → triggers cash reserve violation
    account.buying_power = 100000.0
    broker.get_account.return_value = account
    broker.get_positions.return_value = []
    return broker


@pytest.fixture()
def risk_manager(risk_config: RiskConfig, mock_broker: AsyncMock) -> RiskManager:
    """Create a RiskManager for testing."""
    event_bus = EventBus()
    rm = RiskManager(risk_config, mock_broker, event_bus)
    # Reset throttle state between tests
    _throttled.reset()
    return rm


@pytest.mark.asyncio()
async def test_cash_reserve_warning_throttled(
    risk_manager: RiskManager, mock_broker: AsyncMock
) -> None:
    """Cash reserve violation warning should be throttled — only 1 per 60s."""
    with patch.object(_throttled, "warn_throttled", wraps=_throttled.warn_throttled) as spy:
        # Multiple signals that all trigger cash reserve violation
        for _ in range(5):
            result = await risk_manager.evaluate_signal(_make_signal())
            assert isinstance(result, OrderRejectedEvent)

        # warn_throttled called 5 times but underlying logger only once
        assert spy.call_count == 5
        # All calls used the "cash_reserve_violated" key
        keys_used = [call.args[0] for call in spy.call_args_list]
        assert all(k == "cash_reserve_violated" for k in keys_used)


@pytest.mark.asyncio()
async def test_concentration_floor_warning_throttled(
    risk_config: RiskConfig, mock_broker: AsyncMock
) -> None:
    """Concentration floor rejection warning should be throttled."""
    # Set up scenario: concentration limit reduces shares below min risk floor
    account = MagicMock()
    account.equity = 10000.0  # Low equity → tight concentration limit
    account.cash = 10000.0
    account.buying_power = 10000.0
    mock_broker.get_account.return_value = account

    # Create Order Manager mock that returns existing positions
    mock_om = MagicMock()
    # Existing $400 exposure → only ~$100 remaining at 5% concentration ($500 max)
    mock_position = MagicMock()
    mock_position.is_fully_closed = False
    mock_position.entry_price = 100.0
    mock_position.shares_remaining = 4
    mock_om.get_managed_positions.return_value = {"AAPL": [mock_position]}
    mock_om.get_pending_entry_exposure.return_value = 0.0

    event_bus = EventBus()
    rm = RiskManager(risk_config, mock_broker, event_bus, order_manager=mock_om)
    _throttled.reset()

    with patch.object(_throttled, "warn_throttled", wraps=_throttled.warn_throttled) as spy:
        for _ in range(3):
            result = await rm.evaluate_signal(
                _make_signal(entry_price=100.0, stop_price=99.0, share_count=50)
            )
            assert isinstance(result, OrderRejectedEvent)

        conc_calls = [c for c in spy.call_args_list if c.args[0] == "concentration_floor"]
        assert len(conc_calls) == 3  # Called 3 times, but underlying logger only once

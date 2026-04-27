"""Tests for the Sprint 31.91 Session 0 ``cancel_all_orders`` API extension.

Covers:

- DEC-364 contract preservation when called with no args.
- ``symbol`` filter on ``IBKRBroker``.
- ``await_propagation=True`` polling-until-empty behavior.
- ``await_propagation=True`` timeout raising ``CancelPropagationTimeout``.
- ``AlpacaBroker.cancel_all_orders`` ``DeprecationWarning`` emission.
- ``IBKRBroker`` symbol filter sources from ``ib_async.openTrades()``
  (the live broker cache), not from any internal ARGUS-side cache.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.execution.broker import CancelPropagationTimeout
from argus.execution.ibkr_broker import IBKRBroker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_trade(symbol: str) -> MagicMock:
    """Build a minimal ib_async-shaped Trade mock for a given symbol."""
    trade = MagicMock()
    trade.contract = MagicMock()
    trade.contract.symbol = symbol
    trade.order = MagicMock()
    return trade


def _make_ibkr_broker_with_trades(open_trades: list[MagicMock]) -> tuple[IBKRBroker, MagicMock]:
    """Construct an IBKRBroker stub with a controlled openTrades() return."""
    mock_ib = MagicMock()
    mock_ib.isConnected.return_value = True
    mock_ib.openTrades.return_value = open_trades
    mock_ib.reqGlobalCancel = MagicMock()
    mock_ib.cancelOrder = MagicMock()

    broker = IBKRBroker.__new__(IBKRBroker)
    broker._ib = mock_ib
    broker._connected = True
    broker._event_bus = MagicMock()
    broker._config = MagicMock()
    return broker, mock_ib


# ---------------------------------------------------------------------------
# 1. DEC-364 contract preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_all_orders_no_args_preserves_dec364() -> None:
    """No-args call must still invoke reqGlobalCancel for ALL working orders.

    This is the DEC-364 contract that pre-Session-0 callers depend on.
    """
    open_trades = [
        _make_mock_trade("AAPL"),
        _make_mock_trade("AAPL"),
        _make_mock_trade("TSLA"),
    ]
    broker, mock_ib = _make_ibkr_broker_with_trades(open_trades)

    with patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock):
        count = await broker.cancel_all_orders()

    assert count == 3
    mock_ib.reqGlobalCancel.assert_called_once()
    mock_ib.cancelOrder.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Symbol filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_all_orders_symbol_filter() -> None:
    """When ``symbol="AAPL"`` is passed, TSLA orders must remain untouched."""
    aapl_a = _make_mock_trade("AAPL")
    aapl_b = _make_mock_trade("AAPL")
    tsla = _make_mock_trade("TSLA")
    broker, mock_ib = _make_ibkr_broker_with_trades([aapl_a, aapl_b, tsla])

    count = await broker.cancel_all_orders(symbol="AAPL")

    assert count == 2
    mock_ib.reqGlobalCancel.assert_not_called()
    cancel_targets = [call.args[0] for call in mock_ib.cancelOrder.call_args_list]
    assert aapl_a.order in cancel_targets
    assert aapl_b.order in cancel_targets
    assert tsla.order not in cancel_targets


# ---------------------------------------------------------------------------
# 3. await_propagation polls until empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_all_orders_await_propagation_polls_until_empty() -> None:
    """With ``await_propagation=True``, the impl must poll openTrades() until
    the filtered scope is empty, then return successfully without raising."""
    aapl_trade = _make_mock_trade("AAPL")
    broker, mock_ib = _make_ibkr_broker_with_trades([aapl_trade])

    # First openTrades() call (in the cancel issuance phase) returns the AAPL trade.
    # The poll loop calls openTrades() again: first poll still sees the trade,
    # second poll sees an empty list (cancellation propagated).
    mock_ib.openTrades.side_effect = [
        [aapl_trade],  # initial filter for issuance
        [aapl_trade],  # poll #1 — still pending
        [],            # poll #2 — propagated
    ]

    with patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        count = await broker.cancel_all_orders(symbol="AAPL", await_propagation=True)

    assert count == 1
    mock_ib.cancelOrder.assert_called_once_with(aapl_trade.order)
    # At least one poll-interval sleep must have happened.
    assert mock_sleep.await_count >= 1


# ---------------------------------------------------------------------------
# 4. await_propagation timeout raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_all_orders_await_propagation_timeout_raises() -> None:
    """If openTrades() never goes empty for the filtered scope,
    ``CancelPropagationTimeout`` must be raised within the 2s budget."""
    aapl_trade = _make_mock_trade("AAPL")
    broker, mock_ib = _make_ibkr_broker_with_trades([aapl_trade])

    # Always return the AAPL trade — poll never observes an empty scope.
    mock_ib.openTrades.return_value = [aapl_trade]

    # Simulate event-loop time deterministically: each call to time() returns
    # an increasing value so the deadline is crossed quickly without real
    # wall-clock wait.
    fake_times = iter([0.0, 0.1, 0.5, 1.0, 1.9, 2.1, 2.2])

    fake_loop = MagicMock()
    fake_loop.time = MagicMock(side_effect=lambda: next(fake_times))

    with patch(
        "argus.execution.ibkr_broker.asyncio.get_event_loop",
        return_value=fake_loop,
    ), patch(
        "argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock
    ):
        with pytest.raises(CancelPropagationTimeout):
            await broker.cancel_all_orders(symbol="AAPL", await_propagation=True)


# ---------------------------------------------------------------------------
# 5. AlpacaBroker DeprecationWarning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alpaca_broker_cancel_all_orders_raises_deprecation_warning() -> None:
    """Calling ``AlpacaBroker.cancel_all_orders`` must emit DeprecationWarning
    and delegate to the legacy implementation, returning the legacy count."""
    from argus.execution.alpaca_broker import AlpacaBroker

    broker = AlpacaBroker.__new__(AlpacaBroker)
    broker._cancel_all_orders_legacy = AsyncMock(return_value=7)  # type: ignore[method-assign]

    with pytest.warns(DeprecationWarning, match="Sprint 31.94"):
        count = await broker.cancel_all_orders()

    assert count == 7
    broker._cancel_all_orders_legacy.assert_awaited_once()


# ---------------------------------------------------------------------------
# 6. IBKR symbol filter sources from ib_async.openTrades()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ibkr_broker_cancel_all_orders_symbol_filter_uses_open_orders() -> None:
    """The IBKR impl must source the filter set from ``self._ib.openTrades()``
    and match on ``trade.contract.symbol`` — never from an ARGUS-side cache."""
    aapl = _make_mock_trade("AAPL")
    msft = _make_mock_trade("MSFT")
    broker, mock_ib = _make_ibkr_broker_with_trades([aapl, msft])

    count = await broker.cancel_all_orders(symbol="AAPL")

    # Filter source: openTrades() was queried.
    assert mock_ib.openTrades.called, "Filter must source from openTrades()"
    # Filter expression: trade.contract.symbol == "AAPL".
    assert count == 1
    mock_ib.cancelOrder.assert_called_once_with(aapl.order)


# ---------------------------------------------------------------------------
# Bonus regression: SimulatedBroker symbol filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simulated_broker_cancel_all_orders_symbol_filter() -> None:
    """SimulatedBroker should drop only the matching-symbol pending brackets
    when ``symbol`` is provided, and leave the rest in place."""
    from argus.execution.simulated_broker import PendingBracketOrder, SimulatedBroker
    from argus.models.trading import OrderSide

    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()

    broker._pending_brackets = [
        PendingBracketOrder(
            order_id="ulid-aapl-stop",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            trigger_price=180.0,
            order_type="stop",
            parent_position_symbol="AAPL",
            strategy_id="orb",
        ),
        PendingBracketOrder(
            order_id="ulid-aapl-target",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            trigger_price=185.0,
            order_type="limit",
            parent_position_symbol="AAPL",
            strategy_id="orb",
        ),
        PendingBracketOrder(
            order_id="ulid-tsla-stop",
            symbol="TSLA",
            side=OrderSide.SELL,
            quantity=50,
            trigger_price=240.0,
            order_type="stop",
            parent_position_symbol="TSLA",
            strategy_id="orb",
        ),
    ]

    count = await broker.cancel_all_orders(symbol="AAPL")

    assert count == 2
    remaining_symbols = [b.symbol for b in broker._pending_brackets]
    assert remaining_symbols == ["TSLA"]


@pytest.mark.asyncio
async def test_simulated_broker_cancel_all_orders_no_args_clears_everything() -> None:
    """No-args SimulatedBroker call must clear the entire pending-brackets list
    (DEC-364 contract preserved on the simulated path too)."""
    from argus.execution.simulated_broker import PendingBracketOrder, SimulatedBroker
    from argus.models.trading import OrderSide

    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()
    broker._pending_brackets = [
        PendingBracketOrder(
            order_id=f"ulid-{i}",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=10,
            trigger_price=180.0,
            order_type="stop",
            parent_position_symbol="AAPL",
            strategy_id="orb",
        )
        for i in range(5)
    ]

    count = await broker.cancel_all_orders()

    assert count == 5
    assert broker._pending_brackets == []

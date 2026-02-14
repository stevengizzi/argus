"""Tests for the SimulatedBroker."""

import pytest

from argus.execution.simulated_broker import SimulatedBroker, SimulatedSlippage
from argus.models.trading import Order, OrderSide, OrderStatus, OrderType


def make_order(
    symbol: str = "AAPL",
    side: OrderSide = OrderSide.BUY,
    quantity: int = 100,
    price: float = 150.0,
    strategy_id: str = "test_strategy",
) -> Order:
    """Create a test order."""
    return Order(
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        limit_price=price,
        order_type=OrderType.MARKET,
    )


class TestSimulatedBrokerConnection:
    """Tests for connection state management."""

    @pytest.mark.asyncio
    async def test_connect_sets_connected_state(self) -> None:
        """Broker should be connected after calling connect()."""
        broker = SimulatedBroker(initial_cash=50000)
        await broker.connect()
        assert broker._connected is True

    @pytest.mark.asyncio
    async def test_disconnect_clears_connected_state(self) -> None:
        """Broker should be disconnected after calling disconnect()."""
        broker = SimulatedBroker()
        await broker.connect()
        await broker.disconnect()
        assert broker._connected is False

    @pytest.mark.asyncio
    async def test_place_order_not_connected_raises(self) -> None:
        """Placing an order without connecting should raise RuntimeError."""
        broker = SimulatedBroker()
        order = make_order()
        with pytest.raises(RuntimeError, match="not connected"):
            await broker.place_order(order)


class TestSimulatedBrokerBuyOrders:
    """Tests for buy order behavior."""

    @pytest.mark.asyncio
    async def test_place_buy_order_fills_at_price(self) -> None:
        """Buy order should fill at the specified price."""
        broker = SimulatedBroker(initial_cash=100000)
        await broker.connect()
        order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        result = await broker.place_order(order)

        assert result.status == OrderStatus.FILLED
        assert result.filled_quantity == 100
        assert result.filled_avg_price == 150.0

    @pytest.mark.asyncio
    async def test_place_buy_order_deducts_cash(self) -> None:
        """Buy order should deduct cost from cash."""
        broker = SimulatedBroker(initial_cash=50000)
        await broker.connect()
        order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        await broker.place_order(order)

        account = await broker.get_account()
        assert account.cash == 35000.0  # 50000 - (100 * 150)

    @pytest.mark.asyncio
    async def test_place_buy_order_creates_position(self) -> None:
        """Buy order should create a position."""
        broker = SimulatedBroker()
        await broker.connect()
        order = make_order(symbol="AAPL", quantity=100)
        await broker.place_order(order)

        positions = await broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == 100

    @pytest.mark.asyncio
    async def test_place_buy_order_insufficient_funds_rejected(self) -> None:
        """Buy order exceeding buying power should be rejected."""
        broker = SimulatedBroker(initial_cash=1000)
        await broker.connect()
        order = make_order(quantity=100, price=150.0)  # Cost = 15000
        result = await broker.place_order(order)

        assert result.status == OrderStatus.REJECTED
        assert "buying power" in result.message.lower()


class TestSimulatedBrokerSellOrders:
    """Tests for sell order behavior."""

    @pytest.mark.asyncio
    async def test_place_sell_order_closes_position(self) -> None:
        """Sell order should close the position."""
        broker = SimulatedBroker(initial_cash=100000)
        await broker.connect()

        # Buy first
        buy_order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        await broker.place_order(buy_order)

        # Sell
        sell_order = make_order(side=OrderSide.SELL, quantity=100, price=155.0)
        result = await broker.place_order(sell_order)

        assert result.status == OrderStatus.FILLED
        positions = await broker.get_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_place_sell_order_adds_cash(self) -> None:
        """Sell order should add proceeds to cash."""
        broker = SimulatedBroker(initial_cash=50000)
        await broker.connect()

        # Buy 100 at 150 = -15000, cash = 35000
        buy_order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        await broker.place_order(buy_order)

        # Sell 100 at 155 = +15500, cash = 50500
        sell_order = make_order(side=OrderSide.SELL, quantity=100, price=155.0)
        await broker.place_order(sell_order)

        account = await broker.get_account()
        assert account.cash == 50500.0

    @pytest.mark.asyncio
    async def test_place_sell_order_no_position_rejected(self) -> None:
        """Sell order without a position should be rejected."""
        broker = SimulatedBroker()
        await broker.connect()

        sell_order = make_order(side=OrderSide.SELL, quantity=100, price=155.0)
        result = await broker.place_order(sell_order)

        assert result.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_partial_sell_reduces_position(self) -> None:
        """Partial sell should reduce position shares."""
        broker = SimulatedBroker()
        await broker.connect()

        buy_order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        await broker.place_order(buy_order)

        sell_order = make_order(side=OrderSide.SELL, quantity=50, price=155.0)
        await broker.place_order(sell_order)

        positions = await broker.get_positions()
        assert len(positions) == 1
        assert positions[0].shares == 50


class TestSimulatedBrokerBracketOrders:
    """Tests for bracket order behavior."""

    @pytest.mark.asyncio
    async def test_place_bracket_order_registers_stop_and_targets(self) -> None:
        """Bracket order should register pending stop and target orders."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )
        target = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=50,
            limit_price=155.0,
            order_type=OrderType.LIMIT,
        )

        result = await broker.place_bracket_order(entry, stop, [target])

        assert result.entry.status == OrderStatus.FILLED
        assert result.stop.status == OrderStatus.PENDING
        assert len(result.targets) == 1
        assert result.targets[0].status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_bracket_order_entry_rejected_no_stop_or_targets(self) -> None:
        """If entry is rejected, stop and targets should also be rejected."""
        broker = SimulatedBroker(initial_cash=100)  # Not enough
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )
        target = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=50,
            limit_price=155.0,
            order_type=OrderType.LIMIT,
        )

        result = await broker.place_bracket_order(entry, stop, [target])

        assert result.entry.status == OrderStatus.REJECTED
        assert result.stop.status == OrderStatus.REJECTED
        assert result.targets[0].status == OrderStatus.REJECTED


class TestSimulatedBrokerPriceUpdates:
    """Tests for bracket order triggering via price updates."""

    @pytest.mark.asyncio
    async def test_simulate_price_update_triggers_stop(self) -> None:
        """Price dropping below stop should trigger stop order."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )

        await broker.place_bracket_order(entry, stop, [])

        # Price drops to 144 - below stop at 145
        results = await broker.simulate_price_update("AAPL", 144.0)

        assert len(results) == 1
        assert results[0].status == OrderStatus.FILLED
        positions = await broker.get_positions()
        assert len(positions) == 0  # Position closed by stop

    @pytest.mark.asyncio
    async def test_simulate_price_update_triggers_target(self) -> None:
        """Price rising above target should trigger target order."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )
        target = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            limit_price=155.0,
            order_type=OrderType.LIMIT,
        )

        await broker.place_bracket_order(entry, stop, [target])

        # Price rises to 156 - above target at 155
        results = await broker.simulate_price_update("AAPL", 156.0)

        assert len(results) == 1
        assert results[0].filled_avg_price == 156.0

    @pytest.mark.asyncio
    async def test_stop_trigger_cancels_remaining_brackets(self) -> None:
        """Triggering stop should cancel remaining bracket orders."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )
        target = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            limit_price=155.0,
            order_type=OrderType.LIMIT,
        )

        await broker.place_bracket_order(entry, stop, [target])

        # Trigger stop
        await broker.simulate_price_update("AAPL", 144.0)

        # All bracket orders should be gone
        assert len(broker._pending_brackets) == 0

    @pytest.mark.asyncio
    async def test_target_trigger_cancels_stop_when_position_closed(self) -> None:
        """Triggering target that closes position should cancel stop."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )
        target = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            limit_price=155.0,
            order_type=OrderType.LIMIT,
        )

        await broker.place_bracket_order(entry, stop, [target])

        # Trigger target
        await broker.simulate_price_update("AAPL", 160.0)

        # All brackets should be cancelled
        assert len(broker._pending_brackets) == 0
        assert len(await broker.get_positions()) == 0


class TestSimulatedBrokerCancelModify:
    """Tests for order cancellation and modification."""

    @pytest.mark.asyncio
    async def test_cancel_pending_bracket_order(self) -> None:
        """Should be able to cancel a pending bracket order."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )

        result = await broker.place_bracket_order(entry, stop, [])
        stop_id = result.stop.order_id

        cancelled = await broker.cancel_order(stop_id)
        assert cancelled is True

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order_returns_false(self) -> None:
        """Cancelling non-existent order should return False."""
        broker = SimulatedBroker()
        await broker.connect()

        cancelled = await broker.cancel_order("nonexistent")
        assert cancelled is False


class TestSimulatedBrokerAccount:
    """Tests for account state queries."""

    @pytest.mark.asyncio
    async def test_get_account_reflects_positions(self) -> None:
        """Account info should include position value."""
        broker = SimulatedBroker(initial_cash=100000)
        await broker.connect()

        buy_order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        await broker.place_order(buy_order)

        account = await broker.get_account()
        assert account.positions_value == 15000.0
        assert account.equity == 100000.0  # 85000 cash + 15000 positions
        assert account.cash == 85000.0

    @pytest.mark.asyncio
    async def test_get_order_status_returns_correct_status(self) -> None:
        """Should return correct status for an order."""
        broker = SimulatedBroker()
        await broker.connect()

        order = make_order()
        result = await broker.place_order(order)

        status = await broker.get_order_status(result.order_id)
        assert status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_get_order_status_unknown_id_raises(self) -> None:
        """Should raise KeyError for unknown order ID."""
        broker = SimulatedBroker()
        await broker.connect()

        with pytest.raises(KeyError):
            await broker.get_order_status("nonexistent")


class TestSimulatedBrokerFlatten:
    """Tests for emergency flatten functionality."""

    @pytest.mark.asyncio
    async def test_flatten_all_closes_everything(self) -> None:
        """Flatten should close all positions."""
        broker = SimulatedBroker()
        await broker.connect()

        # Open two positions
        await broker.place_order(make_order(symbol="AAPL", quantity=100, price=150.0))
        await broker.place_order(make_order(symbol="TSLA", quantity=50, price=200.0))

        results = await broker.flatten_all()

        assert len(results) == 2
        positions = await broker.get_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_flatten_all_cancels_pending_brackets(self) -> None:
        """Flatten should cancel all pending bracket orders."""
        broker = SimulatedBroker()
        await broker.connect()

        entry = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        stop = Order(
            strategy_id="test",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=145.0,
            order_type=OrderType.STOP,
        )

        await broker.place_bracket_order(entry, stop, [])

        await broker.flatten_all()

        assert len(broker._pending_brackets) == 0


class TestSimulatedBrokerSlippage:
    """Tests for slippage simulation."""

    @pytest.mark.asyncio
    async def test_fixed_slippage_buy_order(self) -> None:
        """Buy order should get worse price with fixed slippage."""
        broker = SimulatedBroker(
            initial_cash=100000,
            slippage=SimulatedSlippage(mode="fixed", fixed_amount=0.05),
        )
        await broker.connect()

        order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        result = await broker.place_order(order)

        assert result.filled_avg_price == 150.05  # Worse for buyer

    @pytest.mark.asyncio
    async def test_fixed_slippage_sell_order(self) -> None:
        """Sell order should get worse price with fixed slippage."""
        broker = SimulatedBroker(
            initial_cash=100000,
            slippage=SimulatedSlippage(mode="fixed", fixed_amount=0.05),
        )
        await broker.connect()

        # Buy first (at 150.05 with slippage)
        buy_order = make_order(side=OrderSide.BUY, quantity=100, price=150.0)
        await broker.place_order(buy_order)

        # Sell (at 154.95 with slippage - worse for seller)
        sell_order = make_order(side=OrderSide.SELL, quantity=100, price=155.0)
        result = await broker.place_order(sell_order)

        assert result.filled_avg_price == 154.95  # Worse for seller


class TestSimulatedBrokerReset:
    """Tests for broker reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_restores_initial_state(self) -> None:
        """Reset should restore broker to initial state."""
        broker = SimulatedBroker(initial_cash=50000)
        await broker.connect()

        # Make some trades
        await broker.place_order(make_order(quantity=100, price=150.0))

        broker.reset()

        assert broker._cash == 50000
        assert len(broker._positions) == 0
        assert len(broker._orders) == 0
        assert broker._connected is False

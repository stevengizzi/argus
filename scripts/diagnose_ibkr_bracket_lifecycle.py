#!/usr/bin/env python3
"""IBKR Bracket Order Lifecycle Test — Session 7.

Tests the complete bracket order lifecycle through IBKRBroker:
1. Connect via IBKRBroker (paper account verification)
2. Test IBKRBroker.place_bracket_order() with entry + stop + T1 + T2
3. Verify all bracket component orders are submitted atomically
4. Wait for entry fill, verify ManagedPosition tracking
5. Test order cancellation via IBKRBroker.cancel_order()
6. Test flatten_all via IBKRBroker.flatten_all()
7. Verify all orders cancelled and position closed

Run: python scripts/test_ibkr_bracket_lifecycle.py

IMPORTANT: Only runs on paper trading accounts (DU prefix, port 4002).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("session7_test")

# Test configuration
TEST_SYMBOL = "SPY"  # Liquid ETF for testing
TEST_SHARES = 1
FILL_TIMEOUT_SECONDS = 30
BRACKET_STOP_OFFSET = 2.00  # $2 below entry for stop
BRACKET_T1_OFFSET = 1.00    # $1 above entry for T1
BRACKET_T2_OFFSET = 2.00    # $2 above entry for T2


class TestResults:
    """Track test results."""

    def __init__(self) -> None:
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors: list[str] = []

    def record_pass(self, test_name: str) -> None:
        """Record a passing test."""
        self.tests_run += 1
        self.tests_passed += 1
        logger.info("✅ PASS: %s", test_name)

    def record_fail(self, test_name: str, reason: str) -> None:
        """Record a failing test."""
        self.tests_run += 1
        self.tests_failed += 1
        self.errors.append(f"{test_name}: {reason}")
        logger.error("❌ FAIL: %s — %s", test_name, reason)

    def summary(self) -> str:
        """Return test summary."""
        status = "PASS" if self.tests_failed == 0 else "FAIL"
        lines = [
            "",
            "=" * 70,
            f"SESSION 7 TEST SUMMARY: {status}",
            f"  Tests run: {self.tests_run}",
            f"  Passed: {self.tests_passed}",
            f"  Failed: {self.tests_failed}",
        ]
        if self.errors:
            lines.append("  Errors:")
            for err in self.errors:
                lines.append(f"    - {err}")
        lines.append("=" * 70)
        return "\n".join(lines)


async def run_tests() -> int:
    """Run the IBKR bracket order lifecycle test suite through IBKRBroker."""
    from argus.core.config import IBKRConfig
    from argus.core.event_bus import EventBus
    from argus.execution.ibkr_broker import IBKRBroker
    from argus.models.trading import Order, OrderSide, OrderStatus
    from argus.models.trading import OrderType as TradingOrderType

    results = TestResults()

    # Get connection parameters from config
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "4002"))
    client_id = int(os.getenv("IBKR_CLIENT_ID", "98"))  # Use 98 for this test

    logger.info("=" * 70)
    logger.info("SESSION 7: IBKR BRACKET ORDER LIFECYCLE TEST")
    logger.info("=" * 70)
    logger.info("Testing: IBKRBroker.place_bracket_order() with entry + stop + T1 + T2")
    logger.info("Host: %s, Port: %d, ClientId: %d", host, port, client_id)
    logger.info("Symbol: %s, Shares: %d", TEST_SYMBOL, TEST_SHARES)
    logger.info("")

    # ──────────────────────────────────────────────────────────────────
    # Safety Check: Port must be 4002 (paper)
    # ──────────────────────────────────────────────────────────────────
    if port == 4001:
        logger.critical("ABORT: Port 4001 is LIVE trading. Use port 4002 for paper.")
        results.record_fail("Safety Check - Port", "Port 4001 is LIVE, not paper")
        print(results.summary())
        return 1

    # ──────────────────────────────────────────────────────────────────
    # Step 1: Create IBKRBroker and connect
    # ──────────────────────────────────────────────────────────────────
    logger.info("Step 1: Creating IBKRBroker and connecting...")

    config = IBKRConfig(
        host=host,
        port=port,
        client_id=client_id,
        account="",  # Auto-detect
        timeout_seconds=30.0,
        readonly=False,
    )
    event_bus = EventBus()
    broker = IBKRBroker(config, event_bus)

    try:
        await broker.connect()

        if not broker.is_connected:
            results.record_fail("IBKRBroker Connect", "Failed to connect")
            print(results.summary())
            return 1

        results.record_pass("IBKRBroker Connect")

    except Exception as e:
        results.record_fail("IBKRBroker Connect", str(e))
        print(results.summary())
        return 1

    # ──────────────────────────────────────────────────────────────────
    # Safety Check: Account ID must start with "DU" (paper)
    # ──────────────────────────────────────────────────────────────────
    accounts = broker._ib.managedAccounts()
    if not accounts:
        results.record_fail("Safety Check - Account", "No managed accounts found")
        await broker.disconnect()
        print(results.summary())
        return 1

    account_id = accounts[0]
    logger.info("Account ID: %s", account_id)

    if not account_id.startswith("DU"):
        logger.critical("ABORT: Account %s is NOT a paper account (no DU prefix)", account_id)
        results.record_fail("Safety Check - Account", f"Account {account_id} is not paper")
        await broker.disconnect()
        print(results.summary())
        return 1

    results.record_pass("Safety Check - Paper Account (DU prefix)")

    # Get account info via IBKRBroker
    account_info = await broker.get_account()
    logger.info(
        "Account: equity=$%.2f, cash=$%.2f, buying_power=$%.2f",
        account_info.equity,
        account_info.cash,
        account_info.buying_power,
    )

    # ──────────────────────────────────────────────────────────────────
    # Step 2: Get current price for bracket calculations
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 2: Getting current price for %s...", TEST_SYMBOL)

    # Place a quick market order to get current price
    # (We'll close this position before the bracket test)
    price_check_order = Order(
        strategy_id="price_check",
        symbol=TEST_SYMBOL,
        side=OrderSide.BUY,
        order_type=TradingOrderType.MARKET,
        quantity=TEST_SHARES,
    )

    price_result = await broker.place_order(price_check_order)
    logger.info("Price check order submitted: %s", price_result.order_id)

    # Wait for fill
    estimated_price = None
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < FILL_TIMEOUT_SECONDS:
        await asyncio.sleep(0.5)
        trade = broker._find_trade_by_order_id(
            broker._ulid_to_ibkr.get(price_result.order_id, 0)
        )
        if trade and trade.orderStatus.status == "Filled":
            estimated_price = trade.orderStatus.avgFillPrice
            logger.info("Current price for %s: $%.2f", TEST_SYMBOL, estimated_price)
            break

    if estimated_price is None:
        results.record_fail("Get Current Price", "Price check order did not fill")
        await broker.disconnect()
        print(results.summary())
        return 1

    # Close the price check position
    close_order = Order(
        strategy_id="price_check",
        symbol=TEST_SYMBOL,
        side=OrderSide.SELL,
        order_type=TradingOrderType.MARKET,
        quantity=TEST_SHARES,
    )
    await broker.place_order(close_order)
    await asyncio.sleep(2)  # Wait for close
    results.record_pass("Get Current Price")

    # ──────────────────────────────────────────────────────────────────
    # Step 3: Test IBKRBroker.place_bracket_order()
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 3: Testing IBKRBroker.place_bracket_order()...")

    # Calculate bracket prices
    stop_price = round(estimated_price - BRACKET_STOP_OFFSET, 2)
    t1_price = round(estimated_price + BRACKET_T1_OFFSET, 2)
    t2_price = round(estimated_price + BRACKET_T2_OFFSET, 2)

    logger.info(
        "Bracket config: Entry=MARKET, Stop=$%.2f, T1=$%.2f, T2=$%.2f",
        stop_price,
        t1_price,
        t2_price,
    )

    # Calculate T1/T2 share split (50/50 for 2 shares, or 1 share for T1 only)
    t1_shares = max(1, TEST_SHARES // 2)
    t2_shares = TEST_SHARES - t1_shares

    # Create orders
    entry_order = Order(
        strategy_id="bracket_test",
        symbol=TEST_SYMBOL,
        side=OrderSide.BUY,
        order_type=TradingOrderType.MARKET,
        quantity=TEST_SHARES,
    )

    stop_order = Order(
        strategy_id="bracket_test",
        symbol=TEST_SYMBOL,
        side=OrderSide.SELL,
        order_type=TradingOrderType.STOP,
        quantity=TEST_SHARES,
        stop_price=stop_price,
    )

    targets = []
    if t1_shares > 0:
        t1_order = Order(
            strategy_id="bracket_test",
            symbol=TEST_SYMBOL,
            side=OrderSide.SELL,
            order_type=TradingOrderType.LIMIT,
            quantity=t1_shares,
            limit_price=t1_price,
        )
        targets.append(t1_order)

    if t2_shares > 0:
        t2_order = Order(
            strategy_id="bracket_test",
            symbol=TEST_SYMBOL,
            side=OrderSide.SELL,
            order_type=TradingOrderType.LIMIT,
            quantity=t2_shares,
            limit_price=t2_price,
        )
        targets.append(t2_order)

    # Place bracket order
    try:
        bracket_result = await broker.place_bracket_order(entry_order, stop_order, targets)

        logger.info("Bracket order result:")
        logger.info("  Entry: %s (IBKR #%s)", bracket_result.entry.order_id, bracket_result.entry.broker_order_id)
        logger.info("  Stop:  %s (IBKR #%s)", bracket_result.stop.order_id, bracket_result.stop.broker_order_id)
        for i, t in enumerate(bracket_result.targets):
            logger.info("  T%d:    %s (IBKR #%s)", i + 1, t.order_id, t.broker_order_id)

        results.record_pass("IBKRBroker.place_bracket_order() Submission")

    except Exception as e:
        results.record_fail("IBKRBroker.place_bracket_order()", str(e))
        await broker.disconnect()
        print(results.summary())
        return 1

    # ──────────────────────────────────────────────────────────────────
    # Step 4: Wait for entry fill
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 4: Waiting for entry fill...")

    entry_fill_price = None
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < FILL_TIMEOUT_SECONDS:
        await asyncio.sleep(0.5)
        ib_order_id = broker._ulid_to_ibkr.get(bracket_result.entry.order_id, 0)
        trade = broker._find_trade_by_order_id(ib_order_id)
        if trade and trade.orderStatus.status == "Filled":
            entry_fill_price = trade.orderStatus.avgFillPrice
            logger.info(
                "Entry FILLED: %d shares @ $%.2f",
                int(trade.orderStatus.filled),
                entry_fill_price,
            )
            break

    if entry_fill_price is None:
        results.record_fail("Entry Fill", "No fill within timeout")
        # Clean up
        await broker.flatten_all()
        await broker.disconnect()
        print(results.summary())
        return 1

    results.record_pass("Entry Fill")

    # ──────────────────────────────────────────────────────────────────
    # Step 5: Verify bracket children are visible
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 5: Verifying bracket children (stop + targets)...")

    await asyncio.sleep(1)  # Allow orders to propagate

    stop_found = False
    targets_found = []

    for trade in broker._ib.openTrades():
        order_id = trade.order.orderId

        # Check if this is our stop
        stop_ib_id = broker._ulid_to_ibkr.get(bracket_result.stop.order_id, 0)
        if order_id == stop_ib_id:
            stop_found = True
            logger.info(
                "  Stop order: IBKR #%d, status=%s, auxPrice=$%.2f",
                order_id,
                trade.orderStatus.status,
                trade.order.auxPrice,
            )

        # Check if this is one of our targets
        for i, t_result in enumerate(bracket_result.targets):
            t_ib_id = broker._ulid_to_ibkr.get(t_result.order_id, 0)
            if order_id == t_ib_id:
                targets_found.append(i + 1)
                logger.info(
                    "  T%d order:   IBKR #%d, status=%s, lmtPrice=$%.2f",
                    i + 1,
                    order_id,
                    trade.orderStatus.status,
                    trade.order.lmtPrice,
                )

    if stop_found and len(targets_found) == len(bracket_result.targets):
        results.record_pass("Bracket Children Visible")
    else:
        results.record_fail(
            "Bracket Children Visible",
            f"stop_found={stop_found}, targets_found={targets_found}",
        )

    # ──────────────────────────────────────────────────────────────────
    # Step 6: Verify position via IBKRBroker.get_positions()
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 6: Verifying position via IBKRBroker.get_positions()...")

    positions = await broker.get_positions()
    test_position = None
    for pos in positions:
        if pos.symbol == TEST_SYMBOL:
            test_position = pos
            break

    if test_position:
        logger.info(
            "Position found: %s %d shares @ $%.2f avg",
            test_position.symbol,
            test_position.shares,
            test_position.entry_price,
        )
        results.record_pass("Get Positions")
    else:
        results.record_fail("Get Positions", f"No {TEST_SYMBOL} position found")

    # ──────────────────────────────────────────────────────────────────
    # Step 7: Test order cancellation via IBKRBroker.cancel_order()
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 7: Testing IBKRBroker.cancel_order() on stop order...")

    if bracket_result.stop.order_id:
        cancel_success = await broker.cancel_order(bracket_result.stop.order_id)
        logger.info("Cancel request sent: success=%s", cancel_success)

        await asyncio.sleep(1)

        # Verify stop is cancelled
        stop_ib_id = broker._ulid_to_ibkr.get(bracket_result.stop.order_id, 0)
        trade = broker._find_trade_by_order_id(stop_ib_id)
        if trade and trade.orderStatus.status == "Cancelled":
            logger.info("Stop order CANCELLED successfully")
            results.record_pass("Cancel Order")
        elif trade:
            logger.warning("Stop order status: %s", trade.orderStatus.status)
            results.record_fail("Cancel Order", f"Status is {trade.orderStatus.status}, not Cancelled")
        else:
            results.record_fail("Cancel Order", "Cannot find stop trade")
    else:
        results.record_fail("Cancel Order", "No stop order ID")

    # ──────────────────────────────────────────────────────────────────
    # Step 8: Test flatten_all via IBKRBroker.flatten_all()
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 8: Testing IBKRBroker.flatten_all()...")

    flatten_results = await broker.flatten_all()
    logger.info("Flatten results: %d orders submitted", len(flatten_results))
    for fr in flatten_results:
        logger.info("  %s: %s", fr.order_id, fr.message)

    # Wait for flatten to complete
    await asyncio.sleep(3)

    # Verify position is closed
    positions = await broker.get_positions()
    is_flat = True
    for pos in positions:
        if pos.symbol == TEST_SYMBOL and pos.shares > 0:
            is_flat = False
            break

    if is_flat:
        results.record_pass("Flatten All")
        logger.info("Position is FLAT (0 shares)")
    else:
        results.record_fail("Flatten All", f"Still holding {TEST_SYMBOL}")

    # ──────────────────────────────────────────────────────────────────
    # Step 9: Verify no open orders remain
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 9: Verifying no open orders remain...")

    await asyncio.sleep(1)
    open_trades = broker._ib.openTrades()
    our_orders = []

    for trade in open_trades:
        order_id = trade.order.orderId
        # Check if this is one of our orders
        for ulid, ib_id in broker._ulid_to_ibkr.items():
            if ib_id == order_id:
                our_orders.append((ulid, order_id, trade.orderStatus.status))
                break

    if not our_orders:
        results.record_pass("No Open Orders")
    else:
        results.record_fail("No Open Orders", f"Found {len(our_orders)} orders: {our_orders}")

    # ──────────────────────────────────────────────────────────────────
    # Step 10: Disconnect
    # ──────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 10: Disconnecting...")
    await broker.disconnect()
    results.record_pass("Disconnect")

    # Print summary
    print(results.summary())

    return 0 if results.tests_failed == 0 else 1


def main() -> int:
    """Entry point."""
    logger.info("Starting Session 7: IBKR Bracket Order Lifecycle Test...")
    logger.info("Timestamp: %s UTC", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("")

    try:
        return asyncio.run(run_tests())
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Test failed with exception: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

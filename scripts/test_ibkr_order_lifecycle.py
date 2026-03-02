#!/usr/bin/env python3
"""IBKR Order Lifecycle Test Script.

Tests the complete order lifecycle on IBKR paper trading:
1. Connect to paper account (verify DU prefix)
2. Place MARKET order (BUY 1 SPY)
3. Wait for fill
4. Verify position
5. Flatten position (SELL 1 SPY)
6. Verify flat
7. Test bracket order (parent + stop + take-profit)
8. Cancel children and flatten

Run: python scripts/test_ibkr_order_lifecycle.py

IMPORTANT: Only runs on paper trading accounts (DU prefix).
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
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_SYMBOL = "SPY"  # Liquid ETF for testing
TEST_SHARES = 1
FILL_TIMEOUT_SECONDS = 30
BRACKET_STOP_OFFSET = 2.00  # $2 below entry for stop
BRACKET_TP_OFFSET = 2.00  # $2 above entry for take-profit


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
            "=" * 60,
            f"TEST SUMMARY: {status}",
            f"  Tests run: {self.tests_run}",
            f"  Passed: {self.tests_passed}",
            f"  Failed: {self.tests_failed}",
        ]
        if self.errors:
            lines.append("  Errors:")
            for err in self.errors:
                lines.append(f"    - {err}")
        lines.append("=" * 60)
        return "\n".join(lines)


async def run_tests() -> int:
    """Run the full IBKR order lifecycle test suite."""
    from ib_async import IB, LimitOrder, MarketOrder, StopOrder

    results = TestResults()
    ib = IB()

    # Get connection parameters from config
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "4002"))
    client_id = int(os.getenv("IBKR_CLIENT_ID", "99"))  # Use 99 for test script

    logger.info("=" * 60)
    logger.info("IBKR ORDER LIFECYCLE TEST")
    logger.info("=" * 60)
    logger.info("Host: %s, Port: %d, ClientId: %d", host, port, client_id)
    logger.info("Symbol: %s, Shares: %d", TEST_SYMBOL, TEST_SHARES)
    logger.info("")

    # ──────────────────────────────────────────────────────────────
    # Safety Check: Port must be 4002 (paper)
    # ──────────────────────────────────────────────────────────────
    if port == 4001:
        logger.critical("ABORT: Port 4001 is LIVE trading. Use port 4002 for paper.")
        results.record_fail("Safety Check - Port", "Port 4001 is LIVE, not paper")
        print(results.summary())
        return 1

    # ──────────────────────────────────────────────────────────────
    # Step 1: Connect to IBKR
    # ──────────────────────────────────────────────────────────────
    logger.info("Step 1: Connecting to IBKR...")
    try:
        await ib.connectAsync(host=host, port=port, clientId=client_id, timeout=30)

        if not ib.isConnected():
            results.record_fail("Connect", "Failed to connect to IB Gateway")
            print(results.summary())
            return 1

        results.record_pass("Connect to IB Gateway")

    except Exception as e:
        results.record_fail("Connect", str(e))
        print(results.summary())
        return 1

    # ──────────────────────────────────────────────────────────────
    # Safety Check: Account ID must start with "DU" (paper)
    # ──────────────────────────────────────────────────────────────
    accounts = ib.managedAccounts()
    if not accounts:
        results.record_fail("Safety Check - Account", "No managed accounts found")
        ib.disconnect()
        print(results.summary())
        return 1

    account_id = accounts[0]
    logger.info("Account ID: %s", account_id)

    if not account_id.startswith("DU"):
        logger.critical("ABORT: Account %s is NOT a paper account (no DU prefix)", account_id)
        results.record_fail("Safety Check - Account", f"Account {account_id} is not paper (no DU)")
        ib.disconnect()
        print(results.summary())
        return 1

    results.record_pass("Safety Check - Paper Account (DU prefix)")

    # Get account info
    account_values = {av.tag: av.value for av in ib.accountValues() if av.currency == "USD"}
    equity = float(account_values.get("NetLiquidation", 0))
    buying_power = float(account_values.get("BuyingPower", 0))
    logger.info("Equity: $%.2f, Buying Power: $%.2f", equity, buying_power)

    # ──────────────────────────────────────────────────────────────
    # Step 2: Create contract for test symbol
    # ──────────────────────────────────────────────────────────────
    from ib_async import Stock

    contract = Stock(TEST_SYMBOL, "SMART", "USD")
    await ib.qualifyContractsAsync(contract)
    logger.info("Contract qualified: %s", contract)

    # ──────────────────────────────────────────────────────────────
    # Step 3: Place MARKET order (BUY)
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 2: Placing MARKET BUY order for %d %s...", TEST_SHARES, TEST_SYMBOL)

    buy_order = MarketOrder("BUY", TEST_SHARES)
    buy_order.tif = "DAY"

    buy_trade = ib.placeOrder(contract, buy_order)
    logger.info("Order submitted: orderId=%d", buy_trade.order.orderId)

    # Wait for fill
    fill_price = None
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < FILL_TIMEOUT_SECONDS:
        await asyncio.sleep(0.5)
        if buy_trade.orderStatus.status == "Filled":
            fill_price = buy_trade.orderStatus.avgFillPrice
            filled_qty = int(buy_trade.orderStatus.filled)
            logger.info(
                "Order FILLED: %d shares @ $%.2f (commission: $%.2f)",
                filled_qty,
                fill_price,
                buy_trade.orderStatus.commission if buy_trade.orderStatus.commission else 0,
            )
            break
        logger.debug("Waiting for fill... status=%s", buy_trade.orderStatus.status)

    if fill_price is None:
        results.record_fail("Market Order Fill", f"No fill within {FILL_TIMEOUT_SECONDS}s")
        # Try to cancel and clean up
        ib.cancelOrder(buy_order)
        await asyncio.sleep(1)
        ib.disconnect()
        print(results.summary())
        return 1

    results.record_pass("Market Order Fill")

    # ──────────────────────────────────────────────────────────────
    # Step 4: Verify position
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 3: Verifying position...")

    await asyncio.sleep(1)  # Allow position to sync
    positions = ib.positions()
    test_position = None
    for pos in positions:
        if pos.contract.symbol == TEST_SYMBOL:
            test_position = pos
            break

    if test_position is None or test_position.position == 0:
        results.record_fail("Verify Position", f"No {TEST_SYMBOL} position found")
        ib.disconnect()
        print(results.summary())
        return 1

    logger.info(
        "Position: %d shares @ $%.2f avg cost, market value: $%.2f",
        int(test_position.position),
        test_position.avgCost,
        test_position.marketValue if hasattr(test_position, "marketValue") else 0,
    )
    results.record_pass("Verify Position")

    # ──────────────────────────────────────────────────────────────
    # Step 5: Flatten position (SELL)
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 4: Flattening position (SELL %d %s)...", TEST_SHARES, TEST_SYMBOL)

    sell_order = MarketOrder("SELL", TEST_SHARES)
    sell_order.tif = "DAY"

    sell_trade = ib.placeOrder(contract, sell_order)
    logger.info("Sell order submitted: orderId=%d", sell_trade.order.orderId)

    # Wait for fill
    sell_fill_price = None
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < FILL_TIMEOUT_SECONDS:
        await asyncio.sleep(0.5)
        if sell_trade.orderStatus.status == "Filled":
            sell_fill_price = sell_trade.orderStatus.avgFillPrice
            logger.info("Sell FILLED: @ $%.2f", sell_fill_price)
            break

    if sell_fill_price is None:
        results.record_fail("Flatten Position", f"Sell not filled within {FILL_TIMEOUT_SECONDS}s")
        ib.disconnect()
        print(results.summary())
        return 1

    results.record_pass("Flatten Position")

    # ──────────────────────────────────────────────────────────────
    # Step 6: Verify flat
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 5: Verifying position is flat...")

    await asyncio.sleep(1)
    positions = ib.positions()
    is_flat = True
    for pos in positions:
        if pos.contract.symbol == TEST_SYMBOL and pos.position != 0:
            is_flat = False
            break

    if is_flat:
        results.record_pass("Verify Flat")
        logger.info("Position is FLAT (0 shares)")
    else:
        results.record_fail("Verify Flat", f"Still holding {TEST_SYMBOL}")

    # Get updated account equity
    account_values = {av.tag: av.value for av in ib.accountValues() if av.currency == "USD"}
    final_equity = float(account_values.get("NetLiquidation", 0))
    pnl = final_equity - equity
    logger.info("Final equity: $%.2f (change: $%.2f)", final_equity, pnl)

    # ──────────────────────────────────────────────────────────────
    # Step 7: Test bracket order
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 6: Testing BRACKET order...")

    # Get current price estimate (use last fill as approximation)
    estimated_price = fill_price

    # Parent (entry) — MARKET BUY
    parent = MarketOrder("BUY", TEST_SHARES)
    parent.tif = "DAY"
    parent.transmit = False  # Don't transmit until all orders are placed

    # Stop loss — STOP SELL
    stop_price = round(estimated_price - BRACKET_STOP_OFFSET, 2)
    stop_order = StopOrder("SELL", TEST_SHARES, stop_price)
    stop_order.tif = "DAY"
    stop_order.transmit = False  # Wait for take-profit

    # Take profit — LIMIT SELL
    tp_price = round(estimated_price + BRACKET_TP_OFFSET, 2)
    tp_order = LimitOrder("SELL", TEST_SHARES, tp_price)
    tp_order.tif = "DAY"
    tp_order.transmit = True  # This triggers atomic submission

    logger.info(
        "Bracket: Entry=MARKET, Stop=$%.2f, TakeProfit=$%.2f",
        stop_price,
        tp_price,
    )

    # Place parent first to get orderId
    parent_trade = ib.placeOrder(contract, parent)
    parent_id = parent_trade.order.orderId
    logger.info("Parent order placed: orderId=%d", parent_id)

    # Link children to parent
    stop_order.parentId = parent_id
    tp_order.parentId = parent_id

    # Place stop (doesn't transmit yet)
    stop_trade = ib.placeOrder(contract, stop_order)
    logger.info("Stop order placed: orderId=%d", stop_trade.order.orderId)

    # Place take-profit (transmits entire bracket)
    tp_trade = ib.placeOrder(contract, tp_order)
    logger.info("TakeProfit order placed: orderId=%d (bracket transmitted)", tp_trade.order.orderId)

    # Wait for parent fill
    bracket_fill_price = None
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < FILL_TIMEOUT_SECONDS:
        await asyncio.sleep(0.5)
        if parent_trade.orderStatus.status == "Filled":
            bracket_fill_price = parent_trade.orderStatus.avgFillPrice
            logger.info("Bracket parent FILLED: @ $%.2f", bracket_fill_price)
            break

    if bracket_fill_price is None:
        results.record_fail("Bracket Order", f"Parent not filled within {FILL_TIMEOUT_SECONDS}s")
        # Cancel all bracket orders
        ib.cancelOrder(parent)
        ib.cancelOrder(stop_order)
        ib.cancelOrder(tp_order)
        await asyncio.sleep(1)
        ib.disconnect()
        print(results.summary())
        return 1

    results.record_pass("Bracket Parent Fill")

    # ──────────────────────────────────────────────────────────────
    # Step 8: Verify bracket children exist
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 7: Verifying bracket children...")

    await asyncio.sleep(1)
    open_orders = ib.openOrders()
    stop_found = False
    tp_found = False

    for order in open_orders:
        if order.orderId == stop_trade.order.orderId:
            stop_found = True
            logger.info("Stop order OPEN: orderId=%d, status=%s", order.orderId, "PreSubmitted/Submitted")
        if order.orderId == tp_trade.order.orderId:
            tp_found = True
            logger.info("TakeProfit order OPEN: orderId=%d, status=%s", order.orderId, "PreSubmitted/Submitted")

    # Also check trades cache
    for trade in ib.openTrades():
        if trade.order.orderId == stop_trade.order.orderId:
            stop_found = True
            logger.info(
                "Stop trade found: orderId=%d, status=%s",
                trade.order.orderId,
                trade.orderStatus.status,
            )
        if trade.order.orderId == tp_trade.order.orderId:
            tp_found = True
            logger.info(
                "TakeProfit trade found: orderId=%d, status=%s",
                trade.order.orderId,
                trade.orderStatus.status,
            )

    if stop_found and tp_found:
        results.record_pass("Bracket Children Visible")
    else:
        results.record_fail(
            "Bracket Children Visible",
            f"stop_found={stop_found}, tp_found={tp_found}",
        )

    # ──────────────────────────────────────────────────────────────
    # Step 9: Cancel children and flatten
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 8: Cancelling bracket children and flattening...")

    # Cancel stop and take-profit
    ib.cancelOrder(stop_trade.order)
    ib.cancelOrder(tp_trade.order)
    logger.info("Cancel requests sent for stop and TP orders")

    await asyncio.sleep(1)

    # Flatten the bracket position
    flatten_order = MarketOrder("SELL", TEST_SHARES)
    flatten_order.tif = "DAY"

    flatten_trade = ib.placeOrder(contract, flatten_order)
    logger.info("Flatten order submitted: orderId=%d", flatten_trade.order.orderId)

    # Wait for fill
    flatten_fill = None
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < FILL_TIMEOUT_SECONDS:
        await asyncio.sleep(0.5)
        if flatten_trade.orderStatus.status == "Filled":
            flatten_fill = flatten_trade.orderStatus.avgFillPrice
            logger.info("Flatten FILLED: @ $%.2f", flatten_fill)
            break

    if flatten_fill is None:
        results.record_fail("Bracket Flatten", f"Not filled within {FILL_TIMEOUT_SECONDS}s")
    else:
        results.record_pass("Bracket Flatten")

    # Verify flat
    await asyncio.sleep(1)
    positions = ib.positions()
    final_flat = True
    for pos in positions:
        if pos.contract.symbol == TEST_SYMBOL and pos.position != 0:
            final_flat = False
            break

    if final_flat:
        results.record_pass("Final Flat Verification")
    else:
        results.record_fail("Final Flat Verification", f"Still holding {TEST_SYMBOL}")

    # ──────────────────────────────────────────────────────────────
    # Step 10: Disconnect
    # ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("Step 9: Disconnecting...")
    ib.disconnect()
    results.record_pass("Disconnect")

    # Print summary
    print(results.summary())

    return 0 if results.tests_failed == 0 else 1


def main() -> int:
    """Entry point."""
    logger.info("Starting IBKR Order Lifecycle Test...")
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

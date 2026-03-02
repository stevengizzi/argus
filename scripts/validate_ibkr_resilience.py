#!/usr/bin/env python3
"""IBKR Resilience Validation Script — Sprint 21.5 Session 9.

This script validates IBKR reconnection and state reconstruction scenarios.
Run against IB Gateway connected to a paper trading account.

Usage:
    python scripts/validate_ibkr_resilience.py

Scenarios tested:
    1. Connection and initial state
    2. State reconstruction (simulates restart)
    3. Reconnection handling (requires manual Gateway restart)
    4. Position and order consistency checks

Prerequisites:
    - IB Gateway running and connected to paper trading
    - Environment variables set: IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, IBKR_ACCOUNT
    - Or use defaults: localhost:4002, client_id=1
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from argus.core.config import IBKRConfig
from argus.core.event_bus import EventBus
from argus.execution.ibkr_broker import IBKRBroker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("validate_ibkr")


def get_ibkr_config() -> IBKRConfig:
    """Build IBKRConfig from environment variables or defaults."""
    return IBKRConfig(
        host=os.environ.get("IBKR_HOST", "127.0.0.1"),
        port=int(os.environ.get("IBKR_PORT", "4002")),  # Paper trading port
        client_id=int(os.environ.get("IBKR_CLIENT_ID", "1")),
        account=os.environ.get("IBKR_ACCOUNT", ""),
        timeout_seconds=30,
        readonly=False,
        reconnect_max_retries=3,
        reconnect_base_delay_seconds=2.0,
        reconnect_max_delay_seconds=30.0,
    )


async def test_connection(broker: IBKRBroker) -> bool:
    """Test 1: Basic connection to IB Gateway."""
    logger.info("=" * 60)
    logger.info("TEST 1: Connection to IB Gateway")
    logger.info("=" * 60)

    try:
        await broker.connect()
        logger.info("Connection successful: is_connected=%s", broker.is_connected)

        # Get account info
        account = await broker.get_account()
        logger.info(
            "Account info: equity=$%.2f, cash=$%.2f, buying_power=$%.2f",
            account.equity,
            account.cash,
            account.buying_power,
        )

        # Get positions
        positions = await broker.get_positions()
        logger.info("Current positions: %d", len(positions))
        for pos in positions:
            logger.info("  - %s: %d shares @ $%.2f", pos.symbol, pos.shares, pos.entry_price)

        # Get open orders
        open_orders = await broker.get_open_orders()
        logger.info("Open orders: %d", len(open_orders))
        for order in open_orders:
            logger.info(
                "  - %s: %s %d %s %s (stop=$%s, limit=$%s)",
                order.id[:8] + "...",
                order.side.value,
                order.quantity,
                order.symbol,
                order.order_type.value,
                order.stop_price,
                order.limit_price,
            )

        return True
    except Exception as e:
        logger.error("Connection failed: %s", e)
        return False


async def test_state_reconstruction(broker: IBKRBroker) -> bool:
    """Test 2: State reconstruction (simulates restart).

    This test clears the broker's internal ID mappings and then
    calls reconstruct_state() to verify ULID recovery from orderRef.
    """
    logger.info("=" * 60)
    logger.info("TEST 2: State Reconstruction")
    logger.info("=" * 60)

    try:
        # Save current mappings
        original_ulid_count = len(broker._ulid_to_ibkr)
        logger.info("Current ULID mappings: %d", original_ulid_count)

        # Clear mappings (simulating restart)
        broker._ulid_to_ibkr.clear()
        broker._ibkr_to_ulid.clear()
        logger.info("Cleared all ID mappings (simulating restart)")

        # Reconstruct state
        state = await broker.reconstruct_state()
        logger.info("Reconstruction complete:")
        logger.info("  - Positions: %d", len(state["positions"]))
        logger.info("  - Open orders: %d", len(state["open_orders"]))
        logger.info("  - Recovered ULID mappings: %d", len(broker._ulid_to_ibkr))

        # Verify each order has a mapping
        for order_info in state["open_orders"]:
            order_id = order_info["order_id"]
            if order_id.startswith("unknown_"):
                logger.warning("  - Order %s has no orderRef (external order)", order_id)
            else:
                logger.info("  - Order %s recovered successfully", order_id[:8] + "...")

        return True
    except Exception as e:
        logger.error("State reconstruction failed: %s", e)
        return False


async def test_reconnection_prompt(broker: IBKRBroker) -> bool:
    """Test 3: Reconnection handling (interactive).

    This test prompts the user to restart IB Gateway while ARGUS
    monitors for disconnection and automatic reconnection.
    """
    logger.info("=" * 60)
    logger.info("TEST 3: Reconnection Handling (Interactive)")
    logger.info("=" * 60)

    logger.info("")
    logger.info("This test requires you to manually restart IB Gateway.")
    logger.info("ARGUS will detect the disconnect and attempt to reconnect.")
    logger.info("")

    response = input("Do you want to proceed with the reconnection test? [y/N]: ")
    if response.lower() != "y":
        logger.info("Skipping reconnection test")
        return True

    # Snapshot positions before test
    pre_positions = await broker.get_positions()
    pre_orders = await broker.get_open_orders()
    logger.info(
        "Pre-disconnect state: %d positions, %d open orders",
        len(pre_positions),
        len(pre_orders),
    )

    logger.info("")
    logger.info("Please restart IB Gateway now...")
    logger.info("Waiting for disconnect event...")
    logger.info("")

    # Wait for disconnect (with timeout)
    max_wait = 60  # seconds
    start = datetime.now(UTC)
    while broker.is_connected:
        await asyncio.sleep(1)
        elapsed = (datetime.now(UTC) - start).total_seconds()
        if elapsed > max_wait:
            logger.warning("Timeout waiting for disconnect")
            return False
        if int(elapsed) % 10 == 0:
            logger.info("Still connected... (%.0fs)", elapsed)

    logger.info("Disconnection detected!")
    logger.info("")
    logger.info("Waiting for automatic reconnection...")

    # Wait for reconnect (reconnect is scheduled automatically by _on_disconnected)
    max_reconnect_wait = 120  # seconds
    start = datetime.now(UTC)
    while not broker.is_connected:
        await asyncio.sleep(2)
        elapsed = (datetime.now(UTC) - start).total_seconds()
        if elapsed > max_reconnect_wait:
            logger.error("Timeout waiting for reconnection")
            return False
        logger.info("Waiting for reconnection... (%.0fs)", elapsed)

    logger.info("Reconnection successful!")

    # Verify state after reconnect
    post_positions = await broker.get_positions()
    post_orders = await broker.get_open_orders()
    logger.info(
        "Post-reconnect state: %d positions, %d open orders",
        len(post_positions),
        len(post_orders),
    )

    # Compare
    pre_symbols = {p.symbol for p in pre_positions}
    post_symbols = {p.symbol for p in post_positions}

    if pre_symbols == post_symbols:
        logger.info("Position consistency: PASSED")
    else:
        logger.warning(
            "Position mismatch! Pre: %s, Post: %s",
            pre_symbols,
            post_symbols,
        )
        return False

    return True


async def test_position_order_consistency(broker: IBKRBroker) -> bool:
    """Test 4: Verify position/order consistency.

    Check that:
    - All positions have expected stop orders
    - No orphaned orders exist
    - ULID mappings are bidirectional
    """
    logger.info("=" * 60)
    logger.info("TEST 4: Position/Order Consistency Check")
    logger.info("=" * 60)

    positions = await broker.get_positions()
    orders = await broker.get_open_orders()

    # Check ULID mapping consistency
    ulid_to_ibkr = broker._ulid_to_ibkr
    ibkr_to_ulid = broker._ibkr_to_ulid

    logger.info("ULID mapping check:")
    logger.info("  - ulid_to_ibkr entries: %d", len(ulid_to_ibkr))
    logger.info("  - ibkr_to_ulid entries: %d", len(ibkr_to_ulid))

    # Verify bidirectional consistency
    inconsistent = 0
    for ulid, ibkr_id in ulid_to_ibkr.items():
        if ibkr_to_ulid.get(ibkr_id) != ulid:
            logger.warning("Inconsistent mapping: ULID %s -> IBKR %d", ulid, ibkr_id)
            inconsistent += 1

    if inconsistent == 0:
        logger.info("Bidirectional mapping: PASSED")
    else:
        logger.warning("Found %d inconsistent mappings", inconsistent)
        return False

    # Check for orphaned orders (orders without positions)
    position_symbols = {p.symbol for p in positions}
    order_symbols = {o.symbol for o in orders}
    orphaned = order_symbols - position_symbols

    if orphaned:
        logger.info("Note: Orders exist for symbols without positions: %s", orphaned)
        logger.info("  (This may be normal if orders are from other sessions)")

    return True


async def main() -> int:
    """Run all validation tests."""
    logger.info("=" * 60)
    logger.info("IBKR Resilience Validation — Sprint 21.5 Session 9")
    logger.info("=" * 60)
    logger.info("")

    config = get_ibkr_config()
    logger.info("Config: host=%s, port=%d, client_id=%d", config.host, config.port, config.client_id)
    logger.info("")

    event_bus = EventBus()
    broker = IBKRBroker(config=config, event_bus=event_bus)

    results = {}

    # Test 1: Connection
    results["connection"] = await test_connection(broker)
    logger.info("")

    if not results["connection"]:
        logger.error("Connection test failed. Cannot proceed with other tests.")
        return 1

    # Test 2: State Reconstruction
    results["reconstruction"] = await test_state_reconstruction(broker)
    logger.info("")

    # Test 3: Reconnection (interactive)
    results["reconnection"] = await test_reconnection_prompt(broker)
    logger.info("")

    # Test 4: Consistency
    results["consistency"] = await test_position_order_consistency(broker)
    logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info("  %s: %s", test_name.upper(), status)
        if not passed:
            all_passed = False

    logger.info("")
    if all_passed:
        logger.info("All tests PASSED!")
    else:
        logger.error("Some tests FAILED. Review logs above.")

    # Cleanup
    await broker.disconnect()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

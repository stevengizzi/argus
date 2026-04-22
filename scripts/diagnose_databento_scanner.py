#!/usr/bin/env python3
"""Test script for DatabentoScanner gap calculation validation.

Validates the DatabentoScanner by:
1. Fetching historical daily bars from Databento
2. Computing gap percentages
3. Cross-referencing with known market data

Usage:
    python scripts/test_databento_scanner.py

Requires:
    - DATABENTO_API_KEY environment variable set
    - Active Databento subscription (EQUS.MINI dataset)
"""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from argus.data.databento_scanner import DatabentoScanner, DatabentoScannerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def test_scanner_gap_calculation() -> None:
    """Test scanner gap calculation with historical data."""
    # Check API key
    api_key = os.getenv("DATABENTO_API_KEY")
    if not api_key:
        logger.error("DATABENTO_API_KEY not set. Set it in .env file.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("DatabentoScanner Gap Calculation Test")
    logger.info("=" * 60)

    # Configure scanner with a diverse set of symbols
    # Mix of Nasdaq (AAPL, MSFT, NVDA, TSLA, AMZN, META, GOOGL, NFLX)
    # and NYSE (SPY is ARCA, which is covered by EQUS.MINI)
    test_symbols = [
        "AAPL",
        "MSFT",
        "NVDA",
        "TSLA",
        "AMD",
        "AMZN",
        "META",
        "GOOGL",
        "NFLX",
        "SPY",
    ]

    config = DatabentoScannerConfig(
        universe_symbols=test_symbols,
        min_gap_pct=0.01,  # 1% minimum gap for testing (lower threshold)
        min_price=5.0,
        max_price=1000.0,
        min_volume=100_000,  # Lower volume threshold for testing
        max_symbols_returned=10,
        dataset="EQUS.MINI",
    )

    scanner = DatabentoScanner(config=config)

    # Test 1: Recent trading day (Friday Feb 28, 2026 or most recent)
    # Use a known past date for reproducibility
    test_date = datetime(2026, 2, 27, 12, 0, 0, tzinfo=UTC)  # Thursday Feb 27, 2026

    logger.info("\n--- Test 1: Gap calculation for %s ---", test_date.strftime("%Y-%m-%d"))

    try:
        candidates = await scanner.scan_with_gap_data(
            symbols=test_symbols,
            reference_date=test_date,
        )

        if not candidates:
            logger.warning("No candidates returned. Possible reasons:")
            logger.warning("  - No symbols met gap threshold")
            logger.warning("  - Data not available for this date")
            logger.warning("  - API error")
        else:
            logger.info("\n%d candidates found:", len(candidates))
            for c in candidates:
                direction = "UP" if c.gap_pct > 0 else "DOWN"
                logger.info(
                    "  %s: %.2f%% gap %s",
                    c.symbol,
                    abs(c.gap_pct) * 100,
                    direction,
                )

    except Exception as e:
        logger.error("Test 1 failed: %s", e)
        import traceback

        traceback.print_exc()

    # Test 2: Use scan() method (main entry point)
    logger.info("\n--- Test 2: scan() method with full pipeline ---")

    try:
        # Create fresh scanner
        scanner2 = DatabentoScanner(config=config)
        await scanner2.start()

        candidates2 = await scanner2.scan([])

        logger.info("\nscan() returned %d candidates:", len(candidates2))
        for c in candidates2:
            if c.gap_pct != 0:
                direction = "UP" if c.gap_pct > 0 else "DOWN"
                logger.info("  %s: %.2f%% gap %s", c.symbol, abs(c.gap_pct) * 100, direction)
            else:
                logger.info("  %s: gap_pct=0 (fallback mode)", c.symbol)

        await scanner2.stop()

    except Exception as e:
        logger.error("Test 2 failed: %s", e)
        import traceback

        traceback.print_exc()

    # Test 3: Edge case - very high gap threshold (should return nothing)
    logger.info("\n--- Test 3: Edge case - high gap threshold (20%) ---")

    config_high_gap = DatabentoScannerConfig(
        universe_symbols=test_symbols,
        min_gap_pct=0.20,  # 20% - unlikely to have any matches
        min_price=5.0,
        max_price=1000.0,
        min_volume=100_000,
        max_symbols_returned=10,
        dataset="EQUS.MINI",
    )
    scanner3 = DatabentoScanner(config=config_high_gap)

    candidates3 = await scanner3.scan_with_gap_data(
        symbols=test_symbols,
        reference_date=test_date,
    )

    if len(candidates3) == 0:
        logger.info("PASS: No candidates with 20%+ gap (expected)")
    else:
        logger.info("Found %d candidates with 20%+ gap (unusual):", len(candidates3))
        for c in candidates3:
            logger.info("  %s: %.2f%% gap", c.symbol, abs(c.gap_pct) * 100)

    # Test 4: Fetch raw daily data for manual verification
    logger.info("\n--- Test 4: Raw daily data for verification ---")

    try:
        import databento as db

        client = db.Historical(key=api_key)

        # Fetch 3 days of data for AAPL
        start = test_date - timedelta(days=5)
        end = test_date + timedelta(days=1)

        data = client.timeseries.get_range(
            dataset="EQUS.MINI",
            symbols=["AAPL"],
            schema="ohlcv-1d",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            stype_in="raw_symbol",
        )

        df = data.to_df().reset_index()

        if not df.empty:
            logger.info("\nAAPL daily bars (for verification):")
            logger.info("-" * 70)

            for _, row in df.iterrows():
                ts = row["ts_event"]
                o, h, lo, c, v = row["open"], row["high"], row["low"], row["close"], row["volume"]
                logger.info(
                    "  %s: O=%.2f H=%.2f L=%.2f C=%.2f V=%d",
                    ts.strftime("%Y-%m-%d"),
                    o,
                    h,
                    lo,
                    c,
                    v,
                )

            # Compute gap manually for last 2 days
            if len(df) >= 2:
                df_sorted = df.sort_values("ts_event")
                prev = df_sorted.iloc[-2]
                curr = df_sorted.iloc[-1]
                manual_gap = (curr["open"] - prev["close"]) / prev["close"]
                logger.info(
                    "\nManual gap calculation (AAPL):"
                )
                logger.info(
                    "  prev_close (%.2f) -> today_open (%.2f) = %.2f%% gap",
                    prev["close"],
                    curr["open"],
                    manual_gap * 100,
                )
        else:
            logger.warning("No raw data returned for AAPL")

    except Exception as e:
        logger.error("Raw data fetch failed: %s", e)

    logger.info("\n" + "=" * 60)
    logger.info("Scanner Test Complete")
    logger.info("=" * 60)


async def test_scanner_filtering() -> None:
    """Test scanner filter logic."""
    logger.info("\n--- Test 5: Filter logic verification ---")

    # Test with strict filters
    strict_config = DatabentoScannerConfig(
        universe_symbols=["AAPL", "MSFT", "NVDA"],
        min_gap_pct=0.02,  # 2% gap
        min_price=100.0,  # High min price
        max_price=200.0,  # AAPL is ~170-180, others may be filtered
        min_volume=1_000_000,
        max_symbols_returned=10,
        dataset="EQUS.MINI",
    )

    scanner = DatabentoScanner(config=strict_config)
    test_date = datetime(2026, 2, 27, 12, 0, 0, tzinfo=UTC)

    candidates = await scanner.scan_with_gap_data(reference_date=test_date)

    logger.info("Strict filter test (price 100-200, gap >= 2%%):")
    if not candidates:
        logger.info("  No candidates passed filters (expected for strict filters)")
    else:
        for c in candidates:
            logger.info("  %s: %.2f%% gap", c.symbol, abs(c.gap_pct) * 100)


if __name__ == "__main__":
    asyncio.run(test_scanner_gap_calculation())
    asyncio.run(test_scanner_filtering())

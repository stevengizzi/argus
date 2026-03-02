#!/usr/bin/env python3
"""Diagnose Databento EQUS.MINI capabilities.

This script tests all three Databento API paths WITHOUT starting the full
ARGUS system:
1. Historical daily bars (used by scanner for gap calculation)
2. Historical 1-minute bars (used by DataService for warmup)
3. Live streaming capability (used by DataService for real-time data)

Run this script to verify Databento connectivity and data availability
before starting the main ARGUS system.

Usage:
    python scripts/diagnose_databento.py

Requires:
    - DATABENTO_API_KEY environment variable set
    - databento package installed
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

# Add project root to path for running standalone
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, ".env"))
except ImportError:
    pass


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def print_test(num: int, title: str) -> None:
    """Print a test section header."""
    print(f"\n[{num}] {title}")


def main() -> int:
    """Run Databento diagnostic tests.

    Returns:
        0 if all critical tests pass, 1 otherwise.
    """
    import databento as db

    print_header("DATABENTO EQUS.MINI DIAGNOSTIC")
    print(f"Databento library version: {db.__version__}")

    # Check API key
    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        print("\n[ERROR] DATABENTO_API_KEY environment variable not set")
        print("Please set it in your .env file or export it.")
        return 1

    print(f"API key: {api_key[:8]}...{api_key[-4:]} (masked)")

    # Initialize clients
    try:
        hist_client = db.Historical(key=api_key)
        print("\nHistorical client initialized successfully")
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize Historical client: {e}")
        return 1

    all_passed = True

    # Test 1: Historical data availability (daily bars)
    print_test(1, "Historical Data Range (Daily Bars)")
    try:
        # Query without specifying end date to get latest available
        data = hist_client.timeseries.get_range(
            dataset="EQUS.MINI",
            symbols=["SPY"],
            schema="ohlcv-1d",
            start="2026-02-25",  # Last week
            stype_in="raw_symbol",
        )
        df = data.to_df()
        if not df.empty:
            df = df.reset_index()
            # ts_event is a Timestamp in the DataFrame (converted by to_df())
            latest_ts = df["ts_event"].max()
            # Prices are already converted to float by to_df()
            last_close = df.iloc[-1]["close"]
            print(f"  Latest daily bar: {latest_ts.strftime('%Y-%m-%d')}")
            print(f"  SPY close: ${last_close:.2f}")
            print(f"  Total bars returned: {len(df)}")
            print("  [PASS] Historical daily bars working")
        else:
            print("  [WARN] No daily data returned")
            all_passed = False
    except db.BentoHttpError as e:
        if e.http_status == 422 and "data_end_after_available_end" in str(e):
            print(f"  [INFO] Data lag detected: {e}")
            # Try to extract and display the available end date
            import re
            match = re.search(r"data available up to '(\d{4}-\d{2}-\d{2})", str(e))
            if match:
                print(f"  [INFO] Latest available date: {match.group(1)}")
        else:
            print(f"  [FAIL] Historical daily bars failed: {e}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Historical daily bars failed: {e}")
        all_passed = False

    # Test 2: Historical 1-minute bars (what DataService uses for warmup)
    print_test(2, "Historical 1-Minute Bars (Warmup Data)")
    try:
        # Use dates from last Friday to avoid weekend issues
        # Find the most recent Friday
        today = datetime.now(timezone.utc)
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0 and today.hour < 21:  # Before market close
            days_since_friday = 7
        last_friday = today - timedelta(days=days_since_friday)
        start_str = last_friday.strftime("%Y-%m-%dT14:00:00")
        end_str = last_friday.strftime("%Y-%m-%dT16:00:00")

        data = hist_client.timeseries.get_range(
            dataset="EQUS.MINI",
            symbols=["SPY"],
            schema="ohlcv-1m",
            start=start_str,
            end=end_str,
            stype_in="raw_symbol",
        )
        df = data.to_df()
        if not df.empty:
            df = df.reset_index()
            # ts_event is a Timestamp, not nanoseconds
            min_ts = df["ts_event"].min()
            max_ts = df["ts_event"].max()
            print(f"  Query: {start_str} to {end_str}")
            print(f"  Bars returned: {len(df)}")
            print(f"  Time range: {min_ts.strftime('%H:%M')} to {max_ts.strftime('%H:%M')}")
            print("  [PASS] Historical 1-min bars working")
        else:
            print(f"  [WARN] No 1-min data returned for {start_str}")
            print("  This may be expected if querying weekend/holiday")
    except db.BentoHttpError as e:
        if e.http_status == 422:
            print(f"  [INFO] Data not available for requested range: {e}")
        else:
            print(f"  [FAIL] Historical 1-min bars failed: {e}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Historical 1-min bars failed: {e}")
        all_passed = False

    # Test 3: Live streaming capability check
    print_test(3, "Live Stream Connection")
    try:
        live_client = db.Live(key=api_key)
        live_client.subscribe(
            dataset="EQUS.MINI",
            schema="ohlcv-1m",
            symbols=["SPY"],
            stype_in="raw_symbol",
        )
        # Don't actually start receiving - just verify subscription accepted
        print("  [PASS] Live subscription accepted")
        print("  (No data outside market hours - this is expected)")

        # Check symbology map gets populated
        live_client.start()
        # Give it a moment to receive initial messages
        import time
        time.sleep(2)
        symbology_count = len(live_client.symbology_map) if live_client.symbology_map else 0
        print(f"  Symbology mappings received: {symbology_count}")
        live_client.stop()
    except db.BentoHttpError as e:
        if "license" in str(e).lower():
            print(f"  [FAIL] Live subscription failed: {e}")
            print("  [WARN] This may indicate EQUS.MINI doesn't support")
            print("         live streaming on Standard plan. Check with Databento.")
            all_passed = False
        elif "dataset" in str(e).lower():
            print(f"  [FAIL] Dataset error: {e}")
            print("  [WARN] Dataset may not support this schema for live streaming.")
            all_passed = False
        else:
            print(f"  [FAIL] Live subscription failed: {e}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Live subscription failed: {e}")
        all_passed = False

    # Test 4: Check what schemas are available
    print_test(4, "Available Schemas")
    schemas_to_test = ["ohlcv-1m", "ohlcv-1d", "trades", "tbbo"]

    # Use a recent date for schema tests
    schema_test_start = "2026-02-27T15:55:00"
    schema_test_end = "2026-02-27T16:00:00"

    for schema in schemas_to_test:
        try:
            data = hist_client.timeseries.get_range(
                dataset="EQUS.MINI",
                symbols=["SPY"],
                schema=schema,
                start=schema_test_start,
                end=schema_test_end,
                stype_in="raw_symbol",
            )
            df = data.to_df()
            record_count = len(df) if not df.empty else 0
            print(f"  {schema}: [PASS] ({record_count} records)")
        except db.BentoHttpError as e:
            if e.http_status == 422:
                print(f"  {schema}: [INFO] Data not available for test range")
            else:
                print(f"  {schema}: [FAIL] ({e})")
        except Exception as e:
            print(f"  {schema}: [FAIL] ({e})")

    # Test 5: Check available symbols (sample query)
    print_test(5, "Symbol Coverage (Sample)")
    test_symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOGL", "AMZN", "META"]
    try:
        data = hist_client.timeseries.get_range(
            dataset="EQUS.MINI",
            symbols=test_symbols,
            schema="ohlcv-1d",
            start="2026-02-25",
            stype_in="raw_symbol",
        )
        df = data.to_df()
        if not df.empty:
            df = df.reset_index()
            if "symbol" in df.columns:
                found_symbols = df["symbol"].unique().tolist()
                print(f"  Requested: {len(test_symbols)} symbols")
                print(f"  Found: {len(found_symbols)} symbols")
                print(f"  Symbols: {', '.join(found_symbols)}")
                print("  [PASS] Multi-symbol query working")
            else:
                print("  [WARN] Symbol column not in response")
        else:
            print("  [WARN] No data returned for symbol test")
    except Exception as e:
        print(f"  [FAIL] Symbol coverage test failed: {e}")

    # Summary
    print_header("DIAGNOSTIC COMPLETE")
    if all_passed:
        print("[SUCCESS] All critical tests passed")
        print("\nDatabento EQUS.MINI is ready for use.")
        return 0
    else:
        print("[WARNING] Some tests failed or had warnings")
        print("\nReview the output above and check:")
        print("  - API key permissions")
        print("  - Subscription tier (Standard vs Plus)")
        print("  - Data availability for requested dates")
        return 1


if __name__ == "__main__":
    sys.exit(main())

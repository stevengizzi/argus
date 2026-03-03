#!/usr/bin/env python3
"""Diagnostic script to verify Databento live streaming is working.

Usage: python scripts/diagnose_live_streaming.py

Connects to Databento EQUS.MINI, subscribes to AAPL ohlcv-1m, and prints
the first 3 records received. Times out after 60 seconds with error message.
"""

import asyncio
import os
import sys
import time
from datetime import datetime, UTC
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()
    print(f"✓ Loaded environment from {env_file}")
else:
    print(f"✗ No .env file found at {env_file}")
    sys.exit(1)

# Check API key
api_key = os.getenv("DATABENTO_API_KEY")
if not api_key:
    print("✗ DATABENTO_API_KEY not found in environment")
    sys.exit(1)
print(f"✓ DATABENTO_API_KEY found (starts with: {api_key[:10]}...)")

# Import databento after loading env
try:
    import databento as db
    print(f"✓ Databento library version: {db.__version__}")
except ImportError:
    print("✗ databento library not installed")
    sys.exit(1)


def main() -> None:
    """Run the diagnostic."""
    print("\n" + "=" * 60)
    print("DATABENTO LIVE STREAMING DIAGNOSTIC")
    print("=" * 60)
    print(f"Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Dataset: EQUS.MINI")
    print(f"Symbol: AAPL")
    print(f"Schema: ohlcv-1m")
    print("=" * 60 + "\n")

    # Create live client
    print("Creating Databento Live client...")
    client = db.Live(key=api_key)

    # Subscribe
    print("Subscribing to EQUS.MINI ohlcv-1m for AAPL...")
    client.subscribe(
        dataset="EQUS.MINI",
        schema="ohlcv-1m",
        symbols=["AAPL"],
        stype_in="raw_symbol",
    )

    # Track records
    records_received = []
    start_time = time.monotonic()
    timeout_seconds = 60

    def record_callback(record: db.OHLCVMsg | db.SymbolMappingMsg | db.SystemMsg) -> None:
        """Handle incoming records."""
        elapsed = time.monotonic() - start_time

        if isinstance(record, db.OHLCVMsg):
            # Databento prices are fixed-point × 1e9
            price_scale = 1e-9
            ts = datetime.fromtimestamp(record.ts_event / 1e9, tz=UTC)

            # Resolve symbol from symbology_map
            symbol = client.symbology_map.get(record.instrument_id, f"ID:{record.instrument_id}")

            print(f"\n[{elapsed:.1f}s] OHLCVMsg received:")
            print(f"  Symbol: {symbol} (instrument_id={record.instrument_id})")
            print(f"  Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"  Open:  ${record.open * price_scale:.2f}")
            print(f"  High:  ${record.high * price_scale:.2f}")
            print(f"  Low:   ${record.low * price_scale:.2f}")
            print(f"  Close: ${record.close * price_scale:.2f}")
            print(f"  Volume: {record.volume:,}")

            records_received.append(record)

            if len(records_received) >= 3:
                print(f"\n✓ SUCCESS: Received {len(records_received)} OHLCV records")
                client.stop()

        elif isinstance(record, db.SymbolMappingMsg):
            print(f"[{elapsed:.1f}s] SymbolMappingMsg: {record}")

        elif isinstance(record, db.SystemMsg):
            print(f"[{elapsed:.1f}s] SystemMsg: {record}")

    # Register callback
    client.add_callback(record_callback)

    # Start streaming
    print("Starting live stream...")
    client.start()

    # Wait for records or timeout
    print(f"Waiting for OHLCV records (timeout: {timeout_seconds}s)...\n")

    while time.monotonic() - start_time < timeout_seconds:
        if len(records_received) >= 3:
            break
        time.sleep(0.5)

    # Check result
    if len(records_received) == 0:
        print(f"\n✗ TIMEOUT: No OHLCV records received after {timeout_seconds}s")
        print("\nPossible causes:")
        print("  1. Market is closed (check if 9:30 AM - 4:00 PM ET)")
        print("  2. Network/firewall blocking Databento TCP connection")
        print("  3. API key issue (subscription inactive?)")
        print("  4. Symbol not trading (check if AAPL has activity)")
        client.stop()
        sys.exit(1)
    elif len(records_received) < 3:
        print(f"\n⚠ PARTIAL: Only received {len(records_received)}/3 records")
        print("Data is flowing but slowly. This may be normal for low-volume periods.")
        client.stop()
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("DIAGNOSTIC COMPLETE: Databento live streaming is WORKING")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()

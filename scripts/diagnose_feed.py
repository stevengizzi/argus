#!/usr/bin/env python3
"""Diagnostic script to compare IEX vs SIP bar counts from Alpaca.

Usage:
    python scripts/diagnose_feed.py

Requires: ALPACA_API_KEY and ALPACA_SECRET_KEY env vars.
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        return

    client = StockHistoricalDataClient(api_key, secret_key)

    symbols = ["NVDA", "AMZN", "AAPL", "GOOGL", "NFLX"]
    et_tz = ZoneInfo("America/New_York")
    now = datetime.now(et_tz)

    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} ET")
    print()

    # Test 1: Yesterday's data (should work for both feeds)
    if now.weekday() == 0:  # Monday
        days_back = 3
    elif now.weekday() == 6:  # Sunday
        days_back = 2
    else:
        days_back = 1

    yesterday = now - timedelta(days=days_back)
    hist_start = yesterday.replace(hour=9, minute=30, second=0, microsecond=0)
    hist_end = yesterday.replace(hour=10, minute=30, second=0, microsecond=0)

    print("=" * 60)
    print(f"TEST 1: Historical data ({hist_start.strftime('%Y-%m-%d')} 09:30-10:30 ET)")
    print("=" * 60)
    print(f"{'Symbol':<8} {'IEX':<8} {'SIP':<8}")
    print("-" * 24)

    for symbol in symbols:
        iex_count = 0
        sip_count = 0

        try:
            iex_req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=hist_start,
                end=hist_end,
                feed=DataFeed.IEX,
            )
            iex_res = client.get_stock_bars(iex_req)
            iex_count = len(iex_res[symbol]) if symbol in iex_res.data else 0
        except Exception as e:
            iex_count = f"ERR"

        try:
            sip_req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=hist_start,
                end=hist_end,
                feed=DataFeed.SIP,
            )
            sip_res = client.get_stock_bars(sip_req)
            sip_count = len(sip_res[symbol]) if symbol in sip_res.data else 0
        except Exception as e:
            sip_count = f"ERR"

        print(f"{symbol:<8} {str(iex_count):<8} {str(sip_count):<8}")

    # Test 2: Real-time SIP (last 5 minutes)
    print()
    print("=" * 60)
    print("TEST 2: Real-time data (last 5 minutes)")
    print("=" * 60)

    rt_start = now - timedelta(minutes=5)

    print(f"Querying: {rt_start.strftime('%H:%M')} to {now.strftime('%H:%M')} ET")
    print()

    for symbol in ["AAPL"]:
        print(f"Testing {symbol}...")

        # IEX real-time
        try:
            iex_req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=rt_start,
                end=now,
                feed=DataFeed.IEX,
            )
            iex_res = client.get_stock_bars(iex_req)
            iex_count = len(iex_res[symbol]) if symbol in iex_res.data else 0
            print(f"  IEX real-time: {iex_count} bars ✓")
        except Exception as e:
            print(f"  IEX real-time: ERROR - {e}")

        # SIP real-time
        try:
            sip_req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=rt_start,
                end=now,
                feed=DataFeed.SIP,
            )
            sip_res = client.get_stock_bars(sip_req)
            sip_count = len(sip_res[symbol]) if symbol in sip_res.data else 0
            print(f"  SIP real-time: {sip_count} bars ✓")
            print()
            print("  *** REAL-TIME SIP ACCESS CONFIRMED! ***")
            print("  Your account has Algo Trader Plus or equivalent subscription.")
        except Exception as e:
            err_str = str(e)
            if "subscription does not permit" in err_str:
                print(f"  SIP real-time: NOT AVAILABLE (free tier)")
                print()
                print("  Your account is on free tier (IEX only for real-time).")
            else:
                print(f"  SIP real-time: ERROR - {e}")

    print()
    print("=" * 60)
    print("RECOMMENDATION:")
    print("=" * 60)
    print()
    print("The issue is IEX WebSocket streaming vs REST polling:")
    print()
    print("- IEX **WebSocket** only sends a bar when IEX has trades in that minute")
    print("- IEX **REST API** aggregates and returns bars for all minutes")
    print("- For liquid stocks (NVDA, AAPL), IEX WebSocket may miss ~50% of bars")
    print()
    print("If real-time SIP is available, change config/brokers.yaml:")
    print('  data_feed: "sip"')
    print()
    print("If not, options are:")
    print("  1. Upgrade to Alpaca Algo Trader Plus ($99/mo)")
    print("  2. Poll REST API every 60s instead of relying on WebSocket bars")
    print("  3. Accept sparse IEX data and use longer OR windows (less sensitive)")


if __name__ == "__main__":
    main()

"""Sprint 29 smoke backtest — detect patterns on historical data.

Runs each of the 5 new patterns against 6 months of 1-minute data
for AAPL, MSFT, NVDA, TSLA, META. Reports detection counts only.

Usage:
    python scripts/smoke_test_sprint29.py
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from argus.strategies.patterns.base import CandleBar, PatternModule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

DATA_DIR = Path("data/databento_cache")
SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "META"]
START_DATE = date(2025, 9, 1)
END_DATE = date(2026, 3, 1)


def load_parquet_data(
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Load Parquet files for a symbol from the databento cache."""
    symbol_dir = DATA_DIR / symbol
    if not symbol_dir.exists():
        logger.warning("No data for %s", symbol)
        return pd.DataFrame()

    dfs = []
    current = start_date.replace(day=1)
    while current <= end_date:
        fname = f"{current.strftime('%Y-%m')}.parquet"
        fpath = symbol_dir / fname
        if fpath.exists():
            df = pd.read_parquet(fpath)
            dfs.append(df)
        current = (current + timedelta(days=32)).replace(day=1)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    # Ensure timestamp column exists and is datetime
    if "ts_event" in combined.columns:
        combined["timestamp"] = pd.to_datetime(combined["ts_event"], utc=True)
    elif "timestamp" not in combined.columns:
        logger.warning("No timestamp column found for %s", symbol)
        return pd.DataFrame()
    else:
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)

    # Filter to date range
    combined = combined[
        (combined["timestamp"].dt.date >= start_date)
        & (combined["timestamp"].dt.date <= end_date)
    ]

    # Normalize column names
    col_map = {}
    for needed in ["open", "high", "low", "close", "volume"]:
        if needed not in combined.columns:
            for col in combined.columns:
                if col.lower() == needed:
                    col_map[col] = needed
                    break
    if col_map:
        combined = combined.rename(columns=col_map)

    return combined


def df_to_candle_bars(df: pd.DataFrame) -> list[CandleBar]:
    """Convert a DataFrame to a list of CandleBar objects."""
    bars = []
    for _, row in df.iterrows():
        try:
            bars.append(
                CandleBar(
                    timestamp=row["timestamp"].to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0)),
                )
            )
        except (KeyError, ValueError):
            continue
    return bars


def compute_indicators(bars: list[CandleBar]) -> dict[str, float]:
    """Compute basic indicators from a window of bars."""
    if len(bars) < 2:
        return {}

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    # ATR (simple average true range)
    trs = []
    for i in range(1, len(bars)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    atr = sum(trs) / len(trs) if trs else 1.0

    # VWAP approximation (cumulative)
    total_pv = sum(b.close * b.volume for b in bars)
    total_vol = sum(b.volume for b in bars)
    vwap = total_pv / total_vol if total_vol > 0 else closes[-1]

    # Relative volume (last bar volume vs avg)
    avg_vol = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1.0
    rvol = volumes[-1] / avg_vol if avg_vol > 0 else 1.0

    return {
        "atr": atr,
        "vwap": vwap,
        "rvol": rvol,
        "prev_close": closes[-2] if len(closes) >= 2 else closes[-1],
    }


def run_pattern_detection(
    pattern: PatternModule,
    bars: list[CandleBar],
) -> int:
    """Run pattern detection on a sliding window of bars."""
    lookback = pattern.lookback_bars
    detections = 0

    for i in range(lookback, len(bars)):
        window = bars[i - lookback : i + 1]
        indicators = compute_indicators(window)
        result = pattern.detect(window, indicators)
        if result is not None:
            detections += 1

    return detections


def create_patterns() -> dict[str, PatternModule]:
    """Create all 5 new patterns with default parameters."""
    from argus.strategies.patterns import (
        ABCDPattern,
        DipAndRipPattern,
        GapAndGoPattern,
        HODBreakPattern,
        PreMarketHighBreakPattern,
    )

    return {
        "dip_and_rip": DipAndRipPattern(),
        "hod_break": HODBreakPattern(),
        "abcd": ABCDPattern(),
        "gap_and_go": GapAndGoPattern(),
        "premarket_high_break": PreMarketHighBreakPattern(),
    }


def main() -> None:
    """Run smoke backtests for all 5 new patterns."""
    patterns = create_patterns()

    results: dict[str, dict[str, int]] = defaultdict(dict)
    errors: list[str] = []

    for symbol in SYMBOLS:
        logger.info("Loading data for %s...", symbol)
        df = load_parquet_data(symbol, START_DATE, END_DATE)
        if df.empty:
            logger.warning("No data for %s — skipping", symbol)
            for pname in patterns:
                results[pname][symbol] = -1  # -1 = no data
            continue

        logger.info(
            "  %s: %d bars (%s to %s)",
            symbol,
            len(df),
            df["timestamp"].min().date(),
            df["timestamp"].max().date(),
        )

        # Convert to CandleBar list (sample to keep runtime reasonable)
        # Use only market hours bars
        df_et = df.copy()
        df_et["hour_et"] = df_et["timestamp"].dt.tz_convert(ET).dt.hour
        df_market = df_et[
            (df_et["hour_et"] >= 9) & (df_et["hour_et"] < 16)
        ].copy()

        bars = df_to_candle_bars(df_market)
        logger.info("  %s: %d market-hours bars", symbol, len(bars))

        for pname, pattern in patterns.items():
            try:
                count = run_pattern_detection(pattern, bars)
                results[pname][symbol] = count
                logger.info("  %s / %s: %d detections", symbol, pname, count)
            except Exception as e:
                error_msg = f"{pname}/{symbol}: {type(e).__name__}: {e}"
                errors.append(error_msg)
                results[pname][symbol] = -2  # -2 = error
                logger.error("  ERROR: %s", error_msg)

    # Print summary table
    print("\n" + "=" * 80)
    print("SPRINT 29 SMOKE BACKTEST RESULTS")
    print(f"Data range: {START_DATE} to {END_DATE}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print("=" * 80)
    print(f"{'Pattern':<25} " + " ".join(f"{s:>8}" for s in SYMBOLS) + "  TOTAL")
    print("-" * 80)

    for pname in patterns:
        counts = [results[pname].get(s, -1) for s in SYMBOLS]
        total = sum(c for c in counts if c > 0)
        row = f"{pname:<25} "
        for c in counts:
            if c == -1:
                row += "  no_data"
            elif c == -2:
                row += "   ERROR"
            else:
                row += f"{c:>8}"
        row += f"  {total:>5}"
        print(row)

    print("=" * 80)

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\nAll patterns completed without error.")
        sys.exit(0)


if __name__ == "__main__":
    main()

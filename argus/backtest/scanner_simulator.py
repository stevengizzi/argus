"""Scanner simulation for backtesting.

In live trading, AlpacaScanner fetches pre-market snapshots to find
gapping stocks. In backtest mode, we don't have pre-market data
(IEX feed covers regular hours only - see DEF-007).

Instead, we compute the gap as:
    gap_pct = (day_open - prev_close) / prev_close

Where:
    day_open = first 1m bar's open price on the current day
    prev_close = last 1m bar's close price on the previous trading day

We then apply the same filter criteria as the live scanner:
    - min_gap_pct (default 2%)
    - min_price / max_price range

If the filter produces zero symbols for a day, optionally fall back
to feeding all symbols (configurable).

Decision reference: DEC-052 (Scanner Simulation via Gap Computation)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


@dataclass
class DailyWatchlist:
    """Watchlist for a single trading day.

    Attributes:
        trading_date: The date this watchlist is for.
        symbols: List of symbols that passed the scanner filters.
        mode: How the watchlist was generated ("gap_filter" or "all_symbols").
        gap_data: Dict of symbol -> gap percentage for symbols that gapped.
    """

    trading_date: date
    symbols: list[str]
    mode: str  # "gap_filter" or "all_symbols"
    gap_data: dict[str, float] = field(default_factory=dict)


class ScannerSimulator:
    """Simulates pre-market scanning for backtesting.

    Pre-computes watchlists for all trading days by analyzing gap data
    from the historical bar data.

    Args:
        min_gap_pct: Minimum gap percentage to qualify (default 0.02 = 2%).
        min_price: Minimum stock price filter.
        max_price: Maximum stock price filter.
        fallback_all_symbols: If True, use all symbols when gap filter
            finds no candidates.
    """

    def __init__(
        self,
        min_gap_pct: float = 0.02,
        min_price: float = 10.0,
        max_price: float = 500.0,
        fallback_all_symbols: bool = True,
    ) -> None:
        self._min_gap_pct = min_gap_pct
        self._min_price = min_price
        self._max_price = max_price
        self._fallback_all_symbols = fallback_all_symbols

    def compute_watchlists(
        self,
        bar_data: dict[str, pd.DataFrame],
        trading_days: list[date],
    ) -> dict[date, DailyWatchlist]:
        """Pre-compute watchlists for all trading days.

        Args:
            bar_data: Dict of symbol -> DataFrame with columns
                [timestamp, open, high, low, close, volume].
                Timestamps should be timezone-aware or will be treated as UTC.
            trading_days: Ordered list of trading days to compute for.

        Returns:
            Dict of date -> DailyWatchlist.

        Algorithm:
        1. For each symbol, extract the last close of each trading day
           and the first open of the next trading day.
        2. Compute gap_pct = (next_open - prev_close) / prev_close.
        3. Filter by min_gap_pct, min_price, max_price.
        4. If no symbols pass, fall back to all symbols (if enabled).

        Note: The first trading day in the range has no "previous close"
        available (it's the start of our data). Use fallback for day 1.
        """
        if not trading_days:
            return {}

        watchlists: dict[date, DailyWatchlist] = {}
        all_symbols = sorted(bar_data.keys())

        # Build lookup: symbol -> {date -> (first_open, last_close)}
        daily_prices = self._extract_daily_prices(bar_data)

        # Day 1: fallback (no previous close available), but still apply price filters
        day1_symbols = []
        for symbol in all_symbols:
            symbol_prices = daily_prices.get(symbol, {})
            curr_prices = symbol_prices.get(trading_days[0])
            if curr_prices is None:
                continue
            curr_open = curr_prices["first_open"]
            if curr_open < self._min_price or curr_open > self._max_price:
                continue
            day1_symbols.append(symbol)

        watchlists[trading_days[0]] = DailyWatchlist(
            trading_date=trading_days[0],
            symbols=day1_symbols,
            mode="all_symbols",
            gap_data={},
        )
        logger.debug(
            "Day 1 (%s): Using %d symbols after price filter (no prior data for gap)",
            trading_days[0],
            len(day1_symbols),
        )

        # Remaining days: compute gaps from previous day
        for i in range(1, len(trading_days)):
            current_day = trading_days[i]
            prev_day = trading_days[i - 1]

            gap_data: dict[str, float] = {}
            passing_symbols: list[str] = []

            for symbol in all_symbols:
                symbol_prices = daily_prices.get(symbol, {})

                prev_prices = symbol_prices.get(prev_day)
                curr_prices = symbol_prices.get(current_day)

                if prev_prices is None or curr_prices is None:
                    continue

                prev_close = prev_prices["last_close"]
                curr_open = curr_prices["first_open"]

                if prev_close <= 0:
                    continue

                # Compute gap
                gap_pct = (curr_open - prev_close) / prev_close
                gap_data[symbol] = gap_pct

                # Apply filters
                if abs(gap_pct) < self._min_gap_pct:
                    continue
                if curr_open < self._min_price or curr_open > self._max_price:
                    continue

                passing_symbols.append(symbol)

            # Sort by gap descending (largest gaps first)
            passing_symbols.sort(key=lambda s: abs(gap_data.get(s, 0)), reverse=True)

            if passing_symbols:
                watchlists[current_day] = DailyWatchlist(
                    trading_date=current_day,
                    symbols=passing_symbols,
                    mode="gap_filter",
                    gap_data={s: gap_data[s] for s in passing_symbols},
                )
                logger.debug(
                    "%s: Gap filter selected %d symbols",
                    current_day,
                    len(passing_symbols),
                )
            elif self._fallback_all_symbols:
                # Apply price filters even in fallback mode
                fallback_symbols = []
                for symbol in all_symbols:
                    symbol_prices = daily_prices.get(symbol, {})
                    curr_prices = symbol_prices.get(current_day)
                    if curr_prices is None:
                        continue
                    curr_open = curr_prices["first_open"]
                    if curr_open < self._min_price or curr_open > self._max_price:
                        continue
                    fallback_symbols.append(symbol)

                watchlists[current_day] = DailyWatchlist(
                    trading_date=current_day,
                    symbols=fallback_symbols,
                    mode="all_symbols",
                    gap_data=gap_data,
                )
                logger.debug(
                    "%s: Gap filter found no symbols, using %d symbols after price filter",
                    current_day,
                    len(fallback_symbols),
                )
            else:
                watchlists[current_day] = DailyWatchlist(
                    trading_date=current_day,
                    symbols=[],
                    mode="gap_filter",
                    gap_data=gap_data,
                )
                logger.debug("%s: Gap filter found no symbols, empty watchlist", current_day)

        return watchlists

    def _extract_daily_prices(
        self,
        bar_data: dict[str, pd.DataFrame],
    ) -> dict[str, dict[date, dict[str, float]]]:
        """Extract first open and last close for each symbol per trading day.

        Returns:
            Dict of symbol -> {date -> {"first_open": float, "last_close": float}}
        """
        daily_prices: dict[str, dict[date, dict[str, float]]] = {}

        for symbol, df in bar_data.items():
            if df.empty:
                continue

            daily_prices[symbol] = {}

            # Ensure timestamp is datetime
            df = df.copy()
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Convert to ET for trading day extraction
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
            df["timestamp_et"] = df["timestamp"].dt.tz_convert(ET)
            df["trading_date"] = df["timestamp_et"].dt.date

            # Group by trading date
            for trading_date, group in df.groupby("trading_date"):
                if len(group) == 0:
                    continue

                # Sort by timestamp to get first and last
                group = group.sort_values("timestamp")
                first_open = float(group.iloc[0]["open"])
                last_close = float(group.iloc[-1]["close"])

                daily_prices[symbol][trading_date] = {
                    "first_open": first_open,
                    "last_close": last_close,
                }

        return daily_prices

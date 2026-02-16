"""Tests for the scanner simulator module."""

from datetime import UTC, date, datetime

import pandas as pd

from argus.backtest.scanner_simulator import DailyWatchlist, ScannerSimulator


def make_bar_data(
    symbol: str,
    days: list[tuple[date, list[tuple[float, float, float, float, int]]]],
) -> pd.DataFrame:
    """Create bar data for a symbol over multiple days.

    Args:
        symbol: Ticker symbol.
        days: List of (date, bars) where bars is a list of
            (open, high, low, close, volume) tuples.
            Each bar represents one minute starting at 9:30.

    Returns:
        DataFrame with timestamp, open, high, low, close, volume columns.
    """
    rows = []
    for trading_date, bars in days:
        for i, (o, h, low, c, v) in enumerate(bars):
            ts = datetime(
                trading_date.year,
                trading_date.month,
                trading_date.day,
                9,
                30 + i,
                0,
                tzinfo=UTC,
            )
            rows.append(
                {
                    "timestamp": ts,
                    "open": o,
                    "high": h,
                    "low": low,
                    "close": c,
                    "volume": v,
                }
            )
    return pd.DataFrame(rows)


class TestScannerSimulator:
    """Tests for ScannerSimulator class."""

    def test_gap_filter_selects_gapping_stocks(self) -> None:
        """Stocks with sufficient gap are selected."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        # Symbol A: prev_close=100, day_open=103 -> 3% gap -> selected
        # Symbol B: prev_close=100, day_open=100.50 -> 0.5% gap -> filtered out
        bar_data = {
            "A": make_bar_data(
                "A",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(103, 104, 102, 103, 1000)]),
                ],
            ),
            "B": make_bar_data(
                "B",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(100.50, 101, 100, 100.50, 1000)]),
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.02)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert "A" in watchlists[day2].symbols
        assert "B" not in watchlists[day2].symbols
        assert watchlists[day2].mode == "gap_filter"

    def test_price_filter_applied(self) -> None:
        """Symbols below min_price are filtered out."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        # Symbol C: gapping 5% but price=$5 (below min_price=10) -> filtered
        bar_data = {
            "C": make_bar_data(
                "C",
                [
                    (day1, [(5.0, 5.1, 4.9, 5.0, 1000)]),
                    (day2, [(5.25, 5.3, 5.2, 5.25, 1000)]),  # 5% gap
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.02, min_price=10.0)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert "C" not in watchlists[day2].symbols

    def test_first_day_uses_all_symbols(self) -> None:
        """First trading day uses all symbols (no previous close)."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        bar_data = {
            "A": make_bar_data("A", [(day1, [(100, 101, 99, 100, 1000)])]),
            "B": make_bar_data("B", [(day1, [(50, 51, 49, 50, 1000)])]),
        }

        scanner = ScannerSimulator(min_gap_pct=0.02)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert watchlists[day1].mode == "all_symbols"
        assert set(watchlists[day1].symbols) == {"A", "B"}

    def test_fallback_when_no_gaps(self) -> None:
        """Falls back to all symbols when no gaps pass the filter."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        # All symbols gap < 10%
        bar_data = {
            "A": make_bar_data(
                "A",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(101, 102, 100, 101, 1000)]),  # 1% gap
                ],
            ),
            "B": make_bar_data(
                "B",
                [
                    (day1, [(50, 51, 49, 50, 1000)]),
                    (day2, [(51, 52, 50, 51, 1000)]),  # 2% gap
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.10, fallback_all_symbols=True)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert watchlists[day2].mode == "all_symbols"
        assert set(watchlists[day2].symbols) == {"A", "B"}

    def test_no_fallback_returns_empty(self) -> None:
        """When fallback disabled, returns empty list if no gaps pass."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        bar_data = {
            "A": make_bar_data(
                "A",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(101, 102, 100, 101, 1000)]),  # 1% gap
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.10, fallback_all_symbols=False)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert watchlists[day2].symbols == []
        assert watchlists[day2].mode == "gap_filter"

    def test_gap_data_recorded(self) -> None:
        """Gap percentages are recorded in the watchlist."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        bar_data = {
            "A": make_bar_data(
                "A",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(103, 104, 102, 103, 1000)]),  # 3% gap
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.02)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert "A" in watchlists[day2].gap_data
        assert abs(watchlists[day2].gap_data["A"] - 0.03) < 0.001

    def test_symbols_sorted_by_gap_descending(self) -> None:
        """Symbols are sorted by gap size (descending)."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        bar_data = {
            "A": make_bar_data(
                "A",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(103, 104, 102, 103, 1000)]),  # 3% gap
                ],
            ),
            "B": make_bar_data(
                "B",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(105, 106, 104, 105, 1000)]),  # 5% gap
                ],
            ),
            "C": make_bar_data(
                "C",
                [
                    (day1, [(100, 101, 99, 100, 1000)]),
                    (day2, [(102, 103, 101, 102, 1000)]),  # 2% gap
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.02)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        # Should be sorted: B (5%), A (3%), C (2%)
        assert watchlists[day2].symbols == ["B", "A", "C"]

    def test_empty_trading_days_returns_empty(self) -> None:
        """Empty trading days list returns empty watchlists."""
        bar_data = {"A": make_bar_data("A", [])}
        scanner = ScannerSimulator()
        watchlists = scanner.compute_watchlists(bar_data, [])
        assert watchlists == {}

    def test_max_price_filter_applied(self) -> None:
        """Symbols above max_price are filtered out."""
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        trading_days = [day1, day2]

        bar_data = {
            "EXPENSIVE": make_bar_data(
                "EXPENSIVE",
                [
                    (day1, [(600, 610, 590, 600, 1000)]),
                    (day2, [(630, 640, 620, 630, 1000)]),  # 5% gap but price > 500
                ],
            ),
        }

        scanner = ScannerSimulator(min_gap_pct=0.02, max_price=500.0)
        watchlists = scanner.compute_watchlists(bar_data, trading_days)

        assert "EXPENSIVE" not in watchlists[day2].symbols


class TestDailyWatchlist:
    """Tests for DailyWatchlist dataclass."""

    def test_daily_watchlist_creation(self) -> None:
        """DailyWatchlist can be created with all fields."""
        watchlist = DailyWatchlist(
            trading_date=date(2025, 6, 16),
            symbols=["AAPL", "TSLA"],
            mode="gap_filter",
            gap_data={"AAPL": 0.03, "TSLA": 0.05},
        )

        assert watchlist.trading_date == date(2025, 6, 16)
        assert watchlist.symbols == ["AAPL", "TSLA"]
        assert watchlist.mode == "gap_filter"
        assert watchlist.gap_data == {"AAPL": 0.03, "TSLA": 0.05}

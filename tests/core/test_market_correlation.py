"""Tests for MarketCorrelationTracker (Sprint 27.6, Session 3)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from argus.core.config import CorrelationConfig
from argus.core.market_correlation import MarketCorrelationTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    lookback_days: int = 20,
    top_n_symbols: int = 50,
    dispersed_threshold: float = 0.30,
    concentrated_threshold: float = 0.60,
) -> CorrelationConfig:
    return CorrelationConfig(
        lookback_days=lookback_days,
        top_n_symbols=top_n_symbols,
        dispersed_threshold=dispersed_threshold,
        concentrated_threshold=concentrated_threshold,
    )


def _make_daily_bars(prices: list[float]) -> pd.DataFrame:
    """Create a minimal daily-bars DataFrame with a 'close' column."""
    return pd.DataFrame({"close": prices})


async def _fetch_bars_factory(
    bars_map: dict[str, pd.DataFrame | None],
) -> callable:
    """Return an async fetch function backed by a dict."""

    async def _fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
        return bars_map.get(symbol)

    return _fetch


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConstruction:
    """Test MarketCorrelationTracker construction."""

    def test_construction_with_config(self, tmp_path: Path) -> None:
        config = _make_config()
        tracker = MarketCorrelationTracker(config, cache_path=tmp_path / "cache.json")
        assert tracker._config is config
        assert tracker._average_correlation is None
        assert tracker._correlation_regime is None
        assert tracker._symbols_used == 0

    def test_default_cache_path(self) -> None:
        tracker = MarketCorrelationTracker(_make_config())
        assert tracker._cache_path == Path("data/correlation_cache.json")


class TestComputeKnownData:
    """Test compute with known correlation values."""

    @pytest.mark.asyncio
    async def test_compute_known_correlation(self, tmp_path: Path) -> None:
        """Two perfectly correlated series → avg correlation ~1.0."""
        config = _make_config(lookback_days=20)
        cache_path = tmp_path / "cache.json"
        tracker = MarketCorrelationTracker(config, cache_path=cache_path)

        # Two series with identical returns → correlation = 1.0
        prices = [100.0 + i * 1.0 for i in range(25)]
        bars_map = {
            "AAPL": _make_daily_bars(prices),
            "MSFT": _make_daily_bars(prices),
        }

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        def get_symbols() -> list[str]:
            return ["AAPL", "MSFT"]

        await tracker.compute(fetch, get_symbols)
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["average_correlation"] == pytest.approx(1.0, abs=0.01)
        assert snapshot["symbols_used"] == 2

    @pytest.mark.asyncio
    async def test_compute_dispersed_regime(self, tmp_path: Path) -> None:
        """Negatively correlated series → dispersed regime."""
        config = _make_config(lookback_days=20, dispersed_threshold=0.30)
        tracker = MarketCorrelationTracker(config, cache_path=tmp_path / "cache.json")

        np.random.seed(42)
        n = 25
        base = np.cumsum(np.random.randn(n)) + 100
        inverse = -np.cumsum(np.random.randn(n)) + 100

        bars_map = {
            "SYM_A": _make_daily_bars(base.tolist()),
            "SYM_B": _make_daily_bars(inverse.tolist()),
        }

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["SYM_A", "SYM_B"])
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["correlation_regime"] == "dispersed"
        assert snapshot["average_correlation"] < 0.30

    @pytest.mark.asyncio
    async def test_compute_concentrated_regime(self, tmp_path: Path) -> None:
        """Highly correlated series → concentrated regime."""
        config = _make_config(lookback_days=20, concentrated_threshold=0.60)
        tracker = MarketCorrelationTracker(config, cache_path=tmp_path / "cache.json")

        # Nearly identical prices with small noise
        np.random.seed(10)
        base = np.cumsum(np.random.randn(25)) + 100
        noisy = base + np.random.randn(25) * 0.01

        bars_map = {
            "X": _make_daily_bars(base.tolist()),
            "Y": _make_daily_bars(noisy.tolist()),
        }

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["X", "Y"])
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["correlation_regime"] == "concentrated"
        assert snapshot["average_correlation"] > 0.60

    @pytest.mark.asyncio
    async def test_compute_normal_regime(self, tmp_path: Path) -> None:
        """Moderately correlated series → normal regime."""
        config = _make_config(
            lookback_days=20, dispersed_threshold=0.20, concentrated_threshold=0.80
        )
        tracker = MarketCorrelationTracker(config, cache_path=tmp_path / "cache.json")

        np.random.seed(99)
        base = np.cumsum(np.random.randn(25)) + 100
        # Add moderate noise to get mid-range correlation
        moderate = base + np.cumsum(np.random.randn(25)) * 0.5

        bars_map = {
            "A": _make_daily_bars(base.tolist()),
            "B": _make_daily_bars(moderate.tolist()),
        }

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["A", "B"])
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["correlation_regime"] == "normal"
        assert 0.20 <= snapshot["average_correlation"] <= 0.80


class TestEdgeCases:
    """Test edge cases: single symbol, identical returns, insufficient history."""

    @pytest.mark.asyncio
    async def test_single_symbol_neutral_defaults(self, tmp_path: Path) -> None:
        """Single symbol → neutral defaults."""
        tracker = MarketCorrelationTracker(
            _make_config(), cache_path=tmp_path / "cache.json"
        )

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return _make_daily_bars([100 + i for i in range(25)])

        await tracker.compute(fetch, lambda: ["ONLY"])
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["average_correlation"] == 0.4
        assert snapshot["correlation_regime"] == "normal"
        assert snapshot["symbols_used"] == 1

    @pytest.mark.asyncio
    async def test_all_identical_returns_correlation_one(self, tmp_path: Path) -> None:
        """All symbols with identical returns → correlation 1.0."""
        tracker = MarketCorrelationTracker(
            _make_config(lookback_days=20), cache_path=tmp_path / "cache.json"
        )

        prices = [100.0 + i * 2.0 for i in range(25)]
        bars_map = {s: _make_daily_bars(prices) for s in ["A", "B", "C"]}

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["A", "B", "C"])
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["average_correlation"] == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_insufficient_history_excludes_symbol(self, tmp_path: Path) -> None:
        """Symbol with <lookback bars is excluded; if too few remain → neutral."""
        tracker = MarketCorrelationTracker(
            _make_config(lookback_days=20), cache_path=tmp_path / "cache.json"
        )

        good_prices = [100 + i for i in range(25)]
        short_prices = [100 + i for i in range(5)]  # Only 5 bars

        bars_map = {
            "GOOD": _make_daily_bars(good_prices),
            "SHORT": _make_daily_bars(short_prices),
        }

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["GOOD", "SHORT"])
        snapshot = tracker.get_correlation_snapshot()
        # Only 1 valid symbol → neutral
        assert snapshot["average_correlation"] == 0.4
        assert snapshot["correlation_regime"] == "normal"
        assert snapshot["symbols_used"] == 1

    @pytest.mark.asyncio
    async def test_all_fetches_return_none(self, tmp_path: Path) -> None:
        """All daily bar fetches return None → neutral defaults."""
        tracker = MarketCorrelationTracker(
            _make_config(), cache_path=tmp_path / "cache.json"
        )

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return None

        await tracker.compute(fetch, lambda: ["A", "B", "C"])
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["average_correlation"] == 0.4
        assert snapshot["correlation_regime"] == "normal"
        assert snapshot["symbols_used"] == 0


class TestFileCache:
    """Test JSON file cache read/write and invalidation."""

    @pytest.mark.asyncio
    async def test_cache_write_and_read(self, tmp_path: Path) -> None:
        """After compute, cache file contains expected schema."""
        cache_path = tmp_path / "cache.json"
        tracker = MarketCorrelationTracker(
            _make_config(lookback_days=20), cache_path=cache_path
        )

        prices = [100 + i for i in range(25)]
        bars_map = {"A": _make_daily_bars(prices), "B": _make_daily_bars(prices)}

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["A", "B"])

        assert cache_path.exists()
        data = json.loads(cache_path.read_text())
        assert "date" in data
        assert "symbols" in data
        assert "average_correlation" in data
        assert "correlation_regime" in data
        assert isinstance(data["symbols"], list)

    @pytest.mark.asyncio
    async def test_cache_same_day_hit_no_recompute(self, tmp_path: Path) -> None:
        """Same-day cache → no fetch calls, data loaded from cache."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        cache_path = tmp_path / "cache.json"
        today_et = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

        # Pre-seed cache
        cache_data = {
            "date": today_et,
            "symbols": ["X", "Y"],
            "average_correlation": 0.55,
            "correlation_regime": "normal",
        }
        cache_path.write_text(json.dumps(cache_data))

        tracker = MarketCorrelationTracker(_make_config(), cache_path=cache_path)

        fetch_called = False

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            nonlocal fetch_called
            fetch_called = True
            return None

        await tracker.compute(fetch, lambda: ["X", "Y"])

        assert not fetch_called, "fetch should not be called on cache hit"
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["average_correlation"] == 0.55
        assert snapshot["correlation_regime"] == "normal"
        assert snapshot["symbols_used"] == 2

    @pytest.mark.asyncio
    async def test_cache_stale_date_recomputes(self, tmp_path: Path) -> None:
        """Stale cache (yesterday's date) → recompute."""
        cache_path = tmp_path / "cache.json"

        # Write stale cache
        cache_data = {
            "date": "2020-01-01",
            "symbols": ["OLD"],
            "average_correlation": 0.99,
            "correlation_regime": "concentrated",
        }
        cache_path.write_text(json.dumps(cache_data))

        tracker = MarketCorrelationTracker(
            _make_config(lookback_days=20), cache_path=cache_path
        )

        prices = [100 + i for i in range(25)]
        bars_map = {"A": _make_daily_bars(prices), "B": _make_daily_bars(prices)}

        fetch_called = False

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            nonlocal fetch_called
            fetch_called = True
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["A", "B"])

        assert fetch_called, "fetch must be called when cache is stale"
        # New data, not the stale 0.99
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["symbols_used"] == 2


class TestSnapshot:
    """Test get_correlation_snapshot returns current state."""

    def test_snapshot_before_compute_returns_neutral(self) -> None:
        """Before compute, snapshot returns neutral defaults."""
        tracker = MarketCorrelationTracker(_make_config())
        snapshot = tracker.get_correlation_snapshot()
        assert snapshot["average_correlation"] == 0.4
        assert snapshot["correlation_regime"] == "normal"
        assert snapshot["symbols_used"] == 0

    @pytest.mark.asyncio
    async def test_snapshot_after_compute_reflects_computed_values(
        self, tmp_path: Path
    ) -> None:
        """After compute, snapshot reflects actual computed values."""
        tracker = MarketCorrelationTracker(
            _make_config(lookback_days=20), cache_path=tmp_path / "cache.json"
        )

        prices = [100 + i for i in range(25)]
        bars_map = {
            "A": _make_daily_bars(prices),
            "B": _make_daily_bars(prices),
            "C": _make_daily_bars(prices),
        }

        async def fetch(symbol: str, lookback_days: int) -> pd.DataFrame | None:
            return bars_map.get(symbol)

        await tracker.compute(fetch, lambda: ["A", "B", "C"])
        snapshot = tracker.get_correlation_snapshot()

        assert snapshot["average_correlation"] == pytest.approx(1.0, abs=0.01)
        assert snapshot["symbols_used"] == 3
        assert snapshot["correlation_regime"] == "concentrated"

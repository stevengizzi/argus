"""Tests for HistoricalDataFeed (Sprint 27, Session 2).

All Databento API interactions are mocked — no live API calls.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from argus.backtest.historical_data_feed import (
    HistoricalDataFeed,
    HistoricalDataFeedError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    """Provide a temporary cache directory."""
    return tmp_path / "databento_cache"


@pytest.fixture()
def feed(cache_dir: Path) -> HistoricalDataFeed:
    """HistoricalDataFeed with cost validation enabled."""
    return HistoricalDataFeed(cache_dir=cache_dir, verify_zero_cost=True)


@pytest.fixture()
def feed_no_cost_check(cache_dir: Path) -> HistoricalDataFeed:
    """HistoricalDataFeed with cost validation disabled."""
    return HistoricalDataFeed(cache_dir=cache_dir, verify_zero_cost=False)


def _make_sample_df(n_bars: int = 5) -> pd.DataFrame:
    """Create a sample normalized DataFrame matching ARGUS schema."""
    timestamps = pd.date_range(
        "2025-06-02 13:30:00", periods=n_bars, freq="min", tz="UTC"
    )
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": [100.0 + i for i in range(n_bars)],
        "high": [101.0 + i for i in range(n_bars)],
        "low": [99.0 + i for i in range(n_bars)],
        "close": [100.5 + i for i in range(n_bars)],
        "volume": [1000 * (i + 1) for i in range(n_bars)],
    })


def _make_raw_databento_df(n_bars: int = 5) -> pd.DataFrame:
    """Create a DataFrame mimicking Databento's to_df() output (ts_event as index)."""
    timestamps = pd.date_range(
        "2025-06-02 13:30:00", periods=n_bars, freq="min", tz="UTC"
    )
    df = pd.DataFrame({
        "open": [100.0 + i for i in range(n_bars)],
        "high": [101.0 + i for i in range(n_bars)],
        "low": [99.0 + i for i in range(n_bars)],
        "close": [100.5 + i for i in range(n_bars)],
        "volume": [1000 * (i + 1) for i in range(n_bars)],
        "rtype": [0] * n_bars,
        "publisher_id": [1] * n_bars,
        "instrument_id": [12345] * n_bars,
        "symbol": ["AAPL"] * n_bars,
    }, index=pd.Index(timestamps, name="ts_event"))
    return df


def _mock_databento_client(
    cost: float = 0.0,
    raw_df: pd.DataFrame | None = None,
) -> MagicMock:
    """Build a mock Databento Historical client."""
    client = MagicMock()
    client.metadata.get_cost.return_value = cost

    data_result = MagicMock()
    data_result.to_df.return_value = raw_df if raw_df is not None else _make_raw_databento_df()
    client.timeseries.get_range.return_value = data_result

    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDownloadCachesParquet:
    """test_download_caches_parquet — mocked client, verify Parquet file created."""

    @pytest.mark.asyncio()
    async def test_download_caches_parquet(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        mock_client = _mock_databento_client()
        feed._client = mock_client

        result = await feed.download(
            symbols=["AAPL"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        # Parquet file created
        parquet_path = cache_dir / "AAPL" / "2025-06.parquet"
        assert parquet_path.exists()

        # Result maps symbol to its directory
        assert result["AAPL"] == cache_dir / "AAPL"

        # File is readable and has expected columns
        df = pd.read_parquet(parquet_path)
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(df) == 5


class TestCacheHitSkipsDownload:
    """test_cache_hit_skips_download — pre-existing Parquet, verify no API call."""

    @pytest.mark.asyncio()
    async def test_cache_hit_skips_download(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        # Pre-populate cache
        symbol_dir = cache_dir / "AAPL"
        symbol_dir.mkdir(parents=True)
        sample = _make_sample_df()
        sample.to_parquet(symbol_dir / "2025-06.parquet", index=False)

        mock_client = _mock_databento_client()
        feed._client = mock_client

        await feed.download(
            symbols=["AAPL"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        # No API calls made
        mock_client.metadata.get_cost.assert_not_called()
        mock_client.timeseries.get_range.assert_not_called()


class TestIncrementalDownload:
    """test_incremental_download — 3 months requested, 1 cached, verify 2 downloaded."""

    @pytest.mark.asyncio()
    async def test_incremental_download(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        # Pre-populate June cache
        symbol_dir = cache_dir / "AAPL"
        symbol_dir.mkdir(parents=True)
        _make_sample_df().to_parquet(symbol_dir / "2025-06.parquet", index=False)

        mock_client = _mock_databento_client()
        feed._client = mock_client

        await feed.download(
            symbols=["AAPL"],
            start_date=date(2025, 5, 1),
            end_date=date(2025, 7, 31),
        )

        # Should download May and July, skip June
        assert mock_client.timeseries.get_range.call_count == 2
        assert mock_client.metadata.get_cost.call_count == 2


class TestCostValidationZeroPasses:
    """test_cost_validation_zero_passes — get_cost returns 0.0, download proceeds."""

    @pytest.mark.asyncio()
    async def test_cost_validation_zero_passes(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        mock_client = _mock_databento_client(cost=0.0)
        feed._client = mock_client

        await feed.download(
            symbols=["AAPL"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        # Cost check called, then download proceeded
        mock_client.metadata.get_cost.assert_called_once()
        mock_client.timeseries.get_range.assert_called_once()

        # Parquet written
        assert (cache_dir / "AAPL" / "2025-06.parquet").exists()


class TestCostValidationNonzeroRaises:
    """test_cost_validation_nonzero_raises — get_cost returns 5.0, error raised."""

    @pytest.mark.asyncio()
    async def test_cost_validation_nonzero_raises(
        self, feed: HistoricalDataFeed,
    ) -> None:
        mock_client = _mock_databento_client(cost=5.0)
        feed._client = mock_client

        with pytest.raises(HistoricalDataFeedError, match="Cost validation failed"):
            await feed.download(
                symbols=["AAPL"],
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 30),
            )

        # No download attempted
        mock_client.timeseries.get_range.assert_not_called()


class TestCostValidationExceptionRaises:
    """test_cost_validation_exception_raises — get_cost raises network error (AR-3)."""

    @pytest.mark.asyncio()
    async def test_cost_validation_exception_raises(
        self, feed: HistoricalDataFeed,
    ) -> None:
        mock_client = MagicMock()
        mock_client.metadata.get_cost.side_effect = ConnectionError("network timeout")
        feed._client = mock_client

        with pytest.raises(HistoricalDataFeedError, match="Cost validation failed"):
            await feed.download(
                symbols=["AAPL"],
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 30),
            )

        # No download attempted
        mock_client.timeseries.get_range.assert_not_called()


class TestVerifyZeroCostFalseSkipsCheck:
    """test_verify_zero_cost_false_skips_check — no get_cost call at all."""

    @pytest.mark.asyncio()
    async def test_verify_zero_cost_false_skips_check(
        self, feed_no_cost_check: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        mock_client = _mock_databento_client()
        feed_no_cost_check._client = mock_client

        await feed_no_cost_check.download(
            symbols=["AAPL"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        # Cost check NOT called
        mock_client.metadata.get_cost.assert_not_called()

        # But download still proceeded
        mock_client.timeseries.get_range.assert_called_once()
        assert (cache_dir / "AAPL" / "2025-06.parquet").exists()


class TestLoadReturnsNormalizedDataframe:
    """test_load_returns_normalized_dataframe — correct columns, UTC, trading_date."""

    @pytest.mark.asyncio()
    async def test_load_returns_normalized_dataframe(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        # Pre-populate cache with sample data
        symbol_dir = cache_dir / "AAPL"
        symbol_dir.mkdir(parents=True)
        _make_sample_df().to_parquet(symbol_dir / "2025-06.parquet", index=False)

        result = await feed.load(
            symbols=["AAPL"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        df = result["AAPL"]
        assert not df.empty

        # Check columns
        expected_cols = ["timestamp", "open", "high", "low", "close", "volume", "trading_date"]
        assert list(df.columns) == expected_cols

        # Check UTC-aware timestamps
        assert str(df["timestamp"].dt.tz) == "UTC"

        # Check trading_date is a date
        assert all(isinstance(d, date) for d in df["trading_date"])


class TestLoadFiltersDateRange:
    """test_load_filters_date_range — data outside range excluded."""

    @pytest.mark.asyncio()
    async def test_load_filters_date_range(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        # Create data spanning June 2 and June 3
        timestamps = pd.date_range(
            "2025-06-02 13:30:00", periods=3, freq="min", tz="UTC"
        ).tolist() + pd.date_range(
            "2025-06-03 13:30:00", periods=3, freq="min", tz="UTC"
        ).tolist()

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": [100.0] * 6,
            "high": [101.0] * 6,
            "low": [99.0] * 6,
            "close": [100.5] * 6,
            "volume": [1000] * 6,
        })

        symbol_dir = cache_dir / "AAPL"
        symbol_dir.mkdir(parents=True)
        df.to_parquet(symbol_dir / "2025-06.parquet", index=False)

        # Load only June 2
        result = await feed.load(
            symbols=["AAPL"],
            start_date=date(2025, 6, 2),
            end_date=date(2025, 6, 2),
        )

        loaded = result["AAPL"]
        assert len(loaded) == 3
        assert all(d == date(2025, 6, 2) for d in loaded["trading_date"])


class TestLoadEmptySymbol:
    """test_load_empty_symbol — symbol with no data returns empty DataFrame."""

    @pytest.mark.asyncio()
    async def test_load_empty_symbol(
        self, feed: HistoricalDataFeed,
    ) -> None:
        result = await feed.load(
            symbols=["NOPE"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        df = result["NOPE"]
        assert df.empty
        expected_cols = ["timestamp", "open", "high", "low", "close", "volume", "trading_date"]
        assert list(df.columns) == expected_cols


class TestSymbolNotFoundSkips:
    """test_symbol_not_found_skips — Databento returns empty, other symbols continue."""

    @pytest.mark.asyncio()
    async def test_symbol_not_found_skips(
        self, feed: HistoricalDataFeed, cache_dir: Path
    ) -> None:
        empty_df = pd.DataFrame(columns=[
            "open", "high", "low", "close", "volume",
            "rtype", "publisher_id", "instrument_id", "symbol",
        ])
        empty_df.index.name = "ts_event"

        # First call returns empty (NOPE), second returns data (AAPL)
        mock_client = MagicMock()
        mock_client.metadata.get_cost.return_value = 0.0

        empty_result = MagicMock()
        empty_result.to_df.return_value = empty_df

        good_result = MagicMock()
        good_result.to_df.return_value = _make_raw_databento_df()

        mock_client.timeseries.get_range.side_effect = [empty_result, good_result]
        feed._client = mock_client

        result = await feed.download(
            symbols=["NOPE", "AAPL"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        # NOPE gets an empty cache file (prevents re-download)
        nope_path = cache_dir / "NOPE" / "2025-06.parquet"
        assert nope_path.exists()
        nope_df = pd.read_parquet(nope_path)
        assert nope_df.empty

        # AAPL gets real data
        aapl_path = cache_dir / "AAPL" / "2025-06.parquet"
        assert aapl_path.exists()
        aapl_df = pd.read_parquet(aapl_path)
        assert len(aapl_df) == 5

        # Both symbols in result
        assert "NOPE" in result
        assert "AAPL" in result


class TestMonthRangeGeneration:
    """test_month_range_generation — _month_range produces correct tuples."""

    def test_single_month(self, feed: HistoricalDataFeed) -> None:
        result = feed._month_range(date(2025, 6, 1), date(2025, 6, 30))
        assert result == [(2025, 6)]

    def test_multi_month(self, feed: HistoricalDataFeed) -> None:
        result = feed._month_range(date(2025, 6, 15), date(2025, 8, 10))
        assert result == [(2025, 6), (2025, 7), (2025, 8)]

    def test_cross_year(self, feed: HistoricalDataFeed) -> None:
        result = feed._month_range(date(2025, 11, 1), date(2026, 2, 28))
        assert result == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]

    def test_same_day(self, feed: HistoricalDataFeed) -> None:
        result = feed._month_range(date(2025, 6, 15), date(2025, 6, 15))
        assert result == [(2025, 6)]

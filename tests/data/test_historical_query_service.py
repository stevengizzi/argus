"""Tests for HistoricalQueryService (DuckDB Parquet layer).

Creates minimal Parquet test fixtures in temp directories using pandas/pyarrow.
No production cache files are used.

Sprint 31A.5, Session 1.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from argus.data.historical_query_config import HistoricalQueryConfig
from argus.data.historical_query_service import (
    HistoricalQueryService,
    QueryExecutionError,
    ServiceUnavailableError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_parquet(path: Path, num_bars: int = 100) -> None:
    """Write a minimal OHLCV Parquet file matching the Databento schema.

    Args:
        path: Full file path to write.
        num_bars: Number of 1-minute bars to generate.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2025-01-02 14:30:00", periods=num_bars, freq="1min", tz="UTC"
            ),
            "open": [100.0 + i * 0.01 for i in range(num_bars)],
            "high": [101.0 + i * 0.01 for i in range(num_bars)],
            "low": [99.0 + i * 0.01 for i in range(num_bars)],
            "close": [100.5 + i * 0.01 for i in range(num_bars)],
            "volume": [1000 + i for i in range(num_bars)],
        }
    )
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path))


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create a temp cache directory with Parquet files for 3 symbols."""
    _make_parquet(tmp_path / "AAPL" / "2025-01.parquet", num_bars=100)
    _make_parquet(tmp_path / "NVDA" / "2025-01.parquet", num_bars=80)
    _make_parquet(tmp_path / "TSLA" / "2025-01.parquet", num_bars=60)
    return tmp_path


@pytest.fixture
def enabled_config(cache_dir: Path) -> HistoricalQueryConfig:
    """HistoricalQueryConfig pointing at the temp cache dir."""
    return HistoricalQueryConfig(
        enabled=True,
        cache_dir=str(cache_dir),
        max_memory_mb=256,
        default_threads=1,
    )


@pytest.fixture
def service(enabled_config: HistoricalQueryConfig) -> HistoricalQueryService:
    """Initialized HistoricalQueryService with test data."""
    svc = HistoricalQueryService(enabled_config)
    assert svc.is_available, "Service should be available with valid test cache"
    return svc


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestServiceInitialization:
    def test_init_with_valid_cache_is_available(
        self, enabled_config: HistoricalQueryConfig
    ) -> None:
        svc = HistoricalQueryService(enabled_config)
        assert svc.is_available is True

    def test_init_with_disabled_config_is_not_available(self, tmp_path: Path) -> None:
        config = HistoricalQueryConfig(enabled=False, cache_dir=str(tmp_path))
        svc = HistoricalQueryService(config)
        assert svc.is_available is False

    def test_init_with_missing_cache_dir_is_not_available(self, tmp_path: Path) -> None:
        config = HistoricalQueryConfig(
            enabled=True,
            cache_dir=str(tmp_path / "nonexistent"),
        )
        svc = HistoricalQueryService(config)
        assert svc.is_available is False

    def test_init_with_empty_cache_dir_is_not_available(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_cache"
        empty.mkdir()
        config = HistoricalQueryConfig(enabled=True, cache_dir=str(empty))
        svc = HistoricalQueryService(config)
        assert svc.is_available is False


# ---------------------------------------------------------------------------
# query() tests
# ---------------------------------------------------------------------------


class TestQuery:
    def test_query_returns_dataframe_for_valid_sql(
        self, service: HistoricalQueryService
    ) -> None:
        df = service.query("SELECT COUNT(*) AS cnt FROM historical")
        assert not df.empty
        assert "cnt" in df.columns
        assert int(df.iloc[0]["cnt"]) > 0

    def test_query_raises_service_unavailable_when_not_available(
        self, tmp_path: Path
    ) -> None:
        config = HistoricalQueryConfig(enabled=False, cache_dir=str(tmp_path))
        svc = HistoricalQueryService(config)
        with pytest.raises(ServiceUnavailableError):
            svc.query("SELECT 1")

    def test_query_raises_query_execution_error_for_invalid_sql(
        self, service: HistoricalQueryService
    ) -> None:
        with pytest.raises(QueryExecutionError):
            service.query("SELECT * FROM nonexistent_table_xyz_abc")


# ---------------------------------------------------------------------------
# get_symbol_bars() tests
# ---------------------------------------------------------------------------


class TestGetSymbolBars:
    def test_returns_filtered_bars_for_known_symbol(
        self, service: HistoricalQueryService
    ) -> None:
        df = service.get_symbol_bars("AAPL", "2025-01-01", "2025-01-31")
        assert not df.empty
        assert (df["symbol"] == "AAPL").all()

    def test_returns_empty_dataframe_for_unknown_symbol(
        self, service: HistoricalQueryService
    ) -> None:
        df = service.get_symbol_bars("UNKN", "2025-01-01", "2025-01-31")
        assert df.empty

    def test_bars_ordered_by_ts_event(self, service: HistoricalQueryService) -> None:
        df = service.get_symbol_bars("NVDA", "2025-01-01", "2025-01-31")
        if len(df) > 1:
            ts = df["ts_event"].tolist()
            assert ts == sorted(ts)


# ---------------------------------------------------------------------------
# get_available_symbols() tests
# ---------------------------------------------------------------------------


class TestGetAvailableSymbols:
    def test_returns_sorted_list_of_symbols(
        self, service: HistoricalQueryService
    ) -> None:
        symbols = service.get_available_symbols()
        assert symbols == sorted(symbols)
        assert set(symbols) == {"AAPL", "NVDA", "TSLA"}

    def test_returns_cached_result_on_second_call(
        self, service: HistoricalQueryService
    ) -> None:
        result1 = service.get_available_symbols()
        result2 = service.get_available_symbols()
        assert result1 == result2


# ---------------------------------------------------------------------------
# get_date_coverage() tests
# ---------------------------------------------------------------------------


class TestGetDateCoverage:
    def test_per_symbol_coverage_returns_expected_keys(
        self, service: HistoricalQueryService
    ) -> None:
        result = service.get_date_coverage(symbol="AAPL")
        assert "min_date" in result
        assert "max_date" in result
        assert "bar_count" in result
        assert result["bar_count"] == 100

    def test_aggregate_coverage_returns_symbol_count(
        self, service: HistoricalQueryService
    ) -> None:
        result = service.get_date_coverage()
        assert "symbol_count" in result
        assert result["symbol_count"] == 3
        assert "bar_count" in result
        assert result["bar_count"] == 240  # 100 + 80 + 60

    def test_min_date_is_before_max_date(self, service: HistoricalQueryService) -> None:
        result = service.get_date_coverage(symbol="TSLA")
        assert result["min_date"] is not None
        assert result["max_date"] is not None
        assert result["min_date"] <= result["max_date"]


# ---------------------------------------------------------------------------
# validate_symbol_coverage() tests
# ---------------------------------------------------------------------------


class TestValidateSymbolCoverage:
    def test_returns_true_for_symbol_above_threshold(
        self, service: HistoricalQueryService
    ) -> None:
        results = service.validate_symbol_coverage(
            symbols=["AAPL"],
            start_date="2025-01-01",
            end_date="2025-01-31",
            min_bars=50,
        )
        assert results["AAPL"] is True

    def test_returns_false_for_symbol_below_threshold(
        self, service: HistoricalQueryService
    ) -> None:
        results = service.validate_symbol_coverage(
            symbols=["TSLA"],
            start_date="2025-01-01",
            end_date="2025-01-31",
            min_bars=200,  # higher than the 60 bars available
        )
        assert results["TSLA"] is False

    def test_handles_multiple_symbols(self, service: HistoricalQueryService) -> None:
        results = service.validate_symbol_coverage(
            symbols=["AAPL", "NVDA", "TSLA"],
            start_date="2025-01-01",
            end_date="2025-01-31",
            min_bars=10,
        )
        assert results == {"AAPL": True, "NVDA": True, "TSLA": True}

    def test_returns_false_for_symbol_not_in_cache(
        self, service: HistoricalQueryService
    ) -> None:
        results = service.validate_symbol_coverage(
            symbols=["UNKN"],
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        assert results["UNKN"] is False

    def test_empty_symbols_list_returns_empty_dict(
        self, service: HistoricalQueryService
    ) -> None:
        results = service.validate_symbol_coverage(
            symbols=[], start_date="2025-01-01", end_date="2025-01-31"
        )
        assert results == {}


# ---------------------------------------------------------------------------
# get_cache_health() tests
# ---------------------------------------------------------------------------


class TestGetCacheHealth:
    def test_returns_expected_keys(self, service: HistoricalQueryService) -> None:
        health = service.get_cache_health()
        assert "total_symbols" in health
        assert "date_range" in health
        assert "total_bars" in health
        assert "cache_dir" in health
        assert "cache_size_bytes" in health

    def test_total_symbols_correct(self, service: HistoricalQueryService) -> None:
        health = service.get_cache_health()
        assert health["total_symbols"] == 3

    def test_cache_size_bytes_positive(self, service: HistoricalQueryService) -> None:
        health = service.get_cache_health()
        assert health["cache_size_bytes"] > 0


# ---------------------------------------------------------------------------
# close() tests
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_is_idempotent(self, enabled_config: HistoricalQueryConfig) -> None:
        svc = HistoricalQueryService(enabled_config)
        svc.close()
        svc.close()  # second call must not raise

    def test_close_makes_service_unavailable(
        self, enabled_config: HistoricalQueryConfig
    ) -> None:
        svc = HistoricalQueryService(enabled_config)
        assert svc.is_available is True
        svc.close()
        assert svc.is_available is False

    def test_query_after_close_raises_service_unavailable(
        self, enabled_config: HistoricalQueryConfig
    ) -> None:
        svc = HistoricalQueryService(enabled_config)
        svc.close()
        with pytest.raises(ServiceUnavailableError):
            svc.query("SELECT 1")

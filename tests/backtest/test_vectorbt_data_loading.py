"""Tests for VectorBT load_symbol_data dual naming convention support.

Sprint 21.6.1 Session 1: Verifies that load_symbol_data() accepts both
legacy ({SYMBOL}_{YYYY-MM}.parquet) and current ({YYYY-MM}.parquet) naming.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from argus.backtest.vectorbt_orb import load_symbol_data

ET = ZoneInfo("America/New_York")


def _write_sample_parquet(path: Path) -> None:
    """Write a minimal 1-minute OHLCV Parquet file."""
    timestamps = pd.date_range(
        "2024-01-02 09:30",
        periods=5,
        freq="1min",
        tz=ET,
    )
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.5] * 5,
            "volume": [1000] * 5,
        }
    )
    df.to_parquet(path)


def test_load_symbol_data_legacy_naming(tmp_path: Path) -> None:
    """Legacy {SYMBOL}_{YYYY-MM}.parquet files are loaded correctly."""
    symbol_dir = tmp_path / "AAPL"
    symbol_dir.mkdir()
    _write_sample_parquet(symbol_dir / "AAPL_2024-01.parquet")

    df = load_symbol_data(tmp_path, "AAPL", date(2024, 1, 1), date(2024, 1, 31))
    assert not df.empty
    assert len(df) == 5


def test_load_symbol_data_databento_naming(tmp_path: Path) -> None:
    """Current {YYYY-MM}.parquet files (HistoricalDataFeed) are loaded correctly."""
    symbol_dir = tmp_path / "AAPL"
    symbol_dir.mkdir()
    _write_sample_parquet(symbol_dir / "2024-01.parquet")

    df = load_symbol_data(tmp_path, "AAPL", date(2024, 1, 1), date(2024, 1, 31))
    assert not df.empty
    assert len(df) == 5

"""Tests for backtesting configuration models."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.backtest.config import DataFetcherConfig


class TestDataFetcherConfig:
    """Tests for DataFetcherConfig Pydantic model."""

    def test_defaults_are_valid(self) -> None:
        """DataFetcherConfig can be created with all defaults."""
        config = DataFetcherConfig()
        assert config.data_dir == Path("data/historical/1m")
        assert config.max_requests_per_minute == 150
        assert config.adjustment == "split"
        assert config.feed == "iex"

    def test_max_requests_per_minute_capped(self) -> None:
        """Rate limit cannot exceed 200 (Alpaca free tier limit)."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(max_requests_per_minute=201)

    def test_max_requests_per_minute_minimum(self) -> None:
        """Rate limit must be at least 1."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(max_requests_per_minute=0)

    def test_invalid_adjustment_rejected(self) -> None:
        """Only raw, split, all are valid adjustment values."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(adjustment="invalid")

    def test_invalid_feed_rejected(self) -> None:
        """Only iex, sip are valid feed values."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(feed="invalid")

    def test_valid_adjustment_values(self) -> None:
        """All valid adjustment values are accepted."""
        for adj in ["raw", "split", "all"]:
            config = DataFetcherConfig(adjustment=adj)
            assert config.adjustment == adj

    def test_valid_feed_values(self) -> None:
        """All valid feed values are accepted."""
        for feed in ["iex", "sip"]:
            config = DataFetcherConfig(feed=feed)
            assert config.feed == feed

    def test_retry_max_attempts_minimum(self) -> None:
        """Retry attempts must be at least 1."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(retry_max_attempts=0)

    def test_retry_base_delay_positive(self) -> None:
        """Retry delay must be positive."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(retry_base_delay_seconds=0)


class TestBacktestUniverse:
    """Tests for the backtest universe config file."""

    def test_universe_file_exists(self) -> None:
        """backtest_universe.yaml exists in config/."""
        assert Path("config/backtest_universe.yaml").exists()

    def test_universe_loads_and_has_symbols(self) -> None:
        """Universe file loads and contains a non-empty list of symbols."""
        with open("config/backtest_universe.yaml") as f:
            data = yaml.safe_load(f)
        assert "symbols" in data
        assert len(data["symbols"]) >= 20
        assert "SPY" in data["symbols"]

    def test_universe_symbols_are_uppercase_strings(self) -> None:
        """All symbols are uppercase strings with no whitespace."""
        with open("config/backtest_universe.yaml") as f:
            data = yaml.safe_load(f)
        for sym in data["symbols"]:
            assert isinstance(sym, str)
            assert sym == sym.strip().upper()

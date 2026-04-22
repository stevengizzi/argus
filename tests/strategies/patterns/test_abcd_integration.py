"""Integration tests for ABCD harmonic pattern config, wiring, and strategy wrapper.

Sprint 29, Session 6b.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml

from argus.core.config import ABCDConfig, ExitManagementConfig, deep_update, load_abcd_config
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.abcd import ABCDPattern
from argus.strategies.patterns.base import CandleBar, PatternDetection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# 14:00 UTC = 10:00 ET (EDT, UTC-4) — within ABCD operating window
BASE_TIME = datetime(2026, 3, 31, 14, 0, 0, tzinfo=UTC)


def _bar(
    close: float,
    volume: float = 1000.0,
    offset_minutes: int = 0,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
) -> CandleBar:
    """Build a CandleBar with sensible defaults."""
    o = open_ if open_ is not None else close
    h = high if high is not None else close + 0.10
    lo = low if low is not None else close - 0.10
    return CandleBar(
        timestamp=BASE_TIME + timedelta(minutes=offset_minutes),
        open=o,
        high=h,
        low=lo,
        close=close,
        volume=volume,
    )


def _make_candle_event(
    symbol: str,
    close: float,
    offset_minutes: int = 0,
    volume: float = 1000.0,
) -> object:
    """Build a CandleEvent for the strategy wrapper."""
    from argus.core.events import CandleEvent

    ts = BASE_TIME + timedelta(minutes=offset_minutes)
    return CandleEvent(
        symbol=symbol,
        timestamp=ts,
        open=close,
        high=close + 0.10,
        low=close - 0.10,
        close=close,
        volume=int(volume),
    )


def _make_abcd_config(**overrides: object) -> ABCDConfig:
    """Build a minimal ABCDConfig for testing."""
    defaults: dict[str, object] = {
        "strategy_id": "strat_abcd",
        "name": "ABCD",
        "operating_window": {
            "earliest_entry": "10:00",
            "latest_entry": "15:00",
            "force_close": "15:50",
        },
        "pattern_class": "ABCDPattern",
    }
    defaults.update(overrides)
    return ABCDConfig(**defaults)


# ---------------------------------------------------------------------------
# Test 1: ABCD config YAML parses without error
# ---------------------------------------------------------------------------


class TestABCDConfigYAML:
    """Test config YAML parsing and validation."""

    def test_abcd_yaml_parses(self) -> None:
        """abcd.yaml should parse into ABCDConfig without error."""
        yaml_path = Path("config/strategies/abcd.yaml")
        assert yaml_path.exists(), f"Config file not found: {yaml_path}"

        config = load_abcd_config(yaml_path)
        assert config.strategy_id == "strat_abcd"
        assert config.pattern_class == "ABCDPattern"
        assert config.operating_window.earliest_entry == "10:00"
        assert config.operating_window.latest_entry == "15:00"
        assert config.target_1_r == 1.0
        assert config.target_2_r == 2.0
        assert config.time_stop_minutes == 60

    def test_abcd_allowed_regimes(self) -> None:
        """Allowed regimes populated from YAML."""
        yaml_path = Path("config/strategies/abcd.yaml")
        config = load_abcd_config(yaml_path)
        expected = {"bullish_trending", "bearish_trending", "range_bound", "high_volatility"}
        assert set(config.allowed_regimes) == expected


# ---------------------------------------------------------------------------
# Test 2: Universe filter routes symbols correctly
# ---------------------------------------------------------------------------


class TestABCDUniverseFilter:
    """Test universe filter YAML and config validation."""

    def test_universe_filter_yaml_parses(self) -> None:
        """Universe filter YAML parses with correct values."""
        filter_path = Path("config/universe_filters/abcd.yaml")
        assert filter_path.exists(), f"Missing: {filter_path}"

        with open(filter_path) as f:
            data = yaml.safe_load(f)

        assert data["min_price"] == 10.0
        assert data["max_price"] == 300.0
        assert data["min_avg_volume"] == 500000

    def test_universe_filter_in_strategy_yaml(self) -> None:
        """Strategy YAML contains universe_filter with correct values."""
        yaml_path = Path("config/strategies/abcd.yaml")
        config = load_abcd_config(yaml_path)
        assert config.universe_filter is not None
        assert config.universe_filter.min_price == 10.0
        assert config.universe_filter.max_price == 300.0
        assert config.universe_filter.min_avg_volume == 500000


# ---------------------------------------------------------------------------
# Test 3: Exit override merges correctly via deep_update
# ---------------------------------------------------------------------------


class TestABCDExitOverride:
    """Test exit management override structure and merging."""

    def test_exit_override_in_strategy_yaml(self) -> None:
        """Strategy YAML contains exit_management override."""
        yaml_path = Path("config/strategies/abcd.yaml")
        assert yaml_path.exists()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert "exit_management" in data
        exit_cfg = data["exit_management"]
        assert exit_cfg["trailing_stop"]["enabled"] is True
        assert exit_cfg["trailing_stop"]["type"] == "atr"
        assert exit_cfg["trailing_stop"]["atr_multiplier"] == 2.5
        assert exit_cfg["escalation"]["enabled"] is True
        assert len(exit_cfg["escalation"]["phases"]) == 2

    def test_exit_override_applies_via_deep_update(self) -> None:
        """Exit override merges with global defaults via deep_update."""
        global_path = Path("config/exit_management.yaml")
        with open(global_path) as f:
            global_data = yaml.safe_load(f)

        strat_path = Path("config/strategies/abcd.yaml")
        with open(strat_path) as f:
            strat_data = yaml.safe_load(f)

        override = strat_data["exit_management"]
        merged = deep_update(global_data, override)
        cfg = ExitManagementConfig(**merged)
        assert cfg.trailing_stop.atr_multiplier == 2.5  # overridden
        assert cfg.escalation.enabled is True  # overridden
        assert len(cfg.escalation.phases) == 2


# ---------------------------------------------------------------------------
# Test 4: ABCD loads at startup via orchestrator
# ---------------------------------------------------------------------------


class TestABCDStrategyRegistration:
    """Test strategy instantiation and registration."""

    def test_abcd_pattern_wraps_in_pattern_based_strategy(self) -> None:
        """ABCDPattern can be wrapped in PatternBasedStrategy."""
        config = _make_abcd_config()
        pattern = ABCDPattern()
        strategy = PatternBasedStrategy(
            pattern=pattern,
            config=config,
        )
        assert strategy.strategy_id == "strat_abcd"
        assert strategy._pattern.name == "abcd"
        assert strategy._pattern.lookback_bars == 60

    def test_abcd_import_from_patterns_package(self) -> None:
        """ABCDPattern importable from argus.strategies.patterns."""
        from argus.strategies.patterns import ABCDPattern as ImportedABCD

        pattern = ImportedABCD()
        assert pattern.name == "abcd"


# ---------------------------------------------------------------------------
# Test 5: ABCD receives candles through PatternBasedStrategy
# ---------------------------------------------------------------------------


class TestABCDCandleRouting:
    """Test that ABCD pattern receives candles through the wrapper."""

    @pytest.mark.asyncio
    async def test_candle_accumulates_in_window(self) -> None:
        """Candle events accumulate in per-symbol window."""
        config = _make_abcd_config()
        pattern = ABCDPattern()
        strategy = PatternBasedStrategy(
            pattern=pattern,
            config=config,
        )
        strategy.set_watchlist(["AAPL"])

        # Send 5 candles — should accumulate
        for i in range(5):
            event = _make_candle_event("AAPL", 150.0 + i * 0.5, offset_minutes=i)
            await strategy.on_candle(event)

        window = strategy._candle_windows.get("AAPL")
        assert window is not None
        assert len(window) == 5

    @pytest.mark.asyncio
    async def test_outside_window_still_accumulates_bars(self) -> None:
        """Candles outside operating window accumulate but don't signal."""
        config = _make_abcd_config()
        pattern = ABCDPattern()
        strategy = PatternBasedStrategy(
            pattern=pattern,
            config=config,
        )
        strategy.set_watchlist(["AAPL"])

        # 8:00 AM ET = 12:00 UTC — outside 10:00-15:00 window
        from argus.core.events import CandleEvent

        early_ts = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        event = CandleEvent(
            symbol="AAPL",
            timestamp=early_ts,
            open=150.0,
            high=150.10,
            low=149.90,
            close=150.0,
            volume=1000,
        )
        result = await strategy.on_candle(event)
        assert result is None
        # But bar still accumulated
        assert len(strategy._candle_windows.get("AAPL", [])) == 1

    @pytest.mark.asyncio
    async def test_non_watchlist_symbol_ignored(self) -> None:
        """Candles for non-watchlist symbols are ignored."""
        config = _make_abcd_config()
        pattern = ABCDPattern()
        strategy = PatternBasedStrategy(
            pattern=pattern,
            config=config,
        )
        strategy.set_watchlist(["AAPL"])

        event = _make_candle_event("TSLA", 200.0)
        result = await strategy.on_candle(event)
        assert result is None
        assert "TSLA" not in strategy._candle_windows


# ---------------------------------------------------------------------------
# Test 6: ABCDConfig Pydantic model validates
# ---------------------------------------------------------------------------


class TestABCDConfigModel:
    """Test ABCDConfig Pydantic model validation."""

    def test_default_values(self) -> None:
        """ABCDConfig has correct defaults."""
        config = _make_abcd_config()
        assert config.pattern_class == "ABCDPattern"
        assert config.target_1_r == 1.0
        assert config.target_2_r == 2.0
        assert config.time_stop_minutes == 60

    def test_custom_values(self) -> None:
        """ABCDConfig accepts custom target and time values."""
        config = _make_abcd_config(
            target_1_r=1.5,
            target_2_r=3.0,
            time_stop_minutes=90,
        )
        assert config.target_1_r == 1.5
        assert config.target_2_r == 3.0
        assert config.time_stop_minutes == 90

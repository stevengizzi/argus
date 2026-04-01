"""Tests for BacktestEngine reference-data patterns: gap_and_go, premarket_high_break.

Sprint 32.5 Session 4: Verifies:
  - StrategyType enum has GAP_AND_GO and PREMARKET_HIGH_BREAK
  - _create_strategy() factory dispatches to correct pattern wrappers
  - _derive_prior_closes() derives prior close from previous day's last bar
  - _supply_daily_reference_data() passes prior_closes to the pattern
  - First trading day: prior_closes empty, no crash, DEBUG log emitted
  - No PM candles in candle window: PreMarketHighBreakPattern returns None gracefully
  - Non-reference-data patterns (BullFlag) are unaffected
  - runner._PATTERN_TO_STRATEGY_TYPE maps both new patterns
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.intelligence.experiments.runner import _PATTERN_TO_STRATEGY_TYPE
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.base import CandleBar
from argus.strategies.patterns.gap_and_go import GapAndGoPattern
from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern

ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    tmp_path: Path,
    strategy_type: StrategyType,
    strategy_id: str,
) -> BacktestEngineConfig:
    """Build a minimal BacktestEngineConfig for factory tests."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=strategy_type,
        strategy_id=strategy_id,
        log_level="WARNING",
    )


def _make_bar_row(
    trading_date: date,
    ts: datetime,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 10_000,
) -> dict:
    """Build a single bar dict compatible with BacktestEngine._bar_data DataFrames."""
    return {
        "timestamp": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "trading_date": trading_date,
    }


def _make_daily_df(trading_date: date, bars: list[dict]) -> pd.DataFrame:
    """Build a DataFrame of bars for a single trading day."""
    return pd.DataFrame(bars)


# ---------------------------------------------------------------------------
# 1. StrategyType enum membership
# ---------------------------------------------------------------------------


def test_strategy_type_has_gap_and_go() -> None:
    """StrategyType enum includes GAP_AND_GO."""
    assert StrategyType.GAP_AND_GO == "gap_and_go"


def test_strategy_type_has_premarket_high_break() -> None:
    """StrategyType enum includes PREMARKET_HIGH_BREAK."""
    assert StrategyType.PREMARKET_HIGH_BREAK == "premarket_high_break"


# ---------------------------------------------------------------------------
# 2. runner._PATTERN_TO_STRATEGY_TYPE mapping
# ---------------------------------------------------------------------------


def test_runner_maps_gap_and_go() -> None:
    """runner._PATTERN_TO_STRATEGY_TYPE maps gap_and_go → GAP_AND_GO."""
    assert "gap_and_go" in _PATTERN_TO_STRATEGY_TYPE
    assert _PATTERN_TO_STRATEGY_TYPE["gap_and_go"] == StrategyType.GAP_AND_GO


def test_runner_maps_premarket_high_break() -> None:
    """runner._PATTERN_TO_STRATEGY_TYPE maps premarket_high_break → PREMARKET_HIGH_BREAK."""
    assert "premarket_high_break" in _PATTERN_TO_STRATEGY_TYPE
    assert (
        _PATTERN_TO_STRATEGY_TYPE["premarket_high_break"]
        == StrategyType.PREMARKET_HIGH_BREAK
    )


# ---------------------------------------------------------------------------
# 3. Factory: gap_and_go
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_gap_and_go(tmp_path: Path) -> None:
    """GAP_AND_GO creates PatternBasedStrategy wrapping GapAndGoPattern."""
    config = _make_config(tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, GapAndGoPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_gap_and_go_default_params_valid(tmp_path: Path) -> None:
    """GapAndGoPattern constructed via factory has valid default params."""
    config = _make_config(tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        pattern = engine._strategy._pattern  # type: ignore[union-attr]
        params = pattern.get_default_params()
        assert len(params) > 0
        for p in params:
            assert p.name
            assert p.default is not None
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# 4. Factory: premarket_high_break
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_premarket_high_break(tmp_path: Path) -> None:
    """PREMARKET_HIGH_BREAK creates PatternBasedStrategy wrapping PreMarketHighBreakPattern."""
    config = _make_config(
        tmp_path, StrategyType.PREMARKET_HIGH_BREAK, "strat_premarket_high_break"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, PreMarketHighBreakPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_premarket_high_break_default_params_valid(tmp_path: Path) -> None:
    """PreMarketHighBreakPattern constructed via factory has valid default params."""
    config = _make_config(
        tmp_path, StrategyType.PREMARKET_HIGH_BREAK, "strat_premarket_high_break"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        pattern = engine._strategy._pattern  # type: ignore[union-attr]
        params = pattern.get_default_params()
        assert len(params) > 0
        for p in params:
            assert p.name
            assert p.default is not None
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# 5. Prior close derivation — unit tests on _derive_prior_closes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_derive_prior_closes_two_days(tmp_path: Path) -> None:
    """Prior close for day 2 equals the last bar close of day 1."""
    config = _make_config(
        tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        ts1_open = datetime(2025, 6, 16, 9, 30, tzinfo=ET).astimezone(UTC)
        ts1_close = datetime(2025, 6, 16, 15, 55, tzinfo=ET).astimezone(UTC)
        ts2_open = datetime(2025, 6, 17, 9, 30, tzinfo=ET).astimezone(UTC)

        engine._trading_days = [day1, day2]
        engine._bar_data = {
            "TSLA": pd.DataFrame([
                _make_bar_row(day1, ts1_open, close=100.0),
                _make_bar_row(day1, ts1_close, close=105.50),
                _make_bar_row(day2, ts2_open, close=108.0),
            ])
        }

        result = engine._derive_prior_closes(day2, ["TSLA"])

        assert "TSLA" in result
        assert result["TSLA"] == pytest.approx(105.50)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_derive_prior_closes_first_day_returns_empty(tmp_path: Path) -> None:
    """First trading day: _derive_prior_closes returns empty dict (no prior day)."""
    config = _make_config(
        tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        day1 = date(2025, 6, 16)
        ts = datetime(2025, 6, 16, 9, 30, tzinfo=ET).astimezone(UTC)
        engine._trading_days = [day1]
        engine._bar_data = {
            "TSLA": pd.DataFrame([_make_bar_row(day1, ts, close=100.0)])
        }

        result = engine._derive_prior_closes(day1, ["TSLA"])

        assert result == {}
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_derive_prior_closes_missing_symbol_omitted(tmp_path: Path) -> None:
    """Symbol absent from bar_data is omitted from prior_closes dict."""
    config = _make_config(
        tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        ts1 = datetime(2025, 6, 16, 15, 55, tzinfo=ET).astimezone(UTC)

        engine._trading_days = [day1, day2]
        engine._bar_data = {
            "TSLA": pd.DataFrame([_make_bar_row(day1, ts1, close=50.0)])
        }

        result = engine._derive_prior_closes(day2, ["TSLA", "NVDA"])

        assert "TSLA" in result
        assert "NVDA" not in result
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# 6. _supply_daily_reference_data — calls set_reference_data on pattern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supply_reference_data_passes_prior_closes(tmp_path: Path) -> None:
    """_supply_daily_reference_data passes prior_closes to the pattern."""
    config = _make_config(
        tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        ts1 = datetime(2025, 6, 16, 15, 55, tzinfo=ET).astimezone(UTC)
        ts2 = datetime(2025, 6, 17, 9, 30, tzinfo=ET).astimezone(UTC)

        engine._trading_days = [day1, day2]
        engine._bar_data = {
            "TSLA": pd.DataFrame([
                _make_bar_row(day1, ts1, close=200.0),
                _make_bar_row(day2, ts2, close=210.0),
            ])
        }

        engine._supply_daily_reference_data(day2, ["TSLA"])

        assert isinstance(engine._strategy, PatternBasedStrategy)
        pattern = engine._strategy._pattern
        assert isinstance(pattern, GapAndGoPattern)
        assert "TSLA" in pattern._prior_closes
        assert pattern._prior_closes["TSLA"] == pytest.approx(200.0)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_supply_reference_data_first_day_no_crash(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """First trading day: _supply_daily_reference_data logs DEBUG and does not crash."""
    import logging

    config = _make_config(
        tmp_path, StrategyType.GAP_AND_GO, "strat_gap_and_go"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        day1 = date(2025, 6, 16)
        ts1 = datetime(2025, 6, 16, 9, 30, tzinfo=ET).astimezone(UTC)

        engine._trading_days = [day1]
        engine._bar_data = {
            "TSLA": pd.DataFrame([_make_bar_row(day1, ts1, close=100.0)])
        }

        with caplog.at_level(logging.DEBUG, logger="argus.backtest.engine"):
            engine._supply_daily_reference_data(day1, ["TSLA"])

        assert isinstance(engine._strategy, PatternBasedStrategy)
        pattern = engine._strategy._pattern
        assert isinstance(pattern, GapAndGoPattern)
        # Prior closes dict is empty — pattern receives empty dict
        assert pattern._prior_closes == {}
        assert any("prior closes" in rec.message.lower() for rec in caplog.records)
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# 7. PM high derivation — PreMarketHighBreakPattern handles PM candles
# ---------------------------------------------------------------------------


def test_premarket_high_break_detects_pm_high_from_candles() -> None:
    """PreMarketHighBreakPattern derives PM high from pre-9:30 candles in the window.

    BacktestEngine feeds all bars (including pre-market) via feed_bar().
    The pattern splits candles into PM vs market-hours internally.
    When PM candles are present and valid, PM high = max of pre-9:30 bar highs.
    """
    pattern = PreMarketHighBreakPattern(
        min_pm_candles=1,
        min_pm_volume=100.0,
        min_hold_bars=1,
        min_breakout_volume_ratio=1.0,
    )

    # PM candles: 3 bars before 9:30 AM ET with highs 50, 55, 52
    pm_bars = [
        CandleBar(
            timestamp=datetime(2025, 6, 16, 8, 0, tzinfo=ET).astimezone(UTC),
            open=49.0, high=50.0, low=48.0, close=49.5, volume=1000.0,
        ),
        CandleBar(
            timestamp=datetime(2025, 6, 16, 8, 30, tzinfo=ET).astimezone(UTC),
            open=50.0, high=55.0, low=49.5, close=54.0, volume=2000.0,
        ),
        CandleBar(
            timestamp=datetime(2025, 6, 16, 9, 0, tzinfo=ET).astimezone(UTC),
            open=54.0, high=52.0, low=51.0, close=51.5, volume=1500.0,
        ),
    ]
    # Market hours bars: breakout above PM high (55) with volume and hold
    market_bars = [
        CandleBar(
            timestamp=datetime(2025, 6, 16, 9, 35, tzinfo=ET).astimezone(UTC),
            open=55.5, high=57.0, low=55.0, close=56.5, volume=5000.0,
        ),
        CandleBar(
            timestamp=datetime(2025, 6, 16, 9, 36, tzinfo=ET).astimezone(UTC),
            open=56.5, high=58.0, low=56.0, close=57.5, volume=4000.0,
        ),
    ]

    candles = pm_bars + market_bars
    indicators: dict[str, float] = {"atr": 1.0}

    detection = pattern.detect(candles, indicators)

    # PM high should be 55.0 (max of pm bars' highs)
    # Detection should fire (breakout above PM high with volume and hold)
    assert detection is not None
    assert detection.metadata["pm_high"] == pytest.approx(55.0)


def test_premarket_high_break_no_pm_candles_returns_none() -> None:
    """No PM data: all candles after 9:30 AM ET → PreMarketHighBreakPattern returns None."""
    pattern = PreMarketHighBreakPattern(min_pm_candles=1)

    market_only_bars = [
        CandleBar(
            timestamp=datetime(2025, 6, 16, 9, 30, tzinfo=ET).astimezone(UTC),
            open=100.0, high=102.0, low=99.0, close=101.0, volume=5000.0,
        ),
        CandleBar(
            timestamp=datetime(2025, 6, 16, 9, 31, tzinfo=ET).astimezone(UTC),
            open=101.0, high=103.0, low=100.5, close=102.5, volume=4000.0,
        ),
    ]

    detection = pattern.detect(market_only_bars, {"atr": 1.0})

    assert detection is None


# ---------------------------------------------------------------------------
# 8. Non-reference-data patterns unaffected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_pattern_strategy_supply_reference_data_is_noop(
    tmp_path: Path,
) -> None:
    """ORB strategy: _supply_daily_reference_data is a no-op (not PatternBasedStrategy)."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        day1 = date(2025, 6, 16)
        day2 = date(2025, 6, 17)
        ts1 = datetime(2025, 6, 16, 15, 55, tzinfo=ET).astimezone(UTC)

        engine._trading_days = [day1, day2]
        engine._bar_data = {
            "TSLA": pd.DataFrame([_make_bar_row(day1, ts1, close=100.0)])
        }

        # No exception — ORB strategy does not implement set_reference_data
        engine._supply_daily_reference_data(day2, ["TSLA"])
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# Regression: existing pattern mappings unchanged
# ---------------------------------------------------------------------------


def test_runner_bull_flag_mapping_unchanged() -> None:
    """Existing bull_flag mapping is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["bull_flag"] == StrategyType.BULL_FLAG


def test_runner_flat_top_mapping_unchanged() -> None:
    """Existing flat_top_breakout mapping is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["flat_top_breakout"] == StrategyType.FLAT_TOP_BREAKOUT


def test_runner_dip_and_rip_mapping_unchanged() -> None:
    """Existing dip_and_rip mapping (S3) is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["dip_and_rip"] == StrategyType.DIP_AND_RIP


def test_runner_hod_break_mapping_unchanged() -> None:
    """Existing hod_break mapping (S3) is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["hod_break"] == StrategyType.HOD_BREAK


def test_runner_abcd_mapping_unchanged() -> None:
    """Existing abcd mapping (S3) is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["abcd"] == StrategyType.ABCD

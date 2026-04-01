"""Tests for BacktestEngine factory methods — dip_and_rip, hod_break, abcd.

Sprint 32.5 Session 3: Verifies:
  - StrategyType enum has the 3 new values
  - _create_strategy() dispatches to the correct factory method
  - Each factory creates PatternBasedStrategy wrapping the expected pattern
  - _PATTERN_TO_STRATEGY_TYPE in runner.py maps all 3 new patterns
  - bull_flag and flat_top_breakout regressions unchanged
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.intelligence.experiments.runner import _PATTERN_TO_STRATEGY_TYPE
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.abcd import ABCDPattern
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.dip_and_rip import DipAndRipPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.patterns.hod_break import HODBreakPattern


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


# ---------------------------------------------------------------------------
# StrategyType enum membership
# ---------------------------------------------------------------------------


def test_strategy_type_has_dip_and_rip() -> None:
    """StrategyType enum includes DIP_AND_RIP."""
    assert StrategyType.DIP_AND_RIP == "dip_and_rip"


def test_strategy_type_has_hod_break() -> None:
    """StrategyType enum includes HOD_BREAK."""
    assert StrategyType.HOD_BREAK == "hod_break"


def test_strategy_type_has_abcd() -> None:
    """StrategyType enum includes ABCD."""
    assert StrategyType.ABCD == "abcd"


# ---------------------------------------------------------------------------
# _PATTERN_TO_STRATEGY_TYPE mapping
# ---------------------------------------------------------------------------


def test_runner_maps_dip_and_rip() -> None:
    """runner._PATTERN_TO_STRATEGY_TYPE maps dip_and_rip → DIP_AND_RIP."""
    assert "dip_and_rip" in _PATTERN_TO_STRATEGY_TYPE
    assert _PATTERN_TO_STRATEGY_TYPE["dip_and_rip"] == StrategyType.DIP_AND_RIP


def test_runner_maps_hod_break() -> None:
    """runner._PATTERN_TO_STRATEGY_TYPE maps hod_break → HOD_BREAK."""
    assert "hod_break" in _PATTERN_TO_STRATEGY_TYPE
    assert _PATTERN_TO_STRATEGY_TYPE["hod_break"] == StrategyType.HOD_BREAK


def test_runner_maps_abcd() -> None:
    """runner._PATTERN_TO_STRATEGY_TYPE maps abcd → ABCD."""
    assert "abcd" in _PATTERN_TO_STRATEGY_TYPE
    assert _PATTERN_TO_STRATEGY_TYPE["abcd"] == StrategyType.ABCD


# ---------------------------------------------------------------------------
# Regression: existing mappings unchanged
# ---------------------------------------------------------------------------


def test_runner_bull_flag_mapping_unchanged() -> None:
    """Existing bull_flag mapping is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["bull_flag"] == StrategyType.BULL_FLAG


def test_runner_flat_top_mapping_unchanged() -> None:
    """Existing flat_top_breakout mapping is not disturbed."""
    assert _PATTERN_TO_STRATEGY_TYPE["flat_top_breakout"] == StrategyType.FLAT_TOP_BREAKOUT


# ---------------------------------------------------------------------------
# Factory: dip_and_rip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_dip_and_rip(tmp_path: Path) -> None:
    """DIP_AND_RIP creates PatternBasedStrategy wrapping DipAndRipPattern."""
    config = _make_config(tmp_path, StrategyType.DIP_AND_RIP, "strat_dip_and_rip")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, DipAndRipPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_dip_and_rip_default_params_valid(tmp_path: Path) -> None:
    """DipAndRipPattern constructed via factory has valid default params."""
    config = _make_config(tmp_path, StrategyType.DIP_AND_RIP, "strat_dip_and_rip")
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
# Factory: hod_break
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_hod_break(tmp_path: Path) -> None:
    """HOD_BREAK creates PatternBasedStrategy wrapping HODBreakPattern."""
    config = _make_config(tmp_path, StrategyType.HOD_BREAK, "strat_hod_break")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, HODBreakPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_hod_break_default_params_valid(tmp_path: Path) -> None:
    """HODBreakPattern constructed via factory has valid default params."""
    config = _make_config(tmp_path, StrategyType.HOD_BREAK, "strat_hod_break")
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
# Factory: abcd
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_abcd(tmp_path: Path) -> None:
    """ABCD creates PatternBasedStrategy wrapping ABCDPattern."""
    config = _make_config(tmp_path, StrategyType.ABCD, "strat_abcd")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, ABCDPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_abcd_default_params_valid(tmp_path: Path) -> None:
    """ABCDPattern constructed via factory has valid default params."""
    config = _make_config(tmp_path, StrategyType.ABCD, "strat_abcd")
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
# Regression: existing pattern factories unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_bull_flag_regression(tmp_path: Path) -> None:
    """BULL_FLAG factory still creates PatternBasedStrategy(BullFlagPattern)."""
    config = _make_config(tmp_path, StrategyType.BULL_FLAG, "strat_bull_flag")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, BullFlagPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_flat_top_regression(tmp_path: Path) -> None:
    """FLAT_TOP_BREAKOUT factory still creates PatternBasedStrategy(FlatTopBreakoutPattern)."""
    config = _make_config(tmp_path, StrategyType.FLAT_TOP_BREAKOUT, "strat_flat_top_breakout")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, FlatTopBreakoutPattern)
    finally:
        await engine._teardown()

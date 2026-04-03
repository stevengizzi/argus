"""Tests for BacktestEngine DEF-143 fix: pattern constructors use build_pattern_from_config().

Verifies:
  - BullFlag pattern params match config defaults (parity test)
  - DipAndRip pattern respects config overrides (override verification — the
    specific scenario DEF-143 was blocking)
  - All 7 PatternModule StrategyType values produce runnable strategy instances
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.abcd import ABCDPattern
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.dip_and_rip import DipAndRipPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.patterns.gap_and_go import GapAndGoPattern
from argus.strategies.patterns.hod_break import HODBreakPattern
from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern


def _make_config(
    tmp_path: Path,
    strategy_type: StrategyType,
    strategy_id: str,
    config_overrides: dict | None = None,
) -> BacktestEngineConfig:
    """Build a minimal BacktestEngineConfig for factory tests."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=strategy_type,
        strategy_id=strategy_id,
        log_level="WARNING",
        config_overrides=config_overrides or {},
    )


# ---------------------------------------------------------------------------
# Parity test: BullFlag default params match no-arg constructor defaults
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bull_flag_pattern_params_match_config_defaults(tmp_path: Path) -> None:
    """BullFlag pattern built via factory matches no-arg constructor defaults.

    This confirms build_pattern_from_config() extracts and passes the correct
    params — parity between factory-built and directly-constructed instances.
    """
    config = _make_config(tmp_path, StrategyType.BULL_FLAG, "strat_bull_flag")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        factory_pattern = engine._strategy._pattern
        assert isinstance(factory_pattern, BullFlagPattern)

        # Compare against a no-arg default instance
        default_pattern = BullFlagPattern()
        for param in default_pattern.get_default_params():
            factory_val = getattr(factory_pattern, f"_{param.name}", None)
            default_val = getattr(default_pattern, f"_{param.name}", None)
            assert factory_val == default_val, (
                f"BullFlagPattern._{param.name}: factory={factory_val} "
                f"!= default={default_val}"
            )
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# Override test: DipAndRip min_dip_percent override reaches pattern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dip_and_rip_config_override_reaches_pattern(tmp_path: Path) -> None:
    """DipAndRip pattern respects config_overrides — the DEF-143 regression scenario.

    Before the fix, BacktestEngine used DipAndRipPattern() (no-arg), so
    config_overrides had no effect on pattern detection parameters.
    """
    overridden_dip = 0.05  # non-default (default is 0.02)
    config = _make_config(
        tmp_path,
        StrategyType.DIP_AND_RIP,
        "strat_dip_and_rip",
        config_overrides={"min_dip_percent": overridden_dip},
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        pattern = engine._strategy._pattern
        assert isinstance(pattern, DipAndRipPattern)
        assert pattern._min_dip_percent == overridden_dip, (
            f"Expected _min_dip_percent={overridden_dip}, "
            f"got {pattern._min_dip_percent}"
        )
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_dip_and_rip_default_params_parity(tmp_path: Path) -> None:
    """DipAndRip pattern built via factory has the same defaults as no-arg constructor."""
    config = _make_config(tmp_path, StrategyType.DIP_AND_RIP, "strat_dip_and_rip")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        pattern = engine._strategy._pattern  # type: ignore[union-attr]
        assert isinstance(pattern, DipAndRipPattern)
        default_pattern = DipAndRipPattern()
        for param in default_pattern.get_default_params():
            factory_val = getattr(pattern, f"_{param.name}", None)
            default_val = getattr(default_pattern, f"_{param.name}", None)
            assert factory_val == default_val, (
                f"DipAndRipPattern._{param.name}: factory={factory_val} "
                f"!= default={default_val}"
            )
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# All 7 PatternModule StrategyTypes produce runnable strategies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy_type,strategy_id,expected_cls",
    [
        (StrategyType.BULL_FLAG, "strat_bull_flag", BullFlagPattern),
        (StrategyType.FLAT_TOP_BREAKOUT, "strat_flat_top_breakout", FlatTopBreakoutPattern),
        (StrategyType.DIP_AND_RIP, "strat_dip_and_rip", DipAndRipPattern),
        (StrategyType.HOD_BREAK, "strat_hod_break", HODBreakPattern),
        (StrategyType.ABCD, "strat_abcd", ABCDPattern),
        (StrategyType.GAP_AND_GO, "strat_gap_and_go", GapAndGoPattern),
        (StrategyType.PREMARKET_HIGH_BREAK, "strat_premarket_high_break", PreMarketHighBreakPattern),
    ],
)
async def test_all_7_pattern_strategy_types_create_runnable_strategy(
    tmp_path: Path,
    strategy_type: StrategyType,
    strategy_id: str,
    expected_cls: type,
) -> None:
    """Each of the 7 PatternModule StrategyType values produces a runnable PatternBasedStrategy."""
    config = _make_config(tmp_path, strategy_type, strategy_id)
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, expected_cls)
    finally:
        await engine._teardown()

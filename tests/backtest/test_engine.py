"""Tests for BacktestEngine — component assembly + strategy factory.

Sprint 27 Session 3: Verifies _setup() wires SyncEventBus (not EventBus),
FixedClock, SimulatedBroker, and _create_strategy() handles all 7 types.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.core.clock import FixedClock
from argus.core.sync_event_bus import SyncEventBus
from argus.execution.simulated_broker import SimulatedBroker
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy


@pytest.fixture
def engine_config(tmp_path: Path) -> BacktestEngineConfig:
    """Create a BacktestEngineConfig with a temp output directory."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
    )


def _make_config(
    tmp_path: Path,
    strategy_type: StrategyType,
    strategy_id: str,
) -> BacktestEngineConfig:
    """Helper to build engine config for a given strategy type."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=strategy_type,
        strategy_id=strategy_id,
        log_level="WARNING",
    )


@pytest.mark.asyncio
async def test_setup_creates_sync_event_bus(
    engine_config: BacktestEngineConfig,
) -> None:
    """Verify _event_bus is SyncEventBus, not production EventBus."""
    engine = BacktestEngine(engine_config)
    await engine._setup()
    try:
        assert isinstance(engine._event_bus, SyncEventBus)
        # Confirm it is NOT the production EventBus
        from argus.core.event_bus import EventBus

        assert not isinstance(engine._event_bus, EventBus)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_setup_creates_fixed_clock(
    engine_config: BacktestEngineConfig,
) -> None:
    """Verify _clock is FixedClock."""
    engine = BacktestEngine(engine_config)
    await engine._setup()
    try:
        assert isinstance(engine._clock, FixedClock)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_setup_creates_simulated_broker(
    engine_config: BacktestEngineConfig,
) -> None:
    """Verify _broker is SimulatedBroker."""
    engine = BacktestEngine(engine_config)
    await engine._setup()
    try:
        assert isinstance(engine._broker, SimulatedBroker)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_orb_breakout(tmp_path: Path) -> None:
    """strategy_type=ORB_BREAKOUT creates OrbBreakoutStrategy."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbBreakoutStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_orb_scalp(tmp_path: Path) -> None:
    """strategy_type=ORB_SCALP creates OrbScalpStrategy."""
    config = _make_config(tmp_path, StrategyType.ORB_SCALP, "strat_orb_scalp")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbScalpStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_vwap_reclaim(tmp_path: Path) -> None:
    """strategy_type=VWAP_RECLAIM creates VwapReclaimStrategy."""
    config = _make_config(tmp_path, StrategyType.VWAP_RECLAIM, "strat_vwap_reclaim")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, VwapReclaimStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_afternoon_momentum(tmp_path: Path) -> None:
    """strategy_type=AFTERNOON_MOMENTUM creates AfternoonMomentumStrategy."""
    config = _make_config(
        tmp_path, StrategyType.AFTERNOON_MOMENTUM, "strat_afternoon_momentum"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, AfternoonMomentumStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_red_to_green(tmp_path: Path) -> None:
    """strategy_type=RED_TO_GREEN creates RedToGreenStrategy."""
    config = _make_config(tmp_path, StrategyType.RED_TO_GREEN, "strat_red_to_green")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, RedToGreenStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_bull_flag(tmp_path: Path) -> None:
    """strategy_type=BULL_FLAG creates PatternBasedStrategy wrapping BullFlagPattern."""
    config = _make_config(tmp_path, StrategyType.BULL_FLAG, "strat_bull_flag")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, BullFlagPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_flat_top(tmp_path: Path) -> None:
    """strategy_type=FLAT_TOP_BREAKOUT creates PatternBasedStrategy wrapping FlatTopBreakoutPattern."""
    config = _make_config(
        tmp_path, StrategyType.FLAT_TOP_BREAKOUT, "strat_flat_top_breakout"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, FlatTopBreakoutPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_unknown_raises(tmp_path: Path) -> None:
    """Invalid strategy type raises ValueError."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_test")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        # Temporarily override to an invalid value
        engine._config.strategy_type = "not_a_strategy"  # type: ignore[assignment]
        with pytest.raises(ValueError, match="Unknown strategy type"):
            engine._create_strategy(Path("config"))
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_teardown_cleans_up(tmp_path: Path) -> None:
    """run() with stub completes without error and DB file is created."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    engine = BacktestEngine(config)
    result = await engine.run()

    # Verify result is returned
    assert result.strategy_id == "strat_orb_breakout"
    assert result.total_trades == 0
    assert result.initial_capital == 100_000.0

    # Verify DB file was created
    assert engine._db_path is not None
    assert engine._db_path.exists()


@pytest.mark.asyncio
async def test_allocated_capital_set_on_strategy(tmp_path: Path) -> None:
    """Verify allocated_capital is set on the strategy after _setup."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    config.initial_cash = 50_000.0
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert engine._strategy is not None
        assert engine._strategy.allocated_capital == 50_000.0
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_config_overrides_applied(tmp_path: Path) -> None:
    """Verify config_overrides from BacktestEngineConfig are applied to strategy config."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    config.config_overrides = {"orb_window_minutes": 20}
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbBreakoutStrategy)
        assert engine._strategy._config.orb_window_minutes == 20
    finally:
        await engine._teardown()

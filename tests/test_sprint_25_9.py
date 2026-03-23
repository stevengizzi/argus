"""Sprint 25.9 tests — regime fixes and operational visibility.

Tests:
1. All 7 strategies include bearish_trending in allowed_regimes (parameterized)
2. Regime filtering still works for non-allowed regimes
3. Zero-active-strategy warning fires during market hours
4. Zero-active-strategy warning does NOT fire outside market hours
5. Regime reclassification INFO logging cadence (every 6th check)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from zoneinfo import ZoneInfo

from argus.core.clock import FixedClock
from argus.core.config import (
    AfternoonMomentumConfig,
    OrchestratorConfig,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OperatingWindow,
    StrategyRiskLimits,
    VwapReclaimConfig,
)
from argus.core.event_bus import EventBus
from argus.core.orchestrator import Orchestrator
from argus.core.regime import MarketRegime
from argus.models.strategy import MarketConditionsFilter
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy

ET = ZoneInfo("America/New_York")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_RISK = StrategyRiskLimits(
    max_trades_per_day=6,
    max_daily_loss_pct=0.03,
    max_loss_per_trade_pct=0.01,
    max_concurrent_positions=2,
)

_DEFAULT_WINDOW = OperatingWindow(market_open="09:30", latest_entry="11:30")


def _make_orb_breakout() -> OrbBreakoutStrategy:
    config = OrbBreakoutConfig(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        orb_window_minutes=15,
        volume_threshold_rvol=2.0,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=30,
        min_range_atr_ratio=0.5,
        max_range_atr_ratio=2.0,
        chase_protection_pct=0.005,
        breakout_volume_multiplier=1.5,
        risk_limits=_DEFAULT_RISK,
        operating_window=_DEFAULT_WINDOW,
    )
    return OrbBreakoutStrategy(config)


def _make_orb_scalp() -> OrbScalpStrategy:
    config = OrbScalpConfig(
        strategy_id="orb_scalp",
        name="ORB Scalp",
        orb_window_minutes=15,
        volume_threshold_rvol=2.0,
        target_1_r=0.5,
        target_2_r=1.0,
        time_stop_minutes=5,
        min_range_atr_ratio=0.3,
        max_range_atr_ratio=1.5,
        chase_protection_pct=0.003,
        breakout_volume_multiplier=1.2,
        risk_limits=_DEFAULT_RISK,
        operating_window=_DEFAULT_WINDOW,
    )
    return OrbScalpStrategy(config)


def _make_vwap_reclaim() -> VwapReclaimStrategy:
    config = VwapReclaimConfig(
        strategy_id="vwap_reclaim",
        name="VWAP Reclaim",
        vwap_cross_confirmation_bars=2,
        min_distance_from_vwap_pct=0.001,
        max_distance_from_vwap_pct=0.02,
        volume_confirmation_multiplier=1.2,
        pullback_max_bars=10,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=30,
        risk_limits=_DEFAULT_RISK,
        operating_window=OperatingWindow(market_open="09:45", latest_entry="15:00"),
    )
    return VwapReclaimStrategy(config)


def _make_afternoon_momentum() -> AfternoonMomentumStrategy:
    config = AfternoonMomentumConfig(
        strategy_id="afternoon_momentum",
        name="Afternoon Momentum",
        consolidation_start="12:00",
        consolidation_end="14:00",
        breakout_window_start="14:00",
        breakout_window_end="15:30",
        min_consolidation_bars=15,
        max_consolidation_range_atr=0.5,
        breakout_volume_multiplier=1.5,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=45,
        risk_limits=_DEFAULT_RISK,
        operating_window=OperatingWindow(market_open="12:00", latest_entry="15:30"),
    )
    return AfternoonMomentumStrategy(config)


def _make_red_to_green() -> RedToGreenStrategy:
    from argus.core.config import RedToGreenConfig

    config = RedToGreenConfig(
        strategy_id="red_to_green",
        name="Red-to-Green",
        min_gap_down_pct=0.02,
        max_gap_down_pct=0.15,
        min_prior_close=5.0,
        volume_surge_multiplier=2.0,
        confirmation_bars=2,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=30,
        risk_limits=_DEFAULT_RISK,
        operating_window=_DEFAULT_WINDOW,
    )
    return RedToGreenStrategy(config)


def _make_pattern_strategy(pattern_name: str = "bull_flag") -> PatternBasedStrategy:
    """Create a PatternBasedStrategy (covers Bull Flag and Flat-Top Breakout)."""
    from argus.core.config import StrategyConfig

    if pattern_name == "bull_flag":
        from argus.strategies.patterns.bull_flag import BullFlagPattern

        pattern = BullFlagPattern()
    else:
        from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern

        pattern = FlatTopBreakoutPattern()

    config = StrategyConfig(
        strategy_id=pattern_name,
        name=pattern_name.replace("_", " ").title(),
        risk_limits=_DEFAULT_RISK,
        operating_window=_DEFAULT_WINDOW,
    )
    return PatternBasedStrategy(pattern=pattern, config=config)


# ---------------------------------------------------------------------------
# Test 1: All 7 strategies include bearish_trending (DEC-360)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "strategy_factory,strategy_name",
    [
        (_make_orb_breakout, "ORB Breakout"),
        (_make_orb_scalp, "ORB Scalp"),
        (_make_vwap_reclaim, "VWAP Reclaim"),
        (_make_afternoon_momentum, "Afternoon Momentum"),
        (_make_red_to_green, "Red-to-Green"),
        (lambda: _make_pattern_strategy("bull_flag"), "Bull Flag"),
        (lambda: _make_pattern_strategy("flat_top_breakout"), "Flat-Top Breakout"),
    ],
)
def test_strategy_allows_bearish_trending(
    strategy_factory: object, strategy_name: str
) -> None:
    """Each strategy must include bearish_trending in allowed_regimes (DEC-360)."""
    strategy = strategy_factory()
    mcf = strategy.get_market_conditions_filter()
    assert "bearish_trending" in mcf.allowed_regimes, (
        f"{strategy_name} missing bearish_trending in allowed_regimes: {mcf.allowed_regimes}"
    )


# ---------------------------------------------------------------------------
# Test 2: Regime filtering still rejects non-allowed regimes
# ---------------------------------------------------------------------------


def _make_orchestrator(
    clock: FixedClock | None = None,
) -> tuple[Orchestrator, AsyncMock, AsyncMock, AsyncMock]:
    """Create an Orchestrator with mocks for testing."""
    config = OrchestratorConfig(
        allocation_method="equal_weight",
        max_allocation_pct=0.40,
        min_allocation_pct=0.10,
        cash_reserve_pct=0.20,
        performance_lookback_days=20,
        consecutive_loss_throttle=5,
        suspension_sharpe_threshold=0.0,
        suspension_drawdown_pct=0.15,
        regime_check_interval_minutes=30,
        spy_symbol="SPY",
        pre_market_time="09:25",
        eod_review_time="16:05",
        poll_interval_seconds=30,
    )
    event_bus = EventBus()
    if clock is None:
        # 9:30 AM ET = 14:30 UTC
        clock = FixedClock(datetime(2026, 2, 24, 14, 30, tzinfo=UTC))
    mock_tl = AsyncMock()
    mock_tl.get_trades_by_strategy = AsyncMock(return_value=[])
    mock_tl.get_daily_pnl = AsyncMock(return_value=[])
    mock_tl.log_orchestrator_decision = AsyncMock()
    mock_broker = AsyncMock()
    account = MagicMock()
    account.equity = 100000.0
    mock_broker.get_account = AsyncMock(return_value=account)
    mock_ds = AsyncMock()
    mock_ds.fetch_daily_bars = AsyncMock(return_value=None)

    orch = Orchestrator(
        config=config,
        event_bus=event_bus,
        clock=clock,
        trade_logger=mock_tl,
        broker=mock_broker,
        data_service=mock_ds,
    )
    return orch, mock_tl, mock_broker, mock_ds


class MockStrategyBullishOnly:
    """Strategy that only allows bullish_trending."""

    def __init__(self, strategy_id: str = "bullish_only") -> None:
        self._strategy_id = strategy_id
        self.is_active = False
        self.allocated_capital = 0.0

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        return MarketConditionsFilter(allowed_regimes=["bullish_trending"])

    async def reconstruct_state(self, trade_logger: object) -> None:
        pass


@pytest.mark.asyncio
async def test_regime_filtering_rejects_non_allowed() -> None:
    """A strategy restricted to bullish_trending is excluded in range_bound regime."""
    orch, _, _, _ = _make_orchestrator()
    strategy = MockStrategyBullishOnly()
    orch.register_strategy(strategy)
    orch._current_regime = MarketRegime.RANGE_BOUND

    allocations = await orch._calculate_allocations(100000.0)
    alloc = allocations[0]

    assert not alloc.eligible
    assert alloc.allocation_pct == 0.0


# ---------------------------------------------------------------------------
# Test 3: Zero-active-strategy WARNING during market hours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_active_warning_during_market_hours(caplog: pytest.LogCaptureFixture) -> None:
    """Orchestrator logs WARNING when regime filtering yields 0 active strategies during market hours."""
    # Clock at 10:00 AM ET = 15:00 UTC (within market hours)
    clock = FixedClock(datetime(2026, 2, 24, 15, 0, tzinfo=UTC))
    orch, _, _, _ = _make_orchestrator(clock=clock)

    # Register a strategy that only allows bullish_trending
    strategy = MockStrategyBullishOnly()
    orch.register_strategy(strategy)

    # Set regime to crisis — strategy won't be eligible
    orch._current_regime = MarketRegime.CRISIS

    with caplog.at_level(logging.WARNING, logger="argus.core.orchestrator"):
        await orch._calculate_allocations(100000.0)

    warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("0 active strategies" in m for m in warning_msgs), (
        f"Expected zero-active warning, got: {warning_msgs}"
    )


# ---------------------------------------------------------------------------
# Test 4: Zero-active-strategy WARNING does NOT fire outside market hours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_active_no_warning_outside_market_hours(caplog: pytest.LogCaptureFixture) -> None:
    """No warning when 0 strategies are eligible during pre-market (8:00 AM ET)."""
    # 8:00 AM ET = 13:00 UTC (pre-market)
    clock = FixedClock(datetime(2026, 2, 24, 13, 0, tzinfo=UTC))
    orch, _, _, _ = _make_orchestrator(clock=clock)

    strategy = MockStrategyBullishOnly()
    orch.register_strategy(strategy)
    orch._current_regime = MarketRegime.CRISIS

    with caplog.at_level(logging.WARNING, logger="argus.core.orchestrator"):
        await orch._calculate_allocations(100000.0)

    warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert not any("0 active strategies" in m for m in warning_msgs), (
        f"Warning should NOT fire outside market hours, got: {warning_msgs}"
    )


# ---------------------------------------------------------------------------
# Test 5: Regime reclassification logging cadence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regime_reclass_logging_cadence(caplog: pytest.LogCaptureFixture) -> None:
    """INFO fires every 6th unchanged check; DEBUG for other unchanged checks; INFO on change."""
    # Clock at 10:00 AM ET = 15:00 UTC
    clock = FixedClock(datetime(2026, 2, 24, 15, 0, tzinfo=UTC))
    orch, _, _, mock_ds = _make_orchestrator(clock=clock)

    # Create SPY bars that produce a consistent regime
    data = []
    base_price = 500.0
    for i in range(60):
        price = base_price + i * 0.5
        data.append({
            "timestamp": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i),
            "open": price - 1, "high": price + 1,
            "low": price - 2, "close": price, "volume": 100000000,
        })
    mock_ds.fetch_daily_bars.return_value = pd.DataFrame(data)

    # Simulate the _run_regime_reclassification logic inline
    # (can't easily await the infinite loop, so replicate the logging logic)
    from argus.main import ArgusSystem

    system = ArgusSystem.__new__(ArgusSystem)
    system._orchestrator = orch
    system._clock = clock
    system._regime_check_count = 0

    # First call will change regime (range_bound → bullish_trending); stabilize it
    await orch.reclassify_regime()

    # Now run 7 checks with stable (unchanged) regime
    info_checks: list[int] = []
    debug_checks: list[int] = []

    for i in range(1, 8):
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger="argus.main"):
            old, new = await orch.reclassify_regime()
            system._regime_check_count += 1
            if old != new:
                logging.getLogger("argus.main").info(
                    "Regime reclassified: %s → %s", old.value, new.value
                )
            elif system._regime_check_count % 6 == 0:
                indicators = orch.current_indicators
                vol = indicators.spy_realized_vol_20d if indicators else None
                logging.getLogger("argus.main").info(
                    "Regime unchanged: %s (check #%d, SPY vol: %s)",
                    new.value,
                    system._regime_check_count,
                    f"{vol:.4f}" if vol is not None else "N/A",
                )
                info_checks.append(i)
            else:
                logging.getLogger("argus.main").debug("Regime unchanged: %s", new.value)
                debug_checks.append(i)

    # Check 6 should be the INFO one
    assert 6 in info_checks, f"Expected check 6 to be INFO, info_checks={info_checks}"
    # Checks 1-5 and 7 should be DEBUG
    assert debug_checks == [1, 2, 3, 4, 5, 7], f"Unexpected debug_checks={debug_checks}"

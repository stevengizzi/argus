"""Tests for OrbBaseStrategy._calculate_pattern_strength() and signal enrichment.

Sprint 24 Session 1: Verifies the ORB pattern strength scoring (0-100) and
that ORB Breakout / ORB Scalp signals carry pattern_strength, signal_context,
and share_count=0.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import OperatingWindow, OrbBreakoutConfig, OrbScalpConfig, StrategyRiskLimits
from argus.core.events import CandleEvent
from argus.strategies.orb_base import OrbSymbolState
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy

ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_breakout_config(
    min_range_atr_ratio: float = 0.5,
    max_range_atr_ratio: float = 2.0,
    chase_protection_pct: float = 0.005,
    breakout_volume_multiplier: float = 1.5,
) -> OrbBreakoutConfig:
    """Minimal OrbBreakoutConfig for pattern strength tests."""
    return OrbBreakoutConfig(
        strategy_id="strat_orb_breakout",
        name="ORB Breakout",
        orb_window_minutes=15,
        volume_threshold_rvol=2.0,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=30,
        min_range_atr_ratio=min_range_atr_ratio,
        max_range_atr_ratio=max_range_atr_ratio,
        chase_protection_pct=chase_protection_pct,
        breakout_volume_multiplier=breakout_volume_multiplier,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=6,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=2,
        ),
        operating_window=OperatingWindow(latest_entry="11:30"),
    )


def make_scalp_config(
    min_range_atr_ratio: float = 0.5,
    max_range_atr_ratio: float = 999.0,
    chase_protection_pct: float = 0.02,
    breakout_volume_multiplier: float = 1.5,
) -> OrbScalpConfig:
    """Minimal OrbScalpConfig for pattern strength tests."""
    return OrbScalpConfig(
        strategy_id="strat_orb_scalp",
        name="ORB Scalp",
        orb_window_minutes=5,
        scalp_target_r=0.3,
        max_hold_seconds=120,
        stop_placement="midpoint",
        min_range_atr_ratio=min_range_atr_ratio,
        max_range_atr_ratio=max_range_atr_ratio,
        chase_protection_pct=chase_protection_pct,
        breakout_volume_multiplier=breakout_volume_multiplier,
        volume_threshold_rvol=2.0,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=12,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=3,
        ),
        operating_window=OperatingWindow(earliest_entry="09:45", latest_entry="11:30"),
    )


def make_candle(
    close: float = 101.5,
    volume: int = 150_000,
    symbol: str = "AAPL",
    timestamp: datetime | None = None,
) -> CandleEvent:
    """Create a CandleEvent with breakout-like defaults."""
    if timestamp is None:
        timestamp = datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC)
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=close - 0.2,
        high=close + 0.1,
        low=close - 0.5,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


def make_state(
    or_high: float = 101.0,
    or_low: float = 99.0,
    atr_ratio: float | None = 1.0,
) -> OrbSymbolState:
    """Create an OrbSymbolState with a complete, valid OR."""
    state = OrbSymbolState()
    state.or_high = or_high
    state.or_low = or_low
    state.or_midpoint = (or_high + or_low) / 2
    state.or_complete = True
    state.or_valid = True
    state.or_avg_volume = 100_000.0
    state.atr_ratio = atr_ratio
    return state


def make_or_candles(
    num_candles: int,
    or_high: float = 101.0,
    or_low: float = 99.0,
    symbol: str = "AAPL",
) -> list[CandleEvent]:
    """Generate OR candles starting at 9:30 ET."""
    from datetime import timedelta

    base = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
    candles = []
    for i in range(num_candles):
        candles.append(
            CandleEvent(
                symbol=symbol,
                timeframe="1m",
                open=or_low + 0.1,
                high=or_high if i == 2 else or_high - 0.2,
                low=or_low if i == 4 else or_low + 0.2,
                close=(or_high + or_low) / 2,
                volume=100_000 + i * 1000,
                timestamp=base + timedelta(minutes=i),
            )
        )
    return candles


# ---------------------------------------------------------------------------
# Unit tests for _calculate_pattern_strength()
# ---------------------------------------------------------------------------


class TestOrbPatternStrengthMethod:
    """Direct unit tests for _calculate_pattern_strength()."""

    def _make_strategy(self, **kwargs: float) -> OrbBreakoutStrategy:
        config = make_breakout_config(**kwargs)
        return OrbBreakoutStrategy(config)

    def test_orb_pattern_strength_range(self) -> None:
        """All outputs from _calculate_pattern_strength() are in [0, 100]."""
        strategy = self._make_strategy()
        state = make_state(or_high=101.0, or_low=99.0, atr_ratio=1.0)

        test_inputs = [
            (0.5, 0.3, None),
            (1.0, 1.0, 99.5),
            (2.0, 1.25, 100.5),
            (3.0, 2.0, 101.0),
            (10.0, 0.01, 50.0),
        ]
        for vol_ratio, atr_ratio, vwap in test_inputs:
            candle = make_candle(close=101.5)
            strength, _ = strategy._calculate_pattern_strength(
                candle, state, vol_ratio, atr_ratio, vwap
            )
            assert 0.0 <= strength <= 100.0, (
                f"Out of range for vol_ratio={vol_ratio}, atr={atr_ratio}: got {strength}"
            )

    def test_orb_pattern_strength_varies_with_volume(self) -> None:
        """Higher volume ratio → higher pattern_strength."""
        strategy = self._make_strategy()
        state = make_state()
        candle = make_candle(close=101.1)

        low_vol_strength, _ = strategy._calculate_pattern_strength(candle, state, 1.0, 1.0)
        high_vol_strength, _ = strategy._calculate_pattern_strength(candle, state, 3.0, 1.0)

        assert high_vol_strength > low_vol_strength

    def test_orb_pattern_strength_varies_with_atr(self) -> None:
        """Mid-range ATR ratio produces higher score than extreme values."""
        strategy = self._make_strategy(min_range_atr_ratio=0.5, max_range_atr_ratio=2.0)
        state = make_state()
        candle = make_candle(close=101.1)

        # Mid-range ATR = 1.25 (midpoint of [0.5, 2.0])
        mid_strength, _ = strategy._calculate_pattern_strength(candle, state, 2.0, 1.25)
        # Extreme low ATR
        low_strength, _ = strategy._calculate_pattern_strength(candle, state, 2.0, 0.5)
        # Extreme high ATR
        high_strength, _ = strategy._calculate_pattern_strength(candle, state, 2.0, 2.0)

        assert mid_strength > low_strength
        assert mid_strength > high_strength

    def test_orb_pattern_strength_varies_with_chase(self) -> None:
        """Breakout closer to OR high yields higher chase credit."""
        strategy = self._make_strategy(chase_protection_pct=0.01)
        state = make_state(or_high=100.0)

        # Just at OR high
        candle_close = make_candle(close=100.05)  # Very close to OR high
        candle_far = make_candle(close=100.9)  # Near the chase limit

        close_strength, _ = strategy._calculate_pattern_strength(candle_close, state, 2.0, 1.0)
        far_strength, _ = strategy._calculate_pattern_strength(candle_far, state, 2.0, 1.0)

        assert close_strength > far_strength

    def test_orb_pattern_strength_varies_with_vwap(self) -> None:
        """Further above VWAP → higher VWAP credit (with diminishing returns)."""
        strategy = self._make_strategy()
        state = make_state(or_high=100.0)
        candle = make_candle(close=100.5)

        # Just above VWAP (0.1% above = 100.4 VWAP)
        just_above_strength, _ = strategy._calculate_pattern_strength(
            candle, state, 2.0, 1.0, vwap=100.4
        )
        # 1% above VWAP
        far_above_strength, _ = strategy._calculate_pattern_strength(
            candle, state, 2.0, 1.0, vwap=99.5
        )

        assert far_above_strength > just_above_strength

    def test_orb_pattern_strength_vwap_none_neutral(self) -> None:
        """When VWAP is None, VWAP credit is neutral (50) — does not crash."""
        strategy = self._make_strategy()
        state = make_state()
        candle = make_candle(close=101.5)

        strength, context = strategy._calculate_pattern_strength(
            candle, state, 2.0, 1.0, vwap=None
        )
        assert 0.0 <= strength <= 100.0
        assert context["vwap_credit"] == 50.0

    def test_orb_pattern_strength_atr_none_neutral(self) -> None:
        """When atr_ratio is None, ATR credit is neutral (50) — does not crash."""
        strategy = self._make_strategy()
        state = make_state()
        candle = make_candle(close=101.5)

        strength, context = strategy._calculate_pattern_strength(
            candle, state, 2.0, None, vwap=100.0
        )
        assert 0.0 <= strength <= 100.0
        assert context["atr_credit"] == 50.0
        assert context["atr_ratio"] is None

    def test_orb_pattern_strength_state_no_or_high(self) -> None:
        """Gracefully handles state where or_high is None."""
        strategy = self._make_strategy()
        state = OrbSymbolState()  # No OR formed
        candle = make_candle(close=101.5)

        strength, context = strategy._calculate_pattern_strength(
            candle, state, 2.0, None, vwap=None
        )
        assert 0.0 <= strength <= 100.0

    def test_orb_signal_context_populated(self) -> None:
        """signal_context dict contains all expected keys."""
        strategy = self._make_strategy()
        state = make_state(or_high=100.0, atr_ratio=1.0)
        candle = make_candle(close=100.3)

        _, context = strategy._calculate_pattern_strength(
            candle, state, 2.0, 1.0, vwap=99.8
        )

        expected_keys = {
            "volume_ratio",
            "atr_ratio",
            "chase_distance_pct",
            "vwap_distance_pct",
            "volume_credit",
            "atr_credit",
            "chase_credit",
            "vwap_credit",
        }
        assert expected_keys.issubset(set(context.keys()))

    def test_orb_pattern_strength_at_least_3_distinct_buckets(self) -> None:
        """With varied inputs, at least 3 different scores >= 10 apart."""
        strategy = self._make_strategy(chase_protection_pct=0.02)
        state = make_state(or_high=100.0)

        scores = []
        for vol_ratio, atr_ratio, vwap, close in [
            (1.0, 0.5, 100.1, 100.05),   # weak
            (2.0, 1.25, 99.5, 100.3),    # mid
            (4.0, 1.25, 98.0, 100.5),    # strong
        ]:
            candle = make_candle(close=close)
            strength, _ = strategy._calculate_pattern_strength(
                candle, state, vol_ratio, atr_ratio, vwap=vwap
            )
            scores.append(strength)

        # Sort scores and verify spread
        scores.sort()
        assert scores[-1] - scores[0] >= 10.0, (
            f"Score spread too small: {scores}"
        )

    def test_orb_volume_credit_never_below_floor(self) -> None:
        """Volume credit is never below 10.0 regardless of volume_ratio."""
        strategy = self._make_strategy()
        state = make_state()
        candle = make_candle(close=101.5)

        # volume_ratio=0 → formula gives 15, well above the 10 floor
        _, context = strategy._calculate_pattern_strength(candle, state, 0.0, 1.0)
        assert context["volume_credit"] >= 10.0

    def test_orb_volume_credit_clamped_at_high_volume(self) -> None:
        """Volume credit is clamped at 95 even for very high volume_ratio."""
        strategy = self._make_strategy()
        state = make_state()
        candle = make_candle(close=101.5)

        _, context = strategy._calculate_pattern_strength(candle, state, 100.0, 1.0)
        assert context["volume_credit"] == 95.0


# ---------------------------------------------------------------------------
# Integration tests: signal-level assertions
# ---------------------------------------------------------------------------


class TestOrbBreakoutSignalEnrichment:
    """Tests that ORB Breakout signals have share_count=0 and pattern_strength populated."""

    @pytest.mark.asyncio
    async def test_orb_breakout_share_count_zero(self) -> None:
        """ORB Breakout signal always has share_count=0 (Dynamic Sizer deferred)."""
        config = make_breakout_config(chase_protection_pct=0.02)
        mock_ds = AsyncMock()
        mock_ds.get_indicator.side_effect = lambda s, i: {"atr_14": 2.0, "vwap": 100.0}.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles(15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # First post-OR candle to finalize
        post_or = CandleEvent(
            symbol="AAPL", timeframe="1m", open=100.0, high=101.0, low=99.5,
            close=100.5, volume=50_000,
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Breakout candle (entry window: 9:45–11:30)
        breakout = CandleEvent(
            symbol="AAPL", timeframe="1m", open=101.0, high=102.5, low=100.5,
            close=101.8, volume=200_000,
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.share_count == 0

    @pytest.mark.asyncio
    async def test_orb_breakout_pattern_strength_populated(self) -> None:
        """ORB Breakout signal has pattern_strength != 50.0 (was computed, not default)."""
        config = make_breakout_config(chase_protection_pct=0.02)
        mock_ds = AsyncMock()
        mock_ds.get_indicator.side_effect = lambda s, i: {"atr_14": 2.0, "vwap": 100.0}.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles(15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = CandleEvent(
            symbol="AAPL", timeframe="1m", open=100.0, high=101.0, low=99.5,
            close=100.5, volume=50_000,
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = CandleEvent(
            symbol="AAPL", timeframe="1m", open=101.0, high=102.5, low=100.5,
            close=101.8, volume=200_000,
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.pattern_strength != 50.0
        assert 0.0 <= signal.pattern_strength <= 100.0
        assert len(signal.signal_context) > 0


class TestOrbScalpSignalEnrichment:
    """Tests that ORB Scalp signals have share_count=0 and pattern_strength populated."""

    @pytest.mark.asyncio
    async def test_orb_scalp_share_count_zero(self) -> None:
        """ORB Scalp signal always has share_count=0 (Dynamic Sizer deferred)."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_ds = AsyncMock()
        mock_ds.get_indicator.side_effect = lambda s, i: {"atr_14": 2.0, "vwap": 100.0}.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles(5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = CandleEvent(
            symbol="AAPL", timeframe="1m", open=100.0, high=101.0, low=99.5,
            close=100.5, volume=50_000,
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = CandleEvent(
            symbol="AAPL", timeframe="1m", open=101.0, high=102.5, low=100.5,
            close=101.8, volume=200_000,
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.share_count == 0

    @pytest.mark.asyncio
    async def test_orb_scalp_pattern_strength_populated(self) -> None:
        """ORB Scalp signal has pattern_strength != 50.0 (was computed, not default)."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_ds = AsyncMock()
        mock_ds.get_indicator.side_effect = lambda s, i: {"atr_14": 2.0, "vwap": 100.0}.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles(5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = CandleEvent(
            symbol="AAPL", timeframe="1m", open=100.0, high=101.0, low=99.5,
            close=100.5, volume=50_000,
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = CandleEvent(
            symbol="AAPL", timeframe="1m", open=101.0, high=102.5, low=100.5,
            close=101.8, volume=200_000,
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.pattern_strength != 50.0
        assert 0.0 <= signal.pattern_strength <= 100.0
        assert len(signal.signal_context) > 0

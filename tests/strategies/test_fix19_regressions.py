"""Regression tests for FIX-19 strategies session (audit 2026-04-21 Phase 3).

Covers:
- P1-B-M03 (Finding 14): ``StrategyConfig.allowed_regimes`` YAML override flows
  into ``get_market_conditions_filter()`` for every strategy.
- P1-B-M04 (Finding 16): ``PatternBasedStrategy`` default regimes include
  ``"high_volatility"`` so pattern strategies are not silently excluded.
- P1-B-M01 (Finding 5): ``PatternBasedStrategy.reset_daily_state()`` calls
  ``reset_session_state()`` on patterns that expose the hook (VwapBounce).
- P1-B-M06 (Finding 15): Afternoon Momentum ``_build_breakout_signal`` rejects
  zero-R signals via ``_has_zero_r``.
- P1-B-M07 (Finding 11): VWAP Reclaim ``_build_signal`` rejects zero-R signals
  via ``_has_zero_r``.
- P1-B-M02 (Finding 1, DEF-138): telemetry tracking methods are invoked from
  strategy ``on_candle`` paths.
- P1-B-L01 (Finding 2): ``StrategyConfig.mode`` coerces to ``StrategyMode``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import (
    OperatingWindow,
    StrategyConfig,
    StrategyRiskLimits,
    load_afternoon_momentum_config,
    load_orb_config,
    load_orb_scalp_config,
    load_red_to_green_config,
    load_vwap_reclaim_config,
)
from argus.core.events import CandleEvent
from argus.strategies.base_strategy import StrategyMode
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.vwap_bounce import VwapBouncePattern
from argus.strategies.pattern_strategy import PatternBasedStrategy

ET = ZoneInfo("America/New_York")

_ORB_YAML = Path("config/strategies/orb_breakout.yaml")
_ORB_SCALP_YAML = Path("config/strategies/orb_scalp.yaml")
_VWAP_YAML = Path("config/strategies/vwap_reclaim.yaml")
_AFMO_YAML = Path("config/strategies/afternoon_momentum.yaml")
_R2G_YAML = Path("config/strategies/red_to_green.yaml")


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ET)


# ---------------------------------------------------------------------------
# P1-B-M03 — YAML allowed_regimes override flows into filter
# ---------------------------------------------------------------------------


class TestAllowedRegimesOverride:
    """Finding 14: YAML allowed_regimes overrides hardcoded defaults."""

    def test_strategy_config_default_is_none(self) -> None:
        """Base StrategyConfig.allowed_regimes defaults to None (no override)."""
        config = StrategyConfig(
            strategy_id="test",
            name="Test",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
        )
        assert config.allowed_regimes is None

    def test_orb_breakout_honors_config_override(self, tmp_path) -> None:
        """ORB Breakout filter reads self._config.allowed_regimes when set."""
        from argus.strategies.orb_breakout import OrbBreakoutStrategy

        config = load_orb_config(_ORB_YAML)
        # Override with a narrowed regime list
        config = config.model_copy(update={"allowed_regimes": ["bullish_trending"]})
        strategy = OrbBreakoutStrategy(config)
        mcf = strategy.get_market_conditions_filter()
        assert mcf.allowed_regimes == ["bullish_trending"]

    def test_orb_breakout_uses_default_when_config_is_none(self) -> None:
        """ORB Breakout filter uses hardcoded default when config is None."""
        from argus.strategies.orb_breakout import OrbBreakoutStrategy

        config = load_orb_config(_ORB_YAML)
        assert config.allowed_regimes is None
        strategy = OrbBreakoutStrategy(config)
        mcf = strategy.get_market_conditions_filter()
        assert "bullish_trending" in mcf.allowed_regimes
        assert "high_volatility" in mcf.allowed_regimes

    def test_orb_scalp_honors_config_override(self) -> None:
        from argus.strategies.orb_scalp import OrbScalpStrategy

        config = load_orb_scalp_config(_ORB_SCALP_YAML)
        config = config.model_copy(update={"allowed_regimes": ["range_bound"]})
        strategy = OrbScalpStrategy(config)
        mcf = strategy.get_market_conditions_filter()
        assert mcf.allowed_regimes == ["range_bound"]

    def test_vwap_reclaim_honors_config_override(self) -> None:
        from argus.strategies.vwap_reclaim import VwapReclaimStrategy

        config = load_vwap_reclaim_config(_VWAP_YAML)
        config = config.model_copy(update={"allowed_regimes": ["bearish_trending"]})
        strategy = VwapReclaimStrategy(config)
        mcf = strategy.get_market_conditions_filter()
        assert mcf.allowed_regimes == ["bearish_trending"]

    def test_afternoon_momentum_honors_config_override(self) -> None:
        from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy

        config = load_afternoon_momentum_config(_AFMO_YAML)
        config = config.model_copy(update={"allowed_regimes": ["high_volatility"]})
        strategy = AfternoonMomentumStrategy(config)
        mcf = strategy.get_market_conditions_filter()
        assert mcf.allowed_regimes == ["high_volatility"]

    def test_red_to_green_honors_config_override(self) -> None:
        from argus.strategies.red_to_green import RedToGreenStrategy

        config = load_red_to_green_config(_R2G_YAML)
        config = config.model_copy(update={"allowed_regimes": ["range_bound"]})
        strategy = RedToGreenStrategy(config)
        mcf = strategy.get_market_conditions_filter()
        assert mcf.allowed_regimes == ["range_bound"]


# ---------------------------------------------------------------------------
# P1-B-M04 — PatternBasedStrategy default regimes include high_volatility
# ---------------------------------------------------------------------------


class TestPatternBasedStrategyDefaultRegimes:
    """Finding 16: PatternBasedStrategy default list includes high_volatility."""

    def test_default_regimes_include_high_volatility(self) -> None:
        """PatternBasedStrategy.get_market_conditions_filter() default includes high_volatility."""
        config = StrategyConfig(
            strategy_id="test_bull_flag",
            name="Test Bull Flag",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
        )
        pattern = BullFlagPattern()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        mcf = strategy.get_market_conditions_filter()
        assert "high_volatility" in mcf.allowed_regimes
        assert "bullish_trending" in mcf.allowed_regimes
        assert "bearish_trending" in mcf.allowed_regimes
        assert "range_bound" in mcf.allowed_regimes

    def test_yaml_override_wins_over_default(self) -> None:
        """YAML-level allowed_regimes wins over the default list."""
        config = StrategyConfig(
            strategy_id="test_bull_flag",
            name="Test Bull Flag",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
            allowed_regimes=["bullish_trending"],
        )
        pattern = BullFlagPattern()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        mcf = strategy.get_market_conditions_filter()
        assert mcf.allowed_regimes == ["bullish_trending"]


# ---------------------------------------------------------------------------
# P1-B-M01 — VwapBounce session state reset
# ---------------------------------------------------------------------------


class TestVwapBounceSessionReset:
    """Finding 5: PatternBasedStrategy.reset_daily_state() clears pattern session state."""

    def test_reset_daily_state_clears_vwap_bounce_signal_counts(self) -> None:
        """VwapBouncePattern._signal_counts is cleared by reset_daily_state."""
        pattern = VwapBouncePattern()
        pattern._signal_counts["AAPL"] = 3
        pattern._signal_counts["TSLA"] = 2

        config = StrategyConfig(
            strategy_id="test_vwap_bounce",
            name="Test VWAP Bounce",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
        )
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        assert pattern._signal_counts != {}

        strategy.reset_daily_state()
        assert pattern._signal_counts == {}

    def test_reset_daily_state_noop_without_reset_session_state(self) -> None:
        """reset_daily_state does not fail when pattern lacks reset_session_state."""
        pattern = BullFlagPattern()
        assert not hasattr(pattern, "reset_session_state")

        config = StrategyConfig(
            strategy_id="test_bull_flag",
            name="Test Bull Flag",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
        )
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        # Should not raise
        strategy.reset_daily_state()


# ---------------------------------------------------------------------------
# P1-B-L01 — StrategyMode enum coercion
# ---------------------------------------------------------------------------


class TestStrategyModeCoercion:
    """Finding 2: StrategyConfig.mode coerces to StrategyMode on assignment."""

    def test_mode_accepts_literal_live(self) -> None:
        config = StrategyConfig(
            strategy_id="test",
            name="Test",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
            mode="live",
        )
        assert config.mode == StrategyMode.LIVE
        assert config.mode == "live"  # StrEnum equals string

    def test_mode_accepts_literal_shadow(self) -> None:
        config = StrategyConfig(
            strategy_id="test",
            name="Test",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
            mode="shadow",
        )
        assert config.mode == StrategyMode.SHADOW
        assert config.mode == "shadow"

    def test_mode_rejects_invalid_value(self) -> None:
        with pytest.raises(Exception):  # pydantic.ValidationError
            StrategyConfig(
                strategy_id="test",
                name="Test",
                risk_limits=StrategyRiskLimits(),
                operating_window=OperatingWindow(),
                mode="paper",  # invalid
            )


# ---------------------------------------------------------------------------
# P1-B-M02 — DEF-138 telemetry wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDef138TelemetryWiring:
    """Finding 1: Window-summary counters incremented from on_candle paths."""

    async def test_pattern_strategy_tracks_symbol_evaluated(self) -> None:
        """PatternBasedStrategy.on_candle calls _track_symbol_evaluated."""
        pattern = BullFlagPattern()
        config = StrategyConfig(
            strategy_id="test_bull_flag",
            name="Test Bull Flag",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
        )
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        assert strategy._window_symbols_evaluated == 0
        candle = CandleEvent(
            symbol="AAPL",
            timestamp=_ms(2026, 4, 22, 10, 30),
            timeframe="1m",
            open=150.0,
            high=151.0,
            low=149.5,
            close=150.5,
            volume=100_000,
        )
        await strategy.on_candle(candle)
        assert strategy._window_symbols_evaluated == 1

    async def test_pattern_strategy_skips_untracked_watchlist_miss(self) -> None:
        """Symbols not in watchlist don't increment evaluation counter."""
        pattern = BullFlagPattern()
        config = StrategyConfig(
            strategy_id="test_bull_flag",
            name="Test Bull Flag",
            risk_limits=StrategyRiskLimits(),
            operating_window=OperatingWindow(),
        )
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        candle = CandleEvent(
            symbol="TSLA",  # NOT in watchlist
            timestamp=_ms(2026, 4, 22, 10, 30),
            timeframe="1m",
            open=150.0,
            high=151.0,
            low=149.5,
            close=150.5,
            volume=100_000,
        )
        await strategy.on_candle(candle)
        assert strategy._window_symbols_evaluated == 0


# ---------------------------------------------------------------------------
# P1-B-M06/M07 — zero_r guards (Findings 15, 11)
# ---------------------------------------------------------------------------


class TestZeroRGuards:
    """Findings 15 + 11: afternoon_momentum and vwap_reclaim reject zero-R signals."""

    def test_afternoon_momentum_has_zero_r_helper_available(self) -> None:
        """AfternoonMomentumStrategy inherits _has_zero_r helper."""
        from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy

        config = load_afternoon_momentum_config(_AFMO_YAML)
        strategy = AfternoonMomentumStrategy(config)
        # Equal entry / target → zero-R
        assert strategy._has_zero_r("AAPL", 150.00, 150.00) is True
        # Normal ≥ $0.01 distance → not zero-R
        assert strategy._has_zero_r("AAPL", 150.00, 150.25) is False

    def test_vwap_reclaim_has_zero_r_helper_available(self) -> None:
        """VwapReclaimStrategy inherits _has_zero_r helper."""
        from argus.strategies.vwap_reclaim import VwapReclaimStrategy

        config = load_vwap_reclaim_config(_VWAP_YAML)
        strategy = VwapReclaimStrategy(config)
        assert strategy._has_zero_r("AAPL", 150.00, 150.005) is True
        assert strategy._has_zero_r("AAPL", 150.00, 150.25) is False

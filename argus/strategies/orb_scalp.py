"""ORB Scalp Strategy implementation.

The ORB Scalp strategy is a fast-paced variant of the Opening Range Breakout
strategy, designed for quick momentum captures with tight targets and short
hold times.

Key differences from ORB Breakout:
- Single target at 0.3R (instead of T1/T2 at 1R/2R)
- Maximum hold time of 120 seconds (instead of minutes)
- Higher trade frequency (12/day vs 6/day)
- Higher win rate requirement (55% vs 45%)

Entry criteria: Same as ORB Breakout (inherited from OrbBaseStrategy)
Stop loss: Midpoint of opening range (same as ORB)
Target: Single target at scalp_target_r (default 0.3R)

DEC-123: Single target exit, 0.3R default, 120s hold, midpoint stop
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from argus.core.clock import Clock
from argus.core.config import OrbScalpConfig
from argus.core.events import CandleEvent, Side, SignalEvent
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
)
from argus.strategies.orb_base import OrbBaseStrategy, OrbSymbolState
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult

if TYPE_CHECKING:
    from argus.data.service import DataService

logger = logging.getLogger(__name__)


class OrbScalpStrategy(OrbBaseStrategy):
    """ORB Scalp Strategy.

    Fast-paced ORB variant optimized for quick momentum captures with
    single target exits and short hold times.

    Lifecycle:
    1. Formation phase: Accumulate candles during orb_window_minutes (default 5)
    2. Validation: Check range size against ATR bounds
    3. Monitoring: Watch for breakouts with volume/VWAP confirmation
    4. Signal: Emit SignalEvent with single scalp target
    5. Exit: Target at scalp_target_r or max_hold_seconds time stop
    """

    def __init__(
        self,
        config: OrbScalpConfig,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the ORB Scalp strategy.

        Args:
            config: OrbScalpConfig with scalp-specific parameters.
            data_service: DataService for indicator queries (VWAP, ATR).
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        super().__init__(config, data_service=data_service, clock=clock)
        # Keep a typed reference to access scalp-specific fields
        self._scalp_config = config

    async def _build_breakout_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: OrbSymbolState,
        volume_threshold: float,
    ) -> SignalEvent | None:
        """Build a SignalEvent with single scalp target.

        Args:
            symbol: The symbol that triggered the breakout.
            candle: The breakout candle.
            state: The symbol's ORB state (contains OR high/low/midpoint).
            volume_threshold: The volume threshold that was exceeded.

        Returns:
            SignalEvent with single target at scalp_target_r.
        """
        if state.or_high is None or state.or_midpoint is None:
            return None

        entry_price = candle.close
        stop_price = state.or_midpoint
        risk_per_share = entry_price - stop_price

        # Calculate single scalp target
        target = entry_price + risk_per_share * self._scalp_config.scalp_target_r

        # Get VWAP for rationale and pattern strength
        vwap: float | None = None
        vwap_str = "N/A"
        if self._data_service is not None:
            vwap = await self._data_service.get_indicator(symbol, "vwap")
            if vwap is not None:
                vwap_str = f"{vwap:.2f}"

        # Calculate pattern strength (share_count deferred to Dynamic Sizer, Sprint 24 S6a)
        volume_ratio = candle.volume / volume_threshold if volume_threshold > 0 else 1.0
        pattern_strength, signal_context = self._calculate_pattern_strength(
            candle, state, volume_ratio, state.atr_ratio, vwap
        )

        self.record_evaluation(
            symbol,
            EvaluationEventType.QUALITY_SCORED,
            EvaluationResult.INFO,
            f"ORB Scalp pattern strength: {pattern_strength:.1f}",
            signal_context,
        )

        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target,),  # Single target
            share_count=0,
            rationale=(
                f"ORB scalp: {symbol} closed above OR high {state.or_high:.2f}, "
                f"volume {candle.volume} > {volume_threshold:.0f}, VWAP {vwap_str}"
            ),
            time_stop_seconds=self._scalp_config.max_hold_seconds,
            pattern_strength=pattern_strength,
            signal_context=signal_context,
        )

        # Mark breakout as triggered
        state.breakout_triggered = True
        state.position_active = True
        # DEC-261: Mark symbol as triggered for ORB family exclusion
        OrbBaseStrategy._orb_family_triggered_symbols.add(symbol)

        self.record_evaluation(
            symbol,
            EvaluationEventType.SIGNAL_GENERATED,
            EvaluationResult.PASS,
            f"ORB Scalp signal generated for {symbol}",
            {
                "direction": "long",
                "entry": entry_price,
                "stop": stop_price,
                "target1": target,
            },
        )

        logger.info(
            "%s: ORB scalp signal - entry=%.2f, stop=%.2f, target=%.2f, "
            "pattern_strength=%.1f, time_stop=%ds",
            symbol,
            entry_price,
            stop_price,
            target,
            pattern_strength,
            self._scalp_config.max_hold_seconds,
        )

        return signal

    def get_exit_rules(self) -> ExitRules:
        """Return ORB Scalp exit rules (single target, short time stop)."""
        return ExitRules(
            stop_type="fixed",
            stop_price_func="midpoint",
            targets=[
                ProfitTarget(
                    r_multiple=self._scalp_config.scalp_target_r,
                    position_pct=1.0,  # Exit 100% at target
                ),
            ],
            time_stop_minutes=self._scalp_config.max_hold_seconds // 60,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market conditions for ORB Scalp activation.

        Same regimes as ORB Breakout - works well in trending and volatile
        conditions where momentum is present.
        """
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "range_bound", "high_volatility"],
            max_vix=35.0,
        )

"""ORB (Opening Range Breakout) Strategy implementation.

The ORB strategy trades breakouts from the opening range of the trading day.
It forms an opening range during the first N minutes (configurable), then
waits for price to break out above the range with volume confirmation.

Entry criteria:
- Price closes above the opening range high
- Breakout candle volume > threshold × average OR volume
- Price is above VWAP
- Chase protection: price hasn't moved too far from OR high

Stop loss: Midpoint of opening range (DEC-012)
Targets: 1R and 2R (configurable)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from argus.core.clock import Clock
from argus.core.config import OrbBreakoutConfig
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


class OrbBreakoutStrategy(OrbBaseStrategy):
    """ORB (Opening Range Breakout) Strategy.

    Trades breakouts from the opening range of the trading day with
    swing-style targets (1R and 2R).

    Lifecycle:
    1. Formation phase: Accumulate candles during orb_window_minutes
    2. Validation: Check range size against ATR bounds
    3. Monitoring: Watch for breakouts with volume/VWAP confirmation
    4. Signal: Emit SignalEvent when all criteria met
    """

    def __init__(
        self,
        config: OrbBreakoutConfig,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the ORB Breakout strategy.

        Args:
            config: OrbBreakoutConfig with strategy parameters.
            data_service: DataService for indicator queries (VWAP, ATR).
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        super().__init__(config, data_service=data_service, clock=clock)
        # Keep a typed reference to access ORB-specific fields like target_1_r
        self._breakout_config = config

    async def _build_breakout_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: OrbSymbolState,
        volume_threshold: float,
    ) -> SignalEvent | None:
        """Build a SignalEvent with swing-style T1/T2 targets.

        Args:
            symbol: The symbol that triggered the breakout.
            candle: The breakout candle.
            state: The symbol's ORB state (contains OR high/low/midpoint).
            volume_threshold: The volume threshold that was exceeded.

        Returns:
            SignalEvent with T1 (1R) and T2 (2R) targets.
        """
        if state.or_high is None or state.or_midpoint is None:
            return None

        entry_price = candle.close
        stop_price = state.or_midpoint
        risk_per_share = entry_price - stop_price

        # Calculate targets
        target_1 = entry_price + risk_per_share * self._breakout_config.target_1_r
        target_2 = entry_price + risk_per_share * self._breakout_config.target_2_r

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
            f"ORB Breakout pattern strength: {pattern_strength:.1f}",
            signal_context,
        )

        # ATR(14) on 1-min bars per AMD-9 standardization
        atr_value: float | None = None
        if self._data_service is not None:
            atr_value = await self._data_service.get_indicator(symbol, "atr_14")

        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_1, target_2),
            share_count=0,
            rationale=(
                f"ORB breakout: {symbol} closed above OR high {state.or_high:.2f}, "
                f"volume {candle.volume} > {volume_threshold:.0f}, VWAP {vwap_str}"
            ),
            time_stop_seconds=self._breakout_config.time_stop_minutes * 60,
            pattern_strength=pattern_strength,
            signal_context=signal_context,
            atr_value=atr_value,
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
            f"ORB Breakout signal generated for {symbol}",
            {
                "direction": "long",
                "entry": entry_price,
                "stop": stop_price,
                "target1": target_1,
                "target2": target_2,
            },
        )

        logger.info(
            "%s: ORB breakout signal - entry=%.2f, stop=%.2f, targets=(%.2f, %.2f), "
            "pattern_strength=%.1f",
            symbol,
            entry_price,
            stop_price,
            target_1,
            target_2,
            pattern_strength,
        )

        return signal

    def get_exit_rules(self) -> ExitRules:
        """Return ORB exit rules (targets, stop, time stop)."""
        return ExitRules(
            stop_type="fixed",
            stop_price_func="midpoint",
            targets=[
                ProfitTarget(
                    r_multiple=self._breakout_config.target_1_r,
                    position_pct=0.5,
                ),
                ProfitTarget(
                    r_multiple=self._breakout_config.target_2_r,
                    position_pct=0.5,
                ),
            ],
            time_stop_minutes=self._breakout_config.time_stop_minutes,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market conditions for ORB activation."""
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "bearish_trending", "range_bound", "high_volatility"],
            max_vix=35.0,
        )

"""Abstract Base Class for all trading strategies.

All strategies in Argus inherit from BaseStrategy. This defines the
complete interface that strategies must implement, ensuring consistency
across the strategy ecosystem.

Strategies follow a daily-stateful, session-stateless model (DEC-028):
- Within a trading day: accumulate state (opening range, trade count, daily P&L)
- Between trading days: all state wiped by reset_daily_state()
- On mid-day restart: reconstruct intraday state from database via reconstruct_state()
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, time
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.clock import Clock, SystemClock
from argus.core.config import StrategyConfig
from argus.core.events import CandleEvent, SignalEvent, TickEvent
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ScannerCriteria,
)
from argus.strategies.telemetry import (
    EvaluationEvent,
    EvaluationEventType,
    EvaluationResult,
    StrategyEvaluationBuffer,
)

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger

logger = logging.getLogger(__name__)


class StrategyMode(StrEnum):
    """Operating mode for a strategy (Sprint 27.7)."""

    LIVE = "live"      # Normal execution — signals go through quality + risk pipeline
    SHADOW = "shadow"  # Shadow mode — signals routed to CounterfactualTracker


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    Strategies follow a daily-stateful, session-stateless model (DEC-028):
    - Within a trading day: accumulate state (opening range, trade count, daily P&L)
    - Between trading days: all state wiped by reset_daily_state()
    - On mid-day restart: reconstruct intraday state from database via reconstruct_state()

    Subclasses must implement all abstract methods and properties.
    """

    def __init__(self, config: StrategyConfig, clock: Clock | None = None) -> None:
        """Initialize strategy with validated configuration.

        Args:
            config: Strategy configuration loaded from YAML and validated by Pydantic.
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        self._config = config
        self._clock: Clock = clock if clock is not None else SystemClock()
        self._allocated_capital: float = 0.0
        self._is_active: bool = False
        self._daily_pnl: float = 0.0
        self._trade_count_today: int = 0
        self._watchlist: set[str] = set()
        self._eval_buffer = StrategyEvaluationBuffer()

        # Window summary counters — reset each day in reset_daily_state()
        self._window_symbols_evaluated: int = 0
        self._window_signals_generated: int = 0
        self._window_signals_rejected: int = 0
        self._window_rejection_reasons: dict[str, int] = {}
        self._window_summary_logged: bool = False

    # -------------------------------------------------------------------------
    # Identity (from config)
    # -------------------------------------------------------------------------

    @property
    def strategy_id(self) -> str:
        """Unique identifier for this strategy instance."""
        return self._config.strategy_id

    @property
    def name(self) -> str:
        """Human-readable name of the strategy."""
        return self._config.name

    @property
    def version(self) -> str:
        """Version string for the strategy."""
        return self._config.version

    @property
    def config(self) -> StrategyConfig:
        """Access to the full strategy configuration."""
        return self._config

    # -------------------------------------------------------------------------
    # Core Interface (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a new candle. Return a SignalEvent if entry criteria are met.

        This is the primary decision method. Called by the Orchestrator/Event Bus
        for every CandleEvent matching symbols on this strategy's watchlist.

        Args:
            event: The candle event with OHLCV data.

        Returns:
            A SignalEvent if all entry criteria are met, None otherwise.
        """

    @abstractmethod
    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick update. Used for fast strategies and position management.

        Args:
            event: The tick event with current price data.
        """

    @abstractmethod
    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner filter criteria for this strategy's stock selection.

        Returns:
            ScannerCriteria defining the filters for pre-market scanning.
        """

    @abstractmethod
    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Calculate number of shares for a trade.

        Uses the universal formula: shares = risk_dollars / (entry - stop)
        Risk dollars = allocated_capital * risk_per_trade_pct

        Args:
            entry_price: Expected entry price.
            stop_price: Stop loss price.

        Returns:
            Number of shares (integer, floored). Returns 0 if calculation
            is invalid (e.g., stop_price >= entry_price for longs).
        """

    @abstractmethod
    def get_exit_rules(self) -> ExitRules:
        """Return the complete exit configuration for this strategy.

        Returns:
            ExitRules containing stop loss, profit targets, time stop,
            and trailing stop configuration.
        """

    @abstractmethod
    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market regime conditions for strategy activation.

        The Orchestrator checks these conditions daily to decide whether
        this strategy should be active.

        Returns:
            MarketConditionsFilter with required regime, VIX range, etc.
        """

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def _has_zero_r(
        self, symbol: str, entry_price: float, target_price: float
    ) -> bool:
        """Check if signal has zero or negative profit potential.

        Suppresses signals where abs(target - entry) < $0.01 to avoid
        placing trades with no R (e.g., PDBC entry=$16.86 target=$16.86).

        Args:
            symbol: Ticker for logging.
            entry_price: Expected entry price.
            target_price: First target price (T1).

        Returns:
            True if zero-R detected (signal should be suppressed).
        """
        if abs(target_price - entry_price) < 0.01:
            logger.debug(
                "%s: signal suppressed — zero R (entry=%.2f, target=%.2f)",
                symbol,
                entry_price,
                target_price,
            )
            return True
        return False

    def check_internal_risk_limits(self) -> bool:
        """Check strategy-level risk limits.

        Returns:
            True if the strategy is within all its limits and can continue trading.
            False if any limit is hit (max daily loss, max positions, max trades).
        """
        limits = self._config.risk_limits

        # Check max trades per day
        if self._trade_count_today >= limits.max_trades_per_day:
            logger.debug(
                "%s: max_trades_per_day (%d) reached",
                self.strategy_id,
                limits.max_trades_per_day,
            )
            return False

        # Check max daily loss (as percentage of allocated capital)
        if self._allocated_capital > 0:
            loss_pct = abs(self._daily_pnl) / self._allocated_capital
            if self._daily_pnl < 0 and loss_pct >= limits.max_daily_loss_pct:
                logger.debug(
                    "%s: max_daily_loss_pct (%.1f%%) reached",
                    self.strategy_id,
                    limits.max_daily_loss_pct * 100,
                )
                return False

        return True

    def reset_daily_state(self) -> None:
        """Reset all intraday state. Called at start of each trading day.

        Wipes: daily P&L, trade count, opening range, watchlist,
        any strategy-specific intraday state. Does NOT reset config,
        allocated_capital, or pipeline_stage.

        Subclasses should override this to reset strategy-specific state,
        but must call super().reset_daily_state() first.
        """
        self._daily_pnl = 0.0
        self._trade_count_today = 0
        self._watchlist = set()
        self._window_symbols_evaluated = 0
        self._window_signals_generated = 0
        self._window_signals_rejected = 0
        self._window_rejection_reasons = {}
        self._window_summary_logged = False
        logger.debug("%s: daily state reset", self.strategy_id)

    async def reconstruct_state(self, trade_logger: TradeLogger) -> None:
        """Reconstruct intraday state from database after mid-day restart.

        Queries today's trades and open positions from the Trade Logger.

        Args:
            trade_logger: TradeLogger instance for database queries.
        """
        today = self._clock.today()
        trades_today = await trade_logger.get_trades_by_date(today)

        # Filter trades for this strategy
        my_trades = [t for t in trades_today if t.strategy_id == self.strategy_id]

        self._daily_pnl = sum(t.net_pnl for t in my_trades if t.net_pnl is not None)
        self._trade_count_today = len(my_trades)

        logger.info(
            "%s: state reconstructed - daily_pnl=$%.2f, trades=%d",
            self.strategy_id,
            self._daily_pnl,
            self._trade_count_today,
        )

    def set_watchlist(self, symbols: list[str], source: str = "scanner") -> None:
        """Set the watchlist for this strategy.

        Called by the Orchestrator after the Scanner runs, or by the startup
        sequence when the Universe Manager populates strategy watchlists.

        Args:
            symbols: List of ticker symbols to watch today.
            source: Origin of the watchlist (e.g. "scanner", "universe_manager").
        """
        self._watchlist = set(symbols)
        logger.debug(
            "%s: watchlist set to %d symbols (source: %s)",
            self.strategy_id,
            len(self._watchlist),
            source,
        )

    def record_trade_result(self, pnl: float) -> None:
        """Record the result of a completed trade.

        Called by the Order Manager when a position is closed.

        Args:
            pnl: Net P&L of the completed trade.
        """
        self._daily_pnl += pnl
        self._trade_count_today += 1
        logger.debug(
            "%s: trade result recorded - pnl=$%.2f, daily_pnl=$%.2f, trades=%d",
            self.strategy_id,
            pnl,
            self._daily_pnl,
            self._trade_count_today,
        )

    # -------------------------------------------------------------------------
    # Window Summary Tracking
    # -------------------------------------------------------------------------

    def _track_symbol_evaluated(self) -> None:
        """Increment the count of symbols evaluated this window.

        Subclasses call this when they assess a symbol against entry criteria,
        regardless of whether a signal is generated.
        """
        self._window_symbols_evaluated += 1

    def _track_signal_generated(self) -> None:
        """Increment the count of signals generated this window."""
        self._window_signals_generated += 1

    def _track_signal_rejected(self, reason: str) -> None:
        """Increment the rejected-signal counter and record the reason.

        Args:
            reason: Short label for why the signal was suppressed
                (e.g., "no_volume", "outside_window", "zero_r").
        """
        self._window_signals_rejected += 1
        self._window_rejection_reasons[reason] = (
            self._window_rejection_reasons.get(reason, 0) + 1
        )

    def _log_window_summary(self) -> None:
        """Log the end-of-window evaluation summary at INFO level.

        Emits a single structured log line covering symbols evaluated,
        signals generated, signals rejected, and the rejection breakdown.
        Called once per day when the operating window closes.
        """
        rejection_breakdown = (
            ", ".join(
                f"{reason}={count}"
                for reason, count in sorted(self._window_rejection_reasons.items())
            )
            if self._window_rejection_reasons
            else "none"
        )
        logger.info(
            "Strategy %s window closed: %d symbols evaluated, "
            "%d signals generated, %d rejected (%s)",
            self.name,
            self._window_symbols_evaluated,
            self._window_signals_generated,
            self._window_signals_rejected,
            rejection_breakdown,
        )

    def _maybe_log_window_summary(self, candle_time: time) -> None:
        """Emit the window summary once, the first candle after latest_entry.

        Subclasses call this from on_candle with the ET candle time after
        checking their own operating-window state. The call is idempotent —
        only fires once per day (guarded by _window_summary_logged).

        Args:
            candle_time: The ET time of the incoming candle.
        """
        if self._window_summary_logged:
            return
        latest_entry_str = self._config.operating_window.latest_entry
        lh, lm = (int(x) for x in latest_entry_str.split(":"))
        if candle_time >= time(lh, lm):
            self._log_window_summary()
            self._window_summary_logged = True

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Whether this strategy is currently active (accepting signals)."""
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        """Set the active status of this strategy."""
        self._is_active = value

    @property
    def allocated_capital(self) -> float:
        """Capital allocated to this strategy by the Orchestrator."""
        return self._allocated_capital

    @allocated_capital.setter
    def allocated_capital(self, value: float) -> None:
        """Set the capital allocation for this strategy."""
        if value < 0:
            raise ValueError("Allocated capital cannot be negative")
        self._allocated_capital = value

    @property
    def daily_pnl(self) -> float:
        """Current daily realized P&L for this strategy."""
        return self._daily_pnl

    @property
    def trade_count_today(self) -> int:
        """Number of trades executed today by this strategy."""
        return self._trade_count_today

    @property
    def watchlist(self) -> list[str]:
        """Current watchlist of symbols this strategy is tracking."""
        return list(self._watchlist)

    @property
    def eval_buffer(self) -> StrategyEvaluationBuffer:
        """Ring buffer of recent evaluation events for this strategy."""
        return self._eval_buffer

    def record_evaluation(
        self,
        symbol: str,
        event_type: EvaluationEventType,
        result: EvaluationResult,
        reason: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Record a strategy evaluation event. Fire-and-forget — never raises.

        Args:
            symbol: The ticker being evaluated.
            event_type: Category of evaluation step.
            result: Whether the step passed, failed, or is informational.
            reason: Human-readable explanation of the result.
            metadata: Optional strategy-specific supplemental data.
        """
        try:
            et_tz = ZoneInfo("America/New_York")
            event = EvaluationEvent(
                timestamp=datetime.now(et_tz).replace(tzinfo=None),
                symbol=symbol,
                strategy_id=self.strategy_id,
                event_type=event_type,
                result=result,
                reason=reason,
                metadata=metadata or {},
            )
            self._eval_buffer.record(event)
        except Exception:
            pass  # Telemetry must never impact strategy operation

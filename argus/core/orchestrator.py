"""Orchestrator for managing strategy lifecycle and capital allocation.

The Orchestrator is the central coordinator for the Argus trading system.
It manages:
- Market regime classification and monitoring
- Strategy activation/deactivation based on regime
- Capital allocation across strategies
- Performance-based throttling and suspension

V1 is rules-based. Designed for AI enhancement in V2+ (Sprint 22).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.clock import Clock
from argus.core.config import OrchestratorConfig
from argus.core.correlation import CorrelationTracker
from argus.core.event_bus import EventBus
from argus.core.events import (
    AllocationUpdateEvent,
    PositionClosedEvent,
    RegimeChangeEvent,
    StrategyActivatedEvent,
    StrategySuspendedEvent,
)
from argus.core.regime import MarketRegime, RegimeClassifier, RegimeIndicators
from argus.core.throttle import PerformanceThrottler, StrategyAllocation, ThrottleAction

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.data.service import DataService
    from argus.execution.broker import Broker
    from argus.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Orchestrator:
    """Manages strategy lifecycle, capital allocation, and market regime classification.

    V1 is rules-based. Designed for AI enhancement in V2+ (Sprint 22).

    Responsibilities:
    - Pre-market routine: classify regime, allocate capital, activate strategies
    - Intraday monitoring: re-evaluate regime every N minutes, throttle on losses
    - End-of-day review: log decisions, update correlation data
    - Strategy lifecycle: register, activate, deactivate, suspend
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        event_bus: EventBus,
        clock: Clock,
        trade_logger: TradeLogger,
        broker: Broker,
        data_service: DataService,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            config: Orchestrator configuration.
            event_bus: Event bus for publishing events.
            clock: Clock for time access.
            trade_logger: Trade logger for performance data.
            broker: Broker for account information.
            data_service: Data service for fetching daily bars.
        """
        self._config = config
        self._event_bus = event_bus
        self._clock = clock
        self._trade_logger = trade_logger
        self._broker = broker
        self._data_service = data_service

        # Supporting components
        self._regime_classifier = RegimeClassifier(config)
        self._throttler = PerformanceThrottler(config)
        self._correlation_tracker = CorrelationTracker()

        # Strategy registry
        self._strategies: dict[str, BaseStrategy] = {}

        # Current state
        self._current_regime: MarketRegime = MarketRegime.RANGE_BOUND  # safe default
        self._current_allocations: dict[str, StrategyAllocation] = {}
        self._current_indicators: RegimeIndicators | None = None

        # Background task
        self._poll_task: asyncio.Task | None = None
        self._running: bool = False

        # Daily flags
        self._pre_market_done_today: bool = False
        self._eod_done_today: bool = False
        self._last_date: str | None = None
        self._last_regime_check: datetime | None = None

        # Intraday loss tracking
        self._intraday_losses: dict[str, list[float]] = {}  # strategy_id → [pnl, pnl, ...]

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to events and launch poll loop."""
        self._running = True
        self._event_bus.subscribe(PositionClosedEvent, self._on_position_closed)
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Cancel poll loop, unsubscribe."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
        self._event_bus.unsubscribe(PositionClosedEvent, self._on_position_closed)
        logger.info("Orchestrator stopped")

    # -------------------------------------------------------------------------
    # Strategy Management
    # -------------------------------------------------------------------------

    def register_strategy(self, strategy: BaseStrategy) -> None:
        """Register a strategy with the Orchestrator.

        Args:
            strategy: The strategy to register.
        """
        self._strategies[strategy.strategy_id] = strategy
        logger.info("Registered strategy: %s", strategy.strategy_id)

    def get_strategies(self) -> dict[str, BaseStrategy]:
        """Get all registered strategies.

        Returns:
            Dict mapping strategy_id to strategy instance.
        """
        return self._strategies.copy()

    def get_strategy(self, strategy_id: str) -> BaseStrategy | None:
        """Get a specific strategy by ID.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            The strategy instance, or None if not found.
        """
        return self._strategies.get(strategy_id)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def current_regime(self) -> MarketRegime:
        """Get the current market regime."""
        return self._current_regime

    @property
    def current_allocations(self) -> dict[str, StrategyAllocation]:
        """Get current strategy allocations."""
        return self._current_allocations.copy()

    @property
    def current_indicators(self) -> RegimeIndicators | None:
        """Get the current regime indicators."""
        return self._current_indicators

    @property
    def correlation_tracker(self) -> CorrelationTracker:
        """Get the correlation tracker instance."""
        return self._correlation_tracker

    # -------------------------------------------------------------------------
    # Pre-Market Routine
    # -------------------------------------------------------------------------

    async def run_pre_market(self) -> None:
        """Full pre-market sequence. Called at configured time or on mid-day restart."""
        logger.info("Running pre-market routine")

        # 0. Reconstruct strategy state (trade counts, daily P&L) from trade log
        for strategy in self._strategies.values():
            await strategy.reconstruct_state(self._trade_logger)

        # 1. Fetch SPY daily bars
        spy_bars = await self._data_service.fetch_daily_bars(
            self._config.spy_symbol, lookback_days=60
        )

        # 2. Classify regime
        if spy_bars is not None and len(spy_bars) >= 20:
            indicators = self._regime_classifier.compute_indicators(spy_bars)
            new_regime = self._regime_classifier.classify(indicators)
            self._current_indicators = indicators
        else:
            logger.warning(
                "SPY data unavailable — using previous regime: %s",
                self._current_regime.value,
            )
            new_regime = self._current_regime

        old_regime = self._current_regime
        self._current_regime = new_regime

        if old_regime != new_regime:
            await self._event_bus.publish(
                RegimeChangeEvent(
                    old_regime=old_regime.value,
                    new_regime=new_regime.value,
                    indicators=self._indicators_to_dict(),
                )
            )

        # 3. Get account equity for allocation calculation
        account = await self._broker.get_account()
        total_equity = account.equity if account else 100000.0  # fallback

        # 4. Calculate allocations
        allocations = await self._calculate_allocations(total_equity)
        self._current_allocations = {a.strategy_id: a for a in allocations}

        # 5. Apply allocations
        for alloc in allocations:
            strategy = self._strategies.get(alloc.strategy_id)
            if strategy is None:
                continue

            strategy.allocated_capital = alloc.allocation_dollars
            was_active = strategy.is_active
            strategy.is_active = alloc.eligible and alloc.throttle_action != ThrottleAction.SUSPEND

            # Publish events
            await self._event_bus.publish(
                AllocationUpdateEvent(
                    strategy_id=alloc.strategy_id,
                    new_allocation_pct=alloc.allocation_pct,
                    reason=alloc.reason,
                )
            )

            if strategy.is_active and not was_active:
                await self._event_bus.publish(
                    StrategyActivatedEvent(
                        strategy_id=alloc.strategy_id,
                        reason=alloc.reason,
                    )
                )
            elif not strategy.is_active and was_active:
                await self._event_bus.publish(
                    StrategySuspendedEvent(
                        strategy_id=alloc.strategy_id,
                        reason=alloc.reason,
                    )
                )

        # 6. Log decisions
        await self._log_decisions(allocations, new_regime)

        self._pre_market_done_today = True
        self._last_regime_check = self._clock.now()
        logger.info("Pre-market routine complete. Regime: %s", new_regime.value)

    async def _calculate_allocations(self, total_equity: float) -> list[StrategyAllocation]:
        """Calculate per-strategy allocations. Equal weight V1.

        Args:
            total_equity: Total account equity.

        Returns:
            List of StrategyAllocation for each registered strategy.
        """
        allocations: list[StrategyAllocation] = []
        deployable = total_equity * (1.0 - self._config.cash_reserve_pct)

        # Step 1: Filter by regime
        eligible_ids: list[str] = []
        for sid, strategy in self._strategies.items():
            mcf = strategy.get_market_conditions_filter()
            if self._current_regime.value in mcf.allowed_regimes:
                eligible_ids.append(sid)

        # Step 2: Check throttling for eligible strategies
        throttle_results: dict[str, ThrottleAction] = {}
        for sid in eligible_ids:
            trades = await self._trade_logger.get_trades_by_strategy(sid, limit=200)
            daily_pnl = await self._trade_logger.get_daily_pnl(strategy_id=sid)
            throttle_results[sid] = self._throttler.check(sid, trades, daily_pnl)

        active_ids = [
            sid for sid in eligible_ids if throttle_results[sid] != ThrottleAction.SUSPEND
        ]
        # Note: throttled_ids are those with REDUCE action (used for min allocation)
        # Unused variable removed to satisfy linter

        # Step 3: Equal weight allocation
        n_active = len(active_ids)
        if n_active == 0:
            # All suspended or ineligible — give each strategy 0
            for sid in self._strategies:
                allocations.append(
                    StrategyAllocation(
                        strategy_id=sid,
                        allocation_pct=0.0,
                        allocation_dollars=0.0,
                        throttle_action=throttle_results.get(sid, ThrottleAction.NONE),
                        eligible=sid in eligible_ids,
                        reason="No eligible active strategies",
                    )
                )
            return allocations

        base_pct = min(1.0 / n_active, self._config.max_allocation_pct)
        min_pct = self._config.min_allocation_pct

        for sid in self._strategies:
            if sid not in eligible_ids:
                allocations.append(
                    StrategyAllocation(
                        strategy_id=sid,
                        allocation_pct=0.0,
                        allocation_dollars=0.0,
                        throttle_action=ThrottleAction.NONE,
                        eligible=False,
                        reason=f"Regime {self._current_regime.value} not in allowed_regimes",
                    )
                )
            elif throttle_results[sid] == ThrottleAction.SUSPEND:
                allocations.append(
                    StrategyAllocation(
                        strategy_id=sid,
                        allocation_pct=0.0,
                        allocation_dollars=0.0,
                        throttle_action=ThrottleAction.SUSPEND,
                        eligible=True,
                        reason="Suspended: performance threshold breached",
                    )
                )
            elif throttle_results[sid] == ThrottleAction.REDUCE:
                pct = min_pct
                allocations.append(
                    StrategyAllocation(
                        strategy_id=sid,
                        allocation_pct=pct,
                        allocation_dollars=deployable * pct,
                        throttle_action=ThrottleAction.REDUCE,
                        eligible=True,
                        reason=f"Throttled to minimum ({pct:.0%}): consecutive losses",
                    )
                )
            else:
                pct = base_pct
                allocations.append(
                    StrategyAllocation(
                        strategy_id=sid,
                        allocation_pct=pct,
                        allocation_dollars=deployable * pct,
                        throttle_action=ThrottleAction.NONE,
                        eligible=True,
                        reason=f"Active: {pct:.0%} allocation",
                    )
                )

        return allocations

    # -------------------------------------------------------------------------
    # Manual Controls
    # -------------------------------------------------------------------------

    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        """Re-run allocation with current state. API-triggered.

        Returns:
            Current allocations after rebalance.
        """
        account = await self._broker.get_account()
        total_equity = account.equity if account else 100000.0

        allocations = await self._calculate_allocations(total_equity)

        # Apply allocations
        for alloc in allocations:
            strategy = self._strategies.get(alloc.strategy_id)
            if strategy:
                strategy.allocated_capital = alloc.allocation_dollars
                strategy.is_active = (
                    alloc.eligible and alloc.throttle_action != ThrottleAction.SUSPEND
                )

        self._current_allocations = {a.strategy_id: a for a in allocations}
        logger.info("Manual rebalance completed")
        return self._current_allocations

    # -------------------------------------------------------------------------
    # Intraday Event Handlers
    # -------------------------------------------------------------------------

    async def _on_position_closed(self, event: PositionClosedEvent) -> None:
        """Track intraday losses for throttle checks.

        Args:
            event: The position closed event.
        """
        sid = event.strategy_id
        if not sid:
            # No strategy_id in event — skip tracking
            return

        pnl = event.realized_pnl

        if sid not in self._intraday_losses:
            self._intraday_losses[sid] = []
        self._intraday_losses[sid].append(pnl)

        # Check consecutive losses intraday
        recent_losses = self._intraday_losses[sid]
        consecutive = 0
        for p in reversed(recent_losses):
            if p < 0:
                consecutive += 1
            else:
                break

        if consecutive >= self._config.consecutive_loss_throttle:
            strategy = self._strategies.get(sid)
            if strategy and strategy.is_active:
                strategy.is_active = False
                await self._event_bus.publish(
                    StrategySuspendedEvent(
                        strategy_id=sid,
                        reason=f"Intraday throttle: {consecutive} consecutive losses",
                    )
                )
                logger.warning(
                    "Strategy %s suspended intraday: %d consecutive losses",
                    sid,
                    consecutive,
                )

    # -------------------------------------------------------------------------
    # Poll Loop
    # -------------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Background task for time-based triggers."""
        et_tz = ZoneInfo("America/New_York")

        while self._running:
            await asyncio.sleep(self._config.poll_interval_seconds)

            now = self._clock.now()
            now_et = now.astimezone(et_tz)
            today_str = now_et.strftime("%Y-%m-%d")

            # Reset daily flags at midnight
            if self._last_date is not None and self._last_date != today_str:
                self._pre_market_done_today = False
                self._eod_done_today = False
                self._intraday_losses.clear()
            self._last_date = today_str

            # Pre-market trigger
            pre_market_time = datetime.strptime(
                self._config.pre_market_time, "%H:%M"
            ).time()
            if not self._pre_market_done_today and now_et.time() >= pre_market_time:
                try:
                    await self.run_pre_market()
                except Exception:
                    logger.exception("Pre-market routine failed")

            # Intraday regime re-check
            if (
                self._config.regime_check_interval_minutes
                and self._pre_market_done_today
                and self._last_regime_check
            ):
                elapsed = (now - self._last_regime_check).total_seconds() / 60
                market_open = time(9, 30)
                market_close = time(16, 0)
                if (
                    market_open <= now_et.time() <= market_close
                    and elapsed >= self._config.regime_check_interval_minutes
                ):
                        try:
                            await self._run_regime_recheck()
                        except Exception:
                            logger.exception("Regime re-check failed")

            # EOD review trigger
            eod_time = datetime.strptime(self._config.eod_review_time, "%H:%M").time()
            if not self._eod_done_today and now_et.time() >= eod_time:
                try:
                    await self.run_end_of_day()
                except Exception:
                    logger.exception("EOD review failed")

    async def _run_regime_recheck(self) -> None:
        """Re-evaluate regime during market hours."""
        spy_bars = await self._data_service.fetch_daily_bars(self._config.spy_symbol, 60)
        if spy_bars is None or len(spy_bars) < 20:
            return

        indicators = self._regime_classifier.compute_indicators(spy_bars)
        new_regime = self._regime_classifier.classify(indicators)
        self._current_indicators = indicators
        self._last_regime_check = self._clock.now()

        if new_regime != self._current_regime:
            old = self._current_regime
            self._current_regime = new_regime
            logger.info("Regime changed intraday: %s → %s", old.value, new_regime.value)

            await self._event_bus.publish(
                RegimeChangeEvent(
                    old_regime=old.value,
                    new_regime=new_regime.value,
                    indicators=self._indicators_to_dict(),
                )
            )

            # Re-evaluate strategy eligibility
            for sid, strategy in self._strategies.items():
                if not strategy.is_active:
                    continue
                mcf = strategy.get_market_conditions_filter()
                if new_regime.value not in mcf.allowed_regimes:
                    strategy.is_active = False
                    await self._event_bus.publish(
                        StrategySuspendedEvent(
                            strategy_id=sid,
                            reason=f"Regime changed to {new_regime.value} — not in allowed regimes",
                        )
                    )

    # -------------------------------------------------------------------------
    # End of Day
    # -------------------------------------------------------------------------

    async def run_end_of_day(self) -> None:
        """Post-close review."""
        logger.info("Running end-of-day review")

        # Record daily P&L per strategy to correlation tracker
        today = self._clock.today()
        for sid in self._strategies:
            trades = await self._trade_logger.get_trades_by_date(today, strategy_id=sid)
            today_pnl = sum(t.net_pnl for t in trades if t.net_pnl is not None)
            self._correlation_tracker.record_daily_pnl(sid, today.isoformat(), today_pnl)

        # Log EOD summary
        await self._log_decision(
            "eod_review",
            None,
            {"regime": self._current_regime.value},
            "End of day review",
        )

        self._eod_done_today = True
        logger.info("EOD review complete")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _indicators_to_dict(self) -> dict[str, float]:
        """Convert RegimeIndicators to dict for event payload.

        Returns:
            Dict with indicator values.
        """
        if self._current_indicators is None:
            return {}
        return {
            "spy_price": self._current_indicators.spy_price,
            "spy_sma_20": self._current_indicators.spy_sma_20 or 0.0,
            "spy_sma_50": self._current_indicators.spy_sma_50 or 0.0,
            "spy_roc_5d": self._current_indicators.spy_roc_5d or 0.0,
            "spy_realized_vol_20d": self._current_indicators.spy_realized_vol_20d or 0.0,
        }

    async def _log_decision(
        self,
        decision_type: str,
        strategy_id: str | None,
        details: dict,
        rationale: str,
    ) -> None:
        """Log an orchestrator decision to the database.

        Args:
            decision_type: Type of decision (allocation, activation, etc.).
            strategy_id: Strategy ID if applicable.
            details: Dict with decision details.
            rationale: Human-readable explanation.
        """
        today = self._clock.today().isoformat()
        await self._trade_logger.log_orchestrator_decision(
            date=today,
            decision_type=decision_type,
            strategy_id=strategy_id,
            details=details,
            rationale=rationale,
        )

    async def _log_decisions(
        self, allocations: list[StrategyAllocation], regime: MarketRegime
    ) -> None:
        """Log all pre-market decisions.

        Args:
            allocations: List of strategy allocations.
            regime: Current market regime.
        """
        for alloc in allocations:
            decision_type = "allocation" if alloc.eligible else "exclusion"
            await self._log_decision(
                decision_type=decision_type,
                strategy_id=alloc.strategy_id,
                details={
                    "allocation_pct": alloc.allocation_pct,
                    "allocation_dollars": alloc.allocation_dollars,
                    "throttle_action": alloc.throttle_action.value,
                    "eligible": alloc.eligible,
                    "regime": regime.value,
                },
                rationale=alloc.reason,
            )

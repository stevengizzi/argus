"""Risk Manager — gating layer for all trade signals.

Every SignalEvent must pass through ``RiskManager.evaluate_signal()`` before
reaching the broker. No exceptions. No shortcuts.

The manager runs a fixed-order chain of defensive guards grouped into four
bands. Each guard either rejects or accepts; two bands (concentration, cash
reserve, buying power) can also approve-with-modification by reducing the
share count.

Band A — Defensive guard (Sprint 24):
    0. Defensive share-count guard (``share_count <= 0`` → reject).

Band B — Account-level:
    1. Circuit breaker (rejects while ``_circuit_breaker_active``).
    2. Daily loss limit (``_daily_realized_pnl`` vs config).
    3. Weekly loss limit (``_weekly_realized_pnl`` vs config).
    4. Max concurrent positions (broker position count vs config).

Band C — Cross-strategy (Sprint 17+):
    5. Single-stock concentration (DEC-249; approve-with-modification).
    6. Duplicate stock policy (DEC-121/160; hard reject).

Band D — Capital:
    7. Cash reserve (DEC-037; approve-with-modification).
    8. Buying power (approve-with-modification).
    9. PDT compliance (margin accounts below the FINRA threshold).

Reductions under the approve-with-modification bands cascade: concentration
can trim first, then cash reserve, then buying power. At each reduction step
the post-reduction position risk is checked against
``min_position_risk_dollars`` (DEC-249/DEC-250, default $100) — reductions
below that floor are rejected rather than silently accepted.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from argus.core.clock import Clock, SystemClock
from argus.core.config import DuplicateStockPolicy, RiskConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    CircuitBreakerLevel,
    OrderApprovedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    SignalEvent,
)
from argus.execution.broker import Broker
from argus.utils.log_throttle import ThrottledLogger

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.execution.order_manager import OrderManager

logger = logging.getLogger(__name__)
_throttled = ThrottledLogger(logger)


# ---------------------------------------------------------------------------
# Supporting Data Structures
# ---------------------------------------------------------------------------


@dataclass
class PDTTracker:
    """Tracks Pattern Day Trading rule compliance.

    Maintains a rolling window of day trade timestamps. A day trade is
    any round-trip (buy + sell) in the same stock on the same day.

    Attributes:
        day_trades: Deque of dates when day trades occurred.
        account_type: "margin" or "cash".
        threshold_balance: FINRA PDT threshold (default $25,000).
    """

    day_trades: deque[date] = field(default_factory=deque)
    account_type: str = "margin"
    threshold_balance: float = 25000.0

    def record_day_trade(self, trade_date: date) -> None:
        """Record a day trade on the given date."""
        self.day_trades.append(trade_date)
        self._prune(trade_date)

    def day_trades_remaining(self, current_date: date, account_equity: float) -> int:
        """Return how many day trades are available.

        Args:
            current_date: Today's date.
            account_equity: Current account equity.

        Returns:
            Number of day trades remaining. Returns 999 if PDT doesn't apply
            (cash account or equity >= threshold).
        """
        if self.account_type == "cash":
            return 999  # PDT doesn't apply to cash accounts
        if account_equity >= self.threshold_balance:
            return 999  # Above threshold, unlimited day trades

        self._prune(current_date)
        used = len(self.day_trades)
        return max(0, 3 - used)

    def _prune(self, current_date: date) -> None:
        """Remove day trades older than 5 business days."""
        cutoff = self._business_days_ago(current_date, 5)
        while self.day_trades and self.day_trades[0] < cutoff:
            self.day_trades.popleft()

    @staticmethod
    def _business_days_ago(from_date: date, n: int) -> date:
        """Calculate the date N business days before from_date."""
        current = from_date
        days_counted = 0
        while days_counted < n:
            current -= timedelta(days=1)
            if current.weekday() < 5:  # Monday=0, Friday=4
                days_counted += 1
        return current


@dataclass
class IntegrityReport:
    """Result of a daily integrity check.

    Attributes:
        timestamp: When the check was performed.
        positions_checked: Number of positions verified.
        issues: List of issue descriptions. Empty if all checks pass.
        passed: Whether all checks passed.
    """

    timestamp: datetime
    positions_checked: int
    issues: list[str]
    passed: bool


# ---------------------------------------------------------------------------
# Risk Manager
# ---------------------------------------------------------------------------


class RiskManager:
    """Gating layer for all trade signals.

    Every signal must pass through ``evaluate_signal()`` before reaching the
    broker. The manager can approve (with or without modifications), reject
    a signal outright, or — in the post-close and evaluate-time paths —
    trigger the account-level circuit breaker.

    Full guard chain (see module docstring for band-level grouping):

    0. Defensive share-count guard (Sprint 24).
    1. Circuit breaker active (rejects while set).
    2. Daily loss limit.
    3. Weekly loss limit.
    4. Max concurrent positions (account-level).
    5. Single-stock concentration (approve-with-modification, DEC-249).
    6. Duplicate stock policy (hard reject, DEC-121/160).
    7. Cash reserve (approve-with-modification, DEC-037).
    8. Buying power (approve-with-modification).
    9. PDT compliance (margin accounts below the FINRA threshold).

    Public surface:
    - ``evaluate_signal(signal)`` — the hot-path gate.
    - ``daily_integrity_check()`` — diagnostic pass at daily boundaries.
    - ``reset_daily_state()`` / ``reconstruct_state()`` — lifecycle hooks.
    - ``set_order_manager()`` — post-construction wiring.

    Args:
        config: Risk configuration.
        broker: Broker for account state queries.
        event_bus: EventBus for publishing circuit breaker events.
        clock: Clock for time access. Defaults to SystemClock() if not provided.
        order_manager: Optional OrderManager for cross-strategy exposure checks.
    """

    def __init__(
        self,
        config: RiskConfig,
        broker: Broker,
        event_bus: EventBus,
        clock: Clock | None = None,
        order_manager: OrderManager | None = None,
    ) -> None:
        self._config = config
        self._broker = broker
        self._event_bus = event_bus
        self._clock: Clock = clock if clock is not None else SystemClock()
        self._order_manager: OrderManager | None = order_manager

        # Daily/weekly tracking (updated via PositionClosedEvent)
        self._daily_realized_pnl: float = 0.0
        self._weekly_realized_pnl: float = 0.0
        self._current_week_start: date = self._get_monday(self._clock.today())
        self._trades_today: int = 0

        # Start-of-day equity for cash reserve calculations (DEC-037)
        # Snapshotted in reset_daily_state() or reconstruct_state()
        # If 0.0, falls back to live equity for safety
        self._start_of_day_equity: float = 0.0

        # Circuit breaker state
        self._circuit_breaker_active: bool = False

        # PDT tracking
        self._pdt_tracker = PDTTracker(
            account_type=self._config.pdt.account_type.value,
            threshold_balance=self._config.pdt.threshold_balance,
        )

    @staticmethod
    def _get_monday(d: date) -> date:
        """Return the Monday of the week containing date d."""
        return d - timedelta(days=d.weekday())

    async def initialize(self) -> None:
        """Initialize the Risk Manager.

        Subscribes to PositionClosedEvent on the EventBus to track realized P&L.
        Must be called after EventBus is available.
        """
        self._event_bus.subscribe(PositionClosedEvent, self._on_position_closed)
        max_pos = self._config.account.max_concurrent_positions
        logger.info(
            "Risk Manager initialized. Config: daily_limit=%.1f%%, weekly_limit=%.1f%%, "
            "cross-strategy concurrent position limit: %s",
            self._config.account.daily_loss_limit_pct * 100,
            self._config.account.weekly_loss_limit_pct * 100,
            str(max_pos) if max_pos > 0 else "disabled",
        )

    async def evaluate_signal(self, signal: SignalEvent) -> OrderApprovedEvent | OrderRejectedEvent:
        """Evaluate a trade signal against the full risk-guard chain.

        Checks run in order (fail-fast). The numbering matches the module /
        class docstring bands (A: defensive; B: account; C: cross-strategy;
        D: capital).

        0. Defensive share-count guard (``share_count <= 0``) → reject.
        1. Circuit breaker active? → reject.
        2. Daily loss limit breached? → reject.
        3. Weekly loss limit breached? → reject.
        4. Max concurrent positions exceeded? → reject.
        5. Single-stock concentration (DEC-249) → modify share count or reject.
        6. Duplicate stock policy (DEC-121/160) → hard reject if non-ALLOW_ALL.
        7. Cash reserve enforcement → modify share count or reject.
        8. Buying power check → modify share count or reject.
        9. PDT compliance (margin accounts under threshold) → reject.

        Steps 5, 7, and 8 can each reduce share count (approve-with-modification).
        Reductions cascade: concentration may reduce first, then cash reserve
        or buying power may reduce further. All reduction reasons are
        accumulated and reported. At each stage, the minimum risk floor is
        checked — if reduced position's total risk <
        ``min_position_risk_dollars`` (default $100), reject as not worth taking.

        Args:
            signal: The SignalEvent to evaluate.

        Returns:
            OrderApprovedEvent (possibly with modifications) or OrderRejectedEvent.
        """
        # Check 0: Defensive guard against zero share count (Sprint 24)
        if signal.share_count <= 0:
            logger.warning(
                "Signal rejected: share_count=%d (zero or negative)", signal.share_count
            )
            return OrderRejectedEvent(
                signal=signal, reason="Invalid share count: zero or negative"
            )

        # 1. Circuit breaker check
        if self._circuit_breaker_active:
            logger.warning(
                "Signal rejected: circuit breaker active (strategy=%s, symbol=%s)",
                signal.strategy_id,
                signal.symbol,
            )
            return OrderRejectedEvent(
                signal=signal,
                reason="Circuit breaker active — all trading halted for the day",
            )

        # Get account state
        account = await self._broker.get_account()

        # 2. Daily loss limit check
        daily_limit = account.equity * self._config.account.daily_loss_limit_pct
        if self._daily_realized_pnl < 0 and abs(self._daily_realized_pnl) >= daily_limit:
            # Trigger circuit breaker
            self._circuit_breaker_active = True
            await self._event_bus.publish(
                CircuitBreakerEvent(
                    level=CircuitBreakerLevel.ACCOUNT,
                    reason=f"Daily loss limit reached: ${self._daily_realized_pnl:.2f}",
                    strategies_affected=(signal.strategy_id,),
                )
            )
            logger.critical(
                "CIRCUIT BREAKER TRIGGERED: Daily loss $%.2f exceeds limit $%.2f",
                abs(self._daily_realized_pnl),
                daily_limit,
            )
            reason = (
                f"Daily loss limit reached ({self._daily_realized_pnl:.2f} of {daily_limit:.2f})"
            )
            return OrderRejectedEvent(signal=signal, reason=reason)

        # 3. Weekly loss limit check
        weekly_limit = account.equity * self._config.account.weekly_loss_limit_pct
        if self._weekly_realized_pnl < 0 and abs(self._weekly_realized_pnl) >= weekly_limit:
            _throttled.warn_throttled(
                "weekly_loss_limit",
                f"Signal rejected: weekly loss limit reached "
                f"(pnl={self._weekly_realized_pnl:.2f}, limit={weekly_limit:.2f})",
                interval_seconds=60.0,
            )
            return OrderRejectedEvent(
                signal=signal,
                reason="Weekly loss limit reached",
            )

        # 4. Max concurrent positions check (0 = disabled)
        positions = await self._broker.get_positions()
        max_pos = self._config.account.max_concurrent_positions
        if max_pos > 0 and len(positions) >= max_pos:
            logger.warning(
                "Signal rejected: max concurrent positions (%d) reached",
                max_pos,
            )
            return OrderRejectedEvent(
                signal=signal,
                reason=f"Max concurrent positions ({max_pos}) reached",
            )

        # 5. Single-stock concentration limit (DEC-121, DEC-249)
        # This can reduce shares (approve-with-modification), unlike duplicate policy.
        max_conc_shares = self._get_concentration_limit_shares(signal, account.equity)
        modified_shares: int | None = None
        modification_reasons: list[str] = []

        if max_conc_shares is not None and signal.share_count > max_conc_shares:
            if max_conc_shares <= 0:
                max_exp = account.equity * self._config.cross_strategy.max_single_stock_pct
                logger.warning(
                    "Signal rejected: concentration limit already reached for %s (max $%.2f)",
                    signal.symbol,
                    max_exp,
                )
                return OrderRejectedEvent(
                    signal=signal,
                    reason=f"Concentration limit already reached for {signal.symbol}",
                )
            # Reduce shares to fit concentration limit
            if self._below_min_risk_floor(max_conc_shares, signal):
                max_pct = self._config.cross_strategy.max_single_stock_pct * 100
                min_risk = self._config.account.min_position_risk_dollars
                risk_per_share = abs(signal.entry_price - signal.stop_price)
                reduced_risk = max_conc_shares * risk_per_share
                _throttled.warn_throttled(
                    "concentration_floor",
                    f"Signal rejected: concentration-reduced shares ({max_conc_shares}) "
                    f"risk ${reduced_risk:.2f} below ${min_risk:.0f} floor",
                )
                return OrderRejectedEvent(
                    signal=signal,
                    reason=(
                        f"Position reduced for {max_pct:.0f}% concentration limit "
                        f"would risk ${reduced_risk:.2f} — below ${min_risk:.0f} minimum"
                    ),
                )
            modified_shares = max_conc_shares
            modification_reasons.append("concentration limit")
            logger.info(
                "Signal %s %s: shares reduced from %d to %d for concentration limit",
                signal.symbol,
                signal.strategy_id,
                signal.share_count,
                max_conc_shares,
            )

        # 6. Duplicate stock policy check (DEC-121, DEC-124)
        # This is a hard reject — reducing shares won't help.
        dup_reason = await self._check_duplicate_stock_policy(signal)
        if dup_reason:
            logger.warning(
                "Signal rejected: duplicate stock policy (%s %s) - %s",
                signal.strategy_id,
                signal.symbol,
                dup_reason,
            )
            return OrderRejectedEvent(signal=signal, reason=dup_reason)

        # 7. Cash reserve enforcement (DEC-037: use start-of-day equity)
        # Fall back to live equity if start-of-day equity not yet snapshotted
        equity_for_reserve = (
            self._start_of_day_equity if self._start_of_day_equity > 0 else account.equity
        )
        reserve = equity_for_reserve * self._config.account.cash_reserve_pct
        available = account.cash - reserve
        # Use effective share count (may have been reduced by concentration limit)
        effective_shares = modified_shares if modified_shares is not None else signal.share_count
        cost = signal.entry_price * effective_shares

        if cost > available:
            if available <= 0:
                _throttled.warn_throttled(
                    "cash_reserve_violated",
                    f"Signal rejected: cash reserve would be violated (available={available:.2f})",
                )
                return OrderRejectedEvent(
                    signal=signal,
                    reason="Cash reserve would be violated",
                )
            # Calculate reduced shares
            reduced = int(available / signal.entry_price)
            if self._below_min_risk_floor(reduced, signal):
                min_risk = self._config.account.min_position_risk_dollars
                risk_per_share = abs(signal.entry_price - signal.stop_price)
                reduced_risk = reduced * risk_per_share
                _throttled.warn_throttled(
                    "cashreserve_floor",
                    f"Signal rejected: cash-reserve-reduced shares ({reduced}) "
                    f"risk ${reduced_risk:.2f} below ${min_risk:.0f} floor",
                )
                return OrderRejectedEvent(
                    signal=signal,
                    reason=f"Position reduced for cash reserve would risk ${reduced_risk:.2f} — below ${min_risk:.0f} minimum",
                )
            modified_shares = reduced
            modification_reasons.append("cash reserve constraint")

        # 8. Buying power check (recalculate cost with effective shares)
        effective_shares = modified_shares if modified_shares is not None else signal.share_count
        cost = signal.entry_price * effective_shares
        if cost > account.buying_power:
            reduced = int(account.buying_power / signal.entry_price)
            if self._below_min_risk_floor(reduced, signal):
                min_risk = self._config.account.min_position_risk_dollars
                risk_per_share = abs(signal.entry_price - signal.stop_price)
                reduced_risk = reduced * risk_per_share
                logger.warning(
                    "Signal rejected: buying-power-reduced shares (%d) risk $%.2f below $%.0f floor",
                    reduced,
                    reduced_risk,
                    min_risk,
                )
                return OrderRejectedEvent(
                    signal=signal,
                    reason=f"Position reduced for buying power would risk ${reduced_risk:.2f} — below ${min_risk:.0f} minimum",
                )
            modified_shares = reduced
            modification_reasons.append("buying power constraint")

        # 9. PDT check
        if self._config.pdt.enabled:
            remaining = self._pdt_tracker.day_trades_remaining(self._clock.today(), account.equity)
            if remaining <= 0:
                logger.warning("Signal rejected: PDT limit reached")
                return OrderRejectedEvent(
                    signal=signal,
                    reason="PDT limit reached — no day trades remaining in rolling 5-day window",
                )

        # Approve (with or without modifications)
        if modified_shares is not None:
            combined_reason = " + ".join(modification_reasons)
            logger.info(
                "Signal approved with modification: %s %s shares reduced from %d to %d (%s)",
                signal.symbol,
                signal.strategy_id,
                signal.share_count,
                modified_shares,
                combined_reason,
            )
            mod_reason = (
                f"Reduced from {signal.share_count} to {modified_shares} "
                f"shares — {combined_reason}"
            )
            return OrderApprovedEvent(
                signal=signal,
                modifications={"share_count": modified_shares, "reason": mod_reason},
            )

        logger.info(
            "Signal approved: %s %s %d shares @ %.2f",
            signal.strategy_id,
            signal.symbol,
            signal.share_count,
            signal.entry_price,
        )
        return OrderApprovedEvent(signal=signal, modifications=None)

    def _below_min_risk_floor(self, reduced_shares: int, signal: SignalEvent) -> bool:
        """Check if reduced position is below the minimum risk dollar floor.

        Positions with total risk below min_position_risk_dollars are rejected
        as "not worth taking" — e.g., $100 default floor.

        This replaces the ratio-based 0.25R floor (DEC-250) which incorrectly
        compared against uncapped position size, causing valid signals to be
        rejected when concentration limits reduced share counts significantly.

        Args:
            reduced_shares: Proposed reduced share count.
            signal: The original signal.

        Returns:
            True if below floor (should reject), False if acceptable.
        """
        if reduced_shares <= 0:
            return True

        risk_per_share = abs(signal.entry_price - signal.stop_price)
        reduced_risk = reduced_shares * risk_per_share

        return reduced_risk < self._config.account.min_position_risk_dollars

    def _get_concentration_limit_shares(
        self, signal: SignalEvent, equity: float
    ) -> int | None:
        """Calculate max shares allowed by single-stock concentration limit.

        Returns the maximum number of shares that would keep the position within
        the concentration limit (max_single_stock_pct of equity), accounting for
        any existing positions in the same symbol.

        Args:
            signal: The trade signal to evaluate.
            equity: Current account equity.

        Returns:
            Max allowable shares (may be less than signal.share_count), or
            None if Order Manager is unavailable (skip check).
        """
        if self._order_manager is None:
            return None

        cross_config = self._config.cross_strategy

        # Get existing exposure for this symbol
        managed = self._order_manager.get_managed_positions()
        existing_exposure = 0.0

        positions_for_symbol = managed.get(signal.symbol, [])
        for pos in positions_for_symbol:
            if not pos.is_fully_closed:
                existing_exposure += pos.entry_price * pos.shares_remaining

        # Include pending (unfilled) entry orders to prevent race conditions
        pending_exposure = self._order_manager.get_pending_entry_exposure(signal.symbol)
        existing_exposure += pending_exposure

        # Calculate remaining capacity
        max_exposure = equity * cross_config.max_single_stock_pct
        remaining_capacity = max_exposure - existing_exposure

        if remaining_capacity <= 0:
            return 0

        # Max shares we can add
        max_shares = int(remaining_capacity / signal.entry_price)
        return max_shares

    async def _check_duplicate_stock_policy(
        self, signal: SignalEvent
    ) -> str | None:
        """Check duplicate stock policy (hard reject if violated).

        Verifies that the new position wouldn't violate the duplicate stock
        policy (if not ALLOW_ALL). This is a hard reject — cannot be fixed
        by reducing share count.

        Args:
            signal: The trade signal to evaluate.

        Returns:
            Rejection reason string if policy violated, None if acceptable.
        """
        if self._order_manager is None:
            return None

        cross_config = self._config.cross_strategy
        policy = cross_config.duplicate_stock_policy

        if policy == DuplicateStockPolicy.ALLOW_ALL:
            return None

        # Get managed positions for this symbol
        managed = self._order_manager.get_managed_positions()
        positions_for_symbol = managed.get(signal.symbol, [])

        # Check if another strategy already holds this symbol
        for pos in positions_for_symbol:
            if pos.strategy_id != signal.strategy_id and not pos.is_fully_closed:
                # Another strategy holds this symbol
                if policy == DuplicateStockPolicy.BLOCK_ALL:
                    return (
                        f"Duplicate stock blocked: {pos.strategy_id} already holds "
                        f"{signal.symbol} (policy: BLOCK_ALL)"
                    )
                elif policy == DuplicateStockPolicy.FIRST_SIGNAL:
                    return (
                        f"Duplicate stock blocked: {pos.strategy_id} already holds "
                        f"{signal.symbol} (policy: FIRST_SIGNAL)"
                    )
                elif policy == DuplicateStockPolicy.PRIORITY_BY_WIN_RATE:
                    # V1 simplified: reject without win rate comparison.
                    # Full implementation requires win rate data from
                    # TradeLogger. Logged at DEBUG (was WARNING) per
                    # Apr 21 debrief F-08 / IMPROMPTU-07, 2026-04-23 —
                    # this known-unfinished-feature notification fired
                    # 100+ times per session at WARNING level, drowning
                    # genuine operational alerts.
                    logger.debug(
                        "PRIORITY_BY_WIN_RATE is not fully implemented — rejecting %s for %s "
                        "(V1 simplified: always rejects duplicates)",
                        signal.symbol,
                        signal.strategy_id,
                    )
                    return (
                        f"Duplicate stock blocked: {pos.strategy_id} already holds "
                        f"{signal.symbol} (policy: PRIORITY_BY_WIN_RATE, V1 simplified)"
                    )

        return None

    async def _on_position_closed(self, event: PositionClosedEvent) -> None:
        """Track realized P&L and PDT day trades from position close events.

        Args:
            event: The PositionClosedEvent from the EventBus.
        """
        self._daily_realized_pnl += event.realized_pnl
        self._weekly_realized_pnl += event.realized_pnl
        self._trades_today += 1

        # Check if this was a day trade (opened and closed same day)
        if event.entry_time and event.exit_time:
            entry_date = (
                event.entry_time.date()
                if isinstance(event.entry_time, datetime)
                else event.entry_time
            )
            exit_date = (
                event.exit_time.date() if isinstance(event.exit_time, datetime) else event.exit_time
            )
            if entry_date == exit_date:
                self._pdt_tracker.record_day_trade(exit_date)
                logger.debug("Day trade recorded for %s", exit_date)

        # Check if daily loss limit is now breached
        await self._check_circuit_breaker_after_close()

    async def _check_circuit_breaker_after_close(self) -> None:
        """Check if daily loss limit is breached after a position closes."""
        if self._circuit_breaker_active:
            return  # Already triggered

        account = await self._broker.get_account()
        daily_limit = account.equity * self._config.account.daily_loss_limit_pct

        if self._daily_realized_pnl < 0 and abs(self._daily_realized_pnl) >= daily_limit:
            self._circuit_breaker_active = True
            event = CircuitBreakerEvent(
                level=CircuitBreakerLevel.ACCOUNT,
                reason=f"Daily loss limit reached: ${self._daily_realized_pnl:.2f}",
                strategies_affected=(),  # Affects all strategies
            )
            await self._event_bus.publish(event)
            logger.critical(
                "CIRCUIT BREAKER TRIGGERED: Daily loss $%.2f exceeds limit $%.2f",
                abs(self._daily_realized_pnl),
                daily_limit,
            )

    async def reset_daily_state(self) -> None:
        """Reset daily state at the start of each trading day.

        Called by the Orchestrator before market open. Clears daily P&L,
        trade count, and circuit breaker flag. Weekly P&L rolls over
        on Monday. Snapshots start-of-day equity for cash reserve calculations.
        """
        self._daily_realized_pnl = 0.0
        self._trades_today = 0
        self._circuit_breaker_active = False

        # Snapshot start-of-day equity (DEC-037)
        account = await self._broker.get_account()
        self._start_of_day_equity = account.equity
        logger.info("Start-of-day equity snapshotted: $%.2f", self._start_of_day_equity)

        # Check for week rollover (Monday)
        today = self._clock.today()
        monday = self._get_monday(today)
        if monday != self._current_week_start:
            self._weekly_realized_pnl = 0.0
            self._current_week_start = monday
            logger.info("Weekly P&L reset (new week starting %s)", monday)

        logger.info("Risk Manager daily state reset")

    async def reconstruct_state(self, trade_logger: TradeLogger) -> None:
        """Reconstruct intraday state from the database after a mid-day restart.

        Queries today's closed trades from the TradeLogger to rebuild:
        - Daily realized P&L
        - Weekly realized P&L
        - PDT day trade count
        - Trade count
        - Start-of-day equity snapshot

        Args:
            trade_logger: The TradeLogger instance for database queries.
        """
        today = self._clock.today()
        trades_today = await trade_logger.get_trades_by_date(today)

        self._daily_realized_pnl = sum(t.net_pnl for t in trades_today if t.net_pnl is not None)
        self._trades_today = len(trades_today)

        # Reconstruct weekly P&L from Monday through today
        monday = self._get_monday(today)
        self._current_week_start = monday
        weekly_trades = await trade_logger.get_trades_by_date_range(monday, today)
        self._weekly_realized_pnl = sum(t.net_pnl for t in weekly_trades if t.net_pnl is not None)

        # Reconstruct PDT day trades for the rolling 5 business days window
        pdt_cutoff = PDTTracker._business_days_ago(today, 5)
        pdt_trades = await trade_logger.get_trades_by_date_range(pdt_cutoff, today)
        self._pdt_tracker.day_trades.clear()
        for trade in pdt_trades:
            # A day trade is when entry and exit occur on the same day
            entry_date = trade.entry_time.date()
            exit_date = trade.exit_time.date()
            if entry_date == exit_date:
                self._pdt_tracker.record_day_trade(exit_date)

        # Snapshot start-of-day equity (DEC-037)
        # On mid-day restart, use current equity as approximation
        account = await self._broker.get_account()
        self._start_of_day_equity = account.equity

        logger.info(
            "Risk Manager state reconstructed: daily_pnl=$%.2f, weekly_pnl=$%.2f, "
            "trades=%d, pdt_day_trades=%d, start_of_day_equity=$%.2f",
            self._daily_realized_pnl,
            self._weekly_realized_pnl,
            self._trades_today,
            len(self._pdt_tracker.day_trades),
            self._start_of_day_equity,
        )

    async def daily_integrity_check(self) -> IntegrityReport:
        """Verify all open positions have associated stop orders at the broker.

        V1 implementation: verify that the broker reports positions and that
        the system's internal state is consistent with the broker's state.
        Full stop-order verification requires Order Manager (Sprint 4).

        Returns:
            IntegrityReport with check results.
        """
        issues: list[str] = []
        positions = await self._broker.get_positions()

        # Basic checks for V1
        account = await self._broker.get_account()
        if account.equity <= 0:
            issues.append("Account equity is zero or negative")

        return IntegrityReport(
            timestamp=self._clock.now(),
            positions_checked=len(positions),
            issues=issues,
            passed=len(issues) == 0,
        )

    # -------------------------------------------------------------------------
    # Properties (read-only access for testing and monitoring)
    # -------------------------------------------------------------------------

    @property
    def daily_realized_pnl(self) -> float:
        """Current daily realized P&L."""
        return self._daily_realized_pnl

    @property
    def weekly_realized_pnl(self) -> float:
        """Current weekly realized P&L."""
        return self._weekly_realized_pnl

    @property
    def circuit_breaker_active(self) -> bool:
        """Whether the circuit breaker is currently active."""
        return self._circuit_breaker_active

    @property
    def pdt_tracker(self) -> PDTTracker:
        """Access to PDT tracker for monitoring."""
        return self._pdt_tracker

    @property
    def trades_today(self) -> int:
        """Number of trades executed today."""
        return self._trades_today

    @property
    def start_of_day_equity(self) -> float:
        """Start-of-day equity snapshot for cash reserve calculations."""
        return self._start_of_day_equity

    def set_order_manager(self, order_manager: OrderManager) -> None:
        """Set the Order Manager reference for cross-strategy risk checks.

        This setter exists for cases where initialization order prevents
        constructor injection (Risk Manager created before Order Manager).

        Args:
            order_manager: The Order Manager instance.
        """
        self._order_manager = order_manager

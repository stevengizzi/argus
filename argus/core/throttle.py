"""Strategy throttling and allocation types for the Orchestrator.

Defines throttle actions and strategy allocation data structures used
when the Orchestrator adjusts capital distribution across strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argus.core.config import OrchestratorConfig
    from argus.models.trading import Trade


class ThrottleAction(StrEnum):
    """Throttle action applied to a strategy.

    When a strategy underperforms or risk conditions warrant it,
    the Orchestrator can reduce or suspend its allocation.
    """

    NONE = "none"
    REDUCE = "reduce"
    SUSPEND = "suspend"


@dataclass
class StrategyAllocation:
    """Capital allocation for a single strategy.

    Represents the Orchestrator's allocation decision for one strategy,
    including the percentage of capital, dollar amount, any throttle
    action applied, and eligibility status.

    Attributes:
        strategy_id: Unique identifier for the strategy.
        allocation_pct: Percentage of deployable capital allocated (0.0 to 1.0).
        allocation_dollars: Dollar amount allocated to this strategy.
        throttle_action: Current throttle action applied.
        eligible: Whether the strategy is eligible to trade.
        reason: Explanation for the allocation decision.
    """

    strategy_id: str
    allocation_pct: float
    allocation_dollars: float
    throttle_action: ThrottleAction
    eligible: bool
    reason: str


class PerformanceThrottler:
    """Evaluates strategy performance for throttling/suspension decisions.

    Rules (from Bible Section 5.4):
    1. 5 consecutive losses → REDUCE (allocation to minimum)
    2. 20-day rolling Sharpe < 0 → SUSPEND
    3. Drawdown from equity peak > 15% → SUSPEND

    Returns the worst action (SUSPEND > REDUCE > NONE).
    """

    def __init__(self, config: OrchestratorConfig) -> None:
        """Initialize the performance throttler.

        Args:
            config: Orchestrator configuration with throttling thresholds.
        """
        self._config = config

    def check(
        self,
        strategy_id: str,
        trades: list[Trade],
        daily_pnl: list[dict],
    ) -> ThrottleAction:
        """Evaluate a strategy's performance and return throttle action.

        Args:
            strategy_id: Identifier for the strategy being evaluated.
            trades: List of Trade objects, most recent first.
            daily_pnl: Daily P&L data from TradeLogger.get_daily_pnl().
                Expected keys: date, pnl, trades.

        Returns:
            The worst applicable ThrottleAction (SUSPEND > REDUCE > NONE).
        """
        actions: list[ThrottleAction] = []

        # Check consecutive losses → REDUCE
        consecutive_losses = self.get_consecutive_losses(trades)
        if consecutive_losses >= self._config.consecutive_loss_throttle:
            actions.append(ThrottleAction.REDUCE)

        # Check rolling Sharpe → SUSPEND
        rolling_sharpe = self.get_rolling_sharpe(daily_pnl, self._config.performance_lookback_days)
        if rolling_sharpe is not None and rolling_sharpe < self._config.suspension_sharpe_threshold:
            actions.append(ThrottleAction.SUSPEND)

        # Check drawdown → SUSPEND
        drawdown = self.get_drawdown_from_peak(daily_pnl)
        if drawdown > self._config.suspension_drawdown_pct:
            actions.append(ThrottleAction.SUSPEND)

        # Return worst action (SUSPEND > REDUCE > NONE)
        if ThrottleAction.SUSPEND in actions:
            return ThrottleAction.SUSPEND
        if ThrottleAction.REDUCE in actions:
            return ThrottleAction.REDUCE
        return ThrottleAction.NONE

    def get_consecutive_losses(self, trades: list[Trade]) -> int:
        """Count consecutive losses from most recent trade backward.

        A loss is defined as net_pnl < 0. Breakeven (net_pnl == 0) breaks
        the streak.

        Args:
            trades: List of Trade objects, most recent first.

        Returns:
            Number of consecutive losses from the most recent trade.
        """
        if not trades:
            return 0

        count = 0
        for trade in trades:
            if trade.net_pnl < 0:
                count += 1
            else:
                # Win or breakeven breaks the streak
                break

        return count

    def get_rolling_sharpe(self, daily_pnl: list[dict], lookback_days: int) -> float | None:
        """Compute rolling Sharpe ratio from daily P&L data.

        Uses compute_sharpe_ratio() from analytics/performance.py.

        Args:
            daily_pnl: List of dicts with 'date' and 'pnl' keys.
                Expected to be sorted by date descending (most recent first).
            lookback_days: Number of days to include in the calculation.

        Returns:
            Rolling Sharpe ratio, or None if insufficient data (< 5 days).
        """
        from argus.analytics.performance import compute_sharpe_ratio

        if len(daily_pnl) < 5:
            return None

        # Take the most recent lookback_days entries
        # daily_pnl is sorted descending (most recent first), so slice and reverse
        recent_data = daily_pnl[:lookback_days]

        # Extract P&L values in chronological order (oldest first for Sharpe)
        pnl_values = [entry.get("pnl", 0.0) for entry in reversed(recent_data)]

        if len(pnl_values) < 2:
            return None

        return compute_sharpe_ratio(pnl_values)

    def get_drawdown_from_peak(self, daily_pnl: list[dict]) -> float:
        """Compute current drawdown from equity peak as a percentage.

        Equity curve = cumulative sum of daily P&L.
        Drawdown = (peak - current) / peak.

        Args:
            daily_pnl: List of dicts with 'date' and 'pnl' keys.
                Expected to be sorted by date descending (most recent first).

        Returns:
            Current drawdown as a percentage (0.0 to 1.0).
            Returns 0.0 if equity is at or above peak, or if no data.
        """
        if not daily_pnl:
            return 0.0

        # Reverse to chronological order (oldest first)
        chronological_pnl = list(reversed(daily_pnl))

        # Build cumulative equity curve
        cumulative = 0.0
        peak = 0.0
        current = 0.0

        for entry in chronological_pnl:
            cumulative += entry.get("pnl", 0.0)
            current = cumulative
            if cumulative > peak:
                peak = cumulative

        # Calculate drawdown
        if peak <= 0:
            return 0.0

        if current >= peak:
            return 0.0

        return (peak - current) / peak

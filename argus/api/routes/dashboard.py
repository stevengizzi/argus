"""Dashboard aggregate routes for the Command Center API.

Sprint 21d: Provides a single endpoint that returns all Dashboard data in one response.
This eliminates the staggered loading of individual cards by aggregating:
- Account info (equity, cash, buying power, daily P&L)
- Today's stats (trades, win rate, avg R, best trade)
- Monthly goal progress (target, current P&L, pace status)
- Market status (open/closed/pre_market, time)
- Regime classification
- Strategy deployment summary
- Orchestrator status

The Dashboard page makes one query, gets one loading state, and all cards render together.
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.analytics.performance import compute_metrics
from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.api.routes.account import get_market_status
from argus.execution.simulated_broker import SimulatedBroker

router = APIRouter()

ET_TZ = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class AccountSummaryData(BaseModel):
    """Account data section of dashboard summary."""

    equity: float
    cash: float
    buying_power: float
    daily_pnl: float
    daily_pnl_pct: float


class BestTradeData(BaseModel):
    """Best trade highlight."""

    symbol: str
    pnl: float


class TodayStatsData(BaseModel):
    """Today's trading stats section."""

    trade_count: int
    win_rate: float | None  # null if 0 trades
    avg_r: float | None  # null if 0 trades
    best_trade: BestTradeData | None  # null if 0 trades


class GoalsData(BaseModel):
    """Monthly goal progress section."""

    monthly_target_usd: float
    current_month_pnl: float
    trading_days_elapsed: int
    trading_days_remaining: int
    avg_daily_pnl: float
    needed_daily_pnl: float
    pace_status: str  # "ahead" | "on_pace" | "behind"


class MarketData(BaseModel):
    """Market status section."""

    status: str  # "pre_market" | "open" | "closed" | "after_hours"
    time_et: str  # e.g., "2:15 PM ET"
    is_paper: bool


class RegimeData(BaseModel):
    """Market regime section."""

    classification: str
    description: str
    updated_at: str | None


class StrategyDeploymentInfo(BaseModel):
    """Single strategy deployment info."""

    strategy_id: str
    abbreviation: str
    deployed_capital: float
    position_count: int
    aggregate_pnl: float


class DeploymentData(BaseModel):
    """Strategy deployment section."""

    strategies: list[StrategyDeploymentInfo]
    available_capital: float
    total_equity: float


class OrchestratorSummaryData(BaseModel):
    """Orchestrator summary section."""

    active_strategy_count: int
    total_strategy_count: int
    deployed_amount: float
    deployed_pct: float
    risk_used_pct: float
    regime: str


class DashboardSummaryResponse(BaseModel):
    """Aggregate dashboard summary response."""

    account: AccountSummaryData
    today_stats: TodayStatsData
    goals: GoalsData
    market: MarketData
    regime: RegimeData
    deployment: DeploymentData
    orchestrator: OrchestratorSummaryData
    timestamp: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Strategy abbreviation mapping
STRATEGY_ABBREVIATIONS: dict[str, str] = {
    "orb_breakout": "O",
    "orb_scalp": "S",
    "vwap_reclaim": "V",
    "afternoon_momentum": "A",
}

# Regime descriptions
REGIME_DESCRIPTIONS: dict[str, str] = {
    "bullish": "Strong upward momentum",
    "bearish": "Downward pressure",
    "neutral": "Range-bound, mixed signals",
    "volatile": "High volatility, proceed with caution",
    "crisis": "Extreme volatility, trading suspended",
}


def _calculate_trading_days() -> tuple[int, int]:
    """Calculate trading days elapsed and remaining in current month.

    Returns:
        Tuple of (elapsed, remaining) trading day counts.
    """
    now = datetime.now(ET_TZ)
    year = now.year
    month = now.month

    # Last day of current month
    if month == 12:
        last_day = datetime(year + 1, 1, 1, tzinfo=ET_TZ) - datetime.resolution
    else:
        last_day = datetime(year, month + 1, 1, tzinfo=ET_TZ) - datetime.resolution

    today = now.day
    last_date = last_day.day

    # Count weekdays from start of month to today
    elapsed = 0
    for day in range(1, today + 1):
        date = datetime(year, month, day, tzinfo=ET_TZ)
        if date.weekday() < 5:  # Mon-Fri
            elapsed += 1

    # Count weekdays from today+1 to end of month
    remaining = 0
    for day in range(today + 1, last_date + 1):
        date = datetime(year, month, day, tzinfo=ET_TZ)
        if date.weekday() < 5:
            remaining += 1

    return elapsed, remaining


def _get_pace_status(current_pnl: float, target: float, elapsed_pct: float) -> str:
    """Determine pace status based on progress.

    Returns:
        "ahead" (>110% pace), "on_pace" (90-110%), or "behind" (<90%).
    """
    if elapsed_pct <= 0:
        return "on_pace"

    expected_pnl = target * (elapsed_pct / 100)
    if expected_pnl <= 0:
        return "ahead" if current_pnl > 0 else "on_pace"

    pace_ratio = current_pnl / expected_pnl

    if pace_ratio >= 1.1:
        return "ahead"
    elif pace_ratio >= 0.9:
        return "on_pace"
    else:
        return "behind"


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> DashboardSummaryResponse:
    """Get aggregated dashboard data in a single response.

    This endpoint combines data from multiple sources to provide everything
    the Dashboard needs in one API call:
    - Account info from broker
    - Today's performance metrics from trade logger
    - Monthly goal progress
    - Market status
    - Regime classification from orchestrator
    - Strategy deployment state

    Returns:
        DashboardSummaryResponse with all dashboard sections.
    """
    now_utc = state.clock.now() if state.clock else datetime.now(UTC)
    now_et = now_utc.astimezone(ET_TZ)

    is_dev_mode = isinstance(state.broker, SimulatedBroker)

    # ---------------------------------------------------------------------------
    # 1. Account data
    # ---------------------------------------------------------------------------
    account_info = await state.broker.get_account()
    equity = account_info.equity
    cash = account_info.cash
    buying_power = account_info.buying_power

    # Closed trade P&L
    closed_pnl = await state.trade_logger.get_todays_pnl()

    # Unrealized P&L from open positions
    unrealized_pnl = 0.0
    if state.order_manager is not None and state.data_service is not None:
        for pos in state.order_manager.get_all_positions_flat():
            if pos.is_fully_closed:
                continue
            try:
                current_price = await state.data_service.get_current_price(pos.symbol)
                if current_price is not None:
                    unrealized_pnl += (current_price - pos.entry_price) * pos.shares_remaining
            except Exception:
                pass  # Use 0 for positions where price unavailable

    daily_pnl = closed_pnl + unrealized_pnl
    daily_pnl_pct = (daily_pnl / equity * 100) if equity > 0 else 0.0

    account_data = AccountSummaryData(
        equity=equity,
        cash=cash,
        buying_power=buying_power,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
    )

    # ---------------------------------------------------------------------------
    # 2. Today's stats
    # ---------------------------------------------------------------------------
    today_str = now_et.date().isoformat()
    today_trades = await state.trade_logger.query_trades(
        date_from=today_str,
        date_to=today_str,
        limit=1000,
        offset=0,
    )

    trade_count = len(today_trades)
    win_rate: float | None = None
    avg_r: float | None = None
    best_trade_data: BestTradeData | None = None

    if trade_count > 0:
        metrics = compute_metrics(today_trades)
        win_rate = metrics.win_rate
        avg_r = metrics.avg_r_multiple

        # Find best trade by P&L
        best = max(today_trades, key=lambda t: t.get("net_pnl", 0) or 0)
        best_pnl = best.get("net_pnl", 0) or 0
        if best_pnl > 0:
            best_trade_data = BestTradeData(
                symbol=best.get("symbol", ""),
                pnl=best_pnl,
            )

    today_stats = TodayStatsData(
        trade_count=trade_count,
        win_rate=win_rate,
        avg_r=avg_r,
        best_trade=best_trade_data,
    )

    # ---------------------------------------------------------------------------
    # 3. Monthly goals
    # ---------------------------------------------------------------------------
    # Get first of month
    first_of_month = now_et.replace(day=1).date().isoformat()
    today_date = now_et.date().isoformat()

    month_trades = await state.trade_logger.query_trades(
        date_from=first_of_month,
        date_to=today_date,
        limit=10000,
        offset=0,
    )

    current_month_pnl = sum(t.get("net_pnl", 0) or 0 for t in month_trades)
    elapsed, remaining = _calculate_trading_days()
    total_days = elapsed + remaining

    # Get monthly target from config
    monthly_target = 5000.0  # Default
    if state.config and hasattr(state.config, "goals"):
        goals_cfg = state.config.goals
        if goals_cfg and hasattr(goals_cfg, "monthly_target_usd"):
            monthly_target = goals_cfg.monthly_target_usd

    avg_daily_pnl = current_month_pnl / elapsed if elapsed > 0 else 0.0
    remaining_to_target = max(0, monthly_target - current_month_pnl)
    needed_daily_pnl = remaining_to_target / remaining if remaining > 0 else 0.0

    elapsed_pct = (elapsed / total_days * 100) if total_days > 0 else 0.0
    pace_status = _get_pace_status(current_month_pnl, monthly_target, elapsed_pct)

    goals_data = GoalsData(
        monthly_target_usd=monthly_target,
        current_month_pnl=current_month_pnl,
        trading_days_elapsed=elapsed,
        trading_days_remaining=remaining,
        avg_daily_pnl=avg_daily_pnl,
        needed_daily_pnl=needed_daily_pnl,
        pace_status=pace_status,
    )

    # ---------------------------------------------------------------------------
    # 4. Market status
    # ---------------------------------------------------------------------------
    clock_now = state.clock.now() if state.clock else None
    market_status = get_market_status(clock_now)

    # Format time as "2:15 PM ET"
    time_et_str = now_et.strftime("%-I:%M %p ET")

    market_data = MarketData(
        status=market_status,
        time_et=time_et_str,
        is_paper=is_dev_mode,
    )

    # ---------------------------------------------------------------------------
    # 5. Regime classification
    # ---------------------------------------------------------------------------
    regime_classification = "neutral"
    regime_updated_at: str | None = None

    if state.orchestrator is not None:
        regime_classification = state.orchestrator.current_regime.value
        if state.orchestrator.last_regime_check:
            regime_updated_at = state.orchestrator.last_regime_check.astimezone(
                ET_TZ
            ).strftime("%-I:%M %p")

    regime_description = REGIME_DESCRIPTIONS.get(
        regime_classification, "Unknown market conditions"
    )

    regime_data = RegimeData(
        classification=regime_classification,
        description=regime_description,
        updated_at=regime_updated_at,
    )

    # ---------------------------------------------------------------------------
    # 6. Strategy deployment
    # ---------------------------------------------------------------------------
    deployed_by_strategy: dict[str, float] = {}
    position_count_by_strategy: dict[str, int] = {}
    pnl_by_strategy: dict[str, float] = {}

    if state.order_manager is not None:
        all_positions = state.order_manager.get_all_positions_flat()
        for pos in all_positions:
            if not pos.is_fully_closed:
                capital = pos.entry_price * pos.shares_remaining
                deployed_by_strategy[pos.strategy_id] = (
                    deployed_by_strategy.get(pos.strategy_id, 0.0) + capital
                )
                position_count_by_strategy[pos.strategy_id] = (
                    position_count_by_strategy.get(pos.strategy_id, 0) + 1
                )
                # Use realized_pnl from partial exits (ManagedPosition doesn't track current_price)
                pnl_by_strategy[pos.strategy_id] = (
                    pnl_by_strategy.get(pos.strategy_id, 0.0) + pos.realized_pnl
                )

    total_deployed = sum(deployed_by_strategy.values())
    available_capital = equity - total_deployed

    strategies_deployment: list[StrategyDeploymentInfo] = []
    for strategy_id in state.strategies.keys():
        abbrev = STRATEGY_ABBREVIATIONS.get(strategy_id, strategy_id[0].upper())
        deployed = deployed_by_strategy.get(strategy_id, 0.0)
        pos_count = position_count_by_strategy.get(strategy_id, 0)
        agg_pnl = pnl_by_strategy.get(strategy_id, 0.0)

        strategies_deployment.append(
            StrategyDeploymentInfo(
                strategy_id=strategy_id,
                abbreviation=abbrev,
                deployed_capital=deployed,
                position_count=pos_count,
                aggregate_pnl=agg_pnl,
            )
        )

    deployment_data = DeploymentData(
        strategies=strategies_deployment,
        available_capital=available_capital,
        total_equity=equity,
    )

    # ---------------------------------------------------------------------------
    # 7. Orchestrator summary
    # ---------------------------------------------------------------------------
    active_count = 0
    total_count = len(state.strategies)
    deployed_pct = (total_deployed / equity * 100) if equity > 0 else 0.0

    if state.orchestrator is not None:
        for alloc in state.orchestrator.current_allocations.values():
            if alloc.eligible and alloc.throttle_action.value != "suspend":
                active_count += 1

    orchestrator_data = OrchestratorSummaryData(
        active_strategy_count=active_count,
        total_strategy_count=total_count,
        deployed_amount=total_deployed,
        deployed_pct=deployed_pct,
        risk_used_pct=deployed_pct,  # Same as deployed_pct for now
        regime=regime_classification,
    )

    # ---------------------------------------------------------------------------
    # Build response
    # ---------------------------------------------------------------------------
    return DashboardSummaryResponse(
        account=account_data,
        today_stats=today_stats,
        goals=goals_data,
        market=market_data,
        regime=regime_data,
        deployment=deployment_data,
        orchestrator=orchestrator_data,
        timestamp=datetime.now(UTC).isoformat(),
    )

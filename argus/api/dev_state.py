"""Development state factory for frontend development.

Creates an AppState with realistic mock data for testing the Command Center
UI without running the full trading engine.

Usage:
    python -m argus.api --dev
"""

from __future__ import annotations

import os
import random
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argus.analytics.debrief_service import DebriefService
from argus.analytics.trade_logger import TradeLogger
from argus.api.auth import hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.routes.watchlist import SparklinePoint, VwapState, WatchlistItem
from argus.core.clock import SystemClock
from argus.core.config import (
    AfternoonMomentumConfig,
    ApiConfig,
    BacktestSummaryConfig,
    GoalsConfig,
    HealthConfig,
    OperatingWindow,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OrchestratorConfig,
    OrderManagerConfig,
    RiskConfig,
    StrategyConfig,
    SystemConfig,
    VwapReclaimConfig,
)
from argus.core.event_bus import EventBus
from argus.core.health import ComponentStatus, HealthMonitor
from argus.core.regime import MarketRegime, RegimeIndicators
from argus.core.risk_manager import RiskManager
from argus.core.throttle import StrategyAllocation, ThrottleAction
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import AssetClass, ExitReason, OrderSide, Trade, TradeOutcome

# ---------------------------------------------------------------------------
# Mock Strategy for dev mode
# ---------------------------------------------------------------------------


@dataclass
class MockStrategy:
    """Minimal mock strategy for API development.

    Provides the fields needed by the strategies API endpoint without
    requiring the full OrbBreakoutStrategy implementation.
    """

    strategy_id: str
    name: str
    version: str
    is_active: bool
    pipeline_stage: str
    allocated_capital: float
    daily_pnl: float
    trade_count_today: int
    config: StrategyConfig
    # Throttle metrics — stored here for potential direct-access patterns.
    # Note: The orchestrator route currently derives these independently from
    # trade_logger data, so these values serve as reference/documentation of
    # the intended mock scenario rather than being read by the API.
    consecutive_losses: int = 0
    rolling_sharpe: float | None = None
    drawdown_pct: float = 0.0

    @property
    def _is_active(self) -> bool:
        """Compatibility with BaseStrategy._is_active property."""
        return self.is_active

    @property
    def _allocated_capital(self) -> float:
        """Compatibility with BaseStrategy._allocated_capital property."""
        return self.allocated_capital

    @property
    def _daily_pnl(self) -> float:
        """Compatibility with BaseStrategy._daily_pnl property."""
        return self.daily_pnl

    @property
    def _trade_count_today(self) -> int:
        """Compatibility with BaseStrategy._trade_count_today property."""
        return self.trade_count_today

    @property
    def _config(self) -> StrategyConfig:
        """Compatibility with BaseStrategy._config property."""
        return self.config


@dataclass
class MockOrchestrator:
    """Minimal mock orchestrator for API development.

    Provides the fields and methods needed by the orchestrator API endpoint
    without requiring the full Orchestrator implementation.
    """

    _config: OrchestratorConfig
    _current_regime: MarketRegime
    _current_allocations: dict[str, StrategyAllocation]
    _current_indicators: RegimeIndicators | None
    _last_regime_check: datetime | None
    _override_until: dict[str, datetime] | None = None

    def __post_init__(self) -> None:
        """Initialize mutable default fields."""
        if self._override_until is None:
            self._override_until = {}

    @property
    def current_regime(self) -> MarketRegime:
        """Get current market regime."""
        return self._current_regime

    @property
    def current_allocations(self) -> dict[str, StrategyAllocation]:
        """Get current strategy allocations."""
        return self._current_allocations

    @property
    def current_indicators(self) -> RegimeIndicators | None:
        """Get current regime indicators."""
        return self._current_indicators

    @property
    def last_regime_check(self) -> datetime | None:
        """Get last regime check timestamp."""
        return self._last_regime_check

    @property
    def regime_check_interval_minutes(self) -> int:
        """Get regime check interval in minutes."""
        return self._config.regime_check_interval_minutes

    @property
    def cash_reserve_pct(self) -> float:
        """Get cash reserve percentage."""
        return self._config.cash_reserve_pct

    @property
    def pre_market_complete(self) -> bool:
        """Whether pre-market routine has completed today."""
        return True  # Always complete in dev mode

    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        """Mock rebalance - returns current allocations unchanged."""
        return self._current_allocations

    async def override_throttle(
        self, strategy_id: str, duration_minutes: int, reason: str
    ) -> None:
        """Mock override — just set the flag."""
        if self._override_until is None:
            self._override_until = {}
        self._override_until[strategy_id] = datetime.now(UTC) + timedelta(
            minutes=duration_minutes
        )

    def _is_override_active(self, strategy_id: str) -> bool:
        """Check if override is active for a strategy."""
        if self._override_until is None:
            return False
        if strategy_id not in self._override_until:
            return False
        return datetime.now(UTC) < self._override_until[strategy_id]


# ---------------------------------------------------------------------------
# Trade generation
# ---------------------------------------------------------------------------


def _generate_mock_trades(
    orb_count: int = 12,
    scalp_count: int = 6,
    vwap_reclaim_count: int = 8,
    afternoon_momentum_count: int = 6,
) -> list[Trade]:
    """Generate realistic mock trades for seeding the database.

    Creates a mix of:
    - ~55% wins
    - ~40% losses
    - ~5% breakeven

    For ORB Breakout: 5-120 min holds, 1R/2R targets
    For ORB Scalp: 30-120s holds, 0.3R targets, smaller P&L
    For VWAP Reclaim: 5-30 min holds, 1.5R/2R targets, mid-morning entries
    For Afternoon Momentum: 15-60 min holds, 1.5R/2R targets, afternoon entries
    """
    # ORB Breakout uses these symbols
    orb_symbols = ["NVDA", "AAPL", "AMD", "META"]
    # ORB Scalp uses these symbols (distinct from ORB positions)
    scalp_symbols = ["TSLA", "GOOG", "AMZN", "MSFT"]
    # VWAP Reclaim uses mid-cap momentum names
    vwap_reclaim_symbols = ["SOFI", "PLTR", "HOOD", "RIVN"]
    # Afternoon Momentum uses large-cap names that consolidate midday
    afternoon_momentum_symbols = ["MSFT", "GOOG", "META", "AMZN"]

    symbol_prices = {
        "TSLA": (180.0, 250.0),
        "NVDA": (700.0, 950.0),
        "AAPL": (170.0, 195.0),
        "AMD": (120.0, 180.0),
        "META": (450.0, 550.0),
        "GOOG": (150.0, 180.0),
        "AMZN": (180.0, 220.0),
        "MSFT": (400.0, 450.0),
        "SOFI": (12.0, 18.0),
        "PLTR": (25.0, 40.0),
        "HOOD": (18.0, 28.0),
        "RIVN": (14.0, 22.0),
    }

    trades: list[Trade] = []
    now = datetime.now(UTC)

    def generate_trade(
        strategy_id: str,
        symbols: list[str],
        target_r: float,
        min_hold_seconds: int,
        max_hold_seconds: int,
        rationale: str,
        entry_hour_range: tuple[int, int] | None = None,
    ) -> Trade:
        """Generate a single trade with strategy-specific parameters."""
        # Spread trades over the last 30 days
        days_ago = random.randint(0, 29)
        trade_date = now - timedelta(days=days_ago)
        # Set entry time to market hours
        if entry_hour_range:
            # Use specific hour range (for VWAP Reclaim: 10-12 ET)
            hour = random.randint(entry_hour_range[0], entry_hour_range[1])
            minute = random.randint(0, 59)
        else:
            # Default: 9:45 AM - 3:30 PM ET
            hour = random.randint(9, 14)
            minute = random.randint(0, 59)
            if hour == 9:
                minute = random.randint(45, 59)

        entry_time = trade_date.replace(
            hour=hour + 5,  # Convert to UTC (ET + 5 in winter)
            minute=minute,
            second=0,
            microsecond=0,
        )

        # Determine outcome based on distribution
        rand = random.random()
        if rand < 0.55:
            outcome = TradeOutcome.WIN
        elif rand < 0.95:
            outcome = TradeOutcome.LOSS
        else:
            outcome = TradeOutcome.BREAKEVEN

        # Pick symbol and base price
        symbol = random.choice(symbols)
        price_low, price_high = symbol_prices[symbol]
        entry_price = round(random.uniform(price_low, price_high), 2)

        # Calculate risk (stop distance)
        risk_pct = random.uniform(0.005, 0.015)  # 0.5% - 1.5% risk
        stop_distance = round(entry_price * risk_pct, 2)
        stop_price = round(entry_price - stop_distance, 2)

        # Position sizing based on $1000-$3000 risk per trade
        # Scalp uses smaller risk, VWAP Reclaim and Afternoon Momentum are medium
        if strategy_id == "orb_scalp":
            risk_amount = random.uniform(500, 1500)
        elif strategy_id in ("vwap_reclaim", "afternoon_momentum"):
            risk_amount = random.uniform(800, 2000)
        else:
            risk_amount = random.uniform(1000, 3000)
        shares = max(10, int(risk_amount / stop_distance))

        # Calculate exit based on outcome
        if outcome == TradeOutcome.WIN:
            # Win: hit target
            r_multiple = target_r
            exit_price = round(entry_price + (stop_distance * r_multiple), 2)
            exit_reason = ExitReason.TARGET_1
            gross_pnl = round(shares * (exit_price - entry_price), 2)
        elif outcome == TradeOutcome.LOSS:
            # Loss: stopped out or time stop
            exit_reason = random.choice([ExitReason.STOP_LOSS, ExitReason.TIME_STOP])
            if exit_reason == ExitReason.STOP_LOSS:
                exit_price = stop_price
                r_multiple = -1.0
            else:
                # Time stop: exit at partial loss
                loss_pct = random.uniform(0.2, 0.8)
                exit_price = round(entry_price - (stop_distance * loss_pct), 2)
                r_multiple = round(-loss_pct, 2)
            gross_pnl = round(shares * (exit_price - entry_price), 2)
        else:
            # Breakeven: exit near entry
            exit_price = round(entry_price + random.uniform(-0.05, 0.05), 2)
            exit_reason = random.choice([ExitReason.TIME_STOP, ExitReason.EOD_FLATTEN])
            gross_pnl = round(shares * (exit_price - entry_price), 2)
            if stop_distance > 0:
                r_multiple = round(gross_pnl / (shares * stop_distance), 2)
            else:
                r_multiple = 0.0

        # Hold duration based on strategy
        hold_seconds = random.randint(min_hold_seconds, max_hold_seconds)
        exit_time = entry_time + timedelta(seconds=hold_seconds)

        # Commission: $1 per 100 shares (minimum $1)
        commission = max(1.0, round(shares / 100, 2))

        return Trade(
            strategy_id=strategy_id,
            symbol=symbol,
            asset_class=AssetClass.US_STOCKS,
            side=OrderSide.BUY,
            entry_price=entry_price,
            entry_time=entry_time,
            exit_price=exit_price,
            exit_time=exit_time,
            shares=shares,
            stop_price=stop_price,
            target_prices=[round(entry_price + stop_distance * target_r, 2)],
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            commission=commission,
            r_multiple=r_multiple,
            rationale=rationale,
        )

    # Generate ORB Breakout trades (5-120 min holds, 2R targets)
    for _ in range(orb_count):
        trade = generate_trade(
            strategy_id="orb_breakout",
            symbols=orb_symbols,
            target_r=random.choice([1.0, 1.5, 2.0]),
            min_hold_seconds=5 * 60,  # 5 minutes
            max_hold_seconds=120 * 60,  # 2 hours
            rationale="ORB breakout with volume confirmation",
        )
        trades.append(trade)

    # Generate ORB Scalp trades (30-120s holds, 0.3R targets)
    for _ in range(scalp_count):
        trade = generate_trade(
            strategy_id="orb_scalp",
            symbols=scalp_symbols,
            target_r=0.3,
            min_hold_seconds=30,  # 30 seconds
            max_hold_seconds=120,  # 2 minutes
            rationale="ORB scalp quick momentum capture",
        )
        trades.append(trade)

    # Generate VWAP Reclaim trades (5-30 min holds, 1.5-2R targets, mid-morning)
    for _ in range(vwap_reclaim_count):
        trade = generate_trade(
            strategy_id="vwap_reclaim",
            symbols=vwap_reclaim_symbols,
            target_r=random.choice([1.5, 2.0]),
            min_hold_seconds=5 * 60,  # 5 minutes
            max_hold_seconds=30 * 60,  # 30 minutes
            rationale="VWAP reclaim after pullback with volume confirmation",
            entry_hour_range=(10, 11),  # 10:00 AM - 11:59 AM ET
        )
        trades.append(trade)

    # Generate Afternoon Momentum trades (15-60 min holds, 1.5-2R targets, afternoon)
    for _ in range(afternoon_momentum_count):
        trade = generate_trade(
            strategy_id="afternoon_momentum",
            symbols=afternoon_momentum_symbols,
            target_r=random.choice([1.5, 2.0]),
            min_hold_seconds=15 * 60,  # 15 minutes
            max_hold_seconds=60 * 60,  # 60 minutes
            rationale="Afternoon consolidation breakout with volume surge",
            entry_hour_range=(14, 15),  # 2:00 PM - 3:30 PM ET
        )
        trades.append(trade)

    return trades


def _create_mock_positions(now: datetime) -> list[ManagedPosition]:
    """Create mock managed positions for dev mode.

    Creates:
    - 2 ORB Breakout positions (~$15k total notional, within $20k allocation)
    - 2 ORB Scalp positions (~$16k total notional, within $20k allocation)
    - 2 VWAP Reclaim positions (~$14k total notional, within $20k allocation)
    - 2 Afternoon Momentum positions (~$15k total notional, within $20k allocation)

    Position sizes are realistic for a $100k account with 20% allocation per strategy
    (four strategies + 20% cash reserve).
    """
    positions = []

    # --- ORB Breakout Positions (total ~$18k = 68% of $26.7k allocation) ---

    # Position 1: NVDA - entered 30 minutes ago, T1 hit, stop at breakeven
    # 12 shares × $875.50 = $10,506 notional
    entry_time_1 = now - timedelta(minutes=30)
    positions.append(
        ManagedPosition(
            symbol="NVDA",
            strategy_id="orb_breakout",
            entry_price=875.50,
            entry_time=entry_time_1,
            shares_total=12,
            shares_remaining=6,  # T1 took 6 shares
            stop_price=875.50,  # Moved to breakeven
            original_stop_price=868.00,
            stop_order_id="stop_nvda_001",
            t1_price=883.00,
            t1_order_id=None,  # T1 filled
            t1_shares=6,
            t1_filled=True,
            t2_price=890.50,
            high_watermark=886.25,
            realized_pnl=45.0,  # 6 × $7.50
        )
    )

    # Position 2: AAPL - entered 15 minutes ago, still waiting for T1
    # 45 shares × $185.80 = $8,361 notional
    entry_time_2 = now - timedelta(minutes=15)
    positions.append(
        ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=185.80,
            entry_time=entry_time_2,
            shares_total=45,
            shares_remaining=45,
            stop_price=183.50,
            original_stop_price=183.50,
            stop_order_id="stop_aapl_001",
            t1_price=188.10,
            t1_order_id="t1_aapl_001",
            t1_shares=23,
            t1_filled=False,
            t2_price=190.40,
            high_watermark=186.90,
            realized_pnl=0.0,
        )
    )

    # --- ORB Scalp Positions (~$20k total = 75% of $26.7k allocation) ---

    # Position 3: TSLA - scalp entered 45 seconds ago, waiting for target
    # 50 shares × $225.80 = $11,290 notional
    entry_time_3 = now - timedelta(seconds=45)
    positions.append(
        ManagedPosition(
            symbol="TSLA",
            strategy_id="orb_scalp",
            entry_price=225.80,
            entry_time=entry_time_3,
            shares_total=50,
            shares_remaining=50,
            stop_price=224.65,  # Tighter stop for scalp
            original_stop_price=224.65,
            stop_order_id="stop_tsla_scalp_001",
            t1_price=226.15,  # 0.3R target
            t1_order_id="t1_tsla_scalp_001",
            t1_shares=50,  # Scalp exits 100% at T1
            t1_filled=False,
            t2_price=0.0,  # No T2 for scalp
            high_watermark=225.95,
            realized_pnl=0.0,
        )
    )

    # Position 4: GOOG - scalp entered 90 seconds ago, approaching target
    # 55 shares × $165.40 = $9,097 notional
    entry_time_4 = now - timedelta(seconds=90)
    positions.append(
        ManagedPosition(
            symbol="GOOG",
            strategy_id="orb_scalp",
            entry_price=165.40,
            entry_time=entry_time_4,
            shares_total=55,
            shares_remaining=55,
            stop_price=164.55,  # Tighter stop for scalp
            original_stop_price=164.55,
            stop_order_id="stop_goog_scalp_001",
            t1_price=165.66,  # 0.3R target
            t1_order_id="t1_goog_scalp_001",
            t1_shares=55,  # Scalp exits 100% at T1
            t1_filled=False,
            t2_price=0.0,  # No T2 for scalp
            high_watermark=165.58,
            realized_pnl=0.0,
        )
    )

    # --- VWAP Reclaim Positions (~$18k total = 68% of $26.7k allocation) ---
    # Mid-morning entries (10:15 AM, 10:45 AM ET pattern)

    # Position 5: PLTR - entered at 10:15 AM (mid-morning), T1 partially filled
    # 300 shares × $32.50 = $9,750 notional
    entry_time_5 = now - timedelta(minutes=25)
    positions.append(
        ManagedPosition(
            symbol="PLTR",
            strategy_id="vwap_reclaim",
            entry_price=32.50,
            entry_time=entry_time_5,
            shares_total=300,
            shares_remaining=150,  # T1 took half
            stop_price=32.50,  # Moved to breakeven after T1
            original_stop_price=31.85,
            stop_order_id="stop_pltr_vwap_001",
            t1_price=33.15,
            t1_order_id=None,  # T1 filled
            t1_shares=150,
            t1_filled=True,
            t2_price=33.80,
            t2_order_id="t2_pltr_vwap_001",
            high_watermark=33.45,
            realized_pnl=97.50,  # 150 × $0.65
        )
    )

    # Position 6: SOFI - entered at 10:45 AM (mid-morning), waiting for T1
    # 500 shares × $15.20 = $7,600 notional
    entry_time_6 = now - timedelta(minutes=12)
    positions.append(
        ManagedPosition(
            symbol="SOFI",
            strategy_id="vwap_reclaim",
            entry_price=15.20,
            entry_time=entry_time_6,
            shares_total=500,
            shares_remaining=500,
            stop_price=14.90,
            original_stop_price=14.90,
            stop_order_id="stop_sofi_vwap_001",
            t1_price=15.65,
            t1_order_id="t1_sofi_vwap_001",
            t1_shares=250,
            t1_filled=False,
            t2_price=16.10,
            high_watermark=15.42,
            realized_pnl=0.0,
        )
    )

    # --- Afternoon Momentum Positions (~$15k total = 75% of $20k allocation) ---
    # Afternoon entries (2:10 PM, 2:25 PM ET pattern)

    # Position 7: MSFT - entered at 2:10 PM (afternoon consolidation breakout), T1 hit
    # 20 shares × $425.50 = $8,510 notional
    entry_time_7 = now - timedelta(minutes=18)
    positions.append(
        ManagedPosition(
            symbol="MSFT",
            strategy_id="afternoon_momentum",
            entry_price=425.50,
            entry_time=entry_time_7,
            shares_total=20,
            shares_remaining=10,  # T1 took half
            stop_price=425.50,  # Moved to breakeven after T1
            original_stop_price=421.00,
            stop_order_id="stop_msft_aftn_001",
            t1_price=430.00,
            t1_order_id=None,  # T1 filled
            t1_shares=10,
            t1_filled=True,
            t2_price=434.50,
            t2_order_id="t2_msft_aftn_001",
            high_watermark=431.25,
            realized_pnl=45.0,  # 10 × $4.50
        )
    )

    # Position 8: META - entered at 2:25 PM (afternoon breakout), waiting for T1
    # 15 shares × $515.80 = $7,737 notional
    entry_time_8 = now - timedelta(minutes=8)
    positions.append(
        ManagedPosition(
            symbol="META",
            strategy_id="afternoon_momentum",
            entry_price=515.80,
            entry_time=entry_time_8,
            shares_total=15,
            shares_remaining=15,
            stop_price=510.00,
            original_stop_price=510.00,
            stop_order_id="stop_meta_aftn_001",
            t1_price=521.60,
            t1_order_id="t1_meta_aftn_001",
            t1_shares=8,
            t1_filled=False,
            t2_price=527.40,
            high_watermark=518.50,
            realized_pnl=0.0,
        )
    )

    return positions


async def _seed_orchestrator_decisions(trade_logger: TradeLogger, now: datetime) -> None:
    """Seed mock orchestrator decisions for dev mode.

    Creates a realistic trading day timeline with ~15 decisions covering:
    - Pre-market regime classification and allocations (9:25 AM)
    - Strategy activations
    - Regime re-checks at 30-minute intervals
    - ORB Scalp throttle event (10:45 AM)
    - Allocation rebalance after throttle
    - Afternoon strategy activation
    """
    from zoneinfo import ZoneInfo

    et_tz = ZoneInfo("America/New_York")
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()

    # Build base datetime for "today" at 9:25 AM ET
    now_et = now.astimezone(et_tz)
    base_date = now_et.date()

    def make_timestamp(hour: int, minute: int) -> str:
        """Create ISO timestamp for today at given ET hour:minute."""
        dt = datetime(
            base_date.year, base_date.month, base_date.day, hour, minute, 0, 0, tzinfo=et_tz
        )
        return dt.astimezone(UTC).isoformat()

    # === Pre-market decisions (9:25 AM) ===

    # 1. Regime classification
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="regime_classification",
        strategy_id=None,
        details={
            "regime": "bullish_trending",
            "spy_price": 525.50,
            "spy_sma_20": 520.30,
            "spy_sma_50": 515.80,
            "spy_roc_5d": 1.25,
            "spy_realized_vol_20d": 12.5,
            "trend_score": 2,
            "vol_bucket": "normal",
        },
        rationale="SPY above both SMAs, bullish momentum, 12.5% vol → bullish_trending",
        created_at=make_timestamp(9, 25),
    )

    # 2-5. Initial allocations (equal-weight 20% each)
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={
            "allocation_pct": 0.20,
            "allocation_dollars": 20000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 20% allocation (equal-weight, 4 strategies)",
        created_at=make_timestamp(9, 25),
    )

    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_scalp",
        details={
            "allocation_pct": 0.20,
            "allocation_dollars": 20000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 20% allocation (equal-weight, 4 strategies)",
        created_at=make_timestamp(9, 25),
    )

    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="vwap_reclaim",
        details={
            "allocation_pct": 0.20,
            "allocation_dollars": 20000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 20% allocation (equal-weight, 4 strategies)",
        created_at=make_timestamp(9, 25),
    )

    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="afternoon_momentum",
        details={
            "allocation_pct": 0.20,
            "allocation_dollars": 20000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 20% allocation (equal-weight, 4 strategies)",
        created_at=make_timestamp(9, 25),
    )

    # 6-8. Strategy activations
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="strategy_activated",
        strategy_id="orb_breakout",
        details={"operating_window": {"earliest_entry": "09:35", "latest_entry": "11:30"}},
        rationale="ORB Breakout activated for trading",
        created_at=make_timestamp(9, 25),
    )

    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="strategy_activated",
        strategy_id="orb_scalp",
        details={"operating_window": {"earliest_entry": "09:45", "latest_entry": "11:30"}},
        rationale="ORB Scalp activated for trading",
        created_at=make_timestamp(9, 25),
    )

    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="strategy_activated",
        strategy_id="vwap_reclaim",
        details={"operating_window": {"earliest_entry": "10:00", "latest_entry": "12:00"}},
        rationale="VWAP Reclaim activated (will begin scanning at 10:00 AM)",
        created_at=make_timestamp(9, 25),
    )

    # 9. First regime re-check (10:00 AM) - unchanged
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="regime_classification",
        strategy_id=None,
        details={
            "regime": "bullish_trending",
            "regime_changed": False,
            "spy_price": 526.30,
            "spy_change_pct": 0.15,
        },
        rationale="Regime re-check: bullish_trending unchanged, SPY +0.15%",
        created_at=make_timestamp(10, 0),
    )

    # 10. Second regime re-check (10:30 AM) - regime change!
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="regime_classification",
        strategy_id=None,
        details={
            "regime": "range_bound",
            "previous_regime": "bullish_trending",
            "regime_changed": True,
            "spy_price": 521.80,
            "spy_sma_20": 520.30,
            "reason": "SPY dropped below SMA-20",
        },
        rationale="Regime change: bullish_trending → range_bound (SPY dropped below SMA-20)",
        created_at=make_timestamp(10, 30),
    )

    # 11. Allocation check after regime change (10:30 AM)
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id=None,
        details={
            "action": "rebalance_check",
            "result": "no_change",
            "reason": "All strategies eligible in range_bound regime",
        },
        rationale="Rebalance check after regime change — allocations unchanged",
        created_at=make_timestamp(10, 30),
    )

    # 12. ORB Scalp throttle event (10:45 AM) - 3 consecutive losses
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="throttle",
        strategy_id="orb_scalp",
        details={
            "throttle_action": "reduce",
            "previous_action": "none",
            "consecutive_losses": 3,
            "rolling_sharpe": -0.12,
            "drawdown_pct": 0.042,
        },
        rationale="ORB Scalp throttled to REDUCE: 3 consecutive losses",
        created_at=make_timestamp(10, 45),
    )

    # 13. Allocation update after throttle (10:45 AM)
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_scalp",
        details={
            "allocation_pct": 0.10,
            "allocation_dollars": 8000.0,
            "throttle_action": "reduce",
            "previous_allocation_pct": 0.20,
            "freed_capital": 12000.0,
        },
        rationale="ORB Scalp reduced to 10% ($8,000), excess redistributed",
        created_at=make_timestamp(10, 45),
    )

    # 14. Third regime re-check (11:00 AM) - back to bullish
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="regime_classification",
        strategy_id=None,
        details={
            "regime": "bullish_trending",
            "previous_regime": "range_bound",
            "regime_changed": True,
            "spy_price": 527.10,
            "spy_sma_20": 520.30,
            "reason": "SPY reclaimed SMA-20",
        },
        rationale="Regime change: range_bound → bullish_trending (SPY reclaimed SMA-20)",
        created_at=make_timestamp(11, 0),
    )

    # 15. Afternoon Momentum activation (2:00 PM)
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="strategy_activated",
        strategy_id="afternoon_momentum",
        details={"operating_window": {"earliest_entry": "14:00", "latest_entry": "15:30"}},
        rationale="Afternoon Momentum scanning started",
        created_at=make_timestamp(14, 0),
    )

    # === Yesterday's decisions (for history) ===

    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="regime_classification",
        strategy_id=None,
        details={"regime": "bullish_trending"},
        rationale="SPY above both SMAs with positive momentum",
    )

    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={
            "allocation_pct": 0.20,
            "allocation_dollars": 20000.0,
            "throttle_action": "none",
        },
        rationale="Active: 20% allocation (equal-weight, 4 strategies)",
    )

    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="eod_review",
        strategy_id=None,
        details={"regime": "bullish_trending", "total_pnl": 1250.50, "trade_count": 14},
        rationale="End of day review: +$1,250.50 across 14 trades",
    )


def _create_mock_orchestrator(now: datetime) -> MockOrchestrator:
    """Create a mock orchestrator for dev mode.

    Simulates a realistic mid-session state with:
    - ORB Breakout: Active, ThrottleAction.NONE, 20% ($20,000)
    - ORB Scalp: ThrottleAction.REDUCE, 10% ($8,000) — 3 consecutive losses
    - VWAP Reclaim: Active, ThrottleAction.NONE, 25% ($25,000) — gets extra
    - Afternoon Momentum: Active, ThrottleAction.NONE, 25% ($25,000) — gets extra

    Total: 80% deployed + 20% reserve = 100%
    """
    config = OrchestratorConfig()

    # Mock regime indicators
    indicators = RegimeIndicators(
        spy_price=525.50,
        spy_sma_20=520.30,
        spy_sma_50=515.80,
        spy_roc_5d=1.25,
        spy_realized_vol_20d=12.5,
        spy_vs_vwap=0.002,
        timestamp=now,
    )

    # Mock allocations: realistic mid-session with ORB Scalp throttled
    # Base: 20% each = 80% deployable. After throttle: ORB Scalp at 10% minimum,
    # freed 10% redistributed → VWAP Reclaim and Afternoon Momentum each get +5%
    allocations = {
        "orb_breakout": StrategyAllocation(
            strategy_id="orb_breakout",
            allocation_pct=0.20,
            allocation_dollars=20000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 20% allocation (equal-weight base)",
        ),
        "orb_scalp": StrategyAllocation(
            strategy_id="orb_scalp",
            allocation_pct=0.10,
            allocation_dollars=8000.0,
            throttle_action=ThrottleAction.REDUCE,
            eligible=True,
            reason="Throttled to minimum (10%): 3 consecutive losses",
        ),
        "vwap_reclaim": StrategyAllocation(
            strategy_id="vwap_reclaim",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 25% allocation (received +5% from ORB Scalp throttle)",
        ),
        "afternoon_momentum": StrategyAllocation(
            strategy_id="afternoon_momentum",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 25% allocation (received +5% from ORB Scalp throttle)",
        ),
    }

    return MockOrchestrator(
        _config=config,
        _current_regime=MarketRegime.BULLISH_TRENDING,
        _current_allocations=allocations,
        _current_indicators=indicators,
        _last_regime_check=now - timedelta(minutes=16),  # Next check in ~14 min
    )


def _create_mock_watchlist(now: datetime) -> list[WatchlistItem]:
    """Create mock watchlist data for dev mode.

    Creates a realistic watchlist with symbols from the scanner:
    - Mix of strategy assignments (ORB, Scalp, VWAP Reclaim, Afternoon Momentum)
    - Various VWAP states
    - Realistic sparkline data
    """
    # Helper to generate realistic VWAP distance based on state
    def get_vwap_distance(state: VwapState, has_vwap_strategy: bool) -> float | None:
        """Generate realistic VWAP distance based on state."""
        if not has_vwap_strategy:
            return None
        if state == VwapState.WATCHING:
            return None  # VWAP not yet relevant
        if state == VwapState.ABOVE_VWAP:
            return random.uniform(0.001, 0.008)  # Small positive
        if state == VwapState.BELOW_VWAP:
            return random.uniform(-0.010, -0.001)  # Small negative
        if state == VwapState.ENTERED:
            return random.uniform(0.001, 0.005)  # Reclaimed and holding above
        return None

    # Watchlist symbols with their base prices and characteristics
    watchlist_data = [
        # High-momentum gappers - all strategies watching
        {
            "symbol": "NVDA",
            "base_price": 875.50,
            "gap_pct": 3.2,
            "strategies": ["orb", "scalp", "vwap_reclaim", "afternoon_momentum"],
            "vwap_state": VwapState.ABOVE_VWAP,
        },
        {
            "symbol": "TSLA",
            "base_price": 225.80,
            "gap_pct": 2.8,
            "strategies": ["orb", "scalp"],
            "vwap_state": VwapState.WATCHING,
        },
        {
            "symbol": "AMD",
            "base_price": 165.30,
            "gap_pct": 4.1,
            "strategies": ["orb", "scalp", "vwap_reclaim"],
            "vwap_state": VwapState.ENTERED,  # Already in a VWAP Reclaim position
        },
        # Mid-cap momentum - VWAP Reclaim focus
        {
            "symbol": "PLTR",
            "base_price": 32.50,
            "gap_pct": 5.5,
            "strategies": ["vwap_reclaim"],
            "vwap_state": VwapState.ENTERED,
        },
        {
            "symbol": "SOFI",
            "base_price": 15.20,
            "gap_pct": 6.2,
            "strategies": ["vwap_reclaim"],
            "vwap_state": VwapState.BELOW_VWAP,
        },
        {
            "symbol": "HOOD",
            "base_price": 22.40,
            "gap_pct": 3.8,
            "strategies": ["vwap_reclaim"],
            "vwap_state": VwapState.ABOVE_VWAP,
        },
        # Large cap ORB candidates
        {
            "symbol": "AAPL",
            "base_price": 185.80,
            "gap_pct": 1.5,
            "strategies": ["orb"],
            "vwap_state": VwapState.WATCHING,
        },
        # Afternoon Momentum candidates (large-cap consolidation plays)
        {
            "symbol": "META",
            "base_price": 525.60,
            "gap_pct": 2.1,
            "strategies": ["orb", "scalp", "afternoon_momentum"],
            "vwap_state": VwapState.ABOVE_VWAP,
        },
        {
            "symbol": "MSFT",
            "base_price": 425.50,
            "gap_pct": 1.4,
            "strategies": ["afternoon_momentum"],
            "vwap_state": VwapState.WATCHING,
        },
        {
            "symbol": "GOOG",
            "base_price": 165.40,
            "gap_pct": 1.2,
            "strategies": ["scalp", "afternoon_momentum"],
            "vwap_state": VwapState.WATCHING,
        },
        {
            "symbol": "AMZN",
            "base_price": 195.30,
            "gap_pct": 1.8,
            "strategies": ["scalp", "afternoon_momentum"],
            "vwap_state": VwapState.WATCHING,
        },
    ]

    watchlist_items: list[WatchlistItem] = []

    for data in watchlist_data:
        # Generate sparkline data (last 30 1-minute bars)
        sparkline: list[SparklinePoint] = []
        base_price = data["base_price"]

        for i in range(30):
            bar_time = now - timedelta(minutes=30 - i)
            # Add some realistic price movement
            noise = random.uniform(-0.005, 0.005) * base_price
            trend = (i / 30) * random.uniform(-0.01, 0.02) * base_price  # Slight trend
            price = base_price + noise + trend

            sparkline.append(
                SparklinePoint(
                    timestamp=bar_time.isoformat(),
                    price=round(price, 2),
                )
            )

        # Current price is the last sparkline point
        current_price = sparkline[-1].price if sparkline else base_price

        # Calculate VWAP distance based on state and strategy
        has_vwap = "vwap_reclaim" in data["strategies"]
        vwap_distance = get_vwap_distance(data["vwap_state"], has_vwap)

        watchlist_items.append(
            WatchlistItem(
                symbol=data["symbol"],
                current_price=current_price,
                gap_pct=data["gap_pct"],
                strategies=data["strategies"],
                vwap_state=data["vwap_state"],
                sparkline=sparkline,
                vwap_distance_pct=vwap_distance,
            )
        )

    # Sort by gap percentage descending (highest movers first)
    watchlist_items.sort(key=lambda x: x.gap_pct, reverse=True)

    return watchlist_items


# ---------------------------------------------------------------------------
# Debrief Content Seeding
# ---------------------------------------------------------------------------


async def _seed_briefings(debrief_service: DebriefService, now: datetime) -> None:
    """Seed mock briefings for dev mode.

    Creates 5 briefings across the last 2 days:
    - 2 days ago: Pre-market (final) + EOD (final)
    - 1 day ago: Pre-market (final) + EOD (final)
    - Today: Pre-market (draft)
    """
    today = now.date()
    two_days_ago = (now - timedelta(days=2)).date()
    one_day_ago = (now - timedelta(days=1)).date()

    # 1. Pre-market, 2 days ago, final
    await debrief_service.create_briefing(
        date=two_days_ago.isoformat(),
        briefing_type="pre_market",
        title=f"Pre-Market Briefing — {two_days_ago.strftime('%b %d, %Y')}",
        content="""## Market Overview

Overnight futures are pointing higher with ES +0.45% following strong earnings from tech sector.
Asia closed mixed, Europe modestly green. SPY is bullish above the 20-day MA ($521.30),
with resistance at $528.50.

## Key Levels (SPY, QQQ)

| Index | Support | Resistance | VWAP | Notes |
|-------|---------|------------|------|-------|
| SPY   | 521.30  | 528.50     | 524.80 | Above 20MA |
| QQQ   | 442.00  | 451.00     | 446.50 | Strong momentum |

## Watchlist

1. **NVDA** - Gap +3.2%, earnings aftermath momentum, watching $875 breakout level
2. **TSLA** - Gap +2.8%, consolidating after yesterday's move, key level $225
3. **AMD** - Gap +2.1%, following NVDA sympathy, entry above $165
4. **AAPL** - Gap +1.5%, steady accumulation pattern
5. **MSFT** - Gap +1.2%, rotation into quality tech

## Catalysts

- NVDA post-earnings analyst commentary expected mid-morning
- Fed's Williams speaking at 11:00 AM ET
- Weekly jobless claims at 8:30 AM (consensus 215K)

## Game Plan

Aggressive stance today given bullish overnight action. Focus on ORB setups in gappers,
especially NVDA and AMD. Risk limits normal — up to 3 concurrent positions per strategy.
Watch for regime shift if SPY loses 521 level.
""",
    )
    # Update to final status
    briefings, _ = await debrief_service.list_briefings(
        briefing_type="pre_market", date_from=two_days_ago.isoformat()
    )
    if briefings:
        await debrief_service.update_briefing(briefings[0]["id"], status="final")

    # 2. EOD, 2 days ago, final
    await debrief_service.create_briefing(
        date=two_days_ago.isoformat(),
        briefing_type="eod",
        title=f"End of Day Review — {two_days_ago.strftime('%b %d, %Y')}",
        content="""## Session Summary

Strong trend day with SPY closing +1.1% near highs. Volume 15% above average.
Tech led with NVDA +4.2% on earnings follow-through. VIX compressed to 13.5, indicating low fear.

## Trades Review

| Symbol | Strategy | Entry | Exit | P&L | Notes |
|--------|----------|-------|------|-----|-------|
| NVDA | ORB Breakout | 872.50 | 885.20 | +$382 | Perfect setup, held for T2 |
| TSLA | ORB Scalp | 225.10 | 225.85 | +$112 | Quick 0.3R, clean exit |
| AMD | VWAP Reclaim | 163.80 | 166.40 | +$195 | Mid-morning entry |
| AAPL | ORB Breakout | 185.60 | 184.20 | -$140 | Stopped out, weak volume |
| PLTR | VWAP Reclaim | 31.50 | 32.85 | +$135 | Textbook reclaim |
| META | ORB Scalp | 522.30 | 521.10 | -$72 | False breakout |
| MSFT | Afternoon Momentum | 424.50 | 428.20 | +$111 | Consolidation break |
| GOOG | ORB Breakout | 165.80 | 164.50 | -$39 | Chopped out |

**Session Stats:** 8 trades, 5W/3L, Win Rate 62.5%, Net P&L +$684

## What Worked

- NVDA setup was textbook — clear OR, volume surge on break, held through T2
- VWAP Reclaim entries on PLTR and AMD both worked with volume confirmation
- Afternoon Momentum on MSFT caught the 2:15 PM breakout perfectly

## What Didn't Work

- Two false breakouts in first 20 minutes (META, GOOG) — should have waited for volume
- AAPL entry was against weak relative strength, ignored sector rotation

## Key Lessons

1. On trend days, trust the T2 targets — both NVDA and PLTR had room to run
2. Relative strength matters more than gap size — AAPL lagged all day despite gap
3. Low-volume breakouts in first 15 minutes are often traps

## Tomorrow's Focus

Watch for continuation in NVDA/AMD semiconductor names. Fed speak could introduce volatility.
Consider reducing position sizes if VIX expands above 15.
""",
    )
    briefings, _ = await debrief_service.list_briefings(
        briefing_type="eod", date_from=two_days_ago.isoformat()
    )
    if briefings:
        await debrief_service.update_briefing(briefings[0]["id"], status="final")

    # 3. Pre-market, 1 day ago, final (sparse)
    await debrief_service.create_briefing(
        date=one_day_ago.isoformat(),
        briefing_type="pre_market",
        title=f"Pre-Market Briefing — {one_day_ago.strftime('%b %d, %Y')}",
        content="""## Market Overview

Choppy overnight session. Futures flat after yesterday's rally. No clear direction —
expecting range-bound action. VIX ticking up to 14.2.

## Key Levels (SPY, QQQ)

| Index | Support | Resistance | VWAP | Notes |
|-------|---------|------------|------|-------|
| SPY   | 524.00  | 530.00     | 527.50 | Consolidating |
| QQQ   | 448.50  | 454.00     | 451.20 | Inside day setup |

## Watchlist

Reduced watchlist today — fewer quality gaps. Focus on NVDA continuation and any oversold bounces.

## Game Plan

Defensive stance. Reduce position sizes by 30%. Avoid first 30 minutes.
Look for VWAP Reclaim setups after 10:30 AM rather than ORB.
""",
    )
    briefings, _ = await debrief_service.list_briefings(
        briefing_type="pre_market",
        date_from=one_day_ago.isoformat(),
        date_to=one_day_ago.isoformat(),
    )
    if briefings:
        await debrief_service.update_briefing(briefings[0]["id"], status="final")

    # 4. EOD, 1 day ago, final
    await debrief_service.create_briefing(
        date=one_day_ago.isoformat(),
        briefing_type="eod",
        title=f"End of Day Review — {one_day_ago.strftime('%b %d, %Y')}",
        content="""## Session Summary

Choppy, low-conviction day as expected. SPY closed -0.2% on below-average volume.
Multiple failed breakouts in the morning.

## Trades Review

| Symbol | Strategy | Entry | Exit | P&L | Notes |
|--------|----------|-------|------|-----|-------|
| NVDA | ORB Breakout | 888.50 | 883.20 | -$159 | Reversal, should have skipped |
| TSLA | ORB Scalp | 224.30 | 223.85 | -$68 | Scalp stopped |
| HOOD | VWAP Reclaim | 22.80 | 23.45 | +$65 | Only clean setup |
| PLTR | ORB Breakout | 33.20 | 32.10 | -$132 | Gap fade |
| SOFI | ORB Scalp | 15.40 | 15.10 | -$45 | Overtrading |

**Session Stats:** 5 trades, 1W/4L, Win Rate 20%, Net P&L -$339

## What Worked

- HOOD VWAP Reclaim worked because I waited for volume confirmation post-10:30

## What Didn't Work

- Overtrading in morning despite plan to wait — took 3 ORB trades when should have skipped
- Ignored own briefing about defensive stance
- Chased NVDA continuation when setup quality was poor

## Key Lessons

1. When the briefing says "defensive", actually be defensive — follow the plan
2. 3+ morning losses = stop trading ORB strategies for the day
3. Low-volume gap-up days after trend days often mean-revert

## Tomorrow's Focus

Reset mentally. Stick to the plan. Quality over quantity — only A+ setups.
""",
    )
    briefings, _ = await debrief_service.list_briefings(
        briefing_type="eod",
        date_from=one_day_ago.isoformat(),
        date_to=one_day_ago.isoformat(),
    )
    if briefings:
        await debrief_service.update_briefing(briefings[0]["id"], status="final")

    # 5. Pre-market, today, draft (partial)
    await debrief_service.create_briefing(
        date=today.isoformat(),
        briefing_type="pre_market",
        title=f"Pre-Market Briefing — {today.strftime('%b %d, %Y')}",
        content="""## Market Overview

Futures mixed with ES -0.1%, NQ +0.2%. Asia was green overnight. Europe flat.
SPY testing 20-day MA support at $525.20. VIX at 14.8 — slightly elevated.

## Key Levels (SPY, QQQ)

| Index | Support | Resistance | VWAP | Notes |
|-------|---------|------------|------|-------|
| SPY   | 525.20  | 530.50     | -    | At 20MA support |
| QQQ   | 449.00  | 455.00     | -    | Range-bound |

## Watchlist

*Scanning in progress...*

## Catalysts

*To be updated...*

## Game Plan

*Pending market open assessment...*
""",
    )
    # Leave as draft (default status)


async def _seed_documents(debrief_service: DebriefService) -> None:
    """Seed mock documents for dev mode.

    Creates 3 research documents in the database.
    """
    # 1. VWAP Entry Timing Research
    await debrief_service.create_document(
        category="research",
        title="VWAP Entry Timing Research",
        content="""# VWAP Entry Timing Research

## Overview

Analysis of optimal entry timing for VWAP Reclaim strategy based on 6 months of paper trading data.

## Key Findings

### Time Windows

- **Best window:** 10:15 AM - 11:00 AM ET
- **Worst window:** 9:30 AM - 10:00 AM ET (too volatile, many false signals)
- **Afternoon:** 1:30 PM - 2:30 PM works but with lower win rate

### Volume Requirements

Entries with volume > 1.5x average showed:
- 68% win rate vs 52% without volume confirmation
- Average R-multiple of 1.3R vs 0.7R
- Fewer time-stop exits (15% vs 32%)

### Pullback Depth

Optimal pullback range: 0.3% - 0.8% below VWAP
- Shallower pullbacks (<0.3%): Often false breaks
- Deeper pullbacks (>0.8%): Lower success rate, larger stops needed

## Recommendations

1. Wait minimum 30 minutes after open before taking VWAP Reclaim entries
2. Require volume surge on reclaim candle (>1.5x 20-bar average)
3. Target pullbacks in 0.3%-0.8% range for optimal risk/reward

## Data Source

Paper trading results from 2026-01-01 to 2026-02-15. 156 trades analyzed.
""",
        tags=["vwap", "timing", "entry", "research"],
    )

    # 2. ORB Gap Size Analysis
    await debrief_service.create_document(
        category="research",
        title="ORB Gap Size Analysis",
        content="""# ORB Gap Size Analysis

## Purpose

Evaluate the relationship between overnight gap percentage and ORB Breakout success rates.

## Methodology

Analyzed 1,842 ORB Breakout trades from backtest (35 months of data).

## Results by Gap Size

| Gap Range | Win Rate | Avg R | Sample Size |
|-----------|----------|-------|-------------|
| 1.0-2.0%  | 48%      | 0.42R | 412         |
| 2.0-3.0%  | 55%      | 0.85R | 687         |
| 3.0-5.0%  | 61%      | 1.12R | 521         |
| 5.0%+     | 58%      | 0.95R | 222         |

## Key Observations

1. Sweet spot appears to be 2.5%-4.0% gap range
2. Very large gaps (>5%) often mean-revert in first hour
3. Small gaps (<2%) lack momentum for T2 targets

## Parameter Recommendation

Current gap threshold of 2.0% is appropriate. Consider increasing to 2.5% for higher quality setups.
""",
        tags=["orb", "gaps", "statistics", "backtest"],
    )

    # 3. AI Scoring Calibration Notes (placeholder)
    await debrief_service.create_document(
        category="ai_report",
        title="AI Scoring Calibration Notes",
        content="""# AI Scoring Calibration Notes

## Status

*This document will be populated when the AI Layer (Sprint 22+) is implemented.*

## Planned Sections

- Setup Quality Engine calibration data
- Pattern recognition confidence thresholds
- Signal strength scoring methodology
- Calibration procedures and validation results

## Notes

Initial calibration will use first 30 days of AI-scored trades to establish baseline metrics.
""",
        tags=["ai", "scoring", "calibration", "placeholder"],
    )


async def _seed_journal_entries(
    debrief_service: DebriefService, trade_ids: list[str], now: datetime
) -> None:
    """Seed mock journal entries for dev mode.

    Creates 10 journal entries of various types spread across the last 2 weeks.
    """
    # Observations (3)
    await debrief_service.create_journal_entry(
        entry_type="observation",
        title="Regime transitions happen faster than expected",
        content="""Noticed that when SPY breaks below the 20-day MA, the shift from bullish_trending
to range_bound happens within 30-45 minutes, not hours.

The RegimeClassifier's 30-minute polling interval might miss quick regime changes.
Consider implementing event-driven regime updates when SPY crosses key levels.

This matters for allocation decisions — by the time we detect range_bound,
we may have already taken 2-3 bullish-biased trades.""",
        tags=["regime-change", "timing", "observation"],
    )

    await debrief_service.create_journal_entry(
        entry_type="observation",
        title="VWAP gap patterns on high-gap days",
        content="""On days where the scanner finds 10+ stocks with gaps > 3%,
VWAP Reclaim setups tend to fail more often.

Hypothesis: High-gap days correlate with strong trending behavior,
so mean-reversion strategies underperform.

Should investigate adding a "gap day severity" filter that reduces VWAP Reclaim
allocation when scanner finds excessive gap counts.""",
        tags=["gap-day", "vwap", "false-breakout"],
    )

    await debrief_service.create_journal_entry(
        entry_type="observation",
        title="Afternoon momentum works best on trend days",
        content="""Reviewing the last 20 Afternoon Momentum trades:
- On trend days (SPY >+0.5%): 75% win rate, avg 1.4R
- On choppy days (SPY ±0.3%): 40% win rate, avg 0.6R

The strategy needs a regime filter. Consider only activating Afternoon Momentum
when RegimeClassifier shows bullish_trending or bearish_trending.""",
        tags=["momentum", "timing", "regime-change"],
    )

    # Trade annotations (2) - link to real trade IDs
    if len(trade_ids) >= 2:
        await debrief_service.create_journal_entry(
            entry_type="trade_annotation",
            title="TSLA — exited too early on T1",
            content="""This trade hit T1 but continued to T2 and beyond.

Entry was clean — ORB with volume confirmation. Stop was appropriate at OR low.

**Mistake:** Took profits at T1 when momentum was still strong. Should have:
1. Held 50% for T2 as per the plan
2. Trailed stop to breakeven on remaining position

**Lesson:** When volume on breakout is >2x average, extend the T2 target or consider trailing.""",
            linked_trade_ids=[trade_ids[0]],
            tags=["early-exit", "patience", "t1-t2"],
        )

        await debrief_service.create_journal_entry(
            entry_type="trade_annotation",
            title="AMD — entered on low volume, paid the price",
            content="""Classic discipline failure. Entry conditions were met
except volume was only 0.8x average.

Took the trade anyway because "AMD always moves" — that's not a strategy, that's gambling.

**Result:** Stopped out for -1R within 15 minutes.

**Rule to add:** No exceptions to volume filter. If volume < 1.2x average,
skip the setup regardless of pattern quality.""",
            linked_trade_ids=[trade_ids[1]],
            tags=["low-volume", "discipline", "rules-violation"],
        )

    # Pattern notes (2)
    await debrief_service.create_journal_entry(
        entry_type="pattern_note",
        title="ORB gap threshold might need to be 3% not 2%",
        content="""After reviewing the ORB Gap Size Analysis document,
I'm considering raising the minimum gap from 2.0% to 3.0%.

The data shows:
- 2.0-3.0% gaps: 55% win rate
- 3.0-5.0% gaps: 61% win rate

This would reduce trade count by ~40% but increase quality significantly.

**Concerns:**
- Fewer opportunities might lead to overtrading on remaining setups
- Some of my best trades were 2.5% gaps

**Next step:** Run a 2-week paper test with 3.0% threshold alongside current 2.0%
and compare results.""",
        tags=["orb", "gap-threshold", "parameter-tuning"],
    )

    await debrief_service.create_journal_entry(
        entry_type="pattern_note",
        title="Regime-based position sizing idea",
        content="""Thinking about dynamic position sizing based on regime:

| Regime | Base Size | Rationale |
|--------|-----------|-----------|
| bullish_trending | 100% | Full conviction |
| bearish_trending | 75% | Counter-trend risk |
| range_bound | 50% | Low edge environment |
| high_volatility | 50% | Larger stops needed |
| crisis | 25% | Preserve capital |

This would be in addition to the current throttle-based sizing.
The Orchestrator could multiply the two factors.

Need to backtest the impact on overall returns vs risk.""",
        tags=["regime-change", "position-sizing", "discipline"],
    )

    # System notes (2)
    await debrief_service.create_journal_entry(
        entry_type="system_note",
        title="Throttle kicks in too aggressively at 3 consecutive losses",
        content="""Observed issue: The PerformanceThrottler triggers REDUCE at 3 consecutive losses,
but this is happening too often during choppy morning sessions.

**Problem:** 3 quick scalp losses (0.3R each = 0.9R total) trigger the same throttle
as 3 full losses (3R total).

**Proposed fix:** Weight the throttle by R-multiple lost, not just loss count. Suggestion:
- Track cumulative R lost in rolling window
- Trigger REDUCE at -2.5R cumulative
- Trigger SUSPEND at -4.0R cumulative

This would prevent excessive throttling on small scalp losses
while still protecting against real drawdowns.""",
        tags=["throttle", "system", "orb-scalp"],
    )

    await debrief_service.create_journal_entry(
        entry_type="system_note",
        title="RegimeClassifier has ~30min lag on regime changes",
        content="""The 30-minute polling interval for regime classification creates noticeable lag.

**Example from 2/25:**
- SPY broke below 20-day MA at 10:15 AM
- RegimeClassifier detected change at 10:30 AM
- Two ORB trades taken between 10:15-10:30 were bullish-biased and stopped out

**Options:**
1. Reduce polling to 15 minutes (more API calls)
2. Add event-driven detection on MA cross events
3. Accept the lag and filter trades manually

Leaning toward option 2 — should be straightforward to add SPY MA cross detection.""",
        tags=["regime-change", "system", "latency"],
    )

    # Additional observation
    await debrief_service.create_journal_entry(
        entry_type="observation",
        title="Earnings catalysts produce bigger moves than momentum catalysts",
        content="""Comparing catalyst types from the last month:

**Earnings-driven gaps:**
- Average gap: 4.2%
- Follow-through rate: 68%
- Average T2 hit rate: 42%

**Momentum/news-driven gaps:**
- Average gap: 2.8%
- Follow-through rate: 51%
- Average T2 hit rate: 28%

**Implication:** Should weight earnings catalysts more heavily in pre-market scanning.
Consider a catalyst_type field in the watchlist that affects position sizing.""",
        tags=["earnings", "catalyst", "momentum", "statistics"],
    )


# ---------------------------------------------------------------------------
# Main factory
# ---------------------------------------------------------------------------


async def create_dev_state() -> AppState:
    """Create AppState with realistic mock data for frontend development.

    Sets up:
    - Real EventBus
    - Real TradeLogger with temp SQLite, seeded with ~20 trades
    - SimulatedBroker with $100K
    - Real HealthMonitor (all components HEALTHY)
    - Real RiskManager (default config)
    - Real OrderManager with 2-3 mock positions
    - Mock ORB strategy
    - SystemClock
    - SystemConfig with password for "argus"

    Returns:
        Complete AppState ready for API testing.
    """
    # Set JWT secret for authentication
    jwt_secret = "dev-jwt-secret-for-argus-command-center-development-minimum-32-chars"
    os.environ["ARGUS_JWT_SECRET"] = jwt_secret
    set_jwt_secret(jwt_secret)

    # Create temp database
    temp_dir = tempfile.mkdtemp(prefix="argus_dev_")
    db_path = f"{temp_dir}/dev.db"
    db = DatabaseManager(db_path)
    await db.initialize()

    # Core components
    event_bus = EventBus()
    clock = SystemClock()
    trade_logger = TradeLogger(db)
    debrief_service = DebriefService(db)

    # Seed trades (12 ORB Breakout + 6 ORB Scalp + 8 VWAP Reclaim + 6 Afternoon Momentum)
    trades = _generate_mock_trades()
    for trade in trades:
        await trade_logger.log_trade(trade)

    # Seed orchestrator decisions
    now = datetime.now(UTC)
    await _seed_orchestrator_decisions(trade_logger, now)

    # Seed debrief content (briefings, documents, journal entries)
    await _seed_briefings(debrief_service, now)
    await _seed_documents(debrief_service)
    # Get trade IDs for linking journal entries
    recent_trades = await trade_logger.query_trades(limit=10)
    trade_ids = [t["id"] for t in recent_trades]
    await _seed_journal_entries(debrief_service, trade_ids, now)

    # Broker with $100K
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()

    # Config with dev password and goals
    api_config = ApiConfig(
        enabled=True,
        password_hash=hash_password("argus"),
        jwt_secret_env="ARGUS_JWT_SECRET",
    )
    goals_config = GoalsConfig(monthly_target_usd=5000.0)
    system_config = SystemConfig(api=api_config, goals=goals_config)
    health_config = HealthConfig()

    # Health monitor
    health_monitor = HealthMonitor(
        event_bus=event_bus,
        clock=clock,
        config=health_config,
        broker=broker,
        trade_logger=trade_logger,
    )
    await health_monitor.start()

    # Mark all components as healthy
    health_monitor.update_component(
        "broker", ComponentStatus.HEALTHY, "Connected to SimulatedBroker"
    )
    health_monitor.update_component(
        "data_service", ComponentStatus.HEALTHY, "Mock data service active"
    )
    health_monitor.update_component("order_manager", ComponentStatus.HEALTHY, "Processing orders")
    health_monitor.update_component(
        "risk_manager", ComponentStatus.HEALTHY, "Risk evaluation active"
    )
    health_monitor.update_component("strategy_orb", ComponentStatus.HEALTHY, "ORB Breakout running")
    health_monitor.update_component(
        "strategy_orb_scalp", ComponentStatus.HEALTHY, "ORB Scalp running"
    )
    health_monitor.update_component(
        "strategy_vwap_reclaim", ComponentStatus.HEALTHY, "VWAP Reclaim running"
    )
    health_monitor.update_component(
        "strategy_afternoon_momentum", ComponentStatus.HEALTHY, "Afternoon Momentum running"
    )

    # Risk manager
    risk_config = RiskConfig()
    risk_manager = RiskManager(
        config=risk_config,
        broker=broker,
        event_bus=event_bus,
        clock=clock,
    )
    await risk_manager.initialize()

    # Order manager
    order_manager_config = OrderManagerConfig()
    order_manager = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=order_manager_config,
        trade_logger=trade_logger,
    )
    await order_manager.start()

    # Inject mock positions
    now = datetime.now(UTC)
    mock_positions = _create_mock_positions(now)
    for pos in mock_positions:
        if pos.symbol not in order_manager._managed_positions:
            order_manager._managed_positions[pos.symbol] = []
        order_manager._managed_positions[pos.symbol].append(pos)

    # Mock strategies with Pattern Library fields (Sprint 21a)
    # Calculate daily P&L and trade counts by strategy
    orb_todays_trades = [
        t for t in trades
        if t.exit_time.date() == now.date() and t.strategy_id == "orb_breakout"
    ]
    scalp_todays_trades = [
        t for t in trades
        if t.exit_time.date() == now.date() and t.strategy_id == "orb_scalp"
    ]
    vwap_todays_trades = [
        t for t in trades
        if t.exit_time.date() == now.date() and t.strategy_id == "vwap_reclaim"
    ]
    afternoon_todays_trades = [
        t for t in trades
        if t.exit_time.date() == now.date() and t.strategy_id == "afternoon_momentum"
    ]

    # ORB Breakout config with backtest summary and operating window
    orb_config = OrbBreakoutConfig(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        family="orb_family",
        description_short=(
            "Exploits gapping stocks breaking out of the first 5 minutes' "
            "high with volume confirmation."
        ),
        time_window_display="9:35–11:30 AM",
        operating_window=OperatingWindow(
            earliest_entry="09:35",
            latest_entry="11:30",
            force_close="15:50",
        ),
        backtest_summary=BacktestSummaryConfig(
            status="validated",
            wfe_pnl=28450.0,
            oos_sharpe=2.15,
            total_trades=1842,
            data_months=35,
            last_run="2026-02-20",
        ),
    )
    mock_orb_breakout = MockStrategy(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        is_active=True,
        pipeline_stage="paper_trading",
        allocated_capital=20_000.0,  # 20% of $100k
        daily_pnl=sum(t.net_pnl for t in orb_todays_trades),
        trade_count_today=len(orb_todays_trades),
        config=orb_config,
        # Healthy strategy — no throttle issues
        consecutive_losses=1,
        rolling_sharpe=1.25,
        drawdown_pct=0.018,
    )

    # ORB Scalp config with backtest summary and operating window
    scalp_config = OrbScalpConfig(
        strategy_id="orb_scalp",
        name="ORB Scalp",
        version="1.0.0",
        family="orb_family",
        description_short=(
            "Quick 0.3R scalp on the same opening range breakout pattern, "
            "exiting within 120 seconds."
        ),
        time_window_display="9:45–11:30 AM",
        operating_window=OperatingWindow(
            earliest_entry="09:45",
            latest_entry="11:30",
            force_close="15:50",
        ),
        backtest_summary=BacktestSummaryConfig(
            status="validated",
            wfe_pnl=8920.0,
            oos_sharpe=1.85,
            total_trades=3156,
            data_months=35,
            last_run="2026-02-22",
        ),
    )
    mock_orb_scalp = MockStrategy(
        strategy_id="orb_scalp",
        name="ORB Scalp",
        version="1.0.0",
        is_active=True,  # Still active, just throttled
        pipeline_stage="paper_trading",
        allocated_capital=8_000.0,  # 10% of $100k — THROTTLED (REDUCE)
        daily_pnl=sum(t.net_pnl for t in scalp_todays_trades),
        trade_count_today=len(scalp_todays_trades),
        config=scalp_config,
        # Throttled strategy — 3 consecutive losses triggered REDUCE
        consecutive_losses=3,
        rolling_sharpe=-0.12,
        drawdown_pct=0.042,
    )

    # VWAP Reclaim config with backtest summary and operating window
    vwap_config = VwapReclaimConfig(
        strategy_id="vwap_reclaim",
        name="VWAP Reclaim",
        version="1.0.0",
        family="mean_reversion",
        description_short=(
            "Enters long when a gapping stock pulls back below VWAP, "
            "then reclaims above on volume."
        ),
        time_window_display="10:00 AM–12:00 PM",
        operating_window=OperatingWindow(
            earliest_entry="10:00",
            latest_entry="12:00",
            force_close="15:50",
        ),
        backtest_summary=BacktestSummaryConfig(
            status="validated",
            wfe_pnl=15820.0,
            oos_sharpe=1.49,
            total_trades=59556,
            data_months=35,
            last_run="2026-02-25",
        ),
    )
    mock_vwap_reclaim = MockStrategy(
        strategy_id="vwap_reclaim",
        name="VWAP Reclaim",
        version="1.0.0",
        is_active=True,
        pipeline_stage="paper_trading",
        allocated_capital=25_000.0,  # 25% of $100k — received +5% from ORB Scalp throttle
        daily_pnl=sum(t.net_pnl for t in vwap_todays_trades),
        trade_count_today=len(vwap_todays_trades),
        config=vwap_config,
        # Healthy strategy — no throttle issues
        consecutive_losses=0,
        rolling_sharpe=0.98,
        drawdown_pct=0.015,
    )

    # Afternoon Momentum config with backtest summary and operating window
    afternoon_config = AfternoonMomentumConfig(
        strategy_id="afternoon_momentum",
        name="Afternoon Momentum",
        version="1.0.0",
        family="momentum",
        description_short=(
            "Catches afternoon consolidation breakouts in gapping stocks "
            "between 2:00–3:30 PM."
        ),
        time_window_display="2:00–3:30 PM",
        operating_window=OperatingWindow(
            earliest_entry="14:00",
            latest_entry="15:30",
            force_close="15:45",
        ),
        backtest_summary=BacktestSummaryConfig(
            status="validated",
            wfe_pnl=12340.0,
            oos_sharpe=1.72,
            total_trades=1152,
            data_months=35,
            last_run="2026-02-26",
        ),
    )
    mock_afternoon_momentum = MockStrategy(
        strategy_id="afternoon_momentum",
        name="Afternoon Momentum",
        version="1.0.0",
        is_active=True,
        pipeline_stage="paper_trading",
        allocated_capital=25_000.0,  # 25% of $100k — received +5% from ORB Scalp throttle
        daily_pnl=sum(t.net_pnl for t in afternoon_todays_trades),
        trade_count_today=len(afternoon_todays_trades),
        config=afternoon_config,
        # Healthy strategy — no throttle issues
        consecutive_losses=0,
        rolling_sharpe=1.42,
        drawdown_pct=0.012,
    )

    # Mock orchestrator
    mock_orchestrator = _create_mock_orchestrator(now)

    # Mock watchlist
    mock_watchlist = _create_mock_watchlist(now)

    app_state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        data_service=None,
        orchestrator=mock_orchestrator,  # type: ignore[arg-type]
        strategies={
            "orb_breakout": mock_orb_breakout,  # type: ignore[dict-item]
            "orb_scalp": mock_orb_scalp,  # type: ignore[dict-item]
            "vwap_reclaim": mock_vwap_reclaim,  # type: ignore[dict-item]
            "afternoon_momentum": mock_afternoon_momentum,  # type: ignore[dict-item]
        },
        clock=clock,
        config=system_config,
        start_time=time.time(),
        debrief_service=debrief_service,
    )

    # Inject mock watchlist for dev mode
    app_state._mock_watchlist = mock_watchlist  # type: ignore[attr-defined]

    return app_state

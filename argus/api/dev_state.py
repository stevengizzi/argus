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

from argus.analytics.trade_logger import TradeLogger
from argus.api.auth import hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.routes.watchlist import SparklinePoint, VwapState, WatchlistItem
from argus.core.clock import SystemClock
from argus.core.config import (
    AfternoonMomentumConfig,
    ApiConfig,
    BacktestSummaryConfig,
    HealthConfig,
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
    """Seed mock orchestrator decisions for dev mode."""
    # Log some sample orchestrator decisions
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()

    # Today's ORB Breakout allocation (20%)
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
    )

    # Today's ORB Scalp allocation (20%)
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
    )

    # Today's VWAP Reclaim allocation (20%)
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
    )

    # Today's Afternoon Momentum allocation (20%)
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
    )

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
        },
        rationale="SPY above both SMAs with positive momentum",
    )

    # Yesterday's ORB Breakout allocation (20%)
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
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
    )

    # Yesterday's ORB Scalp allocation (20%)
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
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
    )

    # Yesterday's VWAP Reclaim allocation (20%)
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
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
    )

    # Yesterday's Afternoon Momentum allocation (20%)
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
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
    )

    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="eod_review",
        strategy_id=None,
        details={"regime": "bullish_trending"},
        rationale="End of day review",
    )


def _create_mock_orchestrator(now: datetime) -> MockOrchestrator:
    """Create a mock orchestrator for dev mode."""
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

    # Mock allocations: 20% each strategy + 20% reserve = 100%
    # With 4 strategies and equal weight: (100% - 20% reserve) / 4 = 20% each
    allocations = {
        "orb_breakout": StrategyAllocation(
            strategy_id="orb_breakout",
            allocation_pct=0.20,
            allocation_dollars=20000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 20% allocation (equal-weight, 4 strategies)",
        ),
        "orb_scalp": StrategyAllocation(
            strategy_id="orb_scalp",
            allocation_pct=0.20,
            allocation_dollars=20000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 20% allocation (equal-weight, 4 strategies)",
        ),
        "vwap_reclaim": StrategyAllocation(
            strategy_id="vwap_reclaim",
            allocation_pct=0.20,
            allocation_dollars=20000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 20% allocation (equal-weight, 4 strategies)",
        ),
        "afternoon_momentum": StrategyAllocation(
            strategy_id="afternoon_momentum",
            allocation_pct=0.20,
            allocation_dollars=20000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 20% allocation (equal-weight, 4 strategies)",
        ),
    }

    return MockOrchestrator(
        _config=config,
        _current_regime=MarketRegime.BULLISH_TRENDING,
        _current_allocations=allocations,
        _current_indicators=indicators,
        _last_regime_check=now - timedelta(minutes=30),
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

    # Seed trades (12 ORB Breakout + 6 ORB Scalp + 8 VWAP Reclaim + 6 Afternoon Momentum)
    trades = _generate_mock_trades()
    for trade in trades:
        await trade_logger.log_trade(trade)

    # Seed orchestrator decisions
    now = datetime.now(UTC)
    await _seed_orchestrator_decisions(trade_logger, now)

    # Broker with $100K
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()

    # Config with dev password
    api_config = ApiConfig(
        enabled=True,
        password_hash=hash_password("argus"),
        jwt_secret_env="ARGUS_JWT_SECRET",
    )
    system_config = SystemConfig(api=api_config)
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

    # ORB Breakout config with backtest summary
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
        allocated_capital=20_000.0,  # 20% of $100k (4 strategies + 20% reserve)
        daily_pnl=sum(t.net_pnl for t in orb_todays_trades),
        trade_count_today=len(orb_todays_trades),
        config=orb_config,
    )

    # ORB Scalp config with backtest summary
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
        is_active=True,
        pipeline_stage="paper_trading",
        allocated_capital=20_000.0,  # 20% of $100k (4 strategies + 20% reserve)
        daily_pnl=sum(t.net_pnl for t in scalp_todays_trades),
        trade_count_today=len(scalp_todays_trades),
        config=scalp_config,
    )

    # VWAP Reclaim config with backtest summary
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
        allocated_capital=20_000.0,  # 20% of $100k (4 strategies + 20% reserve)
        daily_pnl=sum(t.net_pnl for t in vwap_todays_trades),
        trade_count_today=len(vwap_todays_trades),
        config=vwap_config,
    )

    # Afternoon Momentum config with backtest summary
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
        allocated_capital=20_000.0,  # 20% of $100k (4 strategies + 20% reserve)
        daily_pnl=sum(t.net_pnl for t in afternoon_todays_trades),
        trade_count_today=len(afternoon_todays_trades),
        config=afternoon_config,
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
    )

    # Inject mock watchlist for dev mode
    app_state._mock_watchlist = mock_watchlist  # type: ignore[attr-defined]

    return app_state

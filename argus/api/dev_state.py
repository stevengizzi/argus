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
from argus.core.clock import SystemClock
from argus.core.config import (
    ApiConfig,
    HealthConfig,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OrchestratorConfig,
    OrderManagerConfig,
    RiskConfig,
    StrategyConfig,
    SystemConfig,
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

    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        """Mock rebalance - returns current allocations unchanged."""
        return self._current_allocations


# ---------------------------------------------------------------------------
# Trade generation
# ---------------------------------------------------------------------------


def _generate_mock_trades(orb_count: int = 15, scalp_count: int = 8) -> list[Trade]:
    """Generate realistic mock trades for seeding the database.

    Creates a mix of:
    - ~55% wins
    - ~40% losses
    - ~5% breakeven

    For ORB Breakout: 5-120 min holds, 1R/2R targets
    For ORB Scalp: 30-120s holds, 0.3R targets, smaller P&L
    """
    # ORB Breakout uses these symbols
    orb_symbols = ["NVDA", "AAPL", "AMD", "META"]
    # ORB Scalp uses these symbols (distinct from ORB positions)
    scalp_symbols = ["TSLA", "GOOG", "AMZN", "MSFT"]

    symbol_prices = {
        "TSLA": (180.0, 250.0),
        "NVDA": (700.0, 950.0),
        "AAPL": (170.0, 195.0),
        "AMD": (120.0, 180.0),
        "META": (450.0, 550.0),
        "GOOG": (150.0, 180.0),
        "AMZN": (180.0, 220.0),
        "MSFT": (400.0, 450.0),
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
    ) -> Trade:
        """Generate a single trade with strategy-specific parameters."""
        # Spread trades over the last 30 days
        days_ago = random.randint(0, 29)
        trade_date = now - timedelta(days=days_ago)
        # Set entry time to market hours (9:45 AM - 3:30 PM ET)
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

        # Position sizing based on $1000-$3000 risk per trade (scalp uses smaller)
        if strategy_id == "orb_scalp":
            risk_amount = random.uniform(500, 1500)
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

    return trades


def _create_mock_positions(now: datetime) -> list[ManagedPosition]:
    """Create mock managed positions for dev mode.

    Creates:
    - 3 ORB Breakout positions (5-30 min holds)
    - 2 ORB Scalp positions (30-90s holds, different symbols)
    """
    positions = []

    # --- ORB Breakout Positions ---

    # Position 1: NVDA - entered 30 minutes ago, T1 hit, stop at breakeven
    entry_time_1 = now - timedelta(minutes=30)
    positions.append(
        ManagedPosition(
            symbol="NVDA",
            strategy_id="orb_breakout",
            entry_price=875.50,
            entry_time=entry_time_1,
            shares_total=100,
            shares_remaining=50,  # T1 took 50 shares
            stop_price=875.50,  # Moved to breakeven
            original_stop_price=868.00,
            stop_order_id="stop_nvda_001",
            t1_price=883.00,
            t1_order_id=None,  # T1 filled
            t1_shares=50,
            t1_filled=True,
            t2_price=890.50,
            high_watermark=886.25,
            realized_pnl=375.0,  # 50 * 7.50
        )
    )

    # Position 2: AAPL - entered 15 minutes ago, still waiting for T1
    entry_time_2 = now - timedelta(minutes=15)
    positions.append(
        ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=185.80,
            entry_time=entry_time_2,
            shares_total=150,
            shares_remaining=150,
            stop_price=183.50,
            original_stop_price=183.50,
            stop_order_id="stop_aapl_001",
            t1_price=188.10,
            t1_order_id="t1_aapl_001",
            t1_shares=75,
            t1_filled=False,
            t2_price=190.40,
            high_watermark=186.90,
            realized_pnl=0.0,
        )
    )

    # Position 3: AMD - just entered, all targets pending
    entry_time_3 = now - timedelta(minutes=5)
    positions.append(
        ManagedPosition(
            symbol="AMD",
            strategy_id="orb_breakout",
            entry_price=155.25,
            entry_time=entry_time_3,
            shares_total=200,
            shares_remaining=200,
            stop_price=152.75,
            original_stop_price=152.75,
            stop_order_id="stop_amd_001",
            t1_price=157.75,
            t1_order_id="t1_amd_001",
            t1_shares=100,
            t1_filled=False,
            t2_price=160.25,
            high_watermark=155.60,
            realized_pnl=0.0,
        )
    )

    # --- ORB Scalp Positions (shorter holds, different symbols) ---

    # Position 4: TSLA - scalp entered 45 seconds ago, waiting for target
    entry_time_4 = now - timedelta(seconds=45)
    positions.append(
        ManagedPosition(
            symbol="TSLA",
            strategy_id="orb_scalp",
            entry_price=225.80,
            entry_time=entry_time_4,
            shares_total=80,
            shares_remaining=80,
            stop_price=224.65,  # Tighter stop for scalp (midpoint placement)
            original_stop_price=224.65,
            stop_order_id="stop_tsla_scalp_001",
            t1_price=226.15,  # 0.3R target
            t1_order_id="t1_tsla_scalp_001",
            t1_shares=80,  # Scalp exits 100% at T1
            t1_filled=False,
            t2_price=0.0,  # No T2 for scalp (0.0 = disabled)
            high_watermark=225.95,
            realized_pnl=0.0,
        )
    )

    # Position 5: GOOG - scalp entered 90 seconds ago, approaching target
    entry_time_5 = now - timedelta(seconds=90)
    positions.append(
        ManagedPosition(
            symbol="GOOG",
            strategy_id="orb_scalp",
            entry_price=165.40,
            entry_time=entry_time_5,
            shares_total=100,
            shares_remaining=100,
            stop_price=164.55,  # Tighter stop for scalp
            original_stop_price=164.55,
            stop_order_id="stop_goog_scalp_001",
            t1_price=165.66,  # 0.3R target (~$0.26 gain on ~$0.85 risk)
            t1_order_id="t1_goog_scalp_001",
            t1_shares=100,  # Scalp exits 100% at T1
            t1_filled=False,
            t2_price=0.0,  # No T2 for scalp (0.0 = disabled)
            high_watermark=165.58,
            realized_pnl=0.0,
        )
    )

    return positions


async def _seed_orchestrator_decisions(trade_logger: TradeLogger, now: datetime) -> None:
    """Seed mock orchestrator decisions for dev mode."""
    # Log some sample orchestrator decisions
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()

    # Today's ORB Breakout allocation
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={
            "allocation_pct": 0.30,
            "allocation_dollars": 30000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 30% allocation",
    )

    # Today's ORB Scalp allocation
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_scalp",
        details={
            "allocation_pct": 0.30,
            "allocation_dollars": 30000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 30% allocation",
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

    # Yesterday's ORB Breakout allocation
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={
            "allocation_pct": 0.30,
            "allocation_dollars": 30000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 30% allocation",
    )

    # Yesterday's ORB Scalp allocation
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="allocation",
        strategy_id="orb_scalp",
        details={
            "allocation_pct": 0.30,
            "allocation_dollars": 30000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 30% allocation",
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

    # Mock allocations
    allocations = {
        "orb_breakout": StrategyAllocation(
            strategy_id="orb_breakout",
            allocation_pct=0.30,
            allocation_dollars=30000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 30% allocation",
        ),
        "orb_scalp": StrategyAllocation(
            strategy_id="orb_scalp",
            allocation_pct=0.30,
            allocation_dollars=30000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 30% allocation",
        ),
    }

    return MockOrchestrator(
        _config=config,
        _current_regime=MarketRegime.BULLISH_TRENDING,
        _current_allocations=allocations,
        _current_indicators=indicators,
        _last_regime_check=now - timedelta(minutes=30),
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

    # Seed trades (15 ORB Breakout + 8 ORB Scalp)
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

    # Mock strategies
    orb_config = OrbBreakoutConfig(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
    )
    # Calculate daily P&L and trade counts by strategy
    orb_todays_trades = [
        t for t in trades
        if t.exit_time.date() == now.date() and t.strategy_id == "orb_breakout"
    ]
    scalp_todays_trades = [
        t for t in trades
        if t.exit_time.date() == now.date() and t.strategy_id == "orb_scalp"
    ]

    mock_orb_breakout = MockStrategy(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        is_active=True,
        pipeline_stage="paper",
        allocated_capital=50_000.0,
        daily_pnl=sum(t.net_pnl for t in orb_todays_trades),
        trade_count_today=len(orb_todays_trades),
        config=orb_config,
    )

    scalp_config = OrbScalpConfig(
        strategy_id="orb_scalp",
        name="ORB Scalp",
        version="1.0.0",
    )
    mock_orb_scalp = MockStrategy(
        strategy_id="orb_scalp",
        name="ORB Scalp",
        version="1.0.0",
        is_active=True,
        pipeline_stage="paper",
        allocated_capital=50_000.0,
        daily_pnl=sum(t.net_pnl for t in scalp_todays_trades),
        trade_count_today=len(scalp_todays_trades),
        config=scalp_config,
    )

    # Mock orchestrator
    mock_orchestrator = _create_mock_orchestrator(now)

    return AppState(
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
        },
        clock=clock,
        config=system_config,
        start_time=time.time(),
    )

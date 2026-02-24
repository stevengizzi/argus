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
    OrchestratorConfig,
    OrderManagerConfig,
    RiskConfig,
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
    config: OrbBreakoutConfig

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
    def _config(self) -> OrbBreakoutConfig:
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

    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        """Mock rebalance - returns current allocations unchanged."""
        return self._current_allocations


# ---------------------------------------------------------------------------
# Trade generation
# ---------------------------------------------------------------------------


def _generate_mock_trades(count: int = 20) -> list[Trade]:
    """Generate realistic mock trades for seeding the database.

    Creates a mix of:
    - ~55% wins
    - ~40% losses
    - ~5% breakeven

    With exit reasons: target_1, stop_loss, time_stop, eod
    """
    symbols = ["TSLA", "NVDA", "AAPL", "AMD", "META"]
    symbol_prices = {
        "TSLA": (180.0, 250.0),
        "NVDA": (700.0, 950.0),
        "AAPL": (170.0, 195.0),
        "AMD": (120.0, 180.0),
        "META": (450.0, 550.0),
    }

    trades: list[Trade] = []
    now = datetime.now(UTC)

    for _i in range(count):
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

        # Position sizing based on $1000-$3000 risk per trade
        risk_amount = random.uniform(1000, 3000)
        shares = max(10, int(risk_amount / stop_distance))

        # Calculate exit based on outcome
        if outcome == TradeOutcome.WIN:
            # Win: hit T1 (1R) or T2 (2R)
            r_multiple = random.choice([1.0, 1.5, 2.0])
            exit_price = round(entry_price + (stop_distance * r_multiple), 2)
            exit_reason = ExitReason.TARGET_1 if r_multiple <= 1.0 else ExitReason.TARGET_2
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

        # Hold duration: 5 minutes to 2 hours
        hold_minutes = random.randint(5, 120)
        exit_time = entry_time + timedelta(minutes=hold_minutes)

        # Commission: $1 per 100 shares (minimum $1)
        commission = max(1.0, round(shares / 100, 2))

        trade = Trade(
            strategy_id="orb_breakout",
            symbol=symbol,
            asset_class=AssetClass.US_STOCKS,
            side=OrderSide.BUY,
            entry_price=entry_price,
            entry_time=entry_time,
            exit_price=exit_price,
            exit_time=exit_time,
            shares=shares,
            stop_price=stop_price,
            target_prices=[
                round(entry_price + stop_distance, 2),
                round(entry_price + stop_distance * 2, 2),
            ],
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            commission=commission,
            r_multiple=r_multiple,
            rationale="ORB breakout with volume confirmation",
        )

        trades.append(trade)

    return trades


def _create_mock_positions(now: datetime) -> list[ManagedPosition]:
    """Create 2-3 mock managed positions for dev mode."""
    positions = []

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

    # Position 2: TSLA - entered 15 minutes ago, still waiting for T1
    entry_time_2 = now - timedelta(minutes=15)
    positions.append(
        ManagedPosition(
            symbol="TSLA",
            strategy_id="orb_breakout",
            entry_price=225.80,
            entry_time=entry_time_2,
            shares_total=150,
            shares_remaining=150,
            stop_price=222.50,
            original_stop_price=222.50,
            stop_order_id="stop_tsla_001",
            t1_price=229.10,
            t1_order_id="t1_tsla_001",
            t1_shares=75,
            t1_filled=False,
            t2_price=232.40,
            high_watermark=226.90,
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

    return positions


async def _seed_orchestrator_decisions(trade_logger: TradeLogger, now: datetime) -> None:
    """Seed mock orchestrator decisions for dev mode."""
    # Log some sample orchestrator decisions
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()

    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={
            "allocation_pct": 0.40,
            "allocation_dollars": 40000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 40% allocation",
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

    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={
            "allocation_pct": 0.35,
            "allocation_dollars": 35000.0,
            "throttle_action": "none",
            "eligible": True,
            "regime": "bullish_trending",
        },
        rationale="Active: 35% allocation",
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
            allocation_pct=0.40,
            allocation_dollars=40000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 40% allocation",
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

    # Seed trades
    trades = _generate_mock_trades(20)
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
    health_monitor.update_component(
        "order_manager", ComponentStatus.HEALTHY, "Processing orders"
    )
    health_monitor.update_component(
        "risk_manager", ComponentStatus.HEALTHY, "Risk evaluation active"
    )
    health_monitor.update_component(
        "strategy_orb", ComponentStatus.HEALTHY, "ORB Breakout running"
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

    # Mock strategy
    orb_config = OrbBreakoutConfig(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
    )
    mock_strategy = MockStrategy(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        is_active=True,
        pipeline_stage="paper",
        allocated_capital=100_000.0,
        daily_pnl=sum(t.net_pnl for t in trades if t.exit_time.date() == now.date()),
        trade_count_today=sum(1 for t in trades if t.exit_time.date() == now.date()),
        config=orb_config,
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
        strategies={"orb_breakout": mock_strategy},  # type: ignore[dict-item]
        clock=clock,
        config=system_config,
        start_time=time.time(),
    )

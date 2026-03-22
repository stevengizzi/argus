"""BacktestEngine — Production-code backtesting with synchronous dispatch.

Wires real ARGUS components (strategies, indicators, risk, orders)
in fast-replay mode using SyncEventBus instead of async EventBus.
No tick synthesis — uses bar-level fill model (worst-case priority).

Decision references:
- DEC-055: BacktestDataService (Step-Driven DataService)
- DEC-056: Backtest Database Naming Convention
- Sprint 27 S3: Component assembly + strategy factory
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from argus.analytics.trade_logger import TradeLogger
from argus.backtest.backtest_data_service import BacktestDataService
from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.metrics import BacktestResult
from argus.core.clock import FixedClock
from argus.core.config import (
    AfternoonMomentumConfig,
    BullFlagConfig,
    FlatTopBreakoutConfig,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OrderManagerConfig,
    RedToGreenConfig,
    RiskConfig,
    VwapReclaimConfig,
    load_yaml_file,
)
from argus.core.events import CandleEvent
from argus.core.risk_manager import RiskManager
from argus.core.sync_event_bus import SyncEventBus
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker, SimulatedSlippage
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class BacktestEngine:
    """Production-code backtesting engine with synchronous dispatch.

    Wires real ARGUS components (strategies, indicators, risk, orders)
    in fast-replay mode using SyncEventBus instead of async EventBus.
    No tick synthesis — uses bar-level fill model (worst-case priority).

    Usage:
        config = BacktestEngineConfig(start_date=..., end_date=...)
        engine = BacktestEngine(config)
        result = await engine.run()
    """

    def __init__(self, config: BacktestEngineConfig) -> None:
        """Initialize the BacktestEngine.

        Args:
            config: BacktestEngineConfig with strategy, date range, and
                execution parameters.
        """
        self._config = config

        # Components initialized in _setup()
        self._event_bus: SyncEventBus | None = None
        self._clock: FixedClock | None = None
        self._db_manager: DatabaseManager | None = None
        self._trade_logger: TradeLogger | None = None
        self._broker: SimulatedBroker | None = None
        self._data_service: BacktestDataService | None = None
        self._risk_manager: RiskManager | None = None
        self._order_manager: OrderManager | None = None
        self._strategy: BaseStrategy | None = None
        self._db_path: Path | None = None

        # Trading days populated by run() (S5)
        self._trading_days: list[object] = []

    async def run(self) -> BacktestResult:
        """Run the backtest end-to-end.

        Sets up all components, runs the execution loop (S4/S5),
        computes results, and tears down.

        Returns:
            BacktestResult with metrics from the run.
        """
        await self._setup()
        # Execution loop added in S4/S5
        result = self._empty_result()
        await self._teardown()
        return result

    async def _setup(self) -> None:
        """Initialize all production components for the backtest."""
        # Create output directory
        output_dir = Path(self._config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate database filename (DEC-056)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        start_str = self._config.start_date.strftime("%Y%m%d")
        end_str = self._config.end_date.strftime("%Y%m%d")
        db_filename = (
            f"{self._config.strategy_id}_{start_str}_{end_str}_{timestamp}.db"
        )
        self._db_path = output_dir / db_filename

        # Initialize SyncEventBus (NOT EventBus)
        self._event_bus = SyncEventBus()

        # Initialize FixedClock at pre-market of start_date
        start = self._config.start_date
        initial_time = datetime(
            start.year, start.month, start.day, 9, 25, 0, tzinfo=ET
        ).astimezone(UTC)
        self._clock = FixedClock(initial_time)

        # Initialize DatabaseManager + TradeLogger
        self._db_manager = DatabaseManager(self._db_path)
        await self._db_manager.initialize()
        self._trade_logger = TradeLogger(self._db_manager)

        # Initialize SimulatedBroker
        slippage = SimulatedSlippage(
            mode="fixed",
            fixed_amount=self._config.slippage_per_share,
        )
        self._broker = SimulatedBroker(
            initial_cash=self._config.initial_cash,
            slippage=slippage,
        )
        await self._broker.connect()

        # Initialize BacktestDataService with SyncEventBus
        self._data_service = BacktestDataService(self._event_bus)  # type: ignore[arg-type]

        # Load configs from YAML
        config_dir = Path("config")
        risk_config = self._load_risk_config(config_dir)
        order_manager_config = self._load_order_manager_config(config_dir)

        # Initialize RiskManager
        self._risk_manager = RiskManager(
            config=risk_config,
            broker=self._broker,
            event_bus=self._event_bus,  # type: ignore[arg-type]
            clock=self._clock,
        )
        await self._risk_manager.initialize()

        # Initialize OrderManager
        self._order_manager = OrderManager(
            event_bus=self._event_bus,  # type: ignore[arg-type]
            broker=self._broker,
            clock=self._clock,
            config=order_manager_config,
            trade_logger=self._trade_logger,
        )
        await self._order_manager.start()

        # Initialize strategy via factory
        self._strategy = self._create_strategy(config_dir)
        self._strategy.allocated_capital = self._config.initial_cash

        # Subscribe engine's candle handler to SyncEventBus
        self._event_bus.subscribe(CandleEvent, self._on_candle_event)

        # Apply log level from config
        logging.getLogger("argus").setLevel(self._config.log_level)

        logger.info(
            "BacktestEngine initialized: db=%s, strategy=%s, initial_cash=%.2f",
            self._db_path,
            self._config.strategy_type,
            self._config.initial_cash,
        )

    async def _on_candle_event(self, event: CandleEvent) -> None:
        """Route candle events to the strategy and risk manager.

        Args:
            event: The CandleEvent from the SyncEventBus.
        """
        if self._strategy is None:
            return

        signal = await self._strategy.on_candle(event)
        if signal is not None and self._risk_manager is not None:
            result = await self._risk_manager.evaluate_signal(signal)
            await self._event_bus.publish(result)  # type: ignore[union-attr, arg-type]

    def _create_strategy(self, config_dir: Path) -> BaseStrategy:
        """Create strategy instance from config.strategy_type.

        Handles all 7 strategy types:
        - ORB_BREAKOUT -> OrbBreakoutStrategy
        - ORB_SCALP -> OrbScalpStrategy
        - VWAP_RECLAIM -> VwapReclaimStrategy
        - AFTERNOON_MOMENTUM -> AfternoonMomentumStrategy
        - RED_TO_GREEN -> RedToGreenStrategy
        - BULL_FLAG -> PatternBasedStrategy(BullFlagPattern(), ...)
        - FLAT_TOP_BREAKOUT -> PatternBasedStrategy(FlatTopBreakoutPattern(), ...)

        Args:
            config_dir: Path to the config directory.

        Returns:
            Initialized strategy instance.

        Raises:
            ValueError: If strategy_type is not recognized.
        """
        strategy_type = self._config.strategy_type

        if strategy_type == StrategyType.ORB_BREAKOUT:
            return self._create_orb_breakout_strategy(config_dir)
        elif strategy_type == StrategyType.ORB_SCALP:
            return self._create_orb_scalp_strategy(config_dir)
        elif strategy_type == StrategyType.VWAP_RECLAIM:
            return self._create_vwap_reclaim_strategy(config_dir)
        elif strategy_type == StrategyType.AFTERNOON_MOMENTUM:
            return self._create_afternoon_momentum_strategy(config_dir)
        elif strategy_type == StrategyType.RED_TO_GREEN:
            return self._create_red_to_green_strategy(config_dir)
        elif strategy_type == StrategyType.BULL_FLAG:
            return self._create_bull_flag_strategy(config_dir)
        elif strategy_type == StrategyType.FLAT_TOP_BREAKOUT:
            return self._create_flat_top_breakout_strategy(config_dir)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    # --- Strategy factory methods ---

    def _create_orb_breakout_strategy(
        self, config_dir: Path
    ) -> OrbBreakoutStrategy:
        """Create OrbBreakoutStrategy with config overrides applied.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured OrbBreakoutStrategy.
        """
        orb_file = config_dir / "strategies" / "orb_breakout.yaml"
        if orb_file.exists():
            data = load_yaml_file(orb_file)
            config = OrbBreakoutConfig(**data)
        else:
            config = OrbBreakoutConfig(
                strategy_id="orb_breakout",
                name="ORB Breakout",
            )

        config = self._apply_config_overrides(config)

        return OrbBreakoutStrategy(
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _create_orb_scalp_strategy(
        self, config_dir: Path
    ) -> OrbScalpStrategy:
        """Create OrbScalpStrategy with config overrides applied.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured OrbScalpStrategy.
        """
        scalp_file = config_dir / "strategies" / "orb_scalp.yaml"
        if scalp_file.exists():
            data = load_yaml_file(scalp_file)
            config = OrbScalpConfig(**data)
        else:
            config = OrbScalpConfig(
                strategy_id="orb_scalp",
                name="ORB Scalp",
            )

        config = self._apply_config_overrides(config)

        return OrbScalpStrategy(
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _create_vwap_reclaim_strategy(
        self, config_dir: Path
    ) -> VwapReclaimStrategy:
        """Create VwapReclaimStrategy with config overrides applied.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured VwapReclaimStrategy.
        """
        vwap_file = config_dir / "strategies" / "vwap_reclaim.yaml"
        if vwap_file.exists():
            data = load_yaml_file(vwap_file)
            config = VwapReclaimConfig(**data)
        else:
            config = VwapReclaimConfig(
                strategy_id="strat_vwap_reclaim",
                name="VWAP Reclaim",
            )

        config = self._apply_config_overrides(config)

        return VwapReclaimStrategy(
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _create_afternoon_momentum_strategy(
        self, config_dir: Path
    ) -> AfternoonMomentumStrategy:
        """Create AfternoonMomentumStrategy with config overrides applied.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured AfternoonMomentumStrategy.
        """
        afternoon_file = config_dir / "strategies" / "afternoon_momentum.yaml"
        if afternoon_file.exists():
            data = load_yaml_file(afternoon_file)
            config = AfternoonMomentumConfig(**data)
        else:
            config = AfternoonMomentumConfig(
                strategy_id="strat_afternoon_momentum",
                name="Afternoon Momentum",
            )

        config = self._apply_config_overrides(config)

        return AfternoonMomentumStrategy(
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _create_red_to_green_strategy(
        self, config_dir: Path
    ) -> RedToGreenStrategy:
        """Create RedToGreenStrategy with config overrides applied.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured RedToGreenStrategy.
        """
        r2g_file = config_dir / "strategies" / "red_to_green.yaml"
        if r2g_file.exists():
            data = load_yaml_file(r2g_file)
            config = RedToGreenConfig(**data)
        else:
            config = RedToGreenConfig(
                strategy_id="strat_red_to_green",
                name="Red-to-Green",
            )

        config = self._apply_config_overrides(config)

        return RedToGreenStrategy(
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _create_bull_flag_strategy(
        self, config_dir: Path
    ) -> PatternBasedStrategy:
        """Create PatternBasedStrategy wrapping BullFlagPattern.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured PatternBasedStrategy with BullFlagPattern.
        """
        bull_file = config_dir / "strategies" / "bull_flag.yaml"
        if bull_file.exists():
            data = load_yaml_file(bull_file)
            config = BullFlagConfig(**data)
        else:
            config = BullFlagConfig(
                strategy_id="strat_bull_flag",
                name="Bull Flag",
            )

        config = self._apply_config_overrides(config)
        pattern = BullFlagPattern()

        return PatternBasedStrategy(
            pattern=pattern,
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _create_flat_top_breakout_strategy(
        self, config_dir: Path
    ) -> PatternBasedStrategy:
        """Create PatternBasedStrategy wrapping FlatTopBreakoutPattern.

        Args:
            config_dir: Path to the config directory.

        Returns:
            Configured PatternBasedStrategy with FlatTopBreakoutPattern.
        """
        flat_file = config_dir / "strategies" / "flat_top_breakout.yaml"
        if flat_file.exists():
            data = load_yaml_file(flat_file)
            config = FlatTopBreakoutConfig(**data)
        else:
            config = FlatTopBreakoutConfig(
                strategy_id="strat_flat_top_breakout",
                name="Flat-Top Breakout",
            )

        config = self._apply_config_overrides(config)
        pattern = FlatTopBreakoutPattern()

        return PatternBasedStrategy(
            pattern=pattern,
            config=config,
            data_service=self._data_service,
            clock=self._clock,
        )

    def _apply_config_overrides(self, config: object) -> object:
        """Apply config_overrides from BacktestEngineConfig to a strategy config.

        Overrides are dot-separated keys mapping to strategy config fields.
        For example: {"opening_range_minutes": 15} sets config.opening_range_minutes = 15.

        Args:
            config: The strategy config model to modify.

        Returns:
            Updated config model with overrides applied.
        """
        if not self._config.config_overrides:
            return config  # type: ignore[return-value]

        config_dict = config.model_dump()  # type: ignore[union-attr]
        for key, value in self._config.config_overrides.items():
            # Support dot-separated keys for nested config
            parts = key.split(".")
            target = config_dict
            for part in parts[:-1]:
                if part in target and isinstance(target[part], dict):
                    target = target[part]
                else:
                    break
            else:
                target[parts[-1]] = value
                continue
            # Flat key — set directly if it exists
            if parts[-1] in config_dict:
                config_dict[parts[-1]] = value

        return config.__class__(**config_dict)  # type: ignore[return-value]

    # --- Config loading ---

    def _load_risk_config(self, config_dir: Path) -> RiskConfig:
        """Load risk configuration from YAML.

        Args:
            config_dir: Path to the config directory.

        Returns:
            RiskConfig parsed from YAML or defaults.
        """
        risk_file = config_dir / "risk_limits.yaml"
        if risk_file.exists():
            data = load_yaml_file(risk_file)
            return RiskConfig(**data)
        return RiskConfig()

    def _load_order_manager_config(self, config_dir: Path) -> OrderManagerConfig:
        """Load order manager configuration from YAML.

        Args:
            config_dir: Path to the config directory.

        Returns:
            OrderManagerConfig parsed from YAML or defaults.
        """
        om_file = config_dir / "order_manager.yaml"
        if om_file.exists():
            data = load_yaml_file(om_file)
            return OrderManagerConfig(**data)
        return OrderManagerConfig()

    # --- Result helpers ---

    def _empty_result(self) -> BacktestResult:
        """Return an empty result when there's nothing to compute.

        Returns:
            BacktestResult with zero metrics.
        """
        return BacktestResult(
            strategy_id=self._config.strategy_id,
            start_date=self._config.start_date,
            end_date=self._config.end_date,
            initial_capital=self._config.initial_cash,
            final_equity=self._config.initial_cash,
            trading_days=len(self._trading_days),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_r_multiple=0.0,
            avg_winner_r=0.0,
            avg_loser_r=0.0,
            expectancy=0.0,
            max_drawdown_dollars=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            recovery_factor=0.0,
            avg_hold_minutes=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            largest_win_dollars=0.0,
            largest_loss_dollars=0.0,
            largest_win_r=0.0,
            largest_loss_r=0.0,
        )

    # --- Teardown ---

    async def _teardown(self) -> None:
        """Clean up all components."""
        if self._order_manager is not None:
            await self._order_manager.stop()

        if self._db_manager is not None:
            await self._db_manager.close()

        logger.info("Backtest database saved: %s", self._db_path)

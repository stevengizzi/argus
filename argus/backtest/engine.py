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
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from argus.analytics.trade_logger import TradeLogger
from argus.backtest.backtest_data_service import BacktestDataService
from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.historical_data_feed import HistoricalDataFeed
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
from argus.core.events import CandleEvent, OrderFilledEvent
from argus.core.risk_manager import RiskManager
from argus.core.sync_event_bus import SyncEventBus
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker, SimulatedSlippage
from argus.models.trading import OrderResult, OrderStatus
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

        # Bar data and trading days populated by _load_data()
        self._bar_data: dict[str, pd.DataFrame] = {}
        self._trading_days: list[date] = []

    async def run(self) -> BacktestResult:
        """Run the backtest end-to-end.

        Sets up all components, loads data, runs the day-by-day execution
        loop, computes results, and tears down.

        Returns:
            BacktestResult with metrics from the run.
        """
        await self._setup()
        await self._load_data()

        # Day-by-day execution loop
        watchlist = list(self._bar_data.keys())
        for trading_day in self._trading_days:
            await self._run_trading_day(trading_day, watchlist)

        # Results computation added in S5
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

    # --- Data loading ---

    async def _load_data(self) -> None:
        """Load bar data from HistoricalDataFeed cache.

        Reads Parquet-cached OHLCV-1m data for the configured symbols
        and date range. Extracts trading days from the data.
        """
        symbols = self._config.symbols or []
        if not symbols:
            logger.warning(
                "No symbols configured — backtest will have no data"
            )
            return

        feed = HistoricalDataFeed(
            cache_dir=self._config.cache_dir,
            verify_zero_cost=self._config.verify_zero_cost,
        )

        self._bar_data = await feed.load(
            symbols=symbols,
            start_date=self._config.start_date,
            end_date=self._config.end_date,
        )

        # Extract sorted trading days from loaded data
        all_dates: set[date] = set()
        for df in self._bar_data.values():
            if not df.empty and "trading_date" in df.columns:
                all_dates.update(df["trading_date"].unique())

        self._trading_days = sorted(all_dates)

        logger.info(
            "Loaded data: %d symbols, %d trading days",
            len(self._bar_data),
            len(self._trading_days),
        )

    # --- Day execution ---

    def _get_daily_bars(
        self, trading_day: date, symbols: list[str]
    ) -> pd.DataFrame:
        """Get all bars for the given symbols on the given trading day.

        Returns a DataFrame with bars interleaved chronologically across
        symbols (sorted by timestamp, not grouped by symbol).

        Args:
            trading_day: The date to get bars for.
            symbols: List of symbols to include.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close,
            volume, trading_date, symbol. Empty if no data.
        """
        frames: list[pd.DataFrame] = []

        for symbol in symbols:
            if symbol not in self._bar_data:
                continue

            df = self._bar_data[symbol]
            day_mask = df["trading_date"] == trading_day
            day_df = df[day_mask].copy()

            if len(day_df) > 0:
                day_df["symbol"] = symbol
                frames.append(day_df)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.sort_values("timestamp").reset_index(drop=True)
        return combined

    async def _run_trading_day(
        self, trading_day: date, watchlist: list[str]
    ) -> None:
        """Run a single trading day through the bar-level pipeline.

        Processes bars chronologically across all symbols. No tick
        synthesis — uses bar-level fill model (worst-case priority).

        Args:
            trading_day: The date to simulate.
            watchlist: List of symbols to trade today.
        """
        if (
            self._clock is None
            or self._data_service is None
            or self._strategy is None
            or self._risk_manager is None
            or self._order_manager is None
            or self._broker is None
        ):
            return

        # a. Set clock to pre-market (9:25 AM ET)
        pre_market = datetime(
            trading_day.year,
            trading_day.month,
            trading_day.day,
            9, 25, 0,
            tzinfo=ET,
        ).astimezone(UTC)
        self._clock.set(pre_market)

        # b. Reset daily state
        self._strategy.reset_daily_state()
        await self._risk_manager.reset_daily_state()
        self._order_manager.reset_daily_state()
        self._data_service.reset_daily_state()

        # c. Set strategy watchlist
        self._strategy.set_watchlist(watchlist)

        # d. Get today's bars (all symbols, sorted by timestamp)
        daily_bars = self._get_daily_bars(trading_day, watchlist)
        if daily_bars.empty:
            return

        # e. Process each bar
        for _, row in daily_bars.iterrows():
            symbol: str = row["symbol"]
            bar_ts = row["timestamp"]

            # Normalize timestamp
            if isinstance(bar_ts, pd.Timestamp):
                bar_ts = bar_ts.to_pydatetime()
            if bar_ts.tzinfo is None:
                bar_ts = bar_ts.replace(tzinfo=UTC)

            # i. Advance clock to bar timestamp
            self._clock.set(bar_ts)

            # ii. Set broker price (for market order fills)
            self._broker.set_price(symbol, float(row["close"]))

            # iii. Feed bar to data_service (publishes CandleEvent +
            #      IndicatorEvents via SyncEventBus)
            await self._data_service.feed_bar(
                symbol=symbol,
                timestamp=bar_ts,
                open_=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )

            # iv. After event dispatch: check bracket orders against
            #     this bar's OHLC
            await self._check_bracket_orders(
                symbol=symbol,
                bar_high=float(row["high"]),
                bar_low=float(row["low"]),
                bar_close=float(row["close"]),
                bar_timestamp=bar_ts,
            )

        # f. EOD flatten at configured time
        h, m = map(int, self._config.eod_flatten_time.split(":"))
        eod_dt = datetime(
            trading_day.year,
            trading_day.month,
            trading_day.day,
            h, m, 0,
            tzinfo=ET,
        ).astimezone(UTC)
        self._clock.set(eod_dt)
        await self._order_manager.eod_flatten()

    # --- Bar-level fill model ---

    async def _check_bracket_orders(
        self,
        symbol: str,
        bar_high: float,
        bar_low: float,
        bar_close: float,
        bar_timestamp: datetime,
    ) -> None:
        """Check pending bracket orders against a bar's OHLC.

        Implements worst-case-for-longs priority:
        1. Stop loss — bar.low <= stop_price → fill at stop_price
        2. Target — bar.high >= target_price → fill at target_price
        3. Time stop — elapsed >= time_stop_seconds → fill at bar.close
           (but use stop_price if bar.low also hits stop)

        When both stop and target trigger on the same bar, stop wins.

        Args:
            symbol: The bar's symbol.
            bar_high: Bar high price.
            bar_low: Bar low price.
            bar_close: Bar close price.
            bar_timestamp: Bar timestamp (for time stop calculation).
        """
        if self._broker is None or self._event_bus is None:
            return

        # Collect pending brackets for this symbol
        stop_orders = [
            b for b in self._broker._pending_brackets
            if b.symbol == symbol and b.order_type == "stop"
        ]
        target_orders = sorted(
            [
                b for b in self._broker._pending_brackets
                if b.symbol == symbol and b.order_type == "limit"
            ],
            key=lambda b: b.trigger_price,
        )

        # Priority 1: Stop loss (worst case for longs)
        # When both stop and target could trigger, stop wins
        if stop_orders and bar_low <= stop_orders[0].trigger_price:
            results = await self._broker.simulate_price_update(
                symbol, stop_orders[0].trigger_price
            )
            await self._publish_fill_events(results)
            return  # Position closed

        # Priority 2: Target(s) — process lowest first (T1 before T2)
        for target in target_orders:
            if bar_high >= target.trigger_price:
                # Verify bracket is still pending (prior trigger may
                # have closed the position and cancelled remaining)
                still_pending = any(
                    b.order_id == target.order_id
                    for b in self._broker._pending_brackets
                )
                if still_pending:
                    results = await self._broker.simulate_price_update(
                        symbol, target.trigger_price
                    )
                    await self._publish_fill_events(results)

        # Priority 3: Time stop
        await self._check_time_stop(
            symbol, bar_low, bar_close, bar_timestamp
        )

    async def _check_time_stop(
        self,
        symbol: str,
        bar_low: float,
        bar_close: float,
        bar_timestamp: datetime,
    ) -> None:
        """Check if any managed position's time stop has expired.

        If time_stop_seconds has elapsed since entry, close the position.
        Fill price is bar_close, unless bar_low also hit the stop price
        (worst case for longs → use stop price).

        Args:
            symbol: The bar's symbol.
            bar_low: Bar low price.
            bar_close: Bar close price.
            bar_timestamp: Current bar timestamp.
        """
        if self._order_manager is None or self._broker is None:
            return

        managed_dict = self._order_manager.get_managed_positions()
        positions_for_symbol = managed_dict.get(symbol, [])
        for position in positions_for_symbol:
            if position.is_fully_closed:
                continue
            if position.time_stop_seconds is None:
                continue

            elapsed = (bar_timestamp - position.entry_time).total_seconds()
            if elapsed < position.time_stop_seconds:
                continue

            # Time stop triggered — determine fill price
            stop_brackets = [
                b for b in self._broker._pending_brackets
                if b.symbol == symbol and b.order_type == "stop"
            ]
            if stop_brackets and bar_low <= stop_brackets[0].trigger_price:
                fill_price = stop_brackets[0].trigger_price
            else:
                fill_price = bar_close

            # Set price and close through OrderManager
            self._broker.set_price(symbol, fill_price)
            await self._order_manager.close_position(
                symbol, reason="time_stop"
            )

    async def _publish_fill_events(
        self, results: list[OrderResult]
    ) -> None:
        """Publish OrderFilledEvent for each filled result.

        Args:
            results: List of OrderResults from simulate_price_update.
        """
        if self._event_bus is None:
            return

        for result in results:
            if result.status == OrderStatus.FILLED:
                fill_event = OrderFilledEvent(
                    order_id=result.order_id,
                    fill_price=result.filled_avg_price,
                    fill_quantity=result.filled_quantity,
                )
                await self._event_bus.publish(fill_event)

    # --- Strategy factory ---

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

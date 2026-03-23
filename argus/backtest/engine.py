"""BacktestEngine — Production-code backtesting with synchronous dispatch.

Wires real ARGUS components (strategies, indicators, risk, orders)
in fast-replay mode using SyncEventBus instead of async EventBus.
No tick synthesis — uses bar-level fill model (worst-case priority).

Decision references:
- DEC-055: BacktestDataService (Step-Driven DataService)
- DEC-056: Backtest Database Naming Convention
- Sprint 27 S3: Component assembly + strategy factory
- Sprint 27 S5: Multi-day orchestration + scanner + results + CLI
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from argus.analytics.evaluation import (
    MultiObjectiveResult,
    RegimeMetrics,
    from_backtest_result,
)
from argus.analytics.slippage_model import (
    SlippageConfidence,
    StrategySlippageModel,
    load_slippage_model,
)
from argus.analytics.trade_logger import TradeLogger
from argus.backtest.backtest_data_service import BacktestDataService
from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.historical_data_feed import HistoricalDataFeed
from argus.backtest.metrics import BacktestResult, compute_metrics
from argus.backtest.scanner_simulator import ScannerSimulator
from argus.core.clock import FixedClock
from argus.core.config import (
    AfternoonMomentumConfig,
    BullFlagConfig,
    FlatTopBreakoutConfig,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OrchestratorConfig,
    OrderManagerConfig,
    RedToGreenConfig,
    RiskConfig,
    VwapReclaimConfig,
    load_yaml_file,
)
from argus.core.events import CandleEvent, OrderFilledEvent
from argus.core.regime import MarketRegime, RegimeClassifier
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

    Note: The bar-level fill model is least accurate for strategies with risk
    parameters smaller than the typical 1-minute bar range (e.g., ORB Scalp
    with 0.3R target). For these strategies, the Replay Harness with tick
    synthesis provides higher-fidelity results.

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

        # Slippage model (Sprint 27.5 S6)
        self._slippage_model: StrategySlippageModel | None = None
        if config.slippage_model_path is not None:
            try:
                self._slippage_model = load_slippage_model(
                    config.slippage_model_path
                )
                logger.info(
                    "Loaded slippage model from %s (confidence=%s)",
                    config.slippage_model_path,
                    self._slippage_model.confidence.value,
                )
            except FileNotFoundError:
                logger.warning(
                    "Slippage model file not found: %s — proceeding without model",
                    config.slippage_model_path,
                )
            except ValueError as exc:
                logger.warning(
                    "Invalid slippage model file %s: %s — proceeding without model",
                    config.slippage_model_path,
                    exc,
                )

        # Bar data and trading days populated by _load_data()
        self._bar_data: dict[str, pd.DataFrame] = {}
        self._trading_days: list[date] = []

    async def run(self) -> BacktestResult:
        """Run the backtest end-to-end.

        Follows the ReplayHarness.run() flow:
        1. Log start info
        2. Load data (via HistoricalDataFeed or from pre-loaded bar_data)
        3. If no trading days -> return _empty_result()
        4. Initialize all components via _setup()
        5. Pre-compute watchlists via ScannerSimulator
        6. For each trading day: _run_trading_day(day, watchlist)
        7. Compute results via _compute_results()
        8. Record engine metadata (AR-1)
        9. Teardown
        10. Log completion summary

        Returns:
            BacktestResult with metrics from the run.
        """
        logger.info(
            "Starting BacktestEngine: strategy=%s, period=%s to %s",
            self._config.strategy_id,
            self._config.start_date,
            self._config.end_date,
        )

        # 1. Load data
        await self._load_data()

        # 2. If no trading days, return empty
        if not self._trading_days:
            logger.warning("No trading days found in date range")
            return self._empty_result()

        # 3. Initialize all components
        await self._setup()

        # 4. Pre-compute watchlists via ScannerSimulator
        scanner = ScannerSimulator(
            min_gap_pct=self._config.scanner_min_gap_pct,
            min_price=self._config.scanner_min_price,
            max_price=self._config.scanner_max_price,
            fallback_all_symbols=self._config.scanner_fallback_all_symbols,
        )
        watchlists = scanner.compute_watchlists(
            self._bar_data, self._trading_days
        )

        # 5. Day-by-day execution loop
        for day_num, trading_day in enumerate(self._trading_days, 1):
            daily_watchlist = watchlists.get(trading_day)
            symbols = daily_watchlist.symbols if daily_watchlist else list(
                self._bar_data.keys()
            )
            await self._run_trading_day(trading_day, symbols)

            if day_num % 20 == 0:
                logger.info(
                    "Progress: %d/%d trading days complete",
                    day_num,
                    len(self._trading_days),
                )

        # 6. Compute results
        result = await self._compute_results()

        # 7. Record engine metadata (AR-1)
        self._write_metadata()

        # 8. Teardown
        await self._teardown()

        # 9. Log completion summary
        logger.info(
            "Backtest complete: %d trading days, %d trades, PF=%.2f, WR=%.1f%%",
            result.trading_days,
            result.total_trades,
            result.profit_factor if result.profit_factor != float("inf")
            else 0.0,
            result.win_rate * 100,
        )

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
            # Legacy position sizing for backtest mode (Sprint 24 quality pipeline
            # is not wired into BacktestEngine — strategies emit share_count=0)
            if signal.share_count == 0:
                risk_per_share = abs(signal.entry_price - signal.stop_price)
                if risk_per_share > 0:
                    max_loss_pct = getattr(
                        getattr(
                            getattr(self._strategy, "config", None),
                            "risk_limits",
                            None,
                        ),
                        "max_loss_per_trade_pct",
                        0.01,
                    )
                    shares = int(
                        self._strategy.allocated_capital
                        * max_loss_pct
                        / risk_per_share
                    )
                    signal = replace(signal, share_count=max(shares, 0))
                # If risk_per_share == 0 or shares == 0, let Risk Manager reject

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
            # Auto-detect symbols from cache directory
            cache_path = Path(self._config.cache_dir)
            if cache_path.is_dir():
                symbols = [
                    d.name
                    for d in cache_path.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                ]
            if not symbols:
                logger.warning(
                    "No symbols configured and none found in cache "
                    "— backtest will have no data"
                )
                return
            logger.info(
                "Auto-detected %d symbols from cache: %s",
                len(symbols),
                symbols[:5],
            )

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
        """Load risk configuration from YAML, then apply backtest overrides.

        Args:
            config_dir: Path to the config directory.

        Returns:
            RiskConfig with backtest risk_overrides applied.
        """
        risk_file = config_dir / "risk_limits.yaml"
        if risk_file.exists():
            data = load_yaml_file(risk_file)
            risk_config = RiskConfig(**data)
        else:
            risk_config = RiskConfig()

        # Apply backtest risk overrides (DEC-359)
        for key, value in self._config.risk_overrides.items():
            parts = key.split(".", 1)
            if len(parts) == 2:
                section, field = parts
                sub_config = getattr(risk_config, section, None)
                if sub_config is not None and hasattr(sub_config, field):
                    setattr(sub_config, field, value)
                    logger.debug("Risk override applied: %s = %s", key, value)
                else:
                    logger.warning("Unknown risk override key: %s", key)

        return risk_config

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

    # --- Regime tagging (Sprint 27.5 S2) ---

    def _load_spy_daily_bars(
        self, start_date: date, end_date: date
    ) -> pd.DataFrame | None:
        """Aggregate SPY daily bars from the Parquet cache.

        Reads SPY 1-minute Parquet files from the same cache_dir used by
        HistoricalDataFeed and resamples to daily OHLCV.

        Args:
            start_date: First date of range.
            end_date: Last date of range.

        Returns:
            DataFrame with columns [open, high, low, close, volume] indexed
            by date, or None if SPY not in cache.
        """
        spy_dir = Path(self._config.cache_dir) / "SPY"
        if not spy_dir.exists():
            return None

        feed = HistoricalDataFeed(
            cache_dir=self._config.cache_dir,
            verify_zero_cost=False,
        )

        # Load with generous margin for SMA-50 lookback
        margin_start = date(
            start_date.year if start_date.month > 3
            else start_date.year - 1,
            start_date.month - 3 if start_date.month > 3
            else start_date.month + 9,
            1,
        )

        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(
            feed.load(["SPY"], margin_start, end_date)
        )

        spy_df = data.get("SPY")
        if spy_df is None or spy_df.empty:
            return None

        # Ensure trading_date column exists
        if "trading_date" not in spy_df.columns:
            return None

        # Resample to daily: first open, max high, min low, last close, sum volume
        grouped = spy_df.groupby("trading_date")
        daily = pd.DataFrame({
            "open": grouped["open"].first(),
            "high": grouped["high"].max(),
            "low": grouped["low"].min(),
            "close": grouped["close"].last(),
            "volume": grouped["volume"].sum(),
        })

        daily.index.name = "date"
        return daily.sort_index()

    def _compute_regime_tags(
        self, daily_bars: pd.DataFrame
    ) -> dict[date, str]:
        """Tag each trading day with a market regime.

        Uses RegimeClassifier with default OrchestratorConfig thresholds
        to classify each day based on trailing daily bar history.

        Args:
            daily_bars: DataFrame with daily OHLCV, indexed by date.

        Returns:
            Mapping of date to regime string value.
        """
        config = OrchestratorConfig()
        classifier = RegimeClassifier(config)

        regime_tags: dict[date, str] = {}
        dates = list(daily_bars.index)

        for i, d in enumerate(dates):
            # Use all bars up to and including this date
            history = daily_bars.iloc[: i + 1]

            if len(history) < 20:
                # Insufficient history for SMA computation
                regime_tags[d] = MarketRegime.RANGE_BOUND.value
                continue

            indicators = classifier.compute_indicators(history)
            regime = classifier.classify(indicators)
            regime_tags[d] = regime.value

        return regime_tags

    def _compute_regime_metrics(
        self, trades: list[dict[str, object]]
    ) -> RegimeMetrics:
        """Compute RegimeMetrics for a subset of trades.

        Args:
            trades: List of trade dicts with net_pnl, r_multiple, etc.

        Returns:
            RegimeMetrics for the trade subset.
        """
        total = len(trades)
        if total == 0:
            return RegimeMetrics(
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                profit_factor=0.0,
                win_rate=0.0,
                total_trades=0,
                expectancy_per_trade=0.0,
            )

        winners = [t for t in trades if float(t.get("net_pnl", 0)) > 0.50]  # type: ignore[arg-type]
        losers = [t for t in trades if float(t.get("net_pnl", 0)) < -0.50]  # type: ignore[arg-type]

        win_rate = len(winners) / total if total > 0 else 0.0

        gross_wins = sum(float(t.get("net_pnl", 0)) for t in winners)  # type: ignore[arg-type]
        gross_losses = abs(sum(float(t.get("net_pnl", 0)) for t in losers))  # type: ignore[arg-type]

        if gross_losses > 0:
            profit_factor = gross_wins / gross_losses
        elif gross_wins > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        # Expectancy from R-multiples
        r_values = [float(t.get("r_multiple", 0)) for t in trades]  # type: ignore[arg-type]
        expectancy = sum(r_values) / total if total > 0 else 0.0

        # Daily P&L for Sharpe
        daily_pnl: dict[date, float] = {}
        for t in trades:
            exit_time = t.get("exit_time")
            if exit_time is not None and hasattr(exit_time, "date"):
                d = exit_time.date()  # type: ignore[union-attr]
            else:
                continue
            daily_pnl[d] = daily_pnl.get(d, 0.0) + float(t.get("net_pnl", 0))  # type: ignore[arg-type]

        daily_returns = list(daily_pnl.values())
        if len(daily_returns) >= 2:
            mean_ret = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (
                len(daily_returns) - 1
            )
            std_dev = variance ** 0.5
            sharpe = (
                (mean_ret / std_dev) * (252 ** 0.5) if std_dev > 1e-10 else 0.0
            )
        else:
            sharpe = 0.0

        # Max drawdown from cumulative P&L
        sorted_days = sorted(daily_pnl.keys())
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for d in sorted_days:
            cumulative += daily_pnl[d]
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        max_dd_pct = -(max_dd / peak) if peak > 0 else 0.0

        return RegimeMetrics(
            sharpe_ratio=round(sharpe, 4),
            max_drawdown_pct=round(max_dd_pct, 4),
            profit_factor=profit_factor,
            win_rate=round(win_rate, 4),
            total_trades=total,
            expectancy_per_trade=round(expectancy, 4),
        )

    async def to_multi_objective_result(
        self,
        result: BacktestResult,
        parameter_hash: str = "",
        wfe: float = 0.0,
        is_oos: bool = False,
    ) -> MultiObjectiveResult:
        """Convert a BacktestResult into a MultiObjectiveResult with regime tags.

        Loads SPY daily bars from Parquet cache, computes per-day regime tags,
        partitions trades by exit_date regime, and produces regime-level metrics.

        Args:
            result: BacktestResult from a completed run().
            parameter_hash: Deterministic hash of parameter config.
            wfe: Walk-forward efficiency.
            is_oos: Whether this is out-of-sample data.

        Returns:
            MultiObjectiveResult with populated regime_results.
        """
        # Get trades from the trade logger
        trades: list[dict[str, object]] = []
        if self._trade_logger is not None:
            trade_objects = await self._trade_logger.get_trades_by_date_range(
                result.start_date, result.end_date, result.strategy_id
            )
            trades = [
                {
                    "net_pnl": t.net_pnl,
                    "r_multiple": t.r_multiple,
                    "commission": t.commission,
                    "hold_duration_seconds": t.hold_duration_seconds,
                    "exit_price": t.exit_price,
                    "exit_time": t.exit_time,
                    "gross_pnl": t.gross_pnl,
                }
                for t in trade_objects
            ]

        # Load SPY daily bars and compute regime tags
        daily_bars = self._load_spy_daily_bars(
            result.start_date, result.end_date
        )

        if daily_bars is not None and not daily_bars.empty:
            regime_tags = self._compute_regime_tags(daily_bars)
        else:
            logger.warning(
                "SPY daily bars not available in Parquet cache — "
                "assigning all days RANGE_BOUND"
            )
            # Assign RANGE_BOUND to all trading days
            regime_tags = {
                d: MarketRegime.RANGE_BOUND.value for d in self._trading_days
            }

        # Partition trades by exit_date → regime
        regime_trades: dict[str, list[dict[str, object]]] = {}
        for trade in trades:
            exit_time = trade.get("exit_time")
            if exit_time is not None and hasattr(exit_time, "date"):
                exit_date = exit_time.date()  # type: ignore[union-attr]
            else:
                continue

            regime = regime_tags.get(
                exit_date, MarketRegime.RANGE_BOUND.value
            )
            regime_trades.setdefault(regime, []).append(trade)

        # Compute per-regime metrics
        regime_results: dict[str, RegimeMetrics] = {}
        for regime_key, regime_trade_list in regime_trades.items():
            if len(regime_trade_list) == 0:
                continue
            regime_results[regime_key] = self._compute_regime_metrics(
                regime_trade_list
            )

        mor = from_backtest_result(
            result=result,
            regime_results=regime_results,
            wfe=wfe,
            is_oos=is_oos,
            parameter_hash_value=parameter_hash,
        )

        # Compute execution_quality_adjustment from slippage model (S6).
        # Formula (first-order approximation):
        #   delta_bps = model.mean_slippage - default_slippage_bps
        #   adjustment = -(delta_bps / 10_000) * trades_per_year / return_std
        # A positive delta_bps means real slippage exceeds the backtest
        # assumption, so the Sharpe adjustment is negative (penalizes).
        mor.execution_quality_adjustment = self._compute_execution_quality_adjustment(
            result
        )

        return mor

    def _compute_execution_quality_adjustment(
        self,
        result: BacktestResult,
    ) -> float | None:
        """Compute Sharpe adjustment from calibrated vs assumed slippage.

        Returns None when the slippage model is absent, has INSUFFICIENT
        confidence, or when the computation would be unreliable (zero trades,
        zero return std, zero trading days).

        Args:
            result: Completed BacktestResult.

        Returns:
            Estimated annualized Sharpe impact, or None.
        """
        if self._slippage_model is None:
            return None
        if self._slippage_model.confidence == SlippageConfidence.INSUFFICIENT:
            return None
        if result.total_trades == 0 or len(self._trading_days) == 0:
            return None

        # Default slippage assumption in bps (from config)
        # Approximate: slippage_per_share / avg_entry_price * 10_000
        # Use result's avg trade P&L to estimate avg entry price range.
        # Simpler: use slippage_per_share directly with a representative price.
        # For intraday equities, ~$50 is a reasonable midpoint placeholder.
        # More accurate: derive from actual trade data if available.
        # TODO: derive avg_entry_price from actual trade data for higher accuracy
        avg_entry_price = 50.0  # Conservative midpoint for US equities

        default_slippage_bps = (
            self._config.slippage_per_share / avg_entry_price * 10_000
        )

        # Delta: positive means real slippage > assumed
        delta_bps = (
            self._slippage_model.estimated_mean_slippage_bps - default_slippage_bps
        )

        trading_days = len(self._trading_days)
        trades_per_day = result.total_trades / trading_days
        trades_per_year = trades_per_day * 252

        # Estimate portfolio return std from Sharpe and annualized return
        # Sharpe = return / std → std = return / Sharpe
        # If Sharpe is near zero, std estimation is unreliable.
        if abs(result.sharpe_ratio) < 0.01:
            return None

        # Approximate annualized return from total P&L
        net_pnl = result.final_equity - result.initial_capital
        total_return = net_pnl / self._config.initial_cash
        annualized_return = total_return * (252 / max(trading_days, 1))
        return_std = abs(annualized_return / result.sharpe_ratio)

        if return_std < 1e-10:
            return None

        # Sharpe adjustment: -(delta_bps / 10_000) * trades_per_year / return_std
        adjustment = -(delta_bps / 10_000) * trades_per_year / return_std

        return round(adjustment, 6)

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

    # --- Results & metadata ---

    async def _compute_results(self) -> BacktestResult:
        """Compute all metrics after the backtest completes.

        Delegates to compute_metrics() from argus.backtest.metrics,
        matching the ReplayHarness._compute_results() pattern.

        Returns:
            BacktestResult with all computed metrics.
        """
        if self._trade_logger is None:
            return self._empty_result()

        return await compute_metrics(
            trade_logger=self._trade_logger,
            strategy_id=self._strategy.strategy_id if self._strategy else self._config.strategy_id,
            start_date=self._config.start_date,
            end_date=self._config.end_date,
            initial_capital=self._config.initial_cash,
            trading_days=len(self._trading_days),
        )

    def _write_metadata(self) -> None:
        """Record engine metadata alongside the output database (AR-1).

        Writes a JSON metadata file at {db_path}.meta.json with engine
        type, fill model, strategy info, date range, and run timestamp.
        """
        if self._db_path is None:
            return

        metadata = {
            "engine_type": "backtest_engine",
            "fill_model": "bar_level_worst_case",
            "strategy_type": str(self._config.strategy_type),
            "strategy_id": self._config.strategy_id,
            "start_date": self._config.start_date.isoformat(),
            "end_date": self._config.end_date.isoformat(),
            "symbol_count": len(self._bar_data),
            "trading_days": len(self._trading_days),
            "initial_cash": self._config.initial_cash,
            "slippage_per_share": self._config.slippage_per_share,
            "run_timestamp": datetime.now(UTC).isoformat(),
        }

        meta_path = Path(f"{self._db_path}.meta.json")
        meta_path.write_text(json.dumps(metadata, indent=2))
        logger.info("Engine metadata written: %s", meta_path)

    # --- Teardown ---

    async def _teardown(self) -> None:
        """Clean up all components."""
        if self._order_manager is not None:
            await self._order_manager.stop()

        if self._db_manager is not None:
            await self._db_manager.close()

        logger.info("Backtest database saved: %s", self._db_path)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for BacktestEngine.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Argus BacktestEngine - bar-level production-code backtesting"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        required=True,
        choices=[e.value for e in StrategyType],
        help="Strategy type to backtest",
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (default: all cached)",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/databento_cache",
        help="Path to Databento cache directory",
    )
    parser.add_argument(
        "--output-dir",
        default="data/backtest_runs",
        help="Path to store backtest results",
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100_000.0,
        help="Starting capital",
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.01,
        help="Fixed slippage per share in dollars",
    )
    parser.add_argument(
        "--no-cost-check",
        action="store_true",
        help="Disable Databento zero-cost verification",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: WARNING)",
    )
    parser.add_argument(
        "--config-override",
        action="append",
        default=[],
        help="Config override in key=value format (repeatable)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging (overrides --log-level)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for BacktestEngine."""
    args = parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else args.log_level
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Parse symbols
    symbols: list[str] | None = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]

    # Parse config overrides
    overrides: dict[str, Any] = {}
    for override in args.config_override:
        key, _, value = override.partition("=")
        try:
            parsed_value: float | int | str = float(value)
            if parsed_value == int(parsed_value):
                parsed_value = int(parsed_value)
        except ValueError:
            parsed_value = value
        overrides[key.strip()] = parsed_value

    # Build config
    config = BacktestEngineConfig(
        strategy_type=StrategyType(args.strategy),
        strategy_id=f"strat_{args.strategy}",
        symbols=symbols,
        start_date=args.start,
        end_date=args.end,
        cache_dir=Path(args.cache_dir),
        output_dir=Path(args.output_dir),
        initial_cash=args.initial_cash,
        slippage_per_share=args.slippage,
        verify_zero_cost=not args.no_cost_check,
        log_level=log_level,
        config_overrides=overrides,
    )

    # Run
    engine = BacktestEngine(config)
    result = asyncio.run(engine.run())

    # Print summary
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Strategy:        {result.strategy_id}")
    print(f"Period:          {result.start_date} to {result.end_date}")
    print(f"Trading Days:    {result.trading_days}")
    print(f"Total Trades:    {result.total_trades}")
    print(f"Win Rate:        {result.win_rate:.1%}")
    pf_str = (
        f"{result.profit_factor:.2f}"
        if result.profit_factor != float("inf")
        else "inf"
    )
    print(f"Profit Factor:   {pf_str}")
    print(f"Avg R-Multiple:  {result.avg_r_multiple:.2f}")
    print(f"Expectancy:      {result.expectancy:.3f}R")
    print(
        f"Max Drawdown:    ${result.max_drawdown_dollars:,.2f}"
        f" ({result.max_drawdown_pct:.1%})"
    )
    print(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
    rf_str = (
        f"{result.recovery_factor:.2f}"
        if result.recovery_factor != float("inf")
        else "inf"
    )
    print(f"Recovery Factor: {rf_str}")
    print(
        f"Net P&L:         ${result.final_equity - config.initial_cash:,.2f}"
    )
    print(f"Final Equity:    ${result.final_equity:,.2f}")
    print(f"Avg Hold:        {result.avg_hold_minutes:.0f} min")
    print("=" * 60)


if __name__ == "__main__":
    main()

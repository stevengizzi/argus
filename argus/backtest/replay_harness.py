"""Replay Harness - highest-fidelity backtesting for Argus.

Feeds historical Parquet data through the production trading pipeline:
  EventBus -> BacktestDataService -> OrbBreakout -> RiskManager -> OrderManager -> SimulatedBroker

All components are REAL production code. The only differences from live:
  1. FixedClock instead of SystemClock (simulated time)
  2. BacktestDataService instead of AlpacaDataService (step-by-step bar feed)
  3. SimulatedBroker instead of AlpacaBroker (deterministic fills)
  4. ScannerSimulator instead of AlpacaScanner (gap-based watchlist)

Output: A SQLite database per run with the same schema as production.
All existing SQL queries work on backtest output.

Decision references:
- DEC-052: Scanner Simulation via Gap Computation
- DEC-053: Synthetic Tick Generation from Bar OHLC
- DEC-054: Fixed Slippage Model for V1 Backtesting
- DEC-055: BacktestDataService (Step-Driven DataService)
- DEC-056: Backtest Database Naming Convention
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from argus.analytics.trade_logger import TradeLogger
from argus.backtest.backtest_data_service import BacktestDataService
from argus.backtest.config import BacktestConfig
from argus.backtest.metrics import BacktestResult, compute_metrics
from argus.backtest.scanner_simulator import DailyWatchlist, ScannerSimulator
from argus.backtest.tick_synthesizer import synthesize_ticks
from argus.core.clock import FixedClock
from argus.core.config import (
    OrbBreakoutConfig,
    OrderManagerConfig,
    RiskConfig,
    load_yaml_file,
)
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, OrderFilledEvent
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker, SimulatedSlippage
from argus.models.trading import OrderStatus
from argus.strategies.orb_breakout import OrbBreakoutStrategy

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class ReplayHarness:
    """Orchestrates a complete backtest run using production components.

    Usage:
        config = BacktestConfig(start_date=date(2025, 6, 1), end_date=date(2025, 12, 31))
        harness = ReplayHarness(config)
        result = await harness.run()
        print(result)
    """

    def __init__(self, config: BacktestConfig) -> None:
        """Initialize the replay harness.

        Args:
            config: BacktestConfig with date range, data paths, and settings.
        """
        self._config = config

        # Components - initialized in _setup()
        self._event_bus: EventBus | None = None
        self._clock: FixedClock | None = None
        self._broker: SimulatedBroker | None = None
        self._risk_manager: RiskManager | None = None
        self._order_manager: OrderManager | None = None
        self._strategy: OrbBreakoutStrategy | None = None
        self._data_service: BacktestDataService | None = None
        self._trade_logger: TradeLogger | None = None
        self._db_manager: DatabaseManager | None = None

        # Run state
        self._bar_data: dict[str, pd.DataFrame] = {}
        self._trading_days: list[date] = []
        self._db_path: Path | None = None

    async def run(self) -> BacktestResult:
        """Execute the complete backtest.

        Returns:
            BacktestResult with all performance metrics.
        """
        logger.info(
            "Starting backtest: strategy=%s, period=%s to %s",
            self._config.strategy_id,
            self._config.start_date,
            self._config.end_date,
        )

        # 1. Load historical data
        self._load_data()

        if not self._trading_days:
            logger.warning("No trading days found in date range")
            return self._empty_result()

        # 2. Initialize all components
        await self._setup()

        # 3. Pre-compute watchlists
        scanner = ScannerSimulator(
            min_gap_pct=self._config.scanner_min_gap_pct,
            min_price=self._config.scanner_min_price,
            max_price=self._config.scanner_max_price,
            fallback_all_symbols=self._config.scanner_fallback_all_symbols,
        )
        watchlists = scanner.compute_watchlists(self._bar_data, self._trading_days)

        # 4. Run each trading day
        for day_num, trading_day in enumerate(self._trading_days, 1):
            await self._run_trading_day(trading_day, watchlists.get(trading_day))

            if day_num % 20 == 0:
                logger.info(
                    "Progress: %d/%d trading days complete",
                    day_num,
                    len(self._trading_days),
                )

        # 5. Compute metrics
        result = await self._compute_results()

        # 6. Teardown
        await self._teardown()

        logger.info(
            "Backtest complete: %d trading days, %d trades, PF=%.2f, WR=%.1f%%",
            result.trading_days,
            result.total_trades,
            result.profit_factor if result.profit_factor != float("inf") else 0.0,
            result.win_rate * 100,
        )

        return result

    def _load_data(self) -> None:
        """Load Parquet files for symbols in the data directory.

        If config.symbols is set, only those symbols are loaded.
        Otherwise, all symbols in data_dir are loaded.
        """
        data_dir = Path(self._config.data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        # Determine which symbols to load
        symbols_filter: set[str] | None = None
        if self._config.symbols:
            symbols_filter = {s.upper() for s in self._config.symbols}

        # Find all symbol directories
        all_dates: set[date] = set()

        for symbol_dir in data_dir.iterdir():
            if not symbol_dir.is_dir():
                continue

            symbol = symbol_dir.name.upper()

            # Skip symbols not in filter (if filter is specified)
            if symbols_filter is not None and symbol not in symbols_filter:
                continue

            dfs = []

            # Load all Parquet files for this symbol
            for parquet_file in sorted(symbol_dir.glob("*.parquet")):
                try:
                    df = pd.read_parquet(parquet_file)
                    dfs.append(df)
                except Exception as e:
                    logger.warning("Failed to load %s: %s", parquet_file, e)

            if not dfs:
                continue

            # Concatenate all month files
            combined = pd.concat(dfs, ignore_index=True)
            combined = combined.sort_values("timestamp").reset_index(drop=True)

            # Convert timestamps to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(combined["timestamp"]):
                combined["timestamp"] = pd.to_datetime(combined["timestamp"])

            # Ensure timezone aware (assume UTC if not)
            if combined["timestamp"].dt.tz is None:
                combined["timestamp"] = combined["timestamp"].dt.tz_localize(UTC)

            # Convert to ET for filtering by date
            combined["timestamp_et"] = combined["timestamp"].dt.tz_convert(ET)
            combined["trading_date"] = combined["timestamp_et"].dt.date

            # Filter to date range
            mask = (combined["trading_date"] >= self._config.start_date) & (
                combined["trading_date"] <= self._config.end_date
            )
            filtered = combined[mask].copy()

            if len(filtered) > 0:
                self._bar_data[symbol] = filtered
                all_dates.update(filtered["trading_date"].unique())

        # Get sorted trading days
        self._trading_days = sorted(all_dates)
        logger.info(
            "Loaded data for %d symbols, %d trading days",
            len(self._bar_data),
            len(self._trading_days),
        )

    async def _setup(self) -> None:
        """Initialize all production components for the backtest."""
        # Create output directory
        output_dir = Path(self._config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate database filename (DEC-056)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        start_str = self._config.start_date.strftime("%Y%m%d")
        end_str = self._config.end_date.strftime("%Y%m%d")
        db_filename = f"{self._config.strategy_id}_{start_str}_{end_str}_{timestamp}.db"
        self._db_path = output_dir / db_filename

        # Initialize EventBus
        self._event_bus = EventBus()

        # Initialize FixedClock - start at pre-market of first trading day
        first_day = self._trading_days[0]
        initial_time = datetime(
            first_day.year, first_day.month, first_day.day, 9, 25, 0, tzinfo=ET
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

        # Initialize BacktestDataService
        self._data_service = BacktestDataService(self._event_bus)

        # Load configs from YAML
        config_dir = Path("config")
        risk_config = self._load_risk_config(config_dir)
        order_manager_config = self._load_order_manager_config(config_dir)
        orb_config = self._load_orb_config(config_dir)

        # Apply config overrides
        orb_config = self._apply_config_overrides(orb_config)

        # Initialize RiskManager
        self._risk_manager = RiskManager(
            config=risk_config,
            broker=self._broker,
            event_bus=self._event_bus,
            clock=self._clock,
        )
        await self._risk_manager.initialize()

        # Initialize OrderManager
        self._order_manager = OrderManager(
            event_bus=self._event_bus,
            broker=self._broker,
            clock=self._clock,
            config=order_manager_config,
            trade_logger=self._trade_logger,
        )
        await self._order_manager.start()

        # Initialize OrbBreakout strategy
        self._strategy = OrbBreakoutStrategy(
            config=orb_config,
            data_service=self._data_service,
            clock=self._clock,
        )
        self._strategy.allocated_capital = self._config.initial_cash

        # Subscribe strategy to candle events
        self._event_bus.subscribe(CandleEvent, self._on_candle_event)

        logger.info(
            "Replay harness initialized: db=%s, initial_cash=%.2f",
            self._db_path,
            self._config.initial_cash,
        )

    async def _on_candle_event(self, event) -> None:
        """Route candle events to the strategy and risk manager."""
        if self._strategy is None:
            return

        signal = await self._strategy.on_candle(event)
        if signal is not None and self._risk_manager is not None:
            result = await self._risk_manager.evaluate_signal(signal)
            await self._event_bus.publish(result)

    def _load_risk_config(self, config_dir: Path) -> RiskConfig:
        """Load risk configuration."""
        risk_file = config_dir / "risk_limits.yaml"
        if risk_file.exists():
            data = load_yaml_file(risk_file)
            return RiskConfig(**data)
        return RiskConfig()

    def _load_order_manager_config(self, config_dir: Path) -> OrderManagerConfig:
        """Load order manager configuration."""
        om_file = config_dir / "order_manager.yaml"
        if om_file.exists():
            data = load_yaml_file(om_file)
            return OrderManagerConfig(**data)
        return OrderManagerConfig()

    def _load_orb_config(self, config_dir: Path) -> OrbBreakoutConfig:
        """Load ORB strategy configuration."""
        orb_file = config_dir / "strategies" / "orb_breakout.yaml"
        if orb_file.exists():
            data = load_yaml_file(orb_file)
            return OrbBreakoutConfig(**data)
        # Return default config
        return OrbBreakoutConfig(
            strategy_id="orb_breakout",
            name="ORB Breakout",
        )

    def _apply_config_overrides(self, config: OrbBreakoutConfig) -> OrbBreakoutConfig:
        """Apply config overrides from BacktestConfig."""
        if not self._config.config_overrides:
            return config

        # Convert config to dict, apply overrides, reconstruct
        config_dict = config.model_dump()

        for key, value in self._config.config_overrides.items():
            # Handle nested keys like "orb_breakout.opening_range_minutes"
            parts = key.split(".")
            field_name = parts[1] if parts[0] == "orb_breakout" and len(parts) > 1 else key

            if field_name in config_dict:
                config_dict[field_name] = value
                logger.info("Config override: %s = %s", field_name, value)

        return OrbBreakoutConfig(**config_dict)

    async def _run_trading_day(self, trading_day: date, watchlist: DailyWatchlist | None) -> None:
        """Run a single trading day through the pipeline."""
        if self._clock is None or self._data_service is None:
            return

        # 1. Set clock to pre-market
        pre_market = datetime(
            trading_day.year, trading_day.month, trading_day.day, 9, 25, 0, tzinfo=ET
        ).astimezone(UTC)
        self._clock.set(pre_market)

        # 2. Reset daily state
        if self._strategy is not None:
            self._strategy.reset_daily_state()
        if self._risk_manager is not None:
            await self._risk_manager.reset_daily_state()
        if self._order_manager is not None:
            self._order_manager.reset_daily_state()
        self._data_service.reset_daily_state()

        # 3. Set strategy's watchlist
        if self._strategy is not None and watchlist is not None:
            self._strategy.set_watchlist(watchlist.symbols)

        # 4. Get today's bars
        symbols = watchlist.symbols if watchlist else list(self._bar_data.keys())
        daily_bars = self._get_daily_bars(trading_day, symbols)

        if daily_bars.empty:
            return

        # 5. Process each bar
        for _, row in daily_bars.iterrows():
            symbol = row["symbol"]
            bar_ts = row["timestamp"]

            # Convert timestamp
            if isinstance(bar_ts, pd.Timestamp):
                bar_ts = bar_ts.to_pydatetime()
            if bar_ts.tzinfo is None:
                bar_ts = bar_ts.replace(tzinfo=UTC)

            # Advance clock
            self._clock.set(bar_ts)

            # Set current price in broker (for market order fills)
            if self._broker is not None:
                self._broker.set_price(symbol, float(row["close"]))

            # Feed bar to data service (publishes CandleEvent + IndicatorEvents)
            await self._data_service.feed_bar(
                symbol=symbol,
                timestamp=bar_ts,
                open_=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )

            # Allow event loop to process events
            await asyncio.sleep(0)

            # Synthesize ticks from bar OHLC
            ticks = synthesize_ticks(
                symbol=symbol,
                timestamp=bar_ts,
                open_=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )

            # Process each synthetic tick
            for tick in ticks:
                # Publish tick event
                await self._data_service.publish_tick(
                    symbol=tick.symbol,
                    price=tick.price,
                    volume=tick.volume,
                    timestamp=tick.timestamp,
                )

                # Check for bracket triggers
                await self._process_bracket_triggers(tick.symbol, tick.price)

                # Allow event loop to process
                await asyncio.sleep(0)

        # 6. EOD flatten
        eod_time_str = self._config.eod_flatten_time
        h, m = map(int, eod_time_str.split(":"))
        eod_dt = datetime(
            trading_day.year, trading_day.month, trading_day.day, h, m, 0, tzinfo=ET
        ).astimezone(UTC)
        self._clock.set(eod_dt)

        if self._order_manager is not None:
            await self._order_manager.eod_flatten()
            await asyncio.sleep(0)

    def _get_daily_bars(self, trading_day: date, symbols: list[str]) -> pd.DataFrame:
        """Get all bars for the given symbols on the given trading day."""
        frames = []

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
        # Sort by timestamp to interleave bars from multiple symbols chronologically
        combined = combined.sort_values("timestamp").reset_index(drop=True)

        return combined

    async def _process_bracket_triggers(self, symbol: str, price: float) -> None:
        """Call simulate_price_update and publish fill events."""
        if self._broker is None or self._event_bus is None:
            return

        # Call simulate_price_update
        triggered_results = await self._broker.simulate_price_update(symbol, price)

        # Publish OrderFilledEvent for each triggered fill
        for result in triggered_results:
            if result.status == OrderStatus.FILLED:
                fill_event = OrderFilledEvent(
                    order_id=result.order_id,
                    fill_price=result.filled_avg_price,
                    fill_quantity=result.filled_quantity,
                )
                await self._event_bus.publish(fill_event)

        # Allow events to propagate
        await asyncio.sleep(0)

    async def _compute_results(self) -> BacktestResult:
        """Compute all metrics after the backtest completes."""
        if self._trade_logger is None:
            return self._empty_result()

        return await compute_metrics(
            trade_logger=self._trade_logger,
            strategy_id=self._config.strategy_id,
            start_date=self._config.start_date,
            end_date=self._config.end_date,
            initial_capital=self._config.initial_cash,
            trading_days=len(self._trading_days),
        )

    def _empty_result(self) -> BacktestResult:
        """Return an empty result when there's nothing to compute."""
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


def parse_args():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Argus Replay Harness - backtest ORB strategy on historical data"
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
        "--data-dir",
        default="data/historical/1m",
        help="Path to historical data directory",
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
        "--config-override",
        action="append",
        default=[],
        help="Config override in key=value format (repeatable)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Parse config overrides
    overrides: dict[str, any] = {}
    for override in args.config_override:
        key, _, value = override.partition("=")
        # Try to parse as number
        try:
            parsed_value: any = float(value)
            if parsed_value == int(parsed_value):
                parsed_value = int(parsed_value)
        except ValueError:
            parsed_value = value
        overrides[key.strip()] = parsed_value

    config = BacktestConfig(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        start_date=args.start,
        end_date=args.end,
        initial_cash=args.initial_cash,
        slippage_per_share=args.slippage,
        config_overrides=overrides,
    )

    harness = ReplayHarness(config)
    result = asyncio.run(harness.run())

    # Print summary
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Strategy:        {result.strategy_id}")
    print(f"Period:          {result.start_date} to {result.end_date}")
    print(f"Trading Days:    {result.trading_days}")
    print(f"Total Trades:    {result.total_trades}")
    print(f"Win Rate:        {result.win_rate:.1%}")
    pf_str = f"{result.profit_factor:.2f}" if result.profit_factor != float("inf") else "inf"
    print(f"Profit Factor:   {pf_str}")
    print(f"Avg R-Multiple:  {result.avg_r_multiple:.2f}")
    print(f"Expectancy:      {result.expectancy:.3f}R")
    print(f"Max Drawdown:    ${result.max_drawdown_dollars:,.2f} ({result.max_drawdown_pct:.1%})")
    print(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
    rf_str = f"{result.recovery_factor:.2f}" if result.recovery_factor != float("inf") else "inf"
    print(f"Recovery Factor: {rf_str}")
    print(f"Net P&L:         ${result.final_equity - config.initial_cash:,.2f}")
    print(f"Final Equity:    ${result.final_equity:,.2f}")
    print(f"Avg Hold:        {result.avg_hold_minutes:.0f} min")
    print("=" * 60)


if __name__ == "__main__":
    main()

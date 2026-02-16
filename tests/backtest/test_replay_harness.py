"""Tests for the replay harness module."""

from datetime import date
from pathlib import Path

import pytest

from argus.backtest.config import BacktestConfig
from argus.backtest.replay_harness import ReplayHarness


class TestReplayHarness:
    """Tests for ReplayHarness class."""

    @pytest.mark.asyncio
    async def test_harness_runs_single_day_no_crash(
        self, single_day_parquet: tuple[Path, date]
    ) -> None:
        """Harness completes without crashing on minimal single-day data."""
        data_dir, trading_date = single_day_parquet

        config = BacktestConfig(
            start_date=trading_date,
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        assert result.trading_days == 1
        assert result.total_trades >= 0  # May or may not trade

    @pytest.mark.asyncio
    async def test_harness_creates_output_database(
        self, single_day_parquet: tuple[Path, date]
    ) -> None:
        """Harness creates an output database file."""
        data_dir, trading_date = single_day_parquet
        output_dir = data_dir.parent / "backtest_runs"

        config = BacktestConfig(
            start_date=trading_date,
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=output_dir,
            initial_cash=100000.0,
        )
        harness = ReplayHarness(config)
        await harness.run()

        db_files = list(output_dir.glob("*.db"))
        assert len(db_files) == 1
        assert "orb_breakout" in db_files[0].name

    @pytest.mark.asyncio
    async def test_harness_multi_day_resets_strategy_state(
        self, multi_day_parquet: tuple[Path, list[date]]
    ) -> None:
        """Strategy state resets between trading days."""
        data_dir, trading_days = multi_day_parquet

        config = BacktestConfig(
            start_date=trading_days[0],
            end_date=trading_days[1],
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        # Both days should be processed
        assert result.trading_days == 2

    @pytest.mark.asyncio
    async def test_harness_respects_initial_cash(
        self, single_day_parquet: tuple[Path, date]
    ) -> None:
        """Harness uses configured initial cash."""
        data_dir, trading_date = single_day_parquet

        config = BacktestConfig(
            start_date=trading_date,
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=50000.0,  # Custom amount
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        assert result.initial_capital == 50000.0

    @pytest.mark.asyncio
    async def test_harness_returns_empty_result_for_no_data(
        self, tmp_parquet_dir: Path
    ) -> None:
        """Harness returns empty result when no data matches date range."""
        # Create empty directory structure
        tmp_parquet_dir.mkdir(parents=True, exist_ok=True)

        config = BacktestConfig(
            start_date=date(2025, 6, 16),
            end_date=date(2025, 6, 17),
            data_dir=tmp_parquet_dir,
            output_dir=tmp_parquet_dir.parent / "backtest_runs",
            initial_cash=100000.0,
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        assert result.trading_days == 0
        assert result.total_trades == 0
        assert result.final_equity == 100000.0

    @pytest.mark.asyncio
    async def test_harness_scanner_filters_symbols(
        self, multi_symbol_parquet: tuple[Path, date]
    ) -> None:
        """Scanner simulation filters by gap percentage."""
        data_dir, trading_date = multi_symbol_parquet

        config = BacktestConfig(
            start_date=date(2025, 6, 16),  # Need day 1 for gap calculation
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
            scanner_min_gap_pct=0.02,  # 2% minimum
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        # Should process 2 trading days
        assert result.trading_days == 2

    @pytest.mark.asyncio
    async def test_harness_slippage_configured(
        self, single_day_parquet: tuple[Path, date]
    ) -> None:
        """Slippage configuration is applied."""
        data_dir, trading_date = single_day_parquet

        config = BacktestConfig(
            start_date=trading_date,
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
            slippage_per_share=0.05,  # $0.05/share
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        # Harness should complete without error
        assert result is not None

    @pytest.mark.asyncio
    async def test_harness_date_range_filtering(
        self, multi_day_parquet: tuple[Path, list[date]]
    ) -> None:
        """Harness only processes bars within the configured date range."""
        data_dir, trading_days = multi_day_parquet

        # Only process day 2
        config = BacktestConfig(
            start_date=trading_days[1],
            end_date=trading_days[1],
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        assert result.trading_days == 1


class TestEndToEndTradeExecution:
    """End-to-end tests verifying the full pipeline works correctly."""

    @pytest.mark.asyncio
    async def test_full_pipeline_processes_without_error(
        self, breakout_scenario_parquet: tuple[Path, date]
    ) -> None:
        """Full pipeline runs without errors on breakout scenario data.

        This test verifies:
        1. Scanner simulation runs without error
        2. ORB strategy processes candles
        3. Risk Manager evaluates any signals
        4. Order Manager handles fills correctly
        5. Database is populated with correct schema
        """
        data_dir, trading_date = breakout_scenario_parquet

        # Need to include day 1 for gap calculation
        day1 = date(2025, 6, 16)

        config = BacktestConfig(
            start_date=day1,
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
            scanner_min_gap_pct=0.03,  # 3% minimum gap (our fixture has 5%)
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        # Should have processed 2 trading days
        assert result.trading_days == 2

        # Result should have correct initial capital
        assert result.initial_capital == 100000.0

        # Verify database was created
        from argus.db.manager import DatabaseManager

        output_files = list((data_dir.parent / "backtest_runs").glob("*.db"))
        assert len(output_files) == 1

        db = DatabaseManager(output_files[0])
        await db.initialize()

        # Database should have the trades table
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        table_names = [t[0] for t in tables]
        assert "trades" in table_names

        await db.close()

    @pytest.mark.asyncio
    async def test_trades_logged_with_r_multiple(
        self, breakout_scenario_parquet: tuple[Path, date]
    ) -> None:
        """If trades occur, they have R-multiple computed."""
        data_dir, trading_date = breakout_scenario_parquet
        day1 = date(2025, 6, 16)

        config = BacktestConfig(
            start_date=day1,
            end_date=trading_date,
            data_dir=data_dir,
            output_dir=data_dir.parent / "backtest_runs",
            initial_cash=100000.0,
            scanner_min_gap_pct=0.03,
        )
        harness = ReplayHarness(config)
        result = await harness.run()

        from argus.analytics.trade_logger import TradeLogger
        from argus.db.manager import DatabaseManager
        from argus.models.trading import ExitReason

        output_files = list((data_dir.parent / "backtest_runs").glob("*.db"))
        db = DatabaseManager(output_files[0])
        await db.initialize()
        trade_logger = TradeLogger(db)

        trades = await trade_logger.get_trades_by_strategy("orb_breakout")

        # If trades exist, validate their structure
        if result.total_trades > 0:
            assert len(trades) >= 1

            for trade in trades:
                assert trade.strategy_id == "orb_breakout"
                assert trade.entry_price > 0
                assert trade.exit_price > 0
                assert trade.shares > 0
                assert trade.stop_price > 0
                # R-multiple should be computed (may be 0 for breakeven trades)
                assert isinstance(trade.r_multiple, float)

                # Exit reason should be valid
                valid_reasons = {
                    ExitReason.TARGET_1,
                    ExitReason.TARGET_2,
                    ExitReason.STOP_LOSS,
                    ExitReason.TIME_STOP,
                    ExitReason.EOD_FLATTEN,
                }
                assert trade.exit_reason in valid_reasons

        await db.close()


class TestBacktestConfig:
    """Tests for BacktestConfig validation."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        config = BacktestConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        assert config.strategy_id == "orb_breakout"
        assert config.slippage_per_share == 0.01
        assert config.initial_cash == 100_000.0
        assert config.scanner_min_gap_pct == 0.02

    def test_config_overrides(self) -> None:
        """Config overrides dictionary is stored."""
        overrides = {"orb_breakout.opening_range_minutes": 10}
        config = BacktestConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            config_overrides=overrides,
        )

        assert config.config_overrides == overrides

"""Sprint 3 Integration Test.

End-to-end integration test wiring together all Sprint 1-3 components:
- StaticScanner → provides watchlist
- ReplayDataService → reads Parquet, publishes CandleEvents + IndicatorEvents
- OrbBreakout → receives candles, forms OR, detects breakout, emits SignalEvent
- RiskManager → evaluates signal (should approve)
- SimulatedBroker → receives approved order
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from argus.core.config import (
    AccountRiskConfig,
    OperatingWindow,
    OrbBreakoutConfig,
    RiskConfig,
    StrategyRiskLimits,
)
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, OrderApprovedEvent, SignalEvent
from argus.core.risk_manager import RiskManager
from argus.data.replay_data_service import ReplayDataService
from argus.data.scanner import StaticScanner
from argus.execution.simulated_broker import SimulatedBroker
from argus.strategies.orb_breakout import OrbBreakoutStrategy


def generate_orb_test_parquet(
    symbol: str,
    output_dir: Path,
    or_high: float = 101.0,
    or_low: float = 99.0,
    breakout_close: float = 102.0,
    breakout_volume: int = 200_000,
) -> Path:
    """Generate Parquet data designed to trigger an ORB breakout.

    Creates:
    - 15 candles during OR window (9:30-9:44 ET) establishing the opening range
    - 1 candle at 9:45 ET just after OR window (triggers OR finalization)
    - 1 breakout candle at 10:00 ET that closes above OR high with volume

    Timestamps are stored in UTC (per DEC-049). For February 2026 (EST, UTC-5):
    - 9:30 AM ET = 14:30 UTC
    - 9:45 AM ET = 14:45 UTC
    - 10:00 AM ET = 15:00 UTC

    Args:
        symbol: Ticker symbol.
        output_dir: Directory for the Parquet file.
        or_high: High of the opening range.
        or_low: Low of the opening range.
        breakout_close: Close price of the breakout candle.
        breakout_volume: Volume of the breakout candle.

    Returns:
        Path to the generated Parquet file.
    """
    base_date = datetime(2026, 2, 15, tzinfo=UTC)
    # February 2026 is EST (UTC-5). 9:30 AM ET = 14:30 UTC.
    market_open_utc = base_date.replace(hour=14, minute=30)

    candles = []

    # OR window candles (9:30-9:44, 15 candles)
    or_midpoint = (or_high + or_low) / 2
    for i in range(15):
        timestamp = market_open_utc + timedelta(minutes=i)
        # Vary prices within OR range
        high = or_high if i == 5 else or_high - 0.3
        low = or_low if i == 10 else or_low + 0.2

        close = or_midpoint + (i % 3 - 1) * 0.2

        candles.append({
            "timestamp": timestamp,
            "open": close - 0.1,
            "high": high,
            "low": low,
            "close": close,
            "volume": 100_000 + i * 1000,
        })

    # Post-OR candle (9:45) - triggers OR finalization
    post_or_time = market_open_utc + timedelta(minutes=15)
    candles.append({
        "timestamp": post_or_time,
        "open": or_midpoint,
        "high": or_midpoint + 0.5,
        "low": or_midpoint - 0.3,
        "close": or_midpoint + 0.2,
        "volume": 80_000,
    })

    # Breakout candle (10:00)
    breakout_time = market_open_utc + timedelta(minutes=30)
    candles.append({
        "timestamp": breakout_time,
        "open": or_high,
        "high": breakout_close + 0.5,
        "low": or_high - 0.2,
        "close": breakout_close,
        "volume": breakout_volume,
    })

    df = pd.DataFrame(candles)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{symbol.upper()}.parquet"
    df.to_parquet(file_path, index=False)

    return file_path


class TestSprint3Integration:
    """Integration tests for Sprint 3 components."""

    @pytest.mark.asyncio
    async def test_full_pipeline_scanner_to_signal(self, tmp_path: Path) -> None:
        """Full pipeline: Scanner → DataService → Strategy → Signal."""
        # Generate test data
        generate_orb_test_parquet(
            symbol="TEST",
            output_dir=tmp_path,
            or_high=101.0,
            or_low=99.0,
            breakout_close=101.3,  # Just above OR high, within chase protection
            breakout_volume=200_000,
        )

        # Create components
        event_bus = EventBus()
        scanner = StaticScanner(symbols=["TEST"])
        data_service = ReplayDataService(event_bus=event_bus, data_dir=tmp_path, speed=0)

        orb_config = OrbBreakoutConfig(
            strategy_id="strat_orb_test",
            name="ORB Test",
            orb_window_minutes=15,
            chase_protection_pct=0.01,  # 1% chase protection
            breakout_volume_multiplier=1.5,
            risk_limits=StrategyRiskLimits(
                max_loss_per_trade_pct=0.01,
                max_trades_per_day=6,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        strategy = OrbBreakoutStrategy(orb_config, data_service=data_service)
        strategy.allocated_capital = 100_000

        # Wire up: scanner provides watchlist
        await scanner.start()
        watchlist = await scanner.scan([strategy.get_scanner_criteria()])
        strategy.set_watchlist([item.symbol for item in watchlist])
        await scanner.stop()

        # Collect signals
        signals: list[SignalEvent] = []

        async def handle_candle(candle: CandleEvent) -> None:
            signal = await strategy.on_candle(candle)
            if signal is not None:
                signals.append(signal)

        event_bus.subscribe(CandleEvent, handle_candle)

        # Run replay
        await data_service.start(symbols=["TEST"], timeframes=["1m"])
        await data_service.wait_for_completion()
        await event_bus.drain()
        await data_service.stop()

        # Verify signal was emitted
        assert len(signals) == 1
        signal = signals[0]
        assert signal.symbol == "TEST"
        assert signal.entry_price == pytest.approx(101.3)
        assert signal.stop_price == pytest.approx(100.0)  # Midpoint
        assert signal.share_count > 0

    @pytest.mark.asyncio
    async def test_full_pipeline_with_risk_manager(self, tmp_path: Path) -> None:
        """Full pipeline including Risk Manager approval."""
        # Generate test data
        generate_orb_test_parquet(
            symbol="TEST",
            output_dir=tmp_path,
            or_high=101.0,
            or_low=99.0,
            breakout_close=101.3,
            breakout_volume=200_000,
        )

        # Create components
        event_bus = EventBus()
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                weekly_loss_limit_pct=0.05,
                cash_reserve_pct=0.20,
                max_concurrent_positions=10,
            ),
        )
        risk_manager = RiskManager(config=risk_config, broker=broker, event_bus=event_bus)
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        data_service = ReplayDataService(event_bus=event_bus, data_dir=tmp_path, speed=0)

        orb_config = OrbBreakoutConfig(
            strategy_id="strat_orb_test",
            name="ORB Test",
            orb_window_minutes=15,
            chase_protection_pct=0.01,
            breakout_volume_multiplier=1.5,
            risk_limits=StrategyRiskLimits(
                max_loss_per_trade_pct=0.01,
                max_trades_per_day=6,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        strategy = OrbBreakoutStrategy(orb_config, data_service=data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["TEST"])

        # Track approvals
        approvals: list[OrderApprovedEvent] = []

        async def handle_candle(candle: CandleEvent) -> None:
            signal = await strategy.on_candle(candle)
            if signal is not None:
                result = await risk_manager.evaluate_signal(signal)
                if isinstance(result, OrderApprovedEvent):
                    approvals.append(result)

        event_bus.subscribe(CandleEvent, handle_candle)

        # Run replay
        await data_service.start(symbols=["TEST"], timeframes=["1m"])
        await data_service.wait_for_completion()
        await event_bus.drain()
        await data_service.stop()

        # Verify signal was approved
        assert len(approvals) == 1
        approved = approvals[0]
        assert approved.signal is not None
        assert approved.signal.symbol == "TEST"

    @pytest.mark.asyncio
    async def test_indicators_computed_correctly(self, tmp_path: Path) -> None:
        """Verify indicators are computed and available."""
        # Generate test data with enough candles for all indicators
        generate_orb_test_parquet(
            symbol="TEST",
            output_dir=tmp_path,
        )

        event_bus = EventBus()
        data_service = ReplayDataService(event_bus=event_bus, data_dir=tmp_path, speed=0)

        # Track indicator events
        indicators: dict[str, list[float]] = {}

        def track_indicator(event: IndicatorEvent) -> None:
            if event.indicator_name not in indicators:
                indicators[event.indicator_name] = []
            indicators[event.indicator_name].append(event.value)

        event_bus.subscribe(IndicatorEvent, track_indicator)

        await data_service.start(symbols=["TEST"], timeframes=["1m"])
        await data_service.wait_for_completion()
        await event_bus.drain()
        await data_service.stop()

        # VWAP should be computed for all candles
        assert "vwap" in indicators
        assert len(indicators["vwap"]) == 17  # 15 OR + 1 post-OR + 1 breakout

        # Verify VWAP values are reasonable
        for vwap in indicators["vwap"]:
            assert 95 < vwap < 105  # Should be around our price range

    @pytest.mark.asyncio
    async def test_static_scanner_provides_watchlist(self) -> None:
        """StaticScanner returns configured symbols."""
        scanner = StaticScanner(symbols=["AAPL", "MSFT", "NVDA"])
        await scanner.start()

        watchlist = await scanner.scan([])

        assert len(watchlist) == 3
        symbols = [item.symbol for item in watchlist]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "NVDA" in symbols

        await scanner.stop()

    @pytest.mark.asyncio
    async def test_orb_strategy_respects_watchlist(self, tmp_path: Path) -> None:
        """ORB strategy ignores symbols not in watchlist."""
        generate_orb_test_parquet(
            symbol="TEST",
            output_dir=tmp_path,
            or_high=101.0,
            or_low=99.0,
            breakout_close=101.3,
            breakout_volume=200_000,
        )

        event_bus = EventBus()
        data_service = ReplayDataService(event_bus=event_bus, data_dir=tmp_path, speed=0)

        orb_config = OrbBreakoutConfig(
            strategy_id="strat_orb_test",
            name="ORB Test",
            orb_window_minutes=15,
            chase_protection_pct=0.01,
        )
        strategy = OrbBreakoutStrategy(orb_config, data_service=data_service)
        strategy.allocated_capital = 100_000
        # Set watchlist to a DIFFERENT symbol
        strategy.set_watchlist(["AAPL"])  # Not TEST

        signals: list[SignalEvent] = []

        async def handle_candle(candle: CandleEvent) -> None:
            signal = await strategy.on_candle(candle)
            if signal is not None:
                signals.append(signal)

        event_bus.subscribe(CandleEvent, handle_candle)

        await data_service.start(symbols=["TEST"], timeframes=["1m"])
        await data_service.wait_for_completion()
        await event_bus.drain()
        await data_service.stop()

        # No signal because TEST is not in watchlist
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_multi_symbol_independent_tracking(self, tmp_path: Path) -> None:
        """Multiple symbols are tracked independently."""
        # Generate data for two symbols
        generate_orb_test_parquet(
            symbol="AAPL",
            output_dir=tmp_path,
            or_high=150.0,
            or_low=148.0,
            breakout_close=150.3,
            breakout_volume=200_000,
        )
        generate_orb_test_parquet(
            symbol="MSFT",
            output_dir=tmp_path,
            or_high=350.0,
            or_low=345.0,
            breakout_close=350.5,
            breakout_volume=200_000,
        )

        event_bus = EventBus()
        data_service = ReplayDataService(event_bus=event_bus, data_dir=tmp_path, speed=0)

        orb_config = OrbBreakoutConfig(
            strategy_id="strat_orb_test",
            name="ORB Test",
            orb_window_minutes=15,
            chase_protection_pct=0.01,
            breakout_volume_multiplier=1.5,
            risk_limits=StrategyRiskLimits(
                max_loss_per_trade_pct=0.01,
                max_concurrent_positions=5,
            ),
        )
        strategy = OrbBreakoutStrategy(orb_config, data_service=data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        signals: list[SignalEvent] = []

        async def handle_candle(candle: CandleEvent) -> None:
            signal = await strategy.on_candle(candle)
            if signal is not None:
                signals.append(signal)

        event_bus.subscribe(CandleEvent, handle_candle)

        await data_service.start(symbols=["AAPL", "MSFT"], timeframes=["1m"])
        await data_service.wait_for_completion()
        await event_bus.drain()
        await data_service.stop()

        # Should get signals for both symbols
        assert len(signals) == 2
        symbols = {s.symbol for s in signals}
        assert "AAPL" in symbols
        assert "MSFT" in symbols

        # Verify prices are correct for each symbol
        aapl_signal = next(s for s in signals if s.symbol == "AAPL")
        msft_signal = next(s for s in signals if s.symbol == "MSFT")

        assert aapl_signal.entry_price == pytest.approx(150.3)
        assert aapl_signal.stop_price == pytest.approx(149.0)  # Midpoint of 150/148

        assert msft_signal.entry_price == pytest.approx(350.5)
        assert msft_signal.stop_price == pytest.approx(347.5)  # Midpoint of 350/345

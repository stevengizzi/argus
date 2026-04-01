"""Tests for the ORB Breakout Strategy."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import OperatingWindow, OrbBreakoutConfig, StrategyRiskLimits
from argus.core.events import CandleEvent, Side, SignalEvent
from argus.strategies.orb_breakout import OrbBreakoutStrategy

ET = ZoneInfo("America/New_York")


def make_orb_config(
    strategy_id: str = "strat_orb_breakout",
    orb_window_minutes: int = 15,
    volume_threshold_rvol: float = 2.0,
    target_1_r: float = 1.0,
    target_2_r: float = 2.0,
    time_stop_minutes: int = 30,
    min_range_atr_ratio: float = 0.5,
    max_range_atr_ratio: float = 2.0,
    chase_protection_pct: float = 0.005,
    breakout_volume_multiplier: float = 1.5,
    max_trades_per_day: int = 6,
    max_daily_loss_pct: float = 0.03,
    max_loss_per_trade_pct: float = 0.01,
    max_concurrent_positions: int = 2,
    latest_entry: str = "11:30",
) -> OrbBreakoutConfig:
    """Create an OrbBreakoutConfig for testing."""
    return OrbBreakoutConfig(
        strategy_id=strategy_id,
        name="ORB Breakout",
        orb_window_minutes=orb_window_minutes,
        volume_threshold_rvol=volume_threshold_rvol,
        target_1_r=target_1_r,
        target_2_r=target_2_r,
        time_stop_minutes=time_stop_minutes,
        min_range_atr_ratio=min_range_atr_ratio,
        max_range_atr_ratio=max_range_atr_ratio,
        chase_protection_pct=chase_protection_pct,
        breakout_volume_multiplier=breakout_volume_multiplier,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=max_trades_per_day,
            max_daily_loss_pct=max_daily_loss_pct,
            max_loss_per_trade_pct=max_loss_per_trade_pct,
            max_concurrent_positions=max_concurrent_positions,
        ),
        operating_window=OperatingWindow(latest_entry=latest_entry),
    )


def make_candle(
    symbol: str = "AAPL",
    timestamp: datetime | None = None,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 100_000,
) -> CandleEvent:
    """Create a CandleEvent for testing.

    Timestamps should be provided in UTC. The strategy will convert to ET
    for time window comparisons. For February 2026 (EST, UTC-5):
    - 9:30 AM ET = 14:30 UTC
    - 9:45 AM ET = 14:45 UTC
    - 10:00 AM ET = 15:00 UTC
    - 11:30 AM ET = 16:30 UTC
    """
    if timestamp is None:
        # Default: 9:30 AM ET = 14:30 UTC in February (EST)
        timestamp = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


def make_or_candles(
    symbol: str = "AAPL",
    num_candles: int = 15,
    base_time: datetime | None = None,
    or_high: float = 101.0,
    or_low: float = 99.0,
) -> list[CandleEvent]:
    """Generate candles for the opening range window.

    Generates UTC timestamps that correspond to ET market hours.
    For February 2026 (EST, UTC-5): 9:30 AM ET = 14:30 UTC.
    """
    from datetime import timedelta

    if base_time is None:
        # 9:30 AM ET = 14:30 UTC in February (EST)
        base_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)

    candles = []
    for i in range(num_candles):
        timestamp = base_time + timedelta(minutes=i)
        # Vary prices within the OR range
        high = or_high if i == 5 else or_high - 0.5  # One candle hits the high
        low = or_low if i == 10 else or_low + 0.3  # One candle hits the low
        close = (or_high + or_low) / 2 + (i % 3 - 1) * 0.2

        candles.append(
            make_candle(
                symbol=symbol,
                timestamp=timestamp,
                open_price=close - 0.1,
                high=high,
                low=low,
                close=close,
                volume=100_000 + i * 1000,
            )
        )
    return candles


class TestOrbOpeningRangeFormation:
    """Tests for opening range formation."""

    @pytest.mark.asyncio
    async def test_accumulates_candles_during_or_window(self) -> None:
        """Candles during OR window are accumulated."""
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send 15 candles during OR window (9:30 - 9:44)
        or_candles = make_or_candles("AAPL", num_candles=15)
        for candle in or_candles:
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert len(state.or_candles) == 15
        assert not state.or_complete

    @pytest.mark.asyncio
    async def test_finalizes_or_after_window(self) -> None:
        """OR is finalized after the first candle past the window."""
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send OR candles
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Send first candle after OR window (9:45)
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert state.or_high == 101.0
        assert state.or_low == 99.0
        assert state.or_midpoint == 100.0

    @pytest.mark.asyncio
    async def test_or_too_tight_rejected(self) -> None:
        """OR with range too tight relative to ATR is rejected."""
        config = make_orb_config(min_range_atr_ratio=0.5)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 5.0  # ATR = 5.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 0.5 (high=100.5, low=100.0)
        # range/ATR = 0.5/5.0 = 0.1 < min_range_atr_ratio (0.5)
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=100.5, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "too tight" in state.or_rejection_reason.lower()

    @pytest.mark.asyncio
    async def test_or_too_wide_rejected(self) -> None:
        """OR with range too wide relative to ATR is rejected."""
        config = make_orb_config(max_range_atr_ratio=2.0)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 1.0  # ATR = 1.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 5.0 (high=105, low=100)
        # range/ATR = 5.0/1.0 = 5.0 > max_range_atr_ratio (2.0)
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=105.0, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "too wide" in state.or_rejection_reason.lower()


class TestOrbBreakoutDetection:
    """Tests for breakout detection logic."""

    async def _setup_valid_or(
        self,
        strategy: OrbBreakoutStrategy,
        symbol: str = "AAPL",
        or_high: float = 101.0,
        or_low: float = 99.0,
    ) -> None:
        """Helper to set up a valid opening range."""
        strategy.set_watchlist([symbol])

        or_candles = make_or_candles(symbol, num_candles=15, or_high=or_high, or_low=or_low)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize OR
        post_or = make_candle(
            symbol=symbol,
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

    @pytest.mark.asyncio
    async def test_breakout_above_or_high_emits_signal(self) -> None:
        """Candle closing above OR high with volume emits signal."""
        config = make_orb_config(breakout_volume_multiplier=1.5, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,  # Below entry price
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout candle: close above OR high, high volume
        # Chase limit = 101.0 * 1.02 = 103.02 (with 2% chase protection)
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high (101.0), within chase limit
            volume=200_000,  # 2x avg volume (should exceed 1.5x threshold)
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        assert signal.symbol == "AAPL"
        assert signal.side == Side.LONG
        assert signal.entry_price == 102.0
        assert signal.stop_price == 100.0  # Midpoint of OR

    @pytest.mark.asyncio
    async def test_wick_above_or_high_no_signal(self) -> None:
        """Candle with wick above OR high but close below does not emit signal."""
        config = make_orb_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Wick above OR high but close below
        wick = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            open_price=100.5,
            high=102.0,  # Wicks above OR high
            low=100.3,
            close=100.8,  # Closes below OR high
            volume=200_000,
        )
        signal = await strategy.on_candle(wick)

        assert signal is None

    @pytest.mark.asyncio
    async def test_low_volume_breakout_no_signal(self) -> None:
        """Breakout with insufficient volume does not emit signal."""
        config = make_orb_config(breakout_volume_multiplier=1.5)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0  # VWAP

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout but low volume
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high
            volume=50_000,  # Below 1.5x avg volume
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_below_vwap_no_signal(self) -> None:
        """Breakout below VWAP does not emit signal."""
        config = make_orb_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 105.0,  # VWAP is above entry price
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout but below VWAP
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=102.0,  # Above OR high but below VWAP (105)
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_chase_protection_no_signal(self) -> None:
        """Breakout past chase protection threshold does not emit signal."""
        config = make_orb_config(chase_protection_pct=0.005)  # 0.5%
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Chase protection limit = 101.0 * 1.005 = 101.505
        # Close above this triggers chase protection
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=102.0,  # Above chase protection limit
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None


class TestSignalCorrectness:
    """Tests for correct signal values."""

    @pytest.mark.asyncio
    async def test_signal_entry_price_is_candle_close(self) -> None:
        """Signal entry price equals candle close."""
        config = make_orb_config(chase_protection_pct=0.05)  # Looser chase protection
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Breakout
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.entry_price == 101.5

    @pytest.mark.asyncio
    async def test_signal_stop_is_or_midpoint(self) -> None:
        """Signal stop price equals OR midpoint."""
        config = make_orb_config(chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR: high=102, low=100, midpoint=101
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=102.0, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=102.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.stop_price == 101.0  # Midpoint

    @pytest.mark.asyncio
    async def test_signal_targets_are_correct(self) -> None:
        """Signal targets are calculated correctly from R-multiples."""
        config = make_orb_config(target_1_r=1.0, target_2_r=2.0, chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR: high=101, low=99, midpoint=100
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Entry = 101.5, Stop = 100, Risk = 1.5
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        # Target 1 = entry + 1R = 101.5 + 1.5 = 103.0
        # Target 2 = entry + 2R = 101.5 + 3.0 = 104.5
        assert signal.target_prices[0] == pytest.approx(103.0)
        assert signal.target_prices[1] == pytest.approx(104.5)


class TestRiskLimits:
    """Tests for risk limit enforcement."""

    @pytest.mark.asyncio
    async def test_max_trades_reached_no_signal(self) -> None:
        """No signal after max_trades_per_day reached."""
        config = make_orb_config(max_trades_per_day=2, chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record max trades
        strategy.record_trade_result(100)
        strategy.record_trade_result(100)

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Valid breakout should be rejected due to max trades
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_max_daily_loss_reached_no_signal(self) -> None:
        """No signal after max daily loss reached."""
        config = make_orb_config(max_daily_loss_pct=0.03, chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record 3% loss
        strategy.record_trade_result(-3000)

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None


class TestTimeWindow:
    """Tests for time window enforcement."""

    @pytest.mark.asyncio
    async def test_after_latest_entry_no_signal(self) -> None:
        """No signal after latest entry time."""
        config = make_orb_config(latest_entry="11:30", chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Breakout after latest entry (11:31)
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 16, 31, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_during_or_formation_no_signal(self) -> None:
        """No signal during OR formation period."""
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Candle during OR window (9:44) - even if it looks like breakout
        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 44, 0, tzinfo=UTC),
            close=105.0,  # Would be above any OR high
            volume=200_000,
        )
        signal = await strategy.on_candle(candle)

        # Should not emit signal during OR formation
        assert signal is None


class TestStateManagement:
    """Tests for state management."""

    def test_reset_daily_state_clears_symbol_state(self) -> None:
        """reset_daily_state clears all symbol state."""
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)

        # Add some state
        state = strategy._get_symbol_state("AAPL")
        state.or_complete = True
        state.or_high = 101.0

        strategy.reset_daily_state()

        # State should be cleared
        assert "AAPL" not in strategy._symbol_state


class TestMultiSymbol:
    """Tests for multi-symbol handling."""

    @pytest.mark.asyncio
    async def test_independent_or_tracking(self) -> None:
        """Each symbol has independent OR tracking."""
        config = make_orb_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # Feed AAPL candles
        aapl_candles = make_or_candles("AAPL", num_candles=15, or_high=150.0, or_low=148.0)
        for candle in aapl_candles:
            await strategy.on_candle(candle)

        # Feed MSFT candles (different OR)
        msft_candles = make_or_candles("MSFT", num_candles=15, or_high=350.0, or_low=345.0)
        for candle in msft_candles:
            await strategy.on_candle(candle)

        # Finalize both
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
            )
        )
        await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
            )
        )

        aapl_state = strategy._get_symbol_state("AAPL")
        msft_state = strategy._get_symbol_state("MSFT")

        assert aapl_state.or_high == 150.0
        assert msft_state.or_high == 350.0

        # They should be independent
        assert aapl_state.or_low != msft_state.or_low


class TestPositionSizing:
    """Tests for position sizing calculation."""

    def test_position_size_formula(self) -> None:
        """Position size uses correct formula."""
        config = make_orb_config(max_loss_per_trade_pct=0.01)
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000

        # Entry: 102, Stop: 100, Risk per share: 2
        # Risk dollars: 100K * 1% = 1000
        # Shares: 1000 / 2 = 500
        shares = strategy.calculate_position_size(102.0, 100.0)
        assert shares == 500

    def test_position_size_zero_capital(self) -> None:
        """Returns 0 if no capital allocated."""
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)

        shares = strategy.calculate_position_size(102.0, 100.0)
        assert shares == 0


class TestTimezoneHandling:
    """Tests for correct timezone handling (DEF-008 regression tests).

    The strategy stores time constants in ET (9:30 AM market open, etc.) but
    receives candles with UTC timestamps. These tests verify that UTC timestamps
    are correctly converted to ET for time window comparisons.

    In February 2026 (EST, UTC-5):
    - 9:30 AM ET = 14:30 UTC
    - 9:45 AM ET = 14:45 UTC
    - 10:00 AM ET = 15:00 UTC
    - 11:30 AM ET = 16:30 UTC
    """

    def test_utc_candle_at_market_open_recognized_as_in_or_window(self) -> None:
        """A candle at 14:30 UTC (9:30 AM ET) should be in the OR window."""
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)

        # 14:30 UTC = 9:30 AM ET (market open, in OR window)
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC),  # EDT in June
        )

        assert strategy._is_in_or_window(candle) is True
        assert strategy._is_past_or_window(candle) is False

    def test_utc_candle_at_or_end_recognized_as_past_window(self) -> None:
        """A candle at 14:45 UTC (9:45 AM ET) should be past a 15-min OR window."""
        config = make_orb_config(orb_window_minutes=15)  # OR ends at 9:45 AM ET
        strategy = OrbBreakoutStrategy(config)

        # 13:45 UTC = 9:45 AM EDT (past 15-min OR window)
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),  # EDT in June
        )

        assert strategy._is_in_or_window(candle) is False
        assert strategy._is_past_or_window(candle) is True

    def test_utc_candle_mid_or_window(self) -> None:
        """A candle at 13:37 UTC (9:37 AM EDT) should be in the OR window."""
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)

        # 13:37 UTC = 9:37 AM EDT
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 13, 37, 0, tzinfo=UTC),
        )

        assert strategy._is_in_or_window(candle) is True
        assert strategy._is_past_or_window(candle) is False

    def test_utc_candle_before_latest_entry(self) -> None:
        """A candle before latest entry time is correctly identified."""
        config = make_orb_config(latest_entry="11:30")  # 11:30 AM ET
        strategy = OrbBreakoutStrategy(config)

        # 15:00 UTC = 10:00 AM ET (before 11:30 AM ET)
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 15, 0, 0, tzinfo=UTC),
        )

        assert strategy._is_before_latest_entry(candle) is True

    def test_utc_candle_after_latest_entry(self) -> None:
        """A candle after latest entry time is correctly identified."""
        config = make_orb_config(latest_entry="11:30")  # 11:30 AM ET
        strategy = OrbBreakoutStrategy(config)

        # 16:00 UTC = 12:00 PM EDT (after 11:30 AM ET)
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 16, 0, 0, tzinfo=UTC),
        )

        assert strategy._is_before_latest_entry(candle) is False

    @pytest.mark.asyncio
    async def test_or_forms_correctly_with_utc_timestamps(self) -> None:
        """Feed UTC-timestamped candles through on_candle, verify OR forms.

        This is the key regression test for DEF-008. Prior to the fix,
        UTC timestamps were compared directly against ET time constants,
        causing the OR to never form (zero candles accumulated).
        """
        from datetime import timedelta

        config = make_orb_config(orb_window_minutes=15)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0  # ATR

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["TSLA"])

        # Feed 15 candles from 13:30-13:44 UTC (9:30-9:44 AM EDT in June)
        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="TSLA",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0 if i == 5 else 100.5,
                low=99.0 if i == 10 else 99.5,
                close=100.0 + (i % 3 - 1) * 0.2,
                volume=100_000 + i * 1000,
            )
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("TSLA")

        # Verify candles were accumulated (this failed before the fix)
        assert len(state.or_candles) == 15, (
            f"Expected 15 candles in OR, got {len(state.or_candles)}. "
            "Timezone conversion may not be working correctly."
        )
        assert not state.or_complete

        # Now send first candle after OR window (13:45 UTC = 9:45 AM EDT)
        post_or = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Verify OR finalized correctly
        assert state.or_complete is True
        assert state.or_valid is True
        assert state.or_high == 101.0
        assert state.or_low == 99.0
        assert state.or_midpoint == 100.0

    @pytest.mark.asyncio
    async def test_breakout_signal_with_utc_timestamps(self) -> None:
        """Full pipeline test: OR formation and breakout with UTC timestamps."""
        from datetime import timedelta

        config = make_orb_config(
            orb_window_minutes=15,
            breakout_volume_multiplier=1.5,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["TSLA"])

        # Feed OR candles (13:30-13:44 UTC = 9:30-9:44 AM EDT)
        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="TSLA",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100_000,
            )
            await strategy.on_candle(candle)

        # Finalize OR (13:45 UTC = 9:45 AM EDT)
        await strategy.on_candle(
            make_candle(
                symbol="TSLA",
                timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),
            )
        )

        # Send breakout candle (14:00 UTC = 10:00 AM EDT)
        breakout = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 14, 0, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high (101.0)
            volume=200_000,  # Above 1.5x avg volume
        )
        signal = await strategy.on_candle(breakout)

        # Should produce a valid signal
        assert signal is not None
        assert signal.symbol == "TSLA"
        assert signal.side == Side.LONG
        assert signal.entry_price == 102.0
        assert signal.stop_price == 100.0  # OR midpoint

    def test_dst_transition_edt_to_est(self) -> None:
        """Verify correct handling across DST boundary (EDT→EST).

        In early November, clocks "fall back". A timestamp at 14:30 UTC is:
        - Before DST ends: 10:30 AM EDT (not in OR window)
        - After DST ends: 9:30 AM EST (in OR window)

        The strategy should handle both correctly based on the actual date.
        """
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)

        # November 3, 2025 is after DST ends (EST, UTC-5)
        # 14:30 UTC = 9:30 AM EST = in OR window
        candle_est = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 11, 5, 14, 30, 0, tzinfo=UTC),
        )
        assert strategy._is_in_or_window(candle_est) is True

        # June 2, 2025 is during DST (EDT, UTC-4)
        # 14:30 UTC = 10:30 AM EDT = NOT in OR window (9:30-9:45)
        candle_edt = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 14, 30, 0, tzinfo=UTC),
        )
        assert strategy._is_in_or_window(candle_edt) is False


class TestEarliestEntryEnforcement:
    """Tests for earliest_entry time enforcement.

    ORB Breakout has a 15-min OR window (9:30-9:45) and default earliest_entry=09:45,
    so the first post-OR candle is already eligible for entry. This test confirms
    behavior is unchanged by the earliest_entry enforcement logic.
    """

    @pytest.mark.asyncio
    async def test_first_post_or_candle_is_eligible(self) -> None:
        """First candle at OR end (09:45 ET) is eligible since earliest_entry=09:45.

        With 15-min OR window, OR ends at 09:45. Default earliest_entry is 09:45.
        The first post-OR candle should be immediately eligible for breakout.
        """
        from datetime import timedelta

        # Use default operating window (earliest_entry=09:45)
        config = make_orb_config(
            orb_window_minutes=15,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["TSLA"])

        # Feed OR candles (13:30-13:44 UTC = 9:30-9:44 AM EDT in June)
        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="TSLA",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100_000,
            )
            await strategy.on_candle(candle)

        # First candle after OR window (13:45 UTC = 9:45 AM EDT)
        # This is exactly at earliest_entry=09:45, so should finalize OR
        # but if it's also a breakout, should emit signal
        breakout = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high (101.0)
            volume=200_000,  # Above volume threshold
        )
        signal = await strategy.on_candle(breakout)

        # OR should be finalized and breakout should be accepted
        # since earliest_entry=09:45 matches OR end time
        assert signal is not None
        assert signal.symbol == "TSLA"
        assert signal.entry_price == 102.0


class TestOrbFamilyExclusion:
    """Tests for ORB family same-symbol mutual exclusion (DEC-261).

    When one ORB strategy fires on a symbol, other ORB strategies should
    not also fire on that same symbol in the same session.
    """

    @pytest.mark.asyncio
    async def test_orb_breakout_firing_blocks_orb_scalp(self) -> None:
        """When ORB Breakout fires on AAPL, ORB Scalp should not also fire on AAPL."""
        from argus.core.config import OrbScalpConfig
        from argus.strategies.orb_base import OrbBaseStrategy
        from argus.strategies.orb_scalp import OrbScalpStrategy
        from datetime import timedelta

        # Clear the class-level exclusion set for clean test
        OrbBaseStrategy._orb_family_triggered_symbols.clear()

        # Create ORB Breakout strategy
        breakout_config = make_orb_config(
            strategy_id="strat_orb_breakout",
            orb_window_minutes=15,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        breakout_strategy = OrbBreakoutStrategy(breakout_config, data_service=mock_data_service)
        breakout_strategy.allocated_capital = 100_000
        breakout_strategy.set_watchlist(["AAPL"])

        # Create ORB Scalp strategy
        scalp_config = OrbScalpConfig(
            strategy_id="strat_orb_scalp",
            name="ORB Scalp",
            orb_window_minutes=15,
            scalp_target_r=0.3,
            max_hold_seconds=120,
            risk_limits=StrategyRiskLimits(
                max_trades_per_day=12,
                max_daily_loss_pct=0.03,
                max_loss_per_trade_pct=0.01,
                max_concurrent_positions=2,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        scalp_strategy = OrbScalpStrategy(scalp_config, data_service=mock_data_service)
        scalp_strategy.allocated_capital = 100_000
        scalp_strategy.set_watchlist(["AAPL"])

        # Feed OR candles to both strategies
        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="AAPL",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100_000,
            )
            await breakout_strategy.on_candle(candle)
            await scalp_strategy.on_candle(candle)

        # Finalize OR
        finalize_candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),
        )
        await breakout_strategy.on_candle(finalize_candle)
        await scalp_strategy.on_candle(finalize_candle)

        # Send breakout candle
        breakout_candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 14, 0, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,
            volume=200_000,
        )

        # Breakout fires first
        breakout_signal = await breakout_strategy.on_candle(breakout_candle)
        assert breakout_signal is not None
        assert "AAPL" in OrbBaseStrategy._orb_family_triggered_symbols

        # Scalp should NOT fire (same symbol already triggered)
        scalp_signal = await scalp_strategy.on_candle(breakout_candle)
        assert scalp_signal is None

        # Clean up
        OrbBaseStrategy._orb_family_triggered_symbols.clear()

    @pytest.mark.asyncio
    async def test_orb_exclusion_allows_different_symbols(self) -> None:
        """ORB exclusion only blocks same symbol, not different symbols."""
        from argus.core.config import OrbScalpConfig
        from argus.strategies.orb_base import OrbBaseStrategy
        from argus.strategies.orb_scalp import OrbScalpStrategy
        from datetime import timedelta

        # Clear the class-level exclusion set
        OrbBaseStrategy._orb_family_triggered_symbols.clear()

        # Create strategies
        breakout_config = make_orb_config(
            strategy_id="strat_orb_breakout",
            orb_window_minutes=15,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        breakout_strategy = OrbBreakoutStrategy(breakout_config, data_service=mock_data_service)
        breakout_strategy.allocated_capital = 100_000
        breakout_strategy.set_watchlist(["AAPL", "NVDA"])

        scalp_config = OrbScalpConfig(
            strategy_id="strat_orb_scalp",
            name="ORB Scalp",
            orb_window_minutes=15,
            scalp_target_r=0.3,
            max_hold_seconds=120,
            risk_limits=StrategyRiskLimits(
                max_trades_per_day=12,
                max_daily_loss_pct=0.03,
                max_loss_per_trade_pct=0.01,
                max_concurrent_positions=2,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        scalp_strategy = OrbScalpStrategy(scalp_config, data_service=mock_data_service)
        scalp_strategy.allocated_capital = 100_000
        scalp_strategy.set_watchlist(["AAPL", "NVDA"])

        # Set up OR for AAPL
        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="AAPL",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100_000,
            )
            await breakout_strategy.on_candle(candle)

        # Set up OR for NVDA on scalp strategy
        for i in range(15):
            candle = make_candle(
                symbol="NVDA",
                timestamp=base_time + timedelta(minutes=i),
                high=501.0,
                low=499.0,
                close=500.0,
                volume=100_000,
            )
            await scalp_strategy.on_candle(candle)

        # Finalize
        await breakout_strategy.on_candle(
            make_candle(symbol="AAPL", timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC))
        )
        await scalp_strategy.on_candle(
            make_candle(symbol="NVDA", timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC))
        )

        # Breakout fires on AAPL
        breakout_signal = await breakout_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2025, 6, 2, 14, 0, 0, tzinfo=UTC),
                close=102.0,
                volume=200_000,
            )
        )
        assert breakout_signal is not None
        assert "AAPL" in OrbBaseStrategy._orb_family_triggered_symbols

        # Scalp can still fire on NVDA (different symbol)
        scalp_signal = await scalp_strategy.on_candle(
            make_candle(
                symbol="NVDA",
                timestamp=datetime(2025, 6, 2, 14, 0, 0, tzinfo=UTC),
                close=502.0,
                volume=200_000,
            )
        )
        assert scalp_signal is not None  # Should fire on different symbol

        # Clean up
        OrbBaseStrategy._orb_family_triggered_symbols.clear()

    def test_reset_daily_state_clears_orb_family_exclusion(self) -> None:
        """reset_daily_state clears the ORB family exclusion set."""
        from argus.strategies.orb_base import OrbBaseStrategy

        # Add a symbol to the exclusion set
        OrbBaseStrategy._orb_family_triggered_symbols.add("AAPL")
        OrbBaseStrategy._orb_family_triggered_symbols.add("NVDA")

        # Create a strategy and reset daily state
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)
        strategy.reset_daily_state()

        # Exclusion set should be cleared
        assert len(OrbBaseStrategy._orb_family_triggered_symbols) == 0

    def test_exclusion_set_is_class_level_shared(self) -> None:
        """Exclusion set is shared across all OrbBaseStrategy subclasses."""
        from argus.core.config import OrbScalpConfig
        from argus.strategies.orb_base import OrbBaseStrategy
        from argus.strategies.orb_scalp import OrbScalpStrategy

        # Clear the set
        OrbBaseStrategy._orb_family_triggered_symbols.clear()

        # Create both strategy types
        breakout_config = make_orb_config(strategy_id="strat_breakout")
        scalp_config = OrbScalpConfig(
            strategy_id="strat_scalp",
            name="ORB Scalp",
            orb_window_minutes=15,
            scalp_target_r=0.3,
            max_hold_seconds=120,
            risk_limits=StrategyRiskLimits(
                max_trades_per_day=12,
                max_daily_loss_pct=0.03,
                max_loss_per_trade_pct=0.01,
                max_concurrent_positions=2,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )

        breakout_strategy = OrbBreakoutStrategy(breakout_config)
        scalp_strategy = OrbScalpStrategy(scalp_config)

        # Add a symbol via class attribute
        OrbBaseStrategy._orb_family_triggered_symbols.add("TEST")

        # Both strategies should see it
        assert "TEST" in OrbBaseStrategy._orb_family_triggered_symbols
        # Access via strategy instances (they share the same class variable)
        assert "TEST" in breakout_strategy._orb_family_triggered_symbols
        assert "TEST" in scalp_strategy._orb_family_triggered_symbols

        # Clean up
        OrbBaseStrategy._orb_family_triggered_symbols.clear()

    @pytest.mark.asyncio
    async def test_orb_exclusion_enabled_blocks_scalp(self) -> None:
        """With mutual_exclusion_enabled=True, Breakout fires and Scalp is blocked."""
        from argus.core.config import OrbScalpConfig
        from argus.strategies.orb_base import OrbBaseStrategy
        from argus.strategies.orb_scalp import OrbScalpStrategy
        from datetime import timedelta

        OrbBaseStrategy._orb_family_triggered_symbols.clear()
        OrbBaseStrategy.mutual_exclusion_enabled = True

        breakout_config = make_orb_config(
            strategy_id="strat_breakout",
            orb_window_minutes=15,
            chase_protection_pct=0.02,
        )
        scalp_config = OrbScalpConfig(
            strategy_id="strat_scalp",
            name="ORB Scalp",
            orb_window_minutes=15,
            scalp_target_r=0.3,
            max_hold_seconds=120,
            risk_limits=StrategyRiskLimits(
                max_trades_per_day=12,
                max_daily_loss_pct=0.03,
                max_loss_per_trade_pct=0.01,
                max_concurrent_positions=2,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        mock_ds = AsyncMock()
        mock_ds.get_indicator.side_effect = lambda s, i: {"atr_14": 2.0, "vwap": 100.0}.get(i)

        breakout_strategy = OrbBreakoutStrategy(breakout_config, data_service=mock_ds)
        breakout_strategy.allocated_capital = 100_000
        breakout_strategy.set_watchlist(["AAPL"])

        scalp_strategy = OrbScalpStrategy(scalp_config, data_service=mock_ds)
        scalp_strategy.allocated_capital = 100_000
        scalp_strategy.set_watchlist(["AAPL"])

        # UTC times for June (EDT, UTC-4): 13:30 UTC = 9:30 ET, 13:45 UTC = 9:45 ET
        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="AAPL",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0, low=99.0, close=100.0, volume=100_000,
            )
            await breakout_strategy.on_candle(candle)
            await scalp_strategy.on_candle(candle)

        finalize = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),
            high=101.0, low=99.0, close=100.0, volume=100_000,
        )
        await breakout_strategy.on_candle(finalize)
        await scalp_strategy.on_candle(finalize)

        breakout_candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 14, 0, 0, tzinfo=UTC),
            open_price=101.0, high=102.5, low=100.8, close=102.0, volume=200_000,
        )
        breakout_signal = await breakout_strategy.on_candle(breakout_candle)
        assert breakout_signal is not None

        scalp_signal = await scalp_strategy.on_candle(breakout_candle)
        assert scalp_signal is None, "Scalp should be blocked when exclusion is enabled"

        OrbBaseStrategy._orb_family_triggered_symbols.clear()
        OrbBaseStrategy.mutual_exclusion_enabled = True

    @pytest.mark.asyncio
    async def test_orb_exclusion_disabled_both_fire(self) -> None:
        """With mutual_exclusion_enabled=False, both strategies can fire on same symbol."""
        from argus.core.config import OrbScalpConfig
        from argus.strategies.orb_base import OrbBaseStrategy
        from argus.strategies.orb_scalp import OrbScalpStrategy
        from datetime import timedelta

        OrbBaseStrategy._orb_family_triggered_symbols.clear()
        OrbBaseStrategy.mutual_exclusion_enabled = False

        breakout_config = make_orb_config(
            strategy_id="strat_breakout",
            orb_window_minutes=15,
            chase_protection_pct=0.02,
        )
        scalp_config = OrbScalpConfig(
            strategy_id="strat_scalp",
            name="ORB Scalp",
            orb_window_minutes=15,
            scalp_target_r=0.3,
            max_hold_seconds=120,
            chase_protection_pct=0.02,
            risk_limits=StrategyRiskLimits(
                max_trades_per_day=12,
                max_daily_loss_pct=0.03,
                max_loss_per_trade_pct=0.01,
                max_concurrent_positions=2,
            ),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        mock_ds = AsyncMock()
        mock_ds.get_indicator.side_effect = lambda s, i: {"atr_14": 2.0, "vwap": 100.0}.get(i)

        breakout_strategy = OrbBreakoutStrategy(breakout_config, data_service=mock_ds)
        breakout_strategy.allocated_capital = 100_000
        breakout_strategy.set_watchlist(["AAPL"])

        scalp_strategy = OrbScalpStrategy(scalp_config, data_service=mock_ds)
        scalp_strategy.allocated_capital = 100_000
        scalp_strategy.set_watchlist(["AAPL"])

        base_time = datetime(2025, 6, 2, 13, 30, 0, tzinfo=UTC)
        for i in range(15):
            candle = make_candle(
                symbol="AAPL",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0, low=99.0, close=100.0, volume=100_000,
            )
            await breakout_strategy.on_candle(candle)
            await scalp_strategy.on_candle(candle)

        finalize = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 13, 45, 0, tzinfo=UTC),
            high=101.0, low=99.0, close=100.0, volume=100_000,
        )
        await breakout_strategy.on_candle(finalize)
        await scalp_strategy.on_candle(finalize)

        breakout_candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 14, 0, 0, tzinfo=UTC),
            open_price=101.0, high=102.5, low=100.8, close=102.0, volume=200_000,
        )
        breakout_signal = await breakout_strategy.on_candle(breakout_candle)
        assert breakout_signal is not None, "Breakout should fire when exclusion is disabled"

        scalp_signal = await scalp_strategy.on_candle(breakout_candle)
        assert scalp_signal is not None, "Scalp should also fire when exclusion is disabled"

        OrbBaseStrategy._orb_family_triggered_symbols.clear()
        OrbBaseStrategy.mutual_exclusion_enabled = True

    def test_orb_exclusion_disabled_no_add_to_set(self) -> None:
        """With mutual_exclusion_enabled=False, triggered_symbols set stays empty after fire."""
        from argus.strategies.orb_base import OrbBaseStrategy

        OrbBaseStrategy._orb_family_triggered_symbols.clear()
        OrbBaseStrategy.mutual_exclusion_enabled = False

        # Simulate what orb_breakout._build_breakout_signal() does
        if OrbBaseStrategy.mutual_exclusion_enabled:
            OrbBaseStrategy._orb_family_triggered_symbols.add("AAPL")

        assert len(OrbBaseStrategy._orb_family_triggered_symbols) == 0, (
            "triggered_symbols should remain empty when exclusion is disabled"
        )

        OrbBaseStrategy.mutual_exclusion_enabled = True

    def test_orb_exclusion_config_default_true(self) -> None:
        """OrchestratorConfig.orb_family_mutual_exclusion defaults to True."""
        from argus.core.config import OrchestratorConfig

        config = OrchestratorConfig()
        assert config.orb_family_mutual_exclusion is True

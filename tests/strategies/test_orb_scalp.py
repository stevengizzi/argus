"""Tests for the ORB Scalp Strategy.

RSK-017: Timezone regression tests are critical. The ORB timezone bug was silent
(zero trades, no errors). These tests verify ET conversion works correctly for
Scalp's time windows (09:45–11:30 ET).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import (
    OperatingWindow,
    OrbScalpConfig,
    StrategyRiskLimits,
    load_orb_scalp_config,
)
from argus.core.events import CandleEvent, SignalEvent
from argus.strategies.orb_scalp import OrbScalpStrategy

ET = ZoneInfo("America/New_York")


def make_scalp_config(
    strategy_id: str = "strat_orb_scalp",
    orb_window_minutes: int = 5,
    scalp_target_r: float = 0.3,
    max_hold_seconds: int = 120,
    stop_placement: str = "midpoint",
    min_range_atr_ratio: float = 0.5,
    max_range_atr_ratio: float = 999.0,
    chase_protection_pct: float = 0.005,
    breakout_volume_multiplier: float = 1.5,
    volume_threshold_rvol: float = 2.0,
    max_trades_per_day: int = 12,
    max_daily_loss_pct: float = 0.03,
    max_loss_per_trade_pct: float = 0.01,
    max_concurrent_positions: int = 3,
    earliest_entry: str = "09:45",
    latest_entry: str = "11:30",
) -> OrbScalpConfig:
    """Create an OrbScalpConfig for testing."""
    return OrbScalpConfig(
        strategy_id=strategy_id,
        name="ORB Scalp",
        orb_window_minutes=orb_window_minutes,
        scalp_target_r=scalp_target_r,
        max_hold_seconds=max_hold_seconds,
        stop_placement=stop_placement,
        min_range_atr_ratio=min_range_atr_ratio,
        max_range_atr_ratio=max_range_atr_ratio,
        chase_protection_pct=chase_protection_pct,
        breakout_volume_multiplier=breakout_volume_multiplier,
        volume_threshold_rvol=volume_threshold_rvol,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=max_trades_per_day,
            max_daily_loss_pct=max_daily_loss_pct,
            max_loss_per_trade_pct=max_loss_per_trade_pct,
            max_concurrent_positions=max_concurrent_positions,
        ),
        operating_window=OperatingWindow(
            earliest_entry=earliest_entry,
            latest_entry=latest_entry,
        ),
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
    - 9:35 AM ET = 14:35 UTC (OR ends for 5-min window)
    - 9:45 AM ET = 14:45 UTC (earliest scalp entry)
    - 11:30 AM ET = 16:30 UTC (latest entry)
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
    num_candles: int = 5,
    base_time: datetime | None = None,
    or_high: float = 101.0,
    or_low: float = 99.0,
) -> list[CandleEvent]:
    """Generate candles for the 5-minute opening range window.

    For February 2026 (EST, UTC-5): 9:30 AM ET = 14:30 UTC.
    """
    if base_time is None:
        # 9:30 AM ET = 14:30 UTC in February (EST)
        base_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)

    candles = []
    for i in range(num_candles):
        timestamp = base_time + timedelta(minutes=i)
        # Vary prices within the OR range
        high = or_high if i == 2 else or_high - 0.5  # One candle hits the high
        low = or_low if i == 3 else or_low + 0.3  # One candle hits the low
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


class TestOrbScalpConfig:
    """Tests for OrbScalpConfig validation."""

    def test_default_values(self) -> None:
        """Verify default configuration values."""
        config = OrbScalpConfig(strategy_id="test_scalp", name="Test Scalp")

        assert config.orb_window_minutes == 5
        assert config.scalp_target_r == 0.3
        assert config.max_hold_seconds == 120
        assert config.stop_placement == "midpoint"
        assert config.min_range_atr_ratio == 0.5
        assert config.max_range_atr_ratio == 999.0
        assert config.chase_protection_pct == 0.005
        assert config.breakout_volume_multiplier == 1.5
        assert config.volume_threshold_rvol == 2.0

    def test_validation_scalp_target_r_bounds(self) -> None:
        """scalp_target_r must be > 0 and <= 2.0."""
        # Valid
        config = make_scalp_config(scalp_target_r=0.3)
        assert config.scalp_target_r == 0.3

        config = make_scalp_config(scalp_target_r=2.0)
        assert config.scalp_target_r == 2.0

        # Invalid: 0 or negative
        with pytest.raises(ValueError):
            make_scalp_config(scalp_target_r=0)

        with pytest.raises(ValueError):
            make_scalp_config(scalp_target_r=-0.1)

        # Invalid: > 2.0
        with pytest.raises(ValueError):
            make_scalp_config(scalp_target_r=2.1)

    def test_validation_max_hold_seconds_bounds(self) -> None:
        """max_hold_seconds must be >= 10 and <= 600."""
        # Valid
        config = make_scalp_config(max_hold_seconds=10)
        assert config.max_hold_seconds == 10

        config = make_scalp_config(max_hold_seconds=600)
        assert config.max_hold_seconds == 600

        # Invalid
        with pytest.raises(ValueError):
            make_scalp_config(max_hold_seconds=9)

        with pytest.raises(ValueError):
            make_scalp_config(max_hold_seconds=601)

    def test_load_from_yaml(self, tmp_path: Path) -> None:
        """Test loading OrbScalpConfig from YAML file."""
        yaml_content = """
strategy_id: "strat_orb_scalp_test"
name: "ORB Scalp Test"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

orb_window_minutes: 5
scalp_target_r: 0.35
max_hold_seconds: 90
stop_placement: "midpoint"
min_range_atr_ratio: 0.6
max_range_atr_ratio: 500.0

risk_limits:
  max_trades_per_day: 10
  max_concurrent_positions: 2
"""
        config_path = tmp_path / "orb_scalp.yaml"
        config_path.write_text(yaml_content)

        config = load_orb_scalp_config(config_path)

        assert config.strategy_id == "strat_orb_scalp_test"
        assert config.scalp_target_r == 0.35
        assert config.max_hold_seconds == 90
        assert config.risk_limits.max_trades_per_day == 10


class TestOrbScalpStrategyInit:
    """Tests for OrbScalpStrategy initialization."""

    def test_strategy_id_from_config(self) -> None:
        """Strategy ID comes from config."""
        config = make_scalp_config(strategy_id="strat_orb_scalp")
        strategy = OrbScalpStrategy(config)

        assert strategy.strategy_id == "strat_orb_scalp"

    def test_or_window_calculates_correctly(self) -> None:
        """OR end time calculated from orb_window_minutes."""
        config = make_scalp_config(orb_window_minutes=5)
        strategy = OrbScalpStrategy(config)

        # 9:30 + 5 min = 9:35
        from datetime import time

        assert strategy._or_end_time == time(9, 35)


class TestOrbScalpOpeningRangeFormation:
    """Tests for opening range formation (inherited behavior)."""

    @pytest.mark.asyncio
    async def test_accumulates_candles_during_or_window(self) -> None:
        """Candles during 5-min OR window are accumulated."""
        config = make_scalp_config(orb_window_minutes=5)
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send 5 candles during OR window (9:30 - 9:34)
        or_candles = make_or_candles("AAPL", num_candles=5)
        for candle in or_candles:
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert len(state.or_candles) == 5
        assert not state.or_complete

    @pytest.mark.asyncio
    async def test_finalizes_or_after_window(self) -> None:
        """OR is finalized after the first candle past the 5-min window."""
        config = make_scalp_config(orb_window_minutes=5)
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send OR candles
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Send first candle after OR window (9:35 AM ET = 14:35 UTC)
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert state.or_high == 101.0
        assert state.or_low == 99.0
        assert state.or_midpoint == 100.0


class TestOrbScalpSignal:
    """Tests for scalp signal generation."""

    async def _setup_valid_or(
        self,
        strategy: OrbScalpStrategy,
        symbol: str = "AAPL",
        or_high: float = 101.0,
        or_low: float = 99.0,
    ) -> None:
        """Helper to set up a valid 5-min opening range."""
        strategy.set_watchlist([symbol])

        or_candles = make_or_candles(symbol, num_candles=5, or_high=or_high, or_low=or_low)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize OR (9:35 AM ET = 14:35 UTC)
        post_or = make_candle(
            symbol=symbol,
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

    @pytest.mark.asyncio
    async def test_signal_has_single_target(self) -> None:
        """Signal should have exactly one target price."""
        config = make_scalp_config(
            scalp_target_r=0.3,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout candle (must be after earliest_entry 09:45 ET = 14:45 UTC)
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),  # 9:50 AM ET
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        assert len(signal.target_prices) == 1

    @pytest.mark.asyncio
    async def test_signal_target_is_scalp_target_r(self) -> None:
        """Target should be entry + (risk × scalp_target_r)."""
        config = make_scalp_config(
            scalp_target_r=0.3,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        # OR: high=101, low=99, midpoint=100
        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Entry = 101.5, Stop = 100 (midpoint), Risk = 1.5
        # Target = 101.5 + (1.5 × 0.3) = 101.5 + 0.45 = 101.95
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.target_prices[0] == pytest.approx(101.95)

    @pytest.mark.asyncio
    async def test_signal_has_time_stop_seconds(self) -> None:
        """Signal should have time_stop_seconds set."""
        config = make_scalp_config(
            max_hold_seconds=120,
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.time_stop_seconds == 120

    @pytest.mark.asyncio
    async def test_signal_strategy_id_is_correct(self) -> None:
        """Signal strategy_id should match config."""
        config = make_scalp_config(
            strategy_id="strat_orb_scalp",
            chase_protection_pct=0.02,
        )
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.strategy_id == "strat_orb_scalp"


class TestOrbScalpExitRules:
    """Tests for exit rules configuration."""

    def test_exit_rules_single_target_100_pct(self) -> None:
        """Exit rules should have single target at 100% position."""
        config = make_scalp_config(scalp_target_r=0.3)
        strategy = OrbScalpStrategy(config)

        rules = strategy.get_exit_rules()

        assert len(rules.targets) == 1
        assert rules.targets[0].r_multiple == 0.3
        assert rules.targets[0].position_pct == 1.0

    def test_market_conditions_filter(self) -> None:
        """Market conditions should match ORB regimes."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        filter = strategy.get_market_conditions_filter()

        assert "bullish_trending" in filter.allowed_regimes
        assert "range_bound" in filter.allowed_regimes
        assert "high_volatility" in filter.allowed_regimes
        assert filter.max_vix == 35.0


class TestTimezoneHandling:
    """Tests for correct timezone handling (RSK-017 regression tests).

    The strategy stores time constants in ET (9:30 AM market open, etc.) but
    receives candles with UTC timestamps. These tests verify that UTC timestamps
    are correctly converted to ET for time window comparisons.

    Critical for Scalp strategy which has a tight operating window:
    - OR window: 9:30-9:35 ET (5 min)
    - Entry window: 9:45-11:30 ET
    """

    def test_utc_candle_at_market_open_recognized_as_in_or_window(self) -> None:
        """A candle at 14:30 UTC (9:30 AM ET EST) should be in the OR window."""
        config = make_scalp_config(orb_window_minutes=5)
        strategy = OrbScalpStrategy(config)

        # 14:30 UTC = 9:30 AM EST (market open, in OR window)
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC),  # EST in Feb
        )

        assert strategy._is_in_or_window(candle) is True
        assert strategy._is_past_or_window(candle) is False

    def test_utc_candle_at_or_end_recognized_as_past_window(self) -> None:
        """A candle at 14:35 UTC (9:35 AM ET EST) should be past a 5-min OR window."""
        config = make_scalp_config(orb_window_minutes=5)  # OR ends at 9:35 AM ET
        strategy = OrbScalpStrategy(config)

        # 14:35 UTC = 9:35 AM EST (past 5-min OR window)
        candle = make_candle(
            symbol="TSLA",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )

        assert strategy._is_in_or_window(candle) is False
        assert strategy._is_past_or_window(candle) is True

    def test_scalp_earliest_entry_time_check(self) -> None:
        """Verify earliest_entry (09:45 ET) is correctly enforced."""
        config = make_scalp_config(earliest_entry="09:45", latest_entry="11:30")
        strategy = OrbScalpStrategy(config)

        # 14:44 UTC = 9:44 AM EST (before earliest entry)
        candle_before = make_candle(
            symbol="TSLA",
            timestamp=datetime(2026, 2, 15, 14, 44, 0, tzinfo=UTC),
        )
        # 14:45 UTC = 9:45 AM EST (at earliest entry)
        candle_at = make_candle(
            symbol="TSLA",
            timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC),
        )
        # 14:50 UTC = 9:50 AM EST (after earliest entry, before latest)
        candle_after = make_candle(
            symbol="TSLA",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
        )

        # All should be before latest_entry (11:30 ET = 16:30 UTC)
        assert strategy._is_before_latest_entry(candle_before) is True
        assert strategy._is_before_latest_entry(candle_at) is True
        assert strategy._is_before_latest_entry(candle_after) is True

    @pytest.mark.asyncio
    async def test_or_forms_correctly_with_utc_timestamps(self) -> None:
        """Feed UTC-timestamped candles through on_candle, verify OR forms.

        This is the key regression test for timezone handling. Prior to DEC-061,
        UTC timestamps were compared directly against ET time constants,
        causing the OR to never form (zero candles accumulated).
        """
        config = make_scalp_config(orb_window_minutes=5)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0  # ATR

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["TSLA"])

        # Feed 5 candles from 14:30-14:34 UTC (9:30-9:34 AM EST in Feb)
        base_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
        for i in range(5):
            candle = make_candle(
                symbol="TSLA",
                timestamp=base_time + timedelta(minutes=i),
                high=101.0 if i == 2 else 100.5,
                low=99.0 if i == 3 else 99.5,
                close=100.0 + (i % 3 - 1) * 0.2,
                volume=100_000 + i * 1000,
            )
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("TSLA")

        # Verify candles were accumulated (this failed before DEC-061 fix)
        assert len(state.or_candles) == 5, (
            f"Expected 5 candles in OR, got {len(state.or_candles)}. "
            "Timezone conversion may not be working correctly."
        )
        assert not state.or_complete

        # Now send first candle after OR window (14:35 UTC = 9:35 AM EST)
        post_or = make_candle(
            symbol="TSLA",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Verify OR finalized correctly
        assert state.or_complete is True
        assert state.or_valid is True
        assert state.or_high == 101.0
        assert state.or_low == 99.0

    def test_dst_transition_edt_to_est(self) -> None:
        """Verify correct handling across DST boundary (EDT->EST).

        In early November, clocks "fall back". A timestamp at 14:30 UTC is:
        - Before DST ends: 10:30 AM EDT (not in OR window)
        - After DST ends: 9:30 AM EST (in OR window)
        """
        config = make_scalp_config(orb_window_minutes=5)
        strategy = OrbScalpStrategy(config)

        # November 5, 2025 is after DST ends (EST, UTC-5)
        # 14:30 UTC = 9:30 AM EST = in OR window
        candle_est = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 11, 5, 14, 30, 0, tzinfo=UTC),
        )
        assert strategy._is_in_or_window(candle_est) is True

        # June 2, 2025 is during DST (EDT, UTC-4)
        # 14:30 UTC = 10:30 AM EDT = NOT in OR window (9:30-9:35)
        candle_edt = make_candle(
            symbol="TSLA",
            timestamp=datetime(2025, 6, 2, 14, 30, 0, tzinfo=UTC),
        )
        assert strategy._is_in_or_window(candle_edt) is False

    @pytest.mark.asyncio
    async def test_entry_at_latest_entry_boundary_rejected(self) -> None:
        """Entry at 11:31 ET should be rejected (past latest_entry 11:30)."""
        config = make_scalp_config(latest_entry="11:30", chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize OR
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Breakout at 11:31 ET = 16:31 UTC (past latest entry)
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 16, 31, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None


class TestOrbScalpConfigValidation:
    """Additional config validation tests."""

    def test_orb_window_minutes_bounds(self) -> None:
        """orb_window_minutes must be >= 1 and <= 60."""
        # Valid
        config = make_scalp_config(orb_window_minutes=1)
        assert config.orb_window_minutes == 1

        config = make_scalp_config(orb_window_minutes=60)
        assert config.orb_window_minutes == 60

        # Invalid
        with pytest.raises(ValueError):
            make_scalp_config(orb_window_minutes=0)

        with pytest.raises(ValueError):
            make_scalp_config(orb_window_minutes=61)

    def test_chase_protection_pct_bounds(self) -> None:
        """chase_protection_pct must be >= 0 and <= 0.05."""
        # Valid
        config = make_scalp_config(chase_protection_pct=0)
        assert config.chase_protection_pct == 0

        config = make_scalp_config(chase_protection_pct=0.05)
        assert config.chase_protection_pct == 0.05

        # Invalid
        with pytest.raises(ValueError):
            make_scalp_config(chase_protection_pct=-0.01)

        with pytest.raises(ValueError):
            make_scalp_config(chase_protection_pct=0.06)

    def test_breakout_volume_multiplier_bounds(self) -> None:
        """breakout_volume_multiplier must be > 0."""
        # Valid
        config = make_scalp_config(breakout_volume_multiplier=0.1)
        assert config.breakout_volume_multiplier == 0.1

        # Invalid
        with pytest.raises(ValueError):
            make_scalp_config(breakout_volume_multiplier=0)

        with pytest.raises(ValueError):
            make_scalp_config(breakout_volume_multiplier=-1)

    def test_config_with_all_custom_values(self) -> None:
        """Verify config with all custom values."""
        config = make_scalp_config(
            strategy_id="custom_scalp",
            orb_window_minutes=10,
            scalp_target_r=0.5,
            max_hold_seconds=300,
            stop_placement="bottom",
            min_range_atr_ratio=0.3,
            max_range_atr_ratio=500.0,
            chase_protection_pct=0.01,
            breakout_volume_multiplier=2.0,
            volume_threshold_rvol=3.0,
            max_trades_per_day=8,
            max_daily_loss_pct=0.02,
            max_loss_per_trade_pct=0.005,
            max_concurrent_positions=2,
        )

        assert config.strategy_id == "custom_scalp"
        assert config.orb_window_minutes == 10
        assert config.scalp_target_r == 0.5
        assert config.max_hold_seconds == 300
        assert config.stop_placement == "bottom"
        assert config.min_range_atr_ratio == 0.3
        assert config.max_range_atr_ratio == 500.0
        assert config.chase_protection_pct == 0.01
        assert config.breakout_volume_multiplier == 2.0
        assert config.volume_threshold_rvol == 3.0
        assert config.risk_limits.max_trades_per_day == 8


class TestOrbScalpOpeningRangeValidation:
    """Tests for OR ATR validation and rejection cases."""

    @pytest.mark.asyncio
    async def test_or_too_tight_rejected(self) -> None:
        """OR with range too tight relative to ATR is rejected."""
        config = make_scalp_config(min_range_atr_ratio=0.5)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 5.0  # ATR = 5.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 0.5 (high=100.5, low=100.0)
        # range/ATR = 0.5/5.0 = 0.1 < min_range_atr_ratio (0.5)
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=100.5, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "too tight" in state.or_rejection_reason.lower()

    @pytest.mark.asyncio
    async def test_or_too_wide_rejected(self) -> None:
        """OR with range too wide relative to ATR is rejected."""
        config = make_scalp_config(max_range_atr_ratio=2.0)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 1.0  # ATR = 1.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 5.0 (high=105, low=100)
        # range/ATR = 5.0/1.0 = 5.0 > max_range_atr_ratio (2.0)
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=105.0, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "too wide" in state.or_rejection_reason.lower()

    @pytest.mark.asyncio
    async def test_or_no_candles_rejected(self) -> None:
        """OR with no candles is rejected."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send candle directly past OR window without any OR candles
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "no candles" in state.or_rejection_reason.lower()

    @pytest.mark.asyncio
    async def test_or_valid_when_atr_within_bounds(self) -> None:
        """OR is valid when range/ATR is within bounds."""
        config = make_scalp_config(min_range_atr_ratio=0.5, max_range_atr_ratio=2.0)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0  # ATR = 2.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 2.0 (high=101, low=99)
        # range/ATR = 2.0/2.0 = 1.0 (within 0.5-2.0)
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert state.or_valid

    @pytest.mark.asyncio
    async def test_or_accepted_without_atr(self) -> None:
        """OR is accepted when ATR is not available."""
        config = make_scalp_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = None  # No ATR

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert state.or_valid

    @pytest.mark.asyncio
    async def test_multiple_symbols_independent_tracking(self) -> None:
        """Each symbol has independent OR tracking."""
        config = make_scalp_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # Feed AAPL candles
        aapl_candles = make_or_candles("AAPL", num_candles=5, or_high=150.0, or_low=148.0)
        for candle in aapl_candles:
            await strategy.on_candle(candle)

        # Feed MSFT candles (different OR)
        msft_candles = make_or_candles("MSFT", num_candles=5, or_high=350.0, or_low=345.0)
        for candle in msft_candles:
            await strategy.on_candle(candle)

        # Finalize both
        await strategy.on_candle(
            make_candle(symbol="AAPL", timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        )
        await strategy.on_candle(
            make_candle(symbol="MSFT", timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        )

        aapl_state = strategy._get_symbol_state("AAPL")
        msft_state = strategy._get_symbol_state("MSFT")

        assert aapl_state.or_high == 150.0
        assert msft_state.or_high == 350.0
        assert aapl_state.or_low != msft_state.or_low

    @pytest.mark.asyncio
    async def test_candles_after_or_ignored(self) -> None:
        """Candles after OR complete are not added to OR."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up and finalize OR
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        initial_candle_count = len(state.or_candles)

        # Send more candles
        for i in range(5):
            candle = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 40 + i, 0, tzinfo=UTC),
            )
            await strategy.on_candle(candle)

        # OR candle count should not change
        assert len(state.or_candles) == initial_candle_count

    @pytest.mark.asyncio
    async def test_or_avg_volume_calculated(self) -> None:
        """OR average volume is calculated correctly."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Create candles with known volumes
        base_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
        volumes = [100_000, 120_000, 80_000, 110_000, 90_000]
        for i, vol in enumerate(volumes):
            candle = make_candle(
                symbol="AAPL",
                timestamp=base_time + timedelta(minutes=i),
                volume=vol,
            )
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        expected_avg = sum(volumes) / len(volumes)
        assert state.or_avg_volume == expected_avg


class TestOrbScalpBreakoutDetection:
    """Tests for breakout detection logic."""

    async def _setup_valid_or(
        self,
        strategy: OrbScalpStrategy,
        symbol: str = "AAPL",
        or_high: float = 101.0,
        or_low: float = 99.0,
    ) -> None:
        """Helper to set up a valid opening range."""
        strategy.set_watchlist([symbol])

        or_candles = make_or_candles(symbol, num_candles=5, or_high=or_high, or_low=or_low)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol=symbol,
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

    @pytest.mark.asyncio
    async def test_breakout_above_or_high_emits_signal(self) -> None:
        """Candle closing above OR high with volume emits signal."""
        config = make_scalp_config(breakout_volume_multiplier=1.5, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_wick_above_or_high_no_signal(self) -> None:
        """Candle with wick above OR high but close below does not emit signal."""
        config = make_scalp_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        wick = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
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
        config = make_scalp_config(breakout_volume_multiplier=1.5, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=102.0,
            volume=50_000,  # Below 1.5x avg volume
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_below_vwap_no_signal(self) -> None:
        """Breakout below VWAP does not emit signal."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 105.0,  # VWAP is above entry price
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=102.0,  # Above OR high but below VWAP (105)
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_chase_protection_no_signal(self) -> None:
        """Breakout past chase protection threshold does not emit signal."""
        config = make_scalp_config(chase_protection_pct=0.005)  # 0.5%
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Chase protection limit = 101.0 * 1.005 = 101.505
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=102.0,  # Above chase protection limit
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_max_trades_reached_no_signal(self) -> None:
        """No signal after max_trades_per_day reached."""
        config = make_scalp_config(max_trades_per_day=2, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record max trades
        strategy.record_trade_result(100)
        strategy.record_trade_result(100)

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_max_daily_loss_reached_no_signal(self) -> None:
        """No signal after max daily loss reached."""
        config = make_scalp_config(max_daily_loss_pct=0.03, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record 3% loss
        strategy.record_trade_result(-3000)

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_max_concurrent_positions_reached_no_signal(self) -> None:
        """No signal when max concurrent positions reached."""
        config = make_scalp_config(max_concurrent_positions=1, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # Set up AAPL with an active position
        await self._setup_valid_or(strategy, symbol="AAPL", or_high=101.0, or_low=99.0)

        # Trigger AAPL breakout
        aapl_breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal1 = await strategy.on_candle(aapl_breakout)
        assert signal1 is not None  # First position

        # Set up MSFT
        msft_candles = make_or_candles("MSFT", num_candles=5, or_high=201.0, or_low=199.0)
        for candle in msft_candles:
            await strategy.on_candle(candle)
        await strategy.on_candle(
            make_candle(symbol="MSFT", timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        )

        # Try MSFT breakout - should be rejected
        msft_breakout = make_candle(
            symbol="MSFT",
            timestamp=datetime(2026, 2, 15, 14, 51, 0, tzinfo=UTC),
            close=201.5,
            volume=200_000,
        )
        signal2 = await strategy.on_candle(msft_breakout)

        assert signal2 is None  # Max positions reached

    @pytest.mark.asyncio
    async def test_only_one_breakout_per_symbol(self) -> None:
        """Only one breakout signal per symbol."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # First breakout
        breakout1 = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal1 = await strategy.on_candle(breakout1)
        assert signal1 is not None

        # Second breakout attempt
        breakout2 = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 51, 0, tzinfo=UTC),
            close=102.0,
            volume=200_000,
        )
        signal2 = await strategy.on_candle(breakout2)
        assert signal2 is None

    @pytest.mark.asyncio
    async def test_breakout_with_no_vwap_skips_check(self) -> None:
        """Breakout proceeds when VWAP is not available."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": None,  # No VWAP
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        # Should still generate signal without VWAP check
        assert signal is not None


class TestOrbScalpSignalProperties:
    """Additional tests for signal properties."""

    async def _setup_and_breakout(
        self, strategy: OrbScalpStrategy, or_high: float = 101.0, or_low: float = 99.0
    ) -> SignalEvent | None:
        """Helper to set up OR and trigger breakout."""
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles("AAPL", num_candles=5, or_high=or_high, or_low=or_low)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=or_high + 0.5,
            volume=200_000,
        )
        return await strategy.on_candle(breakout)

    @pytest.mark.asyncio
    async def test_position_size_formula(self) -> None:
        """Position size uses allocated_capital * max_loss_per_trade_pct / risk."""
        config = make_scalp_config(max_loss_per_trade_pct=0.01, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        signal = await self._setup_and_breakout(strategy, or_high=101.0, or_low=99.0)

        assert signal is not None
        # Entry: 101.5, Stop: 100 (midpoint), Risk: 1.5
        # Risk dollars: 100K * 1% = 1000
        # Shares: 1000 / 1.5 = 666
        assert signal.share_count == 666

    @pytest.mark.asyncio
    async def test_rationale_contains_orb_scalp(self) -> None:
        """Rationale string contains 'ORB scalp'."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        signal = await self._setup_and_breakout(strategy)

        assert signal is not None
        assert "ORB scalp" in signal.rationale

    @pytest.mark.asyncio
    async def test_signal_entry_price_is_candle_close(self) -> None:
        """Signal entry price equals candle close."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        signal = await self._setup_and_breakout(strategy, or_high=101.0, or_low=99.0)

        assert signal is not None
        assert signal.entry_price == 101.5  # or_high + 0.5

    @pytest.mark.asyncio
    async def test_signal_stop_is_or_midpoint(self) -> None:
        """Signal stop price equals OR midpoint."""
        config = make_scalp_config(chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        # OR: high=102, low=100, midpoint=101
        signal = await self._setup_and_breakout(strategy, or_high=102.0, or_low=100.0)

        assert signal is not None
        assert signal.stop_price == 101.0  # Midpoint

    @pytest.mark.asyncio
    async def test_different_scalp_target_r_values(self) -> None:
        """Test different scalp_target_r values."""
        for target_r in [0.2, 0.4, 0.5]:
            config = make_scalp_config(scalp_target_r=target_r, chase_protection_pct=0.02)
            mock_data_service = AsyncMock()
            mock_data_service.get_indicator.side_effect = lambda s, i: {
                "atr_14": 2.0,
                "vwap": 100.0,
            }.get(i)

            strategy = OrbScalpStrategy(config, data_service=mock_data_service)
            strategy.allocated_capital = 100_000
            strategy.set_watchlist(["AAPL"])

            # OR: high=101, low=99, midpoint=100
            or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
            for candle in or_candles:
                await strategy.on_candle(candle)

            post_or = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
            )
            await strategy.on_candle(post_or)

            # Entry: 101.5, Stop: 100, Risk: 1.5
            breakout = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
                close=101.5,
                volume=200_000,
            )
            signal = await strategy.on_candle(breakout)

            assert signal is not None
            expected_target = 101.5 + 1.5 * target_r
            assert signal.target_prices[0] == pytest.approx(expected_target)

    @pytest.mark.asyncio
    async def test_different_max_hold_seconds_values(self) -> None:
        """Test different max_hold_seconds values."""
        for hold_seconds in [30, 60, 300]:
            config = make_scalp_config(max_hold_seconds=hold_seconds, chase_protection_pct=0.02)
            mock_data_service = AsyncMock()
            mock_data_service.get_indicator.side_effect = lambda s, i: {
                "atr_14": 2.0,
                "vwap": 100.0,
            }.get(i)

            strategy = OrbScalpStrategy(config, data_service=mock_data_service)
            strategy.allocated_capital = 100_000
            strategy.set_watchlist(["AAPL"])

            or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
            for candle in or_candles:
                await strategy.on_candle(candle)

            post_or = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
            )
            await strategy.on_candle(post_or)

            breakout = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
                close=101.5,
                volume=200_000,
            )
            signal = await strategy.on_candle(breakout)

            assert signal is not None
            assert signal.time_stop_seconds == hold_seconds


class TestOrbScalpStateManagement:
    """Tests for state management methods."""

    def test_reset_daily_state_clears_symbol_state(self) -> None:
        """reset_daily_state clears all symbol state."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        # Add some state
        state = strategy._get_symbol_state("AAPL")
        state.or_complete = True
        state.or_high = 101.0

        strategy.reset_daily_state()

        # State should be cleared
        assert "AAPL" not in strategy._symbol_state

    def test_mark_position_closed_updates_state(self) -> None:
        """mark_position_closed updates position_active to False."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        state = strategy._get_symbol_state("AAPL")
        state.position_active = True

        strategy.mark_position_closed("AAPL")

        assert state.position_active is False

    def test_mark_position_closed_nonexistent_symbol(self) -> None:
        """mark_position_closed handles nonexistent symbol gracefully."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        # Should not raise
        strategy.mark_position_closed("NONEXISTENT")

    def test_set_watchlist(self) -> None:
        """set_watchlist sets the watchlist correctly."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        strategy.set_watchlist(["AAPL", "MSFT", "GOOG"])

        assert strategy._watchlist == ["AAPL", "MSFT", "GOOG"]

    def test_record_trade_result_updates_daily_pnl(self) -> None:
        """record_trade_result updates daily P&L and trade count."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        strategy.record_trade_result(100)
        assert strategy._daily_pnl == 100
        assert strategy._trade_count_today == 1

        strategy.record_trade_result(-50)
        assert strategy._daily_pnl == 50
        assert strategy._trade_count_today == 2

    def test_is_active_property(self) -> None:
        """is_active property can be set and retrieved."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        # Default is False
        assert strategy.is_active is False

        # Can be set to True
        strategy.is_active = True
        assert strategy.is_active is True

    def test_allocated_capital_property(self) -> None:
        """allocated_capital property works correctly."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)

        strategy.allocated_capital = 50_000
        assert strategy.allocated_capital == 50_000

    @pytest.mark.asyncio
    async def test_multiple_symbols_can_fire_independently(self) -> None:
        """Multiple symbols can each generate one breakout."""
        config = make_scalp_config(max_concurrent_positions=3, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # Set up AAPL
        aapl_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in aapl_candles:
            await strategy.on_candle(candle)
        await strategy.on_candle(
            make_candle(symbol="AAPL", timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        )

        # Set up MSFT
        msft_candles = make_or_candles("MSFT", num_candles=5, or_high=201.0, or_low=199.0)
        for candle in msft_candles:
            await strategy.on_candle(candle)
        await strategy.on_candle(
            make_candle(symbol="MSFT", timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        )

        # Both should trigger
        aapl_signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
                close=101.5,
                volume=200_000,
            )
        )
        msft_signal = await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                timestamp=datetime(2026, 2, 15, 14, 51, 0, tzinfo=UTC),
                close=201.5,
                volume=200_000,
            )
        )

        assert aapl_signal is not None
        assert msft_signal is not None
        assert aapl_signal.symbol == "AAPL"
        assert msft_signal.symbol == "MSFT"


class TestOrbScalpExitRulesExtended:
    """Extended tests for exit rules."""

    def test_exit_rules_time_stop_seconds_converted(self) -> None:
        """Time stop is converted from seconds to minutes."""
        config = make_scalp_config(max_hold_seconds=180)  # 3 minutes
        strategy = OrbScalpStrategy(config)

        rules = strategy.get_exit_rules()

        assert rules.time_stop_minutes == 3  # 180 // 60

    def test_exit_rules_time_stop_truncates(self) -> None:
        """Time stop truncates partial minutes."""
        config = make_scalp_config(max_hold_seconds=90)  # 1.5 minutes
        strategy = OrbScalpStrategy(config)

        rules = strategy.get_exit_rules()

        assert rules.time_stop_minutes == 1  # 90 // 60

    def test_scanner_criteria_values(self) -> None:
        """Scanner criteria returns expected values."""
        config = make_scalp_config(volume_threshold_rvol=2.5)
        strategy = OrbScalpStrategy(config)

        criteria = strategy.get_scanner_criteria()

        assert criteria.min_price == 10.0
        assert criteria.max_price == 200.0
        assert criteria.min_volume_avg_daily == 1_000_000
        assert criteria.min_relative_volume == 2.5
        assert criteria.min_gap_pct == 0.02
        assert criteria.max_results == 20


class TestOrbScalpEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_very_short_max_hold_seconds(self) -> None:
        """Strategy works with minimum max_hold_seconds (10s)."""
        config = make_scalp_config(max_hold_seconds=10, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbScalpStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 50, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.time_stop_seconds == 10

    def test_zero_allocated_capital_returns_zero_shares(self) -> None:
        """Position size returns 0 when no capital allocated."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        # Don't set allocated_capital

        shares = strategy.calculate_position_size(102.0, 100.0)
        assert shares == 0

    def test_stop_price_at_entry_returns_zero_shares(self) -> None:
        """Position size returns 0 when stop >= entry (invalid for longs)."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000

        shares = strategy.calculate_position_size(100.0, 100.0)
        assert shares == 0

        shares = strategy.calculate_position_size(100.0, 101.0)
        assert shares == 0

    @pytest.mark.asyncio
    async def test_symbol_not_in_watchlist_ignored(self) -> None:
        """Candles for symbols not in watchlist are ignored."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["MSFT"])  # Only MSFT in watchlist

        # Send AAPL candles
        or_candles = make_or_candles("AAPL", num_candles=5, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # AAPL should not have any state
        assert "AAPL" not in strategy._symbol_state

    @pytest.mark.asyncio
    async def test_during_or_formation_no_signal(self) -> None:
        """No signal during OR formation period."""
        config = make_scalp_config()
        strategy = OrbScalpStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Candle during OR window (9:34) - even if it looks like breakout
        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 34, 0, tzinfo=UTC),
            close=105.0,  # Would be above any OR high
            volume=200_000,
        )
        signal = await strategy.on_candle(candle)

        # Should not emit signal during OR formation
        assert signal is None

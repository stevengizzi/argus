"""Tests for the tick synthesizer module."""

from datetime import UTC, datetime, timedelta

import pytest

from argus.backtest.tick_synthesizer import SyntheticTick, synthesize_ticks


class TestSynthesizeTicks:
    """Tests for synthesize_ticks function."""

    def test_bullish_bar_order(self) -> None:
        """Bullish bar (close >= open) produces O, L, H, C order."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        ticks = synthesize_ticks(
            symbol="AAPL",
            timestamp=ts,
            open_=100.0,
            high=105.0,
            low=98.0,
            close=104.0,
            volume=1000,
        )

        assert len(ticks) == 4
        assert [t.price for t in ticks] == [100.0, 98.0, 105.0, 104.0]
        assert all(t.symbol == "AAPL" for t in ticks)

    def test_bearish_bar_order(self) -> None:
        """Bearish bar (close < open) produces O, H, L, C order."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        ticks = synthesize_ticks(
            symbol="AAPL",
            timestamp=ts,
            open_=100.0,
            high=102.0,
            low=95.0,
            close=96.0,
            volume=1000,
        )

        assert len(ticks) == 4
        assert [t.price for t in ticks] == [100.0, 102.0, 95.0, 96.0]

    def test_doji_bar_treated_as_bullish(self) -> None:
        """Doji bar (close == open) is treated as bullish (O, L, H, C)."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        ticks = synthesize_ticks(
            symbol="AAPL",
            timestamp=ts,
            open_=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=400,
        )

        assert len(ticks) == 4
        # Doji: close >= open, so bullish path
        assert [t.price for t in ticks] == [100.0, 99.0, 101.0, 100.0]

    def test_volume_distributed_evenly(self) -> None:
        """Volume is split evenly among 4 ticks."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        ticks = synthesize_ticks(
            symbol="AAPL",
            timestamp=ts,
            open_=100.0,
            high=105.0,
            low=98.0,
            close=104.0,
            volume=1000,
        )

        assert all(t.volume == 250 for t in ticks)

    def test_volume_minimum_of_one(self) -> None:
        """Volume per tick is at least 1 even for low volume bars."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        ticks = synthesize_ticks(
            symbol="AAPL",
            timestamp=ts,
            open_=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=3,  # 3 // 4 = 0, but we ensure at least 1
        )

        assert all(t.volume >= 1 for t in ticks)

    def test_timestamps_spaced_15_seconds(self) -> None:
        """Tick timestamps are spaced 15 seconds apart."""
        base_ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        ticks = synthesize_ticks(
            symbol="AAPL",
            timestamp=base_ts,
            open_=100.0,
            high=105.0,
            low=98.0,
            close=104.0,
            volume=1000,
        )

        for i, tick in enumerate(ticks):
            expected = base_ts + timedelta(seconds=i * 15)
            assert tick.timestamp == expected

    def test_synthetic_tick_is_frozen(self) -> None:
        """SyntheticTick is immutable (frozen dataclass)."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        tick = SyntheticTick(symbol="AAPL", price=100.0, volume=100, timestamp=ts)

        with pytest.raises(AttributeError):
            tick.price = 101.0  # type: ignore[misc]

"""Tests for event dataclass definitions."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from argus.core.events import (
    CandleEvent,
    CatalystEvent,
    Event,
    ExitReason,
    PositionClosedEvent,
    QualitySignalEvent,
    Side,
    SignalEvent,
    WatchlistEvent,
    WatchlistItem,
)


class TestEventDataclasses:
    """Verify event dataclass behavior."""

    def test_base_event_has_defaults(self) -> None:
        """Base Event has sequence=0 and auto-generated timestamp."""
        event = Event()
        assert event.sequence == 0
        assert event.timestamp is not None

    def test_candle_event_fields(self) -> None:
        """CandleEvent stores all OHLCV fields."""
        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=150.0,
            high=151.0,
            low=149.5,
            close=150.5,
            volume=10000,
        )
        assert candle.symbol == "AAPL"
        assert candle.volume == 10000

    def test_signal_event_with_targets(self) -> None:
        """SignalEvent stores target prices as a tuple."""
        signal = SignalEvent(
            strategy_id="strat_orb",
            symbol="TSLA",
            side=Side.LONG,
            entry_price=200.0,
            stop_price=198.0,
            target_prices=(202.0, 204.0),
            share_count=100,
            rationale="ORB breakout above range high",
        )
        assert len(signal.target_prices) == 2
        assert signal.side == Side.LONG

    def test_events_are_frozen(self) -> None:
        """Events are immutable (frozen dataclasses)."""
        candle = CandleEvent(symbol="AAPL")
        with pytest.raises(AttributeError):
            candle.symbol = "MSFT"  # type: ignore[misc]

    def test_watchlist_event_with_items(self) -> None:
        """WatchlistEvent contains WatchlistItem tuples."""
        items = (
            WatchlistItem(symbol="AAPL", gap_pct=3.5, premarket_volume=500000),
            WatchlistItem(symbol="TSLA", gap_pct=5.2, premarket_volume=800000),
        )
        event = WatchlistEvent(date="2026-02-15", symbols=items)
        assert len(event.symbols) == 2
        assert event.symbols[0].symbol == "AAPL"

    def test_exit_reason_enum(self) -> None:
        """ExitReason enum values are strings."""
        event = PositionClosedEvent(
            position_id="test",
            exit_reason=ExitReason.STOP_LOSS,
        )
        assert event.exit_reason.value == "stop_loss"


class TestSignalEventEnrichment:
    """Tests for Sprint 24 SignalEvent enrichment fields."""

    def test_signal_event_new_fields_defaults(self) -> None:
        """SignalEvent() has pattern_strength=50, signal_context={}, quality_score=0, grade=''."""
        signal = SignalEvent()
        assert signal.pattern_strength == 50.0
        assert signal.signal_context == {}
        assert signal.quality_score == 0.0
        assert signal.quality_grade == ""

    def test_signal_event_backward_compatible(self) -> None:
        """Existing SignalEvent constructors work without new fields."""
        signal = SignalEvent(
            strategy_id="x",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=95.0,
            target_prices=(105.0,),
            share_count=50,
            rationale="test",
        )
        assert signal.strategy_id == "x"
        assert signal.symbol == "AAPL"
        assert signal.share_count == 50
        # New fields at defaults
        assert signal.pattern_strength == 50.0
        assert signal.signal_context == {}

    def test_signal_event_new_fields_settable(self) -> None:
        """New fields on SignalEvent can be set explicitly."""
        context = {"volume_ratio": 2.5, "atr_ratio": 0.7}
        signal = SignalEvent(
            strategy_id="orb",
            symbol="TSLA",
            side=Side.LONG,
            entry_price=200.0,
            stop_price=195.0,
            target_prices=(205.0,),
            share_count=0,
            rationale="test",
            pattern_strength=78.5,
            signal_context=context,
            quality_score=82.0,
            quality_grade="B+",
        )
        assert signal.pattern_strength == 78.5
        assert signal.signal_context["volume_ratio"] == 2.5
        assert signal.quality_score == 82.0
        assert signal.quality_grade == "B+"


class TestQualitySignalEvent:
    """Tests for QualitySignalEvent."""

    def test_quality_signal_event_creation(self) -> None:
        """QualitySignalEvent fields populate correctly."""
        event = QualitySignalEvent(
            symbol="NVDA",
            strategy_id="strat_orb_breakout",
            score=85.5,
            grade="A-",
            risk_tier="tier_1",
            components={"volume": 90.0, "atr": 78.0},
            rationale="Strong breakout with high volume confirmation",
        )
        assert event.symbol == "NVDA"
        assert event.strategy_id == "strat_orb_breakout"
        assert event.score == 85.5
        assert event.grade == "A-"
        assert event.risk_tier == "tier_1"
        assert event.components["volume"] == 90.0
        assert "volume" in event.rationale or event.rationale != ""

    def test_quality_signal_event_defaults(self) -> None:
        """QualitySignalEvent() has safe empty defaults."""
        event = QualitySignalEvent()
        assert event.symbol == ""
        assert event.score == 0.0
        assert event.grade == ""
        assert event.components == {}

    def test_quality_signal_event_is_frozen(self) -> None:
        """QualitySignalEvent is immutable."""
        event = QualitySignalEvent(symbol="AAPL")
        with pytest.raises(AttributeError):
            event.symbol = "TSLA"  # type: ignore[misc]


class TestCatalystEvent:
    """Tests for CatalystEvent timezone handling."""

    def test_catalyst_event_defaults_et(self) -> None:
        """CatalystEvent() with no args produces ET-aware datetimes."""
        event = CatalystEvent()

        # Both timestamps should be timezone-aware
        assert event.published_at.tzinfo is not None
        assert event.classified_at.tzinfo is not None

        # Both should be in America/New_York timezone
        et_zone = ZoneInfo("America/New_York")
        assert str(event.published_at.tzinfo) == str(et_zone)
        assert str(event.classified_at.tzinfo) == str(et_zone)

    def test_catalyst_event_explicit_override(self) -> None:
        """Explicit timestamp still works (no regression)."""
        utc_time = datetime.now(UTC)
        event = CatalystEvent(
            symbol="AAPL",
            published_at=utc_time,
            classified_at=utc_time,
        )

        # Should use the explicitly provided UTC time
        assert event.published_at == utc_time
        assert event.classified_at == utc_time
        assert event.published_at.tzinfo == UTC

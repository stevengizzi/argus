"""Tests for ORB family strategy telemetry instrumentation (Sprint 24.5 S2)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from argus.core.config import (
    OperatingWindow,
    OrbBreakoutConfig,
    OrbScalpConfig,
    StrategyRiskLimits,
)
from argus.core.events import CandleEvent
from argus.strategies.orb_base import OrbBaseStrategy
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult


def _risk_limits(**overrides: object) -> StrategyRiskLimits:
    defaults = {
        "max_trades_per_day": 6,
        "max_daily_loss_pct": 0.03,
        "max_loss_per_trade_pct": 0.01,
        "max_concurrent_positions": 2,
    }
    defaults.update(overrides)
    return StrategyRiskLimits(**defaults)


def _breakout_config(**overrides: object) -> OrbBreakoutConfig:
    defaults = {
        "strategy_id": "strat_orb_breakout",
        "name": "ORB Breakout",
        "orb_window_minutes": 5,
        "volume_threshold_rvol": 2.0,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "time_stop_minutes": 30,
        "min_range_atr_ratio": 0.5,
        "max_range_atr_ratio": 2.0,
        "chase_protection_pct": 0.005,
        "breakout_volume_multiplier": 1.5,
        "risk_limits": _risk_limits(),
        "operating_window": OperatingWindow(earliest_entry="09:35", latest_entry="11:30"),
    }
    defaults.update(overrides)
    return OrbBreakoutConfig(**defaults)


def _scalp_config(**overrides: object) -> OrbScalpConfig:
    defaults = {
        "strategy_id": "strat_orb_scalp",
        "name": "ORB Scalp",
        "orb_window_minutes": 5,
        "scalp_target_r": 0.3,
        "max_hold_seconds": 120,
        "stop_placement": "midpoint",
        "min_range_atr_ratio": 0.5,
        "max_range_atr_ratio": 999.0,
        "chase_protection_pct": 0.005,
        "breakout_volume_multiplier": 1.5,
        "volume_threshold_rvol": 2.0,
        "risk_limits": _risk_limits(max_concurrent_positions=3, max_trades_per_day=12),
        "operating_window": OperatingWindow(earliest_entry="09:35", latest_entry="11:30"),
    }
    defaults.update(overrides)
    return OrbScalpConfig(**defaults)


def _candle(
    symbol: str = "AAPL",
    timestamp: datetime | None = None,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 100_000,
) -> CandleEvent:
    if timestamp is None:
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


def _or_candles(
    symbol: str = "AAPL",
    count: int = 5,
    or_high: float = 101.0,
    or_low: float = 99.0,
) -> list[CandleEvent]:
    """Generate candles spanning the OR window (9:30–9:34 ET = 14:30–14:34 UTC)."""
    base = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
    candles = []
    for i in range(count):
        h = or_high if i == 2 else or_high - 0.3
        lo = or_low if i == 3 else or_low + 0.2
        candles.append(
            _candle(
                symbol=symbol,
                timestamp=base + timedelta(minutes=i),
                open_price=(or_high + or_low) / 2,
                high=h,
                low=lo,
                close=(or_high + or_low) / 2,
                volume=100_000 + i * 1000,
            )
        )
    return candles


def _mock_data_service(atr: float = 1.0, vwap: float = 99.0) -> AsyncMock:
    ds = AsyncMock()

    async def _get_indicator(symbol: str, indicator: str) -> float | None:
        if indicator == "atr_14":
            return atr
        if indicator == "vwap":
            return vwap
        return None

    ds.get_indicator = AsyncMock(side_effect=_get_indicator)
    return ds


def _events_of_type(
    strategy: OrbBaseStrategy,
    event_type: EvaluationEventType,
) -> list[object]:
    return [e for e in strategy.eval_buffer.snapshot() if e.event_type == event_type]


@pytest.fixture(autouse=True)
def _clear_orb_family_state() -> None:
    """Ensure ORB family triggered symbols are empty between tests."""
    OrbBaseStrategy._orb_family_triggered_symbols.clear()


# ---------------------------------------------------------------------------
# Test 1: OR accumulation emits event
# ---------------------------------------------------------------------------


class TestOrbOnCandleOrAccumulationEmitsEvent:

    @pytest.mark.asyncio
    async def test_orb_on_candle_or_accumulation_emits_event(self) -> None:
        strategy = OrbBreakoutStrategy(_breakout_config())
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        candle = _candle(
            timestamp=datetime(2026, 2, 15, 14, 31, 0, tzinfo=UTC),
        )
        await strategy.on_candle(candle)

        events = _events_of_type(strategy, EvaluationEventType.OPENING_RANGE_UPDATE)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.INFO
        assert "OR candle accumulated" in events[0].reason
        assert events[0].metadata["candle_count"] == 1


# ---------------------------------------------------------------------------
# Test 2: OR finalization emits PASS or FAIL
# ---------------------------------------------------------------------------


class TestOrbOnCandleOrFinalizationEmitsEvent:

    @pytest.mark.asyncio
    async def test_orb_on_candle_or_finalization_pass(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # First candle after OR window triggers finalization
        post_or = _candle(timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        events = _events_of_type(strategy, EvaluationEventType.OPENING_RANGE_UPDATE)
        finalization = [
            e for e in events
            if e.result in (EvaluationResult.PASS, EvaluationResult.FAIL)
        ]
        assert len(finalization) == 1
        assert finalization[0].result == EvaluationResult.PASS
        assert "Opening range established" in finalization[0].reason
        assert finalization[0].metadata["or_valid"] is True

    @pytest.mark.asyncio
    async def test_orb_on_candle_or_finalization_fail(self) -> None:
        # ATR=0.5 → range/ATR = 2.0/0.5 = 4.0, exceeds max_range_atr_ratio=2.0
        ds = _mock_data_service(atr=0.5, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        post_or = _candle(timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        events = _events_of_type(strategy, EvaluationEventType.OPENING_RANGE_UPDATE)
        finalization = [e for e in events if e.result == EvaluationResult.FAIL]
        assert len(finalization) == 1
        assert "Opening range invalid" in finalization[0].reason
        assert finalization[0].metadata["or_valid"] is False


# ---------------------------------------------------------------------------
# Test 3: DEC-261 exclusion emits CONDITION_CHECK FAIL
# ---------------------------------------------------------------------------


class TestOrbOnCandleExclusionEmitsEvent:

    @pytest.mark.asyncio
    async def test_orb_on_candle_exclusion_emits_event(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Pre-populate exclusion set
        OrbBaseStrategy._orb_family_triggered_symbols.add("AAPL")

        # Feed OR candles then post-OR candle
        for c in _or_candles():
            await strategy.on_candle(c)
        post_or = _candle(timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        events = _events_of_type(strategy, EvaluationEventType.CONDITION_CHECK)
        exclusion = [e for e in events if "DEC-261" in e.reason]
        assert len(exclusion) == 1
        assert exclusion[0].result == EvaluationResult.FAIL


# ---------------------------------------------------------------------------
# Test 4: Time window check emits FAIL
# ---------------------------------------------------------------------------


class TestOrbOnCandleTimeWindowFailEmitsEvent:

    @pytest.mark.asyncio
    async def test_orb_on_candle_before_earliest_entry(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        # earliest_entry = 09:50, so 09:35 ET candle should fail
        config = _breakout_config(
            operating_window=OperatingWindow(earliest_entry="09:50", latest_entry="11:30"),
        )
        strategy = OrbBreakoutStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # 09:35 ET = 14:35 UTC — before earliest 09:50
        post_or = _candle(timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        events = _events_of_type(strategy, EvaluationEventType.TIME_WINDOW_CHECK)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.FAIL
        assert "Before earliest entry time" in events[0].reason

    @pytest.mark.asyncio
    async def test_orb_on_candle_after_latest_entry(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        config = _breakout_config(
            operating_window=OperatingWindow(earliest_entry="09:35", latest_entry="10:00"),
        )
        strategy = OrbBreakoutStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # 10:01 ET = 15:01 UTC — after latest 10:00
        post_or = _candle(timestamp=datetime(2026, 2, 15, 15, 1, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        events = _events_of_type(strategy, EvaluationEventType.TIME_WINDOW_CHECK)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.FAIL
        assert "After latest entry time" in events[0].reason


# ---------------------------------------------------------------------------
# Test 5: Breakout conditions emits ENTRY_EVALUATION
# ---------------------------------------------------------------------------


class TestOrbOnCandleBreakoutEmitsEntryEvaluation:

    @pytest.mark.asyncio
    async def test_orb_on_candle_breakout_emits_entry_evaluation(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # Post-OR candle that does NOT break out (close <= OR high)
        no_breakout = _candle(
            timestamp=datetime(2026, 2, 15, 14, 36, 0, tzinfo=UTC),
            close=100.0,
            high=100.5,
            low=99.5,
            volume=200_000,
        )
        await strategy.on_candle(no_breakout)

        events = _events_of_type(strategy, EvaluationEventType.ENTRY_EVALUATION)
        assert len(events) >= 1
        fail_events = [e for e in events if e.result == EvaluationResult.FAIL]
        assert len(fail_events) >= 1
        assert "close" in fail_events[0].metadata


# ---------------------------------------------------------------------------
# Test 6: Full signal emits SIGNAL_GENERATED
# ---------------------------------------------------------------------------


class TestOrbOnCandleSignalGeneratedEmitsEvent:

    @pytest.mark.asyncio
    async def test_orb_on_candle_signal_generated_emits_event(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # Breakout candle: close above OR high, high volume, above VWAP
        breakout = _candle(
            timestamp=datetime(2026, 2, 15, 14, 36, 0, tzinfo=UTC),
            close=101.3,
            high=101.5,
            low=100.8,
            open_price=100.9,
            volume=500_000,
        )
        result = await strategy.on_candle(breakout)
        assert result is not None  # Signal generated

        events = _events_of_type(strategy, EvaluationEventType.SIGNAL_GENERATED)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.PASS
        assert events[0].metadata["direction"] == "long"
        assert "entry" in events[0].metadata
        assert "stop" in events[0].metadata


# ---------------------------------------------------------------------------
# Test 7: ORB Breakout pattern strength emits QUALITY_SCORED
# ---------------------------------------------------------------------------


class TestOrbBreakoutPatternStrengthEmitsQualityScored:

    @pytest.mark.asyncio
    async def test_orb_breakout_pattern_strength_emits_quality_scored(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        breakout = _candle(
            timestamp=datetime(2026, 2, 15, 14, 36, 0, tzinfo=UTC),
            close=101.3,
            high=101.5,
            low=100.8,
            open_price=100.9,
            volume=500_000,
        )
        result = await strategy.on_candle(breakout)
        assert result is not None

        events = _events_of_type(strategy, EvaluationEventType.QUALITY_SCORED)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.INFO
        assert "ORB Breakout pattern strength" in events[0].reason
        assert "volume_credit" in events[0].metadata
        assert "atr_credit" in events[0].metadata


# ---------------------------------------------------------------------------
# Test 8: ORB Scalp pattern strength emits QUALITY_SCORED
# ---------------------------------------------------------------------------


class TestOrbScalpPatternStrengthEmitsQualityScored:

    @pytest.mark.asyncio
    async def test_orb_scalp_pattern_strength_emits_quality_scored(self) -> None:
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbScalpStrategy(_scalp_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        breakout = _candle(
            timestamp=datetime(2026, 2, 15, 14, 36, 0, tzinfo=UTC),
            close=101.3,
            high=101.5,
            low=100.8,
            open_price=100.9,
            volume=500_000,
        )
        result = await strategy.on_candle(breakout)
        assert result is not None

        events = _events_of_type(strategy, EvaluationEventType.QUALITY_SCORED)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.INFO
        assert "ORB Scalp pattern strength" in events[0].reason
        assert "volume_credit" in events[0].metadata
        assert "chase_credit" in events[0].metadata


# ---------------------------------------------------------------------------
# Test 9: Entry eval metadata — conditions_passed and conditions_total present
# ---------------------------------------------------------------------------


class TestEntryEvalMetadataHasConditionsPassed:

    @pytest.mark.asyncio
    async def test_entry_eval_metadata_has_conditions_passed(self) -> None:
        """ENTRY_EVALUATION FAIL event includes conditions_passed and conditions_total keys."""
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # Finalize the OR (first post-OR candle)
        post_or = _candle(timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        # Candle that fails condition 1: close <= OR high (101.0)
        fails_close = _candle(
            timestamp=datetime(2026, 2, 15, 14, 36, 0, tzinfo=UTC),
            close=100.5,
            high=100.8,
            low=99.5,
            volume=200_000,
        )
        await strategy.on_candle(fails_close)

        entry_events = _events_of_type(strategy, EvaluationEventType.ENTRY_EVALUATION)
        fail_events = [e for e in entry_events if e.result == EvaluationResult.FAIL]
        assert len(fail_events) >= 1
        metadata = fail_events[0].metadata
        assert "conditions_passed" in metadata
        assert "conditions_total" in metadata


# ---------------------------------------------------------------------------
# Test 10: Entry eval all-pass — conditions_passed == conditions_total == 4
# ---------------------------------------------------------------------------


class TestEntryEvalAllPassConditionsCount:

    @pytest.mark.asyncio
    async def test_entry_eval_all_pass_conditions_count(self) -> None:
        """ENTRY_EVALUATION PASS event has conditions_passed == conditions_total == 4."""
        ds = _mock_data_service(atr=2.0, vwap=99.0)
        strategy = OrbBreakoutStrategy(_breakout_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        for c in _or_candles():
            await strategy.on_candle(c)

        # Finalize the OR
        post_or = _candle(timestamp=datetime(2026, 2, 15, 14, 35, 0, tzinfo=UTC))
        await strategy.on_candle(post_or)

        # Breakout candle: all 4 conditions pass
        # 1. close > OR high (101.0): close=101.3 ✓
        # 2. volume > or_avg_volume * 1.5 (~150k): volume=500k ✓
        # 3. close > vwap (99.0): 101.3 > 99.0 ✓
        # 4. close <= or_high * 1.005 (101.505): 101.3 <= 101.505 ✓
        all_pass = _candle(
            timestamp=datetime(2026, 2, 15, 14, 36, 0, tzinfo=UTC),
            close=101.3,
            high=101.5,
            low=100.8,
            open_price=100.9,
            volume=500_000,
        )
        await strategy.on_candle(all_pass)

        entry_events = _events_of_type(strategy, EvaluationEventType.ENTRY_EVALUATION)
        pass_events = [e for e in entry_events if e.result == EvaluationResult.PASS]
        assert len(pass_events) == 1
        assert pass_events[0].metadata["conditions_passed"] == 4
        assert pass_events[0].metadata["conditions_total"] == 4

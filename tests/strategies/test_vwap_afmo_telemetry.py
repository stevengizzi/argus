"""Tests for VWAP Reclaim and Afternoon Momentum telemetry instrumentation (Sprint 24.5 S3)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from argus.core.config import (
    AfternoonMomentumConfig,
    OperatingWindow,
    StrategyRiskLimits,
    VwapReclaimConfig,
)
from argus.core.events import CandleEvent
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult
from argus.strategies.vwap_reclaim import VwapReclaimStrategy


def _risk_limits(**overrides: object) -> StrategyRiskLimits:
    defaults = {
        "max_trades_per_day": 6,
        "max_daily_loss_pct": 0.03,
        "max_loss_per_trade_pct": 0.01,
        "max_concurrent_positions": 2,
    }
    defaults.update(overrides)
    return StrategyRiskLimits(**defaults)


def _vwap_config(**overrides: object) -> VwapReclaimConfig:
    defaults = {
        "strategy_id": "strat_vwap_reclaim",
        "name": "VWAP Reclaim",
        "min_pullback_pct": 0.002,
        "max_pullback_pct": 0.02,
        "min_pullback_bars": 2,
        "volume_confirmation_multiplier": 1.2,
        "max_chase_above_vwap_pct": 0.003,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "time_stop_minutes": 30,
        "stop_buffer_pct": 0.001,
        "risk_limits": _risk_limits(),
        "operating_window": OperatingWindow(earliest_entry="10:00", latest_entry="12:00"),
    }
    defaults.update(overrides)
    return VwapReclaimConfig(**defaults)


def _afmo_config(**overrides: object) -> AfternoonMomentumConfig:
    defaults = {
        "strategy_id": "strat_afmo",
        "name": "Afternoon Momentum",
        "consolidation_start_time": "12:00",
        "consolidation_atr_ratio": 0.75,
        "max_consolidation_atr_ratio": 2.0,
        "min_consolidation_bars": 5,
        "volume_multiplier": 1.2,
        "max_chase_pct": 0.005,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "max_hold_minutes": 60,
        "stop_buffer_pct": 0.001,
        "force_close_time": "15:45",
        "risk_limits": _risk_limits(),
        "operating_window": OperatingWindow(earliest_entry="14:00", latest_entry="15:30"),
    }
    defaults.update(overrides)
    return AfternoonMomentumConfig(**defaults)


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
        timestamp = datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC)
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


def _mock_data_service(atr: float = 1.0, vwap: float = 100.0) -> AsyncMock:
    ds = AsyncMock()

    async def _get_indicator(symbol: str, indicator: str) -> float | None:
        if indicator == "atr_14":
            return atr
        if indicator == "vwap":
            return vwap
        return None

    ds.get_indicator = AsyncMock(side_effect=_get_indicator)
    return ds


def _events_of_type(strategy: object, event_type: EvaluationEventType) -> list[object]:
    return [e for e in strategy.eval_buffer.snapshot() if e.event_type == event_type]


# ---------------------------------------------------------------------------
# Test 1: VWAP state transition MONITORING → APPROACHING emits STATE_TRANSITION
# ---------------------------------------------------------------------------


class TestVwapStateTransitionEmitsEvent:

    @pytest.mark.asyncio
    async def test_vwap_state_transition_emits_event(self) -> None:
        """WATCHING → ABOVE_VWAP emits STATE_TRANSITION."""
        ds = _mock_data_service(vwap=100.0)
        strategy = VwapReclaimStrategy(_vwap_config(), data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Close above VWAP → WATCHING → ABOVE_VWAP
        candle = _candle(
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
            close=101.0,
        )
        await strategy.on_candle(candle)

        events = _events_of_type(strategy, EvaluationEventType.STATE_TRANSITION)
        transitions = [e for e in events if "State transition:" in e.reason]
        assert len(transitions) >= 1
        first = transitions[0]
        assert first.result == EvaluationResult.INFO
        assert "watching" in first.metadata["from_state"]
        assert "above_vwap" in first.metadata["to_state"]
        assert "trigger" in first.metadata


# ---------------------------------------------------------------------------
# Test 2: VWAP exhaustion emits STATE_TRANSITION
# ---------------------------------------------------------------------------


class TestVwapExhaustionEmitsEvent:

    @pytest.mark.asyncio
    async def test_vwap_exhaustion_emits_event(self) -> None:
        """BELOW_VWAP → EXHAUSTED emits STATE_TRANSITION with exhaustion trigger."""
        ds = _mock_data_service(vwap=100.0)
        config = _vwap_config(max_pullback_pct=0.01)
        strategy = VwapReclaimStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Step 1: WATCHING → ABOVE_VWAP (close > vwap)
        await strategy.on_candle(
            _candle(timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC), close=101.0)
        )
        # Step 2: ABOVE_VWAP → BELOW_VWAP (close <= vwap)
        await strategy.on_candle(
            _candle(timestamp=datetime(2026, 2, 15, 15, 1, 0, tzinfo=UTC), close=99.5, low=97.0)
        )
        # Step 3: BELOW_VWAP → EXHAUSTED (pullback too deep: (100-97)/100 = 3% > 1%)
        await strategy.on_candle(
            _candle(timestamp=datetime(2026, 2, 15, 15, 2, 0, tzinfo=UTC), close=98.0, low=96.0)
        )

        events = _events_of_type(strategy, EvaluationEventType.STATE_TRANSITION)
        exhaustion = [e for e in events if "exhausted" in e.reason.lower()]
        assert len(exhaustion) >= 1
        assert exhaustion[0].metadata["to_state"] == "exhausted"
        assert "exhaustion" in exhaustion[0].metadata["trigger"]


# ---------------------------------------------------------------------------
# Test 3: VWAP entry conditions emit CONDITION_CHECK events
# ---------------------------------------------------------------------------


class TestVwapEntryConditionsEmitEvents:

    @pytest.mark.asyncio
    async def test_vwap_entry_conditions_emit_events(self) -> None:
        """Reclaim attempt emits CONDITION_CHECK for each condition evaluated."""
        ds = _mock_data_service(vwap=100.0)
        config = _vwap_config(min_pullback_bars=1, min_pullback_pct=0.001)
        strategy = VwapReclaimStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # WATCHING → ABOVE_VWAP
        await strategy.on_candle(
            _candle(timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC), close=101.0)
        )
        # ABOVE_VWAP → BELOW_VWAP
        await strategy.on_candle(
            _candle(
                timestamp=datetime(2026, 2, 15, 15, 1, 0, tzinfo=UTC),
                close=99.5,
                low=99.5,
            )
        )
        # Reclaim: close > VWAP → triggers condition checks
        await strategy.on_candle(
            _candle(
                timestamp=datetime(2026, 2, 15, 15, 2, 0, tzinfo=UTC),
                close=100.2,
                volume=200_000,
            )
        )

        events = _events_of_type(strategy, EvaluationEventType.CONDITION_CHECK)
        assert len(events) >= 1
        condition_names = [e.metadata.get("condition_name") for e in events]
        assert "time_window" in condition_names


# ---------------------------------------------------------------------------
# Test 4: VWAP pattern strength emits QUALITY_SCORED
# ---------------------------------------------------------------------------


class TestVwapPatternStrengthEmitsQualityScored:

    @pytest.mark.asyncio
    async def test_vwap_pattern_strength_emits_quality_scored(self) -> None:
        ds = _mock_data_service(vwap=100.0)
        config = _vwap_config(
            min_pullback_bars=1,
            min_pullback_pct=0.001,
            volume_confirmation_multiplier=0.5,
            max_chase_above_vwap_pct=0.01,
        )
        strategy = VwapReclaimStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # WATCHING → ABOVE_VWAP
        await strategy.on_candle(
            _candle(timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC), close=101.0)
        )
        # ABOVE_VWAP → BELOW_VWAP
        await strategy.on_candle(
            _candle(
                timestamp=datetime(2026, 2, 15, 15, 1, 0, tzinfo=UTC),
                close=99.5,
                low=99.5,
                volume=100_000,
            )
        )
        # Reclaim with enough volume and within window
        result = await strategy.on_candle(
            _candle(
                timestamp=datetime(2026, 2, 15, 15, 2, 0, tzinfo=UTC),
                close=100.2,
                low=100.0,
                volume=200_000,
            )
        )
        assert result is not None  # Signal generated

        events = _events_of_type(strategy, EvaluationEventType.QUALITY_SCORED)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.INFO
        assert "VWAP Reclaim pattern strength" in events[0].reason
        assert "path_credit" in events[0].metadata
        assert "depth_credit" in events[0].metadata


# ---------------------------------------------------------------------------
# Test 5: AfMo consolidation emits STATE_TRANSITION
# ---------------------------------------------------------------------------


class TestAfmoConsolidationEmitsStateTransition:

    @pytest.mark.asyncio
    async def test_afmo_consolidation_emits_state_transition(self) -> None:
        """WATCHING → ACCUMULATING and consolidation tracking emit STATE_TRANSITION."""
        ds = _mock_data_service(atr=2.0)
        config = _afmo_config(min_consolidation_bars=5)
        strategy = AfternoonMomentumStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # 12:00 ET = 17:00 UTC → WATCHING → ACCUMULATING
        candle1 = _candle(
            timestamp=datetime(2026, 2, 15, 17, 0, 0, tzinfo=UTC),
            high=100.5,
            low=100.0,
        )
        await strategy.on_candle(candle1)

        events = _events_of_type(strategy, EvaluationEventType.STATE_TRANSITION)
        watching_to_acc = [
            e for e in events
            if "watching" in e.metadata.get("from_state", "")
            and "accumulating" in e.metadata.get("to_state", "")
        ]
        assert len(watching_to_acc) == 1

        # Second candle → consolidation tracking event
        candle2 = _candle(
            timestamp=datetime(2026, 2, 15, 17, 1, 0, tzinfo=UTC),
            high=100.6,
            low=100.1,
        )
        await strategy.on_candle(candle2)

        tracking = [
            e for e in _events_of_type(strategy, EvaluationEventType.STATE_TRANSITION)
            if "Consolidation tracking" in e.reason
        ]
        assert len(tracking) >= 1
        assert tracking[0].metadata["consolidation_bars"] >= 2


# ---------------------------------------------------------------------------
# Test 6: AfMo 8 conditions emit individual CONDITION_CHECK events
# ---------------------------------------------------------------------------


class TestAfmo8ConditionsEmitIndividualEvents:

    @pytest.mark.asyncio
    async def test_afmo_8_conditions_emit_individual_events(self) -> None:
        """Each of 8 breakout conditions emits a separate CONDITION_CHECK event."""
        ds = _mock_data_service(atr=2.0)
        config = _afmo_config(min_consolidation_bars=5)
        strategy = AfternoonMomentumStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Build consolidation: candles at 12:00+ ET (17:00+ UTC)
        for i in range(6):
            await strategy.on_candle(
                _candle(
                    timestamp=datetime(2026, 2, 15, 17, i, 0, tzinfo=UTC),
                    high=100.5,
                    low=100.0,
                    close=100.2,
                    volume=100_000,
                )
            )

        # Breakout candle at 14:01 ET = 19:01 UTC (within entry window)
        breakout = _candle(
            timestamp=datetime(2026, 2, 15, 19, 1, 0, tzinfo=UTC),
            open_price=100.3,
            high=101.0,
            low=100.2,
            close=100.8,
            volume=200_000,
        )
        await strategy.on_candle(breakout)

        events = _events_of_type(strategy, EvaluationEventType.CONDITION_CHECK)
        # Must have exactly 8 condition checks from the breakout evaluation
        condition_names = [e.metadata.get("condition_name") for e in events]
        expected_conditions = [
            "price_above_consolidation_high",
            "volume_confirmation",
            "body_ratio",
            "spread_range",
            "chase_protection",
            "time_remaining",
            "trend_alignment",
            "consolidation_quality",
        ]
        for cond in expected_conditions:
            assert cond in condition_names, f"Missing condition: {cond}"
        assert len(events) == 8


# ---------------------------------------------------------------------------
# Test 7: AfMo signal generated emits SIGNAL_GENERATED
# ---------------------------------------------------------------------------


class TestAfmoSignalGeneratedEmitsEvent:

    @pytest.mark.asyncio
    async def test_afmo_signal_generated_emits_event(self) -> None:
        """All conditions pass → SIGNAL_GENERATED event emitted."""
        ds = _mock_data_service(atr=2.0)
        config = _afmo_config(
            min_consolidation_bars=5,
            volume_multiplier=0.5,
            max_chase_pct=0.03,
        )
        strategy = AfternoonMomentumStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Build consolidation (need >= min_consolidation_bars)
        for i in range(6):
            await strategy.on_candle(
                _candle(
                    timestamp=datetime(2026, 2, 15, 17, i, 0, tzinfo=UTC),
                    high=100.5,
                    low=100.0,
                    close=100.2,
                    volume=100_000,
                )
            )

        # Breakout candle at 14:01 ET = 19:01 UTC
        breakout = _candle(
            timestamp=datetime(2026, 2, 15, 19, 1, 0, tzinfo=UTC),
            open_price=100.3,
            high=101.0,
            low=100.2,
            close=100.8,
            volume=200_000,
        )
        result = await strategy.on_candle(breakout)
        assert result is not None  # Signal generated

        events = _events_of_type(strategy, EvaluationEventType.SIGNAL_GENERATED)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.PASS
        assert "AfMo signal" in events[0].reason
        assert "entry" in events[0].metadata
        assert "stop" in events[0].metadata


# ---------------------------------------------------------------------------
# Test 8: AfMo pattern strength emits QUALITY_SCORED
# ---------------------------------------------------------------------------


class TestAfmoPatternStrengthEmitsQualityScored:

    @pytest.mark.asyncio
    async def test_afmo_pattern_strength_emits_quality_scored(self) -> None:
        ds = _mock_data_service(atr=2.0)
        config = _afmo_config(
            min_consolidation_bars=5,
            volume_multiplier=0.5,
            max_chase_pct=0.03,
        )
        strategy = AfternoonMomentumStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Build consolidation (need >= min_consolidation_bars)
        for i in range(6):
            await strategy.on_candle(
                _candle(
                    timestamp=datetime(2026, 2, 15, 17, i, 0, tzinfo=UTC),
                    high=100.5,
                    low=100.0,
                    close=100.2,
                    volume=100_000,
                )
            )

        # Breakout candle at 14:01 ET = 19:01 UTC
        breakout = _candle(
            timestamp=datetime(2026, 2, 15, 19, 1, 0, tzinfo=UTC),
            open_price=100.3,
            high=101.0,
            low=100.2,
            close=100.8,
            volume=200_000,
        )
        result = await strategy.on_candle(breakout)
        assert result is not None

        events = _events_of_type(strategy, EvaluationEventType.QUALITY_SCORED)
        assert len(events) == 1
        assert events[0].result == EvaluationResult.INFO
        assert "Afternoon Momentum pattern strength" in events[0].reason
        assert "tightness_credit" in events[0].metadata
        assert "surge_credit" in events[0].metadata

"""Unit tests for strategy evaluation telemetry.

Tests the EvaluationEvent model, EvaluationEventType/EvaluationResult enums,
StrategyEvaluationBuffer, and the BaseStrategy.record_evaluation() integration.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from argus.strategies.telemetry import (
    BUFFER_MAX_SIZE,
    EvaluationEvent,
    EvaluationEventType,
    EvaluationResult,
    StrategyEvaluationBuffer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 15, 9, 30, 0)


def _make_event(
    symbol: str = "AAPL",
    strategy_id: str = "strat_orb",
    event_type: EvaluationEventType = EvaluationEventType.CONDITION_CHECK,
    result: EvaluationResult = EvaluationResult.PASS,
    reason: str = "volume above threshold",
) -> EvaluationEvent:
    return EvaluationEvent(
        timestamp=_NOW,
        symbol=symbol,
        strategy_id=strategy_id,
        event_type=event_type,
        result=result,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


def test_evaluation_event_type_enum_values() -> None:
    """EvaluationEventType must have exactly 9 values."""
    values = list(EvaluationEventType)
    assert len(values) == 9
    expected = {
        "TIME_WINDOW_CHECK",
        "INDICATOR_STATUS",
        "OPENING_RANGE_UPDATE",
        "ENTRY_EVALUATION",
        "CONDITION_CHECK",
        "SIGNAL_GENERATED",
        "SIGNAL_REJECTED",
        "STATE_TRANSITION",
        "QUALITY_SCORED",
    }
    assert {v.value for v in values} == expected


def test_evaluation_result_enum_values() -> None:
    """EvaluationResult must have exactly 3 values: PASS, FAIL, INFO."""
    values = list(EvaluationResult)
    assert len(values) == 3
    assert {v.value for v in values} == {"PASS", "FAIL", "INFO"}


# ---------------------------------------------------------------------------
# EvaluationEvent tests
# ---------------------------------------------------------------------------


def test_evaluation_event_construction() -> None:
    """EvaluationEvent stores all fields correctly."""
    meta = {"rvol": 3.2, "atr_ratio": 1.1}
    event = EvaluationEvent(
        timestamp=_NOW,
        symbol="TSLA",
        strategy_id="strat_vwap",
        event_type=EvaluationEventType.SIGNAL_GENERATED,
        result=EvaluationResult.PASS,
        reason="VWAP reclaim confirmed",
        metadata=meta,
    )
    assert event.timestamp == _NOW
    assert event.symbol == "TSLA"
    assert event.strategy_id == "strat_vwap"
    assert event.event_type == EvaluationEventType.SIGNAL_GENERATED
    assert event.result == EvaluationResult.PASS
    assert event.reason == "VWAP reclaim confirmed"
    assert event.metadata == meta


def test_evaluation_event_frozen() -> None:
    """EvaluationEvent is immutable — assigning any field raises FrozenInstanceError."""
    event = _make_event()
    with pytest.raises(FrozenInstanceError):
        event.symbol = "NVDA"  # type: ignore[misc]


def test_evaluation_event_default_metadata() -> None:
    """EvaluationEvent metadata defaults to empty dict when not provided."""
    event = _make_event()
    assert event.metadata == {}


# ---------------------------------------------------------------------------
# StrategyEvaluationBuffer tests
# ---------------------------------------------------------------------------


def test_buffer_record_and_query() -> None:
    """Recorded events are returned by query in newest-first order."""
    buf = StrategyEvaluationBuffer()
    e1 = _make_event(symbol="AAPL", reason="first")
    e2 = _make_event(symbol="AAPL", reason="second")
    buf.record(e1)
    buf.record(e2)
    results = buf.query()
    assert results[0] is e2
    assert results[1] is e1


def test_buffer_fifo_eviction() -> None:
    """When buffer exceeds maxlen, oldest events are evicted first."""
    buf = StrategyEvaluationBuffer(maxlen=3)
    events = [_make_event(reason=f"event_{i}") for i in range(5)]
    for e in events:
        buf.record(e)
    assert len(buf) == 3
    # snapshot is in insertion order, so oldest retained is events[2]
    snapshot = buf.snapshot()
    assert snapshot[0] is events[2]
    assert snapshot[1] is events[3]
    assert snapshot[2] is events[4]


def test_buffer_query_symbol_filter() -> None:
    """query(symbol=...) returns only events for that symbol."""
    buf = StrategyEvaluationBuffer()
    buf.record(_make_event(symbol="AAPL"))
    buf.record(_make_event(symbol="TSLA"))
    buf.record(_make_event(symbol="AAPL"))
    results = buf.query(symbol="AAPL")
    assert len(results) == 2
    assert all(e.symbol == "AAPL" for e in results)


def test_buffer_query_limit() -> None:
    """query(limit=N) returns at most N events."""
    buf = StrategyEvaluationBuffer()
    for i in range(20):
        buf.record(_make_event(reason=f"event_{i}"))
    results = buf.query(limit=5)
    assert len(results) == 5


def test_buffer_snapshot_returns_copy() -> None:
    """snapshot() returns a new list — mutating it does not affect the buffer."""
    buf = StrategyEvaluationBuffer()
    buf.record(_make_event())
    snap = buf.snapshot()
    snap.clear()
    assert len(buf) == 1


def test_buffer_len() -> None:
    """__len__ reports the current number of buffered events."""
    buf = StrategyEvaluationBuffer()
    assert len(buf) == 0
    buf.record(_make_event())
    assert len(buf) == 1


def test_buffer_max_size_constant() -> None:
    """BUFFER_MAX_SIZE module constant equals 1000."""
    assert BUFFER_MAX_SIZE == 1000


# ---------------------------------------------------------------------------
# BaseStrategy.record_evaluation() integration
# ---------------------------------------------------------------------------


def test_record_evaluation_swallows_exceptions() -> None:
    """record_evaluation() must not propagate exceptions from a broken buffer."""
    from argus.core.config import StrategyConfig
    from argus.strategies.base_strategy import BaseStrategy
    from argus.models.strategy import ExitRules, MarketConditionsFilter, ScannerCriteria

    class _ConcreteStrategy(BaseStrategy):
        async def on_candle(self, event):  # type: ignore[override]
            return None

        async def on_tick(self, event):  # type: ignore[override]
            pass

        def get_scanner_criteria(self) -> ScannerCriteria:
            return MagicMock(spec=ScannerCriteria)

        def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
            return 0

        def get_exit_rules(self) -> ExitRules:
            return MagicMock(spec=ExitRules)

        def get_market_conditions_filter(self) -> MarketConditionsFilter:
            return MagicMock(spec=MarketConditionsFilter)

    config = MagicMock(spec=StrategyConfig)
    config.strategy_id = "strat_test"
    config.name = "Test"
    config.version = "1.0"
    config.risk_limits = MagicMock()
    config.risk_limits.max_trades_per_day = 5
    config.risk_limits.max_daily_loss_pct = 0.03

    strategy = _ConcreteStrategy(config=config)

    # Make the buffer's record() raise
    strategy._eval_buffer.record = MagicMock(side_effect=RuntimeError("boom"))

    # Should not raise
    strategy.record_evaluation(
        symbol="AAPL",
        event_type=EvaluationEventType.CONDITION_CHECK,
        result=EvaluationResult.FAIL,
        reason="test exception swallow",
    )

"""Tests for Learning Loop auto-trigger via SessionEndEvent.

Validates Amendment 13 (Event Bus subscription) and Amendment 10
(zero-trade guard).

Sprint 28, Session 5.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from argus.core.event_bus import EventBus
from argus.core.events import SessionEndEvent
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    DataQualityPreamble,
    LearningLoopConfig,
    LearningReport,
)


@pytest.fixture
def ll_config() -> LearningLoopConfig:
    """Provide a LearningLoopConfig with auto-trigger enabled."""
    return LearningLoopConfig(enabled=True, auto_trigger_enabled=True)


@pytest.fixture
def disabled_config() -> LearningLoopConfig:
    """Provide a LearningLoopConfig with auto-trigger disabled."""
    return LearningLoopConfig(enabled=True, auto_trigger_enabled=False)


@pytest.fixture
async def store(tmp_path: Path) -> LearningStore:
    """Provide an initialized LearningStore."""
    s = LearningStore(db_path=str(tmp_path / "learning_test.db"))
    await s.initialize()
    return s


def _make_service(config: LearningLoopConfig, store: LearningStore):
    """Build a LearningService with mocked analyzers."""
    from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
    from argus.intelligence.learning.learning_service import LearningService
    from argus.intelligence.learning.outcome_collector import OutcomeCollector
    from argus.intelligence.learning.threshold_analyzer import ThresholdAnalyzer
    from argus.intelligence.learning.weight_analyzer import WeightAnalyzer

    collector = OutcomeCollector(
        argus_db_path="data/argus.db",
        counterfactual_db_path="data/counterfactual.db",
    )

    return LearningService(
        config=config,
        outcome_collector=collector,
        weight_analyzer=WeightAnalyzer(),
        threshold_analyzer=ThresholdAnalyzer(),
        correlation_analyzer=CorrelationAnalyzer(),
        store=store,
        quality_engine_yaml_path="nonexistent.yaml",  # will use defaults
    )


@pytest.mark.asyncio
async def test_auto_trigger_fires_on_session_end_event(
    ll_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Auto-trigger calls run_analysis when SessionEndEvent arrives."""
    service = _make_service(ll_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    # Mock run_analysis to track calls
    mock_report = AsyncMock(return_value=None)
    service.run_analysis = mock_report  # type: ignore[method-assign]

    event = SessionEndEvent(
        trading_day="2026-03-28",
        trades_count=10,
        counterfactual_count=5,
    )
    await event_bus.publish(event)

    # Give the handler time to run
    await asyncio.sleep(0.05)
    mock_report.assert_called_once()


@pytest.mark.asyncio
async def test_auto_trigger_skips_when_disabled(
    disabled_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Auto-trigger does nothing when auto_trigger_enabled=False."""
    service = _make_service(disabled_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    mock_report = AsyncMock(return_value=None)
    service.run_analysis = mock_report  # type: ignore[method-assign]

    event = SessionEndEvent(
        trading_day="2026-03-28",
        trades_count=10,
        counterfactual_count=5,
    )
    await event_bus.publish(event)
    await asyncio.sleep(0.05)
    mock_report.assert_not_called()


@pytest.mark.asyncio
async def test_zero_trade_guard_skips_on_zero_both(
    ll_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Amendment 10: Skips analysis when trades=0 AND counterfactual=0."""
    service = _make_service(ll_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    mock_report = AsyncMock(return_value=None)
    service.run_analysis = mock_report  # type: ignore[method-assign]

    event = SessionEndEvent(
        trading_day="2026-03-28",
        trades_count=0,
        counterfactual_count=0,
    )
    await event_bus.publish(event)
    await asyncio.sleep(0.05)
    mock_report.assert_not_called()


@pytest.mark.asyncio
async def test_counterfactual_only_runs_analysis(
    ll_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Amendment 10: Runs analysis when trades=0 but counterfactual>0."""
    service = _make_service(ll_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    mock_report = AsyncMock(return_value=None)
    service.run_analysis = mock_report  # type: ignore[method-assign]

    event = SessionEndEvent(
        trading_day="2026-03-28",
        trades_count=0,
        counterfactual_count=15,
    )
    await event_bus.publish(event)
    await asyncio.sleep(0.05)
    mock_report.assert_called_once()


@pytest.mark.asyncio
async def test_timeout_enforcement(
    ll_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Analysis timeout after 120s — handler should not block."""
    service = _make_service(ll_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    # Mock run_analysis to hang forever
    async def slow_analysis(*args, **kwargs):  # type: ignore[no-untyped-def]
        await asyncio.sleep(999)

    service.run_analysis = slow_analysis  # type: ignore[method-assign]

    event = SessionEndEvent(
        trading_day="2026-03-28",
        trades_count=5,
        counterfactual_count=3,
    )

    # Patch the timeout to be very short for the test
    with patch("argus.intelligence.learning.learning_service.asyncio.wait_for") as mock_wait:
        mock_wait.side_effect = asyncio.TimeoutError()
        await event_bus.publish(event)
        await asyncio.sleep(0.05)
        # Should have called wait_for and caught the timeout
        mock_wait.assert_called_once()


@pytest.mark.asyncio
async def test_auto_trigger_does_not_block_shutdown(
    ll_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Exception in auto-trigger is caught — does not propagate."""
    service = _make_service(ll_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    # Mock run_analysis to raise
    async def failing_analysis(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("Simulated failure")

    service.run_analysis = failing_analysis  # type: ignore[method-assign]

    event = SessionEndEvent(
        trading_day="2026-03-28",
        trades_count=5,
        counterfactual_count=3,
    )

    # Should not raise
    await event_bus.publish(event)
    await asyncio.sleep(0.05)
    # Test passes if no exception propagated


@pytest.mark.asyncio
async def test_auto_trigger_uses_event_bus_not_callback(
    ll_config: LearningLoopConfig,
    store: LearningStore,
) -> None:
    """Amendment 13: Verify subscription is via Event Bus."""
    service = _make_service(ll_config, store)
    event_bus = EventBus()
    service.register_auto_trigger(event_bus)

    # Verify SessionEndEvent has subscribers
    assert SessionEndEvent in event_bus._subscribers
    assert len(event_bus._subscribers[SessionEndEvent]) == 1

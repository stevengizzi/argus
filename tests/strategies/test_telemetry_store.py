"""Unit tests for EvaluationEventStore.

Tests DB separation (evaluation.db), rate-limited write warnings,
and pre-initialized store reuse.

Sprint 25.6, Session 1.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from argus.strategies.telemetry import (
    EvaluationEvent,
    EvaluationEventType,
    EvaluationResult,
)
from argus.strategies.telemetry_store import EvaluationEventStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path: Path) -> EvaluationEventStore:
    """Create an initialized EvaluationEventStore in a temp directory."""
    db_path = str(tmp_path / "evaluation.db")
    store = EvaluationEventStore(db_path)
    await store.initialize()
    yield store
    await store.close()


def _make_event(symbol: str = "AAPL", strategy_id: str = "orb") -> EvaluationEvent:
    """Create a minimal EvaluationEvent for testing."""
    return EvaluationEvent(
        timestamp=datetime(2026, 3, 19, 10, 0, 0),
        symbol=symbol,
        strategy_id=strategy_id,
        event_type=EvaluationEventType.ENTRY_EVALUATION,
        result=EvaluationResult.FAIL,
        reason="test",
        metadata={},
    )


# ---------------------------------------------------------------------------
# Test 1: Store connects to evaluation.db path (not argus.db)
# ---------------------------------------------------------------------------


class TestDBSeparation:
    """Verify evaluation data goes to a dedicated database file."""

    @pytest.mark.asyncio
    async def test_store_uses_evaluation_db_path(self, tmp_path: Path) -> None:
        """EvaluationEventStore connects to the path passed in (evaluation.db)."""
        eval_db = str(tmp_path / "evaluation.db")
        store = EvaluationEventStore(eval_db)
        await store.initialize()
        try:
            assert store.is_connected
            assert store._db_path == eval_db
            # The file should exist on disk
            assert Path(eval_db).exists()
        finally:
            await store.close()

    @pytest.mark.asyncio
    async def test_argus_db_unaffected_by_evaluation_store(
        self, tmp_path: Path
    ) -> None:
        """Writing to evaluation.db does not create tables in argus.db."""
        import aiosqlite

        argus_db_path = str(tmp_path / "argus.db")
        eval_db_path = str(tmp_path / "evaluation.db")

        # Create a minimal argus.db with a trades table
        async with aiosqlite.connect(argus_db_path) as conn:
            await conn.execute(
                "CREATE TABLE trades (id INTEGER PRIMARY KEY, symbol TEXT)"
            )
            await conn.execute("INSERT INTO trades (symbol) VALUES ('AAPL')")
            await conn.commit()

        # Create and use evaluation store
        store = EvaluationEventStore(eval_db_path)
        await store.initialize()
        await store.write_event(_make_event())
        await store.close()

        # Verify argus.db still has trades but no evaluation_events
        async with aiosqlite.connect(argus_db_path) as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM trades")
            row = await cursor.fetchone()
            assert row[0] == 1

            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='evaluation_events'"
            )
            assert await cursor.fetchone() is None


# ---------------------------------------------------------------------------
# Test 2: write_event succeeds without contention
# ---------------------------------------------------------------------------


class TestWriteEvent:
    """Verify basic write_event functionality."""

    @pytest.mark.asyncio
    async def test_write_event_persists(self, store: EvaluationEventStore) -> None:
        """write_event inserts a row into evaluation_events."""
        await store.write_event(_make_event("NVDA", "scalp"))

        rows = await store.execute_query(
            "SELECT symbol, strategy_id FROM evaluation_events"
        )
        assert len(rows) == 1
        assert rows[0][0] == "NVDA"
        assert rows[0][1] == "scalp"


# ---------------------------------------------------------------------------
# Test 3: Rate-limiting suppresses repeated warnings
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Verify write_event warning rate-limiting."""

    @pytest.mark.asyncio
    async def test_rate_limits_write_failure_warnings(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Multiple write failures within 60s produce at most 1 warning."""
        store = EvaluationEventStore(str(tmp_path / "evaluation.db"))
        await store.initialize()

        # Force write failures by closing the connection
        await store._conn.close()

        with caplog.at_level(logging.WARNING, logger="argus.strategies.telemetry_store"):
            for _ in range(5):
                await store.write_event(_make_event())

        warning_count = sum(
            1
            for record in caplog.records
            if "Failed to write evaluation event" in record.message
        )
        assert warning_count == 1, f"Expected 1 warning, got {warning_count}"

        # Cleanup: set _conn to None so close() is a no-op
        store._conn = None

    @pytest.mark.asyncio
    async def test_warning_resumes_after_interval(self, tmp_path: Path) -> None:
        """After the suppression interval, a new warning is emitted."""
        store = EvaluationEventStore(str(tmp_path / "evaluation.db"))
        await store.initialize()
        await store._conn.close()

        # Patch _WARNING_INTERVAL_SECONDS to a tiny value for testing
        original_interval = EvaluationEventStore._WARNING_INTERVAL_SECONDS
        EvaluationEventStore._WARNING_INTERVAL_SECONDS = 0.01

        try:
            with patch.object(
                logging.getLogger("argus.strategies.telemetry_store"),
                "warning",
            ) as mock_warn:
                await store.write_event(_make_event())
                assert mock_warn.call_count == 1

                # Wait for interval to elapse
                await asyncio.sleep(0.05)

                await store.write_event(_make_event())
                assert mock_warn.call_count == 2
        finally:
            EvaluationEventStore._WARNING_INTERVAL_SECONDS = original_interval
            store._conn = None


# ---------------------------------------------------------------------------
# Test 4: Health check works with pre-initialized store
# ---------------------------------------------------------------------------


class TestHealthCheckReuse:
    """Verify health check can use a pre-initialized store."""

    @pytest.mark.asyncio
    async def test_health_check_with_pre_initialized_store(
        self, store: EvaluationEventStore
    ) -> None:
        """check_strategy_evaluations works with a store that was not just created."""
        from argus.core.clock import FixedClock
        from argus.core.config import (
            HealthConfig,
            OperatingWindow,
            StrategyConfig,
            StrategyRiskLimits,
        )
        from argus.core.event_bus import EventBus
        from argus.core.events import CandleEvent
        from argus.core.health import HealthMonitor

        # Store is already initialized (from fixture) — no initialize() call here
        assert store.is_connected

        # Write an event so the health check finds data
        await store.write_event(_make_event("AAPL", "strat_test"))

        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 3, 19, 14, 0, 0, tzinfo=UTC))

        config = HealthConfig(
            heartbeat_interval_seconds=60,
            heartbeat_url_env="",
            alert_webhook_url_env="",
            daily_check_enabled=False,
            weekly_reconciliation_enabled=False,
        )
        monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

        # The health check should work fine with the pre-initialized store
        # (no "not initialized" error, no re-initialize needed)
        await monitor.check_strategy_evaluations(
            strategies={},
            eval_store=store,
            clock=clock,
        )
        # If we got here without exception, the pre-initialized store works

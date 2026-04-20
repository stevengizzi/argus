"""Tests for EvaluationEventStore VACUUM and startup reclaim behavior.

Verifies:
1. cleanup_old_events() with VACUUM reclaims deleted pages (DB shrinks).
2. cleanup_old_events() without VACUUM does NOT shrink DB.
3. Startup reclaim triggers when freelist ratio exceeds threshold.
4. Startup reclaim does NOT trigger on a healthy small DB.
5. Startup reclaim skipped when file size is below threshold.

DEF-157 regression tests.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from argus.strategies.telemetry import (
    EvaluationEvent,
    EvaluationEventType,
    EvaluationResult,
)
from argus.strategies.telemetry_store import EvaluationEventStore

_ET = ZoneInfo("America/New_York")


def _make_event(
    trading_date: str, symbol: str = "AAPL", strategy_id: str = "orb"
) -> EvaluationEvent:
    """Create an EvaluationEvent with a specific trading date."""
    ts = datetime.strptime(trading_date, "%Y-%m-%d").replace(
        hour=10, tzinfo=_ET
    )
    return EvaluationEvent(
        timestamp=ts,
        symbol=symbol,
        strategy_id=strategy_id,
        event_type=EvaluationEventType.ENTRY_EVALUATION,
        result=EvaluationResult.FAIL,
        reason="test bulk insert",
        metadata={"padding": "x" * 500},
    )


async def _bulk_insert(
    store: EvaluationEventStore, trading_date: str, count: int
) -> None:
    """Insert many rows to create meaningful DB size."""
    for i in range(count):
        await store.write_event(_make_event(trading_date, f"SYM{i}"))


class TestRetentionVacuum:
    """Verify that VACUUM after retention DELETE reclaims disk space."""

    @pytest.mark.asyncio
    async def test_cleanup_with_vacuum_shrinks_db(self, tmp_path: Path) -> None:
        """DB file size decreases after cleanup_old_events with VACUUM enabled."""
        db_path = str(tmp_path / "evaluation.db")
        store = EvaluationEventStore(db_path)
        await store.initialize()

        # Insert many rows with old dates (>7 days ago)
        old_date = (datetime.now(_ET) - timedelta(days=10)).strftime("%Y-%m-%d")
        await _bulk_insert(store, old_date, 2000)

        # Force WAL checkpoint so data is in main DB file
        assert store._conn is not None
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        size_after_insert = Path(db_path).stat().st_size
        assert size_after_insert > 100_000, (
            f"Need meaningful DB size for test, got {size_after_insert}"
        )

        # Run retention cleanup (VACUUM_AFTER_CLEANUP=True by default)
        await store.cleanup_old_events()

        # DB should be significantly smaller after VACUUM
        size_after_vacuum = Path(db_path).stat().st_size
        assert size_after_vacuum < size_after_insert * 0.1, (
            f"Expected >90% shrinkage: {size_after_insert} -> {size_after_vacuum}"
        )

        # Connection should still be usable
        assert store.is_connected
        rows = await store.execute_query(
            "SELECT COUNT(*) FROM evaluation_events"
        )
        assert rows[0][0] == 0

        await store.close()

    @pytest.mark.asyncio
    async def test_cleanup_without_vacuum_preserves_file_size(
        self, tmp_path: Path
    ) -> None:
        """DB file size does NOT decrease when VACUUM_AFTER_CLEANUP is False."""
        db_path = str(tmp_path / "evaluation.db")
        store = EvaluationEventStore(db_path)
        store.VACUUM_AFTER_CLEANUP = False
        await store.initialize()

        old_date = (datetime.now(_ET) - timedelta(days=10)).strftime("%Y-%m-%d")
        await _bulk_insert(store, old_date, 2000)

        assert store._conn is not None
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        size_after_insert = Path(db_path).stat().st_size

        await store.cleanup_old_events()

        # Force checkpoint so freed pages show up in main file
        assert store._conn is not None
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # Without VACUUM, file size remains large (freed pages stay as freelist)
        size_after_delete = Path(db_path).stat().st_size
        assert size_after_delete >= size_after_insert * 0.9, (
            f"Without VACUUM, size should stay similar: "
            f"{size_after_insert} -> {size_after_delete}"
        )

        # But freelist should be high
        freelist_ratio = await store._get_freelist_ratio()
        assert freelist_ratio > 0.5, (
            f"Expected high freelist ratio after delete, got {freelist_ratio:.2f}"
        )

        await store.close()


class TestStartupReclaim:
    """Verify startup reclaim path triggers appropriately."""

    @pytest.mark.asyncio
    async def test_startup_reclaim_triggers_on_bloated_db(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Startup VACUUM triggers when freelist ratio exceeds threshold."""
        db_path = str(tmp_path / "evaluation.db")

        # Phase 1: create a DB with lots of data, then delete without VACUUM
        store = EvaluationEventStore(db_path)
        store.VACUUM_AFTER_CLEANUP = False
        store.STARTUP_RECLAIM_MIN_SIZE_MB = 0  # Any size
        await store.initialize()

        old_date = (datetime.now(_ET) - timedelta(days=10)).strftime("%Y-%m-%d")
        await _bulk_insert(store, old_date, 2000)

        assert store._conn is not None
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # Delete without VACUUM to create freelist
        await store.cleanup_old_events()
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        size_before_reclaim = Path(db_path).stat().st_size
        await store.close()

        # Phase 2: re-open with startup reclaim enabled (low thresholds)
        store2 = EvaluationEventStore(db_path)
        store2.STARTUP_RECLAIM_MIN_SIZE_MB = 0  # Any size triggers
        store2.STARTUP_RECLAIM_FREELIST_RATIO = 0.3  # Low threshold

        with caplog.at_level(logging.WARNING, logger="argus.strategies.telemetry_store"):
            await store2.initialize()

        # Should see the startup VACUUM warning
        vacuum_warnings = [
            r for r in caplog.records if "running startup VACUUM" in r.message
        ]
        assert len(vacuum_warnings) == 1

        # DB should have shrunk
        size_after_reclaim = Path(db_path).stat().st_size
        assert size_after_reclaim < size_before_reclaim * 0.2, (
            f"Expected >80% shrinkage: {size_before_reclaim} -> {size_after_reclaim}"
        )

        # Connection should still work
        assert store2.is_connected
        await store2.close()

    @pytest.mark.asyncio
    async def test_startup_reclaim_skipped_on_healthy_db(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Startup VACUUM does NOT trigger on a small healthy DB."""
        db_path = str(tmp_path / "evaluation.db")
        store = EvaluationEventStore(db_path)

        with caplog.at_level(logging.WARNING, logger="argus.strategies.telemetry_store"):
            await store.initialize()

        # No VACUUM warnings on a fresh empty DB
        vacuum_warnings = [
            r for r in caplog.records if "running startup VACUUM" in r.message
        ]
        assert len(vacuum_warnings) == 0

        await store.close()

    @pytest.mark.asyncio
    async def test_startup_reclaim_skipped_when_size_below_threshold(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Startup VACUUM skipped when DB size is below STARTUP_RECLAIM_MIN_SIZE_MB."""
        db_path = str(tmp_path / "evaluation.db")

        # Create DB with data and freelist but small file
        store = EvaluationEventStore(db_path)
        store.VACUUM_AFTER_CLEANUP = False
        await store.initialize()

        old_date = (datetime.now(_ET) - timedelta(days=10)).strftime("%Y-%m-%d")
        await _bulk_insert(store, old_date, 100)

        assert store._conn is not None
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        await store.cleanup_old_events()
        await store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        await store.close()

        # Re-open with default 500 MB threshold — small test DB won't qualify
        store2 = EvaluationEventStore(db_path)
        # Default STARTUP_RECLAIM_MIN_SIZE_MB = 500 — test DB is ~100 KB

        with caplog.at_level(logging.WARNING, logger="argus.strategies.telemetry_store"):
            await store2.initialize()

        vacuum_warnings = [
            r for r in caplog.records if "running startup VACUUM" in r.message
        ]
        assert len(vacuum_warnings) == 0

        await store2.close()

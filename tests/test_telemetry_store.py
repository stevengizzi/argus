"""Tests for EvaluationEventStore (SQLite persistence) and REST date routing.

Sprint 24.5, Session 3.5.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.auth import create_access_token, hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import (
    ApiConfig,
    HealthConfig,
    OrbBreakoutConfig,
    OrderManagerConfig,
    RiskConfig,
    SystemConfig,
)
from argus.core.event_bus import EventBus
from argus.core.health import HealthMonitor
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.telemetry import (
    EvaluationEvent,
    EvaluationEventType,
    EvaluationResult,
    StrategyEvaluationBuffer,
)
from argus.strategies.telemetry_store import EvaluationEventStore

_ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    symbol: str = "AAPL",
    strategy_id: str = "strat_orb",
    event_type: EvaluationEventType = EvaluationEventType.CONDITION_CHECK,
    result: EvaluationResult = EvaluationResult.PASS,
    reason: str = "volume above threshold",
    timestamp: datetime | None = None,
) -> EvaluationEvent:
    return EvaluationEvent(
        timestamp=timestamp or datetime(2026, 3, 15, 9, 30, 0),
        symbol=symbol,
        strategy_id=strategy_id,
        event_type=event_type,
        result=result,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Store unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path) -> AsyncGenerator[EvaluationEventStore, None]:
    """Yield an initialized in-memory store."""
    db_path = str(tmp_path / "test_eval.db")
    s = EvaluationEventStore(db_path)
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_store_initialize_creates_table(store: EvaluationEventStore) -> None:
    """Table exists after initialization."""
    assert store._conn is not None
    cursor = await store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='evaluation_events'"
    )
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_store_write_and_read_event(store: EvaluationEventStore) -> None:
    """Written event can be queried back."""
    event = _make_event()
    await store.write_event(event)
    results = await store.query_events(strategy_id="strat_orb", date="2026-03-15")
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"
    assert results[0]["event_type"] == "CONDITION_CHECK"
    assert results[0]["result"] == "PASS"
    assert results[0]["reason"] == "volume above threshold"


@pytest.mark.asyncio
async def test_store_query_by_strategy_id(store: EvaluationEventStore) -> None:
    """Only events matching the strategy_id are returned."""
    await store.write_event(_make_event(strategy_id="strat_orb"))
    await store.write_event(_make_event(strategy_id="strat_vwap"))
    results = await store.query_events(strategy_id="strat_vwap", date="2026-03-15")
    assert len(results) == 1
    assert results[0]["strategy_id"] == "strat_vwap"


@pytest.mark.asyncio
async def test_store_query_by_symbol(store: EvaluationEventStore) -> None:
    """Only events matching the symbol are returned."""
    await store.write_event(_make_event(symbol="AAPL"))
    await store.write_event(_make_event(symbol="TSLA"))
    results = await store.query_events(
        strategy_id="strat_orb", symbol="TSLA", date="2026-03-15"
    )
    assert len(results) == 1
    assert results[0]["symbol"] == "TSLA"


@pytest.mark.asyncio
async def test_store_query_by_date(store: EvaluationEventStore) -> None:
    """Only events matching the date are returned."""
    await store.write_event(
        _make_event(timestamp=datetime(2026, 3, 14, 10, 0, 0))
    )
    await store.write_event(
        _make_event(timestamp=datetime(2026, 3, 15, 10, 0, 0))
    )
    results = await store.query_events(strategy_id="strat_orb", date="2026-03-14")
    assert len(results) == 1
    assert results[0]["trading_date"] == "2026-03-14"


@pytest.mark.asyncio
async def test_store_combined_filters(store: EvaluationEventStore) -> None:
    """strategy + symbol + date combined filter returns correct subset."""
    await store.write_event(_make_event(symbol="AAPL", strategy_id="strat_orb"))
    await store.write_event(_make_event(symbol="TSLA", strategy_id="strat_orb"))
    await store.write_event(_make_event(symbol="AAPL", strategy_id="strat_vwap"))
    results = await store.query_events(
        strategy_id="strat_orb", symbol="AAPL", date="2026-03-15"
    )
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"
    assert results[0]["strategy_id"] == "strat_orb"


@pytest.mark.asyncio
async def test_store_cleanup_purges_old(store: EvaluationEventStore) -> None:
    """Events older than RETENTION_DAYS are deleted."""
    old_ts = datetime.now(_ET) - timedelta(days=10)
    await store.write_event(_make_event(timestamp=old_ts))
    await store.cleanup_old_events()
    # Query with the old date — should be gone
    results = await store.query_events(
        strategy_id="strat_orb", date=old_ts.strftime("%Y-%m-%d")
    )
    assert len(results) == 0


@pytest.mark.asyncio
async def test_store_cleanup_preserves_recent(store: EvaluationEventStore) -> None:
    """Events within RETENTION_DAYS survive cleanup."""
    recent_ts = datetime.now(_ET) - timedelta(days=2)
    await store.write_event(_make_event(timestamp=recent_ts))
    await store.cleanup_old_events()
    results = await store.query_events(
        strategy_id="strat_orb", date=recent_ts.strftime("%Y-%m-%d")
    )
    assert len(results) == 1


# ---------------------------------------------------------------------------
# IMPROMPTU-10 (DEF-197): periodic retention scheduler regression tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_periodic_retention_task_starts_on_initialize(
    store: EvaluationEventStore,
) -> None:
    """initialize() schedules the periodic retention task on a live event loop."""
    assert store._retention_task is not None
    assert not store._retention_task.done()


@pytest.mark.asyncio
async def test_periodic_retention_task_cancels_cleanly_on_close(
    tmp_path: Path,
) -> None:
    """close() cancels the periodic retention task without leaking exceptions.

    Reverting the close() cancellation block leaves task.done() False after
    close() returns and produces a 'Task was destroyed but it is pending'
    warning at GC time — this assertion catches the regression.
    """
    db_path = str(tmp_path / "cancel.db")
    s = EvaluationEventStore(db_path)
    await s.initialize()
    task = s._retention_task
    assert task is not None
    assert not task.done()
    await s.close()
    assert task.done()
    assert task.cancelled() or task.exception() is None


@pytest.mark.asyncio
async def test_periodic_retention_invokes_cleanup_old_events(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The periodic loop actually fires cleanup_old_events() on its cadence.

    Reverting the asyncio.create_task(self._run_periodic_retention()) line in
    initialize() leaves the old-row in place after the wait window — this
    assertion catches the regression. Wall-clock cost ~0.2s.
    """
    db_path = str(tmp_path / "periodic.db")
    s = EvaluationEventStore(db_path)
    # Sprint 31.915 (DEC-389): RETENTION_INTERVAL_SECONDS migrated from
    # class-constant to EvaluationStoreConfig.retention_interval_seconds,
    # synced into ``self.RETENTION_INTERVAL_SECONDS`` in __init__. The
    # original IMPROMPTU-10 test monkeypatched the class constant; we
    # override the instance attribute (which production reads) directly.
    monkeypatch.setattr(s, "RETENTION_INTERVAL_SECONDS", 0.05)
    await s.initialize()
    try:
        old_ts = datetime.now(_ET) - timedelta(days=10)
        await s.write_event(_make_event(timestamp=old_ts))
        pre = await s.query_events(
            strategy_id="strat_orb", date=old_ts.strftime("%Y-%m-%d")
        )
        assert len(pre) == 1
        # Wait long enough for at least one periodic iteration (50ms + buffer)
        import asyncio as _asyncio
        await _asyncio.sleep(0.2)
        post = await s.query_events(
            strategy_id="strat_orb", date=old_ts.strftime("%Y-%m-%d")
        )
        assert len(post) == 0
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_store_write_failure_doesnt_raise(tmp_path) -> None:
    """write_event() logs but never raises on DB failure."""
    store = EvaluationEventStore(str(tmp_path / "test.db"))
    await store.initialize()
    # Close the connection to force a failure
    await store._conn.close()  # type: ignore[union-attr]
    # Should not raise
    await store.write_event(_make_event())


@pytest.mark.asyncio
async def test_store_query_default_date_is_today(store: EvaluationEventStore) -> None:
    """query_events with date=None defaults to today (ET)."""
    today_et = datetime.now(_ET)
    await store.write_event(_make_event(timestamp=today_et))
    results = await store.query_events(strategy_id="strat_orb")
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Buffer → store forwarding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buffer_record_forwards_to_store(store: EvaluationEventStore) -> None:
    """StrategyEvaluationBuffer.record() writes to store when wired."""
    buf = StrategyEvaluationBuffer()
    buf.set_store(store)
    event = _make_event()
    buf.record(event)
    # Let the fire-and-forget task complete
    import asyncio

    await asyncio.sleep(0.05)
    results = await store.query_events(strategy_id="strat_orb", date="2026-03-15")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_buffer_record_works_without_store() -> None:
    """Ring buffer works normally when no store is attached."""
    buf = StrategyEvaluationBuffer()
    event = _make_event()
    buf.record(event)
    assert len(buf) == 1
    assert buf.query()[0] is event


# ---------------------------------------------------------------------------
# REST endpoint date routing
# ---------------------------------------------------------------------------


_TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


@pytest.fixture
def rest_clock() -> FixedClock:
    return FixedClock(datetime(2026, 2, 23, 15, 30, 0, tzinfo=UTC))


@pytest.fixture
async def rest_db(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    mgr = DatabaseManager(tmp_path / "rest_test.db")
    await mgr.initialize()
    yield mgr
    await mgr.close()


@pytest.fixture
async def rest_app_state(
    rest_db: DatabaseManager,
    rest_clock: FixedClock,
    store: EvaluationEventStore,
) -> AppState:
    from argus.analytics.trade_logger import TradeLogger

    bus = EventBus()
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()
    tl = TradeLogger(rest_db)
    hm = HealthMonitor(
        event_bus=bus, clock=rest_clock, config=HealthConfig(),
        broker=broker, trade_logger=tl,
    )
    rm = RiskManager(config=RiskConfig(), broker=broker, event_bus=bus, clock=rest_clock)
    om = OrderManager(
        event_bus=bus, broker=broker, clock=rest_clock,
        config=OrderManagerConfig(), trade_logger=tl,
    )
    cfg = SystemConfig(api=ApiConfig(
        enabled=True, host="127.0.0.1", port=8000,
        password_hash=hash_password("testpw"),
        jwt_secret_env="ARGUS_JWT_SECRET",
    ))

    orb_cfg = OrbBreakoutConfig(
        strategy_id="strat_orb_breakout",
        name="ORB Breakout", version="1.0.0", enabled=True,
    )
    strat = OrbBreakoutStrategy(config=orb_cfg, data_service=None, clock=rest_clock)
    strat.eval_buffer.record(EvaluationEvent(
        timestamp=datetime(2026, 3, 15, 9, 30, 0),
        symbol="AAPL",
        strategy_id=strat.strategy_id,
        event_type=EvaluationEventType.CONDITION_CHECK,
        result=EvaluationResult.PASS,
        reason="volume above threshold",
    ))

    return AppState(
        event_bus=bus, trade_logger=tl, broker=broker,
        health_monitor=hm, risk_manager=rm, order_manager=om,
        clock=rest_clock, config=cfg, start_time=time.time(),
        strategies={strat.strategy_id: strat},
        telemetry_store=store,
    )


@pytest.fixture
def rest_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("ARGUS_JWT_SECRET", _TEST_JWT_SECRET)
    set_jwt_secret(_TEST_JWT_SECRET)
    return _TEST_JWT_SECRET


@pytest.fixture
def rest_auth_headers(rest_jwt_secret: str) -> dict[str, str]:
    token, _ = create_access_token(rest_jwt_secret, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def rest_client(
    rest_app_state: AppState,
    rest_jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(rest_app_state)
    app.state.app_state = rest_app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_rest_date_param_routes_to_store(
    rest_client: AsyncClient,
    rest_auth_headers: dict[str, str],
    store: EvaluationEventStore,
    rest_app_state: AppState,
) -> None:
    """GET /decisions?date=<past> queries the persistent store."""
    strategy_id = "strat_orb_breakout"
    await store.write_event(
        _make_event(
            strategy_id=strategy_id,
            timestamp=datetime(2026, 3, 10, 10, 0, 0),
            reason="historical event",
        )
    )
    response = await rest_client.get(
        f"/api/v1/strategies/{strategy_id}/decisions?date=2026-03-10",
        headers=rest_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["reason"] == "historical event"


@pytest.mark.asyncio
async def test_rest_no_date_uses_buffer(
    rest_client: AsyncClient,
    rest_auth_headers: dict[str, str],
) -> None:
    """GET /decisions without date param uses the ring buffer."""
    response = await rest_client.get(
        "/api/v1/strategies/strat_orb_breakout/decisions",
        headers=rest_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["reason"] == "volume above threshold"


# ---------------------------------------------------------------------------
# Sprint 31.915 — DEC-389 / DEF-231 / DEF-232 / DEF-233 / DEF-234 regression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retention_days_is_config_driven(tmp_path: Path) -> None:
    """G2 / DEF-234 / DEC-389: retention_days reflects EvaluationStoreConfig."""
    from argus.core.config import EvaluationStoreConfig

    cfg = EvaluationStoreConfig(retention_days=3)
    s = EvaluationEventStore(str(tmp_path / "cfgdriven.db"), config=cfg)
    await s.initialize()
    try:
        assert s._config.retention_days == 3
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_retention_logs_zero_deletion_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """G3 / DEF-231: zero-deletion branch emits an INFO log line.

    Mental revert (delete the ``else: logger.info(...)`` branch in
    ``cleanup_old_events``) → this test fails because no INFO line is
    captured. The pre-Sprint-31.915 production code took this path
    silently between Apr 22–27, masking that retention was firing.
    """
    import logging as _logging

    caplog.set_level(_logging.INFO, logger="argus.strategies.telemetry_store")
    s = EvaluationEventStore(str(tmp_path / "zerodel.db"))
    await s.initialize()
    try:
        caplog.clear()
        await s.cleanup_old_events()  # empty DB → 0 deletions
        msgs = [rec.message for rec in caplog.records]
        assert any(
            "0 rows matched" in m for m in msgs
        ), f"Expected zero-deletion INFO log; got: {msgs}"
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_retention_logs_success_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """G3 + G1 regression / DEF-231: positive-deletion branch logs an INFO line.

    Phase A H3 mechanism guard: the production silent-failure mode on
    Apr 27→28 was that VACUUM raised mid-cleanup, propagating up and
    skipping the success-path INFO line that previously lived AFTER the
    VACUUM call. Sprint 31.915's fix moves the deletion-INFO BEFORE the
    VACUUM attempt so a vacuum failure cannot eat the deletion record.

    Mental revert (move the ``logger.info("retention deleted ...")`` line
    back to AFTER ``await self._vacuum()``) → this test still PASSES under
    happy-path VACUUM, but the H4 sibling guard
    ``test_retention_logs_success_even_when_vacuum_fails`` would fail.
    """
    import logging as _logging

    caplog.set_level(_logging.INFO, logger="argus.strategies.telemetry_store")
    s = EvaluationEventStore(str(tmp_path / "succpath.db"))
    await s.initialize()
    try:
        old_ts = datetime.now(_ET) - timedelta(days=10)
        await s.write_event(_make_event(timestamp=old_ts))
        caplog.clear()
        await s.cleanup_old_events()
        msgs = [rec.message for rec in caplog.records]
        assert any(
            "retention deleted 1 rows" in m for m in msgs
        ), f"Expected success-path INFO log; got: {msgs}"
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_retention_logs_success_even_when_vacuum_fails(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Phase A H3 / DEF-231: deletion-INFO survives a VACUUM raising mid-cleanup.

    Production Apr 27→28 mechanism reproducer. Forces ``_vacuum`` to
    raise ``OSError`` AFTER the DELETE has committed; pre-Sprint-31.915
    code would swallow the deletion log because the INFO line was on the
    wrong side of the await. Post-Sprint-31.915 the deletion-INFO fires
    BEFORE VACUUM, so it survives.
    """
    import logging as _logging

    caplog.set_level(_logging.INFO, logger="argus.strategies.telemetry_store")
    s = EvaluationEventStore(str(tmp_path / "vacfail.db"))
    await s.initialize()

    async def _failing_vacuum() -> None:
        raise OSError("ENOSPC: simulated disk pressure during VACUUM")

    s._vacuum = _failing_vacuum  # type: ignore[method-assign]
    try:
        old_ts = datetime.now(_ET) - timedelta(days=10)
        await s.write_event(_make_event(timestamp=old_ts))
        caplog.clear()
        with pytest.raises(OSError):
            await s.cleanup_old_events()
        msgs = [rec.message for rec in caplog.records]
        assert any(
            "retention deleted 1 rows" in m for m in msgs
        ), f"Expected deletion INFO before VACUUM raised; got: {msgs}"
        # Observability fields updated even though VACUUM raised.
        assert s._last_retention_deleted_count == 1
        assert s._last_retention_run_at_et is not None
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_pre_vacuum_disk_headroom_check_aborts_when_insufficient(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """G4 / DEF-232: VACUUM aborts loudly when free disk < 2x DB size."""
    import logging as _logging
    import shutil as _shutil
    from collections import namedtuple

    caplog.set_level(_logging.WARNING, logger="argus.strategies.telemetry_store")
    s = EvaluationEventStore(str(tmp_path / "headroom_short.db"))
    await s.initialize()
    try:
        # Simulate a disk with effectively zero free space.
        DiskUsage = namedtuple("DiskUsage", "total used free")
        monkeypatch.setattr(
            _shutil, "disk_usage", lambda _p: DiskUsage(10**9, 10**9 - 1, 1)
        )
        # Track whether the post-headroom-check VACUUM logic ran. The
        # synchronous VACUUM path uses asyncio.to_thread + sqlite3; if the
        # check aborts correctly, neither the close-aiosqlite step nor the
        # to_thread call should run.
        called: dict[str, bool] = {"to_thread_invoked": False}

        async def _spy_to_thread(func: Any, *args: Any, **kwargs: Any) -> None:
            called["to_thread_invoked"] = True

        monkeypatch.setattr(asyncio, "to_thread", _spy_to_thread)

        caplog.clear()
        await s._vacuum()
        msgs = [rec.message for rec in caplog.records]
        assert any(
            "headroom check FAILED" in m for m in msgs
        ), f"Expected pre-VACUUM headroom WARNING; got: {msgs}"
        assert called["to_thread_invoked"] is False, (
            "VACUUM proceeded despite insufficient headroom — non-bypassable "
            "check broken (RULE-039)."
        )
        # Connection should still be alive — we aborted BEFORE closing it.
        assert s._conn is not None
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_pre_vacuum_disk_headroom_check_proceeds_when_sufficient(
    tmp_path: Path,
) -> None:
    """G4 / DEF-232: VACUUM proceeds when free disk >= 2x DB size (happy path)."""
    s = EvaluationEventStore(str(tmp_path / "headroom_ok.db"))
    await s.initialize()
    try:
        # tmp_path almost certainly has plenty of headroom. Confirm the
        # connection is still alive after VACUUM (reopened post-vacuum).
        await s._vacuum()
        assert s._conn is not None
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_get_health_snapshot_exposes_required_fields(tmp_path: Path) -> None:
    """G5 / DEF-233: get_health_snapshot returns the synchronous slice."""
    s = EvaluationEventStore(str(tmp_path / "snap.db"))
    await s.initialize()
    try:
        snap = s.get_health_snapshot()
        assert "size_mb" in snap
        assert "last_retention_run_at_et" in snap  # null on fresh init
        assert "last_retention_deleted_count" in snap  # null on fresh init
        assert snap["last_retention_run_at_et"] is None
        assert snap["last_retention_deleted_count"] is None
        # Async sibling for freelist
        freelist = await s.get_freelist_pct()
        assert isinstance(freelist, float)
        assert 0.0 <= freelist <= 100.0
    finally:
        await s.close()


@pytest.mark.asyncio
async def test_health_snapshot_updates_after_retention(tmp_path: Path) -> None:
    """G5 / DEF-233: observability fields update after cleanup_old_events."""
    s = EvaluationEventStore(str(tmp_path / "snapupd.db"))
    await s.initialize()
    try:
        old_ts = datetime.now(_ET) - timedelta(days=10)
        await s.write_event(_make_event(timestamp=old_ts))
        await s.cleanup_old_events()
        snap = s.get_health_snapshot()
        assert snap["last_retention_run_at_et"] is not None
        assert snap["last_retention_deleted_count"] == 1
    finally:
        await s.close()

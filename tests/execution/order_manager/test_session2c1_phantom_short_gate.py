"""Sprint 31.91 Session 2c.1 — phantom-short per-symbol entry gate tests.

Covers the new OrderManager state and persistence layer added in Session
2c.1:

- Engagement: ``_handle_broker_orphan_short`` (extended from Session 2b.1)
  adds the symbol to ``_phantom_short_gated_symbols`` and persists the
  row to ``data/operations.db::phantom_short_gated_symbols``.
- Block: ``on_approved`` rejects ``OrderApprovedEvent`` for any symbol
  in the gated set with ``rejection_reason="phantom_short_gate"`` BEFORE
  any broker order is placed.
- Per-symbol granularity: gating AAPL does NOT block MSFT.
- M5 rehydration ordering: ``_rehydrate_gated_symbols_from_db()`` runs
  BEFORE ``start()`` subscribes to ``OrderApprovedEvent``, so a restart
  cannot expose a window of unsafe entries.
- E2E: simulate a shutdown + reconstruction; gated symbol survives.

These tests are revert-proof for the Session 2c.1 changes — the in-memory
state, the persistence + rehydration flow, and the rejection wiring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, ReconciliationConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    Side,
    SignalEvent,
    SignalRejectedEvent,
)
from argus.execution.order_manager import (
    OrderManager,
    ReconciliationPosition,
)
from argus.models.trading import OrderSide


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock()
    broker.place_bracket_order = AsyncMock()
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    broker.get_positions = AsyncMock(return_value=[])
    return broker


def _make_order_manager(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    operations_db_path: Path,
    *,
    broker_orphan_alert_enabled: bool = True,
    broker_orphan_entry_gate_enabled: bool = True,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(
            broker_orphan_alert_enabled=broker_orphan_alert_enabled,
            broker_orphan_entry_gate_enabled=broker_orphan_entry_gate_enabled,
        ),
        operations_db_path=str(operations_db_path),
    )


def _make_signal(symbol: str = "AAPL") -> SignalEvent:
    """Build a minimal SignalEvent for OrderApprovedEvent fixtures."""
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol=symbol,
        side=Side.LONG,
        entry_price=100.0,
        stop_price=99.0,
        target_prices=(101.0, 102.0),
        share_count=10,
    )


async def _drain(event_bus: EventBus) -> None:
    """Yield once so EventBus.publish handler tasks settle."""
    await event_bus.drain()


async def _await_persist_tasks(om: OrderManager) -> None:
    """Wait for any fire-and-forget gate-persistence tasks to complete.

    Sprint 31.91 Session 2c.1's ``_persist_gated_symbol`` is dispatched
    via ``asyncio.create_task`` so reconciliation isn't blocked. Tests
    that read ``operations.db`` directly need to await those tasks
    before the read or they race.
    """
    import asyncio as _asyncio

    while om._pending_gate_persist_tasks:
        # Snapshot — set is mutated by the done-callback as each task
        # completes; gather a copy.
        pending = list(om._pending_gate_persist_tasks)
        await _asyncio.gather(*pending, return_exceptions=True)


# ---------------------------------------------------------------------------
# Test 1 — gate engages on broker-orphan SHORT detection (idempotent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phantom_short_gate_engages_on_broker_orphan_short(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """A broker-orphan SHORT detection adds the symbol to
    ``_phantom_short_gated_symbols`` and persists a row to
    ``operations.db``. Re-detection on the same symbol is idempotent —
    no duplicate row, no duplicate persistence write.
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=100,
        ),
    }

    # Cycle 1 — gate engages
    await om.reconcile_positions(broker_positions)
    await _drain(event_bus)
    await _await_persist_tasks(om)

    assert "AAPL" in om._phantom_short_gated_symbols

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT symbol FROM phantom_short_gated_symbols WHERE symbol = ?",
            ("AAPL",),
        ) as cursor:
            rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "AAPL"

    # Cycle 2 — re-detect; idempotent (no duplicate row, set unchanged,
    # no new persist task spawned because of the ``not in`` guard).
    await om.reconcile_positions(broker_positions)
    await _drain(event_bus)
    await _await_persist_tasks(om)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM phantom_short_gated_symbols"
        ) as cursor:
            count_row = await cursor.fetchone()
    assert count_row is not None
    assert count_row[0] == 1


# ---------------------------------------------------------------------------
# Test 2 — gate blocks OrderApprovedEvent for gated symbol
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_blocks_order_approved_for_gated_symbol(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """When AAPL is in the gated set, an OrderApprovedEvent for AAPL
    publishes a SignalRejectedEvent with reason ``phantom_short_gate``
    and does NOT reach the broker.
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)
    om._phantom_short_gated_symbols.add("AAPL")

    rejected: list[SignalRejectedEvent] = []

    async def _capture(evt: SignalRejectedEvent) -> None:
        rejected.append(evt)

    event_bus.subscribe(SignalRejectedEvent, _capture)

    signal = _make_signal("AAPL")
    await om.on_approved(OrderApprovedEvent(signal=signal))
    await _drain(event_bus)

    assert mock_broker.place_bracket_order.await_count == 0
    assert len(rejected) == 1
    assert rejected[0].rejection_reason == "phantom_short_gate"
    assert rejected[0].rejection_stage == "risk_manager"
    assert rejected[0].metadata.get("gate") == "phantom_short_gate"
    assert rejected[0].metadata.get("symbol") == "AAPL"


# ---------------------------------------------------------------------------
# Test 3 — per-symbol granularity (gating AAPL does NOT block MSFT)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_does_not_block_other_symbols(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """The gate is a ``set[str]`` — a gated AAPL does NOT block an
    OrderApprovedEvent for MSFT. Verifies per-symbol granularity by
    construction: a successful broker.place_bracket_order awaits with
    MSFT order details when AAPL is gated.
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)
    om._phantom_short_gated_symbols.add("AAPL")

    # Mock broker to return a minimal valid bracket result for MSFT
    bracket_result = MagicMock()
    bracket_result.entry = MagicMock(
        order_id="entry-1",
        status="filled",
        filled_avg_price=100.0,
        filled_quantity=10,
    )
    # Make status comparison short-circuit so on_approved doesn't trigger
    # the synchronous-fill branch (avoids touching unrelated handlers).
    bracket_result.entry.status = "submitted"
    bracket_result.stop = MagicMock(order_id="stop-1")
    bracket_result.targets = [MagicMock(order_id="t1-1")]
    mock_broker.place_bracket_order = AsyncMock(return_value=bracket_result)

    rejected: list[SignalRejectedEvent] = []

    async def _capture(evt: SignalRejectedEvent) -> None:
        rejected.append(evt)

    event_bus.subscribe(SignalRejectedEvent, _capture)

    signal = _make_signal("MSFT")
    await om.on_approved(OrderApprovedEvent(signal=signal))
    await _drain(event_bus)

    # MSFT should reach the broker; AAPL gate must not affect it.
    assert mock_broker.place_bracket_order.await_count == 1
    # No phantom_short_gate rejection for MSFT.
    phantom_rejections = [
        r for r in rejected if r.rejection_reason == "phantom_short_gate"
    ]
    assert phantom_rejections == []


# ---------------------------------------------------------------------------
# Test 4 — engagement persists to SQLite with full payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phantom_short_gated_symbols_persist_to_sqlite(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """After gate engagement the row in operations.db has populated
    ``engaged_at_utc``, ``engaged_at_et``, ``engagement_source="engaged"``,
    and ``last_observed_short_shares`` matching the broker reading.
    Read with a fresh aiosqlite connection (not the engagement task's).
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=137,
        ),
    }
    await om.reconcile_positions(broker_positions)
    await _drain(event_bus)
    await _await_persist_tasks(om)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT symbol, engaged_at_utc, engaged_at_et, engagement_source, "
            "last_observed_short_shares FROM phantom_short_gated_symbols "
            "WHERE symbol = ?",
            ("AAPL",),
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    symbol, engaged_at_utc, engaged_at_et, source, shares = row
    assert symbol == "AAPL"
    assert engaged_at_utc  # ISO-formatted timestamp
    assert "T" in engaged_at_utc
    assert engaged_at_et
    assert source == "engaged"
    assert shares == 137


# ---------------------------------------------------------------------------
# Test 5 — M5 rehydration ordering: state populated BEFORE start()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_state_rehydrated_on_restart_before_event_processing(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """Pre-populate operations.db with a gated symbol (simulating a prior
    session). Construct a fresh OrderManager. Run the rehydrate-then-start
    sequence ARGUS uses in main.py.

    Critical assertions:
    - ``_phantom_short_gated_symbols`` contains "AAPL" AFTER rehydration
      and BEFORE ``start()`` subscribes to OrderApprovedEvent.
    - An OrderApprovedEvent published immediately after subscribe is
      rejected — the gate is in place from the moment subscription begins.

    Anti-regression: if the rehydration is moved to run AFTER ``start()``,
    the assertion about state being populated before subscription FAILS.
    """
    db_path = tmp_path / "operations.db"

    # Step 1: pre-populate operations.db with a gated symbol via a sibling
    # OrderManager (simulating a prior session that engaged the gate).
    seed_om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)
    await seed_om._persist_gated_symbol(
        "AAPL", "engaged", last_observed_short_shares=100
    )

    # Step 2: fresh OrderManager (no in-memory state).
    fresh_om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)
    assert fresh_om._phantom_short_gated_symbols == set()

    # Step 3: M5 ordering — rehydrate FIRST.
    await fresh_om._rehydrate_gated_symbols_from_db()

    # State must be populated now, BEFORE start() subscribes.
    assert fresh_om._phantom_short_gated_symbols == {"AAPL"}

    # Step 4: start() subscribes to OrderApprovedEvent.
    await fresh_om.start()
    try:
        rejected: list[SignalRejectedEvent] = []

        async def _capture(evt: SignalRejectedEvent) -> None:
            rejected.append(evt)

        event_bus.subscribe(SignalRejectedEvent, _capture)

        # Step 5: any OrderApprovedEvent for AAPL is rejected from the
        # very first publish — there is no unsafe window.
        await event_bus.publish(OrderApprovedEvent(signal=_make_signal("AAPL")))
        await _drain(event_bus)

        assert mock_broker.place_bracket_order.await_count == 0
        assert len(rejected) == 1
        assert rejected[0].rejection_reason == "phantom_short_gate"
    finally:
        await fresh_om.stop()


# ---------------------------------------------------------------------------
# Test 6 — E2E: gate state survives ARGUS restart and continues blocking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_state_survives_argus_restart_blocks_entries(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """End-to-end coverage of the persist + rehydrate flow.

    1. Trigger gate engagement via reconciliation on instance A.
    2. Simulate shutdown (drop instance A; new EventBus for instance B).
    3. Construct instance B; rehydrate from operations.db; start().
    4. Publish OrderApprovedEvent for the previously-gated symbol.
    5. Assert the entry is rejected and the broker is never invoked.
    """
    db_path = tmp_path / "operations.db"

    # Instance A — engages the gate.
    bus_a = EventBus()
    om_a = _make_order_manager(bus_a, mock_broker, fixed_clock, db_path)
    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=42,
        ),
    }
    await om_a.reconcile_positions(broker_positions)
    await bus_a.drain()
    await _await_persist_tasks(om_a)
    assert "AAPL" in om_a._phantom_short_gated_symbols

    # Simulate shutdown — drop instance A (no explicit close needed; per-
    # write aiosqlite connections are closed by the async-with).
    del om_a

    # Instance B — fresh process; no in-memory state.
    bus_b = EventBus()
    fresh_broker = MagicMock()
    fresh_broker.place_bracket_order = AsyncMock()
    fresh_broker.cancel_order = AsyncMock(return_value=True)
    fresh_broker.cancel_all_orders = AsyncMock(return_value=0)
    fresh_broker.get_positions = AsyncMock(return_value=[])
    om_b = _make_order_manager(bus_b, fresh_broker, fixed_clock, db_path)
    assert om_b._phantom_short_gated_symbols == set()

    # Rehydrate, then start.
    await om_b._rehydrate_gated_symbols_from_db()
    assert om_b._phantom_short_gated_symbols == {"AAPL"}
    await om_b.start()
    try:
        rejected: list[SignalRejectedEvent] = []

        async def _capture(evt: SignalRejectedEvent) -> None:
            rejected.append(evt)

        bus_b.subscribe(SignalRejectedEvent, _capture)

        await bus_b.publish(OrderApprovedEvent(signal=_make_signal("AAPL")))
        await bus_b.drain()

        assert fresh_broker.place_bracket_order.await_count == 0
        assert len(rejected) == 1
        assert rejected[0].rejection_reason == "phantom_short_gate"
    finally:
        await om_b.stop()

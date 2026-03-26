"""Tests for reconciliation redesign — broker-confirmed tracking + miss counter.

Sprint 27.95 Session 1a: Verifies broker-confirmed positions are never
auto-closed, unconfirmed positions require consecutive misses before cleanup,
miss counters reset on snapshot presence, and config fields are recognized.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, ReconciliationConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    ExitReason,
    OrderApprovedEvent,
    PositionClosedEvent,
    Side,
    SignalEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
    OrderManager,
    PendingManagedOrder,
)
from argus.models.trading import BracketOrderResult, OrderResult, OrderStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock()
    order_counter = {"count": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["count"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['count']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        order_counter["count"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['count']}",
            status=OrderStatus.PENDING,
        )
        target_results = []
        for target in targets:
            order_counter["count"] += 1
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{order_counter['count']}",
                    status=OrderStatus.PENDING,
                )
            )
        return BracketOrderResult(
            entry=entry_result, stop=stop_result, targets=target_results
        )

    def make_flatten_result(order: MagicMock) -> OrderResult:
        order_counter["count"] += 1
        return OrderResult(
            order_id=f"flatten-{order_counter['count']}",
            broker_order_id=f"broker-flatten-{order_counter['count']}",
            status=OrderStatus.SUBMITTED,
        )

    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    broker.place_order = AsyncMock(side_effect=make_flatten_result)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=3)
    broker.get_positions = AsyncMock(return_value=[])
    return broker


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 3, 26, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def config() -> OrderManagerConfig:
    return OrderManagerConfig()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
) -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Test signal",
        time_stop_seconds=300,
    )


def _make_om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
    recon_config: ReconciliationConfig | None = None,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        reconciliation_config=recon_config or ReconciliationConfig(),
    )


async def _open_position(
    om: OrderManager,
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
) -> None:
    """Submit an approved signal and get a managed position via entry fill."""
    await om.start()
    signal = _make_signal(symbol=symbol, strategy_id=strategy_id)
    approved = OrderApprovedEvent(signal=signal)
    await om.on_approved(approved)


def _inject_unconfirmed_position(
    om: OrderManager,
    symbol: str = "GHOST",
    strategy_id: str = "orb_breakout",
    clock: FixedClock | None = None,
) -> ManagedPosition:
    """Inject a position directly into managed_positions WITHOUT setting broker_confirmed."""
    entry_time = clock.now() if clock else datetime(2026, 3, 26, 15, 0, 0, tzinfo=UTC)
    pos = ManagedPosition(
        symbol=symbol,
        strategy_id=strategy_id,
        entry_price=150.0,
        entry_time=entry_time,
        shares_total=100,
        shares_remaining=100,
        stop_price=148.0,
        original_stop_price=148.0,
        stop_order_id="stop-ghost",
        t1_price=152.0,
        t1_order_id="t1-ghost",
        t1_shares=50,
        t1_filled=False,
        t2_price=154.0,
        high_watermark=150.0,
    )
    if symbol not in om._managed_positions:
        om._managed_positions[symbol] = []
    om._managed_positions[symbol].append(pos)
    return pos


# ---------------------------------------------------------------------------
# Test 1: Confirmed position NOT cleaned up when missing from snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_position_not_cleaned_on_snapshot_miss(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Broker-confirmed position must NEVER be auto-closed regardless of config."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=1)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await _open_position(om)

    # Verify broker_confirmed is set
    assert om._broker_confirmed.get("AAPL") is True

    # Broker reports empty snapshot (AAPL missing)
    with caplog.at_level(logging.WARNING):
        discrepancies = await om.reconcile_positions({})

    assert len(discrepancies) == 1

    # Position must still be open
    positions = om.get_all_positions_flat()
    assert len(positions) == 1
    assert positions[0].shares_remaining == 100

    # Warning about stale snapshot logged
    warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    stale_msgs = [m for m in warning_msgs if "snapshot may be stale" in m]
    assert len(stale_msgs) == 1


# ---------------------------------------------------------------------------
# Test 2: Unconfirmed position cleaned up after N consecutive misses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unconfirmed_cleaned_after_threshold(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Unconfirmed position cleaned up after consecutive_miss_threshold misses."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=3)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await om.start()
    _inject_unconfirmed_position(om, clock=fixed_clock)

    closed_events: list[PositionClosedEvent] = []

    async def on_close(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, on_close)

    # Miss 1 and 2: not cleaned up yet
    await om.reconcile_positions({})
    await om.reconcile_positions({})
    assert len(om.get_all_positions_flat()) == 1

    # Miss 3: threshold reached, cleaned up
    await om.reconcile_positions({})
    await event_bus.drain()

    assert len(om.get_all_positions_flat()) == 0
    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.RECONCILIATION


# ---------------------------------------------------------------------------
# Test 3: Unconfirmed position NOT cleaned up before threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unconfirmed_not_cleaned_before_threshold(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unconfirmed position survives reconciliation cycles below threshold."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=5)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await om.start()
    _inject_unconfirmed_position(om, clock=fixed_clock)

    with caplog.at_level(logging.INFO):
        await om.reconcile_positions({})
        await om.reconcile_positions({})

    assert len(om.get_all_positions_flat()) == 1

    # Info log about miss count
    info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    miss_msgs = [m for m in info_msgs if "miss 1/5" in m or "miss 2/5" in m]
    assert len(miss_msgs) == 2


# ---------------------------------------------------------------------------
# Test 4: Miss counter resets when position found in snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_miss_counter_resets_on_snapshot_presence(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Miss counter resets to 0 when symbol appears in broker snapshot."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=3)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await om.start()
    _inject_unconfirmed_position(om, clock=fixed_clock)

    # Two misses
    await om.reconcile_positions({})
    await om.reconcile_positions({})
    assert om._reconciliation_miss_count.get("GHOST", 0) == 2

    # Found in snapshot (matching qty) — no mismatch, counter resets
    await om.reconcile_positions({"GHOST": 100.0})
    assert om._reconciliation_miss_count.get("GHOST", 0) == 0

    # Two more misses after reset — still below threshold
    await om.reconcile_positions({})
    await om.reconcile_positions({})
    assert len(om.get_all_positions_flat()) == 1
    assert om._reconciliation_miss_count.get("GHOST", 0) == 2


# ---------------------------------------------------------------------------
# Test 5: Mixed batch — confirmed + unconfirmed in same cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mixed_confirmed_and_unconfirmed(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Confirmed position survives while unconfirmed is cleaned up in same cycle."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=1)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)

    # Open AAPL via normal flow (broker-confirmed)
    await _open_position(om)
    assert om._broker_confirmed.get("AAPL") is True

    # Inject GHOST directly (unconfirmed)
    _inject_unconfirmed_position(om, symbol="GHOST", clock=fixed_clock)
    assert om._broker_confirmed.get("GHOST", False) is False

    closed_events: list[PositionClosedEvent] = []

    async def on_close(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, on_close)

    # Both missing from snapshot
    await om.reconcile_positions({})
    await event_bus.drain()

    # AAPL (confirmed) must survive, GHOST (unconfirmed) must be cleaned
    positions = om.get_all_positions_flat()
    symbols = [p.symbol for p in positions]
    assert "AAPL" in symbols
    assert "GHOST" not in symbols
    assert len(closed_events) == 1
    assert closed_events[0].symbol == "GHOST"


# ---------------------------------------------------------------------------
# Test 6: auto_cleanup_unconfirmed=False → warn-only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warn_only_when_cleanup_disabled(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No cleanup when both auto_cleanup_unconfirmed and auto_cleanup_orphans are False."""
    recon = ReconciliationConfig(
        auto_cleanup_orphans=False,
        auto_cleanup_unconfirmed=False,
    )
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await om.start()
    _inject_unconfirmed_position(om, clock=fixed_clock)

    with caplog.at_level(logging.WARNING):
        # Run many cycles — should never clean up
        for _ in range(10):
            await om.reconcile_positions({})

    assert len(om.get_all_positions_flat()) == 1

    # Warning about disabled cleanup
    warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    disabled_msgs = [m for m in warning_msgs if "auto-cleanup disabled" in m]
    assert len(disabled_msgs) >= 1


# ---------------------------------------------------------------------------
# Test 7: Broker-confirmed flag set on entry fill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_confirmed_set_on_entry_fill(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """_broker_confirmed[symbol] is True after entry fill callback."""
    om = _make_om(event_bus, mock_broker, fixed_clock, config)
    assert om._broker_confirmed.get("AAPL", False) is False

    await _open_position(om)

    assert om._broker_confirmed.get("AAPL") is True


# ---------------------------------------------------------------------------
# Test 8: Broker-confirmed flag cleared on position close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_confirmed_cleared_on_close(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """_broker_confirmed is cleaned up when last position for symbol closes."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=1)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await _open_position(om)
    assert "AAPL" in om._broker_confirmed

    # Close via _close_position directly (simulates a completed fill close)
    positions = om.get_all_positions_flat()
    pos = positions[0]
    pos.shares_remaining = 0
    pos.realized_pnl = 0.0
    await om._close_position(pos, exit_price=150.0, exit_reason=ExitReason.STOP_LOSS)

    # After close, broker_confirmed should be cleaned up
    assert "AAPL" not in om._broker_confirmed


# ---------------------------------------------------------------------------
# Test 9: Miss counter cleared on position close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_miss_counter_cleared_on_close(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """_reconciliation_miss_count is cleaned up when last position for symbol closes."""
    recon = ReconciliationConfig(auto_cleanup_unconfirmed=True, consecutive_miss_threshold=5)
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)
    await om.start()
    pos = _inject_unconfirmed_position(om, symbol="GHOST", clock=fixed_clock)

    # Accumulate some misses
    await om.reconcile_positions({})
    await om.reconcile_positions({})
    assert om._reconciliation_miss_count.get("GHOST", 0) == 2

    # Close via _close_position directly
    pos.shares_remaining = 0
    pos.realized_pnl = 0.0
    await om._close_position(pos, exit_price=150.0, exit_reason=ExitReason.STOP_LOSS)

    # Miss counter should be cleaned up
    assert "GHOST" not in om._reconciliation_miss_count


# ---------------------------------------------------------------------------
# Test 10: Config fields recognized by Pydantic model
# ---------------------------------------------------------------------------


def test_reconciliation_config_fields_recognized() -> None:
    """All ReconciliationConfig fields are recognized by Pydantic."""
    config = ReconciliationConfig(
        auto_cleanup_orphans=True,
        auto_cleanup_unconfirmed=True,
        consecutive_miss_threshold=5,
    )
    assert config.auto_cleanup_orphans is True
    assert config.auto_cleanup_unconfirmed is True
    assert config.consecutive_miss_threshold == 5

    # Verify model_fields contains expected keys
    expected_keys = {"auto_cleanup_orphans", "auto_cleanup_unconfirmed", "consecutive_miss_threshold"}
    assert expected_keys == set(ReconciliationConfig.model_fields.keys())


def test_reconciliation_config_threshold_ge_1() -> None:
    """consecutive_miss_threshold must be >= 1."""
    with pytest.raises(Exception):
        ReconciliationConfig(consecutive_miss_threshold=0)


def test_reconciliation_config_yaml_keys_match_model() -> None:
    """YAML config keys match ReconciliationConfig model_fields."""
    from argus.core.config import load_yaml_file
    from pathlib import Path

    yaml_path = Path("config/system_live.yaml")
    if not yaml_path.exists():
        pytest.skip("system_live.yaml not found")

    raw = load_yaml_file(yaml_path)
    recon_yaml = raw.get("reconciliation", {})

    model_keys = set(ReconciliationConfig.model_fields.keys())
    yaml_keys = set(recon_yaml.keys())

    # All YAML keys must be recognized by the model
    unrecognized = yaml_keys - model_keys
    assert not unrecognized, f"Unrecognized YAML keys: {unrecognized}"


# ---------------------------------------------------------------------------
# Test 11: Legacy auto_cleanup_orphans still works (backwards compat)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_legacy_auto_cleanup_orphans_still_works(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Legacy auto_cleanup_orphans=True still triggers immediate cleanup for unconfirmed."""
    recon = ReconciliationConfig(
        auto_cleanup_orphans=True,
        auto_cleanup_unconfirmed=False,
    )
    om = _make_om(event_bus, mock_broker, fixed_clock, config, recon)

    closed_events: list[PositionClosedEvent] = []

    async def on_close(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, on_close)

    await om.start()
    _inject_unconfirmed_position(om, clock=fixed_clock)

    # Single reconciliation cycle should clean up immediately (legacy behavior)
    await om.reconcile_positions({})
    await event_bus.drain()

    assert len(om.get_all_positions_flat()) == 0
    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.RECONCILIATION

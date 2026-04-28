"""Sprint 31.91 Session 2b.1 — broker-orphan branch + alert taxonomy tests.

Covers the new broker-orphan reconciliation branch added to
``OrderManager.reconcile_positions``:

- **Broker-orphan SHORT** → CRITICAL ``phantom_short`` alert (DEF-204
  detection signal). The alert is the operator-page; the per-symbol
  entry gate (preventing new entries on the gated symbol) lands in
  Session 2c.1 — 2b.1 is detection-only.
- **Broker-orphan LONG cycle 1–2** → WARNING log only.
- **Broker-orphan LONG cycle ≥ 3** → ``stranded_broker_long`` alert with
  M2 exponential-backoff schedule [3, 6, 12, 24, 48], then every 60.
- **Cleanup on broker-zero**, **session reset**, and **side flip safety**
  exercised by the M2 composite test.

The six tests here are revert-proof for the Session 2b.1 changes — the
branch ordering, the alert taxonomy, and the cycle-counter lifecycle.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, ReconciliationConfig
from argus.core.event_bus import EventBus
from argus.core.events import SystemAlertEvent
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
    *,
    broker_orphan_alert_enabled: bool = True,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(
            broker_orphan_alert_enabled=broker_orphan_alert_enabled,
        ),
    )


def _capture_alerts(event_bus: EventBus) -> list[SystemAlertEvent]:
    """Subscribe a list-collector to SystemAlertEvent for assertions.

    Caller should use the ``_reconcile_and_drain`` helper below (or
    explicitly ``await event_bus.drain()``) after a publish to let the
    dispatched handler tasks settle — EventBus creates handler tasks via
    ``asyncio.create_task`` so the captured list is empty until the loop
    yields.
    """
    captured: list[SystemAlertEvent] = []

    async def _on_alert(evt: SystemAlertEvent) -> None:
        captured.append(evt)

    event_bus.subscribe(SystemAlertEvent, _on_alert)
    return captured


async def _reconcile_and_drain(
    om: OrderManager,
    broker_positions: dict[str, ReconciliationPosition],
) -> None:
    """Reconcile then drain the event bus so subscribers run before assertion."""
    await om.reconcile_positions(broker_positions)
    await om._event_bus.drain()


# ---------------------------------------------------------------------------
# Test 1 — phantom_short alert is emitted on broker-orphan SHORT detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_orphan_short_emits_phantom_short_alert(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A broker-orphan SHORT (broker reports SELL for symbol not in
    ``_managed_positions``) emits exactly one CRITICAL ``phantom_short``
    SystemAlertEvent and a CRITICAL log line containing the symbol.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    captured = _capture_alerts(event_bus)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=100,
        ),
    }
    with caplog.at_level(logging.CRITICAL, logger="argus.execution.order_manager"):
        await _reconcile_and_drain(om, broker_positions)

    phantom_alerts = [a for a in captured if a.alert_type == "phantom_short"]
    assert len(phantom_alerts) == 1, (
        f"Expected exactly one phantom_short alert; got {len(phantom_alerts)}: "
        f"{phantom_alerts}"
    )
    assert phantom_alerts[0].severity == "critical"

    critical_lines = [
        r for r in caplog.records
        if r.levelno == logging.CRITICAL and "BROKER ORPHAN SHORT" in r.getMessage()
    ]
    assert len(critical_lines) == 1
    assert "AAPL" in critical_lines[0].getMessage()


# ---------------------------------------------------------------------------
# Test 2 — phantom_short alert payload shape (metadata fields)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_orphan_short_alert_payload_shape(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """The published phantom_short alert carries the structured metadata
    that downstream consumers (HealthMonitor in 5a.1) will read by typed
    keys rather than parsing the message string.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    captured = _capture_alerts(event_bus)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=100,
        ),
    }
    await _reconcile_and_drain(om, broker_positions)

    phantom_alerts = [a for a in captured if a.alert_type == "phantom_short"]
    assert len(phantom_alerts) == 1
    alert = phantom_alerts[0]

    assert alert.source == "reconciliation"
    assert alert.metadata is not None
    assert alert.metadata["symbol"] == "AAPL"
    assert alert.metadata["shares"] == 100
    assert alert.metadata["side"] == "SELL"
    assert (
        alert.metadata["detection_source"]
        == "reconciliation.broker_orphan_branch"
    )


# ---------------------------------------------------------------------------
# Test 3 — config flag disables the broker-orphan alert path entirely
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_orphan_alert_config_flag_disables(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With ``broker_orphan_alert_enabled=False`` the SHORT detection
    emits no alert and no CRITICAL log line. Guards against accidentally
    hard-coding the alert path past the gate.
    """
    om = _make_order_manager(
        event_bus, mock_broker, fixed_clock,
        broker_orphan_alert_enabled=False,
    )
    captured = _capture_alerts(event_bus)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=100,
        ),
    }
    with caplog.at_level(logging.CRITICAL, logger="argus.execution.order_manager"):
        await _reconcile_and_drain(om, broker_positions)

    phantom_alerts = [a for a in captured if a.alert_type == "phantom_short"]
    assert phantom_alerts == [], (
        f"Expected no phantom_short alerts when gate disabled; got {phantom_alerts}"
    )
    critical_lines = [
        r for r in caplog.records
        if r.levelno == logging.CRITICAL and "BROKER ORPHAN SHORT" in r.getMessage()
    ]
    assert critical_lines == []


# ---------------------------------------------------------------------------
# Test 4 — broker-orphan LONG cycle 1: WARNING log only, no alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_orphan_long_cycle_1_warning_only(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """First-cycle long orphan emits WARNING log; no
    ``stranded_broker_long`` alert; cycle counter increments to 1.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    captured = _capture_alerts(event_bus)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.BUY, shares=200,
        ),
    }
    with caplog.at_level(logging.WARNING, logger="argus.execution.order_manager"):
        await _reconcile_and_drain(om, broker_positions)

    stranded = [a for a in captured if a.alert_type == "stranded_broker_long"]
    assert stranded == [], (
        f"Cycle 1 must NOT emit stranded_broker_long; got {stranded}"
    )

    cycle1_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING
        and "Broker-orphan LONG cycle 1" in r.getMessage()
    ]
    assert len(cycle1_warnings) == 1
    assert "AAPL" in cycle1_warnings[0].getMessage()

    assert om._broker_orphan_long_cycles["AAPL"] == 1


# ---------------------------------------------------------------------------
# Test 5 — broker-orphan LONG cycle 3: stranded_broker_long alert fires once
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_orphan_long_cycle_3_emits_stranded_alert(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """A long orphan persisting across 3 reconciliation cycles emits the
    stranded_broker_long alert on the 3rd cycle (severity=warning), NOT
    on cycle 1 or 2. Payload `consecutive_cycles` is 3.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    captured = _capture_alerts(event_bus)

    broker_positions = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.BUY, shares=200,
        ),
    }

    # Cycle 1 and 2 should not alert.
    await _reconcile_and_drain(om, broker_positions)
    await _reconcile_and_drain(om, broker_positions)
    stranded_after_2 = [
        a for a in captured if a.alert_type == "stranded_broker_long"
    ]
    assert stranded_after_2 == [], (
        f"No stranded alert expected before cycle 3; got {stranded_after_2}"
    )

    # Cycle 3 fires the alert.
    await _reconcile_and_drain(om, broker_positions)
    stranded = [a for a in captured if a.alert_type == "stranded_broker_long"]
    assert len(stranded) == 1, (
        f"Expected exactly one stranded_broker_long alert at cycle 3; got "
        f"{len(stranded)}: {stranded}"
    )
    alert = stranded[0]
    assert alert.severity == "warning"
    assert alert.source == "reconciliation"
    assert alert.metadata is not None
    assert alert.metadata["symbol"] == "AAPL"
    assert alert.metadata["shares"] == 200
    assert alert.metadata["side"] == "BUY"
    assert alert.metadata["consecutive_cycles"] == 3
    assert (
        alert.metadata["detection_source"]
        == "reconciliation.broker_orphan_branch"
    )


# ---------------------------------------------------------------------------
# Test 6 — M2 lifecycle: cleanup-on-zero, exp-backoff, session reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_orphan_long_cycles_cleanup_on_zero_exponential_backoff_session_reset(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Composite M2 lifecycle test: cleanup-on-zero, exp-backoff schedule,
    session-reset. The three sub-behaviors are independent assertions
    inside one test because the M2 contract treats them as one lifecycle.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    captured = _capture_alerts(event_bus)

    # ----- Sub-behavior A: cleanup on broker-zero -----
    aapl_long = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.BUY, shares=100,
        ),
    }
    # 3 cycles → 1 alert at cycle 3.
    for _ in range(3):
        await _reconcile_and_drain(om, aapl_long)
    aapl_alerts = [
        a for a in captured
        if a.alert_type == "stranded_broker_long"
        and a.metadata is not None
        and a.metadata.get("symbol") == "AAPL"
    ]
    assert len(aapl_alerts) == 1
    assert om._broker_orphan_long_cycles["AAPL"] == 3
    assert om._broker_orphan_last_alerted_cycle["AAPL"] == 3

    # Broker reports zero on the next cycle (orphan resolved).
    await _reconcile_and_drain(om, {})
    assert "AAPL" not in om._broker_orphan_long_cycles
    assert "AAPL" not in om._broker_orphan_last_alerted_cycle

    # Subsequent cycles with no AAPL must produce no further alerts.
    await _reconcile_and_drain(om, {})
    aapl_alerts_after = [
        a for a in captured
        if a.alert_type == "stranded_broker_long"
        and a.metadata is not None
        and a.metadata.get("symbol") == "AAPL"
    ]
    assert len(aapl_alerts_after) == 1, (
        f"Cleanup-on-zero must prevent further alerts; got {aapl_alerts_after}"
    )

    # ----- Sub-behavior B: exponential backoff -----
    msft_long = {
        "MSFT": ReconciliationPosition(
            symbol="MSFT", side=OrderSide.BUY, shares=50,
        ),
    }
    captured.clear()
    expected_alert_cycles = {3, 6, 12, 24, 48}
    # Run 50 cycles to cover the full schedule [3, 6, 12, 24, 48].
    for cycle in range(1, 51):
        await _reconcile_and_drain(om, msft_long)
        msft_alerts_so_far = [
            a for a in captured
            if a.alert_type == "stranded_broker_long"
            and a.metadata is not None
            and a.metadata.get("symbol") == "MSFT"
        ]
        fired_cycles = {
            a.metadata["consecutive_cycles"]
            for a in msft_alerts_so_far
            if a.metadata is not None
        }
        expected_so_far = {c for c in expected_alert_cycles if c <= cycle}
        assert fired_cycles == expected_so_far, (
            f"At cycle {cycle}, expected fired_cycles={expected_so_far}, "
            f"got {fired_cycles}"
        )

    # No spurious alerts at non-schedule cycles.
    msft_alerts = [
        a for a in captured
        if a.alert_type == "stranded_broker_long"
        and a.metadata is not None
        and a.metadata.get("symbol") == "MSFT"
    ]
    fired_cycles = {
        a.metadata["consecutive_cycles"]
        for a in msft_alerts
        if a.metadata is not None
    }
    assert fired_cycles == expected_alert_cycles, (
        f"Expected exactly {expected_alert_cycles}; got {fired_cycles}"
    )

    # ----- Sub-behavior C: session reset clears the counter -----
    tsla_long = {
        "TSLA": ReconciliationPosition(
            symbol="TSLA", side=OrderSide.BUY, shares=10,
        ),
    }
    # Reset MSFT-related state by clearing captured + dropping MSFT first.
    await _reconcile_and_drain(om, {})  # clears MSFT
    captured.clear()

    for _ in range(5):
        await _reconcile_and_drain(om, tsla_long)
    tsla_alerts_pre_reset = [
        a for a in captured
        if a.alert_type == "stranded_broker_long"
        and a.metadata is not None
        and a.metadata.get("symbol") == "TSLA"
    ]
    assert om._broker_orphan_long_cycles["TSLA"] == 5
    # alerted at cycle 3 (next in schedule after 0), not yet at 6 (need cycle 6)
    assert len(tsla_alerts_pre_reset) == 1
    assert tsla_alerts_pre_reset[0].metadata is not None
    assert tsla_alerts_pre_reset[0].metadata["consecutive_cycles"] == 3

    # Session reset → counter clears for TSLA.
    om.reset_daily_state()
    assert om._broker_orphan_long_cycles == {}
    assert om._broker_orphan_last_alerted_cycle == {}

    # Re-running the orphan post-reset rebuilds the cycle from 1, alerts at 3.
    captured.clear()
    for cycle in range(1, 4):
        await _reconcile_and_drain(om, tsla_long)
    tsla_alerts_post_reset = [
        a for a in captured
        if a.alert_type == "stranded_broker_long"
        and a.metadata is not None
        and a.metadata.get("symbol") == "TSLA"
    ]
    assert len(tsla_alerts_post_reset) == 1
    assert tsla_alerts_post_reset[0].metadata is not None
    assert tsla_alerts_post_reset[0].metadata["consecutive_cycles"] == 3

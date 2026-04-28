"""Sprint 31.91 Session 2b.2 — Pattern A.1 (margin circuit reset) + Pattern B (EOD Pass 2 phantom_short alert).

Pattern A.1: side-aware count filter at the margin-circuit auto-reset
site in ``OrderManager._poll_loop``. Phantom shorts (DEF-204) must not
inflate the broker-position count and prevent the circuit from
resetting once long positions have cleared below the configured
threshold.

Pattern B: alert taxonomy alignment at the EOD Pass 2 short-detection
site. The existing ``logger.error`` "DETECTED UNEXPECTED SHORT
POSITION" line is preserved (DEF-199 A1 fix); a ``phantom_short``
``SystemAlertEvent`` is emitted alongside it so Session 5a.2's
auto-resolution policy table consumes alerts uniformly across all
detection sites (reconciliation orphan branch, Health integrity check,
EOD Pass 2).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, StartupConfig
from argus.core.event_bus import EventBus
from argus.core.events import SystemAlertEvent
from argus.execution.order_manager import OrderManager
from argus.models.trading import OrderResult, OrderSide, OrderStatus, Position


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_hours_clock() -> FixedClock:
    """11 AM ET = 15:00 UTC, weekday."""
    return FixedClock(datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC))


def _make_broker_position(
    symbol: str, shares: int, side: OrderSide = OrderSide.BUY,
) -> MagicMock:
    pos = MagicMock(spec=Position)
    pos.symbol = symbol
    pos.shares = shares
    pos.side = side
    return pos


def _make_broker() -> MagicMock:
    broker = MagicMock()
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="flatten-1",
            broker_order_id="broker-flatten-1",
            status=OrderStatus.PENDING,
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_open_orders = AsyncMock(return_value=[])
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    return broker


def _make_om(
    event_bus: EventBus,
    broker: MagicMock,
    clock: FixedClock,
    *,
    margin_circuit_reset_positions: int = 20,
    fallback_poll_interval_seconds: int = 1,
) -> OrderManager:
    config = OrderManagerConfig(
        margin_rejection_threshold=10,
        margin_circuit_reset_positions=margin_circuit_reset_positions,
        fallback_poll_interval_seconds=fallback_poll_interval_seconds,
        eod_flatten_timeout_seconds=2,
        auto_shutdown_after_eod=False,
        eod_flatten_retry_rejected=False,
    )
    return OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=config,
        startup_config=StartupConfig(flatten_unknown_positions=False),
    )


def _capture_alerts(event_bus: EventBus) -> list[SystemAlertEvent]:
    captured: list[SystemAlertEvent] = []

    async def _on_alert(evt: SystemAlertEvent) -> None:
        captured.append(evt)

    event_bus.subscribe(SystemAlertEvent, _on_alert)
    return captured


# ---------------------------------------------------------------------------
# Pattern A.1 — Margin circuit reset (count filter)
# ---------------------------------------------------------------------------


class TestPatternA1MarginCircuitReset:
    """The margin-circuit reset must count only LONG positions.

    Phantom shorts (DEF-204) inflate the raw broker-position count and
    historically blocked the auto-reset. After Pattern A.1, only longs
    count toward the reset threshold.
    """

    @pytest.mark.asyncio
    async def test_margin_circuit_reset_uses_longs_only(self) -> None:
        """REVERT-PROOF: 18 longs + 5 shorts must RESET (longs=18 < 20).

        Reverting Pattern A.1 makes ``len(positions)=23`` block the reset;
        this test fails because ``_margin_circuit_open`` stays True.
        """
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        positions = [
            _make_broker_position(f"LONG{i}", 100, side=OrderSide.BUY) for i in range(18)
        ] + [
            _make_broker_position(f"SHORT{i}", 50, side=OrderSide.SELL) for i in range(5)
        ]
        broker.get_positions = AsyncMock(return_value=positions)

        om = _make_om(event_bus, broker, clock, margin_circuit_reset_positions=20)
        om._margin_circuit_open = True
        om._margin_rejection_count = 15
        om._flattened_today = True  # block EOD path

        await om.start()
        try:
            await asyncio.sleep(1.5)  # one full poll cycle
        finally:
            await om.stop()

        assert om._margin_circuit_open is False, (
            "Margin circuit should RESET when long_count=18 < threshold=20, "
            "ignoring the 5 phantom shorts."
        )
        assert om._margin_rejection_count == 0

    @pytest.mark.asyncio
    async def test_margin_circuit_reset_logs_breakdown(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Operator-facing breakdown line: longs / shorts / threshold / will_reset."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        positions = [
            _make_broker_position(f"LONG{i}", 100, side=OrderSide.BUY) for i in range(18)
        ] + [
            _make_broker_position(f"SHORT{i}", 50, side=OrderSide.SELL) for i in range(5)
        ]
        broker.get_positions = AsyncMock(return_value=positions)

        om = _make_om(event_bus, broker, clock, margin_circuit_reset_positions=20)
        om._margin_circuit_open = True
        om._margin_rejection_count = 15
        om._flattened_today = True

        with caplog.at_level(logging.INFO, logger="argus.execution.order_manager"):
            await om.start()
            try:
                await asyncio.sleep(1.5)
            finally:
                await om.stop()

        breakdown_lines = [
            r.getMessage() for r in caplog.records
            if "Margin circuit reset check" in r.getMessage()
        ]
        assert breakdown_lines, "Expected an INFO breakdown line at the reset site"
        msg = breakdown_lines[0]
        assert "longs=18" in msg
        assert "shorts=5" in msg
        assert "reset_threshold=20" in msg
        assert "will_reset=True" in msg

    @pytest.mark.asyncio
    async def test_margin_circuit_reset_blocked_when_longs_above_threshold(self) -> None:
        """Non-regression: the side filter does not over-eagerly reset.

        Setup: 25 longs + 5 shorts; threshold 20. ``len(longs)=25 >= 20``
        so the circuit must stay open. This guards against an inverted
        comparator after the refactor.
        """
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        positions = [
            _make_broker_position(f"LONG{i}", 100, side=OrderSide.BUY) for i in range(25)
        ] + [
            _make_broker_position(f"SHORT{i}", 50, side=OrderSide.SELL) for i in range(5)
        ]
        broker.get_positions = AsyncMock(return_value=positions)

        om = _make_om(event_bus, broker, clock, margin_circuit_reset_positions=20)
        om._margin_circuit_open = True
        om._margin_rejection_count = 15
        om._flattened_today = True

        await om.start()
        try:
            await asyncio.sleep(1.5)
        finally:
            await om.stop()

        assert om._margin_circuit_open is True


# ---------------------------------------------------------------------------
# Pattern B — EOD Pass 2 short detection emits phantom_short alert
# ---------------------------------------------------------------------------


class TestPatternBEodPass2PhantomShortAlert:
    """The existing ``logger.error`` is preserved; a ``phantom_short``
    ``SystemAlertEvent`` is emitted alongside it.

    Cross-references DEF-199 (the side-check that REFUSES to flatten
    the short — preserved) and DEF-204 (the phantom_short taxonomy).
    """

    @pytest.mark.asyncio
    async def test_eod_pass2_short_emits_phantom_short_alert_alongside_logger_error(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """REVERT-PROOF: Pass 2 SELL detection emits BOTH the logger.error
        AND a ``phantom_short`` SystemAlertEvent. The DEF-199 A1 protection
        is preserved (no SELL placed)."""
        event_bus = EventBus()
        captured = _capture_alerts(event_bus)

        broker = _make_broker()
        short_pos = _make_broker_position("FAKE", shares=100, side=OrderSide.SELL)
        broker.get_positions = AsyncMock(side_effect=[
            [short_pos],  # Pass 2 query
            [short_pos],  # post-verify (still there — we did NOT auto-cover)
        ])
        clock = _market_hours_clock()

        om = _make_om(event_bus, broker, clock)

        with caplog.at_level(logging.ERROR, logger="argus.execution.order_manager"):
            await om.eod_flatten()
            await event_bus.drain()

        # 1. DEF-199 A1 fix preserved — no SELL placed
        broker.place_order.assert_not_called()

        # 2. Existing logger.error fires
        short_errors = [
            r for r in caplog.records
            if r.levelno == logging.ERROR
            and "FAKE" in r.getMessage()
            and "SHORT" in r.getMessage().upper()
        ]
        assert short_errors, (
            "Expected the existing 'DETECTED UNEXPECTED SHORT POSITION' "
            "ERROR log line for FAKE."
        )

        # 3. NEW: phantom_short SystemAlertEvent published
        phantom_alerts = [
            a for a in captured
            if a.alert_type == "phantom_short" and a.source == "eod_flatten"
        ]
        assert len(phantom_alerts) == 1, (
            f"Expected exactly 1 phantom_short alert from eod_flatten; got: "
            f"{[(a.alert_type, a.source) for a in captured]}"
        )
        alert = phantom_alerts[0]
        assert alert.severity == "critical"
        assert "FAKE" in alert.message
        assert alert.metadata is not None
        assert alert.metadata["symbol"] == "FAKE"
        assert alert.metadata["shares"] == 100
        assert alert.metadata["side"] == "SELL"
        assert alert.metadata["detection_source"] == "eod_flatten.pass2"

    @pytest.mark.asyncio
    async def test_eod_pass2_long_does_not_emit_phantom_short_alert(self) -> None:
        """Non-regression: a BUY-side untracked position triggers a SELL
        flatten and does NOT emit a phantom_short alert (it is not phantom)."""
        event_bus = EventBus()
        captured = _capture_alerts(event_bus)

        broker = _make_broker()
        long_pos = _make_broker_position("REAL", shares=50, side=OrderSide.BUY)
        broker.get_positions = AsyncMock(side_effect=[
            [long_pos],
            [],
        ])
        clock = _market_hours_clock()

        om = _make_om(event_bus, broker, clock)

        await om.eod_flatten()
        await event_bus.drain()

        # Long was flattened
        broker.place_order.assert_called_once()

        # No phantom_short alert
        phantom_alerts = [
            a for a in captured if a.alert_type == "phantom_short"
        ]
        assert phantom_alerts == [], (
            "phantom_short alert should not fire for a long position"
        )

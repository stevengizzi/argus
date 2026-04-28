"""Sprint 31.91 Session 5a.1 (DEF-214) — EOD flatten verification.

Apr 27 paper-session debrief Finding 1 documented a synchronous-poll
false-positive CRITICAL at the EOD post-flatten verification site. The
prior code polled once at the same wall-clock second as flatten-order
submission, BEFORE fills completed, and conflated:

- Longs whose flatten was in flight (potentially failing, but not yet).
- Broker-only SHORTs that ARGUS intentionally does NOT flatten
  (Sprint 30 short-selling deferred; Sprint 31.91 Session 2b.1's
  ``phantom_short`` posture is alert-and-skip).

The fix replaces the synchronous poll with poll-until-flat-with-timeout
+ side-aware classification + distinct alert paths
(``eod_residual_shorts`` WARNING vs. ``eod_flatten_failed`` CRITICAL).

These tests exercise the four scenarios from the prompt's Requirement
0.5.3 acceptance criteria.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, StartupConfig
from argus.core.event_bus import EventBus
from argus.core.events import SystemAlertEvent
from argus.execution.order_manager import OrderManager
from argus.models.trading import (
    OrderResult,
    OrderSide,
    OrderStatus,
    Position,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_hours_clock() -> FixedClock:
    return FixedClock(datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC))


def _make_broker_position(
    symbol: str, shares: int, side: OrderSide
) -> MagicMock:
    pos = MagicMock(spec=Position)
    pos.symbol = symbol
    pos.shares = shares
    pos.side = side
    return pos


def _make_broker(positions_chain: list[list[MagicMock]]) -> MagicMock:
    """Build a broker mock whose ``get_positions()`` returns successive
    snapshots from ``positions_chain``. The last entry repeats indefinitely
    if more calls are made (poll loops can over-call)."""

    iterator = iter(positions_chain)
    last_snapshot: list[MagicMock] = []

    async def _get_positions() -> list[MagicMock]:
        nonlocal last_snapshot
        try:
            last_snapshot = next(iterator)
        except StopIteration:
            pass
        return last_snapshot

    broker = MagicMock()
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="o-1",
            broker_order_id="b-1",
            status=OrderStatus.PENDING,
        )
    )
    broker.get_positions = AsyncMock(side_effect=_get_positions)
    broker.get_open_orders = AsyncMock(return_value=[])
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    return broker


def _make_om(
    broker: MagicMock,
    clock: FixedClock,
    *,
    verify_timeout: float = 5.0,
    verify_poll_interval: float = 0.5,
) -> OrderManager:
    config = OrderManagerConfig(
        eod_flatten_timeout_seconds=1,
        eod_flatten_retry_rejected=False,
        auto_shutdown_after_eod=False,
    )
    # Pydantic validators on ``OrderManagerConfig`` enforce production
    # bounds (timeout ≥ 5s, poll ≥ 0.5s). Tests need shorter values to
    # keep wall-clock cost down, so we patch them post-construction.
    object.__setattr__(config, "eod_verify_timeout_seconds", verify_timeout)
    object.__setattr__(
        config, "eod_verify_poll_interval_seconds", verify_poll_interval
    )
    return OrderManager(
        event_bus=EventBus(),
        broker=broker,
        clock=clock,
        config=config,
        startup_config=StartupConfig(flatten_unknown_positions=True),
    )


def _make_managed_position(symbol: str, shares: int):
    """Construct a minimally-valid ManagedPosition for tests."""
    from argus.execution.order_manager import ManagedPosition

    return ManagedPosition(
        symbol=symbol,
        strategy_id="test",
        entry_price=50.0,
        entry_time=datetime.now(UTC),
        shares_total=shares,
        shares_remaining=shares,
        stop_price=48.0,
        original_stop_price=48.0,
        stop_order_id=None,
        t1_price=51.0,
        t1_order_id=None,
        t1_shares=shares // 2,
        t1_filled=False,
        t2_price=52.0,
        high_watermark=50.0,
    )


def _captured_alerts(om: OrderManager) -> list[SystemAlertEvent]:
    """Subscribe a capture-handler before driving eod_flatten().

    Returns a mutable list the test can inspect after the await.
    """
    captured: list[SystemAlertEvent] = []

    async def handler(event: SystemAlertEvent) -> None:
        captured.append(event)

    om._event_bus.subscribe(SystemAlertEvent, handler)
    return captured


# ---------------------------------------------------------------------------
# Scenario 1 — Clean: no longs, no shorts → INFO log only, no alert.
# ---------------------------------------------------------------------------


class TestEodVerifyClean:
    @pytest.mark.asyncio
    async def test_eod_verify_clean_no_alert(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        broker = _make_broker(
            positions_chain=[
                [],  # Pass 2 broker query (no untracked)
                [],  # Verify poll #1
            ]
        )
        om = _make_om(broker, _market_hours_clock())
        captured = _captured_alerts(om)

        with caplog.at_level(logging.INFO, logger="argus.execution.order_manager"):
            await om.eod_flatten()
        await om._event_bus.drain()

        assert captured == [], (
            f"Expected no SystemAlertEvent on clean EOD; got: "
            f"{[(a.alert_type, a.severity) for a in captured]}"
        )
        # Verify INFO log fires.
        info_msgs = [
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.INFO
        ]
        assert any(
            "EOD flatten verification complete" in m
            for m in info_msgs
        )


# ---------------------------------------------------------------------------
# Scenario 2 — Residual shorts only → eod_residual_shorts WARNING.
# ---------------------------------------------------------------------------


class TestEodVerifyResidualShorts:
    @pytest.mark.asyncio
    async def test_eod_verify_residual_shorts_warning(self) -> None:
        short_pos = _make_broker_position("FAKE", 200, OrderSide.SELL)
        # Pass 2 sees the short; Pass 2 will NOT SELL it (DEF-199 fix).
        # Verify poll sees the short still there but no failed longs → break.
        broker = _make_broker(
            positions_chain=[
                [short_pos],  # Pass 2 broker query
                [short_pos],  # Verify poll #1
            ]
        )
        om = _make_om(broker, _market_hours_clock())
        captured = _captured_alerts(om)

        await om.eod_flatten()
        await om._event_bus.drain()

        assert len(captured) >= 1
        residual = [a for a in captured if a.alert_type == "eod_residual_shorts"]
        assert len(residual) == 1
        evt = residual[0]
        assert evt.severity == "warning"
        assert evt.metadata is not None
        assert evt.metadata["category"] == "expected_residue"
        assert evt.metadata["count"] == 1
        assert "FAKE" in evt.metadata["residual_short_symbols"]

        # No actual-failure CRITICAL.
        failures = [a for a in captured if a.alert_type == "eod_flatten_failed"]
        assert failures == []


# ---------------------------------------------------------------------------
# Scenario 3 — Failed longs → eod_flatten_failed CRITICAL + logger.critical.
# ---------------------------------------------------------------------------


class TestEodVerifyFailedLongs:
    @pytest.mark.asyncio
    async def test_eod_verify_failed_longs_critical(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # We need a managed position whose symbol persists at the broker
        # past the verify timeout. Using a short verify_timeout (0.1s) so
        # the test runs fast.
        long_at_broker = _make_broker_position("STUCK", 100, OrderSide.BUY)
        broker = _make_broker(
            positions_chain=[
                [long_at_broker],  # Pass 2 broker query (treated as untracked
                                   # by Pass 2, but also visible to verify)
                [long_at_broker],  # Verify poll #1
                [long_at_broker],  # Verify poll #2 (timeout)
            ]
        )
        # Set place_order so Pass 2 flatten attempt itself succeeds (returns
        # PENDING) but the position keeps appearing at broker.
        om = _make_om(
            broker,
            _market_hours_clock(),
            verify_timeout=0.2,
            verify_poll_interval=0.05,
        )

        # Manually inject a managed position so the verify path classifies
        # STUCK as a failed-long rather than a Pass-2 untracked.
        mp = _make_managed_position("STUCK", 100)
        om._managed_positions["STUCK"] = [mp]

        captured = _captured_alerts(om)

        with caplog.at_level(logging.CRITICAL, logger="argus.execution.order_manager"):
            await om.eod_flatten()
        await om._event_bus.drain()

        # Critical SystemAlertEvent fired.
        failures = [a for a in captured if a.alert_type == "eod_flatten_failed"]
        assert len(failures) == 1
        evt = failures[0]
        assert evt.severity == "critical"
        assert evt.metadata is not None
        assert evt.metadata["category"] == "actual_failure"
        assert "STUCK" in evt.metadata["failed_long_symbols"]
        assert evt.metadata["count"] == 1

        # logger.critical also called for the failure.
        critical_msgs = [
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.CRITICAL
        ]
        assert any("EOD flatten FAILURE" in m for m in critical_msgs)


# ---------------------------------------------------------------------------
# Scenario 4 — Polls until flat: longs visible for first 2 polls then absent.
# ---------------------------------------------------------------------------


class TestEodVerifyPollsUntilFlat:
    @pytest.mark.asyncio
    async def test_eod_verify_polls_until_flat(self) -> None:
        """Long that disappears mid-poll → no alert; verify exits cleanly."""
        long_at_broker = _make_broker_position("DRAIN", 50, OrderSide.BUY)
        # Pass 2 sees nothing untracked (we'll inject the managed
        # position ourselves so it isn't a Pass-2 candidate). Verify
        # polls see DRAIN at broker for #1, gone at #2.
        broker = _make_broker(
            positions_chain=[
                [],                   # Pass 2 broker query
                [long_at_broker],     # Verify poll #1: still there
                [],                   # Verify poll #2: drained
            ]
        )

        om = _make_om(
            broker,
            _market_hours_clock(),
            verify_timeout=2.0,
            verify_poll_interval=0.05,
        )

        # Inject managed position so DRAIN counts as a "tracked long" for
        # the verify path (not a Pass-2 untracked).
        mp = _make_managed_position("DRAIN", 50)
        om._managed_positions["DRAIN"] = [mp]

        captured = _captured_alerts(om)

        await om.eod_flatten()
        await om._event_bus.drain()

        # No failure alert (long drained within timeout).
        failures = [a for a in captured if a.alert_type == "eod_flatten_failed"]
        assert failures == []
        # No residual short alert either.
        shorts = [a for a in captured if a.alert_type == "eod_residual_shorts"]
        assert shorts == []

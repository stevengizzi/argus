"""Regression tests for DEF-199 — EOD flatten doubling short positions.

Sprint 31.9 IMPROMPTU-04. See docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md §A1
for the root-cause analysis. On Apr 22 2026, 50 of 51 "untracked broker positions"
ended the paper session exactly 2× short because:

1. ``argus/execution/ibkr_broker.py:935`` returns ``shares = abs(int(pos.position))``
   (long/short lives on ``pos.side``, not on ``shares``).
2. ``argus/models/trading.py:164`` constrains ``Position.shares: int = Field(ge=1)``,
   so ``qty > 0`` is trivially True for any open position.
3. ``argus/execution/order_manager.py:1707`` (EOD Pass 2) and ``:1684`` (EOD Pass 1
   retry) filtered candidates on ``qty > 0`` without checking ``pos.side``, then
   unconditionally fired a MARKET SELL — doubling any short position.

These tests are **revert-proof**: if the side-check in the filter is reverted,
the mock broker receives a SELL order for the short-side FAKE position, which
the test asserts MUST NOT happen. The tests therefore fail loudly on regression.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, StartupConfig
from argus.core.event_bus import EventBus
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
    """11 AM ET = 15:00 UTC."""
    return FixedClock(datetime(2026, 4, 1, 15, 0, 0, tzinfo=UTC))


def _make_broker_position(
    symbol: str,
    shares: int,
    side: OrderSide,
) -> MagicMock:
    """Create a mock broker Position object matching IBKRBroker.get_positions() shape.

    IBKRBroker.get_positions() returns Position(shares=abs(int(pos.position)),
    side=OrderSide.BUY if pos.position > 0 else OrderSide.SELL). The bug
    surfaces when ``side == OrderSide.SELL``; the EOD Pass 2 filter historically
    ignored ``side`` and just checked ``shares > 0``, firing a SELL that
    doubled the short.
    """
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
    broker: MagicMock,
    clock: FixedClock,
    *,
    eod_flatten_retry_rejected: bool = True,
) -> OrderManager:
    config = OrderManagerConfig(
        eod_flatten_timeout_seconds=2,
        eod_flatten_retry_rejected=eod_flatten_retry_rejected,
        auto_shutdown_after_eod=False,
    )
    return OrderManager(
        event_bus=EventBus(),
        broker=broker,
        clock=clock,
        config=config,
        startup_config=StartupConfig(flatten_unknown_positions=True),
    )


# ---------------------------------------------------------------------------
# Canary 1 — EOD Pass 2 (:1707) side-check
# ---------------------------------------------------------------------------


class TestEodPass2SideCheck:
    """Pass 2 (broker-only untracked position sweep) MUST NOT SELL a short."""

    @pytest.mark.asyncio
    async def test_short_position_is_not_flattened_by_pass2(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """REVERT-PROOF: a SELL-side position at Pass 2 is skipped, not SOLD.

        Reverting the ``side`` check in order_manager.py:1707 causes this test
        to FAIL because ``place_order`` gets called with a MARKET SELL for FAKE,
        doubling the short. That failure mode IS the DEF-199 bug.
        """
        broker = _make_broker()
        short_pos = _make_broker_position("FAKE", shares=100, side=OrderSide.SELL)
        broker.get_positions = AsyncMock(side_effect=[
            [short_pos],  # Pass 2 query
            [short_pos],  # post-verify (still there, we didn't flatten it)
        ])

        om = _make_om(broker, _market_hours_clock())

        with caplog.at_level(logging.ERROR, logger="argus.execution.order_manager"):
            await om.eod_flatten()

        # Core regression assertion: no SELL placed for the short.
        broker.place_order.assert_not_called()

        # ERROR log must identify the short as unexpected.
        short_errors = [
            rec for rec in caplog.records
            if rec.levelno == logging.ERROR
            and "FAKE" in rec.getMessage()
            and "SHORT" in rec.getMessage().upper()
        ]
        assert short_errors, (
            "Expected an ERROR log naming FAKE as an unexpected short; "
            f"got records: {[r.getMessage() for r in caplog.records]}"
        )

    @pytest.mark.asyncio
    async def test_long_position_is_still_flattened_by_pass2(self) -> None:
        """Non-regression: BUY-side untracked position at Pass 2 is still SOLD."""
        broker = _make_broker()
        long_pos = _make_broker_position("GOOD", shares=50, side=OrderSide.BUY)
        broker.get_positions = AsyncMock(side_effect=[
            [long_pos],  # Pass 2 query
            [],          # post-verify
        ])

        om = _make_om(broker, _market_hours_clock())
        await om.eod_flatten()

        broker.place_order.assert_called_once()
        placed = broker.place_order.call_args[0][0]
        assert placed.symbol == "GOOD"
        assert placed.side == OrderSide.SELL
        assert placed.quantity == 50

    @pytest.mark.asyncio
    async def test_mixed_long_and_short_at_pass2_only_long_flattened(self) -> None:
        """Mix of BUY + SELL in Pass 2: only the BUY gets flattened."""
        broker = _make_broker()
        long_pos = _make_broker_position("LONG1", shares=25, side=OrderSide.BUY)
        short_pos = _make_broker_position("SHORT1", shares=200, side=OrderSide.SELL)
        broker.get_positions = AsyncMock(side_effect=[
            [long_pos, short_pos],  # Pass 2 query
            [short_pos],            # post-verify: short remains
        ])

        om = _make_om(broker, _market_hours_clock())
        await om.eod_flatten()

        assert broker.place_order.call_count == 1
        placed = broker.place_order.call_args[0][0]
        assert placed.symbol == "LONG1"

    @pytest.mark.asyncio
    async def test_pass2_position_with_side_none_is_skipped(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Defensive: unknown side (None) is not auto-flattened — ERROR logged."""
        broker = _make_broker()
        weird_pos = _make_broker_position("WEIRD", shares=10, side=None)  # type: ignore[arg-type]
        broker.get_positions = AsyncMock(side_effect=[
            [weird_pos],
            [weird_pos],
        ])

        om = _make_om(broker, _market_hours_clock())
        with caplog.at_level(logging.ERROR, logger="argus.execution.order_manager"):
            await om.eod_flatten()

        broker.place_order.assert_not_called()
        assert any("WEIRD" in rec.getMessage() for rec in caplog.records)


# ---------------------------------------------------------------------------
# Canary 2 — EOD Pass 1 retry (:1684) side-check
# ---------------------------------------------------------------------------


class TestEodPass1RetrySideCheck:
    """Pass 1 retry (fills-timed-out re-query) MUST NOT SELL a short.

    Forces a Pass 1 timeout by making place_order succeed (no fill callback
    delivered), which leaves the eod_flatten_events Event unset. After the
    timeout expires, the retry pass runs get_positions() and — pre-fix —
    blindly flattens anything with ``qty > 0``.
    """

    @pytest.mark.asyncio
    async def test_pass1_retry_skips_short_position(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """REVERT-PROOF: Pass 1 retry observing a short MUST NOT fire a SELL.

        Setup: open a managed position for FAKE, trigger eod_flatten (Pass 1
        places a flatten order but never gets the fill callback), timeout
        fires, retry pass queries broker and sees FAKE as SHORT 100.
        Pre-fix: retry placed a SELL 100 for FAKE, doubling the short.
        Post-fix: retry logs ERROR and skips.
        """
        from argus.core.events import OrderApprovedEvent, Side, SignalEvent

        broker = _make_broker()
        # Pass 1 place_order returns PENDING but no fill event will be delivered.
        broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="p1-flatten",
                broker_order_id="b-p1-flatten",
                status=OrderStatus.PENDING,
            )
        )
        # Initially empty (for the Pass 1 bracket entry and orphan queries that
        # don't interfere). Then after the timeout: retry_positions returns
        # FAKE as a short. Then post-verify sees it still there.
        broker.get_positions = AsyncMock(side_effect=[
            [_make_broker_position("FAKE", shares=100, side=OrderSide.SELL)],  # retry
            [_make_broker_position("FAKE", shares=100, side=OrderSide.SELL)],  # Pass 2
            [_make_broker_position("FAKE", shares=100, side=OrderSide.SELL)],  # verify
        ])

        # Configure OM with retry enabled, tight timeout, and make the retry
        # place_order succeed so we can assert it never gets called for a short.
        config = OrderManagerConfig(
            eod_flatten_timeout_seconds=1,
            eod_flatten_retry_rejected=True,
            auto_shutdown_after_eod=False,
        )
        om = OrderManager(
            event_bus=EventBus(),
            broker=broker,
            clock=_market_hours_clock(),
            config=config,
            startup_config=StartupConfig(flatten_unknown_positions=True),
        )

        # Open a managed position for FAKE via on_approved so Pass 1 has
        # something to try to flatten.
        broker.place_bracket_order = AsyncMock(
            return_value=MagicMock(
                entry=OrderResult(
                    order_id="entry-1",
                    broker_order_id="b-entry-1",
                    status=OrderStatus.FILLED,
                    filled_quantity=100,
                    filled_avg_price=150.0,
                ),
                stop=OrderResult(
                    order_id="stop-1", broker_order_id="b-stop-1",
                    status=OrderStatus.PENDING,
                ),
                targets=[
                    OrderResult(
                        order_id="t1-1", broker_order_id="b-t1-1",
                        status=OrderStatus.PENDING,
                    ),
                ],
            )
        )
        approved = OrderApprovedEvent(
            signal=SignalEvent(
                strategy_id="orb_breakout",
                symbol="FAKE",
                side=Side.LONG,
                entry_price=150.0,
                stop_price=148.0,
                target_prices=(152.0,),
                share_count=100,
                rationale="test",
                time_stop_seconds=300,
            ),
            modifications=None,
        )
        await om.on_approved(approved)

        # Reset place_order mock AFTER the bracket was submitted, so any
        # subsequent call is definitively attributable to the flatten paths.
        broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="flatten-x",
                broker_order_id="b-flatten-x",
                status=OrderStatus.PENDING,
            )
        )

        with caplog.at_level(logging.ERROR, logger="argus.execution.order_manager"):
            await om.eod_flatten()

        # Pass 1 may legitimately call place_order for the initial flatten
        # attempt on the managed position FAKE (SELL 100). That call IS
        # correct — we're flattening our own long managed position.
        #
        # The retry pass, however, sees side=SELL from the re-query and MUST
        # NOT fire a second SELL. Assert via message inspection that the
        # retry ERROR log fires and no "retrying" WARNING log fires.
        retry_warnings = [
            rec for rec in caplog.records
            if "retrying" in rec.getMessage().lower() and "FAKE" in rec.getMessage()
        ]
        assert not retry_warnings, (
            "Pass 1 retry should have logged ERROR (short detected) instead of "
            f"the pre-fix 'retrying' WARNING. Got: {[r.getMessage() for r in caplog.records]}"
        )
        short_errors = [
            rec for rec in caplog.records
            if rec.levelno == logging.ERROR
            and "FAKE" in rec.getMessage()
            and "SHORT" in rec.getMessage().upper()
        ]
        assert short_errors, (
            "Expected an ERROR log naming FAKE as an unexpected short during "
            "Pass 1 retry or Pass 2 (both should catch it)."
        )

    @pytest.mark.asyncio
    async def test_pass1_retry_still_flattens_long_timeout(
        self,
    ) -> None:
        """Non-regression: a LONG position still gets retried on Pass 1 timeout."""
        from argus.core.events import OrderApprovedEvent, Side, SignalEvent

        broker = _make_broker()
        broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="p1-flatten",
                broker_order_id="b-p1-flatten",
                status=OrderStatus.PENDING,
            )
        )
        # Pass 1 initial flatten will time out; retry sees the position still
        # LONG (side=BUY), so the retry SHOULD fire another SELL.
        broker.get_positions = AsyncMock(side_effect=[
            [_make_broker_position("LONGFAKE", shares=100, side=OrderSide.BUY)],  # retry
            [],  # Pass 2
            [],  # verify
        ])

        config = OrderManagerConfig(
            eod_flatten_timeout_seconds=1,
            eod_flatten_retry_rejected=True,
            auto_shutdown_after_eod=False,
        )
        om = OrderManager(
            event_bus=EventBus(),
            broker=broker,
            clock=_market_hours_clock(),
            config=config,
            startup_config=StartupConfig(flatten_unknown_positions=True),
        )

        broker.place_bracket_order = AsyncMock(
            return_value=MagicMock(
                entry=OrderResult(
                    order_id="entry-1",
                    broker_order_id="b-entry-1",
                    status=OrderStatus.FILLED,
                    filled_quantity=100,
                    filled_avg_price=150.0,
                ),
                stop=OrderResult(
                    order_id="stop-1", broker_order_id="b-stop-1",
                    status=OrderStatus.PENDING,
                ),
                targets=[
                    OrderResult(
                        order_id="t1-1", broker_order_id="b-t1-1",
                        status=OrderStatus.PENDING,
                    ),
                ],
            )
        )
        approved = OrderApprovedEvent(
            signal=SignalEvent(
                strategy_id="orb_breakout",
                symbol="LONGFAKE",
                side=Side.LONG,
                entry_price=150.0,
                stop_price=148.0,
                target_prices=(152.0,),
                share_count=100,
                rationale="test",
                time_stop_seconds=300,
            ),
            modifications=None,
        )
        await om.on_approved(approved)

        broker.place_order.reset_mock()
        await om.eod_flatten()

        # At least one SELL for LONGFAKE should fire (Pass 1 flatten + retry).
        assert broker.place_order.call_count >= 1
        sold_symbols = {
            call[0][0].symbol for call in broker.place_order.call_args_list
        }
        assert "LONGFAKE" in sold_symbols

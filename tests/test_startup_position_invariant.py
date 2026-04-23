"""Tests for the post-connect long-only startup invariant (Sprint 31.9 IMPROMPTU-04).

Context: ARGUS is currently long-only (DEC-166 shorting is scoped but unbuilt).
If the broker reports any position with ``side == OrderSide.SELL`` at connect
time, something has gone wrong upstream — a prior session zombie, a manual
short that wasn't cleared, or a bug like DEF-199 that flipped positions short
during the previous EOD flatten. Auto startup-cleanup must NOT run in that
state; a blind SELL of a short position doubles it (the DEF-199 bug, now
fixed in order_manager).

This test file covers the pure helper function — wiring into
``ArgusSystem.startup()`` is integration-tested via the existing main.py
test scaffolding (ANTHROPIC_API_KEY env-scrubbed to avoid AIConfig drift).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from argus.main import check_startup_position_invariant
from argus.models.trading import AssetClass, OrderSide, Position, PositionStatus


def _pos(symbol: str, shares: int, side: OrderSide) -> Position:
    """Build a real Position (not a MagicMock) to exercise the actual type contract."""
    return Position(
        strategy_id="",
        symbol=symbol,
        asset_class=AssetClass.US_STOCKS,
        side=side,
        status=PositionStatus.OPEN,
        entry_price=100.0,
        entry_time=datetime.now(UTC),
        shares=shares,
        stop_price=0.0,
    )


class TestStartupPositionInvariant:
    """Pure function contract for the startup long-only invariant."""

    def test_empty_positions_returns_ok(self) -> None:
        """No positions = invariant satisfied."""
        ok, shorts = check_startup_position_invariant([])
        assert ok is True
        assert shorts == []

    def test_all_long_positions_returns_ok(self) -> None:
        """Multiple BUY-side positions = invariant satisfied."""
        positions = [
            _pos("AAPL", 100, OrderSide.BUY),
            _pos("TSLA", 50, OrderSide.BUY),
        ]
        ok, shorts = check_startup_position_invariant(positions)
        assert ok is True
        assert shorts == []

    def test_single_short_fails_invariant(self) -> None:
        """One SELL position violates the invariant."""
        positions = [_pos("FAKE", 100, OrderSide.SELL)]
        ok, shorts = check_startup_position_invariant(positions)
        assert ok is False
        assert len(shorts) == 1
        assert "FAKE" in shorts[0]

    def test_mixed_longs_and_shorts_returns_just_the_shorts(self) -> None:
        """Mix of BUY + SELL → invariant violated; only shorts enumerated."""
        positions = [
            _pos("AAPL", 100, OrderSide.BUY),
            _pos("SHORT1", 200, OrderSide.SELL),
            _pos("TSLA", 50, OrderSide.BUY),
            _pos("SHORT2", 300, OrderSide.SELL),
        ]
        ok, shorts = check_startup_position_invariant(positions)
        assert ok is False
        assert len(shorts) == 2
        assert any("SHORT1" in s for s in shorts)
        assert any("SHORT2" in s for s in shorts)

    def test_position_without_side_attr_fails_closed(self) -> None:
        """Defensive: object without a ``side`` attribute is treated as a violation.

        This catches broker-adapter drift where a new broker returns a Position
        without a ``side`` field. Fail-closed is the right posture — we'd rather
        block auto-cleanup on a novel broker than silently proceed.
        """
        # Use a MagicMock with the side attribute explicitly deleted to simulate
        # a Position-shaped object that lacks a side attribute.
        weird = MagicMock(spec=[])
        weird.symbol = "WEIRD"
        weird.shares = 10
        ok, shorts = check_startup_position_invariant([weird])
        assert ok is False
        assert len(shorts) == 1
        assert "WEIRD" in shorts[0]

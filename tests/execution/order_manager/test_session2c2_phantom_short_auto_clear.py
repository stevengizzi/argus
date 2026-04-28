"""Sprint 31.91 Session 2c.2 — phantom-short gate auto-clear (5-cycle, M4) tests.

Covers the auto-clear behaviour layered onto the per-symbol entry gate
introduced in Session 2c.1:

- Default M4 threshold: 5 consecutive broker-non-short reconciliation cycles
  before the gate auto-clears.
- Counter resets on re-detection of the phantom short at the broker
  (preventing a stuttering near-clear/re-engage gate).
- The threshold is configurable via ``ReconciliationConfig`` and the YAML.
- Pydantic bounds (``ge=1, le=60``) on the threshold field.

These tests are revert-proof for the Session 2c.2 changes — the
clear-counter state, the threshold field, and the auto-clear flow.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
import yaml
from pydantic import ValidationError

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, ReconciliationConfig
from argus.core.event_bus import EventBus
from argus.execution.order_manager import (
    OrderManager,
    ReconciliationPosition,
)
from argus.models.trading import OrderSide


# ---------------------------------------------------------------------------
# Fixtures (mirror Session 2c.1's pattern)
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
    broker_orphan_consecutive_clear_threshold: int = 5,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(
            broker_orphan_alert_enabled=True,
            broker_orphan_entry_gate_enabled=True,
            broker_orphan_consecutive_clear_threshold=(
                broker_orphan_consecutive_clear_threshold
            ),
        ),
        operations_db_path=str(operations_db_path),
    )


async def _await_persist_tasks(om: OrderManager) -> None:
    """Wait for any fire-and-forget gate-persistence tasks to settle."""
    import asyncio as _asyncio

    while om._pending_gate_persist_tasks:
        pending = list(om._pending_gate_persist_tasks)
        await _asyncio.gather(*pending, return_exceptions=True)


# ---------------------------------------------------------------------------
# Test 1 — gate auto-clears after 5 consecutive zero-shares cycles (default)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_clears_after_5_consecutive_zero_cycles(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """With the M4 default threshold of 5, a gated symbol whose broker
    reports zero shares for 5 straight cycles auto-clears the gate.
    Cycle 4 -> still engaged, counter at 4. Cycle 5 -> cleared, counter
    cleaned up, ``operations.db`` row removed.
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)

    # Pre-engage the gate (skip the engagement path; that's Session 2c.1's
    # surface). Persist a row so the auto-clear DB delete is observable.
    om._phantom_short_gated_symbols.add("AAPL")
    await om._persist_gated_symbol(
        "AAPL", "engaged", last_observed_short_shares=100
    )

    # Cycles 1..4 — broker reports zero (no AAPL in the dict). Gate stays
    # engaged; counter ramps to 4.
    for expected in range(1, 5):
        await om.reconcile_positions({})
        assert "AAPL" in om._phantom_short_gated_symbols
        assert om._phantom_short_clear_cycles["AAPL"] == expected

    # Cycle 5 — counter reaches threshold; gate clears.
    await om.reconcile_positions({})
    await _await_persist_tasks(om)

    assert "AAPL" not in om._phantom_short_gated_symbols
    assert "AAPL" not in om._phantom_short_clear_cycles

    # DB row removed.
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM phantom_short_gated_symbols WHERE symbol = ?",
            ("AAPL",),
        ) as cursor:
            count_row = await cursor.fetchone()
    assert count_row is not None
    assert count_row[0] == 0


# ---------------------------------------------------------------------------
# Test 2 — re-detection of phantom short resets the clear counter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_persists_through_transient_broker_zero_resets_counter(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """A broker-zero observation that is followed by a re-detection of the
    phantom short MUST reset the clear counter. Otherwise a stuttering
    sequence (zero, short, zero, zero, zero, zero, zero) would trigger
    auto-clear after only 5 total non-short cycles instead of 5 consecutive
    non-short cycles. After the reset, the gate clears only when 5
    consecutive non-short cycles accumulate from scratch.
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(event_bus, mock_broker, fixed_clock, db_path)
    om._phantom_short_gated_symbols.add("AAPL")
    await om._persist_gated_symbol(
        "AAPL", "engaged", last_observed_short_shares=100
    )

    short_pos = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.SELL, shares=100,
        ),
    }

    # Cycle 1: broker reports zero -> counter = 1.
    await om.reconcile_positions({})
    assert om._phantom_short_clear_cycles["AAPL"] == 1

    # Cycle 2: broker reports SHORT -> counter resets (popped); gate engaged.
    await om.reconcile_positions(short_pos)
    assert "AAPL" not in om._phantom_short_clear_cycles
    assert "AAPL" in om._phantom_short_gated_symbols

    # Cycles 3..6: broker reports zero — counter ramps 1..4, gate still engaged.
    for expected in range(1, 5):
        await om.reconcile_positions({})
        assert om._phantom_short_clear_cycles["AAPL"] == expected
        assert "AAPL" in om._phantom_short_gated_symbols

    # Cycle 7: counter reaches 5 -> gate clears.
    await om.reconcile_positions({})
    await _await_persist_tasks(om)
    assert "AAPL" not in om._phantom_short_gated_symbols
    assert "AAPL" not in om._phantom_short_clear_cycles


# ---------------------------------------------------------------------------
# Test 3 — default M4 threshold is 5 (config + YAML)
# ---------------------------------------------------------------------------


def test_clear_threshold_config_loadable_default_5() -> None:
    """``ReconciliationConfig()`` defaults the threshold to 5 (M4
    disposition; 3 in earlier drafts). ``config/system_live.yaml``
    sets it explicitly to 5 in production.
    """
    default = ReconciliationConfig()
    assert default.broker_orphan_consecutive_clear_threshold == 5

    repo_root = Path(__file__).resolve().parents[3]
    live_yaml_path = repo_root / "config" / "system_live.yaml"
    with live_yaml_path.open() as f:
        live_cfg = yaml.safe_load(f)
    assert (
        live_cfg["reconciliation"]["broker_orphan_consecutive_clear_threshold"]
        == 5
    )


# ---------------------------------------------------------------------------
# Test 4 — threshold is configurable; bounds enforced (ge=1, le=60)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_threshold_configurable_override(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    tmp_path: Path,
) -> None:
    """A config override of 10 cycles takes effect at runtime; the gate
    does NOT clear at cycle 5 and DOES clear at cycle 10. Pydantic bounds
    reject ``=0`` (below ge=1) and ``=61`` (above le=60).
    """
    db_path = tmp_path / "operations.db"
    om = _make_order_manager(
        event_bus,
        mock_broker,
        fixed_clock,
        db_path,
        broker_orphan_consecutive_clear_threshold=10,
    )
    om._phantom_short_gated_symbols.add("AAPL")
    await om._persist_gated_symbol(
        "AAPL", "engaged", last_observed_short_shares=100
    )

    # Cycles 1..9 — gate stays engaged under the 10-cycle threshold.
    for expected in range(1, 10):
        await om.reconcile_positions({})
        assert "AAPL" in om._phantom_short_gated_symbols
        assert om._phantom_short_clear_cycles["AAPL"] == expected

    # Cycle 5 specifically: gate is NOT cleared under the override.
    # (Already covered by the loop above at expected==5, but pin it.)
    # Cycle 10 — gate clears.
    await om.reconcile_positions({})
    await _await_persist_tasks(om)
    assert "AAPL" not in om._phantom_short_gated_symbols
    assert "AAPL" not in om._phantom_short_clear_cycles

    # Pydantic bounds: 0 and 61 are rejected.
    with pytest.raises(ValidationError):
        ReconciliationConfig(broker_orphan_consecutive_clear_threshold=0)
    with pytest.raises(ValidationError):
        ReconciliationConfig(broker_orphan_consecutive_clear_threshold=61)

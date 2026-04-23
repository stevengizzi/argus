"""Regression tests for the DEF-164 boot-grace shutdown suppression.

When ARGUS is (re)booted late at night, an EOD flatten running in the
same process can queue a ``ShutdownRequestedEvent`` immediately — and,
pre-DEF-164, that teardown could fire in the middle of phase-11
HistoricalQueryService init (blocking on the Parquet CREATE VIEW) or
any other slow sub-phase, producing the DEF-165 interrupt-close hang.

The fix: ``ArgusSystem._on_shutdown_requested`` checks
``(monotonic() - _boot_monotonic) < auto_shutdown_boot_grace_minutes * 60``
and defers the shutdown if we're still inside the grace window.
"""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.events import ShutdownRequestedEvent
from argus.main import ArgusSystem


def _make_system_with_boot_time(
    *,
    grace_minutes: int,
    boot_monotonic: float | None,
    current_monotonic: float,
    monkeypatch: pytest.MonkeyPatch,
) -> ArgusSystem:
    """Build an ArgusSystem with the minimum state required to exercise
    ``_on_shutdown_requested`` without running ``start()``."""
    system = ArgusSystem.__new__(ArgusSystem)
    system._shutdown_event = asyncio.Event()  # type: ignore[attr-defined]
    system._boot_monotonic = boot_monotonic  # type: ignore[attr-defined]
    system._clock = None  # type: ignore[attr-defined]
    system._trade_logger = None  # type: ignore[attr-defined]
    system._counterfactual_tracker = None  # type: ignore[attr-defined]
    system._event_bus = MagicMock()  # type: ignore[attr-defined]
    system._event_bus.publish = AsyncMock()
    # Minimal config surface for the DEF-164 branch.
    order_manager_cfg = SimpleNamespace(
        auto_shutdown_boot_grace_minutes=grace_minutes
    )
    system._config = SimpleNamespace(order_manager=order_manager_cfg)  # type: ignore[attr-defined]

    # Freeze monotonic() so the grace-check is deterministic.
    monkeypatch.setattr(
        "argus.main.time.monotonic", lambda: current_monotonic
    )
    return system


@pytest.mark.asyncio
async def test_auto_shutdown_deferred_when_inside_grace_window(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Boot was 3 minutes ago, grace is 10 minutes — shutdown must defer.

    Verifies: request_shutdown is NOT scheduled (no delayed task), and a
    'deferred' INFO log is emitted mentioning DEF-164.
    """
    caplog.set_level(logging.INFO, logger="argus.main")
    system = _make_system_with_boot_time(
        grace_minutes=10,
        boot_monotonic=100.0,
        current_monotonic=100.0 + 3 * 60,  # 3 minutes later
        monkeypatch=monkeypatch,
    )

    # Spy on request_shutdown so we can confirm it was NOT queued.
    request_shutdown_spy = MagicMock()
    monkeypatch.setattr(system, "request_shutdown", request_shutdown_spy)

    event = ShutdownRequestedEvent(reason="eod_flatten_complete", delay_seconds=60)
    await system._on_shutdown_requested(event)

    # No shutdown scheduled.
    request_shutdown_spy.assert_not_called()
    # SessionEndEvent publish also suppressed (it's below the deferral return).
    system._event_bus.publish.assert_not_called()
    # Log records the DEF-164 deferral.
    assert any("deferred" in rec.message.lower() for rec in caplog.records)
    assert any("boot grace window" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_auto_shutdown_proceeds_after_grace_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot was 20 minutes ago, grace is 10 minutes — shutdown proceeds.

    Past the grace window, the normal ShutdownRequested path runs:
    SessionEndEvent publishes (which is the first observable side-effect
    past the deferral branch). We don't also assert on the delayed
    shutdown task — ``create_task`` leaves it hanging for the test
    teardown and it's orthogonal to the DEF-164 fix being tested here.
    """
    system = _make_system_with_boot_time(
        grace_minutes=10,
        boot_monotonic=100.0,
        current_monotonic=100.0 + 20 * 60,  # 20 minutes later
        monkeypatch=monkeypatch,
    )
    # Stub _publish_session_end_event so we don't need a full trade_logger.
    publish_session_end = AsyncMock()
    monkeypatch.setattr(system, "_publish_session_end_event", publish_session_end)
    # Also stub create_task so the never-awaited delayed_shutdown doesn't
    # leak into test teardown.
    monkeypatch.setattr("argus.main.asyncio.create_task", lambda coro: coro.close())

    event = ShutdownRequestedEvent(reason="eod_flatten_complete", delay_seconds=0)
    await system._on_shutdown_requested(event)

    # Past the grace window: SessionEndEvent publishes.
    publish_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_shutdown_grace_disabled_when_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``auto_shutdown_boot_grace_minutes=0`` disables the suppression.

    Operators that want the old behavior (no grace window at all) set
    the config to 0. In this case the DEF-164 branch is a no-op and the
    usual shutdown path runs regardless of boot timing.
    """
    system = _make_system_with_boot_time(
        grace_minutes=0,
        boot_monotonic=100.0,
        current_monotonic=100.0 + 30,  # 30 seconds after boot
        monkeypatch=monkeypatch,
    )
    publish_session_end = AsyncMock()
    monkeypatch.setattr(system, "_publish_session_end_event", publish_session_end)
    monkeypatch.setattr("argus.main.asyncio.create_task", lambda coro: coro.close())

    event = ShutdownRequestedEvent(reason="eod_flatten_complete", delay_seconds=0)
    await system._on_shutdown_requested(event)

    # Grace disabled → shutdown path runs.
    publish_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_shutdown_skips_grace_when_boot_time_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensive: if ``_boot_monotonic`` is None (shutdown before start()
    recorded it), the grace check is bypassed rather than silently
    suppressing every shutdown attempt forever."""
    system = _make_system_with_boot_time(
        grace_minutes=10,
        boot_monotonic=None,
        current_monotonic=500.0,
        monkeypatch=monkeypatch,
    )
    publish_session_end = AsyncMock()
    monkeypatch.setattr(system, "_publish_session_end_event", publish_session_end)
    monkeypatch.setattr("argus.main.asyncio.create_task", lambda coro: coro.close())

    event = ShutdownRequestedEvent(reason="eod_flatten_complete", delay_seconds=0)
    await system._on_shutdown_requested(event)

    publish_session_end.assert_awaited_once()

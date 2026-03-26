"""Tests for per-strategy health reporting in main.py.

Sprint 27.8 Session 1: Verifies that inactive (regime-filtered) strategies
report DEGRADED status, while active strategies report HEALTHY.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from argus.core.health import ComponentStatus, HealthConfig, HealthMonitor


def test_per_strategy_health_reflects_regime_filtering() -> None:
    """Inactive strategy reports DEGRADED, active reports HEALTHY."""
    health_monitor = HealthMonitor(
        event_bus=MagicMock(),
        clock=MagicMock(),
        config=HealthConfig(),
    )

    # Simulate strategies dict as returned by orchestrator.get_strategies()
    active_strategy = MagicMock()
    active_strategy.is_active = True
    active_strategy.config.name = "ORB Breakout"

    inactive_strategy = MagicMock()
    inactive_strategy.is_active = False
    inactive_strategy.config.name = "VWAP Reclaim"

    strategies = {
        "orb_breakout": active_strategy,
        "vwap_reclaim": inactive_strategy,
    }

    # Replicate the per-strategy health loop from main.py
    for strategy_id, strategy in strategies.items():
        status = ComponentStatus.HEALTHY if strategy.is_active else ComponentStatus.DEGRADED
        label = "active" if strategy.is_active else "regime-filtered"
        health_monitor.update_component(
            f"strategy_{strategy_id}",
            status,
            message=f"{strategy.config.name} {label}",
        )

    # Verify active strategy → HEALTHY
    orb_component = health_monitor._components.get("strategy_orb_breakout")
    assert orb_component is not None
    assert orb_component.status == ComponentStatus.HEALTHY
    assert "active" in orb_component.message

    # Verify inactive strategy → DEGRADED
    vwap_component = health_monitor._components.get("strategy_vwap_reclaim")
    assert vwap_component is not None
    assert vwap_component.status == ComponentStatus.DEGRADED
    assert "regime-filtered" in vwap_component.message

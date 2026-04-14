"""Tests for BacktestEngine config_fingerprint wiring (DEF-153).

Verifies that BacktestEngineConfig stores config_fingerprint and that
BacktestEngine._setup() registers the fingerprint with the OrderManager
so trades carry it in the output DB.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine


# ---------------------------------------------------------------------------
# Test 6: BacktestEngineConfig stores config_fingerprint field
# ---------------------------------------------------------------------------


def test_backtest_engine_config_fingerprint_field() -> None:
    """BacktestEngineConfig(config_fingerprint=...) stores the value (DEF-153)."""
    fingerprint = "abc123def456abcd"
    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        config_fingerprint=fingerprint,
    )

    assert config.config_fingerprint == fingerprint


def test_backtest_engine_config_fingerprint_defaults_to_none() -> None:
    """config_fingerprint defaults to None when not provided."""
    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
    )

    assert config.config_fingerprint is None


# ---------------------------------------------------------------------------
# Test 7: BacktestEngine._setup() registers fingerprint with OrderManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backtest_engine_registers_fingerprint(tmp_path: Path) -> None:
    """_setup() with config_fingerprint registers it with OrderManager (DEF-153)."""
    fingerprint = "deadbeef12345678"
    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
        config_fingerprint=fingerprint,
    )

    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert engine._order_manager is not None
        # Fingerprint must be registered under the strategy's id
        strategy_id = engine._strategy.strategy_id if engine._strategy else config.strategy_id
        registered = engine._order_manager._fingerprint_registry.get(strategy_id)
        assert registered == fingerprint
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_backtest_engine_no_fingerprint_skips_registration(tmp_path: Path) -> None:
    """_setup() without config_fingerprint leaves fingerprint registry empty (DEF-153)."""
    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
        # No config_fingerprint
    )

    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert engine._order_manager is not None
        # Registry should not have an entry for this strategy
        assert "strat_orb_breakout" not in engine._order_manager._fingerprint_registry
    finally:
        await engine._teardown()

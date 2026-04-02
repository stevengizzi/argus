"""Tests for pre-EOD signal cutoff and related config loading.

Sprint 32.9, Session 3.

Covers:
- Signal cutoff blocks new entries after configured time
- Signal cutoff allows entries before configured time
- Signal cutoff disabled allows entries past configured time
- Signal cutoff logs once per session regardless of signal volume
- max_concurrent_positions=50 loaded from risk_limits.yaml
- overflow broker_capacity=50 loaded from overflow.yaml
- ABCD and Flat-Top Breakout strategies in shadow mode
- Experiments pipeline enabled
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from argus.core.config import BrokerSource, OrchestratorConfig
from argus.core.events import OrderRejectedEvent, Side, SignalEvent
from argus.main import ArgusSystem

_CONFIG_DIR = Path(__file__).parents[2] / "config"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal() -> SignalEvent:
    return SignalEvent(
        strategy_id="strat_orb_breakout",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=100.0,
        stop_price=99.0,
        target_prices=(102.0,),
        share_count=0,
        pattern_strength=60.0,
    )


def _make_datetime_et(hour: int, minute: int) -> datetime:
    """Return a UTC datetime that maps to hour:minute in ET (UTC-4 during DST)."""
    # Use UTC-4 offset (EDT) — tests run during summer trading hours
    from zoneinfo import ZoneInfo
    et_tz = ZoneInfo("America/New_York")
    local = datetime(2026, 4, 2, hour, minute, 0, tzinfo=et_tz)
    return local.astimezone(timezone.utc)


def _build_cutoff_system(
    signal_cutoff_enabled: bool,
    signal_cutoff_time: str,
    clock_hour: int,
    clock_minute: int,
) -> ArgusSystem:
    """Build a minimal ArgusSystem stub for testing signal cutoff logic.

    Uses BrokerSource.SIMULATED so the quality pipeline is bypassed and
    we can verify whether _risk_manager.evaluate_signal is called.
    """
    system = MagicMock()  # No spec — private attrs (_ prefix) blocked by spec=ArgusSystem
    system._cutoff_logged = False

    # Config orchestrator (cutoff settings)
    system._config.orchestrator.signal_cutoff_enabled = signal_cutoff_enabled
    system._config.orchestrator.signal_cutoff_time = signal_cutoff_time

    # Config system (bypass quality pipeline via SIMULATED)
    system._config.system.broker_source = BrokerSource.SIMULATED
    system._config.system.quality_engine.enabled = True
    system._config.system.overflow.enabled = False

    # Clock
    system._clock.now.return_value = _make_datetime_et(clock_hour, clock_minute)

    # Risk manager — returns a rejected event to avoid downstream order placement
    rejected = MagicMock(spec=OrderRejectedEvent)
    system._risk_manager.evaluate_signal = AsyncMock(return_value=rejected)

    # event_bus.publish must be async-compatible
    system._event_bus.publish = AsyncMock()

    # Other components not needed for cutoff tests
    system._quality_engine = None
    system._catalyst_storage = None
    system._orchestrator = None
    system._position_sizer = None
    system._counterfactual_enabled = False
    system._eval_store = None
    system._order_manager = None

    return system


# ---------------------------------------------------------------------------
# Tests — signal cutoff behaviour
# ---------------------------------------------------------------------------


class TestSignalCutoff:
    """Tests for pre-EOD signal cutoff in _process_signal."""

    @pytest.mark.asyncio
    async def test_signal_cutoff_blocks_after_time(self) -> None:
        """Signal at 15:31 ET is dropped when cutoff is enabled at 15:30."""
        system = _build_cutoff_system(
            signal_cutoff_enabled=True,
            signal_cutoff_time="15:30",
            clock_hour=15,
            clock_minute=31,
        )
        signal = _make_signal()
        strategy = MagicMock()

        await ArgusSystem._process_signal(system, signal, strategy)

        system._risk_manager.evaluate_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_signal_cutoff_allows_before_time(self) -> None:
        """Signal at 15:29 ET is processed when cutoff is configured at 15:30."""
        system = _build_cutoff_system(
            signal_cutoff_enabled=True,
            signal_cutoff_time="15:30",
            clock_hour=15,
            clock_minute=29,
        )
        signal = _make_signal()
        strategy = MagicMock()
        strategy.config.mode = "live"
        strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
        strategy.allocated_capital = 100_000.0

        await ArgusSystem._process_signal(system, signal, strategy)

        system._risk_manager.evaluate_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_cutoff_disabled(self) -> None:
        """When signal_cutoff_enabled=False, signals process past cutoff time."""
        system = _build_cutoff_system(
            signal_cutoff_enabled=False,
            signal_cutoff_time="15:30",
            clock_hour=15,
            clock_minute=45,
        )
        signal = _make_signal()
        strategy = MagicMock()
        strategy.config.mode = "live"
        strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
        strategy.allocated_capital = 100_000.0

        await ArgusSystem._process_signal(system, signal, strategy)

        system._risk_manager.evaluate_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_cutoff_logs_once(self) -> None:
        """Cutoff log message is emitted exactly once across multiple blocked signals."""
        system = _build_cutoff_system(
            signal_cutoff_enabled=True,
            signal_cutoff_time="15:30",
            clock_hour=15,
            clock_minute=50,
        )
        signal = _make_signal()
        strategy = MagicMock()

        with patch("argus.main.logger") as mock_logger:
            for _ in range(10):
                system._cutoff_logged = system._cutoff_logged  # read current state
                await ArgusSystem._process_signal(system, signal, strategy)

        info_calls = [c for c in mock_logger.info.call_args_list if "cutoff" in str(c).lower()]
        assert len(info_calls) == 1


# ---------------------------------------------------------------------------
# Tests — OrchestratorConfig fields
# ---------------------------------------------------------------------------


class TestOrchestratorConfigCutoffFields:
    """Tests for signal_cutoff fields on OrchestratorConfig."""

    def test_signal_cutoff_enabled_default_true(self) -> None:
        """signal_cutoff_enabled defaults to True."""
        config = OrchestratorConfig()
        assert config.signal_cutoff_enabled is True

    def test_signal_cutoff_time_default(self) -> None:
        """signal_cutoff_time defaults to '15:30'."""
        config = OrchestratorConfig()
        assert config.signal_cutoff_time == "15:30"

    def test_signal_cutoff_disabled_in_config(self) -> None:
        """signal_cutoff_enabled can be set to False."""
        config = OrchestratorConfig(signal_cutoff_enabled=False)
        assert config.signal_cutoff_enabled is False


# ---------------------------------------------------------------------------
# Tests — config file values
# ---------------------------------------------------------------------------


class TestConfigFileValues:
    """Tests that config files contain expected Sprint 32.9 values."""

    def test_max_concurrent_positions_loaded(self) -> None:
        """risk_limits.yaml max_concurrent_positions is 50."""
        raw = yaml.safe_load((_CONFIG_DIR / "risk_limits.yaml").read_text())
        assert raw["account"]["max_concurrent_positions"] == 50

    def test_overflow_capacity_loaded(self) -> None:
        """overflow.yaml broker_capacity is 50."""
        raw = yaml.safe_load((_CONFIG_DIR / "overflow.yaml").read_text())
        assert raw["overflow"]["broker_capacity"] == 50

    def test_strategy_abcd_shadow_mode(self) -> None:
        """abcd.yaml mode is 'shadow'."""
        raw = yaml.safe_load((_CONFIG_DIR / "strategies" / "abcd.yaml").read_text())
        assert raw["mode"] == "shadow"

    def test_strategy_flat_top_breakout_shadow_mode(self) -> None:
        """flat_top_breakout.yaml mode is 'shadow'."""
        raw = yaml.safe_load(
            (_CONFIG_DIR / "strategies" / "flat_top_breakout.yaml").read_text()
        )
        assert raw["mode"] == "shadow"

    def test_experiments_enabled(self) -> None:
        """experiments.yaml enabled is True."""
        raw = yaml.safe_load((_CONFIG_DIR / "experiments.yaml").read_text())
        assert raw["enabled"] is True

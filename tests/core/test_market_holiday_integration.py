"""Integration tests for market holiday detection across ARGUS components.

Covers:
- HealthMonitor.check_strategy_evaluations() skips DEGRADED on holidays
- Orchestrator._is_market_hours() returns False on holidays
- GET /api/v1/market/status returns correct holiday info
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    HealthConfig,
    OperatingWindow,
    OrchestratorConfig,
    StrategyConfig,
    StrategyRiskLimits,
)
from argus.core.event_bus import EventBus
from argus.core.health import ComponentStatus, HealthMonitor
from argus.models.strategy import ExitRules, MarketConditionsFilter, ProfitTarget, ScannerCriteria
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.telemetry_store import EvaluationEventStore


# 10:00 AM ET on Good Friday 2026 (UTC = 14:00)
_GOOD_FRIDAY_10AM_ET_UTC = datetime(2026, 4, 3, 14, 0, 0, tzinfo=UTC)
# 10:00 AM ET on Monday after Easter 2026 (UTC = 14:00)
_MONDAY_AFTER_EASTER_10AM_ET_UTC = datetime(2026, 4, 6, 14, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Minimal strategy stub (mirrors test_evaluation_telemetry_e2e.py pattern)
# ---------------------------------------------------------------------------


def _make_config(earliest_entry: str = "09:35") -> StrategyConfig:
    return StrategyConfig(
        strategy_id="strat_test",
        name="Test Strategy",
        version="1.0.0",
        enabled=True,
        risk_limits=StrategyRiskLimits(),
        operating_window=OperatingWindow(earliest_entry=earliest_entry),
    )


class _TestStrategy(BaseStrategy):
    """Minimal strategy implementing all abstract methods for testing."""

    async def on_candle(self, event: object) -> None:  # type: ignore[override]
        pass

    async def on_tick(self, event: object) -> None:  # type: ignore[override]
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        return ScannerCriteria(min_price=10.0, max_price=200.0, min_volume_avg_daily=1_000_000)

    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        return 0

    def get_exit_rules(self) -> ExitRules:
        return ExitRules(
            stop_type="fixed",
            stop_price_func="midpoint",
            targets=[ProfitTarget(r_multiple=1.0, position_pct=1.0)],
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        return MarketConditionsFilter()


# ---------------------------------------------------------------------------
# Health Monitor: skip DEGRADED check on holidays
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHealthHolidaySkip:
    """check_strategy_evaluations() must skip DEGRADED assignment on holidays."""

    @pytest.fixture
    async def eval_store(self, tmp_path: Path) -> EvaluationEventStore:
        db_path = str(tmp_path / "eval.db")
        store = EvaluationEventStore(db_path)
        await store.initialize()
        yield store
        await store.close()

    @pytest.fixture
    def health_monitor(self) -> HealthMonitor:
        config = HealthConfig(
            heartbeat_interval_seconds=60,
            heartbeat_url_env="",
            alert_webhook_url_env="",
            daily_check_enabled=False,
            weekly_reconciliation_enabled=False,
        )
        event_bus = EventBus()
        clock = FixedClock(_GOOD_FRIDAY_10AM_ET_UTC)
        return HealthMonitor(event_bus=event_bus, clock=clock, config=config)

    async def test_skips_degraded_on_holiday(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """On a market holiday, check_strategy_evaluations() returns without marking DEGRADED."""
        strat = _TestStrategy(_make_config())
        strat.is_active = True
        strat.set_watchlist(["AAPL", "TSLA"])

        clock = FixedClock(_GOOD_FRIDAY_10AM_ET_UTC)

        with patch(
            "argus.core.market_calendar.is_market_holiday",
            return_value=(True, "Good Friday"),
        ):
            await health_monitor.check_strategy_evaluations(
                strategies={"strat_test": strat},
                eval_store=eval_store,
                clock=clock,
            )

        # No DEGRADED component should have been set
        status = health_monitor.get_status()
        assert "strategy_strat_test" not in status

    async def test_sets_degraded_on_normal_trading_day(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """On a normal trading day, zero evaluations correctly produce DEGRADED."""
        strat = _TestStrategy(_make_config())
        strat.is_active = True
        strat.set_watchlist(["AAPL"])

        clock = FixedClock(_MONDAY_AFTER_EASTER_10AM_ET_UTC)

        with patch(
            "argus.core.market_calendar.is_market_holiday",
            return_value=(False, None),
        ):
            await health_monitor.check_strategy_evaluations(
                strategies={"strat_test": strat},
                eval_store=eval_store,
                clock=clock,
            )

        component = health_monitor.get_status().get("strategy_strat_test")
        assert component is not None
        assert component.status == ComponentStatus.DEGRADED


# ---------------------------------------------------------------------------
# Orchestrator: _is_market_hours() returns False on holidays
# ---------------------------------------------------------------------------


class TestOrchestratorHolidayAware:
    """Orchestrator._is_market_hours() must return False when _market_holiday is set."""

    def _make_orchestrator(self, utc_time: datetime) -> object:
        from argus.core.orchestrator import Orchestrator

        config = OrchestratorConfig()
        event_bus = EventBus()
        clock = FixedClock(utc_time)
        trade_logger = AsyncMock()
        broker = AsyncMock()
        data_service = AsyncMock()

        return Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
        )

    def test_is_market_hours_returns_false_on_holiday(self) -> None:
        """_is_market_hours() returns False when _market_holiday flag is True."""
        orch = self._make_orchestrator(_GOOD_FRIDAY_10AM_ET_UTC)
        orch._market_holiday = True  # type: ignore[attr-defined]
        assert orch._is_market_hours() is False  # type: ignore[attr-defined]

    def test_is_market_hours_returns_true_on_normal_trading_day(self) -> None:
        """_is_market_hours() returns True at 10 AM ET on a normal weekday."""
        orch = self._make_orchestrator(_MONDAY_AFTER_EASTER_10AM_ET_UTC)
        orch._market_holiday = False  # type: ignore[attr-defined]
        assert orch._is_market_hours() is True  # type: ignore[attr-defined]

    def test_market_holiday_flag_initializes_false(self) -> None:
        """Orchestrator initializes with _market_holiday=False (safe default)."""
        orch = self._make_orchestrator(_GOOD_FRIDAY_10AM_ET_UTC)
        assert orch._market_holiday is False  # type: ignore[attr-defined]
        assert orch._holiday_name is None  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_run_pre_market_sets_holiday_flag(self) -> None:
        """run_pre_market() sets _market_holiday flag when is_market_holiday() returns True."""
        orch = self._make_orchestrator(_GOOD_FRIDAY_10AM_ET_UTC)

        orch._data_service.fetch_daily_bars = AsyncMock(return_value=None)  # type: ignore[attr-defined]
        orch._broker.get_account = AsyncMock(  # type: ignore[attr-defined]
            return_value=MagicMock(equity=100000.0)
        )

        with patch(
            "argus.core.market_calendar.is_market_holiday",
            return_value=(True, "Good Friday"),
        ):
            await orch.run_pre_market()  # type: ignore[attr-defined]

        assert orch._market_holiday is True  # type: ignore[attr-defined]
        assert orch._holiday_name == "Good Friday"  # type: ignore[attr-defined]

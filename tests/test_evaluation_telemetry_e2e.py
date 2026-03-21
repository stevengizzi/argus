"""End-to-end tests for the evaluation telemetry pipeline.

Verifies the full path: candle → strategy → ring buffer → SQLite → Observatory.
Also tests the health warning for zero-evaluation strategies.

Sprint 25.5, Session 2.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from argus.analytics.observatory_service import ObservatoryService
from argus.core.clock import FixedClock
from argus.core.config import (
    HealthConfig,
    OperatingWindow,
    StrategyConfig,
    StrategyRiskLimits,
)
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, Side, SignalEvent, TickEvent
from argus.core.health import ComponentStatus, HealthMonitor
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
    ScannerCriteria,
)
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.telemetry import (
    EvaluationEventType,
    EvaluationResult,
)
from argus.strategies.telemetry_store import EvaluationEventStore

_ET = ZoneInfo("America/New_York")


def _today_et() -> str:
    """Return today's date string in ET timezone (matches record_evaluation)."""
    return datetime.now(_ET).strftime("%Y-%m-%d")


def _now_utc_at_10am_et() -> datetime:
    """Return a UTC datetime corresponding to ~10:00 AM ET today.

    Needed because record_evaluation() uses datetime.now() for timestamps,
    so the stored trading_date will be today's real date. The clock must
    match so that health checks query the correct date.
    """
    now_et = datetime.now(_ET)
    # Replace time to 10:00 AM ET (well past 09:35 + 5min grace period)
    at_10am = now_et.replace(hour=10, minute=0, second=0, microsecond=0)
    return at_10am.astimezone(UTC)


async def _flush_pending_writes(max_wait: float = 1.0) -> None:
    """Yield to the event loop repeatedly to let fire-and-forget writes complete.

    The StrategyEvaluationBuffer uses ``loop.create_task(store.write_event(...))``
    which is non-blocking. We must give the loop time to actually run and
    complete these tasks before querying the database.
    """
    elapsed = 0.0
    step = 0.02
    while elapsed < max_wait:
        await asyncio.sleep(step)
        elapsed += step


# ---------------------------------------------------------------------------
# Test Strategy
# ---------------------------------------------------------------------------


class _TestStrategy(BaseStrategy):
    """Minimal strategy that records evaluations on every candle."""

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        if event.symbol not in self._watchlist:
            return None
        self.record_evaluation(
            symbol=event.symbol,
            event_type=EvaluationEventType.ENTRY_EVALUATION,
            result=EvaluationResult.FAIL,
            reason="test evaluation",
            metadata={"checks": {"volume_check": True, "price_check": False}},
        )
        return None

    async def on_tick(self, event: TickEvent) -> None:
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
            time_stop_minutes=30,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        return MarketConditionsFilter()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(
    strategy_id: str = "strat_test",
    earliest_entry: str = "09:35",
) -> StrategyConfig:
    """Create a StrategyConfig with the given operating window."""
    return StrategyConfig(
        strategy_id=strategy_id,
        name="Test Strategy",
        version="1.0.0",
        enabled=True,
        risk_limits=StrategyRiskLimits(),
        operating_window=OperatingWindow(earliest_entry=earliest_entry),
    )


def _make_candle(symbol: str = "AAPL") -> CandleEvent:
    """Create a CandleEvent for testing."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=150.0,
        high=151.0,
        low=149.0,
        close=150.5,
        volume=100_000,
        timestamp=datetime(2026, 3, 18, 10, 0, 0),
    )


@pytest.fixture
def strategy() -> _TestStrategy:
    """Create a test strategy with populated watchlist."""
    config = _make_config()
    strat = _TestStrategy(config)
    strat.is_active = True
    strat.set_watchlist(["AAPL", "NVDA"])
    return strat


@pytest.fixture
async def eval_store(tmp_path: Path) -> EvaluationEventStore:
    """Create an initialized EvaluationEventStore in a temp directory."""
    db_path = str(tmp_path / "telemetry_test.db")
    store = EvaluationEventStore(db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def health_monitor() -> HealthMonitor:
    """Create a HealthMonitor for testing.

    Uses today's real date at 10:00 AM ET so that health queries match
    the trading_date written by record_evaluation() (which uses datetime.now).
    """
    event_bus = EventBus()
    clock = FixedClock(_now_utc_at_10am_et())
    config = HealthConfig(
        heartbeat_interval_seconds=60,
        heartbeat_url_env="",
        alert_webhook_url_env="",
        daily_check_enabled=False,
        weekly_reconciliation_enabled=False,
    )
    return HealthMonitor(event_bus=event_bus, clock=clock, config=config)


# ---------------------------------------------------------------------------
# E2E Pipeline Tests
# ---------------------------------------------------------------------------


class TestE2EPipeline:
    """End-to-end tests: candle → ring buffer → SQLite → Observatory."""

    @pytest.mark.asyncio
    async def test_e2e_candle_to_ring_buffer(self, strategy: _TestStrategy) -> None:
        """Candle → strategy.on_candle() → record_evaluation() → ring buffer."""
        candle = _make_candle("AAPL")

        assert len(strategy.eval_buffer.query()) == 0
        await strategy.on_candle(candle)
        events = strategy.eval_buffer.query()
        assert len(events) == 1
        assert events[0].symbol == "AAPL"
        assert events[0].strategy_id == "strat_test"
        assert events[0].event_type == EvaluationEventType.ENTRY_EVALUATION

    @pytest.mark.asyncio
    async def test_e2e_ring_buffer_to_sqlite(
        self,
        strategy: _TestStrategy,
        eval_store: EvaluationEventStore,
    ) -> None:
        """Events in ring buffer are persisted to SQLite via set_store()."""
        strategy.eval_buffer.set_store(eval_store)

        candle = _make_candle("NVDA")
        await strategy.on_candle(candle)

        # Give the async write task a moment to complete
        await _flush_pending_writes()

        # Query SQLite directly
        rows = await eval_store.execute_query(
            "SELECT symbol, strategy_id, event_type FROM evaluation_events"
        )
        assert len(rows) == 1
        assert rows[0][0] == "NVDA"
        assert rows[0][1] == "strat_test"

    @pytest.mark.asyncio
    async def test_e2e_observatory_pipeline_has_data(
        self,
        strategy: _TestStrategy,
        eval_store: EvaluationEventStore,
    ) -> None:
        """ObservatoryService.get_pipeline_stages() returns non-empty data."""
        strategy.eval_buffer.set_store(eval_store)

        await strategy.on_candle(_make_candle("AAPL"))
        await _flush_pending_writes()

        observatory = ObservatoryService(
            telemetry_store=eval_store,
            universe_manager=None,
            quality_engine=None,
            strategies={"strat_test": strategy},
        )

        stages = await observatory.get_pipeline_stages(date=_today_et())
        assert stages["evaluating"] >= 1

    @pytest.mark.asyncio
    async def test_e2e_observatory_session_summary_has_data(
        self,
        strategy: _TestStrategy,
        eval_store: EvaluationEventStore,
    ) -> None:
        """ObservatoryService.get_session_summary() returns non-empty data."""
        strategy.eval_buffer.set_store(eval_store)

        await strategy.on_candle(_make_candle("AAPL"))
        await _flush_pending_writes()

        observatory = ObservatoryService(
            telemetry_store=eval_store,
            universe_manager=None,
            quality_engine=None,
            strategies={"strat_test": strategy},
        )

        summary = await observatory.get_session_summary(date=_today_et())
        assert summary["total_evaluations"] >= 1
        assert summary["symbols_evaluated"] >= 1


# ---------------------------------------------------------------------------
# Health Warning Tests
# ---------------------------------------------------------------------------


class TestHealthWarning:
    """Tests for check_strategy_evaluations() zero-evaluation detection."""

    @pytest.mark.asyncio
    async def test_health_warning_fires_zero_evaluations(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """WARNING fires: active strategy, non-empty watchlist, 0 evals, past window + 5 min."""
        config = _make_config(earliest_entry="09:35")
        strat = _TestStrategy(config)
        strat.is_active = True
        strat.set_watchlist(["AAPL", "NVDA"])

        clock = FixedClock(_now_utc_at_10am_et())

        await health_monitor.check_strategy_evaluations(
            strategies={"strat_test": strat},
            eval_store=eval_store,
            clock=clock,
        )

        component = health_monitor.get_status().get("strategy_strat_test")
        assert component is not None
        assert component.status == ComponentStatus.DEGRADED
        assert "0 evaluations" in component.message

    @pytest.mark.asyncio
    async def test_health_no_warning_with_evaluations(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """No warning when strategy has ≥1 evaluation event."""
        config = _make_config(earliest_entry="09:35")
        strat = _TestStrategy(config)
        strat.is_active = True
        strat.set_watchlist(["AAPL"])
        strat.eval_buffer.set_store(eval_store)

        # Deliver a candle to generate an evaluation event
        await strat.on_candle(_make_candle("AAPL"))
        await _flush_pending_writes()

        clock = FixedClock(_now_utc_at_10am_et())

        await health_monitor.check_strategy_evaluations(
            strategies={"strat_test": strat},
            eval_store=eval_store,
            clock=clock,
        )

        component = health_monitor.get_status().get("strategy_strat_test")
        # Either no component entry (no warning issued) or not DEGRADED
        assert component is None or component.status != ComponentStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_health_no_warning_empty_watchlist(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """No warning when strategy watchlist is empty (UM routed 0 symbols)."""
        config = _make_config(earliest_entry="09:35")
        strat = _TestStrategy(config)
        strat.is_active = True
        # Watchlist is empty — UM routed nothing

        clock = FixedClock(_now_utc_at_10am_et())

        await health_monitor.check_strategy_evaluations(
            strategies={"strat_test": strat},
            eval_store=eval_store,
            clock=clock,
        )

        component = health_monitor.get_status().get("strategy_strat_test")
        assert component is None  # No component entry created

    @pytest.mark.asyncio
    async def test_health_no_warning_before_window(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """No warning when current time is before window start + 5 min."""
        config = _make_config(earliest_entry="10:00")
        strat = _TestStrategy(config)
        strat.is_active = True
        strat.set_watchlist(["AAPL", "NVDA"])

        # Set clock to 10:03 AM ET today — before 10:00 + 5min = 10:05
        now_et = datetime.now(_ET)
        at_1003 = now_et.replace(hour=10, minute=3, second=0, microsecond=0)
        clock = FixedClock(at_1003.astimezone(UTC))

        await health_monitor.check_strategy_evaluations(
            strategies={"strat_test": strat},
            eval_store=eval_store,
            clock=clock,
        )

        component = health_monitor.get_status().get("strategy_strat_test")
        assert component is None  # No component entry created

    @pytest.mark.asyncio
    async def test_health_warning_self_corrects(
        self,
        health_monitor: HealthMonitor,
        eval_store: EvaluationEventStore,
    ) -> None:
        """Warning self-corrects when evaluations appear after initial 0-eval warning."""
        config = _make_config(earliest_entry="09:35")
        strat = _TestStrategy(config)
        strat.is_active = True
        strat.set_watchlist(["AAPL"])
        strat.eval_buffer.set_store(eval_store)

        clock = FixedClock(_now_utc_at_10am_et())

        # First check: 0 evaluations → DEGRADED
        await health_monitor.check_strategy_evaluations(
            strategies={"strat_test": strat},
            eval_store=eval_store,
            clock=clock,
        )
        component = health_monitor.get_status().get("strategy_strat_test")
        assert component is not None
        assert component.status == ComponentStatus.DEGRADED

        # Now generate an evaluation
        await strat.on_candle(_make_candle("AAPL"))
        await _flush_pending_writes()

        # Second check: evaluations present → self-corrects to HEALTHY
        await health_monitor.check_strategy_evaluations(
            strategies={"strat_test": strat},
            eval_store=eval_store,
            clock=clock,
        )
        component = health_monitor.get_status().get("strategy_strat_test")
        assert component is not None
        assert component.status == ComponentStatus.HEALTHY

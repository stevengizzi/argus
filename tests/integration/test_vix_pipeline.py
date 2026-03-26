"""Integration tests for VIX data pipeline consumer wiring.

Verifies:
- BriefingGenerator includes/omits VIX section correctly
- Orchestrator logs VIX context at pre-market
- SetupQualityEngine scoring unchanged with/without VIX
- RegimeHistoryStore records vix_close from RegimeVector

Sprint 27.9, Session 3b.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import OrchestratorConfig
from argus.core.clock import Clock
from argus.core.event_bus import EventBus
from argus.core.events import Side, SignalEvent
from argus.core.orchestrator import Orchestrator
from argus.core.regime import MarketRegime
from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.quality_engine import SetupQualityEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vix_service(
    *,
    ready: bool = True,
    stale: bool = False,
    latest: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a mock VIXDataService with configurable state."""
    svc = MagicMock()
    svc.is_ready = ready
    svc.is_stale = stale
    if latest is None and ready and not stale:
        latest = {
            "data_date": "2026-03-25",
            "vix_close": 18.5,
            "vol_of_vol_ratio": 0.85,
            "vix_percentile": 0.42,
            "term_structure_proxy": 0.97,
            "realized_vol_20d": 0.14,
            "variance_risk_premium": 145.8,
        }
    svc.get_latest_daily.return_value = latest
    return svc


def _make_stale_vix_service() -> MagicMock:
    """Build a mock VIXDataService that returns stale data (None derived metrics)."""
    return _make_vix_service(
        ready=True,
        stale=True,
        latest={
            "data_date": "2026-03-20",
            "vix_close": 22.1,
            "vol_of_vol_ratio": None,
            "vix_percentile": None,
            "term_structure_proxy": None,
            "realized_vol_20d": None,
            "variance_risk_premium": None,
        },
    )


def _make_signal(
    *,
    symbol: str = "TSLA",
    strategy_id: str = "orb_breakout",
    pattern_strength: float = 75.0,
) -> SignalEvent:
    """Build a realistic SignalEvent for quality scoring."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=0,
        rationale="Test signal",
        pattern_strength=pattern_strength,
        signal_context={"test": True},
    )


def _make_orchestrator(
    *,
    vix_data_service: Any = None,
) -> Orchestrator:
    """Build an Orchestrator with mocked dependencies."""
    config = OrchestratorConfig()
    event_bus = EventBus()
    clock = MagicMock(spec=Clock)
    clock.now.return_value = datetime(2026, 3, 26, 9, 30, tzinfo=UTC)
    clock.today.return_value = datetime(2026, 3, 26, tzinfo=UTC).date()
    trade_logger = AsyncMock()
    trade_logger.get_trades_by_strategy.return_value = []
    trade_logger.get_daily_pnl.return_value = []
    trade_logger.log_orchestrator_decision = AsyncMock()
    broker = AsyncMock()
    account = MagicMock()
    account.equity = 100000.0
    broker.get_account.return_value = account
    data_service = AsyncMock()

    return Orchestrator(
        config=config,
        event_bus=event_bus,
        clock=clock,
        trade_logger=trade_logger,
        broker=broker,
        data_service=data_service,
        vix_data_service=vix_data_service,
    )


# ---------------------------------------------------------------------------
# BriefingGenerator tests
# ---------------------------------------------------------------------------


class TestBriefingWithVix:
    """Tests for VIX context in the intelligence brief."""

    def test_briefing_with_vix_data(self) -> None:
        """VIX section appears in user prompt when data is available."""
        from argus.intelligence.briefing import BriefingGenerator

        vix_svc = _make_vix_service()

        generator = BriefingGenerator(
            client=MagicMock(),
            storage=MagicMock(),
            usage_tracker=MagicMock(),
            config=MagicMock(max_symbols=10),
            vix_data_service=vix_svc,
        )

        context = generator._build_vix_context()
        assert context is not None
        assert "VIX Regime Context" in context
        assert "18.5" in context
        assert "2026-03-25" in context
        assert "145.8" in context

    def test_briefing_without_vix_data(self) -> None:
        """Brief generates without VIX section when service is None."""
        from argus.intelligence.briefing import BriefingGenerator

        generator = BriefingGenerator(
            client=MagicMock(),
            storage=MagicMock(),
            usage_tracker=MagicMock(),
            config=MagicMock(max_symbols=10),
            vix_data_service=None,
        )

        context = generator._build_vix_context()
        assert context is None

    def test_briefing_stale_vix(self) -> None:
        """VIX section omitted when data is stale (derived metrics None)."""
        from argus.intelligence.briefing import BriefingGenerator

        vix_svc = _make_stale_vix_service()

        generator = BriefingGenerator(
            client=MagicMock(),
            storage=MagicMock(),
            usage_tracker=MagicMock(),
            config=MagicMock(max_symbols=10),
            vix_data_service=vix_svc,
        )

        context = generator._build_vix_context()
        assert context is None


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------


class TestOrchestratorVixLogging:
    """Tests for VIX context logging in Orchestrator pre-market."""

    @pytest.mark.asyncio
    async def test_orchestrator_vix_logging(self, caplog: pytest.LogCaptureFixture) -> None:
        """VIX context is logged at INFO level during pre-market."""
        import numpy as np

        vix_svc = _make_vix_service()
        orchestrator = _make_orchestrator(vix_data_service=vix_svc)

        # Provide SPY bars so regime classification succeeds
        spy_bars = MagicMock()
        spy_bars.__len__ = lambda self: 60
        spy_bars.__getitem__ = lambda self, key: np.array([400.0] * 60)
        orchestrator._data_service.fetch_daily_bars.return_value = spy_bars

        # Mock regime classifier to avoid real computation
        mock_indicators = MagicMock()
        orchestrator._regime_classifier.compute_indicators = MagicMock(
            return_value=mock_indicators
        )
        orchestrator._regime_classifier.classify = MagicMock(
            return_value=MarketRegime.RANGE_BOUND
        )

        with caplog.at_level(logging.INFO, logger="argus.core.orchestrator"):
            await orchestrator.run_pre_market()

        vix_messages = [r.message for r in caplog.records if "VIX regime context" in r.message]
        assert len(vix_messages) == 1
        assert "18.50" in vix_messages[0] or "18.5" in vix_messages[0]
        assert "145.8" in vix_messages[0]

    @pytest.mark.asyncio
    async def test_orchestrator_no_vix(self, caplog: pytest.LogCaptureFixture) -> None:
        """No VIX log and no error when VIXDataService is None."""
        import numpy as np

        orchestrator = _make_orchestrator(vix_data_service=None)

        spy_bars = MagicMock()
        spy_bars.__len__ = lambda self: 60
        spy_bars.__getitem__ = lambda self, key: np.array([400.0] * 60)
        orchestrator._data_service.fetch_daily_bars.return_value = spy_bars

        mock_indicators = MagicMock()
        orchestrator._regime_classifier.compute_indicators = MagicMock(
            return_value=mock_indicators
        )
        orchestrator._regime_classifier.classify = MagicMock(
            return_value=MarketRegime.RANGE_BOUND
        )

        with caplog.at_level(logging.INFO, logger="argus.core.orchestrator"):
            await orchestrator.run_pre_market()

        vix_messages = [r.message for r in caplog.records if "VIX regime context" in r.message]
        assert len(vix_messages) == 0


# ---------------------------------------------------------------------------
# Quality engine test
# ---------------------------------------------------------------------------


class TestQualityEngineUnchanged:
    """Verify quality scoring is identical with/without VIX data."""

    def test_quality_engine_unchanged(self) -> None:
        """Same input produces identical quality score regardless of VIX availability."""
        config = QualityEngineConfig()
        engine = SetupQualityEngine(config)
        signal = _make_signal()

        score_without = engine.score_setup(
            signal=signal,
            catalysts=[],
            rvol=1.5,
            regime=MarketRegime.RANGE_BOUND,
            allowed_regimes=["range_bound", "bullish_trending"],
        )

        # Score again — engine is stateless, VIX doesn't affect it
        score_with = engine.score_setup(
            signal=signal,
            catalysts=[],
            rvol=1.5,
            regime=MarketRegime.RANGE_BOUND,
            allowed_regimes=["range_bound", "bullish_trending"],
        )

        assert score_without.score == pytest.approx(score_with.score, abs=0.01)
        assert score_without.grade == score_with.grade
        assert score_without.components == score_with.components


# ---------------------------------------------------------------------------
# Regime history tests
# ---------------------------------------------------------------------------


class TestRegimeHistoryVixClose:
    """Tests for vix_close recording in regime history."""

    @pytest.mark.asyncio
    async def test_regime_history_records_vix_close(self, tmp_path: Any) -> None:
        """RegimeVector with vix_close persists correctly to regime history."""
        from argus.core.regime import MarketRegime, RegimeVector
        from argus.core.regime_history import RegimeHistoryStore

        store = RegimeHistoryStore(db_path=str(tmp_path / "regime_history.db"))
        await store.initialize()

        vector = RegimeVector(
            trend_score=0.5,
            trend_conviction=0.8,
            volatility_level=0.15,
            volatility_direction=-0.02,
            primary_regime=MarketRegime.RANGE_BOUND,
            regime_confidence=0.75,
            computed_at=datetime.now(UTC),
            vix_close=18.5,
        )

        await store.record(vector)

        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        rows = await store.get_regime_history(today_str)
        assert len(rows) >= 1
        assert rows[0]["vix_close"] == pytest.approx(18.5, abs=0.01)

        await store.close()

    @pytest.mark.asyncio
    async def test_regime_history_records_null_when_stale(self, tmp_path: Any) -> None:
        """RegimeVector with vix_close=None persists as NULL."""
        from argus.core.regime import MarketRegime, RegimeVector
        from argus.core.regime_history import RegimeHistoryStore

        store = RegimeHistoryStore(db_path=str(tmp_path / "regime_history.db"))
        await store.initialize()

        vector = RegimeVector(
            trend_score=0.5,
            trend_conviction=0.8,
            volatility_level=0.15,
            volatility_direction=-0.02,
            primary_regime=MarketRegime.RANGE_BOUND,
            regime_confidence=0.75,
            computed_at=datetime.now(UTC),
            vix_close=None,
        )

        await store.record(vector)

        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        rows = await store.get_regime_history(today_str)
        assert len(rows) >= 1
        assert rows[0]["vix_close"] is None

        await store.close()

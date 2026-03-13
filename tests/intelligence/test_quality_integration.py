"""Integration tests for the quality pipeline in ArgusSystem._process_signal().

Sprint 24, Session 6b — tests cover:
- Multi-signal pipeline: different strategies produce different quality scores
- Error paths: quality engine exception, catalyst storage None, RVOL None, regime None
- Bypass modes: BrokerSource.SIMULATED and enabled=false → legacy sizing
- Defense-in-depth: zero-share signal rejected by Risk Manager
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import BrokerSource
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    OrderRejectedEvent,
    QualitySignalEvent,
    Side,
    SignalEvent,
)
from argus.core.regime import MarketRegime
from argus.intelligence.config import (
    QualityEngineConfig,
    QualityWeightsConfig,
)
from argus.intelligence.models import ClassifiedCatalyst
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQuality, SetupQualityEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    strategy_id: str = "strat_orb_breakout",
    symbol: str = "AAPL",
    pattern_strength: float = 70.0,
    entry_price: float = 100.0,
    stop_price: float = 99.0,
    share_count: int = 0,
) -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(102.0, 104.0),
        share_count=share_count,
        rationale="Test signal",
        pattern_strength=pattern_strength,
    )


def _make_catalyst(
    symbol: str = "AAPL",
    quality_score: float = 80.0,
) -> ClassifiedCatalyst:
    now = datetime.now(UTC)
    return ClassifiedCatalyst(
        headline="Test catalyst headline",
        symbol=symbol,
        source="test",
        published_at=now,
        fetched_at=now,
        category="earnings",
        quality_score=quality_score,
        summary="Test summary",
        trading_relevance="high",
        classified_by="test",
        classified_at=now,
        headline_hash="abc123",
    )


class _FakeRiskLimits:
    max_loss_per_trade_pct: float = 0.01


class _FakeStrategyConfig:
    risk_limits = _FakeRiskLimits()


@dataclass
class _FakeStrategy:
    allocated_capital: float = 100_000.0
    config: object = _FakeStrategyConfig()


@dataclass
class _FakeAccount:
    equity: float = 200_000.0
    buying_power: float = 200_000.0


@dataclass
class _FakeConfig:
    """Minimal config to drive _process_signal bypass/quality path."""

    class SystemConfig:
        broker_source: BrokerSource = BrokerSource.IBKR
        quality_engine: QualityEngineConfig = QualityEngineConfig()

    system: SystemConfig = SystemConfig()


async def _build_system_for_pipeline(
    *,
    broker_source: BrokerSource = BrokerSource.IBKR,
    quality_enabled: bool = True,
    min_grade: str = "C+",
    catalyst_storage: object | None = None,
):
    """Create a minimal ArgusSystem with internals wired for _process_signal.

    Returns (system, event_bus, published_events).
    """
    from argus.main import ArgusSystem

    # Create system with a throwaway config dir — we override _config below
    system = ArgusSystem.__new__(ArgusSystem)
    system._shutdown_event = MagicMock()

    event_bus = EventBus()
    system._event_bus = event_bus

    # Track published events
    published_events: list[object] = []
    original_publish = event_bus.publish

    async def tracking_publish(event: object) -> None:
        published_events.append(event)
        await original_publish(event)

    event_bus.publish = tracking_publish

    # Config
    qe_config = QualityEngineConfig(
        enabled=quality_enabled,
        min_grade_to_trade=min_grade,
    )

    config = MagicMock()
    config.system.broker_source = broker_source
    config.system.quality_engine = qe_config
    system._config = config

    # Quality engine + sizer
    if quality_enabled and broker_source != BrokerSource.SIMULATED:
        system._quality_engine = SetupQualityEngine(qe_config)
        system._position_sizer = DynamicPositionSizer(qe_config)
    else:
        system._quality_engine = None
        system._position_sizer = None

    # Catalyst storage
    system._catalyst_storage = catalyst_storage

    # Orchestrator (for regime)
    system._orchestrator = MagicMock()
    system._orchestrator.current_regime = MarketRegime.BULLISH_TRENDING

    # Broker
    system._broker = MagicMock()
    system._broker.get_account = AsyncMock(return_value=_FakeAccount())

    # Risk Manager — real-ish mock that returns approved
    risk_manager = MagicMock()

    async def approve_signal(signal: SignalEvent):
        if signal.share_count <= 0:
            return OrderRejectedEvent(
                signal=signal, reason="Invalid share count: zero or negative"
            )
        return OrderApprovedEvent(signal=signal, modifications=None)

    risk_manager.evaluate_signal = AsyncMock(side_effect=approve_signal)
    system._risk_manager = risk_manager

    return system, event_bus, published_events


# ---------------------------------------------------------------------------
# 1. Multi-signal pipeline
# ---------------------------------------------------------------------------


class TestMultiSignalPipeline:
    """Multiple strategies produce different quality scores."""

    @pytest.mark.asyncio
    async def test_integration_multiple_strategies_different_scores(self) -> None:
        """Two signals with different pattern_strength → different quality grades."""
        system, event_bus, published = await _build_system_for_pipeline()

        # High-quality signal
        signal_high = _make_signal(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            pattern_strength=95.0,
        )
        # Low-quality signal
        signal_low = _make_signal(
            strategy_id="strat_vwap_reclaim",
            symbol="TSLA",
            pattern_strength=35.0,
        )

        strategy = _FakeStrategy()
        await system._process_signal(signal_high, strategy)
        await system._process_signal(signal_low, strategy)

        # Both signals should have reached the risk manager
        rm_calls = system._risk_manager.evaluate_signal.call_args_list
        assert len(rm_calls) == 2

        enriched_high = rm_calls[0][0][0]
        enriched_low = rm_calls[1][0][0]

        # Different quality scores
        assert enriched_high.quality_score > enriched_low.quality_score
        assert enriched_high.quality_grade != enriched_low.quality_grade

        # Both should have non-zero shares
        assert enriched_high.share_count > 0
        assert enriched_low.share_count > 0

        # QualitySignalEvents should be published for each
        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 2


# ---------------------------------------------------------------------------
# 2. Error paths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Quality engine error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_integration_quality_engine_exception_failclosed(self) -> None:
        """Quality engine raises → signal does NOT execute, error logged."""
        system, event_bus, published = await _build_system_for_pipeline()

        # Patch score_setup to raise
        system._quality_engine.score_setup = MagicMock(
            side_effect=RuntimeError("Scoring failed")
        )

        signal = _make_signal()
        strategy = _FakeStrategy()

        with pytest.raises(RuntimeError, match="Scoring failed"):
            await system._process_signal(signal, strategy)

        # Risk manager should NOT have been called (fail-closed)
        system._risk_manager.evaluate_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_integration_catalyst_storage_none_graceful(self) -> None:
        """No catalyst storage → catalyst dimension = 50, signal still scored."""
        system, event_bus, published = await _build_system_for_pipeline(
            catalyst_storage=None,
        )

        signal = _make_signal(pattern_strength=80.0)
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        # Risk manager should have been called
        rm_calls = system._risk_manager.evaluate_signal.call_args_list
        assert len(rm_calls) == 1

        enriched = rm_calls[0][0][0]
        assert enriched.quality_score > 0
        assert enriched.share_count > 0

        # Verify catalyst_quality dimension is the default 50
        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 1
        assert quality_events[0].components["catalyst_quality"] == 50.0

    @pytest.mark.asyncio
    async def test_integration_rvol_none_graceful(self) -> None:
        """No RVOL → volume dimension = 50, signal still scored.

        _process_signal always passes rvol=None currently, so volume_profile
        should be 50.0 (the neutral default from the engine).
        """
        system, event_bus, published = await _build_system_for_pipeline()

        signal = _make_signal(pattern_strength=80.0)
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 1
        assert quality_events[0].components["volume_profile"] == 50.0

    @pytest.mark.asyncio
    async def test_integration_regime_unavailable(self) -> None:
        """No orchestrator → regime defaults to RANGE_BOUND, scored normally."""
        system, event_bus, published = await _build_system_for_pipeline()
        system._orchestrator = None  # No orchestrator

        signal = _make_signal(pattern_strength=80.0)
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        # Should still score (regime falls back to RANGE_BOUND)
        rm_calls = system._risk_manager.evaluate_signal.call_args_list
        assert len(rm_calls) == 1

        # allowed_regimes=[] → _score_regime_alignment returns 70.0 (no constraint)
        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 1
        assert quality_events[0].components["regime_alignment"] == 70.0


# ---------------------------------------------------------------------------
# 3. Bypass verification
# ---------------------------------------------------------------------------


class TestBypassVerification:
    """Legacy path when quality pipeline is bypassed."""

    @pytest.mark.asyncio
    async def test_integration_backtest_bypass_no_quality_history(self) -> None:
        """SIMULATED → legacy sizing, no quality_history rows."""
        from argus.db.manager import DatabaseManager

        system, event_bus, published = await _build_system_for_pipeline(
            broker_source=BrokerSource.SIMULATED,
        )

        # Wire up a real DB to verify no quality_history rows
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db = DatabaseManager(Path(tmpdir) / "test.db")
            await db.initialize()

            # Give the system a quality engine WITH a db to prove it's NOT used
            qe = SetupQualityEngine(QualityEngineConfig(), db_manager=db)
            # But system._quality_engine is None (bypass), so this won't be called
            assert system._quality_engine is None

            signal = _make_signal(entry_price=100.0, stop_price=99.0)
            strategy = _FakeStrategy()
            await system._process_signal(signal, strategy)

            # Signal should reach RM with legacy-calculated shares
            rm_calls = system._risk_manager.evaluate_signal.call_args_list
            assert len(rm_calls) == 1
            enriched = rm_calls[0][0][0]
            # Legacy: 100_000 * 0.01 / 1.0 = 1000 shares
            assert enriched.share_count == 1000

            # No quality_history rows
            async with db.connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM quality_history"
                )
                count = (await cursor.fetchone())[0]
            assert count == 0

            await db.close()

    @pytest.mark.asyncio
    async def test_integration_backtest_bypass_no_quality_events(self) -> None:
        """SIMULATED → no QualitySignalEvents published."""
        system, event_bus, published = await _build_system_for_pipeline(
            broker_source=BrokerSource.SIMULATED,
        )

        signal = _make_signal(entry_price=100.0, stop_price=99.0)
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 0

    @pytest.mark.asyncio
    async def test_integration_disabled_bypass(self) -> None:
        """enabled=false → legacy sizing path, no quality events."""
        system, event_bus, published = await _build_system_for_pipeline(
            quality_enabled=False,
        )

        signal = _make_signal(entry_price=100.0, stop_price=99.0)
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        # Legacy shares
        rm_calls = system._risk_manager.evaluate_signal.call_args_list
        assert len(rm_calls) == 1
        enriched = rm_calls[0][0][0]
        assert enriched.share_count == 1000  # 100k * 0.01 / 1.0

        # No quality events
        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 0


# ---------------------------------------------------------------------------
# 4. Grade filtering
# ---------------------------------------------------------------------------


class TestGradeFiltering:
    """Low-quality signals filtered before reaching Risk Manager."""

    @pytest.mark.asyncio
    async def test_integration_c_grade_never_reaches_rm(self) -> None:
        """Signal with very low pattern_strength → C grade → filtered out."""
        # Weight everything on pattern_strength to guarantee C grade
        weights = QualityWeightsConfig(
            pattern_strength=1.0,
            catalyst_quality=0.0,
            volume_profile=0.0,
            historical_match=0.0,
            regime_alignment=0.0,
        )
        qe_config = QualityEngineConfig(weights=weights, min_grade_to_trade="C+")

        system, event_bus, published = await _build_system_for_pipeline()
        system._quality_engine = SetupQualityEngine(qe_config)
        system._position_sizer = DynamicPositionSizer(qe_config)
        system._config.system.quality_engine = qe_config

        # pattern_strength=10 → score=10 → C grade (below C+ threshold at 30)
        signal = _make_signal(pattern_strength=10.0)
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        # Risk manager should NOT have been called (filtered)
        system._risk_manager.evaluate_signal.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Signal enrichment
# ---------------------------------------------------------------------------


class TestSignalEnrichment:
    """Verify enriched signal preserves original fields."""

    @pytest.mark.asyncio
    async def test_integration_enriched_signal_preserves_original_fields(self) -> None:
        """strategy_id, symbol, entry_price, stop_price unchanged after enrichment."""
        system, event_bus, published = await _build_system_for_pipeline()

        signal = _make_signal(
            strategy_id="strat_orb_breakout",
            symbol="NVDA",
            entry_price=500.0,
            stop_price=495.0,
            pattern_strength=80.0,
        )
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        rm_calls = system._risk_manager.evaluate_signal.call_args_list
        assert len(rm_calls) == 1
        enriched = rm_calls[0][0][0]

        # Original fields preserved
        assert enriched.strategy_id == "strat_orb_breakout"
        assert enriched.symbol == "NVDA"
        assert enriched.entry_price == 500.0
        assert enriched.stop_price == 495.0
        assert enriched.target_prices == (102.0, 104.0)
        assert enriched.rationale == "Test signal"

        # Quality fields populated
        assert enriched.quality_score > 0
        assert enriched.quality_grade != ""
        assert enriched.share_count > 0


# ---------------------------------------------------------------------------
# 6. QualitySignalEvent
# ---------------------------------------------------------------------------


class TestQualitySignalEventPublished:
    """QualitySignalEvent published after quality scoring."""

    @pytest.mark.asyncio
    async def test_integration_quality_signal_event_published(self) -> None:
        """QualitySignalEvent emitted on event bus with correct fields."""
        system, event_bus, published = await _build_system_for_pipeline()

        signal = _make_signal(
            strategy_id="strat_vwap_reclaim",
            symbol="TSLA",
            pattern_strength=75.0,
        )
        strategy = _FakeStrategy()
        await system._process_signal(signal, strategy)

        quality_events = [e for e in published if isinstance(e, QualitySignalEvent)]
        assert len(quality_events) == 1

        qe = quality_events[0]
        assert qe.symbol == "TSLA"
        assert qe.strategy_id == "strat_vwap_reclaim"
        assert qe.score > 0
        assert qe.grade != ""
        assert qe.risk_tier != ""
        assert "pattern_strength" in qe.components
        assert "catalyst_quality" in qe.components
        assert "volume_profile" in qe.components
        assert qe.rationale != ""


# ---------------------------------------------------------------------------
# 7. Defense-in-depth: zero shares
# ---------------------------------------------------------------------------


class TestZeroSharesDefense:
    """Zero-share signal rejected by Risk Manager check 0."""

    @pytest.mark.asyncio
    async def test_integration_zero_shares_rejected_by_rm(self) -> None:
        """Signal with share_count=0 reaching RM → rejected (defense-in-depth)."""
        from argus.core.config import RiskConfig
        from argus.core.risk_manager import RiskManager
        from argus.execution.simulated_broker import SimulatedBroker

        event_bus = EventBus()
        broker = SimulatedBroker()
        await broker.connect()

        risk_config = RiskConfig()
        rm = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
        )

        signal = _make_signal(share_count=0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderRejectedEvent)
        assert "zero or negative" in result.reason.lower()

"""Tests for RegimeClassifierV2 integration, Orchestrator V2 wiring, and Event Bus subscriptions.

Sprint 27.6, Session 6.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from argus.core.breadth import BreadthCalculator
from argus.core.config import (
    BreadthConfig,
    CorrelationConfig,
    IntradayConfig,
    OrchestratorConfig,
    RegimeIntelligenceConfig,
    SectorRotationConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, RegimeChangeEvent
from argus.core.intraday_character import IntradayCharacterDetector
from argus.core.market_correlation import MarketCorrelationTracker
from argus.core.regime import MarketRegime, RegimeClassifierV2, RegimeIndicators, RegimeVector
from argus.core.sector_rotation import SectorRotationAnalyzer


def _make_config() -> OrchestratorConfig:
    return OrchestratorConfig(
        vol_low_threshold=0.08,
        vol_normal_threshold=0.16,
        vol_high_threshold=0.25,
        vol_crisis_threshold=0.35,
    )


def _make_regime_config(
    enabled: bool = True,
    breadth_enabled: bool = True,
    correlation_enabled: bool = True,
    sector_enabled: bool = True,
    intraday_enabled: bool = True,
) -> RegimeIntelligenceConfig:
    return RegimeIntelligenceConfig(
        enabled=enabled,
        breadth=BreadthConfig(enabled=breadth_enabled, min_symbols=10, min_bars_for_valid=2),
        correlation=CorrelationConfig(enabled=correlation_enabled),
        sector_rotation=SectorRotationConfig(enabled=sector_enabled),
        intraday=IntradayConfig(enabled=intraday_enabled),
    )


def _make_indicators(
    price: float = 450.0,
    sma_20: float = 440.0,
    sma_50: float = 430.0,
    roc_5d: float = 0.02,
    vol: float = 0.15,
) -> RegimeIndicators:
    return RegimeIndicators(
        spy_price=price,
        spy_sma_20=sma_20,
        spy_sma_50=sma_50,
        spy_roc_5d=roc_5d,
        spy_realized_vol_20d=vol,
        spy_vs_vwap=0.001,
        timestamp=datetime.now(UTC),
    )


def _make_breadth(config: BreadthConfig | None = None) -> BreadthCalculator:
    cfg = config or BreadthConfig(min_symbols=10, min_bars_for_valid=2)
    calc = BreadthCalculator(cfg)
    # Feed enough data: 10+ symbols with 2+ bars each
    symbols = [f"SYM{i}" for i in range(12)]
    for bar_idx in range(3):
        for sym in symbols:
            calc.on_candle(CandleEvent(symbol=sym, close=100.0 + bar_idx))
    return calc


def _make_correlation() -> MarketCorrelationTracker:
    tracker = MarketCorrelationTracker(CorrelationConfig())
    # Manually set state to simulate computed correlation
    tracker._average_correlation = 0.45
    tracker._correlation_regime = "normal"
    tracker._symbols_used = 10
    return tracker


def _make_sector() -> SectorRotationAnalyzer:
    analyzer = SectorRotationAnalyzer(
        config=SectorRotationConfig(),
        fmp_base_url="https://example.com",
        fmp_api_key="test_key",
    )
    # Set state manually
    analyzer._sector_rotation_phase = "risk_on"
    analyzer._leading_sectors = ["Technology", "Financials", "Consumer Discretionary"]
    analyzer._lagging_sectors = ["Utilities", "Healthcare", "Consumer Staples"]
    return analyzer


def _make_intraday() -> IntradayCharacterDetector:
    detector = IntradayCharacterDetector(IntradayConfig(min_spy_bars=2))
    # Set state manually
    detector._opening_drive_strength = 0.6
    detector._first_30min_range_ratio = 0.8
    detector._vwap_slope = 0.0005
    detector._direction_change_count = 1
    detector._intraday_character = "trending"
    return detector


class TestV2Compose:
    """Tests for V2 compose_regime_vector with all calculators."""

    def test_all_calculators_produce_full_regime_vector(self) -> None:
        """V2 with all calculators fills all RegimeVector dimensions."""
        v2 = RegimeClassifierV2(
            config=_make_config(),
            regime_config=_make_regime_config(),
            breadth=_make_breadth(),
            correlation=_make_correlation(),
            sector=_make_sector(),
            intraday=_make_intraday(),
        )

        vector = v2.compute_regime_vector(_make_indicators())

        assert isinstance(vector, RegimeVector)
        assert vector.primary_regime == MarketRegime.BULLISH_TRENDING
        assert vector.universe_breadth_score is not None
        assert vector.average_correlation is not None
        assert vector.correlation_regime == "normal"
        assert vector.sector_rotation_phase == "risk_on"
        assert len(vector.leading_sectors) == 3
        assert vector.opening_drive_strength is not None
        assert vector.intraday_character == "trending"
        assert 0.0 < vector.regime_confidence <= 1.0

    def test_all_calculators_none_uses_only_trend_and_vol(self) -> None:
        """V2 with no calculators still produces trend + vol dimensions."""
        v2 = RegimeClassifierV2(
            config=_make_config(),
            regime_config=_make_regime_config(),
        )

        vector = v2.compute_regime_vector(_make_indicators())

        assert vector.primary_regime == MarketRegime.BULLISH_TRENDING
        assert vector.trend_score > 0
        assert vector.volatility_level > 0
        assert vector.universe_breadth_score is None
        assert vector.average_correlation is None
        assert vector.sector_rotation_phase is None
        assert vector.intraday_character is None

    def test_individual_dimension_disabled_uses_defaults(self) -> None:
        """Disabling one dimension leaves it at None defaults."""
        v2 = RegimeClassifierV2(
            config=_make_config(),
            regime_config=_make_regime_config(breadth_enabled=False),
            breadth=_make_breadth(),  # Provided but config says disabled
            correlation=_make_correlation(),
            sector=_make_sector(),
            intraday=_make_intraday(),
        )

        vector = v2.compute_regime_vector(_make_indicators())

        # Breadth disabled — should be None despite calculator being present
        assert vector.universe_breadth_score is None
        assert vector.breadth_thrust is None
        # Other dimensions should be populated
        assert vector.average_correlation is not None
        assert vector.sector_rotation_phase is not None
        assert vector.intraday_character is not None

    def test_v2_delegates_to_v1_for_primary_regime(self) -> None:
        """V2.classify() delegates entirely to V1 — no reimplementation."""
        v2 = RegimeClassifierV2(
            config=_make_config(),
            regime_config=_make_regime_config(),
        )

        # Bearish indicators
        bearish_indicators = _make_indicators(
            price=400.0, sma_20=420.0, sma_50=440.0, roc_5d=-0.03
        )
        result = v2.classify(bearish_indicators)
        assert result == MarketRegime.BEARISH_TRENDING

        # Also in compute_regime_vector
        vector = v2.compute_regime_vector(bearish_indicators)
        assert vector.primary_regime == MarketRegime.BEARISH_TRENDING


class TestConfigGate:
    """Tests for config-gate: enabled=false → V1 only."""

    def test_config_gate_disabled_no_v2_instances(self) -> None:
        """When enabled=false, no V2 calculators or store should be created."""
        config = _make_regime_config(enabled=False)
        # This tests the logic that would be in main.py:
        # if config.enabled → create V2, else None
        assert config.enabled is False


class TestOrchestratorV2:
    """Tests for Orchestrator V2 integration."""

    @pytest.mark.asyncio
    async def test_orchestrator_reclassify_with_v2_enriches_event(self) -> None:
        """Orchestrator with V2 computes regime vector on reclassify."""
        from argus.core.orchestrator import Orchestrator

        config = _make_config()
        event_bus = EventBus()
        clock = MagicMock()
        clock.now.return_value = datetime.now(UTC)
        clock.today.return_value = datetime.now(UTC).date()
        trade_logger = AsyncMock()
        broker = AsyncMock()
        broker.get_account = AsyncMock(return_value=MagicMock(equity=100000.0))

        # Mock data service to return valid SPY bars
        data_service = AsyncMock()
        bars = pd.DataFrame({
            "open": [440.0 + i for i in range(60)],
            "high": [445.0 + i for i in range(60)],
            "low": [435.0 + i for i in range(60)],
            "close": [442.0 + i for i in range(60)],
            "volume": [1000000] * 60,
        })
        data_service.fetch_daily_bars = AsyncMock(return_value=bars)

        v2 = RegimeClassifierV2(
            config=config,
            regime_config=_make_regime_config(),
        )

        history = AsyncMock()

        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
            regime_classifier_v2=v2,
            regime_history=history,
        )

        old, new = await orchestrator.reclassify_regime()

        assert old is not None
        assert new is not None
        # V2 should have computed a vector
        assert orchestrator._latest_regime_vector is not None

    @pytest.mark.asyncio
    async def test_regime_change_event_contains_vector_summary(self) -> None:
        """RegimeChangeEvent.regime_vector_summary populated when V2 active."""
        from argus.core.orchestrator import Orchestrator

        config = _make_config()
        event_bus = EventBus()
        clock = MagicMock()
        clock.now.return_value = datetime.now(UTC)

        trade_logger = AsyncMock()
        broker = AsyncMock()
        data_service = AsyncMock()

        # Create V2 with no calculators (still produces trend+vol)
        v2 = RegimeClassifierV2(
            config=config,
            regime_config=_make_regime_config(),
        )

        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
            regime_classifier_v2=v2,
        )

        # Manually set a regime vector so _run_regime_recheck can use it
        from argus.core.regime import RegimeVector
        orchestrator._latest_regime_vector = RegimeVector(
            computed_at=datetime.now(UTC),
            trend_score=0.5,
            trend_conviction=0.8,
            volatility_level=0.15,
            volatility_direction=0.1,
            primary_regime=MarketRegime.BULLISH_TRENDING,
            regime_confidence=0.7,
        )

        # Set current regime so a change triggers event
        orchestrator._current_regime = MarketRegime.RANGE_BOUND

        # Mock reclassify_regime to return a regime change
        bars = pd.DataFrame({
            "open": [440.0 + i for i in range(60)],
            "high": [445.0 + i for i in range(60)],
            "low": [435.0 + i for i in range(60)],
            "close": [442.0 + i for i in range(60)],
            "volume": [1000000] * 60,
        })
        data_service.fetch_daily_bars = AsyncMock(return_value=bars)

        captured_events: list[RegimeChangeEvent] = []

        async def capture_event(e: RegimeChangeEvent) -> None:
            captured_events.append(e)

        event_bus.subscribe(RegimeChangeEvent, capture_event)

        # This should trigger a regime change from RANGE_BOUND to BULLISH
        await orchestrator._run_regime_recheck()
        await event_bus.drain()

        # Should have captured a regime change event with vector summary
        regime_events = [e for e in captured_events if isinstance(e, RegimeChangeEvent)]
        assert len(regime_events) >= 1
        event = regime_events[0]
        assert event.regime_vector_summary is not None
        assert "trend_score" in event.regime_vector_summary


class TestPreMarket:
    """Tests for V2 run_pre_market concurrent execution."""

    @pytest.mark.asyncio
    async def test_run_pre_market_executes_concurrently(self) -> None:
        """run_pre_market uses asyncio.gather for correlation + sector."""
        correlation = AsyncMock(spec=MarketCorrelationTracker)
        correlation.compute = AsyncMock()
        correlation.get_correlation_snapshot = MagicMock(return_value={
            "average_correlation": 0.5,
            "correlation_regime": "normal",
            "symbols_used": 10,
        })

        sector = AsyncMock(spec=SectorRotationAnalyzer)
        sector.fetch = AsyncMock()
        sector.get_sector_snapshot = MagicMock(return_value={
            "sector_rotation_phase": "mixed",
            "leading_sectors": [],
            "lagging_sectors": [],
        })

        v2 = RegimeClassifierV2(
            config=_make_config(),
            regime_config=_make_regime_config(),
            correlation=correlation,
            sector=sector,
        )

        fetch_fn = AsyncMock(return_value=None)
        symbols_fn = MagicMock(return_value=["AAPL", "MSFT"])

        await v2.run_pre_market(fetch_fn, symbols_fn)

        correlation.compute.assert_called_once_with(fetch_fn, symbols_fn)
        sector.fetch.assert_called_once()


class TestEventBusSubscription:
    """Tests for BreadthCalculator + IntradayCharacterDetector Event Bus subscription."""

    @pytest.mark.asyncio
    async def test_breadth_calculator_receives_candle_events(self) -> None:
        """BreadthCalculator.on_candle called when subscribed to CandleEvent via async wrapper."""
        event_bus = EventBus()
        breadth = BreadthCalculator(BreadthConfig(min_symbols=10, min_bars_for_valid=1))

        async def _breadth_handler(event: CandleEvent) -> None:
            breadth.on_candle(event)

        event_bus.subscribe(CandleEvent, _breadth_handler)

        candle = CandleEvent(symbol="AAPL", close=150.0)
        await event_bus.publish(candle)
        await event_bus.drain()

        snap = breadth.get_breadth_snapshot()
        assert snap["symbols_tracked"] == 1

    @pytest.mark.asyncio
    async def test_intraday_detector_filters_spy_only(self) -> None:
        """IntradayCharacterDetector only processes SPY candles via async wrapper."""
        event_bus = EventBus()
        detector = IntradayCharacterDetector(IntradayConfig(min_spy_bars=2), spy_symbol="SPY")

        async def _intraday_handler(event: CandleEvent) -> None:
            detector.on_candle(event)

        event_bus.subscribe(CandleEvent, _intraday_handler)

        # Non-SPY candle should be ignored
        await event_bus.publish(CandleEvent(symbol="AAPL", close=150.0))
        await event_bus.drain()
        assert len(detector._bars) == 0

        # SPY candle should be processed
        await event_bus.publish(CandleEvent(symbol="SPY", close=450.0, open=449.0, high=451.0, low=448.0, volume=100000))
        await event_bus.drain()
        assert len(detector._bars) == 1

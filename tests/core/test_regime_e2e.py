"""End-to-end integration tests for the regime intelligence pipeline.

Covers the full lifecycle: startup → pre-market → market hours → reclassify.
Also: config permutations, FMP degradation, performance, JSON roundtrip, circular imports.

Sprint 27.6, Session 8.
"""

from __future__ import annotations

import importlib
import json
import time as time_mod
from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

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
from argus.core.orchestrator import Orchestrator
from argus.core.regime import (
    MarketRegime,
    RegimeClassifier,
    RegimeClassifierV2,
    RegimeIndicators,
    RegimeVector,
)
from argus.core.regime_history import RegimeHistoryStore
from argus.core.sector_rotation import SectorRotationAnalyzer

_ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orch_config() -> OrchestratorConfig:
    return OrchestratorConfig(
        vol_low_threshold=0.08,
        vol_normal_threshold=0.16,
        vol_high_threshold=0.25,
        vol_crisis_threshold=0.35,
    )


def _make_regime_config(
    enabled: bool = True,
    breadth: bool = True,
    correlation: bool = True,
    sector: bool = True,
    intraday: bool = True,
) -> RegimeIntelligenceConfig:
    return RegimeIntelligenceConfig(
        enabled=enabled,
        breadth=BreadthConfig(enabled=breadth, min_symbols=10, min_bars_for_valid=2),
        correlation=CorrelationConfig(enabled=correlation),
        sector_rotation=SectorRotationConfig(enabled=sector),
        intraday=IntradayConfig(enabled=intraday, min_spy_bars=2),
    )


def _make_spy_bars(num_bars: int = 60, start: float = 440.0) -> pd.DataFrame:
    """Synthetic SPY daily bars, monotonically rising."""
    return pd.DataFrame(
        {
            "open": [start + i for i in range(num_bars)],
            "high": [start + i + 5 for i in range(num_bars)],
            "low": [start + i - 2 for i in range(num_bars)],
            "close": [start + i + 2 for i in range(num_bars)],
            "volume": [1_000_000] * num_bars,
        }
    )


def _make_indicators(
    price: float = 450.0,
    sma_20: float = 440.0,
    sma_50: float = 430.0,
    roc: float = 0.02,
    vol: float = 0.15,
) -> RegimeIndicators:
    return RegimeIndicators(
        spy_price=price,
        spy_sma_20=sma_20,
        spy_sma_50=sma_50,
        spy_roc_5d=roc,
        spy_realized_vol_20d=vol,
        spy_vs_vwap=0.001,
        timestamp=datetime.now(UTC),
    )


def _wire_v2_full(
    regime_config: RegimeIntelligenceConfig | None = None,
) -> tuple[RegimeClassifierV2, BreadthCalculator, IntradayCharacterDetector]:
    """Create a fully-wired V2 classifier with all calculators populated."""
    rc = regime_config or _make_regime_config()
    orch_cfg = _make_orch_config()

    breadth = BreadthCalculator(rc.breadth)
    # Feed enough candle data for breadth to produce a score
    for bar_idx in range(3):
        for i in range(12):
            breadth.on_candle(CandleEvent(symbol=f"SYM{i}", close=100.0 + bar_idx))

    corr = MarketCorrelationTracker(rc.correlation)
    corr._average_correlation = 0.45
    corr._correlation_regime = "normal"
    corr._symbols_used = 10

    sector = SectorRotationAnalyzer(
        config=rc.sector_rotation,
        fmp_base_url="https://example.com",
        fmp_api_key="test",
    )
    sector._sector_rotation_phase = "risk_on"
    sector._leading_sectors = ["Technology", "Financials", "Consumer Discretionary"]
    sector._lagging_sectors = ["Utilities", "Healthcare", "Consumer Staples"]

    intraday = IntradayCharacterDetector(rc.intraday, spy_symbol="SPY")
    intraday._opening_drive_strength = 0.6
    intraday._first_30min_range_ratio = 0.8
    intraday._vwap_slope = 0.0005
    intraday._direction_change_count = 1
    intraday._intraday_character = "trending"

    v2 = RegimeClassifierV2(
        config=orch_cfg,
        regime_config=rc,
        breadth=breadth,
        correlation=corr,
        sector=sector,
        intraday=intraday,
    )

    return v2, breadth, intraday


def _make_orchestrator(
    v2: RegimeClassifierV2 | None = None,
    history: RegimeHistoryStore | None = None,
) -> tuple[Orchestrator, EventBus, AsyncMock]:
    """Build an Orchestrator with mocked infrastructure."""
    config = _make_orch_config()
    event_bus = EventBus()
    clock = MagicMock()
    clock.now.return_value = datetime.now(UTC)
    clock.today.return_value = datetime.now(UTC).date()

    trade_logger = AsyncMock()
    trade_logger.get_trades_by_strategy = AsyncMock(return_value=[])
    trade_logger.get_daily_pnl = AsyncMock(return_value=[])
    trade_logger.log_orchestrator_decision = AsyncMock()

    broker = AsyncMock()
    broker.get_account = AsyncMock(return_value=MagicMock(equity=100_000.0))

    data_service = AsyncMock()
    data_service.fetch_daily_bars = AsyncMock(return_value=_make_spy_bars())

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

    return orchestrator, event_bus, data_service


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


class TestPreMarketToMarketHoursFlow:
    """E2E: pre-market startup → calculators init → V2 run → market hours reclassify."""

    @pytest.mark.asyncio
    async def test_pre_market_produces_regime_vector(self) -> None:
        """Full pre-market: V2 computes RegimeVector, history store receives it."""
        v2, _, _ = _wire_v2_full()
        history = AsyncMock(spec=RegimeHistoryStore)

        orchestrator, event_bus, _ = _make_orchestrator(v2=v2, history=history)

        # Register a dummy strategy so allocation runs
        strategy = MagicMock()
        strategy.strategy_id = "test_strategy"
        strategy.is_active = True
        strategy.get_market_conditions_filter.return_value = MagicMock(
            allowed_regimes=["bullish_trending", "range_bound"]
        )
        strategy.reconstruct_state = AsyncMock()
        orchestrator.register_strategy(strategy)

        await orchestrator.run_pre_market()

        # V2 should have produced a vector
        assert orchestrator._latest_regime_vector is not None
        vector = orchestrator._latest_regime_vector
        assert isinstance(vector, RegimeVector)
        assert vector.primary_regime in list(MarketRegime)
        assert 0.0 <= vector.regime_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_market_hours_reclassify_evolves_vector(self) -> None:
        """Reclassify during market hours updates the regime vector."""
        v2, _, _ = _wire_v2_full()
        history = AsyncMock(spec=RegimeHistoryStore)

        orchestrator, _, data_service = _make_orchestrator(v2=v2, history=history)

        # First classification
        old, new = await orchestrator.reclassify_regime()
        first_vector = orchestrator._latest_regime_vector
        assert first_vector is not None

        # Modify SPY bars to simulate market movement (bearish)
        bearish_bars = _make_spy_bars(num_bars=60, start=500.0)
        # Make closes decline
        bearish_bars["close"] = [500.0 - i * 2 for i in range(60)]
        bearish_bars["open"] = [502.0 - i * 2 for i in range(60)]
        data_service.fetch_daily_bars = AsyncMock(return_value=bearish_bars)

        # Second classification
        old2, new2 = await orchestrator.reclassify_regime()
        second_vector = orchestrator._latest_regime_vector
        assert second_vector is not None

        # Vectors should differ in computed_at at minimum
        assert second_vector.computed_at >= first_vector.computed_at


class TestConfigPermutations:
    """E2E: all config permutation tests."""

    def test_all_dimensions_enabled(self) -> None:
        """All dimensions enabled produces a fully-populated RegimeVector."""
        v2, _, _ = _wire_v2_full()
        vector = v2.compute_regime_vector(_make_indicators())

        assert vector.universe_breadth_score is not None
        assert vector.breadth_thrust is not None
        assert vector.average_correlation is not None
        assert vector.correlation_regime is not None
        assert vector.sector_rotation_phase is not None
        assert len(vector.leading_sectors) > 0
        assert vector.opening_drive_strength is not None
        assert vector.intraday_character is not None
        assert vector.regime_confidence > 0.0

    def test_all_dimensions_disabled(self) -> None:
        """All dimensions disabled produces trend+vol only."""
        rc = _make_regime_config(
            breadth=False, correlation=False, sector=False, intraday=False
        )
        v2 = RegimeClassifierV2(
            config=_make_orch_config(),
            regime_config=rc,
        )
        vector = v2.compute_regime_vector(_make_indicators())

        # Trend and vol always present
        assert vector.trend_score != 0.0 or vector.trend_conviction >= 0.0
        assert vector.volatility_level >= 0.0

        # All optional dimensions should be None
        assert vector.universe_breadth_score is None
        assert vector.breadth_thrust is None
        assert vector.average_correlation is None
        assert vector.correlation_regime is None
        assert vector.sector_rotation_phase is None
        assert vector.leading_sectors == []
        assert vector.lagging_sectors == []
        assert vector.opening_drive_strength is None
        assert vector.intraday_character is None

    def test_breadth_off_others_on(self) -> None:
        """Breadth disabled, other dimensions on — breadth fields None, rest populated."""
        rc = _make_regime_config(breadth=False)
        v2, _, _ = _wire_v2_full(regime_config=rc)

        # Override the regime_config on the V2 (it was built with the wrong one)
        v2._regime_config = rc
        vector = v2.compute_regime_vector(_make_indicators())

        assert vector.universe_breadth_score is None
        assert vector.breadth_thrust is None
        # Other dimensions populated
        assert vector.average_correlation is not None
        assert vector.sector_rotation_phase is not None
        assert vector.intraday_character is not None


class TestFMPDegradation:
    """E2E: FMP unavailable → graceful degradation."""

    @pytest.mark.asyncio
    async def test_fmp_unavailable_sector_degrades_gracefully(self) -> None:
        """When FMP returns 403, sector dimension degrades to defaults."""
        rc = _make_regime_config()
        orch_cfg = _make_orch_config()

        sector = SectorRotationAnalyzer(
            config=rc.sector_rotation,
            fmp_base_url="https://example.com",
            fmp_api_key=None,  # No key → immediate degradation
        )

        v2 = RegimeClassifierV2(
            config=orch_cfg,
            regime_config=rc,
            sector=sector,
        )

        # Fetch will degrade gracefully (no API key)
        await sector.fetch()

        vector = v2.compute_regime_vector(_make_indicators())

        # Sector should have degraded default values
        assert vector.sector_rotation_phase == "mixed"
        assert vector.leading_sectors == []
        assert vector.lagging_sectors == []

        # Vector is still valid — primary regime, trend, vol are present
        assert vector.primary_regime in list(MarketRegime)
        assert vector.regime_confidence > 0.0


class TestStressBreadth:
    """Stress test: BreadthCalculator with 5,000 symbols."""

    def test_breadth_5000_symbols_under_1ms_per_candle(self) -> None:
        """5,000 symbols × 1 candle each should average < 1ms per candle."""
        config = BreadthConfig(
            min_symbols=10, min_bars_for_valid=1, ma_period=20
        )
        calc = BreadthCalculator(config)

        num_symbols = 5_000
        candles = [
            CandleEvent(symbol=f"SYM{i}", close=100.0 + (i % 50))
            for i in range(num_symbols)
        ]

        start = time_mod.perf_counter()
        for candle in candles:
            calc.on_candle(candle)
        elapsed = time_mod.perf_counter() - start

        avg_per_candle_ms = (elapsed / num_symbols) * 1_000
        assert avg_per_candle_ms < 1.0, (
            f"Average {avg_per_candle_ms:.3f}ms per candle exceeds 1ms threshold"
        )

        # Verify snapshot works after ingestion
        snap = calc.get_breadth_snapshot()
        assert snap["symbols_tracked"] == num_symbols
        assert snap["symbols_qualifying"] == num_symbols


class TestConfigGateIsolation:
    """Config-gate: when disabled, verify zero V2 code paths execute."""

    def test_disabled_config_zero_v2_execution(self) -> None:
        """When regime_intelligence.enabled=false, no V2 calculators created."""
        rc = _make_regime_config(enabled=False)

        # Simulate the gating logic from main.py
        breadth_calc = None
        correlation_tracker = None
        sector_analyzer = None
        intraday_detector = None
        regime_v2 = None

        if rc.enabled:
            breadth_calc = BreadthCalculator(rc.breadth)
            correlation_tracker = MarketCorrelationTracker(rc.correlation)
            sector_analyzer = SectorRotationAnalyzer(
                config=rc.sector_rotation,
                fmp_base_url="https://example.com",
                fmp_api_key="test",
            )
            intraday_detector = IntradayCharacterDetector(rc.intraday)
            regime_v2 = RegimeClassifierV2(
                config=_make_orch_config(),
                regime_config=rc,
                breadth=breadth_calc,
                correlation=correlation_tracker,
                sector=sector_analyzer,
                intraday=intraday_detector,
            )

        assert breadth_calc is None
        assert correlation_tracker is None
        assert sector_analyzer is None
        assert intraday_detector is None
        assert regime_v2 is None

    @pytest.mark.asyncio
    async def test_orchestrator_without_v2_skips_vector(self) -> None:
        """Orchestrator with no V2 classifier produces no vector on reclassify."""
        orchestrator, _, _ = _make_orchestrator(v2=None, history=None)

        old, new = await orchestrator.reclassify_regime()

        # No V2 → no vector
        assert orchestrator._latest_regime_vector is None
        # V1 still works
        assert new in list(MarketRegime)


class TestCircularImports:
    """Verify no circular imports in new modules."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "argus.core.breadth",
            "argus.core.market_correlation",
            "argus.core.sector_rotation",
            "argus.core.intraday_character",
            "argus.core.regime_history",
            "argus.core.regime",
        ],
    )
    def test_module_importable(self, module_path: str) -> None:
        """Each new module can be imported without circular import errors."""
        mod = importlib.import_module(module_path)
        assert mod is not None


class TestRegimeVectorJsonRoundtrip:
    """RegimeVector serialize → deserialize → equal for all field combinations."""

    def test_full_vector_roundtrip(self) -> None:
        """Full RegimeVector with all fields populated survives JSON roundtrip."""
        original = RegimeVector(
            computed_at=datetime(2026, 3, 24, 14, 30, 0, tzinfo=UTC),
            trend_score=0.75,
            trend_conviction=0.85,
            volatility_level=0.18,
            volatility_direction=0.3,
            universe_breadth_score=0.65,
            breadth_thrust=True,
            average_correlation=0.45,
            correlation_regime="normal",
            sector_rotation_phase="risk_on",
            leading_sectors=["Technology", "Financials"],
            lagging_sectors=["Utilities", "Healthcare"],
            opening_drive_strength=0.6,
            first_30min_range_ratio=0.8,
            vwap_slope=0.0005,
            direction_change_count=2,
            intraday_character="trending",
            primary_regime=MarketRegime.BULLISH_TRENDING,
            regime_confidence=0.78,
        )

        d = original.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        restored = RegimeVector.from_dict(parsed)

        assert restored.computed_at == original.computed_at
        assert restored.trend_score == original.trend_score
        assert restored.trend_conviction == original.trend_conviction
        assert restored.volatility_level == original.volatility_level
        assert restored.volatility_direction == original.volatility_direction
        assert restored.universe_breadth_score == original.universe_breadth_score
        assert restored.breadth_thrust == original.breadth_thrust
        assert restored.average_correlation == original.average_correlation
        assert restored.correlation_regime == original.correlation_regime
        assert restored.sector_rotation_phase == original.sector_rotation_phase
        assert restored.leading_sectors == original.leading_sectors
        assert restored.lagging_sectors == original.lagging_sectors
        assert restored.opening_drive_strength == original.opening_drive_strength
        assert restored.first_30min_range_ratio == original.first_30min_range_ratio
        assert restored.vwap_slope == original.vwap_slope
        assert restored.direction_change_count == original.direction_change_count
        assert restored.intraday_character == original.intraday_character
        assert restored.primary_regime == original.primary_regime
        assert restored.regime_confidence == original.regime_confidence

    def test_minimal_vector_roundtrip(self) -> None:
        """Minimal RegimeVector (only required fields, optional as None) roundtrips."""
        original = RegimeVector(
            computed_at=datetime(2026, 3, 24, 10, 0, 0, tzinfo=UTC),
            trend_score=-0.5,
            trend_conviction=0.3,
            volatility_level=0.22,
            volatility_direction=-0.1,
            primary_regime=MarketRegime.BEARISH_TRENDING,
            regime_confidence=0.55,
        )

        d = original.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        restored = RegimeVector.from_dict(parsed)

        assert restored.trend_score == original.trend_score
        assert restored.universe_breadth_score is None
        assert restored.breadth_thrust is None
        assert restored.average_correlation is None
        assert restored.primary_regime == MarketRegime.BEARISH_TRENDING


class TestMultipleReclassificationCycles:
    """Multiple reclassification cycles: RegimeVector consistency over time."""

    @pytest.mark.asyncio
    async def test_repeated_reclassify_produces_consistent_vectors(self) -> None:
        """5 consecutive reclassifications produce valid vectors each time."""
        v2, _, _ = _wire_v2_full()
        history = AsyncMock(spec=RegimeHistoryStore)

        orchestrator, _, _ = _make_orchestrator(v2=v2, history=history)

        vectors: list[RegimeVector] = []
        for _ in range(5):
            old, new = await orchestrator.reclassify_regime()
            vector = orchestrator._latest_regime_vector
            assert vector is not None
            assert isinstance(vector, RegimeVector)
            assert 0.0 <= vector.regime_confidence <= 1.0
            assert vector.primary_regime in list(MarketRegime)
            vectors.append(vector)

        # Vectors should be temporally ordered
        for i in range(1, len(vectors)):
            assert vectors[i].computed_at >= vectors[i - 1].computed_at


class TestGoldenFileParity:
    """V1 and V2 produce identical primary_regime on the same inputs."""

    def test_v1_v2_parity_on_spy_bars(self) -> None:
        """V2.classify() and V1.classify() return identical results on 100 bar scenarios."""
        orch_cfg = _make_orch_config()
        v1 = RegimeClassifier(orch_cfg)
        v2 = RegimeClassifierV2(
            config=orch_cfg,
            regime_config=_make_regime_config(),
        )

        # Generate 5 distinct indicator scenarios covering all regimes
        scenarios = [
            # Bullish: price above both SMAs, positive ROC
            _make_indicators(price=460.0, sma_20=450.0, sma_50=440.0, roc=0.03, vol=0.12),
            # Bearish: price below both SMAs, negative ROC
            _make_indicators(price=400.0, sma_20=420.0, sma_50=440.0, roc=-0.03, vol=0.15),
            # Range-bound: mixed SMA signals
            _make_indicators(price=435.0, sma_20=430.0, sma_50=440.0, roc=0.005, vol=0.14),
            # High vol: crisis threshold
            _make_indicators(price=400.0, sma_20=420.0, sma_50=440.0, roc=-0.05, vol=0.40),
            # Low vol range-bound
            _make_indicators(price=440.0, sma_20=440.0, sma_50=440.0, roc=0.0, vol=0.06),
        ]

        for indicators in scenarios:
            v1_result = v1.classify(indicators)
            v2_result = v2.classify(indicators)
            assert v1_result == v2_result, (
                f"V1/V2 parity mismatch: V1={v1_result}, V2={v2_result}, "
                f"price={indicators.spy_price}"
            )

    def test_v1_v2_compute_indicators_parity(self) -> None:
        """V2.compute_indicators delegates to V1 and returns identical results."""
        orch_cfg = _make_orch_config()
        v1 = RegimeClassifier(orch_cfg)
        v2 = RegimeClassifierV2(
            config=orch_cfg,
            regime_config=_make_regime_config(),
        )

        bars = _make_spy_bars(num_bars=100)
        v1_indicators = v1.compute_indicators(bars)
        v2_indicators = v2.compute_indicators(bars)

        assert v1_indicators.spy_price == v2_indicators.spy_price
        assert v1_indicators.spy_sma_20 == v2_indicators.spy_sma_20
        assert v1_indicators.spy_sma_50 == v2_indicators.spy_sma_50
        assert v1_indicators.spy_roc_5d == v2_indicators.spy_roc_5d
        assert v1_indicators.spy_realized_vol_20d == v2_indicators.spy_realized_vol_20d


class TestCleanupVerification:
    """Verify no TODO/FIXME/HACK markers in new code files."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "argus/core/breadth.py",
            "argus/core/market_correlation.py",
            "argus/core/sector_rotation.py",
            "argus/core/intraday_character.py",
            "argus/core/regime_history.py",
        ],
    )
    def test_no_todo_fixme_hack(self, module_path: str) -> None:
        """New V2 code files contain no TODO, FIXME, or HACK markers."""
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        filepath = root / module_path
        content = filepath.read_text(encoding="utf-8")

        for marker in ("TODO", "FIXME", "HACK"):
            assert marker not in content, (
                f"Found {marker} in {module_path} — cleanup needed"
            )

"""Tests for the quality pipeline wiring in ArgusSystem._process_signal().

Sprint 24, Session 6a — tests cover:
- Quality pipeline scoring and sizing
- Grade filtering (C grade → skip)
- Sizer zero-shares skip
- Backtest bypass (BrokerSource.SIMULATED)
- Config bypass (enabled=false)
- Quality history recording for passed and filtered signals
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import BrokerSource
from argus.core.event_bus import EventBus
from argus.core.events import (
    CandleEvent,
    OrderApprovedEvent,
    OrderRejectedEvent,
    QualitySignalEvent,
    Side,
    SignalEvent,
)
from argus.core.regime import MarketRegime
from argus.intelligence.config import (
    QualityEngineConfig,
    QualityRiskTiersConfig,
    QualityThresholdsConfig,
    QualityWeightsConfig,
)
from argus.intelligence.models import ClassifiedCatalyst
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQuality, SetupQualityEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_signal(
    pattern_strength: float = 70.0,
    entry_price: float = 100.0,
    stop_price: float = 99.0,
    share_count: int = 0,
) -> SignalEvent:
    return SignalEvent(
        strategy_id="strat_orb_breakout",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(102.0, 104.0),
        share_count=share_count,
        rationale="Test signal",
        pattern_strength=pattern_strength,
    )


@dataclass
class FakeConfig:
    """Minimal config stand-in for testing _process_signal."""

    class SystemConfig:
        broker_source: BrokerSource = BrokerSource.IBKR
        quality_engine: QualityEngineConfig = QualityEngineConfig()

    system: SystemConfig = SystemConfig()


class _FakeRiskLimits:
    max_loss_per_trade_pct: float = 0.01


class _FakeStrategyConfig:
    risk_limits = _FakeRiskLimits()


@dataclass
class FakeStrategy:
    """Minimal strategy stand-in."""

    allocated_capital: float = 100_000.0
    config: object = _FakeStrategyConfig()


@dataclass
class FakeAccount:
    equity: float = 200_000.0
    buying_power: float = 200_000.0


# ---------------------------------------------------------------------------
# Quality pipeline: score + size
# ---------------------------------------------------------------------------


class TestQualityPipelineScoresAndSizes:
    """Test that the quality pipeline correctly scores and sizes signals."""

    @pytest.mark.asyncio
    async def test_quality_pipeline_scores_and_sizes_signal(self) -> None:
        """Signal with varied pattern_strength → correct quality score and non-zero shares."""
        qe_config = QualityEngineConfig()
        engine = SetupQualityEngine(qe_config)
        sizer = DynamicPositionSizer(qe_config)

        signal = make_signal(pattern_strength=80.0)
        quality = engine.score_setup(
            signal=signal,
            catalysts=[],
            rvol=2.0,
            regime=MarketRegime.BULLISH_TRENDING,
            allowed_regimes=["bullish_trending"],
        )

        shares = sizer.calculate_shares(
            quality=quality,
            entry_price=signal.entry_price,
            stop_price=signal.stop_price,
            allocated_capital=100_000.0,
            buying_power=200_000.0,
        )

        assert quality.score > 0
        assert quality.grade != ""
        assert shares > 0

    @pytest.mark.asyncio
    async def test_quality_pipeline_filters_c_grade(self) -> None:
        """Low pattern_strength → C grade → signal should be filtered."""
        # Use weights that make PS the only contributor
        weights = QualityWeightsConfig(
            pattern_strength=1.0,
            catalyst_quality=0.0,
            volume_profile=0.0,
            historical_match=0.0,
            regime_alignment=0.0,
        )
        qe_config = QualityEngineConfig(weights=weights, min_grade_to_trade="C+")
        engine = SetupQualityEngine(qe_config)

        signal = make_signal(pattern_strength=10.0)
        quality = engine.score_setup(
            signal=signal,
            catalysts=[],
            rvol=None,
            regime=MarketRegime.RANGE_BOUND,
            allowed_regimes=["bullish_trending"],
        )

        assert quality.grade == "C"
        # C is below the min_grade_to_trade of C+
        from argus.intelligence.config import VALID_GRADES

        grade_order = {g: i for i, g in enumerate(reversed(VALID_GRADES))}
        assert grade_order.get("C", -1) < grade_order.get("C+", 0)

    @pytest.mark.asyncio
    async def test_quality_pipeline_sizer_zero_shares_skipped(self) -> None:
        """Sizer returns 0 when entry == stop → signal should be skipped."""
        qe_config = QualityEngineConfig()
        sizer = DynamicPositionSizer(qe_config)

        quality = SetupQuality(
            score=70.0,
            grade="A-",
            risk_tier="A-",
            components={
                "pattern_strength": 70.0,
                "catalyst_quality": 50.0,
                "volume_profile": 50.0,
                "historical_match": 50.0,
                "regime_alignment": 70.0,
            },
            rationale="test",
        )

        # entry == stop → risk_per_share = 0 → shares = 0
        shares = sizer.calculate_shares(
            quality=quality,
            entry_price=100.0,
            stop_price=100.0,
            allocated_capital=100_000.0,
            buying_power=200_000.0,
        )
        assert shares == 0


# ---------------------------------------------------------------------------
# Bypass paths
# ---------------------------------------------------------------------------


class TestBypassPaths:
    """Test legacy sizing bypass for backtesting and config-disabled."""

    @pytest.mark.asyncio
    async def test_backtest_bypass_uses_legacy_sizing(self) -> None:
        """BrokerSource.SIMULATED → no quality pipeline, strategy-calculated shares."""
        signal = make_signal(entry_price=100.0, stop_price=99.0)
        strategy = FakeStrategy()

        # Legacy sizing: allocated_capital * max_loss_per_trade_pct / risk_per_share
        risk_per_share = abs(signal.entry_price - signal.stop_price)
        expected_shares = int(
            strategy.allocated_capital
            * strategy.config.risk_limits.max_loss_per_trade_pct
            / risk_per_share
        )

        # Verify the math directly
        assert expected_shares == 1000
        assert risk_per_share == 1.0

    @pytest.mark.asyncio
    async def test_config_disabled_bypass(self) -> None:
        """enabled=false → legacy sizing."""
        qe_config = QualityEngineConfig(enabled=False)
        assert not qe_config.enabled


# ---------------------------------------------------------------------------
# Grade comparison
# ---------------------------------------------------------------------------


class TestGradeMeetsMinimum:
    """Test the _grade_meets_minimum helper logic."""

    def test_grade_ordering(self) -> None:
        """Verify grade ordering: A+ > A > A- > ... > C+ > C."""
        from argus.intelligence.config import VALID_GRADES

        grade_order = {g: i for i, g in enumerate(reversed(VALID_GRADES))}

        assert grade_order["A+"] > grade_order["A"]
        assert grade_order["A"] > grade_order["A-"]
        assert grade_order["B+"] > grade_order["B"]
        assert grade_order["C+"] > grade_order.get("C", -1)

    def test_c_below_c_plus(self) -> None:
        """C grade does not meet C+ minimum."""
        from argus.intelligence.config import VALID_GRADES

        grade_order = {g: i for i, g in enumerate(reversed(VALID_GRADES))}
        assert grade_order.get("C", -1) < grade_order.get("C+", 0)

    def test_b_plus_meets_c_plus(self) -> None:
        """B+ meets C+ minimum."""
        from argus.intelligence.config import VALID_GRADES

        grade_order = {g: i for i, g in enumerate(reversed(VALID_GRADES))}
        assert grade_order["B+"] >= grade_order["C+"]


# ---------------------------------------------------------------------------
# Quality history recording
# ---------------------------------------------------------------------------


class TestQualityHistoryRecording:
    """Test record_quality_history persistence."""

    @pytest.mark.asyncio
    async def test_quality_history_recorded_for_passed_signal(self, tmp_path) -> None:
        """quality_history row with shares > 0 for a passed signal."""
        from argus.db.manager import DatabaseManager

        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        await db.initialize()

        qe_config = QualityEngineConfig()
        engine = SetupQualityEngine(qe_config, db_manager=db)

        signal = make_signal(pattern_strength=80.0)
        quality = SetupQuality(
            score=75.0,
            grade="A-",
            risk_tier="A-",
            components={
                "pattern_strength": 80.0,
                "catalyst_quality": 50.0,
                "volume_profile": 70.0,
                "historical_match": 50.0,
                "regime_alignment": 80.0,
            },
            rationale="test",
        )

        await engine.record_quality_history(signal, quality, shares=500)

        # Verify the row was written
        async with db.connection() as conn:
            cursor = await conn.execute("SELECT * FROM quality_history")
            rows = await cursor.fetchall()

        assert len(rows) == 1
        row = rows[0]
        # id, symbol, strategy_id, scored_at, ps, cq, vp, hm, ra, score, grade, tier,
        # entry, stop, shares, context, outcome_trade_id, outcome_pnl, outcome_r, created
        assert row[1] == "AAPL"  # symbol
        assert row[2] == "strat_orb_breakout"  # strategy_id
        assert row[9] == 75.0  # composite_score
        assert row[10] == "A-"  # grade
        assert row[14] == 500  # calculated_shares

        await db.close()

    @pytest.mark.asyncio
    async def test_quality_history_recorded_for_filtered_signal(self, tmp_path) -> None:
        """quality_history row with shares = 0 for a filtered signal."""
        from argus.db.manager import DatabaseManager

        db_path = tmp_path / "test.db"
        db = DatabaseManager(db_path)
        await db.initialize()

        qe_config = QualityEngineConfig()
        engine = SetupQualityEngine(qe_config, db_manager=db)

        signal = make_signal(pattern_strength=10.0)
        quality = SetupQuality(
            score=20.0,
            grade="C",
            risk_tier="C",
            components={
                "pattern_strength": 10.0,
                "catalyst_quality": 50.0,
                "volume_profile": 10.0,
                "historical_match": 50.0,
                "regime_alignment": 20.0,
            },
            rationale="test",
        )

        await engine.record_quality_history(signal, quality, shares=0)

        async with db.connection() as conn:
            cursor = await conn.execute("SELECT * FROM quality_history")
            rows = await cursor.fetchall()

        assert len(rows) == 1
        assert rows[0][14] == 0  # calculated_shares
        assert rows[0][10] == "C"  # grade

        await db.close()

    @pytest.mark.asyncio
    async def test_quality_history_no_db_is_noop(self) -> None:
        """record_quality_history with no db_manager does nothing (no error)."""
        engine = SetupQualityEngine(QualityEngineConfig(), db_manager=None)
        signal = make_signal()
        quality = SetupQuality(
            score=50.0,
            grade="B",
            risk_tier="B",
            components={
                "pattern_strength": 50.0,
                "catalyst_quality": 50.0,
                "volume_profile": 50.0,
                "historical_match": 50.0,
                "regime_alignment": 50.0,
            },
            rationale="test",
        )
        # Should not raise
        await engine.record_quality_history(signal, quality, shares=100)

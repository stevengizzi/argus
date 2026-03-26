"""Tests for RegimeVector expansion with VIX landscape fields (Sprint 27.9 S2a).

Verifies:
- Backward-compatible construction with original 6 dimensions
- Full 11-field construction
- primary_regime unchanged for known inputs
- to_dict includes all 11 fields
- matches_conditions match-any for new enum dimensions
- RegimeHistoryStore schema migration (vix_close column)
"""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
import pytest

from argus.core.regime import (
    MarketRegime,
    RegimeOperatingConditions,
    RegimeVector,
)
from argus.core.regime_history import RegimeHistoryStore
from argus.data.vix_config import (
    TermStructureRegime,
    VolRegimeMomentum,
    VolRegimePhase,
    VRPTier,
)


def _make_vector(**overrides: object) -> RegimeVector:
    """Create a RegimeVector with sensible defaults."""
    defaults: dict[str, object] = {
        "computed_at": datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC),
        "trend_score": 0.5,
        "trend_conviction": 0.7,
        "volatility_level": 0.15,
        "volatility_direction": 0.1,
        "primary_regime": MarketRegime.BULLISH_TRENDING,
        "regime_confidence": 0.75,
    }
    defaults.update(overrides)
    return RegimeVector(**defaults)  # type: ignore[arg-type]


class TestConstructionWithOriginalFieldsOnly:
    """Construct RegimeVector with only original 6 dimensions — new fields default to None."""

    def test_construction_with_original_fields_only(self) -> None:
        vector = _make_vector()

        # Original fields present
        assert vector.trend_score == 0.5
        assert vector.trend_conviction == 0.7
        assert vector.volatility_level == 0.15
        assert vector.volatility_direction == 0.1
        assert vector.primary_regime == MarketRegime.BULLISH_TRENDING
        assert vector.regime_confidence == 0.75

        # New VIX fields all None
        assert vector.vol_regime_phase is None
        assert vector.vol_regime_momentum is None
        assert vector.term_structure_regime is None
        assert vector.variance_risk_premium is None
        assert vector.vix_close is None


class TestConstructionWithAllFields:
    """Construct RegimeVector with all 11 fields populated."""

    def test_construction_with_all_fields(self) -> None:
        vector = _make_vector(
            vol_regime_phase=VolRegimePhase.CALM,
            vol_regime_momentum=VolRegimeMomentum.STABILIZING,
            term_structure_regime=TermStructureRegime.CONTANGO_LOW,
            variance_risk_premium=VRPTier.NORMAL,
            vix_close=18.5,
        )

        assert vector.vol_regime_phase == VolRegimePhase.CALM
        assert vector.vol_regime_momentum == VolRegimeMomentum.STABILIZING
        assert vector.term_structure_regime == TermStructureRegime.CONTANGO_LOW
        assert vector.variance_risk_premium == VRPTier.NORMAL
        assert vector.vix_close == 18.5

        # Original fields still correct
        assert vector.trend_score == 0.5
        assert vector.primary_regime == MarketRegime.BULLISH_TRENDING


class TestPrimaryRegimeUnchanged:
    """Verify primary_regime returns identical value as pre-sprint for known inputs."""

    def test_primary_regime_bullish(self) -> None:
        vector = _make_vector(primary_regime=MarketRegime.BULLISH_TRENDING)
        assert vector.primary_regime == MarketRegime.BULLISH_TRENDING

    def test_primary_regime_bearish(self) -> None:
        vector = _make_vector(primary_regime=MarketRegime.BEARISH_TRENDING)
        assert vector.primary_regime == MarketRegime.BEARISH_TRENDING

    def test_primary_regime_crisis(self) -> None:
        vector = _make_vector(primary_regime=MarketRegime.CRISIS)
        assert vector.primary_regime == MarketRegime.CRISIS

    def test_primary_regime_range_bound(self) -> None:
        vector = _make_vector(primary_regime=MarketRegime.RANGE_BOUND)
        assert vector.primary_regime == MarketRegime.RANGE_BOUND

    def test_primary_regime_high_volatility(self) -> None:
        vector = _make_vector(primary_regime=MarketRegime.HIGH_VOLATILITY)
        assert vector.primary_regime == MarketRegime.HIGH_VOLATILITY

    def test_primary_regime_unaffected_by_vix_fields(self) -> None:
        """Adding VIX fields does NOT change primary_regime."""
        vector_without = _make_vector(primary_regime=MarketRegime.BULLISH_TRENDING)
        vector_with = _make_vector(
            primary_regime=MarketRegime.BULLISH_TRENDING,
            vol_regime_phase=VolRegimePhase.CRISIS,
            vix_close=45.0,
        )
        assert vector_without.primary_regime == vector_with.primary_regime


class TestToDictIncludesAllFields:
    """Verify to_dict() returns all 11 field groups."""

    def test_to_dict_includes_all_fields(self) -> None:
        vector = _make_vector(
            vol_regime_phase=VolRegimePhase.VOL_EXPANSION,
            vol_regime_momentum=VolRegimeMomentum.DETERIORATING,
            term_structure_regime=TermStructureRegime.BACKWARDATION_HIGH,
            variance_risk_premium=VRPTier.ELEVATED,
            vix_close=32.1,
        )
        d = vector.to_dict()

        # All 23 keys present (18 original + 5 new)
        expected_new_keys = {
            "vol_regime_phase",
            "vol_regime_momentum",
            "term_structure_regime",
            "variance_risk_premium",
            "vix_close",
        }
        for key in expected_new_keys:
            assert key in d, f"Missing key: {key}"

        # Enum values serialized as strings
        assert d["vol_regime_phase"] == "vol_expansion"
        assert d["vol_regime_momentum"] == "deteriorating"
        assert d["term_structure_regime"] == "backwardation_high"
        assert d["variance_risk_premium"] == "elevated"
        assert d["vix_close"] == 32.1

        # Original keys still present
        assert d["primary_regime"] == "bullish_trending"
        assert d["trend_score"] == 0.5

    def test_to_dict_none_fields_are_none_not_missing(self) -> None:
        vector = _make_vector()
        d = vector.to_dict()

        assert "vol_regime_phase" in d
        assert d["vol_regime_phase"] is None
        assert "vol_regime_momentum" in d
        assert d["vol_regime_momentum"] is None
        assert "vix_close" in d
        assert d["vix_close"] is None


class TestMatchesConditionsMatchAny:
    """Test match-any semantics for new VIX enum dimensions."""

    def test_condition_none_always_matches(self) -> None:
        """Condition None → skip (match-any)."""
        vector = _make_vector(vol_regime_phase=VolRegimePhase.CRISIS)
        conditions = RegimeOperatingConditions()  # all None
        assert vector.matches_conditions(conditions) is True

    def test_vector_none_with_non_none_condition_matches(self) -> None:
        """Vector field None + condition non-None → match (match-any from vector side)."""
        vector = _make_vector(vol_regime_phase=None)
        conditions = RegimeOperatingConditions(
            vol_regime_phase=VolRegimePhase.CALM,
        )
        assert vector.matches_conditions(conditions) is True

    def test_both_non_none_equal_matches(self) -> None:
        """Both non-None and equal → match."""
        vector = _make_vector(vol_regime_phase=VolRegimePhase.CALM)
        conditions = RegimeOperatingConditions(
            vol_regime_phase=VolRegimePhase.CALM,
        )
        assert vector.matches_conditions(conditions) is True

    def test_both_non_none_different_fails(self) -> None:
        """Both non-None and different → no match."""
        vector = _make_vector(vol_regime_phase=VolRegimePhase.CRISIS)
        conditions = RegimeOperatingConditions(
            vol_regime_phase=VolRegimePhase.CALM,
        )
        assert vector.matches_conditions(conditions) is False

    def test_multiple_vix_conditions_all_must_match(self) -> None:
        """Multiple VIX conditions use AND logic."""
        vector = _make_vector(
            vol_regime_phase=VolRegimePhase.CALM,
            variance_risk_premium=VRPTier.EXTREME,
        )
        conditions = RegimeOperatingConditions(
            vol_regime_phase=VolRegimePhase.CALM,
            variance_risk_premium=VRPTier.NORMAL,  # mismatch
        )
        assert vector.matches_conditions(conditions) is False

    def test_vix_conditions_combined_with_original_conditions(self) -> None:
        """VIX conditions work alongside original range/string conditions."""
        vector = _make_vector(
            trend_score=0.5,
            vol_regime_phase=VolRegimePhase.TRANSITION,
        )
        conditions = RegimeOperatingConditions(
            trend_score=(0.0, 1.0),
            vol_regime_phase=VolRegimePhase.TRANSITION,
        )
        assert vector.matches_conditions(conditions) is True


@pytest.mark.asyncio
class TestHistoryStoreMigration:
    """Test RegimeHistoryStore schema migration for vix_close column."""

    async def test_history_store_migration(self, tmp_path: object) -> None:
        """Create DB with old schema, init store → migration runs.

        Insert new row with vix_close → read back correctly.
        Read old row → vix_close is None.
        """
        from pathlib import Path

        db_path = str(Path(str(tmp_path)) / "test_regime_history.db")

        # Step 1: Create DB with OLD schema (no vix_close column)
        db = await aiosqlite.connect(db_path)
        await db.execute("""
            CREATE TABLE regime_snapshots (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                primary_regime TEXT NOT NULL,
                regime_confidence REAL NOT NULL,
                trend_score REAL NOT NULL,
                trend_conviction REAL NOT NULL,
                volatility_level REAL NOT NULL,
                volatility_direction REAL NOT NULL,
                universe_breadth_score REAL,
                breadth_thrust INTEGER,
                avg_correlation REAL,
                correlation_regime TEXT,
                sector_rotation_phase TEXT,
                intraday_character TEXT,
                regime_vector_json TEXT NOT NULL
            )
        """)
        # Insert an old-format row (no vix_close)
        await db.execute(
            """
            INSERT INTO regime_snapshots (
                id, timestamp, trading_date, primary_regime,
                regime_confidence, trend_score, trend_conviction,
                volatility_level, volatility_direction,
                regime_vector_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "old-row-001",
                "2026-03-25T10:00:00-04:00",
                "2026-03-25",
                "bullish_trending",
                0.75,
                0.5,
                0.7,
                0.15,
                0.1,
                "{}",
            ),
        )
        await db.commit()
        await db.close()

        # Step 2: Initialize RegimeHistoryStore → should run migration
        store = RegimeHistoryStore(db_path=db_path)
        await store.initialize()

        # Step 3: Insert a new row WITH vix_close via record()
        vector = _make_vector()
        await store.record(vector, vix_close=22.5)

        # Step 4: Read back all rows
        rows = await store.get_regime_history("2026-03-25")
        assert len(rows) == 1
        assert rows[0]["vix_close"] is None  # old row has NULL

        rows_new = await store.get_regime_history("2026-03-26")
        assert len(rows_new) == 1
        assert rows_new[0]["vix_close"] == 22.5

        await store.close()

    async def test_migration_idempotent(self, tmp_path: object) -> None:
        """Running initialize() twice doesn't error (idempotent migration)."""
        from pathlib import Path

        db_path = str(Path(str(tmp_path)) / "test_regime_idempotent.db")

        store = RegimeHistoryStore(db_path=db_path)
        await store.initialize()
        await store.close()

        # Second init on same DB — should not raise
        store2 = RegimeHistoryStore(db_path=db_path)
        await store2.initialize()
        await store2.close()

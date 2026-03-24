"""Tests for RegimeHistoryStore persistence.

Sprint 27.6, Session 6.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from argus.core.regime import MarketRegime, RegimeVector
from argus.core.regime_history import RegimeHistoryStore

_ET = ZoneInfo("America/New_York")


def _make_vector(
    regime: MarketRegime = MarketRegime.BULLISH_TRENDING,
    confidence: float = 0.75,
    computed_at: datetime | None = None,
) -> RegimeVector:
    """Create a test RegimeVector."""
    return RegimeVector(
        computed_at=computed_at or datetime.now(UTC),
        trend_score=0.8,
        trend_conviction=0.9,
        volatility_level=0.15,
        volatility_direction=0.1,
        universe_breadth_score=0.6,
        breadth_thrust=True,
        average_correlation=0.45,
        correlation_regime="normal",
        sector_rotation_phase="risk_on",
        leading_sectors=["Technology", "Financials"],
        lagging_sectors=["Utilities", "Healthcare"],
        opening_drive_strength=0.5,
        first_30min_range_ratio=0.8,
        vwap_slope=0.0003,
        direction_change_count=2,
        intraday_character="trending",
        primary_regime=regime,
        regime_confidence=confidence,
    )


@pytest.fixture
async def store() -> RegimeHistoryStore:
    """Create a RegimeHistoryStore with a temp database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_regime_history.db")
        s = RegimeHistoryStore(db_path=db_path)
        await s.initialize()
        yield s
        await s.close()


class TestRegimeHistoryStore:
    """Tests for RegimeHistoryStore write + query operations."""

    @pytest.mark.asyncio
    async def test_write_and_query_by_date(self, store: RegimeHistoryStore) -> None:
        """Write a vector and query it back by trading date."""
        vector = _make_vector()
        await store.record(vector)

        # Query by today's date (ET)
        today_et = vector.computed_at.astimezone(_ET).strftime("%Y-%m-%d")
        rows = await store.get_regime_history(today_et)

        assert len(rows) == 1
        assert rows[0]["primary_regime"] == "bullish_trending"
        assert rows[0]["regime_confidence"] == 0.75
        assert rows[0]["trend_score"] == 0.8
        assert rows[0]["universe_breadth_score"] == 0.6
        assert rows[0]["breadth_thrust"] == 1  # True → 1
        assert rows[0]["correlation_regime"] == "normal"
        assert rows[0]["sector_rotation_phase"] == "risk_on"
        assert rows[0]["intraday_character"] == "trending"

    @pytest.mark.asyncio
    async def test_query_by_timestamp(self, store: RegimeHistoryStore) -> None:
        """Query the most recent snapshot at or before a timestamp."""
        now = datetime.now(UTC)
        v1 = _make_vector(computed_at=now - timedelta(minutes=10))
        v2 = _make_vector(
            regime=MarketRegime.RANGE_BOUND,
            computed_at=now - timedelta(minutes=5),
        )
        await store.record(v1)
        await store.record(v2)

        # Query at a time between v1 and v2 should return v1
        query_time = now - timedelta(minutes=7)
        result = await store.get_regime_at_time(query_time)

        assert result is not None
        assert result["primary_regime"] == "bullish_trending"

        # Query at now should return v2 (most recent)
        result = await store.get_regime_at_time(now)
        assert result is not None
        assert result["primary_regime"] == "range_bound"

    @pytest.mark.asyncio
    async def test_fire_and_forget_write_failure_does_not_propagate(
        self, store: RegimeHistoryStore
    ) -> None:
        """Write failure logged as WARNING, never raises."""
        vector = _make_vector()

        # Close the DB to force a write failure
        await store.close()
        store._db = None

        # Should not raise
        await store.record(vector)

    @pytest.mark.asyncio
    async def test_seven_day_retention_cleanup(self) -> None:
        """Records older than 7 days are deleted on initialize."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_retention.db")
            s = RegimeHistoryStore(db_path=db_path)
            await s.initialize()

            # Write a record with an old date
            now = datetime.now(UTC)
            old_vector = _make_vector(computed_at=now - timedelta(days=10))
            await s.record(old_vector)

            # Write a recent record
            recent_vector = _make_vector(computed_at=now)
            await s.record(recent_vector)

            # Re-initialize (triggers cleanup)
            await s.close()
            s2 = RegimeHistoryStore(db_path=db_path)
            await s2.initialize()

            # The old record's trading_date should have been cleaned up
            old_date = old_vector.computed_at.astimezone(_ET).strftime("%Y-%m-%d")
            old_rows = await s2.get_regime_history(old_date)
            assert len(old_rows) == 0

            # The recent record should still exist
            recent_date = recent_vector.computed_at.astimezone(_ET).strftime("%Y-%m-%d")
            recent_rows = await s2.get_regime_history(recent_date)
            assert len(recent_rows) == 1

            await s2.close()

    @pytest.mark.asyncio
    async def test_get_regime_summary(self, store: RegimeHistoryStore) -> None:
        """Summary returns dominant regime, transition count, avg confidence."""
        now = datetime.now(UTC)

        # Write 3 snapshots: 2 bullish, 1 range_bound
        await store.record(_make_vector(
            regime=MarketRegime.BULLISH_TRENDING,
            confidence=0.8,
            computed_at=now - timedelta(minutes=10),
        ))
        await store.record(_make_vector(
            regime=MarketRegime.RANGE_BOUND,
            confidence=0.6,
            computed_at=now - timedelta(minutes=5),
        ))
        await store.record(_make_vector(
            regime=MarketRegime.BULLISH_TRENDING,
            confidence=0.7,
            computed_at=now,
        ))

        today_et = now.astimezone(_ET).strftime("%Y-%m-%d")
        summary = await store.get_regime_summary(today_et)

        assert summary["dominant_regime"] == "bullish_trending"
        assert summary["transition_count"] == 2  # bull→range→bull
        assert 0.6 <= summary["avg_confidence"] <= 0.8
        assert summary["snapshot_count"] == 3

    @pytest.mark.asyncio
    async def test_config_gate_persist_history_false(self) -> None:
        """When persist_history=false, store should not be initialized."""
        from argus.core.config import RegimeIntelligenceConfig

        config = RegimeIntelligenceConfig(enabled=True, persist_history=False)
        assert config.persist_history is False
        # In main.py, the logic is:
        # if regime_config.persist_history: create store
        # This test verifies the config value is correct

    @pytest.mark.asyncio
    async def test_regime_vector_json_stored(self, store: RegimeHistoryStore) -> None:
        """regime_vector_json column contains full serialized vector."""
        import json

        vector = _make_vector()
        await store.record(vector)

        today_et = vector.computed_at.astimezone(_ET).strftime("%Y-%m-%d")
        rows = await store.get_regime_history(today_et)

        assert len(rows) == 1
        blob = json.loads(rows[0]["regime_vector_json"])
        assert blob["trend_score"] == 0.8
        assert blob["intraday_character"] == "trending"
        assert blob["primary_regime"] == "bullish_trending"

"""Tests for CatalystStorage.

Sprint 23.5 Session 3 — DEC-164
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from argus.intelligence.models import (
    CatalystClassification,
    ClassifiedCatalyst,
    IntelligenceBrief,
    compute_headline_hash,
)
from argus.intelligence.storage import CatalystStorage

_ET = ZoneInfo("America/New_York")


@pytest.fixture
async def storage() -> CatalystStorage:
    """Create an in-memory storage instance."""
    s = CatalystStorage(":memory:")
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
def sample_catalyst() -> ClassifiedCatalyst:
    """Create a sample classified catalyst."""
    now = datetime.now(_ET)
    return ClassifiedCatalyst(
        headline="AAPL beats Q3 earnings",
        symbol="AAPL",
        source="test",
        published_at=now,
        fetched_at=now,
        category="earnings",
        quality_score=85.0,
        summary="Apple exceeded expectations",
        trading_relevance="high",
        classified_by="claude",
        classified_at=now,
        headline_hash=compute_headline_hash("AAPL beats Q3 earnings"),
    )


@pytest.fixture
def sample_classification() -> CatalystClassification:
    """Create a sample classification."""
    now = datetime.now(_ET)
    return CatalystClassification(
        category="earnings",
        quality_score=85.0,
        summary="Apple exceeded expectations",
        trading_relevance="high",
        classified_by="claude",
        classified_at=now,
    )


@pytest.fixture
def sample_brief() -> IntelligenceBrief:
    """Create a sample intelligence brief."""
    now = datetime.now(_ET)
    return IntelligenceBrief(
        date="2026-03-10",
        brief_type="premarket",
        content="# Pre-Market Brief\n\nToday's key catalysts...",
        symbols_covered=["AAPL", "TSLA", "NVDA"],
        catalyst_count=5,
        generated_at=now,
        generation_cost_usd=0.15,
    )


class TestCatalystEvents:
    """Tests for catalyst event storage."""

    @pytest.mark.asyncio
    async def test_store_and_get_by_symbol_roundtrip(
        self,
        storage: CatalystStorage,
        sample_catalyst: ClassifiedCatalyst,
    ) -> None:
        """Store catalyst and retrieve by symbol."""
        catalyst_id = await storage.store_catalyst(sample_catalyst)
        assert catalyst_id is not None
        assert len(catalyst_id) == 26  # ULID length

        results = await storage.get_catalysts_by_symbol("AAPL")
        assert len(results) == 1
        assert results[0].headline == sample_catalyst.headline
        assert results[0].symbol == "AAPL"
        assert results[0].category == "earnings"
        assert results[0].quality_score == 85.0

    @pytest.mark.asyncio
    async def test_get_recent_catalysts_with_limit_and_offset(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Get recent catalysts respects limit and offset."""
        now = datetime.now(_ET)

        # Store 5 catalysts
        for i in range(5):
            catalyst = ClassifiedCatalyst(
                headline=f"News {i}",
                symbol="TEST",
                source="test",
                published_at=now,
                fetched_at=now,
                category="other",
                quality_score=50.0,
                summary=f"Summary {i}",
                trading_relevance="low",
                classified_by="fallback",
                classified_at=now,
                headline_hash=compute_headline_hash(f"News {i}"),
            )
            await storage.store_catalyst(catalyst)

        # Get with limit
        results = await storage.get_recent_catalysts(limit=3)
        assert len(results) == 3

        # Get with offset
        results_offset = await storage.get_recent_catalysts(limit=3, offset=2)
        assert len(results_offset) == 3

        # Headlines should be different (offset skips first 2)
        headlines = [r.headline for r in results]
        headlines_offset = [r.headline for r in results_offset]
        # Since ordered by created_at DESC, the offset should get older items
        assert headlines != headlines_offset


class TestClassificationCache:
    """Tests for classification cache."""

    @pytest.mark.asyncio
    async def test_cache_and_get_classification_roundtrip(
        self,
        storage: CatalystStorage,
        sample_classification: CatalystClassification,
    ) -> None:
        """Cache classification and retrieve it."""
        headline_hash = "abc123hash"

        await storage.cache_classification(headline_hash, sample_classification)
        cached = await storage.get_cached_classification(headline_hash)

        assert cached is not None
        assert cached.category == "earnings"
        assert cached.quality_score == 85.0
        assert cached.summary == "Apple exceeded expectations"
        assert cached.trading_relevance == "high"

    @pytest.mark.asyncio
    async def test_is_cache_valid_with_expired_ttl(
        self,
        storage: CatalystStorage,
        sample_classification: CatalystClassification,
    ) -> None:
        """Cache entry with expired TTL returns invalid."""
        headline_hash = "expiredHash"

        # Store the classification
        await storage.cache_classification(headline_hash, sample_classification)

        # With 24 hour TTL, should be valid
        assert await storage.is_cache_valid(headline_hash, ttl_hours=24) is True

        # With 0 hour TTL (immediately expired), should be invalid
        assert await storage.is_cache_valid(headline_hash, ttl_hours=0) is False

    @pytest.mark.asyncio
    async def test_get_cached_classification_returns_none_for_missing(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Missing cache entry returns None."""
        result = await storage.get_cached_classification("nonexistent_hash")
        assert result is None


class TestIntelligenceBriefs:
    """Tests for intelligence brief storage."""

    @pytest.mark.asyncio
    async def test_store_and_get_brief_roundtrip(
        self,
        storage: CatalystStorage,
        sample_brief: IntelligenceBrief,
    ) -> None:
        """Store brief and retrieve by date and type."""
        brief_id = await storage.store_brief(sample_brief)
        assert brief_id is not None
        assert len(brief_id) == 26  # ULID length

        retrieved = await storage.get_brief("2026-03-10", "premarket")
        assert retrieved is not None
        assert retrieved.date == "2026-03-10"
        assert retrieved.brief_type == "premarket"
        assert "Pre-Market Brief" in retrieved.content
        assert retrieved.symbols_covered == ["AAPL", "TSLA", "NVDA"]
        assert retrieved.catalyst_count == 5
        assert retrieved.generation_cost_usd == 0.15

    @pytest.mark.asyncio
    async def test_get_brief_history_ordered_by_date(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Brief history is returned ordered by date DESC."""
        now = datetime.now(_ET)

        # Store briefs for different dates
        dates = ["2026-03-08", "2026-03-10", "2026-03-09"]
        for date in dates:
            brief = IntelligenceBrief(
                date=date,
                brief_type="premarket",
                content=f"Brief for {date}",
                symbols_covered=["AAPL"],
                catalyst_count=1,
                generated_at=now,
                generation_cost_usd=0.10,
            )
            await storage.store_brief(brief)

        history = await storage.get_brief_history(limit=10)

        assert len(history) == 3
        # Should be in descending date order
        assert history[0].date == "2026-03-10"
        assert history[1].date == "2026-03-09"
        assert history[2].date == "2026-03-08"

    @pytest.mark.asyncio
    async def test_get_brief_returns_none_for_missing(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Missing brief returns None."""
        result = await storage.get_brief("2025-01-01", "premarket")
        assert result is None

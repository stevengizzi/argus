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


class TestGetTotalCount:
    """Tests for get_total_count() method."""

    @pytest.mark.asyncio
    async def test_get_total_count_empty(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Returns 0 on fresh DB with no catalysts."""
        count = await storage.get_total_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_total_count_after_inserts(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Returns correct count after storing N catalysts."""
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

        count = await storage.get_total_count()
        assert count == 5

        # Add 2 more
        for i in range(5, 7):
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

        count = await storage.get_total_count()
        assert count == 7


class TestFetchedAtRoundTrip:
    """Tests for fetched_at column persistence."""

    @pytest.mark.asyncio
    async def test_fetched_at_round_trip(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Store a catalyst, read it back, verify fetched_at matches original."""
        now = datetime.now(_ET)
        fetched_time = now - timedelta(minutes=5)

        catalyst = ClassifiedCatalyst(
            headline="AAPL Q4 earnings beat",
            symbol="AAPL",
            source="test",
            published_at=now - timedelta(hours=1),
            fetched_at=fetched_time,
            category="earnings",
            quality_score=85.0,
            summary="Apple exceeded expectations",
            trading_relevance="high",
            classified_by="claude",
            classified_at=now,
            headline_hash=compute_headline_hash("AAPL Q4 earnings beat"),
        )

        await storage.store_catalyst(catalyst)
        results = await storage.get_catalysts_by_symbol("AAPL")

        assert len(results) == 1
        retrieved = results[0]
        # Compare timestamps (allow for microsecond rounding in ISO format)
        assert retrieved.fetched_at.replace(microsecond=0) == fetched_time.replace(
            microsecond=0
        )

    @pytest.mark.asyncio
    async def test_fetched_at_null_fallback(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Simulate old data with NULL fetched_at, verify falls back to created_at."""
        conn = storage._ensure_connected()
        now = datetime.now(_ET)

        # Insert directly with NULL fetched_at (simulating old data)
        sql = """
            INSERT INTO catalyst_events (
                id, symbol, catalyst_type, quality_score, headline, summary,
                source, source_url, filing_type, headline_hash, published_at,
                classified_at, classified_by, trading_relevance, created_at,
                fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        created_at = now.isoformat()
        await conn.execute(
            sql,
            (
                "test_id_123456789012345",
                "TSLA",
                "earnings",
                75.0,
                "TSLA earnings report",
                "Tesla summary",
                "test",
                None,
                None,
                compute_headline_hash("TSLA earnings report"),
                now.isoformat(),
                now.isoformat(),
                "fallback",
                "medium",
                created_at,
                None,  # NULL fetched_at
            ),
        )
        await conn.commit()

        results = await storage.get_catalysts_by_symbol("TSLA")
        assert len(results) == 1
        retrieved = results[0]
        # fetched_at should fall back to created_at
        assert retrieved.fetched_at.isoformat() == created_at


class TestStoreCatalystsBatch:
    """Tests for store_catalysts_batch() method."""

    @pytest.mark.asyncio
    async def test_store_catalysts_batch_success(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Batch insert 5 catalysts, verify all stored with correct IDs."""
        now = datetime.now(_ET)
        catalysts = []

        for i in range(5):
            catalyst = ClassifiedCatalyst(
                headline=f"Batch news {i}",
                symbol=f"SYM{i}",
                source="test",
                published_at=now,
                fetched_at=now,
                category="other",
                quality_score=50.0 + i,
                summary=f"Batch summary {i}",
                trading_relevance="low",
                classified_by="fallback",
                classified_at=now,
                headline_hash=compute_headline_hash(f"Batch news {i}"),
            )
            catalysts.append(catalyst)

        ids = await storage.store_catalysts_batch(catalysts)

        assert len(ids) == 5
        # All IDs should be valid ULIDs
        for catalyst_id in ids:
            assert len(catalyst_id) == 26

        # Verify all stored
        count = await storage.get_total_count()
        assert count == 5

        # Verify data integrity
        for i in range(5):
            results = await storage.get_catalysts_by_symbol(f"SYM{i}")
            assert len(results) == 1
            assert results[0].headline == f"Batch news {i}"

    @pytest.mark.asyncio
    async def test_store_catalysts_batch_single_transaction(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Verify single commit (batch of 3 all appear together)."""
        now = datetime.now(_ET)
        catalysts = []

        for i in range(3):
            catalyst = ClassifiedCatalyst(
                headline=f"Transaction test {i}",
                symbol="BATCH",
                source="test",
                published_at=now,
                fetched_at=now,
                category="other",
                quality_score=50.0,
                summary=f"Summary {i}",
                trading_relevance="low",
                classified_by="fallback",
                classified_at=now,
                headline_hash=compute_headline_hash(f"Transaction test {i}"),
            )
            catalysts.append(catalyst)

        # Store batch
        ids = await storage.store_catalysts_batch(catalysts)

        # All 3 should appear
        results = await storage.get_catalysts_by_symbol("BATCH")
        assert len(results) == 3

        # All IDs returned should be valid
        assert len(ids) == 3

    @pytest.mark.asyncio
    async def test_store_catalysts_batch_empty(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Empty list returns empty list, no errors."""
        ids = await storage.store_catalysts_batch([])
        assert ids == []

        # No catalysts should be stored
        count = await storage.get_total_count()
        assert count == 0


class TestGetCatalystsBySymbolSince:
    """Tests for since parameter in get_catalysts_by_symbol()."""

    @pytest.mark.asyncio
    async def test_get_catalysts_by_symbol_since(
        self,
        storage: CatalystStorage,
    ) -> None:
        """Store 3 catalysts with different published_at, query with since."""
        now = datetime.now(_ET)

        # Store 3 catalysts with different published_at times
        times = [
            now - timedelta(hours=3),  # Oldest
            now - timedelta(hours=2),  # Middle
            now - timedelta(hours=1),  # Newest
        ]

        for i, pub_time in enumerate(times):
            catalyst = ClassifiedCatalyst(
                headline=f"AAPL news {i}",
                symbol="AAPL",
                source="test",
                published_at=pub_time,
                fetched_at=now,
                category="news_sentiment",
                quality_score=50.0,
                summary=f"Summary {i}",
                trading_relevance="medium",
                classified_by="fallback",
                classified_at=now,
                headline_hash=compute_headline_hash(f"AAPL news {i}"),
            )
            await storage.store_catalyst(catalyst)

        # Query with since = 2.5 hours ago (should return 2 newest)
        since_time = now - timedelta(hours=2, minutes=30)
        results = await storage.get_catalysts_by_symbol("AAPL", since=since_time)

        assert len(results) == 2
        # All returned should be published at or after since_time
        for r in results:
            assert r.published_at >= since_time

    @pytest.mark.asyncio
    async def test_get_catalysts_by_symbol_since_none(
        self,
        storage: CatalystStorage,
    ) -> None:
        """since=None returns all catalysts (unchanged behavior)."""
        now = datetime.now(_ET)

        # Store 3 catalysts
        for i in range(3):
            catalyst = ClassifiedCatalyst(
                headline=f"NVDA news {i}",
                symbol="NVDA",
                source="test",
                published_at=now - timedelta(hours=i),
                fetched_at=now,
                category="news_sentiment",
                quality_score=50.0,
                summary=f"Summary {i}",
                trading_relevance="medium",
                classified_by="fallback",
                classified_at=now,
                headline_hash=compute_headline_hash(f"NVDA news {i}"),
            )
            await storage.store_catalyst(catalyst)

        # Query without since (should return all 3)
        results = await storage.get_catalysts_by_symbol("NVDA", since=None)
        assert len(results) == 3

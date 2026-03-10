"""Tests for the CatalystPipeline.

Sprint 23.5 Session 3 — DEC-164
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from argus.ai.client import UsageRecord
from argus.core.event_bus import EventBus
from argus.core.events import CatalystEvent
from argus.intelligence import CatalystClassifier, CatalystPipeline
from argus.intelligence.config import CatalystConfig
from argus.intelligence.models import CatalystRawItem
from argus.intelligence.sources import CatalystSource
from argus.intelligence.storage import CatalystStorage

_ET = ZoneInfo("America/New_York")


class MockSource(CatalystSource):
    """Mock catalyst source for testing."""

    def __init__(self, name: str, items: list[CatalystRawItem]) -> None:
        self._name = name
        self._items = items
        self._started = False

    @property
    def source_name(self) -> str:
        return self._name

    async def fetch_catalysts(self, symbols: list[str]) -> list[CatalystRawItem]:
        return self._items

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False


def _make_claude_response(classifications: list[dict[str, Any]]) -> tuple[dict[str, Any], UsageRecord]:
    """Create a mock Claude API response."""
    import json

    response = {
        "type": "message",
        "content": [{"type": "text", "text": json.dumps(classifications)}],
    }
    usage = UsageRecord(
        input_tokens=100,
        output_tokens=50,
        model="claude-3-haiku",
        estimated_cost_usd=0.01,
    )
    return response, usage


@pytest.fixture
async def storage() -> CatalystStorage:
    """Create an in-memory storage instance."""
    s = CatalystStorage(":memory:")
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock ClaudeClient."""
    client = MagicMock()
    client.enabled = True
    return client


@pytest.fixture
def mock_usage_tracker() -> MagicMock:
    """Create a mock UsageTracker."""
    tracker = MagicMock()
    tracker.record_usage = AsyncMock()
    tracker.get_daily_usage = AsyncMock(return_value={"estimated_cost_usd": 0.0})
    return tracker


@pytest.fixture
def config() -> CatalystConfig:
    """Create a test config."""
    return CatalystConfig(
        enabled=True,
        max_batch_size=20,
        daily_cost_ceiling_usd=10.0,
    )


@pytest.fixture
def event_bus() -> EventBus:
    """Create an event bus."""
    return EventBus()


class TestCatalystPipeline:
    """Tests for the complete pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_sources_to_events(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
        event_bus: EventBus,
    ) -> None:
        """Full pipeline: sources return items → dedup → classify → store → events published."""
        now = datetime.now(_ET)

        # Create mock source with items
        items = [
            CatalystRawItem(
                headline="AAPL beats earnings",
                symbol="AAPL",
                source="test_source",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="TSLA announces new product",
                symbol="TSLA",
                source="test_source",
                published_at=now,
                fetched_at=now,
            ),
        ]
        source = MockSource("test_source", items)

        # Mock Claude response
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple beat earnings",
                "trading_relevance": "high",
            },
            {
                "category": "corporate_event",
                "quality_score": 70,
                "summary": "Tesla new product",
                "trading_relevance": "medium",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        # Track published events
        published_events: list[CatalystEvent] = []

        async def capture_event(event: CatalystEvent) -> None:
            published_events.append(event)

        event_bus.subscribe(CatalystEvent, capture_event)

        # Create and run pipeline
        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["AAPL", "TSLA"])
        await event_bus.drain()
        await pipeline.stop()

        # Verify results
        assert len(results) == 2
        assert results[0].symbol == "AAPL"
        assert results[1].symbol == "TSLA"

        # Verify storage
        aapl_catalysts = await storage.get_catalysts_by_symbol("AAPL")
        assert len(aapl_catalysts) == 1

        tsla_catalysts = await storage.get_catalysts_by_symbol("TSLA")
        assert len(tsla_catalysts) == 1

        # Verify events were published
        assert len(published_events) == 2
        symbols = {e.symbol for e in published_events}
        assert symbols == {"AAPL", "TSLA"}

    @pytest.mark.asyncio
    async def test_cross_source_dedup_same_headline(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
        event_bus: EventBus,
    ) -> None:
        """Same headline from FMP and Finnhub is classified only once."""
        now = datetime.now(_ET)

        # Same headline from two different sources
        duplicate_headline = "NVDA announces AI breakthrough"

        fmp_items = [
            CatalystRawItem(
                headline=duplicate_headline,
                symbol="NVDA",
                source="fmp_news",
                published_at=now,
                fetched_at=now,
            ),
        ]
        finnhub_items = [
            CatalystRawItem(
                headline=duplicate_headline,  # Same headline
                symbol="NVDA",
                source="finnhub",
                published_at=now,
                fetched_at=now,
            ),
        ]

        fmp_source = MockSource("fmp_news", fmp_items)
        finnhub_source = MockSource("finnhub", finnhub_items)

        # Mock Claude response for single item
        response, usage = _make_claude_response([
            {
                "category": "news_sentiment",
                "quality_score": 90,
                "summary": "NVDA AI breakthrough",
                "trading_relevance": "high",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        # Track published events
        published_events: list[CatalystEvent] = []

        async def capture_event(event: CatalystEvent) -> None:
            published_events.append(event)

        event_bus.subscribe(CatalystEvent, capture_event)

        # Create and run pipeline with both sources
        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[fmp_source, finnhub_source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["NVDA"])
        await event_bus.drain()
        await pipeline.stop()

        # Should only have ONE result despite two sources providing the same headline
        assert len(results) == 1
        assert results[0].symbol == "NVDA"
        assert results[0].headline == duplicate_headline

        # Should only have ONE event published
        assert len(published_events) == 1
        assert published_events[0].headline == duplicate_headline

        # First source wins for the source attribution
        # Since sources are processed in order [fmp, finnhub], fmp_news should win
        assert results[0].source == "fmp_news"

        # Verify only ONE item stored
        nvda_catalysts = await storage.get_catalysts_by_symbol("NVDA")
        assert len(nvda_catalysts) == 1

    @pytest.mark.asyncio
    async def test_pipeline_uses_batch_store(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
        event_bus: EventBus,
    ) -> None:
        """Pipeline uses store_catalysts_batch instead of individual store_catalyst calls."""
        from datetime import timedelta
        from unittest.mock import patch

        now = datetime.now(_ET)

        items = [
            CatalystRawItem(
                headline="AAPL earnings beat",
                symbol="AAPL",
                source="test_source",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="TSLA production update",
                symbol="TSLA",
                source="test_source",
                published_at=now + timedelta(hours=1),
                fetched_at=now + timedelta(hours=1),
            ),
        ]
        source = MockSource("test_source", items)

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple beat earnings",
                "trading_relevance": "high",
            },
            {
                "category": "corporate_event",
                "quality_score": 70,
                "summary": "Tesla production",
                "trading_relevance": "medium",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()

        # Patch both methods to track calls
        with patch.object(
            storage, "store_catalyst", wraps=storage.store_catalyst
        ) as mock_single, patch.object(
            storage, "store_catalysts_batch", wraps=storage.store_catalysts_batch
        ) as mock_batch:
            await pipeline.run_poll(["AAPL", "TSLA"])

            # Should use batch, not individual
            mock_batch.assert_called_once()
            mock_single.assert_not_called()

            # Verify correct number of items in batch call
            batch_call_args = mock_batch.call_args[0][0]
            assert len(batch_call_args) == 2

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_pipeline_publish_after_store(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
        event_bus: EventBus,
    ) -> None:
        """Events are published only after all catalysts are stored."""
        now = datetime.now(_ET)

        items = [
            CatalystRawItem(
                headline="AAPL earnings",
                symbol="AAPL",
                source="test_source",
                published_at=now,
                fetched_at=now,
            ),
        ]
        source = MockSource("test_source", items)

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple earnings",
                "trading_relevance": "high",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        # Track order of operations
        operation_order: list[str] = []

        original_batch_store = storage.store_catalysts_batch

        async def tracked_batch_store(catalysts: list) -> list[str]:
            result = await original_batch_store(catalysts)
            operation_order.append("store")
            return result

        original_publish = event_bus.publish

        async def tracked_publish(event: CatalystEvent) -> None:
            operation_order.append("publish")
            await original_publish(event)

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()

        storage.store_catalysts_batch = tracked_batch_store  # type: ignore[method-assign]
        event_bus.publish = tracked_publish  # type: ignore[method-assign]

        await pipeline.run_poll(["AAPL"])
        await event_bus.drain()

        # Store must happen before publish
        assert operation_order == ["store", "publish"]

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_pipeline_publish_failure_continues(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
        event_bus: EventBus,
    ) -> None:
        """Failed publish for one catalyst doesn't prevent others from publishing."""
        from datetime import timedelta

        now = datetime.now(_ET)

        items = [
            CatalystRawItem(
                headline="AAPL earnings",
                symbol="AAPL",
                source="test_source",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="TSLA production",
                symbol="TSLA",
                source="test_source",
                published_at=now + timedelta(hours=1),
                fetched_at=now + timedelta(hours=1),
            ),
            CatalystRawItem(
                headline="NVDA AI news",
                symbol="NVDA",
                source="test_source",
                published_at=now + timedelta(hours=2),
                fetched_at=now + timedelta(hours=2),
            ),
        ]
        source = MockSource("test_source", items)

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple earnings",
                "trading_relevance": "high",
            },
            {
                "category": "corporate_event",
                "quality_score": 70,
                "summary": "Tesla production",
                "trading_relevance": "medium",
            },
            {
                "category": "news_sentiment",
                "quality_score": 90,
                "summary": "NVDA AI",
                "trading_relevance": "high",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        # Track successful publishes
        published_symbols: list[str] = []
        call_count = 0

        original_publish = event_bus.publish

        async def failing_publish(event: CatalystEvent) -> None:
            nonlocal call_count
            call_count += 1
            # Fail on second publish (TSLA)
            if call_count == 2:
                raise RuntimeError("Simulated publish failure")
            published_symbols.append(event.symbol)
            await original_publish(event)

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        event_bus.publish = failing_publish  # type: ignore[method-assign]

        # Should NOT raise, despite middle publish failing
        results = await pipeline.run_poll(["AAPL", "TSLA", "NVDA"])
        await event_bus.drain()

        # All 3 items should be returned (stored)
        assert len(results) == 3

        # AAPL and NVDA should have published, TSLA failed
        assert "AAPL" in published_symbols
        assert "NVDA" in published_symbols
        assert "TSLA" not in published_symbols

        await pipeline.stop()


class TestSemanticDedup:
    """Tests for the semantic deduplication feature."""

    @pytest.mark.asyncio
    async def test_semantic_dedup_same_symbol_category_within_window(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        event_bus: EventBus,
    ) -> None:
        """Two items with same (symbol, category) within window: keep higher score."""
        from datetime import timedelta

        config = CatalystConfig(
            enabled=True,
            max_batch_size=20,
            daily_cost_ceiling_usd=10.0,
            dedup_window_minutes=30,
        )

        now = datetime.now(_ET)

        # Two AAPL earnings items, 10 minutes apart (within 30 min window)
        items = [
            CatalystRawItem(
                headline="AAPL beats earnings expectations",
                symbol="AAPL",
                source="source_a",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="AAPL earnings surprise higher than forecast",
                symbol="AAPL",
                source="source_b",
                published_at=now + timedelta(minutes=10),
                fetched_at=now + timedelta(minutes=10),
            ),
        ]
        source = MockSource("test_source", items)

        # First item has lower score (70), second has higher (90)
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 70,
                "summary": "Apple beat earnings",
                "trading_relevance": "high",
            },
            {
                "category": "earnings",
                "quality_score": 90,
                "summary": "Apple earnings surprise",
                "trading_relevance": "high",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["AAPL"])
        await pipeline.stop()

        # Should keep only the higher-scoring item
        assert len(results) == 1
        assert results[0].quality_score == 90
        assert "surprise" in results[0].summary.lower()

    @pytest.mark.asyncio
    async def test_semantic_dedup_same_symbol_different_category(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        event_bus: EventBus,
    ) -> None:
        """Two items with same symbol but different category: both kept."""
        from datetime import timedelta

        config = CatalystConfig(
            enabled=True,
            max_batch_size=20,
            daily_cost_ceiling_usd=10.0,
            dedup_window_minutes=30,
        )

        now = datetime.now(_ET)

        # AAPL earnings + AAPL insider trade (different categories)
        items = [
            CatalystRawItem(
                headline="AAPL beats earnings",
                symbol="AAPL",
                source="source_a",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="AAPL insider sells shares",
                symbol="AAPL",
                source="source_b",
                published_at=now + timedelta(minutes=5),
                fetched_at=now + timedelta(minutes=5),
            ),
        ]
        source = MockSource("test_source", items)

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple beat earnings",
                "trading_relevance": "high",
            },
            {
                "category": "insider_trade",
                "quality_score": 75,
                "summary": "Apple insider sale",
                "trading_relevance": "medium",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["AAPL"])
        await pipeline.stop()

        # Both should be kept (different categories)
        assert len(results) == 2
        categories = {r.category for r in results}
        assert categories == {"earnings", "insider_trade"}

    @pytest.mark.asyncio
    async def test_semantic_dedup_same_category_outside_window(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        event_bus: EventBus,
    ) -> None:
        """Two items with same (symbol, category) but outside window: both kept."""
        from datetime import timedelta

        config = CatalystConfig(
            enabled=True,
            max_batch_size=20,
            daily_cost_ceiling_usd=10.0,
            dedup_window_minutes=30,
        )

        now = datetime.now(_ET)

        # Two AAPL earnings items, 45 minutes apart (outside 30 min window)
        items = [
            CatalystRawItem(
                headline="AAPL Q1 earnings beat",
                symbol="AAPL",
                source="source_a",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="AAPL Q1 earnings call highlights",
                symbol="AAPL",
                source="source_b",
                published_at=now + timedelta(minutes=45),
                fetched_at=now + timedelta(minutes=45),
            ),
        ]
        source = MockSource("test_source", items)

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple Q1 beat",
                "trading_relevance": "high",
            },
            {
                "category": "earnings",
                "quality_score": 70,
                "summary": "Apple earnings call",
                "trading_relevance": "medium",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["AAPL"])
        await pipeline.stop()

        # Both should be kept (outside dedup window)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_semantic_dedup_equal_scores_keeps_first(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        event_bus: EventBus,
    ) -> None:
        """Two items with equal quality_score: first by published_at wins."""
        from datetime import timedelta

        config = CatalystConfig(
            enabled=True,
            max_batch_size=20,
            daily_cost_ceiling_usd=10.0,
            dedup_window_minutes=30,
        )

        now = datetime.now(_ET)

        # Two AAPL earnings items with same score, first one should win
        items = [
            CatalystRawItem(
                headline="AAPL earnings beat first report",
                symbol="AAPL",
                source="source_a",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="AAPL earnings beat second report",
                symbol="AAPL",
                source="source_b",
                published_at=now + timedelta(minutes=10),
                fetched_at=now + timedelta(minutes=10),
            ),
        ]
        source = MockSource("test_source", items)

        # Both have the same score
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple beat first",
                "trading_relevance": "high",
            },
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple beat second",
                "trading_relevance": "high",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["AAPL"])
        await pipeline.stop()

        # Should keep the first one (earlier published_at)
        assert len(results) == 1
        assert "first" in results[0].summary.lower()

    @pytest.mark.asyncio
    async def test_dedup_window_configurable(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        event_bus: EventBus,
    ) -> None:
        """dedup_window_minutes from config is respected."""
        from datetime import timedelta

        # Use a 10-minute window
        config = CatalystConfig(
            enabled=True,
            max_batch_size=20,
            daily_cost_ceiling_usd=10.0,
            dedup_window_minutes=10,
        )

        now = datetime.now(_ET)

        # Two items 15 minutes apart (outside 10-min window, but would be inside 30-min)
        items = [
            CatalystRawItem(
                headline="AAPL earnings beat first",
                symbol="AAPL",
                source="source_a",
                published_at=now,
                fetched_at=now,
            ),
            CatalystRawItem(
                headline="AAPL earnings beat second",
                symbol="AAPL",
                source="source_b",
                published_at=now + timedelta(minutes=15),
                fetched_at=now + timedelta(minutes=15),
            ),
        ]
        source = MockSource("test_source", items)

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 70,
                "summary": "Apple beat first",
                "trading_relevance": "high",
            },
            {
                "category": "earnings",
                "quality_score": 90,
                "summary": "Apple beat second",
                "trading_relevance": "high",
            },
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(["AAPL"])
        await pipeline.stop()

        # Both should be kept because 15 min > 10 min window
        assert len(results) == 2

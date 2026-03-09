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

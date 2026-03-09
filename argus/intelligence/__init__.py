"""Intelligence layer — AI-enhanced trading intelligence components (Sprint 23.5+).

Provides the NLP Catalyst Pipeline for ingesting, classifying, and surfacing
market-moving events from multiple data sources.

Components:
    - CatalystPipeline: Orchestrates sources → dedup → classify → store → publish
    - CatalystClassifier: Claude API + fallback keyword classification
    - CatalystStorage: SQLite persistence for catalysts and briefs
    - CatalystSource: Abstract base class for data sources

Sprint 23.5 — DEC-164
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from argus.core.events import CatalystEvent
from argus.intelligence.classifier import CatalystClassifier
from argus.intelligence.models import (
    CatalystClassification,
    CatalystRawItem,
    ClassifiedCatalyst,
    IntelligenceBrief,
    compute_headline_hash,
)
from argus.intelligence.sources import CatalystSource
from argus.intelligence.storage import CatalystStorage

if TYPE_CHECKING:
    from argus.core.event_bus import EventBus
    from argus.intelligence.config import CatalystConfig

logger = logging.getLogger(__name__)


class CatalystPipeline:
    """Orchestrates the NLP Catalyst Pipeline end-to-end.

    Coordinates data sources, deduplication, classification, storage,
    and Event Bus publishing for a complete catalyst ingestion flow.

    Flow:
        1. Fetch raw items from all enabled sources concurrently
        2. Flatten and deduplicate across sources by headline hash
        3. Classify batch via CatalystClassifier (Claude + fallback)
        4. Store each classified catalyst in SQLite
        5. Publish CatalystEvent on Event Bus for each item

    Usage:
        pipeline = CatalystPipeline(
            sources=[sec_edgar, fmp_news, finnhub],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )
        await pipeline.start()
        results = await pipeline.run_poll(["AAPL", "TSLA"])
        await pipeline.stop()
    """

    def __init__(
        self,
        sources: list[CatalystSource],
        classifier: CatalystClassifier,
        storage: CatalystStorage,
        event_bus: EventBus,
        config: CatalystConfig,
    ) -> None:
        """Initialize the pipeline.

        Args:
            sources: List of catalyst data sources.
            classifier: Classifier for categorizing raw items.
            storage: Storage for persisting catalysts.
            event_bus: Event bus for publishing CatalystEvents.
            config: Pipeline configuration.
        """
        self._sources = sources
        self._classifier = classifier
        self._storage = storage
        self._event_bus = event_bus
        self._config = config

    async def start(self) -> None:
        """Initialize storage and start all sources.

        Call this before run_poll().
        """
        await self._storage.initialize()
        logger.info("Starting %d catalyst sources", len(self._sources))

        for source in self._sources:
            try:
                await source.start()
                logger.info("Started source: %s", source.source_name)
            except Exception as e:
                logger.error("Failed to start source %s: %s", source.source_name, e)

    async def stop(self) -> None:
        """Stop all sources.

        Call this during shutdown.
        """
        logger.info("Stopping %d catalyst sources", len(self._sources))

        for source in self._sources:
            try:
                await source.stop()
                logger.debug("Stopped source: %s", source.source_name)
            except Exception as e:
                logger.error("Failed to stop source %s: %s", source.source_name, e)

    async def run_poll(self, symbols: list[str]) -> list[ClassifiedCatalyst]:
        """Run a single poll cycle across all sources.

        Fetches from all sources concurrently, deduplicates, classifies,
        stores, and publishes events.

        Args:
            symbols: List of stock ticker symbols to poll.

        Returns:
            List of newly classified catalysts.
        """
        if not symbols:
            return []

        # Step 1: Fetch from all sources concurrently
        fetch_tasks = [source.fetch_catalysts(symbols) for source in self._sources]
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Collect raw items and log per-source counts
        all_raw_items: list[CatalystRawItem] = []
        for source, result in zip(self._sources, results, strict=True):
            if isinstance(result, Exception):
                logger.error("Source %s failed: %s", source.source_name, result)
                continue

            items = result
            logger.debug("Source %s returned %d items", source.source_name, len(items))
            all_raw_items.extend(items)

        logger.info(
            "Fetched %d total raw items from %d sources",
            len(all_raw_items),
            len(self._sources),
        )

        if not all_raw_items:
            return []

        # Step 2: Deduplicate across sources by headline hash (first occurrence wins)
        seen_hashes: set[str] = set()
        deduplicated: list[CatalystRawItem] = []

        for item in all_raw_items:
            headline_hash = compute_headline_hash(item.headline)
            if headline_hash not in seen_hashes:
                seen_hashes.add(headline_hash)
                deduplicated.append(item)

        dedup_count = len(all_raw_items) - len(deduplicated)
        if dedup_count > 0:
            logger.debug("Deduplicated %d duplicate items across sources", dedup_count)

        # Step 3: Classify batch
        classified = await self._classifier.classify_batch(deduplicated)

        # Count fallback vs Claude classifications
        fallback_count = sum(1 for c in classified if c.classified_by == "fallback")
        claude_count = len(classified) - fallback_count

        logger.info(
            "Classified %d items: %d via Claude, %d via fallback",
            len(classified),
            claude_count,
            fallback_count,
        )

        # Step 4 & 5: Store and publish events
        for catalyst in classified:
            # Store
            await self._storage.store_catalyst(catalyst)

            # Publish CatalystEvent
            event = CatalystEvent(
                symbol=catalyst.symbol,
                catalyst_type=catalyst.category,
                quality_score=catalyst.quality_score,
                headline=catalyst.headline,
                summary=catalyst.summary,
                source=catalyst.source,
                source_url=catalyst.source_url,
                filing_type=catalyst.filing_type,
                published_at=catalyst.published_at,
                classified_at=catalyst.classified_at,
            )
            await self._event_bus.publish(event)

        logger.info(
            "Pipeline cycle: %d fetched, %d dedups, %d classified, %d published",
            len(all_raw_items),
            dedup_count,
            len(classified),
            len(classified),
        )

        return classified


__all__ = [
    "CatalystClassifier",
    "CatalystClassification",
    "CatalystPipeline",
    "CatalystRawItem",
    "CatalystSource",
    "CatalystStorage",
    "ClassifiedCatalyst",
    "IntelligenceBrief",
    "compute_headline_hash",
]

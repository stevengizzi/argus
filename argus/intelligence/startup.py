"""Intelligence pipeline startup factory.

Provides factory functions to build all intelligence pipeline components
from configuration. Designed to be called from the app lifecycle handler
but is independently testable.

Sprint 23.6 Session 3a — DEC-164
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from argus.intelligence import CatalystPipeline
from argus.intelligence.briefing import BriefingGenerator
from argus.intelligence.classifier import CatalystClassifier
from argus.intelligence.sources import CatalystSource
from argus.intelligence.sources.finnhub import FinnhubClient
from argus.intelligence.sources.fmp_news import FMPNewsClient
from argus.intelligence.sources.sec_edgar import SECEdgarClient
from argus.intelligence.storage import CatalystStorage

if TYPE_CHECKING:
    from argus.ai.client import ClaudeClient
    from argus.ai.usage import UsageTracker
    from argus.core.event_bus import EventBus
    from argus.intelligence.config import CatalystConfig

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceComponents:
    """Container for all intelligence pipeline components.

    Attributes:
        pipeline: The main catalyst pipeline orchestrator.
        storage: SQLite storage for catalysts and briefs.
        classifier: Catalyst classifier (Claude + fallback).
        briefing_generator: Pre-market brief generator.
        sources: List of enabled catalyst data sources.
    """

    pipeline: CatalystPipeline
    storage: CatalystStorage
    classifier: CatalystClassifier
    briefing_generator: BriefingGenerator
    sources: list[CatalystSource]


async def create_intelligence_components(
    config: CatalystConfig,
    event_bus: EventBus,
    ai_client: ClaudeClient | None,
    usage_tracker: UsageTracker | None,
    data_dir: str = "data",
) -> IntelligenceComponents | None:
    """Create all intelligence pipeline components from configuration.

    Factory function that builds the complete intelligence pipeline based
    on configuration settings. Returns None if the pipeline is disabled.

    Args:
        config: Catalyst pipeline configuration.
        event_bus: Event bus for publishing CatalystEvents.
        ai_client: Optional Claude API client. If None or disabled, classifier
            degrades to fallback-only mode.
        usage_tracker: Optional usage tracker for API cost tracking.
        data_dir: Base data directory for the catalyst database.

    Returns:
        IntelligenceComponents containing all pipeline components,
        or None if config.enabled is False.
    """
    if not config.enabled:
        logger.info("Intelligence pipeline disabled in config")
        return None

    # Create storage with path under data_dir
    db_path = Path(data_dir) / "catalyst.db"
    storage = CatalystStorage(db_path)

    # Build sources list based on individual enabled flags
    sources: list[CatalystSource] = []
    enabled_source_names: list[str] = []

    if config.sources.sec_edgar.enabled:
        sources.append(SECEdgarClient(config.sources.sec_edgar))
        enabled_source_names.append("sec_edgar")

    if config.sources.fmp_news.enabled:
        sources.append(FMPNewsClient(config.sources.fmp_news))
        enabled_source_names.append("fmp_news")

    if config.sources.finnhub.enabled:
        sources.append(FinnhubClient(config.sources.finnhub))
        enabled_source_names.append("finnhub")

    # Determine classifier mode
    # If ai_client is None or disabled, classifier still works via fallback
    # The classifier checks client.enabled internally in _classify_with_claude
    classifier_mode = "fallback-only"
    if ai_client is not None and ai_client.enabled:
        classifier_mode = "claude"

    # Create classifier
    # Note: classifier handles ai_client.enabled == False gracefully by returning
    # None from _classify_with_claude, which triggers fallback path
    classifier = CatalystClassifier(
        client=ai_client,  # type: ignore[arg-type]
        usage_tracker=usage_tracker,  # type: ignore[arg-type]
        config=config,
        storage=storage,
    )

    # Create briefing generator
    briefing_generator = BriefingGenerator(
        client=ai_client,  # type: ignore[arg-type]
        storage=storage,
        usage_tracker=usage_tracker,  # type: ignore[arg-type]
        config=config.briefing,
    )

    # Create pipeline
    pipeline = CatalystPipeline(
        sources=sources,
        classifier=classifier,
        storage=storage,
        event_bus=event_bus,
        config=config,
    )

    logger.info(
        "Intelligence pipeline created: %d sources enabled [%s], classifier mode=%s",
        len(sources),
        ", ".join(enabled_source_names) if enabled_source_names else "none",
        classifier_mode,
    )

    return IntelligenceComponents(
        pipeline=pipeline,
        storage=storage,
        classifier=classifier,
        briefing_generator=briefing_generator,
        sources=sources,
    )


async def shutdown_intelligence(components: IntelligenceComponents) -> None:
    """Shutdown intelligence pipeline components.

    Stops the pipeline and closes storage connections. Safe to call
    even if components were not fully started.

    Args:
        components: The intelligence components to shut down.
    """
    logger.info("Shutting down intelligence pipeline")

    await components.pipeline.stop()
    await components.storage.close()

    logger.info("Intelligence pipeline shutdown complete")

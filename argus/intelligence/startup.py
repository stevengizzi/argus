"""Intelligence pipeline startup factory.

Provides factory functions to build all intelligence pipeline components
from configuration. Designed to be called from the app lifecycle handler
but is independently testable.

Sprint 23.6 Session 3a — DEC-164
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import time as dt_time
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.intelligence import CatalystPipeline
from argus.intelligence.briefing import BriefingGenerator
from argus.intelligence.classifier import CatalystClassifier
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQualityEngine
from argus.intelligence.sources import CatalystSource
from argus.intelligence.sources.finnhub import FinnhubClient
from argus.intelligence.sources.fmp_news import FMPNewsClient
from argus.intelligence.sources.sec_edgar import SECEdgarClient
from argus.intelligence.storage import CatalystStorage

if TYPE_CHECKING:
    from argus.ai.client import ClaudeClient
    from argus.ai.usage import UsageTracker
    from argus.core.event_bus import EventBus
    from argus.db.manager import DatabaseManager
    from argus.intelligence.config import CatalystConfig, QualityEngineConfig

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


def create_quality_components(
    config: QualityEngineConfig, db_manager: DatabaseManager | None = None
) -> tuple[SetupQualityEngine, DynamicPositionSizer] | None:
    """Build quality engine + sizer from config. Returns None if disabled.

    Args:
        config: Quality engine configuration.
        db_manager: Optional database manager for quality history persistence.

    Returns:
        Tuple of (SetupQualityEngine, DynamicPositionSizer) if enabled,
        None if config.enabled is False.
    """
    if not config.enabled:
        logger.info("Quality engine disabled in config")
        return None

    engine = SetupQualityEngine(config, db_manager=db_manager)
    sizer = DynamicPositionSizer(config)

    logger.info("Quality components created (engine + sizer)")
    return engine, sizer


async def build_counterfactual_tracker(
    config: object,
    candle_store: object | None = None,
) -> tuple[object, object] | None:
    """Build and initialize the Counterfactual Engine components.

    Returns None if counterfactual.enabled is False.

    Args:
        config: SystemConfig with a counterfactual attribute.
        candle_store: Optional IntradayCandleStore for backfill.

    Returns:
        Tuple of (CounterfactualTracker, CounterfactualStore) if enabled,
        None if disabled.
    """
    from argus.intelligence.counterfactual import CounterfactualTracker
    from argus.intelligence.counterfactual_store import CounterfactualStore

    cf_config = config.counterfactual  # type: ignore[attr-defined]
    if not cf_config.enabled:
        logger.info("Counterfactual Engine disabled in config")
        return None

    store = CounterfactualStore(db_path="data/counterfactual.db")
    await store.initialize()

    # Attach live QualityEngineConfig so the tracker can stamp each shadow
    # position with a scoring-context fingerprint (FIX-01 audit 2026-04-21).
    # isinstance-gated — tests that pass a MagicMock config must not crash
    # the fingerprint code path when they don't exercise it.
    from argus.intelligence.config import QualityEngineConfig

    raw_qe = getattr(config, "quality_engine", None)
    quality_config = raw_qe if isinstance(raw_qe, QualityEngineConfig) else None

    tracker = CounterfactualTracker(
        candle_store=candle_store,
        eod_close_time=cf_config.eod_close_time,
        no_data_timeout_seconds=cf_config.no_data_timeout_seconds,
        quality_config=quality_config,
    )
    tracker.set_store(store)

    logger.info("Counterfactual Engine created (tracker + store)")
    return tracker, store


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


async def run_polling_loop(
    pipeline: CatalystPipeline,
    config: CatalystConfig,
    get_symbols: Callable[[], list[str]],
    market_open: str = "09:30",
    market_close: str = "16:00",
    firehose: bool = True,
) -> None:
    """Run the catalyst polling loop indefinitely.

    Polls the pipeline at configurable intervals, with market-hours-aware
    interval switching. Handles errors gracefully without crashing.

    Args:
        pipeline: The CatalystPipeline instance to poll.
        config: Catalyst configuration with polling intervals.
        get_symbols: Callback that returns the current list of symbols to poll.
        market_open: Market open time in HH:MM format (ET).
        market_close: Market close time in HH:MM format (ET).
        firehose: When True (default), use firehose mode for market-wide
            feed instead of per-symbol polling.
    """
    logger.debug("Polling loop coroutine entered")

    et_tz = ZoneInfo("America/New_York")
    open_hour, open_minute = map(int, market_open.split(":"))
    close_hour, close_minute = map(int, market_close.split(":"))
    open_time = dt_time(open_hour, open_minute)
    close_time = dt_time(close_hour, close_minute)

    # Overlap protection lock
    poll_lock = asyncio.Lock()

    logger.info(
        "Polling loop started (premarket=%ds, session=%ds, market=%s-%s ET)",
        config.polling_interval_premarket_seconds,
        config.polling_interval_session_seconds,
        market_open,
        market_close,
    )

    while True:
        poll_start = time.monotonic()

        # Determine interval based on current ET time
        now_et = datetime.now(et_tz)
        current_time = now_et.time()
        is_market_hours = open_time <= current_time < close_time

        if is_market_hours:
            interval = config.polling_interval_session_seconds
        else:
            interval = config.polling_interval_premarket_seconds

        # Attempt poll with overlap protection
        if poll_lock.locked():
            logger.warning("Previous poll still running, skipping this cycle")
        else:
            async with poll_lock:
                try:
                    # Initialize symbols here so it is always defined in except blocks
                    # even when firehose=True skips the get_symbols() assignment path
                    symbols: list[str] = []
                    if firehose:
                        logger.info("Polling in firehose mode (market-wide)")
                        await asyncio.wait_for(
                            pipeline.run_poll(symbols=[], firehose=True),
                            timeout=120.0,
                        )
                    else:
                        symbols = get_symbols()
                        if not symbols:
                            logger.warning(
                                "No symbols returned from get_symbols(), "
                                "skipping poll"
                            )
                        else:
                            logger.info(
                                "Polling %d symbols: %s...",
                                len(symbols),
                                symbols[:5],
                            )
                            await asyncio.wait_for(
                                pipeline.run_poll(symbols),
                                timeout=120.0,
                            )
                except asyncio.TimeoutError:
                    logger.critical(
                        "Poll cycle timed out after 120s waiting for source fetches "
                        "(%d sources, %d symbols)",
                        len(pipeline._sources),
                        len(symbols),
                    )
                except asyncio.CancelledError:
                    logger.info("Polling loop cancelled")
                    raise
                except Exception as e:
                    logger.error("Poll cycle failed: %s", e, exc_info=True)

        # Calculate sleep time
        poll_duration = time.monotonic() - poll_start
        sleep_time = interval - poll_duration

        if sleep_time <= 0:
            logger.warning(
                "Poll cycle took %.1fs, exceeding interval of %ds",
                poll_duration,
                interval,
            )
        else:
            await asyncio.sleep(sleep_time)

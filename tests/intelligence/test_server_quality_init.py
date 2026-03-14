"""Tests for quality engine server initialization and firehose pipeline mode.

Sprint 24, Session 7.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.core.event_bus import EventBus
from argus.intelligence.config import (
    CatalystConfig,
    FinnhubConfig,
    FMPNewsConfig,
    QualityEngineConfig,
    SECEdgarConfig,
    SourcesConfig,
)
from argus.intelligence.models import CatalystRawItem
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQualityEngine
from argus.intelligence.sources import CatalystSource
from argus.intelligence.startup import (
    create_quality_components,
    run_polling_loop,
)

_ET = ZoneInfo("America/New_York")


# --- Fixtures ---


@pytest.fixture
def enabled_quality_config() -> QualityEngineConfig:
    """Quality engine config with enabled=True."""
    return QualityEngineConfig(enabled=True)


@pytest.fixture
def disabled_quality_config() -> QualityEngineConfig:
    """Quality engine config with enabled=False."""
    return QualityEngineConfig(enabled=False)


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Mock DatabaseManager."""
    return MagicMock()


class MockFirehoseSource(CatalystSource):
    """Mock source that tracks fetch_catalysts calls."""

    def __init__(self, name: str, items: list[CatalystRawItem] | None = None) -> None:
        self._name = name
        self._items = items or []
        self.fetch_calls: list[dict] = []

    @property
    def source_name(self) -> str:
        return self._name

    async def fetch_catalysts(
        self, symbols: list[str], firehose: bool = False
    ) -> list[CatalystRawItem]:
        self.fetch_calls.append({"symbols": symbols, "firehose": firehose})
        return self._items

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


# --- Tests: create_quality_components ---


class TestCreateQualityComponents:
    """Tests for the create_quality_components factory."""

    def test_create_quality_components_enabled(
        self, enabled_quality_config: QualityEngineConfig
    ) -> None:
        """Returns (engine, sizer) tuple when enabled."""
        result = create_quality_components(enabled_quality_config)

        assert result is not None
        engine, sizer = result
        assert isinstance(engine, SetupQualityEngine)
        assert isinstance(sizer, DynamicPositionSizer)

    def test_create_quality_components_disabled(
        self, disabled_quality_config: QualityEngineConfig
    ) -> None:
        """Returns None when enabled=false."""
        result = create_quality_components(disabled_quality_config)

        assert result is None

    def test_create_quality_components_with_db_manager(
        self,
        enabled_quality_config: QualityEngineConfig,
        mock_db_manager: MagicMock,
    ) -> None:
        """Passes db_manager through to SetupQualityEngine."""
        result = create_quality_components(
            enabled_quality_config, db_manager=mock_db_manager
        )

        assert result is not None
        engine, _ = result
        assert engine._db is mock_db_manager

    def test_create_quality_components_without_db_manager(
        self, enabled_quality_config: QualityEngineConfig
    ) -> None:
        """Engine created with None db_manager when not provided."""
        result = create_quality_components(enabled_quality_config)

        assert result is not None
        engine, _ = result
        assert engine._db is None


# --- Tests: Pipeline firehose mode ---


class TestPipelineFirehoseMode:
    """Tests for CatalystPipeline.run_poll firehose parameter."""

    @pytest.fixture
    def config(self) -> CatalystConfig:
        return CatalystConfig(enabled=True, max_batch_size=20)

    @pytest.fixture
    def event_bus(self) -> EventBus:
        return EventBus()

    @pytest.mark.asyncio
    async def test_pipeline_run_firehose_mode(
        self, config: CatalystConfig, event_bus: EventBus
    ) -> None:
        """Sources called with firehose=True when pipeline.run_poll(firehose=True)."""
        from argus.intelligence import CatalystPipeline
        from argus.intelligence.classifier import CatalystClassifier
        from argus.intelligence.storage import CatalystStorage

        source = MockFirehoseSource("test_source")

        storage = CatalystStorage(":memory:")
        await storage.initialize()

        mock_client = MagicMock()
        mock_client.enabled = False
        mock_tracker = MagicMock()
        mock_tracker.get_daily_usage = AsyncMock(
            return_value={"estimated_cost_usd": 0.0}
        )

        classifier = CatalystClassifier(mock_client, mock_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        await pipeline.run_poll(symbols=[], firehose=True)
        await pipeline.stop()
        await storage.close()

        assert len(source.fetch_calls) == 1
        assert source.fetch_calls[0]["firehose"] is True
        assert source.fetch_calls[0]["symbols"] == []

    @pytest.mark.asyncio
    async def test_pipeline_run_per_symbol_mode(
        self, config: CatalystConfig, event_bus: EventBus
    ) -> None:
        """Default behavior unchanged: sources called with firehose=False."""
        from argus.intelligence import CatalystPipeline
        from argus.intelligence.classifier import CatalystClassifier
        from argus.intelligence.storage import CatalystStorage

        source = MockFirehoseSource("test_source")

        storage = CatalystStorage(":memory:")
        await storage.initialize()

        mock_client = MagicMock()
        mock_client.enabled = False
        mock_tracker = MagicMock()
        mock_tracker.get_daily_usage = AsyncMock(
            return_value={"estimated_cost_usd": 0.0}
        )

        classifier = CatalystClassifier(mock_client, mock_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        await pipeline.run_poll(symbols=["AAPL", "TSLA"])
        await pipeline.stop()
        await storage.close()

        assert len(source.fetch_calls) == 1
        assert source.fetch_calls[0]["firehose"] is False
        assert source.fetch_calls[0]["symbols"] == ["AAPL", "TSLA"]

    @pytest.mark.asyncio
    async def test_pipeline_firehose_empty_sources_return(
        self, config: CatalystConfig, event_bus: EventBus
    ) -> None:
        """Firehose mode with sources returning empty lists completes without error."""
        from argus.intelligence import CatalystPipeline
        from argus.intelligence.classifier import CatalystClassifier
        from argus.intelligence.storage import CatalystStorage

        source = MockFirehoseSource("empty_source", items=[])

        storage = CatalystStorage(":memory:")
        await storage.initialize()

        mock_client = MagicMock()
        mock_client.enabled = False
        mock_tracker = MagicMock()
        mock_tracker.get_daily_usage = AsyncMock(
            return_value={"estimated_cost_usd": 0.0}
        )

        classifier = CatalystClassifier(mock_client, mock_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(symbols=[], firehose=True)
        await pipeline.stop()
        await storage.close()

        assert results == []

    @pytest.mark.asyncio
    async def test_pipeline_empty_symbols_no_firehose_returns_empty(
        self, config: CatalystConfig, event_bus: EventBus
    ) -> None:
        """Empty symbols without firehose still returns [] (backward compat)."""
        from argus.intelligence import CatalystPipeline
        from argus.intelligence.classifier import CatalystClassifier
        from argus.intelligence.storage import CatalystStorage

        source = MockFirehoseSource("test_source")

        storage = CatalystStorage(":memory:")
        await storage.initialize()

        mock_client = MagicMock()
        mock_client.enabled = False
        mock_tracker = MagicMock()
        mock_tracker.get_daily_usage = AsyncMock(
            return_value={"estimated_cost_usd": 0.0}
        )

        classifier = CatalystClassifier(mock_client, mock_tracker, config, storage)
        pipeline = CatalystPipeline(
            sources=[source],
            classifier=classifier,
            storage=storage,
            event_bus=event_bus,
            config=config,
        )

        await pipeline.start()
        results = await pipeline.run_poll(symbols=[])
        await pipeline.stop()
        await storage.close()

        assert results == []
        # Source should NOT have been called
        assert len(source.fetch_calls) == 0


# --- Tests: Polling loop firehose ---


class TestPollingLoopFirehose:
    """Tests for firehose parameter in run_polling_loop."""

    @pytest.fixture
    def mock_pipeline(self) -> MagicMock:
        pipeline = MagicMock()
        pipeline.run_poll = AsyncMock(return_value=[])
        pipeline._sources = []
        return pipeline

    @pytest.fixture
    def polling_config(self) -> CatalystConfig:
        return CatalystConfig(
            enabled=True,
            polling_interval_premarket_seconds=60,
            polling_interval_session_seconds=120,
        )

    @pytest.mark.asyncio
    async def test_polling_loop_firehose_calls_run_poll_with_firehose(
        self, mock_pipeline: MagicMock, polling_config: CatalystConfig
    ) -> None:
        """Polling loop with firehose=True calls pipeline.run_poll(firehose=True)."""
        call_count = 0

        async def capture_run_poll(
            symbols: list[str] = [], firehose: bool = False
        ) -> list:
            nonlocal call_count
            call_count += 1
            assert firehose is True
            assert symbols == []
            raise asyncio.CancelledError()

        mock_pipeline.run_poll = capture_run_poll

        task = asyncio.create_task(
            run_polling_loop(
                pipeline=mock_pipeline,
                config=polling_config,
                get_symbols=lambda: ["AAPL"],
                firehose=True,
            )
        )

        with pytest.raises(asyncio.CancelledError):
            await task

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_polling_loop_no_firehose_uses_get_symbols(
        self, mock_pipeline: MagicMock, polling_config: CatalystConfig
    ) -> None:
        """Polling loop with firehose=False calls get_symbols and passes to run_poll."""
        call_count = 0

        async def capture_run_poll(
            symbols: list[str], firehose: bool = False
        ) -> list:
            nonlocal call_count
            call_count += 1
            assert firehose is False
            assert symbols == ["AAPL", "TSLA"]
            raise asyncio.CancelledError()

        mock_pipeline.run_poll = capture_run_poll

        task = asyncio.create_task(
            run_polling_loop(
                pipeline=mock_pipeline,
                config=polling_config,
                get_symbols=lambda: ["AAPL", "TSLA"],
                firehose=False,
            )
        )

        with pytest.raises(asyncio.CancelledError):
            await task

        assert call_count == 1


# --- Tests: Finnhub firehose suppression ---


class TestFinnhubFirehoseSuppression:
    """Verify firehose mode with symbols=[] suppresses per-symbol rec calls."""

    @pytest.mark.asyncio
    async def test_finnhub_firehose_single_api_call(self) -> None:
        """pipeline.run(symbols=[], firehose=True) results in exactly 1 API call
        per source (general news), NOT 1+N per-symbol calls.
        """
        from argus.intelligence.sources.finnhub import FinnhubClient

        config = FinnhubConfig(enabled=True)
        client = FinnhubClient(config)

        # Simulate started state
        client._api_key = "test-key"
        client._session = MagicMock()

        general_news_called = False
        company_news_calls: list[str] = []
        rec_calls: list[str] = []

        async def mock_general_news(fetch_time: datetime) -> list[CatalystRawItem]:
            nonlocal general_news_called
            general_news_called = True
            return []

        async def mock_company_news(
            symbol: str, fetch_time: datetime
        ) -> list[CatalystRawItem]:
            company_news_calls.append(symbol)
            return []

        async def mock_recommendations(
            symbol: str, fetch_time: datetime
        ) -> list[CatalystRawItem]:
            rec_calls.append(symbol)
            return []

        client._fetch_general_news = mock_general_news  # type: ignore[method-assign]
        client._fetch_company_news = mock_company_news  # type: ignore[method-assign]
        client._fetch_recommendations = mock_recommendations  # type: ignore[method-assign]

        result = await client.fetch_catalysts(symbols=[], firehose=True)

        assert general_news_called is True
        assert company_news_calls == []
        assert rec_calls == []



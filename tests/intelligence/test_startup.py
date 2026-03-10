"""Tests for the intelligence startup factory.

Sprint 23.6 Session 3a — DEC-164
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.event_bus import EventBus
from argus.intelligence.config import (
    CatalystConfig,
    FinnhubConfig,
    FMPNewsConfig,
    SECEdgarConfig,
    SourcesConfig,
)
from argus.intelligence.startup import (
    IntelligenceComponents,
    create_intelligence_components,
    shutdown_intelligence,
)


@pytest.fixture
def event_bus() -> EventBus:
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def mock_ai_client() -> MagicMock:
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
def disabled_config() -> CatalystConfig:
    """Create a disabled config."""
    return CatalystConfig(enabled=False)


@pytest.fixture
def enabled_config_all_sources() -> CatalystConfig:
    """Create an enabled config with all sources enabled."""
    return CatalystConfig(
        enabled=True,
        sources=SourcesConfig(
            sec_edgar=SECEdgarConfig(enabled=True, user_agent_email="test@example.com"),
            fmp_news=FMPNewsConfig(enabled=True),
            finnhub=FinnhubConfig(enabled=True),
        ),
    )


@pytest.fixture
def enabled_config_partial_sources() -> CatalystConfig:
    """Create an enabled config with only SEC EDGAR enabled."""
    return CatalystConfig(
        enabled=True,
        sources=SourcesConfig(
            sec_edgar=SECEdgarConfig(enabled=True, user_agent_email="test@example.com"),
            fmp_news=FMPNewsConfig(enabled=False),
            finnhub=FinnhubConfig(enabled=False),
        ),
    )


@pytest.fixture
def enabled_config_no_sources() -> CatalystConfig:
    """Create an enabled config with no sources enabled."""
    return CatalystConfig(
        enabled=True,
        sources=SourcesConfig(
            sec_edgar=SECEdgarConfig(enabled=False),
            fmp_news=FMPNewsConfig(enabled=False),
            finnhub=FinnhubConfig(enabled=False),
        ),
    )


class TestCreateIntelligenceComponents:
    """Tests for create_intelligence_components factory."""

    @pytest.mark.asyncio
    async def test_create_disabled_returns_none(
        self,
        disabled_config: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
    ) -> None:
        """Factory returns None when config.enabled is False."""
        result = await create_intelligence_components(
            config=disabled_config,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_enabled_all_sources(
        self,
        enabled_config_all_sources: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Factory creates components with all three sources when all are enabled."""
        result = await create_intelligence_components(
            config=enabled_config_all_sources,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
            data_dir=str(tmp_path),
        )

        assert result is not None
        assert isinstance(result, IntelligenceComponents)
        assert len(result.sources) == 3
        assert result.pipeline is not None
        assert result.storage is not None
        assert result.classifier is not None
        assert result.briefing_generator is not None

        # Verify source types
        source_names = {s.source_name for s in result.sources}
        assert "sec_edgar" in source_names
        assert "fmp_news" in source_names
        assert "finnhub" in source_names

        # Cleanup
        await result.storage.close()

    @pytest.mark.asyncio
    async def test_create_enabled_partial_sources(
        self,
        enabled_config_partial_sources: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Factory creates components with only SEC EDGAR when others are disabled."""
        result = await create_intelligence_components(
            config=enabled_config_partial_sources,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
            data_dir=str(tmp_path),
        )

        assert result is not None
        assert len(result.sources) == 1
        assert result.sources[0].source_name == "sec_edgar"

        # Cleanup
        await result.storage.close()

    @pytest.mark.asyncio
    async def test_create_no_sources_enabled(
        self,
        enabled_config_no_sources: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Factory creates components with empty sources list when all sources disabled."""
        result = await create_intelligence_components(
            config=enabled_config_no_sources,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
            data_dir=str(tmp_path),
        )

        assert result is not None
        assert len(result.sources) == 0
        assert result.pipeline is not None  # Pipeline still created

        # Cleanup
        await result.storage.close()

    @pytest.mark.asyncio
    async def test_create_no_ai_client(
        self,
        enabled_config_all_sources: CatalystConfig,
        event_bus: EventBus,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Factory creates classifier in fallback mode when ai_client is None."""
        result = await create_intelligence_components(
            config=enabled_config_all_sources,
            event_bus=event_bus,
            ai_client=None,
            usage_tracker=mock_usage_tracker,
            data_dir=str(tmp_path),
        )

        assert result is not None
        assert result.classifier is not None
        # Classifier is created even without ai_client (fallback mode)

        # Cleanup
        await result.storage.close()

    @pytest.mark.asyncio
    async def test_create_with_ai_client(
        self,
        enabled_config_all_sources: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Factory creates classifier with Claude mode when ai_client is provided and enabled."""
        mock_ai_client.enabled = True

        result = await create_intelligence_components(
            config=enabled_config_all_sources,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
            data_dir=str(tmp_path),
        )

        assert result is not None
        assert result.classifier is not None
        # Verify the classifier was given the client
        assert result.classifier._client is mock_ai_client

        # Cleanup
        await result.storage.close()

    @pytest.mark.asyncio
    async def test_storage_path_uses_data_dir(
        self,
        enabled_config_all_sources: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Factory creates storage with correct path under data_dir."""
        custom_data_dir = str(tmp_path / "custom_data")

        result = await create_intelligence_components(
            config=enabled_config_all_sources,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
            data_dir=custom_data_dir,
        )

        assert result is not None
        expected_path = str(Path(custom_data_dir) / "catalyst.db")
        assert result.storage._db_path == expected_path

        # Cleanup
        await result.storage.close()


class TestShutdownIntelligence:
    """Tests for shutdown_intelligence helper."""

    @pytest.mark.asyncio
    async def test_shutdown_calls_stop_and_close(
        self,
        enabled_config_all_sources: CatalystConfig,
        event_bus: EventBus,
        mock_ai_client: MagicMock,
        mock_usage_tracker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Shutdown calls pipeline.stop() and storage.close()."""
        result = await create_intelligence_components(
            config=enabled_config_all_sources,
            event_bus=event_bus,
            ai_client=mock_ai_client,
            usage_tracker=mock_usage_tracker,
            data_dir=str(tmp_path),
        )

        assert result is not None

        # Patch the methods to track calls
        with patch.object(
            result.pipeline, "stop", new_callable=AsyncMock
        ) as mock_stop, patch.object(
            result.storage, "close", new_callable=AsyncMock
        ) as mock_close:
            await shutdown_intelligence(result)

            mock_stop.assert_called_once()
            mock_close.assert_called_once()

"""Tests for intelligence pipeline integration in server lifespan.

Sprint 23.6 Session 3b — Tests for app lifecycle wiring of intelligence pipeline.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from argus.api.dependencies import AppState
from argus.core.config import ApiConfig, SystemConfig
from argus.intelligence.config import CatalystConfig

if TYPE_CHECKING:
    from argus.core.event_bus import EventBus


# -----------------------------------------------------------------------------
# Config Tests
# -----------------------------------------------------------------------------


def test_config_loads_catalyst_section():
    """Config.catalyst is CatalystConfig when loading system.yaml."""
    config_path = Path("config/system.yaml")
    if not config_path.exists():
        pytest.skip("system.yaml not found in config/")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # Verify catalyst section exists in YAML
    assert "catalyst" in raw, "catalyst section missing from system.yaml"

    # Load via SystemConfig
    config = SystemConfig(**raw)

    # Verify catalyst is CatalystConfig instance
    assert isinstance(config.catalyst, CatalystConfig)


def test_config_catalyst_default_disabled():
    """Default CatalystConfig has enabled=False."""
    config = CatalystConfig()
    assert config.enabled is False


def test_config_catalyst_yaml_keys_match_model():
    """All YAML keys are recognized by CatalystConfig (no silently ignored keys)."""
    config_path = Path("config/system.yaml")
    if not config_path.exists():
        pytest.skip("system.yaml not found in config/")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    catalyst_yaml = raw.get("catalyst", {})
    if not catalyst_yaml:
        pytest.skip("No catalyst section in system.yaml")

    # Get all valid field names from CatalystConfig model
    valid_fields = set(CatalystConfig.model_fields.keys())

    # Check top-level keys
    yaml_keys = set(catalyst_yaml.keys())

    # Find any silently ignored keys
    ignored = yaml_keys - valid_fields
    assert not ignored, f"YAML keys not in CatalystConfig model: {ignored}"


# -----------------------------------------------------------------------------
# Lifespan Tests
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_event_bus() -> EventBus:
    """Provide a mock EventBus for testing."""
    from argus.core.event_bus import EventBus

    return EventBus()


@pytest.fixture
def minimal_app_state(
    mock_event_bus: EventBus,
    test_trade_logger,
    test_broker,
    test_health_monitor,
    test_risk_manager,
    test_order_manager,
    test_clock,
    monkeypatch: pytest.MonkeyPatch,
) -> AppState:
    """Minimal AppState for lifespan testing."""
    # Prevent AIConfig auto-detect from picking up ANTHROPIC_API_KEY
    # leaked into the process by load_dotenv() in argus.main
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return AppState(
        event_bus=mock_event_bus,
        trade_logger=test_trade_logger,
        broker=test_broker,
        health_monitor=test_health_monitor,
        risk_manager=test_risk_manager,
        order_manager=test_order_manager,
        clock=test_clock,
        config=SystemConfig(api=ApiConfig()),
        start_time=time.time(),
    )


@pytest.mark.asyncio
async def test_lifespan_catalyst_enabled(
    minimal_app_state: AppState,
    tmp_path: Path,
    jwt_secret: str,
):
    """With catalyst.enabled=True, AppState.catalyst_storage is set after startup."""
    from argus.api.server import create_app

    # Enable catalyst in config
    minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
    minimal_app_state.config.data_dir = str(tmp_path)

    # Mock the intelligence startup components
    mock_storage = MagicMock()
    mock_briefing_gen = MagicMock()
    mock_pipeline = MagicMock()
    mock_pipeline.start = AsyncMock()
    mock_pipeline.stop = AsyncMock()

    mock_components = MagicMock()
    mock_components.storage = mock_storage
    mock_components.briefing_generator = mock_briefing_gen
    mock_components.pipeline = mock_pipeline
    mock_components.sources = ["finnhub", "fmp_news"]

    with patch(
        "argus.intelligence.startup.create_intelligence_components",
        new=AsyncMock(return_value=mock_components),
    ):
        app = create_app(minimal_app_state)

        # Manually trigger lifespan
        async with app.router.lifespan_context(app):
            # After startup, catalyst_storage should be set
            assert minimal_app_state.catalyst_storage is mock_storage
            assert minimal_app_state.briefing_generator is mock_briefing_gen

        # Pipeline start should have been called
        mock_pipeline.start.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_catalyst_disabled(
    minimal_app_state: AppState,
    jwt_secret: str,
):
    """With catalyst.enabled=False, AppState.catalyst_storage remains None."""
    from argus.api.server import create_app

    # Ensure catalyst is disabled (default)
    minimal_app_state.config.catalyst = CatalystConfig(enabled=False)

    app = create_app(minimal_app_state)

    # Manually trigger lifespan
    async with app.router.lifespan_context(app):
        # catalyst_storage should remain None
        assert minimal_app_state.catalyst_storage is None
        assert minimal_app_state.briefing_generator is None


@pytest.mark.asyncio
async def test_lifespan_catalyst_shutdown_cleanup(
    minimal_app_state: AppState,
    tmp_path: Path,
    jwt_secret: str,
):
    """After shutdown, AppState.catalyst_storage is None."""
    from argus.api.server import create_app

    # Enable catalyst in config
    minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
    minimal_app_state.config.data_dir = str(tmp_path)

    # Mock the intelligence startup components
    mock_storage = MagicMock()
    mock_storage.close = AsyncMock()
    mock_briefing_gen = MagicMock()
    mock_pipeline = MagicMock()
    mock_pipeline.start = AsyncMock()
    mock_pipeline.stop = AsyncMock()

    mock_components = MagicMock()
    mock_components.storage = mock_storage
    mock_components.briefing_generator = mock_briefing_gen
    mock_components.pipeline = mock_pipeline
    mock_components.sources = ["finnhub"]

    with (
        patch(
            "argus.intelligence.startup.create_intelligence_components",
            new=AsyncMock(return_value=mock_components),
        ),
        patch(
            "argus.intelligence.startup.shutdown_intelligence",
            new=AsyncMock(),
        ) as mock_shutdown,
    ):
        app = create_app(minimal_app_state)

        # Trigger full lifespan (startup and shutdown)
        async with app.router.lifespan_context(app):
            # During lifespan, should be set
            assert minimal_app_state.catalyst_storage is mock_storage

        # After lifespan exits (shutdown), should be None
        assert minimal_app_state.catalyst_storage is None
        assert minimal_app_state.briefing_generator is None

        # shutdown_intelligence should have been called
        mock_shutdown.assert_called_once_with(mock_components)


@pytest.mark.asyncio
async def test_lifespan_catalyst_error_graceful(
    minimal_app_state: AppState,
    tmp_path: Path,
    jwt_secret: str,
    caplog,
):
    """Factory error is logged and app continues without intelligence."""
    from argus.api.server import create_app

    # Enable catalyst in config
    minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
    minimal_app_state.config.data_dir = str(tmp_path)

    # Mock factory to raise an error
    with patch(
        "argus.intelligence.startup.create_intelligence_components",
        new=AsyncMock(side_effect=RuntimeError("Test error: database locked")),
    ):
        app = create_app(minimal_app_state)

        # Lifespan should complete without error
        async with app.router.lifespan_context(app):
            # catalyst_storage should remain None due to error
            assert minimal_app_state.catalyst_storage is None

        # Error should be logged
        assert "Failed to initialize intelligence pipeline" in caplog.text


@pytest.mark.asyncio
async def test_lifespan_ai_disabled_catalyst_enabled(
    minimal_app_state: AppState,
    tmp_path: Path,
    jwt_secret: str,
):
    """AI client None but catalyst enabled works (classifier uses fallback)."""
    from argus.api.server import create_app

    # Enable catalyst, but AI is not available (ai_client is None)
    minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
    minimal_app_state.config.data_dir = str(tmp_path)
    minimal_app_state.ai_client = None  # Explicitly None

    # Mock components that work without AI client
    mock_storage = MagicMock()
    mock_briefing_gen = MagicMock()
    mock_pipeline = MagicMock()
    mock_pipeline.start = AsyncMock()
    mock_pipeline.stop = AsyncMock()

    mock_components = MagicMock()
    mock_components.storage = mock_storage
    mock_components.briefing_generator = mock_briefing_gen
    mock_components.pipeline = mock_pipeline
    mock_components.sources = ["sec_edgar"]

    captured_ai_client = []

    async def capture_create_components(
        config, event_bus, ai_client, usage_tracker, data_dir
    ):
        captured_ai_client.append(ai_client)
        return mock_components

    with (
        patch(
            "argus.intelligence.startup.create_intelligence_components",
            new=capture_create_components,
        ),
        patch(
            "argus.intelligence.startup.shutdown_intelligence",
            new=AsyncMock(),
        ),
    ):
        app = create_app(minimal_app_state)

        async with app.router.lifespan_context(app):
            # Pipeline should still be initialized
            assert minimal_app_state.catalyst_storage is mock_storage

        # Factory was called with ai_client=None
        assert len(captured_ai_client) == 1
        assert captured_ai_client[0] is None


# -----------------------------------------------------------------------------
# get_symbols Tests (Sprint 23.8 Session 1)
# -----------------------------------------------------------------------------


class TestGetSymbols:
    """Tests for the get_symbols closure in server lifespan."""

    @pytest.mark.asyncio
    async def test_get_symbols_returns_watchlist_when_populated(
        self,
        minimal_app_state: AppState,
        tmp_path: Path,
        jwt_secret: str,
    ):
        """get_symbols returns cached_watchlist symbols when watchlist is populated."""
        from argus.api.server import create_app
        from argus.core.events import WatchlistItem

        # Populate cached_watchlist
        minimal_app_state.cached_watchlist = [
            WatchlistItem(symbol="AAPL", gap_pct=3.5),
            WatchlistItem(symbol="TSLA", gap_pct=5.2),
            WatchlistItem(symbol="NVDA", gap_pct=2.8),
        ]
        minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
        minimal_app_state.config.data_dir = str(tmp_path)

        # We need to capture get_symbols from the lifespan
        captured_get_symbols = []

        mock_pipeline = MagicMock()
        mock_pipeline.start = AsyncMock()
        mock_pipeline.stop = AsyncMock()

        mock_components = MagicMock()
        mock_components.storage = MagicMock()
        mock_components.briefing_generator = MagicMock()
        mock_components.pipeline = mock_pipeline
        mock_components.sources = ["finnhub"]

        original_run_polling_loop = None

        async def capture_polling_loop(pipeline, config, get_symbols, **kwargs):
            captured_get_symbols.append(get_symbols)
            # Don't actually run the loop — just capture and return
            raise asyncio.CancelledError()

        with (
            patch(
                "argus.intelligence.startup.create_intelligence_components",
                new=AsyncMock(return_value=mock_components),
            ),
            patch(
                "argus.intelligence.startup.run_polling_loop",
                side_effect=capture_polling_loop,
            ),
            patch(
                "argus.intelligence.startup.shutdown_intelligence",
                new=AsyncMock(),
            ),
        ):
            app = create_app(minimal_app_state)

            async with app.router.lifespan_context(app):
                # Give the task a moment to start
                await asyncio.sleep(0.05)

                assert len(captured_get_symbols) == 1
                symbols = captured_get_symbols[0]()
                assert symbols == ["AAPL", "TSLA", "NVDA"]

    @pytest.mark.asyncio
    async def test_get_symbols_returns_capped_viable_universe_when_watchlist_empty(
        self,
        minimal_app_state: AppState,
        tmp_path: Path,
        jwt_secret: str,
    ):
        """get_symbols returns capped viable universe when watchlist is empty."""
        from argus.api.server import create_app

        # Empty watchlist, set up universe manager mock
        minimal_app_state.cached_watchlist = []
        mock_um = MagicMock()
        mock_um.viable_count = 50
        mock_um.viable_symbols = {f"SYM{i}" for i in range(50)}
        minimal_app_state.universe_manager = mock_um

        minimal_app_state.config.catalyst = CatalystConfig(
            enabled=True, max_batch_size=10
        )
        minimal_app_state.config.data_dir = str(tmp_path)

        captured_get_symbols = []

        mock_pipeline = MagicMock()
        mock_pipeline.start = AsyncMock()
        mock_pipeline.stop = AsyncMock()

        mock_components = MagicMock()
        mock_components.storage = MagicMock()
        mock_components.briefing_generator = MagicMock()
        mock_components.pipeline = mock_pipeline
        mock_components.sources = ["finnhub"]

        async def capture_polling_loop(pipeline, config, get_symbols, **kwargs):
            captured_get_symbols.append(get_symbols)
            raise asyncio.CancelledError()

        with (
            patch(
                "argus.intelligence.startup.create_intelligence_components",
                new=AsyncMock(return_value=mock_components),
            ),
            patch(
                "argus.intelligence.startup.run_polling_loop",
                side_effect=capture_polling_loop,
            ),
            patch(
                "argus.intelligence.startup.shutdown_intelligence",
                new=AsyncMock(),
            ),
        ):
            app = create_app(minimal_app_state)

            async with app.router.lifespan_context(app):
                await asyncio.sleep(0.05)

                assert len(captured_get_symbols) == 1
                symbols = captured_get_symbols[0]()
                # Should be capped at max_batch_size=10
                assert len(symbols) == 10

    @pytest.mark.asyncio
    async def test_get_symbols_returns_empty_when_both_sources_empty(
        self,
        minimal_app_state: AppState,
        tmp_path: Path,
        jwt_secret: str,
    ):
        """get_symbols returns [] when watchlist and viable universe are both empty."""
        from argus.api.server import create_app

        # Empty watchlist, no universe manager
        minimal_app_state.cached_watchlist = []
        minimal_app_state.universe_manager = None

        minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
        minimal_app_state.config.data_dir = str(tmp_path)

        captured_get_symbols = []

        mock_pipeline = MagicMock()
        mock_pipeline.start = AsyncMock()
        mock_pipeline.stop = AsyncMock()

        mock_components = MagicMock()
        mock_components.storage = MagicMock()
        mock_components.briefing_generator = MagicMock()
        mock_components.pipeline = mock_pipeline
        mock_components.sources = ["finnhub"]

        async def capture_polling_loop(pipeline, config, get_symbols, **kwargs):
            captured_get_symbols.append(get_symbols)
            raise asyncio.CancelledError()

        with (
            patch(
                "argus.intelligence.startup.create_intelligence_components",
                new=AsyncMock(return_value=mock_components),
            ),
            patch(
                "argus.intelligence.startup.run_polling_loop",
                side_effect=capture_polling_loop,
            ),
            patch(
                "argus.intelligence.startup.shutdown_intelligence",
                new=AsyncMock(),
            ),
        ):
            app = create_app(minimal_app_state)

            async with app.router.lifespan_context(app):
                await asyncio.sleep(0.05)

                assert len(captured_get_symbols) == 1
                symbols = captured_get_symbols[0]()
                assert symbols == []


# -----------------------------------------------------------------------------
# done_callback Tests (Sprint 23.8 Session 1)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_done_callback_logs_critical_on_task_crash(
    minimal_app_state: AppState,
    tmp_path: Path,
    jwt_secret: str,
    caplog,
):
    """done_callback logs CRITICAL when polling task crashes with an exception."""
    from argus.api.server import create_app

    minimal_app_state.config.catalyst = CatalystConfig(enabled=True)
    minimal_app_state.config.data_dir = str(tmp_path)

    mock_pipeline = MagicMock()
    mock_pipeline.start = AsyncMock()
    mock_pipeline.stop = AsyncMock()

    mock_components = MagicMock()
    mock_components.storage = MagicMock()
    mock_components.briefing_generator = MagicMock()
    mock_components.pipeline = mock_pipeline
    mock_components.sources = ["finnhub"]

    async def crashing_polling_loop(pipeline, config, get_symbols, **kwargs):
        raise RuntimeError("Simulated polling crash")

    with (
        patch(
            "argus.intelligence.startup.create_intelligence_components",
            new=AsyncMock(return_value=mock_components),
        ),
        patch(
            "argus.intelligence.startup.run_polling_loop",
            side_effect=crashing_polling_loop,
        ),
        patch(
            "argus.intelligence.startup.shutdown_intelligence",
            new=AsyncMock(),
        ),
    ):
        import contextlib
        import logging

        with caplog.at_level(logging.CRITICAL, logger="argus.api.server"):
            app = create_app(minimal_app_state)

            # The shutdown path awaits the polling task, which re-raises
            # the RuntimeError. Suppress it since we're testing the callback.
            with contextlib.suppress(RuntimeError):
                async with app.router.lifespan_context(app):
                    # Give the task time to crash and callback to fire
                    await asyncio.sleep(0.1)

            assert "Intelligence polling task CRASHED" in caplog.text
            assert "Simulated polling crash" in caplog.text


# -----------------------------------------------------------------------------
# Additional Edge Case Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_catalyst_no_config():
    """No crash when config is None (defensive)."""
    from argus.api.server import create_app
    from argus.core.event_bus import EventBus

    # Minimal state with no config
    event_bus = EventBus()

    # Create minimal mock objects for required fields
    mock_broker = MagicMock()
    mock_broker.is_connected = True

    mock_trade_logger = MagicMock()
    mock_trade_logger._db = MagicMock()

    app_state = AppState(
        event_bus=event_bus,
        trade_logger=mock_trade_logger,
        broker=mock_broker,
        health_monitor=MagicMock(),
        risk_manager=MagicMock(),
        order_manager=MagicMock(),
        config=None,  # Explicitly None
        start_time=time.time(),
    )

    app = create_app(app_state)

    # Should not crash
    async with app.router.lifespan_context(app):
        # No intelligence should be initialized
        assert app_state.catalyst_storage is None

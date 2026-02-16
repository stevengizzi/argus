"""Tests for the HealthMonitor module."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import HealthConfig
from argus.core.event_bus import EventBus
from argus.core.events import CircuitBreakerEvent, CircuitBreakerLevel, HeartbeatEvent
from argus.core.health import ComponentStatus, HealthMonitor


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def clock() -> FixedClock:
    """Create a FixedClock at a known time (10:00 AM ET on a Monday)."""
    return FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))  # 10 AM ET


@pytest.fixture
def config() -> HealthConfig:
    """Create default HealthConfig for tests (no webhooks)."""
    return HealthConfig(
        heartbeat_interval_seconds=60,
        heartbeat_url_env="",
        alert_webhook_url_env="",
        daily_check_enabled=True,
        weekly_reconciliation_enabled=True,
    )


@pytest.fixture
def health_monitor(event_bus: EventBus, clock: FixedClock, config: HealthConfig) -> HealthMonitor:
    """Create a HealthMonitor instance for tests."""
    return HealthMonitor(
        event_bus=event_bus,
        clock=clock,
        config=config,
    )


# ---------------------------------------------------------------------------
# Component Registry Tests
# ---------------------------------------------------------------------------


class TestComponentRegistry:
    """Tests for component health tracking."""

    def test_update_component_stores_health(
        self, health_monitor: HealthMonitor, clock: FixedClock
    ) -> None:
        """Updating a component stores its health status."""
        health_monitor.update_component("broker", ComponentStatus.HEALTHY, "Connected")

        status = health_monitor.get_status()
        assert "broker" in status
        assert status["broker"].status == ComponentStatus.HEALTHY
        assert status["broker"].message == "Connected"
        assert status["broker"].last_updated == clock.now()

    def test_overall_status_healthy_when_all_healthy(
        self, health_monitor: HealthMonitor
    ) -> None:
        """Overall status is HEALTHY when all components are HEALTHY."""
        health_monitor.update_component("broker", ComponentStatus.HEALTHY)
        health_monitor.update_component("data_service", ComponentStatus.HEALTHY)
        health_monitor.update_component("strategy", ComponentStatus.HEALTHY)

        assert health_monitor.get_overall_status() == ComponentStatus.HEALTHY

    def test_overall_status_degraded_when_any_degraded(
        self, health_monitor: HealthMonitor
    ) -> None:
        """Overall status is DEGRADED when any component is DEGRADED."""
        health_monitor.update_component("broker", ComponentStatus.HEALTHY)
        health_monitor.update_component("data_service", ComponentStatus.DEGRADED, "Reconnecting")
        health_monitor.update_component("strategy", ComponentStatus.HEALTHY)

        assert health_monitor.get_overall_status() == ComponentStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_overall_status_unhealthy_when_any_unhealthy(
        self, event_bus: EventBus, clock: FixedClock, config: HealthConfig
    ) -> None:
        """Overall status is UNHEALTHY when any component is UNHEALTHY."""
        # Need async context because update_component creates a task on UNHEALTHY
        health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)
        health_monitor.update_component("broker", ComponentStatus.HEALTHY)
        health_monitor.update_component(
            "data_service", ComponentStatus.UNHEALTHY, "Connection lost"
        )
        await asyncio.sleep(0.01)  # Let alert task run
        health_monitor.update_component("strategy", ComponentStatus.HEALTHY)

        assert health_monitor.get_overall_status() == ComponentStatus.UNHEALTHY

    def test_overall_status_starting_when_empty(
        self, health_monitor: HealthMonitor
    ) -> None:
        """Overall status is STARTING when no components registered."""
        assert health_monitor.get_overall_status() == ComponentStatus.STARTING


# ---------------------------------------------------------------------------
# Heartbeat Tests
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """Tests for heartbeat functionality."""

    @pytest.mark.asyncio
    async def test_heartbeat_publishes_event(
        self, event_bus: EventBus, clock: FixedClock, config: HealthConfig
    ) -> None:
        """Heartbeat loop publishes HeartbeatEvent to event bus."""
        config.heartbeat_interval_seconds = 1  # Short interval for test
        health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

        received_events: list[HeartbeatEvent] = []

        async def capture_event(event: HeartbeatEvent) -> None:
            received_events.append(event)

        event_bus.subscribe(HeartbeatEvent, capture_event)

        await health_monitor.start()
        await asyncio.sleep(0.1)  # Let heartbeat run once
        await health_monitor.stop()

        assert len(received_events) >= 1
        assert received_events[0].system_status is not None

    @pytest.mark.asyncio
    async def test_heartbeat_sends_http_post(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """Heartbeat sends HTTP POST to configured URL."""
        # Set env var for the heartbeat URL
        with patch.dict(os.environ, {"TEST_HEARTBEAT_URL": "https://hc.example.com/ping/abc123"}):
            config = HealthConfig(
                heartbeat_interval_seconds=10,  # Minimum allowed
                heartbeat_url_env="TEST_HEARTBEAT_URL",
                alert_webhook_url_env="",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)
            health_monitor.update_component("broker", ComponentStatus.HEALTHY)

            with patch("argus.core.health.aiohttp.ClientSession") as mock_session_class:
                mock_session = MagicMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__.return_value = mock_response
                mock_session.post.return_value = mock_context_manager
                mock_session_class.return_value.__aenter__.return_value = mock_session

                # Call _send_heartbeat directly to avoid waiting for interval
                await health_monitor._send_heartbeat(ComponentStatus.HEALTHY)

                mock_session.post.assert_called()
                call_args = mock_session.post.call_args
                assert call_args[0][0] == "https://hc.example.com/ping/abc123"

    @pytest.mark.asyncio
    async def test_heartbeat_handles_http_failure(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """HTTP error during heartbeat is logged but doesn't crash."""
        with patch.dict(os.environ, {"TEST_HEARTBEAT_URL": "https://hc.example.com/ping/abc123"}):
            config = HealthConfig(
                heartbeat_interval_seconds=10,  # Minimum allowed
                heartbeat_url_env="TEST_HEARTBEAT_URL",
                alert_webhook_url_env="",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

            with patch("argus.core.health.aiohttp.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__.side_effect = Exception("Network error")

                # Should not raise - call directly to test error handling
                await health_monitor._send_heartbeat(ComponentStatus.HEALTHY)

    @pytest.mark.asyncio
    async def test_heartbeat_skips_when_no_url(
        self, event_bus: EventBus, clock: FixedClock, config: HealthConfig
    ) -> None:
        """No HTTP call when heartbeat_url is empty."""
        # config fixture already has empty heartbeat_url_env
        health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

        with patch("aiohttp.ClientSession") as mock_session_class:
            await health_monitor.start()
            await asyncio.sleep(0.1)
            await health_monitor.stop()

            mock_session_class.assert_not_called()


# ---------------------------------------------------------------------------
# Alert Tests
# ---------------------------------------------------------------------------


class TestAlerts:
    """Tests for alert functionality."""

    @pytest.mark.asyncio
    async def test_alert_sends_discord_format(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """Discord webhook URL triggers Discord payload format."""
        with patch.dict(os.environ, {"TEST_ALERT_URL": "https://discord.com/api/webhooks/123/abc"}):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await health_monitor.send_critical_alert("Test Alert", "Test body")

                call_args = mock_session.post.call_args
                payload = call_args[1]["json"]
                assert "content" in payload
                assert "🚨" in payload["content"]
                assert "**Test Alert**" in payload["content"]

    @pytest.mark.asyncio
    async def test_alert_sends_generic_format(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """Non-Discord webhook URL triggers generic payload format."""
        with patch.dict(os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await health_monitor.send_critical_alert("Test Alert", "Test body")

                call_args = mock_session.post.call_args
                payload = call_args[1]["json"]
                assert payload["title"] == "Test Alert"
                assert payload["body"] == "Test body"
                assert payload["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_unhealthy_transition_triggers_alert(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """Transition to UNHEALTHY triggers an alert."""
        with patch.dict(os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                # First set to HEALTHY
                health_monitor.update_component("broker", ComponentStatus.HEALTHY)
                await asyncio.sleep(0.05)  # Let task run

                # Then transition to UNHEALTHY
                health_monitor.update_component(
                    "broker", ComponentStatus.UNHEALTHY, "Lost connection"
                )
                await asyncio.sleep(0.05)  # Let task run

                # Verify alert was sent
                assert mock_session.post.called
                call_args = mock_session.post.call_args
                payload = call_args[1]["json"]
                assert "UNHEALTHY" in payload["title"]

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers_alert(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """CircuitBreakerEvent triggers a critical alert."""
        with patch.dict(os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await health_monitor.start()

                # Publish circuit breaker event
                await event_bus.publish(CircuitBreakerEvent(
                    level=CircuitBreakerLevel.ACCOUNT,
                    reason="Daily loss limit exceeded",
                ))

                await asyncio.sleep(0.1)  # Let handler run
                await health_monitor.stop()

                # Verify alert was sent
                assert mock_session.post.called
                call_args = mock_session.post.call_args
                payload = call_args[1]["json"]
                assert "Circuit Breaker" in payload["title"]


# ---------------------------------------------------------------------------
# Integrity Check Tests
# ---------------------------------------------------------------------------


class TestIntegrityChecks:
    """Tests for integrity check functionality."""

    @pytest.mark.asyncio
    async def test_daily_check_finds_unprotected_position(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """Daily check alerts when position has no stop order."""
        with patch.dict(os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )

            mock_broker = AsyncMock()
            mock_position = MagicMock()
            mock_position.symbol = "AAPL"
            mock_broker.get_positions.return_value = [mock_position]
            mock_broker.get_open_orders.return_value = []  # No stop orders

            health_monitor = HealthMonitor(
                event_bus=event_bus,
                clock=clock,
                config=config,
                broker=mock_broker,
            )

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                await health_monitor._run_daily_integrity_check()

                # Should have sent an alert
                assert mock_session.post.called
                call_args = mock_session.post.call_args
                payload = call_args[1]["json"]
                assert "Integrity Check FAILED" in payload["title"]
                assert "AAPL" in payload["body"]

    @pytest.mark.asyncio
    async def test_daily_check_all_positions_have_stops(
        self, event_bus: EventBus, clock: FixedClock, config: HealthConfig
    ) -> None:
        """Daily check passes when all positions have stops."""
        mock_broker = AsyncMock()
        mock_position = MagicMock()
        mock_position.symbol = "AAPL"
        mock_broker.get_positions.return_value = [mock_position]

        mock_order = MagicMock()
        mock_order.symbol = "AAPL"
        mock_order.order_type = "stop"
        mock_broker.get_open_orders.return_value = [mock_order]

        health_monitor = HealthMonitor(
            event_bus=event_bus,
            clock=clock,
            config=config,
            broker=mock_broker,
        )

        # Should not raise and should not send alert
        await health_monitor._run_daily_integrity_check()

    @pytest.mark.asyncio
    async def test_daily_check_no_positions_is_ok(
        self, event_bus: EventBus, clock: FixedClock, config: HealthConfig
    ) -> None:
        """Daily check passes when no positions exist."""
        mock_broker = AsyncMock()
        mock_broker.get_positions.return_value = []

        health_monitor = HealthMonitor(
            event_bus=event_bus,
            clock=clock,
            config=config,
            broker=mock_broker,
        )

        # Should not raise
        await health_monitor._run_daily_integrity_check()

    @pytest.mark.asyncio
    async def test_daily_check_skipped_without_broker(
        self, health_monitor: HealthMonitor
    ) -> None:
        """Daily check is skipped when no broker is configured."""
        # health_monitor fixture has no broker
        # Should not raise
        await health_monitor._run_daily_integrity_check()


# ---------------------------------------------------------------------------
# Lifecycle Tests
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop_lifecycle(
        self, event_bus: EventBus, clock: FixedClock, config: HealthConfig
    ) -> None:
        """Start creates tasks, stop cancels them."""
        health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

        await health_monitor.start()

        assert health_monitor._running is True
        assert health_monitor._heartbeat_task is not None
        assert health_monitor._integrity_task is not None

        await health_monitor.stop()

        assert health_monitor._running is False

    @pytest.mark.asyncio
    async def test_multiple_unhealthy_only_one_alert_each(
        self, event_bus: EventBus, clock: FixedClock
    ) -> None:
        """Same component going UNHEALTHY twice only sends one alert per transition."""
        with patch.dict(os.environ, {"TEST_ALERT_URL": "https://webhook.example.com/alert"}):
            config = HealthConfig(
                heartbeat_interval_seconds=60,
                heartbeat_url_env="",
                alert_webhook_url_env="TEST_ALERT_URL",
            )
            health_monitor = HealthMonitor(event_bus=event_bus, clock=clock, config=config)

            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session_class.return_value.__aenter__.return_value = mock_session

                # First UNHEALTHY transition
                health_monitor.update_component("broker", ComponentStatus.UNHEALTHY, "Error 1")
                await asyncio.sleep(0.05)

                # Second UNHEALTHY (no transition, already unhealthy)
                health_monitor.update_component("broker", ComponentStatus.UNHEALTHY, "Error 2")
                await asyncio.sleep(0.05)

                # Should only have called post once
                assert mock_session.post.call_count == 1

    @pytest.mark.asyncio
    async def test_component_recovery_clears_status(
        self, health_monitor: HealthMonitor
    ) -> None:
        """Component recovering from UNHEALTHY to HEALTHY updates status."""
        health_monitor.update_component("broker", ComponentStatus.UNHEALTHY, "Error")
        assert health_monitor.get_status()["broker"].status == ComponentStatus.UNHEALTHY

        health_monitor.update_component("broker", ComponentStatus.HEALTHY, "Recovered")
        assert health_monitor.get_status()["broker"].status == ComponentStatus.HEALTHY

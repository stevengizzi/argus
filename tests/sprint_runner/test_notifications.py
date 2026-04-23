"""Tests for the notification system."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from scripts.sprint_runner.config import (
    NotificationChannel,
    NotificationsConfig,
    NotificationTiers,
    QuietHours,
    SecondaryChannel,
)
from scripts.sprint_runner.notifications import (
    BYPASS_QUIET_HOURS,
    PRIORITY_MAP,
    TAG_MAP,
    NotificationData,
    NotificationManager,
)
from scripts.sprint_runner.state import NotificationTier, RunState


@pytest.fixture
def basic_config() -> NotificationsConfig:
    """Basic notification configuration with all tiers enabled."""
    return NotificationsConfig(
        tiers=NotificationTiers(
            HALTED=True,
            SESSION_COMPLETE=True,
            PHASE_TRANSITION=True,
            WARNING=True,
            COMPLETED=True,
        ),
        primary=NotificationChannel(
            type="ntfy",
            endpoint="https://ntfy.sh/test-topic",
        ),
        quiet_hours=QuietHours(enabled=False),
        halted_reminder_minutes=60,
    )


@pytest.fixture
def manager(basic_config: NotificationsConfig) -> NotificationManager:
    """Create a NotificationManager with basic config."""
    return NotificationManager(basic_config)


class TestPriorityAndTagMappings:
    """Tests for priority and tag mapping constants."""

    def test_priority_map_has_all_tiers(self) -> None:
        """All notification tiers have priority mappings."""
        expected_tiers = {"HALTED", "SESSION_COMPLETE", "PHASE_TRANSITION", "WARNING", "COMPLETED"}
        assert set(PRIORITY_MAP.keys()) == expected_tiers

    def test_tag_map_has_all_tiers(self) -> None:
        """All notification tiers have tag mappings."""
        expected_tiers = {"HALTED", "SESSION_COMPLETE", "PHASE_TRANSITION", "WARNING", "COMPLETED"}
        assert set(TAG_MAP.keys()) == expected_tiers

    def test_halted_has_highest_priority(self) -> None:
        """HALTED tier has priority 5 (highest)."""
        assert PRIORITY_MAP["HALTED"] == "5"

    def test_bypass_quiet_hours_contains_critical_tiers(self) -> None:
        """HALTED and COMPLETED bypass quiet hours."""
        assert "HALTED" in BYPASS_QUIET_HOURS
        assert "COMPLETED" in BYPASS_QUIET_HOURS
        assert "SESSION_COMPLETE" not in BYPASS_QUIET_HOURS


class TestNotificationFormatting:
    """Tests for notification message formatting."""

    def test_format_halted(self, manager: NotificationManager) -> None:
        """Format HALTED notification with all data."""
        data = NotificationData(
            sprint="23.5",
            session="S2",
            halt_reason="Test verification mismatch",
            current_phase="CLOSEOUT_PARSE",
            completed_sessions=1,
            total_sessions=4,
            run_log_path="/path/to/run-log",
        )
        title, body = manager.format_halted(data)

        assert "Sprint 23.5 HALTED at S2" in title
        assert "Test verification mismatch" in body
        assert "CLOSEOUT_PARSE" in body
        assert "1/4" in body

    def test_format_session_complete(self, manager: NotificationManager) -> None:
        """Format SESSION_COMPLETE notification with test counts."""
        data = NotificationData(
            sprint="23.5",
            session="S1",
            tests_before=2100,
            tests_after=2115,
            next_session="S2",
            completed_sessions=1,
            total_sessions=4,
        )
        title, body = manager.format_session_complete(data)

        assert "Sprint 23.5 S1: CLEAR" in title
        assert "2100 -> 2115 (+15)" in body
        assert "S2" in body
        assert "1/4" in body

    def test_format_phase_transition(self, manager: NotificationManager) -> None:
        """Format PHASE_TRANSITION notification."""
        data = NotificationData(
            sprint="23.5",
            session="S1",
            phase_name="Implementation started",
            phase_description="Session S1",
        )
        title, body = manager.format_phase_transition(data)

        assert "Sprint 23.5 S1: Implementation started" in title
        assert "Session S1" in body

    def test_format_warning(self, manager: NotificationManager) -> None:
        """Format WARNING notification."""
        data = NotificationData(
            sprint="23.5",
            session="S1",
            warning_type="Compaction likely",
            warning_description="Output size exceeds threshold",
            warning_action="Logged",
        )
        title, body = manager.format_warning(data)

        assert "Sprint 23.5 S1: Compaction likely" in title
        assert "Output size exceeds threshold" in body
        assert "logged, run continues" in body.lower()

    def test_format_completed(self, manager: NotificationManager) -> None:
        """Format COMPLETED notification with summary stats."""
        data = NotificationData(
            sprint="23.5",
            completed_sessions=4,
            total_sessions=4,
            tests_before=2100,
            tests_after=2150,
            fix_count=1,
            cost="12.50",
            duration="1h 30m",
            doc_sync_status="pending",
        )
        title, body = manager.format_completed(data)

        assert "Sprint 23.5 COMPLETED" in title
        assert "4/4" in body
        assert "2100 -> 2150 (+50)" in body
        assert "$12.50" in body
        assert "1h 30m" in body


class TestTierEnabling:
    """Tests for tier enable/disable functionality."""

    def test_disabled_tier_returns_false(self) -> None:
        """Sending to a disabled tier returns False."""
        config = NotificationsConfig(
            tiers=NotificationTiers(
                HALTED=True,
                SESSION_COMPLETE=False,  # Disabled
                PHASE_TRANSITION=False,
                WARNING=False,
                COMPLETED=True,
            ),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
        )
        manager = NotificationManager(config)

        result = manager.send("SESSION_COMPLETE", "Test", "Body")
        assert result is False

    def test_enabled_tier_sends(self) -> None:
        """Sending to an enabled tier attempts delivery."""
        config = NotificationsConfig(
            tiers=NotificationTiers(
                HALTED=True,
                SESSION_COMPLETE=True,
                PHASE_TRANSITION=True,
                WARNING=True,
                COMPLETED=True,
            ),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=False),
        )
        manager = NotificationManager(config)

        with patch.object(manager, "_send_to_primary", return_value=True):
            result = manager.send("SESSION_COMPLETE", "Test", "Body")
            assert result is True


class TestQuietHours:
    """Tests for quiet hours functionality."""

    def test_quiet_hours_suppresses_session_complete(self) -> None:
        """SESSION_COMPLETE is queued during quiet hours."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=True, start_utc="00:00", end_utc="23:59"),
        )
        manager = NotificationManager(config)

        result = manager.send("SESSION_COMPLETE", "Test", "Body")

        assert result is True
        assert len(manager.queued) == 1
        assert manager.queued[0].tier == "SESSION_COMPLETE"

    def test_halted_bypasses_quiet_hours(self) -> None:
        """HALTED sends even during quiet hours."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=True, start_utc="00:00", end_utc="23:59"),
        )
        manager = NotificationManager(config)

        with patch.object(manager, "_send_to_primary", return_value=True):
            result = manager.send("HALTED", "Test", "Body")

        assert result is True
        assert len(manager.queued) == 0

    def test_completed_bypasses_quiet_hours(self) -> None:
        """COMPLETED sends even during quiet hours."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=True, start_utc="00:00", end_utc="23:59"),
        )
        manager = NotificationManager(config)

        with patch.object(manager, "_send_to_primary", return_value=True):
            result = manager.send("COMPLETED", "Test", "Body")

        assert result is True
        assert len(manager.queued) == 0

    def test_flush_queue_sends_all_queued(self) -> None:
        """flush_queue sends all queued notifications."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=True, start_utc="00:00", end_utc="23:59"),
        )
        manager = NotificationManager(config)

        # Queue some notifications
        manager.send("SESSION_COMPLETE", "Test 1", "Body 1")
        manager.send("WARNING", "Test 2", "Body 2")
        assert len(manager.queued) == 2

        # Flush the queue
        with patch.object(manager, "_send_to_primary", return_value=True):
            count = manager.flush_queue()

        assert count == 2
        assert len(manager.queued) == 0


class TestReminderEscalation:
    """Tests for HALTED reminder escalation."""

    def test_check_reminder_returns_false_when_not_halted(
        self, manager: NotificationManager
    ) -> None:
        """check_reminder returns False when no HALTED notification sent."""
        assert manager.last_halted_notification is None
        result = manager.check_reminder()
        assert result is False

    def test_check_reminder_tracks_halted_time(self) -> None:
        """Sending HALTED sets last_halted_notification timestamp."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=False),
            halted_reminder_minutes=60,
        )
        manager = NotificationManager(config)

        with patch.object(manager, "_send_to_primary", return_value=True):
            manager.send("HALTED", "Test", "Body")

        assert manager.last_halted_notification is not None

    def test_check_reminder_sends_after_interval(self) -> None:
        """check_reminder sends reminder after configured interval."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=False),
            halted_reminder_minutes=1,  # 1 minute for testing
        )
        manager = NotificationManager(config)

        # Simulate HALTED sent 2 minutes ago (DEF-150: prior arithmetic
        # `(minute - 2) % 60` moved the timestamp into the future when
        # minute ∈ {0,1}, causing check_reminder to skip the send).
        manager.last_halted_notification = datetime.now(UTC) - timedelta(minutes=2)

        with patch.object(manager, "send", return_value=True) as mock_send:
            result = manager.check_reminder()

        assert result is True
        mock_send.assert_called_once()


class TestNtfyDelivery:
    """Tests for ntfy.sh delivery."""

    def test_send_ntfy_success(self, manager: NotificationManager) -> None:
        """Successful ntfy delivery returns True."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = manager._send_ntfy("Title", "Body", "HALTED")

        assert result is True

    def test_send_ntfy_uses_correct_priority(self, manager: NotificationManager) -> None:
        """ntfy request includes correct priority header."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            manager._send_ntfy("Title", "Body", "HALTED")

        # Check the request headers
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.get_header("Priority") == "5"
        assert "warning" in request.get_header("Tags")

    def test_send_ntfy_handles_error(self, manager: NotificationManager) -> None:
        """ntfy delivery handles URLError gracefully."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            result = manager._send_ntfy("Title", "Body", "HALTED")

        assert result is False

    def test_send_ntfy_missing_endpoint_returns_false(self) -> None:
        """Missing ntfy endpoint returns False."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint=""),
        )
        manager = NotificationManager(config)

        result = manager._send_ntfy("Title", "Body", "HALTED")
        assert result is False


class TestSlackDelivery:
    """Tests for Slack webhook delivery."""

    def test_send_slack_success(self, manager: NotificationManager) -> None:
        """Successful Slack delivery returns True."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = manager._send_slack("Title", "Body", "https://hooks.slack.com/test")

        assert result is True

    def test_send_slack_missing_webhook_returns_false(
        self, manager: NotificationManager
    ) -> None:
        """Missing Slack webhook returns False."""
        result = manager._send_slack("Title", "Body", None)
        assert result is False

    def test_send_slack_handles_error(self, manager: NotificationManager) -> None:
        """Slack delivery handles URLError gracefully."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            result = manager._send_slack("Title", "Body", "https://hooks.slack.com/test")

        assert result is False


class TestSecondaryChannels:
    """Tests for secondary channel delivery."""

    def test_send_to_secondary_slack(self) -> None:
        """Secondary Slack channel receives notifications."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            secondary=[
                SecondaryChannel(
                    type="slack", webhook_url="https://hooks.slack.com/services/test"
                )
            ],
            quiet_hours=QuietHours(enabled=False),
        )
        manager = NotificationManager(config)

        with (
            patch.object(manager, "_send_to_primary", return_value=True),
            patch.object(manager, "_send_slack", return_value=True) as mock_slack,
        ):
            manager.send("HALTED", "Title", "Body")

        mock_slack.assert_called_once_with(
            "Title", "Body", "https://hooks.slack.com/services/test"
        )


class TestNotificationLogging:
    """Tests for notification logging to state."""

    def test_send_logs_to_state(self) -> None:
        """Sending a notification logs it to state.notifications_sent."""
        config = NotificationsConfig(
            tiers=NotificationTiers(),
            primary=NotificationChannel(type="ntfy", endpoint="https://ntfy.sh/test"),
            quiet_hours=QuietHours(enabled=False),
        )
        manager = NotificationManager(config)

        # Create a mock state
        state = MagicMock(spec=RunState)
        state.notifications_sent = []

        with patch.object(manager, "_send_to_primary", return_value=True):
            manager.send("HALTED", "Test Title", "Test Body", state)

        assert len(state.notifications_sent) == 1
        notification = state.notifications_sent[0]
        assert notification.tier == NotificationTier.HALTED
        assert "Test Title" in notification.message

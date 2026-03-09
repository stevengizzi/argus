"""Notification system for the sprint runner.

Implements multi-channel notifications (ntfy.sh primary, Slack/email secondary)
with tier-based routing, quiet hours, and reminder escalation.
"""

from __future__ import annotations

import json
import logging
import smtplib
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from .config import NotificationsConfig
from .state import NotificationSent, NotificationTier

if TYPE_CHECKING:
    from .state import RunState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Priority and Tag Mappings
# ---------------------------------------------------------------------------

PRIORITY_MAP: dict[str, str] = {
    "HALTED": "5",
    "SESSION_COMPLETE": "3",
    "PHASE_TRANSITION": "2",
    "WARNING": "2",
    "COMPLETED": "3",
}

TAG_MAP: dict[str, str] = {
    "HALTED": "warning,rotating_light",
    "SESSION_COMPLETE": "white_check_mark",
    "PHASE_TRANSITION": "arrow_forward",
    "WARNING": "information_source",
    "COMPLETED": "tada",
}

# Tiers that bypass quiet hours
BYPASS_QUIET_HOURS: set[str] = {"HALTED", "COMPLETED"}


# ---------------------------------------------------------------------------
# Notification Data
# ---------------------------------------------------------------------------


@dataclass
class NotificationData:
    """Data for constructing a notification message."""

    sprint: str = ""
    session: str = ""
    halt_reason: str = ""
    current_phase: str = ""
    completed_sessions: int = 0
    total_sessions: int = 0
    tests_before: int = 0
    tests_after: int = 0
    next_session: str = ""
    phase_name: str = ""
    phase_description: str = ""
    warning_type: str = ""
    warning_description: str = ""
    warning_action: str = ""
    fix_count: int = 0
    cost: str = "0.00"
    duration: str = ""
    doc_sync_status: str = ""
    run_log_path: str = ""
    verdict: str = ""


@dataclass
class QueuedNotification:
    """A notification queued during quiet hours."""

    tier: str
    title: str
    body: str
    timestamp: str


# ---------------------------------------------------------------------------
# Notification Manager
# ---------------------------------------------------------------------------


class NotificationManager:
    """Manages notification delivery across multiple channels.

    Handles tier-based routing, quiet hours suppression, and reminder
    escalation for HALTED states.
    """

    def __init__(self, config: NotificationsConfig) -> None:
        """Initialize the notification manager.

        Args:
            config: Notification configuration.
        """
        self.config = config
        self.queued: list[QueuedNotification] = []
        self.last_halted_notification: datetime | None = None

    def send(
        self,
        tier: str,
        title: str,
        body: str,
        state: RunState | None = None,
    ) -> bool:
        """Send a notification to all enabled channels.

        Args:
            tier: Notification tier (HALTED, SESSION_COMPLETE, etc.).
            title: Notification title.
            body: Notification body.
            state: Optional run state for logging notifications.

        Returns:
            True if notification was sent (or queued), False if tier disabled.
        """
        # Check if tier is enabled
        if not self._is_tier_enabled(tier):
            logger.debug(f"Notification tier {tier} is disabled")
            return False

        # Check quiet hours
        if self._is_quiet_hours() and tier not in BYPASS_QUIET_HOURS:
            self._queue_notification(tier, title, body)
            if state:
                self._log_notification(state, tier, f"[QUEUED] {title}: {body}", "queued")
            return True

        # Track HALTED notification time for reminder escalation
        if tier == "HALTED":
            self.last_halted_notification = datetime.now(UTC)

        # Send to primary channel
        delivered = self._send_to_primary(tier, title, body)

        # Send to secondary channels
        for secondary in self.config.secondary:
            if secondary.type == "slack":
                self._send_slack(title, body, secondary.webhook_url)
            elif secondary.type == "email":
                self._send_email(title, body, secondary)

        # Log notification
        if state:
            channel = self.config.primary.type
            self._log_notification(state, tier, f"{title}: {body}", channel)

        return delivered

    def check_reminder(self, state: RunState | None = None) -> bool:
        """Check if a HALTED reminder should be sent.

        Should be called periodically when the runner is in HALTED state.

        Args:
            state: Optional run state for logging.

        Returns:
            True if a reminder was sent.
        """
        if self.last_halted_notification is None:
            return False

        elapsed = (datetime.now(UTC) - self.last_halted_notification).total_seconds()
        reminder_seconds = self.config.halted_reminder_minutes * 60

        if elapsed >= reminder_seconds:
            title = "HALTED Reminder"
            body = (
                "The sprint runner is still HALTED and waiting for human intervention. "
                f"Time since last notification: {int(elapsed // 60)} minutes."
            )
            self.send("HALTED", title, body, state)
            return True

        return False

    def flush_queue(self, state: RunState | None = None) -> int:
        """Send all queued notifications.

        Called when quiet hours end.

        Args:
            state: Optional run state for logging.

        Returns:
            Number of notifications sent.
        """
        count = 0
        for queued in self.queued:
            self._send_to_primary(queued.tier, queued.title, queued.body)
            for secondary in self.config.secondary:
                if secondary.type == "slack":
                    self._send_slack(queued.title, queued.body, secondary.webhook_url)
                elif secondary.type == "email":
                    self._send_email(queued.title, queued.body, secondary)
            if state:
                self._log_notification(
                    state, queued.tier, f"{queued.title}: {queued.body}", "primary"
                )
            count += 1

        self.queued.clear()
        return count

    def format_halted(self, data: NotificationData) -> tuple[str, str]:
        """Format a HALTED notification.

        Args:
            data: Notification data.

        Returns:
            Tuple of (title, body).
        """
        title = f"Sprint {data.sprint} HALTED at {data.session}"
        body = (
            f"Reason: {data.halt_reason}\n"
            f"Phase: {data.current_phase}\n"
            f"Sessions completed: {data.completed_sessions}/{data.total_sessions}\n"
            f"Run log: {data.run_log_path}\n"
            f"Resume: python -m scripts.sprint_runner --resume --config <config>"
        )
        return title, body

    def format_session_complete(self, data: NotificationData) -> tuple[str, str]:
        """Format a SESSION_COMPLETE notification.

        Args:
            data: Notification data.

        Returns:
            Tuple of (title, body).
        """
        new_tests = data.tests_after - data.tests_before
        title = f"Sprint {data.sprint} {data.session}: CLEAR"
        body = (
            f"Tests: {data.tests_before} -> {data.tests_after} (+{new_tests})\n"
            f"Proceeding to: {data.next_session}\n"
            f"Progress: {data.completed_sessions}/{data.total_sessions} sessions"
        )
        return title, body

    def format_phase_transition(self, data: NotificationData) -> tuple[str, str]:
        """Format a PHASE_TRANSITION notification.

        Args:
            data: Notification data.

        Returns:
            Tuple of (title, body).
        """
        title = f"Sprint {data.sprint} {data.session}: {data.phase_name}"
        body = data.phase_description
        return title, body

    def format_warning(self, data: NotificationData) -> tuple[str, str]:
        """Format a WARNING notification.

        Args:
            data: Notification data.

        Returns:
            Tuple of (title, body).
        """
        title = f"Sprint {data.sprint} {data.session}: {data.warning_type}"
        body = (
            f"{data.warning_description}\n"
            f"Action taken: {data.warning_action} (logged, run continues)"
        )
        return title, body

    def format_completed(self, data: NotificationData) -> tuple[str, str]:
        """Format a COMPLETED notification.

        Args:
            data: Notification data.

        Returns:
            Tuple of (title, body).
        """
        new_tests = data.tests_after - data.tests_before
        title = f"Sprint {data.sprint} COMPLETED"
        body = (
            f"Sessions: {data.completed_sessions}/{data.total_sessions}\n"
            f"Tests: {data.tests_before} -> {data.tests_after} (+{new_tests})\n"
            f"Fix sessions inserted: {data.fix_count}\n"
            f"Estimated cost: ${data.cost}\n"
            f"Duration: {data.duration}\n"
            f"Doc sync: {data.doc_sync_status}"
        )
        return title, body

    def _is_tier_enabled(self, tier: str) -> bool:
        """Check if a notification tier is enabled.

        Args:
            tier: The tier to check.

        Returns:
            True if enabled.
        """
        tier_config = self.config.tiers
        return getattr(tier_config, tier, False)

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours.

        Returns:
            True if in quiet hours.
        """
        if not self.config.quiet_hours.enabled:
            return False

        now = datetime.now(UTC)
        current_time = now.strftime("%H:%M")

        start = self.config.quiet_hours.start_utc
        end = self.config.quiet_hours.end_utc

        # Handle overnight quiet hours (e.g., 22:00 to 06:00)
        if start > end:
            return current_time >= start or current_time < end
        return start <= current_time < end

    def _queue_notification(self, tier: str, title: str, body: str) -> None:
        """Queue a notification for later delivery.

        Args:
            tier: Notification tier.
            title: Notification title.
            body: Notification body.
        """
        self.queued.append(
            QueuedNotification(
                tier=tier,
                title=title,
                body=body,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )
        logger.info(f"Queued {tier} notification (quiet hours active)")

    def _send_to_primary(self, tier: str, title: str, body: str) -> bool:
        """Send notification to the primary channel.

        Args:
            tier: Notification tier.
            title: Notification title.
            body: Notification body.

        Returns:
            True if sent successfully.
        """
        if self.config.primary.type == "ntfy":
            return self._send_ntfy(title, body, tier)
        return False

    def _send_ntfy(self, title: str, body: str, tier: str) -> bool:
        """Send notification via ntfy.sh.

        Args:
            title: Notification title.
            body: Notification body.
            tier: Notification tier for priority/tags.

        Returns:
            True if sent successfully.
        """
        endpoint = self.config.primary.endpoint
        if not endpoint:
            logger.warning("ntfy endpoint not configured")
            return False

        headers = {
            "Title": title,
            "Priority": PRIORITY_MAP.get(tier, "3"),
            "Tags": TAG_MAP.get(tier, ""),
        }

        # Add auth token if configured
        if self.config.primary.auth_token:
            headers["Authorization"] = f"Bearer {self.config.primary.auth_token}"

        try:
            request = urllib.request.Request(
                endpoint,
                data=body.encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Sent ntfy notification: {title}")
                    return True
                logger.warning(f"ntfy returned status {response.status}")
                return False
        except urllib.error.URLError as e:
            logger.error(f"Failed to send ntfy notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending ntfy notification: {e}")
            return False

    def _send_slack(self, title: str, body: str, webhook_url: str | None) -> bool:
        """Send notification via Slack webhook.

        Args:
            title: Notification title.
            body: Notification body.
            webhook_url: Slack webhook URL.

        Returns:
            True if sent successfully.
        """
        if not webhook_url:
            return False

        payload = {
            "text": f"*{title}*\n{body}",
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Sent Slack notification: {title}")
                    return True
                logger.warning(f"Slack returned status {response.status}")
                return False
        except urllib.error.URLError as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")
            return False

    def _send_email(self, title: str, body: str, config: object) -> bool:
        """Send notification via email.

        Args:
            title: Notification title.
            body: Notification body.
            config: Secondary channel config with SMTP settings.

        Returns:
            True if sent successfully.
        """
        smtp_host = getattr(config, "smtp_host", None)
        smtp_port = getattr(config, "smtp_port", 587)
        from_addr = getattr(config, "from_addr", None)
        to_addr = getattr(config, "to", None)

        if not all([smtp_host, from_addr, to_addr]):
            return False

        msg = MIMEText(body)
        msg["Subject"] = title
        msg["From"] = from_addr
        msg["To"] = to_addr

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.sendmail(from_addr, [to_addr], msg.as_string())
            logger.info(f"Sent email notification: {title}")
            return True
        except smtplib.SMTPException as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email notification: {e}")
            return False

    def _log_notification(
        self,
        state: RunState,
        tier: str,
        message: str,
        channel: str,
    ) -> None:
        """Log a notification to state.

        Args:
            state: Run state to update.
            tier: Notification tier.
            message: Notification message.
            channel: Delivery channel.
        """
        state.notifications_sent.append(
            NotificationSent(
                timestamp=datetime.now(UTC).isoformat(),
                tier=NotificationTier(tier),
                message=message,
                channel=channel,
            )
        )

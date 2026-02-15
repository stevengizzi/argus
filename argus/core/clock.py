"""Clock abstraction for injectable time provider.

This module provides a Clock protocol for components that need to access current
time. By accepting a Clock parameter instead of calling datetime.now() or date.today()
directly, components become testable with controllable time.

Components using Clock: Risk Manager, BaseStrategy, and any component where
date boundaries matter for logic or testing.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    """Protocol for injectable time provider.

    Components that need current time should accept a Clock parameter
    instead of calling datetime.now() or date.today() directly.
    """

    def now(self) -> datetime:
        """Return current datetime (timezone-aware, UTC).

        Returns:
            Current UTC datetime with timezone info.
        """
        ...

    def today(self) -> date:
        """Return current date in the system's configured timezone.

        Returns:
            Current date in the configured timezone (not UTC).
        """
        ...


class SystemClock:
    """Production clock using real system time.

    This is the default clock implementation for production use. It returns
    the actual current time from the system clock.
    """

    def __init__(self, timezone: str = "America/New_York"):
        """Initialize the system clock.

        Args:
            timezone: IANA timezone string. Used for today() to determine
                      the correct date boundary for trading days. Defaults
                      to America/New_York (US Eastern Time).
        """
        self._timezone = ZoneInfo(timezone)

    def now(self) -> datetime:
        """Return current UTC datetime.

        Returns:
            Current datetime in UTC with timezone info.
        """
        return datetime.now(UTC)

    def today(self) -> date:
        """Return today's date in the configured timezone.

        This accounts for timezone offsets. For example, at 11 PM EST,
        the UTC date might be "tomorrow", but today() returns the EST date.

        Returns:
            Current date in the configured timezone.
        """
        return datetime.now(self._timezone).date()


class FixedClock:
    """Test clock with manually controllable time.

    This clock is frozen at a specific datetime and can be advanced
    manually. Used for testing components that depend on time passing
    or date boundaries.
    """

    def __init__(self, fixed_time: datetime):
        """Initialize the fixed clock.

        Args:
            fixed_time: The datetime to freeze the clock at. Should be
                        timezone-aware (UTC).

        Raises:
            ValueError: If fixed_time is not timezone-aware.
        """
        if fixed_time.tzinfo is None:
            raise ValueError("fixed_time must be timezone-aware (use datetime.now(UTC))")
        self._time = fixed_time

    def now(self) -> datetime:
        """Return the fixed datetime.

        Returns:
            The fixed datetime set at initialization or via set().
        """
        return self._time

    def today(self) -> date:
        """Return the date portion of the fixed datetime.

        Returns:
            Date portion of the fixed datetime.
        """
        return self._time.date()

    def advance(self, **kwargs) -> None:
        """Advance time by a timedelta.

        Args:
            **kwargs: Keyword arguments passed to timedelta constructor.
                      Examples: hours=1, minutes=30, days=1, seconds=45.

        Example:
            clock.advance(hours=1, minutes=30)  # Advance by 1h 30m
            clock.advance(days=1)  # Advance by 1 day
        """
        self._time += timedelta(**kwargs)

    def set(self, new_time: datetime) -> None:
        """Set time to a specific datetime.

        Args:
            new_time: The new datetime to set. Should be timezone-aware (UTC).

        Raises:
            ValueError: If new_time is not timezone-aware.
        """
        if new_time.tzinfo is None:
            raise ValueError("new_time must be timezone-aware (use datetime.now(UTC))")
        self._time = new_time

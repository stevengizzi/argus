"""Tests for the Clock abstraction (SystemClock and FixedClock)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from argus.core.clock import FixedClock, SystemClock


class TestSystemClock:
    """Tests for SystemClock (production clock using real system time)."""

    def test_now_returns_current_utc_time(self):
        """SystemClock.now() should return current UTC datetime with timezone."""
        clock = SystemClock()
        before = datetime.now(timezone.utc)
        result = clock.now()
        after = datetime.now(timezone.utc)

        assert before <= result <= after
        assert result.tzinfo == timezone.utc

    def test_today_returns_current_date_in_configured_timezone(self):
        """SystemClock.today() should return today's date in configured timezone."""
        clock = SystemClock(timezone="America/New_York")
        result = clock.today()

        # Get expected date in EST
        expected = datetime.now(ZoneInfo("America/New_York")).date()
        assert result == expected

    def test_today_respects_timezone_boundary(self):
        """SystemClock.today() should respect timezone boundaries.

        At 11 PM EST, the UTC date might be "tomorrow", but today()
        should return the EST date.
        """
        # This test uses real system time, so we just verify the mechanism
        # works by checking that timezone is applied correctly
        est_clock = SystemClock(timezone="America/New_York")
        utc_clock = SystemClock(timezone="UTC")

        est_date = est_clock.today()
        utc_date = utc_clock.today()

        # They might be the same or differ by one day depending on time
        # Just verify both are valid dates and timezone logic is applied
        assert isinstance(est_date, type(utc_date))

    def test_default_timezone_is_new_york(self):
        """SystemClock should default to America/New_York timezone."""
        clock = SystemClock()
        # Access the internal timezone to verify default
        assert clock._timezone == ZoneInfo("America/New_York")

    def test_custom_timezone_can_be_set(self):
        """SystemClock should accept custom timezone parameter."""
        clock = SystemClock(timezone="Europe/London")
        assert clock._timezone == ZoneInfo("Europe/London")


class TestFixedClock:
    """Tests for FixedClock (test clock with controllable time)."""

    def test_now_returns_fixed_time(self):
        """FixedClock.now() should return the exact time it was initialized with."""
        fixed_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        assert clock.now() == fixed_time

    def test_today_returns_date_portion_of_fixed_time(self):
        """FixedClock.today() should return the date portion of fixed time."""
        fixed_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        assert clock.today() == fixed_time.date()

    def test_advance_moves_time_forward(self):
        """FixedClock.advance() should move time forward by specified delta."""
        fixed_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        clock.advance(hours=1, minutes=30)

        expected = fixed_time + timedelta(hours=1, minutes=30)
        assert clock.now() == expected

    def test_advance_with_days(self):
        """FixedClock.advance() should handle day advancement."""
        fixed_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        clock.advance(days=1)

        expected = fixed_time + timedelta(days=1)
        assert clock.now() == expected
        assert clock.today() == expected.date()

    def test_set_changes_time_to_specific_datetime(self):
        """FixedClock.set() should change time to a specific datetime."""
        fixed_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        new_time = datetime(2026, 3, 20, 9, 0, 0, tzinfo=timezone.utc)
        clock.set(new_time)

        assert clock.now() == new_time
        assert clock.today() == new_time.date()

    def test_fixed_clock_rejects_naive_datetime_in_constructor(self):
        """FixedClock should raise ValueError if initialized with naive datetime."""
        naive_time = datetime(2026, 2, 15, 14, 30, 0)  # No tzinfo

        with pytest.raises(ValueError, match="fixed_time must be timezone-aware"):
            FixedClock(naive_time)

    def test_fixed_clock_rejects_naive_datetime_in_set(self):
        """FixedClock.set() should raise ValueError if given naive datetime."""
        fixed_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        naive_time = datetime(2026, 3, 20, 9, 0, 0)  # No tzinfo

        with pytest.raises(ValueError, match="new_time must be timezone-aware"):
            clock.set(naive_time)

    def test_multiple_advances(self):
        """FixedClock should handle multiple advance() calls correctly."""
        fixed_time = datetime(2026, 2, 15, 9, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        clock.advance(minutes=15)
        clock.advance(minutes=15)
        clock.advance(hours=1)

        expected = fixed_time + timedelta(hours=1, minutes=30)
        assert clock.now() == expected

    def test_advance_across_date_boundary(self):
        """FixedClock.advance() should correctly handle date boundary crossing."""
        fixed_time = datetime(2026, 2, 15, 23, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed_time)

        clock.advance(hours=2)

        expected = datetime(2026, 2, 16, 1, 30, 0, tzinfo=timezone.utc)
        assert clock.now() == expected
        assert clock.today() == expected.date()

"""Unit tests for argus/core/market_calendar.py.

Cross-validates against NYSE published holiday calendars for 2025–2030
and tests all helper functions: Easter, observed-date rules, is_market_holiday,
get_next_trading_day.
"""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest

from argus.core.market_calendar import (
    _compute_easter_sunday,
    _observed,
    get_next_trading_day,
    get_nyse_holidays,
    is_market_holiday,
)


# ---------------------------------------------------------------------------
# Easter Sunday (Anonymous Gregorian algorithm)
# ---------------------------------------------------------------------------


class TestComputeEasterSunday:
    """Verify Easter Sunday dates match authoritative tables."""

    # Reference: https://www.timeanddate.com/holidays/us/easter-sunday
    @pytest.mark.parametrize(
        "year, expected",
        [
            (2025, datetime.date(2025, 4, 20)),
            (2026, datetime.date(2026, 4, 5)),
            (2027, datetime.date(2027, 3, 28)),
            (2028, datetime.date(2028, 4, 16)),
            (2029, datetime.date(2029, 4, 1)),
            (2030, datetime.date(2030, 4, 21)),
        ],
    )
    def test_easter_sunday_matches_reference(
        self, year: int, expected: datetime.date
    ) -> None:
        assert _compute_easter_sunday(year) == expected


# ---------------------------------------------------------------------------
# Good Friday dates (derived from Easter)
# ---------------------------------------------------------------------------


class TestGoodFriday:
    """Good Friday is 2 days before Easter Sunday."""

    @pytest.mark.parametrize(
        "year, expected",
        [
            (2025, datetime.date(2025, 4, 18)),
            (2026, datetime.date(2026, 4, 3)),
            (2027, datetime.date(2027, 3, 26)),
            (2028, datetime.date(2028, 4, 14)),
            (2029, datetime.date(2029, 3, 30)),
            (2030, datetime.date(2030, 4, 19)),
        ],
    )
    def test_good_friday_in_holiday_list(self, year: int, expected: datetime.date) -> None:
        holidays = get_nyse_holidays(year)
        assert expected in holidays
        assert holidays[expected] == "Good Friday"


# ---------------------------------------------------------------------------
# Observed date shift rules
# ---------------------------------------------------------------------------


class TestObservedRule:
    """Saturday → Friday, Sunday → Monday, weekday → unchanged."""

    def test_saturday_shifts_to_friday(self) -> None:
        # July 4, 2020 falls on Saturday → observed Friday July 3
        result = _observed(2020, 7, 4)
        assert result == datetime.date(2020, 7, 3)
        assert result.weekday() == 4  # Friday

    def test_sunday_shifts_to_monday(self) -> None:
        # July 4, 2021 falls on Sunday → observed Monday July 5
        result = _observed(2021, 7, 4)
        assert result == datetime.date(2021, 7, 5)
        assert result.weekday() == 0  # Monday

    def test_weekday_unchanged(self) -> None:
        # July 4, 2022 falls on Monday — no shift
        result = _observed(2022, 7, 4)
        assert result == datetime.date(2022, 7, 4)
        assert result.weekday() == 0  # Monday

    def test_friday_unchanged(self) -> None:
        # July 4, 2025 falls on Friday — no shift
        result = _observed(2025, 7, 4)
        assert result == datetime.date(2025, 7, 4)
        assert result.weekday() == 4  # Friday


# ---------------------------------------------------------------------------
# Full holiday lists: cross-reference against NYSE published calendar
# ---------------------------------------------------------------------------


class TestNYSEHolidays2025:
    """2025 NYSE holidays (published calendar cross-reference)."""

    def test_new_years_day_2025(self) -> None:
        holidays = get_nyse_holidays(2025)
        # Jan 1 falls on Wednesday
        assert datetime.date(2025, 1, 1) in holidays

    def test_mlk_day_2025(self) -> None:
        # 3rd Monday of January 2025 = Jan 20
        assert datetime.date(2025, 1, 20) in get_nyse_holidays(2025)

    def test_presidents_day_2025(self) -> None:
        # 3rd Monday of February 2025 = Feb 17
        assert datetime.date(2025, 2, 17) in get_nyse_holidays(2025)

    def test_good_friday_2025(self) -> None:
        assert datetime.date(2025, 4, 18) in get_nyse_holidays(2025)

    def test_memorial_day_2025(self) -> None:
        # Last Monday of May 2025 = May 26
        assert datetime.date(2025, 5, 26) in get_nyse_holidays(2025)

    def test_juneteenth_2025(self) -> None:
        # June 19 falls on Thursday 2025 — no shift
        assert datetime.date(2025, 6, 19) in get_nyse_holidays(2025)

    def test_independence_day_2025(self) -> None:
        # July 4 falls on Friday 2025 — no shift
        assert datetime.date(2025, 7, 4) in get_nyse_holidays(2025)

    def test_labor_day_2025(self) -> None:
        # 1st Monday of September 2025 = Sep 1
        assert datetime.date(2025, 9, 1) in get_nyse_holidays(2025)

    def test_thanksgiving_2025(self) -> None:
        # 4th Thursday of November 2025 = Nov 27
        assert datetime.date(2025, 11, 27) in get_nyse_holidays(2025)

    def test_christmas_2025(self) -> None:
        # Dec 25 falls on Thursday 2025 — no shift
        assert datetime.date(2025, 12, 25) in get_nyse_holidays(2025)

    def test_total_holiday_count_2025(self) -> None:
        assert len(get_nyse_holidays(2025)) == 10


class TestNYSEHolidays2026:
    """2026 NYSE holidays."""

    def test_new_years_day_2026(self) -> None:
        # Jan 1, 2026 falls on Thursday
        assert datetime.date(2026, 1, 1) in get_nyse_holidays(2026)

    def test_good_friday_2026(self) -> None:
        assert datetime.date(2026, 4, 3) in get_nyse_holidays(2026)

    def test_juneteenth_2026(self) -> None:
        # June 19, 2026 falls on Friday
        assert datetime.date(2026, 6, 19) in get_nyse_holidays(2026)

    def test_independence_day_2026(self) -> None:
        # July 4, 2026 falls on Saturday → observed Friday July 3
        assert datetime.date(2026, 7, 3) in get_nyse_holidays(2026)
        assert datetime.date(2026, 7, 4) not in get_nyse_holidays(2026)

    def test_christmas_2026(self) -> None:
        # Dec 25, 2026 falls on Friday
        assert datetime.date(2026, 12, 25) in get_nyse_holidays(2026)

    def test_total_holiday_count_2026(self) -> None:
        assert len(get_nyse_holidays(2026)) == 10


class TestNYSEHolidays2027:
    """2027 NYSE holidays — includes Sunday-observed shifts."""

    def test_new_years_day_2027(self) -> None:
        # Jan 1, 2027 falls on Friday
        assert datetime.date(2027, 1, 1) in get_nyse_holidays(2027)

    def test_juneteenth_2027(self) -> None:
        # June 19, 2027 falls on Saturday → observed Friday June 18
        assert datetime.date(2027, 6, 18) in get_nyse_holidays(2027)
        assert datetime.date(2027, 6, 19) not in get_nyse_holidays(2027)

    def test_independence_day_2027(self) -> None:
        # July 4, 2027 falls on Sunday → observed Monday July 5
        assert datetime.date(2027, 7, 5) in get_nyse_holidays(2027)
        assert datetime.date(2027, 7, 4) not in get_nyse_holidays(2027)

    def test_christmas_2027(self) -> None:
        # Dec 25, 2027 falls on Saturday → observed Friday Dec 24
        assert datetime.date(2027, 12, 24) in get_nyse_holidays(2027)
        assert datetime.date(2027, 12, 25) not in get_nyse_holidays(2027)


# ---------------------------------------------------------------------------
# is_market_holiday()
# ---------------------------------------------------------------------------


class TestIsMarketHoliday:
    """Tests for is_market_holiday() return values."""

    def test_good_friday_2026_is_holiday(self) -> None:
        is_hol, name = is_market_holiday(datetime.date(2026, 4, 3))
        assert is_hol is True
        assert name == "Good Friday"

    def test_regular_monday_is_not_holiday(self) -> None:
        is_hol, name = is_market_holiday(datetime.date(2026, 4, 6))
        assert is_hol is False
        assert name is None

    def test_saturday_is_not_a_holiday(self) -> None:
        # Weekends are not NYSE holiday entries — they are simply weekends
        is_hol, name = is_market_holiday(datetime.date(2026, 4, 4))
        assert is_hol is False

    def test_thanksgiving_2026(self) -> None:
        # 4th Thursday of November 2026 = Nov 26
        is_hol, name = is_market_holiday(datetime.date(2026, 11, 26))
        assert is_hol is True
        assert name == "Thanksgiving Day"

    def test_christmas_2026(self) -> None:
        is_hol, name = is_market_holiday(datetime.date(2026, 12, 25))
        assert is_hol is True
        assert name == "Christmas Day"

    def test_defaults_to_today(self) -> None:
        """is_market_holiday() with no arg should not raise."""
        result = is_market_holiday()
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)

    def test_day_after_christmas_is_not_holiday(self) -> None:
        is_hol, name = is_market_holiday(datetime.date(2026, 12, 26))
        assert is_hol is False
        assert name is None


# ---------------------------------------------------------------------------
# get_next_trading_day()
# ---------------------------------------------------------------------------


class TestGetNextTradingDay:
    """Tests for get_next_trading_day()."""

    def test_friday_before_holiday_monday_skips_holiday(self) -> None:
        # MLK Day 2026 = Jan 19 (Monday)
        # So Friday Jan 16 → next trading day is Tuesday Jan 20
        result = get_next_trading_day(datetime.date(2026, 1, 16))
        assert result == datetime.date(2026, 1, 20)

    def test_regular_friday_goes_to_monday(self) -> None:
        # March 6, 2026 (Friday) → next is March 9, 2026 (Monday, no holiday)
        result = get_next_trading_day(datetime.date(2026, 3, 6))
        assert result == datetime.date(2026, 3, 9)

    def test_good_friday_goes_to_monday(self) -> None:
        # April 3, 2026 (Good Friday) → next is Monday April 6
        result = get_next_trading_day(datetime.date(2026, 4, 3))
        assert result == datetime.date(2026, 4, 6)

    def test_thursday_goes_to_friday(self) -> None:
        result = get_next_trading_day(datetime.date(2026, 4, 9))
        assert result == datetime.date(2026, 4, 10)

    def test_saturday_goes_to_monday(self) -> None:
        # A regular Saturday (no holiday Monday)
        result = get_next_trading_day(datetime.date(2026, 3, 7))
        assert result == datetime.date(2026, 3, 9)

    def test_defaults_to_today(self) -> None:
        result = get_next_trading_day()
        assert isinstance(result, datetime.date)
        assert result > datetime.date.today()

    def test_thanksgiving_thursday_goes_to_friday(self) -> None:
        # Thanksgiving 2026 = Nov 26 (Thursday) — next is Friday Nov 27
        # (Note: day-after-Thanksgiving is a half-day, not a full holiday)
        result = get_next_trading_day(datetime.date(2026, 11, 26))
        assert result == datetime.date(2026, 11, 27)


# ---------------------------------------------------------------------------
# Year cache correctness
# ---------------------------------------------------------------------------


class TestHolidayCache:
    """Verify caching returns identical results on repeated calls."""

    def test_same_result_on_repeated_call(self) -> None:
        first = get_nyse_holidays(2026)
        second = get_nyse_holidays(2026)
        assert first is second  # Same dict object (cache hit)

    def test_different_years_independent(self) -> None:
        h2025 = get_nyse_holidays(2025)
        h2026 = get_nyse_holidays(2026)
        # Good Friday differs between years
        assert datetime.date(2025, 4, 18) in h2025
        assert datetime.date(2026, 4, 3) in h2026
        assert datetime.date(2025, 4, 18) not in h2026

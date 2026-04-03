"""NYSE market holiday calendar for ARGUS.

Pure algorithmic computation — no external APIs, no dependencies beyond stdlib.
Ported from ui/src/utils/marketTime.ts to ensure Python/frontend parity.

NYSE observed holidays per NYSE Rule 7.2:
- New Year's Day (Jan 1)
- Martin Luther King Jr. Day (3rd Monday of January)
- Presidents' Day (3rd Monday of February)
- Good Friday (Friday before Easter Sunday)
- Memorial Day (last Monday of May)
- Juneteenth (June 19)
- Independence Day (July 4)
- Labor Day (1st Monday of September)
- Thanksgiving Day (4th Thursday of November)
- Christmas Day (Dec 25)

Weekend-observed rule: Saturday → preceding Friday; Sunday → following Monday.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")

# Module-level cache: year → {date: holiday_name}
_holiday_cache: dict[int, dict[datetime.date, str]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_easter_sunday(year: int) -> datetime.date:
    """Compute Easter Sunday for a given year using the Anonymous Gregorian algorithm.

    Matches the TypeScript implementation in ui/src/utils/marketTime.ts.

    Args:
        year: The calendar year.

    Returns:
        Date of Easter Sunday.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime.date:
    """Return the Nth occurrence of a weekday in a given month/year.

    Args:
        year: Calendar year.
        month: Calendar month (1-indexed).
        weekday: 0=Monday, 6=Sunday (Python isoweekday: 1=Mon, 7=Sun).
        n: Which occurrence (1=first, 2=second, etc.).

    Returns:
        The date of the Nth weekday.
    """
    # Find the first occurrence
    first = datetime.date(year, month, 1)
    # first.weekday(): 0=Mon, 6=Sun
    days_ahead = (weekday - first.weekday()) % 7
    first_occurrence = first + datetime.timedelta(days=days_ahead)
    return first_occurrence + datetime.timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> datetime.date:
    """Return the last occurrence of a weekday in a given month/year.

    Args:
        year: Calendar year.
        month: Calendar month (1-indexed).
        weekday: 0=Monday, 6=Sunday (Python isoweekday convention).

    Returns:
        The date of the last occurrence of that weekday.
    """
    # Find last day of month
    if month == 12:
        last_day = datetime.date(year, 12, 31)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    days_back = (last_day.weekday() - weekday) % 7
    return last_day - datetime.timedelta(days=days_back)


def _observed(year: int, month: int, day: int) -> datetime.date:
    """Apply NYSE weekend-observed rule to a fixed-date holiday.

    Saturday → preceding Friday; Sunday → following Monday; otherwise unchanged.

    Args:
        year: Nominal year.
        month: Nominal month.
        day: Nominal day.

    Returns:
        The observed date.
    """
    date = datetime.date(year, month, day)
    dow = date.weekday()  # 0=Mon, 5=Sat, 6=Sun
    if dow == 5:  # Saturday → Friday
        return date - datetime.timedelta(days=1)
    if dow == 6:  # Sunday → Monday
        return date + datetime.timedelta(days=1)
    return date


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_nyse_holidays(year: int) -> dict[datetime.date, str]:
    """Compute NYSE market holidays for a given year.

    Results are cached per year — computed once on first access.

    Args:
        year: Calendar year.

    Returns:
        Dict mapping each holiday date to its name string.
    """
    if year in _holiday_cache:
        return _holiday_cache[year]

    holidays: dict[datetime.date, str] = {}

    # Fixed-date holidays (weekend-observed rule applies)
    holidays[_observed(year, 1, 1)] = "New Year's Day"
    holidays[_observed(year, 6, 19)] = "Juneteenth"
    holidays[_observed(year, 7, 4)] = "Independence Day"
    holidays[_observed(year, 12, 25)] = "Christmas Day"

    # Nth-weekday holidays (always fall on the correct day — no observed shift needed)
    holidays[_nth_weekday(year, 1, 0, 3)] = "Martin Luther King Jr. Day"  # 3rd Monday Jan
    holidays[_nth_weekday(year, 2, 0, 3)] = "Presidents' Day"             # 3rd Monday Feb
    holidays[_last_weekday(year, 5, 0)] = "Memorial Day"                  # Last Monday May
    holidays[_nth_weekday(year, 9, 0, 1)] = "Labor Day"                   # 1st Monday Sep
    holidays[_nth_weekday(year, 11, 3, 4)] = "Thanksgiving Day"           # 4th Thursday Nov

    # Good Friday = 2 days before Easter Sunday
    easter = _compute_easter_sunday(year)
    good_friday = easter - datetime.timedelta(days=2)
    holidays[good_friday] = "Good Friday"

    _holiday_cache[year] = holidays
    return holidays


def is_market_holiday(
    date: datetime.date | None = None,
) -> tuple[bool, str | None]:
    """Check whether a given date is an NYSE market holiday.

    Args:
        date: The date to check. Defaults to today in US Eastern time.

    Returns:
        Tuple of (is_holiday, holiday_name). holiday_name is None when not a holiday.

    Examples:
        >>> is_market_holiday(datetime.date(2026, 4, 3))
        (True, 'Good Friday')
        >>> is_market_holiday(datetime.date(2026, 4, 6))
        (False, None)
    """
    if date is None:
        date = datetime.datetime.now(tz=_ET).date()

    holidays = get_nyse_holidays(date.year)
    holiday_name = holidays.get(date)
    if holiday_name is not None:
        return True, holiday_name
    return False, None


def get_next_trading_day(date: datetime.date | None = None) -> datetime.date:
    """Return the next calendar date that is neither a weekend nor a holiday.

    Args:
        date: Starting date (exclusive). Defaults to today in US Eastern time.

    Returns:
        The next trading day.

    Examples:
        >>> get_next_trading_day(datetime.date(2026, 4, 3))  # Good Friday
        datetime.date(2026, 4, 6)  # Monday
    """
    if date is None:
        date = datetime.datetime.now(tz=_ET).date()

    candidate = date + datetime.timedelta(days=1)
    for _ in range(14):  # Safety limit — never more than 2 weeks of holidays in a row
        if candidate.weekday() < 5:  # Monday–Friday
            is_holiday, _ = is_market_holiday(candidate)
            if not is_holiday:
                return candidate
        candidate += datetime.timedelta(days=1)

    # Fallback: should never reach here under normal circumstances
    return candidate

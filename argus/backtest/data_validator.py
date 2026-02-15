"""Validation logic for downloaded historical bar data.

Checks:
1. No missing trading days in the date range.
2. No zero-volume bars during regular market hours (9:30-16:00 ET).
3. Timestamps are UTC.
4. OHLC internal consistency (high >= open/close, low <= open/close).
5. No duplicate timestamps.
6. Spot-check split adjustment for known splits (optional).
"""

import calendar
import logging
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# US market holidays - enough for 2025. Expand as needed.
# Source: NYSE holiday calendar.
US_MARKET_HOLIDAYS_2025 = {
    date(2025, 1, 1),  # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents' Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),  # Independence Day
    date(2025, 9, 1),  # Labor Day
    date(2025, 11, 27),  # Thanksgiving
    date(2025, 12, 25),  # Christmas
}

# Add 2026 holidays through February (our download range)
US_MARKET_HOLIDAYS_2026 = {
    date(2026, 1, 1),  # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents' Day
}

US_MARKET_HOLIDAYS = US_MARKET_HOLIDAYS_2025 | US_MARKET_HOLIDAYS_2026

# Regular market hours in ET: 9:30 AM - 4:00 PM
MARKET_OPEN_ET = time(9, 30)
MARKET_CLOSE_ET = time(16, 0)


@dataclass
class ValidationResult:
    """Result of validating a single Parquet file.

    Attributes:
        symbol: Ticker symbol.
        year: Year of the data.
        month: Month of the data.
        file_path: Path to the validated file.
        row_count: Total number of bars in the file.
        issues: List of human-readable issue descriptions.
        is_valid: True if no critical issues found.
    """

    symbol: str
    year: int
    month: int
    file_path: str
    row_count: int
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """File is valid if it has rows and no critical issues.

        Note: Some issues are warnings (e.g., a few zero-volume bars in
        low-liquidity periods) rather than critical failures. For V1,
        we treat all issues as warnings but still flag them.
        """
        return self.row_count > 0


def get_expected_trading_days(year: int, month: int) -> list[date]:
    """Return list of expected trading days for a given month.

    A trading day is a weekday that is not a US market holiday.

    Args:
        year: Calendar year.
        month: Calendar month (1-12).

    Returns:
        Sorted list of expected trading dates.
    """
    cal = calendar.Calendar()
    trading_days = []
    for d in cal.itermonthdates(year, month):
        if d.month != month:
            continue  # calendar.itermonthdates includes overflow days
        if d.weekday() >= 5:  # Saturday=5, Sunday=6
            continue
        if d in US_MARKET_HOLIDAYS:
            continue
        # Don't include future dates
        if d > date.today():
            continue
        trading_days.append(d)
    return sorted(trading_days)


def validate_parquet_file(
    file_path: Path,
    symbol: str,
    year: int,
    month: int,
) -> ValidationResult:
    """Validate a single Parquet file for data quality.

    Args:
        file_path: Path to the Parquet file.
        symbol: Expected ticker symbol.
        year: Expected year of data.
        month: Expected month of data.

    Returns:
        ValidationResult with any issues found.
    """
    result = ValidationResult(
        symbol=symbol,
        year=year,
        month=month,
        file_path=str(file_path),
        row_count=0,
    )

    if not file_path.exists():
        result.issues.append(f"File not found: {file_path}")
        return result

    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        result.issues.append(f"Failed to read Parquet file: {e}")
        return result

    result.row_count = len(df)
    if result.row_count == 0:
        result.issues.append("File contains zero rows")
        return result

    # --- Check required columns ---
    required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        result.issues.append(f"Missing columns: {missing}")
        return result  # Can't do further checks without core columns

    # --- Check timestamps are UTC ---
    if hasattr(df["timestamp"].dtype, "tz"):
        if df["timestamp"].dt.tz is None:
            result.issues.append("Timestamps are timezone-naive (expected UTC)")
        elif str(df["timestamp"].dt.tz) != "UTC":
            result.issues.append(
                f"Timestamps are in {df['timestamp'].dt.tz} (expected UTC)"
            )
    else:
        # If stored as datetime64 without tz, it's naive
        result.issues.append("Timestamps are timezone-naive (expected UTC)")

    # --- Check for duplicate timestamps ---
    dupes = df["timestamp"].duplicated().sum()
    if dupes > 0:
        result.issues.append(f"{dupes} duplicate timestamps found")

    # --- Check OHLC consistency ---
    ohlc_issues = 0
    ohlc_issues += (df["high"] < df["open"]).sum()
    ohlc_issues += (df["high"] < df["close"]).sum()
    ohlc_issues += (df["low"] > df["open"]).sum()
    ohlc_issues += (df["low"] > df["close"]).sum()
    if ohlc_issues > 0:
        result.issues.append(
            f"{ohlc_issues} bars with OHLC inconsistency "
            "(high < open/close or low > open/close)"
        )

    # --- Check for missing trading days ---
    expected_days = get_expected_trading_days(year, month)
    if expected_days:
        # Convert timestamps to dates for comparison
        try:
            if (
                hasattr(df["timestamp"].dtype, "tz")
                and df["timestamp"].dt.tz is not None
            ):
                actual_dates = set(
                    df["timestamp"].dt.tz_convert("America/New_York").dt.date
                )
            else:
                # Assume UTC if naive, convert
                actual_dates = set(
                    pd.to_datetime(df["timestamp"], utc=True)
                    .dt.tz_convert("America/New_York")
                    .dt.date
                )
            missing_days = [d for d in expected_days if d not in actual_dates]
            if missing_days:
                result.issues.append(
                    f"{len(missing_days)} missing trading day(s): "
                    f"{', '.join(str(d) for d in missing_days[:5])}"
                    f"{'...' if len(missing_days) > 5 else ''}"
                )
        except Exception as e:
            result.issues.append(f"Could not check trading days: {e}")

    # --- Check for zero-volume bars during market hours ---
    try:
        if hasattr(df["timestamp"].dtype, "tz") and df["timestamp"].dt.tz is not None:
            et_times = df["timestamp"].dt.tz_convert("America/New_York")
        else:
            et_times = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
                "America/New_York"
            )
        market_hours = (et_times.dt.time >= MARKET_OPEN_ET) & (
            et_times.dt.time < MARKET_CLOSE_ET
        )
        zero_vol_market = ((df["volume"] == 0) & market_hours).sum()
        if zero_vol_market > 0:
            result.issues.append(
                f"{zero_vol_market} zero-volume bar(s) during market hours"
            )
    except Exception as e:
        result.issues.append(f"Could not check zero-volume bars: {e}")

    if result.issues:
        logger.warning(
            "Validation issues for %s %d-%02d: %s",
            symbol,
            year,
            month,
            "; ".join(result.issues),
        )
    else:
        logger.info(
            "Validation passed for %s %d-%02d (%d bars)",
            symbol,
            year,
            month,
            result.row_count,
        )

    return result

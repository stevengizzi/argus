# ARGUS — Sprint 6 Implementation Spec

> **Sprint 6 Scope:** Historical Data Acquisition (Phase 2, Backtesting Validation)
> **Date:** February 16, 2026
> **Prerequisite:** Phase 1 complete (362 tests passing, ruff clean). Sprint 5 committed.
> **Estimated tests:** ~18–22 new tests

---

## Context

Read these files before starting:
- `CLAUDE.md` — project rules, code style, architectural constraints
- `docs/09_PHASE2_SPRINT_PLAN.md` — Phase 2 plan with Sprint 6 scope
- `argus/data/replay_data_service.py` — existing ReplayDataService (reads Parquet, publishes CandleEvents)
- `argus/core/config.py` — existing Pydantic config models
- `config/` — existing YAML config directory

Sprint 6 is the first sprint of Phase 2 (Backtesting Validation). It builds the tooling to download and store historical 1-minute bar data from Alpaca for use in backtesting. By the end of this sprint, you have a `data/historical/1m/` directory full of validated Parquet files covering 6–12 months of data for ~20–30 liquid US stocks, with a manifest tracking everything and a validation report confirming data quality.

This sprint has **no interaction with the live trading system**. It's a standalone data pipeline that produces Parquet files consumed by Sprint 7 (Replay Harness) and Sprint 8 (VectorBT).

---

## Micro-Decisions (All Resolved)

| ID | Decision | Choice |
|----|----------|--------|
| MD-6-1 | Parquet file granularity | **Per-symbol-per-month.** File naming: `data/historical/1m/{SYMBOL}/{SYMBOL}_2025-03.parquet`. Small files (~300–500 KB each), trivial resume, aligns with walk-forward monthly boundaries. |
| MD-6-2 | Rate limit handling | **200 API calls/min on free tier.** One call per symbol-month (~8,190 bars fits in 10,000 limit). Entire download (~360 calls for 30 symbols × 12 months) completes in ~2–3 minutes. Throttle to 150/min for safety. Retry on 429. |
| MD-6-3 | Split-adjusted prices | **Always use `adjustment=Adjustment.SPLIT`.** Day trading doesn't need dividend adjustment. Record adjustment type in manifest. Spot-check a known split during validation. |
| MD-6-4 | Time zone storage | **Store as UTC** (matching what Alpaca returns and what ReplayDataService expects). Convert to ET at read time in downstream consumers (Sprint 7+). |

---

## Adaptation Notes for Claude Code

The code in this spec is a **detailed guide**, not copy-paste-ready. Claude Code must:

1. **Check actual imports and class names** in the repo. Verify exact locations of Pydantic models, config loading patterns, etc.
2. **Check alpaca-py API** for `StockHistoricalDataClient`, `StockBarsRequest`, `Adjustment`, `TimeFrame` — verify import paths match the installed version (>= 0.30).
3. **Match existing code patterns** for logging, error handling, type hints, and docstrings (Google style).
4. **Run `ruff check`** after implementation and fix any linting issues.
5. **Run the full test suite** (`pytest`) to ensure no regressions against the existing 362 tests.
6. **Do NOT modify any existing production code** unless explicitly stated. This sprint adds new files only.

---

## Step 1: Pydantic Config Model for Backtest Data

### File: `argus/backtest/__init__.py`

Create empty `__init__.py` if it doesn't already exist.

### File: `argus/backtest/config.py`

New config model for the data fetcher. Follows DEC-032 (Pydantic BaseModel, loaded from YAML).

```python
"""Configuration models for backtesting data acquisition."""

from pathlib import Path

from pydantic import BaseModel, Field


class DataFetcherConfig(BaseModel):
    """Configuration for the historical data fetcher.

    Controls which symbols to download, the date range, storage location,
    and rate limiting parameters.
    """

    # Storage
    data_dir: Path = Path("data/historical/1m")
    manifest_path: Path = Path("data/historical/manifest.json")

    # Rate limiting
    max_requests_per_minute: int = Field(default=150, ge=1, le=200)
    retry_max_attempts: int = Field(default=3, ge=1)
    retry_base_delay_seconds: float = Field(default=2.0, gt=0)

    # Data parameters
    adjustment: str = Field(default="split", pattern=r"^(raw|split|all)$")
    feed: str = Field(default="iex", pattern=r"^(iex|sip)$")
```

### File: `config/backtest_universe.yaml`

The curated list of symbols for historical download. Separate from `config/scanner.yaml` (which is for live scanning).

```yaml
# Backtest Universe — symbols for historical data download
# These are high-liquidity US stocks that frequently appear in ORB scans.
# Expand as needed. SPY is included for market regime context.

symbols:
  # Market reference
  - SPY

  # Large-cap tech / momentum
  - AAPL
  - MSFT
  - NVDA
  - TSLA
  - META
  - AMZN
  - GOOG
  - AMD
  - NFLX

  # High-ADV momentum / day trading favorites
  - PLTR
  - SOFI
  - COIN
  - MARA
  - RIOT
  - SQ
  - SNAP
  - UBER
  - SHOP
  - ROKU

  # Additional liquid large-caps
  - BA
  - DIS
  - JPM
  - GS
  - XOM
  - INTC
  - MU
  - SMCI
  - ARM
```

**Note:** This is a starting point — 29 symbols. The user may adjust this list before running the fetcher. The DataFetcher also accepts `--symbols` on the CLI to override.

### Tests for Step 1: `tests/backtest/test_config.py`

```python
class TestDataFetcherConfig:
    """Tests for DataFetcherConfig Pydantic model."""

    def test_defaults_are_valid(self) -> None:
        """DataFetcherConfig can be created with all defaults."""
        config = DataFetcherConfig()
        assert config.data_dir == Path("data/historical/1m")
        assert config.max_requests_per_minute == 150
        assert config.adjustment == "split"
        assert config.feed == "iex"

    def test_max_requests_per_minute_capped(self) -> None:
        """Rate limit cannot exceed 200 (Alpaca free tier limit)."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(max_requests_per_minute=201)

    def test_invalid_adjustment_rejected(self) -> None:
        """Only raw, split, all are valid adjustment values."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(adjustment="invalid")

    def test_invalid_feed_rejected(self) -> None:
        """Only iex, sip are valid feed values."""
        with pytest.raises(ValidationError):
            DataFetcherConfig(feed="invalid")
```

```python
class TestBacktestUniverse:
    """Tests for the backtest universe config file."""

    def test_universe_file_exists(self) -> None:
        """backtest_universe.yaml exists in config/."""
        assert Path("config/backtest_universe.yaml").exists()

    def test_universe_loads_and_has_symbols(self) -> None:
        """Universe file loads and contains a non-empty list of symbols."""
        import yaml
        with open("config/backtest_universe.yaml") as f:
            data = yaml.safe_load(f)
        assert "symbols" in data
        assert len(data["symbols"]) >= 20
        assert "SPY" in data["symbols"]

    def test_universe_symbols_are_uppercase_strings(self) -> None:
        """All symbols are uppercase strings with no whitespace."""
        import yaml
        with open("config/backtest_universe.yaml") as f:
            data = yaml.safe_load(f)
        for sym in data["symbols"]:
            assert isinstance(sym, str)
            assert sym == sym.strip().upper()
```

---

## Step 2: Manifest Model

The manifest tracks what has been downloaded, enabling resume capability and data inventory.

### File: `argus/backtest/manifest.py`

```python
"""Manifest for tracking downloaded historical data.

The manifest is a JSON file that records which symbol-months have been
downloaded, their row counts, date ranges, and any data quality issues.
This enables resume-on-interrupt and powers the DATA_INVENTORY report.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SymbolMonthEntry:
    """Record of a single downloaded symbol-month Parquet file.

    Attributes:
        symbol: Ticker symbol (e.g., "AAPL").
        year: Year of the data (e.g., 2025).
        month: Month of the data (1–12).
        row_count: Number of bars in the Parquet file.
        file_path: Relative path to the Parquet file from repo root.
        downloaded_at: ISO 8601 timestamp of when the download completed.
        source: Data source identifier (e.g., "alpaca_free").
        adjustment: Price adjustment type used ("split", "raw", "all").
        feed: Data feed used ("iex" or "sip").
        data_quality_issues: List of any issues found during validation.
    """
    symbol: str
    year: int
    month: int
    row_count: int
    file_path: str
    downloaded_at: str
    source: str = "alpaca_free"
    adjustment: str = "split"
    feed: str = "iex"
    data_quality_issues: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    """Top-level manifest tracking all downloaded historical data.

    Attributes:
        entries: Dict keyed by "{SYMBOL}_{YYYY}-{MM}" → SymbolMonthEntry.
        created_at: When the manifest was first created.
        last_updated: When the manifest was last modified.
        schema_version: Manifest format version for future compatibility.
    """
    entries: dict[str, SymbolMonthEntry] = field(default_factory=dict)
    created_at: str = ""
    last_updated: str = ""
    schema_version: int = 1

    def entry_key(self, symbol: str, year: int, month: int) -> str:
        """Generate the dict key for a symbol-month entry."""
        return f"{symbol}_{year}-{month:02d}"

    def has_entry(self, symbol: str, year: int, month: int) -> bool:
        """Check if a symbol-month has already been downloaded."""
        return self.entry_key(symbol, year, month) in self.entries

    def add_entry(self, entry: SymbolMonthEntry) -> None:
        """Add or replace a symbol-month entry."""
        key = self.entry_key(entry.symbol, entry.year, entry.month)
        self.entries[key] = entry
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def get_symbols(self) -> list[str]:
        """Return sorted list of unique symbols in the manifest."""
        return sorted({e.symbol for e in self.entries.values()})

    def get_date_range(self, symbol: str) -> tuple[str, str] | None:
        """Return (earliest_month, latest_month) for a symbol, or None."""
        months = [
            (e.year, e.month)
            for e in self.entries.values()
            if e.symbol == symbol
        ]
        if not months:
            return None
        months.sort()
        earliest = f"{months[0][0]}-{months[0][1]:02d}"
        latest = f"{months[-1][0]}-{months[-1][1]:02d}"
        return (earliest, latest)

    def total_rows(self) -> int:
        """Return total bar count across all entries."""
        return sum(e.row_count for e in self.entries.values())

    def total_files(self) -> int:
        """Return number of Parquet files tracked."""
        return len(self.entries)

    def entries_with_issues(self) -> list[SymbolMonthEntry]:
        """Return entries that have data quality issues."""
        return [e for e in self.entries.values() if e.data_quality_issues]


def load_manifest(path: Path) -> Manifest:
    """Load manifest from JSON file. Returns empty Manifest if file doesn't exist.

    Args:
        path: Path to manifest.json.

    Returns:
        Manifest instance populated from file, or empty Manifest.
    """
    if not path.exists():
        logger.info("No existing manifest at %s — starting fresh", path)
        now = datetime.now(timezone.utc).isoformat()
        return Manifest(created_at=now, last_updated=now)

    with open(path) as f:
        data = json.load(f)

    manifest = Manifest(
        created_at=data.get("created_at", ""),
        last_updated=data.get("last_updated", ""),
        schema_version=data.get("schema_version", 1),
    )
    for key, entry_data in data.get("entries", {}).items():
        manifest.entries[key] = SymbolMonthEntry(**entry_data)

    return manifest


def save_manifest(manifest: Manifest, path: Path) -> None:
    """Save manifest to JSON file. Creates parent directories if needed.

    Args:
        manifest: Manifest instance to save.
        path: Path to write manifest.json.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": manifest.schema_version,
        "created_at": manifest.created_at,
        "last_updated": manifest.last_updated,
        "entries": {k: asdict(v) for k, v in manifest.entries.items()},
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Manifest saved to %s (%d entries)", path, len(manifest.entries))
```

### Tests for Step 2: `tests/backtest/test_manifest.py`

```python
class TestSymbolMonthEntry:
    """Tests for SymbolMonthEntry dataclass."""

    def test_creation(self) -> None:
        """SymbolMonthEntry can be created with required fields."""
        entry = SymbolMonthEntry(
            symbol="AAPL",
            year=2025,
            month=6,
            row_count=8190,
            file_path="data/historical/1m/AAPL/AAPL_2025-06.parquet",
            downloaded_at="2026-02-16T10:00:00Z",
        )
        assert entry.symbol == "AAPL"
        assert entry.source == "alpaca_free"
        assert entry.data_quality_issues == []


class TestManifest:
    """Tests for Manifest operations."""

    def test_empty_manifest(self) -> None:
        """Fresh manifest has no entries."""
        m = Manifest(created_at="now", last_updated="now")
        assert m.total_files() == 0
        assert m.total_rows() == 0
        assert m.get_symbols() == []

    def test_add_and_check_entry(self) -> None:
        """Adding an entry makes it findable via has_entry."""
        m = Manifest(created_at="now", last_updated="now")
        entry = SymbolMonthEntry(
            symbol="TSLA", year=2025, month=3, row_count=8000,
            file_path="data/historical/1m/TSLA/TSLA_2025-03.parquet",
            downloaded_at="2026-02-16T10:00:00Z",
        )
        assert not m.has_entry("TSLA", 2025, 3)
        m.add_entry(entry)
        assert m.has_entry("TSLA", 2025, 3)
        assert m.total_files() == 1
        assert m.total_rows() == 8000

    def test_get_date_range(self) -> None:
        """get_date_range returns correct earliest and latest months."""
        m = Manifest(created_at="now", last_updated="now")
        for month in [3, 6, 9, 12]:
            m.add_entry(SymbolMonthEntry(
                symbol="AAPL", year=2025, month=month, row_count=8000,
                file_path=f"data/historical/1m/AAPL/AAPL_2025-{month:02d}.parquet",
                downloaded_at="2026-02-16T10:00:00Z",
            ))
        assert m.get_date_range("AAPL") == ("2025-03", "2025-12")
        assert m.get_date_range("MSFT") is None

    def test_entries_with_issues(self) -> None:
        """entries_with_issues filters correctly."""
        m = Manifest(created_at="now", last_updated="now")
        m.add_entry(SymbolMonthEntry(
            symbol="AAPL", year=2025, month=3, row_count=8000,
            file_path="...", downloaded_at="...",
        ))
        m.add_entry(SymbolMonthEntry(
            symbol="TSLA", year=2025, month=3, row_count=7500,
            file_path="...", downloaded_at="...",
            data_quality_issues=["3 zero-volume bars during market hours"],
        ))
        issues = m.entries_with_issues()
        assert len(issues) == 1
        assert issues[0].symbol == "TSLA"

    def test_entry_key_format(self) -> None:
        """Entry keys follow {SYMBOL}_{YYYY}-{MM} format."""
        m = Manifest(created_at="now", last_updated="now")
        assert m.entry_key("AAPL", 2025, 3) == "AAPL_2025-03"
        assert m.entry_key("AAPL", 2025, 12) == "AAPL_2025-12"


class TestManifestPersistence:
    """Tests for manifest save/load."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Manifest survives a save → load roundtrip."""
        path = tmp_path / "manifest.json"
        m = Manifest(created_at="2026-02-16T00:00:00Z", last_updated="2026-02-16T00:00:00Z")
        m.add_entry(SymbolMonthEntry(
            symbol="AAPL", year=2025, month=6, row_count=8190,
            file_path="data/historical/1m/AAPL/AAPL_2025-06.parquet",
            downloaded_at="2026-02-16T10:00:00Z",
            data_quality_issues=["1 zero-volume bar at 12:34"],
        ))
        save_manifest(m, path)

        loaded = load_manifest(path)
        assert loaded.total_files() == 1
        assert loaded.has_entry("AAPL", 2025, 6)
        entry = loaded.entries["AAPL_2025-06"]
        assert entry.row_count == 8190
        assert entry.data_quality_issues == ["1 zero-volume bar at 12:34"]

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        """Loading from a nonexistent path returns an empty manifest."""
        m = load_manifest(tmp_path / "nope.json")
        assert m.total_files() == 0
        assert m.created_at != ""  # Should be set to now

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Saving creates parent directories if they don't exist."""
        path = tmp_path / "deep" / "nested" / "manifest.json"
        m = Manifest(created_at="now", last_updated="now")
        save_manifest(m, path)
        assert path.exists()
```

---

## Step 3: Data Validator

Validates downloaded Parquet files for data quality issues.

### File: `argus/backtest/data_validator.py`

```python
"""Validation logic for downloaded historical bar data.

Checks:
1. No missing trading days in the date range.
2. No zero-volume bars during regular market hours (9:30–16:00 ET).
3. Timestamps are UTC.
4. OHLC internal consistency (high >= open/close, low <= open/close).
5. No duplicate timestamps.
6. Spot-check split adjustment for known splits (optional).
"""

import logging
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# US market holidays — enough for 2025. Expand as needed.
# Source: NYSE holiday calendar.
US_MARKET_HOLIDAYS_2025 = {
    date(2025, 1, 1),    # New Year's Day
    date(2025, 1, 20),   # MLK Day
    date(2025, 2, 17),   # Presidents' Day
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 26),   # Memorial Day
    date(2025, 6, 19),   # Juneteenth
    date(2025, 7, 4),    # Independence Day
    date(2025, 9, 1),    # Labor Day
    date(2025, 11, 27),  # Thanksgiving
    date(2025, 12, 25),  # Christmas
}

# Add 2026 holidays through February (our download range)
US_MARKET_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # MLK Day
    date(2026, 2, 16),   # Presidents' Day
}

US_MARKET_HOLIDAYS = US_MARKET_HOLIDAYS_2025 | US_MARKET_HOLIDAYS_2026

# Regular market hours in ET: 9:30 AM – 4:00 PM
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
        month: Calendar month (1–12).

    Returns:
        Sorted list of expected trading dates.
    """
    import calendar
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
        result.issues.append(f"{ohlc_issues} bars with OHLC inconsistency (high < open/close or low > open/close)")

    # --- Check for missing trading days ---
    expected_days = get_expected_trading_days(year, month)
    if expected_days:
        # Convert timestamps to dates for comparison
        try:
            if hasattr(df["timestamp"].dtype, "tz") and df["timestamp"].dt.tz is not None:
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
            symbol, year, month, "; ".join(result.issues),
        )
    else:
        logger.info(
            "Validation passed for %s %d-%02d (%d bars)",
            symbol, year, month, result.row_count,
        )

    return result
```

### Tests for Step 3: `tests/backtest/test_data_validator.py`

```python
class TestGetExpectedTradingDays:
    """Tests for trading day calendar logic."""

    def test_january_2025(self) -> None:
        """January 2025 has correct trading days (excludes New Year's + MLK)."""
        days = get_expected_trading_days(2025, 1)
        assert date(2025, 1, 1) not in days   # New Year's
        assert date(2025, 1, 20) not in days   # MLK Day
        assert date(2025, 1, 2) in days        # First trading day
        assert date(2025, 1, 4) not in days    # Saturday
        assert date(2025, 1, 5) not in days    # Sunday

    def test_no_future_dates(self) -> None:
        """Expected trading days don't include dates after today."""
        import datetime
        days = get_expected_trading_days(2027, 1)
        for d in days:
            assert d <= datetime.date.today()


class TestValidateParquetFile:
    """Tests for Parquet file validation."""

    def _make_valid_parquet(self, tmp_path: Path, symbol: str, year: int, month: int) -> Path:
        """Helper to create a valid Parquet file for testing."""
        import numpy as np
        # Generate bars for every trading day, every minute 9:30-16:00 ET
        days = get_expected_trading_days(year, month)
        rows = []
        for d in days:
            for hour in range(14, 21):  # UTC hours covering 9:30-16:00 ET (EST)
                for minute in range(60):
                    # Rough mapping: 14:30 UTC = 9:30 ET (EST)
                    if hour == 14 and minute < 30:
                        continue
                    if hour >= 21:
                        continue
                    ts = pd.Timestamp(
                        year=d.year, month=d.month, day=d.day,
                        hour=hour, minute=minute, tz="UTC"
                    )
                    price = 150.0 + np.random.uniform(-1, 1)
                    rows.append({
                        "timestamp": ts,
                        "open": price,
                        "high": price + 0.5,
                        "low": price - 0.5,
                        "close": price + 0.1,
                        "volume": int(np.random.uniform(1000, 50000)),
                    })
        df = pd.DataFrame(rows)
        file_dir = tmp_path / symbol
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / f"{symbol}_{year}-{month:02d}.parquet"
        df.to_parquet(file_path, index=False)
        return file_path

    def test_valid_file_passes(self, tmp_path: Path) -> None:
        """A well-formed Parquet file passes validation."""
        # Use a past month to avoid future-date filtering
        path = self._make_valid_parquet(tmp_path, "AAPL", 2025, 6)
        result = validate_parquet_file(path, "AAPL", 2025, 6)
        assert result.is_valid
        assert result.row_count > 0

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file is flagged."""
        result = validate_parquet_file(
            tmp_path / "nope.parquet", "AAPL", 2025, 6
        )
        assert not result.is_valid
        assert any("not found" in i for i in result.issues)

    def test_ohlc_inconsistency_detected(self, tmp_path: Path) -> None:
        """Bars where high < open are flagged."""
        df = pd.DataFrame([{
            "timestamp": pd.Timestamp("2025-06-02 14:30:00", tz="UTC"),
            "open": 150.0,
            "high": 149.0,  # BAD: high < open
            "low": 148.0,
            "close": 149.5,
            "volume": 1000,
        }])
        path = tmp_path / "BAD" / "BAD_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "BAD", 2025, 6)
        assert any("OHLC inconsistency" in i for i in result.issues)

    def test_zero_volume_market_hours_detected(self, tmp_path: Path) -> None:
        """Zero-volume bars during market hours are flagged."""
        df = pd.DataFrame([{
            "timestamp": pd.Timestamp("2025-06-02 15:00:00", tz="UTC"),  # 10 AM ET
            "open": 150.0,
            "high": 151.0,
            "low": 149.0,
            "close": 150.5,
            "volume": 0,  # BAD: zero volume during market hours
        }])
        path = tmp_path / "ZV" / "ZV_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "ZV", 2025, 6)
        assert any("zero-volume" in i.lower() for i in result.issues)

    def test_duplicate_timestamps_detected(self, tmp_path: Path) -> None:
        """Duplicate timestamps are flagged."""
        ts = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        df = pd.DataFrame([
            {"timestamp": ts, "open": 150.0, "high": 151.0, "low": 149.0, "close": 150.5, "volume": 1000},
            {"timestamp": ts, "open": 150.1, "high": 151.1, "low": 149.1, "close": 150.6, "volume": 2000},
        ])
        path = tmp_path / "DUP" / "DUP_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "DUP", 2025, 6)
        assert any("duplicate" in i.lower() for i in result.issues)
```

---

## Step 4: DataFetcher (Core Logic)

### File: `argus/backtest/data_fetcher.py`

```python
"""Historical data fetcher for Alpaca 1-minute bars.

Downloads historical bar data from Alpaca's StockHistoricalDataClient,
saves as Parquet files (one per symbol per month), tracks progress in
a manifest, and validates data quality after download.

Usage:
    python -m argus.backtest.data_fetcher \\
        --symbols TSLA,NVDA,AAPL \\
        --start 2025-03-01 \\
        --end 2026-02-01

Or use the backtest_universe.yaml for the full symbol list:
    python -m argus.backtest.data_fetcher \\
        --start 2025-03-01 \\
        --end 2026-02-01
"""

import asyncio
import logging
import time
from datetime import datetime, date, timezone
from pathlib import Path

import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import Adjustment, DataFeed

from argus.backtest.config import DataFetcherConfig
from argus.backtest.data_validator import validate_parquet_file
from argus.backtest.manifest import (
    Manifest,
    SymbolMonthEntry,
    load_manifest,
    save_manifest,
)

logger = logging.getLogger(__name__)


def _generate_month_ranges(
    start_date: date, end_date: date
) -> list[tuple[int, int, date, date]]:
    """Generate (year, month, first_day, last_day) tuples for the date range.

    The range is inclusive of start_date's month and exclusive of end_date's month
    if end_date is the 1st of a month, otherwise inclusive.

    Args:
        start_date: Beginning of desired range.
        end_date: End of desired range.

    Returns:
        List of (year, month, month_start, month_end) tuples.
    """
    import calendar

    ranges = []
    current = date(start_date.year, start_date.month, 1)
    while current < end_date:
        year, month = current.year, current.month
        last_day = calendar.monthrange(year, month)[1]
        month_end = date(year, month, last_day)
        # Don't go past end_date
        if month_end > end_date:
            month_end = end_date
        ranges.append((year, month, current, month_end))
        # Advance to next month
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)
    return ranges


def _bars_to_dataframe(bars) -> pd.DataFrame:
    """Convert Alpaca bar response to a standardized DataFrame.

    Normalizes the Alpaca SDK's bar objects into our standard schema:
    timestamp (UTC), open, high, low, close, volume.

    Args:
        bars: Response from StockHistoricalDataClient.get_stock_bars().
              This is a BarSet (dict of symbol → list of Bar objects).

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume.
        Empty DataFrame if no bars.
    """
    rows = []
    # bars is a BarSet — iterate through the dict values
    for symbol, bar_list in bars.items():
        for bar in bar_list:
            rows.append({
                "timestamp": bar.timestamp,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
            })
    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows)

    # Ensure timestamps are UTC-aware
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    elif str(df["timestamp"].dt.tz) != "UTC":
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    return df.sort_values("timestamp").reset_index(drop=True)


class DataFetcher:
    """Downloads and stores historical 1-minute bar data from Alpaca.

    Uses Alpaca's StockHistoricalDataClient to fetch bars, saves them
    as Parquet files organized by symbol and month, tracks progress in
    a manifest for resume capability, and validates data quality.

    Args:
        config: DataFetcherConfig with storage and rate limit settings.
        api_key: Alpaca API key (from environment).
        api_secret: Alpaca API secret (from environment).
    """

    def __init__(
        self,
        config: DataFetcherConfig,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self._config = config
        self._client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=api_secret,
        )
        self._manifest = load_manifest(config.manifest_path)
        self._request_timestamps: list[float] = []

    @property
    def manifest(self) -> Manifest:
        """Access the current manifest (for testing and reporting)."""
        return self._manifest

    async def _rate_limit(self) -> None:
        """Enforce rate limiting by sleeping if necessary.

        Maintains a sliding window of request timestamps. If we've hit
        the per-minute limit, sleep until the oldest request falls out
        of the window.
        """
        now = time.monotonic()
        # Remove timestamps older than 60 seconds
        self._request_timestamps = [
            t for t in self._request_timestamps if now - t < 60.0
        ]
        if len(self._request_timestamps) >= self._config.max_requests_per_minute:
            sleep_time = 60.0 - (now - self._request_timestamps[0]) + 0.1
            if sleep_time > 0:
                logger.debug("Rate limit: sleeping %.1f seconds", sleep_time)
                await asyncio.sleep(sleep_time)
        self._request_timestamps.append(time.monotonic())

    def _fetch_bars_sync(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch bars for a single symbol and date range (synchronous).

        Handles pagination if the response exceeds the per-request limit.
        Retries on 429 (rate limit) responses.

        Args:
            symbol: Ticker symbol.
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            DataFrame with all bars for the range.
        """
        adjustment = Adjustment.SPLIT if self._config.adjustment == "split" else (
            Adjustment.ALL if self._config.adjustment == "all" else Adjustment.RAW
        )
        feed = DataFeed.IEX if self._config.feed == "iex" else DataFeed.SIP

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=TimeFrame(1, TimeFrameUnit.Minute),
            adjustment=adjustment,
            feed=feed,
            limit=10000,
        )

        for attempt in range(self._config.retry_max_attempts):
            try:
                bars = self._client.get_stock_bars(request)
                return _bars_to_dataframe(bars)
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "too many" in error_str or "rate" in error_str:
                    delay = self._config.retry_base_delay_seconds * (2 ** attempt)
                    logger.warning(
                        "Rate limited fetching %s (attempt %d/%d), sleeping %.1fs",
                        symbol, attempt + 1, self._config.retry_max_attempts, delay,
                    )
                    # Synchronous sleep in sync context
                    import time as time_mod
                    time_mod.sleep(delay)
                else:
                    logger.error(
                        "Error fetching %s (attempt %d/%d): %s",
                        symbol, attempt + 1, self._config.retry_max_attempts, e,
                    )
                    if attempt == self._config.retry_max_attempts - 1:
                        raise

        return pd.DataFrame()  # Should not reach here

    def _save_parquet(
        self, df: pd.DataFrame, symbol: str, year: int, month: int
    ) -> Path:
        """Save a DataFrame as a Parquet file in the expected directory structure.

        Creates directories as needed. File path:
        {data_dir}/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet

        Args:
            df: DataFrame to save.
            symbol: Ticker symbol.
            year: Year of data.
            month: Month of data.

        Returns:
            Path to the saved file.
        """
        symbol_dir = self._config.data_dir / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        file_path = symbol_dir / f"{symbol}_{year}-{month:02d}.parquet"
        df.to_parquet(file_path, index=False)
        logger.info(
            "Saved %d bars to %s", len(df), file_path
        )
        return file_path

    async def fetch_symbol_month(
        self,
        symbol: str,
        year: int,
        month: int,
        month_start: date,
        month_end: date,
        force: bool = False,
    ) -> SymbolMonthEntry | None:
        """Fetch and save one symbol-month of data.

        Skips if already in manifest (unless force=True).
        Validates after saving. Updates manifest.

        Args:
            symbol: Ticker symbol.
            year: Year.
            month: Month.
            month_start: First day of the month range.
            month_end: Last day of the month range.
            force: If True, re-download even if already in manifest.

        Returns:
            SymbolMonthEntry if downloaded, None if skipped.
        """
        if not force and self._manifest.has_entry(symbol, year, month):
            logger.debug("Skipping %s %d-%02d (already in manifest)", symbol, year, month)
            return None

        await self._rate_limit()

        start_dt = datetime(month_start.year, month_start.month, month_start.day, tzinfo=timezone.utc)
        end_dt = datetime(month_end.year, month_end.month, month_end.day, 23, 59, 59, tzinfo=timezone.utc)

        logger.info("Fetching %s %d-%02d ...", symbol, year, month)

        # Run the synchronous Alpaca call in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, self._fetch_bars_sync, symbol, start_dt, end_dt
        )

        if df.empty:
            logger.warning("No data returned for %s %d-%02d", symbol, year, month)
            entry = SymbolMonthEntry(
                symbol=symbol,
                year=year,
                month=month,
                row_count=0,
                file_path="",
                downloaded_at=datetime.now(timezone.utc).isoformat(),
                source="alpaca_free",
                adjustment=self._config.adjustment,
                feed=self._config.feed,
                data_quality_issues=["No data returned from API"],
            )
            self._manifest.add_entry(entry)
            return entry

        file_path = self._save_parquet(df, symbol, year, month)

        # Validate
        validation = validate_parquet_file(file_path, symbol, year, month)

        entry = SymbolMonthEntry(
            symbol=symbol,
            year=year,
            month=month,
            row_count=validation.row_count,
            file_path=str(file_path),
            downloaded_at=datetime.now(timezone.utc).isoformat(),
            source="alpaca_free",
            adjustment=self._config.adjustment,
            feed=self._config.feed,
            data_quality_issues=validation.issues,
        )
        self._manifest.add_entry(entry)
        return entry

    async def fetch_all(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        force: bool = False,
    ) -> Manifest:
        """Fetch historical data for all symbols across the full date range.

        Iterates through each symbol and each month in the range.
        Saves manifest after each symbol completes (crash recovery).

        Args:
            symbols: List of ticker symbols.
            start_date: Start date of the range.
            end_date: End date of the range.
            force: If True, re-download everything ignoring manifest.

        Returns:
            Updated manifest with all entries.
        """
        month_ranges = _generate_month_ranges(start_date, end_date)
        total = len(symbols) * len(month_ranges)
        completed = 0
        skipped = 0

        logger.info(
            "Starting download: %d symbols × %d months = %d symbol-months",
            len(symbols), len(month_ranges), total,
        )

        for symbol in symbols:
            for year, month, m_start, m_end in month_ranges:
                entry = await self.fetch_symbol_month(
                    symbol, year, month, m_start, m_end, force=force
                )
                if entry is None:
                    skipped += 1
                completed += 1

                if completed % 10 == 0:
                    logger.info(
                        "Progress: %d/%d (%.0f%%), skipped %d",
                        completed, total, 100 * completed / total, skipped,
                    )

            # Save manifest after each symbol (crash recovery)
            save_manifest(self._manifest, self._config.manifest_path)
            logger.info(
                "Completed %s. Manifest saved (%d entries total).",
                symbol, self._manifest.total_files(),
            )

        # Final save
        save_manifest(self._manifest, self._config.manifest_path)
        logger.info(
            "Download complete. %d files, %d total bars, %d skipped.",
            self._manifest.total_files(),
            self._manifest.total_rows(),
            skipped,
        )
        return self._manifest

    def print_summary(self) -> None:
        """Print a human-readable summary of the manifest."""
        m = self._manifest
        print(f"\n{'=' * 60}")
        print(f"ARGUS Historical Data Summary")
        print(f"{'=' * 60}")
        print(f"Total files:  {m.total_files()}")
        print(f"Total bars:   {m.total_rows():,}")
        print(f"Symbols:      {len(m.get_symbols())}")
        print(f"\nSymbol Details:")
        for symbol in m.get_symbols():
            date_range = m.get_date_range(symbol)
            if date_range:
                print(f"  {symbol:8s}  {date_range[0]} → {date_range[1]}")
        issues = m.entries_with_issues()
        if issues:
            print(f"\nData Quality Issues ({len(issues)} files):")
            for entry in issues:
                print(f"  {entry.symbol} {entry.year}-{entry.month:02d}:")
                for issue in entry.data_quality_issues:
                    print(f"    - {issue}")
        else:
            print(f"\nNo data quality issues found.")
        print(f"{'=' * 60}\n")
```

---

## Step 5: CLI Entry Point

### File: `argus/backtest/__main__.py`

This allows running `python -m argus.backtest.data_fetcher ...` from the command line.

Actually, the cleaner approach: make `data_fetcher.py` itself runnable, and also provide a `__main__.py` for the backtest package if desired. The CLI lives at the bottom of `data_fetcher.py`:

### Append to `argus/backtest/data_fetcher.py`:

```python
def main() -> None:
    """CLI entry point for the data fetcher."""
    import argparse
    import os
    import yaml

    parser = argparse.ArgumentParser(
        description="Download historical 1-minute bar data from Alpaca.",
        prog="python -m argus.backtest.data_fetcher",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols (e.g., TSLA,NVDA,AAPL). "
             "If omitted, reads from config/backtest_universe.yaml.",
    )
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/historical/1m",
        help="Directory to store Parquet files (default: data/historical/1m).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if data exists in manifest.",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Resolve symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        universe_path = Path("config/backtest_universe.yaml")
        if not universe_path.exists():
            logger.error("No --symbols provided and %s not found", universe_path)
            raise SystemExit(1)
        with open(universe_path) as f:
            data = yaml.safe_load(f)
        symbols = data.get("symbols", [])
        if not symbols:
            logger.error("No symbols found in %s", universe_path)
            raise SystemExit(1)
        logger.info("Loaded %d symbols from %s", len(symbols), universe_path)

    # Parse dates
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    if end_date <= start_date:
        logger.error("End date must be after start date")
        raise SystemExit(1)

    # Build config
    config = DataFetcherConfig(
        data_dir=Path(args.data_dir),
        manifest_path=Path(args.data_dir).parent / "manifest.json",
    )

    # Get API credentials from environment
    api_key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        logger.error(
            "Alpaca API credentials not found. Set APCA_API_KEY_ID and "
            "APCA_API_SECRET_KEY environment variables."
        )
        raise SystemExit(1)

    fetcher = DataFetcher(config, api_key=api_key, api_secret=api_secret)

    logger.info(
        "Fetching %d symbols from %s to %s (data_dir: %s, force: %s)",
        len(symbols), start_date, end_date, config.data_dir, args.force,
    )

    asyncio.run(fetcher.fetch_all(symbols, start_date, end_date, force=args.force))
    fetcher.print_summary()


if __name__ == "__main__":
    main()
```

---

## Step 6: Tests for DataFetcher

### File: `tests/backtest/test_data_fetcher.py`

The DataFetcher tests mock the Alpaca client — we do NOT make real API calls in tests.

```python
"""Tests for the historical data fetcher.

All Alpaca API calls are mocked. These tests verify:
- Month range generation
- DataFrame conversion from Alpaca bar format
- File saving in correct directory structure
- Manifest tracking and resume behavior
- Rate limit logic
- CLI argument parsing
"""

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pandas as pd
import pytest

from argus.backtest.config import DataFetcherConfig
from argus.backtest.data_fetcher import (
    DataFetcher,
    _generate_month_ranges,
    _bars_to_dataframe,
)
from argus.backtest.manifest import load_manifest


class TestGenerateMonthRanges:
    """Tests for _generate_month_ranges helper."""

    def test_single_month(self) -> None:
        """Single month range generates one entry."""
        ranges = _generate_month_ranges(date(2025, 6, 1), date(2025, 7, 1))
        assert len(ranges) == 1
        year, month, start, end = ranges[0]
        assert (year, month) == (2025, 6)
        assert start == date(2025, 6, 1)
        assert end == date(2025, 6, 30)

    def test_multiple_months(self) -> None:
        """Multi-month range generates correct entries."""
        ranges = _generate_month_ranges(date(2025, 3, 1), date(2025, 6, 1))
        assert len(ranges) == 3  # March, April, May
        assert (ranges[0][0], ranges[0][1]) == (2025, 3)
        assert (ranges[1][0], ranges[1][1]) == (2025, 4)
        assert (ranges[2][0], ranges[2][1]) == (2025, 5)

    def test_cross_year_boundary(self) -> None:
        """Range crossing year boundary works correctly."""
        ranges = _generate_month_ranges(date(2025, 11, 1), date(2026, 2, 1))
        assert len(ranges) == 3  # Nov, Dec, Jan
        assert (ranges[0][0], ranges[0][1]) == (2025, 11)
        assert (ranges[1][0], ranges[1][1]) == (2025, 12)
        assert (ranges[2][0], ranges[2][1]) == (2026, 1)

    def test_full_year(self) -> None:
        """Full year generates 12 entries."""
        ranges = _generate_month_ranges(date(2025, 1, 1), date(2026, 1, 1))
        assert len(ranges) == 12

    def test_empty_range(self) -> None:
        """Same start and end produces empty list."""
        ranges = _generate_month_ranges(date(2025, 6, 1), date(2025, 6, 1))
        assert len(ranges) == 0


class TestBarsToDataFrame:
    """Tests for _bars_to_dataframe conversion."""

    def test_converts_alpaca_bars(self) -> None:
        """Alpaca bar objects are converted to standard DataFrame."""
        mock_bar = MagicMock()
        mock_bar.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        mock_bar.open = 150.0
        mock_bar.high = 151.0
        mock_bar.low = 149.0
        mock_bar.close = 150.5
        mock_bar.volume = 10000

        # BarSet is dict-like: {symbol: [bar, bar, ...]}
        bars = {"AAPL": [mock_bar]}
        df = _bars_to_dataframe(bars)

        assert len(df) == 1
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert df.iloc[0]["open"] == 150.0
        assert df.iloc[0]["volume"] == 10000

    def test_empty_bars_returns_empty_df(self) -> None:
        """Empty bar response returns empty DataFrame with correct columns."""
        df = _bars_to_dataframe({})
        assert len(df) == 0
        assert "timestamp" in df.columns

    def test_timestamps_are_utc(self) -> None:
        """Output timestamps are always UTC-aware."""
        mock_bar = MagicMock()
        mock_bar.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        mock_bar.open = 150.0
        mock_bar.high = 151.0
        mock_bar.low = 149.0
        mock_bar.close = 150.5
        mock_bar.volume = 10000
        bars = {"AAPL": [mock_bar]}
        df = _bars_to_dataframe(bars)
        assert str(df["timestamp"].dt.tz) == "UTC"


class TestDataFetcher:
    """Tests for the DataFetcher class.

    Alpaca client is mocked — no real API calls.
    """

    @pytest.fixture
    def config(self, tmp_path: Path) -> DataFetcherConfig:
        """DataFetcherConfig pointing at tmp_path."""
        return DataFetcherConfig(
            data_dir=tmp_path / "1m",
            manifest_path=tmp_path / "manifest.json",
        )

    @pytest.fixture
    def mock_bar(self):
        """Create a mock Alpaca Bar object."""
        bar = MagicMock()
        bar.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        bar.open = 150.0
        bar.high = 151.0
        bar.low = 149.0
        bar.close = 150.5
        bar.volume = 10000
        return bar

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_fetch_symbol_month_saves_parquet(
        self, mock_client_cls, config, mock_bar, tmp_path
    ) -> None:
        """fetch_symbol_month downloads and saves a Parquet file."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        entry = await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )

        assert entry is not None
        assert entry.symbol == "AAPL"
        assert entry.row_count == 1
        parquet_path = tmp_path / "1m" / "AAPL" / "AAPL_2025-06.parquet"
        assert parquet_path.exists()

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_skips_if_already_in_manifest(
        self, mock_client_cls, config, mock_bar, tmp_path
    ) -> None:
        """fetch_symbol_month skips download if manifest has the entry."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        # First download
        await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )
        # Second download — should skip
        entry = await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )
        assert entry is None
        # Alpaca should have been called only once
        assert mock_client.get_stock_bars.call_count == 1

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_force_redownloads(
        self, mock_client_cls, config, mock_bar, tmp_path
    ) -> None:
        """force=True re-downloads even if in manifest."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )
        await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30), force=True
        )
        assert mock_client.get_stock_bars.call_count == 2

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_manifest_persists_after_fetch_all(
        self, mock_client_cls, config, mock_bar, tmp_path
    ) -> None:
        """fetch_all saves the manifest to disk."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        await fetcher.fetch_all(
            ["AAPL"], date(2025, 6, 1), date(2025, 7, 1)
        )

        # Load manifest from disk
        loaded = load_manifest(config.manifest_path)
        assert loaded.has_entry("AAPL", 2025, 6)
        assert loaded.total_files() == 1

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_empty_api_response_tracked(
        self, mock_client_cls, config, tmp_path
    ) -> None:
        """Empty API response is recorded in manifest with quality issue."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        entry = await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )

        assert entry is not None
        assert entry.row_count == 0
        assert "No data returned" in entry.data_quality_issues[0]
```

### File: `tests/backtest/__init__.py`

Create empty `__init__.py`.

---

## Step 7: .gitignore Update

Add to the project `.gitignore` (if not already present):

```
# Historical data (large Parquet files)
data/historical/
data/backtest_runs/
```

**Do NOT gitignore** `config/backtest_universe.yaml` — that's configuration, not data.

---

## Step 8: Documentation Stubs

### File: `docs/backtesting/DATA_INVENTORY.md`

```markdown
# ARGUS — Historical Data Inventory

> *Auto-generated after running the data fetcher. Update by re-running.*
> *Last updated: [pending first run]*

## Data Source

- **Provider:** Alpaca Markets (free tier)
- **Feed:** IEX
- **Adjustment:** Split-adjusted
- **Timeframe:** 1-minute bars
- **Storage format:** Parquet (one file per symbol per month)
- **Timezone:** UTC

## Symbol Universe

[pending first run]

## Date Range

[pending first run]

## Data Quality

[pending first run]

## Disk Usage

[pending first run]
```

This file gets filled in by the user after the first data fetch run.

---

## Test File Structure Summary

New files created in this sprint:

```
argus/
└── backtest/
    ├── __init__.py
    ├── config.py
    ├── data_fetcher.py       (includes CLI main())
    ├── data_validator.py
    └── manifest.py

config/
└── backtest_universe.yaml

data/
└── historical/               (gitignored — created by fetcher)
    ├── manifest.json          (created by fetcher)
    └── 1m/
        ├── AAPL/
        │   ├── AAPL_2025-03.parquet
        │   └── ...
        └── ...

docs/
└── backtesting/
    └── DATA_INVENTORY.md

tests/
└── backtest/
    ├── __init__.py
    ├── test_config.py
    ├── test_data_fetcher.py
    ├── test_data_validator.py
    └── test_manifest.py
```

---

## Success Criteria

Sprint 6 is done when:
- [ ] `DataFetcherConfig` Pydantic model created and tested
- [ ] `config/backtest_universe.yaml` created with ~29 symbols
- [ ] `Manifest` and `SymbolMonthEntry` dataclasses implemented with save/load
- [ ] `validate_parquet_file()` checks all 5 quality dimensions (OHLC, volume, timestamps, duplicates, missing days)
- [ ] `DataFetcher` downloads bars from Alpaca, saves as monthly Parquet files, tracks in manifest
- [ ] Resume capability works (skips existing entries, `--force` overrides)
- [ ] Rate limiting implemented (150 req/min throttle with sliding window)
- [ ] CLI works: `python -m argus.backtest.data_fetcher --symbols AAPL --start 2025-03-01 --end 2025-04-01`
- [ ] All new tests pass (target: ~18–22 new tests)
- [ ] All 362 existing tests still pass (no regressions)
- [ ] Ruff clean
- [ ] Committed and pushed

---

## After This Sprint

**User action required:** Run the data fetcher against Alpaca to download the actual data:

```bash
python -m argus.backtest.data_fetcher --start 2025-03-01 --end 2026-02-01
```

Review the summary output and fill in `docs/backtesting/DATA_INVENTORY.md` with the actual results. Fix any data quality issues before proceeding to Sprint 7 (Replay Harness).

**Spot-check:** Manually verify a few bars against a chart (e.g., NVDA's first bar on June 10, 2025 — the day after the 10:1 split took effect). Confirm split adjustment is working correctly.

---

## Decision Log Entries (to be committed with this sprint)

### DEC-048 | Parquet File Granularity
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | One Parquet file per symbol per month. Path: `data/historical/1m/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet` |
| **Rationale** | Small files (~300–500 KB), trivial resume on interrupted downloads, aligns with walk-forward monthly boundaries, efficient selective loading for date range queries. |
| **Alternatives** | Per-quarter (fewer files but harder resume), per-year (simpler but loads too much for partial ranges). |
| **Status** | Active |

### DEC-049 | Historical Data Time Zone Storage
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Store all historical bar timestamps in UTC. Convert to ET at read time in consumers. |
| **Rationale** | UTC is unambiguous (no DST transitions), matches Alpaca API output, matches existing ReplayDataService expectation (`timestamp: datetime (UTC)` in Sprint 3 spec), future-proof for non-US assets. |
| **Alternatives** | Store in ET (simpler for strategy logic but introduces DST ambiguity and diverges from existing code). |
| **Status** | Active |

### DEC-050 | Split-Adjusted Prices for Backtesting
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Always use `adjustment=Adjustment.SPLIT` when fetching historical bars. No dividend adjustment. |
| **Rationale** | Day trading strategies don't hold overnight, so dividends don't affect P&L. Split adjustment is essential to avoid phantom price jumps. Adjustment type recorded in manifest for traceability. |
| **Alternatives** | `all` (split + dividend — unnecessary for intraday), `raw` (would break any backtest spanning a split). |
| **Status** | Active |

### DEC-051 | Alpaca Free Tier Rate Limit Handling
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Throttle to 150 requests/minute (vs 200 limit). Sliding window rate limiter. Exponential backoff retry on 429. No overnight batching needed — full download completes in ~2–3 minutes. |
| **Rationale** | 30 symbols × 12 months = 360 requests, each returning ~8,190 bars (under 10,000 limit). Leaving 25% headroom prevents hitting the hard limit. Retry logic is a safety net, not expected to fire. |
| **Alternatives** | Paid plan at $99/month for 10,000 req/min (unnecessary for this volume). |
| **Status** | Active |

---

*End of Sprint 6 Implementation Spec*

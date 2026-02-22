"""Manifest for tracking downloaded historical data.

The manifest is a JSON file that records which symbol-months have been
downloaded, their row counts, date ranges, and any data quality issues.
This enables resume-on-interrupt and powers the DATA_INVENTORY report.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SymbolMonthEntry:
    """Record of a single downloaded symbol-month Parquet file.

    Attributes:
        symbol: Ticker symbol (e.g., "AAPL").
        year: Year of the data (e.g., 2025).
        month: Month of the data (1-12).
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
        entries: Dict keyed by "{SYMBOL}_{YYYY}-{MM}" -> SymbolMonthEntry.
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
        self.last_updated = datetime.now(UTC).isoformat()

    def get_symbols(self) -> list[str]:
        """Return sorted list of unique symbols in the manifest."""
        return sorted({e.symbol for e in self.entries.values()})

    def get_date_range(self, symbol: str) -> tuple[str, str] | None:
        """Return (earliest_month, latest_month) for a symbol, or None."""
        months = [(e.year, e.month) for e in self.entries.values() if e.symbol == symbol]
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
        logger.info("No existing manifest at %s - starting fresh", path)
        now = datetime.now(UTC).isoformat()
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

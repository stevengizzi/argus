"""Tests for the historical data manifest."""

from pathlib import Path

from argus.backtest.manifest import (
    Manifest,
    SymbolMonthEntry,
    load_manifest,
    save_manifest,
)


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

    def test_creation_with_issues(self) -> None:
        """SymbolMonthEntry can be created with data quality issues."""
        entry = SymbolMonthEntry(
            symbol="TSLA",
            year=2025,
            month=3,
            row_count=8000,
            file_path="data/historical/1m/TSLA/TSLA_2025-03.parquet",
            downloaded_at="2026-02-16T10:00:00Z",
            data_quality_issues=["3 zero-volume bars"],
        )
        assert len(entry.data_quality_issues) == 1
        assert "zero-volume" in entry.data_quality_issues[0]


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
            symbol="TSLA",
            year=2025,
            month=3,
            row_count=8000,
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
            m.add_entry(
                SymbolMonthEntry(
                    symbol="AAPL",
                    year=2025,
                    month=month,
                    row_count=8000,
                    file_path=f"data/historical/1m/AAPL/AAPL_2025-{month:02d}.parquet",
                    downloaded_at="2026-02-16T10:00:00Z",
                )
            )
        assert m.get_date_range("AAPL") == ("2025-03", "2025-12")
        assert m.get_date_range("MSFT") is None

    def test_entries_with_issues(self) -> None:
        """entries_with_issues filters correctly."""
        m = Manifest(created_at="now", last_updated="now")
        m.add_entry(
            SymbolMonthEntry(
                symbol="AAPL",
                year=2025,
                month=3,
                row_count=8000,
                file_path="...",
                downloaded_at="...",
            )
        )
        m.add_entry(
            SymbolMonthEntry(
                symbol="TSLA",
                year=2025,
                month=3,
                row_count=7500,
                file_path="...",
                downloaded_at="...",
                data_quality_issues=["3 zero-volume bars during market hours"],
            )
        )
        issues = m.entries_with_issues()
        assert len(issues) == 1
        assert issues[0].symbol == "TSLA"

    def test_entry_key_format(self) -> None:
        """Entry keys follow {SYMBOL}_{YYYY}-{MM} format."""
        m = Manifest(created_at="now", last_updated="now")
        assert m.entry_key("AAPL", 2025, 3) == "AAPL_2025-03"
        assert m.entry_key("AAPL", 2025, 12) == "AAPL_2025-12"

    def test_get_symbols_sorted(self) -> None:
        """get_symbols returns sorted unique symbols."""
        m = Manifest(created_at="now", last_updated="now")
        for sym in ["TSLA", "AAPL", "NVDA", "AAPL"]:  # AAPL twice
            m.add_entry(
                SymbolMonthEntry(
                    symbol=sym,
                    year=2025,
                    month=6,
                    row_count=8000,
                    file_path="...",
                    downloaded_at="...",
                )
            )
        symbols = m.get_symbols()
        assert symbols == ["AAPL", "NVDA", "TSLA"]

    def test_add_entry_updates_last_updated(self) -> None:
        """Adding an entry updates last_updated timestamp."""
        m = Manifest(created_at="2026-01-01T00:00:00Z", last_updated="2026-01-01T00:00:00Z")
        original = m.last_updated
        m.add_entry(
            SymbolMonthEntry(
                symbol="AAPL",
                year=2025,
                month=6,
                row_count=8000,
                file_path="...",
                downloaded_at="...",
            )
        )
        assert m.last_updated != original


class TestManifestPersistence:
    """Tests for manifest save/load."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Manifest survives a save -> load roundtrip."""
        path = tmp_path / "manifest.json"
        m = Manifest(
            created_at="2026-02-16T00:00:00Z", last_updated="2026-02-16T00:00:00Z"
        )
        m.add_entry(
            SymbolMonthEntry(
                symbol="AAPL",
                year=2025,
                month=6,
                row_count=8190,
                file_path="data/historical/1m/AAPL/AAPL_2025-06.parquet",
                downloaded_at="2026-02-16T10:00:00Z",
                data_quality_issues=["1 zero-volume bar at 12:34"],
            )
        )
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

    def test_multiple_entries_roundtrip(self, tmp_path: Path) -> None:
        """Multiple entries survive roundtrip."""
        path = tmp_path / "manifest.json"
        m = Manifest(
            created_at="2026-02-16T00:00:00Z", last_updated="2026-02-16T00:00:00Z"
        )
        for month in range(1, 7):
            m.add_entry(
                SymbolMonthEntry(
                    symbol="AAPL",
                    year=2025,
                    month=month,
                    row_count=8000 + month * 100,
                    file_path=f"data/historical/1m/AAPL/AAPL_2025-{month:02d}.parquet",
                    downloaded_at="2026-02-16T10:00:00Z",
                )
            )
        save_manifest(m, path)

        loaded = load_manifest(path)
        assert loaded.total_files() == 6
        assert loaded.get_date_range("AAPL") == ("2025-01", "2025-06")

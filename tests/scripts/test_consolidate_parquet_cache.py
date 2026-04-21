"""Tests for scripts/consolidate_parquet_cache.py (Sprint 31.85, Session 1).

Fixture: a tiny 3-symbol, 2-month synthetic cache built under tmp_path.
All tests run with --workers 1 so the per-symbol worker executes in-process,
letting monkeypatches reach the consolidation path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from scripts import consolidate_parquet_cache as cpc  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SYMBOLS = ["AAA", "BBB", "CCC"]
_MONTHS = ["2025-01", "2025-02"]
_ROWS_PER_FILE = 5


def _build_month_frame(symbol: str, month: str) -> pd.DataFrame:
    """Construct a 5-row deterministic OHLCV frame for one (symbol, month)."""
    year, mo = month.split("-")
    base_ts = pd.Timestamp(f"{year}-{mo}-01T09:30:00", tz="UTC")
    symbol_offset = (ord(symbol[0]) - ord("A")) * 100.0
    records = []
    for i in range(_ROWS_PER_FILE):
        records.append(
            {
                "timestamp": base_ts + pd.Timedelta(minutes=i),
                "open": symbol_offset + i + 0.1,
                "high": symbol_offset + i + 0.5,
                "low": symbol_offset + i + 0.0,
                "close": symbol_offset + i + 0.3,
                "volume": 1000 + i,
            }
        )
    return pd.DataFrame.from_records(records)


def _build_fake_cache(root: Path) -> Path:
    """Build a 3-symbol × 2-month synthetic cache under `root`.

    Returns:
        The source directory path.
    """
    source = root / "source"
    for symbol in _SYMBOLS:
        sym_dir = source / symbol
        sym_dir.mkdir(parents=True, exist_ok=True)
        for month in _MONTHS:
            df = _build_month_frame(symbol, month)
            pq.write_table(pa.Table.from_pandas(df), sym_dir / f"{month}.parquet")
    return source


def _snapshot_tree(root: Path) -> dict[str, tuple[int, int, int]]:
    """Snapshot file -> (size, mtime_ns, inode) for byte-identity comparisons."""
    snap: dict[str, tuple[int, int, int]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            st = path.stat()
            snap[str(path.relative_to(root))] = (st.st_size, st.st_mtime_ns, st.st_ino)
    return snap


@pytest.fixture
def cache(tmp_path: Path) -> tuple[Path, Path]:
    """Return (source_dir, dest_dir) for a fresh canary cache."""
    source = _build_fake_cache(tmp_path)
    dest = tmp_path / "dest"
    return source, dest


# ---------------------------------------------------------------------------
# Core invariants
# ---------------------------------------------------------------------------


def test_consolidation_happy_path(cache: tuple[Path, Path]) -> None:
    """Script produces one file per symbol with the correct schema and row count."""
    source, dest = cache
    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    assert rc == 0

    produced = sorted(p for p in dest.rglob("*.parquet"))
    assert [p.name for p in produced] == [
        "AAA.parquet",
        "BBB.parquet",
        "CCC.parquet",
    ]
    tmp_leftovers = list(dest.rglob("*.parquet.tmp"))
    assert tmp_leftovers == []

    for p in produced:
        tbl = pq.read_table(p)
        assert tbl.num_rows == _ROWS_PER_FILE * len(_MONTHS)
        required = {"timestamp", "open", "high", "low", "close", "volume", "symbol"}
        assert required.issubset(set(tbl.column_names))
        df = tbl.to_pandas()
        assert df["timestamp"].is_monotonic_increasing


def test_original_cache_is_unmodified(cache: tuple[Path, Path]) -> None:
    """The source tree's file sizes and mtimes are byte-identical before/after."""
    source, dest = cache
    before = _snapshot_tree(source)
    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    assert rc == 0
    after = _snapshot_tree(source)
    assert before == after


def test_row_count_validation_detects_corruption(
    cache: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If concat yields a different row count than the source, the symbol fails."""
    source, dest = cache

    original_concat = cpc.pa.concat_tables

    def drop_one_row(tables, **kwargs):  # type: ignore[no-untyped-def]
        merged = original_concat(tables, **kwargs)
        return merged.slice(0, merged.num_rows - 1)

    monkeypatch.setattr(cpc.pa, "concat_tables", drop_one_row)

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    assert rc == 1
    assert list(dest.rglob("*.parquet")) == []
    assert list(dest.rglob("*.parquet.tmp")) == []


def test_resume_skips_valid_existing(
    cache: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    """A second run with default --resume skips every symbol."""
    source, dest = cache
    cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    first_snapshot = _snapshot_tree(dest)

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    assert rc == 0
    second_snapshot = _snapshot_tree(dest)
    for relpath, (size, mtime_ns, inode) in first_snapshot.items():
        assert second_snapshot[relpath] == (size, mtime_ns, inode), (
            f"{relpath} was rewritten during --resume second pass"
        )


def test_resume_reconsolidates_on_row_count_mismatch(
    cache: tuple[Path, Path]
) -> None:
    """--resume must re-validate by row count, not by existence alone."""
    source, dest = cache
    symbol = "AAA"
    sym_dest = dest / symbol
    sym_dest.mkdir(parents=True)
    bogus = pa.table({"timestamp": [pd.Timestamp("1999-01-01", tz="UTC")]})
    pq.write_table(bogus, sym_dest / f"{symbol}.parquet")

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
            "--symbols",
            "AAA",
        ]
    )
    assert rc == 0
    tbl = pq.read_table(sym_dest / f"{symbol}.parquet")
    assert tbl.num_rows == _ROWS_PER_FILE * len(_MONTHS)


def test_force_reconsolidates_always(cache: tuple[Path, Path]) -> None:
    """With --force, the second run re-writes every output file."""
    source, dest = cache
    cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    first = _snapshot_tree(dest)

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
            "--force",
        ]
    )
    assert rc == 0
    second = _snapshot_tree(dest)
    for relpath in first:
        assert first[relpath][2] != second[relpath][2], (
            f"inode unchanged — {relpath} was not rewritten under --force"
        )


def test_symbols_filter_comma_separated(cache: tuple[Path, Path]) -> None:
    """`--symbols AAA,CCC` processes only those two symbols."""
    source, dest = cache
    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
            "--symbols",
            "AAA,CCC",
        ]
    )
    assert rc == 0
    produced = sorted(p.parent.name for p in dest.rglob("*.parquet"))
    assert produced == ["AAA", "CCC"]


def test_symbols_filter_file(cache: tuple[Path, Path], tmp_path: Path) -> None:
    """`--symbols @file.txt` reads symbols from a file."""
    source, dest = cache
    symbols_file = tmp_path / "syms.txt"
    symbols_file.write_text("BBB\n# comment\n\nCCC\n")

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
            "--symbols",
            f"@{symbols_file}",
        ]
    )
    assert rc == 0
    produced = sorted(p.parent.name for p in dest.rglob("*.parquet"))
    assert produced == ["BBB", "CCC"]


def test_limit_flag(cache: tuple[Path, Path]) -> None:
    """--limit 2 processes only the first two symbols in sorted order."""
    source, dest = cache
    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
            "--limit",
            "2",
        ]
    )
    assert rc == 0
    produced = sorted(p.parent.name for p in dest.rglob("*.parquet"))
    assert produced == ["AAA", "BBB"]


def test_dry_run_writes_nothing(cache: tuple[Path, Path]) -> None:
    """--dry-run creates no output files."""
    source, dest = cache
    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
            "--dry-run",
        ]
    )
    assert rc == 0
    assert list(dest.rglob("*.parquet")) == []
    assert list(dest.rglob("*.parquet.tmp")) == []


def test_verify_benchmark_runs(cache: tuple[Path, Path], tmp_path: Path) -> None:
    """--verify-only produces a markdown report against an existing consolidated cache."""
    source, dest = cache
    cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        (tmp_path / "data").mkdir(exist_ok=True)
        rc = cpc.main(
            [
                "--dest-dir",
                str(dest),
                "--verify-only",
            ]
        )
    finally:
        os.chdir(cwd)

    assert rc == 0
    reports = list((tmp_path / "data").glob("consolidation_benchmark_*.md"))
    assert len(reports) == 1
    text = reports[0].read_text()
    assert "Q1 COUNT(DISTINCT symbol)" in text
    assert "Q2 single-symbol range" in text
    assert "Q3 batch coverage" in text


def test_disk_space_preflight_blocks(
    cache: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Insufficient disk space causes exit code 1 before any work runs."""
    source, dest = cache

    class FakeUsage:
        total = 0
        used = 0
        free = 1 * 1024**3  # 1 GB, well below the 60 GB default

    monkeypatch.setattr(cpc.shutil, "disk_usage", lambda _path: FakeUsage())

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--min-free-gb",
            "60",
        ]
    )
    assert rc == 1
    assert list(dest.rglob("*.parquet")) == []


def test_symbol_column_populated_correctly(cache: tuple[Path, Path]) -> None:
    """Every row in each consolidated file carries its own symbol label."""
    source, dest = cache
    cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    for symbol in _SYMBOLS:
        tbl = pq.read_table(dest / symbol / f"{symbol}.parquet")
        values = tbl.column("symbol").to_pylist()
        assert values == [symbol] * tbl.num_rows


def test_atomic_write_cleanup(
    cache: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """If write_table raises, no .parquet.tmp remains and no final file is promoted."""
    source, dest = cache

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise IOError("simulated write failure")

    monkeypatch.setattr(cpc.pq, "write_table", boom)

    rc = cpc.main(
        [
            "--source-dir",
            str(source),
            "--dest-dir",
            str(dest),
            "--workers",
            "1",
            "--force-no-disk-check",
        ]
    )
    assert rc == 1  # any failed symbol — including IO failures — exits non-zero
    assert list(dest.rglob("*.parquet")) == []
    assert list(dest.rglob("*.parquet.tmp")) == []


def test_no_bypass_flag_exists() -> None:
    """Grep the script source for bypass markers that must NOT exist."""
    script_path = _REPO_ROOT / "scripts" / "consolidate_parquet_cache.py"
    src = script_path.read_text()
    for forbidden in (
        "--skip-validation",
        "--no-validate",
        "SKIP_VALIDATION",
    ):
        assert forbidden not in src, f"forbidden bypass token present: {forbidden}"

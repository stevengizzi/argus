"""Tests for universe-aware sweep flags added in Sprint 31A.75, Session 1.

Covers _parse_symbols, _load_universe_filter, and parse_args behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Make sure the repo root is on the path so scripts/ is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from scripts.run_experiment import _load_universe_filter, _parse_symbols, parse_args  # noqa: E402


# ---------------------------------------------------------------------------
# _parse_symbols tests
# ---------------------------------------------------------------------------


def test_parse_symbols_comma_separated() -> None:
    """Comma-separated string produces correct uppercased list."""
    result = _parse_symbols("AAPL,NVDA,TSLA")
    assert result == ["AAPL", "NVDA", "TSLA"]


def test_parse_symbols_with_whitespace() -> None:
    """Whitespace around symbols is stripped and symbols are uppercased."""
    result = _parse_symbols(" aapl , nvda , tsla ")
    assert result == ["AAPL", "NVDA", "TSLA"]


def test_parse_symbols_from_file(tmp_path: Path) -> None:
    """@filepath reads symbols from file, one per line."""
    symbol_file = tmp_path / "symbols.txt"
    symbol_file.write_text("AAPL\nNVDA\nTSLA\n")
    result = _parse_symbols(f"@{symbol_file}")
    assert result == ["AAPL", "NVDA", "TSLA"]


def test_parse_symbols_from_file_blank_lines(tmp_path: Path) -> None:
    """Blank lines in symbol file are filtered out."""
    symbol_file = tmp_path / "symbols.txt"
    symbol_file.write_text("AAPL\n\nNVDA\n  \nTSLA\n")
    result = _parse_symbols(f"@{symbol_file}")
    assert result == ["AAPL", "NVDA", "TSLA"]


def test_parse_symbols_deduplicates() -> None:
    """Duplicate symbols are removed while preserving order."""
    result = _parse_symbols("AAPL,NVDA,AAPL")
    assert result == ["AAPL", "NVDA"]


def test_parse_symbols_uppercase() -> None:
    """Lowercase input is uppercased."""
    result = _parse_symbols("aapl,nvda")
    assert result == ["AAPL", "NVDA"]


# ---------------------------------------------------------------------------
# _load_universe_filter tests
# ---------------------------------------------------------------------------


def test_load_universe_filter_valid() -> None:
    """Loading narrow_range_breakout returns expected UniverseFilterConfig."""
    config = _load_universe_filter("narrow_range_breakout")
    assert config.min_price == pytest.approx(5.0)
    assert config.max_price == pytest.approx(200.0)
    assert config.min_avg_volume == 300000


def test_load_universe_filter_missing() -> None:
    """Nonexistent filter name raises SystemExit."""
    with pytest.raises(SystemExit):
        _load_universe_filter("__nonexistent_filter_xyz__")


# ---------------------------------------------------------------------------
# parse_args tests
# ---------------------------------------------------------------------------


def test_parse_args_symbols_flag() -> None:
    """--symbols flag is parsed correctly."""
    ns = parse_args(["--pattern", "bull_flag", "--symbols", "AAPL,NVDA"])
    assert ns.symbols == "AAPL,NVDA"


def test_parse_args_universe_filter_with_value() -> None:
    """--universe-filter with explicit value stores that value."""
    ns = parse_args(["--pattern", "bull_flag", "--universe-filter", "hod_break"])
    assert ns.universe_filter == "hod_break"


def test_parse_args_universe_filter_no_value() -> None:
    """--universe-filter without value stores sentinel '__from_pattern__'."""
    ns = parse_args(["--pattern", "bull_flag", "--universe-filter"])
    assert ns.universe_filter == "__from_pattern__"


def test_parse_args_defaults_unchanged() -> None:
    """Without new flags, symbols and universe_filter default to None."""
    ns = parse_args(["--pattern", "bull_flag"])
    assert ns.symbols is None
    assert ns.universe_filter is None

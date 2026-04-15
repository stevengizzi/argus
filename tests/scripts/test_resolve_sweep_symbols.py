"""Tests for scripts/resolve_sweep_symbols.py — Sprint 31.75, Session 3b."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

# ---------------------------------------------------------------------------
# Make sure the repo root is on sys.path so scripts/ is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from argus.core.config import UniverseFilterConfig  # noqa: E402
from scripts.resolve_sweep_symbols import (  # noqa: E402
    _apply_static_filters,
    _count_cache_symbols,
    _discover_patterns,
    _load_filter_config,
    _parse_date_range,
    _resolve_one_pattern,
    main,
    parse_args,
)


# ---------------------------------------------------------------------------
# 1. test_resolve_sweep_symbols_parse_args
# ---------------------------------------------------------------------------


def test_resolve_sweep_symbols_parse_args_single_pattern() -> None:
    """--pattern sets the pattern attribute; other args take defaults."""
    args = parse_args(["--pattern", "bull_flag", "--date-range", "2025-01-01,2025-12-31"])
    assert args.pattern == "bull_flag"
    assert args.all_patterns is False
    assert args.date_range == "2025-01-01,2025-12-31"
    assert args.cache_dir == "data/databento_cache"
    assert args.output_dir == "data/sweep_logs"
    assert args.persist_db == "data/historical_query.duckdb"
    assert args.min_bars == 100


def test_resolve_sweep_symbols_parse_args_all_patterns() -> None:
    """--all-patterns sets flag; mutually exclusive with --pattern."""
    args = parse_args(["--all-patterns", "--date-range", "2025-06-01,2025-12-31"])
    assert args.all_patterns is True
    assert args.pattern is None
    assert args.date_range == "2025-06-01,2025-12-31"


def test_resolve_sweep_symbols_parse_args_overrides() -> None:
    """Custom --cache-dir, --output-dir, --persist-db, --min-bars are respected."""
    args = parse_args([
        "--pattern", "hod_break",
        "--date-range", "2025-01-01,2025-12-31",
        "--cache-dir", "/tmp/cache",
        "--output-dir", "/tmp/out",
        "--persist-db", "/tmp/test.duckdb",
        "--min-bars", "200",
    ])
    assert args.cache_dir == "/tmp/cache"
    assert args.output_dir == "/tmp/out"
    assert args.persist_db == "/tmp/test.duckdb"
    assert args.min_bars == 200


def test_resolve_sweep_symbols_parse_args_mutual_exclusion() -> None:
    """--pattern and --all-patterns are mutually exclusive."""
    with pytest.raises(SystemExit):
        parse_args(["--pattern", "bull_flag", "--all-patterns", "--date-range", "2025-01-01,2025-12-31"])


def test_resolve_sweep_symbols_parse_date_range_valid() -> None:
    """Valid date range parses to (start, end) tuple."""
    start, end = _parse_date_range("2025-01-01,2025-12-31")
    assert start == "2025-01-01"
    assert end == "2025-12-31"


def test_resolve_sweep_symbols_parse_date_range_invalid() -> None:
    """Invalid date range string causes SystemExit."""
    with pytest.raises(SystemExit):
        _parse_date_range("2025-01-01")


# ---------------------------------------------------------------------------
# 2. test_resolve_sweep_symbols_single_pattern
# ---------------------------------------------------------------------------


def test_resolve_sweep_symbols_single_pattern(tmp_path: Path) -> None:
    """Single pattern: output file is written with correct sorted symbols."""
    filter_config = UniverseFilterConfig(min_price=10.0, max_price=500.0, min_avg_volume=500000)

    # Mock HistoricalQueryService
    mock_service = MagicMock()
    mock_service.is_available = True

    # _apply_static_filters queries service.query() — returns AAPL + NVDA
    mock_service.query.return_value = pd.DataFrame({"symbol": ["NVDA", "AAPL"]})
    # validate_symbol_coverage: AAPL has coverage, NVDA does not
    mock_service.validate_symbol_coverage.return_value = {"AAPL": True, "NVDA": False}

    # cache_total is passed in directly (computed by main() before looping)
    count = _resolve_one_pattern(
        service=mock_service,
        pattern_name="bull_flag",
        filter_config=filter_config,
        start_date="2025-01-01",
        end_date="2025-12-31",
        min_bars=100,
        output_dir=tmp_path,
        cache_total=50,
    )

    output_file = tmp_path / "symbols_bull_flag.txt"
    assert output_file.exists(), "Output file must be written"

    lines = [l for l in output_file.read_text().splitlines() if l.strip()]
    assert lines == ["AAPL"]  # sorted, NVDA dropped (no coverage)
    assert count == 1


def test_resolve_sweep_symbols_single_pattern_all_pass(tmp_path: Path) -> None:
    """When all symbols pass coverage, all are written to the output file."""
    filter_config = UniverseFilterConfig(min_price=5.0)
    mock_service = MagicMock()
    mock_service.query.return_value = pd.DataFrame({"symbol": ["TSLA", "AAPL", "MSFT"]})
    mock_service.validate_symbol_coverage.return_value = {
        "AAPL": True,
        "MSFT": True,
        "TSLA": True,
    }

    count = _resolve_one_pattern(
        service=mock_service,
        pattern_name="micro_pullback",
        filter_config=filter_config,
        start_date="2025-01-01",
        end_date="2025-12-31",
        min_bars=100,
        output_dir=tmp_path,
        cache_total=100,
    )

    output_file = tmp_path / "symbols_micro_pullback.txt"
    lines = [l for l in output_file.read_text().splitlines() if l.strip()]
    assert sorted(lines) == ["AAPL", "MSFT", "TSLA"]
    assert count == 3


# ---------------------------------------------------------------------------
# 3. test_resolve_sweep_symbols_all_patterns
# ---------------------------------------------------------------------------


def test_resolve_sweep_symbols_all_patterns_iterates_filter_dir() -> None:
    """_discover_patterns returns all stems from config/universe_filters/."""
    patterns = _discover_patterns()
    # All 10 production patterns must be present (bull_flag_trend added in S3b)
    expected_subset = {
        "bull_flag",
        "flat_top_breakout",
        "micro_pullback",
        "vwap_bounce",
        "narrow_range_breakout",
        "hod_break",
        "abcd",
        "gap_and_go",
        "premarket_high_break",
        "dip_and_rip",
    }
    assert expected_subset.issubset(set(patterns)), (
        f"Expected patterns not found. Discovered: {patterns}"
    )


def test_resolve_sweep_symbols_all_patterns_main_single_service(tmp_path: Path) -> None:
    """--all-patterns creates ONE HistoricalQueryService, not one per pattern."""
    service_instance = MagicMock()
    service_instance.is_available = True
    # Return empty df for count query; empty df for filter queries
    service_instance.query.return_value = pd.DataFrame({"n": [0]})
    service_instance.validate_symbol_coverage.return_value = {}

    constructor_call_count: list[int] = []

    def _mock_constructor(*args, **kwargs) -> MagicMock:
        constructor_call_count.append(1)
        return service_instance

    with (
        patch("scripts.resolve_sweep_symbols.HistoricalQueryService", side_effect=_mock_constructor),
        patch("scripts.resolve_sweep_symbols._discover_patterns", return_value=["bull_flag", "hod_break"]),
        patch("scripts.resolve_sweep_symbols.Path.mkdir"),
    ):
        # Patch the output file writes to use tmp_path
        with patch("scripts.resolve_sweep_symbols._resolve_one_pattern", return_value=0) as mock_resolve:
            exit_code = main([
                "--all-patterns",
                "--date-range", "2025-01-01,2025-12-31",
                "--output-dir", str(tmp_path),
                "--cache-dir", "/tmp/cache",
            ])

    # Exactly ONE HistoricalQueryService was constructed (reused across patterns)
    assert len(constructor_call_count) == 1, (
        f"Expected 1 service instantiation, got {len(constructor_call_count)}"
    )
    # Both patterns were processed
    assert mock_resolve.call_count == 2
    assert exit_code == 0


# ---------------------------------------------------------------------------
# 4. test_bull_flag_trend_yaml_valid
# ---------------------------------------------------------------------------


def test_bull_flag_trend_yaml_valid() -> None:
    """bull_flag_trend.yaml parses into a valid UniverseFilterConfig."""
    yaml_path = Path("config/universe_filters/bull_flag_trend.yaml")
    assert yaml_path.exists(), f"File not found: {yaml_path}"

    raw = yaml.safe_load(yaml_path.read_text()) or {}
    cfg = UniverseFilterConfig(**raw)

    assert cfg.min_price is not None and cfg.min_price > 0
    assert cfg.max_price is not None and cfg.max_price > 0
    assert cfg.min_avg_volume is not None and cfg.min_avg_volume > 0


def test_bull_flag_trend_differs_from_bull_flag() -> None:
    """bull_flag_trend.yaml has different criteria from bull_flag.yaml."""
    trend_raw = yaml.safe_load(
        Path("config/universe_filters/bull_flag_trend.yaml").read_text()
    ) or {}
    momentum_raw = yaml.safe_load(
        Path("config/universe_filters/bull_flag.yaml").read_text()
    ) or {}

    trend_cfg = UniverseFilterConfig(**trend_raw)
    momentum_cfg = UniverseFilterConfig(**momentum_raw)

    # At least one criterion must differ (otherwise comparison is meaningless)
    differs = (
        trend_cfg.min_price != momentum_cfg.min_price
        or trend_cfg.max_price != momentum_cfg.max_price
        or trend_cfg.min_avg_volume != momentum_cfg.min_avg_volume
    )
    assert differs, "bull_flag_trend.yaml must differ from bull_flag.yaml for the S4 comparison to be meaningful"


# ---------------------------------------------------------------------------
# 5. test_run_sweep_batch_exists_and_executable
# ---------------------------------------------------------------------------


def test_run_sweep_batch_exists_and_executable() -> None:
    """scripts/run_sweep_batch.sh exists and has the executable bit set."""
    script_path = Path("scripts/run_sweep_batch.sh")
    assert script_path.exists(), "scripts/run_sweep_batch.sh must exist"
    assert script_path.stat().st_mode & 0o111, "run_sweep_batch.sh must be executable"


def test_run_sweep_batch_no_tee_in_sweep_phase() -> None:
    """Output redirection must use '> logfile 2>&1', not '| tee' (prevents pipe hangs)."""
    script_content = Path("scripts/run_sweep_batch.sh").read_text()
    assert "| tee" not in script_content, (
        "run_sweep_batch.sh must not use '| tee' — use '> logfile 2>&1' instead "
        "to prevent pipe-death hangs when a test hangs"
    )


def test_run_sweep_batch_uses_continue_not_exit() -> None:
    """Error handling must use 'continue' (not '|| exit') for pattern isolation.

    The script uses '|| { ... continue }' block form; we verify 'continue' is
    present for per-pattern isolation and that '|| exit' is absent.
    """
    script_content = Path("scripts/run_sweep_batch.sh").read_text()
    # 'continue' must appear somewhere in the sweep loop for error isolation
    assert "continue" in script_content, (
        "run_sweep_batch.sh must use 'continue' for per-pattern error isolation"
    )
    # Ensure we don't have || exit in the sweep loop (would kill the whole batch)
    assert "|| exit" not in script_content, (
        "run_sweep_batch.sh must not use '|| exit' in the sweep loop"
    )

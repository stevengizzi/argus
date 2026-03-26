"""Tests for scripts/validate_all_strategies.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_all_strategies import (
    STRATEGY_REGISTRY,
    build_output_json,
    main,
    parse_args,
    parse_validation_result,
    run_comparison_phase,
)


# ---------------------------------------------------------------------------
# 1. Strategy registry has all seven strategies
# ---------------------------------------------------------------------------


def test_strategy_registry_has_all_seven() -> None:
    """Verify all 7 strategies are defined in the registry."""
    expected_keys = {
        "orb",
        "orb_scalp",
        "vwap_reclaim",
        "afternoon_momentum",
        "red_to_green",
        "bull_flag",
        "flat_top_breakout",
    }
    assert set(STRATEGY_REGISTRY.keys()) == expected_keys

    # Each entry must have start, end, description
    for key, config in STRATEGY_REGISTRY.items():
        assert "start" in config, f"{key} missing 'start'"
        assert "end" in config, f"{key} missing 'end'"
        assert "description" in config, f"{key} missing 'description'"


# ---------------------------------------------------------------------------
# 2. CLI --help exits 0
# ---------------------------------------------------------------------------


def test_cli_help_works() -> None:
    """Verify --help exits 0 without error."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# 3. CLI requires --cache-dir
# ---------------------------------------------------------------------------


def test_cli_requires_cache_dir() -> None:
    """Verify missing --cache-dir causes exit with error."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args([])
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 4. --strategies filter only processes specified strategies
# ---------------------------------------------------------------------------


def test_strategies_filter() -> None:
    """Verify --strategies orb vwap_reclaim only processes those two."""
    args = parse_args([
        "--cache-dir", "/tmp/fake-cache",
        "--strategies", "orb", "vwap_reclaim",
    ])
    assert args.strategies == ["orb", "vwap_reclaim"]
    assert args.cache_dir == "/tmp/fake-cache"


# ---------------------------------------------------------------------------
# 5. JSON output structure has expected keys
# ---------------------------------------------------------------------------


def _make_mock_raw() -> dict[str, Any]:
    """Create a mock revalidate_strategy.py JSON output."""
    return {
        "strategy": "orb_breakout",
        "strategy_type": "orb",
        "date_range": {"start": "2023-03-01", "end": "2025-03-01"},
        "data_source": "databento_ohlcv_1m",
        "engine": "backtest_engine",
        "baseline": None,
        "new_results": {
            "oos_sharpe": 1.82,
            "wfe_pnl": 0.56,
            "wfe_sharpe": 0.48,
            "total_oos_trades": 847,
            "avg_win_rate": 0.421,
            "avg_profit_factor": 1.34,
            "total_windows": 8,
            "valid_windows": 8,
            "data_months": 24,
        },
        "divergence": {"flagged": False, "flags": []},
        "status": "VALIDATED",
        "walk_forward_available": True,
        "notes": "",
    }


def test_output_json_structure() -> None:
    """Verify JSON output has all expected top-level keys."""
    mock_raw = _make_mock_raw()
    mor = parse_validation_result("orb", mock_raw)

    results = {"orb": mor}
    raw_results = {"orb": mock_raw}
    analysis = run_comparison_phase(results)
    failures: dict[str, str] = {}

    output = build_output_json(results, raw_results, analysis, failures, None)

    # Top-level keys
    assert "timestamp" in output
    assert "strategies" in output
    assert "failures" in output
    assert "analysis" in output
    assert "ensemble" in output
    assert "summary" in output

    # Summary structure
    summary = output["summary"]
    assert summary["total"] == 1
    assert summary["succeeded"] == 1
    assert summary["failed"] == 0
    assert "pareto_members" in summary

    # Strategy entry structure
    strat_entry = output["strategies"]["orb"]
    assert "multi_objective_result" in strat_entry
    assert "raw_validation" in strat_entry

    # MOR has standard fields
    mor_dict = strat_entry["multi_objective_result"]
    assert "sharpe_ratio" in mor_dict
    assert "win_rate" in mor_dict
    assert "total_trades" in mor_dict
    assert "confidence_tier" in mor_dict


# ---------------------------------------------------------------------------
# 6. Failed strategy continues — one failure doesn't abort others
# ---------------------------------------------------------------------------


def test_failed_strategy_continues() -> None:
    """One strategy failure doesn't abort the remaining strategies."""
    mock_raw = _make_mock_raw()

    call_count = 0

    def mock_subprocess_run(
        cmd: list[str],
        capture_output: bool = False,
        text: bool = False,
        timeout: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal call_count
        call_count += 1
        strategy_idx = None
        for i, arg in enumerate(cmd):
            if arg == "--strategy" and i + 1 < len(cmd):
                strategy_idx = cmd[i + 1]
                break

        if strategy_idx == "orb":
            # First strategy fails
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr="Simulated failure for orb",
            )
        else:
            # Others succeed
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

    def mock_find_json(output_dir: str, strategy_key: str) -> Path | None:
        if strategy_key == "orb":
            return None
        tmp_path = Path(output_dir) / f"{strategy_key}_validation.json"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(mock_raw))
        return tmp_path

    with (
        patch(
            "scripts.validate_all_strategies.subprocess.run",
            side_effect=mock_subprocess_run,
        ),
        patch(
            "scripts.validate_all_strategies._find_validation_json",
            side_effect=mock_find_json,
        ),
    ):
        exit_code = main([
            "--cache-dir", "/tmp/fake-cache",
            "--strategies", "orb", "vwap_reclaim",
        ])

    # Should have called subprocess for both strategies
    assert call_count == 2
    # Exit code 1 because orb failed
    assert exit_code == 1


# ---------------------------------------------------------------------------
# 7. parse_validation_result constructs valid MultiObjectiveResult
# ---------------------------------------------------------------------------


def test_parse_validation_result_fields() -> None:
    """Verify parse_validation_result maps fields correctly."""
    mock_raw = _make_mock_raw()
    mor = parse_validation_result("orb", mock_raw)

    assert mor.strategy_id == "orb"
    assert mor.sharpe_ratio == 1.82
    assert mor.win_rate == 0.421
    assert mor.profit_factor == 1.34
    assert mor.total_trades == 847
    assert mor.wfe == 0.56
    assert mor.is_oos is True
    assert mor.data_range[0].isoformat() == "2023-03-01"
    assert mor.data_range[1].isoformat() == "2025-03-01"


# ---------------------------------------------------------------------------
# 8. --ensemble flag is parsed correctly
# ---------------------------------------------------------------------------


def test_ensemble_flag_parsed() -> None:
    """Verify --ensemble flag is correctly parsed."""
    args_with = parse_args([
        "--cache-dir", "/tmp/fake",
        "--ensemble",
    ])
    assert args_with.ensemble is True

    args_without = parse_args(["--cache-dir", "/tmp/fake"])
    assert args_without.ensemble is False

"""Tests for the re-validation harness script.

Tests config extraction, baseline parsing, and divergence detection logic.
Does NOT actually run BacktestEngine or walk-forward (those are expensive).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure scripts directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from revalidate_strategy import (
    SHARPE_DIVERGENCE_THRESHOLD,
    detect_divergence,
    determine_status,
    extract_baseline,
    extract_fixed_params,
)


# ---------------------------------------------------------------------------
# Fixtures: representative YAML configs
# ---------------------------------------------------------------------------


@pytest.fixture
def orb_yaml_config() -> dict[str, Any]:
    """ORB Breakout YAML config (mirrors config/strategies/orb_breakout.yaml)."""
    return {
        "strategy_id": "strat_orb_breakout",
        "name": "ORB Breakout",
        "orb_window_minutes": 5,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "time_stop_minutes": 15,
        "max_range_atr_ratio": 999.0,
        "backtest_summary": {
            "status": "walk_forward_complete",
            "wfe_pnl": 0.56,
            "oos_sharpe": 0.34,
            "total_trades": 137,
            "data_months": 35,
            "last_run": "2026-02-17",
        },
    }


@pytest.fixture
def vwap_yaml_config() -> dict[str, Any]:
    """VWAP Reclaim YAML config (mirrors config/strategies/vwap_reclaim.yaml)."""
    return {
        "strategy_id": "strat_vwap_reclaim",
        "name": "VWAP Reclaim",
        "min_pullback_pct": 0.002,
        "min_pullback_bars": 3,
        "volume_confirmation_multiplier": 1.2,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "time_stop_minutes": 30,
        "backtest_summary": {
            "status": "walk_forward_complete",
            "wfe_pnl": None,
            "oos_sharpe": 1.49,
            "total_trades": 59556,
            "data_months": 35,
            "last_run": "2026-02-26",
        },
    }


# ---------------------------------------------------------------------------
# Tests: extract_fixed_params
# ---------------------------------------------------------------------------


class TestExtractFixedParams:
    """Tests for YAML → fixed-params mapping."""

    def test_extract_fixed_params_orb(self, orb_yaml_config: dict[str, Any]) -> None:
        """Verify ORB Breakout YAML maps to correct VectorBT fixed-params."""
        params = extract_fixed_params("orb", orb_yaml_config)

        assert params["or_minutes"] == 5
        assert params["target_r"] == 2.0
        assert params["stop_buffer_pct"] == 0.0
        assert params["max_hold_minutes"] == 15
        assert params["max_range_atr_ratio"] == 999.0
        # min_gap_pct defaults to 2.0 when not in YAML
        assert params["min_gap_pct"] == 2.0
        # Exactly 6 params expected for ORB
        assert len(params) == 6

    def test_extract_fixed_params_vwap(self, vwap_yaml_config: dict[str, Any]) -> None:
        """Verify VWAP Reclaim YAML maps to correct VectorBT fixed-params."""
        params = extract_fixed_params("vwap_reclaim", vwap_yaml_config)

        assert params["min_pullback_pct"] == 0.002
        assert params["min_pullback_bars"] == 3
        assert params["volume_multiplier"] == 1.2
        assert params["target_r"] == 2.0
        assert params["time_stop_bars"] == 30
        assert len(params) == 5

    def test_extract_fixed_params_orb_scalp(self) -> None:
        """Verify ORB Scalp YAML maps correctly (seconds → bars)."""
        config = {"scalp_target_r": 0.3, "max_hold_seconds": 120}
        params = extract_fixed_params("orb_scalp", config)

        assert params["scalp_target_r"] == 0.3
        assert params["max_hold_bars"] == 2  # 120s / 60 = 2 bars
        assert len(params) == 2

    def test_extract_fixed_params_afternoon_momentum(self) -> None:
        """Verify Afternoon Momentum YAML maps correctly."""
        config = {
            "consolidation_atr_ratio": 0.75,
            "min_consolidation_bars": 30,
            "volume_multiplier": 1.2,
            "target_2_r": 2.0,
            "max_hold_minutes": 60,
        }
        params = extract_fixed_params("afternoon_momentum", config)

        assert params["consolidation_atr_ratio"] == 0.75
        assert params["min_consolidation_bars"] == 30
        assert params["volume_multiplier"] == 1.2
        assert params["target_r"] == 2.0
        assert params["time_stop_bars"] == 60
        assert len(params) == 5

    def test_extract_fixed_params_red_to_green(self) -> None:
        """Verify Red-to-Green YAML maps correctly."""
        config = {
            "min_gap_down_pct": 0.02,
            "level_proximity_pct": 0.003,
            "volume_confirmation_multiplier": 1.2,
            "time_stop_minutes": 20,
        }
        params = extract_fixed_params("red_to_green", config)

        assert params["min_gap_down_pct"] == 0.02
        assert params["level_proximity_pct"] == 0.003
        assert params["volume_confirmation_multiplier"] == 1.2
        assert params["time_stop_minutes"] == 20
        assert len(params) == 4

    def test_extract_fixed_params_bull_flag(self) -> None:
        """Verify Bull Flag extracts pattern params (skip metadata keys)."""
        config = {
            "strategy_id": "strat_bull_flag",
            "name": "Bull Flag",
            "version": "1.0.0",
            "enabled": True,
            "asset_class": "us_stocks",
            "pipeline_stage": "exploration",
            "family": "continuation",
            "description_short": "Bull flag continuation...",
            "time_window_display": "10:00 AM–3:00 PM",
            "operating_window": {"earliest_entry": "10:00"},
            "risk_limits": {"max_loss_per_trade_pct": 0.01},
            "benchmarks": {"min_win_rate": 0.45},
            "backtest_summary": {"status": "exploration"},
            "universe_filter": {"min_price": 10.0},
            "pole_min_bars": 5,
            "pole_min_move_pct": 0.03,
            "flag_max_bars": 20,
            "flag_max_retrace_pct": 0.50,
            "breakout_volume_multiplier": 1.3,
            "target_1_r": 1.0,
            "target_2_r": 2.0,
            "time_stop_minutes": 30,
        }
        params = extract_fixed_params("bull_flag", config)

        # Should only include scalar strategy params, not metadata/dicts
        assert "pole_min_bars" in params
        assert "flag_max_bars" in params
        assert "target_2_r" in params
        assert "strategy_id" not in params
        assert "name" not in params
        assert "operating_window" not in params
        assert "risk_limits" not in params
        assert "backtest_summary" not in params

    def test_extract_fixed_params_unknown_strategy_raises(self) -> None:
        """Verify unknown strategy key raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy key"):
            extract_fixed_params("nonexistent", {})


# ---------------------------------------------------------------------------
# Tests: extract_baseline
# ---------------------------------------------------------------------------


class TestExtractBaseline:
    """Tests for baseline extraction from YAML backtest_summary."""

    def test_extract_baseline_from_yaml(self, orb_yaml_config: dict[str, Any]) -> None:
        """Verify baseline extraction with populated fields."""
        baseline = extract_baseline(orb_yaml_config)

        assert baseline is not None
        assert baseline["oos_sharpe"] == 0.34
        assert baseline["wfe_pnl"] == 0.56
        assert baseline["total_trades"] == 137
        assert baseline["data_months"] == 35

    def test_extract_baseline_null_values(self, vwap_yaml_config: dict[str, Any]) -> None:
        """Verify null/missing baseline values handled gracefully."""
        baseline = extract_baseline(vwap_yaml_config)

        assert baseline is not None
        assert baseline["oos_sharpe"] == 1.49
        assert baseline["wfe_pnl"] is None  # null in YAML
        assert baseline["total_trades"] == 59556

    def test_extract_baseline_no_summary(self) -> None:
        """Verify None returned when no backtest_summary section."""
        config: dict[str, Any] = {"strategy_id": "strat_test", "name": "Test"}
        baseline = extract_baseline(config)
        assert baseline is None


# ---------------------------------------------------------------------------
# Tests: detect_divergence
# ---------------------------------------------------------------------------


class TestDetectDivergence:
    """Tests for divergence detection logic."""

    def test_divergence_detection_flagged(self) -> None:
        """Verify Sharpe diff > 0.5 triggers flag."""
        baseline = {
            "oos_sharpe": 0.34,
            "wfe_pnl": 0.56,
            "total_trades": 137,
        }
        new_results = {
            "oos_sharpe": 1.2,  # diff = 0.86 > 0.5
            "wfe_pnl": 0.60,
        }

        divergence = detect_divergence(baseline, new_results)

        assert divergence["flagged"] is True
        assert "sharpe_divergence" in divergence["flags"]
        assert divergence["sharpe_diff"] is not None
        assert divergence["sharpe_diff"] > SHARPE_DIVERGENCE_THRESHOLD

    def test_divergence_detection_clear(self) -> None:
        """Verify small differences don't trigger flag."""
        baseline = {
            "oos_sharpe": 0.34,
            "wfe_pnl": 0.56,
            "total_trades": 137,
        }
        new_results = {
            "oos_sharpe": 0.50,  # diff = 0.16 < 0.5
            "wfe_pnl": 0.60,
        }

        divergence = detect_divergence(baseline, new_results)

        assert divergence["flagged"] is False
        assert len(divergence["flags"]) == 0

    def test_divergence_no_baseline(self) -> None:
        """Verify graceful handling when baseline is None."""
        new_results = {"oos_sharpe": 0.50, "wfe_pnl": 0.60}
        divergence = detect_divergence(None, new_results)

        assert divergence["flagged"] is False
        assert "N/A" in divergence.get("note", "")

    def test_divergence_null_baseline_sharpe(self) -> None:
        """Verify null baseline sharpe doesn't flag."""
        baseline = {"oos_sharpe": None, "wfe_pnl": None, "total_trades": None}
        new_results = {"oos_sharpe": 1.5, "wfe_pnl": 0.8}

        divergence = detect_divergence(baseline, new_results)
        assert divergence["flagged"] is False
        assert divergence["sharpe_diff"] is None


# ---------------------------------------------------------------------------
# Tests: determine_status
# ---------------------------------------------------------------------------


class TestDetermineStatus:
    """Tests for validation status determination."""

    def test_zero_trades(self) -> None:
        """Verify ZERO_TRADES status when no trades."""
        assert determine_status(
            {"total_oos_trades": 0}, {"flagged": False}, {"oos_sharpe": 0.5}
        ) == "ZERO_TRADES"

    def test_new_baseline(self) -> None:
        """Verify NEW_BASELINE when baseline has all null values."""
        baseline = {"oos_sharpe": None, "wfe_pnl": None, "total_trades": None}
        assert determine_status(
            {"total_oos_trades": 50, "wfe_pnl": 0.5},
            {"flagged": False},
            baseline,
        ) == "NEW_BASELINE"

    def test_wfe_below_threshold(self) -> None:
        """Verify WFE_BELOW_THRESHOLD when WFE < 0.3."""
        baseline = {"oos_sharpe": 0.5, "wfe_pnl": 0.6, "total_trades": 100}
        assert determine_status(
            {"total_oos_trades": 50, "wfe_pnl": 0.2},
            {"flagged": False},
            baseline,
        ) == "WFE_BELOW_THRESHOLD"

    def test_divergent(self) -> None:
        """Verify DIVERGENT when flagged."""
        baseline = {"oos_sharpe": 0.5, "wfe_pnl": 0.6, "total_trades": 100}
        assert determine_status(
            {"total_oos_trades": 50, "wfe_pnl": 0.5},
            {"flagged": True, "flags": ["sharpe_divergence"]},
            baseline,
        ) == "DIVERGENT"

    def test_validated(self) -> None:
        """Verify VALIDATED when all checks pass."""
        baseline = {"oos_sharpe": 0.5, "wfe_pnl": 0.6, "total_trades": 100}
        assert determine_status(
            {"total_oos_trades": 50, "wfe_pnl": 0.5},
            {"flagged": False},
            baseline,
        ) == "VALIDATED"

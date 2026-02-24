"""Tests for walk-forward analysis engine."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from argus.backtest.walk_forward import (
    NoQualifyingParamsError,
    WalkForwardConfig,
    WalkForwardResult,
    WindowResult,
    compute_parameter_stability,
    compute_wfe,
    compute_windows,
    evaluate_fixed_params_on_is,
    load_walk_forward_results,
    optimize_in_sample,
    save_walk_forward_results,
    validate_out_of_sample,
)

# ---------------------------------------------------------------------------
# Test 1: compute_windows_basic
# ---------------------------------------------------------------------------


def test_compute_windows_basic():
    """11 months of data with 4/2/2 config produces correct windows with correct date ranges."""
    config = WalkForwardConfig(
        in_sample_months=4,
        out_of_sample_months=2,
        step_months=2,
    )

    # 12 months of data: Mar 2025 to Feb 2026 (need full 12 months for 4 windows)
    data_start = date(2025, 3, 1)
    data_end = date(2026, 2, 28)

    windows = compute_windows(data_start, data_end, config)

    assert len(windows) == 4

    # Window 1: IS=Mar-Jun 2025, OOS=Jul-Aug 2025
    assert windows[0][0] == date(2025, 3, 1)  # is_start
    assert windows[0][1] == date(2025, 6, 30)  # is_end
    assert windows[0][2] == date(2025, 7, 1)  # oos_start
    assert windows[0][3] == date(2025, 8, 31)  # oos_end

    # Window 2: IS=May-Aug 2025, OOS=Sep-Oct 2025
    assert windows[1][0] == date(2025, 5, 1)  # is_start
    assert windows[1][1] == date(2025, 8, 31)  # is_end
    assert windows[1][2] == date(2025, 9, 1)  # oos_start
    assert windows[1][3] == date(2025, 10, 31)  # oos_end

    # Window 3: IS=Jul-Oct 2025, OOS=Nov-Dec 2025
    assert windows[2][0] == date(2025, 7, 1)  # is_start
    assert windows[2][1] == date(2025, 10, 31)  # is_end
    assert windows[2][2] == date(2025, 11, 1)  # oos_start
    assert windows[2][3] == date(2025, 12, 31)  # oos_end

    # Window 4: IS=Sep-Dec 2025, OOS=Jan-Feb 2026
    assert windows[3][0] == date(2025, 9, 1)  # is_start
    assert windows[3][1] == date(2025, 12, 31)  # is_end
    assert windows[3][2] == date(2026, 1, 1)  # oos_start
    assert windows[3][3] == date(2026, 2, 28)  # oos_end


# ---------------------------------------------------------------------------
# Test 2: compute_windows_insufficient_data
# ---------------------------------------------------------------------------


def test_compute_windows_insufficient_data():
    """Data range too short for one window returns empty list."""
    config = WalkForwardConfig(
        in_sample_months=4,
        out_of_sample_months=2,
        step_months=2,
    )

    # Only 5 months of data (need 6 for one window)
    data_start = date(2025, 3, 1)
    data_end = date(2025, 7, 31)

    windows = compute_windows(data_start, data_end, config)

    assert windows == []


# ---------------------------------------------------------------------------
# Test 3: compute_windows_edge_month_boundaries
# ---------------------------------------------------------------------------


def test_compute_windows_edge_month_boundaries():
    """Windows align to month boundaries correctly."""
    config = WalkForwardConfig(
        in_sample_months=3,
        out_of_sample_months=1,
        step_months=1,
    )

    # Start mid-month shouldn't affect month boundary alignment
    data_start = date(2025, 3, 15)
    data_end = date(2025, 8, 15)

    windows = compute_windows(data_start, data_end, config)

    # Should get windows starting from March 15
    assert len(windows) >= 1

    # First window
    is_start, is_end, oos_start, oos_end = windows[0]

    # IS should be 3 months from start
    assert is_start == date(2025, 3, 15)
    # is_end should be 3 months later minus 1 day
    assert is_end == date(2025, 6, 14)
    # OOS starts right after IS ends
    assert oos_start == date(2025, 6, 15)
    # OOS is 1 month
    assert oos_end == date(2025, 7, 14)


# ---------------------------------------------------------------------------
# Test 4: compute_windows_custom_config
# ---------------------------------------------------------------------------


def test_compute_windows_custom_config():
    """Non-default IS/OOS/step values produce correct windows."""
    config = WalkForwardConfig(
        in_sample_months=6,
        out_of_sample_months=3,
        step_months=3,
    )

    # 12 months of data
    data_start = date(2025, 1, 1)
    data_end = date(2025, 12, 31)

    windows = compute_windows(data_start, data_end, config)

    # With 6+3=9 months needed and 3-month steps, should get 2 windows
    assert len(windows) == 2

    # Window 1: IS=Jan-Jun, OOS=Jul-Sep
    assert windows[0][0] == date(2025, 1, 1)
    assert windows[0][1] == date(2025, 6, 30)
    assert windows[0][2] == date(2025, 7, 1)
    assert windows[0][3] == date(2025, 9, 30)

    # Window 2: IS=Apr-Sep, OOS=Oct-Dec
    assert windows[1][0] == date(2025, 4, 1)
    assert windows[1][1] == date(2025, 9, 30)
    assert windows[1][2] == date(2025, 10, 1)
    assert windows[1][3] == date(2025, 12, 31)


# ---------------------------------------------------------------------------
# Test 5: optimize_in_sample_returns_best
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optimize_in_sample_returns_best():
    """Given sweep results, selects parameter set with highest Sharpe that meets min_trades."""
    config = WalkForwardConfig(
        min_trades=10,
        optimization_metric="sharpe",
    )

    # Create mock sweep results
    mock_results = pd.DataFrame(
        {
            "symbol": ["TSLA", "TSLA", "TSLA"],
            "or_minutes": [15, 15, 15],
            "target_r": [2.0, 2.0, 2.0],
            "stop_buffer_pct": [0.0, 0.1, 0.2],
            "max_hold_minutes": [60, 60, 60],
            "min_gap_pct": [2.0, 2.0, 2.0],
            "max_range_atr_ratio": [1.0, 1.0, 1.0],
            "total_trades": [15, 20, 25],
            "sharpe_ratio": [1.5, 2.0, 1.8],
            "win_rate": [0.55, 0.60, 0.58],
            "profit_factor": [1.5, 2.0, 1.7],
            "total_return_pct": [5.0, 10.0, 8.0],
            "max_drawdown_pct": [5.0, 4.0, 6.0],
        }
    )

    with patch("argus.backtest.walk_forward.run_sweep", return_value=mock_results):
        best_params, is_metrics = await optimize_in_sample(
            is_start=date(2025, 3, 1),
            is_end=date(2025, 6, 30),
            config=config,
        )

    # Should select stop_buffer_pct=0.1 with highest Sharpe (2.0)
    assert best_params["stop_buffer_pct"] == 0.1
    assert is_metrics["sharpe"] == 2.0
    assert is_metrics["total_trades"] == 20


# ---------------------------------------------------------------------------
# Test 6: optimize_in_sample_min_trades_filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optimize_in_sample_min_trades_filter():
    """Parameter set with highest Sharpe but <20 trades is skipped; next-best is selected."""
    config = WalkForwardConfig(
        min_trades=20,
        optimization_metric="sharpe",
    )

    # Create mock results where best Sharpe has too few trades
    mock_results = pd.DataFrame(
        {
            "symbol": ["TSLA", "TSLA"],
            "or_minutes": [15, 15],
            "target_r": [2.0, 2.0],
            "stop_buffer_pct": [0.0, 0.1],
            "max_hold_minutes": [60, 60],
            "min_gap_pct": [2.0, 2.0],
            "max_range_atr_ratio": [1.0, 1.0],
            "total_trades": [10, 25],  # First has too few trades
            "sharpe_ratio": [2.5, 1.8],  # First has best Sharpe but too few trades
            "win_rate": [0.70, 0.58],
            "profit_factor": [3.0, 1.7],
            "total_return_pct": [15.0, 8.0],
            "max_drawdown_pct": [3.0, 6.0],
        }
    )

    with patch("argus.backtest.walk_forward.run_sweep", return_value=mock_results):
        best_params, is_metrics = await optimize_in_sample(
            is_start=date(2025, 3, 1),
            is_end=date(2025, 6, 30),
            config=config,
        )

    # Should select stop_buffer_pct=0.1 (meets min_trades) not 0.0 (too few trades)
    assert best_params["stop_buffer_pct"] == 0.1
    assert is_metrics["total_trades"] == 25
    assert is_metrics["sharpe"] == 1.8


# ---------------------------------------------------------------------------
# Test 7: optimize_in_sample_no_qualifying
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optimize_in_sample_no_qualifying():
    """All parameter sets below min_trades raises NoQualifyingParamsError."""
    config = WalkForwardConfig(
        min_trades=50,
        optimization_metric="sharpe",
    )

    # Create mock results where all have too few trades
    mock_results = pd.DataFrame(
        {
            "symbol": ["TSLA", "TSLA"],
            "or_minutes": [15, 15],
            "target_r": [2.0, 2.0],
            "stop_buffer_pct": [0.0, 0.1],
            "max_hold_minutes": [60, 60],
            "min_gap_pct": [2.0, 2.0],
            "max_range_atr_ratio": [1.0, 1.0],
            "total_trades": [10, 25],  # Both below min_trades=50
            "sharpe_ratio": [2.5, 1.8],
            "win_rate": [0.70, 0.58],
            "profit_factor": [3.0, 1.7],
            "total_return_pct": [15.0, 8.0],
            "max_drawdown_pct": [3.0, 6.0],
        }
    )

    with (
        patch("argus.backtest.walk_forward.run_sweep", return_value=mock_results),
        pytest.raises(NoQualifyingParamsError) as exc_info,
    ):
        await optimize_in_sample(
            is_start=date(2025, 3, 1),
            is_end=date(2025, 6, 30),
            config=config,
        )

    assert "min_trades=50" in str(exc_info.value)
    assert "25" in str(exc_info.value)  # Max trades found


# ---------------------------------------------------------------------------
# Test 8: validate_oos_translates_params
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_oos_translates_params():
    """VectorBT param names correctly mapped to production config names."""
    config = WalkForwardConfig(
        data_dir="data/historical/1m",
        initial_cash=100_000.0,
    )

    best_params = {
        "or_minutes": 15,
        "target_r": 2.0,
        "stop_buffer_pct": 0.1,
        "max_hold_minutes": 60,
        "min_gap_pct": 2.0,
        "max_range_atr_ratio": 0.75,
    }

    # Mock BacktestResult
    mock_result = MagicMock()
    mock_result.total_trades = 30
    mock_result.win_rate = 0.55
    mock_result.profit_factor = 1.8
    mock_result.sharpe_ratio = 1.5
    mock_result.final_equity = 105_000.0
    mock_result.max_drawdown_pct = 5.0
    mock_result.avg_r_multiple = 0.3

    mock_harness = AsyncMock()
    mock_harness.run.return_value = mock_result

    with patch(
        "argus.backtest.walk_forward.ReplayHarness", return_value=mock_harness
    ) as mock_class:
        oos_metrics = await validate_out_of_sample(
            oos_start=date(2025, 7, 1),
            oos_end=date(2025, 8, 31),
            best_params=best_params,
            config=config,
        )

    # Verify BacktestConfig was created with correct parameter mapping
    call_args = mock_class.call_args
    backtest_config = call_args[0][0]

    assert backtest_config.config_overrides["orb_breakout.opening_range_minutes"] == 15
    assert backtest_config.config_overrides["orb_breakout.profit_target_r"] == 2.0
    assert backtest_config.config_overrides["orb_breakout.stop_buffer_pct"] == 0.1
    assert backtest_config.config_overrides["orb_breakout.max_hold_minutes"] == 60
    assert backtest_config.config_overrides["orb_breakout.max_range_atr_ratio"] == 0.75
    # min_gap_pct goes to scanner config, converted to decimal
    assert backtest_config.scanner_min_gap_pct == 0.02  # 2.0 / 100

    # Verify metrics extracted correctly
    assert oos_metrics["total_trades"] == 30
    assert oos_metrics["total_pnl"] == 5000.0  # 105k - 100k


# ---------------------------------------------------------------------------
# Test 9: walk_forward_efficiency_calculation
# ---------------------------------------------------------------------------


def test_walk_forward_efficiency_calculation():
    """WFE = OOS Sharpe / IS Sharpe, handle zero IS Sharpe gracefully."""
    # Normal case
    assert compute_wfe(2.0, 1.5) == 0.75

    # Zero IS Sharpe should return 0.0
    assert compute_wfe(0.0, 1.5) == 0.0

    # Negative IS Sharpe should return 0.0
    assert compute_wfe(-1.0, 0.5) == 0.0

    # Both positive
    assert compute_wfe(1.0, 0.5) == 0.5

    # OOS can be negative (but WFE will be negative)
    assert compute_wfe(2.0, -1.0) == -0.5


# ---------------------------------------------------------------------------
# Test 10: parameter_stability_all_same
# ---------------------------------------------------------------------------


def test_parameter_stability_all_same():
    """All windows choose same params → stability = 1.0."""
    windows = [
        WindowResult(
            window_number=i,
            is_start=date(2025, 1, 1),
            is_end=date(2025, 4, 30),
            oos_start=date(2025, 5, 1),
            oos_end=date(2025, 6, 30),
            best_params={"or_minutes": 15, "target_r": 2.0, "stop_buffer_pct": 0.1},
            is_total_trades=50,
            is_win_rate=0.55,
            is_profit_factor=1.8,
            is_sharpe=2.0,
            is_total_pnl=5000.0,
            is_max_drawdown=5.0,
            oos_total_trades=20,
            oos_win_rate=0.50,
            oos_profit_factor=1.5,
            oos_sharpe=1.5,
            oos_total_pnl=2000.0,
            oos_max_drawdown=4.0,
            wfe_sharpe=0.75,
            wfe_pnl=0.4,
        )
        for i in range(4)
    ]

    stability = compute_parameter_stability(windows)

    assert stability["or_minutes"]["stability"] == 1.0
    assert stability["or_minutes"]["mode"] == 15
    assert stability["target_r"]["stability"] == 1.0
    assert stability["stop_buffer_pct"]["stability"] == 1.0


# ---------------------------------------------------------------------------
# Test 11: parameter_stability_all_different
# ---------------------------------------------------------------------------


def test_parameter_stability_all_different():
    """Each window chooses different params → low stability score."""
    windows = []
    or_values = [5, 10, 15, 20]

    for i, or_min in enumerate(or_values):
        windows.append(
            WindowResult(
                window_number=i + 1,
                is_start=date(2025, 1, 1),
                is_end=date(2025, 4, 30),
                oos_start=date(2025, 5, 1),
                oos_end=date(2025, 6, 30),
                best_params={"or_minutes": or_min, "target_r": 2.0},
                is_total_trades=50,
                is_win_rate=0.55,
                is_profit_factor=1.8,
                is_sharpe=2.0,
                is_total_pnl=5000.0,
                is_max_drawdown=5.0,
                oos_total_trades=20,
                oos_win_rate=0.50,
                oos_profit_factor=1.5,
                oos_sharpe=1.5,
                oos_total_pnl=2000.0,
                oos_max_drawdown=4.0,
                wfe_sharpe=0.75,
                wfe_pnl=0.4,
            )
        )

    stability = compute_parameter_stability(windows)

    # or_minutes has all different values → stability = 0.25 (1/4)
    assert stability["or_minutes"]["stability"] == 0.25

    # target_r is same for all → stability = 1.0
    assert stability["target_r"]["stability"] == 1.0


# ---------------------------------------------------------------------------
# Test 12: save_and_load_results
# ---------------------------------------------------------------------------


def test_save_and_load_results():
    """Save to JSON/CSV, reload, verify round-trip fidelity."""
    config = WalkForwardConfig(
        in_sample_months=4,
        out_of_sample_months=2,
        step_months=2,
        min_trades=20,
        data_dir="data/historical/1m",
    )

    windows = [
        WindowResult(
            window_number=1,
            is_start=date(2025, 3, 1),
            is_end=date(2025, 6, 30),
            oos_start=date(2025, 7, 1),
            oos_end=date(2025, 8, 31),
            best_params={"or_minutes": 15, "target_r": 2.0, "stop_buffer_pct": 0.1},
            is_total_trades=50,
            is_win_rate=0.55,
            is_profit_factor=1.8,
            is_sharpe=2.0,
            is_total_pnl=5000.0,
            is_max_drawdown=5.0,
            oos_total_trades=20,
            oos_win_rate=0.50,
            oos_profit_factor=1.5,
            oos_sharpe=1.5,
            oos_total_pnl=2000.0,
            oos_max_drawdown=4.0,
            wfe_sharpe=0.75,
            wfe_pnl=0.4,
        ),
        WindowResult(
            window_number=2,
            is_start=date(2025, 5, 1),
            is_end=date(2025, 8, 31),
            oos_start=date(2025, 9, 1),
            oos_end=date(2025, 10, 31),
            best_params={"or_minutes": 10, "target_r": 2.5, "stop_buffer_pct": 0.2},
            is_total_trades=60,
            is_win_rate=0.60,
            is_profit_factor=2.0,
            is_sharpe=2.5,
            is_total_pnl=8000.0,
            is_max_drawdown=4.0,
            oos_total_trades=25,
            oos_win_rate=0.52,
            oos_profit_factor=1.6,
            oos_sharpe=1.8,
            oos_total_pnl=3000.0,
            oos_max_drawdown=3.5,
            wfe_sharpe=0.72,
            wfe_pnl=0.375,
        ),
    ]

    from datetime import UTC, datetime

    run_started = datetime(2026, 2, 16, 10, 0, 0, tzinfo=UTC)
    run_completed = datetime(2026, 2, 16, 10, 5, 30, tzinfo=UTC)

    result = WalkForwardResult(
        config=config,
        windows=windows,
        avg_wfe_sharpe=0.735,
        avg_wfe_pnl=0.3875,
        parameter_stability={
            "or_minutes": {"values": [15, 10], "mode": 15, "stability": 0.5},
            "target_r": {"values": [2.0, 2.5], "mode": 2.0, "stability": 0.5},
        },
        total_oos_trades=45,
        overall_oos_sharpe=1.65,
        overall_oos_pnl=5000.0,
        run_started=run_started,
        run_completed=run_completed,
        run_duration_seconds=330.0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save
        save_walk_forward_results(result, tmpdir)

        # Verify files created
        assert (Path(tmpdir) / "walk_forward_summary.json").exists()
        assert (Path(tmpdir) / "walk_forward_windows.csv").exists()
        assert (Path(tmpdir) / "walk_forward_params.csv").exists()

        # Load
        loaded = load_walk_forward_results(tmpdir)

    assert loaded is not None

    # Verify aggregates
    assert loaded.avg_wfe_sharpe == result.avg_wfe_sharpe
    assert loaded.avg_wfe_pnl == result.avg_wfe_pnl
    assert loaded.total_oos_trades == result.total_oos_trades
    assert loaded.overall_oos_sharpe == result.overall_oos_sharpe
    assert loaded.overall_oos_pnl == result.overall_oos_pnl

    # Verify config
    assert loaded.config.in_sample_months == config.in_sample_months
    assert loaded.config.out_of_sample_months == config.out_of_sample_months
    assert loaded.config.min_trades == config.min_trades

    # Verify windows
    assert len(loaded.windows) == 2
    assert loaded.windows[0].window_number == 1
    assert loaded.windows[0].is_start == date(2025, 3, 1)
    assert loaded.windows[0].oos_total_trades == 20
    assert loaded.windows[0].wfe_sharpe == 0.75

    # Verify best_params loaded
    assert loaded.windows[0].best_params["or_minutes"] == 15
    assert loaded.windows[1].best_params["target_r"] == 2.5


# ---------------------------------------------------------------------------
# Test 13: cross_validate_vectorbt_ge_replay (DEF-009)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_validate_vectorbt_ge_replay():
    """VectorBT trade count >= Replay Harness trade count for same params."""
    from argus.backtest.walk_forward import cross_validate_single_symbol

    # Mock VectorBT to return more trades than Replay Harness
    mock_vbt_results = pd.DataFrame(
        {
            "symbol": ["TSLA"],
            "total_trades": [50],
            "total_return_pct": [10.0],
            "sharpe_ratio": [1.5],
            "win_rate": [0.55],
            "profit_factor": [1.8],
        }
    )

    # Mock Replay Harness result
    mock_replay_result = MagicMock()
    mock_replay_result.total_trades = 30  # Fewer than VectorBT
    mock_replay_result.win_rate = 0.50
    mock_replay_result.profit_factor = 1.5
    mock_replay_result.sharpe_ratio = 1.2
    mock_replay_result.final_equity = 103_000.0
    mock_replay_result.max_drawdown_pct = 4.0
    mock_replay_result.avg_r_multiple = 0.25

    mock_harness = AsyncMock()
    mock_harness.run.return_value = mock_replay_result

    # Params must include all required keys
    params = {
        "or_minutes": 15,
        "target_r": 2.0,
        "stop_buffer_pct": 0.0,
        "max_hold_minutes": 60,
        "min_gap_pct": 2.0,
        "max_range_atr_ratio": 999.0,
    }

    with (
        patch("argus.backtest.walk_forward.run_sweep", return_value=mock_vbt_results),
        patch("argus.backtest.walk_forward.ReplayHarness", return_value=mock_harness),
    ):
        result = await cross_validate_single_symbol(
            symbol="TSLA",
            start=date(2025, 6, 1),
            end=date(2025, 12, 31),
            params=params,
        )

    assert result["vectorbt_trades"] == 50
    assert result["replay_trades"] == 30
    assert result["ratio"] > 1.0
    assert result["assessment"] == "PASS"


@pytest.mark.asyncio
async def test_cross_validate_vectorbt_lt_replay_fails():
    """If VectorBT has fewer trades than Replay, assessment is FAIL."""
    from argus.backtest.walk_forward import cross_validate_single_symbol

    # Mock VectorBT to return FEWER trades than Replay Harness (unexpected)
    mock_vbt_results = pd.DataFrame(
        {
            "symbol": ["TSLA"],
            "total_trades": [20],
            "total_return_pct": [5.0],
            "sharpe_ratio": [1.0],
            "win_rate": [0.50],
            "profit_factor": [1.2],
        }
    )

    # Mock Replay Harness result with more trades
    mock_replay_result = MagicMock()
    mock_replay_result.total_trades = 40  # More than VectorBT - unexpected!
    mock_replay_result.win_rate = 0.55
    mock_replay_result.profit_factor = 1.8
    mock_replay_result.sharpe_ratio = 1.5
    mock_replay_result.final_equity = 105_000.0
    mock_replay_result.max_drawdown_pct = 5.0
    mock_replay_result.avg_r_multiple = 0.30

    mock_harness = AsyncMock()
    mock_harness.run.return_value = mock_replay_result

    # Params must include all required keys
    params = {
        "or_minutes": 15,
        "target_r": 2.0,
        "stop_buffer_pct": 0.0,
        "max_hold_minutes": 60,
        "min_gap_pct": 2.0,
        "max_range_atr_ratio": 999.0,
    }

    with (
        patch("argus.backtest.walk_forward.run_sweep", return_value=mock_vbt_results),
        patch("argus.backtest.walk_forward.ReplayHarness", return_value=mock_harness),
    ):
        result = await cross_validate_single_symbol(
            symbol="TSLA",
            start=date(2025, 6, 1),
            end=date(2025, 12, 31),
            params=params,
        )

    assert result["vectorbt_trades"] == 20
    assert result["replay_trades"] == 40
    assert result["ratio"] < 1.0
    assert result["assessment"] == "FAIL"


# ---------------------------------------------------------------------------
# Test 15: cross_validate_missing_params_raises (DEC-074 fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_validate_missing_params_raises():
    """Cross-validation raises KeyError if required params are missing."""
    from argus.backtest.walk_forward import cross_validate_single_symbol

    # Incomplete params dict - missing max_range_atr_ratio
    incomplete_params = {
        "or_minutes": 15,
        "target_r": 2.0,
        # Missing: stop_buffer_pct, max_hold_minutes, min_gap_pct, max_range_atr_ratio
    }

    with pytest.raises(KeyError, match="Missing required parameters"):
        await cross_validate_single_symbol(
            symbol="TSLA",
            start=date(2025, 6, 1),
            end=date(2025, 12, 31),
            params=incomplete_params,
        )


# ---------------------------------------------------------------------------
# Test 16: optimize_in_sample_scalp_returns_best (Sprint 18)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optimize_in_sample_scalp_returns_best():
    """Scalp strategy in-sample optimization selects params with highest Sharpe."""
    config = WalkForwardConfig(
        min_trades=10,
        optimization_metric="sharpe",
        strategy="orb_scalp",
    )

    # Create mock scalp sweep results - scalp only uses scalp_target_r and max_hold_bars
    mock_results = pd.DataFrame(
        {
            "symbol": ["TSLA", "TSLA", "TSLA"],
            "scalp_target_r": [0.2, 0.3, 0.4],
            "max_hold_bars": [2, 2, 2],
            "total_trades": [40, 50, 45],
            "sharpe_ratio": [1.2, 1.8, 1.5],
            "win_rate": [0.60, 0.65, 0.62],
            "profit_factor": [1.4, 1.9, 1.6],
            "total_return_pct": [3.0, 5.0, 4.0],
            "max_drawdown_pct": [2.0, 1.5, 2.5],
        }
    )

    with patch("argus.backtest.walk_forward.run_scalp_sweep", return_value=mock_results):
        best_params, is_metrics = await optimize_in_sample(
            is_start=date(2025, 3, 1),
            is_end=date(2025, 6, 30),
            config=config,
        )

    # Should select scalp_target_r=0.3 with highest Sharpe (1.8)
    assert best_params["scalp_target_r"] == 0.3
    assert best_params["max_hold_bars"] == 2
    assert is_metrics["sharpe"] == 1.8
    assert is_metrics["total_trades"] == 50


# ---------------------------------------------------------------------------
# Test 17: validate_oos_scalp_translates_params (Sprint 18)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_oos_scalp_translates_params():
    """Scalp VectorBT params correctly mapped to production config names."""
    config = WalkForwardConfig(
        data_dir="data/historical/1m",
        initial_cash=100_000.0,
        strategy="orb_scalp",
    )

    # Scalp params are minimal: only scalp_target_r and max_hold_bars
    best_params = {
        "scalp_target_r": 0.3,
        "max_hold_bars": 2,
    }

    # Mock BacktestResult
    mock_result = MagicMock()
    mock_result.total_trades = 60
    mock_result.win_rate = 0.65
    mock_result.profit_factor = 1.5
    mock_result.sharpe_ratio = 1.2
    mock_result.final_equity = 102_000.0
    mock_result.max_drawdown_pct = 2.0
    mock_result.avg_r_multiple = 0.15

    mock_harness = AsyncMock()
    mock_harness.run.return_value = mock_result

    with patch(
        "argus.backtest.walk_forward.ReplayHarness", return_value=mock_harness
    ) as mock_class:
        oos_metrics = await validate_out_of_sample(
            oos_start=date(2025, 7, 1),
            oos_end=date(2025, 8, 31),
            best_params=best_params,
            config=config,
        )

    # Verify BacktestConfig was created with scalp parameter mapping
    call_args = mock_class.call_args
    backtest_config = call_args[0][0]

    # Scalp translates: max_hold_bars -> max_hold_seconds (1 bar = 60s)
    assert backtest_config.config_overrides["orb_scalp.scalp_target_r"] == 0.3
    assert backtest_config.config_overrides["orb_scalp.max_hold_seconds"] == 120  # 2 bars * 60s
    assert backtest_config.config_overrides["orb_scalp.orb_window_minutes"] == 5  # Fixed default
    # Scalp uses default 2% gap
    assert backtest_config.scanner_min_gap_pct == 0.02

    # Verify metrics extracted correctly
    assert oos_metrics["total_trades"] == 60
    assert oos_metrics["total_pnl"] == 2000.0  # 102k - 100k


# ---------------------------------------------------------------------------
# Test 18: walk_forward_config_scalp_strategy (Sprint 18)
# ---------------------------------------------------------------------------


def test_walk_forward_config_scalp_strategy():
    """WalkForwardConfig accepts strategy='orb_scalp' with scalp-specific grids."""
    config = WalkForwardConfig(
        strategy="orb_scalp",
        scalp_target_r_values=[0.2, 0.3, 0.4],
        max_hold_bars_values=[1, 2, 3],
    )

    assert config.strategy == "orb_scalp"
    assert config.scalp_target_r_values == [0.2, 0.3, 0.4]
    assert config.max_hold_bars_values == [1, 2, 3]
    # Should still have ORB defaults for other params
    assert config.or_minutes_values == [5, 10, 15, 20, 30]  # Full default grid


# ---------------------------------------------------------------------------
# Test 19: evaluate_fixed_params_scalp_dispatches (Sprint 18)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_fixed_params_scalp_dispatches():
    """evaluate_fixed_params_on_is uses scalp sweep for orb_scalp strategy."""
    config = WalkForwardConfig(
        strategy="orb_scalp",
        min_trades=10,
    )

    # Scalp only needs scalp_target_r and max_hold_bars
    fixed_params = {
        "scalp_target_r": 0.3,
        "max_hold_bars": 2,
    }

    mock_results = pd.DataFrame(
        {
            "symbol": ["TSLA"],
            "scalp_target_r": [0.3],
            "max_hold_bars": [2],
            "total_trades": [80],
            "sharpe_ratio": [1.5],
            "win_rate": [0.65],
            "profit_factor": [1.8],
            "total_return_pct": [4.0],
            "max_drawdown_pct": [1.5],
        }
    )

    with patch(
        "argus.backtest.walk_forward.run_scalp_sweep", return_value=mock_results
    ) as mock_sweep:
        metrics = await evaluate_fixed_params_on_is(
            is_start=date(2025, 3, 1),
            is_end=date(2025, 6, 30),
            fixed_params=fixed_params,
            config=config,
        )

    # Verify scalp sweep was called (not orb sweep)
    mock_sweep.assert_called_once()
    assert metrics["total_trades"] == 80
    assert metrics["sharpe"] == 1.5


# ---------------------------------------------------------------------------
# Test 20: replay_harness_creates_scalp_strategy (Sprint 18)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_harness_creates_scalp_strategy():
    """ReplayHarness is created with StrategyType.ORB_SCALP for scalp validation."""
    from argus.backtest.config import StrategyType

    config = WalkForwardConfig(
        data_dir="data/historical/1m",
        initial_cash=100_000.0,
        strategy="orb_scalp",
    )

    # Scalp params
    best_params = {
        "scalp_target_r": 0.3,
        "max_hold_bars": 2,
    }

    # Mock BacktestResult
    mock_result = MagicMock()
    mock_result.total_trades = 60
    mock_result.win_rate = 0.60
    mock_result.profit_factor = 1.4
    mock_result.sharpe_ratio = 1.0
    mock_result.final_equity = 101_500.0
    mock_result.max_drawdown_pct = 1.5
    mock_result.avg_r_multiple = 0.10

    mock_harness = AsyncMock()
    mock_harness.run.return_value = mock_result

    with patch(
        "argus.backtest.walk_forward.ReplayHarness", return_value=mock_harness
    ) as mock_class:
        await validate_out_of_sample(
            oos_start=date(2025, 7, 1),
            oos_end=date(2025, 8, 31),
            best_params=best_params,
            config=config,
        )

    # Verify BacktestConfig has correct strategy type
    call_args = mock_class.call_args
    backtest_config = call_args[0][0]

    assert backtest_config.strategy_type == StrategyType.ORB_SCALP
    assert backtest_config.strategy_id == "strat_orb_scalp"

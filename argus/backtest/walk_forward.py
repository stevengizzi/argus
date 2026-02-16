"""Walk-Forward Analysis Engine.

Walk-forward analysis is the overfitting defense. It splits historical data into
rolling windows, optimizes parameters on the in-sample (IS) portion, then tests
those parameters on the out-of-sample (OOS) portion.

Key metric: Walk-Forward Efficiency (WFE) = OOS Sharpe / IS Sharpe
Per DEC-047: WFE > 0.3 required, values above 0.5 suggest good generalization.

Usage:
    python -m argus.backtest.walk_forward \
        --data-dir data/historical/1m \
        --is-months 4 --oos-months 2 --step-months 2 \
        --min-trades 20 \
        --output-dir data/backtest_runs/walk_forward
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mode
from typing import Any

import pandas as pd
from dateutil.relativedelta import relativedelta

from argus.backtest.config import BacktestConfig
from argus.backtest.replay_harness import ReplayHarness
from argus.backtest.vectorbt_orb import SweepConfig, run_sweep

logger = logging.getLogger(__name__)


class NoQualifyingParamsError(Exception):
    """Raised when no parameter set meets the minimum trades threshold."""

    pass


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward analysis."""

    # Window sizing
    in_sample_months: int = 4
    out_of_sample_months: int = 2
    step_months: int = 2  # How far to slide the window each iteration

    # Data
    data_dir: str = "data/historical/1m"
    symbols: list[str] | None = None  # None = auto-detect from data_dir

    # Optimization
    optimization_metric: str = "sharpe"  # What to maximize in IS
    min_trades: int = 20  # Minimum trades to qualify (DEC-066)

    # Parameter grid (same as VectorBT sweep)
    or_minutes_values: list[int] = field(
        default_factory=lambda: [5, 10, 15, 20, 30]
    )
    target_r_values: list[float] = field(
        default_factory=lambda: [1.0, 1.5, 2.0, 2.5, 3.0]
    )
    stop_buffer_values: list[float] = field(
        default_factory=lambda: [0.0, 0.1, 0.2, 0.5]
    )
    hold_minutes_values: list[int] = field(
        default_factory=lambda: [15, 30, 45, 60, 90, 120]
    )
    min_gap_values: list[float] = field(
        default_factory=lambda: [1.0, 1.5, 2.0, 3.0, 5.0]
    )
    max_range_atr_values: list[float] = field(
        default_factory=lambda: [0.3, 0.5, 0.75, 1.0, 1.5, 999.0]
    )

    # Output
    output_dir: str = "data/backtest_runs/walk_forward"

    # Replay Harness settings (for OOS validation)
    initial_cash: float = 100_000.0
    slippage_per_share: float = 0.01


@dataclass
class WindowResult:
    """Results for a single walk-forward window."""

    window_number: int

    # Date ranges
    is_start: date
    is_end: date
    oos_start: date
    oos_end: date

    # Best IS parameters (from VectorBT sweep)
    best_params: dict[str, Any]

    # IS metrics (from VectorBT sweep with best params)
    is_total_trades: int
    is_win_rate: float
    is_profit_factor: float
    is_sharpe: float
    is_total_pnl: float
    is_max_drawdown: float

    # OOS metrics (from Replay Harness with best params)
    oos_total_trades: int
    oos_win_rate: float
    oos_profit_factor: float
    oos_sharpe: float
    oos_total_pnl: float
    oos_max_drawdown: float

    # Walk-forward efficiency
    wfe_sharpe: float  # oos_sharpe / is_sharpe (handle div-by-zero)
    wfe_pnl: float  # oos_total_pnl / is_total_pnl (handle div-by-zero)

    # Error tracking
    error: str | None = None  # Set if window processing failed


@dataclass
class WalkForwardResult:
    """Aggregate results across all walk-forward windows."""

    config: WalkForwardConfig
    windows: list[WindowResult]

    # Aggregate metrics
    avg_wfe_sharpe: float
    avg_wfe_pnl: float
    parameter_stability: dict[str, dict[str, Any]]  # How much best params vary

    # Overall assessment
    total_oos_trades: int
    overall_oos_sharpe: float
    overall_oos_pnl: float

    # Timestamps
    run_started: datetime
    run_completed: datetime
    run_duration_seconds: float


def compute_windows(
    data_start: date,
    data_end: date,
    config: WalkForwardConfig,
) -> list[tuple[date, date, date, date]]:
    """Compute (is_start, is_end, oos_start, oos_end) tuples for each window.

    For 11 months of data (2025-03 to 2026-01) with 4/2/2 config:
    Window 1: IS=Mar-Jun 2025, OOS=Jul-Aug 2025
    Window 2: IS=May-Aug 2025, OOS=Sep-Oct 2025
    Window 3: IS=Jul-Oct 2025, OOS=Nov-Dec 2025
    Window 4: IS=Sep-Dec 2025, OOS=Jan 2026

    Args:
        data_start: First date of available data.
        data_end: Last date of available data.
        config: WalkForwardConfig with window sizing.

    Returns:
        List of (is_start, is_end, oos_start, oos_end) tuples.
        Empty list if data range is too short for even one window.
    """
    windows: list[tuple[date, date, date, date]] = []

    # Start at the beginning of the data
    is_start = data_start

    while True:
        # Compute window boundaries using relativedelta for proper month arithmetic
        is_end = (
            is_start + relativedelta(months=config.in_sample_months) - relativedelta(days=1)
        )
        oos_start = is_end + relativedelta(days=1)
        oos_end = (
            oos_start + relativedelta(months=config.out_of_sample_months) - relativedelta(days=1)
        )

        # Check if OOS end exceeds data range
        if oos_end > data_end:
            break

        windows.append((is_start, is_end, oos_start, oos_end))

        # Slide window by step_months
        is_start = is_start + relativedelta(months=config.step_months)

    return windows


async def optimize_in_sample(
    is_start: date,
    is_end: date,
    config: WalkForwardConfig,
) -> tuple[dict[str, Any], dict[str, float]]:
    """Run VectorBT sweep on IS period. Return (best_params, is_metrics).

    Uses vectorbt_orb.run_sweep() with the IS date range.
    Selects best parameter set by optimization_metric, subject to min_trades floor.

    Args:
        is_start: Start date for in-sample period.
        is_end: End date for in-sample period.
        config: WalkForwardConfig with parameter ranges.

    Returns:
        Tuple of (best_params, is_metrics) where:
        - best_params: dict with keys matching VectorBT parameter names
        - is_metrics: dict with sharpe, win_rate, profit_factor, total_pnl, etc.

    Raises:
        NoQualifyingParamsError: if no parameter set meets min_trades threshold.
    """
    # Build SweepConfig from WalkForwardConfig
    sweep_config = SweepConfig(
        data_dir=Path(config.data_dir),
        symbols=config.symbols or [],
        start_date=is_start,
        end_date=is_end,
        output_dir=Path(config.output_dir) / "is_sweeps",
        or_minutes_list=config.or_minutes_values,
        target_r_list=config.target_r_values,
        stop_buffer_list=config.stop_buffer_values,
        max_hold_list=config.hold_minutes_values,
        min_gap_list=config.min_gap_values,
        max_range_atr_list=config.max_range_atr_values,
    )

    # Run sweep (this is CPU-bound, run in executor to avoid blocking)
    loop = asyncio.get_running_loop()
    results_df = await loop.run_in_executor(None, run_sweep, sweep_config)

    if results_df.empty:
        raise NoQualifyingParamsError("VectorBT sweep produced no results")

    # Aggregate results across symbols for each parameter combination
    param_cols = [
        "or_minutes",
        "target_r",
        "stop_buffer_pct",
        "max_hold_minutes",
        "min_gap_pct",
        "max_range_atr_ratio",
    ]

    aggregated = (
        results_df.groupby(param_cols)
        .agg(
            total_trades=("total_trades", "sum"),
            sharpe_ratio=("sharpe_ratio", "mean"),
            win_rate=("win_rate", "mean"),
            profit_factor=("profit_factor", "mean"),
            total_return_pct=("total_return_pct", "sum"),
            max_drawdown_pct=("max_drawdown_pct", "max"),
        )
        .reset_index()
    )

    # Filter by min_trades threshold
    qualifying = aggregated[aggregated["total_trades"] >= config.min_trades]

    if qualifying.empty:
        max_trades = aggregated["total_trades"].max() if not aggregated.empty else 0
        raise NoQualifyingParamsError(
            f"No parameter set meets min_trades={config.min_trades}. "
            f"Max trades found: {max_trades}"
        )

    # Select best by optimization metric
    if config.optimization_metric == "sharpe":
        metric_col = "sharpe_ratio"
    else:
        metric_col = config.optimization_metric
    best_row = qualifying.loc[qualifying[metric_col].idxmax()]

    best_params = {col: best_row[col] for col in param_cols}

    # Convert total_return_pct (percentage) to dollar P&L for consistent units with OOS
    total_pnl_dollars = float(best_row["total_return_pct"]) * config.initial_cash / 100.0

    is_metrics = {
        "total_trades": int(best_row["total_trades"]),
        "sharpe": float(best_row["sharpe_ratio"]),
        "win_rate": float(best_row["win_rate"]),
        "profit_factor": float(best_row["profit_factor"]),
        "total_pnl": total_pnl_dollars,
        "max_drawdown": float(best_row["max_drawdown_pct"]),
    }

    return best_params, is_metrics


async def validate_out_of_sample(
    oos_start: date,
    oos_end: date,
    best_params: dict[str, Any],
    config: WalkForwardConfig,
) -> dict[str, Any]:
    """Run Replay Harness on OOS period with the IS-optimized parameters.

    This is the high-fidelity validation: actual production code (OrbBreakout strategy,
    Risk Manager, Order Manager, SimulatedBroker) processes the OOS data.

    Translates VectorBT param names to production config:
    - or_minutes → opening_range_minutes
    - target_r → profit_target_r
    - stop_buffer → stop_buffer_pct
    - hold_minutes → max_hold_minutes
    - min_gap → (scanner config)
    - max_range_atr → max_range_atr_ratio

    Args:
        oos_start: Start date for out-of-sample period.
        oos_end: End date for out-of-sample period.
        best_params: Parameters optimized in IS period.
        config: WalkForwardConfig with data paths and settings.

    Returns:
        Dict with: total_trades, win_rate, profit_factor, sharpe, total_pnl,
        max_drawdown, avg_r_multiple.
    """
    # Translate VectorBT param names to production config overrides
    config_overrides = {
        "orb_breakout.opening_range_minutes": int(best_params["or_minutes"]),
        "orb_breakout.profit_target_r": float(best_params["target_r"]),
        "orb_breakout.stop_buffer_pct": float(best_params["stop_buffer_pct"]),
        "orb_breakout.max_hold_minutes": int(best_params["max_hold_minutes"]),
        "orb_breakout.max_range_atr_ratio": float(best_params["max_range_atr_ratio"]),
    }

    # Build BacktestConfig
    backtest_config = BacktestConfig(
        data_dir=Path(config.data_dir),
        output_dir=Path(config.output_dir) / "oos_runs",
        symbols=config.symbols,  # Pass symbols filter from WalkForwardConfig
        start_date=oos_start,
        end_date=oos_end,
        initial_cash=config.initial_cash,
        slippage_per_share=config.slippage_per_share,
        scanner_min_gap_pct=float(best_params["min_gap_pct"]) / 100.0,  # Convert to decimal
        config_overrides=config_overrides,
    )

    # Run Replay Harness
    harness = ReplayHarness(backtest_config)
    result = await harness.run()

    return {
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor if result.profit_factor != float("inf") else 0.0,
        "sharpe": result.sharpe_ratio,
        "total_pnl": result.final_equity - config.initial_cash,
        "max_drawdown": result.max_drawdown_pct,
        "avg_r_multiple": result.avg_r_multiple,
    }


def compute_wfe(is_value: float, oos_value: float) -> float:
    """Compute walk-forward efficiency (OOS / IS).

    Handles division by zero gracefully.

    Args:
        is_value: In-sample metric value.
        oos_value: Out-of-sample metric value.

    Returns:
        WFE ratio. Returns 0.0 if IS value is zero or negative.
    """
    if is_value <= 0:
        return 0.0
    return oos_value / is_value


def compute_parameter_stability(windows: list[WindowResult]) -> dict[str, dict[str, Any]]:
    """Analyze how much the best parameters vary across windows.

    For each parameter, compute:
    - values_chosen: list of values selected in each window
    - mode: most frequently chosen value
    - stability_score: fraction of windows that chose the mode

    High stability (e.g., or_minutes=15 in 4/4 windows) suggests the parameter
    is robust. Low stability (different value each window) suggests sensitivity
    or overfitting.

    Args:
        windows: List of WindowResult objects.

    Returns:
        Dict of {param_name: {"values": [...], "mode": val, "stability": float}}
    """
    if not windows:
        return {}

    # Filter out windows with errors or no params
    valid_windows = [w for w in windows if w.best_params and w.error is None]
    if not valid_windows:
        return {}

    # Get param names from first window
    param_names = list(valid_windows[0].best_params.keys())
    stability: dict[str, dict[str, Any]] = {}

    for param in param_names:
        values = [
            w.best_params.get(param)
            for w in valid_windows
            if w.best_params.get(param) is not None
        ]

        if not values:
            stability[param] = {"values": [], "mode": None, "stability": 0.0}
            continue

        # Find mode (most common value)
        # Python 3.8+ statistics.mode() no longer raises StatisticsError for multimodal data
        mode_value = mode(values)

        # Stability = fraction of windows that chose the mode
        mode_count = sum(1 for v in values if v == mode_value)
        stability_score = mode_count / len(values)

        stability[param] = {
            "values": values,
            "mode": mode_value,
            "stability": stability_score,
        }

    return stability


async def run_walk_forward(config: WalkForwardConfig) -> WalkForwardResult:
    """Execute the full walk-forward analysis.

    For each window:
    1. Run VectorBT sweep on IS period
    2. Select best parameters (by optimization_metric, min_trades floor)
    3. Run Replay Harness on OOS period with those parameters
    4. Compute WFE metrics

    After all windows:
    5. Compute aggregate metrics
    6. Assess parameter stability
    7. Save results to output_dir

    Args:
        config: WalkForwardConfig with all settings.

    Returns:
        WalkForwardResult with all window results and aggregates.
    """
    run_started = datetime.now(UTC)

    # Create output directory
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect data range from files
    data_dir = Path(config.data_dir)
    data_start, data_end = _detect_data_range(data_dir)

    logger.info(
        "Walk-forward analysis: data=%s to %s, IS=%d months, OOS=%d months, step=%d months",
        data_start,
        data_end,
        config.in_sample_months,
        config.out_of_sample_months,
        config.step_months,
    )

    # Compute windows
    windows_spec = compute_windows(data_start, data_end, config)

    if not windows_spec:
        logger.error("Data range too short for even one walk-forward window")
        return _empty_walk_forward_result(config, run_started)

    logger.info("Generated %d walk-forward windows", len(windows_spec))

    # Process each window
    window_results: list[WindowResult] = []

    for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_spec, 1):
        logger.info(
            "Window %d/%d: IS=%s to %s, OOS=%s to %s",
            i,
            len(windows_spec),
            is_start,
            is_end,
            oos_start,
            oos_end,
        )

        try:
            # 1. Optimize on IS
            best_params, is_metrics = await optimize_in_sample(is_start, is_end, config)
            logger.info("Window %d IS best params: %s", i, best_params)

            # 2. Validate on OOS
            oos_metrics = await validate_out_of_sample(oos_start, oos_end, best_params, config)
            logger.info(
                "Window %d OOS: trades=%d, sharpe=%.2f, pnl=$%.2f",
                i,
                oos_metrics["total_trades"],
                oos_metrics["sharpe"],
                oos_metrics["total_pnl"],
            )

            # 3. Compute WFE
            wfe_sharpe = compute_wfe(is_metrics["sharpe"], oos_metrics["sharpe"])
            wfe_pnl = compute_wfe(is_metrics["total_pnl"], oos_metrics["total_pnl"])

            window_result = WindowResult(
                window_number=i,
                is_start=is_start,
                is_end=is_end,
                oos_start=oos_start,
                oos_end=oos_end,
                best_params=best_params,
                is_total_trades=is_metrics["total_trades"],
                is_win_rate=is_metrics["win_rate"],
                is_profit_factor=is_metrics["profit_factor"],
                is_sharpe=is_metrics["sharpe"],
                is_total_pnl=is_metrics["total_pnl"],
                is_max_drawdown=is_metrics["max_drawdown"],
                oos_total_trades=oos_metrics["total_trades"],
                oos_win_rate=oos_metrics["win_rate"],
                oos_profit_factor=oos_metrics["profit_factor"],
                oos_sharpe=oos_metrics["sharpe"],
                oos_total_pnl=oos_metrics["total_pnl"],
                oos_max_drawdown=oos_metrics["max_drawdown"],
                wfe_sharpe=wfe_sharpe,
                wfe_pnl=wfe_pnl,
            )

        except NoQualifyingParamsError as e:
            logger.warning("Window %d: %s", i, str(e))
            window_result = _error_window_result(i, is_start, is_end, oos_start, oos_end, str(e))

        except Exception as e:
            logger.exception("Window %d failed: %s", i, str(e))
            window_result = _error_window_result(i, is_start, is_end, oos_start, oos_end, str(e))

        window_results.append(window_result)

    # Compute aggregate metrics
    valid_windows = [w for w in window_results if w.error is None]

    if valid_windows:
        avg_wfe_sharpe = sum(w.wfe_sharpe for w in valid_windows) / len(valid_windows)
        avg_wfe_pnl = sum(w.wfe_pnl for w in valid_windows) / len(valid_windows)
        total_oos_trades = sum(w.oos_total_trades for w in valid_windows)
        overall_oos_pnl = sum(w.oos_total_pnl for w in valid_windows)

        # Compute overall OOS Sharpe from concatenated returns (approximation)
        oos_sharpes = [w.oos_sharpe for w in valid_windows if w.oos_total_trades > 0]
        overall_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0.0
    else:
        avg_wfe_sharpe = 0.0
        avg_wfe_pnl = 0.0
        total_oos_trades = 0
        overall_oos_pnl = 0.0
        overall_oos_sharpe = 0.0

    # Compute parameter stability
    parameter_stability = compute_parameter_stability(window_results)

    run_completed = datetime.now(UTC)
    run_duration = (run_completed - run_started).total_seconds()

    result = WalkForwardResult(
        config=config,
        windows=window_results,
        avg_wfe_sharpe=avg_wfe_sharpe,
        avg_wfe_pnl=avg_wfe_pnl,
        parameter_stability=parameter_stability,
        total_oos_trades=total_oos_trades,
        overall_oos_sharpe=overall_oos_sharpe,
        overall_oos_pnl=overall_oos_pnl,
        run_started=run_started,
        run_completed=run_completed,
        run_duration_seconds=run_duration,
    )

    # Save results
    save_walk_forward_results(result, config.output_dir)

    logger.info(
        "Walk-forward complete: %d windows, avg WFE=%.2f, total OOS trades=%d, total OOS P&L=$%.2f",
        len(window_results),
        avg_wfe_sharpe,
        total_oos_trades,
        overall_oos_pnl,
    )

    return result


def _detect_data_range(data_dir: Path) -> tuple[date, date]:
    """Detect the date range of available data.

    Optimized: reads only timestamp column and only first/last files per symbol
    (sorted alphabetically, which corresponds to date order for our naming convention).

    Args:
        data_dir: Path to the historical data directory.

    Returns:
        Tuple of (start_date, end_date).
    """
    min_date: date | None = None
    max_date: date | None = None

    for symbol_dir in data_dir.iterdir():
        if not symbol_dir.is_dir():
            continue

        # Get sorted list of parquet files
        parquet_files = sorted(symbol_dir.glob("*.parquet"))
        if not parquet_files:
            continue

        # Only read first and last file (covers date range)
        files_to_read = [parquet_files[0]]
        if len(parquet_files) > 1:
            files_to_read.append(parquet_files[-1])

        for parquet_file in files_to_read:
            try:
                # Read only timestamp column (column pushdown)
                df = pd.read_parquet(parquet_file, columns=["timestamp"])
                if df.empty:
                    continue

                # Convert to dates
                if df["timestamp"].dt.tz is None:
                    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")

                file_min = df["timestamp"].min().date()
                file_max = df["timestamp"].max().date()

                if min_date is None or file_min < min_date:
                    min_date = file_min
                if max_date is None or file_max > max_date:
                    max_date = file_max

            except Exception as e:
                logger.warning("Error reading %s: %s", parquet_file, e)

    if min_date is None or max_date is None:
        raise ValueError(f"No data found in {data_dir}")

    return min_date, max_date


def _empty_walk_forward_result(
    config: WalkForwardConfig,
    run_started: datetime,
) -> WalkForwardResult:
    """Create an empty result when no windows can be processed."""
    run_completed = datetime.now(UTC)
    return WalkForwardResult(
        config=config,
        windows=[],
        avg_wfe_sharpe=0.0,
        avg_wfe_pnl=0.0,
        parameter_stability={},
        total_oos_trades=0,
        overall_oos_sharpe=0.0,
        overall_oos_pnl=0.0,
        run_started=run_started,
        run_completed=run_completed,
        run_duration_seconds=(run_completed - run_started).total_seconds(),
    )


def _error_window_result(
    window_number: int,
    is_start: date,
    is_end: date,
    oos_start: date,
    oos_end: date,
    error: str,
) -> WindowResult:
    """Create a WindowResult with error state."""
    return WindowResult(
        window_number=window_number,
        is_start=is_start,
        is_end=is_end,
        oos_start=oos_start,
        oos_end=oos_end,
        best_params={},
        is_total_trades=0,
        is_win_rate=0.0,
        is_profit_factor=0.0,
        is_sharpe=0.0,
        is_total_pnl=0.0,
        is_max_drawdown=0.0,
        oos_total_trades=0,
        oos_win_rate=0.0,
        oos_profit_factor=0.0,
        oos_sharpe=0.0,
        oos_total_pnl=0.0,
        oos_max_drawdown=0.0,
        wfe_sharpe=0.0,
        wfe_pnl=0.0,
        error=error,
    )


def save_walk_forward_results(result: WalkForwardResult, output_dir: str) -> str:
    """Save results as JSON + per-window detail CSVs.

    Files created:
    - walk_forward_summary.json: WalkForwardResult as JSON
    - walk_forward_windows.csv: One row per window with all metrics
    - walk_forward_params.csv: Best params per window for stability analysis

    Args:
        result: WalkForwardResult to save.
        output_dir: Directory to save files.

    Returns:
        Path to summary JSON file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save summary JSON
    summary_path = output_path / "walk_forward_summary.json"
    summary_dict = {
        "run_started": result.run_started.isoformat(),
        "run_completed": result.run_completed.isoformat(),
        "run_duration_seconds": result.run_duration_seconds,
        "config": {
            "in_sample_months": result.config.in_sample_months,
            "out_of_sample_months": result.config.out_of_sample_months,
            "step_months": result.config.step_months,
            "min_trades": result.config.min_trades,
            "optimization_metric": result.config.optimization_metric,
            "data_dir": result.config.data_dir,
        },
        "aggregates": {
            "avg_wfe_sharpe": result.avg_wfe_sharpe,
            "avg_wfe_pnl": result.avg_wfe_pnl,
            "total_oos_trades": result.total_oos_trades,
            "overall_oos_sharpe": result.overall_oos_sharpe,
            "overall_oos_pnl": result.overall_oos_pnl,
        },
        "parameter_stability": result.parameter_stability,
        "window_count": len(result.windows),
        "valid_window_count": len([w for w in result.windows if w.error is None]),
    }

    with open(summary_path, "w") as f:
        json.dump(summary_dict, f, indent=2)

    # Save windows CSV
    windows_csv_path = output_path / "walk_forward_windows.csv"
    window_rows = []
    for w in result.windows:
        row = {
            "window_number": w.window_number,
            "is_start": w.is_start.isoformat(),
            "is_end": w.is_end.isoformat(),
            "oos_start": w.oos_start.isoformat(),
            "oos_end": w.oos_end.isoformat(),
            "is_total_trades": w.is_total_trades,
            "is_win_rate": w.is_win_rate,
            "is_profit_factor": w.is_profit_factor,
            "is_sharpe": w.is_sharpe,
            "is_total_pnl": w.is_total_pnl,
            "is_max_drawdown": w.is_max_drawdown,
            "oos_total_trades": w.oos_total_trades,
            "oos_win_rate": w.oos_win_rate,
            "oos_profit_factor": w.oos_profit_factor,
            "oos_sharpe": w.oos_sharpe,
            "oos_total_pnl": w.oos_total_pnl,
            "oos_max_drawdown": w.oos_max_drawdown,
            "wfe_sharpe": w.wfe_sharpe,
            "wfe_pnl": w.wfe_pnl,
            "error": w.error or "",
        }
        window_rows.append(row)

    windows_df = pd.DataFrame(window_rows)
    windows_df.to_csv(windows_csv_path, index=False)

    # Save params CSV
    params_csv_path = output_path / "walk_forward_params.csv"
    params_rows = []
    for w in result.windows:
        if w.best_params:
            row = {"window_number": w.window_number, **w.best_params}
            params_rows.append(row)

    if params_rows:
        params_df = pd.DataFrame(params_rows)
        params_df.to_csv(params_csv_path, index=False)

    logger.info("Saved walk-forward results to %s", output_path)
    return str(summary_path)


def load_walk_forward_results(output_dir: str) -> WalkForwardResult | None:
    """Load walk-forward results from JSON/CSV files.

    Args:
        output_dir: Directory containing saved results.

    Returns:
        WalkForwardResult or None if files don't exist.
    """
    output_path = Path(output_dir)
    summary_path = output_path / "walk_forward_summary.json"

    if not summary_path.exists():
        return None

    # Load summary JSON
    with open(summary_path) as f:
        summary = json.load(f)

    # Load windows CSV
    windows_csv_path = output_path / "walk_forward_windows.csv"
    if not windows_csv_path.exists():
        return None

    windows_df = pd.read_csv(windows_csv_path)

    # Load params CSV
    params_csv_path = output_path / "walk_forward_params.csv"
    params_by_window: dict[int, dict[str, Any]] = {}
    if params_csv_path.exists():
        params_df = pd.read_csv(params_csv_path)
        for _, row in params_df.iterrows():
            window_num = int(row["window_number"])
            params = {k: v for k, v in row.items() if k != "window_number"}
            params_by_window[window_num] = params

    # Reconstruct WindowResult objects
    windows: list[WindowResult] = []
    for _, row in windows_df.iterrows():
        w = WindowResult(
            window_number=int(row["window_number"]),
            is_start=date.fromisoformat(row["is_start"]),
            is_end=date.fromisoformat(row["is_end"]),
            oos_start=date.fromisoformat(row["oos_start"]),
            oos_end=date.fromisoformat(row["oos_end"]),
            best_params=params_by_window.get(int(row["window_number"]), {}),
            is_total_trades=int(row["is_total_trades"]),
            is_win_rate=float(row["is_win_rate"]),
            is_profit_factor=float(row["is_profit_factor"]),
            is_sharpe=float(row["is_sharpe"]),
            is_total_pnl=float(row["is_total_pnl"]),
            is_max_drawdown=float(row["is_max_drawdown"]),
            oos_total_trades=int(row["oos_total_trades"]),
            oos_win_rate=float(row["oos_win_rate"]),
            oos_profit_factor=float(row["oos_profit_factor"]),
            oos_sharpe=float(row["oos_sharpe"]),
            oos_total_pnl=float(row["oos_total_pnl"]),
            oos_max_drawdown=float(row["oos_max_drawdown"]),
            wfe_sharpe=float(row["wfe_sharpe"]),
            wfe_pnl=float(row["wfe_pnl"]),
            error=row["error"] if row["error"] else None,
        )
        windows.append(w)

    # Reconstruct WalkForwardConfig (partial)
    config = WalkForwardConfig(
        in_sample_months=summary["config"]["in_sample_months"],
        out_of_sample_months=summary["config"]["out_of_sample_months"],
        step_months=summary["config"]["step_months"],
        min_trades=summary["config"]["min_trades"],
        optimization_metric=summary["config"]["optimization_metric"],
        data_dir=summary["config"]["data_dir"],
    )

    return WalkForwardResult(
        config=config,
        windows=windows,
        avg_wfe_sharpe=summary["aggregates"]["avg_wfe_sharpe"],
        avg_wfe_pnl=summary["aggregates"]["avg_wfe_pnl"],
        parameter_stability=summary["parameter_stability"],
        total_oos_trades=summary["aggregates"]["total_oos_trades"],
        overall_oos_sharpe=summary["aggregates"]["overall_oos_sharpe"],
        overall_oos_pnl=summary["aggregates"]["overall_oos_pnl"],
        run_started=datetime.fromisoformat(summary["run_started"]),
        run_completed=datetime.fromisoformat(summary["run_completed"]),
        run_duration_seconds=summary["run_duration_seconds"],
    )


# ---------------------------------------------------------------------------
# Fixed-Params Walk-Forward Analysis
# ---------------------------------------------------------------------------


async def evaluate_fixed_params_on_is(
    is_start: date,
    is_end: date,
    fixed_params: dict[str, Any],
    config: WalkForwardConfig,
) -> dict[str, float]:
    """Evaluate fixed parameters on IS period using VectorBT.

    Args:
        is_start: Start date for in-sample period.
        is_end: End date for in-sample period.
        fixed_params: Fixed parameter set (VectorBT naming).
        config: WalkForwardConfig with data paths.

    Returns:
        Dict with sharpe, win_rate, profit_factor, total_pnl, total_trades.
    """
    # Build SweepConfig with single parameter combination
    sweep_config = SweepConfig(
        data_dir=Path(config.data_dir),
        symbols=config.symbols or [],
        start_date=is_start,
        end_date=is_end,
        output_dir=Path(config.output_dir) / "is_fixed",
        or_minutes_list=[int(fixed_params["or_minutes"])],
        target_r_list=[float(fixed_params["target_r"])],
        stop_buffer_list=[float(fixed_params["stop_buffer_pct"])],
        max_hold_list=[int(fixed_params["max_hold_minutes"])],
        min_gap_list=[float(fixed_params["min_gap_pct"])],
        max_range_atr_list=[float(fixed_params["max_range_atr_ratio"])],
    )

    loop = asyncio.get_running_loop()
    results_df = await loop.run_in_executor(None, run_sweep, sweep_config)

    if results_df.empty:
        return {
            "total_trades": 0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
        }

    # Aggregate across symbols
    total_trades = int(results_df["total_trades"].sum())
    avg_sharpe = float(results_df["sharpe_ratio"].mean())
    avg_win_rate = float(results_df["win_rate"].mean())
    avg_pf = float(results_df["profit_factor"].mean())
    total_return = float(results_df["total_return_pct"].sum())
    max_dd = float(results_df["max_drawdown_pct"].max())

    total_pnl_dollars = total_return * config.initial_cash / 100.0

    return {
        "total_trades": total_trades,
        "sharpe": avg_sharpe,
        "win_rate": avg_win_rate,
        "profit_factor": avg_pf,
        "total_pnl": total_pnl_dollars,
        "max_drawdown": max_dd,
    }


async def run_fixed_params_walk_forward(
    config: WalkForwardConfig,
    fixed_params: dict[str, Any],
) -> WalkForwardResult:
    """Execute walk-forward analysis with fixed parameters (no IS optimization).

    For each window:
    1. Evaluate fixed params on IS period using VectorBT
    2. Evaluate fixed params on OOS period using Replay Harness
    3. Compute WFE metrics

    Args:
        config: WalkForwardConfig with all settings.
        fixed_params: Fixed parameter set (VectorBT naming convention).

    Returns:
        WalkForwardResult with all window results and aggregates.
    """
    run_started = datetime.now(UTC)

    # Create output directory
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect data range from files
    data_dir = Path(config.data_dir)
    data_start, data_end = _detect_data_range(data_dir)

    logger.info(
        "Fixed-params walk-forward: data=%s to %s, IS=%d months, OOS=%d months",
        data_start,
        data_end,
        config.in_sample_months,
        config.out_of_sample_months,
    )
    logger.info("Fixed params: %s", fixed_params)

    # Compute windows
    windows_spec = compute_windows(data_start, data_end, config)

    if not windows_spec:
        logger.error("Data range too short for even one walk-forward window")
        return _empty_walk_forward_result(config, run_started)

    logger.info("Generated %d walk-forward windows", len(windows_spec))

    # Process each window
    window_results: list[WindowResult] = []

    for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_spec, 1):
        logger.info(
            "Window %d/%d: IS=%s to %s, OOS=%s to %s",
            i,
            len(windows_spec),
            is_start,
            is_end,
            oos_start,
            oos_end,
        )

        try:
            # 1. Evaluate fixed params on IS
            is_metrics = await evaluate_fixed_params_on_is(is_start, is_end, fixed_params, config)
            logger.info(
                "Window %d IS: trades=%d, sharpe=%.2f",
                i,
                is_metrics["total_trades"],
                is_metrics["sharpe"],
            )

            # 2. Validate on OOS with fixed params
            oos_metrics = await validate_out_of_sample(oos_start, oos_end, fixed_params, config)
            logger.info(
                "Window %d OOS: trades=%d, sharpe=%.2f, pnl=$%.2f",
                i,
                oos_metrics["total_trades"],
                oos_metrics["sharpe"],
                oos_metrics["total_pnl"],
            )

            # 3. Compute WFE
            wfe_sharpe = compute_wfe(is_metrics["sharpe"], oos_metrics["sharpe"])
            wfe_pnl = compute_wfe(is_metrics["total_pnl"], oos_metrics["total_pnl"])

            window_result = WindowResult(
                window_number=i,
                is_start=is_start,
                is_end=is_end,
                oos_start=oos_start,
                oos_end=oos_end,
                best_params=fixed_params,  # Fixed params, not optimized
                is_total_trades=int(is_metrics["total_trades"]),
                is_win_rate=float(is_metrics["win_rate"]),
                is_profit_factor=float(is_metrics["profit_factor"]),
                is_sharpe=float(is_metrics["sharpe"]),
                is_total_pnl=float(is_metrics["total_pnl"]),
                is_max_drawdown=float(is_metrics["max_drawdown"]),
                oos_total_trades=oos_metrics["total_trades"],
                oos_win_rate=oos_metrics["win_rate"],
                oos_profit_factor=oos_metrics["profit_factor"],
                oos_sharpe=oos_metrics["sharpe"],
                oos_total_pnl=oos_metrics["total_pnl"],
                oos_max_drawdown=oos_metrics["max_drawdown"],
                wfe_sharpe=wfe_sharpe,
                wfe_pnl=wfe_pnl,
            )

        except Exception as e:
            logger.exception("Window %d failed: %s", i, str(e))
            window_result = _error_window_result(i, is_start, is_end, oos_start, oos_end, str(e))

        window_results.append(window_result)

    # Compute aggregate metrics
    valid_windows = [w for w in window_results if w.error is None]

    if valid_windows:
        avg_wfe_sharpe = sum(w.wfe_sharpe for w in valid_windows) / len(valid_windows)
        avg_wfe_pnl = sum(w.wfe_pnl for w in valid_windows) / len(valid_windows)
        total_oos_trades = sum(w.oos_total_trades for w in valid_windows)
        overall_oos_pnl = sum(w.oos_total_pnl for w in valid_windows)

        oos_sharpes = [w.oos_sharpe for w in valid_windows if w.oos_total_trades > 0]
        overall_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0.0
    else:
        avg_wfe_sharpe = 0.0
        avg_wfe_pnl = 0.0
        total_oos_trades = 0
        overall_oos_pnl = 0.0
        overall_oos_sharpe = 0.0

    # For fixed params, stability is 100% by definition
    parameter_stability = {
        param: {"values": [v] * len(valid_windows), "mode": v, "stability": 1.0}
        for param, v in fixed_params.items()
    }

    run_completed = datetime.now(UTC)
    run_duration = (run_completed - run_started).total_seconds()

    result = WalkForwardResult(
        config=config,
        windows=window_results,
        avg_wfe_sharpe=avg_wfe_sharpe,
        avg_wfe_pnl=avg_wfe_pnl,
        parameter_stability=parameter_stability,
        total_oos_trades=total_oos_trades,
        overall_oos_sharpe=overall_oos_sharpe,
        overall_oos_pnl=overall_oos_pnl,
        run_started=run_started,
        run_completed=run_completed,
        run_duration_seconds=run_duration,
    )

    # Save results
    save_walk_forward_results(result, config.output_dir)

    logger.info(
        "Fixed-params walk-forward complete: %d windows, avg WFE=%.2f, OOS trades=%d, OOS P&L=$%.2f",
        len(window_results),
        avg_wfe_sharpe,
        total_oos_trades,
        overall_oos_pnl,
    )

    return result


# ---------------------------------------------------------------------------
# Cross-Validation (DEF-009)
# ---------------------------------------------------------------------------


async def cross_validate_single_symbol(
    symbol: str,
    start: date,
    end: date,
    params: dict[str, Any],
    data_dir: str = "data/historical/1m",
    initial_cash: float = 100_000.0,
    slippage: float = 0.01,
) -> dict[str, Any]:
    """Run both VectorBT and Replay Harness with identical parameters on one symbol.

    Compare trade counts, directions, and approximate P&L. VectorBT should produce
    MORE trades than Replay Harness because it uses simplified logic (no volume
    confirmation, no VWAP filter, no Risk Manager).

    Args:
        symbol: Ticker symbol to test.
        start: Start date.
        end: End date.
        params: Parameters to use (VectorBT naming convention). MUST contain all 6 keys:
            - or_minutes: Opening range window in minutes
            - target_r: Profit target as R-multiple
            - stop_buffer_pct: Stop buffer percentage
            - max_hold_minutes: Maximum hold time
            - min_gap_pct: Minimum gap percentage for scanner
            - max_range_atr_ratio: Maximum OR range / ATR ratio
        data_dir: Path to historical data.
        initial_cash: Starting capital for Replay Harness.
        slippage: Slippage per share for Replay Harness.

    Returns:
        Dict with comparison results:
        - vectorbt_trades: number of trades from VectorBT
        - replay_trades: number of trades from Replay Harness
        - vectorbt_pnl: P&L from VectorBT
        - replay_pnl: P&L from Replay Harness
        - ratio: vectorbt_trades / replay_trades
        - assessment: "PASS" if VectorBT >= Replay, else "FAIL"

    Raises:
        KeyError: If any required parameter is missing from params dict.
    """
    # Validate all required params are present (no defaults - prevents mismatch bugs)
    required_params = [
        "or_minutes",
        "target_r",
        "stop_buffer_pct",
        "max_hold_minutes",
        "min_gap_pct",
        "max_range_atr_ratio",
    ]
    missing = [p for p in required_params if p not in params]
    if missing:
        raise KeyError(f"Missing required parameters for cross-validation: {missing}")

    # Run VectorBT sweep with single parameter combination
    # Use explicit indexing (no .get() defaults) to ensure identical params
    sweep_config = SweepConfig(
        data_dir=Path(data_dir),
        symbols=[symbol],
        start_date=start,
        end_date=end,
        output_dir=Path(data_dir).parent.parent / "backtest_runs" / "cross_validation",
        or_minutes_list=[int(params["or_minutes"])],
        target_r_list=[float(params["target_r"])],
        stop_buffer_list=[float(params["stop_buffer_pct"])],
        max_hold_list=[int(params["max_hold_minutes"])],
        min_gap_list=[float(params["min_gap_pct"])],
        max_range_atr_list=[float(params["max_range_atr_ratio"])],
    )

    loop = asyncio.get_running_loop()
    vbt_results = await loop.run_in_executor(None, run_sweep, sweep_config)

    vectorbt_trades = 0
    vectorbt_pnl = 0.0
    if not vbt_results.empty:
        vectorbt_trades = int(vbt_results["total_trades"].sum())
        vectorbt_pnl = float(vbt_results["total_return_pct"].sum())

    # Run Replay Harness
    wf_config = WalkForwardConfig(
        data_dir=data_dir,
        symbols=[symbol],
        initial_cash=initial_cash,
        slippage_per_share=slippage,
    )

    oos_metrics = await validate_out_of_sample(start, end, params, wf_config)
    replay_trades = oos_metrics["total_trades"]
    replay_pnl = oos_metrics["total_pnl"]

    # Compute ratio
    if replay_trades > 0:
        ratio = vectorbt_trades / replay_trades
    else:
        ratio = float("inf") if vectorbt_trades > 0 else 1.0

    # Assessment: VectorBT should have >= trades (fewer filters)
    assessment = "PASS" if vectorbt_trades >= replay_trades else "FAIL"

    return {
        "symbol": symbol,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "params": params,
        "vectorbt_trades": vectorbt_trades,
        "replay_trades": replay_trades,
        "vectorbt_pnl": vectorbt_pnl,
        "replay_pnl": replay_pnl,
        "ratio": ratio,
        "assessment": assessment,
    }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Argus Walk-Forward Analysis",
        prog="python -m argus.backtest.walk_forward",
    )

    parser.add_argument(
        "--data-dir",
        default="data/historical/1m",
        help="Directory containing historical Parquet files",
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Comma-separated symbols (empty = all in data-dir)",
    )
    parser.add_argument(
        "--is-months",
        type=int,
        default=4,
        help="In-sample period length in months",
    )
    parser.add_argument(
        "--oos-months",
        type=int,
        default=2,
        help="Out-of-sample period length in months",
    )
    parser.add_argument(
        "--step-months",
        type=int,
        default=2,
        help="Step size between windows in months",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=20,
        help="Minimum trades to qualify a parameter set",
    )
    parser.add_argument(
        "--metric",
        default="sharpe",
        choices=["sharpe"],
        help="Optimization metric for IS period",
    )
    parser.add_argument(
        "--output-dir",
        default="data/backtest_runs/walk_forward",
        help="Output directory for results",
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100_000.0,
        help="Starting capital for OOS validation",
    )

    # Fixed-params mode
    parser.add_argument(
        "--fixed-params",
        action="store_true",
        help="Use fixed parameters across all windows (no IS optimization)",
    )
    parser.add_argument(
        "--fp-or-minutes",
        type=int,
        default=15,
        help="Fixed opening range minutes",
    )
    parser.add_argument(
        "--fp-target-r",
        type=float,
        default=2.0,
        help="Fixed target R-multiple",
    )
    parser.add_argument(
        "--fp-stop-buffer",
        type=float,
        default=0.0,
        help="Fixed stop buffer percent",
    )
    parser.add_argument(
        "--fp-max-hold",
        type=int,
        default=60,
        help="Fixed max hold minutes",
    )
    parser.add_argument(
        "--fp-min-gap",
        type=float,
        default=2.0,
        help="Fixed min gap percent",
    )
    parser.add_argument(
        "--fp-max-atr",
        type=float,
        default=999.0,
        help="Fixed max range ATR ratio",
    )

    # Cross-validation mode
    parser.add_argument(
        "--cross-validate",
        action="store_true",
        help="Run cross-validation instead of walk-forward",
    )
    parser.add_argument(
        "--symbol",
        default="TSLA",
        help="Symbol for cross-validation (default: TSLA)",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Start date for cross-validation (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="End date for cross-validation (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--or-minutes",
        type=int,
        default=15,
        help="Opening range minutes for cross-validation",
    )
    parser.add_argument(
        "--target-r",
        type=float,
        default=2.0,
        help="Target R-multiple for cross-validation",
    )
    parser.add_argument(
        "--stop-buffer",
        type=float,
        default=0.0,
        help="Stop buffer percentage for cross-validation",
    )
    parser.add_argument(
        "--max-hold",
        type=int,
        default=60,
        help="Maximum hold minutes for cross-validation",
    )
    parser.add_argument(
        "--min-gap",
        type=float,
        default=2.0,
        help="Minimum gap percentage for cross-validation",
    )
    parser.add_argument(
        "--max-atr",
        type=float,
        default=999.0,
        help="Maximum range/ATR ratio for cross-validation",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.cross_validate:
        # Cross-validation mode (DEF-009)
        if args.start and args.end:
            start = date.fromisoformat(args.start)
            end = date.fromisoformat(args.end)
        else:
            # Default: 6 months of data
            start = date(2025, 6, 1)
            end = date(2025, 12, 31)

        # All 6 parameters must be specified (no hidden defaults that cause mismatches)
        params = {
            "or_minutes": args.or_minutes,
            "target_r": args.target_r,
            "stop_buffer_pct": args.stop_buffer,
            "max_hold_minutes": args.max_hold,
            "min_gap_pct": args.min_gap,
            "max_range_atr_ratio": args.max_atr,
        }

        result = asyncio.run(
            cross_validate_single_symbol(
                symbol=args.symbol,
                start=start,
                end=end,
                params=params,
                data_dir=args.data_dir,
            )
        )

        print("\n" + "=" * 60)
        print("CROSS-VALIDATION RESULTS (DEC-074 FIX)")
        print("=" * 60)
        print(f"Symbol:          {result['symbol']}")
        print(f"Period:          {result['start']} to {result['end']}")
        print("-" * 60)
        print("Parameters (identical for both engines):")
        print(f"  or_minutes:         {params['or_minutes']}")
        print(f"  target_r:           {params['target_r']}")
        print(f"  stop_buffer_pct:    {params['stop_buffer_pct']}")
        print(f"  max_hold_minutes:   {params['max_hold_minutes']}")
        print(f"  min_gap_pct:        {params['min_gap_pct']}")
        print(f"  max_range_atr_ratio:{params['max_range_atr_ratio']}")
        print("-" * 60)
        print(f"VectorBT Trades: {result['vectorbt_trades']}")
        print(f"Replay Trades:   {result['replay_trades']}")
        print(f"Ratio:           {result['ratio']:.2f}")
        print("-" * 60)
        print(f"Assessment:      {result['assessment']}")
        if result["assessment"] == "FAIL":
            print("  WARNING: VectorBT produced fewer trades than Replay Harness.")
            print("  This suggests a bug in the vectorized implementation.")
        print("=" * 60)

    elif args.fixed_params:
        # Fixed-params walk-forward mode
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None

        config = WalkForwardConfig(
            data_dir=args.data_dir,
            symbols=symbols,
            in_sample_months=args.is_months,
            out_of_sample_months=args.oos_months,
            step_months=args.step_months,
            min_trades=args.min_trades,
            optimization_metric=args.metric,
            output_dir=args.output_dir,
            initial_cash=args.initial_cash,
        )

        fixed_params = {
            "or_minutes": args.fp_or_minutes,
            "target_r": args.fp_target_r,
            "stop_buffer_pct": args.fp_stop_buffer,
            "max_hold_minutes": args.fp_max_hold,
            "min_gap_pct": args.fp_min_gap,
            "max_range_atr_ratio": args.fp_max_atr,
        }

        result = asyncio.run(run_fixed_params_walk_forward(config, fixed_params))

        # Print summary
        print("\n" + "=" * 60)
        print("FIXED-PARAMS WALK-FORWARD ANALYSIS RESULTS")
        print("=" * 60)
        print(f"Fixed Parameters:  or={args.fp_or_minutes}, target_r={args.fp_target_r}, "
              f"max_atr={args.fp_max_atr}")
        print(f"                   max_hold={args.fp_max_hold}, min_gap={args.fp_min_gap}, "
              f"stop_buf={args.fp_stop_buffer}")
        print("-" * 60)
        print(f"Windows Processed: {len(result.windows)}")
        print(f"Valid Windows:     {len([w for w in result.windows if w.error is None])}")
        print(f"Duration:          {result.run_duration_seconds:.1f} seconds")
        print("-" * 60)
        print(f"Avg WFE (Sharpe):  {result.avg_wfe_sharpe:.2f}")
        print(f"Total OOS Trades:  {result.total_oos_trades}")
        print(f"Overall OOS Sharpe:{result.overall_oos_sharpe:.2f}")
        print(f"Overall OOS P&L:   ${result.overall_oos_pnl:,.2f}")
        print("-" * 60)

        # Per-window details
        print("\nPer-Window Results:")
        print(f"{'Window':<8} {'IS Period':<25} {'OOS Period':<25} {'IS Sharpe':<10} "
              f"{'OOS Sharpe':<11} {'WFE':<8} {'OOS Trades':<11}")
        print("-" * 100)
        for w in result.windows:
            if w.error:
                print(f"{w.window_number:<8} ERROR: {w.error}")
            else:
                is_period = f"{w.is_start} to {w.is_end}"
                oos_period = f"{w.oos_start} to {w.oos_end}"
                print(f"{w.window_number:<8} {is_period:<25} {oos_period:<25} {w.is_sharpe:<10.2f} "
                      f"{w.oos_sharpe:<11.2f} {w.wfe_sharpe:<8.2f} {w.oos_total_trades:<11}")
        print("-" * 100)

        # WFE assessment
        windows_above_03 = len([w for w in result.windows if w.error is None and w.wfe_sharpe >= 0.3])
        windows_above_05 = len([w for w in result.windows if w.error is None and w.wfe_sharpe >= 0.5])
        valid_count = len([w for w in result.windows if w.error is None])
        print(f"\nWindows with WFE >= 0.3: {windows_above_03}/{valid_count}")
        print(f"Windows with WFE >= 0.5: {windows_above_05}/{valid_count}")

        if result.avg_wfe_sharpe >= 0.5:
            print("\nAssessment:        GOOD - WFE >= 0.5 indicates robust parameters")
        elif result.avg_wfe_sharpe >= 0.3:
            print("\nAssessment:        ACCEPTABLE - WFE >= 0.3 meets DEC-047 threshold")
        else:
            print("\nAssessment:        POOR - WFE < 0.3 indicates potential overfitting")

        print("=" * 60)
        print(f"Results saved to:  {args.output_dir}")

    else:
        # Walk-forward mode (with IS optimization)
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None

        config = WalkForwardConfig(
            data_dir=args.data_dir,
            symbols=symbols,
            in_sample_months=args.is_months,
            out_of_sample_months=args.oos_months,
            step_months=args.step_months,
            min_trades=args.min_trades,
            optimization_metric=args.metric,
            output_dir=args.output_dir,
            initial_cash=args.initial_cash,
        )

        result = asyncio.run(run_walk_forward(config))

        # Print summary
        print("\n" + "=" * 60)
        print("WALK-FORWARD ANALYSIS RESULTS")
        print("=" * 60)
        print(f"Windows Processed: {len(result.windows)}")
        print(f"Valid Windows:     {len([w for w in result.windows if w.error is None])}")
        print(f"Duration:          {result.run_duration_seconds:.1f} seconds")
        print("-" * 60)
        print(f"Avg WFE (Sharpe):  {result.avg_wfe_sharpe:.2f}")
        print(f"Avg WFE (P&L):     {result.avg_wfe_pnl:.2f}")
        print(f"Total OOS Trades:  {result.total_oos_trades}")
        print(f"Overall OOS Sharpe:{result.overall_oos_sharpe:.2f}")
        print(f"Overall OOS P&L:   ${result.overall_oos_pnl:,.2f}")
        print("-" * 60)

        # WFE assessment
        if result.avg_wfe_sharpe >= 0.5:
            print("Assessment:        GOOD - WFE >= 0.5 indicates robust parameters")
        elif result.avg_wfe_sharpe >= 0.3:
            print("Assessment:        ACCEPTABLE - WFE >= 0.3 meets DEC-047 threshold")
        else:
            print("Assessment:        POOR - WFE < 0.3 indicates potential overfitting")

        print("=" * 60)
        print(f"Results saved to:  {args.output_dir}")

        # Print parameter stability
        if result.parameter_stability:
            print("\nParameter Stability:")
            for param, stats in result.parameter_stability.items():
                print(f"  {param}: mode={stats['mode']}, stability={stats['stability']:.0%}")


if __name__ == "__main__":
    main()

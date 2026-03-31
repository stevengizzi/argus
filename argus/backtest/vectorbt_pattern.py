"""Generic VectorBT pattern backtester.

Accepts any PatternModule + config and runs parameter sweeps and walk-forward
validation. Reuses the precompute+vectorize architecture from the ORB/R2G
backtesters, adapted for the pattern detection sliding-window interface.

Usage:
    python -m argus.backtest.vectorbt_pattern \
        --pattern bull_flag \
        --config config/strategies/bull_flag.yaml \
        --data-dir data/historical/1m \
        --start 2025-01-01 --end 2025-12-31
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import product
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml

from argus.backtest.vectorbt_red_to_green import (
    load_symbol_data,
)
from argus.backtest.walk_forward import (
    WalkForwardResult,
    WindowResult,
    compute_wfe,
    compute_windows,
    WalkForwardConfig,
    compute_parameter_stability,
)
from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# Market hours
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM ET


@dataclass
class PatternSweepConfig:
    """Configuration for a generic pattern parameter sweep."""

    data_dir: Path
    symbols: list[str]
    start_date: date
    end_date: date
    output_dir: Path

    # Fixed from strategy config
    target_1_r: float = 1.0
    target_2_r: float = 2.0
    time_stop_minutes: int = 30

    # Scanner-like filters
    min_price: float = 10.0
    max_price: float = 200.0


@dataclass
class PatternSweepResult:
    """Results from a single parameter combination on a single symbol."""

    symbol: str
    params: dict[str, object]

    total_trades: int
    win_rate: float
    total_return_pct: float
    avg_r_multiple: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_hold_bars: float


@dataclass
class PatternTradeInfo:
    """A single trade from pattern signal to exit."""

    entry_price: float
    exit_price: float
    risk: float
    pnl: float
    r_multiple: float
    hold_bars: int
    exit_reason: str


def ohlcv_row_to_candle_bar(
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> CandleBar:
    """Convert a single OHLCV row to a CandleBar.

    Args:
        timestamp: Bar timestamp.
        open_price: Opening price.
        high: High price.
        low: Low price.
        close: Closing price.
        volume: Bar volume.

    Returns:
        CandleBar instance.
    """
    return CandleBar(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def df_window_to_candle_bars(df: pd.DataFrame, start_idx: int, count: int) -> list[CandleBar]:
    """Convert a DataFrame window to a list of CandleBar objects.

    Args:
        df: OHLCV DataFrame with timestamp, open, high, low, close, volume columns.
        start_idx: Starting row index (inclusive).
        count: Number of rows to convert.

    Returns:
        List of CandleBar objects (chronological order).
    """
    end_idx = min(start_idx + count, len(df))
    candles: list[CandleBar] = []
    for i in range(start_idx, end_idx):
        row = df.iloc[i]
        candles.append(
            ohlcv_row_to_candle_bar(
                timestamp=row["timestamp"].to_pydatetime(),
                open_price=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return candles


@dataclass
class _EntryCandidate:
    """Pre-computed entry candidate from pattern detection."""

    bar_idx: int
    detection: PatternDetection
    score: float
    post_entry_highs: np.ndarray
    post_entry_lows: np.ndarray
    post_entry_closes: np.ndarray
    post_entry_minutes: np.ndarray


def _find_exit_vectorized(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    minutes: np.ndarray,
    entry_price: float,
    stop_price: float,
    target_price: float,
    time_stop_bars: int,
) -> PatternTradeInfo | None:
    """Find exit using vectorized operations.

    Exit priority (worst-case for longs):
    1. Stop loss
    2. Target
    3. Time stop (check if stop also hit)
    4. EOD (check if stop also hit)

    Args:
        highs: Post-entry high prices.
        lows: Post-entry low prices.
        closes: Post-entry close prices.
        minutes: Post-entry minutes_from_midnight.
        entry_price: Entry price.
        stop_price: Stop loss price.
        target_price: Target price.
        time_stop_bars: Bars until time stop.

    Returns:
        PatternTradeInfo or None if no valid exit.
    """
    n = len(highs)
    if n == 0:
        return None

    stop_hit = lows <= stop_price
    target_hit = highs >= target_price
    bars_held = np.arange(1, n + 1)
    time_stop_hit = bars_held >= time_stop_bars
    eod_hit = minutes >= EOD_FLATTEN_MINUTES

    stop_idx = int(np.argmax(stop_hit)) if stop_hit.any() else n
    target_idx = int(np.argmax(target_hit)) if target_hit.any() else n
    time_idx = int(np.argmax(time_stop_hit)) if time_stop_hit.any() else n
    eod_idx = int(np.argmax(eod_hit)) if eod_hit.any() else n

    exit_idx = min(stop_idx, target_idx, time_idx, eod_idx)

    if exit_idx >= n:
        exit_idx = n - 1
        reason = "eod"
        exit_price = float(closes[exit_idx])
    elif exit_idx == eod_idx and eod_hit[exit_idx]:
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        else:
            reason = "eod"
            exit_price = float(closes[exit_idx])
    elif exit_idx == time_idx and time_stop_hit[exit_idx]:
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        else:
            reason = "time_stop"
            exit_price = float(closes[exit_idx])
    elif exit_idx == stop_idx and stop_hit[exit_idx]:
        reason = "stop"
        exit_price = stop_price
    elif exit_idx == target_idx and target_hit[exit_idx]:
        reason = "target"
        exit_price = target_price
    else:
        reason = "eod"
        exit_price = float(closes[exit_idx])

    hold_bars = exit_idx + 1
    risk = entry_price - stop_price
    pnl = exit_price - entry_price
    r_multiple = pnl / risk if risk > 0 else 0.0

    return PatternTradeInfo(
        entry_price=entry_price,
        exit_price=exit_price,
        risk=risk,
        pnl=pnl,
        r_multiple=r_multiple,
        hold_bars=hold_bars,
        exit_reason=reason,
    )


def _compute_metrics(
    trades: list[PatternTradeInfo],
) -> dict[str, float]:
    """Compute aggregate metrics from a list of trades.

    Args:
        trades: List of PatternTradeInfo objects.

    Returns:
        Dict with win_rate, avg_r_multiple, sharpe_ratio, profit_factor,
        max_drawdown_pct, total_return_pct, avg_hold_bars.
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_r_multiple": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "total_return_pct": 0.0,
            "avg_hold_bars": 0.0,
        }

    r_multiples = [t.r_multiple for t in trades]
    winners = [t for t in trades if t.r_multiple > 0]
    win_rate = len(winners) / len(trades)
    avg_r = sum(r_multiples) / len(r_multiples)

    gross_wins = sum(t.pnl for t in trades if t.pnl > 0)
    gross_losses = abs(sum(t.pnl for t in trades if t.pnl < 0))
    if gross_losses > 0:
        profit_factor = gross_wins / gross_losses
    elif gross_wins > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    risk_per_trade = 100.0
    total_r = sum(r_multiples)
    total_return_pct = total_r * risk_per_trade / 10000.0 * 100

    avg_hold = sum(t.hold_bars for t in trades) / len(trades)

    # Equity curve for drawdown and Sharpe
    equity = [10000.0]
    for r in r_multiples:
        equity.append(equity[-1] + r * risk_per_trade)

    max_dd_pct = _compute_max_drawdown_pct(equity)
    sharpe = _compute_sharpe(r_multiples)

    return {
        "total_trades": float(len(trades)),
        "win_rate": win_rate,
        "avg_r_multiple": avg_r,
        "sharpe_ratio": sharpe,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_dd_pct,
        "total_return_pct": total_return_pct,
        "avg_hold_bars": avg_hold,
    }


def _compute_max_drawdown_pct(equity: list[float]) -> float:
    """Compute maximum drawdown as percentage from equity curve."""
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for value in equity:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, drawdown)
    return max_dd * 100


def _compute_sharpe(
    r_multiples: list[float],
    annualization_factor: float = 252.0,
) -> float:
    """Compute Sharpe ratio from R-multiples."""
    if len(r_multiples) < 2:
        return 0.0
    mean_r = sum(r_multiples) / len(r_multiples)
    variance = sum((r - mean_r) ** 2 for r in r_multiples) / (len(r_multiples) - 1)
    std_r = variance**0.5
    if std_r < 1e-10:
        return 0.0
    return (mean_r / std_r) * (annualization_factor**0.5)


def params_to_dict(params: list[PatternParam]) -> dict[str, object]:
    """Extract default values from a list of PatternParam as a flat dict.

    Converts the structured PatternParam list back to the legacy
    ``{name: default}`` format for code that expects the old dict interface.

    Args:
        params: List of PatternParam objects.

    Returns:
        Dictionary mapping parameter names to their default values.
    """
    return {p.name: p.default for p in params}


class PatternBacktester:
    """Generic backtester for any PatternModule implementation.

    Uses a sliding-window approach over historical OHLCV data to detect patterns,
    then applies vectorized exit logic for stop/target/time-stop/EOD exits.

    The backtester is pattern-agnostic: it relies entirely on the PatternModule
    interface (detect, score, get_default_params, lookback_bars) and never
    references specific pattern implementations.

    Args:
        pattern: A PatternModule instance (used as template for default params).
        config_path: Path to the strategy YAML config file.
    """

    def __init__(self, pattern: PatternModule, config_path: Path) -> None:
        self._pattern = pattern
        self._config_path = config_path
        self._config = self._load_config(config_path)

    @staticmethod
    def _load_config(config_path: Path) -> dict[str, object]:
        """Load strategy config from YAML.

        Args:
            config_path: Path to YAML config file.

        Returns:
            Parsed config dictionary.
        """
        with open(config_path) as f:
            return dict(yaml.safe_load(f))

    def _create_pattern_with_params(self, params: dict[str, object]) -> PatternModule:
        """Create a new pattern instance with the given parameters.

        Uses the same class as the template pattern, passing params as kwargs.

        Args:
            params: Parameter dict (keys match __init__ kwargs of the pattern class).

        Returns:
            New PatternModule instance with the specified parameters.
        """
        pattern_class = type(self._pattern)
        return pattern_class(**params)

    def generate_signals(
        self,
        day_df: pd.DataFrame,
        pattern: PatternModule,
    ) -> list[_EntryCandidate]:
        """Generate entry signals by sliding a window over a single day's data.

        At each bar position (starting from lookback_bars), constructs a
        CandleBar window, calls pattern.detect(), and if a detection is found,
        captures post-entry arrays for vectorized exit detection.

        Only one entry per day (first detection wins).

        Args:
            day_df: DataFrame for a single trading day with OHLCV columns.
            pattern: PatternModule instance to use for detection.

        Returns:
            List of _EntryCandidate objects (typically 0 or 1 per day).
        """
        lookback = pattern.lookback_bars
        n_bars = len(day_df)

        if n_bars < lookback + 1:
            return []

        highs = day_df["high"].to_numpy()
        lows = day_df["low"].to_numpy()
        closes = day_df["close"].to_numpy()
        minutes = day_df["minutes_from_midnight"].to_numpy()

        candidates: list[_EntryCandidate] = []

        for bar_idx in range(lookback, n_bars - 1):
            # Build CandleBar window
            window_start = bar_idx - lookback
            candles = df_window_to_candle_bars(day_df, window_start, lookback + 1)

            # Detect pattern (no indicators in generic backtester)
            detection = pattern.detect(candles, {})
            if detection is None:
                continue

            score = pattern.score(detection)

            # Capture post-entry arrays for vectorized exit
            post_idx = bar_idx + 1
            candidates.append(
                _EntryCandidate(
                    bar_idx=bar_idx,
                    detection=detection,
                    score=score,
                    post_entry_highs=highs[post_idx:].copy(),
                    post_entry_lows=lows[post_idx:].copy(),
                    post_entry_closes=closes[post_idx:].copy(),
                    post_entry_minutes=minutes[post_idx:].copy(),
                )
            )

            # One entry per day
            break

        return candidates

    def build_parameter_grid(self) -> list[dict[str, object]]:
        """Build a parameter grid from the pattern's PatternParam metadata.

        For each PatternParam with numeric type and complete range metadata
        (min_value, max_value, step), generates values from min to max
        stepping by step. The default value is always included in the grid.

        For bool params, both True and False are included.
        For params with incomplete range metadata, only the default is used.

        Returns:
            List of parameter dicts, each a unique combination.
        """
        param_list = self._pattern.get_default_params()

        per_param_values: dict[str, list[object]] = {}

        for param in param_list:
            if param.param_type is bool:
                per_param_values[param.name] = [True, False]
            elif (
                param.param_type in (int, float)
                and param.min_value is not None
                and param.max_value is not None
                and param.step is not None
                and param.step > 0
            ):
                values: list[float] = []
                current = param.min_value
                while current <= param.max_value + param.step * 0.01:
                    values.append(current)
                    current += param.step

                # Ensure default is included
                default_val = float(param.default)
                if default_val not in values:
                    values.append(default_val)
                    values.sort()

                if param.param_type is int:
                    int_values: list[object] = list(
                        dict.fromkeys(round(v) for v in values)
                    )
                    per_param_values[param.name] = int_values
                else:
                    rounded: list[object] = list(
                        dict.fromkeys(round(v, 6) for v in values)
                    )
                    per_param_values[param.name] = rounded
            else:
                per_param_values[param.name] = [param.default]

        param_names = list(per_param_values.keys())
        param_value_lists = [per_param_values[n] for n in param_names]

        grid: list[dict[str, object]] = []
        for combo in product(*param_value_lists):
            grid.append(dict(zip(param_names, combo)))

        return grid

    def run_sweep(
        self,
        ohlcv_df: pd.DataFrame,
        symbols: list[str] | None = None,
    ) -> pd.DataFrame:
        """Run a parameter sweep over the full grid.

        For each parameter combination, creates a pattern instance,
        scans all trading days for signals, computes trades via vectorized
        exit detection, and aggregates metrics.

        Args:
            ohlcv_df: DataFrame with OHLCV data (from load_symbol_data or similar).
                      Must have trading_day, minutes_from_midnight columns.
            symbols: Optional list of symbols (for logging). Defaults to ["UNKNOWN"].

        Returns:
            DataFrame with one row per (symbol, param_combo) with metrics.
        """
        grid = self.build_parameter_grid()
        logger.info(
            "Pattern sweep: %d parameter combinations for %s",
            len(grid),
            self._pattern.name,
        )

        target_1_r = float(self._config.get("target_1_r", 1.0))
        time_stop_minutes = int(self._config.get("time_stop_minutes", 30))

        # Group by trading day once
        day_groups: dict[date, pd.DataFrame] = {
            day: group.reset_index(drop=True)
            for day, group in ohlcv_df.groupby("trading_day")  # type: ignore[misc]
        }

        results: list[dict[str, object]] = []

        for param_combo in grid:
            try:
                pattern = self._create_pattern_with_params(param_combo)
            except Exception as e:
                logger.warning("Failed to create pattern with params %s: %s", param_combo, e)
                continue

            all_trades: list[PatternTradeInfo] = []

            for _day, day_df in sorted(day_groups.items()):
                candidates = self.generate_signals(day_df, pattern)

                for candidate in candidates:
                    detection = candidate.detection
                    entry_price = detection.entry_price
                    stop_price = detection.stop_price
                    risk = entry_price - stop_price

                    if risk <= 0:
                        continue

                    # Use detection targets if available, else config R-multiples
                    if detection.target_prices:
                        target_price = detection.target_prices[0]
                    else:
                        target_price = entry_price + risk * target_1_r

                    trade = _find_exit_vectorized(
                        candidate.post_entry_highs,
                        candidate.post_entry_lows,
                        candidate.post_entry_closes,
                        candidate.post_entry_minutes,
                        entry_price,
                        stop_price,
                        target_price,
                        time_stop_minutes,
                    )

                    if trade is not None:
                        all_trades.append(trade)

            metrics = _compute_metrics(all_trades)

            row: dict[str, object] = {
                "pattern": self._pattern.name,
                **{f"param_{k}": v for k, v in param_combo.items()},
                "total_trades": int(metrics["total_trades"]),
                "win_rate": metrics["win_rate"],
                "avg_r_multiple": metrics["avg_r_multiple"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown_pct": metrics["max_drawdown_pct"],
                "total_return_pct": metrics["total_return_pct"],
                "avg_hold_bars": metrics["avg_hold_bars"],
            }
            results.append(row)

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results)

    def run_walk_forward(
        self,
        data_dir: Path,
        symbols: list[str],
        start_date: date,
        end_date: date,
        in_sample_months: int = 4,
        out_of_sample_months: int = 2,
        step_months: int = 2,
        min_trades: int = 10,
    ) -> dict[str, object]:
        """Run walk-forward validation for this pattern.

        Uses compute_windows from walk_forward.py for window generation.
        For each window, runs a parameter sweep on IS data, selects best
        params by Sharpe, then evaluates on OOS data.

        Args:
            data_dir: Path to historical data directory.
            symbols: List of ticker symbols.
            start_date: Data start date.
            end_date: Data end date.
            in_sample_months: IS window size.
            out_of_sample_months: OOS window size.
            step_months: Window slide step.
            min_trades: Minimum trades to qualify a parameter set.

        Returns:
            Dict with avg_wfe_sharpe, windows, best_params, status, etc.
        """
        wf_config = WalkForwardConfig(
            in_sample_months=in_sample_months,
            out_of_sample_months=out_of_sample_months,
            step_months=step_months,
            min_trades=min_trades,
        )

        windows_spec = compute_windows(start_date, end_date, wf_config)

        if not windows_spec:
            logger.warning("Data range too short for walk-forward windows")
            return {
                "status": "no_data",
                "avg_wfe_sharpe": 0.0,
                "windows": [],
                "best_params": {},
            }

        logger.info(
            "Walk-forward: %d windows for %s pattern",
            len(windows_spec),
            self._pattern.name,
        )

        # Load all data once, then slice per window
        all_data: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = load_symbol_data(data_dir, symbol, start_date, end_date)
            if not df.empty:
                all_data[symbol] = df

        if not all_data:
            return {
                "status": "no_data",
                "avg_wfe_sharpe": 0.0,
                "windows": [],
                "best_params": {},
            }

        window_results: list[dict[str, object]] = []

        for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_spec, 1):
            logger.info(
                "Window %d/%d: IS=%s–%s, OOS=%s–%s",
                i, len(windows_spec), is_start, is_end, oos_start, oos_end,
            )

            # Slice IS data
            is_dfs = []
            for _sym, df in all_data.items():
                is_slice = df[
                    (df["trading_day"] >= is_start) & (df["trading_day"] <= is_end)
                ]
                if not is_slice.empty:
                    is_dfs.append(is_slice)

            if not is_dfs:
                window_results.append({"window": i, "error": "no_is_data"})
                continue

            is_combined = pd.concat(is_dfs, ignore_index=True)

            # Run sweep on IS
            is_results_df = self.run_sweep(is_combined)
            if is_results_df.empty:
                window_results.append({"window": i, "error": "no_is_results"})
                continue

            # Filter by min trades and find best by Sharpe
            qualified = is_results_df[is_results_df["total_trades"] >= min_trades]
            if qualified.empty:
                window_results.append({"window": i, "error": "no_qualifying_params"})
                continue

            best_idx = qualified["sharpe_ratio"].idxmax()
            best_row = qualified.loc[best_idx]

            # Extract best params
            param_cols = [c for c in qualified.columns if c.startswith("param_")]
            best_params: dict[str, object] = {
                c.removeprefix("param_"): best_row[c] for c in param_cols
            }
            is_sharpe = float(best_row["sharpe_ratio"])

            # Slice OOS data
            oos_dfs = []
            for _sym, df in all_data.items():
                oos_slice = df[
                    (df["trading_day"] >= oos_start) & (df["trading_day"] <= oos_end)
                ]
                if not oos_slice.empty:
                    oos_dfs.append(oos_slice)

            if not oos_dfs:
                window_results.append({"window": i, "error": "no_oos_data"})
                continue

            oos_combined = pd.concat(oos_dfs, ignore_index=True)

            # Evaluate best params on OOS
            try:
                oos_pattern = self._create_pattern_with_params(best_params)
            except Exception as e:
                window_results.append({"window": i, "error": f"pattern_create_failed: {e}"})
                continue

            oos_trades = self._evaluate_pattern_on_data(oos_combined, oos_pattern)
            oos_metrics = _compute_metrics(oos_trades)
            oos_sharpe = oos_metrics["sharpe_ratio"]

            wfe = compute_wfe(is_sharpe, oos_sharpe)

            window_results.append({
                "window": i,
                "is_start": str(is_start),
                "is_end": str(is_end),
                "oos_start": str(oos_start),
                "oos_end": str(oos_end),
                "best_params": best_params,
                "is_sharpe": is_sharpe,
                "is_trades": int(best_row["total_trades"]),
                "oos_sharpe": oos_sharpe,
                "oos_trades": int(oos_metrics["total_trades"]),
                "wfe_sharpe": wfe,
            })

        # Aggregate
        valid_wfes = [
            float(w["wfe_sharpe"])
            for w in window_results
            if "wfe_sharpe" in w
        ]
        avg_wfe = sum(valid_wfes) / len(valid_wfes) if valid_wfes else 0.0

        # Determine overall best params (from window with highest IS Sharpe)
        valid_windows = [w for w in window_results if "best_params" in w]
        if valid_windows:
            best_window = max(valid_windows, key=lambda w: float(w.get("is_sharpe", 0)))
            overall_best_params = best_window["best_params"]
        else:
            overall_best_params = {}

        status = "validated" if avg_wfe > 0.3 else "exploration"

        return {
            "status": status,
            "avg_wfe_sharpe": round(avg_wfe, 3),
            "windows": window_results,
            "best_params": overall_best_params,
            "total_windows": len(windows_spec),
            "valid_windows": len(valid_wfes),
        }

    def _evaluate_pattern_on_data(
        self,
        ohlcv_df: pd.DataFrame,
        pattern: PatternModule,
    ) -> list[PatternTradeInfo]:
        """Evaluate a specific pattern on OHLCV data and return trades.

        Args:
            ohlcv_df: Combined OHLCV DataFrame for evaluation period.
            pattern: Pattern instance with specific parameters.

        Returns:
            List of PatternTradeInfo objects.
        """
        target_1_r = float(self._config.get("target_1_r", 1.0))
        time_stop_minutes = int(self._config.get("time_stop_minutes", 30))

        day_groups: dict[date, pd.DataFrame] = {
            day: group.reset_index(drop=True)
            for day, group in ohlcv_df.groupby("trading_day")  # type: ignore[misc]
        }

        trades: list[PatternTradeInfo] = []

        for _day, day_df in sorted(day_groups.items()):
            candidates = self.generate_signals(day_df, pattern)

            for candidate in candidates:
                detection = candidate.detection
                entry_price = detection.entry_price
                stop_price = detection.stop_price
                risk = entry_price - stop_price

                if risk <= 0:
                    continue

                if detection.target_prices:
                    target_price = detection.target_prices[0]
                else:
                    target_price = entry_price + risk * target_1_r

                trade = _find_exit_vectorized(
                    candidate.post_entry_highs,
                    candidate.post_entry_lows,
                    candidate.post_entry_closes,
                    candidate.post_entry_minutes,
                    entry_price,
                    stop_price,
                    target_price,
                    time_stop_minutes,
                )

                if trade is not None:
                    trades.append(trade)

        return trades


def run_pattern_backtest(
    pattern_name: str,
    config_path: Path,
    data_dir: Path,
    symbols: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, object]:
    """Run a full pattern backtest: sweep + walk-forward.

    Factory function that instantiates the appropriate PatternModule
    and runs the generic backtester.

    Args:
        pattern_name: Pattern identifier ("bull_flag" or "flat_top_breakout").
        config_path: Path to strategy YAML config.
        data_dir: Path to historical data directory.
        symbols: Ticker symbols to test.
        start_date: Start date.
        end_date: End date.

    Returns:
        Dict with sweep and walk-forward results.
    """
    pattern = _create_pattern_by_name(pattern_name, config_path)
    backtester = PatternBacktester(pattern, config_path)

    # Load data for sweep
    all_dfs = []
    for symbol in symbols:
        df = load_symbol_data(data_dir, symbol, start_date, end_date)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        logger.warning("No data found for any symbol")
        return {"status": "no_data"}

    combined_df = pd.concat(all_dfs, ignore_index=True)

    # Run sweep
    sweep_df = backtester.run_sweep(combined_df, symbols)
    logger.info("Sweep complete: %d rows", len(sweep_df))

    # Run walk-forward
    wf_result = backtester.run_walk_forward(
        data_dir=data_dir,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "pattern": pattern_name,
        "sweep_rows": len(sweep_df),
        "walk_forward": wf_result,
    }


def _create_pattern_by_name(name: str, config_path: Path) -> PatternModule:
    """Create a PatternModule instance by name, using config defaults.

    Args:
        name: Pattern name ("bull_flag" or "flat_top_breakout").
        config_path: Path to YAML config with pattern parameters.

    Returns:
        PatternModule instance.

    Raises:
        ValueError: If pattern name is unknown.
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if name == "bull_flag":
        from argus.strategies.patterns.bull_flag import BullFlagPattern

        return BullFlagPattern(
            pole_min_bars=config.get("pole_min_bars", 5),
            pole_min_move_pct=config.get("pole_min_move_pct", 0.03),
            flag_max_bars=config.get("flag_max_bars", 20),
            flag_max_retrace_pct=config.get("flag_max_retrace_pct", 0.50),
            breakout_volume_multiplier=config.get("breakout_volume_multiplier", 1.3),
        )
    elif name == "flat_top_breakout":
        from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern

        return FlatTopBreakoutPattern(
            resistance_touches=config.get("resistance_touches", 3),
            resistance_tolerance_pct=config.get("resistance_tolerance_pct", 0.002),
            consolidation_min_bars=config.get("consolidation_min_bars", 10),
            breakout_volume_multiplier=config.get("breakout_volume_multiplier", 1.3),
            target_1_r=config.get("target_1_r", 1.0),
            target_2_r=config.get("target_2_r", 2.0),
        )
    elif name == "abcd":
        from argus.strategies.patterns.abcd import ABCDPattern

        return ABCDPattern(
            swing_lookback=config.get("swing_lookback", 5),
            min_swing_atr_mult=config.get("min_swing_atr_mult", 0.5),
            fib_b_min=config.get("fib_b_min", 0.382),
            fib_b_max=config.get("fib_b_max", 0.618),
            completion_tolerance_percent=config.get(
                "completion_tolerance_percent", 1.0
            ),
            stop_buffer_atr_mult=config.get("stop_buffer_atr_mult", 0.5),
            target_extension=config.get("target_extension", 1.272),
        )
    else:
        raise ValueError(f"Unknown pattern: {name}")


def main() -> None:
    """CLI entry point for the generic pattern backtester."""
    parser = argparse.ArgumentParser(
        description="Run generic pattern VectorBT backtest.",
        prog="python -m argus.backtest.vectorbt_pattern",
    )
    parser.add_argument("--pattern", type=str, required=True, help="Pattern name")
    parser.add_argument("--config", type=str, required=True, help="Config YAML path")
    parser.add_argument("--data-dir", type=str, default="data/historical/1m")
    parser.add_argument("--symbols", type=str, default=None)
    parser.add_argument("--start", type=str, required=True)
    parser.add_argument("--end", type=str, required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else []
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    result = run_pattern_backtest(
        pattern_name=args.pattern,
        config_path=Path(args.config),
        data_dir=Path(args.data_dir),
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )

    print("\n" + "=" * 60)
    print(f"Pattern Backtest: {args.pattern}")
    print("=" * 60)
    for key, value in result.items():
        if key == "walk_forward" and isinstance(value, dict):
            print(f"  walk_forward:")
            for wf_key, wf_val in value.items():
                if wf_key != "windows":
                    print(f"    {wf_key}: {wf_val}")
        else:
            print(f"  {key}: {value}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

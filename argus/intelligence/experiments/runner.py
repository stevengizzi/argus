"""Experiment runner — backtest pre-filter for parameterized pattern variants.

Generates parameter grids from PatternParam metadata, runs BacktestEngine
for each configuration against the Parquet cache, and stores results in
ExperimentStore.  Only configurations that clear a minimum expectancy and
trade-count bar are eligible for shadow spawning (COMPLETED status).

Sprint 32, Session 6.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.core.ids import generate_id
from argus.intelligence.experiments.config import ExitSweepParam
from argus.intelligence.experiments.models import ExperimentRecord, ExperimentStatus
from argus.intelligence.experiments.store import ExperimentStore
from argus.strategies.patterns.base import PatternParam
from argus.strategies.patterns.factory import get_pattern_class

logger = logging.getLogger(__name__)

_GRID_CAP = 500
_SECONDS_PER_GRID_POINT = 30

# Patterns supported by BacktestEngine StrategyType (DEF-121 tracks the rest)
_PATTERN_TO_STRATEGY_TYPE: dict[str, StrategyType] = {
    "bull_flag": StrategyType.BULL_FLAG,
    "flat_top_breakout": StrategyType.FLAT_TOP_BREAKOUT,
    "dip_and_rip": StrategyType.DIP_AND_RIP,
    "hod_break": StrategyType.HOD_BREAK,
    # NOTE: ABCD swing detection is O(n³) per DEF-122 — backtesting a single
    # symbol/month with default params will run noticeably slower than other
    # patterns.  Do NOT optimize here; just document and accept the limitation.
    "abcd": StrategyType.ABCD,
    # Reference-data patterns (Sprint 32.5 S4): BacktestEngine derives prior
    # closes from the Parquet cache and calls set_reference_data() each day.
    "gap_and_go": StrategyType.GAP_AND_GO,
    "premarket_high_break": StrategyType.PREMARKET_HIGH_BREAK,
    "micro_pullback": StrategyType.MICRO_PULLBACK,
    "vwap_bounce": StrategyType.VWAP_BOUNCE,
}


class ExperimentRunner:
    """Generates parameter grids and runs BacktestEngine sweeps.

    Results are stored in ExperimentStore.  Configs that fail the
    expectancy/trade-count pre-filter receive FAILED status; those that pass
    receive COMPLETED and are eligible for shadow spawning by the variant
    spawner.

    Args:
        store: ExperimentStore for persisting experiment records.
        config: Experiment config section dict.  Recognised keys:
            - ``backtest_min_expectancy`` (float, default 0.0)
            - ``backtest_min_trades`` (int, default 10)
            - ``backtest_start_date`` (str ISO, fallback start date)
            - ``backtest_end_date`` (str ISO, fallback end date)
    """

    def __init__(self, store: ExperimentStore, config: dict[str, Any]) -> None:
        self._store = store
        self._config = config
        self._min_expectancy: float = float(
            config.get("backtest_min_expectancy", 0.0)
        )
        self._min_trades: int = int(config.get("backtest_min_trades", 10))

    # ---------------------------------------------------------------------------
    # Grid generation
    # ---------------------------------------------------------------------------

    def generate_parameter_grid(
        self,
        pattern_name: str,
        param_subset: list[str] | None = None,
        exit_sweep_params: list[ExitSweepParam] | None = None,
    ) -> list[dict[str, Any]]:
        """Build a deterministic cartesian-product grid from PatternParam metadata.

        For each PatternParam:
        - ``int`` with range: ``range(min_value, max_value+1, step)``
        - ``float`` with range: step-spaced values from min to max (inclusive)
        - ``bool``: ``[True, False]``
        - string / no range: ``[default]`` only
        - if ``param_subset`` given and param not in it: ``[default]`` only

        When *exit_sweep_params* is provided and non-empty, the detection grid
        is crossed with an exit parameter grid.  Each resulting grid point has
        the form ``{"detection_params": {...}, "exit_overrides": {...}}`` where
        ``exit_overrides`` keys are the dot-path strings from
        ``ExitSweepParam.path`` (e.g. ``"trailing_stop.atr_multiplier"``).

        When *exit_sweep_params* is absent or empty, the return format is
        identical to the current behaviour (list of flat detection param dicts).

        Logs a WARNING if the cartesian product exceeds 500 points.

        Args:
            pattern_name: Snake_case or PascalCase pattern name.
            param_subset: If provided, only params in this list are varied;
                all others use their default values.
            exit_sweep_params: Optional exit-management parameters to sweep.
                When provided, the grid is the cross-product of detection ×
                exit dimensions.

        Returns:
            When *exit_sweep_params* is absent: list of flat detection param
            dicts (current behaviour).  When present: list of structured dicts
            ``{"detection_params": {...}, "exit_overrides": {...}}``.

        Raises:
            ValueError: If ``pattern_name`` is not a registered pattern.
        """
        pattern_class = get_pattern_class(pattern_name)
        instance = pattern_class()
        pattern_params: list[PatternParam] = instance.get_default_params()

        param_ranges: dict[str, list[Any]] = {
            param.name: _generate_param_values(param, param_subset)
            for param in pattern_params
        }

        keys = list(param_ranges.keys())
        combos = list(itertools.product(*[param_ranges[k] for k in keys]))
        detection_grid: list[dict[str, Any]] = [dict(zip(keys, combo)) for combo in combos]

        if not exit_sweep_params:
            if len(detection_grid) > _GRID_CAP:
                logger.warning(
                    "Grid for pattern '%s' has %d points (cap=%d). "
                    "Use param_subset to reduce the search space.",
                    pattern_name,
                    len(detection_grid),
                    _GRID_CAP,
                )
            logger.info(
                "Generated parameter grid for pattern '%s': %d points",
                pattern_name,
                len(detection_grid),
            )
            return detection_grid

        # Build exit grid from ExitSweepParam definitions
        exit_ranges: dict[str, list[float]] = {
            p.path: _generate_exit_values(p) for p in exit_sweep_params
        }
        exit_keys = list(exit_ranges.keys())
        exit_combos = list(itertools.product(*[exit_ranges[k] for k in exit_keys]))
        exit_grid: list[dict[str, Any]] = [
            dict(zip(exit_keys, combo)) for combo in exit_combos
        ]

        # Cross-product: detection × exit
        combined: list[dict[str, Any]] = [
            {"detection_params": detection, "exit_overrides": exit_override}
            for detection, exit_override in itertools.product(detection_grid, exit_grid)
        ]

        if len(combined) > _GRID_CAP:
            logger.warning(
                "Grid for pattern '%s' has %d points (cap=%d). "
                "Use param_subset to reduce the search space.",
                pattern_name,
                len(combined),
                _GRID_CAP,
            )
        logger.info(
            "Generated parameter grid for pattern '%s': %d points "
            "(%d detection × %d exit)",
            pattern_name,
            len(combined),
            len(detection_grid),
            len(exit_grid),
        )
        return combined

    # ---------------------------------------------------------------------------
    # Sweep orchestration
    # ---------------------------------------------------------------------------

    async def run_sweep(
        self,
        pattern_name: str,
        cache_dir: str,
        param_subset: list[str] | None = None,
        date_range: tuple[str, str] | None = None,
        symbols: list[str] | None = None,
        dry_run: bool = False,
        exit_sweep_params: list[ExitSweepParam] | None = None,
    ) -> list[ExperimentRecord]:
        """Run BacktestEngine for every point in the parameter grid.

        For each grid point:
        1. Compute fingerprint — skip if already in store.
        2. Create ExperimentRecord with RUNNING status.
        3. Invoke BacktestEngine; convert result to MultiObjectiveResult.
        4. Apply pre-filter: expectancy < min or trades < min → FAILED.
        5. Persist record and log progress.

        When *exit_sweep_params* is provided, the grid is the cross-product of
        detection × exit dimensions.  BacktestEngine receives only the
        detection params as ``config_overrides``; the exit params are stored in
        the ExperimentRecord alongside the detection params.

        Args:
            pattern_name: Snake_case or PascalCase pattern name.
            cache_dir: Path to the Databento/Parquet cache directory.
            param_subset: Restrict grid variation to these param names.
            date_range: ``(start_iso, end_iso)`` strings.  Falls back to
                ``backtest_start_date``/``backtest_end_date`` in config.
            symbols: Symbols to include.  ``None`` = BacktestEngine
                auto-detection from cache.
            dry_run: Log grid size and sample configs; skip all backtest runs.
            exit_sweep_params: Optional exit-management parameters to sweep.
                When present, grid includes exit dimensions.

        Returns:
            List of ExperimentRecord for all processed grid points (skipped
            duplicates are excluded).

        Raises:
            ValueError: If date range cannot be resolved.
        """
        grid = self.generate_parameter_grid(pattern_name, param_subset, exit_sweep_params)

        if dry_run:
            sample = grid[:3] if len(grid) > 3 else grid
            logger.info(
                "Dry run: %d grid points for pattern '%s'. Sample configs: %s",
                len(grid),
                pattern_name,
                sample,
            )
            return []

        start_date, end_date = self._resolve_date_range(date_range)
        strategy_type = _PATTERN_TO_STRATEGY_TYPE.get(pattern_name)
        records: list[ExperimentRecord] = []
        total = len(grid)

        for i, params in enumerate(grid):
            # Support both detection-only (flat dict) and exit-sweep (structured dict)
            if "detection_params" in params:
                detection_params: dict[str, Any] = params["detection_params"]
            else:
                detection_params = params

            fingerprint = _compute_fingerprint(params)

            existing = await self._store.get_by_fingerprint(pattern_name, fingerprint)
            if existing is not None:
                logger.info(
                    "[%d/%d] pattern=%s fingerprint=%s status=SKIPPED (already exists)",
                    i + 1,
                    total,
                    pattern_name,
                    fingerprint,
                )
                continue

            now = datetime.now(UTC)
            record = ExperimentRecord(
                experiment_id=generate_id(),
                pattern_name=pattern_name,
                parameter_fingerprint=fingerprint,
                parameters=params,
                status=ExperimentStatus.RUNNING,
                backtest_result=None,
                shadow_trades=0,
                shadow_expectancy=None,
                is_baseline=False,
                created_at=now,
                updated_at=now,
            )

            if strategy_type is None:
                record.status = ExperimentStatus.FAILED
                record.backtest_result = {
                    "error": (
                        f"Pattern '{pattern_name}' is not yet supported by "
                        "BacktestEngine. See DEF-121."
                    )
                }
                record.updated_at = datetime.now(UTC)
                await self._store.save_experiment(record)
                records.append(record)
                logger.info(
                    "[%d/%d] pattern=%s fingerprint=%s status=FAILED (unsupported pattern)",
                    i + 1,
                    total,
                    pattern_name,
                    fingerprint,
                )
                continue

            try:
                engine_config = BacktestEngineConfig(
                    strategy_type=strategy_type,
                    strategy_id=f"strat_{pattern_name}",
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    cache_dir=Path(cache_dir),
                    config_overrides=detection_params,
                )
                engine = BacktestEngine(engine_config)
                result = await engine.run()

                passes_filter = (
                    result.expectancy >= self._min_expectancy
                    and result.total_trades >= self._min_trades
                )

                try:
                    mor = await engine.to_multi_objective_result(
                        result, parameter_hash=fingerprint
                    )
                    backtest_result_dict: dict[str, Any] = mor.to_dict()
                except Exception:
                    logger.warning(
                        "to_multi_objective_result failed for fingerprint=%s — "
                        "storing BacktestResult fields only",
                        fingerprint,
                        exc_info=True,
                    )
                    backtest_result_dict = _backtest_result_to_dict(result)

                record.status = (
                    ExperimentStatus.COMPLETED
                    if passes_filter
                    else ExperimentStatus.FAILED
                )
                record.backtest_result = backtest_result_dict

            except Exception:
                logger.error(
                    "BacktestEngine failed for pattern=%s fingerprint=%s",
                    pattern_name,
                    fingerprint,
                    exc_info=True,
                )
                record.status = ExperimentStatus.FAILED

            record.updated_at = datetime.now(UTC)
            await self._store.save_experiment(record)
            records.append(record)
            logger.info(
                "[%d/%d] pattern=%s fingerprint=%s status=%s",
                i + 1,
                total,
                pattern_name,
                fingerprint,
                record.status,
            )

        return records

    # ---------------------------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------------------------

    def estimate_sweep_time(self, grid_size: int) -> str:
        """Return a human-readable sweep time estimate.

        Uses ~30 seconds per grid point as the baseline.

        Args:
            grid_size: Number of parameter combinations to evaluate.

        Returns:
            Human-readable string, e.g. ``"~25 minutes for 50 grid points"``.
        """
        total_seconds = grid_size * _SECONDS_PER_GRID_POINT
        minutes = total_seconds // 60
        return f"~{minutes} minutes for {grid_size} grid points"

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _resolve_date_range(
        self, date_range: tuple[str, str] | None
    ) -> tuple[date, date]:
        """Resolve start/end dates from argument or config fallback.

        Args:
            date_range: Optional ``(start_iso, end_iso)`` pair from the caller.

        Returns:
            ``(start_date, end_date)`` as ``datetime.date`` objects.

        Raises:
            ValueError: If no date range can be resolved.
        """
        if date_range is not None:
            return (
                date.fromisoformat(date_range[0]),
                date.fromisoformat(date_range[1]),
            )

        start_str = self._config.get("backtest_start_date")
        end_str = self._config.get("backtest_end_date")
        if start_str and end_str:
            return (
                date.fromisoformat(str(start_str)),
                date.fromisoformat(str(end_str)),
            )

        raise ValueError(
            "date_range must be provided as argument or configured via "
            "'backtest_start_date' / 'backtest_end_date' in the experiment config."
        )


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions, no class state)
# ---------------------------------------------------------------------------


def _generate_exit_values(param: ExitSweepParam) -> list[float]:
    """Generate sweep values for a single ExitSweepParam.

    Step-spaced floats from *min_value* to *max_value* (inclusive).

    Args:
        param: ExitSweepParam descriptor.

    Returns:
        List of float values spanning [min_value, max_value] at *step* intervals.
    """
    n_steps = round((param.max_value - param.min_value) / param.step)
    return [round(param.min_value + i * param.step, 6) for i in range(n_steps + 1)]


def _generate_param_values(
    param: PatternParam, param_subset: list[str] | None
) -> list[Any]:
    """Generate the list of values for a single PatternParam.

    Args:
        param: PatternParam descriptor.
        param_subset: If not None, params absent from this list use default only.

    Returns:
        List of values to include for this parameter in the grid.
    """
    if param_subset is not None and param.name not in param_subset:
        return [param.default]

    if param.param_type is bool:
        return [True, False]

    if (
        param.min_value is not None
        and param.max_value is not None
        and param.step is not None
    ):
        if param.param_type is int:
            return list(
                range(int(param.min_value), int(param.max_value) + 1, int(param.step))
            )
        if param.param_type is float:
            n_steps = round((param.max_value - param.min_value) / param.step)
            return [
                round(param.min_value + i * param.step, 6) for i in range(n_steps + 1)
            ]

    return [param.default]


def _compute_fingerprint(params: dict[str, Any]) -> str:
    """Compute a 16-character SHA-256 hex fingerprint of a param dict.

    Deterministic: identical param dicts always produce the same fingerprint.
    Uses canonical JSON (sorted keys, compact separators) to avoid ordering
    artefacts.

    Args:
        params: Detection parameter dict.

    Returns:
        First 16 hex characters of the SHA-256 hash.
    """
    canonical = json.dumps(
        params, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _backtest_result_to_dict(result: object) -> dict[str, Any]:
    """Serialize a BacktestResult dataclass to a JSON-compatible dict.

    Falls back gracefully if the result is not a dataclass.

    Args:
        result: BacktestResult (or any dataclass) to serialize.

    Returns:
        Dict with all fields; ``date``/``datetime`` values are ISO strings.
    """
    import dataclasses  # local import — only called on fallback path

    if not dataclasses.is_dataclass(result) or isinstance(result, type):
        return {}
    raw: dict[str, Any] = dataclasses.asdict(result)  # type: ignore[call-overload]
    return {
        k: v.isoformat() if isinstance(v, (date, datetime)) else v
        for k, v in raw.items()
    }

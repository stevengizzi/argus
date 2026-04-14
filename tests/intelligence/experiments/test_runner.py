"""Tests for ExperimentRunner — Sprint 32 Session 6 + Sprint 31.5 Session 1."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from argus.intelligence.experiments.config import ExperimentConfig
from argus.intelligence.experiments.models import ExperimentRecord, ExperimentStatus
from argus.intelligence.experiments.runner import (
    ExperimentRunner,
    _compute_fingerprint,
    _generate_param_values,
    _run_single_backtest,
)
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule, PatternParam


# ---------------------------------------------------------------------------
# Minimal pattern fixtures
# ---------------------------------------------------------------------------


class _TwoParamPattern(PatternModule):
    """Minimal pattern with one int param and one float param.

    int_param:   range(2, 4+1, 2) → [2, 4]   (2 values)
    float_param: 0.1 to 0.3 step 0.1         → [0.1, 0.2, 0.3] (3 values)

    Full grid: 2 × 3 = 6 points.
    """

    @property
    def name(self) -> str:
        return "two_param"

    @property
    def lookback_bars(self) -> int:
        return 5

    def detect(
        self, candles: list[CandleBar], indicators: dict[str, float]
    ) -> PatternDetection | None:
        return None

    def score(self, detection: PatternDetection) -> float:
        return 0.0

    def get_default_params(self) -> list[PatternParam]:
        return [
            PatternParam(
                name="int_param",
                param_type=int,
                default=4,
                min_value=2,
                max_value=4,  # range(2, 5, 2) → [2, 4]
                step=2,
            ),
            PatternParam(
                name="float_param",
                param_type=float,
                default=0.2,
                min_value=0.1,
                max_value=0.3,
                step=0.1,
            ),
        ]


class _LargeGridPattern(PatternModule):
    """Pattern whose full grid exceeds the 500-point cap."""

    @property
    def name(self) -> str:
        return "large_grid"

    @property
    def lookback_bars(self) -> int:
        return 5

    def detect(
        self, candles: list[CandleBar], indicators: dict[str, float]
    ) -> PatternDetection | None:
        return None

    def score(self, detection: PatternDetection) -> float:
        return 0.0

    def get_default_params(self) -> list[PatternParam]:
        # 10 × 10 × 6 = 600 > 500
        return [
            PatternParam(
                name="param_a",
                param_type=int,
                default=5,
                min_value=1,
                max_value=10,
                step=1,
            ),
            PatternParam(
                name="param_b",
                param_type=int,
                default=5,
                min_value=1,
                max_value=10,
                step=1,
            ),
            PatternParam(
                name="param_c",
                param_type=int,
                default=3,
                min_value=1,
                max_value=6,
                step=1,
            ),
        ]


class _BoolAndStringPattern(PatternModule):
    """Pattern with a bool param and a string param (no range)."""

    @property
    def name(self) -> str:
        return "bool_string"

    @property
    def lookback_bars(self) -> int:
        return 5

    def detect(
        self, candles: list[CandleBar], indicators: dict[str, float]
    ) -> PatternDetection | None:
        return None

    def score(self, detection: PatternDetection) -> float:
        return 0.0

    def get_default_params(self) -> list[PatternParam]:
        return [
            PatternParam(
                name="flag_strict",
                param_type=bool,
                default=True,
            ),
            PatternParam(
                name="entry_mode",
                param_type=str,
                default="breakout",
            ),
        ]


# ---------------------------------------------------------------------------
# Store mock helpers
# ---------------------------------------------------------------------------


def _make_store_mock(existing_records: list[ExperimentRecord] | None = None) -> MagicMock:
    """Build an AsyncMock-backed ExperimentStore."""
    records = existing_records or []

    async def _get_by_fingerprint(
        pattern_name: str, fingerprint: str
    ) -> ExperimentRecord | None:
        for r in records:
            if r.pattern_name == pattern_name and r.parameter_fingerprint == fingerprint:
                return r
        return None

    store = MagicMock()
    store.list_experiments = AsyncMock(return_value=records)
    store.get_by_fingerprint = _get_by_fingerprint
    store.save_experiment = AsyncMock(return_value=None)
    return store


# ---------------------------------------------------------------------------
# BacktestEngine mock helpers
# ---------------------------------------------------------------------------


def _make_engine_mock(
    expectancy: float = 0.5,
    total_trades: int = 20,
) -> MagicMock:
    """Return a mock BacktestEngine with a configured result."""
    result = MagicMock()
    result.expectancy = expectancy
    result.total_trades = total_trades

    mor = MagicMock()
    mor.to_dict.return_value = {
        "expectancy_per_trade": expectancy,
        "total_trades": total_trades,
    }

    engine = MagicMock()
    engine.run = AsyncMock(return_value=result)
    engine.to_multi_objective_result = AsyncMock(return_value=mor)
    return engine


# ---------------------------------------------------------------------------
# _generate_param_values unit tests
# ---------------------------------------------------------------------------


def test_int_param_produces_int_values() -> None:
    param = PatternParam(
        name="bars",
        param_type=int,
        default=5,
        min_value=3,
        max_value=9,
        step=3,
    )
    values = _generate_param_values(param, param_subset=None)
    assert values == [3, 6, 9]
    assert all(isinstance(v, int) for v in values)


def test_float_param_produces_float_values() -> None:
    param = PatternParam(
        name="ratio",
        param_type=float,
        default=0.5,
        min_value=0.2,
        max_value=0.8,
        step=0.2,
    )
    values = _generate_param_values(param, param_subset=None)
    assert len(values) == 4  # 0.2, 0.4, 0.6, 0.8
    assert all(isinstance(v, float) for v in values)
    assert pytest.approx(values[0]) == 0.2
    assert pytest.approx(values[-1]) == 0.8


def test_bool_param_produces_true_and_false() -> None:
    param = PatternParam(
        name="strict",
        param_type=bool,
        default=True,
    )
    values = _generate_param_values(param, param_subset=None)
    assert set(values) == {True, False}


def test_string_param_uses_default_only() -> None:
    param = PatternParam(
        name="mode",
        param_type=str,
        default="breakout",
    )
    values = _generate_param_values(param, param_subset=None)
    assert values == ["breakout"]


def test_param_not_in_subset_uses_default() -> None:
    param = PatternParam(
        name="bars",
        param_type=int,
        default=5,
        min_value=3,
        max_value=9,
        step=3,
    )
    values = _generate_param_values(param, param_subset=["other_param"])
    assert values == [5]


# ---------------------------------------------------------------------------
# generate_parameter_grid tests
# ---------------------------------------------------------------------------


def _runner_with_mock(pattern_class: type[PatternModule]) -> ExperimentRunner:
    """Return an ExperimentRunner whose get_pattern_class is patched."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 5,
            "backtest_start_date": "2025-01-01",
            "backtest_end_date": "2025-12-31",
        },
    )
    return runner


def test_grid_basic_size() -> None:
    """TwoParamPattern → int [2,4] × float [0.1,0.2,0.3] = 6 combos."""
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid = runner.generate_parameter_grid("two_param")

    assert len(grid) == 6
    for point in grid:
        assert "int_param" in point
        assert "float_param" in point


def test_grid_int_values_are_ints() -> None:
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid = runner.generate_parameter_grid("two_param")

    int_values = sorted({p["int_param"] for p in grid})
    assert int_values == [2, 4]
    assert all(isinstance(v, int) for v in int_values)


def test_grid_float_values_are_floats() -> None:
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid = runner.generate_parameter_grid("two_param")

    float_values = sorted({p["float_param"] for p in grid})
    assert all(isinstance(v, float) for v in float_values)
    assert pytest.approx(float_values[0]) == 0.1
    assert pytest.approx(float_values[-1]) == 0.3


def test_grid_param_subset_limits_variation() -> None:
    """With param_subset=['int_param'], float_param uses default only → 2 combos."""
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid = runner.generate_parameter_grid("two_param", param_subset=["int_param"])

    assert len(grid) == 2  # only int_param varied: [2, 4]
    float_vals = {p["float_param"] for p in grid}
    assert float_vals == {0.2}  # default


def test_grid_cap_warning_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Grid > 500 points logs a WARNING."""
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_LargeGridPattern,
    ):
        with caplog.at_level("WARNING", logger="argus.intelligence.experiments.runner"):
            grid = runner.generate_parameter_grid("large_grid")

    # 10 × 10 × 6 = 600 > 500
    assert len(grid) == 600
    assert any("cap=" in r.message for r in caplog.records)


def test_grid_is_deterministic() -> None:
    """Same call produces identical grid order."""
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid_a = runner.generate_parameter_grid("two_param")
        grid_b = runner.generate_parameter_grid("two_param")

    assert grid_a == grid_b


def test_grid_bull_flag_exceeds_cap_and_warns(caplog: pytest.LogCaptureFixture) -> None:
    """BullFlagPattern's full grid is >> 500 and triggers a WARNING."""
    from argus.strategies.patterns.bull_flag import BullFlagPattern

    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    with caplog.at_level("WARNING", logger="argus.intelligence.experiments.runner"):
        grid = runner.generate_parameter_grid("bull_flag")

    assert len(grid) > 500
    assert any("cap=" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# run_sweep tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_records_created_and_stored() -> None:
    """Sweep with a 1-point grid creates one ExperimentRecord in the store."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
        },
    )

    mock_engine = _make_engine_mock(expectancy=0.8, total_trades=15)

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            return_value=mock_engine,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
        )

    assert len(records) == 1
    store.save_experiment.assert_called_once()


@pytest.mark.asyncio
async def test_sweep_prefilter_negative_expectancy_yields_failed() -> None:
    """Negative expectancy → ExperimentStatus.FAILED."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={"backtest_min_expectancy": 0.1, "backtest_min_trades": 1},
    )

    mock_engine = _make_engine_mock(expectancy=-0.5, total_trades=20)

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            return_value=mock_engine,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
        )

    assert len(records) == 1
    assert records[0].status == ExperimentStatus.FAILED


@pytest.mark.asyncio
async def test_sweep_prefilter_insufficient_trades_yields_failed() -> None:
    """Trade count below threshold → ExperimentStatus.FAILED."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={"backtest_min_expectancy": 0.0, "backtest_min_trades": 30},
    )

    mock_engine = _make_engine_mock(expectancy=0.8, total_trades=5)

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            return_value=mock_engine,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
        )

    assert len(records) == 1
    assert records[0].status == ExperimentStatus.FAILED


@pytest.mark.asyncio
async def test_sweep_prefilter_passing_config_yields_completed() -> None:
    """Passing expectancy and trade count → ExperimentStatus.COMPLETED."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={"backtest_min_expectancy": 0.1, "backtest_min_trades": 10},
    )

    mock_engine = _make_engine_mock(expectancy=0.5, total_trades=25)

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            return_value=mock_engine,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
        )

    assert len(records) == 1
    assert records[0].status == ExperimentStatus.COMPLETED


@pytest.mark.asyncio
async def test_dry_run_makes_no_engine_calls() -> None:
    """Dry run logs but does not invoke BacktestEngine."""
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    engine_cls = MagicMock()

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            engine_cls,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="two_param",
            cache_dir="/tmp/cache",
            date_range=("2025-01-01", "2025-12-31"),
            dry_run=True,
        )

    assert records == []
    engine_cls.assert_not_called()
    store.save_experiment.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_fingerprint_is_skipped() -> None:
    """A fingerprint already in the store is skipped (not re-run)."""
    now = datetime.now(UTC)
    existing = ExperimentRecord(
        experiment_id="existing-id",
        pattern_name="bull_flag",
        # Pre-compute the fingerprint that param_subset=[] would produce for
        # _TwoParamPattern defaults: {int_param: 4, float_param: 0.2}
        parameter_fingerprint=_compute_fingerprint(
            {"int_param": 4, "float_param": 0.2}
        ),
        parameters={"int_param": 4, "float_param": 0.2},
        status=ExperimentStatus.COMPLETED,
        backtest_result=None,
        shadow_trades=0,
        shadow_expectancy=None,
        is_baseline=False,
        created_at=now,
        updated_at=now,
    )

    store = _make_store_mock(existing_records=[existing])
    runner = ExperimentRunner(
        store=store,
        config={"backtest_min_expectancy": 0.0, "backtest_min_trades": 1},
    )

    engine_cls = MagicMock()

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            engine_cls,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
        )

    # Grid has 1 point (param_subset=[]), already exists → skipped
    assert records == []
    engine_cls.assert_not_called()
    store.save_experiment.assert_not_called()


@pytest.mark.asyncio
async def test_backtest_engine_exception_yields_failed() -> None:
    """BacktestEngine.run() raising an exception → ExperimentStatus.FAILED."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={"backtest_min_expectancy": 0.0, "backtest_min_trades": 1},
    )

    engine = MagicMock()
    engine.run = AsyncMock(side_effect=RuntimeError("simulated engine failure"))

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            return_value=engine,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
        )

    assert len(records) == 1
    assert records[0].status == ExperimentStatus.FAILED


# ---------------------------------------------------------------------------
# estimate_sweep_time
# ---------------------------------------------------------------------------


def test_estimate_sweep_time_formatting() -> None:
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    result = runner.estimate_sweep_time(50)
    assert "25" in result
    assert "50" in result


def test_estimate_sweep_time_zero_grid() -> None:
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    result = runner.estimate_sweep_time(0)
    assert "0" in result


# ---------------------------------------------------------------------------
# Integration tests — registry completeness (Sprint 31A S6)
# ---------------------------------------------------------------------------


def test_all_ten_strategy_types_in_pattern_to_strategy_type_map() -> None:
    """All 10 PatternModule patterns must be registered in _PATTERN_TO_STRATEGY_TYPE.

    Verifies that the ExperimentRunner can dispatch any pattern to a BacktestEngine
    StrategyType. This guards against adding a new pattern (factory + registry) without
    wiring the runner map — which would cause every sweep to silently FAIL.
    """
    from argus.backtest.config import StrategyType
    from argus.intelligence.experiments.runner import _PATTERN_TO_STRATEGY_TYPE
    from argus.strategies.patterns.factory import _SNAKE_CASE_ALIASES

    pattern_names = set(_SNAKE_CASE_ALIASES.keys())
    assert len(pattern_names) == 10, (  # noqa: PLR2004
        f"Expected 10 patterns in _SNAKE_CASE_ALIASES, got {len(pattern_names)}"
    )

    missing = pattern_names - set(_PATTERN_TO_STRATEGY_TYPE.keys())
    assert not missing, (
        f"Patterns missing from _PATTERN_TO_STRATEGY_TYPE: {sorted(missing)}"
    )

    # All mapped values must be valid StrategyType members
    for name, st in _PATTERN_TO_STRATEGY_TYPE.items():
        assert isinstance(st, StrategyType), (
            f"Mapped value for '{name}' is not a StrategyType: {st!r}"
        )


def test_all_ten_patterns_in_pattern_registry() -> None:
    """All 10 PatternModule patterns must have an entry in _PATTERN_REGISTRY.

    Ensures every pattern is importable via get_pattern_class() — the primary
    factory entrypoint used by ExperimentRunner and build_pattern_from_config().
    Also verifies each registered class is a concrete PatternModule subclass.
    """
    from argus.strategies.patterns.base import PatternModule
    from argus.strategies.patterns.factory import (
        _PATTERN_REGISTRY,
        _SNAKE_CASE_ALIASES,
        get_pattern_class,
    )

    expected_pascal = set(_SNAKE_CASE_ALIASES.values())
    assert len(expected_pascal) == 10, (  # noqa: PLR2004
        f"Expected 10 patterns, got {len(expected_pascal)}"
    )

    missing = expected_pascal - set(_PATTERN_REGISTRY.keys())
    assert not missing, (
        f"Patterns missing from _PATTERN_REGISTRY: {sorted(missing)}"
    )

    # Each alias must resolve to a concrete PatternModule subclass
    for snake_name in _SNAKE_CASE_ALIASES:
        cls = get_pattern_class(snake_name)
        assert issubclass(cls, PatternModule), (
            f"get_pattern_class('{snake_name}') returned non-PatternModule: {cls!r}"
        )
        # Must be instantiable with no arguments
        instance = cls()
        assert isinstance(instance.get_default_params(), list)


def test_experiments_yaml_loads_without_parse_error() -> None:
    """config/experiments.yaml must be valid YAML and pass ExperimentConfig validation.

    Catches syntax errors, duplicate keys, and Pydantic field mismatches that
    would silently break the experiment pipeline at startup.
    """
    from pathlib import Path

    import yaml

    from argus.intelligence.experiments.config import ExperimentConfig

    yaml_path = Path("config/experiments.yaml")
    assert yaml_path.exists(), "config/experiments.yaml not found"

    raw = yaml.safe_load(yaml_path.read_text())
    assert isinstance(raw, dict), "experiments.yaml must be a YAML mapping at the top level"

    # Pydantic validation — will raise ValidationError on field mismatches
    config = ExperimentConfig(**raw)
    assert config.enabled is True or config.enabled is False


# ---------------------------------------------------------------------------
# Sprint 31.5 S1 — Parallel Sweep Infrastructure tests
# ---------------------------------------------------------------------------


def _mock_worker_result(args_dict: dict) -> dict:
    """Synchronous mock for _run_single_backtest — returns a completed result."""
    return {
        "fingerprint": args_dict["fingerprint"],
        "experiment_id": args_dict["experiment_id"],
        "created_at": args_dict["created_at"],
        "params": args_dict["params"],
        "pattern_name": args_dict["pattern_name"],
        "status": "completed",
        "backtest_result": {"expectancy_per_trade": 0.5, "total_trades": 20},
        "error": None,
    }


def _mock_worker_fail(args_dict: dict) -> dict:
    """Synchronous mock for _run_single_backtest — always returns failed."""
    return {
        "fingerprint": args_dict["fingerprint"],
        "experiment_id": args_dict["experiment_id"],
        "created_at": args_dict["created_at"],
        "params": args_dict["params"],
        "pattern_name": args_dict["pattern_name"],
        "status": "failed",
        "backtest_result": None,
        "error": "simulated worker failure",
    }


# 1. test_run_sweep_parallel_distributes_work
@pytest.mark.asyncio
async def test_run_sweep_parallel_distributes_work() -> None:
    """workers=2: all 4 grid points complete when workers > 1."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
            "backtest_start_date": "2025-01-01",
            "backtest_end_date": "2025-12-31",
        },
    )

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner._run_single_backtest",
            side_effect=_mock_worker_result,
        ),
        patch(
            "argus.intelligence.experiments.runner.ProcessPoolExecutor",
            ThreadPoolExecutor,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=["int_param"],
            date_range=("2025-01-01", "2025-12-31"),
            workers=2,
        )

    # _TwoParamPattern with param_subset=["int_param"] → 2 grid points
    assert len(records) == 2
    assert all(r.status == ExperimentStatus.COMPLETED for r in records)
    assert store.save_experiment.call_count == 2


# 2. test_run_sweep_parallel_worker_error_isolated
@pytest.mark.asyncio
async def test_run_sweep_parallel_worker_error_isolated() -> None:
    """A failed worker result yields FAILED status; other grid points unaffected."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
            "backtest_start_date": "2025-01-01",
            "backtest_end_date": "2025-12-31",
        },
    )

    call_count: list[int] = [0]

    def _alternating_worker(args_dict: dict) -> dict:
        call_count[0] += 1
        if call_count[0] == 1:
            return _mock_worker_fail(args_dict)
        return _mock_worker_result(args_dict)

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner._run_single_backtest",
            side_effect=_alternating_worker,
        ),
        patch(
            "argus.intelligence.experiments.runner.ProcessPoolExecutor",
            ThreadPoolExecutor,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=["int_param"],
            date_range=("2025-01-01", "2025-12-31"),
            workers=2,
        )

    assert len(records) == 2
    statuses = {r.status for r in records}
    assert ExperimentStatus.FAILED in statuses
    assert ExperimentStatus.COMPLETED in statuses


# 3. test_run_sweep_sequential_identical
@pytest.mark.asyncio
async def test_run_sweep_sequential_identical() -> None:
    """workers=1 uses sequential path and produces the same record structure."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
        },
    )

    mock_engine = _make_engine_mock(expectancy=0.5, total_trades=20)

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.BacktestEngine",
            return_value=mock_engine,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=[],
            date_range=("2025-01-01", "2025-12-31"),
            workers=1,
        )

    assert len(records) == 1
    assert records[0].status == ExperimentStatus.COMPLETED
    store.save_experiment.assert_called_once()


# 4. test_run_sweep_parallel_skips_existing_fingerprints
@pytest.mark.asyncio
async def test_run_sweep_parallel_skips_existing_fingerprints() -> None:
    """Parallel path: fingerprints already in store are skipped before dispatch."""
    now = datetime.now(UTC)
    # Pre-compute both fingerprints _TwoParamPattern with param_subset=["int_param"] produces
    fp_int2 = _compute_fingerprint({"int_param": 2, "float_param": 0.2})
    fp_int4 = _compute_fingerprint({"int_param": 4, "float_param": 0.2})
    existing_records = [
        ExperimentRecord(
            experiment_id="existing-1",
            pattern_name="bull_flag",
            parameter_fingerprint=fp_int2,
            parameters={"int_param": 2, "float_param": 0.2},
            status=ExperimentStatus.COMPLETED,
            backtest_result=None,
            shadow_trades=0,
            shadow_expectancy=None,
            is_baseline=False,
            created_at=now,
            updated_at=now,
        ),
        ExperimentRecord(
            experiment_id="existing-2",
            pattern_name="bull_flag",
            parameter_fingerprint=fp_int4,
            parameters={"int_param": 4, "float_param": 0.2},
            status=ExperimentStatus.COMPLETED,
            backtest_result=None,
            shadow_trades=0,
            shadow_expectancy=None,
            is_baseline=False,
            created_at=now,
            updated_at=now,
        ),
    ]

    store = _make_store_mock(existing_records=existing_records)
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
        },
    )

    worker_cls = MagicMock()

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner._run_single_backtest",
            side_effect=_mock_worker_result,
        ),
        patch(
            "argus.intelligence.experiments.runner.ProcessPoolExecutor",
            ThreadPoolExecutor,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=["int_param"],
            date_range=("2025-01-01", "2025-12-31"),
            workers=2,
        )

    # Both fingerprints exist → nothing dispatched, no records created
    assert records == []
    store.save_experiment.assert_not_called()


# 5. test_run_sweep_dry_run_no_workers
@pytest.mark.asyncio
async def test_run_sweep_dry_run_no_workers() -> None:
    """dry_run=True with workers > 1 returns empty list without spawning processes."""
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    executor_cls = MagicMock()

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner.ProcessPoolExecutor",
            executor_cls,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="two_param",
            cache_dir="/tmp/cache",
            date_range=("2025-01-01", "2025-12-31"),
            dry_run=True,
            workers=4,
        )

    assert records == []
    executor_cls.assert_not_called()
    store.save_experiment.assert_not_called()


# 6. test_run_sweep_parallel_store_writes_main_process
@pytest.mark.asyncio
async def test_run_sweep_parallel_store_writes_main_process() -> None:
    """store.save_experiment is called for each completed future in main process."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
            "backtest_start_date": "2025-01-01",
            "backtest_end_date": "2025-12-31",
        },
    )

    with (
        patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ),
        patch(
            "argus.intelligence.experiments.runner._run_single_backtest",
            side_effect=_mock_worker_result,
        ),
        patch(
            "argus.intelligence.experiments.runner.ProcessPoolExecutor",
            ThreadPoolExecutor,
        ),
    ):
        records = await runner.run_sweep(
            pattern_name="bull_flag",
            cache_dir="/tmp/cache",
            param_subset=["int_param"],
            date_range=("2025-01-01", "2025-12-31"),
            workers=3,
        )

    # 2 grid points → 2 store writes, all from main process (ThreadPoolExecutor is sync)
    assert store.save_experiment.call_count == len(records)
    assert all(isinstance(r, ExperimentRecord) for r in records)


# 7. test_config_max_workers_field
def test_config_max_workers_field() -> None:
    """ExperimentConfig.max_workers validates correctly."""
    # Default
    cfg = ExperimentConfig()
    assert cfg.max_workers == 4

    # Explicit valid
    cfg2 = ExperimentConfig(max_workers=8)
    assert cfg2.max_workers == 8

    # Below lower bound
    with pytest.raises(ValidationError):
        ExperimentConfig(max_workers=0)

    # Above upper bound
    with pytest.raises(ValidationError):
        ExperimentConfig(max_workers=33)


# 8. test_run_single_backtest_returns_dict
def test_run_single_backtest_returns_dict() -> None:
    """_run_single_backtest returns a correctly structured dict."""
    mock_result = MagicMock()
    mock_result.expectancy = 0.8
    mock_result.total_trades = 30

    mock_mor = MagicMock()
    mock_mor.to_dict.return_value = {"expectancy_per_trade": 0.8, "total_trades": 30}

    mock_engine_instance = MagicMock()
    mock_engine_instance.run = AsyncMock(return_value=mock_result)
    mock_engine_instance.to_multi_objective_result = AsyncMock(return_value=mock_mor)

    args: dict[str, Any] = {
        "strategy_type_value": "bull_flag",
        "strategy_id": "strat_bull_flag",
        "symbols": None,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "cache_dir": "/tmp/cache",
        "detection_params": {},
        "params": {"int_param": 4},
        "fingerprint": "abc123def456abcd",
        "pattern_name": "bull_flag",
        "min_expectancy": 0.0,
        "min_trades": 10,
        "experiment_id": "test-experiment-id",
        "created_at": "2025-01-01T00:00:00+00:00",
    }

    with patch(
        "argus.backtest.engine.BacktestEngine",
        return_value=mock_engine_instance,
    ):
        result = _run_single_backtest(args)

    assert isinstance(result, dict)
    assert result["fingerprint"] == "abc123def456abcd"
    assert result["experiment_id"] == "test-experiment-id"
    assert result["pattern_name"] == "bull_flag"
    assert result["status"] in ("completed", "failed")
    assert "backtest_result" in result
    assert "error" in result
    assert result["params"] == {"int_param": 4}


def test_run_single_backtest_passes_fingerprint() -> None:
    """_run_single_backtest passes config_fingerprint=fingerprint to BacktestEngineConfig (DEF-153)."""
    from argus.backtest.config import BacktestEngineConfig  # noqa: PLC0415

    captured_configs: list[BacktestEngineConfig] = []

    mock_result = MagicMock()
    mock_result.expectancy = 0.8
    mock_result.total_trades = 30

    mock_mor = MagicMock()
    mock_mor.to_dict.return_value = {"expectancy_per_trade": 0.8, "total_trades": 30}

    def _capture_engine(config: BacktestEngineConfig) -> MagicMock:
        captured_configs.append(config)
        instance = MagicMock()
        instance.run = AsyncMock(return_value=mock_result)
        instance.to_multi_objective_result = AsyncMock(return_value=mock_mor)
        return instance

    expected_fingerprint = "cafebabe12345678"

    args: dict[str, Any] = {
        "strategy_type_value": "bull_flag",
        "strategy_id": "strat_bull_flag",
        "symbols": None,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "cache_dir": "/tmp/cache",
        "detection_params": {},
        "params": {"int_param": 4},
        "fingerprint": expected_fingerprint,
        "pattern_name": "bull_flag",
        "min_expectancy": 0.0,
        "min_trades": 10,
        "experiment_id": "test-experiment-id",
        "created_at": "2025-01-01T00:00:00+00:00",
    }

    with patch(
        "argus.backtest.engine.BacktestEngine",
        side_effect=_capture_engine,
    ):
        _run_single_backtest(args)

    assert len(captured_configs) == 1
    assert captured_configs[0].config_fingerprint == expected_fingerprint


# ---------------------------------------------------------------------------
# Sprint 31.5 S2 — Universe filter tests (DEF-146)
# ---------------------------------------------------------------------------


import pandas as pd  # noqa: E402 — kept here to keep imports close to usage

from argus.core.config import UniverseFilterConfig  # noqa: E402


def _make_service_mock(
    is_available: bool = True,
    query_symbols: list[str] | None = None,
    coverage: dict[str, bool] | None = None,
    available_symbols: list[str] | None = None,
) -> MagicMock:
    """Build a mock HistoricalQueryService for universe filter tests."""
    service = MagicMock()
    service.is_available = is_available

    if query_symbols is not None:
        df = pd.DataFrame(
            {
                "symbol": query_symbols,
                "avg_price": [50.0] * len(query_symbols),
                "avg_volume": [500_000] * len(query_symbols),
            }
        )
    else:
        df = pd.DataFrame(columns=["symbol", "avg_price", "avg_volume"])
    service.query.return_value = df

    service.validate_symbol_coverage.return_value = (
        coverage if coverage is not None else {}
    )
    service.get_available_symbols.return_value = (
        available_symbols if available_symbols is not None else []
    )
    return service


# 1. test_run_sweep_with_universe_filter_resolves_symbols
@pytest.mark.asyncio
async def test_run_sweep_with_universe_filter_resolves_symbols() -> None:
    """When universe_filter is provided, run_sweep() calls _resolve_universe_symbols().

    Verifies that the resolved symbol list replaces the original None, and that
    _resolve_universe_symbols() receives the correct arguments.
    """
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
            "backtest_start_date": "2025-01-01",
            "backtest_end_date": "2025-12-31",
        },
    )

    universe_filter = UniverseFilterConfig(min_avg_volume=300_000)
    resolved = ["AAPL", "NVDA"]

    with patch.object(runner, "_resolve_universe_symbols", return_value=resolved) as mock_resolve:
        with patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ):
            with patch(
                "argus.intelligence.experiments.runner.BacktestEngine",
                return_value=_make_engine_mock(),
            ):
                await runner.run_sweep(
                    pattern_name="bull_flag",
                    cache_dir="/tmp/cache",
                    param_subset=[],
                    date_range=("2025-01-01", "2025-12-31"),
                    universe_filter=universe_filter,
                )

    mock_resolve.assert_called_once_with(
        universe_filter=universe_filter,
        cache_dir="/tmp/cache",
        start_date="2025-01-01",
        end_date="2025-12-31",
        candidate_symbols=None,
    )


# 2. test_run_sweep_universe_filter_with_candidate_symbols
@pytest.mark.asyncio
async def test_run_sweep_universe_filter_with_candidate_symbols() -> None:
    """When both symbols and universe_filter are provided, candidate_symbols is passed to resolver.

    Ensures the runner passes the user-supplied symbol list as the candidate set
    so _resolve_universe_symbols() applies the filter only within that set.
    """
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={
            "backtest_min_expectancy": 0.0,
            "backtest_min_trades": 1,
            "backtest_start_date": "2025-01-01",
            "backtest_end_date": "2025-12-31",
        },
    )

    universe_filter = UniverseFilterConfig(min_price=10.0)
    candidate = ["AAPL", "TSLA", "NVDA"]
    resolved = ["AAPL", "NVDA"]

    with patch.object(runner, "_resolve_universe_symbols", return_value=resolved) as mock_resolve:
        with patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ):
            with patch(
                "argus.intelligence.experiments.runner.BacktestEngine",
                return_value=_make_engine_mock(),
            ):
                await runner.run_sweep(
                    pattern_name="bull_flag",
                    cache_dir="/tmp/cache",
                    param_subset=[],
                    date_range=("2025-01-01", "2025-12-31"),
                    symbols=candidate,
                    universe_filter=universe_filter,
                )

    mock_resolve.assert_called_once_with(
        universe_filter=universe_filter,
        cache_dir="/tmp/cache",
        start_date="2025-01-01",
        end_date="2025-12-31",
        candidate_symbols=candidate,
    )


# 3. test_run_sweep_universe_filter_zero_symbols_raises
@pytest.mark.asyncio
async def test_run_sweep_universe_filter_zero_symbols_raises() -> None:
    """_resolve_universe_symbols() returning [] causes run_sweep() to raise ValueError."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={"backtest_start_date": "2025-01-01", "backtest_end_date": "2025-12-31"},
    )

    universe_filter = UniverseFilterConfig(min_price=9999.0)  # impossible threshold

    with patch.object(runner, "_resolve_universe_symbols", return_value=[]):
        with patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ):
            with pytest.raises(ValueError, match="No symbols remaining"):
                await runner.run_sweep(
                    pattern_name="bull_flag",
                    cache_dir="/tmp/cache",
                    param_subset=[],
                    date_range=("2025-01-01", "2025-12-31"),
                    universe_filter=universe_filter,
                )


# 4. test_run_sweep_universe_filter_service_unavailable_raises
@pytest.mark.asyncio
async def test_run_sweep_universe_filter_service_unavailable_raises() -> None:
    """When HistoricalQueryService is unavailable, run_sweep() raises ValueError."""
    store = _make_store_mock()
    runner = ExperimentRunner(
        store=store,
        config={"backtest_start_date": "2025-01-01", "backtest_end_date": "2025-12-31"},
    )

    universe_filter = UniverseFilterConfig(min_avg_volume=100_000)
    unavailable_service = _make_service_mock(is_available=False)

    with patch(
        "argus.data.historical_query_service.HistoricalQueryService",
        return_value=unavailable_service,
    ):
        with patch(
            "argus.intelligence.experiments.runner.get_pattern_class",
            return_value=_TwoParamPattern,
        ):
            with pytest.raises(ValueError, match="unavailable"):
                await runner.run_sweep(
                    pattern_name="bull_flag",
                    cache_dir="/tmp/cache",
                    param_subset=[],
                    date_range=("2025-01-01", "2025-12-31"),
                    universe_filter=universe_filter,
                )


# 5. test_resolve_universe_symbols_static_filters
def test_resolve_universe_symbols_static_filters() -> None:
    """_resolve_universe_symbols() builds the correct SQL HAVING clauses and returns filtered symbols.

    Verifies:
    - Static filters (min_price, max_price, min_avg_volume) appear in the HAVING clause.
    - Coverage validation is called on the filtered symbol list.
    - Service is closed after use.
    - Returned list matches the symbols that pass both filter and coverage.
    """
    store = _make_store_mock()
    runner = ExperimentRunner(store=store, config={})

    filter_cfg = UniverseFilterConfig(min_price=5.0, max_price=200.0, min_avg_volume=300_000)
    service = _make_service_mock(
        is_available=True,
        query_symbols=["AAPL", "NVDA"],
        coverage={"AAPL": True, "NVDA": False},
        available_symbols=["AAPL", "MSFT", "NVDA", "TSLA"],
    )

    with patch(
        "argus.data.historical_query_service.HistoricalQueryService",
        return_value=service,
    ):
        result = runner._resolve_universe_symbols(
            universe_filter=filter_cfg,
            cache_dir="/tmp/cache",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )

    # Only AAPL passes coverage validation (NVDA=False)
    assert result == ["AAPL"]

    # Static filters must appear in the SQL query
    query_sql: str = service.query.call_args[0][0]
    assert "AVG(close) >= 5.0" in query_sql
    assert "AVG(close) <= 200.0" in query_sql
    assert "AVG(volume) >= 300000" in query_sql

    # Coverage validation called on filtered symbols
    service.validate_symbol_coverage.assert_called_once_with(
        ["AAPL", "NVDA"], "2025-01-01", "2025-12-31", min_bars=100
    )

    # Service must be closed after use
    service.close.assert_called_once()


# 6. test_cli_delegates_filter_to_runner
@pytest.mark.asyncio
async def test_cli_delegates_filter_to_runner() -> None:
    """When --universe-filter is active, CLI passes universe_filter to run_sweep().

    Verifies that the main run() path does NOT call _apply_universe_filter() inline
    but instead delegates filtering to the runner via the universe_filter argument.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from scripts.run_experiment import _apply_universe_filter, run

    args = MagicMock()
    args.pattern = "narrow_range_breakout"
    args.cache_dir = None
    args.params = None
    args.dry_run = False
    args.date_range = "2025-01-01,2025-12-31"
    args.symbols = None
    args.universe_filter = "narrow_range_breakout"

    # Capture the universe_filter kwarg that run_sweep() receives
    received_filter: list[object] = []

    async def _fake_run_sweep(**kwargs: object) -> list:
        received_filter.append(kwargs.get("universe_filter"))
        return []

    with (
        patch("scripts.run_experiment.ExperimentStore"),
        patch("scripts.run_experiment.ExperimentRunner") as mock_runner_cls,
        patch("scripts.run_experiment._apply_universe_filter") as mock_inline_filter,
    ):
        mock_runner_instance = MagicMock()
        mock_runner_instance.generate_parameter_grid.return_value = [{"p": 1}]
        mock_runner_instance.estimate_sweep_time.return_value = "~0 minutes for 1 grid points"
        mock_runner_instance.run_sweep = AsyncMock(side_effect=_fake_run_sweep)
        mock_runner_cls.return_value = mock_runner_instance

        store_instance = MagicMock()
        store_instance.initialize = AsyncMock()
        patch("scripts.run_experiment.ExperimentStore", return_value=store_instance).start()

        await run(args)

    # universe_filter must be a UniverseFilterConfig (not None)
    assert len(received_filter) == 1
    assert isinstance(received_filter[0], UniverseFilterConfig)

    # Inline filter function must NOT have been called
    mock_inline_filter.assert_not_called()

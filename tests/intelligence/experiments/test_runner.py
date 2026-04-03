"""Tests for ExperimentRunner — Sprint 32 Session 6."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.intelligence.experiments.models import ExperimentRecord, ExperimentStatus
from argus.intelligence.experiments.runner import (
    ExperimentRunner,
    _compute_fingerprint,
    _generate_param_values,
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

"""Tests for Sprint 32.5 S2: exit_overrides in spawner + exit sweep grid in runner."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import BullFlagConfig, deep_update
from argus.intelligence.experiments import ExperimentStore, VariantDefinition
from argus.intelligence.experiments.config import ExitSweepParam
from argus.intelligence.experiments.runner import (
    ExperimentRunner,
    _compute_fingerprint,
    _generate_exit_values,
)
from argus.intelligence.experiments.spawner import VariantSpawner, _dotpath_to_nested
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule, PatternParam
from argus.strategies.patterns.factory import (
    build_pattern_from_config,
    compute_parameter_fingerprint,
    get_pattern_class,
)
from argus.strategies.pattern_strategy import PatternBasedStrategy


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_bull_flag_config(**overrides: object) -> BullFlagConfig:
    fields: dict[str, object] = {"strategy_id": "strat_bull_flag", "name": "Bull Flag"}
    fields.update(overrides)
    return BullFlagConfig(**fields)  # type: ignore[arg-type]


def _make_bull_flag_strategy(config: BullFlagConfig) -> PatternBasedStrategy:
    pattern = build_pattern_from_config(config, "bull_flag")
    return PatternBasedStrategy(pattern=pattern, config=config)


@pytest.fixture
async def store(tmp_path: object) -> ExperimentStore:
    db_path = str(tmp_path) + "/exit_sweep_test.db"  # type: ignore[operator]
    s = ExperimentStore(db_path=db_path)
    await s.initialize()
    return s


# ---------------------------------------------------------------------------
# Minimal pattern for runner tests (same as test_runner.py)
# ---------------------------------------------------------------------------


class _TwoParamPattern(PatternModule):
    """int [2,4] × float [0.1,0.2,0.3] = 6 detection points."""

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
            PatternParam(name="int_param", param_type=int, default=4, min_value=2, max_value=4, step=2),
            PatternParam(name="float_param", param_type=float, default=0.2, min_value=0.1, max_value=0.3, step=0.1),
        ]


def _make_store_mock() -> MagicMock:
    store = MagicMock()
    store.get_by_fingerprint = AsyncMock(return_value=None)
    store.save_experiment = AsyncMock(return_value=None)
    return store


def _make_engine_mock(expectancy: float = 0.5, total_trades: int = 20) -> MagicMock:
    result = MagicMock()
    result.expectancy = expectancy
    result.total_trades = total_trades
    mor = MagicMock()
    mor.to_dict.return_value = {"expectancy_per_trade": expectancy}
    engine = MagicMock()
    engine.run = AsyncMock(return_value=result)
    engine.to_multi_objective_result = AsyncMock(return_value=mor)
    return engine


# ---------------------------------------------------------------------------
# Test 1: Spawner exit override apply
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawner_exit_override_stored_on_strategy(store: ExperimentStore) -> None:
    """Spawn variant with exit_overrides → strategy._exit_overrides is nested dict."""
    base_config = _make_bull_flag_config()
    base_strategy = _make_bull_flag_strategy(base_config)
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]] = {
        "bull_flag": (base_config, base_strategy)
    }

    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "v_exit_test",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                    "exit_overrides": {"trailing_stop.atr_multiplier": 2.0},
                }
            ]
        },
    }
    spawner = VariantSpawner(store, config)
    spawned = await spawner.spawn_variants(base_strategies, data_service=None, clock=None)  # type: ignore[arg-type]

    assert len(spawned) == 1
    strategy = spawned[0]
    assert hasattr(strategy, "_exit_overrides")
    assert strategy._exit_overrides == {"trailing_stop": {"atr_multiplier": 2.0}}


# ---------------------------------------------------------------------------
# Test 2: Deep merge precedence
# ---------------------------------------------------------------------------


def test_deep_merge_exit_overrides_precedence() -> None:
    """exit_overrides applied via deep_update() wins, base keys untouched."""
    flat_overrides = {"trailing_stop.atr_multiplier": 3.5}
    nested = _dotpath_to_nested(flat_overrides)

    base: dict[str, Any] = {
        "trailing_stop": {
            "atr_multiplier": 2.5,
            "type": "atr",
            "enabled": True,
        }
    }
    merged = deep_update(base, nested)

    assert merged["trailing_stop"]["atr_multiplier"] == pytest.approx(3.5)
    assert merged["trailing_stop"]["type"] == "atr"  # unchanged
    assert merged["trailing_stop"]["enabled"] is True  # unchanged


# ---------------------------------------------------------------------------
# Test 3: Grid with exit dims includes cross-product
# ---------------------------------------------------------------------------


def test_grid_with_exit_dims_has_structured_format() -> None:
    """generate_parameter_grid with exit_sweep_params → structured dicts."""
    runner = ExperimentRunner(store=_make_store_mock(), config={})
    exit_params = [
        ExitSweepParam(name="atr_mult", path="trailing_stop.atr_multiplier", min_value=1.0, max_value=2.0, step=0.5)
    ]

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid = runner.generate_parameter_grid("two_param", exit_sweep_params=exit_params)

    assert len(grid) > 0
    point = grid[0]
    assert "detection_params" in point
    assert "exit_overrides" in point
    assert "int_param" in point["detection_params"]
    assert "trailing_stop.atr_multiplier" in point["exit_overrides"]


# ---------------------------------------------------------------------------
# Test 4: Grid without exit dims is identical to current format
# ---------------------------------------------------------------------------


def test_grid_without_exit_dims_identical_to_current() -> None:
    """generate_parameter_grid without exit_sweep_params → flat dicts (unchanged format)."""
    runner = ExperimentRunner(store=_make_store_mock(), config={})

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid_old = runner.generate_parameter_grid("two_param")
        grid_no_exit = runner.generate_parameter_grid("two_param", exit_sweep_params=None)

    assert grid_old == grid_no_exit
    assert len(grid_old) == 6  # 2 × 3
    assert "int_param" in grid_old[0]
    assert "detection_params" not in grid_old[0]


# ---------------------------------------------------------------------------
# Test 5: Combined grid size = N × M
# ---------------------------------------------------------------------------


def test_combined_grid_size_is_detection_times_exit() -> None:
    """N detection points × M exit points = N×M total grid size."""
    runner = ExperimentRunner(store=_make_store_mock(), config={})
    # _TwoParamPattern: 2 × 3 = 6 detection points
    # exit: 1.0, 1.5, 2.0, 2.5 → 4 exit points
    exit_params = [
        ExitSweepParam(name="atr", path="trailing_stop.atr_multiplier", min_value=1.0, max_value=2.5, step=0.5)
    ]

    with patch(
        "argus.intelligence.experiments.runner.get_pattern_class",
        return_value=_TwoParamPattern,
    ):
        grid = runner.generate_parameter_grid("two_param", exit_sweep_params=exit_params)

    # 6 detection × 4 exit = 24
    assert len(grid) == 24


# ---------------------------------------------------------------------------
# Test 6: Integration spawn + fingerprint includes exit_overrides
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawner_fingerprint_changes_with_exit_overrides(store: ExperimentStore) -> None:
    """Two variants identical except for exit_overrides → different fingerprints."""
    base_config = _make_bull_flag_config()
    base_strategy = _make_bull_flag_strategy(base_config)
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]] = {
        "bull_flag": (base_config, base_strategy)
    }

    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "v_exit_low",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                    "exit_overrides": {"trailing_stop.atr_multiplier": 1.5},
                },
                {
                    "variant_id": "v_exit_high",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                    "exit_overrides": {"trailing_stop.atr_multiplier": 3.5},
                },
            ]
        },
    }
    spawner = VariantSpawner(store, config)
    spawned = await spawner.spawn_variants(base_strategies, data_service=None, clock=None)  # type: ignore[arg-type]

    assert len(spawned) == 2
    fp_low = spawned[0]._config_fingerprint
    fp_high = spawned[1]._config_fingerprint
    assert fp_low != fp_high


# ---------------------------------------------------------------------------
# Test 7: Integration run + exit grid produces records for each point
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_sweep_with_exit_grid_produces_nm_records() -> None:
    """run_sweep with exit_sweep_params produces N×M ExperimentRecords."""
    store_mock = _make_store_mock()
    runner = ExperimentRunner(
        store=store_mock,
        config={"backtest_min_expectancy": 0.0, "backtest_min_trades": 1},
    )
    # _TwoParamPattern with param_subset=[] → 1 detection point (defaults only)
    # exit: 2 points → 1 × 2 = 2 records
    exit_params = [
        ExitSweepParam(name="atr", path="trailing_stop.atr_multiplier", min_value=1.0, max_value=2.0, step=1.0)
    ]
    mock_engine = _make_engine_mock(expectancy=0.5, total_trades=15)

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
            exit_sweep_params=exit_params,
        )

    assert len(records) == 2
    assert store_mock.save_experiment.call_count == 2


# ---------------------------------------------------------------------------
# Test 8: Exit override conflict — deep_update last-write-wins
# ---------------------------------------------------------------------------


def test_exit_override_conflict_last_write_wins() -> None:
    """When exit_overrides conflicts with base, deep_update override wins."""
    flat_overrides = {
        "trailing_stop.atr_multiplier": 5.0,
        "trailing_stop.enabled": False,
    }
    nested = _dotpath_to_nested(flat_overrides)

    base: dict[str, Any] = {
        "trailing_stop": {
            "atr_multiplier": 2.5,
            "enabled": True,
            "type": "atr",
        }
    }
    merged = deep_update(base, nested)

    assert merged["trailing_stop"]["atr_multiplier"] == pytest.approx(5.0)
    assert merged["trailing_stop"]["enabled"] is False
    assert merged["trailing_stop"]["type"] == "atr"  # unrelated key preserved


# ---------------------------------------------------------------------------
# Bonus: _dotpath_to_nested unit tests
# ---------------------------------------------------------------------------


def test_dotpath_to_nested_single_level() -> None:
    """Single-dot path produces correct nesting."""
    result = _dotpath_to_nested({"a.b": 1})
    assert result == {"a": {"b": 1}}


def test_dotpath_to_nested_multi_level() -> None:
    """Two-dot path produces correct deep nesting."""
    result = _dotpath_to_nested({"a.b.c": 42})
    assert result == {"a": {"b": {"c": 42}}}


def test_dotpath_to_nested_multiple_keys_same_parent() -> None:
    """Two keys sharing the same parent are merged into one nested dict."""
    result = _dotpath_to_nested({"ts.atr": 2.0, "ts.pct": 0.02})
    assert result == {"ts": {"atr": 2.0, "pct": 0.02}}


def test_dotpath_to_nested_empty_input() -> None:
    """Empty flat dict → empty nested dict."""
    result = _dotpath_to_nested({})
    assert result == {}


# ---------------------------------------------------------------------------
# Bonus: _generate_exit_values unit tests
# ---------------------------------------------------------------------------


def test_generate_exit_values_basic() -> None:
    """min=1.0, max=3.0, step=1.0 → [1.0, 2.0, 3.0]."""
    param = ExitSweepParam(name="x", path="a.b", min_value=1.0, max_value=3.0, step=1.0)
    values = _generate_exit_values(param)
    assert len(values) == 3
    assert pytest.approx(values) == [1.0, 2.0, 3.0]


def test_generate_exit_values_fractional_step() -> None:
    """min=0.0, max=1.0, step=0.25 → 5 values."""
    param = ExitSweepParam(name="x", path="a.b", min_value=0.0, max_value=1.0, step=0.25)
    values = _generate_exit_values(param)
    assert len(values) == 5
    assert pytest.approx(values[0]) == 0.0
    assert pytest.approx(values[-1]) == 1.0


# ---------------------------------------------------------------------------
# Regression: spawner without exit_overrides behaves identically
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawner_without_exit_overrides_unchanged(store: ExperimentStore) -> None:
    """Spawner with exit_overrides=None (not present in variant def) → _exit_overrides is None."""
    base_config = _make_bull_flag_config()
    base_strategy = _make_bull_flag_strategy(base_config)
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]] = {
        "bull_flag": (base_config, base_strategy)
    }

    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "v_no_exit",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                    # No exit_overrides key
                }
            ]
        },
    }
    spawner = VariantSpawner(store, config)
    spawned = await spawner.spawn_variants(base_strategies, data_service=None, clock=None)  # type: ignore[arg-type]

    assert len(spawned) == 1
    assert spawned[0]._exit_overrides is None


# ---------------------------------------------------------------------------
# Regression: fingerprint with exit_overrides=None is identical to detection-only
# ---------------------------------------------------------------------------


def test_fingerprint_with_none_exit_overrides_matches_detection_only() -> None:
    """compute_parameter_fingerprint(..., exit_overrides=None) == fingerprint without exit_overrides."""
    config = _make_bull_flag_config()
    pattern_class = get_pattern_class("bull_flag")

    fp_no_arg = compute_parameter_fingerprint(config, pattern_class)
    fp_none = compute_parameter_fingerprint(config, pattern_class, exit_overrides=None)
    fp_empty = compute_parameter_fingerprint(config, pattern_class, exit_overrides={})

    assert fp_no_arg == fp_none == fp_empty

"""Tests for VariantSpawner — Sprint 32 Session 5."""

from __future__ import annotations

import pytest

from argus.core.config import BullFlagConfig
from argus.intelligence.experiments import ExperimentStore
from argus.intelligence.experiments.spawner import VariantSpawner
from argus.strategies.patterns.factory import (
    build_pattern_from_config,
    compute_parameter_fingerprint,
    get_pattern_class,
)
from argus.strategies.pattern_strategy import PatternBasedStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bull_flag_config(**overrides: object) -> BullFlagConfig:
    """Create a minimal BullFlagConfig with optional field overrides."""
    fields: dict[str, object] = {"strategy_id": "strat_bull_flag", "name": "Bull Flag"}
    fields.update(overrides)
    return BullFlagConfig(**fields)  # type: ignore[arg-type]


def _make_bull_flag_strategy(config: BullFlagConfig) -> PatternBasedStrategy:
    """Wrap a BullFlagConfig in a PatternBasedStrategy."""
    pattern = build_pattern_from_config(config, "bull_flag")
    return PatternBasedStrategy(pattern=pattern, config=config)


def _two_variant_config(
    *, max_per_pattern: int = 5
) -> dict[str, object]:
    """Returns an experiments config with two distinct bull_flag variants."""
    return {
        "max_variants_per_pattern": max_per_pattern,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "strat_bull_flag__v2_tight",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                },
                {
                    "variant_id": "strat_bull_flag__v3_loose",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.65, "flag_max_bars": 30},
                },
            ]
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def experiment_store(tmp_path: object) -> ExperimentStore:
    """Async-initialised ExperimentStore backed by a temporary database."""
    from pathlib import Path

    db_path = str(Path(str(tmp_path)) / "experiments_test.db")
    store = ExperimentStore(db_path=db_path)
    await store.initialize()
    return store


@pytest.fixture
def base_config() -> BullFlagConfig:
    return _make_bull_flag_config()


@pytest.fixture
def base_strategy(base_config: BullFlagConfig) -> PatternBasedStrategy:
    strategy = _make_bull_flag_strategy(base_config)
    strategy.set_watchlist(["AAPL", "TSLA"])
    return strategy


@pytest.fixture
def base_strategies(
    base_config: BullFlagConfig, base_strategy: PatternBasedStrategy
) -> dict[str, tuple[BullFlagConfig, PatternBasedStrategy]]:
    return {"bull_flag": (base_config, base_strategy)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spawns_two_bull_flag_variants(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """Spawner with 2 bull_flag variants → 2 PatternBasedStrategy instances."""
    spawner = VariantSpawner(experiment_store, _two_variant_config())
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 2
    assert all(isinstance(s, PatternBasedStrategy) for s in spawned)
    ids = {s.strategy_id for s in spawned}
    assert ids == {"strat_bull_flag__v2_tight", "strat_bull_flag__v3_loose"}


@pytest.mark.asyncio
async def test_duplicate_fingerprint_with_base_is_skipped(
    experiment_store: ExperimentStore,
    base_config: BullFlagConfig,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """Variant whose params produce the same fingerprint as the base → skipped."""
    pattern_class = get_pattern_class("bull_flag")
    # Build a params dict that replicates every detection field of the base config
    from argus.strategies.patterns.factory import extract_detection_params

    base_params = extract_detection_params(base_config, pattern_class)
    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "strat_bull_flag__duplicate",
                    "mode": "shadow",
                    "params": base_params,  # Identical to base → same fingerprint
                }
            ]
        },
    }
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 0


@pytest.mark.asyncio
async def test_invalid_variant_params_are_skipped_not_fatal(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """Invalid Pydantic params → logged and skipped; valid sibling still spawns."""
    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "strat_bull_flag__invalid",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 999.0},  # exceeds le=1.0
                },
                {
                    "variant_id": "strat_bull_flag__valid",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                },
            ]
        },
    }
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 1
    assert spawned[0].strategy_id == "strat_bull_flag__valid"


@pytest.mark.asyncio
async def test_shadow_mode_sets_config_mode_shadow(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """Variant with mode: shadow → strategy.config.mode == 'shadow'."""
    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "strat_bull_flag__shadow",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                }
            ]
        },
    }
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 1
    assert spawned[0].config.mode == "shadow"


@pytest.mark.asyncio
async def test_live_mode_sets_config_mode_live(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """Variant with mode: live → strategy.config.mode == 'live'."""
    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "strat_bull_flag__live_v2",
                    "mode": "live",
                    "params": {"flag_max_retrace_pct": 0.35},
                }
            ]
        },
    }
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 1
    assert spawned[0].config.mode == "live"


@pytest.mark.asyncio
async def test_max_variants_per_pattern_respected(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """With max=2 and 4 distinct variants defined, only 2 are spawned."""
    config = _two_variant_config(max_per_pattern=2)
    # Add two more distinct variants to the same pattern
    config["variants"]["bull_flag"].extend(  # type: ignore[index]
        [
            {
                "variant_id": "v3",
                "mode": "shadow",
                "params": {"flag_max_retrace_pct": 0.40},
            },
            {
                "variant_id": "v4",
                "mode": "shadow",
                "params": {"flag_max_retrace_pct": 0.45},
            },
        ]
    )
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 2


@pytest.mark.asyncio
async def test_empty_variants_config_yields_zero_variants(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
) -> None:
    """Empty variants dict → zero variants (experiments.enabled=false code path)."""
    config: dict[str, object] = {
        "max_variants_per_pattern": 5,
        "variants": {},
    }
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        base_strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 0


@pytest.mark.asyncio
async def test_variant_receives_same_watchlist_as_base(
    experiment_store: ExperimentStore,
    base_config: BullFlagConfig,
) -> None:
    """Spawned variant inherits the base strategy's watchlist."""
    base_watchlist = ["AAPL", "TSLA", "NVDA"]
    base_strat = _make_bull_flag_strategy(base_config)
    base_strat.set_watchlist(base_watchlist)
    strategies = {"bull_flag": (base_config, base_strat)}

    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                {
                    "variant_id": "strat_bull_flag__watchlist_test",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                }
            ]
        },
    }
    spawner = VariantSpawner(experiment_store, config)
    spawned = await spawner.spawn_variants(
        strategies, data_service=None, clock=None  # type: ignore[arg-type]
    )
    assert len(spawned) == 1
    assert sorted(spawned[0].watchlist) == sorted(base_watchlist)


# ---------------------------------------------------------------------------
# FIX-16 / H2-S02 + H2-S04 (audit 2026-04-21): variant key + shape validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_param_key_typo_is_rejected_not_silently_dropped(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """H2-S02: misspelled variant param key fails loudly, not silently.

    Prior bug: strategy configs don't use ``extra="forbid"`` so unknown keys
    were dropped by model_dump()+model_validate(). The variant would collapse
    onto base defaults with no operator-visible signal. The spawner now
    explicitly validates ``variant_params`` keys against the config class's
    ``model_fields``.
    """
    import logging

    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                # `flag_retrace_pct` is a typo of `flag_max_retrace_pct`.
                {
                    "variant_id": "strat_bull_flag__typo",
                    "mode": "shadow",
                    "params": {"flag_retrace_pct": 0.35},
                },
                # Valid sibling still spawns — typo is skipped, not fatal.
                {
                    "variant_id": "strat_bull_flag__valid",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                },
            ]
        },
    }
    with caplog.at_level(logging.ERROR):
        spawner = VariantSpawner(experiment_store, config)
        spawned = await spawner.spawn_variants(
            base_strategies,
            data_service=None,  # type: ignore[arg-type]
            clock=None,  # type: ignore[arg-type]
        )

    assert len(spawned) == 1
    assert spawned[0].strategy_id == "strat_bull_flag__valid"
    # The error log must name the typo'd key so operators can act on it.
    assert any(
        "flag_retrace_pct" in record.message
        and "strat_bull_flag__typo" in record.message
        for record in caplog.records
    ), f"Expected ERROR log naming the typo; saw: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_non_dict_variant_entry_is_rejected(
    experiment_store: ExperimentStore,
    base_strategies: dict[str, tuple[BullFlagConfig, PatternBasedStrategy]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """H2-S04: variant entry that is not a dict is rejected with a clear log.

    Prior bug: the spawner implicitly trusted each list element was a
    ``dict`` (via ``.get("variant_id", "")``). A scalar or list entry from a
    malformed YAML caused an AttributeError deep in the loop rather than a
    clear operator-facing message.
    """
    import logging

    config = {
        "max_variants_per_pattern": 5,
        "variants": {
            "bull_flag": [
                "strat_bull_flag__oops_this_is_a_string",
                {
                    "variant_id": "strat_bull_flag__valid",
                    "mode": "shadow",
                    "params": {"flag_max_retrace_pct": 0.35},
                },
            ]
        },
    }
    with caplog.at_level(logging.ERROR):
        spawner = VariantSpawner(experiment_store, config)
        spawned = await spawner.spawn_variants(
            base_strategies,
            data_service=None,  # type: ignore[arg-type]
            clock=None,  # type: ignore[arg-type]
        )

    assert len(spawned) == 1
    assert spawned[0].strategy_id == "strat_bull_flag__valid"
    assert any(
        "variant entry" in record.message and "must be a dict" in record.message
        for record in caplog.records
    ), f"Expected ERROR log about non-dict variant entry; saw: {[r.message for r in caplog.records]}"


def test_existing_experiments_yaml_has_no_typos_in_variant_params() -> None:
    """Guard: the 22 shadow variants in config/experiments.yaml are all valid.

    Run as a fleet-sanity check: every ``params`` key in every variant must
    resolve to a real Pydantic field on the matching ``*Config`` class. If
    this test fails, a typo has been introduced in experiments.yaml that
    would be silently dropped in pre-FIX-16 code (H2-S02).
    """
    import yaml
    from pathlib import Path

    from argus.core.config import (
        ABCDConfig,
        BullFlagConfig,
        DipAndRipConfig,
        FlatTopBreakoutConfig,
        GapAndGoConfig,
        HODBreakConfig,
        MicroPullbackConfig,
        NarrowRangeBreakoutConfig,
        PreMarketHighBreakConfig,
        VwapBounceConfig,
    )

    pattern_config_map = {
        "dip_and_rip": DipAndRipConfig,
        "micro_pullback": MicroPullbackConfig,
        "hod_break": HODBreakConfig,
        "gap_and_go": GapAndGoConfig,
        "premarket_high_break": PreMarketHighBreakConfig,
        "vwap_bounce": VwapBounceConfig,
        "narrow_range_breakout": NarrowRangeBreakoutConfig,
        "abcd": ABCDConfig,
        "bull_flag": BullFlagConfig,
        "flat_top_breakout": FlatTopBreakoutConfig,
    }

    path = Path("config/experiments.yaml")
    assert path.exists(), "config/experiments.yaml must exist"
    with path.open() as f:
        cfg = yaml.safe_load(f)

    bad: list[tuple[str, str, str]] = []
    for pattern_name, variants in (cfg.get("variants") or {}).items():
        config_cls = pattern_config_map.get(pattern_name)
        assert config_cls is not None, (
            f"experiments.yaml references unknown pattern '{pattern_name}'"
        )
        fields = set(config_cls.model_fields.keys())
        for variant in variants:
            variant_id = variant.get("variant_id", "<missing>")
            for key in (variant.get("params") or {}):
                if key not in fields:
                    bad.append((pattern_name, variant_id, key))

    assert not bad, (
        f"Typo'd variant param keys found in config/experiments.yaml: {bad}. "
        f"These would be silently dropped in pre-FIX-16 code (H2-S02)."
    )

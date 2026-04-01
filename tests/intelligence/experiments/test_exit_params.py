"""Tests for Sprint 32.5 S1: ExitSweepParam, exit_overrides on VariantDefinition,
ExperimentConfig exit_sweep_params, and ExperimentStore schema migration.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from argus.core.ids import generate_id
from argus.intelligence.experiments import ExperimentStore, VariantDefinition
from argus.intelligence.experiments.config import ExitSweepParam, ExperimentConfig


# ---------------------------------------------------------------------------
# ExitSweepParam
# ---------------------------------------------------------------------------


class TestExitSweepParam:
    def test_valid_exit_sweep_param_construction(self) -> None:
        """ExitSweepParam accepts valid inputs and exposes them."""
        param = ExitSweepParam(
            name="atr_multiplier",
            path="trailing_stop.atr_multiplier",
            min_value=1.0,
            max_value=4.0,
            step=0.5,
        )
        assert param.name == "atr_multiplier"
        assert param.path == "trailing_stop.atr_multiplier"
        assert param.min_value == pytest.approx(1.0)
        assert param.max_value == pytest.approx(4.0)
        assert param.step == pytest.approx(0.5)

    def test_exit_sweep_param_missing_required_field_raises(self) -> None:
        """Omitting a required field raises ValidationError."""
        with pytest.raises(ValidationError):
            ExitSweepParam(  # type: ignore[call-arg]
                name="atr_multiplier",
                path="trailing_stop.atr_multiplier",
                min_value=1.0,
                max_value=4.0,
                # step is missing
            )

    def test_exit_sweep_param_is_frozen(self) -> None:
        """ExitSweepParam instances are immutable."""
        param = ExitSweepParam(
            name="x", path="a.b", min_value=0.0, max_value=1.0, step=0.1
        )
        with pytest.raises((TypeError, ValidationError)):
            param.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExperimentConfig exit_sweep_params
# ---------------------------------------------------------------------------


class TestExperimentConfigExitSweepParams:
    def test_config_accepts_exit_sweep_params(self) -> None:
        """ExperimentConfig.exit_sweep_params accepts a list of ExitSweepParam."""
        cfg = ExperimentConfig(
            exit_sweep_params=[
                ExitSweepParam(
                    name="atr_mult",
                    path="trailing_stop.atr_multiplier",
                    min_value=1.0,
                    max_value=3.0,
                    step=0.5,
                )
            ]
        )
        assert cfg.exit_sweep_params is not None
        assert len(cfg.exit_sweep_params) == 1
        assert cfg.exit_sweep_params[0].name == "atr_mult"

    def test_config_defaults_exit_sweep_params_to_none(self) -> None:
        """ExperimentConfig.exit_sweep_params defaults to None."""
        cfg = ExperimentConfig()
        assert cfg.exit_sweep_params is None

    def test_config_extra_forbid_still_rejects_unknown_keys(self) -> None:
        """ExperimentConfig with extra='forbid' rejects unknown keys."""
        with pytest.raises(ValidationError):
            ExperimentConfig(unknown_field="should_fail")  # type: ignore[call-arg]

    def test_config_loads_without_exit_fields(self) -> None:
        """Existing configs without exit_sweep_params load without error."""
        cfg = ExperimentConfig(
            enabled=False,
            auto_promote=False,
            max_variants_per_pattern=3,
            backtest_min_trades=20,
        )
        assert cfg.exit_sweep_params is None


# ---------------------------------------------------------------------------
# VariantDefinition exit_overrides
# ---------------------------------------------------------------------------


class TestVariantDefinitionExitOverrides:
    def test_variant_defaults_exit_overrides_to_none(self) -> None:
        """VariantDefinition.exit_overrides defaults to None."""
        variant = VariantDefinition(
            variant_id="v1",
            base_pattern="bull_flag",
            parameter_fingerprint="abc123",
            parameters={"pole_min_bars": 5},
            mode="shadow",
            source="manual",
            created_at=datetime.now(UTC),
        )
        assert variant.exit_overrides is None

    def test_variant_accepts_exit_overrides_dict(self) -> None:
        """VariantDefinition accepts and stores exit_overrides."""
        overrides = {"trailing_stop.atr_multiplier": 2.5}
        variant = VariantDefinition(
            variant_id="v2",
            base_pattern="bull_flag",
            parameter_fingerprint="def456",
            parameters={"pole_min_bars": 5},
            mode="shadow",
            source="manual",
            created_at=datetime.now(UTC),
            exit_overrides=overrides,
        )
        assert variant.exit_overrides == overrides

    def test_variant_with_exit_overrides_is_frozen(self) -> None:
        """VariantDefinition with exit_overrides is still immutable (frozen dataclass)."""
        variant = VariantDefinition(
            variant_id="v3",
            base_pattern="bull_flag",
            parameter_fingerprint="ghi789",
            parameters={},
            mode="live",
            source="grid_sweep",
            created_at=datetime.now(UTC),
            exit_overrides={"trailing_stop.atr_multiplier": 2.0},
        )
        with pytest.raises((TypeError, AttributeError)):
            variant.exit_overrides = None  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExperimentStore exit_overrides persistence
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path: object) -> ExperimentStore:
    db_path = str(tmp_path) + "/test_exit_params.db"  # type: ignore[operator]
    s = ExperimentStore(db_path=db_path)
    await s.initialize()
    return s


def _make_variant_with_exit(
    exit_overrides: dict[str, object] | None = None,
) -> VariantDefinition:
    return VariantDefinition(
        variant_id=f"v_{generate_id()}",
        base_pattern="bull_flag",
        parameter_fingerprint="fp_test",
        parameters={"pole_min_bars": 5},
        mode="shadow",
        source="manual",
        created_at=datetime.now(UTC),
        exit_overrides=exit_overrides,
    )


@pytest.mark.asyncio
async def test_variant_with_exit_overrides_round_trips(store: ExperimentStore) -> None:
    """save_variant + get_variant preserves exit_overrides through DB round-trip."""
    overrides = {"trailing_stop.atr_multiplier": 2.5, "escalation.trigger_r": 1.0}
    variant = _make_variant_with_exit(exit_overrides=overrides)

    await store.save_variant(variant)

    retrieved = await store.get_variant(variant.variant_id)
    assert retrieved is not None
    assert retrieved.exit_overrides == overrides


@pytest.mark.asyncio
async def test_variant_without_exit_overrides_round_trips_as_none(
    store: ExperimentStore,
) -> None:
    """Variant saved without exit_overrides loads back with exit_overrides=None."""
    variant = _make_variant_with_exit(exit_overrides=None)

    await store.save_variant(variant)

    retrieved = await store.get_variant(variant.variant_id)
    assert retrieved is not None
    assert retrieved.exit_overrides is None


@pytest.mark.asyncio
async def test_schema_migration_on_existing_db(tmp_path: object) -> None:
    """ExperimentStore.initialize() can be called twice without error (idempotent migration)."""
    db_path = str(tmp_path) + "/migration_test.db"  # type: ignore[operator]

    store_first = ExperimentStore(db_path=db_path)
    await store_first.initialize()

    # Second initialization should not raise (ALTER TABLE is idempotent via try/except)
    store_second = ExperimentStore(db_path=db_path)
    await store_second.initialize()

    # Verify the store works normally after double initialization
    variant = _make_variant_with_exit(exit_overrides={"trailing_stop.atr_multiplier": 3.0})
    await store_second.save_variant(variant)
    retrieved = await store_second.get_variant(variant.variant_id)
    assert retrieved is not None
    assert retrieved.exit_overrides == {"trailing_stop.atr_multiplier": 3.0}

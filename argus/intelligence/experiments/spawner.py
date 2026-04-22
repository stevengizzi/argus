"""Variant spawner for parameterized experiment strategies.

Reads variant definitions from the experiments config, uses the pattern factory
to instantiate each variant as a PatternBasedStrategy, and records them in the
ExperimentStore.

Sprint 32, Session 5.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from argus.core.config import deep_update
from argus.core.ids import generate_id
from argus.intelligence.experiments.models import (
    ExperimentRecord,
    ExperimentStatus,
    VariantDefinition,
)
from argus.intelligence.experiments.store import ExperimentStore
from argus.strategies.patterns.factory import (
    build_pattern_from_config,
    compute_parameter_fingerprint,
    get_pattern_class,
)
from argus.strategies.pattern_strategy import PatternBasedStrategy

if TYPE_CHECKING:
    from argus.core.clock import Clock
    from argus.core.config import StrategyConfig
    from argus.data.service import DataService

logger = logging.getLogger(__name__)


def _dotpath_to_nested(flat: dict[str, Any]) -> dict[str, Any]:
    """Convert a flat dot-path dict into a nested dict for deep_update.

    For example, ``{"trailing_stop.atr_multiplier": 2.5}`` becomes
    ``{"trailing_stop": {"atr_multiplier": 2.5}}``.

    Args:
        flat: Dict whose keys are dot-delimited paths.

    Returns:
        Equivalent nested dict.
    """
    nested: dict[str, Any] = {}
    for dotpath, value in flat.items():
        parts = dotpath.split(".")
        current = nested
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return nested


class VariantSpawner:
    """Spawns PatternBasedStrategy variants from experiment config definitions.

    Reads variant definitions from the experiments config section, uses the
    pattern factory to instantiate each variant, and records them in the
    ExperimentStore. Duplicate fingerprints and invalid params are skipped
    without raising — spawning failure is never fatal to the base system.

    Args:
        experiment_store: The ExperimentStore to record variants in.
        config: The parsed experiments config dict (from experiments.yaml).
    """

    def __init__(
        self, experiment_store: ExperimentStore, config: dict[str, Any]
    ) -> None:
        self._experiment_store = experiment_store
        self._config = config

    async def spawn_variants(
        self,
        base_strategies: dict[str, tuple[StrategyConfig, PatternBasedStrategy]],
        data_service: DataService | None,
        clock: Clock | None,
    ) -> list[PatternBasedStrategy]:
        """Spawn variant PatternBasedStrategy instances from config definitions.

        For each pattern in the variants config, creates a PatternBasedStrategy
        wrapping a pattern instance constructed with the variant's parameters.
        Duplicate fingerprints (relative to the base or other spawned variants)
        are skipped. Invalid variant params are logged and skipped, not fatal.

        Args:
            base_strategies: Mapping of pattern name to (StrategyConfig,
                PatternBasedStrategy) for each registered base pattern strategy.
            data_service: DataService instance to pass to the strategy constructor.
            clock: Clock instance to pass to the strategy constructor.

        Returns:
            List of spawned variant PatternBasedStrategy instances.
        """
        variants_config: dict[str, list[dict[str, Any]]] = (
            self._config.get("variants") or {}
        )
        max_per_pattern: int = self._config.get("max_variants_per_pattern", 5)

        spawned: list[PatternBasedStrategy] = []

        for pattern_name, variant_defs in variants_config.items():
            if not isinstance(variant_defs, list):
                logger.warning(
                    "VariantSpawner: variants for '%s' must be a list — skipping",
                    pattern_name,
                )
                continue

            if pattern_name not in base_strategies:
                logger.warning(
                    "VariantSpawner: pattern '%s' not found in base strategies — skipping",
                    pattern_name,
                )
                continue

            base_config, base_strategy = base_strategies[pattern_name]

            try:
                pattern_class = get_pattern_class(pattern_name)
                base_fingerprint = compute_parameter_fingerprint(
                    base_config, pattern_class
                )
            except ValueError:
                logger.warning(
                    "VariantSpawner: failed to resolve pattern class for '%s' — skipping",
                    pattern_name,
                    exc_info=True,
                )
                continue

            spawned_fingerprints: set[str] = set()
            spawned_count = 0

            for variant_def in variant_defs:
                if spawned_count >= max_per_pattern:
                    logger.warning(
                        "VariantSpawner: max_variants_per_pattern=%d reached for "
                        "'%s' — remaining variants skipped",
                        max_per_pattern,
                        pattern_name,
                    )
                    break

                variant_id: str = variant_def.get("variant_id", "")
                variant_mode: str = variant_def.get("mode", "shadow")
                variant_params: dict[str, Any] = variant_def.get("params") or {}
                # Flat dot-path exit overrides (e.g. {"trailing_stop.atr_multiplier": 2.5})
                exit_overrides_raw: dict[str, Any] | None = (
                    variant_def.get("exit_overrides") or None
                )
                # Nested form ready for deep_update at runtime
                exit_overrides_nested: dict[str, Any] | None = (
                    _dotpath_to_nested(exit_overrides_raw)
                    if exit_overrides_raw
                    else None
                )

                if not variant_id:
                    logger.warning(
                        "VariantSpawner: variant missing variant_id for pattern "
                        "'%s' — skipping",
                        pattern_name,
                    )
                    continue

                # Apply and validate detection param overrides
                try:
                    params_config = self._apply_variant_params(
                        base_config, variant_params
                    )
                except ValidationError as exc:
                    logger.warning(
                        "VariantSpawner: invalid params for variant '%s' "
                        "(pattern='%s') — skipping. Validation error: %s",
                        variant_id,
                        pattern_name,
                        exc,
                    )
                    continue

                # Compute fingerprint covering detection params + exit overrides
                variant_fingerprint = compute_parameter_fingerprint(
                    params_config, pattern_class, exit_overrides=exit_overrides_raw
                )

                # Skip if fingerprint matches the base strategy
                if variant_fingerprint == base_fingerprint:
                    logger.info(
                        "VariantSpawner: variant '%s' has identical fingerprint "
                        "to base '%s' — skipping",
                        variant_id,
                        pattern_name,
                    )
                    continue

                # Skip if fingerprint duplicates an already-spawned variant
                if variant_fingerprint in spawned_fingerprints:
                    logger.info(
                        "VariantSpawner: variant '%s' is a duplicate of an "
                        "already-spawned variant (fingerprint=%s) — skipping",
                        variant_id,
                        variant_fingerprint,
                    )
                    continue

                # Build final config: set strategy_id to variant_id and apply mode
                try:
                    variant_config = type(base_config).model_validate(
                        {
                            **params_config.model_dump(),
                            "strategy_id": variant_id,
                            "mode": variant_mode,
                        }
                    )
                except ValidationError as exc:
                    logger.warning(
                        "VariantSpawner: failed to finalize config for variant "
                        "'%s' — skipping. Error: %s",
                        variant_id,
                        exc,
                    )
                    continue

                # Construct the pattern instance with variant detection params
                try:
                    variant_pattern = build_pattern_from_config(
                        variant_config, pattern_name
                    )
                except Exception:
                    logger.warning(
                        "VariantSpawner: failed to build pattern for variant "
                        "'%s' — skipping",
                        variant_id,
                        exc_info=True,
                    )
                    continue

                # Wrap in PatternBasedStrategy
                variant_strategy = PatternBasedStrategy(
                    pattern=variant_pattern,
                    config=variant_config,
                    data_service=data_service,
                    clock=clock,
                )
                variant_strategy.set_config_fingerprint(variant_fingerprint)
                # Nested exit overrides stored for OrderManager registration by caller
                variant_strategy._exit_overrides = exit_overrides_nested

                # Copy watchlist from base strategy (UM will override if active)
                if base_strategy.watchlist:
                    variant_strategy.set_watchlist(list(base_strategy.watchlist))

                # Record in ExperimentStore (fire-and-forget per ExperimentStore contract)
                now = datetime.now(UTC)
                variant_definition = VariantDefinition(
                    variant_id=variant_id,
                    base_pattern=pattern_name,
                    parameter_fingerprint=variant_fingerprint,
                    parameters=variant_params,
                    mode=variant_mode,
                    source="manual",
                    created_at=now,
                    exit_overrides=exit_overrides_raw,
                )
                await self._experiment_store.save_variant(variant_definition)

                experiment_record = ExperimentRecord(
                    experiment_id=generate_id(),
                    pattern_name=pattern_name,
                    parameter_fingerprint=variant_fingerprint,
                    parameters=variant_params,
                    status=(
                        ExperimentStatus.ACTIVE_SHADOW
                        if variant_mode == "shadow"
                        else ExperimentStatus.ACTIVE_LIVE
                    ),
                    backtest_result=None,
                    shadow_trades=0,
                    shadow_expectancy=None,
                    is_baseline=False,
                    created_at=now,
                    updated_at=now,
                )
                await self._experiment_store.save_experiment(experiment_record)

                spawned.append(variant_strategy)
                spawned_fingerprints.add(variant_fingerprint)
                spawned_count += 1

                logger.info(
                    "VariantSpawner: spawned variant '%s' "
                    "(pattern='%s', mode='%s', fingerprint='%s')",
                    variant_id,
                    pattern_name,
                    variant_mode,
                    variant_fingerprint,
                )

        return spawned

    @staticmethod
    def _apply_variant_params(
        base_config: StrategyConfig,
        variant_params: dict[str, Any],
    ) -> StrategyConfig:
        """Deep-copy base config and override with variant detection params.

        Validates the resulting config via Pydantic model_validate to catch
        invalid parameter values early.

        Args:
            base_config: The base strategy Pydantic config to copy from.
            variant_params: Dict of detection parameter overrides.

        Returns:
            New StrategyConfig instance with variant params applied.

        Raises:
            ValidationError: If any variant param fails Pydantic validation.
        """
        base_dict = base_config.model_dump()
        base_dict.update(variant_params)
        return type(base_config).model_validate(base_dict)

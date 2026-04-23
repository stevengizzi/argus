"""Pydantic configuration model for the experiment pipeline.

Config-gated via ``experiments.enabled``. When disabled, ExperimentStore is
not initialized and all REST endpoints return 503.

Sprint 32, Session 8. Exit sweep params added Sprint 32.5, Session 1.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VariantConfig(BaseModel):
    """A single variant definition under ``ExperimentConfig.variants[pattern_name]``.

    P1-D2-C02 (FIX-08): Replaces an untyped ``dict[str, Any]`` so that a typo
    inside a variant entry (e.g. ``moed:`` → entry silently ignored) is
    rejected by Pydantic at parse time. Production currently reads
    ``experiments.yaml`` as a raw dict via ``VariantSpawner`` rather than via
    ``ExperimentConfig`` instantiation, so this enforcement applies whenever a
    consumer (tests, future startup wiring) builds ``ExperimentConfig`` from a
    dict. The shape mirrors what ``VariantSpawner`` reads in
    ``argus/intelligence/experiments/spawner.py``.

    Attributes:
        variant_id: Unique identifier for this variant (e.g.
            ``"strat_bull_flag__v2_strong_pole"``).
        mode: Routing mode — ``"shadow"`` (default) routes through
            CounterfactualTracker, ``"live"`` enters the live order pipeline.
        params: Detection parameter overrides applied on top of the base
            pattern config.
        exit_overrides: Optional flat dot-path overrides for exit management
            (e.g. ``{"trailing_stop.atr_multiplier": 2.5}``).
    """

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    mode: Literal["live", "shadow"] = "shadow"
    params: dict[str, Any] = Field(default_factory=dict)
    exit_overrides: dict[str, float] | None = None


class ExitSweepParam(BaseModel):
    """Definition of a single exit-management parameter to sweep.

    Attributes:
        name: Human-readable parameter name (e.g. ``"atr_multiplier"``).
        path: Dot-delimited path within the exit config
            (e.g. ``"trailing_stop.atr_multiplier"``).
        min_value: Inclusive lower bound of the sweep range.
        max_value: Inclusive upper bound of the sweep range.
        step: Step size between sweep values.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    min_value: float
    max_value: float
    step: float


class ExperimentConfig(BaseModel):
    """Configuration for the parameterized experiment pipeline.

    Attributes:
        enabled: Master switch — when False the experiment pipeline is not
            initialized and all experiment endpoints return 503.
        auto_promote: When True, PromotionEvaluator runs autonomously at
            session end via the Learning Loop auto-trigger.
        max_variants_per_pattern: Maximum variants (shadow or live) allowed per
            base pattern at any one time.
        backtest_min_trades: Minimum trade count for an experiment to pass
            the backtest pre-filter (COMPLETED vs FAILED).
        backtest_min_expectancy: Minimum expectancy (R-multiple mean) for an
            experiment to pass the backtest pre-filter.
        promotion_min_shadow_days: Minimum number of trading days with shadow
            activity required before promotion is evaluated.
        promotion_min_shadow_trades: Minimum number of shadow trades required
            before promotion is evaluated.
        promotion_query_limit: Maximum number of records fetched from the
            counterfactual store and trade logger during promotion evaluation.
        cache_dir: Path to the Databento/Parquet cache directory used by
            ExperimentRunner for backtesting.
        variants: Variant definitions keyed by pattern name. Each value is a
            list of variant config dicts consumed by VariantSpawner.
        exit_sweep_params: Optional list of exit-management parameters to
            include in parameter sweeps. When None, only detection parameters
            are swept.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    auto_promote: bool = False
    max_variants_per_pattern: int = Field(default=5, ge=1, le=50)
    backtest_min_trades: int = Field(default=20, ge=1)
    backtest_min_expectancy: float = Field(default=0.0)
    promotion_min_shadow_days: int = Field(default=5, ge=1)
    promotion_min_shadow_trades: int = Field(default=30, ge=1)
    promotion_query_limit: int = Field(default=1000, ge=100, le=50_000)
    cache_dir: str = "data/databento_cache"
    backtest_start_date: str | None = None
    backtest_end_date: str | None = None
    max_workers: int = Field(default=4, ge=1, le=32)
    variants: dict[str, list[VariantConfig]] = Field(default_factory=dict)
    exit_sweep_params: list[ExitSweepParam] | None = None

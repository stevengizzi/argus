"""Pydantic configuration model for the experiment pipeline.

Config-gated via ``experiments.enabled``. When disabled, ExperimentStore is
not initialized and all REST endpoints return 503.

Sprint 32, Session 8.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExperimentConfig(BaseModel):
    """Configuration for the parameterized experiment pipeline.

    Attributes:
        enabled: Master switch — when False the experiment pipeline is not
            initialized and all experiment endpoints return 503.
        auto_promote: When True, PromotionEvaluator runs autonomously at
            session end via the Learning Loop auto-trigger.
        max_shadow_variants_per_pattern: Maximum shadow variants allowed per
            base pattern at any one time.
        backtest_min_trades: Minimum trade count for an experiment to pass
            the backtest pre-filter (COMPLETED vs FAILED).
        backtest_min_expectancy: Minimum expectancy (R-multiple mean) for an
            experiment to pass the backtest pre-filter.
        promotion_min_shadow_days: Minimum number of trading days with shadow
            activity required before promotion is evaluated.
        promotion_min_shadow_trades: Minimum number of shadow trades required
            before promotion is evaluated.
        cache_dir: Path to the Databento/Parquet cache directory used by
            ExperimentRunner for backtesting.
        variants: Variant definitions keyed by pattern name. Each value is a
            list of variant config dicts consumed by VariantSpawner.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    auto_promote: bool = False
    max_shadow_variants_per_pattern: int = Field(default=5, ge=1, le=50)
    backtest_min_trades: int = Field(default=20, ge=1)
    backtest_min_expectancy: float = Field(default=0.0)
    promotion_min_shadow_days: int = Field(default=5, ge=1)
    promotion_min_shadow_trades: int = Field(default=30, ge=1)
    cache_dir: str = "data/databento_cache"
    variants: dict = Field(default_factory=dict)

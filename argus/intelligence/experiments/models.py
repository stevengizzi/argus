"""Data models for the experiment registry.

Defines ExperimentStatus, VariantDefinition, ExperimentRecord, and
PromotionEvent — the core data types for the Sprint 32 experiment pipeline.
backtest_result and comparison_verdict are stored as JSON dicts to avoid
circular dependencies with argus.analytics.evaluation.

Sprint 32, Session 4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ExperimentStatus(StrEnum):
    """Lifecycle states for a pattern experiment."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PROMOTED = "PROMOTED"
    DEMOTED = "DEMOTED"
    ACTIVE_SHADOW = "ACTIVE_SHADOW"
    ACTIVE_LIVE = "ACTIVE_LIVE"


@dataclass(frozen=True)
class VariantDefinition:
    """Immutable description of a parameterized pattern variant.

    Attributes:
        variant_id: Unique identifier (e.g., ``strat_bull_flag__v2_aggressive``).
        base_pattern: Pattern template name (e.g., ``bull_flag``).
        parameter_fingerprint: Hash produced by the pattern factory.
        parameters: Full detection parameter dict.
        mode: Runtime mode — "live" or "shadow".
        source: How this variant was created ("manual", "grid_sweep",
            "learning_loop").
        created_at: UTC creation timestamp.
        exit_overrides: Optional dict of exit management parameter overrides
            for this variant (e.g. ``{"trailing_stop.atr_multiplier": 2.5}``).
            None means this variant uses the default exit configuration.
    """

    variant_id: str
    base_pattern: str
    parameter_fingerprint: str
    parameters: dict[str, Any]
    mode: str
    source: str
    created_at: datetime
    exit_overrides: dict[str, Any] | None = None


@dataclass
class ExperimentRecord:
    """Mutable record for a single experiment run.

    Attributes:
        experiment_id: ULID primary key.
        pattern_name: Name of the pattern template.
        parameter_fingerprint: Hash of the parameter set.
        parameters: Full detection parameter dict.
        status: Current experiment lifecycle state.
        backtest_result: Serialized MultiObjectiveResult dict, or None.
        shadow_trades: Number of shadow trades observed so far.
        shadow_expectancy: Mean R-multiple from shadow trades, or None.
        is_baseline: Whether this record is the current baseline for its pattern.
        created_at: UTC creation timestamp.
        updated_at: UTC last-update timestamp.
    """

    experiment_id: str
    pattern_name: str
    parameter_fingerprint: str
    parameters: dict[str, Any]
    status: ExperimentStatus
    backtest_result: dict[str, Any] | None
    shadow_trades: int
    shadow_expectancy: float | None
    is_baseline: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PromotionEvent:
    """Immutable record of a variant promotion or demotion decision.

    Attributes:
        event_id: ULID primary key.
        variant_id: ID of the variant that was promoted/demoted.
        action: "promote" or "demote".
        previous_mode: Mode before the transition.
        new_mode: Mode after the transition.
        reason: Human-readable explanation.
        comparison_verdict: Serialized ComparisonVerdict dict, or None.
        shadow_trades: Shadow trade count at decision time.
        shadow_expectancy: Shadow expectancy at decision time, or None.
        timestamp: UTC timestamp of the promotion decision.
    """

    event_id: str
    variant_id: str
    action: str
    previous_mode: str
    new_mode: str
    reason: str
    comparison_verdict: str | None
    shadow_trades: int
    shadow_expectancy: float | None
    timestamp: datetime

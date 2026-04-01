"""Experiment registry package.

Provides persistence for parameterized strategy variants, backtest results,
and promotion history. Used by the Sprint 32 experiment pipeline.
"""

from argus.intelligence.experiments.models import (
    ExperimentRecord,
    ExperimentStatus,
    PromotionEvent,
    VariantDefinition,
)
from argus.intelligence.experiments.store import ExperimentStore

__all__ = [
    "ExperimentStore",
    "ExperimentRecord",
    "VariantDefinition",
    "PromotionEvent",
    "ExperimentStatus",
]

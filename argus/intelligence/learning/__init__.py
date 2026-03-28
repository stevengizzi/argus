"""Learning Loop package for ARGUS intelligence layer.

Sprint 28 — data models, outcome collection, analysis, and
config proposal management.
"""

from argus.intelligence.learning.models import (
    ConfidenceLevel,
    ConfigProposal,
    CorrelationResult,
    DataQualityPreamble,
    LearningLoopConfig,
    LearningReport,
    OutcomeRecord,
    ThresholdRecommendation,
    WeightRecommendation,
)
from argus.intelligence.learning.outcome_collector import OutcomeCollector

__all__ = [
    "ConfidenceLevel",
    "ConfigProposal",
    "CorrelationResult",
    "DataQualityPreamble",
    "LearningLoopConfig",
    "LearningReport",
    "OutcomeCollector",
    "OutcomeRecord",
    "ThresholdRecommendation",
    "WeightRecommendation",
]

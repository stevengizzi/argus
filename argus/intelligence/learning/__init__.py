"""Learning Loop package for ARGUS intelligence layer.

Sprint 28 — data models, outcome collection, analysis, and
config proposal management.
"""

from argus.intelligence.learning.config_proposal_manager import (
    ConfigProposalManager,
)
from argus.intelligence.learning.learning_service import LearningService
from argus.intelligence.learning.learning_store import LearningStore
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
    "ConfigProposalManager",
    "CorrelationResult",
    "DataQualityPreamble",
    "LearningLoopConfig",
    "LearningReport",
    "LearningService",
    "LearningStore",
    "OutcomeCollector",
    "OutcomeRecord",
    "ThresholdRecommendation",
    "WeightRecommendation",
]

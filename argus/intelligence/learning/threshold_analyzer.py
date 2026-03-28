"""Threshold Analyzer for the Learning Loop.

Evaluates quality grade thresholds by computing missed-opportunity rates
(profitable rejections) and correct-rejection rates (unprofitable rejections)
from counterfactual data. Uses Amendment 12 decision criteria.

Sprint 28, Session 2a.
"""

from __future__ import annotations

import logging

from argus.intelligence.learning.models import (
    ConfidenceLevel,
    LearningLoopConfig,
    OutcomeRecord,
    ThresholdRecommendation,
)

logger = logging.getLogger(__name__)

# Grade levels to analyze (A+ through C+)
_GRADE_LEVELS = ("A+", "A", "A-", "B+", "B", "B-", "C+")

# Amendment 12 decision criteria thresholds
_MISSED_OPPORTUNITY_THRESHOLD = 0.40
_CORRECT_REJECTION_THRESHOLD = 0.50


class ThresholdAnalyzer:
    """Analyzes quality grade thresholds using counterfactual outcomes.

    Computes missed-opportunity rates and correct-rejection rates per
    grade, then generates threshold adjustment recommendations.
    """

    def analyze(
        self,
        records: list[OutcomeRecord],
        config: LearningLoopConfig,
        current_thresholds: dict[str, int],
    ) -> list[ThresholdRecommendation]:
        """Compute per-grade threshold recommendations.

        Amendment 3/12: Missed-opportunity and correct-rejection rates
        computed from counterfactual records only.

        Args:
            records: Outcome records from OutcomeCollector.
            config: Learning loop configuration.
            current_thresholds: Current score thresholds per grade.

        Returns:
            List of ThresholdRecommendation for grades needing adjustment.
        """
        if not records:
            return []

        # Source separation (Amendment 3/12)
        cf_records = [r for r in records if r.source == "counterfactual"]
        if not cf_records:
            return []

        recommendations: list[ThresholdRecommendation] = []

        for grade in _GRADE_LEVELS:
            grade_recs = self._analyze_grade(
                grade=grade,
                cf_records=cf_records,
                config=config,
                current_threshold=current_thresholds.get(grade, 0),
            )
            recommendations.extend(grade_recs)

        return recommendations

    @staticmethod
    def _analyze_grade(
        grade: str,
        cf_records: list[OutcomeRecord],
        config: LearningLoopConfig,
        current_threshold: int,
    ) -> list[ThresholdRecommendation]:
        """Analyze a single grade level for threshold recommendations.

        Amendment 12 decision criteria:
        - missed_opportunity_rate > 0.40 -> "lower" (too aggressive)
        - correct_rejection_rate < 0.50 -> "raise" (too lenient)
        Both conditions can be true simultaneously.

        Args:
            grade: Quality grade string (e.g., "B+").
            cf_records: Counterfactual records only.
            config: Learning loop configuration.
            current_threshold: Current score threshold for this grade.

        Returns:
            List of recommendations (0, 1, or 2 per grade).
        """
        grade_records = [r for r in cf_records if r.quality_grade == grade]
        sample_size = len(grade_records)

        if sample_size < config.min_sample_count:
            return []

        profitable = sum(1 for r in grade_records if r.pnl > 0)
        unprofitable = sum(1 for r in grade_records if r.pnl <= 0)

        missed_opportunity_rate = profitable / sample_size
        correct_rejection_rate = unprofitable / sample_size

        results: list[ThresholdRecommendation] = []

        # Amendment 12: missed > 0.40 -> "lower" (too aggressive filtering)
        if missed_opportunity_rate > _MISSED_OPPORTUNITY_THRESHOLD:
            confidence = (
                ConfidenceLevel.HIGH
                if sample_size >= config.min_sample_count * 2
                else ConfidenceLevel.MODERATE
            )
            results.append(
                ThresholdRecommendation(
                    grade=grade,
                    current_threshold=float(current_threshold),
                    recommended_direction="lower",
                    missed_opportunity_rate=missed_opportunity_rate,
                    correct_rejection_rate=correct_rejection_rate,
                    sample_size=sample_size,
                    confidence=confidence,
                )
            )

        # Amendment 12: correct < 0.50 -> "raise" (too lenient)
        if correct_rejection_rate < _CORRECT_REJECTION_THRESHOLD:
            confidence = (
                ConfidenceLevel.HIGH
                if sample_size >= config.min_sample_count * 2
                else ConfidenceLevel.MODERATE
            )
            results.append(
                ThresholdRecommendation(
                    grade=grade,
                    current_threshold=float(current_threshold),
                    recommended_direction="raise",
                    missed_opportunity_rate=missed_opportunity_rate,
                    correct_rejection_rate=correct_rejection_rate,
                    sample_size=sample_size,
                    confidence=confidence,
                )
            )

        return results

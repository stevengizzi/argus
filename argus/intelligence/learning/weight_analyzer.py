"""Weight Analyzer for the Learning Loop.

Computes Spearman rank correlations between quality dimension scores and
trade P&L to recommend weight adjustments. Separates trade and counterfactual
sources per Amendment 3, applies p-value checks per Amendment 4, and uses
the explicit weight formula from Amendment 5.

Sprint 28, Session 2a.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from scipy.stats import spearmanr

from argus.intelligence.learning.models import (
    ConfidenceLevel,
    LearningLoopConfig,
    OutcomeRecord,
    WeightRecommendation,
)

logger = logging.getLogger(__name__)

# Source divergence threshold (Amendment 3)
_SOURCE_DIVERGENCE_THRESHOLD = 0.3


class WeightAnalyzer:
    """Analyzes quality dimension correlations with P&L outcomes.

    Produces WeightRecommendation objects indicating how quality engine
    weights should be adjusted based on observed outcome data.
    """

    def analyze(
        self,
        records: list[OutcomeRecord],
        config: LearningLoopConfig,
        current_weights: dict[str, float],
    ) -> list[WeightRecommendation]:
        """Compute per-dimension weight recommendations.

        Separates records by source (trade vs counterfactual), computes
        Spearman correlations for each dimension, and produces weight
        recommendations using the Amendment 5 formula.

        Args:
            records: Outcome records from OutcomeCollector.
            config: Learning loop configuration.
            current_weights: Current quality dimension weights.

        Returns:
            List of WeightRecommendation, one per dimension.
        """
        if not records or not current_weights:
            return []

        trade_records = [r for r in records if r.source == "trade"]
        cf_records = [r for r in records if r.source == "counterfactual"]

        # Per-dimension correlation results keyed by dimension
        dim_results: dict[str, _DimensionCorrelation] = {}

        for dimension in current_weights:
            dim_results[dimension] = self._compute_dimension_correlation(
                dimension=dimension,
                trade_records=trade_records,
                cf_records=cf_records,
                config=config,
            )

        return self._build_recommendations(
            dim_results=dim_results,
            current_weights=current_weights,
            config=config,
        )

    def analyze_by_regime(
        self,
        records: list[OutcomeRecord],
        config: LearningLoopConfig,
        current_weights: dict[str, float],
    ) -> dict[str, list[WeightRecommendation]]:
        """Compute weight recommendations grouped by primary regime.

        Groups records by the primary_regime field from regime_context
        (5-value MarketRegime enum only, per Amendment 7). Only analyzes
        regimes with sufficient sample count.

        Args:
            records: Outcome records from OutcomeCollector.
            config: Learning loop configuration.
            current_weights: Current quality dimension weights.

        Returns:
            Dict keyed by regime name, each with a list of recommendations.
        """
        if not records or not current_weights:
            return {}

        # Group by primary_regime from regime_context
        regime_groups: dict[str, list[OutcomeRecord]] = defaultdict(list)
        for record in records:
            regime = record.regime_context.get("primary_regime")
            if regime is not None:
                regime_groups[str(regime)].append(record)

        results: dict[str, list[WeightRecommendation]] = {}
        for regime_name, regime_records in regime_groups.items():
            if len(regime_records) < config.min_sample_per_regime:
                continue
            recs = self.analyze(regime_records, config, current_weights)
            if recs:
                results[regime_name] = recs

        return results

    # --- Internal helpers ---

    def _compute_dimension_correlation(
        self,
        dimension: str,
        trade_records: list[OutcomeRecord],
        cf_records: list[OutcomeRecord],
        config: LearningLoopConfig,
    ) -> _DimensionCorrelation:
        """Compute Spearman correlation for a single dimension.

        Computes separately for trade and counterfactual sources.
        Applies zero-variance and p-value checks.

        Args:
            dimension: Quality dimension name.
            trade_records: Trade-sourced outcome records.
            cf_records: Counterfactual-sourced outcome records.
            config: Learning loop configuration.

        Returns:
            _DimensionCorrelation with results from both sources.
        """
        trade_result = self._correlate_source(dimension, trade_records)
        cf_result = self._correlate_source(dimension, cf_records)

        return _DimensionCorrelation(
            trade_corr=trade_result,
            cf_corr=cf_result,
            p_value_threshold=config.correlation_p_value_threshold,
            min_sample_count=config.min_sample_count,
        )

    @staticmethod
    def _correlate_source(
        dimension: str,
        records: list[OutcomeRecord],
    ) -> _SourceCorrelation:
        """Compute Spearman correlation for one source type.

        Args:
            dimension: Quality dimension name.
            records: Records from a single source (trade or counterfactual).

        Returns:
            _SourceCorrelation with correlation, p-value, and sample size.
        """
        scores: list[float] = []
        pnls: list[float] = []

        for record in records:
            score = record.dimension_scores.get(dimension)
            if score is not None:
                scores.append(score)
                pnls.append(record.pnl)

        sample_size = len(scores)
        if sample_size < 2:
            return _SourceCorrelation(
                correlation=None,
                p_value=None,
                sample_size=sample_size,
                zero_variance=False,
            )

        # Check zero-variance on dimension scores (Amendment 15)
        if len(set(scores)) <= 1:
            return _SourceCorrelation(
                correlation=None,
                p_value=None,
                sample_size=sample_size,
                zero_variance=True,
            )

        # Check zero-variance on P&L outcomes (Amendment 15)
        if len(set(pnls)) <= 1:
            return _SourceCorrelation(
                correlation=None,
                p_value=None,
                sample_size=sample_size,
                zero_variance=True,
            )

        corr, p_value = spearmanr(scores, pnls)
        return _SourceCorrelation(
            correlation=float(corr),
            p_value=float(p_value),
            sample_size=sample_size,
            zero_variance=False,
        )

    def _build_recommendations(
        self,
        dim_results: dict[str, _DimensionCorrelation],
        current_weights: dict[str, float],
        config: LearningLoopConfig,
    ) -> list[WeightRecommendation]:
        """Build weight recommendations from correlation results.

        Applies Amendment 5 formula: recommended_weight_i = max(0, ρ_i) /
        Σ max(0, ρ_j), scaled to non-stub allocation. Zero-variance
        dimensions held at current weight.

        Args:
            dim_results: Per-dimension correlation results.
            current_weights: Current quality dimension weights.
            config: Learning loop configuration.

        Returns:
            List of WeightRecommendation, one per dimension.
        """
        # Classify dimensions into stub (zero-variance) and non-stub
        effective_corrs: dict[str, float | None] = {}
        is_stub: dict[str, bool] = {}

        for dimension, result in dim_results.items():
            corr, confidence = result.effective_correlation(config.min_sample_count)
            is_stub[dimension] = result.is_zero_variance()

            if is_stub[dimension]:
                effective_corrs[dimension] = None
            elif confidence == ConfidenceLevel.INSUFFICIENT_DATA:
                effective_corrs[dimension] = None
            else:
                effective_corrs[dimension] = corr

        # Compute stub allocation (sum of weights for stub dimensions)
        stub_weight_sum = sum(
            current_weights[d] for d in current_weights if is_stub.get(d, False)
        )
        non_stub_allocation = 1.0 - stub_weight_sum

        # Amendment 5: max(0, ρ_i) / Σ max(0, ρ_j) scaled to non-stub allocation
        non_stub_positive_corrs: dict[str, float] = {}
        for dim, corr in effective_corrs.items():
            if corr is not None and not is_stub.get(dim, False):
                clamped = max(0.0, corr)
                non_stub_positive_corrs[dim] = clamped

        positive_sum = sum(non_stub_positive_corrs.values())

        # If all non-stub dimensions have non-significant or negative
        # correlations → no recommendations generated
        if positive_sum <= 0.0 and any(
            not is_stub.get(d, False) for d in current_weights
        ):
            # Check if ALL non-stub dimensions lack usable correlations
            all_unusable = all(
                effective_corrs.get(d) is None or effective_corrs[d] <= 0.0  # type: ignore[operator]
                for d in current_weights
                if not is_stub.get(d, False)
            )
            if all_unusable:
                return []

        recommendations: list[WeightRecommendation] = []
        for dimension in current_weights:
            result = dim_results[dimension]
            _, confidence = result.effective_correlation(config.min_sample_count)

            if is_stub[dimension]:
                # Stub dimensions held at current weight
                recommended = current_weights[dimension]
            elif positive_sum > 0.0:
                proportion = non_stub_positive_corrs.get(dimension, 0.0) / positive_sum
                recommended = proportion * non_stub_allocation
            else:
                # No positive correlations — hold at current weight
                recommended = current_weights[dimension]

            # Clamp delta by max_change_per_cycle
            delta = recommended - current_weights[dimension]
            max_change = config.max_weight_change_per_cycle
            clamped_delta = max(-max_change, min(max_change, delta))
            recommended = current_weights[dimension] + clamped_delta

            recommendations.append(
                WeightRecommendation(
                    dimension=dimension,
                    current_weight=current_weights[dimension],
                    recommended_weight=recommended,
                    delta=clamped_delta,
                    correlation_trade_source=(
                        result.trade_corr.correlation
                    ),
                    correlation_counterfactual_source=(
                        result.cf_corr.correlation
                    ),
                    p_value=result.effective_p_value(config.min_sample_count),
                    sample_size=result.total_sample_size(),
                    confidence=confidence,
                    regime_breakdown={},
                    source_divergence_flag=result.has_source_divergence(),
                )
            )

        # Normalize recommended weights to sum to 1.0
        self._normalize_weights(recommendations, current_weights)
        return recommendations

    @staticmethod
    def _normalize_weights(
        recommendations: list[WeightRecommendation],
        current_weights: dict[str, float],
    ) -> None:
        """Normalize recommended weights to sum to 1.0.

        Adjusts recommended weights proportionally so their sum is exactly
        1.0. Mutates the recommendations list by replacing dataclass
        instances (since they are frozen).

        Args:
            recommendations: List of recommendations to normalize.
            current_weights: Current weights for reference.
        """
        if not recommendations:
            return

        total = sum(r.recommended_weight for r in recommendations)
        if total <= 0.0 or abs(total - 1.0) < 1e-10:
            return

        for i, rec in enumerate(recommendations):
            normalized = rec.recommended_weight / total
            new_delta = normalized - rec.current_weight
            recommendations[i] = WeightRecommendation(
                dimension=rec.dimension,
                current_weight=rec.current_weight,
                recommended_weight=normalized,
                delta=new_delta,
                correlation_trade_source=rec.correlation_trade_source,
                correlation_counterfactual_source=rec.correlation_counterfactual_source,
                p_value=rec.p_value,
                sample_size=rec.sample_size,
                confidence=rec.confidence,
                regime_breakdown=rec.regime_breakdown,
                source_divergence_flag=rec.source_divergence_flag,
            )


class _SourceCorrelation:
    """Correlation result from a single data source."""

    __slots__ = ("correlation", "p_value", "sample_size", "zero_variance")

    def __init__(
        self,
        correlation: float | None,
        p_value: float | None,
        sample_size: int,
        zero_variance: bool,
    ) -> None:
        self.correlation = correlation
        self.p_value = p_value
        self.sample_size = sample_size
        self.zero_variance = zero_variance


class _DimensionCorrelation:
    """Combined correlation results for a dimension across both sources."""

    __slots__ = (
        "trade_corr",
        "cf_corr",
        "p_value_threshold",
        "min_sample_count",
    )

    def __init__(
        self,
        trade_corr: _SourceCorrelation,
        cf_corr: _SourceCorrelation,
        p_value_threshold: float,
        min_sample_count: int,
    ) -> None:
        self.trade_corr = trade_corr
        self.cf_corr = cf_corr
        self.p_value_threshold = p_value_threshold
        self.min_sample_count = min_sample_count

    def is_zero_variance(self) -> bool:
        """True if both sources show zero variance."""
        return self.trade_corr.zero_variance and self.cf_corr.zero_variance

    def effective_correlation(
        self, min_sample_count: int
    ) -> tuple[float | None, ConfidenceLevel]:
        """Get the effective correlation and confidence level.

        Source preference (Amendment 3): Use trade-sourced correlation when
        trade sample count >= min_sample_count. Otherwise fall back to
        counterfactual-sourced with MODERATE confidence cap.

        Args:
            min_sample_count: Minimum sample count for trade preference.

        Returns:
            Tuple of (correlation value or None, confidence level).
        """
        if self.is_zero_variance():
            return None, ConfidenceLevel.INSUFFICIENT_DATA

        # Try trade source first (Amendment 3)
        if (
            self.trade_corr.correlation is not None
            and self.trade_corr.sample_size >= min_sample_count
            and self.trade_corr.p_value is not None
            and self.trade_corr.p_value < self.p_value_threshold
        ):
            return self.trade_corr.correlation, ConfidenceLevel.HIGH

        # Fall back to counterfactual with MODERATE cap (Amendment 3)
        if (
            self.cf_corr.correlation is not None
            and self.cf_corr.sample_size >= min_sample_count
            and self.cf_corr.p_value is not None
            and self.cf_corr.p_value < self.p_value_threshold
        ):
            return self.cf_corr.correlation, ConfidenceLevel.MODERATE

        # Try trade source with insufficient samples but valid correlation
        if (
            self.trade_corr.correlation is not None
            and self.trade_corr.p_value is not None
            and self.trade_corr.p_value < self.p_value_threshold
        ):
            return self.trade_corr.correlation, ConfidenceLevel.LOW

        # Try cf with insufficient samples
        if (
            self.cf_corr.correlation is not None
            and self.cf_corr.p_value is not None
            and self.cf_corr.p_value < self.p_value_threshold
        ):
            return self.cf_corr.correlation, ConfidenceLevel.LOW

        return None, ConfidenceLevel.INSUFFICIENT_DATA

    def effective_p_value(self, min_sample_count: int) -> float | None:
        """Get the p-value from the preferred source.

        Args:
            min_sample_count: Minimum sample count for trade preference.

        Returns:
            P-value from the preferred source, or None.
        """
        if (
            self.trade_corr.p_value is not None
            and self.trade_corr.sample_size >= min_sample_count
        ):
            return self.trade_corr.p_value
        if self.cf_corr.p_value is not None:
            return self.cf_corr.p_value
        return self.trade_corr.p_value

    def total_sample_size(self) -> int:
        """Total sample size across both sources."""
        return self.trade_corr.sample_size + self.cf_corr.sample_size

    def has_source_divergence(self) -> bool:
        """True if trade and counterfactual correlations diverge > 0.3.

        Amendment 3: Flag divergence > 0.3 between sources.

        Returns:
            True if divergence exceeds threshold.
        """
        if (
            self.trade_corr.correlation is not None
            and self.cf_corr.correlation is not None
        ):
            diff = abs(self.trade_corr.correlation - self.cf_corr.correlation)
            return diff > _SOURCE_DIVERGENCE_THRESHOLD
        return False

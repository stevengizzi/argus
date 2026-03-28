"""LearningService orchestrator for the Learning Loop.

Wires OutcomeCollector, analyzers, and LearningStore into a single
analysis pipeline. Produces LearningReports with weight, threshold,
and correlation recommendations. Auto-supersedes prior PENDING proposals
and generates new ConfigProposals for actionable recommendations.

Sprint 28, Session 3b.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from ulid import ULID

from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    ConfidenceLevel,
    ConfigProposal,
    LearningLoopConfig,
    LearningReport,
    WeightRecommendation,
)
from argus.intelligence.learning.outcome_collector import OutcomeCollector
from argus.intelligence.learning.threshold_analyzer import ThresholdAnalyzer
from argus.intelligence.learning.weight_analyzer import WeightAnalyzer

logger = logging.getLogger(__name__)

_DEFAULT_QE_YAML = "config/quality_engine.yaml"

# Grade key mapping: YAML snake_case → display format
_GRADE_KEY_TO_DISPLAY: dict[str, str] = {
    "a_plus": "A+",
    "a": "A",
    "a_minus": "A-",
    "b_plus": "B+",
    "b": "B",
    "b_minus": "B-",
    "c_plus": "C+",
}


class LearningService:
    """Orchestrates the full learning loop analysis pipeline.

    Collects outcomes, runs weight/threshold/correlation analysis,
    assembles a LearningReport, persists it, and generates ConfigProposals
    for actionable recommendations.

    Args:
        config: LearningLoopConfig with analysis parameters.
        outcome_collector: OutcomeCollector for reading trade/CF data.
        weight_analyzer: WeightAnalyzer for dimension correlation analysis.
        threshold_analyzer: ThresholdAnalyzer for grade threshold analysis.
        correlation_analyzer: CorrelationAnalyzer for cross-strategy analysis.
        store: LearningStore for persistence.
        quality_engine_yaml_path: Path to quality_engine.yaml.
    """

    def __init__(
        self,
        config: LearningLoopConfig,
        outcome_collector: OutcomeCollector,
        weight_analyzer: WeightAnalyzer,
        threshold_analyzer: ThresholdAnalyzer,
        correlation_analyzer: CorrelationAnalyzer,
        store: LearningStore,
        quality_engine_yaml_path: str = _DEFAULT_QE_YAML,
    ) -> None:
        self._config = config
        self._collector = outcome_collector
        self._weight_analyzer = weight_analyzer
        self._threshold_analyzer = threshold_analyzer
        self._correlation_analyzer = correlation_analyzer
        self._store = store
        self._qe_yaml_path = quality_engine_yaml_path
        self._running = False

    async def run_analysis(
        self,
        window_days: int | None = None,
        strategy_id: str | None = None,
    ) -> LearningReport | None:
        """Run the full learning loop analysis pipeline.

        1. Check concurrent guard
        2. Read current weights/thresholds from quality_engine.yaml
        3. Collect outcomes
        4. Build data quality preamble
        5. Run WeightAnalyzer (overall + per-regime)
        6. Run ThresholdAnalyzer
        7. Run CorrelationAnalyzer
        8. Assemble LearningReport
        9. Persist to LearningStore
        10. Auto-supersede prior PENDING proposals (Amendment 6)
        11. Generate ConfigProposals for actionable recommendations
        12. Save proposals to store
        13. Log summary

        Args:
            window_days: Override for analysis_window_days.
            strategy_id: Optional strategy filter.

        Returns:
            LearningReport on success, None if disabled.

        Raises:
            RuntimeError: If another analysis is already running.
        """
        if not self._config.enabled:
            logger.info("Learning loop disabled — skipping analysis")
            return None

        if self._running:
            raise RuntimeError("Learning analysis already running")

        self._running = True
        start_time = time.monotonic()
        try:
            return await self._execute_analysis(window_days, strategy_id)
        finally:
            self._running = False
            elapsed = time.monotonic() - start_time
            logger.info("Learning analysis completed in %.1fs", elapsed)

    async def _execute_analysis(
        self,
        window_days: int | None,
        strategy_id: str | None,
    ) -> LearningReport:
        """Execute the analysis pipeline (internal, guarded by _running).

        Args:
            window_days: Override for analysis_window_days.
            strategy_id: Optional strategy filter.

        Returns:
            LearningReport with all analysis results.
        """
        days = window_days or self._config.analysis_window_days
        now = datetime.now(UTC)
        end_date = now
        start_date = now - timedelta(days=days)

        # Step 2: Read current weights/thresholds from YAML
        current_weights, current_thresholds = self._read_quality_engine_config()

        # Step 3: Collect outcomes
        records = await self._collector.collect(start_date, end_date, strategy_id)

        # Step 4: Build data quality preamble
        data_quality = await self._collector.build_data_quality_preamble(records)

        # Step 5: Run WeightAnalyzer (overall + per-regime)
        weight_recs = self._weight_analyzer.analyze(
            records, self._config, current_weights
        )
        regime_recs = self._weight_analyzer.analyze_by_regime(
            records, self._config, current_weights
        )

        # Enrich weight recommendations with regime breakdown
        enriched_weight_recs = self._enrich_with_regime(weight_recs, regime_recs)

        # Step 6: Run ThresholdAnalyzer
        threshold_recs = self._threshold_analyzer.analyze(
            records, self._config, current_thresholds
        )

        # Step 7: Run CorrelationAnalyzer
        correlation_result = self._correlation_analyzer.analyze(
            records, self._config
        )

        # Step 8: Assemble LearningReport
        report = LearningReport(
            report_id=str(ULID()),
            generated_at=now,
            analysis_window_start=start_date,
            analysis_window_end=end_date,
            data_quality=data_quality,
            weight_recommendations=enriched_weight_recs,
            threshold_recommendations=threshold_recs,
            correlation_result=correlation_result,
            version=1,
        )

        # Step 9: Persist to LearningStore
        await self._store.save_report(report)

        # Step 10: Auto-supersede prior PENDING proposals (Amendment 6)
        superseded = await self._store.supersede_proposals(report.report_id)
        if superseded > 0:
            logger.info("Superseded %d prior PENDING proposals", superseded)

        # Steps 11-12: Generate and save ConfigProposals
        proposals = self._generate_proposals(report, current_weights)
        for proposal in proposals:
            await self._store.save_proposal(proposal)

        # Step 13: Log summary
        logger.info(
            "Learning analysis: %d weight recs, %d threshold recs, "
            "%d proposals generated, data quality: %d trades + %d CF "
            "over %d days",
            len(enriched_weight_recs),
            len(threshold_recs),
            len(proposals),
            data_quality.total_trades,
            data_quality.total_counterfactual,
            data_quality.trading_days_count,
        )

        return report

    def _read_quality_engine_config(
        self,
    ) -> tuple[dict[str, float], dict[str, int]]:
        """Read current weights and thresholds from quality_engine.yaml.

        Returns:
            Tuple of (weights dict, thresholds dict with display-format keys).
        """
        path = Path(self._qe_yaml_path)
        if not path.exists():
            logger.warning(
                "quality_engine.yaml not found at %s — using defaults",
                self._qe_yaml_path,
            )
            return _default_weights(), _default_thresholds()

        raw = yaml.safe_load(path.read_text())
        if not isinstance(raw, dict):
            return _default_weights(), _default_thresholds()

        # Extract weights
        weights_raw = raw.get("weights", {})
        weights: dict[str, float] = {}
        if isinstance(weights_raw, dict):
            for key, val in weights_raw.items():
                weights[str(key)] = float(val)

        # Extract thresholds with display-format keys
        thresholds_raw = raw.get("thresholds", {})
        thresholds: dict[str, int] = {}
        if isinstance(thresholds_raw, dict):
            for key, val in thresholds_raw.items():
                display_key = _GRADE_KEY_TO_DISPLAY.get(str(key), str(key))
                thresholds[display_key] = int(val)

        return weights or _default_weights(), thresholds or _default_thresholds()

    @staticmethod
    def _enrich_with_regime(
        overall_recs: list[WeightRecommendation],
        regime_recs: dict[str, list[WeightRecommendation]],
    ) -> list[WeightRecommendation]:
        """Merge per-regime correlation data into overall recommendations.

        Args:
            overall_recs: Overall weight recommendations.
            regime_recs: Per-regime weight recommendations.

        Returns:
            Enriched recommendations with regime_breakdown populated.
        """
        if not regime_recs:
            return overall_recs

        enriched: list[WeightRecommendation] = []
        for rec in overall_recs:
            breakdown: dict[str, float] = {}
            for regime_name, regime_rec_list in regime_recs.items():
                for regime_rec in regime_rec_list:
                    if regime_rec.dimension == rec.dimension:
                        corr = (
                            regime_rec.correlation_trade_source
                            or regime_rec.correlation_counterfactual_source
                            or 0.0
                        )
                        breakdown[regime_name] = corr

            enriched.append(WeightRecommendation(
                dimension=rec.dimension,
                current_weight=rec.current_weight,
                recommended_weight=rec.recommended_weight,
                delta=rec.delta,
                correlation_trade_source=rec.correlation_trade_source,
                correlation_counterfactual_source=rec.correlation_counterfactual_source,
                p_value=rec.p_value,
                sample_size=rec.sample_size,
                confidence=rec.confidence,
                regime_breakdown=breakdown if breakdown else rec.regime_breakdown,
                source_divergence_flag=rec.source_divergence_flag,
            ))

        return enriched

    def _generate_proposals(
        self,
        report: LearningReport,
        current_weights: dict[str, float],
    ) -> list[ConfigProposal]:
        """Generate ConfigProposals for actionable recommendations.

        Only generates proposals for recommendations with confidence
        above MODERATE (i.e., HIGH or MODERATE).

        Args:
            report: The completed LearningReport.
            current_weights: Current weight values for reference.

        Returns:
            List of ConfigProposal objects.
        """
        now = datetime.now(UTC)
        proposals: list[ConfigProposal] = []
        actionable = {ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE}

        # Weight recommendations → proposals
        for rec in report.weight_recommendations:
            if rec.confidence not in actionable:
                continue
            if abs(rec.delta) < 1e-6:
                continue

            proposals.append(ConfigProposal(
                proposal_id=str(ULID()),
                report_id=report.report_id,
                field_path=f"weights.{rec.dimension}",
                current_value=rec.current_weight,
                proposed_value=rec.recommended_weight,
                rationale=(
                    f"{rec.dimension}: correlation={rec.correlation_trade_source or rec.correlation_counterfactual_source}, "
                    f"confidence={rec.confidence.value}, "
                    f"delta={rec.delta:+.4f}"
                ),
                status="PENDING",
                created_at=now,
                updated_at=now,
            ))

        # Threshold recommendations → proposals (informational)
        for rec in report.threshold_recommendations:
            if rec.confidence not in actionable:
                continue

            proposals.append(ConfigProposal(
                proposal_id=str(ULID()),
                report_id=report.report_id,
                field_path=f"thresholds.{_grade_to_yaml_key(rec.grade)}",
                current_value=rec.current_threshold,
                proposed_value=(
                    rec.current_threshold - 5.0
                    if rec.recommended_direction == "lower"
                    else rec.current_threshold + 5.0
                ),
                rationale=(
                    f"{rec.grade} threshold: {rec.recommended_direction} "
                    f"(missed_opp={rec.missed_opportunity_rate:.2f}, "
                    f"correct_rej={rec.correct_rejection_rate:.2f}, "
                    f"confidence={rec.confidence.value})"
                ),
                status="PENDING",
                created_at=now,
                updated_at=now,
            ))

        return proposals


def _default_weights() -> dict[str, float]:
    """Return default quality engine weights."""
    return {
        "pattern_strength": 0.30,
        "catalyst_quality": 0.25,
        "volume_profile": 0.20,
        "historical_match": 0.15,
        "regime_alignment": 0.10,
    }


def _default_thresholds() -> dict[str, int]:
    """Return default quality grade thresholds (display-format keys)."""
    return {
        "A+": 90,
        "A": 80,
        "A-": 70,
        "B+": 60,
        "B": 50,
        "B-": 40,
        "C+": 30,
    }


def _grade_to_yaml_key(grade: str) -> str:
    """Convert display-format grade to YAML snake_case key.

    Args:
        grade: Grade string like "A+", "B-".

    Returns:
        YAML key like "a_plus", "b_minus".
    """
    return grade.lower().replace("+", "_plus").replace("-", "_minus")

"""LearningService orchestrator for the Learning Loop.

Wires OutcomeCollector, analyzers, and LearningStore into a single
analysis pipeline. Produces LearningReports with weight, threshold,
and correlation recommendations. Auto-supersedes prior PENDING proposals
and generates new ConfigProposals for actionable recommendations.

Sprint 28, Session 3b.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from ulid import ULID

if TYPE_CHECKING:
    from argus.core.event_bus import EventBus

from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    ConfidenceLevel,
    ConfigProposal,
    LearningLoopConfig,
    LearningReport,
    OutcomeRecord,
    StrategyMetricsSummary,
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

    def register_auto_trigger(self, event_bus: EventBus) -> None:
        """Subscribe to SessionEndEvent for automatic post-session analysis.

        Amendment 13: Uses Event Bus subscription, not direct callback.

        Args:
            event_bus: The system event bus.
        """
        from argus.core.events import SessionEndEvent

        event_bus.subscribe(SessionEndEvent, self._on_session_end)
        logger.info("LearningService auto-trigger registered on SessionEndEvent")

    async def _on_session_end(self, event: object) -> None:
        """Handle SessionEndEvent — fire-and-forget analysis.

        Amendment 10: Zero-trade guard skips if both trades_count
        and counterfactual_count are zero. Runs if counterfactual-only.
        Timeout of 120s. Exceptions logged, never delay shutdown.

        Args:
            event: SessionEndEvent (typed as object to avoid circular import).
        """
        from argus.core.events import SessionEndEvent

        if not isinstance(event, SessionEndEvent):
            return

        if not self._config.auto_trigger_enabled:
            logger.info("Auto-trigger disabled — skipping post-session analysis")
            return

        # Zero-trade guard (Amendment 10)
        if event.trades_count == 0 and event.counterfactual_count == 0:
            logger.info(
                "Zero trades and zero counterfactual — skipping post-session analysis"
            )
            return

        logger.info(
            "Auto-trigger: starting post-session analysis "
            "(trades=%d, counterfactual=%d, day=%s)",
            event.trades_count,
            event.counterfactual_count,
            event.trading_day,
        )

        try:
            await asyncio.wait_for(self.run_analysis(), timeout=120)
        except asyncio.TimeoutError:
            logger.warning("Auto-trigger: analysis timed out after 120s")
        except RuntimeError:
            logger.warning("Auto-trigger: analysis already running, skipping")
        except Exception:
            logger.warning("Auto-trigger: analysis failed", exc_info=True)

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

        # Step 4.5: Compute per-strategy metrics
        strategy_metrics = self._compute_strategy_metrics(records)

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
            strategy_metrics=strategy_metrics,
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
    def _compute_strategy_metrics(
        records: list[OutcomeRecord],
    ) -> dict[str, StrategyMetricsSummary]:
        """Compute per-strategy trailing performance metrics.

        Uses trade-sourced records preferentially per Amendment 3 spirit.
        Falls back to combined (trade + counterfactual) if fewer than
        5 trade records for a strategy.

        Args:
            records: All OutcomeRecords from the collection window.

        Returns:
            Dict of strategy_id -> StrategyMetricsSummary.
        """
        from collections import defaultdict
        from datetime import date
        from zoneinfo import ZoneInfo

        import numpy as np

        eastern = ZoneInfo("America/New_York")

        # Group by strategy
        trade_by_strategy: dict[str, list[OutcomeRecord]] = defaultdict(list)
        all_by_strategy: dict[str, list[OutcomeRecord]] = defaultdict(list)
        for r in records:
            all_by_strategy[r.strategy_id].append(r)
            if r.source == "trade":
                trade_by_strategy[r.strategy_id].append(r)

        result: dict[str, StrategyMetricsSummary] = {}

        for strategy_id, all_recs in all_by_strategy.items():
            trade_recs = trade_by_strategy.get(strategy_id, [])

            # Source selection: trade if >= 5 records, else combined
            if len(trade_recs) >= 5:
                working = trade_recs
                source = "trade"
            elif len(all_recs) >= 5:
                working = all_recs
                source = "combined"
            else:
                result[strategy_id] = StrategyMetricsSummary(
                    strategy_id=strategy_id,
                    sharpe=None,
                    win_rate=0.0,
                    expectancy=0.0,
                    trade_count=len(all_recs),
                    source="insufficient",
                )
                continue

            # Win rate
            wins = sum(1 for r in working if r.pnl > 0)
            win_rate = wins / len(working)

            # Expectancy: use r_multiple where available, else raw P&L
            r_multiples = [r.r_multiple for r in working if r.r_multiple is not None]
            if len(r_multiples) >= len(working) * 0.5:
                expectancy = sum(r_multiples) / len(r_multiples)
            else:
                expectancy = sum(r.pnl for r in working) / len(working)

            # Sharpe: annualized from daily P&L
            daily_pnl: dict[date, float] = defaultdict(float)
            for r in working:
                et_date = r.timestamp.astimezone(eastern).date()
                daily_pnl[et_date] += r.pnl

            sharpe: float | None = None
            if len(daily_pnl) >= 5:
                daily_values = list(daily_pnl.values())
                mean_daily = float(np.mean(daily_values))
                std_daily = float(np.std(daily_values, ddof=1))
                if std_daily > 0:
                    sharpe = mean_daily / std_daily * float(np.sqrt(252))

            result[strategy_id] = StrategyMetricsSummary(
                strategy_id=strategy_id,
                sharpe=sharpe,
                win_rate=win_rate,
                expectancy=expectancy,
                trade_count=len(working),
                source=source,
            )

        return result

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

            # P1-D2-L07 (FIX-08): when both source correlations are None
            # the rationale used to render literal "correlation=None"; fall
            # back to 0.0 so the operator-facing string is always numeric.
            correlation = (
                rec.correlation_trade_source
                or rec.correlation_counterfactual_source
                or 0.0
            )
            proposals.append(ConfigProposal(
                proposal_id=str(ULID()),
                report_id=report.report_id,
                field_path=f"weights.{rec.dimension}",
                current_value=rec.current_weight,
                proposed_value=rec.recommended_weight,
                rationale=(
                    f"{rec.dimension}: correlation={correlation:+.4f}, "
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

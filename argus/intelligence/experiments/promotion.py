"""Promotion evaluator for experiment variants.

Compares shadow variant performance against live variants using accumulated
counterfactual and live trade data. Uses Pareto dominance (compare()) to decide
whether to promote a shadow variant to live or demote a live variant to shadow.

This is the first intraday mode adaptation mechanism in ARGUS. Mode changes
(shadow ↔ live) take effect on the next signal processed by _process_signal()
in main.py, which reads ``strategy.config.mode`` at signal time.

Designed to run autonomously at session end, after the Learning Loop, when
``experiments.auto_promote`` is enabled in ``config/experiments.yaml``.

Sprint 32, Session 7.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, date, datetime

from argus.analytics.comparison import compare
from argus.analytics.evaluation import (
    ComparisonVerdict,
    MultiObjectiveResult,
    compute_confidence_tier,
)
from argus.core.ids import generate_id
from argus.intelligence.experiments.models import (
    ExperimentRecord,
    PromotionEvent,
    VariantDefinition,
)
from argus.intelligence.experiments.store import ExperimentStore

logger = logging.getLogger(__name__)


class PromotionEvaluator:
    """Evaluates shadow variants for promotion to live and live variants for demotion.

    Uses Pareto dominance to compare a shadow variant's counterfactual performance
    against live variants for the same base pattern. Hysteresis prevents
    newly-promoted variants from being immediately demoted.

    Promotion/demotion is idempotent — promoting an already-live variant or
    demoting an already-shadow variant is a no-op.

    PromotionEvents are persisted to ExperimentStore before mode changes take
    effect, ensuring atomic safety if the process crashes mid-promotion.

    Args:
        store: ExperimentStore for variant and promotion event persistence.
        counterfactual_store: CounterfactualStore for shadow results.
            Duck-typed to avoid circular imports.
        trade_logger: TradeLogger for live trade results.
            Duck-typed to avoid circular imports.
        config: Experiments YAML config dict. Recognised keys:
            ``promotion_min_shadow_trades`` (int, default 30),
            ``promotion_min_shadow_days`` (int, default 5).
    """

    def __init__(
        self,
        store: ExperimentStore,
        counterfactual_store: object,
        trade_logger: object,
        config: dict[str, object],
    ) -> None:
        self._store = store
        self._counterfactual_store = counterfactual_store
        self._trade_logger = trade_logger
        self._min_shadow_trades: int = int(
            config.get("promotion_min_shadow_trades", 30)
        )
        self._min_shadow_days: int = int(
            config.get("promotion_min_shadow_days", 5)
        )

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    async def evaluate_all_variants(self) -> list[PromotionEvent]:
        """Evaluate all active variants for promotion or demotion.

        Groups variants by ``base_pattern``, then for each pattern evaluates
        shadow variants for promotion and non-baseline live variants for
        demotion.

        Returns:
            All PromotionEvents generated during this evaluation pass.
        """
        all_variants = await self._store.list_variants()
        events: list[PromotionEvent] = []

        # Group by base_pattern
        by_pattern: dict[str, list[VariantDefinition]] = {}
        for variant in all_variants:
            by_pattern.setdefault(variant.base_pattern, []).append(variant)

        for pattern_name, variants in by_pattern.items():
            live_variants = [v for v in variants if v.mode == "live"]
            shadow_variants = [v for v in variants if v.mode == "shadow"]
            baseline = await self._store.get_baseline(pattern_name)

            for shadow_variant in shadow_variants:
                event = await self._evaluate_for_promotion(
                    shadow_variant, live_variants
                )
                if event is not None:
                    events.append(event)
                    # Append the newly-promoted variant to live_variants so
                    # subsequent shadow variants for this pattern compare against
                    # the updated set.
                    live_variants = live_variants + [
                        VariantDefinition(
                            variant_id=shadow_variant.variant_id,
                            base_pattern=shadow_variant.base_pattern,
                            parameter_fingerprint=shadow_variant.parameter_fingerprint,
                            parameters=shadow_variant.parameters,
                            mode="live",
                            source=shadow_variant.source,
                            created_at=shadow_variant.created_at,
                        )
                    ]

            for live_variant in live_variants:
                event = await self._evaluate_for_demotion(live_variant, baseline)
                if event is not None:
                    events.append(event)

        return events

    # ---------------------------------------------------------------------------
    # Promotion path
    # ---------------------------------------------------------------------------

    async def _evaluate_for_promotion(
        self,
        shadow_variant: VariantDefinition,
        live_variants: list[VariantDefinition],
    ) -> PromotionEvent | None:
        """Evaluate whether a shadow variant should be promoted to live.

        Promotion requires:
        1. Minimum shadow trade count (``promotion_min_shadow_trades``).
        2. Minimum shadow trading days (``promotion_min_shadow_days``).
        3. Shadow result Pareto-dominates at least one live variant.

        PromotionEvent is persisted BEFORE the mode update to ensure
        the decision is durable if the process crashes.

        Args:
            shadow_variant: The shadow variant to evaluate.
            live_variants: Current live variants for the same base pattern.

        Returns:
            PromotionEvent with action="promote", or None if promotion
            criteria are not met.
        """
        # Idempotency guard — already live
        if shadow_variant.mode == "live":
            return None

        shadow_result = await self._build_result_from_shadow(shadow_variant.variant_id)
        if shadow_result is None:
            return None

        shadow_trades = shadow_result.total_trades
        if shadow_trades < self._min_shadow_trades:
            logger.debug(
                "Shadow variant %s below min trades threshold (%d < %d)",
                shadow_variant.variant_id,
                shadow_trades,
                self._min_shadow_trades,
            )
            return None

        shadow_days = await self._count_shadow_trading_days(shadow_variant.variant_id)
        if shadow_days < self._min_shadow_days:
            logger.debug(
                "Shadow variant %s below min days threshold (%d < %d)",
                shadow_variant.variant_id,
                shadow_days,
                self._min_shadow_days,
            )
            return None

        if not live_variants:
            logger.debug(
                "Shadow variant %s has no live variants to compare against",
                shadow_variant.variant_id,
            )
            return None

        # Promote if shadow Pareto-dominates at least one live variant
        dominated_live: VariantDefinition | None = None
        verdict_str: str | None = None

        for live_variant in live_variants:
            live_result = await self._build_result_from_trades(live_variant.variant_id)
            if live_result is None:
                continue
            verdict = compare(shadow_result, live_result)
            if verdict == ComparisonVerdict.DOMINATES:
                dominated_live = live_variant
                verdict_str = str(verdict)
                break

        if dominated_live is None:
            return None

        event = PromotionEvent(
            event_id=generate_id(),
            variant_id=shadow_variant.variant_id,
            action="promote",
            previous_mode="shadow",
            new_mode="live",
            reason=(
                f"Shadow variant Pareto-dominates live variant "
                f"{dominated_live.variant_id} "
                f"after {shadow_trades} shadow trades ({shadow_days} days)"
            ),
            comparison_verdict=verdict_str,
            shadow_trades=shadow_trades,
            shadow_expectancy=shadow_result.expectancy_per_trade,
            timestamp=datetime.now(UTC),
        )

        # Persist event BEFORE mode change (atomic safety)
        await self._store.save_promotion_event(event)
        await self._store.update_variant_mode(shadow_variant.variant_id, "live")

        logger.info(
            "Promoted variant %s from shadow to live (trades=%d, days=%d)",
            shadow_variant.variant_id,
            shadow_trades,
            shadow_days,
        )
        return event

    # ---------------------------------------------------------------------------
    # Demotion path
    # ---------------------------------------------------------------------------

    async def _evaluate_for_demotion(
        self,
        live_variant: VariantDefinition,
        baseline: ExperimentRecord | None,
    ) -> PromotionEvent | None:
        """Evaluate whether a live variant should be demoted to shadow.

        Demotion requires:
        1. A baseline experiment record with a serialised backtest_result.
        2. Baseline Pareto-dominates the live variant's actual performance.
        3. Hysteresis: at least ``promotion_min_shadow_days`` must have passed
           since the most recent promotion of this variant.

        PromotionEvent is persisted BEFORE the mode update to ensure
        the decision is durable if the process crashes.

        Args:
            live_variant: The live variant to evaluate.
            baseline: Baseline ExperimentRecord for this pattern, or None.

        Returns:
            PromotionEvent with action="demote", or None if demotion
            criteria are not met.
        """
        # Idempotency guard — already shadow
        if live_variant.mode == "shadow":
            return None

        if baseline is None or baseline.backtest_result is None:
            return None

        # Hysteresis: skip demotion if promoted too recently
        past_events = await self._store.list_promotion_events(
            variant_id=live_variant.variant_id
        )
        last_promote = next(
            (e for e in past_events if e.action == "promote"),
            None,
        )
        if last_promote is not None:
            days_since = (datetime.now(UTC) - last_promote.timestamp).days
            if days_since < self._min_shadow_days:
                logger.debug(
                    "Skipping demotion of %s — only %d days since last promotion "
                    "(hysteresis min=%d)",
                    live_variant.variant_id,
                    days_since,
                    self._min_shadow_days,
                )
                return None

        live_result = await self._build_result_from_trades(live_variant.variant_id)
        if live_result is None:
            return None

        baseline_result = MultiObjectiveResult.from_dict(baseline.backtest_result)
        verdict = compare(baseline_result, live_result)
        if verdict != ComparisonVerdict.DOMINATES:
            return None

        live_trades = live_result.total_trades
        event = PromotionEvent(
            event_id=generate_id(),
            variant_id=live_variant.variant_id,
            action="demote",
            previous_mode="live",
            new_mode="shadow",
            reason=(
                f"Baseline Pareto-dominates live variant after {live_trades} trades"
            ),
            comparison_verdict=str(verdict),
            shadow_trades=live_trades,
            shadow_expectancy=live_result.expectancy_per_trade,
            timestamp=datetime.now(UTC),
        )

        # Persist event BEFORE mode change (atomic safety)
        await self._store.save_promotion_event(event)
        await self._store.update_variant_mode(live_variant.variant_id, "shadow")

        logger.info(
            "Demoted variant %s from live to shadow (trades=%d)",
            live_variant.variant_id,
            live_trades,
        )
        return event

    # ---------------------------------------------------------------------------
    # Result builders
    # ---------------------------------------------------------------------------

    async def _build_result_from_trades(
        self,
        strategy_id: str,
    ) -> MultiObjectiveResult | None:
        """Build a MultiObjectiveResult from live trade data.

        Args:
            strategy_id: Strategy ID to query trade data for.

        Returns:
            MultiObjectiveResult, or None if fewer than 2 trades.
        """
        trades = await self._trade_logger.query_trades(
            strategy_id=strategy_id, limit=1000
        )
        if not trades:
            return None

        r_multiples = [
            float(t["r_multiple"])
            for t in trades
            if t.get("r_multiple") is not None
        ]
        return self._compute_result(strategy_id, r_multiples)

    async def _build_result_from_shadow(
        self,
        strategy_id: str,
    ) -> MultiObjectiveResult | None:
        """Build a MultiObjectiveResult from shadow (counterfactual) data.

        Args:
            strategy_id: Strategy ID to query shadow positions for.

        Returns:
            MultiObjectiveResult, or None if counterfactual store is unavailable
            or fewer than 2 closed positions exist.
        """
        if self._counterfactual_store is None:
            return None
        positions = await self._counterfactual_store.query(
            strategy_id=strategy_id, limit=1000
        )
        closed = [
            p for p in positions
            if p.get("theoretical_r_multiple") is not None
        ]
        if not closed:
            return None

        r_multiples = [float(p["theoretical_r_multiple"]) for p in closed]
        return self._compute_result(strategy_id, r_multiples)

    async def _count_shadow_trading_days(self, strategy_id: str) -> int:
        """Count unique trading days with shadow positions for a strategy.

        Args:
            strategy_id: Strategy ID to count trading days for.

        Returns:
            Number of unique calendar dates with at least one shadow position,
            or 0 if the counterfactual store is unavailable.
        """
        if self._counterfactual_store is None:
            return 0
        positions = await self._counterfactual_store.query(
            strategy_id=strategy_id, limit=1000
        )
        unique_days: set[str] = set()
        for pos in positions:
            opened_at = pos.get("opened_at")
            if opened_at is not None:
                unique_days.add(str(opened_at)[:10])
        return len(unique_days)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _compute_result(
        strategy_id: str,
        r_multiples: list[float],
    ) -> MultiObjectiveResult | None:
        """Compute a MultiObjectiveResult from a list of R-multiples.

        Uses R-multiples as a proxy for per-trade returns. Computes all five
        Pareto comparison metrics: Sharpe, max drawdown, profit factor, win
        rate, and expectancy.

        Args:
            strategy_id: Strategy identifier for the result.
            r_multiples: Per-trade R-multiple values.

        Returns:
            MultiObjectiveResult, or None if fewer than 2 data points.
        """
        n = len(r_multiples)
        if n < 2:
            return None

        wins = [r for r in r_multiples if r > 0]
        losses = [r for r in r_multiples if r <= 0]

        win_rate = len(wins) / n
        expectancy = sum(r_multiples) / n

        gross_wins = sum(wins) if wins else 0.0
        gross_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = (
            gross_wins / gross_losses if gross_losses > 0 else float("inf")
        )

        mean_r = expectancy
        variance = sum((r - mean_r) ** 2 for r in r_multiples) / (n - 1)
        std_r = math.sqrt(variance) if variance > 0 else 0.0
        # Annualise-equivalent Sharpe using sqrt(n) as a scaling proxy
        sharpe = (mean_r / std_r * math.sqrt(n)) if std_r > 0 else 0.0

        # Peak-to-trough drawdown over the cumulative R sequence
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in r_multiples:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            denominator = max(abs(peak), 1.0)
            dd = (peak - cumulative) / denominator
            if dd > max_dd:
                max_dd = dd
        max_drawdown_pct = -max_dd

        confidence = compute_confidence_tier(
            total_trades=n,
            regime_trade_counts={},
        )

        today = date.today()
        return MultiObjectiveResult(
            strategy_id=strategy_id,
            parameter_hash=strategy_id,
            evaluation_date=datetime.now(UTC),
            data_range=(today, today),
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_drawdown_pct,
            profit_factor=profit_factor,
            win_rate=win_rate,
            total_trades=n,
            expectancy_per_trade=expectancy,
            confidence_tier=confidence,
        )

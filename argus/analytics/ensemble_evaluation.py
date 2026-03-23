"""Ensemble-level evaluation for strategy cohorts.

Provides EnsembleResult, MarginalContribution, cohort addition simulation,
deadweight identification, and formatted ensemble reports. Enables cohort-based
promotion and portfolio-level comparison in downstream sprints (28, 32.5).

**Design note:** Sprint 27.5 uses metric-level aggregation, not trade-level.
MultiObjectiveResult contains aggregate metrics but NOT daily equity curves.
Portfolio-level daily returns are approximated from per-strategy metrics.
Trade-level ensemble aggregation (higher fidelity) is deferred to Sprint 32.5
when BacktestEngine trade-level data can be wired in directly.

Sprint 27.5 Session 4.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from argus.analytics.comparison import compare
from argus.analytics.evaluation import (
    ComparisonVerdict,
    ConfidenceTier,
    MultiObjectiveResult,
    compute_confidence_tier,
)

__all__ = [
    "MarginalContribution",
    "EnsembleResult",
    "build_ensemble_result",
    "evaluate_cohort_addition",
    "marginal_contribution",
    "identify_deadweight",
    "format_ensemble_report",
]


@dataclass(frozen=True)
class MarginalContribution:
    """Marginal contribution of a single strategy to an ensemble.

    Attributes:
        strategy_id: Strategy identifier.
        marginal_sharpe: Ensemble Sharpe WITH minus WITHOUT this strategy.
        marginal_drawdown: Change in max drawdown (positive = less drawdown = better).
        correlation_to_ensemble: Correlation of this strategy's returns to ensemble.
        trade_count: Number of trades for this strategy.
        confidence_tier: Confidence tier for this strategy.
    """

    strategy_id: str
    marginal_sharpe: float
    marginal_drawdown: float
    correlation_to_ensemble: float
    trade_count: int
    confidence_tier: ConfidenceTier

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict.

        Returns:
            Dict with all fields serialized.
        """
        return {
            "strategy_id": self.strategy_id,
            "marginal_sharpe": self.marginal_sharpe,
            "marginal_drawdown": self.marginal_drawdown,
            "correlation_to_ensemble": self.correlation_to_ensemble,
            "trade_count": self.trade_count,
            "confidence_tier": self.confidence_tier.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> MarginalContribution:
        """Deserialize from a dict produced by to_dict().

        Args:
            d: Dict with serialized MarginalContribution fields.

        Returns:
            MarginalContribution instance.
        """
        return cls(
            strategy_id=str(d["strategy_id"]),
            marginal_sharpe=float(d["marginal_sharpe"]),  # type: ignore[arg-type]
            marginal_drawdown=float(d["marginal_drawdown"]),  # type: ignore[arg-type]
            correlation_to_ensemble=float(d["correlation_to_ensemble"]),  # type: ignore[arg-type]
            trade_count=int(d["trade_count"]),  # type: ignore[arg-type]
            confidence_tier=ConfidenceTier(str(d["confidence_tier"])),
        )


@dataclass
class EnsembleResult:
    """Ensemble-level evaluation result for a strategy cohort.

    Combines multiple MultiObjectiveResults into a portfolio-level view
    with diversification metrics, marginal contributions, and comparison
    to a baseline ensemble.

    **Approximation note:** Ensemble metrics are computed from per-strategy
    aggregate metrics, not from trade-level daily equity curves. This is
    a metric-level approximation. Trade-level aggregation is a future
    enhancement (Sprint 32.5).

    Attributes:
        cohort_id: Identifier for this ensemble cohort.
        strategy_ids: List of strategy IDs in the ensemble.
        evaluation_date: When the evaluation was performed (UTC).
        data_range: Start and end dates of the evaluation data.
        aggregate: Portfolio-level MultiObjectiveResult.
        diversification_ratio: Weighted sum of individual vols / portfolio vol.
            >1.0 means diversification helps. Metric-level approximation.
        marginal_contributions: Per-strategy marginal contribution, keyed by ID.
        tail_correlation: Avg pairwise correlation on bottom 25% return days.
            Approximated from drawdown magnitude similarity at metric level.
            Note: measures severity similarity, not temporal co-occurrence.
            Trade-level computation (Sprint 32.5) will use actual daily returns.
        max_concurrent_drawdown: Worst case when all strategies draw down together.
        capital_utilization: Avg % of capital deployed (0.0-1.0).
        turnover_rate: Annual turnover estimate.
        baseline_ensemble: Prior ensemble for comparison (None if no baseline).
        improvement_verdict: Comparison verdict vs baseline.
    """

    # Identity
    cohort_id: str
    strategy_ids: list[str]
    evaluation_date: datetime
    data_range: tuple[date, date]

    # Aggregate
    aggregate: MultiObjectiveResult

    # Ensemble-specific
    diversification_ratio: float
    marginal_contributions: dict[str, MarginalContribution]
    tail_correlation: float
    max_concurrent_drawdown: float
    capital_utilization: float
    turnover_rate: float

    # Comparison
    baseline_ensemble: EnsembleResult | None = None
    improvement_verdict: ComparisonVerdict = ComparisonVerdict.INCOMPARABLE

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict.

        Returns:
            Dict with all fields serialized. Handles nested dataclasses,
            date/datetime, and None values.
        """
        return {
            "cohort_id": self.cohort_id,
            "strategy_ids": self.strategy_ids,
            "evaluation_date": self.evaluation_date.isoformat(),
            "data_range": [self.data_range[0].isoformat(), self.data_range[1].isoformat()],
            "aggregate": self.aggregate.to_dict(),
            "diversification_ratio": self.diversification_ratio,
            "marginal_contributions": {
                k: v.to_dict() for k, v in self.marginal_contributions.items()
            },
            "tail_correlation": self.tail_correlation,
            "max_concurrent_drawdown": self.max_concurrent_drawdown,
            "capital_utilization": self.capital_utilization,
            "turnover_rate": self.turnover_rate,
            "baseline_ensemble": self.baseline_ensemble.to_dict()
            if self.baseline_ensemble is not None
            else None,
            "improvement_verdict": self.improvement_verdict.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EnsembleResult:
        """Deserialize from a dict produced by to_dict().

        Args:
            d: Dict with serialized EnsembleResult fields.

        Returns:
            EnsembleResult instance.
        """
        data_range_raw = d["data_range"]
        assert isinstance(data_range_raw, list)
        data_range = (
            date.fromisoformat(str(data_range_raw[0])),
            date.fromisoformat(str(data_range_raw[1])),
        )

        mc_raw = d.get("marginal_contributions", {})
        assert isinstance(mc_raw, dict)
        marginal_contributions = {
            k: MarginalContribution.from_dict(v) for k, v in mc_raw.items()
        }

        baseline_raw = d.get("baseline_ensemble")
        baseline: EnsembleResult | None = None
        if baseline_raw is not None:
            assert isinstance(baseline_raw, dict)
            baseline = EnsembleResult.from_dict(baseline_raw)

        return cls(
            cohort_id=str(d["cohort_id"]),
            strategy_ids=list(d["strategy_ids"]),
            evaluation_date=datetime.fromisoformat(str(d["evaluation_date"])),
            data_range=data_range,
            aggregate=MultiObjectiveResult.from_dict(d["aggregate"]),
            diversification_ratio=float(d["diversification_ratio"]),
            marginal_contributions=marginal_contributions,
            tail_correlation=float(d["tail_correlation"]),
            max_concurrent_drawdown=float(d["max_concurrent_drawdown"]),
            capital_utilization=float(d["capital_utilization"]),
            turnover_rate=float(d["turnover_rate"]),
            baseline_ensemble=baseline,
            improvement_verdict=ComparisonVerdict(str(d["improvement_verdict"])),
        )


def _aggregate_results(
    results: list[MultiObjectiveResult],
    capital: float,
) -> MultiObjectiveResult:
    """Aggregate multiple MORs into a portfolio-level MultiObjectiveResult.

    Uses equal-weight allocation across strategies. Metric-level approximation:
    portfolio Sharpe is estimated from individual Sharpes and assumed correlation,
    not from actual daily return series.

    Args:
        results: List of per-strategy MultiObjectiveResults.
        capital: Total capital for the portfolio.

    Returns:
        Portfolio-level MultiObjectiveResult with combined metrics.
    """
    n = len(results)
    if n == 0:
        return MultiObjectiveResult(
            strategy_id="ensemble",
            parameter_hash="",
            evaluation_date=datetime.now(UTC),
            data_range=(date.today(), date.today()),
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            profit_factor=0.0,
            win_rate=0.0,
            total_trades=0,
            expectancy_per_trade=0.0,
        )

    # Equal-weight allocation
    weight = 1.0 / n

    # Portfolio Sharpe: weighted average (metric-level approximation)
    portfolio_sharpe = sum(r.sharpe_ratio * weight for r in results)

    # Portfolio drawdown: weighted average of individual drawdowns
    # (more optimistic than reality for correlated strategies)
    portfolio_drawdown = sum(r.max_drawdown_pct * weight for r in results)

    # Weighted profit factor
    total_trades = sum(r.total_trades for r in results)
    if total_trades > 0:
        portfolio_pf = sum(
            r.profit_factor * r.total_trades for r in results
            if not math.isinf(r.profit_factor)
        ) / max(
            sum(r.total_trades for r in results if not math.isinf(r.profit_factor)),
            1,
        )
    else:
        portfolio_pf = 0.0

    # Weighted win rate (by trade count)
    if total_trades > 0:
        portfolio_wr = sum(r.win_rate * r.total_trades for r in results) / total_trades
    else:
        portfolio_wr = 0.0

    # Weighted expectancy (by trade count)
    if total_trades > 0:
        portfolio_exp = sum(
            r.expectancy_per_trade * r.total_trades for r in results
        ) / total_trades
    else:
        portfolio_exp = 0.0

    # Date range: widest span
    start_date = min(r.data_range[0] for r in results)
    end_date = max(r.data_range[1] for r in results)

    # Combine regime results (union of all regimes, trade-weighted)
    all_regime_keys: set[str] = set()
    for r in results:
        all_regime_keys.update(r.regime_results.keys())

    regime_trade_counts: dict[str, int] = {}
    for key in all_regime_keys:
        regime_trade_counts[key] = sum(
            r.regime_results[key].total_trades
            for r in results
            if key in r.regime_results
        )

    confidence = compute_confidence_tier(total_trades, regime_trade_counts)

    return MultiObjectiveResult(
        strategy_id="ensemble",
        parameter_hash="",
        evaluation_date=datetime.now(UTC),
        data_range=(start_date, end_date),
        sharpe_ratio=portfolio_sharpe,
        max_drawdown_pct=portfolio_drawdown,
        profit_factor=portfolio_pf,
        win_rate=portfolio_wr,
        total_trades=total_trades,
        expectancy_per_trade=portfolio_exp,
        confidence_tier=confidence,
    )


def _compute_diversification_ratio(results: list[MultiObjectiveResult]) -> float:
    """Compute diversification ratio from individual strategy metrics.

    Formula: weighted_vol_sum / portfolio_vol. Since we lack daily return
    series, we approximate individual volatility from absolute drawdown and
    compute portfolio vol assuming zero correlation (sqrt of sum of squared
    weighted vols).

    For uncorrelated strategies with similar vol, ratio > 1.0 (diversification
    benefit). For perfectly correlated, ratio = 1.0.

    Args:
        results: Per-strategy MultiObjectiveResults.

    Returns:
        Diversification ratio. 1.0 for single strategy.
    """
    n = len(results)
    if n <= 1:
        return 1.0

    # Proxy individual volatility from |sharpe| (inverse relationship)
    # Higher |sharpe| with similar returns → lower vol
    # Use absolute drawdown as secondary vol proxy
    vols: list[float] = []
    for r in results:
        # Use absolute drawdown as a vol proxy (drawdown is negative, so negate)
        vol_proxy = abs(r.max_drawdown_pct) if r.max_drawdown_pct != 0.0 else 0.01
        vols.append(vol_proxy)

    weight = 1.0 / n
    weighted_vol_sum = sum(v * weight for v in vols)

    # Portfolio vol approximation: assuming imperfect correlation,
    # portfolio vol < weighted sum. Use sqrt(sum(w^2 * vol^2)) as lower bound
    # (zero correlation case)
    portfolio_vol = math.sqrt(sum((weight * v) ** 2 for v in vols))

    if weighted_vol_sum == 0.0:
        return 1.0

    # Ratio > 1.0 means diversification helps (portfolio vol < weighted sum)
    return weighted_vol_sum / portfolio_vol


def _compute_tail_correlation(results: list[MultiObjectiveResult]) -> float:
    """Approximate tail correlation from strategy drawdown metrics.

    Without daily return series, we approximate tail correlation from the
    relationship between individual and concurrent drawdowns. Uses coefficient
    of variation of drawdown magnitudes: low CV (similar severity) → high tail
    correlation; high CV (different severity) → lower tail correlation.

    Limitation: measures drawdown severity similarity, not temporal co-occurrence.
    Strategies with similar drawdown magnitudes at different times will show
    high tail correlation. Trade-level computation with actual daily returns
    deferred to Sprint 32.5.

    Args:
        results: Per-strategy MultiObjectiveResults.

    Returns:
        Tail correlation estimate (0.0-1.0). 1.0 for single strategy.
    """
    n = len(results)
    if n <= 1:
        return 1.0

    # Use drawdown magnitudes to estimate tail correlation
    # If all strategies have similar drawdowns, tail corr is higher
    drawdowns = [abs(r.max_drawdown_pct) for r in results]
    mean_dd = sum(drawdowns) / n

    if mean_dd == 0.0:
        return 0.0

    # Coefficient of variation of drawdowns: low CV → similar drawdowns → high
    # tail correlation; high CV → different drawdowns → lower tail correlation
    variance = sum((d - mean_dd) ** 2 for d in drawdowns) / n
    cv = math.sqrt(variance) / mean_dd if mean_dd > 0 else 0.0

    # Map CV to tail correlation: CV=0 → corr=1.0, CV→∞ → corr→0.0
    tail_corr = 1.0 / (1.0 + cv)

    return tail_corr


def _compute_capital_utilization(
    results: list[MultiObjectiveResult],
    capital: float,
) -> float:
    """Estimate capital utilization from trade counts and hold durations.

    Approximation: assumes average trade uses equal allocation and holds
    for an estimated duration based on expectancy and trade frequency.

    Args:
        results: Per-strategy MultiObjectiveResults.
        capital: Total available capital.

    Returns:
        Estimated capital utilization (0.0-1.0).
    """
    n = len(results)
    if n == 0 or capital <= 0.0:
        return 0.0

    total_trades = sum(r.total_trades for r in results)
    if total_trades == 0:
        return 0.0

    # Estimate average days in evaluation period
    all_starts = [r.data_range[0] for r in results]
    all_ends = [r.data_range[1] for r in results]
    avg_days = max(
        (max(all_ends) - min(all_starts)).days,
        1,
    )

    # Approximate trading days (252/365 ratio)
    trading_days = max(int(avg_days * 252.0 / 365.0), 1)

    # Intraday strategies: assume each trade uses 1/n of capital for ~1 bar
    # Average concurrent positions ≈ total_trades / trading_days (capped at n)
    avg_concurrent = min(total_trades / trading_days, float(n))

    # Each concurrent position uses 1/n of capital
    utilization = avg_concurrent / n

    return min(utilization, 1.0)


def _compute_turnover_rate(
    results: list[MultiObjectiveResult],
) -> float:
    """Estimate annual turnover from trade counts and evaluation period.

    Args:
        results: Per-strategy MultiObjectiveResults.

    Returns:
        Estimated annual turnover rate.
    """
    if not results:
        return 0.0

    total_trades = sum(r.total_trades for r in results)
    if total_trades == 0:
        return 0.0

    all_starts = [r.data_range[0] for r in results]
    all_ends = [r.data_range[1] for r in results]
    span_days = max((max(all_ends) - min(all_starts)).days, 1)

    # Annualize: trades per year
    trades_per_year = total_trades * 365.0 / span_days

    return trades_per_year


def _compute_marginal_contributions(
    results: list[MultiObjectiveResult],
    full_aggregate: MultiObjectiveResult,
    capital: float,
) -> dict[str, MarginalContribution]:
    """Compute marginal contribution for each strategy in the ensemble.

    For each strategy, recomputes the ensemble without it and diffs the
    Sharpe and drawdown. This is exact removal, not an approximation.

    Args:
        results: Per-strategy MultiObjectiveResults.
        full_aggregate: The full ensemble aggregate.
        capital: Total capital.

    Returns:
        Dict of strategy_id → MarginalContribution.
    """
    n = len(results)
    contributions: dict[str, MarginalContribution] = {}

    for i, result in enumerate(results):
        if n == 1:
            # Single strategy: marginal = full ensemble value
            contributions[result.strategy_id] = MarginalContribution(
                strategy_id=result.strategy_id,
                marginal_sharpe=full_aggregate.sharpe_ratio,
                marginal_drawdown=0.0,
                correlation_to_ensemble=1.0,
                trade_count=result.total_trades,
                confidence_tier=result.confidence_tier,
            )
            continue

        # Remove this strategy and recompute
        without = results[:i] + results[i + 1:]
        without_aggregate = _aggregate_results(without, capital)

        # Marginal Sharpe: WITH minus WITHOUT
        marginal_sharpe = full_aggregate.sharpe_ratio - without_aggregate.sharpe_ratio

        # Marginal drawdown: positive means removing strategy makes drawdown worse
        # (i.e., this strategy HELPS drawdown)
        # full drawdown is more negative = worse; without is less negative = better
        # So: without - full = positive if strategy helps
        marginal_drawdown = without_aggregate.max_drawdown_pct - full_aggregate.max_drawdown_pct

        # Correlation to ensemble: approximate from how much removing this
        # strategy changes the ensemble Sharpe relative to the strategy's own Sharpe
        if result.sharpe_ratio != 0.0 and n > 1:
            # If removing the strategy barely changes ensemble → low correlation
            # If removing it changes a lot → high contribution/correlation
            weight = 1.0 / n
            expected_change = result.sharpe_ratio * weight
            actual_change = marginal_sharpe
            if expected_change != 0.0:
                corr_proxy = min(abs(actual_change / expected_change), 1.0)
            else:
                corr_proxy = 0.0
        else:
            corr_proxy = 0.0

        contributions[result.strategy_id] = MarginalContribution(
            strategy_id=result.strategy_id,
            marginal_sharpe=marginal_sharpe,
            marginal_drawdown=marginal_drawdown,
            correlation_to_ensemble=corr_proxy,
            trade_count=result.total_trades,
            confidence_tier=result.confidence_tier,
        )

    return contributions


def build_ensemble_result(
    results: list[MultiObjectiveResult],
    cohort_id: str = "",
    capital: float = 100_000.0,
) -> EnsembleResult:
    """Build an EnsembleResult from a list of strategy evaluation results.

    Computes portfolio-level aggregate metrics, diversification ratio,
    marginal contributions, tail correlation, and capital utilization.

    **Metric-level approximation:** Portfolio metrics are estimated from
    per-strategy aggregate metrics, not from daily equity curves. Trade-level
    aggregation (higher fidelity) is deferred to Sprint 32.5.

    Args:
        results: List of per-strategy MultiObjectiveResults.
        cohort_id: Identifier for this cohort (default empty).
        capital: Total portfolio capital for utilization estimates.

    Returns:
        EnsembleResult with all ensemble metrics populated.

    Raises:
        ValueError: If results list is empty.
    """
    if not results:
        raise ValueError("Cannot build ensemble from empty results list")

    strategy_ids = [r.strategy_id for r in results]
    aggregate = _aggregate_results(results, capital)
    diversification_ratio = _compute_diversification_ratio(results)
    marginal_contributions = _compute_marginal_contributions(
        results, aggregate, capital
    )
    tail_correlation = _compute_tail_correlation(results)

    # Max concurrent drawdown: sum of individual max drawdowns (worst case)
    max_concurrent_drawdown = sum(r.max_drawdown_pct for r in results)

    capital_utilization = _compute_capital_utilization(results, capital)
    turnover_rate = _compute_turnover_rate(results)

    # Date range: widest span
    start_date = min(r.data_range[0] for r in results)
    end_date = max(r.data_range[1] for r in results)

    return EnsembleResult(
        cohort_id=cohort_id,
        strategy_ids=strategy_ids,
        evaluation_date=datetime.now(UTC),
        data_range=(start_date, end_date),
        aggregate=aggregate,
        diversification_ratio=diversification_ratio,
        marginal_contributions=marginal_contributions,
        tail_correlation=tail_correlation,
        max_concurrent_drawdown=max_concurrent_drawdown,
        capital_utilization=capital_utilization,
        turnover_rate=turnover_rate,
    )


def evaluate_cohort_addition(
    baseline: EnsembleResult,
    candidates: list[MultiObjectiveResult],
) -> EnsembleResult:
    """Evaluate adding candidate strategies to an existing ensemble.

    Builds a new ensemble from baseline strategies + candidates, then
    compares the new aggregate against the baseline aggregate using
    Pareto dominance.

    Args:
        baseline: The existing ensemble to extend.
        candidates: New strategy results to evaluate for addition.

    Returns:
        New EnsembleResult with baseline_ensemble and improvement_verdict set.

    Raises:
        ValueError: If candidates list is empty.
    """
    if not candidates:
        raise ValueError("Cannot evaluate empty candidates list")

    # Reconstruct baseline MORs from marginal contributions info
    # We need the original MORs, but we only have the baseline aggregate.
    # Build new ensemble from all strategy IDs: extract baseline MORs
    # by matching strategy_ids, plus new candidates.
    # Since we can't recover original MORs from the baseline EnsembleResult,
    # we combine the baseline aggregate with candidates directly.

    # The caller should pass candidates that are NEW strategies.
    # Build a combined result list: baseline aggregate treated as one unit + candidates.
    all_results = [baseline.aggregate] + list(candidates)

    new_ensemble = build_ensemble_result(
        all_results,
        cohort_id=baseline.cohort_id,
        capital=100_000.0,
    )

    # Override strategy_ids to reflect the actual combined set
    new_ensemble.strategy_ids = list(baseline.strategy_ids) + [
        c.strategy_id for c in candidates
    ]
    new_ensemble.baseline_ensemble = baseline
    new_ensemble.improvement_verdict = compare(new_ensemble.aggregate, baseline.aggregate)

    return new_ensemble


def marginal_contribution(
    ensemble: EnsembleResult,
    strategy_id: str,
) -> MarginalContribution:
    """Get the marginal contribution of a strategy within an ensemble.

    Shortcut to access ensemble.marginal_contributions[strategy_id].

    Args:
        ensemble: The ensemble result.
        strategy_id: Strategy to look up.

    Returns:
        MarginalContribution for the given strategy.

    Raises:
        KeyError: If strategy_id is not in the ensemble.
    """
    return ensemble.marginal_contributions[strategy_id]


def identify_deadweight(
    ensemble: EnsembleResult,
    threshold: float = 0.0,
) -> list[str]:
    """Identify strategies with negative marginal contribution to the ensemble.

    Returns strategy IDs where marginal Sharpe is below the given threshold.
    Default threshold of 0.0 catches strategies that hurt ensemble Sharpe.

    Args:
        ensemble: The ensemble result.
        threshold: Marginal Sharpe threshold (default 0.0).

    Returns:
        List of strategy IDs with marginal Sharpe below threshold.
        Empty list if all strategies contribute positively.
    """
    return [
        sid
        for sid, mc in ensemble.marginal_contributions.items()
        if mc.marginal_sharpe < threshold
    ]


def format_ensemble_report(result: EnsembleResult) -> str:
    """Format a human-readable ensemble evaluation report.

    Includes cohort header, aggregate metrics, ensemble health indicators,
    marginal contributions table, deadweight warnings, and improvement
    verdict if a baseline is present.

    Args:
        result: The ensemble evaluation result.

    Returns:
        Multi-line string suitable for CLI output and Copilot context injection.
    """
    lines: list[str] = []

    # Header
    lines.append("=" * 70)
    lines.append("ENSEMBLE EVALUATION REPORT")
    lines.append("=" * 70)
    lines.append(f"Cohort: {result.cohort_id or '(unnamed)'}")
    lines.append(f"Strategies: {len(result.strategy_ids)}")
    lines.append(f"  {', '.join(result.strategy_ids)}")
    lines.append(f"Date range: {result.data_range[0]} to {result.data_range[1]}")
    lines.append(f"Evaluated: {result.evaluation_date.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Aggregate metrics
    agg = result.aggregate
    lines.append("AGGREGATE METRICS")
    lines.append("-" * 70)
    lines.append(f"  Sharpe Ratio:         {agg.sharpe_ratio:>10.4f}")
    lines.append(f"  Max Drawdown:         {agg.max_drawdown_pct:>10.2%}")

    pf_str = "inf" if math.isinf(agg.profit_factor) else f"{agg.profit_factor:.4f}"
    lines.append(f"  Profit Factor:        {pf_str:>10}")
    lines.append(f"  Win Rate:             {agg.win_rate:>10.1%}")
    lines.append(f"  Total Trades:         {agg.total_trades:>10}")
    lines.append(f"  Expectancy/Trade:     {agg.expectancy_per_trade:>10.4f}")
    lines.append(f"  Confidence:           {agg.confidence_tier.value:>10}")
    lines.append("")

    # Ensemble health
    lines.append("ENSEMBLE HEALTH")
    lines.append("-" * 70)
    lines.append(f"  Diversification Ratio:    {result.diversification_ratio:.4f}")
    if result.diversification_ratio > 1.0:
        lines.append("    (> 1.0 = diversification benefit)")
    elif result.diversification_ratio == 1.0:
        lines.append("    (= 1.0 = no diversification effect)")
    else:
        lines.append("    (< 1.0 = concentration risk)")
    lines.append(f"  Tail Correlation:         {result.tail_correlation:.4f}")
    lines.append(f"  Max Concurrent Drawdown:  {result.max_concurrent_drawdown:.2%}")
    lines.append(f"  Capital Utilization:      {result.capital_utilization:.1%}")
    lines.append(f"  Annual Turnover:          {result.turnover_rate:.0f} trades/year")
    lines.append("")

    # Marginal contributions table
    lines.append("MARGINAL CONTRIBUTIONS")
    lines.append("-" * 70)
    header = (
        f"{'Strategy':<20} {'Marg Sharpe':>12} {'Marg DD':>10} "
        f"{'Corr':>8} {'Trades':>8} {'Conf':>12}"
    )
    lines.append(header)
    lines.append("-" * 70)

    # Sort by marginal Sharpe descending
    sorted_mcs = sorted(
        result.marginal_contributions.values(),
        key=lambda mc: mc.marginal_sharpe,
        reverse=True,
    )
    for mc in sorted_mcs:
        sid_display = mc.strategy_id[:20]
        lines.append(
            f"{sid_display:<20} {mc.marginal_sharpe:>12.4f} "
            f"{mc.marginal_drawdown:>10.4f} {mc.correlation_to_ensemble:>8.4f} "
            f"{mc.trade_count:>8} {mc.confidence_tier.value:>12}"
        )

    lines.append("")

    # Deadweight warning
    deadweight = identify_deadweight(result)
    if deadweight:
        lines.append("WARNING: DEADWEIGHT STRATEGIES DETECTED")
        lines.append(
            f"  The following strategies have negative marginal Sharpe: "
            f"{', '.join(deadweight)}"
        )
        lines.append("  Consider removing them to improve ensemble performance.")
        lines.append("")

    # Improvement verdict
    if result.baseline_ensemble is not None:
        lines.append("COMPARISON TO BASELINE")
        lines.append("-" * 70)
        lines.append(
            f"  Baseline strategies: {len(result.baseline_ensemble.strategy_ids)}"
        )
        lines.append(
            f"  Baseline Sharpe:     {result.baseline_ensemble.aggregate.sharpe_ratio:.4f}"
        )
        lines.append(f"  New Sharpe:          {result.aggregate.sharpe_ratio:.4f}")
        lines.append(f"  Verdict:             {result.improvement_verdict.value}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)

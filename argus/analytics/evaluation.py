"""Evaluation framework core data models.

Defines MultiObjectiveResult, RegimeMetrics, ConfidenceTier, and comparison
verdicts — the shared currency for all downstream optimization and experiment
sprints (28, 32.5, 33, 34, 38).

Sprint 27.5 Session 1.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argus.backtest.metrics import BacktestResult

__all__ = [
    "RegimeMetrics",
    "ConfidenceTier",
    "ComparisonVerdict",
    "MultiObjectiveResult",
    "compute_confidence_tier",
    "parameter_hash",
    "from_backtest_result",
]


@dataclass(frozen=True)
class RegimeMetrics:
    """Per-regime performance metrics.

    Attributes:
        sharpe_ratio: Annualized Sharpe ratio for this regime.
        max_drawdown_pct: Maximum drawdown as negative decimal (e.g. -0.12 = 12%).
        profit_factor: Gross wins / gross losses (inf if no losses).
        win_rate: Winning trades / total trades (0.0–1.0).
        total_trades: Number of trades in this regime.
        expectancy_per_trade: Expected R-multiple per trade.
    """

    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    win_rate: float
    total_trades: int
    expectancy_per_trade: float

    def to_dict(self) -> dict[str, float | int | str]:
        """Serialize to a plain dict.

        Returns:
            Dict with all fields. Infinite profit_factor preserved as string
            "Infinity" for JSON compatibility.
        """
        pf = self.profit_factor
        return {
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_pct": self.max_drawdown_pct,
            "profit_factor": "Infinity" if pf == float("inf") else ("-Infinity" if pf == float("-inf") else pf),
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "expectancy_per_trade": self.expectancy_per_trade,
        }

    @classmethod
    def from_dict(cls, d: dict[str, float | int | str]) -> RegimeMetrics:
        """Deserialize from a plain dict.

        Args:
            d: Dict produced by to_dict().

        Returns:
            RegimeMetrics instance.
        """
        pf = d["profit_factor"]
        profit_factor = float("inf") if pf == "Infinity" else (float("-inf") if pf == "-Infinity" else float(pf))
        return cls(
            sharpe_ratio=float(d["sharpe_ratio"]),
            max_drawdown_pct=float(d["max_drawdown_pct"]),
            profit_factor=profit_factor,
            win_rate=float(d["win_rate"]),
            total_trades=int(d["total_trades"]),
            expectancy_per_trade=float(d["expectancy_per_trade"]),
        )


class ConfidenceTier(StrEnum):
    """Confidence tier based on trade count and regime distribution.

    HIGH: 50+ trades total AND 15+ trades in >=3 regime types.
    MODERATE: 30+ trades AND 10+ trades in >=2 regime types
              (OR 50+ trades but insufficient regime coverage for HIGH).
    LOW: 10–29 trades total.
    ENSEMBLE_ONLY: <10 trades total.
    """

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    ENSEMBLE_ONLY = "ensemble_only"


class ComparisonVerdict(StrEnum):
    """Result of comparing two MultiObjectiveResults.

    DOMINATES: A is strictly better on all comparison metrics.
    DOMINATED: B is strictly better on all comparison metrics.
    INCOMPARABLE: Mixed results across metrics.
    INSUFFICIENT_DATA: Confidence too low for meaningful comparison.
    """

    DOMINATES = "dominates"
    DOMINATED = "dominated"
    INCOMPARABLE = "incomparable"
    INSUFFICIENT_DATA = "insufficient_data"


def compute_confidence_tier(
    total_trades: int,
    regime_trade_counts: dict[str, int],
) -> ConfidenceTier:
    """Compute confidence tier from trade count and regime distribution.

    Args:
        total_trades: Total number of trades across all regimes.
        regime_trade_counts: Mapping of regime key to trade count in that regime.

    Returns:
        The appropriate ConfidenceTier.
    """
    regimes_with_15_plus = sum(1 for c in regime_trade_counts.values() if c >= 15)
    regimes_with_10_plus = sum(1 for c in regime_trade_counts.values() if c >= 10)

    if total_trades >= 50 and regimes_with_15_plus >= 3:
        return ConfidenceTier.HIGH
    if total_trades >= 30 and regimes_with_10_plus >= 2:
        return ConfidenceTier.MODERATE
    # 50+ trades but insufficient regime coverage for HIGH → MODERATE
    if total_trades >= 50:
        return ConfidenceTier.MODERATE
    if total_trades >= 10:
        return ConfidenceTier.LOW
    return ConfidenceTier.ENSEMBLE_ONLY


def parameter_hash(config: dict[str, object]) -> str:
    """Compute a deterministic hash of a parameter config dict.

    Args:
        config: Strategy parameter dictionary.

    Returns:
        16-character hex string. Same dict with different key ordering
        produces the same hash.
    """
    serialized = json.dumps(config, sort_keys=True, default=str).encode()
    return hashlib.sha256(serialized).hexdigest()[:16]


@dataclass
class MultiObjectiveResult:
    """Multi-objective evaluation result for a strategy parameter set.

    Bridges BacktestResult into a format suitable for Pareto comparison,
    ensemble evaluation, and experiment tracking.

    Attributes:
        strategy_id: Strategy identifier.
        parameter_hash: Deterministic hash of the parameter config.
        evaluation_date: When the evaluation was performed (UTC).
        data_range: Start and end dates of the evaluation data.
        sharpe_ratio: Annualized Sharpe ratio.
        max_drawdown_pct: Maximum drawdown as negative decimal.
        profit_factor: Gross wins / gross losses.
        win_rate: Winning trades / total trades.
        total_trades: Number of trades.
        expectancy_per_trade: Expected R-multiple per trade.
        regime_results: Per-regime metrics, string-keyed for Sprint 27.6 compat.
        confidence_tier: Computed confidence tier.
        p_value: Statistical significance placeholder (populated in Sprint 33).
        confidence_interval: CI placeholder (populated in Sprint 33).
        wfe: Walk-forward efficiency (0.0 if not from walk-forward).
        is_oos: Whether this result is from out-of-sample data.
        execution_quality_adjustment: Slippage adjustment (populated in S6).
    """

    # Identity
    strategy_id: str
    parameter_hash: str
    evaluation_date: datetime
    data_range: tuple[date, date]

    # Primary metrics
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    win_rate: float
    total_trades: int
    expectancy_per_trade: float

    # Regime
    regime_results: dict[str, RegimeMetrics] = field(default_factory=dict)

    # Confidence
    confidence_tier: ConfidenceTier = ConfidenceTier.ENSEMBLE_ONLY

    # Statistical placeholders
    p_value: float | None = None
    confidence_interval: tuple[float, float] | None = None

    # Walk-forward
    wfe: float = 0.0
    is_oos: bool = False

    # Execution quality
    execution_quality_adjustment: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict.

        Returns:
            Dict with all fields serialized. Handles date, datetime, None,
            and infinite float values.
        """
        pf = self.profit_factor
        return {
            "strategy_id": self.strategy_id,
            "parameter_hash": self.parameter_hash,
            "evaluation_date": self.evaluation_date.isoformat(),
            "data_range": [self.data_range[0].isoformat(), self.data_range[1].isoformat()],
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_pct": self.max_drawdown_pct,
            "profit_factor": "Infinity" if pf == float("inf") else ("-Infinity" if pf == float("-inf") else pf),
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "expectancy_per_trade": self.expectancy_per_trade,
            "regime_results": {k: v.to_dict() for k, v in self.regime_results.items()},
            "confidence_tier": self.confidence_tier.value,
            "p_value": self.p_value,
            "confidence_interval": list(self.confidence_interval)
            if self.confidence_interval is not None
            else None,
            "wfe": self.wfe,
            "is_oos": self.is_oos,
            "execution_quality_adjustment": self.execution_quality_adjustment,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> MultiObjectiveResult:
        """Deserialize from a dict produced by to_dict().

        Args:
            d: Dict with serialized MOR fields.

        Returns:
            MultiObjectiveResult instance.
        """
        # Parse data_range
        data_range_raw = d["data_range"]
        if not isinstance(data_range_raw, list):
            raise TypeError(f"data_range must be a list, got {type(data_range_raw).__name__}")
        data_range = (
            date.fromisoformat(str(data_range_raw[0])),
            date.fromisoformat(str(data_range_raw[1])),
        )

        # Parse regime_results
        regime_raw = d.get("regime_results", {})
        if not isinstance(regime_raw, dict):
            raise TypeError(f"regime_results must be a dict, got {type(regime_raw).__name__}")
        regime_results = {k: RegimeMetrics.from_dict(v) for k, v in regime_raw.items()}

        # Parse profit_factor
        pf_raw = d["profit_factor"]
        profit_factor = float("inf") if pf_raw == "Infinity" else (float("-inf") if pf_raw == "-Infinity" else float(pf_raw))  # type: ignore[arg-type]

        # Parse confidence_interval
        ci_raw = d.get("confidence_interval")
        confidence_interval: tuple[float, float] | None = None
        if ci_raw is not None:
            if not isinstance(ci_raw, list):
                raise TypeError(f"confidence_interval must be a list, got {type(ci_raw).__name__}")
            confidence_interval = (float(ci_raw[0]), float(ci_raw[1]))

        # Parse p_value
        p_value_raw = d.get("p_value")
        p_value: float | None = float(p_value_raw) if p_value_raw is not None else None  # type: ignore[arg-type]

        # Parse execution_quality_adjustment
        eqa_raw = d.get("execution_quality_adjustment")
        eqa: float | None = float(eqa_raw) if eqa_raw is not None else None  # type: ignore[arg-type]

        return cls(
            strategy_id=str(d["strategy_id"]),
            parameter_hash=str(d["parameter_hash"]),
            evaluation_date=datetime.fromisoformat(str(d["evaluation_date"])),
            data_range=data_range,
            sharpe_ratio=float(d["sharpe_ratio"]),  # type: ignore[arg-type]
            max_drawdown_pct=float(d["max_drawdown_pct"]),  # type: ignore[arg-type]
            profit_factor=profit_factor,
            win_rate=float(d["win_rate"]),  # type: ignore[arg-type]
            total_trades=int(d["total_trades"]),  # type: ignore[arg-type]
            expectancy_per_trade=float(d["expectancy_per_trade"]),  # type: ignore[arg-type]
            regime_results=regime_results,
            confidence_tier=ConfidenceTier(str(d["confidence_tier"])),
            p_value=p_value,
            confidence_interval=confidence_interval,
            wfe=float(d.get("wfe", 0.0)),  # type: ignore[arg-type]
            is_oos=bool(d.get("is_oos", False)),
            execution_quality_adjustment=eqa,
        )


def from_backtest_result(
    result: BacktestResult,
    regime_results: dict[str, RegimeMetrics] | None = None,
    wfe: float = 0.0,
    is_oos: bool = False,
    parameter_hash_value: str = "",
) -> MultiObjectiveResult:
    """Create a MultiObjectiveResult from a BacktestResult.

    Maps BacktestResult fields to the multi-objective evaluation structure.
    Computes confidence_tier from trade count and regime distribution.

    Args:
        result: BacktestResult from a backtest run.
        regime_results: Optional per-regime metrics (string-keyed).
        wfe: Walk-forward efficiency (default 0.0).
        is_oos: Whether this is out-of-sample data.
        parameter_hash_value: Pre-computed parameter hash (empty string if none).

    Returns:
        MultiObjectiveResult with mapped fields and computed confidence tier.
    """
    regimes = regime_results or {}

    # Compute regime trade counts for confidence tier
    regime_trade_counts = {k: v.total_trades for k, v in regimes.items()}

    confidence_tier = compute_confidence_tier(result.total_trades, regime_trade_counts)

    return MultiObjectiveResult(
        strategy_id=result.strategy_id,
        parameter_hash=parameter_hash_value,
        evaluation_date=datetime.now(UTC),
        data_range=(result.start_date, result.end_date),
        sharpe_ratio=result.sharpe_ratio,
        max_drawdown_pct=result.max_drawdown_pct,
        profit_factor=result.profit_factor,
        win_rate=result.win_rate,
        total_trades=result.total_trades,
        expectancy_per_trade=result.expectancy,
        regime_results=regimes,
        confidence_tier=confidence_tier,
        wfe=wfe,
        is_oos=is_oos,
    )

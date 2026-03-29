"""Data models for the Learning Loop.

Frozen dataclasses for outcome records, analysis reports, weight/threshold
recommendations, and config proposals. LearningLoopConfig is a Pydantic
BaseModel with validated fields.

Sprint 28, Session 1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ConfidenceLevel(StrEnum):
    """Confidence level for analysis recommendations."""

    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class OutcomeRecord:
    """Unified record for a trade or counterfactual outcome.

    Attributes:
        symbol: Ticker symbol.
        strategy_id: Strategy that generated the signal.
        quality_score: Composite quality score (0-100).
        quality_grade: Quality grade string (e.g., "B+").
        dimension_scores: Per-dimension scores if available.
        regime_context: Primary regime + full vector snapshot.
        pnl: Realized (trade) or theoretical (counterfactual) P&L.
        r_multiple: Risk-normalized return, if available.
        source: Whether this came from a real trade or counterfactual.
        timestamp: When the outcome occurred.
        rejection_stage: Rejection stage (counterfactual only).
        rejection_reason: Rejection reason (counterfactual only).
    """

    symbol: str
    strategy_id: str
    quality_score: float
    quality_grade: str
    dimension_scores: dict[str, float]
    regime_context: dict[str, object]
    pnl: float
    r_multiple: float | None
    source: Literal["trade", "counterfactual"]
    timestamp: datetime
    rejection_stage: str | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True)
class DataQualityPreamble:
    """Summary of data quality for an analysis window.

    Attributes:
        trading_days_count: Number of unique trading days.
        total_trades: Number of real trade records.
        total_counterfactual: Number of counterfactual records.
        effective_sample_size: Total usable records.
        known_data_gaps: List of known data quality issues.
        earliest_date: Earliest record timestamp.
        latest_date: Latest record timestamp.
    """

    trading_days_count: int
    total_trades: int
    total_counterfactual: int
    effective_sample_size: int
    known_data_gaps: list[str]
    earliest_date: datetime | None
    latest_date: datetime | None


@dataclass(frozen=True)
class WeightRecommendation:
    """Recommendation for adjusting a quality dimension weight.

    Attributes:
        dimension: Quality dimension name (e.g., "pattern_strength").
        current_weight: Current weight value.
        recommended_weight: Proposed new weight.
        delta: Difference (recommended - current).
        correlation_trade_source: Correlation from trade data.
        correlation_counterfactual_source: Correlation from counterfactual data.
        p_value: Statistical significance p-value.
        sample_size: Number of records used.
        confidence: Confidence level of the recommendation.
        regime_breakdown: Per-regime correlation values.
        source_divergence_flag: True if trade vs counterfactual diverge.
    """

    dimension: str
    current_weight: float
    recommended_weight: float
    delta: float
    correlation_trade_source: float | None
    correlation_counterfactual_source: float | None
    p_value: float | None
    sample_size: int
    confidence: ConfidenceLevel
    regime_breakdown: dict[str, float]
    source_divergence_flag: bool


@dataclass(frozen=True)
class ThresholdRecommendation:
    """Recommendation for adjusting a quality grade threshold.

    Attributes:
        grade: Quality grade (e.g., "B+").
        current_threshold: Current score threshold for this grade.
        recommended_direction: Whether to raise or lower the threshold.
        missed_opportunity_rate: Rate of profitable rejected signals.
        correct_rejection_rate: Rate of unprofitable rejected signals.
        sample_size: Number of records analyzed.
        confidence: Confidence level of the recommendation.
    """

    grade: str
    current_threshold: float
    recommended_direction: Literal["raise", "lower"]
    missed_opportunity_rate: float
    correct_rejection_rate: float
    sample_size: int
    confidence: ConfidenceLevel


@dataclass(frozen=True)
class CorrelationResult:
    """Cross-strategy daily P&L correlation analysis.

    Attributes:
        strategy_pairs: List of strategy pair tuples analyzed.
        correlation_matrix: Correlation values keyed by strategy pair.
        flagged_pairs: Pairs exceeding the correlation threshold.
        excluded_strategies: Strategies with zero trades.
        window_days: Number of trading days in the window.
    """

    strategy_pairs: list[tuple[str, str]]
    correlation_matrix: dict[tuple[str, str], float]
    flagged_pairs: list[tuple[str, str]]
    excluded_strategies: list[str]
    window_days: int


@dataclass(frozen=True)
class LearningReport:
    """Complete learning loop analysis report.

    Attributes:
        report_id: Unique report ID (ULID).
        generated_at: When this report was generated.
        analysis_window_start: Start of the analysis window.
        analysis_window_end: End of the analysis window.
        data_quality: Data quality preamble.
        weight_recommendations: Per-dimension weight recommendations.
        threshold_recommendations: Per-grade threshold recommendations.
        correlation_result: Cross-strategy correlation, if computed.
        version: Schema version for forward compatibility.
    """

    report_id: str
    generated_at: datetime
    analysis_window_start: datetime
    analysis_window_end: datetime
    data_quality: DataQualityPreamble
    weight_recommendations: list[WeightRecommendation]
    threshold_recommendations: list[ThresholdRecommendation]
    correlation_result: CorrelationResult | None
    version: int = 1

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict.

        Returns:
            Dict representation with datetimes as ISO strings
            and tuple keys converted to string keys.
        """
        d = asdict(self)
        _convert_datetimes(d)
        # Fix correlation_matrix tuple keys → string keys
        if d.get("correlation_result") is not None:
            cr = d["correlation_result"]
            if isinstance(cr, dict) and "correlation_matrix" in cr:
                matrix = cr["correlation_matrix"]
                cr["correlation_matrix"] = {
                    f"{k[0]}|{k[1]}": v for k, v in matrix.items()
                }
            if isinstance(cr, dict) and "strategy_pairs" in cr:
                cr["strategy_pairs"] = [
                    list(pair) for pair in cr["strategy_pairs"]
                ]
            if isinstance(cr, dict) and "flagged_pairs" in cr:
                cr["flagged_pairs"] = [
                    list(pair) for pair in cr["flagged_pairs"]
                ]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> LearningReport:
        """Deserialize from a dict (inverse of to_dict).

        Args:
            d: Dict as produced by to_dict().

        Returns:
            Reconstructed LearningReport.
        """
        dq_raw = d["data_quality"]
        assert isinstance(dq_raw, dict)
        data_quality = DataQualityPreamble(
            trading_days_count=int(dq_raw["trading_days_count"]),
            total_trades=int(dq_raw["total_trades"]),
            total_counterfactual=int(dq_raw["total_counterfactual"]),
            effective_sample_size=int(dq_raw["effective_sample_size"]),
            known_data_gaps=list(dq_raw["known_data_gaps"]),
            earliest_date=_parse_dt(dq_raw.get("earliest_date")),
            latest_date=_parse_dt(dq_raw.get("latest_date")),
        )

        weight_recs_raw = d.get("weight_recommendations", [])
        assert isinstance(weight_recs_raw, list)
        weight_recs = [_parse_weight_rec(wr) for wr in weight_recs_raw]

        threshold_recs_raw = d.get("threshold_recommendations", [])
        assert isinstance(threshold_recs_raw, list)
        threshold_recs = [_parse_threshold_rec(tr) for tr in threshold_recs_raw]

        cr_raw = d.get("correlation_result")
        correlation_result: CorrelationResult | None = None
        if cr_raw is not None:
            assert isinstance(cr_raw, dict)
            # Restore tuple keys from "a|b" string keys
            raw_matrix = cr_raw.get("correlation_matrix", {})
            assert isinstance(raw_matrix, dict)
            matrix: dict[tuple[str, str], float] = {}
            for key_str, val in raw_matrix.items():
                assert isinstance(key_str, str)
                parts = key_str.split("|")
                matrix[(parts[0], parts[1])] = float(val)

            raw_pairs = cr_raw.get("strategy_pairs", [])
            assert isinstance(raw_pairs, list)
            strategy_pairs = [(p[0], p[1]) for p in raw_pairs]

            raw_flagged = cr_raw.get("flagged_pairs", [])
            assert isinstance(raw_flagged, list)
            flagged_pairs = [(p[0], p[1]) for p in raw_flagged]

            correlation_result = CorrelationResult(
                strategy_pairs=strategy_pairs,
                correlation_matrix=matrix,
                flagged_pairs=flagged_pairs,
                excluded_strategies=list(cr_raw.get("excluded_strategies", [])),
                window_days=int(cr_raw["window_days"]),
            )

        return cls(
            report_id=str(d["report_id"]),
            generated_at=_parse_dt_required(d["generated_at"]),
            analysis_window_start=_parse_dt_required(d["analysis_window_start"]),
            analysis_window_end=_parse_dt_required(d["analysis_window_end"]),
            data_quality=data_quality,
            weight_recommendations=weight_recs,
            threshold_recommendations=threshold_recs,
            correlation_result=correlation_result,
            version=int(d.get("version", 1)),
        )


@dataclass(frozen=True)
class ConfigProposal:
    """A proposed configuration change from the learning loop.

    Attributes:
        proposal_id: Unique proposal ID (ULID).
        report_id: ID of the LearningReport that generated this.
        field_path: Config field path (e.g., "weights.pattern_strength").
        current_value: Current config value.
        proposed_value: Proposed new value.
        rationale: Human-readable explanation.
        status: Proposal lifecycle status.
        created_at: When this proposal was created.
        updated_at: When this proposal was last updated.
        human_notes: Optional operator notes.
    """

    proposal_id: str
    report_id: str
    field_path: str
    current_value: float
    proposed_value: float
    rationale: str
    status: str
    created_at: datetime
    updated_at: datetime
    human_notes: str | None = None


# Valid ConfigProposal status values per Amendment 6
PROPOSAL_STATUSES = frozenset({
    "PENDING",
    "APPROVED",
    "DISMISSED",
    "SUPERSEDED",
    "REJECTED_GUARD",
    "REJECTED_VALIDATION",
    "APPLIED",
    "REVERTED",
})


class LearningLoopConfig(BaseModel):
    """Configuration for the Learning Loop.

    Validated Pydantic model with all 13 config fields.
    """

    enabled: bool = True
    analysis_window_days: int = 30
    min_sample_count: int = Field(default=30, ge=5)
    min_sample_per_regime: int = 5
    max_weight_change_per_cycle: float = Field(default=0.10, ge=0.01, le=0.50)
    max_cumulative_drift: float = Field(default=0.20, ge=0.05, le=0.50)
    cumulative_drift_window_days: int = 30
    auto_trigger_enabled: bool = True
    correlation_window_days: int = 20
    report_retention_days: int = 90
    correlation_threshold: float = 0.7
    weight_divergence_threshold: float = 0.10
    correlation_p_value_threshold: float = Field(
        default=0.10, ge=0.01, le=0.20
    )

    @field_validator("min_sample_count")
    @classmethod
    def validate_min_sample_count(cls, v: int) -> int:
        """Ensure min_sample_count is at least 5."""
        if v < 5:
            msg = "min_sample_count must be >= 5"
            raise ValueError(msg)
        return v

    @field_validator("max_weight_change_per_cycle")
    @classmethod
    def validate_max_weight_change(cls, v: float) -> float:
        """Ensure max_weight_change_per_cycle is between 0.01 and 0.50."""
        if not 0.01 <= v <= 0.50:
            msg = "max_weight_change_per_cycle must be between 0.01 and 0.50"
            raise ValueError(msg)
        return v

    @field_validator("max_cumulative_drift")
    @classmethod
    def validate_max_cumulative_drift(cls, v: float) -> float:
        """Ensure max_cumulative_drift is between 0.05 and 0.50."""
        if not 0.05 <= v <= 0.50:
            msg = "max_cumulative_drift must be between 0.05 and 0.50"
            raise ValueError(msg)
        return v

    @field_validator("correlation_p_value_threshold")
    @classmethod
    def validate_p_value_threshold(cls, v: float) -> float:
        """Ensure correlation_p_value_threshold is between 0.01 and 0.20."""
        if not 0.01 <= v <= 0.20:
            msg = "correlation_p_value_threshold must be between 0.01 and 0.20"
            raise ValueError(msg)
        return v


# --- Internal helpers ---


def _convert_datetimes(obj: object) -> None:
    """Recursively convert datetime objects to ISO strings in-place."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            val = obj[key]
            if isinstance(val, datetime):
                obj[key] = val.isoformat()
            elif isinstance(val, (dict, list)):
                _convert_datetimes(val)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, datetime):
                obj[i] = item.isoformat()
            elif isinstance(item, (dict, list)):
                _convert_datetimes(item)


def _parse_dt(val: object) -> datetime | None:
    """Parse an ISO datetime string or return None."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(str(val))


def _parse_dt_required(val: object) -> datetime:
    """Parse an ISO datetime string (required)."""
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(str(val))


def _parse_weight_rec(raw: dict[str, object]) -> WeightRecommendation:
    """Parse a WeightRecommendation from a dict."""
    regime_breakdown = raw.get("regime_breakdown", {})
    assert isinstance(regime_breakdown, dict)
    return WeightRecommendation(
        dimension=str(raw["dimension"]),
        current_weight=float(raw["current_weight"]),
        recommended_weight=float(raw["recommended_weight"]),
        delta=float(raw["delta"]),
        correlation_trade_source=(
            float(raw["correlation_trade_source"])
            if raw.get("correlation_trade_source") is not None
            else None
        ),
        correlation_counterfactual_source=(
            float(raw["correlation_counterfactual_source"])
            if raw.get("correlation_counterfactual_source") is not None
            else None
        ),
        p_value=(
            float(raw["p_value"])
            if raw.get("p_value") is not None
            else None
        ),
        sample_size=int(raw["sample_size"]),
        confidence=ConfidenceLevel(str(raw["confidence"])),
        regime_breakdown={str(k): float(v) for k, v in regime_breakdown.items()},
        source_divergence_flag=bool(raw["source_divergence_flag"]),
    )


def _parse_threshold_rec(raw: dict[str, object]) -> ThresholdRecommendation:
    """Parse a ThresholdRecommendation from a dict."""
    direction = str(raw["recommended_direction"])
    assert direction in ("raise", "lower")
    return ThresholdRecommendation(
        grade=str(raw["grade"]),
        current_threshold=float(raw["current_threshold"]),
        recommended_direction=direction,  # type: ignore[arg-type]
        missed_opportunity_rate=float(raw["missed_opportunity_rate"]),
        correct_rejection_rate=float(raw["correct_rejection_rate"]),
        sample_size=int(raw["sample_size"]),
        confidence=ConfidenceLevel(str(raw["confidence"])),
    )

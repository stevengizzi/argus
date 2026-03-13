"""Pydantic configuration models for the intelligence layer.

Provides typed, validated config models for the catalyst: and
quality_engine: sections in system.yaml and system_live.yaml.

Sprint 23.5 — DEC-164, Sprint 24 S5a — Quality Engine config + Position Sizer.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class SECEdgarConfig(BaseModel):
    """Configuration for the SEC EDGAR data source.

    Attributes:
        enabled: Whether to fetch from SEC EDGAR.
        filing_types: List of SEC filing types to ingest (e.g., "8-K", "4").
        user_agent_email: Email for SEC fair-access User-Agent header. Required when enabled.
        rate_limit_per_second: Maximum requests per second to SEC EDGAR.
    """

    enabled: bool = True
    filing_types: list[str] = ["8-K", "4"]
    user_agent_email: str = ""
    rate_limit_per_second: float = 10.0


class FMPNewsConfig(BaseModel):
    """Configuration for the FMP news data source.

    Attributes:
        enabled: Whether to fetch from FMP news endpoints.
        api_key_env_var: Environment variable name containing the FMP API key.
        endpoints: List of FMP news endpoint identifiers to query.
    """

    enabled: bool = True
    api_key_env_var: str = "FMP_API_KEY"
    endpoints: list[str] = ["stock_news", "press_releases"]


class FinnhubConfig(BaseModel):
    """Configuration for the Finnhub data source.

    Attributes:
        enabled: Whether to fetch from Finnhub.
        api_key_env_var: Environment variable name containing the Finnhub API key.
        rate_limit_per_minute: Maximum requests per minute to Finnhub.
    """

    enabled: bool = True
    api_key_env_var: str = "FINNHUB_API_KEY"
    rate_limit_per_minute: int = 60


class SourcesConfig(BaseModel):
    """Aggregated configuration for all catalyst data sources.

    Attributes:
        sec_edgar: SEC EDGAR source configuration.
        fmp_news: FMP news source configuration.
        finnhub: Finnhub source configuration.
    """

    sec_edgar: SECEdgarConfig = SECEdgarConfig()
    fmp_news: FMPNewsConfig = FMPNewsConfig()
    finnhub: FinnhubConfig = FinnhubConfig()


class BriefingConfig(BaseModel):
    """Configuration for the intelligence brief generator.

    Attributes:
        model: Claude model to use for briefing (None inherits from ai.model).
        max_symbols: Maximum number of symbols to include in a single brief.
    """

    model: str | None = None
    max_symbols: int = 30


class CatalystConfig(BaseModel):
    """Configuration for the NLP Catalyst Pipeline.

    Controls ingestion scheduling, cost limits, caching, and source
    activation. Set enabled: true to activate the pipeline.

    Attributes:
        enabled: Whether the catalyst pipeline is active.
        polling_interval_premarket_seconds: Ingestion polling interval before market open.
        polling_interval_session_seconds: Ingestion polling interval during market hours.
        max_batch_size: Maximum number of items to classify in a single Claude API call.
        daily_cost_ceiling_usd: Maximum USD to spend on Claude API per day.
        classification_cache_ttl_hours: Hours before a cached classification expires.
        sources: Per-source enable/configuration settings.
        briefing: Intelligence brief generation settings.
    """

    enabled: bool = False
    polling_interval_premarket_seconds: int = 900
    polling_interval_session_seconds: int = 1800
    max_batch_size: int = 20
    daily_cost_ceiling_usd: float = 5.0
    classification_cache_ttl_hours: int = 24
    dedup_window_minutes: int = 30
    sources: SourcesConfig = SourcesConfig()
    briefing: BriefingConfig = BriefingConfig()


VALID_GRADES: tuple[str, ...] = ("A+", "A", "A-", "B+", "B", "B-", "C+")


class QualityWeightsConfig(BaseModel):
    """Per-dimension weights for quality scoring. Must sum to 1.0.

    Attributes:
        pattern_strength: Weight for pattern strength dimension.
        catalyst_quality: Weight for catalyst quality dimension.
        volume_profile: Weight for volume profile dimension.
        historical_match: Weight for historical match dimension.
        regime_alignment: Weight for regime alignment dimension.
    """

    pattern_strength: float = 0.30
    catalyst_quality: float = 0.25
    volume_profile: float = 0.20
    historical_match: float = 0.15
    regime_alignment: float = 0.10

    @model_validator(mode="after")
    def validate_weight_sum(self) -> QualityWeightsConfig:
        """Validate that all five weights sum to 1.0 (±0.001 tolerance)."""
        total = (
            self.pattern_strength
            + self.catalyst_quality
            + self.volume_profile
            + self.historical_match
            + self.regime_alignment
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Quality weights must sum to 1.0, got {total:.4f}")
        return self

    def get(self, key: str, default: float = 0.2) -> float:
        """Dict-like access for backward compatibility with SetupQualityEngine."""
        return getattr(self, key, default)


class QualityThresholdsConfig(BaseModel):
    """Score thresholds for grade assignment (inclusive lower bounds).

    All values must be integers in [0, 100] and strictly descending.

    Attributes:
        a_plus: Minimum score for A+ grade.
        a: Minimum score for A grade.
        a_minus: Minimum score for A- grade.
        b_plus: Minimum score for B+ grade.
        b: Minimum score for B grade.
        b_minus: Minimum score for B- grade.
        c_plus: Minimum score for C+ grade.
    """

    a_plus: int = 90
    a: int = 80
    a_minus: int = 70
    b_plus: int = 60
    b: int = 50
    b_minus: int = 40
    c_plus: int = 30

    @model_validator(mode="after")
    def validate_descending(self) -> QualityThresholdsConfig:
        """Validate all thresholds are in [0, 100] and strictly descending."""
        values = [
            self.a_plus, self.a, self.a_minus,
            self.b_plus, self.b, self.b_minus, self.c_plus,
        ]
        for v in values:
            if not 0 <= v <= 100:
                raise ValueError(f"Threshold {v} not in [0, 100]")
        for i in range(len(values) - 1):
            if values[i] <= values[i + 1]:
                raise ValueError(
                    f"Thresholds must be strictly descending: "
                    f"{values[i]} <= {values[i + 1]}"
                )
        return self


class QualityRiskTiersConfig(BaseModel):
    """Risk percentage ranges per grade for dynamic position sizing.

    Each tier is a [min, max] pair where min <= max and both in [0, 1].

    Attributes:
        a_plus: Risk range for A+ grade setups.
        a: Risk range for A grade setups.
        a_minus: Risk range for A- grade setups.
        b_plus: Risk range for B+ grade setups.
        b: Risk range for B grade setups.
        b_minus: Risk range for B- grade setups.
        c_plus: Risk range for C+ grade setups.
    """

    a_plus: list[float] = [0.02, 0.03]
    a: list[float] = [0.015, 0.02]
    a_minus: list[float] = [0.01, 0.015]
    b_plus: list[float] = [0.0075, 0.01]
    b: list[float] = [0.005, 0.0075]
    b_minus: list[float] = [0.0025, 0.005]
    c_plus: list[float] = [0.0025, 0.0025]

    @model_validator(mode="after")
    def validate_tiers(self) -> QualityRiskTiersConfig:
        """Validate each tier pair has exactly 2 values, min <= max, both in [0, 1]."""
        for grade in VALID_GRADES:
            field_name = grade.lower().replace("+", "_plus").replace("-", "_minus")
            pair = getattr(self, field_name)
            if len(pair) != 2:
                raise ValueError(f"Risk tier {grade} must have exactly 2 values")
            lo, hi = pair
            if not (0.0 <= lo <= 1.0) or not (0.0 <= hi <= 1.0):
                raise ValueError(f"Risk tier {grade} values must be in [0, 1]")
            if lo > hi:
                raise ValueError(
                    f"Risk tier {grade} min ({lo}) exceeds max ({hi})"
                )
        return self


class QualityEngineConfig(BaseModel):
    """Configuration for the SetupQualityEngine and DynamicPositionSizer.

    Attributes:
        enabled: Whether quality scoring is active.
        weights: Per-dimension weights (must sum to 1.0).
        thresholds: Score-to-grade mapping thresholds.
        risk_tiers: Risk percentage ranges per grade for position sizing.
        min_grade_to_trade: Minimum quality grade required to place a trade.
    """

    enabled: bool = True
    weights: QualityWeightsConfig = QualityWeightsConfig()
    thresholds: QualityThresholdsConfig = QualityThresholdsConfig()
    risk_tiers: QualityRiskTiersConfig = QualityRiskTiersConfig()
    min_grade_to_trade: str = "C+"

    @model_validator(mode="after")
    def validate_min_grade(self) -> QualityEngineConfig:
        """Validate min_grade_to_trade is a recognized grade string."""
        if self.min_grade_to_trade not in VALID_GRADES:
            raise ValueError(
                f"min_grade_to_trade must be one of {VALID_GRADES}, "
                f"got '{self.min_grade_to_trade}'"
            )
        return self

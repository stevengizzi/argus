"""Pydantic configuration models for the NLP Catalyst Pipeline.

Provides typed, validated config models for the catalyst: section
in system.yaml and system_live.yaml.

Sprint 23.5 — DEC-164
"""

from __future__ import annotations

from pydantic import BaseModel


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

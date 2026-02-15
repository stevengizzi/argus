"""Configuration models for backtesting data acquisition."""

from pathlib import Path

from pydantic import BaseModel, Field


class DataFetcherConfig(BaseModel):
    """Configuration for the historical data fetcher.

    Controls which symbols to download, the date range, storage location,
    and rate limiting parameters.
    """

    # Storage
    data_dir: Path = Path("data/historical/1m")
    manifest_path: Path = Path("data/historical/manifest.json")

    # Rate limiting
    max_requests_per_minute: int = Field(default=150, ge=1, le=200)
    retry_max_attempts: int = Field(default=3, ge=1)
    retry_base_delay_seconds: float = Field(default=2.0, gt=0)

    # Data parameters
    adjustment: str = Field(default="split", pattern=r"^(raw|split|all)$")
    feed: str = Field(default="iex", pattern=r"^(iex|sip)$")

"""Configuration models for backtesting data acquisition and replay."""

from datetime import date
from pathlib import Path
from typing import Any

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


class BacktestConfig(BaseModel):
    """Configuration for the Replay Harness.

    Controls data sources, date range, slippage model, scanner simulation
    parameters, and strategy configuration overrides.

    Attributes:
        data_dir: Directory containing historical Parquet files.
        output_dir: Directory for backtest output databases.
        start_date: First trading day to include in the backtest.
        end_date: Last trading day to include in the backtest.
        strategy_id: Strategy to run (default: orb_breakout).
        slippage_per_share: Fixed slippage applied to each fill (DEC-054).
        initial_cash: Starting account balance.
        scanner_min_gap_pct: Minimum gap percentage for scanner simulation.
        scanner_min_price: Minimum stock price filter.
        scanner_max_price: Maximum stock price filter.
        scanner_fallback_all_symbols: Use all symbols if gap filter finds none.
        eod_flatten_time: Time to flatten all positions (HH:MM in ET).
        eod_flatten_timezone: Timezone for EOD flatten (default: America/New_York).
        config_overrides: Strategy config overrides as dot-separated keys.
    """

    # Data
    data_dir: Path = Field(default=Path("data/historical/1m"))
    output_dir: Path = Field(default=Path("data/backtest_runs"))

    # Date range
    start_date: date
    end_date: date

    # Strategy
    strategy_id: str = Field(default="orb_breakout")

    # Slippage (DEC-054: Fixed $0.01/share)
    slippage_per_share: float = Field(default=0.01, ge=0.0)

    # SimulatedBroker
    initial_cash: float = Field(default=100_000.0, gt=0)

    # Scanner simulation (DEC-052)
    scanner_min_gap_pct: float = Field(default=0.02, ge=0.0)
    scanner_min_price: float = Field(default=10.0, ge=0.0)
    scanner_max_price: float = Field(default=500.0, gt=0.0)
    scanner_fallback_all_symbols: bool = Field(default=True)

    # EOD flatten
    eod_flatten_time: str = Field(default="15:50")
    eod_flatten_timezone: str = Field(default="America/New_York")

    # Config overrides (applied on top of YAML config)
    # Keys are dot-separated paths: {"orb_breakout.opening_range_minutes": 15}
    config_overrides: dict[str, Any] = Field(default_factory=dict)

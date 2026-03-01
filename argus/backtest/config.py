"""Configuration models for backtesting data acquisition and replay."""

from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StrategyType(StrEnum):
    """Strategy type for backtest selection."""

    ORB_BREAKOUT = "orb"
    ORB_SCALP = "orb_scalp"
    VWAP_RECLAIM = "vwap_reclaim"
    AFTERNOON_MOMENTUM = "afternoon_momentum"


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

    # Data source selection
    source: str = Field(default="alpaca", pattern=r"^(alpaca|databento)$")

    # Databento-specific settings (DEC-237: EQUS.MINI for Standard plan)
    databento_dataset: str = "EQUS.MINI"
    databento_cache_dir: Path = Path("data/databento_cache")


class BacktestConfig(BaseModel):
    """Configuration for the Replay Harness.

    Controls data sources, date range, slippage model, scanner simulation
    parameters, and strategy configuration overrides.

    Attributes:
        data_dir: Directory containing historical Parquet files.
        output_dir: Directory for backtest output databases.
        symbols: Optional list of symbols to include. If None, use all symbols in data_dir.
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
    symbols: list[str] | None = Field(default=None)  # None = all symbols in data_dir

    # Date range
    start_date: date
    end_date: date

    # Strategy
    strategy_id: str = Field(default="strat_orb_breakout")
    strategy_type: StrategyType = Field(default=StrategyType.ORB_BREAKOUT)

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

    # VWAP Reclaim params (used when strategy_type=VWAP_RECLAIM)
    vwap_min_pullback_pct: float | None = None
    vwap_min_pullback_bars: int | None = None
    vwap_volume_multiplier: float | None = None
    vwap_target_1_r: float | None = None
    vwap_target_2_r: float | None = None
    vwap_time_stop_minutes: int | None = None
    vwap_stop_buffer_pct: float | None = None
    vwap_max_pullback_pct: float | None = None
    vwap_max_chase_pct: float | None = None

    # Afternoon Momentum params (used when strategy_type=AFTERNOON_MOMENTUM)
    consolidation_atr_ratio: float = 0.75
    min_consolidation_bars: int = 30
    afternoon_volume_multiplier: float = 1.2
    afternoon_max_hold_minutes: int = 60
    afternoon_target_1_r: float = 1.0
    afternoon_target_2_r: float = 2.0

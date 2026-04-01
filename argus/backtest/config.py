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
    RED_TO_GREEN = "red_to_green"
    BULL_FLAG = "bull_flag"
    FLAT_TOP_BREAKOUT = "flat_top_breakout"
    DIP_AND_RIP = "dip_and_rip"
    HOD_BREAK = "hod_break"
    ABCD = "abcd"
    GAP_AND_GO = "gap_and_go"
    PREMARKET_HIGH_BREAK = "premarket_high_break"


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

    # Red-to-Green params (used when strategy_type=RED_TO_GREEN)
    r2g_min_gap_down_pct: float = 0.02
    r2g_level_proximity_pct: float = 0.003
    r2g_volume_confirmation_multiplier: float = 1.2
    r2g_time_stop_minutes: int = 20
    r2g_target_1_r: float = 1.0
    r2g_target_2_r: float = 2.0
    r2g_stop_buffer_pct: float = 0.001


class BacktestEngineConfig(BaseModel):
    """Configuration for BacktestEngine runs.

    Controls strategy selection, date range, data source, execution parameters,
    scanner simulation, and output settings for the new bar-level backtest engine.
    """

    # Strategy
    strategy_type: StrategyType = StrategyType.ORB_BREAKOUT
    strategy_id: str = "strat_orb_breakout"
    symbols: list[str] | None = None  # None = all available

    # Date range
    start_date: date
    end_date: date

    # Data
    data_source: str = Field(default="databento", pattern=r"^(databento|parquet)$")
    cache_dir: Path = Path("data/databento_cache")
    verify_zero_cost: bool = True

    # Execution
    engine_mode: str = Field(default="sync", pattern=r"^(sync)$")  # Only sync for now
    initial_cash: float = Field(default=100_000.0, gt=0)
    slippage_per_share: float = Field(default=0.01, ge=0.0)

    # Scanner
    scanner_min_gap_pct: float = Field(default=0.02, ge=0.0)
    scanner_min_price: float = Field(default=10.0, ge=0.0)
    scanner_max_price: float = Field(default=500.0, gt=0.0)
    scanner_fallback_all_symbols: bool = True

    # EOD
    eod_flatten_time: str = "15:50"

    # Output
    output_dir: Path = Path("data/backtest_runs")
    log_level: str = Field(default="WARNING", pattern=r"^(DEBUG|INFO|WARNING|ERROR)$")

    # Config overrides (strategy parameter overrides)
    config_overrides: dict[str, Any] = Field(default_factory=dict)

    # Slippage model (Sprint 27.5 S6)
    slippage_model_path: str | None = Field(
        default=None,
        description=(
            "Path to calibrated StrategySlippageModel JSON. When set, loads "
            "calibrated slippage for execution_quality_adjustment computation."
        ),
    )

    # Risk overrides for single-strategy backtesting (DEC-359)
    # Applied on top of risk_limits.yaml to relax constraints that are
    # inappropriate for isolated strategy validation.
    risk_overrides: dict[str, Any] = Field(default_factory=lambda: {
        "account.min_position_risk_dollars": 1.0,
        "account.cash_reserve_pct": 0.05,
        "cross_strategy.max_single_stock_pct": 0.50,
    })

    # Regime classification version (Sprint 27.6 S7)
    # When True, uses RegimeClassifierV2 with all calculators as None
    # (backtest mode — trend+vol only). Produces identical regime tags to V1.
    use_regime_v2: bool = False

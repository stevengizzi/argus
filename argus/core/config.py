"""Argus configuration system.

Loads configuration from YAML files and validates via Pydantic models.
All tunable parameters live in YAML config files, never hardcoded.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AccountType(StrEnum):
    """Brokerage account type."""

    MARGIN = "margin"
    CASH = "cash"


class DuplicateStockPolicy(StrEnum):
    """Policy when multiple strategies want the same stock."""

    PRIORITY_BY_WIN_RATE = "priority_by_win_rate"
    FIRST_SIGNAL = "first_signal"
    BLOCK_ALL = "block_all"
    ALLOW_ALL = "allow_all"


class LogLevel(StrEnum):
    """Logging level."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Config Sub-Models
# ---------------------------------------------------------------------------


class HealthConfig(BaseModel):
    """Health monitoring configuration."""

    heartbeat_interval_seconds: int = Field(default=60, ge=10, le=300)
    heartbeat_url_env: str = ""  # Env var name for Healthchecks.io ping URL
    alert_webhook_url_env: str = ""  # Env var name for Discord/Slack webhook
    daily_check_enabled: bool = True
    weekly_reconciliation_enabled: bool = True

    @property
    def heartbeat_url(self) -> str:
        """Resolve heartbeat URL from environment variable."""
        import os

        if not self.heartbeat_url_env:
            return ""
        return os.environ.get(self.heartbeat_url_env, "")

    @property
    def alert_webhook_url(self) -> str:
        """Resolve alert webhook URL from environment variable."""
        import os

        if not self.alert_webhook_url_env:
            return ""
        return os.environ.get(self.alert_webhook_url_env, "")


class ApiConfig(BaseModel):
    """Configuration for the Command Center API server (Sprint 14)."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    password_hash: str = ""  # bcrypt hash — use setup_password CLI to generate
    jwt_secret_env: str = "ARGUS_JWT_SECRET"  # env var name for JWT signing key
    jwt_expiry_hours: int = Field(default=24, ge=1)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    ws_heartbeat_interval_seconds: int = Field(default=30, ge=5)
    ws_tick_throttle_ms: int = Field(default=1000, ge=100)
    static_dir: str = ""  # path to built React app; empty = don't serve static


class DataSource(StrEnum):
    """Data service provider selection."""

    ALPACA = "alpaca"
    DATABENTO = "databento"


class BrokerSource(StrEnum):
    """Broker provider selection (DEC-094).

    Mirrors DataSource pattern from DEC-090.
    Used by main.py Phase 3 to select the Broker implementation.
    """

    ALPACA = "alpaca"
    IBKR = "ibkr"
    SIMULATED = "simulated"


class SystemConfig(BaseModel):
    """Global system settings."""

    timezone: str = "America/New_York"
    market_open: str = "09:30"
    market_close: str = "16:00"
    log_level: LogLevel = LogLevel.INFO
    # Legacy field — use health.heartbeat_interval_seconds instead
    heartbeat_interval_seconds: int = Field(default=60, ge=1)
    data_dir: str = "data"
    health: HealthConfig = Field(default_factory=HealthConfig)
    # Data source selection (DEC-082: Databento is primary production)
    data_source: DataSource = DataSource.ALPACA
    # Broker source selection (DEC-094: mirrors DataSource pattern)
    broker_source: BrokerSource = BrokerSource.SIMULATED
    # IBKR configuration (Sprint 13) — uses default_factory for forward reference
    ibkr: IBKRConfig = Field(default_factory=lambda: IBKRConfig())
    # Command Center API configuration (Sprint 14)
    api: ApiConfig = Field(default_factory=lambda: ApiConfig())

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string is plausible (basic check)."""
        if "/" not in v and v != "UTC":
            raise ValueError(f"Timezone must be IANA format (e.g., 'America/New_York'), got '{v}'")
        return v


class AccountRiskConfig(BaseModel):
    """Account-level risk limits."""

    daily_loss_limit_pct: float = Field(default=0.03, gt=0, le=0.2)
    weekly_loss_limit_pct: float = Field(default=0.05, gt=0, le=0.3)
    cash_reserve_pct: float = Field(default=0.20, ge=0, le=0.5)
    max_concurrent_positions: int = Field(default=10, ge=1)
    emergency_shutdown_enabled: bool = True


class CrossStrategyRiskConfig(BaseModel):
    """Cross-strategy risk limits."""

    max_single_stock_pct: float = Field(default=0.05, gt=0, le=0.5)
    max_single_sector_pct: float = Field(default=0.15, gt=0, le=0.5)
    duplicate_stock_policy: DuplicateStockPolicy = DuplicateStockPolicy.ALLOW_ALL


class PDTConfig(BaseModel):
    """Pattern Day Trader tracking configuration."""

    enabled: bool = True
    account_type: AccountType = AccountType.MARGIN
    threshold_balance: float = 25000.0  # FINRA PDT threshold


class RiskConfig(BaseModel):
    """Complete risk management configuration."""

    account: AccountRiskConfig = AccountRiskConfig()
    cross_strategy: CrossStrategyRiskConfig = CrossStrategyRiskConfig()
    pdt: PDTConfig = PDTConfig()


class AlpacaConfig(BaseModel):
    """Configuration for Alpaca API connections."""

    enabled: bool = True
    api_key_env: str = "ALPACA_API_KEY"  # Env var name (not the key itself!)
    secret_key_env: str = "ALPACA_SECRET_KEY"  # Env var name (not the key itself!)
    paper: bool = True  # Paper trading mode
    data_feed: str = "iex"  # "iex" (free) or "sip" (paid)

    # WebSocket reconnection
    ws_reconnect_base_seconds: float = 1.0
    ws_reconnect_max_seconds: float = 30.0
    ws_reconnect_max_failures_before_alert: int = 3

    # Stale data
    stale_data_timeout_seconds: float = 30.0

    # Data streams
    subscribe_bars: bool = True  # 1m bar stream
    subscribe_trades: bool = True  # Individual trade stream


class DatabentoConfig(BaseModel):
    """Configuration for Databento market data connectivity.

    API key is read from environment variable at runtime, never stored in config.
    Follows the same pattern as AlpacaConfig (DEC-032).
    """

    enabled: bool = True

    # API key — name of the environment variable containing the key
    api_key_env_var: str = "DATABENTO_API_KEY"

    # Dataset selection — determines which exchange feeds are included
    # XNAS.ITCH = Nasdaq TotalView-ITCH (recommended for trading firms)
    dataset: str = "XNAS.ITCH"

    # Schema subscriptions for live streaming
    bar_schema: str = "ohlcv-1m"  # Completed 1-minute OHLCV bars → CandleEvents
    trade_schema: str = "trades"  # Individual trades → TickEvents + price cache
    depth_schema: str = "mbp-10"  # L2 10-level depth (when enabled)
    enable_depth: bool = False  # L2 depth subscription off by default

    # Symbol configuration
    # Either a list of specific symbols or "ALL_SYMBOLS" for full universe
    symbols: list[str] | str = "ALL_SYMBOLS"

    # Symbology type for input symbols
    stype_in: str = "raw_symbol"

    # Session management
    reconnect_max_retries: int = 10
    reconnect_base_delay_seconds: float = 1.0
    reconnect_max_delay_seconds: float = 60.0

    # Circuit breaker — halt new trades if no data received within this window
    stale_data_timeout_seconds: float = 30.0

    # Historical data cache directory (DEC-085)
    historical_cache_dir: str = "data/databento_cache"

    @field_validator("dataset")
    @classmethod
    def validate_dataset(cls, v: str) -> str:
        """Validate dataset is a known Databento US equities dataset."""
        known_datasets = {
            "XNAS.ITCH",  # Nasdaq TotalView-ITCH (primary recommendation)
            "XNAS.BASIC",  # Nasdaq Basic with NLS Plus
            "XNYS.PILLAR",  # NYSE Integrated
            "ARCX.PILLAR",  # NYSE Arca Integrated
            "XASE.PILLAR",  # NYSE American Integrated
            "DBEQ.BASIC",  # Databento Equities Basic (free tier)
            "XBOS.ITCH",  # Nasdaq BX TotalView-ITCH
            "XPSX.ITCH",  # Nasdaq PSX TotalView-ITCH
            "XCHI.PILLAR",  # NYSE Chicago Integrated
            "XCIS.TRADESBBO",  # NYSE National Trades and BBO
            "EQUS.SUMMARY",  # Consolidated summary (delayed)
        }
        if v not in known_datasets:
            raise ValueError(f"Unknown dataset '{v}'. Known datasets: {sorted(known_datasets)}")
        return v

    @field_validator("bar_schema")
    @classmethod
    def validate_bar_schema(cls, v: str) -> str:
        """Validate bar schema is a known OHLCV schema."""
        valid = {"ohlcv-1s", "ohlcv-1m", "ohlcv-1h", "ohlcv-1d"}
        if v not in valid:
            raise ValueError(f"Invalid bar_schema '{v}'. Valid: {sorted(valid)}")
        return v

    @field_validator("stype_in")
    @classmethod
    def validate_stype_in(cls, v: str) -> str:
        """Validate symbology type is valid."""
        valid = {"raw_symbol", "instrument_id", "smart"}
        if v not in valid:
            raise ValueError(f"Invalid stype_in '{v}'. Valid: {sorted(valid)}")
        return v


class IBKRConfig(BaseModel):
    """Interactive Brokers connection configuration (DEC-094).

    Configures connection to IB Gateway/TWS via ib_async library.
    All trading goes through IBKR once the adapter is validated.
    """

    # Connection settings
    host: str = "127.0.0.1"
    port: int = Field(default=4002, ge=1, le=65535)  # 4001=live, 4002=paper
    client_id: int = Field(default=1, ge=0)
    account: str = ""  # IBKR account ID (e.g., "U24619949")
    timeout_seconds: float = Field(default=30.0, gt=0)
    readonly: bool = False  # If True, no orders can be placed

    # Reconnection settings (same pattern as DatabentoConfig)
    reconnect_max_retries: int = Field(default=10, ge=0)
    reconnect_base_delay_seconds: float = Field(default=1.0, gt=0)
    reconnect_max_delay_seconds: float = Field(default=60.0, gt=0)

    # Operational safety
    max_order_rate_per_second: float = Field(default=45.0, gt=0)  # IBKR limit is 50/sec


class BrokerConfig(BaseModel):
    """Broker routing and connection configuration."""

    primary: str = "alpaca"
    alpaca: AlpacaConfig = AlpacaConfig()
    databento: DatabentoConfig = DatabentoConfig()


class OrchestratorConfig(BaseModel):
    """Orchestrator behavior configuration.

    Controls capital allocation across strategies, regime detection,
    performance-based throttling, and correlation limits.
    """

    # Allocation settings
    allocation_method: str = "equal_weight"  # "equal_weight" or "performance_weighted"
    max_allocation_pct: float = Field(default=0.40, gt=0, le=1.0)
    min_allocation_pct: float = Field(default=0.10, gt=0, le=1.0)
    cash_reserve_pct: float = Field(default=0.20, ge=0, le=0.5)

    # Performance evaluation
    performance_lookback_days: int = Field(default=20, ge=5)
    consecutive_loss_throttle: int = Field(default=5, ge=2)
    suspension_sharpe_threshold: float = 0.0
    suspension_drawdown_pct: float = Field(default=0.15, gt=0, le=0.5)
    recovery_days_required: int = Field(default=10, ge=1)

    # Regime detection
    regime_check_interval_minutes: int | None = Field(default=30, ge=1)
    spy_symbol: str = "SPY"
    vol_low_threshold: float = Field(default=0.08, ge=0)
    vol_normal_threshold: float = Field(default=0.16, ge=0)
    vol_high_threshold: float = Field(default=0.25, ge=0)
    vol_crisis_threshold: float = Field(default=0.35, ge=0)

    # Scheduling
    pre_market_time: str = "09:25"  # HH:MM in market timezone
    eod_review_time: str = "16:05"  # HH:MM in market timezone
    poll_interval_seconds: int = Field(default=30, ge=1)

    # Correlation limits
    correlation_enabled: bool = True
    min_correlation_days: int = Field(default=20, ge=5)
    max_combined_correlated_allocation: float = Field(default=0.60, gt=0, le=1.0)


class NotificationChannelConfig(BaseModel):
    """Configuration for a single notification channel."""

    enabled: bool = False
    # Specific fields vary by channel; stored as extra dict
    settings: dict[str, Any] = Field(default_factory=dict)


class NotificationsConfig(BaseModel):
    """Notification system configuration."""

    telegram: NotificationChannelConfig = NotificationChannelConfig()
    discord: NotificationChannelConfig = NotificationChannelConfig()
    email: NotificationChannelConfig = NotificationChannelConfig()
    push: NotificationChannelConfig = NotificationChannelConfig()


# ---------------------------------------------------------------------------
# Top-Level Config
# ---------------------------------------------------------------------------


class ArgusConfig(BaseModel):
    """Root configuration for the entire Argus system.

    Composed of domain-specific sub-configs. Loaded from YAML files
    via load_config().
    """

    system: SystemConfig = SystemConfig()
    risk: RiskConfig = RiskConfig()
    broker: BrokerConfig = BrokerConfig()
    orchestrator: OrchestratorConfig = OrchestratorConfig()
    notifications: NotificationsConfig = NotificationsConfig()


# ---------------------------------------------------------------------------
# Strategy Config (Base — individual strategies extend this)
# ---------------------------------------------------------------------------


class StrategyRiskLimits(BaseModel):
    """Risk limits specific to a single strategy."""

    max_loss_per_trade_pct: float = Field(default=0.01, gt=0, le=0.05)
    max_daily_loss_pct: float = Field(default=0.03, gt=0, le=0.1)
    max_consecutive_losses_pause: int = Field(default=5, ge=2)
    max_trades_per_day: int = Field(default=10, ge=1)
    max_concurrent_positions: int = Field(default=3, ge=1)


class OperatingWindow(BaseModel):
    """Time window when a strategy is allowed to enter trades."""

    earliest_entry: str = "09:45"  # HH:MM in market timezone
    latest_entry: str = "11:30"
    force_close: str = "15:50"
    active_days: list[str] = Field(
        default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )


class PerformanceBenchmarks(BaseModel):
    """Minimum performance thresholds to remain in active deployment."""

    min_win_rate: float = Field(default=0.40, ge=0, le=1.0)
    min_avg_r_multiple: float = Field(default=0.5)
    min_profit_factor: float = Field(default=1.2, ge=0)
    min_sharpe_ratio: float = Field(default=0.0)
    max_drawdown_pct: float = Field(default=0.15, gt=0, le=1.0)


class StrategyConfig(BaseModel):
    """Base configuration for any strategy. Individual strategies
    extend this with strategy-specific parameters."""

    strategy_id: str
    name: str
    version: str = "1.0.0"
    enabled: bool = True
    asset_class: str = "us_stocks"
    risk_limits: StrategyRiskLimits = StrategyRiskLimits()
    operating_window: OperatingWindow = OperatingWindow()
    benchmarks: PerformanceBenchmarks = PerformanceBenchmarks()


# ---------------------------------------------------------------------------
# Data Service Config (Sprint 3)
# ---------------------------------------------------------------------------


class DataServiceConfig(BaseModel):
    """Configuration for the Data Service."""

    active_timeframes: list[str] = Field(default_factory=lambda: ["1m"])
    supported_timeframes: list[str] = Field(default_factory=lambda: ["1s", "5s", "1m", "5m", "15m"])
    indicators: list[str] = Field(
        default_factory=lambda: ["vwap", "atr_14", "rvol", "sma_9", "sma_20", "sma_50"]
    )
    stale_data_timeout_seconds: int = Field(default=30, ge=1)


# ---------------------------------------------------------------------------
# Scanner Config (Sprint 3)
# ---------------------------------------------------------------------------


class ScannerConfig(BaseModel):
    """Configuration for the Scanner."""

    scanner_type: str = "static"  # "static" or "alpaca"
    static_symbols: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Order Manager Config (Sprint 4b)
# ---------------------------------------------------------------------------


class OrderManagerConfig(BaseModel):
    """Configuration for the Order Manager.

    Controls position lifecycle management including T1/T2 targets,
    stop-to-breakeven, time stops, and EOD flatten.
    """

    eod_flatten_time: str = "15:50"  # HH:MM in ET
    eod_flatten_timezone: str = "America/New_York"
    fallback_poll_interval_seconds: int = Field(default=5, ge=1)
    enable_stop_to_breakeven: bool = True
    breakeven_buffer_pct: float = Field(default=0.001, ge=0, le=0.1)  # 0.1%
    enable_trailing_stop: bool = False  # V1: disabled by default
    trailing_stop_atr_multiplier: float = Field(default=2.0, gt=0)
    max_position_duration_minutes: int = Field(default=120, ge=1)  # Hard time stop
    entry_timeout_seconds: int = Field(default=30, ge=1)
    t1_position_pct: float = Field(default=0.5, gt=0, le=1.0)  # 50% at T1
    stop_retry_max: int = Field(default=1, ge=0)


# ---------------------------------------------------------------------------
# Alpaca Scanner Config (Sprint 4b)
# ---------------------------------------------------------------------------


class AlpacaScannerConfig(BaseModel):
    """Configuration for the Alpaca live scanner.

    Scans a configured universe of symbols using Alpaca's snapshot API
    to find stocks matching gap, volume, and price criteria.
    """

    universe_source: str = "config"  # "config" = use universe_symbols list
    universe_symbols: list[str] = Field(default_factory=list)
    min_price: float = Field(default=5.0, gt=0)
    max_price: float = Field(default=500.0, gt=0)
    min_volume_yesterday: int = Field(default=1_000_000, ge=0)
    max_symbols_returned: int = Field(default=10, ge=1)


# ---------------------------------------------------------------------------
# ORB Breakout Strategy Config (Sprint 3)
# ---------------------------------------------------------------------------


class OrbBreakoutConfig(StrategyConfig):
    """ORB-specific configuration extending the base StrategyConfig.

    Validates ORB-specific parameters on top of the common strategy config.
    """

    orb_window_minutes: int = Field(default=15, ge=1, le=60)
    stop_placement: str = "midpoint"  # "midpoint" or "bottom"
    volume_threshold_rvol: float = Field(default=2.0, gt=0)
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)
    min_range_atr_ratio: float = Field(default=0.5, gt=0)
    max_range_atr_ratio: float = Field(default=2.0, gt=0)
    chase_protection_pct: float = Field(default=0.005, ge=0, le=0.05)
    breakout_volume_multiplier: float = Field(default=1.5, gt=0)


class OrbScalpConfig(StrategyConfig):
    """ORB Scalp strategy configuration (DEC-123).

    Scalp variant of ORB with single target, shorter hold times, and
    tighter risk parameters optimized for quick momentum captures.
    """

    orb_window_minutes: int = Field(default=5, ge=1, le=60)
    scalp_target_r: float = Field(default=0.3, gt=0, le=2.0)
    max_hold_seconds: int = Field(default=120, ge=10, le=600)
    stop_placement: str = "midpoint"  # "midpoint" or "bottom"
    min_range_atr_ratio: float = Field(default=0.5, gt=0)
    max_range_atr_ratio: float = Field(default=999.0, gt=0)
    chase_protection_pct: float = Field(default=0.005, ge=0, le=0.05)
    breakout_volume_multiplier: float = Field(default=1.5, gt=0)
    volume_threshold_rvol: float = Field(default=2.0, gt=0)


class VwapReclaimConfig(StrategyConfig):
    """VWAP Reclaim strategy configuration.

    Mean-reversion strategy that buys stocks reclaiming VWAP after
    a pullback. Operates 10:00 AM – 12:00 PM ET.

    State machine: WATCHING → ABOVE_VWAP → BELOW_VWAP → entry (or EXHAUSTED)
    """

    # Pullback parameters
    min_pullback_pct: float = Field(default=0.002, ge=0, le=0.05)
    max_pullback_pct: float = Field(default=0.02, ge=0, le=0.10)
    min_pullback_bars: int = Field(default=3, ge=1, le=30)

    # Reclaim confirmation
    volume_confirmation_multiplier: float = Field(default=1.2, gt=0, le=5.0)
    max_chase_above_vwap_pct: float = Field(default=0.003, ge=0, le=0.02)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)


# ---------------------------------------------------------------------------
# Config Loader
# ---------------------------------------------------------------------------


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse a single YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file is not valid YAML.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def load_config(config_dir: Path) -> ArgusConfig:
    """Load the complete Argus configuration from a directory of YAML files.

    Expected files in config_dir:
        - system.yaml
        - risk_limits.yaml
        - brokers.yaml
        - orchestrator.yaml
        - notifications.yaml

    Missing files use defaults. Extra fields in YAML are ignored.

    Args:
        config_dir: Path to the configuration directory.

    Returns:
        Validated ArgusConfig instance.

    Raises:
        FileNotFoundError: If config_dir does not exist.
        pydantic.ValidationError: If any config value fails validation.
    """
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    raw: dict[str, Any] = {}

    file_mapping = {
        "system": "system.yaml",
        "risk": "risk_limits.yaml",
        "broker": "brokers.yaml",
        "orchestrator": "orchestrator.yaml",
        "notifications": "notifications.yaml",
    }

    for key, filename in file_mapping.items():
        filepath = config_dir / filename
        if filepath.exists():
            raw[key] = load_yaml_file(filepath)

    return ArgusConfig(**raw)


def load_strategy_config(path: Path) -> StrategyConfig:
    """Load a single strategy configuration from a YAML file.

    Args:
        path: Path to the strategy YAML file.

    Returns:
        Validated StrategyConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return StrategyConfig(**data)


def load_orb_config(path: Path) -> OrbBreakoutConfig:
    """Load ORB Breakout strategy configuration from a YAML file.

    Args:
        path: Path to the ORB strategy YAML file.

    Returns:
        Validated OrbBreakoutConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return OrbBreakoutConfig(**data)


def load_orb_scalp_config(path: Path) -> OrbScalpConfig:
    """Load ORB Scalp strategy configuration from a YAML file.

    Args:
        path: Path to the ORB Scalp strategy YAML file.

    Returns:
        Validated OrbScalpConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return OrbScalpConfig(**data)


def load_vwap_reclaim_config(path: Path) -> VwapReclaimConfig:
    """Load VWAP Reclaim strategy configuration from a YAML file.

    Args:
        path: Path to the VWAP Reclaim strategy YAML file.

    Returns:
        Validated VwapReclaimConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return VwapReclaimConfig(**data)


def load_scanner_config(path: Path) -> ScannerConfig:
    """Load scanner configuration from a YAML file.

    Args:
        path: Path to the scanner YAML file.

    Returns:
        Validated ScannerConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return ScannerConfig(**data)


def load_data_service_config(path: Path) -> DataServiceConfig:
    """Load data service configuration from a YAML file.

    Args:
        path: Path to the data service YAML file.

    Returns:
        Validated DataServiceConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return DataServiceConfig(**data)

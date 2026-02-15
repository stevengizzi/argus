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


class LogLevel(StrEnum):
    """Logging level."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Config Sub-Models
# ---------------------------------------------------------------------------

class SystemConfig(BaseModel):
    """Global system settings."""
    timezone: str = "America/New_York"
    market_open: str = "09:30"
    market_close: str = "16:00"
    log_level: LogLevel = LogLevel.INFO
    heartbeat_interval_seconds: int = Field(default=60, ge=1)
    data_dir: str = "data"

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
    duplicate_stock_policy: DuplicateStockPolicy = DuplicateStockPolicy.PRIORITY_BY_WIN_RATE


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


class BrokerConfig(BaseModel):
    """Broker routing and connection configuration."""

    primary: str = "alpaca"
    alpaca: AlpacaConfig = AlpacaConfig()


class OrchestratorConfig(BaseModel):
    """Orchestrator behavior configuration."""
    allocation_method: str = "equal_weight"
    max_allocation_pct: float = Field(default=0.40, gt=0, le=1.0)
    min_allocation_pct: float = Field(default=0.10, gt=0, le=1.0)
    cash_reserve_pct: float = Field(default=0.20, ge=0, le=0.5)
    performance_lookback_days: int = Field(default=20, ge=5)
    consecutive_loss_throttle: int = Field(default=5, ge=2)
    suspension_sharpe_threshold: float = 0.0
    suspension_drawdown_pct: float = Field(default=0.15, gt=0, le=0.5)


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
    supported_timeframes: list[str] = Field(
        default_factory=lambda: ["1s", "5s", "1m", "5m", "15m"]
    )
    indicators: list[str] = Field(
        default_factory=lambda: ["vwap", "atr_14", "rvol", "sma_9", "sma_20", "sma_50"]
    )
    stale_data_timeout_seconds: int = Field(default=30, ge=1)


# ---------------------------------------------------------------------------
# Scanner Config (Sprint 3)
# ---------------------------------------------------------------------------


class ScannerConfig(BaseModel):
    """Configuration for the Scanner."""

    scanner_type: str = "static"  # "static" or "alpaca" (future)
    static_symbols: list[str] = Field(default_factory=list)


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

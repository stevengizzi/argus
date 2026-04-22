"""Argus configuration system.

Loads configuration from YAML files and validates via Pydantic models.
All tunable parameters live in YAML config files, never hardcoded.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

from argus.ai.config import AIConfig
from argus.core.exit_math import StopToLevel
from argus.analytics.config import ObservatoryConfig
from argus.core.regime import RegimeOperatingConditions
from argus.data.historical_query_config import HistoricalQueryConfig
from argus.data.vix_config import VixRegimeConfig
from argus.intelligence.config import (
    CatalystConfig,
    CounterfactualConfig,
    OverflowConfig,
    QualityEngineConfig,
)
from argus.intelligence.experiments.config import ExperimentConfig
from argus.intelligence.learning.models import LearningLoopConfig

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into *base* at the field level (AMD-1).

    Returns a new dict; neither input is mutated.  When both base and
    override have a dict value for the same key, the merge recurses.
    Otherwise the override value wins.

    Args:
        base: The default / global config dict.
        override: The per-strategy (or per-context) overrides.

    Returns:
        A new dict with override values merged into base.
    """
    merged: dict[str, Any] = {}
    for key in base:
        if key in override:
            if isinstance(base[key], dict) and isinstance(override[key], dict):
                merged[key] = deep_update(base[key], override[key])
            else:
                merged[key] = override[key]
        else:
            merged[key] = base[key]
    # Include keys present in override but not in base
    for key in override:
        if key not in base:
            merged[key] = override[key]
    return merged


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


class BreadthConfig(BaseModel):
    """Universe breadth dimension configuration (Sprint 27.6).

    Controls how the breadth calculator measures the fraction of
    the universe trending above their moving averages.
    """

    enabled: bool = True
    ma_period: int = Field(default=20, ge=5, le=200)
    thrust_threshold: float = Field(default=0.80, gt=0, le=1.0)
    min_symbols: int = Field(default=50, ge=10)
    min_bars_for_valid: int = Field(default=10, ge=1)


class CorrelationConfig(BaseModel):
    """Correlation dimension configuration (Sprint 27.6).

    Controls pairwise correlation measurement across the top
    symbols to detect dispersion vs concentration regimes.
    """

    enabled: bool = True
    lookback_days: int = Field(default=20, ge=5, le=252)
    top_n_symbols: int = Field(default=50, ge=10)
    dispersed_threshold: float = Field(default=0.30, ge=0, le=1.0)
    concentrated_threshold: float = Field(default=0.60, ge=0, le=1.0)


class SectorRotationConfig(BaseModel):
    """Sector rotation dimension configuration (Sprint 27.6).

    Controls sector-level relative performance tracking to detect
    risk-on/risk-off rotations.
    """

    enabled: bool = True


class IntradayConfig(BaseModel):
    """Intraday character dimension configuration (Sprint 27.6).

    Controls how the intraday character of the session is classified
    using SPY price action in the first 30 minutes and beyond.
    """

    enabled: bool = True
    first_bar_minutes: int = Field(default=5, ge=1, le=30)
    classification_times: list[str] = Field(
        default_factory=lambda: ["09:35", "10:00", "10:30"]
    )
    min_spy_bars: int = Field(default=3, ge=1)
    drive_strength_trending: float = Field(default=0.4, ge=0)
    drive_strength_breakout: float = Field(default=0.5, ge=0)
    drive_strength_reversal: float = Field(default=0.3, ge=0)
    range_ratio_breakout: float = Field(default=1.2, ge=0)
    vwap_slope_trending: float = Field(default=0.0002, ge=0)
    max_direction_changes_trending: int = Field(default=2, ge=0)


class RegimeIntelligenceConfig(BaseModel):
    """Top-level regime intelligence configuration (Sprint 27.6).

    Gates the entire regime intelligence subsystem and contains
    per-dimension sub-configs.
    """

    enabled: bool = True
    persist_history: bool = True
    vix_calculators_enabled: bool = True
    breadth: BreadthConfig = Field(default_factory=BreadthConfig)
    correlation: CorrelationConfig = Field(default_factory=CorrelationConfig)
    sector_rotation: SectorRotationConfig = Field(default_factory=SectorRotationConfig)
    intraday: IntradayConfig = Field(default_factory=IntradayConfig)


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


class StartupConfig(BaseModel):
    """Configuration for startup behavior (Sprint 27.95 S4).

    Controls how ARGUS handles unknown broker positions at startup.
    """

    flatten_unknown_positions: bool = True


class ReconciliationConfig(BaseModel):
    """Configuration for position reconciliation (Sprint 27.8 + 27.95).

    Controls how the Order Manager handles mismatches between ARGUS
    internal positions and IBKR portfolio snapshots.
    """

    auto_cleanup_orphans: bool = False
    auto_cleanup_unconfirmed: bool = False
    consecutive_miss_threshold: int = Field(default=3, ge=1)


class TrailingStopConfig(BaseModel):
    """Configuration for trailing stop behavior (Sprint 28.5).

    Controls how the trailing stop distance is computed and when it activates.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    type: Literal["atr", "percent", "fixed"] = "atr"
    atr_multiplier: float = Field(default=2.5, gt=0)
    percent: float = Field(default=0.02, gt=0, le=0.2)
    fixed_distance: float = Field(default=0.50, gt=0)
    activation: Literal["after_t1", "after_profit_pct", "immediate"] = "after_t1"
    activation_profit_pct: float = Field(default=0.005, ge=0)
    min_trail_distance: float = Field(default=0.05, ge=0)


class EscalationPhase(BaseModel):
    """A single time-based escalation phase (Sprint 28.5, AMD-5).

    Defines at what fraction of the time stop the stop should ratchet
    to a given profit level.
    """

    model_config = ConfigDict(extra="forbid")

    elapsed_pct: float = Field(gt=0, le=1.0)
    stop_to: StopToLevel


class ExitEscalationConfig(BaseModel):
    """Configuration for time-based exit escalation (Sprint 28.5).

    As time progresses toward the time stop, the stop is ratcheted
    through escalation phases toward profit.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    phases: list[EscalationPhase] = Field(default_factory=list)

    @field_validator("phases")
    @classmethod
    def validate_phases_sorted(cls, v: list[EscalationPhase]) -> list[EscalationPhase]:
        """Phases must be sorted by elapsed_pct ascending."""
        for i in range(1, len(v)):
            if v[i].elapsed_pct <= v[i - 1].elapsed_pct:
                raise ValueError(
                    f"Phases must be sorted by elapsed_pct ascending, "
                    f"but phase {i} ({v[i].elapsed_pct}) <= phase {i - 1} ({v[i - 1].elapsed_pct})"
                )
        return v


class ExitManagementConfig(BaseModel):
    """Top-level exit management configuration (Sprint 28.5).

    Groups trailing stop and escalation configs. Global defaults live in
    config/exit_management.yaml; per-strategy overrides use deep_update().
    """

    model_config = ConfigDict(extra="forbid")

    trailing_stop: TrailingStopConfig = Field(default_factory=TrailingStopConfig)
    escalation: ExitEscalationConfig = Field(default_factory=ExitEscalationConfig)


class ApiConfig(BaseModel):
    """Configuration for the Command Center API server (Sprint 14).

    ``cors_origins`` default is ``["http://localhost:5173"]`` (Vite dev
    server). Tauri desktop and PWA mobile deployments use different origins
    (``tauri://localhost``, the deployed hostname, etc.) and MUST override
    ``api.cors_origins`` in ``system_live.yaml`` before shipping. The dev
    default exists only to keep ``python -m argus.main`` usable during
    frontend development.
    """

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    # Empty default is a sentinel for "not yet configured". Runtime boot
    # calls ``validate_password_hash_set()`` and fails loudly if
    # ``enabled=True`` and the hash is still empty — without that check an
    # operator booting system.yaml (Alpaca incubator) would get a silently
    # broken JWT login path (H2-H10 audit 2026-04-21). The check lives at
    # runtime (not as a ``model_validator``) so that ``ApiConfig()`` stays
    # usable in test contexts where the API is not exercised.
    # Generate a real hash via ``python -m argus.api.setup_password``.
    password_hash: str = ""
    jwt_secret_env: str = "ARGUS_JWT_SECRET"  # env var name for JWT signing key
    jwt_expiry_hours: int = Field(default=24, ge=1)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    ws_heartbeat_interval_seconds: int = Field(default=30, ge=5)
    ws_tick_throttle_ms: int = Field(default=1000, ge=100)
    static_dir: str = ""  # path to built React app; empty = don't serve static

    def validate_password_hash_set(self) -> None:
        """Fail loudly if the API is enabled with no password hash (H2-H10).

        Called by ``load_config()`` at boot time. Not a Pydantic
        ``model_validator`` — tests routinely construct ``ApiConfig()`` /
        ``SystemConfig()`` with defaults and are not exercising the JWT
        path, so tripping the check there would force every test to thread
        a dummy hash.

        Raises:
            ValueError: If ``enabled=True`` and ``password_hash`` is empty.
        """
        if self.enabled and not self.password_hash:
            raise ValueError(
                "api.password_hash is empty but api.enabled is true. "
                "Generate a bcrypt hash with "
                "`python -m argus.api.setup_password` and set "
                "api.password_hash in your system YAML, or set "
                "api.enabled: false to disable the Command Center API."
            )


class GoalsConfig(BaseModel):
    """Goal tracking configuration (Sprint 21d, DEC-214).

    Configures performance targets for the GoalTracker dashboard widget.
    Simple config value for V1; database-backed goals with history can upgrade later.
    """

    monthly_target_usd: float = Field(default=5000.0, ge=0)


class UniverseFilterConfig(BaseModel):
    """Per-strategy universe filtering criteria (Sprint 23).

    Defines the criteria a strategy uses to filter the viable universe
    for symbols matching its requirements.
    """

    min_price: float | None = None
    max_price: float | None = None
    min_market_cap: float | None = None  # USD
    max_market_cap: float | None = None  # USD
    min_float: float | None = None  # shares
    min_avg_volume: int | None = None
    min_relative_volume: float | None = None  # minimum relative volume (RVOL)
    min_gap_percent: float | None = None  # minimum gap-up/gap-down percent
    min_premarket_volume: int | None = None  # minimum pre-market volume
    sectors: list[str] = Field(default_factory=list)  # empty = all sectors
    exclude_sectors: list[str] = Field(default_factory=list)  # empty = no exclusions


class UniverseManagerConfig(BaseModel):
    """System-level universe manager configuration (Sprint 23).

    Controls the Universe Manager which builds and maintains the
    viable trading universe from reference data sources.
    """

    enabled: bool = False
    min_price: float = 5.0
    max_price: float = 10000.0
    min_avg_volume: int = 100000
    exclude_otc: bool = True
    reference_cache_ttl_hours: int = 24
    fmp_batch_size: int = 50
    trust_cache_on_startup: bool = True


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
    # Goal tracking configuration (Sprint 21d, DEC-214)
    goals: GoalsConfig = Field(default_factory=lambda: GoalsConfig())
    # AI Layer configuration (Sprint 22)
    ai: AIConfig = Field(default_factory=lambda: AIConfig())
    # Universe Manager configuration (Sprint 23)
    universe_manager: UniverseManagerConfig = Field(default_factory=UniverseManagerConfig)
    # NLP Catalyst Pipeline configuration (Sprint 23.5 — DEC-164)
    catalyst: CatalystConfig = Field(default_factory=CatalystConfig)
    # Quality Engine configuration (Sprint 24 — Setup Quality + Dynamic Sizer)
    quality_engine: QualityEngineConfig = Field(default_factory=QualityEngineConfig)
    # Observatory configuration (Sprint 25 — The Observatory)
    observatory: ObservatoryConfig = Field(default_factory=ObservatoryConfig)
    # Regime Intelligence configuration (Sprint 27.6 — multi-dimensional regime)
    regime_intelligence: RegimeIntelligenceConfig = Field(default_factory=RegimeIntelligenceConfig)
    # Counterfactual Engine configuration (Sprint 27.7 — shadow position tracking)
    counterfactual: CounterfactualConfig = Field(default_factory=CounterfactualConfig)
    # VIX Regime configuration (Sprint 27.9 — VIX landscape dimension)
    vix_regime: VixRegimeConfig = Field(default_factory=VixRegimeConfig)
    # Startup behavior configuration (Sprint 27.95 S4 — zombie cleanup)
    startup: StartupConfig = Field(default_factory=StartupConfig)
    # Reconciliation configuration (Sprint 27.8 + 27.95 — ghost position fix)
    reconciliation: ReconciliationConfig = Field(default_factory=ReconciliationConfig)
    # Overflow management configuration (Sprint 27.95 — signal overflow routing)
    overflow: OverflowConfig = Field(default_factory=OverflowConfig)
    # Learning Loop configuration (Sprint 28 — adaptive config tuning)
    learning_loop: LearningLoopConfig = Field(default_factory=LearningLoopConfig)
    # Experiment pipeline configuration (Sprint 32 — parameterized templates)
    experiments: ExperimentConfig = Field(default_factory=ExperimentConfig)
    # Historical Query Service configuration (Sprint 31A.5 — DuckDB Parquet layer)
    historical_query: HistoricalQueryConfig = Field(default_factory=HistoricalQueryConfig)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string is plausible (basic check)."""
        if "/" not in v and v != "UTC":
            raise ValueError(f"Timezone must be IANA format (e.g., 'America/New_York'), got '{v}'")
        return v


class AccountRiskConfig(BaseModel):
    """Account-level risk limits."""

    daily_loss_limit_pct: float = Field(default=0.03, gt=0, le=1.0)
    weekly_loss_limit_pct: float = Field(default=0.05, gt=0, le=1.0)
    cash_reserve_pct: float = Field(default=0.20, ge=0, le=0.5)
    max_concurrent_positions: int = Field(default=10, ge=0)  # 0 = disabled (no limit)
    emergency_shutdown_enabled: bool = True
    # Minimum position risk floor — positions below this dollar amount are rejected
    # as "not worth taking" (replaces ratio-based 0.25R floor — DEC-250)
    min_position_risk_dollars: float = Field(default=100.0, gt=0)


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
    # EQUS.MINI = US Equities Mini consolidated feed (Standard plan — DEC-237)
    dataset: str = "EQUS.MINI"

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
            # Consolidated feeds (preferred for Standard plan — DEC-237)
            "EQUS.MINI",  # US Equities Mini — consolidated feed (Standard plan)
            "EQUS.MAX",  # US Equities Max — all exchanges (Plus/Pro)
            "EQUS.SUMMARY",  # Consolidated summary (delayed)
            # Exchange-specific feeds (require Plus tier or higher)
            "XNAS.ITCH",  # Nasdaq TotalView-ITCH
            "XNAS.BASIC",  # Nasdaq Basic with NLS Plus
            "XNYS.PILLAR",  # NYSE Integrated
            "ARCX.PILLAR",  # NYSE Arca Integrated
            "XASE.PILLAR",  # NYSE American Integrated
            "DBEQ.BASIC",  # Databento Equities Basic (free tier)
            "XBOS.ITCH",  # Nasdaq BX TotalView-ITCH
            "XPSX.ITCH",  # Nasdaq PSX TotalView-ITCH
            "XCHI.PILLAR",  # NYSE Chicago Integrated
            "XCIS.TRADESBBO",  # NYSE National Trades and BBO
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

    # Throttler suspend bypass (paper trading data capture)
    throttler_suspend_enabled: bool = True

    # Correlation limits
    correlation_enabled: bool = True
    min_correlation_days: int = Field(default=20, ge=5)
    max_combined_correlated_allocation: float = Field(default=0.60, gt=0, le=1.0)

    # ORB family mutual exclusion (DEC-261)
    orb_family_mutual_exclusion: bool = True

    # Pre-EOD signal cutoff (Sprint 32.9)
    signal_cutoff_enabled: bool = True
    signal_cutoff_time: str = "15:30"  # HH:MM ET — no new entries after this time


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
    max_concurrent_positions: int = Field(default=3, ge=0)  # 0 = disabled (no limit)


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


class BacktestSummaryConfig(BaseModel):
    """Backtest validation summary for a strategy (Sprint 21a).

    Tracks the validation status and key metrics from parameter sweeps
    and walk-forward analysis.

    Documentary fields (``data_source``, ``universe_size``, ``universe_note``,
    ``avg_win_rate``, ``avg_profit_factor``, ``data_range``,
    ``prior_baseline``) added by FIX-16 (audit 2026-04-21, H2-S03): all 15
    strategy YAMLs already carried these in the ``backtest_summary`` block,
    but the model only modelled the original 6 fields, so the rest were
    silently dropped at load time. The frontend currently consumes only the
    base 6, but the documentary fields belong on the strategy spec sheet
    and now survive the load.
    """

    status: str = "not_validated"
    wfe_pnl: float | None = None
    oos_sharpe: float | None = None
    total_trades: int | None = None
    data_months: int | None = None
    last_run: str | None = None
    # Documentary fields preserved from strategy YAML for spec-sheet display
    # (FIX-16, audit 2026-04-21, H2-S03). ``prior_baseline`` is a free-form
    # dict (e.g. ``{source, oos_sharpe, wfe_pnl, total_trades}``) — modelled
    # as ``dict[str, Any]`` rather than a sub-Pydantic model so that schema
    # drift in old strategy YAMLs does not cause load failure.
    data_source: str | None = None
    universe_size: int | None = None
    universe_note: str | None = None
    data_range: str | None = None
    avg_win_rate: float | None = None
    avg_profit_factor: float | None = None
    prior_baseline: dict[str, Any] | None = None


class StrategyMode(StrEnum):
    """Operating mode for a strategy (Sprint 27.7).

    Defined here (rather than in ``argus.strategies.base_strategy``) to let
    ``StrategyConfig.mode`` be a typed enum field without a circular import.
    ``base_strategy`` re-exports it for callers who still reference the old
    import path (FIX-19 P1-B-L01).
    """

    LIVE = "live"      # Signals flow through the quality + risk pipeline.
    SHADOW = "shadow"  # Signals routed to CounterfactualTracker only.


class StrategyConfig(BaseModel):
    """Base configuration for any strategy. Individual strategies
    extend this with strategy-specific parameters."""

    strategy_id: str
    name: str
    version: str = "1.0.0"
    enabled: bool = True
    mode: StrategyMode = StrategyMode.LIVE  # "live" | "shadow" (Sprint 27.7)
    asset_class: str = "us_stocks"
    pipeline_stage: str = "concept"
    family: str = "uncategorized"
    description_short: str = ""
    time_window_display: str = ""
    backtest_summary: BacktestSummaryConfig = Field(default_factory=BacktestSummaryConfig)
    risk_limits: StrategyRiskLimits = StrategyRiskLimits()
    operating_window: OperatingWindow = OperatingWindow()
    benchmarks: PerformanceBenchmarks = PerformanceBenchmarks()
    universe_filter: UniverseFilterConfig | None = None
    operating_conditions: RegimeOperatingConditions | None = None
    # Regime filter override — when non-None, overrides the hardcoded default in
    # `get_market_conditions_filter()`. Values must be valid `MarketRegime` enum
    # members (bullish_trending, bearish_trending, range_bound, high_volatility,
    # crisis). See FIX-19 P1-B-M03.
    allowed_regimes: list[str] | None = None


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
# Scanner Config — ScannerConfig + load_scanner_config removed by FIX-16
# (audit 2026-04-21, H2-S06). The shim only modelled scanner_type +
# static_symbols; the 3 nested provider blocks in config/scanner.yaml
# (fmp_scanner, alpaca_scanner, databento_scanner) were silently dropped.
# Production code in argus/main.py reads scanner.yaml directly and builds
# provider-specific configs (FMPScannerConfig, DatabentoScannerConfig,
# AlpacaScannerConfig) from each block.
# ---------------------------------------------------------------------------


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
    # Trailing stop config moved to exit_management.yaml / ExitManagementConfig
    # in Sprint 28.5. Legacy V1 fields (enable_trailing_stop,
    # trailing_stop_atr_multiplier) removed by FIX-16 (audit 2026-04-21, DEF-109).
    max_position_duration_minutes: int = Field(default=120, ge=1)  # Hard time stop
    entry_timeout_seconds: int = Field(default=30, ge=1)
    t1_position_pct: float = Field(default=0.5, gt=0, le=1.0)  # 50% at T1
    # Max retries for _submit_stop_order broker connectivity failures
    stop_retry_max: int = Field(default=3, ge=0)
    # Max retries for _resubmit_stop_with_retry cancel-event loop (IBKR cancels the stop)
    stop_cancel_retry_max: int = Field(default=3, ge=0)
    auto_shutdown_after_eod: bool = True  # Gracefully shutdown after EOD flatten
    auto_shutdown_delay_seconds: int = Field(default=60, ge=0)  # Delay before shutdown
    # Flatten-pending timeout: cancel+resubmit stale flatten orders (Sprint 28.75)
    flatten_pending_timeout_seconds: int = Field(default=120, ge=10)
    max_flatten_retries: int = Field(default=3, ge=1)
    # Max flatten retry cycles before abandoning (Sprint 29.5)
    max_flatten_cycles: int = Field(default=2, ge=1)
    # EOD flatten fill-verification timeout (Sprint 32.9)
    eod_flatten_timeout_seconds: int = Field(default=30, ge=1)
    # Retry timed-out/rejected EOD flattens once via broker re-query (Sprint 32.9)
    eod_flatten_retry_rejected: bool = True
    # Margin circuit breaker: open after N IBKR margin rejections this session (Sprint 32.9 S2)
    margin_rejection_threshold: int = Field(default=10, ge=1)
    # Auto-reset margin circuit when broker position count drops below N (Sprint 32.9 S2)
    margin_circuit_reset_positions: int = Field(default=20, ge=1)


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

    @model_validator(mode="after")
    def validate_pullback_range(self) -> VwapReclaimConfig:
        """Ensure min_pullback_pct is less than max_pullback_pct."""
        if self.min_pullback_pct >= self.max_pullback_pct:
            raise ValueError(
                f"min_pullback_pct ({self.min_pullback_pct}) must be less than "
                f"max_pullback_pct ({self.max_pullback_pct})"
            )
        return self


class AfternoonMomentumConfig(StrategyConfig):
    """Afternoon Momentum strategy configuration (DEC-152).

    Consolidation breakout strategy that identifies stocks consolidating
    during midday (12:00–2:00 PM) and entering on breakouts after 2:00 PM.

    State machine: WATCHING → ACCUMULATING → CONSOLIDATED → entry (or REJECTED)
    """

    # Consolidation window
    consolidation_start_time: str = "12:00"

    # Consolidation parameters
    consolidation_atr_ratio: float = Field(default=0.75, gt=0, le=5.0)
    max_consolidation_atr_ratio: float = Field(default=2.0, gt=0, le=10.0)
    min_consolidation_bars: int = Field(default=30, ge=5, le=120)

    # Breakout confirmation
    volume_multiplier: float = Field(default=1.2, gt=0, le=5.0)
    max_chase_pct: float = Field(default=0.005, ge=0, le=0.03)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    max_hold_minutes: int = Field(default=60, ge=5, le=120)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)
    force_close_time: str = "15:45"

    @model_validator(mode="after")
    def validate_atr_ratios(self) -> AfternoonMomentumConfig:
        """Ensure consolidation_atr_ratio is less than max_consolidation_atr_ratio."""
        if self.consolidation_atr_ratio >= self.max_consolidation_atr_ratio:
            raise ValueError(
                f"consolidation_atr_ratio ({self.consolidation_atr_ratio}) must be less than "
                f"max_consolidation_atr_ratio ({self.max_consolidation_atr_ratio})"
            )
        return self


class RedToGreenConfig(StrategyConfig):
    """Red-to-Green strategy configuration (Sprint 26).

    Gap-down reversal strategy that enters long when price tests and
    holds a key support level (VWAP, premarket low, prior close) after
    a gap down. Operates 9:45 AM – 11:00 AM ET.

    State machine: WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → entry
    (or EXHAUSTED)
    """

    # Gap parameters
    min_gap_down_pct: float = Field(default=0.02, ge=0, le=0.50)
    max_gap_down_pct: float = Field(default=0.10, ge=0, le=0.50)

    # Level testing parameters
    level_proximity_pct: float = Field(default=0.003, ge=0, le=0.05)
    min_level_test_bars: int = Field(default=2, ge=1, le=30)
    volume_confirmation_multiplier: float = Field(default=1.2, gt=0, le=5.0)
    max_chase_pct: float = Field(default=0.003, ge=0, le=0.05)
    max_level_attempts: int = Field(default=2, ge=1, le=10)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=20, ge=1)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)

    @model_validator(mode="after")
    def validate_gap_range(self) -> RedToGreenConfig:
        """Ensure min_gap_down_pct is less than max_gap_down_pct."""
        if self.min_gap_down_pct >= self.max_gap_down_pct:
            raise ValueError(
                f"min_gap_down_pct ({self.min_gap_down_pct}) must be less than "
                f"max_gap_down_pct ({self.max_gap_down_pct})"
            )
        return self


class BullFlagConfig(StrategyConfig):
    """Bull Flag continuation pattern strategy configuration (Sprint 26).

    Detects strong upward moves (pole) followed by tight consolidation
    (flag), then enters on breakout with volume confirmation.
    Operates 10:00 AM - 3:00 PM ET.
    """

    # Pole parameters
    pole_min_bars: int = Field(default=5, ge=2, le=50)
    pole_min_move_pct: float = Field(default=0.03, gt=0, le=0.50)

    # Flag parameters
    flag_max_bars: int = Field(default=20, ge=1, le=100)
    flag_max_retrace_pct: float = Field(default=0.50, gt=0, le=1.0)

    # Breakout confirmation
    breakout_volume_multiplier: float = Field(default=1.3, gt=0, le=10.0)

    # Detection scoring parameters
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)
    pole_strength_cap_pct: float = Field(default=0.10, gt=0, le=1.0)
    breakout_excess_cap_pct: float = Field(default=0.02, gt=0, le=0.50)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)


class FlatTopBreakoutConfig(StrategyConfig):
    """Flat-Top Breakout pattern strategy configuration (Sprint 26).

    Detects horizontal resistance with multiple touches, tight
    consolidation below, and volume-confirmed breakout above.
    Operates 10:00 AM - 3:00 PM ET.
    """

    # Resistance parameters
    resistance_touches: int = Field(default=3, ge=2, le=20)
    resistance_tolerance_pct: float = Field(default=0.002, gt=0, le=0.05)

    # Consolidation parameters
    consolidation_min_bars: int = Field(default=10, ge=2, le=100)

    # Breakout confirmation
    breakout_volume_multiplier: float = Field(default=1.3, gt=0, le=10.0)

    # Detection scoring parameters
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)
    max_range_narrowing: float = Field(default=1.0, ge=0, le=2.0)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)


class DipAndRipConfig(StrategyConfig):
    """Dip-and-Rip momentum reversal pattern strategy configuration (Sprint 29).

    Detects sharp intraday dips followed by rapid recoveries.
    Enters on confirmed recovery with volume. Operates 9:45 AM - 11:30 AM ET.
    """

    # Dip detection parameters
    dip_lookback: int = Field(default=10, ge=2, le=30)
    min_dip_percent: float = Field(default=0.02, gt=0, le=0.10)
    max_dip_bars: int = Field(default=5, ge=1, le=20)

    # Recovery parameters
    min_recovery_percent: float = Field(default=0.50, gt=0, le=1.0)
    max_recovery_bars: int = Field(default=8, ge=1, le=30)
    max_recovery_ratio: float = Field(default=1.5, gt=0, le=5.0)
    entry_threshold_percent: float = Field(default=0.60, gt=0, le=1.0)

    # Volume filtering
    min_recovery_volume_ratio: float = Field(default=1.3, gt=0, le=10.0)

    # Stop and target
    stop_buffer_atr_mult: float = Field(default=0.3, gt=0, le=2.0)
    target_ratio: float = Field(default=1.5, gt=0, le=5.0)

    # Targets and stops
    target_1_r: float = Field(default=1.5, gt=0)
    target_2_r: float = Field(default=2.5, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)


class HODBreakConfig(StrategyConfig):
    """HOD Break continuation pattern strategy configuration (Sprint 29).

    Detects high-of-day breakout continuations — consolidation near
    session high followed by volume-confirmed breakout.
    Operates 10:00 AM - 3:30 PM ET.
    """

    # HOD tracking
    hod_proximity_percent: float = Field(default=0.003, gt=0, le=0.01)

    # Consolidation parameters
    consolidation_min_bars: int = Field(default=5, ge=2, le=30)
    consolidation_max_range_atr: float = Field(default=0.8, gt=0, le=3.0)

    # Breakout confirmation
    breakout_margin_percent: float = Field(default=0.001, gt=0, le=0.01)
    min_hold_bars: int = Field(default=2, ge=1, le=10)
    min_breakout_volume_ratio: float = Field(default=1.5, gt=0, le=10.0)

    # Stop and target
    stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=2.0)
    target_ratio: float = Field(default=2.0, gt=0, le=5.0)

    # VWAP scoring parameter
    vwap_extended_pct: float = Field(default=0.05, gt=0, le=0.10)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=45, ge=1)


class GapAndGoConfig(StrategyConfig):
    """Gap-and-Go continuation pattern strategy configuration (Sprint 29).

    Detects gap-up continuations — stocks gapping up on high relative
    volume that maintain momentum after the open. Requires prior close
    data via set_reference_data() hook.
    Operates 9:35 AM - 10:30 AM ET.
    """

    # Gap detection
    min_gap_percent: float = Field(default=3.0, gt=0, le=20.0)

    # Volume confirmation
    min_relative_volume: float = Field(default=2.0, gt=0, le=20.0)
    volume_check_bars: int = Field(default=5, ge=1, le=15)

    # VWAP hold
    min_vwap_hold_bars: int = Field(default=3, ge=1, le=15)
    vwap_check_window: int = Field(default=8, ge=1, le=15)

    # Entry mode
    entry_mode: str = Field(default="first_pullback")

    # Stop mode
    stop_mode: str = Field(default="tighter")

    # Target
    target_ratio: float = Field(default=1.0, gt=0, le=5.0)

    # Detection scoring parameters
    prior_day_avg_volume: float = Field(default=0.0, ge=0)
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)
    gap_atr_cap: float = Field(default=5.0, gt=0, le=10.0)
    volume_score_cap: float = Field(default=5.0, gt=0, le=20.0)
    vwap_hold_score_divisor: float = Field(default=8.0, gt=0, le=15.0)
    catalyst_base_score: float = Field(default=10.0, ge=0, le=25.0)
    min_risk_per_share: float = Field(default=0.10, gt=0, le=0.50)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=20, ge=1)


class ABCDConfig(StrategyConfig):
    """ABCD harmonic pattern strategy configuration (Sprint 29).

    Detects measured-move ABCD patterns where the CD leg mirrors
    the AB leg with Fibonacci retracement at B and C points.
    Operates 10:00 AM - 3:00 PM ET.
    """

    # ``pattern_class`` field removed by FIX-16 (audit 2026-04-21, H2-S08):
    # only ABCDConfig had it, so an operator adding ``pattern_class:`` to any
    # other pattern YAML would see it silently dropped. Pattern resolution
    # now flows uniformly through factory class-name inference for all 10
    # patterns (``ABCDConfig`` → ``ABCDPattern``).

    # Swing detection parameters
    swing_lookback: int = Field(default=5, ge=2, le=20)
    min_swing_atr_mult: float = Field(default=0.5, gt=0, le=5.0)

    # Fibonacci parameters
    fib_b_min: float = Field(default=0.382, gt=0, le=1.0)
    fib_b_max: float = Field(default=0.618, gt=0, le=1.0)
    fib_c_min: float = Field(default=0.500, gt=0, le=1.0)
    fib_c_max: float = Field(default=0.786, gt=0, le=1.5)

    # Leg ratio parameters
    leg_price_ratio_min: float = Field(default=0.8, gt=0, le=2.0)
    leg_price_ratio_max: float = Field(default=1.2, gt=0, le=3.0)
    leg_time_ratio_min: float = Field(default=0.5, gt=0, le=2.0)
    leg_time_ratio_max: float = Field(default=2.0, gt=0, le=5.0)

    # Completion and trade parameters
    completion_tolerance_percent: float = Field(default=1.0, ge=0, le=5.0)
    stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=3.0)
    target_extension: float = Field(default=1.272, gt=0, le=3.0)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=60, ge=1)

    # allowed_regimes inherited from StrategyConfig (FIX-19 P1-B-M03).


class PreMarketHighBreakConfig(StrategyConfig):
    """Pre-Market High Break pattern strategy configuration (Sprint 29).

    Detects breakouts above the pre-market session high with volume
    confirmation and hold-bar validation. Requires pre-market candle
    data via set_reference_data() hook.
    Operates 9:35 AM - 10:30 AM ET.
    """

    # Pre-market session
    min_pm_candles: int = Field(default=3, ge=1, le=20)
    min_pm_volume: int = Field(default=10000, ge=0)

    # Breakout detection
    breakout_margin_percent: float = Field(default=0.0015, ge=0, le=0.05)
    min_breakout_volume_ratio: float = Field(default=1.5, gt=0, le=10.0)
    min_hold_bars: int = Field(default=2, ge=1, le=10)
    pm_high_proximity_percent: float = Field(default=0.002, ge=0, le=0.05)

    # Stop and target
    stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=3.0)
    target_ratio: float = Field(default=1.5, gt=0, le=5.0)

    # Detection scoring parameters
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)
    vwap_extended_pct: float = Field(default=0.05, gt=0, le=0.10)
    gap_up_bonus_pct: float = Field(default=1.0, ge=0, le=20.0)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)


class MicroPullbackConfig(StrategyConfig):
    """Micro Pullback continuation pattern strategy configuration (Sprint 31A).

    Detects the first shallow pullback to a short-term EMA after a strong
    impulsive move — a momentum continuation entry with volume confirmation.
    Operates 10:00 AM – 14:00 ET.
    """

    # EMA detection
    ema_period: int = Field(default=9, ge=5, le=21)

    # Impulse detection
    min_impulse_percent: float = Field(default=0.02, gt=0, le=0.10)
    min_impulse_bars: int = Field(default=3, ge=2, le=8)
    max_impulse_bars: int = Field(default=15, ge=5, le=20)

    # Pullback parameters
    max_pullback_bars: int = Field(default=5, ge=2, le=10)
    pullback_tolerance_atr: float = Field(default=0.3, gt=0, le=1.0)

    # Volume confirmation
    min_bounce_volume_ratio: float = Field(default=1.2, gt=0, le=10.0)

    # Stop and target
    stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=2.0)
    target_ratio: float = Field(default=2.0, gt=0, le=5.0)

    # Scoring gate
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)


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


# Standalone YAML files that override their corresponding top-level keys
# inside the loaded system config (Option B, DEC-384 / FIX-01 audit 2026-04-21).
#
# When a file listed here exists at ``config/<filename>``, its contents are
# deep-merged over the matching top-level key of the system config with
# precedence ``standalone > live > base``. This keeps per-subsystem configs
# as a single source of truth without forcing operators to keep values
# duplicated across ``system.yaml`` / ``system_live.yaml``.
#
# **File shape convention**: bare fields at the top level — do NOT wrap the
# contents in a ``<section_key>:`` block. The registry's ``section_key``
# (e.g. ``"overflow"``) tells ``load_config()`` which top-level key of the
# system config this file overlays; the file itself contains only the fields
# (e.g. ``enabled: true`` / ``broker_capacity: 50``). ``quality_engine.yaml``
# is the reference; ``overflow.yaml`` follows the same shape (FIX-02).
#
# Extend this tuple — do NOT edit ``load_config()`` logic — when a new
# standalone config is introduced.
_STANDALONE_SYSTEM_OVERLAYS: tuple[tuple[str, str], ...] = (
    ("quality_engine", "quality_engine.yaml"),
    ("overflow", "overflow.yaml"),
    # FIX-16 (audit 2026-04-21) — wired the four previously-dead YAMLs that
    # operators were editing under the assumption they took effect:
    #   H2-H13 / H2-DEAD01 → learning_loop.yaml
    #   H2-H15 / H2-DEAD02 → regime.yaml
    #   H2-DEAD06          → vix_regime.yaml
    #   H2-D06             → historical_query.yaml (operator-owned cache_dir)
    # Each file already had bare-field shape (no top-level wrapper), matching
    # the DEC-384 / FIX-02 convention.
    ("learning_loop", "learning_loop.yaml"),
    ("regime_intelligence", "regime.yaml"),
    ("vix_regime", "vix_regime.yaml"),
    ("historical_query", "historical_query.yaml"),
)


def load_config(config_dir: Path, system_config_file: Path | None = None) -> ArgusConfig:
    """Load the complete Argus configuration from a directory of YAML files.

    Expected files in config_dir:
        - system.yaml (or override via system_config_file)
        - risk_limits.yaml
        - brokers.yaml
        - orchestrator.yaml
        - notifications.yaml

    Missing files use defaults. Extra fields in YAML are ignored.

    **Standalone overlays** (DEC-384 / FIX-01 audit 2026-04-21; extended by
    FIX-02). Files listed in ``_STANDALONE_SYSTEM_OVERLAYS`` — currently
    ``quality_engine.yaml`` and ``overflow.yaml`` — are deep-merged over the
    corresponding top-level key of the loaded system config. Precedence:
    ``standalone > live > base``. This lets a per-subsystem YAML serve as
    the single source of truth for its block without duplicating values into
    ``system.yaml`` / ``system_live.yaml``.

    Args:
        config_dir: Path to the configuration directory.
        system_config_file: Optional path to a specific system config file.
            If provided, this file is used instead of config_dir/system.yaml.
            Useful for switching between profiles (e.g., system_live.yaml).

    Returns:
        Validated ArgusConfig instance.

    Raises:
        FileNotFoundError: If config_dir does not exist or system_config_file
            is specified but does not exist.
        pydantic.ValidationError: If any config value fails validation.
    """
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    if system_config_file is not None and not system_config_file.exists():
        raise FileNotFoundError(f"System config file not found: {system_config_file}")

    raw: dict[str, Any] = {}

    file_mapping = {
        "system": "system.yaml",
        "risk": "risk_limits.yaml",
        "broker": "brokers.yaml",
        "orchestrator": "orchestrator.yaml",
        "notifications": "notifications.yaml",
    }

    for key, filename in file_mapping.items():
        # Use custom system config file if provided
        if key == "system" and system_config_file is not None:
            raw[key] = load_yaml_file(system_config_file)
        else:
            filepath = config_dir / filename
            if filepath.exists():
                raw[key] = load_yaml_file(filepath)

    # Apply standalone YAML overlays over the system block (DEC-384).
    system_block = raw.get("system")
    if isinstance(system_block, dict):
        merged_sections: list[str] = []
        for section_key, overlay_filename in _STANDALONE_SYSTEM_OVERLAYS:
            overlay_path = config_dir / overlay_filename
            if not overlay_path.exists():
                continue
            overlay = load_yaml_file(overlay_path)
            if not isinstance(overlay, dict):
                logger.warning(
                    "load_config: standalone overlay %s is not a dict "
                    "(got %s) — skipping",
                    overlay_filename,
                    type(overlay).__name__,
                )
                continue
            existing = system_block.get(section_key)
            if isinstance(existing, dict):
                system_block[section_key] = deep_update(existing, overlay)
            else:
                system_block[section_key] = overlay
            merged_sections.append(section_key)
        if merged_sections:
            logger.info(
                "load_config: standalone overlays merged into system block — %s",
                ", ".join(merged_sections),
            )
        raw["system"] = system_block

    argus_config = ArgusConfig(**raw)

    # H2-H10 (audit 2026-04-21): fail loudly on empty password_hash when
    # api.enabled is true. Runs only on real load_config() — bare
    # ApiConfig() / SystemConfig() in tests remains unaffected.
    argus_config.system.api.validate_password_hash_set()

    return argus_config


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


def load_afternoon_momentum_config(path: Path) -> AfternoonMomentumConfig:
    """Load Afternoon Momentum strategy configuration from a YAML file.

    Args:
        path: Path to the Afternoon Momentum strategy YAML file.

    Returns:
        Validated AfternoonMomentumConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return AfternoonMomentumConfig(**data)


def load_red_to_green_config(path: Path) -> RedToGreenConfig:
    """Load Red-to-Green strategy configuration from a YAML file.

    Args:
        path: Path to the Red-to-Green strategy YAML file.

    Returns:
        Validated RedToGreenConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return RedToGreenConfig(**data)


def load_bull_flag_config(path: Path) -> BullFlagConfig:
    """Load Bull Flag strategy configuration from a YAML file.

    Args:
        path: Path to the Bull Flag strategy YAML file.

    Returns:
        Validated BullFlagConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return BullFlagConfig(**data)


def load_flat_top_breakout_config(path: Path) -> FlatTopBreakoutConfig:
    """Load Flat-Top Breakout strategy configuration from a YAML file.

    Args:
        path: Path to the Flat-Top Breakout strategy YAML file.

    Returns:
        Validated FlatTopBreakoutConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return FlatTopBreakoutConfig(**data)


def load_dip_and_rip_config(path: Path) -> DipAndRipConfig:
    """Load Dip-and-Rip strategy configuration from a YAML file.

    Args:
        path: Path to the Dip-and-Rip strategy YAML file.

    Returns:
        Validated DipAndRipConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return DipAndRipConfig(**data)


def load_hod_break_config(path: Path) -> HODBreakConfig:
    """Load HOD Break strategy configuration from a YAML file.

    Args:
        path: Path to the HOD Break strategy YAML file.

    Returns:
        Validated HODBreakConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return HODBreakConfig(**data)


def load_abcd_config(path: Path) -> ABCDConfig:
    """Load ABCD harmonic pattern strategy configuration from a YAML file.

    Args:
        path: Path to the ABCD strategy YAML file.

    Returns:
        Validated ABCDConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return ABCDConfig(**data)


def load_gap_and_go_config(path: Path) -> GapAndGoConfig:
    """Load Gap-and-Go strategy configuration from a YAML file.

    Args:
        path: Path to the Gap-and-Go strategy YAML file.

    Returns:
        Validated GapAndGoConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return GapAndGoConfig(**data)


def load_premarket_high_break_config(
    path: Path,
) -> PreMarketHighBreakConfig:
    """Load Pre-Market High Break strategy configuration from a YAML file.

    Args:
        path: Path to the Pre-Market High Break strategy YAML file.

    Returns:
        Validated PreMarketHighBreakConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return PreMarketHighBreakConfig(**data)


class VwapBounceConfig(StrategyConfig):
    """VWAP Bounce continuation pattern strategy configuration (Sprint 31A).

    Detects a pullback to VWAP from above followed by a bounce with volume
    confirmation — a continuation entry complementing VWAP Reclaim.
    Operates 10:30 AM – 15:00 ET.
    """

    # VWAP proximity thresholds
    vwap_approach_distance_pct: float = Field(default=0.005, gt=0, le=0.015)
    vwap_touch_tolerance_pct: float = Field(default=0.002, gt=0, le=0.005)

    # Bounce confirmation
    min_bounce_bars: int = Field(default=2, ge=1, le=5)
    min_bounce_volume_ratio: float = Field(default=1.3, gt=0, le=10.0)

    # Prior trend requirements
    min_prior_trend_bars: int = Field(default=15, ge=10, le=30)
    min_price_above_vwap_pct: float = Field(default=0.003, gt=0, le=0.010)

    # Stop and target
    stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=2.0)
    target_ratio: float = Field(default=2.0, gt=0, le=5.0)

    # Scoring gate
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)

    # Targets
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)

    # Signal density controls (DEF-154)
    min_approach_distance_pct: float = Field(default=0.003, gt=0, le=0.010)
    min_bounce_follow_through_bars: int = Field(default=2, ge=0, le=5)
    max_signals_per_symbol: int = Field(default=3, ge=1, le=10)


class NarrowRangeBreakoutConfig(StrategyConfig):
    """Narrow Range Breakout pattern strategy configuration (Sprint 31A).

    Detects volatility compression via progressively narrowing bar ranges,
    then enters on a volume-confirmed breakout above the consolidation high.
    Operates 10:00 AM – 15:00 ET.
    """

    # Narrowing-sequence detection
    nr_lookback: int = Field(default=7, ge=4, le=15)
    min_narrowing_bars: int = Field(default=3, ge=2, le=7)
    range_decay_tolerance: float = Field(default=1.05, ge=1.0, le=1.15)

    # Breakout confirmation
    breakout_margin_percent: float = Field(default=0.001, gt=0, le=0.005)
    min_breakout_volume_ratio: float = Field(default=1.5, gt=0, le=10.0)

    # Consolidation quality gate
    consolidation_max_range_atr: float = Field(default=0.8, gt=0, le=2.0)

    # Stop and target
    stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=2.0)
    target_ratio: float = Field(default=2.0, gt=0, le=5.0)

    # Scoring gate
    min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)

    # Targets
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)


def load_micro_pullback_config(path: Path) -> MicroPullbackConfig:
    """Load Micro Pullback strategy configuration from a YAML file.

    Args:
        path: Path to the Micro Pullback strategy YAML file.

    Returns:
        Validated MicroPullbackConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return MicroPullbackConfig(**data)


def load_vwap_bounce_config(path: Path) -> VwapBounceConfig:
    """Load VWAP Bounce strategy configuration from a YAML file.

    Args:
        path: Path to the VWAP Bounce strategy YAML file.

    Returns:
        Validated VwapBounceConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return VwapBounceConfig(**data)


def load_narrow_range_breakout_config(path: Path) -> NarrowRangeBreakoutConfig:
    """Load Narrow Range Breakout strategy configuration from a YAML file.

    Args:
        path: Path to the Narrow Range Breakout strategy YAML file.

    Returns:
        Validated NarrowRangeBreakoutConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If validation fails.
    """
    data = load_yaml_file(path)
    return NarrowRangeBreakoutConfig(**data)


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

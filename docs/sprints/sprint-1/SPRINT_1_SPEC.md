# ARGUS — Sprint 1 Implementation Spec

> **Sprint 1: Foundation (Steps 1–3)**
> **Date:** February 15, 2026
> **Goal:** Config system, Event Bus, Data Models, Database, Trade Logger
> **End State:** `pytest` passes with config loading, event pub/sub, and trade read/write all working.

---

## Instructions for Claude Code

Build everything in this spec in order (Step 1 → Step 2 → Step 3). Run tests after each step to verify before moving on. Follow the CLAUDE.md code style rules exactly (type hints everywhere, Google-style docstrings, no magic). All config values come from YAML — no hardcoded defaults in business logic.

---

## Step 1: Project Skeleton + Config Layer

### 1.1 pyproject.toml

Create at repo root:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "argus"
version = "0.1.0"
description = "Automated multi-strategy day trading ecosystem"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5,<3",
    "pydantic-settings>=2.1,<3",
    "PyYAML>=6.0,<7",
    "aiosqlite>=0.19,<1",
    "python-ulid>=2.2,<3",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4,<9",
    "pytest-asyncio>=0.23,<1",
    "pytest-cov>=4.1,<6",
    "ruff>=0.2,<1",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]

[tool.setuptools.packages.find]
include = ["argus*"]
```

### 1.2 Package Structure

Create all of these directories and `__init__.py` files. Every `__init__.py` starts empty except where noted.

```
argus/
├── __init__.py              # version = "0.1.0"
├── core/
│   ├── __init__.py
│   ├── config.py            # Config models + loader (Step 1)
│   ├── event_bus.py         # Event Bus (Step 2)
│   ├── events.py            # Event dataclasses (Step 2)
│   └── ids.py               # ULID utility (Step 3)
├── strategies/
│   └── __init__.py
├── data/
│   └── __init__.py
├── execution/
│   └── __init__.py
├── analytics/
│   ├── __init__.py
│   └── trade_logger.py      # Trade Logger (Step 3)
├── backtest/
│   └── __init__.py
├── notifications/
│   └── __init__.py
├── accounting/
│   └── __init__.py
├── api/
│   └── __init__.py
├── models/
│   ├── __init__.py
│   └── trading.py           # Shared data models (Step 3)
├── db/
│   ├── __init__.py
│   ├── manager.py           # DB connection manager (Step 3)
│   └── schema.sql           # Full SQL schema (Step 3)
config/
├── system.yaml
├── risk_limits.yaml
├── brokers.yaml
├── orchestrator.yaml
├── notifications.yaml
└── strategies/
    └── orb_breakout.yaml
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── fixtures/
│   ├── test_system.yaml
│   ├── test_risk_limits.yaml
│   └── test_brokers.yaml
├── core/
│   ├── __init__.py
│   ├── test_config.py       # Step 1
│   ├── test_event_bus.py    # Step 2
│   └── test_events.py       # Step 2
├── analytics/
│   ├── __init__.py
│   └── test_trade_logger.py # Step 3
├── db/
│   ├── __init__.py
│   └── test_manager.py      # Step 3
└── models/
    ├── __init__.py
    └── test_trading.py      # Step 3
```

### 1.3 Config Models (`argus/core/config.py`)

```python
"""Argus configuration system.

Loads configuration from YAML files and validates via Pydantic models.
All tunable parameters live in YAML config files, never hardcoded.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AccountType(str, Enum):
    """Brokerage account type."""
    MARGIN = "margin"
    CASH = "cash"


class DuplicateStockPolicy(str, Enum):
    """Policy when multiple strategies want the same stock."""
    PRIORITY_BY_WIN_RATE = "priority_by_win_rate"
    FIRST_SIGNAL = "first_signal"
    BLOCK_ALL = "block_all"


class LogLevel(str, Enum):
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


class RiskConfig(BaseModel):
    """Complete risk management configuration."""
    account: AccountRiskConfig = AccountRiskConfig()
    cross_strategy: CrossStrategyRiskConfig = CrossStrategyRiskConfig()
    pdt: PDTConfig = PDTConfig()


class BrokerConnectionConfig(BaseModel):
    """Configuration for a single broker connection."""
    enabled: bool = True
    paper_trading: bool = True
    base_url: str = ""
    data_feed: str = "iex"  # Alpaca-specific: 'iex' (free) or 'sip' (paid)


class BrokerConfig(BaseModel):
    """Broker routing and connection configuration."""
    primary: str = "alpaca"
    alpaca: BrokerConnectionConfig = BrokerConnectionConfig()


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
```

### 1.4 YAML Config Files

**`config/system.yaml`:**
```yaml
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
```

**`config/risk_limits.yaml`:**
```yaml
account:
  daily_loss_limit_pct: 0.03
  weekly_loss_limit_pct: 0.05
  cash_reserve_pct: 0.20
  max_concurrent_positions: 10
  emergency_shutdown_enabled: true

cross_strategy:
  max_single_stock_pct: 0.05
  max_single_sector_pct: 0.15
  duplicate_stock_policy: "priority_by_win_rate"

pdt:
  enabled: true
  account_type: "margin"
```

**`config/brokers.yaml`:**
```yaml
primary: "alpaca"
alpaca:
  enabled: true
  paper_trading: true
  base_url: "https://paper-api.alpaca.markets"
  data_feed: "iex"
```

**`config/orchestrator.yaml`:**
```yaml
allocation_method: "equal_weight"
max_allocation_pct: 0.40
min_allocation_pct: 0.10
cash_reserve_pct: 0.20
performance_lookback_days: 20
consecutive_loss_throttle: 5
suspension_sharpe_threshold: 0.0
suspension_drawdown_pct: 0.15
```

**`config/notifications.yaml`:**
```yaml
telegram:
  enabled: false
  settings: {}
discord:
  enabled: false
  settings: {}
email:
  enabled: false
  settings: {}
push:
  enabled: false
  settings: {}
```

**`config/strategies/orb_breakout.yaml`:**
```yaml
strategy_id: "strat_orb_breakout"
name: "ORB Breakout"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

risk_limits:
  max_loss_per_trade_pct: 0.01
  max_daily_loss_pct: 0.03
  max_consecutive_losses_pause: 5
  max_trades_per_day: 6
  max_concurrent_positions: 2

operating_window:
  earliest_entry: "09:45"
  latest_entry: "11:30"
  force_close: "15:50"
  active_days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

benchmarks:
  min_win_rate: 0.45
  min_avg_r_multiple: 0.6
  min_profit_factor: 1.3
  min_sharpe_ratio: 0.5
  max_drawdown_pct: 0.15

# Strategy-specific parameters (not validated by base StrategyConfig —
# will be validated by OrbBreakoutConfig which extends StrategyConfig)
orb_window_minutes: 15
stop_placement: "midpoint"
volume_threshold_rvol: 2.0
target_1_r: 1.0
target_2_r: 2.0
time_stop_minutes: 30
min_range_atr_ratio: 0.5
max_range_atr_ratio: 2.0
chase_protection_pct: 0.005
```

### 1.5 Test Fixtures

**`tests/fixtures/test_system.yaml`:**
```yaml
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "DEBUG"
heartbeat_interval_seconds: 10
data_dir: "/tmp/argus_test_data"
```

**`tests/fixtures/test_risk_limits.yaml`:**
```yaml
account:
  daily_loss_limit_pct: 0.03
  weekly_loss_limit_pct: 0.05
  cash_reserve_pct: 0.20
  max_concurrent_positions: 10
  emergency_shutdown_enabled: true

cross_strategy:
  max_single_stock_pct: 0.05
  max_single_sector_pct: 0.15
  duplicate_stock_policy: "priority_by_win_rate"

pdt:
  enabled: true
  account_type: "margin"
```

**`tests/fixtures/test_brokers.yaml`:**
```yaml
primary: "alpaca"
alpaca:
  enabled: true
  paper_trading: true
  base_url: "https://paper-api.alpaca.markets"
  data_feed: "iex"
```

### 1.6 Tests (`tests/core/test_config.py`)

```python
"""Tests for the Argus configuration system."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.core.config import (
    AccountType,
    ArgusConfig,
    StrategyConfig,
    SystemConfig,
    load_config,
    load_strategy_config,
    load_yaml_file,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestLoadYamlFile:
    """Tests for the YAML file loader."""

    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        """Valid YAML file is loaded correctly."""
        f = tmp_path / "test.yaml"
        f.write_text("key: value\nnested:\n  a: 1\n  b: 2\n")
        result = load_yaml_file(f)
        assert result == {"key": "value", "nested": {"a": 1, "b": 2}}

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_yaml_file(tmp_path / "nonexistent.yaml")

    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty YAML file returns empty dict, not None."""
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = load_yaml_file(f)
        assert result == {}

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML syntax raises yaml.YAMLError."""
        f = tmp_path / "bad.yaml"
        f.write_text("key: [invalid\n")
        with pytest.raises(yaml.YAMLError):
            load_yaml_file(f)


class TestArgusConfig:
    """Tests for the top-level ArgusConfig model."""

    def test_defaults_are_valid(self) -> None:
        """ArgusConfig can be created with all defaults."""
        config = ArgusConfig()
        assert config.system.timezone == "America/New_York"
        assert config.risk.account.daily_loss_limit_pct == 0.03
        assert config.broker.primary == "alpaca"

    def test_loads_from_config_dir(self) -> None:
        """load_config reads YAML files and returns validated config."""
        # This uses the real config/ directory
        config = load_config(Path("config"))
        assert config.system.timezone == "America/New_York"
        assert config.risk.pdt.account_type == AccountType.MARGIN

    def test_loads_from_test_fixtures(self, tmp_path: Path) -> None:
        """load_config works with a custom config directory."""
        # Copy test fixtures into a temp directory structure
        (tmp_path / "system.yaml").write_text(
            (FIXTURES_DIR / "test_system.yaml").read_text()
        )
        (tmp_path / "risk_limits.yaml").write_text(
            (FIXTURES_DIR / "test_risk_limits.yaml").read_text()
        )
        (tmp_path / "brokers.yaml").write_text(
            (FIXTURES_DIR / "test_brokers.yaml").read_text()
        )
        config = load_config(tmp_path)
        assert config.system.log_level.value == "DEBUG"

    def test_missing_config_dir_raises(self) -> None:
        """Missing config directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/path"))

    def test_missing_optional_files_use_defaults(self, tmp_path: Path) -> None:
        """Missing YAML files result in default values, not errors."""
        # Empty directory — all configs use defaults
        config = load_config(tmp_path)
        assert config.system.timezone == "America/New_York"
        assert config.risk.account.daily_loss_limit_pct == 0.03


class TestConfigValidation:
    """Tests for Pydantic validation on config values."""

    def test_invalid_timezone_rejected(self) -> None:
        """Timezone without / separator is rejected (unless UTC)."""
        with pytest.raises(ValidationError):
            SystemConfig(timezone="InvalidTimezone")

    def test_utc_timezone_accepted(self) -> None:
        """UTC is accepted as a valid timezone."""
        config = SystemConfig(timezone="UTC")
        assert config.timezone == "UTC"

    def test_daily_loss_limit_out_of_range(self) -> None:
        """Daily loss limit > 20% is rejected."""
        with pytest.raises(ValidationError):
            ArgusConfig(risk={"account": {"daily_loss_limit_pct": 0.25}})

    def test_negative_heartbeat_rejected(self) -> None:
        """Heartbeat interval must be >= 1."""
        with pytest.raises(ValidationError):
            SystemConfig(heartbeat_interval_seconds=0)


class TestStrategyConfig:
    """Tests for strategy-level configuration."""

    def test_loads_orb_config(self) -> None:
        """ORB strategy config loads and validates from YAML."""
        config = load_strategy_config(Path("config/strategies/orb_breakout.yaml"))
        assert config.strategy_id == "strat_orb_breakout"
        assert config.name == "ORB Breakout"
        assert config.risk_limits.max_trades_per_day == 6

    def test_strategy_config_defaults(self) -> None:
        """Strategy config works with minimal required fields."""
        config = StrategyConfig(strategy_id="test_strat", name="Test")
        assert config.version == "1.0.0"
        assert config.enabled is True
        assert config.risk_limits.max_loss_per_trade_pct == 0.01
```

### 1.7 Shared Test Fixtures (`tests/conftest.py`)

```python
"""Shared test fixtures for the Argus test suite."""

from pathlib import Path

import pytest

from argus.core.config import ArgusConfig, load_config


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def config() -> ArgusConfig:
    """Provide a default ArgusConfig loaded from real config files."""
    return load_config(Path("config"))


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR
```

### Step 1 Acceptance Criteria

- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `ruff check argus/ tests/` passes with no errors
- [ ] All `__init__.py` files exist for every package
- [ ] `load_config(Path("config"))` returns a valid `ArgusConfig`
- [ ] `load_strategy_config(Path("config/strategies/orb_breakout.yaml"))` returns a valid `StrategyConfig`
- [ ] All tests in `tests/core/test_config.py` pass
- [ ] Config validation catches invalid values (tested)
- [ ] Missing YAML files fall back to defaults (tested)

---

## Step 2: Event Bus + Event Definitions

### 2.1 Event Definitions (`argus/core/events.py`)

```python
"""Event definitions for the Argus event system.

All inter-component communication flows through typed events on the Event Bus.
Events are immutable dataclasses. The `sequence` field is assigned by the
Event Bus at publish time — never set it manually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Side(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    """Order type for broker submission."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class ExitReason(str, Enum):
    """Why a position was closed."""
    TARGET_1 = "target_1"
    TARGET_2 = "target_2"
    TARGET_3 = "target_3"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TIME_STOP = "time_stop"
    EOD_FLATTEN = "eod"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"
    EMERGENCY = "emergency"


class CircuitBreakerLevel(str, Enum):
    """Which level triggered the circuit breaker."""
    STRATEGY = "strategy"
    CROSS_STRATEGY = "cross_strategy"
    ACCOUNT = "account"


class SystemStatus(str, Enum):
    """Overall system health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    SAFE_MODE = "safe_mode"


# ---------------------------------------------------------------------------
# Base Event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Event:
    """Base event class. All events inherit from this.

    Attributes:
        sequence: Monotonic sequence number assigned by EventBus at publish time.
            Do not set this manually — pass 0 and the EventBus will overwrite it.
        timestamp: When the event was created (UTC).
    """
    sequence: int = field(default=0)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Market Data Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CandleEvent(Event):
    """A completed candle at a specific timeframe."""
    symbol: str = ""
    timeframe: str = ""      # "1s", "5s", "1m", "5m", "15m"
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0


@dataclass(frozen=True)
class TickEvent(Event):
    """A single price update (trade or quote)."""
    symbol: str = ""
    price: float = 0.0
    volume: int = 0


@dataclass(frozen=True)
class IndicatorEvent(Event):
    """A computed indicator value update."""
    symbol: str = ""
    indicator_name: str = ""  # "vwap", "atr_14", "rvol", "sma_20", etc.
    value: float = 0.0


# ---------------------------------------------------------------------------
# Scanner Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WatchlistItem:
    """A single stock on the scanner watchlist with metadata."""
    symbol: str = ""
    gap_pct: float = 0.0
    premarket_volume: int = 0
    float_shares: int = 0
    catalyst: str = ""


@dataclass(frozen=True)
class WatchlistEvent(Event):
    """Pre-market scanner results — the day's watchlist."""
    date: str = ""  # YYYY-MM-DD
    symbols: tuple[WatchlistItem, ...] = ()


# ---------------------------------------------------------------------------
# Strategy Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SignalEvent(Event):
    """A trade signal emitted by a strategy."""
    strategy_id: str = ""
    symbol: str = ""
    side: Side = Side.LONG
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_prices: tuple[float, ...] = ()
    share_count: int = 0
    rationale: str = ""


# ---------------------------------------------------------------------------
# Risk Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderApprovedEvent(Event):
    """Risk Manager approved a signal (possibly with modifications)."""
    signal: SignalEvent | None = None
    modifications: dict[str, Any] | None = None


@dataclass(frozen=True)
class OrderRejectedEvent(Event):
    """Risk Manager rejected a signal."""
    signal: SignalEvent | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Execution Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderSubmittedEvent(Event):
    """An order has been submitted to the broker."""
    order_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    side: Side = Side.LONG
    quantity: int = 0
    order_type: OrderType = OrderType.MARKET


@dataclass(frozen=True)
class OrderFilledEvent(Event):
    """An order has been filled (partially or fully)."""
    order_id: str = ""
    fill_price: float = 0.0
    fill_quantity: int = 0


@dataclass(frozen=True)
class OrderCancelledEvent(Event):
    """An order has been cancelled."""
    order_id: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Position Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionOpenedEvent(Event):
    """A new position has been opened."""
    position_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    entry_price: float = 0.0
    shares: int = 0
    stop_price: float = 0.0
    target_prices: tuple[float, ...] = ()


@dataclass(frozen=True)
class PositionUpdatedEvent(Event):
    """An existing position's state has changed."""
    position_id: str = ""
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    stop_updated_to: float | None = None


@dataclass(frozen=True)
class PositionClosedEvent(Event):
    """A position has been fully closed."""
    position_id: str = ""
    exit_price: float = 0.0
    realized_pnl: float = 0.0
    exit_reason: ExitReason = ExitReason.MANUAL
    hold_duration_seconds: int = 0


# ---------------------------------------------------------------------------
# System Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CircuitBreakerEvent(Event):
    """A circuit breaker has been triggered."""
    level: CircuitBreakerLevel = CircuitBreakerLevel.ACCOUNT
    reason: str = ""
    strategies_affected: tuple[str, ...] = ()


@dataclass(frozen=True)
class HeartbeatEvent(Event):
    """Periodic system health signal."""
    system_status: SystemStatus = SystemStatus.HEALTHY


@dataclass(frozen=True)
class RegimeChangeEvent(Event):
    """Market regime has changed."""
    old_regime: str = ""
    new_regime: str = ""
    indicators: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationUpdateEvent(Event):
    """Strategy capital allocation has changed."""
    strategy_id: str = ""
    new_allocation_pct: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class StrategyActivatedEvent(Event):
    """A strategy has been activated by the Orchestrator."""
    strategy_id: str = ""
    reason: str = ""


@dataclass(frozen=True)
class StrategySuspendedEvent(Event):
    """A strategy has been suspended by the Orchestrator."""
    strategy_id: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Approval Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ApprovalRequestedEvent(Event):
    """An action requires human approval."""
    action_id: str = ""
    action_type: str = ""
    description: str = ""
    risk_level: str = "medium"  # "low", "medium", "high"


@dataclass(frozen=True)
class ApprovalGrantedEvent(Event):
    """Human approved an action."""
    action_id: str = ""


@dataclass(frozen=True)
class ApprovalDeniedEvent(Event):
    """Human denied an action."""
    action_id: str = ""
    reason: str = ""
```

### 2.2 Event Bus (`argus/core/event_bus.py`)

```python
"""Argus Event Bus — in-process async pub/sub.

The Event Bus is the communication backbone of the Argus system. Components
publish typed events and subscribe to event types. FIFO delivery per subscriber.
No global ordering guarantees. No priority queues.

Every event is assigned a monotonic sequence number at publish time for
debugging and deterministic replay.

Usage:
    bus = EventBus()
    
    async def my_handler(event: CandleEvent) -> None:
        print(f"Got candle: {event.symbol}")
    
    bus.subscribe(CandleEvent, my_handler)
    await bus.publish(CandleEvent(symbol="AAPL", ...))
    await bus.drain()  # Wait for all handlers to complete
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import replace
from typing import Any, Callable, Coroutine, Type, TypeVar

from argus.core.events import Event

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Event)

# Type alias for an async event handler
EventHandler = Callable[[Any], Coroutine[Any, Any, None]]


class EventBus:
    """In-process async event bus with FIFO delivery per subscriber.

    Attributes:
        _subscribers: Mapping of event type to list of handler functions.
        _sequence: Monotonic counter for event sequence numbers.
        _pending: Set of pending handler tasks for drain().
    """

    def __init__(self) -> None:
        self._subscribers: dict[Type[Event], list[EventHandler]] = defaultdict(list)
        self._sequence: int = 0
        self._pending: set[asyncio.Task[None]] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    def subscribe(self, event_type: Type[T], handler: EventHandler) -> None:
        """Register a handler for an event type.

        The handler will be called with every event of this type (or subtype)
        published to the bus. Handlers are called in subscription order (FIFO).

        Args:
            event_type: The event class to subscribe to.
            handler: Async callable that takes an event instance.
        """
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__qualname__, event_type.__name__)

    def unsubscribe(self, event_type: Type[T], handler: EventHandler) -> None:
        """Remove a handler for an event type.

        Args:
            event_type: The event class to unsubscribe from.
            handler: The handler to remove.

        Raises:
            ValueError: If the handler is not subscribed to this event type.
        """
        try:
            self._subscribers[event_type].remove(handler)
            logger.debug("Unsubscribed %s from %s", handler.__qualname__, event_type.__name__)
        except ValueError:
            raise ValueError(
                f"Handler {handler.__qualname__} is not subscribed to {event_type.__name__}"
            )

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of its type.

        Assigns a monotonic sequence number to the event before delivery.
        Handlers are dispatched as async tasks and run concurrently.

        Args:
            event: The event to publish.
        """
        async with self._lock:
            self._sequence += 1
            seq = self._sequence

        # Replace the sequence number on the (frozen) event
        stamped_event = replace(event, sequence=seq)

        event_type = type(stamped_event)
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(
                "No subscribers for %s (seq=%d)", event_type.__name__, seq
            )
            return

        for handler in handlers:
            task = asyncio.create_task(
                self._safe_call(handler, stamped_event),
                name=f"{event_type.__name__}->{handler.__qualname__}",
            )
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Call a handler with error isolation.

        If a handler raises, the exception is logged but does not propagate.
        One bad handler must not break other subscribers.
        """
        try:
            await handler(event)
        except Exception:
            logger.exception(
                "Handler %s raised on %s (seq=%d)",
                handler.__qualname__,
                type(event).__name__,
                event.sequence,
            )

    async def drain(self) -> None:
        """Wait for all pending handler tasks to complete.

        Useful in tests and shutdown sequences to ensure all events
        have been fully processed before proceeding.
        """
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)

    def subscriber_count(self, event_type: Type[Event]) -> int:
        """Return the number of subscribers for an event type.

        Args:
            event_type: The event class to check.

        Returns:
            Number of registered handlers.
        """
        return len(self._subscribers.get(event_type, []))

    def reset(self) -> None:
        """Clear all subscriptions and reset sequence counter.

        Intended for testing only. Do not call during live trading.
        """
        self._subscribers.clear()
        self._sequence = 0
        self._pending.clear()
```

### 2.3 Event Bus Tests (`tests/core/test_event_bus.py`)

```python
"""Tests for the Argus Event Bus."""

import asyncio

import pytest

from argus.core.event_bus import EventBus
from argus.core.events import (
    CandleEvent,
    Event,
    HeartbeatEvent,
    SignalEvent,
    Side,
    TickEvent,
)


@pytest.fixture
def bus() -> EventBus:
    """Fresh EventBus for each test."""
    return EventBus()


class TestSubscribePublish:
    """Core subscribe/publish behavior."""

    async def test_subscriber_receives_event(self, bus: EventBus) -> None:
        """A subscriber receives a published event."""
        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="AAPL", close=150.0))
        await bus.drain()

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].close == 150.0

    async def test_multiple_subscribers_all_receive(self, bus: EventBus) -> None:
        """Multiple subscribers to the same event type all receive it."""
        received_a: list[Event] = []
        received_b: list[Event] = []

        async def handler_a(event: CandleEvent) -> None:
            received_a.append(event)

        async def handler_b(event: CandleEvent) -> None:
            received_b.append(event)

        bus.subscribe(CandleEvent, handler_a)
        bus.subscribe(CandleEvent, handler_b)
        await bus.publish(CandleEvent(symbol="MSFT"))
        await bus.drain()

        assert len(received_a) == 1
        assert len(received_b) == 1

    async def test_subscriber_only_receives_subscribed_type(self, bus: EventBus) -> None:
        """A subscriber to CandleEvent does not receive TickEvent."""
        received: list[Event] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        await bus.drain()

        assert len(received) == 0

    async def test_no_subscribers_no_error(self, bus: EventBus) -> None:
        """Publishing with no subscribers does not raise."""
        await bus.publish(CandleEvent(symbol="AAPL"))
        await bus.drain()  # Should not hang or raise


class TestSequenceNumbers:
    """Monotonic sequence numbering."""

    async def test_sequence_numbers_are_monotonic(self, bus: EventBus) -> None:
        """Events receive sequential, increasing sequence numbers."""
        received: list[Event] = []

        async def handler(event: HeartbeatEvent) -> None:
            received.append(event)

        bus.subscribe(HeartbeatEvent, handler)

        for _ in range(5):
            await bus.publish(HeartbeatEvent())
        await bus.drain()

        sequences = [e.sequence for e in received]
        assert sequences == [1, 2, 3, 4, 5]

    async def test_sequence_numbers_span_event_types(self, bus: EventBus) -> None:
        """Sequence numbers are global, not per-event-type."""
        all_events: list[Event] = []

        async def candle_handler(event: CandleEvent) -> None:
            all_events.append(event)

        async def tick_handler(event: TickEvent) -> None:
            all_events.append(event)

        bus.subscribe(CandleEvent, candle_handler)
        bus.subscribe(TickEvent, tick_handler)

        await bus.publish(CandleEvent(symbol="A"))
        await bus.publish(TickEvent(symbol="B"))
        await bus.publish(CandleEvent(symbol="C"))
        await bus.drain()

        sequences = sorted([e.sequence for e in all_events])
        assert sequences == [1, 2, 3]

    async def test_original_event_sequence_not_mutated(self, bus: EventBus) -> None:
        """The original event object is not mutated (frozen dataclass)."""
        original = CandleEvent(symbol="AAPL")
        assert original.sequence == 0  # Default

        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(original)
        await bus.drain()

        assert original.sequence == 0  # Unchanged
        assert received[0].sequence == 1  # Stamped copy


class TestUnsubscribe:
    """Unsubscribe behavior."""

    async def test_unsubscribed_handler_stops_receiving(self, bus: EventBus) -> None:
        """After unsubscribing, handler no longer receives events."""
        received: list[Event] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="A"))
        await bus.drain()
        assert len(received) == 1

        bus.unsubscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="B"))
        await bus.drain()
        assert len(received) == 1  # No new events

    async def test_unsubscribe_unknown_handler_raises(self, bus: EventBus) -> None:
        """Unsubscribing a handler that was never subscribed raises ValueError."""
        async def handler(event: CandleEvent) -> None:
            pass

        with pytest.raises(ValueError):
            bus.unsubscribe(CandleEvent, handler)


class TestErrorIsolation:
    """Handler errors are isolated."""

    async def test_failing_handler_does_not_break_others(self, bus: EventBus) -> None:
        """If one handler raises, other handlers still receive the event."""
        received: list[Event] = []

        async def bad_handler(event: CandleEvent) -> None:
            raise RuntimeError("I broke")

        async def good_handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, bad_handler)
        bus.subscribe(CandleEvent, good_handler)
        await bus.publish(CandleEvent(symbol="AAPL"))
        await bus.drain()

        assert len(received) == 1  # good_handler still got it


class TestUtilities:
    """Helper methods."""

    async def test_subscriber_count(self, bus: EventBus) -> None:
        """subscriber_count returns the correct number."""
        assert bus.subscriber_count(CandleEvent) == 0

        async def handler(e: CandleEvent) -> None:
            pass

        bus.subscribe(CandleEvent, handler)
        assert bus.subscriber_count(CandleEvent) == 1

    async def test_reset_clears_everything(self, bus: EventBus) -> None:
        """reset() clears subscribers and resets sequence counter."""
        async def handler(e: CandleEvent) -> None:
            pass

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent())
        await bus.drain()

        bus.reset()
        assert bus.subscriber_count(CandleEvent) == 0

        # Sequence counter resets too
        received: list[Event] = []

        async def new_handler(e: HeartbeatEvent) -> None:
            received.append(e)

        bus.subscribe(HeartbeatEvent, new_handler)
        await bus.publish(HeartbeatEvent())
        await bus.drain()
        assert received[0].sequence == 1  # Reset to 1, not continuing
```

### 2.4 Event Tests (`tests/core/test_events.py`)

```python
"""Tests for event dataclass definitions."""

from argus.core.events import (
    CandleEvent,
    Event,
    ExitReason,
    PositionClosedEvent,
    Side,
    SignalEvent,
    WatchlistEvent,
    WatchlistItem,
)


class TestEventDataclasses:
    """Verify event dataclass behavior."""

    def test_base_event_has_defaults(self) -> None:
        """Base Event has sequence=0 and auto-generated timestamp."""
        event = Event()
        assert event.sequence == 0
        assert event.timestamp is not None

    def test_candle_event_fields(self) -> None:
        """CandleEvent stores all OHLCV fields."""
        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=150.0,
            high=151.0,
            low=149.5,
            close=150.5,
            volume=10000,
        )
        assert candle.symbol == "AAPL"
        assert candle.volume == 10000

    def test_signal_event_with_targets(self) -> None:
        """SignalEvent stores target prices as a tuple."""
        signal = SignalEvent(
            strategy_id="strat_orb",
            symbol="TSLA",
            side=Side.LONG,
            entry_price=200.0,
            stop_price=198.0,
            target_prices=(202.0, 204.0),
            share_count=100,
            rationale="ORB breakout above range high",
        )
        assert len(signal.target_prices) == 2
        assert signal.side == Side.LONG

    def test_events_are_frozen(self) -> None:
        """Events are immutable (frozen dataclasses)."""
        candle = CandleEvent(symbol="AAPL")
        with __import__("pytest").raises(AttributeError):
            candle.symbol = "MSFT"  # type: ignore[misc]

    def test_watchlist_event_with_items(self) -> None:
        """WatchlistEvent contains WatchlistItem tuples."""
        items = (
            WatchlistItem(symbol="AAPL", gap_pct=3.5, premarket_volume=500000),
            WatchlistItem(symbol="TSLA", gap_pct=5.2, premarket_volume=800000),
        )
        event = WatchlistEvent(date="2026-02-15", symbols=items)
        assert len(event.symbols) == 2
        assert event.symbols[0].symbol == "AAPL"

    def test_exit_reason_enum(self) -> None:
        """ExitReason enum values are strings."""
        event = PositionClosedEvent(
            position_id="test",
            exit_reason=ExitReason.STOP_LOSS,
        )
        assert event.exit_reason.value == "stop_loss"
```

### Step 2 Acceptance Criteria

- [ ] All event dataclasses are frozen and have correct default values
- [ ] EventBus delivers events to subscribers (FIFO)
- [ ] Sequence numbers are monotonic and global
- [ ] Unsubscribe works correctly
- [ ] Handler errors are isolated (one bad handler doesn't break others)
- [ ] `bus.drain()` waits for all pending handlers
- [ ] `bus.reset()` clears state
- [ ] All tests in `test_event_bus.py` and `test_events.py` pass

---

## Step 3: Data Models + Database + Trade Logger

### 3.1 ULID Utility (`argus/core/ids.py`)

```python
"""ULID-based ID generation for Argus.

All database primary keys use ULIDs — globally unique, time-sortable,
26 characters. Wrapping in a utility centralizes the dependency.
"""

from ulid import ULID


def generate_id() -> str:
    """Generate a new ULID as a 26-character string.

    Returns:
        A new ULID string, e.g. '01HQJY7Z4K0G5P3VXJK5MZQN9T'.
    """
    return str(ULID())
```

### 3.2 Shared Data Models (`argus/models/trading.py`)

```python
"""Shared data models used across the Argus system.

These are the canonical representations of trading objects. They are
Pydantic models for validation and serialization. Components that
need to exchange trading data use these types.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from argus.core.ids import generate_id


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetClass(str, Enum):
    """Supported asset classes."""
    US_STOCKS = "us_stocks"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"


class OrderSide(str, Enum):
    """Order direction."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type for broker submission."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Current state of an order."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(str, Enum):
    """Current state of a position."""
    OPEN = "open"
    CLOSED = "closed"


class PipelineStage(str, Enum):
    """Strategy incubator pipeline stages."""
    CONCEPT = "concept"
    EXPLORATION = "exploration"
    VALIDATION = "validation"
    ECOSYSTEM_REPLAY = "ecosystem_replay"
    PAPER = "paper"
    LIVE_MIN = "live_min"
    LIVE_FULL = "live_full"
    MONITORING = "monitoring"
    SUSPENDED = "suspended"
    RETIRED = "retired"


# ---------------------------------------------------------------------------
# Order Models
# ---------------------------------------------------------------------------

class Order(BaseModel):
    """An order to be submitted to a broker."""
    id: str = Field(default_factory=generate_id)
    strategy_id: str
    symbol: str
    asset_class: AssetClass = AssetClass.US_STOCKS
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: int = Field(ge=1)
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: str = "day"  # 'day', 'gtc', 'ioc', 'fok'
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderResult(BaseModel):
    """Result from submitting an order to the broker."""
    order_id: str
    broker_order_id: str = ""
    status: OrderStatus = OrderStatus.SUBMITTED
    filled_quantity: int = 0
    filled_avg_price: float = 0.0
    message: str = ""


class BracketOrderResult(BaseModel):
    """Result from submitting a bracket order (entry + stop + targets)."""
    entry: OrderResult
    stop: OrderResult
    targets: list[OrderResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Position Model
# ---------------------------------------------------------------------------

class Position(BaseModel):
    """A tracked trading position."""
    id: str = Field(default_factory=generate_id)
    strategy_id: str
    symbol: str
    asset_class: AssetClass = AssetClass.US_STOCKS
    side: str = "long"  # "long" or "short"
    entry_price: float
    entry_time: datetime
    shares: int = Field(ge=1)
    current_price: float = 0.0
    stop_price: float
    target_prices: list[float] = Field(default_factory=list)
    status: PositionStatus = PositionStatus.OPEN
    exit_price: float | None = None
    exit_time: datetime | None = None
    exit_reason: str | None = None
    realized_pnl: float | None = None
    unrealized_pnl: float = 0.0

    @property
    def r_multiple(self) -> float | None:
        """Calculate R-multiple if position is closed.

        R = risk per share = abs(entry_price - stop_price)
        R-multiple = pnl_per_share / R
        """
        if self.realized_pnl is None:
            return None
        risk_per_share = abs(self.entry_price - self.stop_price)
        if risk_per_share == 0:
            return None
        pnl_per_share = self.realized_pnl / self.shares
        return pnl_per_share / risk_per_share


# ---------------------------------------------------------------------------
# Account Model
# ---------------------------------------------------------------------------

class AccountInfo(BaseModel):
    """Broker account information."""
    account_id: str = ""
    equity: float = 0.0
    cash: float = 0.0
    buying_power: float = 0.0
    portfolio_value: float = 0.0
    day_trade_count: int = 0
    pattern_day_trader: bool = False
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Trade Record (for database persistence)
# ---------------------------------------------------------------------------

class TradeRecord(BaseModel):
    """A completed trade record for database storage.

    This represents the full lifecycle of a trade from entry to exit.
    Created by the Trade Logger when a position is closed.
    """
    id: str = Field(default_factory=generate_id)
    strategy_id: str
    strategy_version: str = "1.0.0"
    symbol: str
    asset_class: str = "us_stocks"
    side: str = "long"
    entry_price: float
    entry_time: datetime
    exit_price: float
    exit_time: datetime
    shares: int = Field(ge=1)
    stop_price: float
    target_prices: list[float] = Field(default_factory=list)
    exit_reason: str
    pnl_dollars: float
    pnl_r_multiple: float | None = None
    commission: float = 0.0
    slippage: float = 0.0
    hold_duration_seconds: int = 0
    market_regime: str = ""
    spy_price_at_entry: float = 0.0
    vix_at_entry: float = 0.0
    rvol_at_entry: float = 0.0
    notes: str = ""
    # Fields for tracking Risk Manager modifications
    original_share_count: int | None = None
    modifications: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DailyPerformance(BaseModel):
    """Daily performance record for a single strategy."""
    date: str  # YYYY-MM-DD
    strategy_id: str
    trades_taken: int = 0
    wins: int = 0
    losses: int = 0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_r_multiple: float | None = None
    allocated_capital: float = 0.0
    market_regime: str = ""
    circuit_breaker_triggered: bool = False


class AccountSnapshot(BaseModel):
    """End-of-day account snapshot."""
    date: str  # YYYY-MM-DD
    total_equity: float
    cash_balance: float
    deployed_capital: float
    total_pnl: float
    active_strategies: int = 0
    total_trades: int = 0
    market_regime: str = ""
    base_capital: float = 0.0
    growth_pool: float = 0.0
```

### 3.3 Database Schema (`argus/db/schema.sql`)

```sql
-- Argus Database Schema
-- SQLite with WAL mode for concurrent read/write
-- All id columns use ULIDs (26-char, time-sortable)

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'us_stocks',
    side TEXT NOT NULL DEFAULT 'long',
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,
    exit_price REAL,
    exit_time TEXT,
    shares INTEGER NOT NULL,
    stop_price REAL NOT NULL,
    target_prices TEXT,
    exit_reason TEXT,
    pnl_dollars REAL,
    pnl_r_multiple REAL,
    commission REAL DEFAULT 0,
    slippage REAL DEFAULT 0,
    hold_duration_seconds INTEGER,
    market_regime TEXT DEFAULT '',
    spy_price_at_entry REAL DEFAULT 0,
    vix_at_entry REAL DEFAULT 0,
    rvol_at_entry REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    original_share_count INTEGER,
    modifications TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_trades_exit_reason ON trades(exit_reason);

CREATE TABLE IF NOT EXISTS strategy_daily_performance (
    date TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    trades_taken INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    gross_pnl REAL DEFAULT 0,
    net_pnl REAL DEFAULT 0,
    largest_win REAL DEFAULT 0,
    largest_loss REAL DEFAULT 0,
    avg_r_multiple REAL,
    allocated_capital REAL DEFAULT 0,
    market_regime TEXT DEFAULT '',
    circuit_breaker_triggered BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (date, strategy_id)
);

CREATE TABLE IF NOT EXISTS account_daily_snapshot (
    date TEXT PRIMARY KEY,
    total_equity REAL NOT NULL,
    cash_balance REAL NOT NULL,
    deployed_capital REAL NOT NULL,
    total_pnl REAL NOT NULL,
    active_strategies INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    market_regime TEXT DEFAULT '',
    base_capital REAL DEFAULT 0,
    growth_pool REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orchestrator_decisions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    strategy_id TEXT,
    details TEXT,
    rationale TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_orch_decisions_date ON orchestrator_decisions(date);

CREATE TABLE IF NOT EXISTS approval_log (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'medium',
    proposed_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    proposed_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_log(status);

CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    entry_type TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'user',
    linked_strategy_id TEXT,
    linked_trade_ids TEXT,
    linked_date_range TEXT,
    tags TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_journal_author ON journal_entries(author);

CREATE TABLE IF NOT EXISTS system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    component TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'healthy',
    latency_ms REAL,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_health_component ON system_health(component);
CREATE INDEX IF NOT EXISTS idx_health_timestamp ON system_health(timestamp);
```

### 3.4 Database Manager (`argus/db/manager.py`)

```python
"""Database connection manager for Argus.

Manages SQLite connections via aiosqlite. Handles schema initialization,
connection pooling (single connection for SQLite), and cleanup.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Path to the schema file, relative to this module
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class DatabaseManager:
    """Async SQLite database manager.

    Usage:
        db = DatabaseManager("/path/to/argus.db")
        await db.initialize()
        # ... use db.connection for queries ...
        await db.close()

    Or as an async context manager:
        async with DatabaseManager("/path/to/argus.db") as db:
            await db.execute("SELECT ...")

    Attributes:
        db_path: Path to the SQLite database file.
        connection: The aiosqlite connection (available after initialize()).
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the database connection and apply the schema.

        Creates the database file if it doesn't exist. Applies all
        CREATE TABLE IF NOT EXISTS statements from schema.sql.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(str(self.db_path))
        self.connection.row_factory = aiosqlite.Row

        # Enable WAL mode and foreign keys
        await self.connection.execute("PRAGMA journal_mode = WAL")
        await self.connection.execute("PRAGMA foreign_keys = ON")

        # Apply schema
        schema_sql = SCHEMA_PATH.read_text()
        await self.connection.executescript(schema_sql)
        await self.connection.commit()

        logger.info("Database initialized at %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a SQL statement.

        Args:
            sql: SQL statement with ? placeholders.
            params: Parameter tuple for the statement.

        Returns:
            The cursor from the execution.

        Raises:
            RuntimeError: If the database is not initialized.
        """
        if not self.connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        cursor = await self.connection.execute(sql, params)
        return cursor

    async def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """Execute a SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement with ? placeholders.
            params_list: List of parameter tuples.

        Raises:
            RuntimeError: If the database is not initialized.
        """
        if not self.connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        await self.connection.executemany(sql, params_list)

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute a query and return a single row as a dict.

        Args:
            sql: SQL query with ? placeholders.
            params: Parameter tuple for the query.

        Returns:
            Row as a dict, or None if no results.
        """
        if not self.connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        cursor = await self.connection.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a query and return all rows as dicts.

        Args:
            sql: SQL query with ? placeholders.
            params: Parameter tuple for the query.

        Returns:
            List of rows as dicts.
        """
        if not self.connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        cursor = await self.connection.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self.connection:
            await self.connection.commit()

    async def __aenter__(self) -> DatabaseManager:
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
```

### 3.5 Trade Logger (`argus/analytics/trade_logger.py`)

```python
"""Trade Logger — persistent trade recording and querying.

The Trade Logger is the system's memory. Every trade, every daily performance
snapshot, and every account snapshot is recorded here. It is the sole interface
for trade persistence — other components read and write through this module.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from argus.db.manager import DatabaseManager
from argus.models.trading import (
    AccountSnapshot,
    DailyPerformance,
    TradeRecord,
)

logger = logging.getLogger(__name__)


class TradeLogger:
    """Async trade logging and querying interface.

    All database writes go through this class. It owns the DatabaseManager
    and provides typed query methods for common access patterns.

    Usage:
        db = DatabaseManager("argus.db")
        await db.initialize()
        trade_logger = TradeLogger(db)
        await trade_logger.log_trade(trade_record)
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Trade Recording
    # ------------------------------------------------------------------

    async def log_trade(self, trade: TradeRecord) -> str:
        """Record a completed trade to the database.

        Args:
            trade: The trade record to persist.

        Returns:
            The trade ID.
        """
        await self._db.execute(
            """INSERT INTO trades (
                id, strategy_id, strategy_version, symbol, asset_class, side,
                entry_price, entry_time, exit_price, exit_time, shares,
                stop_price, target_prices, exit_reason, pnl_dollars,
                pnl_r_multiple, commission, slippage, hold_duration_seconds,
                market_regime, spy_price_at_entry, vix_at_entry, rvol_at_entry,
                notes, original_share_count, modifications
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade.id,
                trade.strategy_id,
                trade.strategy_version,
                trade.symbol,
                trade.asset_class,
                trade.side,
                trade.entry_price,
                trade.entry_time.isoformat(),
                trade.exit_price,
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.shares,
                trade.stop_price,
                json.dumps(trade.target_prices),
                trade.exit_reason,
                trade.pnl_dollars,
                trade.pnl_r_multiple,
                trade.commission,
                trade.slippage,
                trade.hold_duration_seconds,
                trade.market_regime,
                trade.spy_price_at_entry,
                trade.vix_at_entry,
                trade.rvol_at_entry,
                trade.notes,
                trade.original_share_count,
                json.dumps(trade.modifications) if trade.modifications else None,
            ),
        )
        await self._db.commit()
        logger.info("Trade logged: %s %s %s P&L=%.2f", trade.id, trade.symbol, trade.side, trade.pnl_dollars)
        return trade.id

    async def get_trade(self, trade_id: str) -> TradeRecord | None:
        """Retrieve a single trade by ID.

        Args:
            trade_id: The ULID of the trade.

        Returns:
            TradeRecord if found, None otherwise.
        """
        row = await self._db.fetch_one("SELECT * FROM trades WHERE id = ?", (trade_id,))
        if row is None:
            return None
        return self._row_to_trade(row)

    async def get_trades_by_strategy(
        self, strategy_id: str, limit: int = 100
    ) -> list[TradeRecord]:
        """Retrieve recent trades for a specific strategy.

        Args:
            strategy_id: Strategy identifier.
            limit: Maximum number of trades to return.

        Returns:
            List of TradeRecords, most recent first.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM trades WHERE strategy_id = ? ORDER BY id DESC LIMIT ?",
            (strategy_id, limit),
        )
        return [self._row_to_trade(row) for row in rows]

    async def get_trades_by_date(self, date: str) -> list[TradeRecord]:
        """Retrieve all trades for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            List of TradeRecords for that date.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM trades WHERE entry_time LIKE ? ORDER BY id",
            (f"{date}%",),
        )
        return [self._row_to_trade(row) for row in rows]

    async def get_trades_today(self, strategy_id: str | None = None) -> list[TradeRecord]:
        """Retrieve all trades from today.

        Args:
            strategy_id: Optional filter by strategy.

        Returns:
            List of today's TradeRecords.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if strategy_id:
            rows = await self._db.fetch_all(
                "SELECT * FROM trades WHERE entry_time LIKE ? AND strategy_id = ? ORDER BY id",
                (f"{today}%", strategy_id),
            )
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM trades WHERE entry_time LIKE ? ORDER BY id",
                (f"{today}%",),
            )
        return [self._row_to_trade(row) for row in rows]

    async def count_trades_today(self, strategy_id: str | None = None) -> int:
        """Count trades taken today.

        Args:
            strategy_id: Optional filter by strategy.

        Returns:
            Number of trades today.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if strategy_id:
            row = await self._db.fetch_one(
                "SELECT COUNT(*) as cnt FROM trades WHERE entry_time LIKE ? AND strategy_id = ?",
                (f"{today}%", strategy_id),
            )
        else:
            row = await self._db.fetch_one(
                "SELECT COUNT(*) as cnt FROM trades WHERE entry_time LIKE ?",
                (f"{today}%",),
            )
        return row["cnt"] if row else 0

    async def get_daily_pnl(self, strategy_id: str | None = None) -> float:
        """Get total P&L for today.

        Args:
            strategy_id: Optional filter by strategy.

        Returns:
            Sum of pnl_dollars for today's trades.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if strategy_id:
            row = await self._db.fetch_one(
                "SELECT COALESCE(SUM(pnl_dollars), 0) as total FROM trades WHERE entry_time LIKE ? AND strategy_id = ?",
                (f"{today}%", strategy_id),
            )
        else:
            row = await self._db.fetch_one(
                "SELECT COALESCE(SUM(pnl_dollars), 0) as total FROM trades WHERE entry_time LIKE ?",
                (f"{today}%",),
            )
        return row["total"] if row else 0.0

    # ------------------------------------------------------------------
    # Daily Performance
    # ------------------------------------------------------------------

    async def save_daily_performance(self, perf: DailyPerformance) -> None:
        """Save or update a daily performance record.

        Uses INSERT OR REPLACE to handle both new and updated records.

        Args:
            perf: The daily performance record.
        """
        await self._db.execute(
            """INSERT OR REPLACE INTO strategy_daily_performance (
                date, strategy_id, trades_taken, wins, losses,
                gross_pnl, net_pnl, largest_win, largest_loss,
                avg_r_multiple, allocated_capital, market_regime,
                circuit_breaker_triggered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                perf.date,
                perf.strategy_id,
                perf.trades_taken,
                perf.wins,
                perf.losses,
                perf.gross_pnl,
                perf.net_pnl,
                perf.largest_win,
                perf.largest_loss,
                perf.avg_r_multiple,
                perf.allocated_capital,
                perf.market_regime,
                perf.circuit_breaker_triggered,
            ),
        )
        await self._db.commit()

    async def get_daily_performance(
        self, strategy_id: str, date: str
    ) -> DailyPerformance | None:
        """Retrieve a daily performance record.

        Args:
            strategy_id: Strategy identifier.
            date: Date in YYYY-MM-DD format.

        Returns:
            DailyPerformance if found, None otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM strategy_daily_performance WHERE strategy_id = ? AND date = ?",
            (strategy_id, date),
        )
        if row is None:
            return None
        return DailyPerformance(**row)

    async def get_performance_history(
        self, strategy_id: str, days: int = 20
    ) -> list[DailyPerformance]:
        """Retrieve recent daily performance records for a strategy.

        Args:
            strategy_id: Strategy identifier.
            days: Number of most recent days to retrieve.

        Returns:
            List of DailyPerformance records, most recent first.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM strategy_daily_performance WHERE strategy_id = ? ORDER BY date DESC LIMIT ?",
            (strategy_id, days),
        )
        return [DailyPerformance(**row) for row in rows]

    # ------------------------------------------------------------------
    # Account Snapshots
    # ------------------------------------------------------------------

    async def save_account_snapshot(self, snapshot: AccountSnapshot) -> None:
        """Save or update an account daily snapshot.

        Args:
            snapshot: The account snapshot to persist.
        """
        await self._db.execute(
            """INSERT OR REPLACE INTO account_daily_snapshot (
                date, total_equity, cash_balance, deployed_capital,
                total_pnl, active_strategies, total_trades,
                market_regime, base_capital, growth_pool
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                snapshot.date,
                snapshot.total_equity,
                snapshot.cash_balance,
                snapshot.deployed_capital,
                snapshot.total_pnl,
                snapshot.active_strategies,
                snapshot.total_trades,
                snapshot.market_regime,
                snapshot.base_capital,
                snapshot.growth_pool,
            ),
        )
        await self._db.commit()

    async def get_account_snapshot(self, date: str) -> AccountSnapshot | None:
        """Retrieve an account snapshot for a date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            AccountSnapshot if found, None otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM account_daily_snapshot WHERE date = ?",
            (date,),
        )
        if row is None:
            return None
        return AccountSnapshot(**row)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_trade(row: dict) -> TradeRecord:
        """Convert a database row dict to a TradeRecord.

        Handles JSON deserialization for list/dict fields and datetime parsing.
        """
        return TradeRecord(
            id=row["id"],
            strategy_id=row["strategy_id"],
            strategy_version=row["strategy_version"],
            symbol=row["symbol"],
            asset_class=row["asset_class"],
            side=row["side"],
            entry_price=row["entry_price"],
            entry_time=datetime.fromisoformat(row["entry_time"]),
            exit_price=row["exit_price"],
            exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
            shares=row["shares"],
            stop_price=row["stop_price"],
            target_prices=json.loads(row["target_prices"]) if row["target_prices"] else [],
            exit_reason=row["exit_reason"] or "",
            pnl_dollars=row["pnl_dollars"] or 0.0,
            pnl_r_multiple=row["pnl_r_multiple"],
            commission=row["commission"] or 0.0,
            slippage=row["slippage"] or 0.0,
            hold_duration_seconds=row["hold_duration_seconds"] or 0,
            market_regime=row["market_regime"] or "",
            spy_price_at_entry=row["spy_price_at_entry"] or 0.0,
            vix_at_entry=row["vix_at_entry"] or 0.0,
            rvol_at_entry=row["rvol_at_entry"] or 0.0,
            notes=row["notes"] or "",
            original_share_count=row["original_share_count"],
            modifications=json.loads(row["modifications"]) if row["modifications"] else None,
        )
```

### 3.6 Tests — Database Manager (`tests/db/test_manager.py`)

```python
"""Tests for the database manager."""

import pytest

from argus.db.manager import DatabaseManager


class TestDatabaseManager:
    """Tests for DatabaseManager lifecycle and queries."""

    async def test_initialize_creates_tables(self, tmp_path) -> None:
        """Schema is applied on initialization."""
        async with DatabaseManager(tmp_path / "test.db") as db:
            # Verify tables exist
            rows = await db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_names = {row["name"] for row in rows}
            assert "trades" in table_names
            assert "strategy_daily_performance" in table_names
            assert "account_daily_snapshot" in table_names
            assert "orchestrator_decisions" in table_names
            assert "approval_log" in table_names
            assert "journal_entries" in table_names
            assert "system_health" in table_names

    async def test_execute_and_fetch(self, tmp_path) -> None:
        """Basic execute and fetch operations work."""
        async with DatabaseManager(tmp_path / "test.db") as db:
            await db.execute(
                "INSERT INTO system_health (timestamp, component, status) VALUES (?, ?, ?)",
                ("2026-02-15T10:00:00Z", "event_bus", "healthy"),
            )
            await db.commit()

            row = await db.fetch_one(
                "SELECT * FROM system_health WHERE component = ?", ("event_bus",)
            )
            assert row is not None
            assert row["status"] == "healthy"

    async def test_fetch_all_returns_list(self, tmp_path) -> None:
        """fetch_all returns a list of dicts."""
        async with DatabaseManager(tmp_path / "test.db") as db:
            for i in range(3):
                await db.execute(
                    "INSERT INTO system_health (timestamp, component, status) VALUES (?, ?, ?)",
                    (f"2026-02-15T10:0{i}:00Z", f"comp_{i}", "healthy"),
                )
            await db.commit()

            rows = await db.fetch_all("SELECT * FROM system_health")
            assert len(rows) == 3

    async def test_fetch_one_returns_none_when_empty(self, tmp_path) -> None:
        """fetch_one returns None when no rows match."""
        async with DatabaseManager(tmp_path / "test.db") as db:
            row = await db.fetch_one("SELECT * FROM trades WHERE id = ?", ("nonexistent",))
            assert row is None

    async def test_operations_before_initialize_raise(self) -> None:
        """Operations on uninitialized DB raise RuntimeError."""
        db = DatabaseManager("/tmp/never_opened.db")
        with pytest.raises(RuntimeError, match="not initialized"):
            await db.execute("SELECT 1")
```

### 3.7 Tests — Trade Logger (`tests/analytics/test_trade_logger.py`)

```python
"""Tests for the Trade Logger."""

from datetime import datetime, timedelta

import pytest

from argus.analytics.trade_logger import TradeLogger
from argus.core.ids import generate_id
from argus.db.manager import DatabaseManager
from argus.models.trading import AccountSnapshot, DailyPerformance, TradeRecord


@pytest.fixture
async def trade_logger(tmp_path):
    """Provide a TradeLogger with a fresh database."""
    db = DatabaseManager(tmp_path / "test_trades.db")
    await db.initialize()
    logger = TradeLogger(db)
    yield logger
    await db.close()


def make_trade(**overrides) -> TradeRecord:
    """Factory for creating TradeRecords with sensible defaults."""
    defaults = {
        "id": generate_id(),
        "strategy_id": "strat_orb_breakout",
        "strategy_version": "1.0.0",
        "symbol": "AAPL",
        "asset_class": "us_stocks",
        "side": "long",
        "entry_price": 150.0,
        "entry_time": datetime.utcnow(),
        "exit_price": 152.0,
        "exit_time": datetime.utcnow() + timedelta(minutes=15),
        "shares": 100,
        "stop_price": 149.0,
        "target_prices": [151.0, 153.0],
        "exit_reason": "target_1",
        "pnl_dollars": 200.0,
        "pnl_r_multiple": 2.0,
        "hold_duration_seconds": 900,
        "market_regime": "bullish_trending",
    }
    defaults.update(overrides)
    return TradeRecord(**defaults)


class TestTradeLogging:
    """Tests for recording and retrieving trades."""

    async def test_log_and_retrieve_trade(self, trade_logger: TradeLogger) -> None:
        """A logged trade can be retrieved by ID."""
        trade = make_trade()
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.pnl_dollars == 200.0
        assert retrieved.target_prices == [151.0, 153.0]

    async def test_get_nonexistent_trade_returns_none(self, trade_logger: TradeLogger) -> None:
        """Retrieving a nonexistent trade returns None."""
        result = await trade_logger.get_trade("nonexistent_id")
        assert result is None

    async def test_get_trades_by_strategy(self, trade_logger: TradeLogger) -> None:
        """Trades can be filtered by strategy ID."""
        for symbol in ["AAPL", "MSFT", "TSLA"]:
            await trade_logger.log_trade(make_trade(symbol=symbol))
        await trade_logger.log_trade(
            make_trade(strategy_id="strat_vwap_reclaim", symbol="GOOG")
        )

        orb_trades = await trade_logger.get_trades_by_strategy("strat_orb_breakout")
        assert len(orb_trades) == 3

        vwap_trades = await trade_logger.get_trades_by_strategy("strat_vwap_reclaim")
        assert len(vwap_trades) == 1

    async def test_trade_with_modifications_logged(self, trade_logger: TradeLogger) -> None:
        """Risk Manager modifications are preserved in the database."""
        trade = make_trade(
            original_share_count=200,
            modifications={"share_count": {"original": 200, "modified": 100, "reason": "buying_power"}},
        )
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.original_share_count == 200
        assert retrieved.modifications is not None
        assert retrieved.modifications["share_count"]["modified"] == 100

    async def test_ulid_ordering(self, trade_logger: TradeLogger) -> None:
        """Trades ordered by ID are in chronological order."""
        ids = []
        for i in range(5):
            trade = make_trade(
                entry_price=150.0 + i,
                entry_time=datetime(2026, 2, 15, 10, 0, 0) + timedelta(minutes=i),
            )
            trade_id = await trade_logger.log_trade(trade)
            ids.append(trade_id)

        # ULIDs should already be sorted chronologically
        assert ids == sorted(ids)


class TestDailyPnl:
    """Tests for daily P&L queries."""

    async def test_count_trades_today(self, trade_logger: TradeLogger) -> None:
        """count_trades_today returns correct count."""
        for _ in range(3):
            await trade_logger.log_trade(make_trade())

        count = await trade_logger.count_trades_today()
        assert count == 3

    async def test_count_trades_today_by_strategy(self, trade_logger: TradeLogger) -> None:
        """count_trades_today filters by strategy."""
        await trade_logger.log_trade(make_trade(strategy_id="strat_a"))
        await trade_logger.log_trade(make_trade(strategy_id="strat_a"))
        await trade_logger.log_trade(make_trade(strategy_id="strat_b"))

        assert await trade_logger.count_trades_today("strat_a") == 2
        assert await trade_logger.count_trades_today("strat_b") == 1

    async def test_get_daily_pnl(self, trade_logger: TradeLogger) -> None:
        """get_daily_pnl sums today's P&L correctly."""
        await trade_logger.log_trade(make_trade(pnl_dollars=100.0))
        await trade_logger.log_trade(make_trade(pnl_dollars=-50.0))
        await trade_logger.log_trade(make_trade(pnl_dollars=75.0))

        total = await trade_logger.get_daily_pnl()
        assert total == pytest.approx(125.0)


class TestDailyPerformance:
    """Tests for strategy daily performance records."""

    async def test_save_and_retrieve_performance(self, trade_logger: TradeLogger) -> None:
        """Daily performance can be saved and retrieved."""
        perf = DailyPerformance(
            date="2026-02-15",
            strategy_id="strat_orb_breakout",
            trades_taken=5,
            wins=3,
            losses=2,
            gross_pnl=450.0,
            net_pnl=450.0,
            largest_win=200.0,
            largest_loss=-100.0,
            avg_r_multiple=1.5,
            allocated_capital=25000.0,
            market_regime="bullish_trending",
        )
        await trade_logger.save_daily_performance(perf)

        retrieved = await trade_logger.get_daily_performance("strat_orb_breakout", "2026-02-15")
        assert retrieved is not None
        assert retrieved.wins == 3
        assert retrieved.net_pnl == 450.0

    async def test_performance_history(self, trade_logger: TradeLogger) -> None:
        """Performance history returns records in reverse chronological order."""
        for i in range(5):
            perf = DailyPerformance(
                date=f"2026-02-{10 + i:02d}",
                strategy_id="strat_orb",
                trades_taken=i + 1,
                net_pnl=float(i * 100),
            )
            await trade_logger.save_daily_performance(perf)

        history = await trade_logger.get_performance_history("strat_orb", days=3)
        assert len(history) == 3
        assert history[0].date == "2026-02-14"  # Most recent first


class TestAccountSnapshots:
    """Tests for account daily snapshots."""

    async def test_save_and_retrieve_snapshot(self, trade_logger: TradeLogger) -> None:
        """Account snapshot can be saved and retrieved."""
        snapshot = AccountSnapshot(
            date="2026-02-15",
            total_equity=50000.0,
            cash_balance=15000.0,
            deployed_capital=35000.0,
            total_pnl=500.0,
            active_strategies=3,
            total_trades=12,
            market_regime="bullish_trending",
            base_capital=45000.0,
            growth_pool=5000.0,
        )
        await trade_logger.save_account_snapshot(snapshot)

        retrieved = await trade_logger.get_account_snapshot("2026-02-15")
        assert retrieved is not None
        assert retrieved.total_equity == 50000.0
        assert retrieved.growth_pool == 5000.0
```

### 3.8 Tests — Data Models (`tests/models/test_trading.py`)

```python
"""Tests for shared trading data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from argus.models.trading import (
    AccountInfo,
    AssetClass,
    Order,
    OrderSide,
    OrderStatus,
    OrderResult,
    PipelineStage,
    Position,
    TradeRecord,
)


class TestOrder:
    """Tests for the Order model."""

    def test_order_has_auto_generated_id(self) -> None:
        """Orders get a ULID automatically if not provided."""
        order = Order(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
        )
        assert len(order.id) == 26  # ULID length

    def test_order_rejects_zero_quantity(self) -> None:
        """Quantity must be >= 1."""
        with pytest.raises(ValidationError):
            Order(
                strategy_id="strat_orb",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=0,
            )


class TestPosition:
    """Tests for the Position model."""

    def test_r_multiple_calculation(self) -> None:
        """R-multiple is calculated correctly for a closed position."""
        pos = Position(
            strategy_id="strat_orb",
            symbol="AAPL",
            entry_price=150.0,
            entry_time=datetime(2026, 2, 15, 10, 0, 0),
            shares=100,
            stop_price=149.0,
            realized_pnl=200.0,  # $2/share on 100 shares
        )
        # Risk per share = 150 - 149 = $1
        # PnL per share = 200 / 100 = $2
        # R-multiple = 2 / 1 = 2.0
        assert pos.r_multiple == pytest.approx(2.0)

    def test_r_multiple_none_when_open(self) -> None:
        """R-multiple is None for open positions (no realized P&L)."""
        pos = Position(
            strategy_id="strat_orb",
            symbol="AAPL",
            entry_price=150.0,
            entry_time=datetime(2026, 2, 15, 10, 0, 0),
            shares=100,
            stop_price=149.0,
        )
        assert pos.r_multiple is None

    def test_r_multiple_none_when_zero_risk(self) -> None:
        """R-multiple is None when stop = entry (zero risk)."""
        pos = Position(
            strategy_id="strat_orb",
            symbol="AAPL",
            entry_price=150.0,
            entry_time=datetime(2026, 2, 15, 10, 0, 0),
            shares=100,
            stop_price=150.0,  # Same as entry
            realized_pnl=100.0,
        )
        assert pos.r_multiple is None


class TestPipelineStage:
    """Tests for strategy pipeline stages."""

    def test_all_stages_exist(self) -> None:
        """All 10 pipeline stages are defined."""
        stages = list(PipelineStage)
        assert len(stages) == 10
        assert PipelineStage.CONCEPT in stages
        assert PipelineStage.RETIRED in stages


class TestTradeRecord:
    """Tests for the trade record model."""

    def test_trade_record_auto_id(self) -> None:
        """TradeRecord gets a ULID automatically."""
        trade = TradeRecord(
            strategy_id="strat_orb",
            symbol="AAPL",
            entry_price=150.0,
            entry_time=datetime.utcnow(),
            exit_price=152.0,
            exit_time=datetime.utcnow(),
            shares=100,
            stop_price=149.0,
            exit_reason="target_1",
            pnl_dollars=200.0,
        )
        assert len(trade.id) == 26
```

### 3.9 Update `tests/conftest.py`

Add the database fixtures to the shared conftest:

```python
"""Shared test fixtures for the Argus test suite."""

from pathlib import Path

import pytest

from argus.core.config import ArgusConfig, load_config
from argus.core.event_bus import EventBus
from argus.db.manager import DatabaseManager
from argus.analytics.trade_logger import TradeLogger


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def config() -> ArgusConfig:
    """Provide a default ArgusConfig loaded from real config files."""
    return load_config(Path("config"))


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def bus() -> EventBus:
    """Provide a fresh EventBus."""
    return EventBus()


@pytest.fixture
async def db(tmp_path) -> DatabaseManager:
    """Provide an initialized DatabaseManager with a temp database."""
    manager = DatabaseManager(tmp_path / "argus_test.db")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
async def trade_logger(db: DatabaseManager) -> TradeLogger:
    """Provide a TradeLogger backed by a temp database."""
    return TradeLogger(db)
```

### Step 3 Acceptance Criteria

- [ ] `generate_id()` returns 26-character ULID strings
- [ ] ULIDs generated in sequence are lexicographically ordered
- [ ] All Pydantic models validate correctly (Order, Position, TradeRecord, etc.)
- [ ] `Position.r_multiple` property calculates correctly
- [ ] Database schema creates all 7 tables with correct indexes
- [ ] `DatabaseManager` context manager works (init + close)
- [ ] Operations on uninitialized DB raise `RuntimeError`
- [ ] `TradeLogger.log_trade()` writes and `get_trade()` reads correctly
- [ ] JSON fields (target_prices, modifications) survive round-trip to DB
- [ ] `get_trades_by_strategy()` filters correctly
- [ ] `count_trades_today()` and `get_daily_pnl()` return correct values
- [ ] `DailyPerformance` and `AccountSnapshot` save and retrieve correctly
- [ ] All tests in `test_manager.py`, `test_trade_logger.py`, and `test_trading.py` pass
- [ ] `ruff check argus/ tests/` passes clean

---

## Sprint 1 Complete — Definition of Done

All of the following must be true:

1. `pip install -e ".[dev]"` succeeds
2. `ruff check argus/ tests/` — no errors
3. `pytest tests/ -v` — all tests pass
4. Config loads from YAML, validates with Pydantic, rejects bad values
5. Event Bus delivers events with monotonic sequence numbers
6. Trade Logger writes to SQLite and reads back with full fidelity
7. No hardcoded configuration values in any module
8. All public methods have type hints and docstrings

When this is done, come back here and we'll review before starting Sprint 2 (Broker Abstraction + Risk Manager).

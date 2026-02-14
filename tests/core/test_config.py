"""Tests for the Argus configuration system."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.core.config import (
    AccountType,
    ArgusConfig,
    DataServiceConfig,
    OrbBreakoutConfig,
    ScannerConfig,
    StrategyConfig,
    SystemConfig,
    load_config,
    load_orb_config,
    load_scanner_config,
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


class TestDataServiceConfig:
    """Tests for Data Service configuration."""

    def test_defaults_are_valid(self) -> None:
        """DataServiceConfig can be created with all defaults."""
        config = DataServiceConfig()
        assert config.active_timeframes == ["1m"]
        assert "1m" in config.supported_timeframes
        assert "vwap" in config.indicators
        assert config.stale_data_timeout_seconds == 30

    def test_custom_timeframes(self) -> None:
        """Custom timeframes can be specified."""
        config = DataServiceConfig(active_timeframes=["1m", "5m"])
        assert config.active_timeframes == ["1m", "5m"]

    def test_stale_timeout_must_be_positive(self) -> None:
        """Stale data timeout must be >= 1."""
        with pytest.raises(ValidationError):
            DataServiceConfig(stale_data_timeout_seconds=0)


class TestScannerConfig:
    """Tests for Scanner configuration."""

    def test_defaults_are_valid(self) -> None:
        """ScannerConfig can be created with all defaults."""
        config = ScannerConfig()
        assert config.scanner_type == "static"
        assert config.static_symbols == []

    def test_loads_from_yaml(self) -> None:
        """Scanner config loads from scanner.yaml."""
        config = load_scanner_config(Path("config/scanner.yaml"))
        assert config.scanner_type == "static"
        assert "AAPL" in config.static_symbols

    def test_custom_symbols(self) -> None:
        """Custom symbol list can be specified."""
        config = ScannerConfig(static_symbols=["SPY", "QQQ"])
        assert config.static_symbols == ["SPY", "QQQ"]


class TestOrbBreakoutConfig:
    """Tests for ORB Breakout strategy configuration."""

    def test_loads_from_yaml(self) -> None:
        """OrbBreakoutConfig loads and validates from YAML."""
        config = load_orb_config(Path("config/strategies/orb_breakout.yaml"))
        assert config.strategy_id == "strat_orb_breakout"
        assert config.name == "ORB Breakout"
        assert config.orb_window_minutes == 15
        assert config.stop_placement == "midpoint"
        assert config.volume_threshold_rvol == 2.0
        assert config.target_1_r == 1.0
        assert config.target_2_r == 2.0
        assert config.time_stop_minutes == 30
        assert config.min_range_atr_ratio == 0.5
        assert config.max_range_atr_ratio == 2.0
        assert config.chase_protection_pct == 0.005
        assert config.breakout_volume_multiplier == 1.5

    def test_defaults_are_valid(self) -> None:
        """OrbBreakoutConfig can be created with required fields only."""
        config = OrbBreakoutConfig(strategy_id="orb", name="ORB")
        assert config.orb_window_minutes == 15
        assert config.target_1_r == 1.0
        assert config.breakout_volume_multiplier == 1.5

    def test_orb_window_constraints(self) -> None:
        """ORB window must be between 1 and 60 minutes."""
        with pytest.raises(ValidationError):
            OrbBreakoutConfig(strategy_id="orb", name="ORB", orb_window_minutes=0)
        with pytest.raises(ValidationError):
            OrbBreakoutConfig(strategy_id="orb", name="ORB", orb_window_minutes=61)

    def test_chase_protection_constraints(self) -> None:
        """Chase protection must be between 0 and 5%."""
        with pytest.raises(ValidationError):
            OrbBreakoutConfig(strategy_id="orb", name="ORB", chase_protection_pct=-0.01)
        with pytest.raises(ValidationError):
            OrbBreakoutConfig(strategy_id="orb", name="ORB", chase_protection_pct=0.06)

    def test_inherits_strategy_config(self) -> None:
        """OrbBreakoutConfig inherits all StrategyConfig fields."""
        config = load_orb_config(Path("config/strategies/orb_breakout.yaml"))
        # Base StrategyConfig fields
        assert config.risk_limits.max_trades_per_day == 6
        assert config.operating_window.earliest_entry == "09:45"
        assert config.benchmarks.min_win_rate == 0.45

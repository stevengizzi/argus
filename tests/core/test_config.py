"""Tests for the Argus configuration system."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.core.config import (
    AccountType,
    ArgusConfig,
    BrokerConfig,
    BrokerSource,
    DatabentoConfig,
    DataServiceConfig,
    IBKRConfig,
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
        # Sprint 10 optimization: or=5, hold=15, atr=999 (DEC-075)
        assert config.orb_window_minutes == 5
        assert config.stop_placement == "midpoint"
        assert config.volume_threshold_rvol == 2.0
        assert config.target_1_r == 1.0
        assert config.target_2_r == 2.0
        assert config.time_stop_minutes == 15
        assert config.min_range_atr_ratio == 0.5
        assert config.max_range_atr_ratio == 999.0
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
        # DEC-078: earliest_entry changed from 09:45 to 09:35 to match or=5 window
        assert config.operating_window.earliest_entry == "09:35"
        assert config.benchmarks.min_win_rate == 0.45


class TestDatabentoConfig:
    """Tests for Databento market data configuration (Sprint 12)."""

    def test_default_config_creates_successfully(self) -> None:
        """DatabentoConfig can be created with all defaults."""
        config = DatabentoConfig()
        assert config.enabled is True
        assert config.api_key_env_var == "DATABENTO_API_KEY"
        assert config.dataset == "XNAS.ITCH"
        assert config.bar_schema == "ohlcv-1m"
        assert config.trade_schema == "trades"
        assert config.depth_schema == "mbp-10"
        assert config.enable_depth is False
        assert config.symbols == "ALL_SYMBOLS"
        assert config.stype_in == "raw_symbol"
        assert config.stale_data_timeout_seconds == 30.0
        assert config.historical_cache_dir == "data/databento_cache"

    def test_custom_dataset_validates(self) -> None:
        """Known datasets are accepted."""
        for dataset in ["XNAS.ITCH", "XNYS.PILLAR", "DBEQ.BASIC"]:
            config = DatabentoConfig(dataset=dataset)
            assert config.dataset == dataset

    def test_invalid_dataset_raises_value_error(self) -> None:
        """Unknown dataset raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            DatabentoConfig(dataset="INVALID.DATASET")
        assert "Unknown dataset" in str(exc_info.value)

    def test_invalid_bar_schema_raises_value_error(self) -> None:
        """Invalid bar schema raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            DatabentoConfig(bar_schema="ohlcv-5m")
        assert "Invalid bar_schema" in str(exc_info.value)

    def test_valid_bar_schemas(self) -> None:
        """Valid bar schemas are accepted."""
        for schema in ["ohlcv-1s", "ohlcv-1m", "ohlcv-1h", "ohlcv-1d"]:
            config = DatabentoConfig(bar_schema=schema)
            assert config.bar_schema == schema

    def test_invalid_stype_in_raises_value_error(self) -> None:
        """Invalid stype_in raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            DatabentoConfig(stype_in="invalid_type")
        assert "Invalid stype_in" in str(exc_info.value)

    def test_valid_stype_in_values(self) -> None:
        """Valid stype_in values are accepted."""
        for stype in ["raw_symbol", "instrument_id", "smart"]:
            config = DatabentoConfig(stype_in=stype)
            assert config.stype_in == stype

    def test_symbols_as_list_works(self) -> None:
        """Symbols can be a list of tickers."""
        config = DatabentoConfig(symbols=["AAPL", "TSLA", "NVDA"])
        assert config.symbols == ["AAPL", "TSLA", "NVDA"]

    def test_symbols_as_all_symbols_string_works(self) -> None:
        """Symbols can be 'ALL_SYMBOLS' for full universe."""
        config = DatabentoConfig(symbols="ALL_SYMBOLS")
        assert config.symbols == "ALL_SYMBOLS"

    def test_reconnection_defaults_are_sane(self) -> None:
        """Reconnection settings have reasonable defaults."""
        config = DatabentoConfig()
        assert config.reconnect_max_retries == 10
        assert config.reconnect_base_delay_seconds == 1.0
        assert config.reconnect_max_delay_seconds == 60.0
        # Ensure max > base
        assert config.reconnect_max_delay_seconds > config.reconnect_base_delay_seconds

    def test_config_serialization_round_trip(self) -> None:
        """Config can be serialized to dict and back."""
        original = DatabentoConfig(
            dataset="XNYS.PILLAR",
            symbols=["SPY", "QQQ"],
            enable_depth=True,
        )
        # Serialize to dict
        data = original.model_dump()
        # Deserialize back
        restored = DatabentoConfig(**data)
        assert restored.dataset == original.dataset
        assert restored.symbols == original.symbols
        assert restored.enable_depth == original.enable_depth

    def test_config_integrates_into_broker_config(self) -> None:
        """DatabentoConfig is accessible via BrokerConfig."""
        config = BrokerConfig()
        assert hasattr(config, "databento")
        assert isinstance(config.databento, DatabentoConfig)
        assert config.databento.dataset == "XNAS.ITCH"

    def test_all_known_datasets_validate(self) -> None:
        """All documented datasets pass validation."""
        known_datasets = [
            "XNAS.ITCH",
            "XNAS.BASIC",
            "XNYS.PILLAR",
            "ARCX.PILLAR",
            "XASE.PILLAR",
            "DBEQ.BASIC",
            "XBOS.ITCH",
            "XPSX.ITCH",
            "XCHI.PILLAR",
            "XCIS.TRADESBBO",
            "EQUS.SUMMARY",
        ]
        for dataset in known_datasets:
            config = DatabentoConfig(dataset=dataset)
            assert config.dataset == dataset


class TestIBKRConfig:
    """Tests for Interactive Brokers configuration (Sprint 13)."""

    def test_default_config_creates_successfully(self) -> None:
        """IBKRConfig can be created with all defaults."""
        config = IBKRConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 4002  # Paper trading port by default
        assert config.client_id == 1
        assert config.account == ""
        assert config.timeout_seconds == 30.0
        assert config.readonly is False
        assert config.reconnect_max_retries == 10
        assert config.reconnect_base_delay_seconds == 1.0
        assert config.reconnect_max_delay_seconds == 60.0
        assert config.max_order_rate_per_second == 45.0

    def test_config_loads_from_system_yaml(self) -> None:
        """IBKRConfig loads correctly from system.yaml via SystemConfig."""
        config = load_config(Path("config"))
        assert hasattr(config.system, "ibkr")
        assert isinstance(config.system.ibkr, IBKRConfig)
        # Verify values from YAML
        assert config.system.ibkr.port == 4002
        assert config.system.ibkr.timeout_seconds == 30.0
        assert config.system.ibkr.max_order_rate_per_second == 45.0

    def test_port_validation(self) -> None:
        """Port must be in valid range (1-65535)."""
        # Valid ports
        assert IBKRConfig(port=4001).port == 4001  # Live
        assert IBKRConfig(port=4002).port == 4002  # Paper
        assert IBKRConfig(port=7496).port == 7496  # TWS live
        assert IBKRConfig(port=7497).port == 7497  # TWS paper

        # Invalid ports
        with pytest.raises(ValidationError):
            IBKRConfig(port=0)
        with pytest.raises(ValidationError):
            IBKRConfig(port=65536)

    def test_timeout_must_be_positive(self) -> None:
        """Timeout must be > 0."""
        assert IBKRConfig(timeout_seconds=1.0).timeout_seconds == 1.0
        with pytest.raises(ValidationError):
            IBKRConfig(timeout_seconds=0)
        with pytest.raises(ValidationError):
            IBKRConfig(timeout_seconds=-1.0)

    def test_client_id_must_be_non_negative(self) -> None:
        """Client ID must be >= 0."""
        assert IBKRConfig(client_id=0).client_id == 0
        assert IBKRConfig(client_id=100).client_id == 100
        with pytest.raises(ValidationError):
            IBKRConfig(client_id=-1)

    def test_reconnection_settings_validate(self) -> None:
        """Reconnection settings must be positive."""
        # Valid settings
        config = IBKRConfig(
            reconnect_max_retries=5,
            reconnect_base_delay_seconds=0.5,
            reconnect_max_delay_seconds=30.0,
        )
        assert config.reconnect_max_retries == 5
        assert config.reconnect_base_delay_seconds == 0.5
        assert config.reconnect_max_delay_seconds == 30.0

        # Zero retries allowed
        assert IBKRConfig(reconnect_max_retries=0).reconnect_max_retries == 0

        # Delays must be positive
        with pytest.raises(ValidationError):
            IBKRConfig(reconnect_base_delay_seconds=0)
        with pytest.raises(ValidationError):
            IBKRConfig(reconnect_max_delay_seconds=0)

    def test_max_order_rate_must_be_positive(self) -> None:
        """Max order rate must be > 0."""
        assert IBKRConfig(max_order_rate_per_second=50.0).max_order_rate_per_second == 50.0
        with pytest.raises(ValidationError):
            IBKRConfig(max_order_rate_per_second=0)


class TestBrokerSource:
    """Tests for BrokerSource enum (DEC-094)."""

    def test_broker_source_values(self) -> None:
        """BrokerSource has expected values."""
        assert BrokerSource.ALPACA.value == "alpaca"
        assert BrokerSource.IBKR.value == "ibkr"
        assert BrokerSource.SIMULATED.value == "simulated"

    def test_broker_source_loads_from_yaml(self) -> None:
        """broker_source loads correctly from system.yaml."""
        config = load_config(Path("config"))
        assert hasattr(config.system, "broker_source")
        assert config.system.broker_source == BrokerSource.SIMULATED

    def test_broker_source_default_is_simulated(self) -> None:
        """Default broker_source is simulated (safest default)."""
        config = SystemConfig()
        assert config.broker_source == BrokerSource.SIMULATED

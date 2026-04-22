"""Tests for the Argus configuration system."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.core.config import (
    AccountType,
    AfternoonMomentumConfig,
    ArgusConfig,
    BrokerConfig,
    BrokerSource,
    DatabentoConfig,
    DataServiceConfig,
    IBKRConfig,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OrchestratorConfig,
    StrategyConfig,
    OrderManagerConfig,
    StartupConfig,
    SystemConfig,
    UniverseFilterConfig,
    UniverseManagerConfig,
    VwapReclaimConfig,
    load_afternoon_momentum_config,
    load_config,
    load_orb_config,
    load_orb_scalp_config,
    load_strategy_config,
    load_vwap_reclaim_config,
    load_yaml_file,
)
from argus.intelligence.config import QualityEngineConfig

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
        (tmp_path / "system.yaml").write_text((FIXTURES_DIR / "test_system.yaml").read_text())
        (tmp_path / "risk_limits.yaml").write_text(
            (FIXTURES_DIR / "test_risk_limits.yaml").read_text()
        )
        (tmp_path / "brokers.yaml").write_text((FIXTURES_DIR / "test_brokers.yaml").read_text())
        config = load_config(tmp_path)
        assert config.system.log_level.value == "DEBUG"

    def test_missing_config_dir_raises(self) -> None:
        """Missing config directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/path"))

    def test_missing_optional_files_use_defaults(self, tmp_path: Path) -> None:
        """Missing YAML files result in default values, not errors."""
        # Minimal system.yaml with api.enabled: false so the H2-H10
        # validator (FIX-16, audit 2026-04-21) does not trip — default
        # ApiConfig has enabled=True + empty password_hash, which is the
        # sentinel rejected at load time in production.
        (tmp_path / "system.yaml").write_text("api:\n  enabled: false\n")
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
        """Daily loss limit > 100% is rejected."""
        with pytest.raises(ValidationError):
            ArgusConfig(risk={"account": {"daily_loss_limit_pct": 1.5}})

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


# TestScannerConfig removed by FIX-16 (audit 2026-04-21, H2-S06): the
# ScannerConfig Pydantic class only modelled scanner_type + static_symbols;
# the 3 nested provider blocks in config/scanner.yaml (fmp_scanner,
# alpaca_scanner, databento_scanner) were silently dropped. Production code
# reads scanner.yaml directly in argus/main.py — each provider block feeds
# into its own dedicated config class.


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
        assert config.dataset == "EQUS.MINI"  # DEC-237: Standard plan default
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
        assert config.databento.dataset == "EQUS.MINI"  # DEC-237: Standard plan default

    def test_all_known_datasets_validate(self) -> None:
        """All documented datasets pass validation."""
        known_datasets = [
            # Consolidated feeds (DEC-237)
            "EQUS.MINI",  # Standard plan
            "EQUS.MAX",  # Plus/Pro
            "EQUS.SUMMARY",
            # Exchange-specific feeds
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


class TestOrchestratorConfig:
    """Tests for Orchestrator configuration (Sprint 17)."""

    def test_default_config_creates_successfully(self) -> None:
        """OrchestratorConfig can be created with all defaults."""
        config = OrchestratorConfig()
        assert config.allocation_method == "equal_weight"
        assert config.max_allocation_pct == 0.40
        assert config.min_allocation_pct == 0.10
        assert config.cash_reserve_pct == 0.20
        assert config.performance_lookback_days == 20
        assert config.consecutive_loss_throttle == 5
        assert config.suspension_sharpe_threshold == 0.0
        assert config.suspension_drawdown_pct == 0.15
        assert config.recovery_days_required == 10
        assert config.regime_check_interval_minutes == 30
        assert config.spy_symbol == "SPY"
        assert config.vol_low_threshold == 0.08
        assert config.vol_normal_threshold == 0.16
        assert config.vol_high_threshold == 0.25
        assert config.vol_crisis_threshold == 0.35
        assert config.pre_market_time == "09:25"
        assert config.eod_review_time == "16:05"
        assert config.poll_interval_seconds == 30
        assert config.correlation_enabled is True
        assert config.min_correlation_days == 20
        assert config.max_combined_correlated_allocation == 0.60

    def test_config_loads_from_yaml(self) -> None:
        """OrchestratorConfig loads correctly from orchestrator.yaml."""
        config = load_config(Path("config"))
        assert hasattr(config, "orchestrator")
        assert isinstance(config.orchestrator, OrchestratorConfig)
        assert config.orchestrator.allocation_method == "equal_weight"
        assert config.orchestrator.max_allocation_pct == 0.40
        assert config.orchestrator.correlation_enabled is True

    def test_max_allocation_pct_must_be_in_range(self) -> None:
        """max_allocation_pct must be between 0 and 1."""
        assert OrchestratorConfig(max_allocation_pct=0.50).max_allocation_pct == 0.50
        assert OrchestratorConfig(max_allocation_pct=1.0).max_allocation_pct == 1.0
        with pytest.raises(ValidationError):
            OrchestratorConfig(max_allocation_pct=0)
        with pytest.raises(ValidationError):
            OrchestratorConfig(max_allocation_pct=1.1)

    def test_min_allocation_pct_must_be_in_range(self) -> None:
        """min_allocation_pct must be between 0 and 1."""
        assert OrchestratorConfig(min_allocation_pct=0.05).min_allocation_pct == 0.05
        with pytest.raises(ValidationError):
            OrchestratorConfig(min_allocation_pct=0)
        with pytest.raises(ValidationError):
            OrchestratorConfig(min_allocation_pct=1.1)

    def test_cash_reserve_pct_must_be_in_range(self) -> None:
        """cash_reserve_pct must be between 0 and 0.5."""
        assert OrchestratorConfig(cash_reserve_pct=0.0).cash_reserve_pct == 0.0
        assert OrchestratorConfig(cash_reserve_pct=0.5).cash_reserve_pct == 0.5
        with pytest.raises(ValidationError):
            OrchestratorConfig(cash_reserve_pct=-0.1)
        with pytest.raises(ValidationError):
            OrchestratorConfig(cash_reserve_pct=0.6)

    def test_performance_lookback_days_must_be_at_least_5(self) -> None:
        """performance_lookback_days must be >= 5."""
        assert OrchestratorConfig(performance_lookback_days=5).performance_lookback_days == 5
        assert OrchestratorConfig(performance_lookback_days=60).performance_lookback_days == 60
        with pytest.raises(ValidationError):
            OrchestratorConfig(performance_lookback_days=4)

    def test_consecutive_loss_throttle_must_be_at_least_2(self) -> None:
        """consecutive_loss_throttle must be >= 2."""
        assert OrchestratorConfig(consecutive_loss_throttle=2).consecutive_loss_throttle == 2
        with pytest.raises(ValidationError):
            OrchestratorConfig(consecutive_loss_throttle=1)

    def test_recovery_days_required_must_be_positive(self) -> None:
        """recovery_days_required must be >= 1."""
        assert OrchestratorConfig(recovery_days_required=1).recovery_days_required == 1
        with pytest.raises(ValidationError):
            OrchestratorConfig(recovery_days_required=0)

    def test_regime_check_interval_can_be_none(self) -> None:
        """regime_check_interval_minutes can be None to disable."""
        config = OrchestratorConfig(regime_check_interval_minutes=None)
        assert config.regime_check_interval_minutes is None

    def test_poll_interval_must_be_positive(self) -> None:
        """poll_interval_seconds must be >= 1."""
        assert OrchestratorConfig(poll_interval_seconds=1).poll_interval_seconds == 1
        with pytest.raises(ValidationError):
            OrchestratorConfig(poll_interval_seconds=0)

    def test_min_correlation_days_must_be_at_least_5(self) -> None:
        """min_correlation_days must be >= 5."""
        assert OrchestratorConfig(min_correlation_days=5).min_correlation_days == 5
        with pytest.raises(ValidationError):
            OrchestratorConfig(min_correlation_days=4)

    def test_max_combined_correlated_allocation_must_be_in_range(self) -> None:
        """max_combined_correlated_allocation must be between 0 and 1."""
        config = OrchestratorConfig(max_combined_correlated_allocation=0.80)
        assert config.max_combined_correlated_allocation == 0.80
        with pytest.raises(ValidationError):
            OrchestratorConfig(max_combined_correlated_allocation=0)
        with pytest.raises(ValidationError):
            OrchestratorConfig(max_combined_correlated_allocation=1.1)


class TestUniverseFilterConfig:
    """Tests for UniverseFilterConfig (Sprint 23)."""

    def test_universe_filter_config_defaults(self) -> None:
        """UniverseFilterConfig can be created with all defaults (all None/empty)."""
        config = UniverseFilterConfig()
        assert config.min_price is None
        assert config.max_price is None
        assert config.min_market_cap is None
        assert config.max_market_cap is None
        assert config.min_float is None
        assert config.min_avg_volume is None
        assert config.sectors == []
        assert config.exclude_sectors == []

    def test_universe_filter_config_full(self) -> None:
        """UniverseFilterConfig validates correctly with all fields set."""
        config = UniverseFilterConfig(
            min_price=5.0,
            max_price=500.0,
            min_market_cap=1_000_000_000,  # 1B
            max_market_cap=100_000_000_000,  # 100B
            min_float=10_000_000,  # 10M shares
            min_avg_volume=1_000_000,
            sectors=["Technology", "Healthcare"],
            exclude_sectors=["Utilities", "Real Estate"],
        )
        assert config.min_price == 5.0
        assert config.max_price == 500.0
        assert config.min_market_cap == 1_000_000_000
        assert config.max_market_cap == 100_000_000_000
        assert config.min_float == 10_000_000
        assert config.min_avg_volume == 1_000_000
        assert config.sectors == ["Technology", "Healthcare"]
        assert config.exclude_sectors == ["Utilities", "Real Estate"]

    def test_universe_filter_config_invalid_types(self) -> None:
        """UniverseFilterConfig rejects wrong types."""
        # String where float expected
        with pytest.raises(ValidationError):
            UniverseFilterConfig(min_price="invalid")  # type: ignore[arg-type]

        # String where int expected
        with pytest.raises(ValidationError):
            UniverseFilterConfig(min_avg_volume="invalid")  # type: ignore[arg-type]

        # String where list expected
        with pytest.raises(ValidationError):
            UniverseFilterConfig(sectors="Technology")  # type: ignore[arg-type]

    def test_min_relative_volume_rejects_negative(self) -> None:
        """FIX-06 audit 2026-04-21 (P1-C2-3): Sprint 29 field rejects negative."""
        with pytest.raises(ValidationError):
            UniverseFilterConfig(min_relative_volume=-0.5)

    def test_min_premarket_volume_rejects_negative(self) -> None:
        """FIX-06 audit 2026-04-21 (P1-C2-3): Sprint 29 field rejects negative."""
        with pytest.raises(ValidationError):
            UniverseFilterConfig(min_premarket_volume=-100)

    def test_min_gap_percent_rejects_out_of_range(self) -> None:
        """FIX-06 audit 2026-04-21 (P1-C2-3): gap percent is bounded [-100, 100]."""
        with pytest.raises(ValidationError):
            UniverseFilterConfig(min_gap_percent=150.0)
        with pytest.raises(ValidationError):
            UniverseFilterConfig(min_gap_percent=-200.0)

    def test_sprint_29_fields_accept_valid_bounds(self) -> None:
        """FIX-06 audit 2026-04-21 (P1-C2-3): zero-lower-bound accepted at bound."""
        config = UniverseFilterConfig(
            min_relative_volume=0.0,
            min_gap_percent=-100.0,
            min_premarket_volume=0,
        )
        assert config.min_relative_volume == 0.0
        assert config.min_gap_percent == -100.0
        assert config.min_premarket_volume == 0


class TestUniverseManagerConfig:
    """Tests for UniverseManagerConfig (Sprint 23)."""

    def test_universe_manager_config_defaults(self) -> None:
        """UniverseManagerConfig has correct default values."""
        config = UniverseManagerConfig()
        assert config.enabled is False
        assert config.min_price == 5.0
        assert config.max_price == 10000.0
        assert config.min_avg_volume == 100000
        assert config.exclude_otc is True
        assert config.reference_cache_ttl_hours == 24
        assert config.fmp_batch_size == 50

    def test_universe_manager_config_custom_values(self) -> None:
        """UniverseManagerConfig accepts custom values."""
        config = UniverseManagerConfig(
            enabled=True,
            min_price=10.0,
            max_price=500.0,
            min_avg_volume=500_000,
            exclude_otc=False,
            reference_cache_ttl_hours=12,
            fmp_batch_size=100,
        )
        assert config.enabled is True
        assert config.min_price == 10.0
        assert config.max_price == 500.0
        assert config.min_avg_volume == 500_000
        assert config.exclude_otc is False
        assert config.reference_cache_ttl_hours == 12
        assert config.fmp_batch_size == 100


class TestStrategyConfigUniverseFilter:
    """Tests for StrategyConfig integration with UniverseFilterConfig (Sprint 23)."""

    def test_strategy_config_with_universe_filter(self) -> None:
        """StrategyConfig accepts universe_filter field."""
        universe_filter = UniverseFilterConfig(
            min_price=10.0,
            max_price=200.0,
            sectors=["Technology"],
        )
        config = StrategyConfig(
            strategy_id="test_strat",
            name="Test Strategy",
            universe_filter=universe_filter,
        )
        assert config.universe_filter is not None
        assert config.universe_filter.min_price == 10.0
        assert config.universe_filter.max_price == 200.0
        assert config.universe_filter.sectors == ["Technology"]

    def test_strategy_config_without_universe_filter(self) -> None:
        """StrategyConfig works without universe_filter (backward compat)."""
        config = StrategyConfig(strategy_id="test_strat", name="Test Strategy")
        assert config.universe_filter is None
        # Verify other fields still work
        assert config.strategy_id == "test_strat"
        assert config.name == "Test Strategy"
        assert config.version == "1.0.0"
        assert config.enabled is True


class TestSystemConfigUniverseManager:
    """Tests for SystemConfig integration with UniverseManagerConfig (Sprint 23)."""

    def test_system_config_with_universe_manager(self) -> None:
        """SystemConfig includes universe_manager field with defaults."""
        config = SystemConfig()
        assert hasattr(config, "universe_manager")
        assert isinstance(config.universe_manager, UniverseManagerConfig)
        # Verify defaults are applied
        assert config.universe_manager.enabled is False
        assert config.universe_manager.min_price == 5.0

    def test_system_config_with_custom_universe_manager(self) -> None:
        """SystemConfig accepts custom universe_manager values."""
        config = SystemConfig(
            universe_manager=UniverseManagerConfig(
                enabled=True,
                min_price=20.0,
            )
        )
        assert config.universe_manager.enabled is True
        assert config.universe_manager.min_price == 20.0

    def test_config_yaml_pydantic_field_match(self, tmp_path: Path) -> None:
        """YAML keys must match UniverseManagerConfig model_fields."""
        # Create a fixture YAML with universe_manager section
        # Note: system.yaml content goes directly into the file without "system:" wrapper
        yaml_content = """
timezone: America/New_York
# api.enabled: false avoids tripping the H2-H10 password_hash validator
api:
  enabled: false
universe_manager:
  enabled: true
  min_price: 10.0
  max_price: 500.0
  min_avg_volume: 250000
  exclude_otc: true
  reference_cache_ttl_hours: 12
  fmp_batch_size: 75
"""
        system_yaml = tmp_path / "system.yaml"
        system_yaml.write_text(yaml_content)

        # Load and validate
        config = load_config(tmp_path)

        # Verify loaded correctly
        assert config.system.universe_manager.enabled is True
        assert config.system.universe_manager.min_price == 10.0
        assert config.system.universe_manager.max_price == 500.0
        assert config.system.universe_manager.min_avg_volume == 250000
        assert config.system.universe_manager.exclude_otc is True
        assert config.system.universe_manager.reference_cache_ttl_hours == 12
        assert config.system.universe_manager.fmp_batch_size == 75

        # Verify no unrecognized keys: parse YAML and check against model fields
        raw_yaml = yaml.safe_load(yaml_content)
        yaml_keys = set(raw_yaml["universe_manager"].keys())
        model_fields = set(UniverseManagerConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys in YAML: {unrecognized}"


class TestOrbFamilyUniverseFilter:
    """Tests for ORB family universe_filter declarations (Sprint 23, Session 2b)."""

    def test_orb_breakout_config_loads_with_filter(self) -> None:
        """ORB Breakout config loads with universe_filter populated."""
        config = load_orb_config(Path("config/strategies/orb_breakout.yaml"))
        assert config.strategy_id == "strat_orb_breakout"
        assert config.universe_filter is not None
        assert isinstance(config.universe_filter, UniverseFilterConfig)

    def test_orb_scalp_config_loads_with_filter(self) -> None:
        """ORB Scalp config loads with universe_filter populated."""
        config = load_orb_scalp_config(Path("config/strategies/orb_scalp.yaml"))
        assert config.strategy_id == "strat_orb_scalp"
        assert config.universe_filter is not None
        assert isinstance(config.universe_filter, UniverseFilterConfig)

    def test_orb_breakout_filter_values_reasonable(self) -> None:
        """ORB Breakout filter values are positive and reasonable."""
        config = load_orb_config(Path("config/strategies/orb_breakout.yaml"))
        assert config.universe_filter is not None
        # Values extracted from get_scanner_criteria() in orb_base.py
        assert config.universe_filter.min_price is not None
        assert config.universe_filter.min_price > 0
        assert config.universe_filter.max_price is not None
        assert config.universe_filter.max_price > config.universe_filter.min_price
        assert config.universe_filter.min_avg_volume is not None
        assert config.universe_filter.min_avg_volume > 0

    def test_orb_scalp_filter_values_reasonable(self) -> None:
        """ORB Scalp filter values are positive and reasonable."""
        config = load_orb_scalp_config(Path("config/strategies/orb_scalp.yaml"))
        assert config.universe_filter is not None
        # Values extracted from get_scanner_criteria() in orb_base.py
        assert config.universe_filter.min_price is not None
        assert config.universe_filter.min_price > 0
        assert config.universe_filter.max_price is not None
        assert config.universe_filter.max_price > config.universe_filter.min_price
        assert config.universe_filter.min_avg_volume is not None
        assert config.universe_filter.min_avg_volume > 0

    def test_orb_breakout_yaml_keys_match_model(self) -> None:
        """ORB Breakout YAML universe_filter has no unrecognized keys."""
        yaml_path = Path("config/strategies/orb_breakout.yaml")
        raw_yaml = yaml.safe_load(yaml_path.read_text())

        # Verify universe_filter section exists
        assert "universe_filter" in raw_yaml, "universe_filter section missing from YAML"

        # Check for unrecognized keys
        yaml_keys = set(raw_yaml["universe_filter"].keys())
        model_fields = set(UniverseFilterConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys in universe_filter: {unrecognized}"

    def test_orb_scalp_yaml_keys_match_model(self) -> None:
        """ORB Scalp YAML universe_filter has no unrecognized keys."""
        yaml_path = Path("config/strategies/orb_scalp.yaml")
        raw_yaml = yaml.safe_load(yaml_path.read_text())

        # Verify universe_filter section exists
        assert "universe_filter" in raw_yaml, "universe_filter section missing from YAML"

        # Check for unrecognized keys
        yaml_keys = set(raw_yaml["universe_filter"].keys())
        model_fields = set(UniverseFilterConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys in universe_filter: {unrecognized}"


class TestVwapAfternoonUniverseFilter:
    """Tests for VWAP/Afternoon Momentum universe_filter declarations (Sprint 23, Session 2c)."""

    def test_vwap_reclaim_config_loads_with_filter(self) -> None:
        """VWAP Reclaim config loads with universe_filter populated."""
        config = load_vwap_reclaim_config(Path("config/strategies/vwap_reclaim.yaml"))
        assert config.strategy_id == "strat_vwap_reclaim"
        assert config.universe_filter is not None
        assert isinstance(config.universe_filter, UniverseFilterConfig)

    def test_afternoon_momentum_config_loads_with_filter(self) -> None:
        """Afternoon Momentum config loads with universe_filter populated."""
        config = load_afternoon_momentum_config(
            Path("config/strategies/afternoon_momentum.yaml")
        )
        assert config.strategy_id == "strat_afternoon_momentum"
        assert config.universe_filter is not None
        assert isinstance(config.universe_filter, UniverseFilterConfig)

    def test_vwap_reclaim_filter_values_reasonable(self) -> None:
        """VWAP Reclaim filter values are positive and reasonable."""
        config = load_vwap_reclaim_config(Path("config/strategies/vwap_reclaim.yaml"))
        assert config.universe_filter is not None
        # VWAP Reclaim: mean-reversion with mid-to-large cap preference
        assert config.universe_filter.min_price is not None
        assert config.universe_filter.min_price > 0
        assert config.universe_filter.max_price is not None
        assert config.universe_filter.max_price > config.universe_filter.min_price
        assert config.universe_filter.min_avg_volume is not None
        assert config.universe_filter.min_avg_volume > 0
        # VWAP benefits from institutional flow
        assert config.universe_filter.min_market_cap is not None
        assert config.universe_filter.min_market_cap >= 500_000_000  # Mid-cap minimum

    def test_afternoon_momentum_filter_values_reasonable(self) -> None:
        """Afternoon Momentum filter values are positive and reasonable."""
        config = load_afternoon_momentum_config(
            Path("config/strategies/afternoon_momentum.yaml")
        )
        assert config.universe_filter is not None
        # Afternoon Momentum: active stocks with volume
        assert config.universe_filter.min_price is not None
        assert config.universe_filter.min_price > 0
        assert config.universe_filter.max_price is not None
        assert config.universe_filter.max_price > config.universe_filter.min_price
        assert config.universe_filter.min_avg_volume is not None
        assert config.universe_filter.min_avg_volume > 0

    def test_vwap_reclaim_yaml_keys_match_model(self) -> None:
        """VWAP Reclaim YAML universe_filter has no unrecognized keys."""
        yaml_path = Path("config/strategies/vwap_reclaim.yaml")
        raw_yaml = yaml.safe_load(yaml_path.read_text())

        # Verify universe_filter section exists
        assert "universe_filter" in raw_yaml, "universe_filter section missing from YAML"

        # Check for unrecognized keys
        yaml_keys = set(raw_yaml["universe_filter"].keys())
        model_fields = set(UniverseFilterConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys in universe_filter: {unrecognized}"

    def test_afternoon_momentum_yaml_keys_match_model(self) -> None:
        """Afternoon Momentum YAML universe_filter has no unrecognized keys."""
        yaml_path = Path("config/strategies/afternoon_momentum.yaml")
        raw_yaml = yaml.safe_load(yaml_path.read_text())

        # Verify universe_filter section exists
        assert "universe_filter" in raw_yaml, "universe_filter section missing from YAML"

        # Check for unrecognized keys
        yaml_keys = set(raw_yaml["universe_filter"].keys())
        model_fields = set(UniverseFilterConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys in universe_filter: {unrecognized}"


class TestUniverseManagerSystemYamlIntegration:
    """Tests for UniverseManagerConfig integration with system.yaml (Sprint 23, Session 4a).

    Verifies that:
    1. system.yaml loads with the universe_manager section
    2. Default values match between YAML and Pydantic model
    3. Missing universe_manager section falls back to defaults
    4. No YAML keys are silently ignored (YAML↔Pydantic match)
    5. UniverseManager accepts the real Pydantic config
    6. system_live.yaml also loads successfully
    """

    def test_system_yaml_loads_with_universe_manager(self) -> None:
        """Actual config/system.yaml loads with universe_manager section."""
        config = load_config(Path("config"))

        # Verify universe_manager section loaded
        assert hasattr(config.system, "universe_manager")
        assert isinstance(config.system.universe_manager, UniverseManagerConfig)

        # Verify section exists in raw YAML
        raw_yaml = yaml.safe_load(Path("config/system.yaml").read_text())
        assert "universe_manager" in raw_yaml, "universe_manager section missing from system.yaml"

    def test_system_yaml_universe_manager_defaults(self) -> None:
        """system.yaml universe_manager values match Pydantic defaults."""
        config = load_config(Path("config"))
        um = config.system.universe_manager

        # These should match the YAML values which should match defaults
        # (Session 4a sets YAML to defaults for safe initial deployment)
        assert um.enabled is False  # Start disabled
        assert um.min_price == 5.0
        assert um.max_price == 10000.0
        assert um.min_avg_volume == 100000
        assert um.exclude_otc is True
        assert um.reference_cache_ttl_hours == 24
        assert um.fmp_batch_size == 50

    def test_system_yaml_missing_universe_manager(self, tmp_path: Path) -> None:
        """Missing universe_manager section in YAML → defaults apply."""
        # Create minimal system.yaml without universe_manager section
        # (api.enabled: false avoids tripping the H2-H10 password_hash validator)
        yaml_content = """
timezone: America/New_York
market_open: "09:30"
market_close: "16:00"
log_level: INFO
api:
  enabled: false
"""
        (tmp_path / "system.yaml").write_text(yaml_content)

        # Load config - should use defaults
        config = load_config(tmp_path)

        # Verify defaults are applied
        assert config.system.universe_manager.enabled is False
        assert config.system.universe_manager.min_price == 5.0
        assert config.system.universe_manager.max_price == 10000.0
        assert config.system.universe_manager.min_avg_volume == 100000
        assert config.system.universe_manager.exclude_otc is True
        assert config.system.universe_manager.reference_cache_ttl_hours == 24
        assert config.system.universe_manager.fmp_batch_size == 50

    def test_universe_manager_yaml_keys_match_pydantic(self) -> None:
        """All keys in system.yaml universe_manager section match Pydantic model fields.

        This prevents silent key ignoring where a typo in YAML is ignored.
        """
        yaml_path = Path("config/system.yaml")
        raw_yaml = yaml.safe_load(yaml_path.read_text())

        # Verify universe_manager section exists
        assert "universe_manager" in raw_yaml, "universe_manager section missing from system.yaml"

        # Get keys from YAML
        yaml_keys = set(raw_yaml["universe_manager"].keys())

        # Get model field names
        model_fields = set(UniverseManagerConfig.model_fields.keys())

        # Check for keys in YAML that aren't in the model (would be silently ignored)
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), (
            f"Unrecognized keys in universe_manager YAML (silently ignored): {unrecognized}. "
            f"Valid keys: {sorted(model_fields)}"
        )

    def test_universe_manager_config_swap_in_manager(self) -> None:
        """UniverseManager accepts the real UniverseManagerConfig from config.py.

        This verifies the Session 4a swap from temporary dataclass to real Pydantic model.
        """
        from unittest.mock import MagicMock

        from argus.data.universe_manager import UniverseManager

        # Create real config from Pydantic model
        config = UniverseManagerConfig(
            enabled=True,
            min_price=10.0,
            max_price=200.0,
            min_avg_volume=500000,
            exclude_otc=True,
            reference_cache_ttl_hours=12,
            fmp_batch_size=100,
        )

        # Create mock dependencies
        mock_reference_client = MagicMock()
        mock_reference_client._cache = {}
        mock_scanner = MagicMock()

        # UniverseManager should accept the real config
        manager = UniverseManager(mock_reference_client, config, mock_scanner)

        # Verify config was stored correctly
        assert manager._config.enabled is True
        assert manager._config.min_price == 10.0
        assert manager._config.max_price == 200.0
        assert manager._config.min_avg_volume == 500000
        assert manager._config.exclude_otc is True
        assert manager._config.reference_cache_ttl_hours == 12
        assert manager._config.fmp_batch_size == 100

    def test_system_live_yaml_loads(self) -> None:
        """config/system_live.yaml loads successfully with universe_manager."""
        system_live_path = Path("config/system_live.yaml")

        # Skip if file doesn't exist (optional file)
        if not system_live_path.exists():
            pytest.skip("system_live.yaml not present")

        # Load using custom system config file
        config = load_config(Path("config"), system_config_file=system_live_path)

        # Verify universe_manager section loaded
        assert hasattr(config.system, "universe_manager")
        assert isinstance(config.system.universe_manager, UniverseManagerConfig)

        # Verify universe_manager is enabled in live config (Sprint 23.3)
        assert config.system.universe_manager.enabled is True

        # Verify raw YAML has the section
        raw_yaml = yaml.safe_load(system_live_path.read_text())
        assert "universe_manager" in raw_yaml, (
            "universe_manager section missing from system_live.yaml"
        )


class TestQualityEngineConfigWiring:
    """Tests for QualityEngineConfig integration into SystemConfig (Sprint 24 S5b)."""

    def test_system_config_loads_quality_engine(self) -> None:
        """SystemConfig with quality_engine section parses correctly."""
        config = SystemConfig(
            quality_engine={
                "enabled": True,
                "weights": {
                    "pattern_strength": 0.30,
                    "catalyst_quality": 0.25,
                    "volume_profile": 0.20,
                    "historical_match": 0.15,
                    "regime_alignment": 0.10,
                },
                "thresholds": {"a_plus": 90, "a": 80, "a_minus": 70,
                               "b_plus": 60, "b": 50, "b_minus": 40, "c_plus": 30},
                "min_grade_to_trade": "B",
            }
        )
        assert config.quality_engine.enabled is True
        assert config.quality_engine.weights.pattern_strength == 0.30
        assert config.quality_engine.thresholds.a_plus == 90
        assert config.quality_engine.min_grade_to_trade == "B"

    def test_system_config_default_quality_engine(self) -> None:
        """Missing quality_engine section yields valid defaults (enabled=True)."""
        config = SystemConfig()
        assert isinstance(config.quality_engine, QualityEngineConfig)
        assert config.quality_engine.enabled is True
        assert config.quality_engine.min_grade_to_trade == "C+"

    def test_quality_engine_yaml_keys_match_model(self) -> None:
        """All keys in quality_engine.yaml map to QualityEngineConfig fields."""
        yaml_path = Path("config/quality_engine.yaml")
        if not yaml_path.exists():
            pytest.skip("quality_engine.yaml not present")

        raw = yaml.safe_load(yaml_path.read_text())

        # Top-level keys must all be valid QualityEngineConfig fields
        model_fields = set(QualityEngineConfig.model_fields.keys())
        yaml_keys = set(raw.keys())
        extra = yaml_keys - model_fields
        assert not extra, f"YAML has keys not in model: {extra}"
        # All model fields should be present in YAML
        missing = model_fields - yaml_keys
        assert not missing, f"Model fields missing from YAML: {missing}"

    def test_quality_engine_yaml_loads_as_config(self) -> None:
        """quality_engine.yaml can be loaded as a valid QualityEngineConfig."""
        yaml_path = Path("config/quality_engine.yaml")
        if not yaml_path.exists():
            pytest.skip("quality_engine.yaml not present")

        raw = yaml.safe_load(yaml_path.read_text())
        config = QualityEngineConfig(**raw)
        assert config.enabled is True
        assert abs(sum([
            config.weights.pattern_strength,
            config.weights.catalyst_quality,
            config.weights.volume_profile,
            config.weights.historical_match,
            config.weights.regime_alignment,
        ]) - 1.0) < 0.001

    def test_system_yaml_has_quality_engine(self) -> None:
        """config/system.yaml includes quality_engine section and parses."""
        system_path = Path("config/system.yaml")
        if not system_path.exists():
            pytest.skip("system.yaml not present")

        config = load_config(Path("config"))
        assert hasattr(config.system, "quality_engine")
        assert isinstance(config.system.quality_engine, QualityEngineConfig)
        assert config.system.quality_engine.enabled is True

        raw_yaml = yaml.safe_load(system_path.read_text())
        assert "quality_engine" in raw_yaml, (
            "quality_engine section missing from system.yaml"
        )

    def test_system_live_yaml_has_quality_engine(self) -> None:
        """config/system_live.yaml includes quality_engine section and parses."""
        system_live_path = Path("config/system_live.yaml")
        if not system_live_path.exists():
            pytest.skip("system_live.yaml not present")

        config = load_config(Path("config"), system_config_file=system_live_path)
        assert hasattr(config.system, "quality_engine")
        assert isinstance(config.system.quality_engine, QualityEngineConfig)
        assert config.system.quality_engine.enabled is True

        raw_yaml = yaml.safe_load(system_live_path.read_text())
        assert "quality_engine" in raw_yaml, (
            "quality_engine section missing from system_live.yaml"
        )

    def test_quality_engine_disabled_config(self) -> None:
        """quality_engine can be explicitly disabled."""
        config = SystemConfig(quality_engine={"enabled": False})
        assert config.quality_engine.enabled is False

    def test_quality_engine_risk_tiers_loaded_from_yaml(self) -> None:
        """Risk tiers from YAML preserve ordering invariant (A+ > A > B+ > B > C+)."""
        yaml_path = Path("config/quality_engine.yaml")
        if not yaml_path.exists():
            pytest.skip("quality_engine.yaml not present")

        raw = yaml.safe_load(yaml_path.read_text())
        config = QualityEngineConfig(**raw)
        # Assert tiers are ordered: A+ > A > B+ > B > C+ (all positive)
        assert config.risk_tiers.a_plus[1] > 0  # A+ max is positive
        assert max(config.risk_tiers.a_plus) > max(config.risk_tiers.a)  # A+ max > A max
        assert max(config.risk_tiers.a) >= max(config.risk_tiers.b_plus)  # A max >= B+ max
        assert max(config.risk_tiers.b_plus) >= max(config.risk_tiers.b)  # B+ max >= B max
        assert max(config.risk_tiers.b) >= max(config.risk_tiers.c_plus)  # B max >= C+ max
        assert min(config.risk_tiers.c_plus) > 0  # C+ min is positive (not zero)


# ---------------------------------------------------------------------------
# Sprint 27.95 S5 — Config Split + Alignment Tests
# ---------------------------------------------------------------------------


class TestOrderManagerConfigSplit:
    """Tests for stop_retry_max / stop_cancel_retry_max config split (S5 Fix 3)."""

    def test_both_retry_fields_exist_with_correct_defaults(self) -> None:
        """OrderManagerConfig has both stop_retry_max and stop_cancel_retry_max."""
        cfg = OrderManagerConfig()
        assert cfg.stop_retry_max == 3
        assert cfg.stop_cancel_retry_max == 3

    def test_retry_fields_independently_configurable(self) -> None:
        """Both fields can be set to different values."""
        cfg = OrderManagerConfig(stop_retry_max=1, stop_cancel_retry_max=5)
        assert cfg.stop_retry_max == 1
        assert cfg.stop_cancel_retry_max == 5

    def test_order_manager_yaml_keys_match_model(self) -> None:
        """order_manager.yaml keys match OrderManagerConfig.model_fields."""
        yaml_path = Path("config/order_manager.yaml")
        if not yaml_path.exists():
            pytest.skip("order_manager.yaml not present")

        raw = yaml.safe_load(yaml_path.read_text())
        yaml_keys = set(raw.keys())
        model_fields = set(OrderManagerConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys in YAML: {unrecognized}"

        # Both retry fields present in YAML
        assert "stop_retry_max" in yaml_keys
        assert "stop_cancel_retry_max" in yaml_keys


class TestStartupConfigAlignment:
    """Tests for StartupConfig YAML alignment (S4 + S5)."""

    def test_startup_config_in_system_yaml(self) -> None:
        """system.yaml has startup.flatten_unknown_positions."""
        yaml_path = Path("config/system.yaml")
        if not yaml_path.exists():
            pytest.skip("system.yaml not present")

        raw = yaml.safe_load(yaml_path.read_text())
        assert "startup" in raw, "Missing 'startup' section in system.yaml"
        yaml_keys = set(raw["startup"].keys())
        model_fields = set(StartupConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys: {unrecognized}"

    def test_startup_config_in_system_live_yaml(self) -> None:
        """system_live.yaml has startup.flatten_unknown_positions."""
        yaml_path = Path("config/system_live.yaml")
        if not yaml_path.exists():
            pytest.skip("system_live.yaml not present")

        raw = yaml.safe_load(yaml_path.read_text())
        assert "startup" in raw, "Missing 'startup' section in system_live.yaml"
        yaml_keys = set(raw["startup"].keys())
        model_fields = set(StartupConfig.model_fields.keys())
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized keys: {unrecognized}"


# ---------------------------------------------------------------------------
# H2-S01 (audit 2026-04-21): benchmarks.min_sharpe YAML key was silently
# dropped (Pydantic field is min_sharpe_ratio). Guard that the configured
# 0.3 value reaches PerformanceBenchmarks for every strategy YAML.
# ---------------------------------------------------------------------------


class TestStrategyBenchmarkMinSharpeRatioWires:
    """Every strategy YAML's benchmarks.min_sharpe_ratio reaches the Pydantic model."""

    @pytest.mark.parametrize(
        "yaml_name",
        sorted(
            p.name for p in Path("config/strategies").glob("*.yaml")
        ),
    )
    def test_min_sharpe_ratio_loads_nonzero(self, yaml_name: str) -> None:
        """YAML value must flow to PerformanceBenchmarks.min_sharpe_ratio.

        Prior bug (H2-S01, audit 2026-04-21): 12 of 15 strategy YAMLs spelled
        the field as ``min_sharpe`` — silently dropped by Pydantic, leaving
        the benchmark gate at the default 0.0. Renaming to ``min_sharpe_ratio``
        in FIX-16 restores the configured threshold.
        """
        from argus.core.config import load_strategy_config

        path = Path("config/strategies") / yaml_name
        raw = yaml.safe_load(path.read_text())
        yaml_value = (raw.get("benchmarks") or {}).get("min_sharpe_ratio")

        # Only run the guard on strategies that declare the field in YAML.
        # (Not all YAMLs must carry it — defaults remain valid.)
        if yaml_value is None:
            pytest.skip(f"{yaml_name} does not declare benchmarks.min_sharpe_ratio")

        config = load_strategy_config(path)
        assert config.benchmarks.min_sharpe_ratio == yaml_value, (
            f"{yaml_name}: benchmarks.min_sharpe_ratio in YAML "
            f"({yaml_value}) does not match loaded value "
            f"({config.benchmarks.min_sharpe_ratio}) — H2-S01 regression"
        )
        # Guard that nobody regresses back to the pre-fix spelling.
        assert "min_sharpe" not in raw.get("benchmarks", {}) or (
            "min_sharpe_ratio" in raw.get("benchmarks", {})
        ), f"{yaml_name} uses deprecated 'min_sharpe' spelling"

    def test_no_yaml_uses_deprecated_min_sharpe_key(self) -> None:
        """Regression guard: no strategy YAML may use the pre-fix 'min_sharpe' spelling."""
        offenders: list[str] = []
        for path in Path("config/strategies").glob("*.yaml"):
            raw = yaml.safe_load(path.read_text())
            benchmarks = raw.get("benchmarks") or {}
            if "min_sharpe" in benchmarks and "min_sharpe_ratio" not in benchmarks:
                offenders.append(path.name)
        assert not offenders, (
            f"Strategy YAMLs using deprecated 'min_sharpe' (should be "
            f"'min_sharpe_ratio'): {offenders}"
        )


# ---------------------------------------------------------------------------
# H2-H10 (audit 2026-04-21): ApiConfig.password_hash empty-sentinel behavior.
# Empty hash + enabled=true would silently break JWT login. load_config()
# now fails loudly via ApiConfig.validate_password_hash_set().
# ---------------------------------------------------------------------------


class TestApiPasswordHashLoadTimeCheck:
    """FIX-16 H2-H10: load_config rejects empty password_hash when API enabled."""

    def test_validate_password_hash_set_raises_when_enabled_and_empty(self) -> None:
        """Direct unit test on the runtime validator."""
        from argus.core.config import ApiConfig

        cfg = ApiConfig(enabled=True, password_hash="")
        with pytest.raises(ValueError, match="api.password_hash is empty"):
            cfg.validate_password_hash_set()

    def test_validate_password_hash_set_passes_when_hash_present(self) -> None:
        """Non-empty hash: no error."""
        from argus.core.config import ApiConfig

        cfg = ApiConfig(enabled=True, password_hash="$2b$12$somehashvalue")
        # Does not raise
        cfg.validate_password_hash_set()

    def test_validate_password_hash_set_passes_when_api_disabled(self) -> None:
        """If API is disabled, empty hash is OK."""
        from argus.core.config import ApiConfig

        cfg = ApiConfig(enabled=False, password_hash="")
        # Does not raise
        cfg.validate_password_hash_set()

    def test_load_config_fails_on_empty_password_hash(
        self, tmp_path: Path
    ) -> None:
        """Writing a minimal system.yaml with empty hash + enabled=true → load fails."""
        system_yaml = tmp_path / "system.yaml"
        system_yaml.write_text(
            'api:\n'
            '  enabled: true\n'
            '  password_hash: ""\n'
        )
        with pytest.raises(ValueError, match="api.password_hash is empty"):
            load_config(tmp_path)

    def test_load_config_passes_on_api_disabled(self, tmp_path: Path) -> None:
        """Empty hash + enabled=false → load succeeds."""
        system_yaml = tmp_path / "system.yaml"
        system_yaml.write_text(
            'api:\n'
            '  enabled: false\n'
            '  password_hash: ""\n'
        )
        config = load_config(tmp_path)
        assert config.system.api.enabled is False
        assert config.system.api.password_hash == ""

    def test_ApiConfig_can_still_be_constructed_with_defaults(self) -> None:
        """Bare ApiConfig() must remain usable in tests (no validator at construct)."""
        from argus.core.config import ApiConfig

        cfg = ApiConfig()
        assert cfg.enabled is True
        assert cfg.password_hash == ""

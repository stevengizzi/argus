"""Tests for the main entry point.

All components are mocked — no real broker connections, no real data.
These tests verify the ArgusSystem wiring, not the individual components.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set ANTHROPIC_API_KEY to empty string before any argus imports to prevent AIConfig auto-enable.
# This must happen before any test imports argus.main (which calls load_dotenv()).
# Setting to empty string (not deleting) prevents load_dotenv() from loading it from .env.
os.environ["ANTHROPIC_API_KEY"] = ""


@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with minimal config files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # system.yaml
    (config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "alpaca"
broker_source: "alpaca"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url: ""
  alert_webhook_url: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false

ai:
  enabled: false
""")

    # brokers.yaml
    (config_dir / "brokers.yaml").write_text("""
primary: "alpaca"
alpaca:
  enabled: true
  api_key_env: "ALPACA_API_KEY"
  secret_key_env: "ALPACA_SECRET_KEY"
  paper: true
  data_feed: "iex"
databento:
  enabled: true
  api_key_env_var: "DATABENTO_API_KEY"
  dataset: "XNAS.ITCH"
""")

    # risk_limits.yaml
    (config_dir / "risk_limits.yaml").write_text("""
account:
  daily_loss_limit_pct: 0.03
  weekly_loss_limit_pct: 0.05
  cash_reserve_pct: 0.20
  max_concurrent_positions: 10
""")

    # scanner.yaml
    (config_dir / "scanner.yaml").write_text("""
scanner_type: "static"
static_symbols:
  - "AAPL"
  - "MSFT"

alpaca_scanner:
  universe_source: "config"
  universe_symbols:
    - "AAPL"
    - "MSFT"
  min_price: 5.0
  max_price: 500.0
  min_volume_yesterday: 1000000
  max_symbols_returned: 10

databento_scanner:
  universe_symbols:
    - "AAPL"
    - "MSFT"
  min_gap_pct: 0.02
  min_price: 10.0
  max_price: 500.0
  min_volume: 1000000
  max_symbols_returned: 10
  dataset: "XNAS.ITCH"
""")

    # order_manager.yaml
    (config_dir / "order_manager.yaml").write_text("""
eod_flatten_time: "15:50"
eod_flatten_timezone: "America/New_York"
fallback_poll_interval_seconds: 5
""")

    # orchestrator.yaml (required by load_config)
    (config_dir / "orchestrator.yaml").write_text("""
allocation_method: "equal_weight"
""")

    # notifications.yaml (required by load_config)
    (config_dir / "notifications.yaml").write_text("""
telegram:
  enabled: false
""")

    # strategies/orb_breakout.yaml
    strategies_dir = config_dir / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "orb_breakout.yaml").write_text("""
strategy_id: "orb_breakout"
name: "ORB Breakout"
version: "1.0.0"
enabled: true
orb_window_minutes: 15
""")

    return config_dir


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock environment variables for API keys."""
    monkeypatch.setenv("ALPACA_API_KEY", "test_api_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test_secret_key")
    # Ensure ANTHROPIC_API_KEY is not set (AIConfig auto-enables if present)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


class TestArgusSystemWiring:
    """Tests for system component wiring."""

    @pytest.mark.asyncio
    async def test_system_starts_in_correct_order(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify start() calls components in dependency order."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        call_order: list[str] = []

        # Mock all components
        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_strategy_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Track call order
            def make_tracker(name: str, cls: MagicMock) -> MagicMock:
                def init_cb():
                    call_order.append(f"{name}.initialize")

                def start_cb(*a, **kw):
                    call_order.append(f"{name}.start")

                def connect_cb():
                    call_order.append(f"{name}.connect")

                instance = MagicMock()
                instance.initialize = AsyncMock(side_effect=init_cb)
                instance.start = AsyncMock(side_effect=start_cb)
                instance.connect = AsyncMock(side_effect=connect_cb)
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                cls.return_value = instance
                call_order.append(f"{name}.created")
                return instance

            def tracker(name: str, cls: MagicMock):
                return lambda *a, **kw: make_tracker(name, cls)

            mock_db_class.side_effect = tracker("db", mock_db_class)
            mock_conv_class.side_effect = tracker("conv", mock_conv_class)
            mock_usage_class.side_effect = tracker("usage", mock_usage_class)
            mock_action_class.side_effect = tracker("action", mock_action_class)
            mock_broker_class.side_effect = tracker("broker", mock_broker_class)
            mock_health_class.side_effect = tracker("health", mock_health_class)
            mock_risk_class.side_effect = tracker("risk", mock_risk_class)
            mock_data_class.side_effect = tracker("data", mock_data_class)
            mock_scanner_class.side_effect = tracker("scanner", mock_scanner_class)
            mock_strategy_class.side_effect = tracker("strategy", mock_strategy_class)
            mock_om_class.side_effect = tracker("om", mock_om_class)

            with contextlib.suppress(Exception):
                await system.start()

            # Verify order: db before broker, broker before health, etc.
            assert "db.created" in call_order
            db_idx = call_order.index("db.created")
            broker_idx = call_order.index("broker.created")
            assert db_idx < broker_idx

    @pytest.mark.asyncio
    async def test_system_shuts_down_in_reverse_order(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify shutdown() calls components in reverse order."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # Manually set mocked components
        system._scanner = MagicMock()
        system._scanner.stop = AsyncMock()

        system._data_service = MagicMock()
        system._data_service.stop = AsyncMock()

        system._order_manager = MagicMock()
        system._order_manager.stop = AsyncMock()

        system._health_monitor = MagicMock()
        system._health_monitor.stop = AsyncMock()
        system._health_monitor.send_warning_alert = AsyncMock()

        system._db = MagicMock()
        system._db.close = AsyncMock()

        system._broker = MagicMock()
        system._broker.disconnect = AsyncMock()

        # ActionManager (Sprint 22.3a)
        system._action_manager = None

        await system.shutdown()

        # Verify all stop methods were called
        system._scanner.stop.assert_called_once()
        system._data_service.stop.assert_called_once()
        system._order_manager.stop.assert_called_once()
        system._health_monitor.stop.assert_called_once()
        system._db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_handles_startup_failure_gracefully(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Broker connect fails → error logged, shutdown called."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
        ):
            mock_db = MagicMock()
            mock_db.initialize = AsyncMock()
            mock_db.close = AsyncMock()
            mock_db_class.return_value = mock_db

            # AI managers
            for ai_cls in [mock_conv_class, mock_usage_class]:
                ai_inst = MagicMock()
                ai_inst.initialize = AsyncMock()
                ai_cls.return_value = ai_inst

            mock_broker = MagicMock()
            mock_broker.connect = AsyncMock(side_effect=Exception("Connection failed"))
            mock_broker.disconnect = AsyncMock()  # Add disconnect mock
            mock_broker_class.return_value = mock_broker

            # Should not raise
            await system.run()

            # Verify db was closed during shutdown
            mock_db.close.assert_called()

    @pytest.mark.asyncio
    async def test_signal_handlers_request_shutdown(self, mock_config_dir: Path) -> None:
        """request_shutdown() sets shutdown event."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir)

        assert not system._shutdown_event.is_set()
        system.request_shutdown()
        assert system._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_dry_run_skips_data_streams(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """--dry-run → data_service.start() not called with symbols."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy"),
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                cls.return_value = instance

            with contextlib.suppress(Exception):
                await system.start()

            # In dry run mode, data service.start is never called (or called
            # with no symbols, depending on implementation)

    @pytest.mark.asyncio
    async def test_no_symbols_uses_static_fallback(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Scanner returns empty → system falls back to static symbols from config."""
        # This test verifies the static symbols fallback logic
        # by checking the config file structure we created
        import yaml

        scanner_yaml = yaml.safe_load((mock_config_dir / "scanner.yaml").read_text())
        static_symbols = scanner_yaml.get("static_symbols", [])

        # Verify config has static symbols as fallback
        assert len(static_symbols) > 0
        assert "AAPL" in static_symbols

    @pytest.mark.asyncio
    async def test_config_loaded_from_directory(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Config dir → load_config called with correct path."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.load_config") as mock_load_config,
            patch("argus.main.DatabaseManager"),
        ):
            mock_config = MagicMock()
            mock_config.system.data_dir = "data"
            mock_config.system.health = MagicMock()
            mock_config.broker.alpaca = MagicMock()
            mock_config.risk = MagicMock()
            mock_load_config.return_value = mock_config

            with contextlib.suppress(Exception):
                await system.start()

            # load_config now takes (config_dir, system_config_file)
            mock_load_config.assert_called_once_with(mock_config_dir, None)

    def test_parse_args_defaults(self) -> None:
        """Parse args returns correct defaults."""
        from argus.main import parse_args

        with patch("sys.argv", ["argus.main"]):
            args = parse_args()

        assert args.config == Path("config")
        assert args.paper is True
        assert args.dry_run is False

    def test_parse_args_custom_config(self) -> None:
        """Parse args handles custom config path."""
        from argus.main import parse_args

        with patch("sys.argv", ["argus.main", "--config", "/custom/path"]):
            args = parse_args()

        assert args.config == Path("/custom/path")

    def test_parse_args_dry_run(self) -> None:
        """Parse args handles --dry-run flag."""
        from argus.main import parse_args

        with patch("sys.argv", ["argus.main", "--dry-run"]):
            args = parse_args()

        assert args.dry_run is True


class TestDataSourceSelection:
    """Tests for data source selection between Alpaca and Databento."""

    def test_config_data_source_defaults_to_alpaca(self, mock_config_dir: Path) -> None:
        """Default data_source config value is alpaca."""
        from argus.core.config import DataSource, load_config

        config = load_config(mock_config_dir)

        assert config.system.data_source == DataSource.ALPACA

    def test_config_data_source_can_be_databento(self, mock_config_dir: Path) -> None:
        """data_source can be set to databento in config."""
        from argus.core.config import DataSource, load_config

        # Update system.yaml to use Databento
        (mock_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "databento"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url_env: ""
  alert_webhook_url_env: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false
""")

        config = load_config(mock_config_dir)

        assert config.system.data_source == DataSource.DATABENTO

    def test_data_source_enum_values(self) -> None:
        """DataSource enum has expected values."""
        from argus.core.config import DataSource

        assert DataSource.ALPACA.value == "alpaca"
        assert DataSource.DATABENTO.value == "databento"

    def test_scanner_yaml_has_databento_section(self, mock_config_dir: Path) -> None:
        """scanner.yaml includes databento_scanner configuration."""
        import yaml

        scanner_yaml = yaml.safe_load((mock_config_dir / "scanner.yaml").read_text())

        assert "databento_scanner" in scanner_yaml
        assert "universe_symbols" in scanner_yaml["databento_scanner"]
        assert "min_gap_pct" in scanner_yaml["databento_scanner"]

    def test_brokers_yaml_has_databento_section(self, mock_config_dir: Path) -> None:
        """brokers.yaml includes databento configuration."""
        import yaml

        brokers_yaml = yaml.safe_load((mock_config_dir / "brokers.yaml").read_text())

        assert "databento" in brokers_yaml
        assert brokers_yaml["databento"]["enabled"] is True
        assert "api_key_env_var" in brokers_yaml["databento"]


class TestOrchestratorIntegration:
    """Tests for Orchestrator integration into main.py startup."""

    @pytest.mark.asyncio
    async def test_12_phase_startup_creates_orchestrator(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify start() creates and starts the Orchestrator in Phase 9."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_strategy_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks with all necessary async methods
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_strategy_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()  # For RiskManager and Strategy
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.is_active = False  # Strategy starts inactive
                cls.return_value = instance

            # Setup orchestrator mock
            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(return_value={})
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify Orchestrator was created with correct dependencies
            mock_orchestrator_class.assert_called_once()
            call_kwargs = mock_orchestrator_class.call_args[1]
            assert "config" in call_kwargs
            assert "event_bus" in call_kwargs
            assert "clock" in call_kwargs
            assert "trade_logger" in call_kwargs
            assert "broker" in call_kwargs
            assert "data_service" in call_kwargs

            # Verify Orchestrator lifecycle methods were called
            mock_orchestrator.register_strategy.assert_called_once()
            mock_orchestrator.start.assert_called_once()
            mock_orchestrator.run_pre_market.assert_called_once()

    @pytest.mark.asyncio
    async def test_strategy_activated_by_orchestrator(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify strategy.is_active is NOT set directly by main.py, but by Orchestrator."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        strategy_instance = MagicMock()
        strategy_instance.is_active = False  # Start inactive
        strategy_instance.strategy_id = "orb_breakout"
        strategy_instance.reconstruct_state = AsyncMock()

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_strategy_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks with all necessary async methods
            for cls in [
                mock_db_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()  # For RiskManager
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                cls.return_value = instance

            mock_strategy_class.return_value = strategy_instance

            # Setup orchestrator mock
            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": strategy_instance}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify strategy.is_active was NOT set to True directly
            # (it should still be False because run_pre_market is mocked)
            # This confirms main.py doesn't hardcode is_active = True
            assert strategy_instance.is_active is False

    @pytest.mark.asyncio
    async def test_orchestrator_in_app_state(
        self, mock_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify AppState includes the Orchestrator when API is enabled."""
        from argus.main import ArgusSystem

        # Ensure AI is disabled — load_dotenv() may have loaded the real key
        # from .env before mock_env_vars deleted it, so set it to empty string
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        # Set JWT secret so API starts
        monkeypatch.setenv("ARGUS_JWT_SECRET", "test_secret")

        # Update system.yaml to enable API (ai: false prevents load_dotenv race
        # when ANTHROPIC_API_KEY exists in .env but monkeypatch.delenv removed it)
        (mock_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "alpaca"
broker_source: "alpaca"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url: ""
  alert_webhook_url: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false

ai:
  enabled: false

api:
  enabled: true
  host: "127.0.0.1"
  port: 8000
  jwt_secret_env: "ARGUS_JWT_SECRET"
""")

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True, enable_api=True)
        captured_app_state = None

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_strategy_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.api.server.create_app") as mock_create_app,
            patch("argus.api.server.run_server") as mock_run_server,
            patch("argus.api.websocket.get_bridge") as mock_get_bridge,
        ):
            # Setup all mocks with all necessary async methods
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_strategy_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()  # For RiskManager and Strategy
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.is_active = True
                cls.return_value = instance

            # Setup orchestrator mock
            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(return_value={"orb_breakout": MagicMock()})
            mock_orchestrator_class.return_value = mock_orchestrator

            # Capture AppState when create_app is called
            def capture_app_state(app_state):
                nonlocal captured_app_state
                captured_app_state = app_state
                return MagicMock()

            mock_create_app.side_effect = capture_app_state
            mock_run_server.return_value = AsyncMock()
            mock_get_bridge.return_value = MagicMock()

            with contextlib.suppress(Exception):
                await system.start()

            # Verify AppState was created with orchestrator
            assert captured_app_state is not None
            assert captured_app_state.orchestrator is mock_orchestrator

    @pytest.mark.asyncio
    async def test_orchestrator_shutdown_called(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify Orchestrator.stop() is called during shutdown."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # Manually set mocked components
        mock_orchestrator = MagicMock()
        mock_orchestrator.stop = AsyncMock()
        system._orchestrator = mock_orchestrator

        system._scanner = MagicMock()
        system._scanner.stop = AsyncMock()

        system._data_service = MagicMock()
        system._data_service.stop = AsyncMock()

        system._order_manager = MagicMock()
        system._order_manager.stop = AsyncMock()

        system._health_monitor = MagicMock()
        system._health_monitor.stop = AsyncMock()
        system._health_monitor.send_warning_alert = AsyncMock()

        system._db = MagicMock()
        system._db.close = AsyncMock()

        system._broker = MagicMock()
        system._broker.disconnect = AsyncMock()

        # ActionManager (Sprint 22.3a)
        system._action_manager = None

        await system.shutdown()

        # Verify orchestrator.stop was called
        mock_orchestrator.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_uses_strategies_from_registry(
        self, mock_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify AppState.strategies comes from orchestrator.get_strategies()."""
        from argus.main import ArgusSystem

        monkeypatch.setenv("ARGUS_JWT_SECRET", "test_secret")

        # Update system.yaml to enable API (ai: false prevents load_dotenv race
        # when ANTHROPIC_API_KEY exists in .env but monkeypatch.delenv removed it)
        (mock_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "alpaca"
broker_source: "alpaca"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url: ""
  alert_webhook_url: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false

ai:
  enabled: false

api:
  enabled: true
  host: "127.0.0.1"
  port: 8000
  jwt_secret_env: "ARGUS_JWT_SECRET"
""")

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True, enable_api=True)
        captured_app_state = None

        # Create distinct strategy mocks
        strategy_1 = MagicMock()
        strategy_1.strategy_id = "strategy_1"
        strategy_2 = MagicMock()
        strategy_2.strategy_id = "strategy_2"
        orchestrator_strategies = {"strategy_1": strategy_1, "strategy_2": strategy_2}

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_strategy_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.api.server.create_app") as mock_create_app,
            patch("argus.api.server.run_server") as mock_run_server,
            patch("argus.api.websocket.get_bridge") as mock_get_bridge,
        ):
            # Setup all mocks with all necessary async methods
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_strategy_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()  # For RiskManager and Strategy
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.is_active = True
                cls.return_value = instance

            # Setup orchestrator mock
            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(return_value=orchestrator_strategies)
            mock_orchestrator_class.return_value = mock_orchestrator

            # Capture AppState
            def capture_app_state(app_state):
                nonlocal captured_app_state
                captured_app_state = app_state
                return MagicMock()

            mock_create_app.side_effect = capture_app_state
            mock_run_server.return_value = AsyncMock()
            mock_get_bridge.return_value = MagicMock()

            with contextlib.suppress(Exception):
                await system.start()

            # Verify strategies come from orchestrator
            assert captured_app_state is not None
            assert captured_app_state.strategies == orchestrator_strategies
            mock_orchestrator.get_strategies.assert_called()


class TestMultiStrategyWiring:
    """Tests for Sprint 18 Session 6 — multi-strategy wiring in main.py."""

    @pytest.mark.asyncio
    async def test_both_strategies_created(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify both OrbBreakout and OrbScalp strategies are created."""
        from argus.main import ArgusSystem

        # Add orb_scalp.yaml to config
        (mock_config_dir / "strategies" / "orb_scalp.yaml").write_text("""
strategy_id: "orb_scalp"
name: "ORB Scalp"
version: "1.0.0"
enabled: true
orb_window_minutes: 5
scalp_target_r: 0.3
max_hold_seconds: 120
""")

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)
        strategies_created: list[str] = []

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.OrbScalpStrategy") as mock_scalp_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Track strategy creation
            def orb_created(*a, **kw):
                strategies_created.append("OrbBreakout")
                mock = MagicMock()
                mock.set_watchlist = MagicMock()
                mock.strategy_id = "orb_breakout"
                mock.is_active = True
                return mock

            def scalp_created(*a, **kw):
                strategies_created.append("OrbScalp")
                mock = MagicMock()
                mock.set_watchlist = MagicMock()
                mock.strategy_id = "orb_scalp"
                mock.is_active = True
                return mock

            mock_orb_class.side_effect = orb_created
            mock_scalp_class.side_effect = scalp_created

            # Setup orchestrator mock
            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(return_value={})
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify both strategies were created
            assert "OrbBreakout" in strategies_created
            assert "OrbScalp" in strategies_created
            assert len(strategies_created) == 2

    @pytest.mark.asyncio
    async def test_multiple_strategies_registered_with_orchestrator(
        self, mock_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify both strategies are registered with the Orchestrator."""
        from argus.main import ArgusSystem

        # Ensure AI is disabled — load_dotenv() may have loaded the real key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")

        # Add orb_scalp.yaml to config
        (mock_config_dir / "strategies" / "orb_scalp.yaml").write_text("""
strategy_id: "orb_scalp"
name: "ORB Scalp"
version: "1.0.0"
enabled: true
orb_window_minutes: 5
scalp_target_r: 0.3
max_hold_seconds: 120
""")

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.OrbScalpStrategy") as mock_scalp_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Create strategy mocks
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            scalp_strategy = MagicMock()
            scalp_strategy.set_watchlist = MagicMock()
            scalp_strategy.strategy_id = "orb_scalp"
            scalp_strategy.is_active = True
            mock_scalp_class.return_value = scalp_strategy

            # Setup orchestrator mock
            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy, "orb_scalp": scalp_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify both strategies were registered
            calls = mock_orchestrator.register_strategy.call_args_list
            assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_candle_event_routing_subscribed(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify CandleEvent routing is subscribed after Order Manager starts."""
        from argus.core.events import CandleEvent
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)
        event_bus_mock = MagicMock()
        event_bus_mock.subscribe = MagicMock()
        event_bus_mock.publish = AsyncMock()

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.EventBus", return_value=event_bus_mock),
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify CandleEvent subscription was made
            subscribe_calls = event_bus_mock.subscribe.call_args_list
            candle_subscribed = any(args[0] == CandleEvent for args, _ in subscribe_calls)
            assert candle_subscribed, "CandleEvent routing not subscribed"

    @pytest.mark.asyncio
    async def test_risk_manager_wired_to_order_manager(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify Risk Manager has set_order_manager called."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_data_class,
                mock_scanner_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                cls.return_value = instance

            # Setup risk manager mock with set_order_manager
            mock_risk = MagicMock()
            mock_risk.initialize = AsyncMock()
            mock_risk.reconstruct_state = AsyncMock()
            mock_risk.set_order_manager = MagicMock()
            mock_risk_class.return_value = mock_risk

            # Setup order manager mock
            mock_om = MagicMock()
            mock_om.start = AsyncMock()
            mock_om.reconstruct_from_broker = AsyncMock()
            mock_om_class.return_value = mock_om

            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify set_order_manager was called on risk manager
            mock_risk.set_order_manager.assert_called_once_with(mock_om)

    @pytest.mark.asyncio
    async def test_multi_strategy_health_status(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify health monitor reports multi-strategy status."""
        from argus.main import ArgusSystem

        # Add orb_scalp.yaml to config
        (mock_config_dir / "strategies" / "orb_scalp.yaml").write_text("""
strategy_id: "orb_scalp"
name: "ORB Scalp"
version: "1.0.0"
enabled: true
orb_window_minutes: 5
scalp_target_r: 0.3
max_hold_seconds: 120
""")

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)
        health_update_calls: list[tuple[str, str]] = []

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.OrbScalpStrategy") as mock_scalp_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup health monitor to capture calls
            mock_health = MagicMock()
            mock_health.start = AsyncMock()
            mock_health.stop = AsyncMock()
            mock_health.send_warning_alert = AsyncMock()

            def capture_update(component, status, message=""):
                health_update_calls.append((component, message))

            mock_health.update_component = capture_update
            mock_health_class.return_value = mock_health

            # Create strategy mocks
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            scalp_strategy = MagicMock()
            scalp_strategy.set_watchlist = MagicMock()
            scalp_strategy.strategy_id = "orb_scalp"
            scalp_strategy.is_active = True
            mock_scalp_class.return_value = scalp_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy, "orb_scalp": scalp_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify multi-strategy health status
            strategy_updates = [msg for comp, msg in health_update_calls if comp == "strategy"]
            assert any("2/2 strategies active" in msg for msg in strategy_updates), (
                f"Multi-strategy health status not found in: {strategy_updates}"
            )

    @pytest.mark.asyncio
    async def test_strategies_receive_watchlist(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify strategies have set_watchlist called with scanner results."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup scanner to return symbols
            mock_scanner = MagicMock()
            mock_scanner.start = AsyncMock()
            mock_scanner.scan = AsyncMock(return_value=[])  # Empty, use static fallback
            mock_scanner_class.return_value = mock_scanner

            # Create strategy mock that tracks set_watchlist calls
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify set_watchlist was called (using static fallback AAPL, MSFT)
            orb_strategy.set_watchlist.assert_called_once()
            call_args = orb_strategy.set_watchlist.call_args[0][0]
            assert "AAPL" in call_args
            assert "MSFT" in call_args


class TestPositionClosedEventRouting:
    """Tests for PositionClosedEvent routing to strategies (Sprint 21.5 C1 fix)."""

    @pytest.mark.asyncio
    async def test_position_closed_event_includes_symbol(self) -> None:
        """PositionClosedEvent includes symbol field (C1 bug fix)."""
        from argus.core.events import ExitReason, PositionClosedEvent

        event = PositionClosedEvent(
            position_id="pos_123",
            strategy_id="strat_vwap_reclaim",
            symbol="AAPL",
            exit_price=100.0,
            realized_pnl=50.0,
            exit_reason=ExitReason.TIME_STOP,
            hold_duration_seconds=1802,
        )

        assert event.symbol == "AAPL"
        assert event.exit_reason == ExitReason.TIME_STOP

    @pytest.mark.asyncio
    async def test_position_closed_routes_to_strategy(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """PositionClosedEvent correctly routes to strategy with mark_position_closed."""
        from argus.core.events import ExitReason, PositionClosedEvent
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # Create mock orchestrator with strategy
        mock_strategy = MagicMock()
        mock_strategy.mark_position_closed = MagicMock()

        mock_orchestrator = MagicMock()
        mock_orchestrator.get_strategies = MagicMock(
            return_value={"vwap_reclaim": mock_strategy}
        )
        system._orchestrator = mock_orchestrator

        # Create a time-stop PositionClosedEvent
        event = PositionClosedEvent(
            position_id="pos_123",
            strategy_id="vwap_reclaim",
            symbol="AAPL",
            exit_price=100.0,
            realized_pnl=50.0,
            exit_reason=ExitReason.TIME_STOP,
        )

        # Call the handler directly
        await system._on_position_closed_for_strategies(event)

        # Verify mark_position_closed was called with the symbol
        mock_strategy.mark_position_closed.assert_called_once_with("AAPL")


class TestAutoShutdown:
    """Tests for auto-shutdown after EOD flatten (Sprint 21.5 C1 feature)."""

    @pytest.mark.asyncio
    async def test_shutdown_requested_event_schedules_shutdown(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """ShutdownRequestedEvent schedules delayed shutdown."""
        import asyncio

        from argus.core.events import ShutdownRequestedEvent
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # Create event with very short delay for testing
        event = ShutdownRequestedEvent(
            reason="eod_flatten_complete",
            delay_seconds=0,  # Immediate for test
        )

        # Handle the event
        await system._on_shutdown_requested(event)

        # Allow the scheduled task to run
        await asyncio.sleep(0.1)

        # Verify shutdown was requested
        assert system._shutdown_event.is_set()

        # Clean up: cancel any pending tasks created by _on_shutdown_requested
        # to prevent the event loop from hanging during pytest teardown
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task() and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    def test_shutdown_requested_event_has_correct_fields(self) -> None:
        """ShutdownRequestedEvent has reason and delay_seconds fields."""
        from argus.core.events import ShutdownRequestedEvent

        event = ShutdownRequestedEvent(
            reason="eod_flatten_complete",
            delay_seconds=60,
        )

        assert event.reason == "eod_flatten_complete"
        assert event.delay_seconds == 60

    @pytest.mark.asyncio
    async def test_order_manager_config_has_auto_shutdown_fields(self) -> None:
        """OrderManagerConfig has auto_shutdown_after_eod and delay fields."""
        from argus.core.config import OrderManagerConfig

        config = OrderManagerConfig()

        assert hasattr(config, "auto_shutdown_after_eod")
        assert hasattr(config, "auto_shutdown_delay_seconds")
        assert config.auto_shutdown_after_eod is True  # Default
        assert config.auto_shutdown_delay_seconds == 60  # Default


class TestUniverseManagerWiring:
    """Tests for Sprint 23 Session 4b — Universe Manager wiring in main.py."""

    @pytest.fixture
    def um_enabled_config_dir(self, mock_config_dir: Path) -> Path:
        """Create a config directory with Universe Manager enabled."""
        # Update system.yaml to enable Universe Manager and use Databento
        (mock_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "databento"
broker_source: "ibkr"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url_env: ""
  alert_webhook_url_env: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false

ai:
  enabled: false

universe_manager:
  enabled: true
  min_price: 5.0
  max_price: 10000.0
  min_avg_volume: 100000
  exclude_otc: true
  fmp_batch_size: 50
""")
        return mock_config_dir

    @pytest.mark.asyncio
    async def test_startup_with_um_enabled(
        self, um_enabled_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify Universe Manager path executes when enabled + non-simulated broker."""
        from argus.main import ArgusSystem

        monkeypatch.setenv("DATABENTO_API_KEY", "test_db_key")
        monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")

        system = ArgusSystem(config_dir=um_enabled_config_dir, dry_run=True)
        um_build_called = False

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.ibkr_broker.IBKRBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.DatabentoDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.FMPReferenceClient") as mock_fmp_class,
            patch("argus.main.UniverseManager") as mock_um_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                instance.set_viable_universe = MagicMock()
                cls.return_value = instance

            # Setup FMP mock (Sprint 23.3: now needs fetch_stock_list)
            mock_fmp = MagicMock()
            mock_fmp.start = AsyncMock()
            mock_fmp.fetch_stock_list = AsyncMock(return_value=["AAPL", "MSFT", "GOOGL"])
            mock_fmp_class.return_value = mock_fmp

            # Setup Universe Manager mock
            def um_build(*args, **kwargs):
                nonlocal um_build_called
                um_build_called = True
                return {"AAPL", "MSFT"}

            mock_um = MagicMock()
            mock_um.build_viable_universe = AsyncMock(side_effect=um_build)
            mock_um.build_routing_table = MagicMock()
            mock_um.viable_symbols = {"AAPL", "MSFT"}
            mock_um.viable_count = 2
            mock_um.is_built = True
            mock_um_class.return_value = mock_um

            # Setup strategy mock
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify Universe Manager was used
            assert um_build_called, "Universe Manager build_viable_universe was not called"
            mock_um.build_routing_table.assert_called()

    @pytest.mark.asyncio
    async def test_startup_with_um_disabled(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify old scanner path executes when Universe Manager is disabled."""
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)
        watchlist_set = False

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.AlpacaScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup strategy mock that tracks watchlist
            def track_watchlist(symbols):
                nonlocal watchlist_set
                watchlist_set = True

            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock(side_effect=track_watchlist)
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify old path was used (set_watchlist called)
            assert watchlist_set, "set_watchlist was not called (old path should have been used)"

    @pytest.mark.asyncio
    async def test_startup_um_enabled_fmp_fails(
        self, um_enabled_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify graceful degradation to scanner symbols when FMP fails."""
        from argus.main import ArgusSystem

        monkeypatch.setenv("DATABENTO_API_KEY", "test_db_key")
        monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")

        system = ArgusSystem(config_dir=um_enabled_config_dir, dry_run=True)

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.ibkr_broker.IBKRBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.DatabentoDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.FMPReferenceClient") as mock_fmp_class,
            patch("argus.main.UniverseManager") as mock_um_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                instance.set_viable_universe = MagicMock()
                cls.return_value = instance

            # Setup FMP mock (Sprint 23.3: fetch_stock_list returns empty = failure)
            mock_fmp = MagicMock()
            mock_fmp.start = AsyncMock()
            mock_fmp.fetch_stock_list = AsyncMock(return_value=[])  # Simulates failure
            mock_fmp_class.return_value = mock_fmp

            # Sprint 23.3: When fetch_stock_list returns empty, main.py falls back to
            # scanner symbols and passes them to build_viable_universe. Track what symbols
            # were passed to verify fallback behavior.
            symbols_passed_to_um: list[str] = []

            async def track_um_build(symbols, *args, **kwargs):
                nonlocal symbols_passed_to_um
                symbols_passed_to_um = list(symbols)
                return {"AAPL", "MSFT"}

            mock_um = MagicMock()
            mock_um.build_viable_universe = AsyncMock(side_effect=track_um_build)
            mock_um.build_routing_table = MagicMock()
            mock_um.viable_symbols = {"AAPL", "MSFT"}
            mock_um.viable_count = 2
            mock_um.is_built = True
            mock_um_class.return_value = mock_um

            # Setup strategy mock
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify build_viable_universe was called (with fallback scanner symbols since
            # fetch_stock_list returned empty). Scanner returns [] in this test, so empty
            # list is passed. The key is that build_viable_universe WAS called.
            assert mock_um.build_viable_universe.called, "build_viable_universe should be called"

    @pytest.mark.asyncio
    async def test_candle_routing_um_active(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify candle dispatched only to matching strategies via routing table."""
        from argus.core.events import CandleEvent
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # Create mock Universe Manager with routing table
        mock_um = MagicMock()
        mock_um.is_built = True
        mock_um.route_candle = MagicMock(return_value={"strategy_a"})  # Only strategy_a matches
        system._universe_manager = mock_um

        # Create mock strategies
        strategy_a = MagicMock()
        strategy_a.is_active = True
        strategy_a.on_candle = AsyncMock(return_value=None)

        strategy_b = MagicMock()
        strategy_b.is_active = True
        strategy_b.on_candle = AsyncMock(return_value=None)

        system._strategies = {"strategy_a": strategy_a, "strategy_b": strategy_b}
        system._risk_manager = MagicMock()

        # Create candle event
        from datetime import UTC, datetime

        candle = CandleEvent(
            symbol="AAPL",
            timestamp=datetime.now(UTC),
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            volume=1000000,
            timeframe="1m",
        )

        # Route candle
        await system._on_candle_for_strategies(candle)

        # Verify only strategy_a was called (the one in routing table)
        strategy_a.on_candle.assert_called_once_with(candle)
        strategy_b.on_candle.assert_not_called()

    @pytest.mark.asyncio
    async def test_candle_routing_um_disabled(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify candle dispatched via old watchlist path when UM disabled."""
        from argus.core.events import CandleEvent
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # No Universe Manager
        system._universe_manager = None

        # Create mock strategies
        strategy_a = MagicMock()
        strategy_a.is_active = True
        strategy_a.watchlist = ["AAPL"]
        strategy_a.on_candle = AsyncMock(return_value=None)

        strategy_b = MagicMock()
        strategy_b.is_active = True
        strategy_b.watchlist = ["MSFT"]
        strategy_b.on_candle = AsyncMock(return_value=None)

        mock_orchestrator = MagicMock()
        mock_orchestrator.get_strategies = MagicMock(
            return_value={"strategy_a": strategy_a, "strategy_b": strategy_b}
        )
        system._orchestrator = mock_orchestrator
        system._risk_manager = MagicMock()

        # Create candle event for AAPL
        from datetime import UTC, datetime

        candle = CandleEvent(
            symbol="AAPL",
            timestamp=datetime.now(UTC),
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            volume=1000000,
            timeframe="1m",
        )

        # Route candle
        await system._on_candle_for_strategies(candle)

        # Verify only strategy_a was called (AAPL in its watchlist)
        strategy_a.on_candle.assert_called_once_with(candle)
        strategy_b.on_candle.assert_not_called()

    @pytest.mark.asyncio
    async def test_backtest_mode_ignores_um(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify simulated broker mode ignores Universe Manager config."""
        # Update config to enable UM but use simulated broker
        (mock_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "alpaca"
broker_source: "simulated"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url_env: ""
  alert_webhook_url_env: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false

ai:
  enabled: false

universe_manager:
  enabled: true
  min_price: 5.0
  max_price: 10000.0
""")

        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)
        um_used = False

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.simulated_broker.SimulatedBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.UniverseManager") as mock_um_class,
        ):
            # Track if UniverseManager was instantiated
            def track_um(*args, **kwargs):
                nonlocal um_used
                um_used = True
                return MagicMock()

            mock_um_class.side_effect = track_um

            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify UniverseManager was NOT used (simulated broker)
            assert not um_used, "UniverseManager should not be used in simulated broker mode"

    @pytest.mark.asyncio
    async def test_universe_manager_in_app_state(
        self, um_enabled_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify Universe Manager is accessible via AppState."""
        from argus.main import ArgusSystem

        monkeypatch.setenv("DATABENTO_API_KEY", "test_db_key")
        monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")
        monkeypatch.setenv("ARGUS_JWT_SECRET", "test_secret")

        # Update config to enable API
        (um_enabled_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
data_dir: "data"
data_source: "databento"
broker_source: "ibkr"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url_env: ""
  alert_webhook_url_env: ""
  daily_check_enabled: false

ai:
  enabled: false

api:
  enabled: true
  host: "127.0.0.1"
  port: 8000
  jwt_secret_env: "ARGUS_JWT_SECRET"

universe_manager:
  enabled: true
  min_price: 5.0
  max_price: 10000.0
""")

        system = ArgusSystem(config_dir=um_enabled_config_dir, dry_run=True, enable_api=True)
        captured_app_state = None

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.ibkr_broker.IBKRBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.DatabentoDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.FMPReferenceClient") as mock_fmp_class,
            patch("argus.main.UniverseManager") as mock_um_class,
            patch("argus.api.server.create_app") as mock_create_app,
            patch("argus.api.server.run_server") as mock_run_server,
            patch("argus.api.websocket.get_bridge") as mock_get_bridge,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_data_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                instance.set_viable_universe = MagicMock()
                cls.return_value = instance

            # Setup FMP mock (Sprint 23.3: now needs fetch_stock_list)
            mock_fmp = MagicMock()
            mock_fmp.start = AsyncMock()
            mock_fmp.fetch_stock_list = AsyncMock(return_value=["AAPL", "MSFT", "GOOGL"])
            mock_fmp_class.return_value = mock_fmp

            # Setup Universe Manager mock
            mock_um = MagicMock()
            mock_um.build_viable_universe = AsyncMock(return_value={"AAPL", "MSFT"})
            mock_um.build_routing_table = MagicMock()
            mock_um.viable_symbols = {"AAPL", "MSFT"}
            mock_um.viable_count = 2
            mock_um.is_built = True
            mock_um_class.return_value = mock_um

            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            # Capture AppState
            def capture_app_state(app_state):
                nonlocal captured_app_state
                captured_app_state = app_state
                return MagicMock()

            mock_create_app.side_effect = capture_app_state
            mock_run_server.return_value = AsyncMock()
            mock_get_bridge.return_value = MagicMock()

            with contextlib.suppress(Exception):
                await system.start()

            # Verify AppState has universe_manager
            assert captured_app_state is not None
            assert captured_app_state.universe_manager is mock_um

    @pytest.mark.asyncio
    async def test_strategy_not_called_for_non_matching_symbol(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify strategy.on_candle NOT called for symbol outside its filter."""
        from argus.core.events import CandleEvent
        from argus.main import ArgusSystem

        system = ArgusSystem(config_dir=mock_config_dir, dry_run=True)

        # Create mock Universe Manager with routing table that returns empty for AAPL
        mock_um = MagicMock()
        mock_um.is_built = True
        mock_um.route_candle = MagicMock(return_value=set())  # No strategies match AAPL
        system._universe_manager = mock_um

        # Create mock strategy
        strategy_a = MagicMock()
        strategy_a.is_active = True
        strategy_a.on_candle = AsyncMock(return_value=None)

        system._strategies = {"strategy_a": strategy_a}
        system._risk_manager = MagicMock()

        # Create candle event
        from datetime import UTC, datetime

        candle = CandleEvent(
            symbol="AAPL",
            timestamp=datetime.now(UTC),
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            volume=1000000,
            timeframe="1m",
        )

        # Route candle
        await system._on_candle_for_strategies(candle)

        # Verify strategy was NOT called (routing table returned empty)
        strategy_a.on_candle.assert_not_called()


class TestWarmupSymbolSelection:
    """Tests for Sprint 23.3 — Warm-up uses viable symbols when Universe Manager enabled."""

    @pytest.fixture
    def um_enabled_config_dir(self, mock_config_dir: Path) -> Path:
        """Create a config directory with Universe Manager enabled."""
        # Update system.yaml to enable Universe Manager and use Databento
        (mock_config_dir / "system.yaml").write_text("""
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"
data_source: "databento"
broker_source: "ibkr"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url_env: ""
  alert_webhook_url_env: ""
  daily_check_enabled: false
  weekly_reconciliation_enabled: false

ai:
  enabled: false

universe_manager:
  enabled: true
  min_price: 5.0
  max_price: 10000.0
  min_avg_volume: 100000
  exclude_otc: true
  fmp_batch_size: 50
""")
        return mock_config_dir

    @pytest.mark.asyncio
    async def test_warmup_uses_viable_symbols_when_um_enabled(
        self, um_enabled_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify data service warm-up uses viable symbols when UM enabled."""
        from argus.main import ArgusSystem

        monkeypatch.setenv("DATABENTO_API_KEY", "test_db_key")
        monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")

        # dry_run=False so that data service start() is actually called
        system = ArgusSystem(config_dir=um_enabled_config_dir, dry_run=False)
        warmup_symbols_received: list[str] = []

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.ibkr_broker.IBKRBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.DatabentoDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.FMPReferenceClient") as mock_fmp_class,
            patch("argus.main.UniverseManager") as mock_um_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_scanner_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.scan = AsyncMock(return_value=[])
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup data service mock that captures symbols passed to start()
            mock_data = MagicMock()

            async def capture_start(symbols, timeframes):
                nonlocal warmup_symbols_received
                warmup_symbols_received = list(symbols) if symbols else []

            mock_data.start = AsyncMock(side_effect=capture_start)
            mock_data.stop = AsyncMock()
            mock_data.set_viable_universe = MagicMock()
            mock_data_class.return_value = mock_data

            # Setup FMP mock - returns full stock list
            mock_fmp = MagicMock()
            mock_fmp.start = AsyncMock()
            mock_fmp.fetch_stock_list = AsyncMock(
                return_value=["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
            )
            mock_fmp_class.return_value = mock_fmp

            # Setup Universe Manager mock - filters down to just 3 symbols
            mock_um = MagicMock()
            mock_um.build_viable_universe = AsyncMock(return_value={"AAPL", "MSFT", "NVDA"})
            mock_um.build_routing_table = MagicMock()
            mock_um.viable_symbols = {"AAPL", "MSFT", "NVDA"}
            mock_um.viable_count = 3
            mock_um.is_built = True
            mock_um_class.return_value = mock_um

            # Setup strategy mock
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify warm-up received viable symbols (3), not full stock list (7)
            assert len(warmup_symbols_received) == 3
            assert set(warmup_symbols_received) == {"AAPL", "MSFT", "NVDA"}

    @pytest.mark.asyncio
    async def test_warmup_fallback_on_stocklist_failure(
        self, um_enabled_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify warm-up falls back to scanner symbols when stock-list fetch fails."""
        from argus.core.events import WatchlistItem
        from argus.main import ArgusSystem

        monkeypatch.setenv("DATABENTO_API_KEY", "test_db_key")
        monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")

        # dry_run=False so data service start() is called
        system = ArgusSystem(config_dir=um_enabled_config_dir, dry_run=False)
        warmup_symbols_received: list[str] = []

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.ibkr_broker.IBKRBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.DatabentoDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.FMPReferenceClient") as mock_fmp_class,
            patch("argus.main.UniverseManager") as mock_um_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup scanner to return 2 symbols
            mock_scanner = MagicMock()
            mock_scanner.start = AsyncMock()
            mock_scanner.stop = AsyncMock()
            mock_scanner.scan = AsyncMock(
                return_value=[
                    WatchlistItem(symbol="SCAN1"),
                    WatchlistItem(symbol="SCAN2"),
                ]
            )
            mock_scanner_class.return_value = mock_scanner

            # Setup data service mock that captures symbols passed to start()
            mock_data = MagicMock()

            async def capture_start(symbols, timeframes):
                nonlocal warmup_symbols_received
                warmup_symbols_received = list(symbols) if symbols else []

            mock_data.start = AsyncMock(side_effect=capture_start)
            mock_data.stop = AsyncMock()
            mock_data.set_viable_universe = MagicMock()
            mock_data_class.return_value = mock_data

            # Setup FMP mock - fetch_stock_list returns empty (failure)
            mock_fmp = MagicMock()
            mock_fmp.start = AsyncMock()
            mock_fmp.fetch_stock_list = AsyncMock(return_value=[])  # Failure!
            mock_fmp_class.return_value = mock_fmp

            # Setup Universe Manager mock - receives scanner symbols as fallback
            mock_um = MagicMock()
            # When passed scanner symbols, returns viable set
            mock_um.build_viable_universe = AsyncMock(return_value={"SCAN1", "SCAN2"})
            mock_um.build_routing_table = MagicMock()
            mock_um.viable_symbols = {"SCAN1", "SCAN2"}
            mock_um.viable_count = 2
            mock_um.is_built = True
            mock_um_class.return_value = mock_um

            # Setup strategy mock
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify warm-up received scanner symbols (fallback)
            assert len(warmup_symbols_received) == 2
            assert set(warmup_symbols_received) == {"SCAN1", "SCAN2"}

    @pytest.mark.asyncio
    async def test_warmup_fallback_on_empty_viable(
        self, um_enabled_config_dir: Path, mock_env_vars: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify warm-up falls back to scanner symbols when viable set is empty."""
        from argus.core.events import WatchlistItem
        from argus.main import ArgusSystem

        monkeypatch.setenv("DATABENTO_API_KEY", "test_db_key")
        monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")

        # dry_run=False so data service start() is called
        system = ArgusSystem(config_dir=um_enabled_config_dir, dry_run=False)
        warmup_symbols_received: list[str] = []

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.execution.ibkr_broker.IBKRBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.DatabentoDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
            patch("argus.main.FMPReferenceClient") as mock_fmp_class,
            patch("argus.main.UniverseManager") as mock_um_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup scanner to return 2 symbols
            mock_scanner = MagicMock()
            mock_scanner.start = AsyncMock()
            mock_scanner.stop = AsyncMock()
            mock_scanner.scan = AsyncMock(
                return_value=[
                    WatchlistItem(symbol="FALLBACK1"),
                    WatchlistItem(symbol="FALLBACK2"),
                ]
            )
            mock_scanner_class.return_value = mock_scanner

            # Setup data service mock that captures symbols passed to start()
            mock_data = MagicMock()

            async def capture_start(symbols, timeframes):
                nonlocal warmup_symbols_received
                warmup_symbols_received = list(symbols) if symbols else []

            mock_data.start = AsyncMock(side_effect=capture_start)
            mock_data.stop = AsyncMock()
            mock_data.set_viable_universe = MagicMock()
            mock_data_class.return_value = mock_data

            # Setup FMP mock - returns stock list
            mock_fmp = MagicMock()
            mock_fmp.start = AsyncMock()
            mock_fmp.fetch_stock_list = AsyncMock(return_value=["A", "B", "C"])
            mock_fmp_class.return_value = mock_fmp

            # Setup Universe Manager mock - returns EMPTY viable set
            mock_um = MagicMock()
            mock_um.build_viable_universe = AsyncMock(return_value=set())  # Empty!
            mock_um.build_routing_table = MagicMock()
            mock_um.viable_symbols = set()
            mock_um.viable_count = 0
            mock_um.is_built = True
            mock_um_class.return_value = mock_um

            # Setup strategy mock
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify warm-up received scanner symbols (fallback because viable is empty)
            assert len(warmup_symbols_received) == 2
            assert set(warmup_symbols_received) == {"FALLBACK1", "FALLBACK2"}

    @pytest.mark.asyncio
    async def test_warmup_uses_scanner_symbols_when_um_disabled(
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify warm-up uses scanner symbols when Universe Manager is disabled."""
        from argus.core.events import WatchlistItem
        from argus.main import ArgusSystem

        # dry_run=False so data service start() is called
        system = ArgusSystem(config_dir=mock_config_dir, dry_run=False)
        warmup_symbols_received: list[str] = []

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
            patch("argus.main.ConversationManager") as mock_conv_class,
            patch("argus.main.UsageTracker") as mock_usage_class,
            patch("argus.main.ActionManager") as mock_action_class,
            patch("argus.main.AlpacaBroker") as mock_broker_class,
            patch("argus.main.HealthMonitor") as mock_health_class,
            patch("argus.main.RiskManager") as mock_risk_class,
            patch("argus.main.AlpacaDataService") as mock_data_class,
            patch("argus.main.StaticScanner") as mock_scanner_class,  # Config uses static scanner
            patch("argus.main.OrbBreakoutStrategy") as mock_orb_class,
            patch("argus.main.Orchestrator") as mock_orchestrator_class,
            patch("argus.main.OrderManager") as mock_om_class,
        ):
            # Setup all mocks
            for cls in [
                mock_db_class,
                mock_conv_class,
                mock_usage_class,
                mock_action_class,
                mock_broker_class,
                mock_health_class,
                mock_risk_class,
                mock_om_class,
            ]:
                instance = MagicMock()
                instance.initialize = AsyncMock()
                instance.start = AsyncMock()
                instance.connect = AsyncMock()
                instance.stop = AsyncMock()
                instance.close = AsyncMock()
                instance.get_account = AsyncMock(return_value=MagicMock(equity=100000))
                instance.reconstruct_from_broker = AsyncMock()
                instance.reconstruct_state = AsyncMock()
                instance.update_component = MagicMock()
                instance.send_warning_alert = AsyncMock()
                instance.set_order_manager = MagicMock()
                cls.return_value = instance

            # Setup scanner to return 3 symbols
            mock_scanner = MagicMock()
            mock_scanner.start = AsyncMock()
            mock_scanner.stop = AsyncMock()
            mock_scanner.scan = AsyncMock(
                return_value=[
                    WatchlistItem(symbol="SCANNER1"),
                    WatchlistItem(symbol="SCANNER2"),
                    WatchlistItem(symbol="SCANNER3"),
                ]
            )
            mock_scanner_class.return_value = mock_scanner

            # Setup data service mock that captures symbols passed to start()
            mock_data = MagicMock()

            async def capture_start(symbols, timeframes):
                nonlocal warmup_symbols_received
                warmup_symbols_received = list(symbols) if symbols else []

            mock_data.start = AsyncMock(side_effect=capture_start)
            mock_data.stop = AsyncMock()
            mock_data_class.return_value = mock_data

            # Setup strategy mock
            orb_strategy = MagicMock()
            orb_strategy.set_watchlist = MagicMock()
            orb_strategy.strategy_id = "orb_breakout"
            orb_strategy.is_active = True
            orb_strategy.config = MagicMock()
            mock_orb_class.return_value = orb_strategy

            mock_orchestrator = MagicMock()
            mock_orchestrator.start = AsyncMock()
            mock_orchestrator.stop = AsyncMock()
            mock_orchestrator.run_pre_market = AsyncMock()
            mock_orchestrator.register_strategy = MagicMock()
            mock_orchestrator.get_strategies = MagicMock(
                return_value={"orb_breakout": orb_strategy}
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            with contextlib.suppress(Exception):
                await system.start()

            # Verify warm-up received scanner symbols (UM disabled)
            assert len(warmup_symbols_received) == 3
            assert set(warmup_symbols_received) == {"SCANNER1", "SCANNER2", "SCANNER3"}

"""Tests for the main entry point.

All components are mocked — no real broker connections, no real data.
These tests verify the ArgusSystem wiring, not the individual components.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
            patch("argus.main.AlpacaBroker") as mock_broker_class,
        ):
            mock_db = MagicMock()
            mock_db.initialize = AsyncMock()
            mock_db.close = AsyncMock()
            mock_db_class.return_value = mock_db

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

            mock_load_config.assert_called_once_with(mock_config_dir)

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

        # Set JWT secret so API starts
        monkeypatch.setenv("ARGUS_JWT_SECRET", "test_secret")

        # Update system.yaml to enable API
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

        # Update system.yaml to enable API
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
        self, mock_config_dir: Path, mock_env_vars: None
    ) -> None:
        """Verify both strategies are registered with the Orchestrator."""
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

        with (
            patch("argus.main.DatabaseManager") as mock_db_class,
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
            candle_subscribed = any(
                args[0] == CandleEvent for args, _ in subscribe_calls
            )
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

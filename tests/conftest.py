"""Shared test fixtures for the Argus test suite."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from argus.analytics.trade_logger import TradeLogger
from argus.core.config import ArgusConfig, load_config
from argus.core.event_bus import EventBus
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.strategies.orb_base import OrbBaseStrategy

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
async def db(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """Provide an initialized DatabaseManager with a temp database."""
    manager = DatabaseManager(tmp_path / "argus_test.db")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def trade_logger(db: DatabaseManager) -> TradeLogger:
    """Provide a TradeLogger backed by a temp database."""
    return TradeLogger(db)


@pytest.fixture
def simulated_broker() -> SimulatedBroker:
    """SimulatedBroker with default settings."""
    return SimulatedBroker(initial_cash=100_000.0)


@pytest.fixture
def risk_manager(
    config: ArgusConfig, simulated_broker: SimulatedBroker, bus: EventBus
) -> RiskManager:
    """RiskManager with default config, simulated broker, and event bus."""
    return RiskManager(
        config=config.risk,
        broker=simulated_broker,
        event_bus=bus,
    )


@pytest.fixture(autouse=True)
def clear_orb_family_exclusion_set() -> None:
    """Clear the ORB family exclusion set before and after each test.

    The _orb_family_triggered_symbols is a class variable shared across
    all OrbBaseStrategy subclasses. If not cleared between tests, state
    from one test can affect another, causing false failures.
    """
    OrbBaseStrategy._orb_family_triggered_symbols.clear()
    yield
    OrbBaseStrategy._orb_family_triggered_symbols.clear()

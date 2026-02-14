"""Shared test fixtures for the Argus test suite."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from argus.analytics.trade_logger import TradeLogger
from argus.core.config import ArgusConfig, load_config
from argus.core.event_bus import EventBus
from argus.db.manager import DatabaseManager

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

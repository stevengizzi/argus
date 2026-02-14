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

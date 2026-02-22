"""Tests for AlpacaScanner.

All Alpaca API calls are mocked. No network calls.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from argus.core.config import AlpacaConfig, AlpacaScannerConfig
from argus.data.alpaca_scanner import AlpacaScanner
from argus.models.strategy import ScannerCriteria

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_snapshot(
    open_price: float = 105.0,
    prev_close: float = 100.0,
    prev_volume: int = 2_000_000,
    daily_volume: int = 50_000,
    latest_trade_price: float | None = None,
) -> MagicMock:
    """Create a mock Alpaca snapshot."""
    snapshot = MagicMock()

    # Daily bar
    snapshot.daily_bar = MagicMock()
    snapshot.daily_bar.open = open_price
    snapshot.daily_bar.volume = daily_volume

    # Previous daily bar
    snapshot.previous_daily_bar = MagicMock()
    snapshot.previous_daily_bar.close = prev_close
    snapshot.previous_daily_bar.volume = prev_volume

    # Latest trade
    snapshot.latest_trade = MagicMock()
    snapshot.latest_trade.price = latest_trade_price or open_price

    return snapshot


@pytest.fixture
def scanner_config() -> AlpacaScannerConfig:
    """Create test scanner config."""
    return AlpacaScannerConfig(
        universe_symbols=["AAPL", "TSLA", "NVDA", "AMD", "MSFT"],
        min_price=5.0,
        max_price=500.0,
        min_volume_yesterday=1_000_000,
        max_symbols_returned=10,
    )


@pytest.fixture
def alpaca_config() -> AlpacaConfig:
    """Create test Alpaca config."""
    return AlpacaConfig(
        api_key_env="TEST_ALPACA_API_KEY",
        secret_key_env="TEST_ALPACA_SECRET_KEY",
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock StockHistoricalDataClient."""
    client = MagicMock()
    return client


@pytest.fixture
async def scanner(
    scanner_config: AlpacaScannerConfig,
    alpaca_config: AlpacaConfig,
    mock_client: MagicMock,
) -> AlpacaScanner:
    """Create AlpacaScanner with mocked client."""
    scanner = AlpacaScanner(scanner_config, alpaca_config)

    # Set environment variables
    os.environ["TEST_ALPACA_API_KEY"] = "test_key"
    os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

    with patch(
        "alpaca.data.historical.StockHistoricalDataClient",
        return_value=mock_client,
    ):
        await scanner.start()

    yield scanner

    await scanner.stop()
    del os.environ["TEST_ALPACA_API_KEY"]
    del os.environ["TEST_ALPACA_SECRET_KEY"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_returns_watchlist_items(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Mock snapshots → WatchlistItems returned."""
    # Setup mock snapshots
    mock_client.get_stock_snapshot.return_value = {
        "AAPL": make_snapshot(open_price=155.0, prev_close=150.0),
        "TSLA": make_snapshot(open_price=210.0, prev_close=200.0),
    }

    criteria = [ScannerCriteria(min_gap_pct=0.01)]
    result = await scanner.scan(criteria)

    assert len(result) == 2
    symbols = {item.symbol for item in result}
    assert "AAPL" in symbols
    assert "TSLA" in symbols


@pytest.mark.asyncio
async def test_filters_by_gap_percentage(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Only symbols within min/max gap returned."""
    mock_client.get_stock_snapshot.return_value = {
        "AAPL": make_snapshot(open_price=110.0, prev_close=100.0),  # 10% gap
        "TSLA": make_snapshot(open_price=101.0, prev_close=100.0),  # 1% gap
        "NVDA": make_snapshot(open_price=125.0, prev_close=100.0),  # 25% gap
    }

    # Only accept 5-20% gaps
    criteria = [ScannerCriteria(min_gap_pct=0.05, max_gap_pct=0.20)]
    result = await scanner.scan(criteria)

    assert len(result) == 1
    assert result[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_filters_by_price_range(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Symbols outside price range excluded."""
    mock_client.get_stock_snapshot.return_value = {
        "AAPL": make_snapshot(open_price=150.0, prev_close=145.0),  # In range
        "PENNY": make_snapshot(open_price=2.0, prev_close=1.8),  # Below min
        "HIGH": make_snapshot(open_price=600.0, prev_close=580.0),  # Above max
    }

    criteria = [ScannerCriteria()]
    result = await scanner.scan(criteria)

    assert len(result) == 1
    assert result[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_filters_by_minimum_volume(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Low-volume symbols excluded."""
    mock_client.get_stock_snapshot.return_value = {
        "AAPL": make_snapshot(open_price=150.0, prev_close=145.0, prev_volume=2_000_000),
        "LOWVOL": make_snapshot(open_price=50.0, prev_close=48.0, prev_volume=500_000),  # Below min
    }

    criteria = [ScannerCriteria()]
    result = await scanner.scan(criteria)

    assert len(result) == 1
    assert result[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_sorts_by_gap_descending(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Strongest gappers first."""
    mock_client.get_stock_snapshot.return_value = {
        "SMALL": make_snapshot(open_price=102.0, prev_close=100.0),  # 2%
        "MEDIUM": make_snapshot(open_price=105.0, prev_close=100.0),  # 5%
        "LARGE": make_snapshot(open_price=110.0, prev_close=100.0),  # 10%
    }

    criteria = [ScannerCriteria()]
    result = await scanner.scan(criteria)

    # Should be sorted by gap descending
    assert result[0].symbol == "LARGE"
    assert result[1].symbol == "MEDIUM"
    assert result[2].symbol == "SMALL"


@pytest.mark.asyncio
async def test_respects_max_symbols_limit(
    scanner_config: AlpacaScannerConfig,
    alpaca_config: AlpacaConfig,
) -> None:
    """Returns at most max_symbols_returned."""
    # Override config with limit of 2
    config = AlpacaScannerConfig(
        universe_symbols=["A", "B", "C", "D", "E"],
        max_symbols_returned=2,
        min_volume_yesterday=0,  # Disable volume filter
    )

    scanner = AlpacaScanner(config, alpaca_config)

    # Set environment variables
    os.environ["TEST_ALPACA_API_KEY"] = "test_key"
    os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

    mock_client = MagicMock()
    mock_client.get_stock_snapshot.return_value = {
        "A": make_snapshot(open_price=110.0, prev_close=100.0, prev_volume=2_000_000),
        "B": make_snapshot(open_price=108.0, prev_close=100.0, prev_volume=2_000_000),
        "C": make_snapshot(open_price=106.0, prev_close=100.0, prev_volume=2_000_000),
        "D": make_snapshot(open_price=104.0, prev_close=100.0, prev_volume=2_000_000),
        "E": make_snapshot(open_price=102.0, prev_close=100.0, prev_volume=2_000_000),
    }

    with patch(
        "alpaca.data.historical.StockHistoricalDataClient",
        return_value=mock_client,
    ):
        await scanner.start()
        result = await scanner.scan([ScannerCriteria()])
        await scanner.stop()

    assert len(result) == 2

    del os.environ["TEST_ALPACA_API_KEY"]
    del os.environ["TEST_ALPACA_SECRET_KEY"]


@pytest.mark.asyncio
async def test_handles_missing_snapshot_data(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Incomplete snapshot → skipped."""
    # Create snapshot with missing data
    incomplete = MagicMock()
    incomplete.daily_bar = None
    incomplete.previous_daily_bar = None

    mock_client.get_stock_snapshot.return_value = {
        "GOOD": make_snapshot(open_price=110.0, prev_close=100.0),
        "BAD": incomplete,
    }

    criteria = [ScannerCriteria()]
    result = await scanner.scan(criteria)

    assert len(result) == 1
    assert result[0].symbol == "GOOD"


@pytest.mark.asyncio
async def test_gap_calculation_correct(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """Verify gap = (open - prev_close) / prev_close."""
    mock_client.get_stock_snapshot.return_value = {
        "AAPL": make_snapshot(open_price=110.0, prev_close=100.0),  # 10% gap
    }

    criteria = [ScannerCriteria()]
    result = await scanner.scan(criteria)

    assert len(result) == 1
    # Gap should be (110 - 100) / 100 = 0.10
    assert result[0].gap_pct == pytest.approx(0.10)


@pytest.mark.asyncio
async def test_empty_universe_returns_empty(
    alpaca_config: AlpacaConfig,
) -> None:
    """No symbols configured → empty list."""
    config = AlpacaScannerConfig(universe_symbols=[])
    scanner = AlpacaScanner(config, alpaca_config)

    # Set environment variables
    os.environ["TEST_ALPACA_API_KEY"] = "test_key"
    os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

    mock_client = MagicMock()
    with patch(
        "alpaca.data.historical.StockHistoricalDataClient",
        return_value=mock_client,
    ):
        await scanner.start()
        result = await scanner.scan([ScannerCriteria()])
        await scanner.stop()

    assert result == []

    del os.environ["TEST_ALPACA_API_KEY"]
    del os.environ["TEST_ALPACA_SECRET_KEY"]


@pytest.mark.asyncio
async def test_all_symbols_filtered_out(
    scanner: AlpacaScanner,
    mock_client: MagicMock,
) -> None:
    """No matches → empty list."""
    # All stocks have gaps below 50%
    mock_client.get_stock_snapshot.return_value = {
        "A": make_snapshot(open_price=105.0, prev_close=100.0),  # 5%
        "B": make_snapshot(open_price=110.0, prev_close=100.0),  # 10%
    }

    # Require 50%+ gap
    criteria = [ScannerCriteria(min_gap_pct=0.50)]
    result = await scanner.scan(criteria)

    assert result == []

"""Mock Databento objects for unit tests.

These mocks allow testing DatabentoDataService and related components
without requiring the real databento package or API access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class MockRecordHeader:
    """Mock Databento record header.

    All Databento messages have a header (hd) with common metadata.
    """

    instrument_id: int = 0
    length: int = 0
    rtype: int = 0
    publisher_id: int = 0
    ts_event: int = 0


@dataclass
class MockOHLCVMsg:
    """Mock Databento OHLCVMsg for unit tests.

    Represents a completed OHLCV bar from the ohlcv-1m schema.
    In the current Databento API, prices are in fixed-point format (scaled by 1e9).
    instrument_id is now a direct attribute (not nested in hd).
    """

    instrument_id: int = 0  # Direct attribute in current API
    open: float = 0.0  # Fixed-point scaled by 1e9
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    ts_event: int = 0  # Nanosecond Unix timestamp (bar OPEN time)
    hd: MockRecordHeader = field(default_factory=MockRecordHeader)  # Legacy, kept for compatibility


@dataclass
class MockTradeMsg:
    """Mock Databento TradeMsg for unit tests.

    Represents an individual trade from the trades schema.
    In the current Databento API, instrument_id is a direct attribute.
    """

    instrument_id: int = 0  # Direct attribute in current API
    price: float = 0.0  # Fixed-point scaled by 1e9
    size: int = 0
    ts_event: int = 0  # Nanosecond Unix timestamp
    hd: MockRecordHeader = field(default_factory=MockRecordHeader)  # Legacy, kept for compatibility


@dataclass
class MockSymbolMappingMsg:
    """Mock Databento SymbolMappingMsg for unit tests.

    Maps instrument_id to human-readable ticker symbol.
    These arrive at session start before data messages.
    """

    instrument_id: int = 0
    stype_in_symbol: str = ""


@dataclass
class MockErrorMsg:
    """Mock Databento ErrorMsg for unit tests."""

    err: str = ""


class MockLiveClient:
    """Mock Databento Live client for unit tests.

    Records subscribe/start/stop calls. Allows injecting messages
    via fire_callback() to simulate Databento data arriving.
    Provides symbology_map for instrument_id → symbol resolution.
    """

    def __init__(self, key: str = "") -> None:
        """Initialize mock client.

        Args:
            key: API key (ignored in mock).
        """
        self.key = key
        self.subscriptions: list[dict[str, Any]] = []
        self.callbacks: list[Any] = []
        self.started = False
        self.stopped = False
        self._block_for_close_should_raise: Exception | None = None
        self._block_for_close_should_return_immediately = False
        # symbology_map: instrument_id → symbol (current Databento API)
        self._symbology_map: dict[int, str] = {}

    @property
    def symbology_map(self) -> dict[int, str]:
        """Return the instrument_id → symbol mapping.

        In the real Databento client, this is populated automatically
        from SymbolMappingMsg records at session start.
        """
        return self._symbology_map

    def subscribe(
        self,
        dataset: str = "",
        schema: str = "",
        symbols: str | list[str] = "",
        stype_in: str = "raw_symbol",
        **kwargs: Any,
    ) -> None:
        """Record a subscription request.

        Args:
            dataset: Databento dataset (e.g., "XNAS.ITCH").
            schema: Data schema (e.g., "ohlcv-1m", "trades").
            symbols: Symbol(s) to subscribe to.
            stype_in: Input symbology type.
            **kwargs: Additional subscription parameters.
        """
        self.subscriptions.append(
            {
                "dataset": dataset,
                "schema": schema,
                "symbols": symbols,
                "stype_in": stype_in,
                **kwargs,
            }
        )

    def add_callback(self, callback: Any) -> None:
        """Register a callback for incoming records.

        Args:
            callback: Callable to receive records.
        """
        self.callbacks.append(callback)

    def start(self) -> None:
        """Start the live session (marks started=True)."""
        self.started = True

    def stop(self) -> None:
        """Stop the live session (marks stopped=True)."""
        self.stopped = True

    def block_for_close(self) -> None:
        """Block until the session is closed.

        In real Databento client, this blocks until the TCP connection closes.
        In mock, it returns immediately or raises configured exception.
        """
        if self._block_for_close_should_raise is not None:
            raise self._block_for_close_should_raise
        # Return immediately for testing

    def fire_callback(self, record: Any) -> None:
        """Simulate a record arriving from Databento.

        Calls all registered callbacks with the record.
        In tests, this runs on the test thread (no threading).

        Args:
            record: Mock record to dispatch.
        """
        for cb in self.callbacks:
            cb(record)


class MockTimeseries:
    """Mock timeseries endpoint for Historical client."""

    def __init__(self) -> None:
        self._data: pd.DataFrame | None = None

    def get_range(
        self,
        dataset: str = "",
        symbols: str | list[str] = "",
        schema: str = "",
        start: str = "",
        end: str = "",
        **kwargs: Any,
    ) -> MockDBNStore:
        """Mock get_range call.

        Args:
            dataset: Databento dataset.
            symbols: Symbol(s) to query.
            schema: Data schema.
            start: Start datetime (ISO format).
            end: End datetime (ISO format).
            **kwargs: Additional parameters.

        Returns:
            MockDBNStore with configured data.
        """
        return MockDBNStore(self._data)


class MockHistoricalClient:
    """Mock Databento Historical client for unit tests."""

    def __init__(self, key: str = "") -> None:
        """Initialize mock client.

        Args:
            key: API key (ignored in mock).
        """
        self.key = key
        self.timeseries = MockTimeseries()


class MockDBNStore:
    """Mock DBNStore returned by Historical client's get_range().

    Wraps a DataFrame for compatibility with Databento's .to_df() pattern.
    """

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        """Initialize mock store.

        Args:
            df: DataFrame to return from to_df(), or None for empty.
        """
        self._df = df

    def to_df(self) -> pd.DataFrame:
        """Convert to DataFrame.

        Returns:
            Configured DataFrame or empty DataFrame with expected columns.
        """
        if self._df is not None:
            return self._df
        return pd.DataFrame(columns=["ts_event", "open", "high", "low", "close", "volume"])

"""Shared utilities for Databento data normalization.

Provides common functions used by both DatabentoDataService and DataFetcher
to ensure consistent data handling across the codebase.
"""

import pandas as pd


def normalize_databento_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Databento DataFrame to ARGUS standard schema.

    Databento's to_df() returns data with:
        - ts_event as the index (datetime)
        - Columns: rtype, publisher_id, instrument_id, open, high, low, close, volume, symbol

    ARGUS standard schema:
        timestamp, open, high, low, close, volume

    This function:
    1. Extracts ts_event from index (or column if present) → timestamp
    2. Ensures timestamps are UTC-aware
    3. Sorts by timestamp
    4. Resets index

    Args:
        df: DataFrame from Databento's to_df() method.

    Returns:
        Normalized DataFrame with standard schema:
        [timestamp, open, high, low, close, volume]

    Example:
        >>> data = db_client.timeseries.get_range(...)
        >>> df = data.to_df()
        >>> normalized = normalize_databento_df(df)
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Handle both cases: ts_event as index or as column
    if "ts_event" in df.columns:
        # ts_event is a column (older library versions or different methods)
        result = df[["ts_event", "open", "high", "low", "close", "volume"]].copy()
        result = result.rename(columns={"ts_event": "timestamp"})
    elif df.index.name == "ts_event":
        # ts_event is the index (current library behavior)
        result = df[["open", "high", "low", "close", "volume"]].copy()
        result = result.reset_index()
        result = result.rename(columns={"ts_event": "timestamp"})
    else:
        # Fallback: try to use the index as timestamp if it's datetime-like
        result = df[["open", "high", "low", "close", "volume"]].copy()
        result = result.reset_index()
        result.columns = ["timestamp", "open", "high", "low", "close", "volume"]

    # Ensure UTC-aware timestamps
    if result["timestamp"].dt.tz is None:
        result["timestamp"] = result["timestamp"].dt.tz_localize("UTC")
    elif str(result["timestamp"].dt.tz) != "UTC":
        result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")

    return result.sort_values("timestamp").reset_index(drop=True)

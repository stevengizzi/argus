"""Shared utilities for Databento data normalization.

Provides common functions used by both DatabentoDataService and DataFetcher
to ensure consistent data handling across the codebase.
"""

import pandas as pd


def normalize_databento_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Databento DataFrame to ARGUS standard schema.

    Databento's to_df() returns columns like:
        ts_event, rtype, publisher_id, instrument_id, open, high, low, close, volume, ...

    ARGUS standard schema:
        timestamp, open, high, low, close, volume

    This function:
    1. Selects and renames ts_event → timestamp
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
        return pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

    result = df[["ts_event", "open", "high", "low", "close", "volume"]].copy()
    result = result.rename(columns={"ts_event": "timestamp"})

    # Ensure UTC-aware timestamps
    if result["timestamp"].dt.tz is None:
        result["timestamp"] = result["timestamp"].dt.tz_localize("UTC")
    elif str(result["timestamp"].dt.tz) != "UTC":
        result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")

    return result.sort_values("timestamp").reset_index(drop=True)

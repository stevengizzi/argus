"""Market correlation tracker for regime intelligence.

Computes rolling pairwise correlation across top symbols using daily bars.
File-based JSON cache keyed by calendar date (ET). Standalone module —
wired into RegimeClassifierV2 in Session 6.

Sprint 27.6, Session 3.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from argus.core.config import CorrelationConfig

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

# Neutral defaults when data is unavailable
_NEUTRAL_AVG_CORRELATION = 0.4
_NEUTRAL_REGIME = "normal"

# Type aliases for injected callables
FetchDailyBarsFn = Callable[[str, int], Awaitable[pd.DataFrame | None]]
GetTopSymbolsFn = Callable[[], list[str]]


class MarketCorrelationTracker:
    """Compute and cache rolling pairwise correlation for top symbols.

    Accepts dependency-injected callables for fetching daily bars and
    retrieving the top symbols list.  Never imports FMP or Universe Manager
    directly.

    Args:
        config: CorrelationConfig with thresholds and lookback settings.
        cache_path: Path for the JSON file cache. Defaults to data/correlation_cache.json.
    """

    def __init__(
        self,
        config: CorrelationConfig,
        cache_path: Path | None = None,
    ) -> None:
        self._config = config
        self._cache_path = cache_path or Path("data/correlation_cache.json")
        self._average_correlation: float | None = None
        self._correlation_regime: str | None = None
        self._symbols_used: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute(
        self,
        fetch_daily_bars_fn: FetchDailyBarsFn,
        get_top_symbols_fn: GetTopSymbolsFn,
    ) -> None:
        """Compute correlation snapshot, using cache when possible.

        Args:
            fetch_daily_bars_fn: async (symbol, lookback_days) -> DataFrame | None
            get_top_symbols_fn: () -> list[str] of top N symbols by volume
        """
        today_et = datetime.now(_ET).strftime("%Y-%m-%d")

        # Check file cache
        cached = self._read_cache()
        if cached is not None and cached.get("date") == today_et:
            logger.info("Correlation cache hit for %s", today_et)
            self._average_correlation = cached["average_correlation"]
            self._correlation_regime = cached["correlation_regime"]
            self._symbols_used = len(cached.get("symbols", []))
            return

        # Fetch symbols
        symbols = get_top_symbols_fn()
        if len(symbols) < 2:
            logger.warning(
                "Fewer than 2 symbols (%d) — using neutral defaults", len(symbols)
            )
            self._set_neutral(symbols_used=len(symbols))
            return

        # Cap at top_n_symbols
        symbols = symbols[: self._config.top_n_symbols]

        # Fetch daily bars concurrently
        lookback = self._config.lookback_days
        tasks = [fetch_daily_bars_fn(sym, lookback + 5) for sym in symbols]
        results: list[pd.DataFrame | None] = await asyncio.gather(*tasks)

        # Build returns matrix
        returns_map: dict[str, pd.Series] = {}
        for sym, df in zip(symbols, results):
            if df is None or len(df) < lookback:
                logger.debug(
                    "Excluding %s: insufficient history (%s bars)",
                    sym,
                    len(df) if df is not None else 0,
                )
                continue
            # Use last `lookback` rows, compute daily returns
            close = df["close"].iloc[-lookback:]
            daily_returns = close.pct_change().dropna()
            if len(daily_returns) < lookback - 1:
                continue
            returns_map[sym] = daily_returns.reset_index(drop=True)

        if len(returns_map) < 2:
            logger.warning(
                "Fewer than 2 symbols with sufficient history (%d) — neutral defaults",
                len(returns_map),
            )
            self._set_neutral(symbols_used=len(returns_map))
            return

        # Compute pairwise correlation matrix
        returns_df = pd.DataFrame(returns_map)
        corr_matrix = returns_df.corr()

        # Extract upper triangle (excluding diagonal)
        mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
        upper_values = corr_matrix.values[mask]

        # Filter NaN (shouldn't happen with valid data, but defensive)
        valid_values = upper_values[~np.isnan(upper_values)]
        if len(valid_values) == 0:
            self._set_neutral(symbols_used=len(returns_map))
            return

        avg_corr = float(np.mean(valid_values))
        regime = self._classify_regime(avg_corr)

        self._average_correlation = avg_corr
        self._correlation_regime = regime
        self._symbols_used = len(returns_map)

        # Write cache
        used_symbols = list(returns_map.keys())
        self._write_cache(today_et, used_symbols, avg_corr, regime)

        logger.info(
            "Correlation computed: avg=%.3f regime=%s symbols=%d",
            avg_corr,
            regime,
            len(returns_map),
        )

    def get_correlation_snapshot(self) -> dict[str, Any]:
        """Return current correlation state.

        Returns:
            Dict with average_correlation, correlation_regime, symbols_used.
        """
        return {
            "average_correlation": self._average_correlation
            if self._average_correlation is not None
            else _NEUTRAL_AVG_CORRELATION,
            "correlation_regime": self._correlation_regime
            if self._correlation_regime is not None
            else _NEUTRAL_REGIME,
            "symbols_used": self._symbols_used,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_regime(self, avg_correlation: float) -> str:
        """Classify correlation into dispersed / normal / concentrated."""
        if avg_correlation < self._config.dispersed_threshold:
            return "dispersed"
        if avg_correlation > self._config.concentrated_threshold:
            return "concentrated"
        return "normal"

    def _set_neutral(self, symbols_used: int = 0) -> None:
        """Set neutral defaults when data is insufficient."""
        self._average_correlation = _NEUTRAL_AVG_CORRELATION
        self._correlation_regime = _NEUTRAL_REGIME
        self._symbols_used = symbols_used

    def _read_cache(self) -> dict[str, Any] | None:
        """Read the JSON file cache. Returns None if missing or malformed."""
        try:
            if not self._cache_path.exists():
                return None
            text = self._cache_path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, dict) or "date" not in data:
                return None
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read correlation cache: %s", exc)
            return None

    def _write_cache(
        self,
        date_str: str,
        symbols: list[str],
        average_correlation: float,
        correlation_regime: str,
    ) -> None:
        """Write correlation results to JSON file cache."""
        payload = {
            "date": date_str,
            "symbols": symbols,
            "average_correlation": round(average_correlation, 6),
            "correlation_regime": correlation_regime,
        }
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Failed to write correlation cache: %s", exc)

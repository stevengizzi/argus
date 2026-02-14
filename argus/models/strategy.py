"""Strategy-related models for the Argus system.

These models define the data structures used by strategies for:
- Scanner criteria (what stocks to watch)
- Exit rules (how to manage positions)
- Market conditions (when to activate)
- Watchlist items (stocks being tracked)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScannerCriteria:
    """Defines what stocks a strategy wants to see.

    Used by the Scanner to build a watchlist. Strategies return this
    from get_scanner_criteria() to specify their stock selection filters.
    """

    min_price: float = 10.0
    max_price: float = 200.0
    min_volume_avg_daily: int = 1_000_000  # Average Daily Volume
    min_relative_volume: float = 2.0  # RVOL threshold
    min_gap_pct: float | None = None  # Gap percentage (e.g., 0.02 = 2%)
    max_gap_pct: float | None = None
    min_market_cap: float | None = None
    max_spread_pct: float | None = None  # Maximum bid-ask spread as %
    excluded_symbols: list[str] = field(default_factory=list)
    max_results: int = 20  # Max watchlist size


@dataclass
class ProfitTarget:
    """A single profit target level.

    Defines when to take partial or full profits based on R-multiple.
    """

    r_multiple: float  # Target as R-multiple (1.0 = 1R)
    position_pct: float  # Percentage of position to close at this target (0.5 = 50%)


@dataclass
class ExitRules:
    """Complete exit configuration for a strategy.

    Defines all the conditions under which a position may be closed.
    """

    stop_type: str  # "fixed", "trailing", "atr_based"
    stop_price_func: str  # How to calculate stop: "midpoint", "bottom", "atr"
    targets: list[ProfitTarget] = field(default_factory=list)
    time_stop_minutes: int | None = None
    trailing_stop_atr_multiplier: float | None = None


@dataclass
class MarketConditionsFilter:
    """Conditions under which a strategy may be activated by the Orchestrator.

    The Orchestrator checks these conditions daily to decide whether
    a strategy should be active.
    """

    allowed_regimes: list[str] = field(default_factory=list)
    max_vix: float | None = None
    min_vix: float | None = None
    require_spy_above_sma: int | None = None  # e.g., 20 (20-day SMA)


@dataclass
class StrategyWatchlistItem:
    """A single stock on a strategy's watchlist.

    More flexible than the WatchlistItem in events.py, which is frozen
    for event payloads. This version allows strategies to track
    additional metadata as needed.
    """

    symbol: str
    gap_pct: float | None = None
    relative_volume: float | None = None
    atr: float | None = None
    premarket_volume: int | None = None
    float_shares: int | None = None
    catalyst: str | None = None

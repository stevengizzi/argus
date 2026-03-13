"""Dynamic position sizer driven by quality grades.

Maps SetupQuality grades to risk tiers and calculates share counts
based on allocated capital, entry/stop spread, and buying power.

Sprint 24, Session 5a.
"""

from __future__ import annotations

import logging

from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.quality_engine import SetupQuality

logger = logging.getLogger(__name__)


class DynamicPositionSizer:
    """Converts a quality grade into a position size (share count).

    Uses the midpoint of the grade's risk tier range to determine
    the dollar amount at risk, then divides by per-share risk.

    Args:
        config: QualityEngineConfig containing risk_tiers.
    """

    def __init__(self, config: QualityEngineConfig) -> None:
        self._config = config

    def calculate_shares(
        self,
        quality: SetupQuality,
        entry_price: float,
        stop_price: float,
        allocated_capital: float,
        buying_power: float,
    ) -> int:
        """Calculate share count for a trade based on quality grade.

        Grade → risk % (midpoint of tier range) → dollar risk → shares.
        Capped by available buying power.

        Args:
            quality: SetupQuality result from the quality engine.
            entry_price: Planned entry price.
            stop_price: Planned stop-loss price.
            allocated_capital: Capital allocated to this strategy.
            buying_power: Available buying power in the account.

        Returns:
            Number of shares to trade (0 if position is not viable).
        """
        if entry_price <= 0 or stop_price <= 0:
            return 0

        tier = self._get_risk_tier(quality.grade)
        risk_pct = (tier[0] + tier[1]) / 2
        risk_dollars = allocated_capital * risk_pct

        risk_per_share = abs(entry_price - stop_price)
        if risk_per_share <= 0:
            return 0

        shares = int(risk_dollars / risk_per_share)

        if shares * entry_price > buying_power:
            shares = int(buying_power / entry_price)

        return max(0, shares)

    def _get_risk_tier(self, grade: str) -> list[float]:
        """Look up the risk tier [min, max] for a quality grade.

        Args:
            grade: Quality grade string (e.g. "A+", "B-").

        Returns:
            Two-element list [min_risk_pct, max_risk_pct].
        """
        field_name = grade.lower().replace("+", "_plus").replace("-", "_minus")
        tier = getattr(self._config.risk_tiers, field_name, None)
        if tier is None:
            logger.warning("Unknown grade '%s', defaulting to C+ tier", grade)
            return self._config.risk_tiers.c_plus
        return tier

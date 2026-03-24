"""Sector rotation analyzer for regime intelligence.

Fetches FMP /stable/sector-performance during pre-market, classifies
rotation phase (risk_on, risk_off, transitioning, mixed), and identifies
leading/lagging sectors.  Circuit breaker on 403.

Sprint 27.6, Session 4.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from argus.core.config import SectorRotationConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sector classification buckets
# ---------------------------------------------------------------------------

RISK_ON_SECTORS: frozenset[str] = frozenset(
    {
        "Technology",
        "Consumer Discretionary",
        "Communication Services",
        "Financials",
    }
)

RISK_OFF_SECTORS: frozenset[str] = frozenset(
    {
        "Utilities",
        "Healthcare",
        "Consumer Staples",
        "Real Estate",
    }
)

_FETCH_TIMEOUT_SECONDS = 10


class SectorRotationAnalyzer:
    """Fetches sector performance from FMP and classifies rotation phase.

    The analyzer maintains a simple circuit breaker: if FMP returns 403
    (plan restriction), the circuit opens permanently for the process
    lifetime and all subsequent calls degrade gracefully.

    Attributes:
        config: Sector rotation configuration.
    """

    def __init__(
        self,
        config: SectorRotationConfig,
        fmp_base_url: str,
        fmp_api_key: str | None,
    ) -> None:
        self._config = config
        self._fmp_base_url = fmp_base_url.rstrip("/")
        self._fmp_api_key = fmp_api_key

        # Internal state
        self._circuit_open: bool = False
        self._sector_rotation_phase: str = "mixed"
        self._leading_sectors: list[str] = []
        self._lagging_sectors: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch(self) -> None:
        """Fetch sector performance from FMP and classify rotation.

        On 403 the circuit breaker opens permanently.  On timeout or
        any other HTTP error the analyzer degrades to mixed/empty for
        this call but does NOT open the circuit breaker.
        """
        if self._circuit_open:
            logger.debug("SectorRotation circuit open — skipping fetch")
            self._degrade()
            return

        if not self._fmp_api_key:
            logger.warning("SectorRotation: no FMP API key — degrading")
            self._degrade()
            return

        url = (
            f"{self._fmp_base_url}/stable/sector-performance"
            f"?apikey={self._fmp_api_key}"
        )

        try:
            timeout = aiohttp.ClientTimeout(total=_FETCH_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 403:
                        logger.warning(
                            "FMP sector-performance unavailable "
                            "(Starter plan) — using fallback "
                            "classification"
                        )
                        self._circuit_open = True
                        self._degrade()
                        return

                    if response.status != 200:
                        logger.warning(
                            "FMP sector-performance HTTP %d — degrading",
                            response.status,
                        )
                        self._degrade()
                        return

                    data = await response.json()

        except TimeoutError:
            logger.warning("FMP sector-performance timeout — degrading")
            self._degrade()
            return
        except (aiohttp.ClientError, Exception):
            logger.warning(
                "FMP sector-performance request failed — degrading",
                exc_info=True,
            )
            self._degrade()
            return

        self._classify(data)

    def get_sector_snapshot(self) -> dict[str, Any]:
        """Return current sector rotation state.

        Returns:
            Dictionary with keys: sector_rotation_phase, leading_sectors,
            lagging_sectors.
        """
        return {
            "sector_rotation_phase": self._sector_rotation_phase,
            "leading_sectors": list(self._leading_sectors),
            "lagging_sectors": list(self._lagging_sectors),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _degrade(self) -> None:
        """Set state to graceful degradation defaults."""
        self._sector_rotation_phase = "mixed"
        self._leading_sectors = []
        self._lagging_sectors = []

    def _classify(self, data: list[dict[str, Any]]) -> None:
        """Classify rotation phase from FMP sector performance data.

        Args:
            data: List of dicts with at least 'sector' and
                'changesPercentage' keys, sorted or unsorted.
        """
        # Parse and sort by performance descending
        parsed = _parse_sector_data(data)

        if len(parsed) < 5:
            logger.warning(
                "SectorRotation: only %d sectors returned — "
                "defaulting to mixed",
                len(parsed),
            )
            self._degrade()
            return

        # Leading = top 3, lagging = bottom 3
        self._leading_sectors = [name for name, _ in parsed[:3]]
        self._lagging_sectors = [name for name, _ in parsed[-3:]]

        top_3_names = set(self._leading_sectors)
        bottom_3_names = set(self._lagging_sectors)

        top_risk_on = len(top_3_names & RISK_ON_SECTORS)
        top_risk_off = len(top_3_names & RISK_OFF_SECTORS)
        bottom_risk_on = len(bottom_3_names & RISK_ON_SECTORS)
        bottom_risk_off = len(bottom_3_names & RISK_OFF_SECTORS)

        if top_risk_on >= 2:
            self._sector_rotation_phase = "risk_on"
        elif top_risk_off >= 2:
            self._sector_rotation_phase = "risk_off"
        elif (top_risk_on >= 1 and top_risk_off >= 1) and (
            bottom_risk_off >= 1 and bottom_risk_on >= 1
        ):
            # Mix in top AND inverted mix in bottom
            self._sector_rotation_phase = "transitioning"
        else:
            self._sector_rotation_phase = "mixed"


def _parse_sector_data(
    data: list[dict[str, Any]],
) -> list[tuple[str, float]]:
    """Extract (sector_name, change_pct) pairs sorted by performance desc.

    Args:
        data: Raw FMP response list.

    Returns:
        Sorted list of (sector, changesPercentage) tuples, highest first.
    """
    results: list[tuple[str, float]] = []
    for entry in data:
        sector = entry.get("sector", "")
        change = entry.get("changesPercentage")
        if sector and change is not None:
            try:
                results.append((sector, float(change)))
            except (ValueError, TypeError):
                continue

    results.sort(key=lambda pair: pair[1], reverse=True)
    return results

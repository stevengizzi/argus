"""Tests for SectorRotationAnalyzer (Sprint 27.6 S4)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import SectorRotationConfig
from argus.core.sector_rotation import (
    SectorRotationAnalyzer,
    _parse_sector_data,
)


class _AsyncCtx:
    """Helper for mocking async context managers."""

    def __init__(self, return_value: Any) -> None:
        self.return_value = return_value

    async def __aenter__(self) -> Any:
        return self.return_value

    async def __aexit__(self, *args: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sector_data(
    sectors: list[tuple[str, float]],
) -> list[dict[str, Any]]:
    """Build FMP-style sector performance response."""
    return [
        {"sector": name, "changesPercentage": pct}
        for name, pct in sectors
    ]


def _default_config() -> SectorRotationConfig:
    return SectorRotationConfig(enabled=True)


# Canonical sector lists for test scenarios
RISK_ON_LEADING = [
    ("Technology", 2.5),
    ("Consumer Discretionary", 1.8),
    ("Financials", 1.2),
    ("Industrials", 0.5),
    ("Healthcare", 0.3),
    ("Materials", 0.1),
    ("Utilities", -0.2),
    ("Consumer Staples", -0.5),
    ("Real Estate", -0.8),
    ("Energy", -1.0),
    ("Communication Services", -1.2),
]

RISK_OFF_LEADING = [
    ("Utilities", 2.5),
    ("Healthcare", 1.8),
    ("Consumer Staples", 1.2),
    ("Industrials", 0.5),
    ("Technology", 0.3),
    ("Materials", 0.1),
    ("Financials", -0.2),
    ("Consumer Discretionary", -0.5),
    ("Real Estate", -0.8),
    ("Energy", -1.0),
    ("Communication Services", -1.2),
]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    """SectorRotationAnalyzer construction."""

    def test_construction_defaults(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://financialmodelingprep.com/api",
            fmp_api_key="test-key",
        )
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "mixed"
        assert snapshot["leading_sectors"] == []
        assert snapshot["lagging_sectors"] == []

    def test_construction_strips_trailing_slash(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com/api/",
            fmp_api_key="key",
        )
        assert analyzer._fmp_base_url == "https://example.com/api"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    """Sector rotation phase classification rules."""

    def test_classify_risk_on(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(RISK_ON_LEADING))
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "risk_on"
        assert snapshot["leading_sectors"] == [
            "Technology",
            "Consumer Discretionary",
            "Financials",
        ]

    def test_classify_risk_off(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(RISK_OFF_LEADING))
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "risk_off"
        assert snapshot["leading_sectors"] == [
            "Utilities",
            "Healthcare",
            "Consumer Staples",
        ]

    def test_classify_transitioning(self) -> None:
        """Top 3 has mix of risk-on and risk-off; bottom 3 is inverted."""
        sectors = [
            ("Technology", 3.0),         # risk-on  (1 risk-on in top 3)
            ("Utilities", 2.5),          # risk-off (1 risk-off in top 3)
            ("Industrials", 2.0),        # neither
            ("Materials", 1.0),
            ("Energy", 0.5),
            ("Healthcare", 0.0),
            ("Consumer Staples", -0.5),
            ("Communication Services", -1.0),
            ("Real Estate", -1.5),       # risk-off (1 risk-off in bottom 3)
            ("Financials", -2.0),        # risk-on  (1 risk-on in bottom 3)
            ("Consumer Discretionary", -2.5),  # risk-on
        ]
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(sectors))
        assert analyzer.get_sector_snapshot()["sector_rotation_phase"] == "transitioning"

    def test_classify_mixed(self) -> None:
        """No clear risk-on or risk-off pattern → mixed."""
        sectors = [
            ("Industrials", 2.0),
            ("Materials", 1.5),
            ("Energy", 1.0),
            ("Technology", 0.5),
            ("Healthcare", 0.0),
            ("Utilities", -0.5),
            ("Consumer Staples", -1.0),
            ("Consumer Discretionary", -1.5),
            ("Communication Services", -2.0),
            ("Financials", -2.5),
            ("Real Estate", -3.0),
        ]
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(sectors))
        assert analyzer.get_sector_snapshot()["sector_rotation_phase"] == "mixed"

    def test_partial_data_less_than_5_sectors_defaults_to_mixed(self) -> None:
        sectors = [
            ("Technology", 2.0),
            ("Healthcare", 1.0),
            ("Utilities", 0.5),
            ("Energy", -0.5),
        ]
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(sectors))
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "mixed"
        assert snapshot["leading_sectors"] == []
        assert snapshot["lagging_sectors"] == []

    def test_leading_lagging_identification(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(RISK_ON_LEADING))
        snapshot = analyzer.get_sector_snapshot()
        assert len(snapshot["leading_sectors"]) == 3
        assert len(snapshot["lagging_sectors"]) == 3
        # Bottom 3 by performance (slice of sorted-desc list)
        assert snapshot["lagging_sectors"] == [
            "Real Estate",
            "Energy",
            "Communication Services",
        ]


# ---------------------------------------------------------------------------
# Fetch — HTTP mocking
# ---------------------------------------------------------------------------


class TestFetch:
    """Async fetch with HTTP mocking."""

    @pytest.mark.asyncio
    async def test_fetch_403_opens_circuit_breaker(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )

        mock_response = AsyncMock()
        mock_response.status = 403

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=_AsyncCtx(mock_response))

        with patch(
            "argus.core.sector_rotation.aiohttp.ClientSession",
            return_value=_AsyncCtx(mock_session),
        ):
            await analyzer.fetch()

        assert analyzer._circuit_open is True
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "mixed"
        assert snapshot["leading_sectors"] == []

        # Second call should skip fetch entirely (circuit open)
        mock_session.get.reset_mock()
        with patch(
            "argus.core.sector_rotation.aiohttp.ClientSession",
            return_value=_AsyncCtx(mock_session),
        ):
            await analyzer.fetch()
        mock_session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_timeout_degrades_gracefully(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=TimeoutError("timed out"))

        with patch(
            "argus.core.sector_rotation.aiohttp.ClientSession",
            return_value=_AsyncCtx(mock_session),
        ):
            await analyzer.fetch()

        assert analyzer._circuit_open is False
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "mixed"
        assert snapshot["leading_sectors"] == []

    @pytest.mark.asyncio
    async def test_fetch_success_classifies(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=_make_sector_data(RISK_ON_LEADING)
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=_AsyncCtx(mock_response))

        with patch(
            "argus.core.sector_rotation.aiohttp.ClientSession",
            return_value=_AsyncCtx(mock_session),
        ):
            await analyzer.fetch()

        assert analyzer._circuit_open is False
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "risk_on"
        assert len(snapshot["leading_sectors"]) == 3

    @pytest.mark.asyncio
    async def test_fetch_no_api_key_degrades(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key=None,
        )
        await analyzer.fetch()
        assert analyzer._circuit_open is False
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "mixed"


# ---------------------------------------------------------------------------
# get_sector_snapshot
# ---------------------------------------------------------------------------


class TestGetSectorSnapshot:
    """get_sector_snapshot returns current state."""

    def test_snapshot_returns_current_state_after_classify(self) -> None:
        analyzer = SectorRotationAnalyzer(
            config=_default_config(),
            fmp_base_url="https://example.com",
            fmp_api_key="key",
        )
        analyzer._classify(_make_sector_data(RISK_OFF_LEADING))
        snapshot = analyzer.get_sector_snapshot()
        assert snapshot["sector_rotation_phase"] == "risk_off"
        assert isinstance(snapshot["leading_sectors"], list)
        assert isinstance(snapshot["lagging_sectors"], list)


# ---------------------------------------------------------------------------
# _parse_sector_data
# ---------------------------------------------------------------------------


class TestParseSectorData:
    """Internal parser tests."""

    def test_sorts_descending_by_performance(self) -> None:
        data = _make_sector_data([("A", -1.0), ("B", 3.0), ("C", 0.5)])
        result = _parse_sector_data(data)
        assert [name for name, _ in result] == ["B", "C", "A"]

    def test_skips_entries_with_missing_change(self) -> None:
        data = [
            {"sector": "Tech", "changesPercentage": 1.0},
            {"sector": "Health"},
            {"sector": "Util", "changesPercentage": None},
        ]
        result = _parse_sector_data(data)
        assert len(result) == 1
        assert result[0][0] == "Tech"

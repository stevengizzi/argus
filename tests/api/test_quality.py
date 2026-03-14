"""Tests for quality scoring API routes.

Sprint 24, Session 8.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.auth import create_access_token
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.event_bus import EventBus
from argus.db.manager import DatabaseManager
from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.quality_engine import SetupQualityEngine

_ET = ZoneInfo("America/New_York")


# --- Fixtures ---


@pytest.fixture
async def quality_db(tmp_path) -> AsyncGenerator[DatabaseManager, None]:
    """Provide an initialized DatabaseManager with quality_history table."""
    db = DatabaseManager(tmp_path / "quality_test.db")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def quality_engine(quality_db: DatabaseManager) -> SetupQualityEngine:
    """Provide a SetupQualityEngine backed by the test DB."""
    config = QualityEngineConfig()
    return SetupQualityEngine(config=config, db_manager=quality_db)


@pytest.fixture
async def seeded_quality_engine(
    quality_engine: SetupQualityEngine,
    quality_db: DatabaseManager,
) -> SetupQualityEngine:
    """Seed quality_history with test data and return the engine."""
    today = datetime.now(_ET).strftime("%Y-%m-%d")
    yesterday = "2026-03-13"

    rows = [
        # Today — AAPL, two records (latest should be returned for /symbol)
        (
            "id_aapl_1", "AAPL", "orb_breakout", f"{today}T09:35:00",
            80.0, 70.0, 65.0, 50.0, 80.0,
            72.0, "A-", "A-",
            185.0, 183.0, 100, None,
        ),
        (
            "id_aapl_2", "AAPL", "orb_breakout", f"{today}T09:45:00",
            85.0, 75.0, 70.0, 50.0, 80.0,
            75.0, "A", "A",
            186.0, 184.0, 120, None,
        ),
        # Today — NVDA, grade B+
        (
            "id_nvda_1", "NVDA", "orb_scalp", f"{today}T09:40:00",
            60.0, 55.0, 50.0, 50.0, 70.0,
            57.0, "B+", "B+",
            750.0, 740.0, 50, None,
        ),
        # Today — TSLA, grade C (below min_grade_to_trade default C+)
        (
            "id_tsla_1", "TSLA", "vwap_reclaim", f"{today}T10:00:00",
            30.0, 20.0, 40.0, 50.0, 20.0,
            32.0, "C", "C",
            200.0, 198.0, 0, None,
        ),
        # Today — MSFT, grade A+
        (
            "id_msft_1", "MSFT", "orb_breakout", f"{today}T09:50:00",
            95.0, 90.0, 85.0, 50.0, 80.0,
            88.0, "A+", "A+",
            420.0, 415.0, 80, None,
        ),
        # Yesterday — AMD, grade B
        (
            "id_amd_1", "AMD", "orb_scalp", f"{yesterday}T10:15:00",
            55.0, 50.0, 45.0, 50.0, 60.0,
            52.0, "B", "B",
            150.0, 147.0, 60, None,
        ),
        # Yesterday — GOOG, grade A
        (
            "id_goog_1", "GOOG", "orb_breakout", f"{yesterday}T09:35:00",
            82.0, 78.0, 72.0, 50.0, 80.0,
            74.0, "A", "A",
            175.0, 172.0, 50, None,
        ),
    ]

    for row in rows:
        await quality_db.execute(
            """
            INSERT INTO quality_history (
                id, symbol, strategy_id, scored_at,
                pattern_strength, catalyst_quality, volume_profile,
                historical_match, regime_alignment,
                composite_score, grade, risk_tier,
                entry_price, stop_price, calculated_shares,
                signal_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
    await quality_db.commit()

    return quality_engine


@pytest.fixture
async def quality_app_state(
    seeded_quality_engine: SetupQualityEngine,
    test_event_bus: EventBus,
    test_trade_logger,
    test_broker,
    test_health_monitor,
    test_risk_manager,
    test_order_manager,
    test_clock,
    test_system_config,
) -> AppState:
    """Provide AppState with seeded quality engine."""
    return AppState(
        event_bus=test_event_bus,
        trade_logger=test_trade_logger,
        broker=test_broker,
        health_monitor=test_health_monitor,
        risk_manager=test_risk_manager,
        order_manager=test_order_manager,
        clock=test_clock,
        config=test_system_config,
        start_time=time.time(),
        quality_engine=seeded_quality_engine,
    )


@pytest.fixture
async def quality_client(
    quality_app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx.AsyncClient with quality engine wired."""
    app = create_app(quality_app_state)
    app.state.app_state = quality_app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# --- Tests ---


@pytest.mark.asyncio
async def test_quality_symbol_returns_latest(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Insert 2 records for AAPL, verify latest (higher score) returned."""
    resp = await quality_client.get(
        "/api/v1/quality/AAPL", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["score"] == 75.0
    assert data["grade"] == "A"
    assert data["scored_at"].startswith(datetime.now(_ET).strftime("%Y-%m-%d"))
    assert data["components"]["ps"] == 85.0


@pytest.mark.asyncio
async def test_quality_symbol_404(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """No records for UNKNOWN → 404."""
    resp = await quality_client.get(
        "/api/v1/quality/UNKNOWN", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_quality_symbol_case_insensitive(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Lowercase symbol should still match."""
    resp = await quality_client.get(
        "/api/v1/quality/aapl", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_quality_history_pagination(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify limit/offset pagination."""
    resp = await quality_client.get(
        "/api/v1/quality/history?limit=3&offset=0", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    assert data["limit"] == 3
    assert data["offset"] == 0
    assert len(data["items"]) == 3

    # Second page
    resp2 = await quality_client.get(
        "/api/v1/quality/history?limit=3&offset=3", headers=auth_headers
    )
    data2 = resp2.json()
    assert data2["total"] == 7
    assert len(data2["items"]) == 3

    # Third page (remaining)
    resp3 = await quality_client.get(
        "/api/v1/quality/history?limit=3&offset=6", headers=auth_headers
    )
    data3 = resp3.json()
    assert len(data3["items"]) == 1


@pytest.mark.asyncio
async def test_quality_history_filter_by_grade(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Filter grade='A' → only A records."""
    resp = await quality_client.get(
        "/api/v1/quality/history?grade=A", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # AAPL (latest) + GOOG
    for item in data["items"]:
        assert item["grade"] == "A"


@pytest.mark.asyncio
async def test_quality_history_filter_by_symbol(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Filter symbol → correct records."""
    resp = await quality_client.get(
        "/api/v1/quality/history?symbol=AAPL", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_quality_history_filter_by_strategy(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Filter strategy_id → correct records."""
    resp = await quality_client.get(
        "/api/v1/quality/history?strategy_id=orb_scalp", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # NVDA + AMD
    for item in data["items"]:
        assert item["symbol"] in ("NVDA", "AMD")


@pytest.mark.asyncio
async def test_quality_history_date_range_filter(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """start_date/end_date filtering."""
    # Only yesterday
    resp = await quality_client.get(
        "/api/v1/quality/history?start_date=2026-03-13&end_date=2026-03-13",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # AMD + GOOG (yesterday only)
    symbols = {item["symbol"] for item in data["items"]}
    assert symbols == {"AMD", "GOOG"}


@pytest.mark.asyncio
async def test_quality_distribution_all_grades(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """All grades present (zero counts for empty)."""
    resp = await quality_client.get(
        "/api/v1/quality/distribution", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    # All 8 grades should be present
    assert len(data["grades"]) == 8
    for g in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C"):
        assert g in data["grades"]

    # Today: A+ (MSFT), A (AAPL), A- (AAPL older), B+ (NVDA), C (TSLA) = 5
    assert data["total"] == 5
    assert data["grades"]["A+"] == 1
    assert data["grades"]["A"] == 1
    assert data["grades"]["A-"] == 1
    assert data["grades"]["B+"] == 1
    assert data["grades"]["C"] == 1
    # Empty grades
    assert data["grades"]["B"] == 0
    assert data["grades"]["B-"] == 0
    assert data["grades"]["C+"] == 0


@pytest.mark.asyncio
async def test_quality_distribution_includes_filtered_count(
    quality_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Count of below-min-grade signals (default min is C+)."""
    resp = await quality_client.get(
        "/api/v1/quality/distribution", headers=auth_headers
    )
    data = resp.json()
    # C is below C+ → filtered = 1 (TSLA)
    assert data["filtered"] == 1


@pytest.mark.asyncio
async def test_quality_endpoints_require_auth(
    quality_client: AsyncClient,
) -> None:
    """All 3 endpoints return 401 without JWT."""
    for url in (
        "/api/v1/quality/AAPL",
        "/api/v1/quality/history",
        "/api/v1/quality/distribution",
    ):
        resp = await quality_client.get(url)
        assert resp.status_code == 401, f"{url} should require auth"


@pytest.mark.asyncio
async def test_quality_503_when_engine_not_available(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Returns 503 when quality_engine is None on AppState."""
    resp = await client.get(
        "/api/v1/quality/AAPL", headers=auth_headers
    )
    assert resp.status_code == 503

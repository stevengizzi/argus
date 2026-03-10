"""Tests for Intelligence API routes.

Sprint 23.5 Session 4 — DEC-164
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.auth import create_access_token, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.intelligence.briefing import BriefingGenerator
from argus.intelligence.config import BriefingConfig
from argus.intelligence.models import (
    ClassifiedCatalyst,
    IntelligenceBrief,
    compute_headline_hash,
)
from argus.intelligence.storage import CatalystStorage

_ET = ZoneInfo("America/New_York")
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


def make_catalyst(
    symbol: str,
    headline: str,
    category: str = "news_sentiment",
    quality_score: float = 50.0,
    trading_relevance: str = "medium",
    hours_ago: int = 1,
) -> ClassifiedCatalyst:
    """Create a test catalyst."""
    now = datetime.now(_ET)
    return ClassifiedCatalyst(
        headline=headline,
        symbol=symbol,
        source="test",
        published_at=now - timedelta(hours=hours_ago),
        fetched_at=now,
        category=category,
        quality_score=quality_score,
        summary=f"Summary for {headline}",
        trading_relevance=trading_relevance,
        classified_by="test",
        classified_at=now,
        headline_hash=compute_headline_hash(headline),
    )


@pytest.fixture
async def catalyst_storage() -> AsyncGenerator[CatalystStorage, None]:
    """Create an in-memory catalyst storage."""
    storage = CatalystStorage(":memory:")
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.fixture
def mock_briefing_generator(catalyst_storage: CatalystStorage) -> MagicMock:
    """Create a mock briefing generator."""
    generator = MagicMock(spec=BriefingGenerator)
    generator.generate_brief = AsyncMock()
    return generator


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set up JWT secret for tests."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)
    return TEST_JWT_SECRET


@pytest.fixture
def auth_headers(jwt_secret: str) -> dict[str, str]:
    """Provide Authorization headers with a valid JWT token."""
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def minimal_app_state(
    catalyst_storage: CatalystStorage,
    mock_briefing_generator: MagicMock,
) -> AppState:
    """Create a minimal AppState with intelligence services."""
    from argus.analytics.trade_logger import TradeLogger
    from argus.core.event_bus import EventBus
    from argus.core.health import HealthMonitor
    from argus.core.risk_manager import RiskManager
    from argus.db.manager import DatabaseManager
    from argus.execution.order_manager import OrderManager
    from argus.execution.simulated_broker import SimulatedBroker
    from argus.core.clock import FixedClock
    from argus.core.config import (
        ApiConfig,
        HealthConfig,
        OrderManagerConfig,
        RiskConfig,
        SystemConfig,
    )
    from datetime import UTC

    # Create minimal required components
    event_bus = EventBus()
    clock = FixedClock(datetime(2026, 3, 10, 10, 0, 0, tzinfo=UTC))
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()

    # Create in-memory DB for trade logger
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DatabaseManager(db_path)
        await db.initialize()

        trade_logger = TradeLogger(db)
        health_monitor = HealthMonitor(
            event_bus=event_bus,
            clock=clock,
            config=HealthConfig(),
            broker=broker,
            trade_logger=trade_logger,
        )
        risk_manager = RiskManager(
            config=RiskConfig(),
            broker=broker,
            event_bus=event_bus,
            clock=clock,
        )
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=OrderManagerConfig(),
            trade_logger=trade_logger,
        )

        api_config = ApiConfig(
            enabled=True,
            host="127.0.0.1",
            port=8000,
            password_hash="unused",
            jwt_secret_env="ARGUS_JWT_SECRET",
        )

        state = AppState(
            event_bus=event_bus,
            trade_logger=trade_logger,
            broker=broker,
            health_monitor=health_monitor,
            risk_manager=risk_manager,
            order_manager=order_manager,
            clock=clock,
            config=SystemConfig(api=api_config),
            start_time=time.time(),
            catalyst_storage=catalyst_storage,
            briefing_generator=mock_briefing_generator,
        )

        yield state

        await db.close()


@pytest.fixture
async def client(
    minimal_app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an HTTP client for testing."""
    app = create_app(minimal_app_state)
    app.state.app_state = minimal_app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class TestCatalystsEndpoints:
    """Tests for /catalysts endpoints."""

    @pytest.mark.asyncio
    async def test_get_catalysts_by_symbol_returns_catalysts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        catalyst_storage: CatalystStorage,
    ) -> None:
        """GET /catalysts/{symbol} returns catalysts for known symbol."""
        # Store catalysts
        cat1 = make_catalyst("AAPL", "AAPL earnings beat", "earnings", 85)
        cat2 = make_catalyst("AAPL", "AAPL guidance raised", "earnings", 75)
        await catalyst_storage.store_catalyst(cat1)
        await catalyst_storage.store_catalyst(cat2)

        response = await client.get(
            "/api/v1/catalysts/AAPL",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["count"] == 2
        assert len(data["catalysts"]) == 2

    @pytest.mark.asyncio
    async def test_get_catalysts_by_symbol_returns_empty_for_unknown(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /catalysts/{symbol} returns empty list (200) for unknown symbol."""
        response = await client.get(
            "/api/v1/catalysts/UNKNOWN",
            headers=auth_headers,
        )

        assert response.status_code == 200  # Not 404!
        data = response.json()
        assert data["symbol"] == "UNKNOWN"
        assert data["count"] == 0
        assert data["catalysts"] == []

    @pytest.mark.asyncio
    async def test_get_recent_catalysts_with_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        catalyst_storage: CatalystStorage,
    ) -> None:
        """GET /catalysts/recent returns catalysts with pagination."""
        # Store 5 catalysts
        for i in range(5):
            cat = make_catalyst(f"SYM{i}", f"News {i}", "news_sentiment", 50 + i)
            await catalyst_storage.store_catalyst(cat)

        # Get first page
        response = await client.get(
            "/api/v1/catalysts/recent?limit=2&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["total"] == 5
        assert len(data["catalysts"]) == 2

        # Get second page
        response2 = await client.get(
            "/api/v1/catalysts/recent?limit=2&offset=2",
            headers=auth_headers,
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["count"] == 2
        assert data2["total"] == 5

    @pytest.mark.asyncio
    async def test_catalysts_endpoints_require_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Catalyst endpoints return 401 without JWT token."""
        response = await client.get("/api/v1/catalysts/AAPL")
        assert response.status_code == 401

        response = await client.get("/api/v1/catalysts/recent")
        assert response.status_code == 401


class TestBriefingEndpoints:
    """Tests for /premarket/briefing endpoints."""

    @pytest.mark.asyncio
    async def test_get_briefing_returns_todays_briefing(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        catalyst_storage: CatalystStorage,
    ) -> None:
        """GET /premarket/briefing returns briefing for today."""
        # Store a briefing
        today = datetime.now(_ET).date().isoformat()
        brief = IntelligenceBrief(
            date=today,
            brief_type="premarket",
            content="# Pre-Market Brief\n\nTest content.",
            symbols_covered=["AAPL", "TSLA"],
            catalyst_count=5,
            generated_at=datetime.now(_ET),
            generation_cost_usd=0.05,
        )
        await catalyst_storage.store_brief(brief)

        response = await client.get(
            "/api/v1/premarket/briefing",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == today
        assert data["brief_type"] == "premarket"
        assert "Test content" in data["content"]
        assert data["catalyst_count"] == 5
        assert data["symbols_covered"] == ["AAPL", "TSLA"]

    @pytest.mark.asyncio
    async def test_get_briefing_returns_404_when_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /premarket/briefing returns 404 when no briefing exists."""
        response = await client.get(
            "/api/v1/premarket/briefing?date=2025-01-01",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "No briefing found for 2025-01-01" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_briefing_history_returns_ordered_list(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        catalyst_storage: CatalystStorage,
    ) -> None:
        """GET /premarket/briefing/history returns briefings ordered by date DESC."""
        # Store briefings for different dates
        dates = ["2026-03-08", "2026-03-10", "2026-03-09"]
        for date in dates:
            brief = IntelligenceBrief(
                date=date,
                brief_type="premarket",
                content=f"Brief for {date}",
                symbols_covered=["AAPL"],
                catalyst_count=1,
                generated_at=datetime.now(_ET),
                generation_cost_usd=0.01,
            )
            await catalyst_storage.store_brief(brief)

        response = await client.get(
            "/api/v1/premarket/briefing/history",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3

        # Should be in descending date order
        dates_returned = [b["date"] for b in data["briefings"]]
        assert dates_returned == ["2026-03-10", "2026-03-09", "2026-03-08"]

    @pytest.mark.asyncio
    async def test_generate_briefing_creates_and_returns_briefing(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        mock_briefing_generator: MagicMock,
    ) -> None:
        """POST /premarket/briefing/generate creates and returns briefing."""
        # Mock the generator response
        today = datetime.now(_ET).date().isoformat()
        mock_brief = IntelligenceBrief(
            date=today,
            brief_type="premarket",
            content="# Pre-Market Brief\n\nGenerated content.",
            symbols_covered=["AAPL", "TSLA"],
            catalyst_count=3,
            generated_at=datetime.now(_ET),
            generation_cost_usd=0.10,
        )
        mock_briefing_generator.generate_brief.return_value = mock_brief

        response = await client.post(
            "/api/v1/premarket/briefing/generate",
            json={"symbols": ["AAPL", "TSLA"]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == today
        assert data["brief_type"] == "premarket"
        assert "Generated content" in data["content"]

        # Verify generator was called with correct symbols
        mock_briefing_generator.generate_brief.assert_called_once_with(["AAPL", "TSLA"])

    @pytest.mark.asyncio
    async def test_briefing_endpoints_require_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Briefing endpoints return 401 without JWT token."""
        response = await client.get("/api/v1/premarket/briefing")
        assert response.status_code == 401

        response = await client.get("/api/v1/premarket/briefing/history")
        assert response.status_code == 401

        response = await client.post(
            "/api/v1/premarket/briefing/generate",
            json={"symbols": ["AAPL"]},
        )
        assert response.status_code == 401


class TestServiceAvailability:
    """Tests for service availability checks."""

    @pytest.mark.asyncio
    async def test_returns_503_when_storage_not_available(
        self,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns 503 when catalyst storage is not available."""
        from argus.analytics.trade_logger import TradeLogger
        from argus.core.event_bus import EventBus
        from argus.core.health import HealthMonitor
        from argus.core.risk_manager import RiskManager
        from argus.db.manager import DatabaseManager
        from argus.execution.order_manager import OrderManager
        from argus.execution.simulated_broker import SimulatedBroker
        from argus.core.clock import FixedClock
        from argus.core.config import (
            ApiConfig,
            HealthConfig,
            OrderManagerConfig,
            RiskConfig,
            SystemConfig,
        )
        from datetime import UTC
        from pathlib import Path
        import tempfile

        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 3, 10, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000.0)
        await broker.connect()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseManager(db_path)
            await db.initialize()

            trade_logger = TradeLogger(db)
            health_monitor = HealthMonitor(
                event_bus=event_bus,
                clock=clock,
                config=HealthConfig(),
                broker=broker,
                trade_logger=trade_logger,
            )
            risk_manager = RiskManager(
                config=RiskConfig(),
                broker=broker,
                event_bus=event_bus,
                clock=clock,
            )
            order_manager = OrderManager(
                event_bus=event_bus,
                broker=broker,
                clock=clock,
                config=OrderManagerConfig(),
                trade_logger=trade_logger,
            )

            api_config = ApiConfig(
                enabled=True,
                host="127.0.0.1",
                port=8000,
                password_hash="unused",
                jwt_secret_env="ARGUS_JWT_SECRET",
            )

            # Create state WITHOUT catalyst_storage
            state = AppState(
                event_bus=event_bus,
                trade_logger=trade_logger,
                broker=broker,
                health_monitor=health_monitor,
                risk_manager=risk_manager,
                order_manager=order_manager,
                clock=clock,
                config=SystemConfig(api=api_config),
                start_time=time.time(),
                catalyst_storage=None,  # Not available
                briefing_generator=None,
            )

            app = create_app(state)
            app.state.app_state = state

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/catalysts/AAPL",
                    headers=auth_headers,
                )
                assert response.status_code == 503
                assert "Catalyst storage not available" in response.json()["detail"]

            await db.close()


class TestSprint236Fixes:
    """Tests for Sprint 23.6 fixes (C2, S1, S2, M3)."""

    @pytest.mark.asyncio
    async def test_recent_catalysts_total_count(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        catalyst_storage: CatalystStorage,
    ) -> None:
        """Verify response total field uses COUNT(*) query, not len()."""
        # Store exactly 5 catalysts
        for i in range(5):
            cat = make_catalyst(f"SYM{i}", f"News {i}", "news_sentiment", 50 + i)
            await catalyst_storage.store_catalyst(cat)

        # Request with limit=2
        response = await client.get(
            "/api/v1/catalysts/recent?limit=2&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2  # Only 2 returned
        assert data["total"] == 5  # But total should be 5 (from COUNT query)

    @pytest.mark.asyncio
    async def test_catalysts_by_symbol_since_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        catalyst_storage: CatalystStorage,
    ) -> None:
        """Verify since parameter filters correctly via API."""
        now = datetime.now(_ET)

        # Store 3 catalysts with different published_at times
        times = [
            now - timedelta(hours=3),  # Oldest
            now - timedelta(hours=2),  # Middle
            now - timedelta(hours=1),  # Newest
        ]

        for i, pub_time in enumerate(times):
            cat = ClassifiedCatalyst(
                headline=f"MSFT news {i}",
                symbol="MSFT",
                source="test",
                published_at=pub_time,
                fetched_at=now,
                category="news_sentiment",
                quality_score=50.0,
                summary=f"Summary {i}",
                trading_relevance="medium",
                classified_by="fallback",
                classified_at=now,
                headline_hash=compute_headline_hash(f"MSFT news {i}"),
            )
            await catalyst_storage.store_catalyst(cat)

        # Query with since = 2.5 hours ago (should return 2 newest)
        since_time = (now - timedelta(hours=2, minutes=30)).isoformat()
        response = await client.get(
            f"/api/v1/catalysts/MSFT?since={since_time}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["symbol"] == "MSFT"

    @pytest.mark.asyncio
    async def test_schema_migration_alter_table(self) -> None:
        """Create DB without fetched_at column, re-initialize, verify column added."""
        import tempfile
        from pathlib import Path

        import aiosqlite

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_migration.db"

            # Create DB with old schema (no fetched_at column)
            async with aiosqlite.connect(str(db_path)) as conn:
                await conn.execute("""
                    CREATE TABLE catalyst_events (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        catalyst_type TEXT NOT NULL,
                        quality_score REAL NOT NULL,
                        headline TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        source TEXT NOT NULL,
                        source_url TEXT,
                        filing_type TEXT,
                        headline_hash TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        classified_at TEXT NOT NULL,
                        classified_by TEXT NOT NULL,
                        trading_relevance TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                await conn.commit()

            # Verify column doesn't exist initially
            async with aiosqlite.connect(str(db_path)) as conn:
                cursor = await conn.execute("PRAGMA table_info(catalyst_events)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                assert "fetched_at" not in column_names

            # Initialize storage (should run migration)
            storage = CatalystStorage(db_path)
            await storage.initialize()

            # Verify column now exists
            conn = storage._ensure_connected()
            cursor = await conn.execute("PRAGMA table_info(catalyst_events)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            assert "fetched_at" in column_names

            await storage.close()

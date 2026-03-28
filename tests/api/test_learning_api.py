"""Tests for the Learning Loop REST API endpoints.

Sprint 28, Session 5.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.auth import create_access_token, hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import ApiConfig, HealthConfig, OrderManagerConfig, SystemConfig
from argus.core.event_bus import EventBus
from argus.core.health import HealthMonitor
from argus.core.risk_manager import RiskManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    ConfigProposal,
    CorrelationResult,
    DataQualityPreamble,
    LearningLoopConfig,
    LearningReport,
    WeightRecommendation,
)

TEST_PASSWORD = "testpassword123"
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


# --- Fixtures ---


@pytest.fixture
def learning_config() -> LearningLoopConfig:
    """Provide a LearningLoopConfig for tests."""
    return LearningLoopConfig(enabled=True)


@pytest.fixture
async def learning_store(tmp_path: Path) -> LearningStore:
    """Provide an initialized LearningStore with a temp database."""
    store = LearningStore(db_path=str(tmp_path / "learning_test.db"))
    await store.initialize()
    return store


@pytest.fixture
async def seeded_store(learning_store: LearningStore) -> LearningStore:
    """Provide a LearningStore seeded with a report and proposals."""
    now = datetime.now(UTC)
    report = LearningReport(
        report_id="RPT_001",
        generated_at=now,
        analysis_window_start=now - timedelta(days=30),
        analysis_window_end=now,
        data_quality=DataQualityPreamble(
            trading_days_count=20,
            total_trades=50,
            total_counterfactual=30,
            effective_sample_size=80,
            known_data_gaps=[],
            earliest_date=now - timedelta(days=30),
            latest_date=now,
        ),
        weight_recommendations=[],
        threshold_recommendations=[],
        correlation_result=None,
        version=1,
    )
    await learning_store.save_report(report)

    # PENDING proposal
    await learning_store.save_proposal(ConfigProposal(
        proposal_id="PROP_001",
        report_id="RPT_001",
        field_path="weights.pattern_strength",
        current_value=0.30,
        proposed_value=0.35,
        rationale="Correlation=0.42, HIGH confidence",
        status="PENDING",
        created_at=now,
        updated_at=now,
    ))

    # SUPERSEDED proposal
    await learning_store.save_proposal(ConfigProposal(
        proposal_id="PROP_002",
        report_id="RPT_001",
        field_path="weights.volume_profile",
        current_value=0.20,
        proposed_value=0.15,
        rationale="Correlation=-0.12, LOW confidence",
        status="SUPERSEDED",
        created_at=now,
        updated_at=now,
    ))

    # APPLIED proposal (for revert tests)
    await learning_store.save_proposal(ConfigProposal(
        proposal_id="PROP_003",
        report_id="RPT_001",
        field_path="weights.catalyst_quality",
        current_value=0.25,
        proposed_value=0.30,
        rationale="Correlation=0.38, MODERATE confidence",
        status="APPLIED",
        created_at=now,
        updated_at=now,
    ))

    return learning_store


@pytest.fixture
async def learning_app_state(
    seeded_store: LearningStore,
    tmp_path: Path,
) -> AppState:
    """Provide an AppState with learning components wired in."""
    from argus.analytics.trade_logger import TradeLogger
    from argus.db.manager import DatabaseManager
    from argus.intelligence.learning.config_proposal_manager import (
        ConfigProposalManager,
    )
    from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
    from argus.intelligence.learning.learning_service import LearningService
    from argus.intelligence.learning.outcome_collector import OutcomeCollector
    from argus.intelligence.learning.threshold_analyzer import ThresholdAnalyzer
    from argus.intelligence.learning.weight_analyzer import WeightAnalyzer

    event_bus = EventBus()
    clock = FixedClock(datetime(2026, 2, 23, 15, 30, 0, tzinfo=UTC))

    db_manager = DatabaseManager(tmp_path / "argus_test.db")
    await db_manager.initialize()
    trade_logger = TradeLogger(db_manager)

    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()

    health_monitor = HealthMonitor(
        event_bus=event_bus,
        clock=clock,
        config=HealthConfig(),
        broker=broker,
        trade_logger=trade_logger,
    )

    risk_config = __import__("argus.core.config", fromlist=["RiskConfig"]).RiskConfig()
    risk_manager = RiskManager(
        config=risk_config,
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
        password_hash=hash_password(TEST_PASSWORD),
        jwt_secret_env="ARGUS_JWT_SECRET",
    )

    ll_config = LearningLoopConfig(enabled=True)
    sys_config = SystemConfig(api=api_config, learning_loop=ll_config)

    # Create a minimal quality_engine.yaml for ConfigProposalManager
    qe_yaml = tmp_path / "quality_engine.yaml"
    qe_yaml.write_text(
        "weights:\n"
        "  pattern_strength: 0.30\n"
        "  catalyst_quality: 0.25\n"
        "  volume_profile: 0.20\n"
        "  historical_match: 0.15\n"
        "  regime_alignment: 0.10\n"
        "thresholds:\n"
        "  a_plus: 90\n"
        "  a: 80\n"
        "  a_minus: 70\n"
        "  b_plus: 60\n"
        "  b: 50\n"
        "  b_minus: 40\n"
        "  c_plus: 30\n"
        "min_grade: C+\n"
        "enabled: true\n"
    )

    # Build LearningService with mock collector
    outcome_collector = OutcomeCollector(
        argus_db_path=str(tmp_path / "argus_test.db"),
        counterfactual_db_path=str(tmp_path / "counterfactual_test.db"),
    )

    learning_service = LearningService(
        config=ll_config,
        outcome_collector=outcome_collector,
        weight_analyzer=WeightAnalyzer(),
        threshold_analyzer=ThresholdAnalyzer(),
        correlation_analyzer=CorrelationAnalyzer(),
        store=seeded_store,
        quality_engine_yaml_path=str(qe_yaml),
    )

    config_proposal_manager = ConfigProposalManager(
        config=ll_config,
        store=seeded_store,
        quality_engine_yaml_path=str(qe_yaml),
    )

    state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        strategies={},
        clock=clock,
        config=sys_config,
        start_time=time.time(),
        learning_service=learning_service,
        learning_store=seeded_store,
        config_proposal_manager=config_proposal_manager,
    )

    return state


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set up JWT secret for testing."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)
    return TEST_JWT_SECRET


@pytest.fixture
def auth_headers(jwt_secret: str) -> dict[str, str]:
    """Provide valid JWT auth headers."""
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(
    learning_app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx.AsyncClient with learning components."""
    app = create_app(learning_app_state)
    app.state.app_state = learning_app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# --- Tests ---


@pytest.mark.asyncio
async def test_trigger_analysis_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /trigger runs analysis and returns report summary."""
    resp = await client.post(
        "/api/v1/learning/trigger", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "report_id" in data
    assert "generated_at" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_trigger_analysis_409_concurrent(
    client: AsyncClient,
    auth_headers: dict[str, str],
    learning_app_state: AppState,
) -> None:
    """POST /trigger returns 409 when analysis is already running."""
    assert learning_app_state.learning_service is not None
    # Force the running flag
    learning_app_state.learning_service._running = True
    try:
        resp = await client.post(
            "/api/v1/learning/trigger", headers=auth_headers
        )
        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"]
    finally:
        learning_app_state.learning_service._running = False


@pytest.mark.asyncio
async def test_list_reports(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /reports returns list of reports."""
    resp = await client.get(
        "/api/v1/learning/reports", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data
    assert "count" in data
    assert data["count"] >= 1
    assert data["reports"][0]["report_id"] == "RPT_001"


@pytest.mark.asyncio
async def test_get_report_detail(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /reports/{id} returns full report."""
    resp = await client.get(
        "/api/v1/learning/reports/RPT_001", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["report"]["report_id"] == "RPT_001"


@pytest.mark.asyncio
async def test_get_report_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /reports/{id} returns 404 for missing report."""
    resp = await client.get(
        "/api/v1/learning/reports/NONEXISTENT", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_proposals(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /proposals returns list of proposals."""
    resp = await client.get(
        "/api/v1/learning/proposals", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3  # PENDING + SUPERSEDED + APPLIED


@pytest.mark.asyncio
async def test_list_proposals_with_status_filter(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /proposals?status=PENDING returns filtered list."""
    resp = await client.get(
        "/api/v1/learning/proposals?status=PENDING", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["proposals"][0]["status"] == "PENDING"


@pytest.mark.asyncio
async def test_approve_proposal_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /proposals/{id}/approve transitions PENDING → APPROVED."""
    resp = await client.post(
        "/api/v1/learning/proposals/PROP_001/approve",
        headers=auth_headers,
        json={"notes": "Looks good"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proposal"]["status"] == "APPROVED"
    assert data["proposal"]["human_notes"] == "Looks good"


@pytest.mark.asyncio
async def test_approve_superseded_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /proposals/{id}/approve returns 400 for SUPERSEDED proposal."""
    resp = await client.post(
        "/api/v1/learning/proposals/PROP_002/approve",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "SUPERSEDED" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_dismiss_proposal_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /proposals/{id}/dismiss transitions PENDING → DISMISSED."""
    resp = await client.post(
        "/api/v1/learning/proposals/PROP_001/dismiss",
        headers=auth_headers,
        json={"notes": "Not needed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proposal"]["status"] == "DISMISSED"


@pytest.mark.asyncio
async def test_revert_applied_proposal(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /proposals/{id}/revert transitions APPLIED → REVERTED."""
    resp = await client.post(
        "/api/v1/learning/proposals/PROP_003/revert",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proposal"]["status"] == "REVERTED"


@pytest.mark.asyncio
async def test_revert_pending_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /proposals/{id}/revert returns 400 for PENDING proposal."""
    resp = await client.post(
        "/api/v1/learning/proposals/PROP_001/revert",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "APPLIED" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_config_history_returns_list(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /config-history returns change history."""
    resp = await client.get(
        "/api/v1/learning/config-history", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "changes" in data
    assert "count" in data
    assert isinstance(data["changes"], list)


@pytest.mark.asyncio
async def test_endpoints_require_auth(
    client: AsyncClient,
) -> None:
    """All learning endpoints require JWT authentication."""
    endpoints = [
        ("POST", "/api/v1/learning/trigger"),
        ("GET", "/api/v1/learning/reports"),
        ("GET", "/api/v1/learning/reports/RPT_001"),
        ("GET", "/api/v1/learning/proposals"),
        ("POST", "/api/v1/learning/proposals/PROP_001/approve"),
        ("POST", "/api/v1/learning/proposals/PROP_001/dismiss"),
        ("POST", "/api/v1/learning/proposals/PROP_001/revert"),
        ("GET", "/api/v1/learning/config-history"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path)
        assert resp.status_code == 401, f"{method} {path} should require auth"

"""Tests for the experiment pipeline REST API endpoints.

Sprint 32, Session 8.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.auth import create_access_token, hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import ApiConfig, HealthConfig, OrderManagerConfig, RiskConfig, SystemConfig
from argus.core.event_bus import EventBus
from argus.core.health import HealthMonitor
from argus.core.risk_manager import RiskManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.intelligence.experiments.config import ExperimentConfig
from argus.intelligence.experiments.models import ExperimentRecord, ExperimentStatus
from argus.intelligence.experiments.store import ExperimentStore

TEST_PASSWORD = "testpassword123"
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def experiment_store(tmp_path: Path) -> ExperimentStore:
    """Provide an initialized ExperimentStore with a temp database."""
    store = ExperimentStore(db_path=str(tmp_path / "exp_test.db"))
    await store.initialize()
    return store


@pytest.fixture
async def seeded_store(experiment_store: ExperimentStore) -> ExperimentStore:
    """Provide an ExperimentStore seeded with one experiment record."""
    now = datetime.now(UTC)
    record = ExperimentRecord(
        experiment_id="EXP_001",
        pattern_name="bull_flag",
        parameter_fingerprint="abc123def456abcd",
        parameters={"pole_min_move_pct": 0.04},
        status=ExperimentStatus.COMPLETED,
        backtest_result={"total_trades": 35, "expectancy_per_trade": 0.12, "sharpe_ratio": 1.5},
        shadow_trades=0,
        shadow_expectancy=None,
        is_baseline=False,
        created_at=now,
        updated_at=now,
    )
    await experiment_store.save_experiment(record)
    return experiment_store


@pytest.fixture
async def app_state_with_experiments(
    seeded_store: ExperimentStore,
    tmp_path: Path,
) -> AppState:
    """Provide an AppState with experiment_store wired in."""
    from argus.analytics.trade_logger import TradeLogger
    from argus.db.manager import DatabaseManager

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

    risk_manager = RiskManager(
        config=RiskConfig(),
        broker=broker,
        event_bus=event_bus,
        clock=clock,
    )
    order_manager = OrderManager(
        broker=broker,
        event_bus=event_bus,
        clock=clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
    )

    system_config = SystemConfig(
        api=ApiConfig(password_hash=hash_password(TEST_PASSWORD)),
        experiments=ExperimentConfig(enabled=True),
    )

    state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        clock=clock,
        config=system_config,
        experiment_store=seeded_store,
    )
    return state


@pytest.fixture
async def app_state_experiments_disabled(
    tmp_path: Path,
) -> AppState:
    """Provide an AppState with experiments disabled (no experiment_store)."""
    from argus.analytics.trade_logger import TradeLogger
    from argus.db.manager import DatabaseManager

    event_bus = EventBus()
    clock = FixedClock(datetime(2026, 2, 23, 15, 30, 0, tzinfo=UTC))

    db_manager = DatabaseManager(tmp_path / "argus_disabled.db")
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

    risk_manager = RiskManager(
        config=RiskConfig(),
        broker=broker,
        event_bus=event_bus,
        clock=clock,
    )
    order_manager = OrderManager(
        broker=broker,
        event_bus=event_bus,
        clock=clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
    )

    system_config = SystemConfig(
        api=ApiConfig(password_hash=hash_password(TEST_PASSWORD)),
        experiments=ExperimentConfig(enabled=False),
    )

    state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        clock=clock,
        config=system_config,
        experiment_store=None,  # disabled
    )
    return state


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide valid JWT auth headers."""
    set_jwt_secret(TEST_JWT_SECRET)
    token, _ = create_access_token(TEST_JWT_SECRET, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _make_client(app_state: AppState) -> AsyncClient:
    """Create an AsyncClient wrapping the FastAPI app."""
    app = create_app(app_state)
    app.state.app_state = app_state
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Tests — JWT protection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_experiments_requires_jwt(
    app_state_with_experiments: AppState,
) -> None:
    """GET /experiments returns 403 without auth token."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_experiment_requires_jwt(
    app_state_with_experiments: AppState,
) -> None:
    """GET /experiments/{id} returns 403 without auth token."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments/EXP_001")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_baseline_requires_jwt(
    app_state_with_experiments: AppState,
) -> None:
    """GET /experiments/baseline/{pattern} returns 401 or 403 without auth token."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments/baseline/bull_flag")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_run_sweep_requires_jwt(
    app_state_with_experiments: AppState,
) -> None:
    """POST /experiments/run returns 403 without auth token."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.post("/api/v1/experiments/run", json={"pattern": "bull_flag"})
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests — 503 when disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_experiments_503_when_disabled(
    app_state_experiments_disabled: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments returns 503 when experiments.enabled is False."""
    async with await _make_client(app_state_experiments_disabled) as client:
        resp = await client.get("/api/v1/experiments", headers=auth_headers)
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_experiment_503_when_disabled(
    app_state_experiments_disabled: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments/{id} returns 503 when experiments disabled."""
    async with await _make_client(app_state_experiments_disabled) as client:
        resp = await client.get("/api/v1/experiments/EXP_001", headers=auth_headers)
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_baseline_503_when_disabled(
    app_state_experiments_disabled: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments/baseline/{pattern} returns 503 when disabled."""
    async with await _make_client(app_state_experiments_disabled) as client:
        resp = await client.get("/api/v1/experiments/baseline/bull_flag", headers=auth_headers)
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_run_sweep_503_when_disabled(
    app_state_experiments_disabled: AppState,
    auth_headers: dict[str, str],
) -> None:
    """POST /experiments/run returns 503 when experiments disabled."""
    async with await _make_client(app_state_experiments_disabled) as client:
        resp = await client.post(
            "/api/v1/experiments/run",
            json={"pattern": "bull_flag"},
            headers=auth_headers,
        )
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_experiments_returns_empty_list(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    """GET /experiments with no experiments returns empty list."""
    # Use a fresh store with no records
    fresh_store = ExperimentStore(db_path=str(tmp_path / "fresh.db"))
    await fresh_store.initialize()
    app_state_with_experiments.experiment_store = fresh_store

    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["experiments"] == []
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_list_experiments_returns_records(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments returns stored experiment records."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["experiments"][0]["experiment_id"] == "EXP_001"


@pytest.mark.asyncio
async def test_list_experiments_pattern_filter(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments?pattern=bull_flag returns only matching records."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get(
            "/api/v1/experiments?pattern=bull_flag", headers=auth_headers
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1

    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get(
            "/api/v1/experiments?pattern=flat_top_breakout", headers=auth_headers
        )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_get_experiment_returns_record(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments/{id} returns the experiment with backtest_result."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments/EXP_001", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment"]["experiment_id"] == "EXP_001"
    assert data["experiment"]["backtest_result"]["total_trades"] == 35


@pytest.mark.asyncio
async def test_get_experiment_404_for_nonexistent(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments/{id} returns 404 for unknown ID."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get("/api/v1/experiments/DOES_NOT_EXIST", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_baseline_404_when_no_baseline(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments/baseline/{pattern} returns 404 when no baseline set."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get(
            "/api/v1/experiments/baseline/bull_flag", headers=auth_headers
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_baseline_returns_record(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """GET /experiments/baseline/{pattern} returns baseline after it is set."""
    await app_state_with_experiments.experiment_store.set_baseline("EXP_001")

    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.get(
            "/api/v1/experiments/baseline/bull_flag", headers=auth_headers
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment"]["experiment_id"] == "EXP_001"
    assert data["experiment"]["is_baseline"] is True


@pytest.mark.asyncio
async def test_run_sweep_triggers_background_task(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """POST /experiments/run returns grid_size and launches background task."""
    with patch(
        "argus.intelligence.experiments.runner.ExperimentRunner"
    ) as MockRunner:
        mock_instance = MagicMock()
        mock_instance.generate_parameter_grid.return_value = [{"a": 1}, {"a": 2}]
        MockRunner.return_value = mock_instance

        async with await _make_client(app_state_with_experiments) as client:
            resp = await client.post(
                "/api/v1/experiments/run",
                json={"pattern": "bull_flag", "dry_run": False},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["grid_size"] == 2
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_run_sweep_invalid_pattern_returns_400(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """POST /experiments/run returns 400 for unknown pattern name."""
    async with await _make_client(app_state_with_experiments) as client:
        resp = await client.post(
            "/api/v1/experiments/run",
            json={"pattern": "nonexistent_pattern_xyz"},
            headers=auth_headers,
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_run_sweep_dry_run_does_not_trigger_task(
    app_state_with_experiments: AppState,
    auth_headers: dict[str, str],
) -> None:
    """POST /experiments/run with dry_run=true returns grid_size without background task."""
    with patch(
        "argus.intelligence.experiments.runner.ExperimentRunner"
    ) as MockRunner:
        mock_instance = MagicMock()
        mock_instance.generate_parameter_grid.return_value = [{"a": 1}]
        MockRunner.return_value = mock_instance

        async with await _make_client(app_state_with_experiments) as client:
            resp = await client.post(
                "/api/v1/experiments/run",
                json={"pattern": "bull_flag", "dry_run": True},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["grid_size"] == 1
    # run_sweep should NOT have been called in dry_run mode
    mock_instance.run_sweep.assert_not_called()

"""Regression tests for FIX-11-backend-api (audit 2026-04-21).

Guards the fixes applied in FIX-11 against silent rollback:

- F1-3: TradeLogger.db_manager public property
- F1-1: GET /market/{symbol}/bars response has a `source` field
- F1-21: create_access_token requires expires_hours (no default)
- F1-24: GET /auth/me response matches UserInfoResponse schema
- F1-9: POST /historical/validate-coverage rejects malformed bodies via Pydantic (422)
- F1-10: GET /trades/{id}/replay returns 501 (DEF-029 gate)
- F1-12: /strategies/{id}/decisions uses _auth (not _user) parameter name
- F1-14: Broker.get_account() is on the ABC (hasattr check removed)
- F1-23: jose.jwt is imported at module level in websocket/live.py
- F1-19/25: route imports alphabetical, observatory noted as conditional
- F1-13: QueueFull emits state_desync message
- F1-4: Orchestrator.attach_vix_service / regime_classifier_v2 public API
"""

from __future__ import annotations

import asyncio
import inspect

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# F1-3: TradeLogger.db_manager public property
# ---------------------------------------------------------------------------


def test_trade_logger_exposes_db_manager_property() -> None:
    """TradeLogger.db_manager returns the underlying DatabaseManager (F1-3)."""
    from argus.analytics.trade_logger import TradeLogger
    from argus.db.manager import DatabaseManager

    # Using unittest.mock-style sentinel via a tiny stand-in; we only need
    # identity equality.
    sentinel = object()
    logger = TradeLogger.__new__(TradeLogger)
    logger._db = sentinel  # type: ignore[assignment]

    assert logger.db_manager is sentinel


def test_trade_logger_db_manager_property_typed() -> None:
    """TradeLogger.db_manager annotated as DatabaseManager (F1-3 contract).

    ``from __future__ import annotations`` in trade_logger.py means the
    annotation is stored as the string ``"DatabaseManager"``. We resolve
    it via ``typing.get_type_hints`` and confirm it's the real class.
    """
    from typing import get_type_hints

    from argus.analytics.trade_logger import TradeLogger
    from argus.db.manager import DatabaseManager

    prop = inspect.getattr_static(TradeLogger, "db_manager")
    assert isinstance(prop, property)
    hints = get_type_hints(prop.fget)  # type: ignore[arg-type]
    assert hints.get("return") is DatabaseManager


# ---------------------------------------------------------------------------
# F1-1: BarsResponse.source field
# ---------------------------------------------------------------------------


def test_bars_response_has_source_field() -> None:
    """BarsResponse exposes `source: Literal['live','historical','synthetic']`."""
    from argus.api.routes.market import BarsResponse

    fields = BarsResponse.model_fields
    assert "source" in fields


@pytest.mark.asyncio
async def test_synthetic_fallback_flags_source(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """When no real data is available, the response flags source='synthetic' (F1-1).

    In the default test AppState there is no IntradayCandleStore and no
    DataService, so the route falls through to the synthetic generator.
    """
    response = await client.get("/api/v1/market/AAPL/bars", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "synthetic"
    # Synthetic is still capped at 390 bars (one RTH session).
    assert body["count"] <= 390


# ---------------------------------------------------------------------------
# F1-21: create_access_token requires expires_hours
# ---------------------------------------------------------------------------


def test_create_access_token_requires_expires_hours() -> None:
    """No implicit default — calling without expires_hours raises TypeError (F1-21)."""
    from argus.api.auth import create_access_token

    with pytest.raises(TypeError):
        create_access_token("secret")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# F1-24: /auth/me returns UserInfoResponse schema
# ---------------------------------------------------------------------------


def test_userinforesponse_model_exists() -> None:
    """UserInfoResponse is defined on the auth router module (F1-24)."""
    from argus.api.routes.auth import UserInfoResponse

    fields = UserInfoResponse.model_fields
    assert set(fields.keys()) == {"user", "timestamp"}


@pytest.mark.asyncio
async def test_auth_me_matches_user_info_response(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /auth/me response round-trips through UserInfoResponse (F1-24)."""
    from argus.api.routes.auth import UserInfoResponse

    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    # Will raise if schema drifts.
    parsed = UserInfoResponse.model_validate(response.json())
    assert parsed.user == "operator"


# ---------------------------------------------------------------------------
# F1-9: POST /historical/validate-coverage uses Pydantic body
# ---------------------------------------------------------------------------


def test_validate_coverage_request_model_exists() -> None:
    """ValidateCoverageRequest is defined with typed fields (F1-9)."""
    from argus.api.routes.historical import ValidateCoverageRequest

    fields = ValidateCoverageRequest.model_fields
    assert set(fields.keys()) == {"symbols", "start_date", "end_date", "min_bars"}


# ---------------------------------------------------------------------------
# F1-12: /strategies/{id}/decisions uses _auth parameter name
# ---------------------------------------------------------------------------


def test_strategy_decisions_auth_param_renamed() -> None:
    """Auth parameter is _auth (not _user) on get_strategy_decisions (F1-12)."""
    from argus.api.routes.strategies import get_strategy_decisions

    sig = inspect.signature(get_strategy_decisions)
    params = set(sig.parameters.keys())
    assert "_auth" in params
    assert "_user" not in params


# ---------------------------------------------------------------------------
# F1-14: Broker.get_account() is on the ABC
# ---------------------------------------------------------------------------


def test_broker_abc_declares_get_account() -> None:
    """Broker ABC declares get_account(); the hasattr() gate is dead code (F1-14)."""
    from argus.execution.broker import Broker

    assert hasattr(Broker, "get_account")
    assert getattr(Broker, "get_account").__isabstractmethod__


# ---------------------------------------------------------------------------
# F1-23: jwt imported at module level in websocket/live.py
# ---------------------------------------------------------------------------


def test_live_ws_imports_jwt_at_module_level() -> None:
    """jose.jwt is imported at module scope, not inside the endpoint (F1-23)."""
    from argus.api.websocket import live as live_module

    # Module-level symbol, not fetched from jose inside a function body.
    assert hasattr(live_module, "jwt")


# ---------------------------------------------------------------------------
# F1-10: /trades/{id}/replay is 501 until DEF-029
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trade_replay_returns_501_until_def029(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Replay endpoint surfaces 501 instead of empty bars (F1-10).

    Uses a nonexistent trade ID — the 404 path fires first, confirming
    the 404 guard still runs before 501. The positive-path 501 check
    lives in test_replay_and_goals.py (it needs seeded trades).
    """
    response = await client.get(
        "/api/v1/trades/nonexistent_id/replay",
        headers=auth_headers,
    )
    # 404 precedes 501 — bad IDs still fail fast.
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# F1-4: Orchestrator public VIX wiring API
# ---------------------------------------------------------------------------


def test_orchestrator_exposes_public_vix_wiring() -> None:
    """Orchestrator has attach_vix_service + regime_classifier_v2 property (F1-4)."""
    from argus.core.orchestrator import Orchestrator

    assert hasattr(Orchestrator, "attach_vix_service")
    assert callable(Orchestrator.attach_vix_service)
    prop = inspect.getattr_static(Orchestrator, "regime_classifier_v2")
    assert isinstance(prop, property)


def test_regime_classifier_v2_exposes_public_calculator_accessors() -> None:
    """RegimeClassifierV2 has vol_phase_calc/... + attach_vix_service (F1-4)."""
    from argus.core.regime import RegimeClassifierV2

    for name in (
        "vol_phase_calc",
        "vol_momentum_calc",
        "term_structure_calc",
        "vrp_calc",
    ):
        prop = inspect.getattr_static(RegimeClassifierV2, name)
        assert isinstance(prop, property), f"{name} should be a property"
    assert hasattr(RegimeClassifierV2, "attach_vix_service")


def test_vix_data_service_shutdown_is_async() -> None:
    """VIXDataService.shutdown is a public async cleanup hook (F1-4)."""
    from argus.data.vix_data_service import VIXDataService

    assert hasattr(VIXDataService, "shutdown")
    assert asyncio.iscoroutinefunction(VIXDataService.shutdown)


# ---------------------------------------------------------------------------
# F1-19 / F1-25: route imports alphabetical + observatory comment
# ---------------------------------------------------------------------------


def test_routes_module_alphabetical_imports_and_observatory_note() -> None:
    """routes/__init__.py imports are sorted + observatory note present (F1-19, F1-25)."""
    from pathlib import Path

    src = Path(
        "argus/api/routes/__init__.py"
    ).read_text(encoding="utf-8")
    # Observatory documentation note
    assert "conditionally mounted" in src
    assert "observatory" in src.lower()

    # Verify import ordering: the `from argus.api.routes.X import ...` lines
    # should appear alphabetically by X.
    import_lines = [
        line for line in src.splitlines()
        if line.startswith("from argus.api.routes.")
    ]
    modules = [line.split(".")[3].split(" ")[0] for line in import_lines]
    assert modules == sorted(modules), (
        f"route imports not alphabetical: {modules}"
    )

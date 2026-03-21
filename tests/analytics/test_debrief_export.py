"""Tests for the debrief export module."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from argus.analytics.debrief_export import export_debrief_data

SESSION_DATE = "2026-03-20"


def _make_db_mock() -> MagicMock:
    """Build a DatabaseManager mock with fetch_all returning empty lists."""
    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[])
    return db


def _make_eval_store_mock() -> MagicMock:
    """Build an EvaluationEventStore mock with execute_query returning empty lists."""
    eval_store = MagicMock()
    eval_store.execute_query = AsyncMock(return_value=[])
    return eval_store


def _make_broker_mock() -> MagicMock:
    """Build a Broker mock with account and position data."""
    account = MagicMock()
    account.equity = 100_000.0
    account.buying_power = 50_000.0
    account.cash = 25_000.0

    broker = MagicMock()
    broker.get_account = AsyncMock(return_value=account)
    broker.get_positions = AsyncMock(return_value=[])
    return broker


def _make_orchestrator_mock() -> MagicMock:
    """Build an Orchestrator mock with regime and allocation state."""
    regime = MagicMock()
    regime.value = "NEUTRAL"

    orchestrator = MagicMock()
    orchestrator.current_regime = regime
    orchestrator.current_allocations = {}
    orchestrator._spy_unavailable_count = 0
    return orchestrator


@pytest.mark.asyncio
async def test_export_creates_json_file(tmp_path: Path) -> None:
    """export_debrief_data writes a JSON file with all expected top-level keys."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
    )

    assert result_path is not None
    output_file = Path(result_path)
    assert output_file.exists()

    payload = json.loads(output_file.read_text(encoding="utf-8"))

    expected_keys = {
        "session_date",
        "exported_at",
        "orchestrator_decisions",
        "evaluation_summary",
        "quality_history",
        "trades",
        "catalyst_summary",
        "account_state",
        "regime",
    }
    assert expected_keys == set(payload.keys())
    assert payload["session_date"] == SESSION_DATE


@pytest.mark.asyncio
async def test_export_handles_missing_eval_store(tmp_path: Path) -> None:
    """Passing eval_store=None produces a partial export with an error key in evaluation_summary."""
    db = _make_db_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=None,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    assert "error" in payload["evaluation_summary"]
    # All other sections should still be present
    assert "orchestrator_decisions" in payload
    assert "quality_history" in payload
    assert "trades" in payload


@pytest.mark.asyncio
async def test_export_handles_missing_catalyst_db(tmp_path: Path) -> None:
    """Providing a nonexistent catalyst_db_path produces an error key in catalyst_summary."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    nonexistent_path = str(tmp_path / "does_not_exist.db")

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=nonexistent_path,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    assert "error" in payload["catalyst_summary"]
    # File should still contain the other sections
    assert "trades" in payload
    assert "account_state" in payload


@pytest.mark.asyncio
async def test_export_handles_broker_error(tmp_path: Path) -> None:
    """A broker.get_account() exception produces an error key in account_state."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    orchestrator = _make_orchestrator_mock()

    broker = MagicMock()
    broker.get_account = AsyncMock(side_effect=Exception("connection refused"))
    broker.get_positions = AsyncMock(return_value=[])

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    assert "error" in payload["account_state"]
    assert "connection refused" in payload["account_state"]["error"]
    # Other sections unaffected
    assert "regime" in payload
    assert "trades" in payload


@pytest.mark.asyncio
async def test_export_json_serializes_datetimes(tmp_path: Path) -> None:
    """Datetime values returned by mocks serialize cleanly to JSON without TypeError."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    orchestrator = _make_orchestrator_mock()

    now = datetime.now(UTC)
    account = MagicMock()
    account.equity = 99_000.0
    account.buying_power = 49_000.0
    account.cash = 20_000.0

    position = MagicMock()
    position.symbol = "AAPL"
    position.shares = 10
    position.entry_price = 175.50
    position.current_price = 175.50
    position.unrealized_pnl = 0.0

    broker = MagicMock()
    broker.get_account = AsyncMock(return_value=account)
    broker.get_positions = AsyncMock(return_value=[position])

    # Inject a datetime value into the fetch_all return for orchestrator_decisions
    db.fetch_all = AsyncMock(
        side_effect=[
            # orchestrator_decisions: row with a datetime in created_at
            [("ALLOCATE", "orb_breakout", "{}", "regime NEUTRAL", now)],
            # quality_history: empty
            [],
            # trades PRAGMA: empty col info
            [],
            # trades rows: empty
            [],
        ]
    )

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
    )

    assert result_path is not None
    # json.loads would raise if serialization failed; reaching here confirms success
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    assert payload["session_date"] == SESSION_DATE

    decisions = payload["orchestrator_decisions"]
    assert isinstance(decisions, list)
    assert len(decisions) == 1
    # Datetime must have been serialized to a string by json.dumps(default=str)
    assert isinstance(decisions[0]["created_at"], str)

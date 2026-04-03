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
        "quality_distribution",
        "trades",
        "catalyst_summary",
        "account_state",
        "regime",
        "counterfactual_summary",
        "experiment_summary",
        "safety_summary",
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


@pytest.mark.asyncio
async def test_export_safety_summary_with_order_manager(tmp_path: Path) -> None:
    """safety_summary reads margin circuit state from the order_manager via getattr."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    order_manager = MagicMock()
    order_manager._margin_circuit_open = True
    order_manager._margin_rejection_count = 12
    order_manager._config = MagicMock()
    order_manager._config.margin_rejection_threshold = 10
    order_manager._config.eod_flatten_timeout_seconds = 30

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
        order_manager=order_manager,
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    safety = payload["safety_summary"]
    assert safety["margin_circuit_breaker"]["triggered"] is True
    assert safety["margin_circuit_breaker"]["rejection_count"] == 12
    assert safety["margin_circuit_breaker"]["rejection_threshold"] == 10
    assert safety["eod_flatten"]["timeout_seconds"] == 30
    # Non-tracked fields must be null
    assert safety["margin_circuit_breaker"]["open_time"] is None
    assert safety["eod_flatten"]["pass1_filled"] is None
    assert safety["signal_cutoff"]["signals_skipped"] is None


@pytest.mark.asyncio
async def test_export_safety_summary_without_order_manager(tmp_path: Path) -> None:
    """safety_summary returns defaults when order_manager is None."""
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
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    safety = payload["safety_summary"]
    assert safety["margin_circuit_breaker"]["triggered"] is False
    assert safety["margin_circuit_breaker"]["rejection_count"] == 0


@pytest.mark.asyncio
async def test_export_counterfactual_summary_missing_db(tmp_path: Path) -> None:

    """Nonexistent counterfactual_db_path produces an error key in counterfactual_summary."""
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
        counterfactual_db_path=str(tmp_path / "no_cf.db"),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    assert "error" in payload["counterfactual_summary"]
    # Other sections unaffected
    assert "safety_summary" in payload
    assert "experiment_summary" in payload


@pytest.mark.asyncio
async def test_export_experiment_summary_missing_db(tmp_path: Path) -> None:
    """Nonexistent experiment_db_path produces an error key in experiment_summary."""
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
        experiment_db_path=str(tmp_path / "no_exp.db"),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    assert "error" in payload["experiment_summary"]
    assert "counterfactual_summary" in payload


@pytest.mark.asyncio
async def test_export_counterfactual_summary_with_live_db(tmp_path: Path) -> None:
    """counterfactual_summary returns structured keys when a valid DB exists."""
    import aiosqlite

    db_path = tmp_path / "counterfactual.db"
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(
            """CREATE TABLE counterfactual_positions (
                position_id TEXT PRIMARY KEY,
                symbol TEXT, strategy_id TEXT,
                entry_price REAL, stop_price REAL, target_price REAL,
                time_stop_seconds INTEGER, rejection_stage TEXT, rejection_reason TEXT,
                quality_score REAL, quality_grade TEXT, regime_vector_snapshot TEXT,
                signal_metadata TEXT, opened_at TEXT, closed_at TEXT,
                exit_price REAL, exit_reason TEXT, theoretical_pnl REAL,
                theoretical_r_multiple REAL, duration_seconds REAL,
                max_adverse_excursion REAL, max_favorable_excursion REAL,
                bars_monitored INTEGER, variant_id TEXT
            )"""
        )
        await conn.execute(
            "INSERT INTO counterfactual_positions VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "pos1", "AAPL", "strat_abcd",
                150.0, 148.0, 154.0,
                300, "shadow", "shadow_mode",
                65.0, "B+", None, "{}", f"{SESSION_DATE}T10:00:00",
                f"{SESSION_DATE}T11:00:00", 154.0, "target_hit",
                4.0, 2.0, 3600.0, 0.5, 4.0, 10, None,
            ),
        )
        await conn.commit()

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
        counterfactual_db_path=str(db_path),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    cf = payload["counterfactual_summary"]
    assert cf["total_positions_opened"] == 1
    assert cf["total_positions_closed"] == 1
    assert "strat_abcd" in cf["by_strategy"]
    assert cf["by_strategy"]["strat_abcd"]["wins"] == 1
    assert cf["by_rejection_stage"]["shadow"] == 1
    assert cf["by_exit_reason"]["target_hit"] == 1


@pytest.mark.asyncio
async def test_export_experiment_summary_with_data(tmp_path: Path) -> None:
    """experiment_summary returns structured keys when a valid experiments.db exists."""
    import aiosqlite

    db_path = tmp_path / "experiments.db"
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(
            """CREATE TABLE variants (
                variant_id TEXT PRIMARY KEY,
                base_pattern TEXT NOT NULL,
                parameter_fingerprint TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                mode TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        await conn.execute(
            """CREATE TABLE experiments (
                experiment_id TEXT PRIMARY KEY,
                pattern_name TEXT NOT NULL,
                parameter_fingerprint TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                status TEXT NOT NULL,
                backtest_result_json TEXT,
                shadow_trades INTEGER NOT NULL DEFAULT 0,
                shadow_expectancy REAL,
                is_baseline INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        await conn.execute(
            """CREATE TABLE promotion_events (
                event_id TEXT PRIMARY KEY,
                variant_id TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_mode TEXT NOT NULL,
                new_mode TEXT NOT NULL,
                reason TEXT NOT NULL,
                comparison_verdict_json TEXT,
                shadow_trades INTEGER NOT NULL DEFAULT 0,
                shadow_expectancy REAL,
                timestamp TEXT NOT NULL
            )"""
        )
        await conn.execute(
            "INSERT INTO variants VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "var-001", "bull_flag", "abc123", "{}",
                "shadow", "sweep", f"{SESSION_DATE}T09:00:00",
            ),
        )
        await conn.execute(
            "INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "var-001", "bull_flag", "abc123", "{}", "shadow",
                None, 5, 0.35, 0,
                f"{SESSION_DATE}T09:00:00", f"{SESSION_DATE}T09:00:00",
            ),
        )
        await conn.execute(
            "INSERT INTO promotion_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-001", "var-001", "promote", "shadow", "paper",
                "good expectancy", None, 5, 0.35, f"{SESSION_DATE}T15:00:00",
            ),
        )
        await conn.commit()

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
        experiment_db_path=str(db_path),
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    exp = payload["experiment_summary"]
    assert exp["variants_spawned"] == 1
    assert "bull_flag" in exp["variants_by_pattern"]
    assert "var-001" in exp["variants_by_pattern"]["bull_flag"]
    assert exp["promotion_events_today"] == 1
    assert "var-001" in exp["variant_shadow_trades"]
    assert exp["variant_shadow_trades"]["var-001"]["trades"] == 5
    assert exp["variant_shadow_trades"]["var-001"]["pattern_name"] == "bull_flag"


@pytest.mark.asyncio
async def test_export_quality_distribution(tmp_path: Path) -> None:
    """quality_distribution returns grade_counts and dimension_averages from quality_history."""
    from argus.analytics.debrief_export import _export_quality_distribution

    db = MagicMock()
    db.fetch_all = AsyncMock(
        side_effect=[
            # grade_counts: (grade, count)
            [("A+", 2), ("B+", 5), ("B", 3)],
            # grade_outcomes: (grade, signals, wins, avg_r) WHERE outcome_trade_id IS NOT NULL
            [("A+", 2, 2, 1.5), ("B+", 3, 2, 0.8)],
            # dimension_averages: single row of 6 floats
            [(70.0, 50.0, 60.0, 50.0, 55.0, 62.5)],
        ]
    )

    result = await _export_quality_distribution(db, SESSION_DATE)

    assert result["grade_counts"] == {"A+": 2, "B+": 5, "B": 3}
    assert "A+" in result["grade_outcomes"]
    assert result["grade_outcomes"]["A+"]["win_rate"] == 1.0
    assert result["grade_outcomes"]["B+"]["win_rate"] == pytest.approx(0.667, abs=0.001)
    assert result["dimension_averages"] is not None
    assert result["dimension_averages"]["pattern_strength"] == 70.0
    assert result["dimension_averages"]["composite_score"] == 62.5


@pytest.mark.asyncio
async def test_export_backward_compatible(tmp_path: Path) -> None:
    """export_debrief_data works with default (None) values for new Sprint 32.9+ params."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    # Call without any of the new Sprint 32.9+ keyword parameters
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

    # All top-level keys must be present
    assert "counterfactual_summary" in payload
    assert "experiment_summary" in payload
    assert "safety_summary" in payload
    assert "quality_distribution" in payload

    # None paths degrade gracefully to error dicts
    assert "error" in payload["counterfactual_summary"]
    assert "error" in payload["experiment_summary"]

    # safety_summary with None order_manager returns zero-value defaults, not an error
    safety = payload["safety_summary"]
    assert "margin_circuit_breaker" in safety
    assert safety["margin_circuit_breaker"]["triggered"] is False
    assert safety["margin_circuit_breaker"]["rejection_count"] == 0


# ---------------------------------------------------------------------------
# DEF-144: safety_summary reads new tracking attributes (Sprint 31A S1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_safety_summary_reads_new_tracking_attributes(tmp_path: Path) -> None:
    """safety_summary returns non-null values when OrderManager tracking attrs are set."""
    from datetime import UTC, datetime as dt

    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    open_ts = dt(2026, 4, 3, 14, 30, 0, tzinfo=UTC)
    reset_ts = dt(2026, 4, 3, 14, 45, 0, tzinfo=UTC)

    order_manager = MagicMock()
    order_manager._margin_circuit_open = False
    order_manager._margin_rejection_count = 5
    order_manager._config = MagicMock()
    order_manager._config.margin_rejection_threshold = 10
    order_manager._config.eod_flatten_timeout_seconds = 30
    # New tracking attributes — actual typed values (not MagicMock)
    order_manager.margin_circuit_breaker_open_time = open_ts
    order_manager.margin_circuit_breaker_reset_time = reset_ts
    order_manager.margin_entries_blocked_count = 3
    order_manager.eod_flatten_pass1_count = 8
    order_manager.eod_flatten_pass2_count = 1
    order_manager.signal_cutoff_skipped_count = 4

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
        order_manager=order_manager,
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    safety = payload["safety_summary"]
    mcb = safety["margin_circuit_breaker"]
    assert mcb["open_time"] == open_ts.isoformat()
    assert mcb["reset_time"] == reset_ts.isoformat()
    assert mcb["entries_blocked"] == 3

    eod = safety["eod_flatten"]
    assert eod["pass1_filled"] == 8
    assert eod["pass2_orphans_found"] == 1

    sc = safety["signal_cutoff"]
    assert sc["signals_skipped"] == 4


@pytest.mark.asyncio
async def test_safety_summary_null_tracking_attrs_when_no_events(tmp_path: Path) -> None:
    """safety_summary returns None for datetime attrs and 0 for counters when no events occurred."""
    db = _make_db_mock()
    eval_store = _make_eval_store_mock()
    broker = _make_broker_mock()
    orchestrator = _make_orchestrator_mock()

    # Simulate an OrderManager with zero-event defaults
    order_manager = MagicMock()
    order_manager._margin_circuit_open = False
    order_manager._margin_rejection_count = 0
    order_manager._config = MagicMock()
    order_manager._config.margin_rejection_threshold = 10
    order_manager._config.eod_flatten_timeout_seconds = 30
    # Tracking attrs at defaults — None datetimes, zero counters
    order_manager.margin_circuit_breaker_open_time = None
    order_manager.margin_circuit_breaker_reset_time = None
    order_manager.margin_entries_blocked_count = 0
    order_manager.eod_flatten_pass1_count = 0
    order_manager.eod_flatten_pass2_count = 0
    order_manager.signal_cutoff_skipped_count = 0

    result_path = await export_debrief_data(
        session_date=SESSION_DATE,
        db=db,
        eval_store=eval_store,
        catalyst_db_path=None,
        broker=broker,
        orchestrator=orchestrator,
        output_dir=str(tmp_path),
        order_manager=order_manager,
    )

    assert result_path is not None
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))

    safety = payload["safety_summary"]
    # open_time / reset_time must be None (no events happened)
    assert safety["margin_circuit_breaker"]["open_time"] is None
    assert safety["margin_circuit_breaker"]["reset_time"] is None
    # Integer zero counts should come through as 0
    assert safety["margin_circuit_breaker"]["entries_blocked"] == 0
    assert safety["eod_flatten"]["pass1_filled"] == 0
    assert safety["eod_flatten"]["pass2_orphans_found"] == 0
    assert safety["signal_cutoff"]["signals_skipped"] == 0

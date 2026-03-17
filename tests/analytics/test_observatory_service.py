"""Tests for ObservatoryService analytics layer.

Sprint 25, Session 1.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import aiosqlite
import pytest

from argus.analytics.observatory_service import (
    ObservatoryService,
    _extract_conditions,
    _safe_json_loads,
)

_ET = ZoneInfo("America/New_York")

# Fixed test date
TEST_DATE = "2026-03-17"

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS evaluation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trading_date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    result TEXT NOT NULL,
    reason TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
)
"""


class FakeStore:
    """Minimal stand-in for EvaluationEventStore with a real SQLite connection."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @property
    def is_connected(self) -> bool:
        """Return True if the database connection is open."""
        return self._conn is not None

    async def execute_query(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> list[aiosqlite.Row]:
        """Execute a read-only SQL query and return all rows."""
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchall()


async def _make_store(tmp_path: Path) -> tuple[FakeStore, aiosqlite.Connection]:
    """Create a FakeStore backed by a temporary SQLite database."""
    db_path = str(tmp_path / "test_observatory.db")
    conn = await aiosqlite.connect(db_path)
    await conn.execute(_CREATE_TABLE)
    await conn.commit()
    return FakeStore(conn), conn


async def _insert_event(
    conn: aiosqlite.Connection,
    *,
    trading_date: str = TEST_DATE,
    timestamp: str = "2026-03-17T10:30:00",
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
    event_type: str = "ENTRY_EVALUATION",
    result: str = "FAIL",
    reason: str = "condition not met",
    metadata: dict | None = None,
) -> None:
    """Insert a single evaluation event into the test database."""
    meta_json = json.dumps(metadata or {})
    await conn.execute(
        "INSERT INTO evaluation_events "
        "(trading_date, timestamp, symbol, strategy_id, event_type, "
        "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (trading_date, timestamp, symbol, strategy_id, event_type,
         result, reason, meta_json),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# Pipeline stages tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_stages_returns_all_tiers(tmp_path: Path) -> None:
    """Verify all 7 tier keys are present in the response."""
    store, conn = await _make_store(tmp_path)
    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    result = await svc.get_pipeline_stages(date=TEST_DATE)

    expected_keys = {
        "universe", "viable", "routed", "evaluating",
        "near_trigger", "signal", "traded", "date",
    }
    assert expected_keys == set(result.keys())
    await conn.close()


@pytest.mark.asyncio
async def test_pipeline_stages_counts_accurate(tmp_path: Path) -> None:
    """With seeded data, verify counts match."""
    store, conn = await _make_store(tmp_path)

    # 3 distinct symbols with ENTRY_EVALUATION events
    await _insert_event(conn, symbol="AAPL", event_type="ENTRY_EVALUATION")
    await _insert_event(conn, symbol="NVDA", event_type="ENTRY_EVALUATION")
    await _insert_event(conn, symbol="TSLA", event_type="ENTRY_EVALUATION")

    # 1 signal generated
    await _insert_event(conn, symbol="AAPL", event_type="SIGNAL_GENERATED",
                        result="PASS")

    # 1 quality scored (traded proxy)
    await _insert_event(conn, symbol="AAPL", event_type="QUALITY_SCORED",
                        result="INFO")

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    result = await svc.get_pipeline_stages(date=TEST_DATE)

    assert result["evaluating"] == 3
    assert result["signal"] == 1
    assert result["traded"] == 1
    await conn.close()


@pytest.mark.asyncio
async def test_pipeline_stages_with_date_filter(tmp_path: Path) -> None:
    """Historical date returns different counts than today."""
    store, conn = await _make_store(tmp_path)

    # Events on two different dates
    await _insert_event(conn, trading_date="2026-03-16", symbol="AAPL",
                        timestamp="2026-03-16T10:00:00")
    await _insert_event(conn, trading_date="2026-03-17", symbol="NVDA",
                        timestamp="2026-03-17T10:00:00")
    await _insert_event(conn, trading_date="2026-03-17", symbol="TSLA",
                        timestamp="2026-03-17T10:00:00")

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )

    result_16 = await svc.get_pipeline_stages(date="2026-03-16")
    result_17 = await svc.get_pipeline_stages(date="2026-03-17")

    assert result_16["evaluating"] == 1
    assert result_17["evaluating"] == 2
    await conn.close()


# ---------------------------------------------------------------------------
# Closest misses tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_closest_misses_sorted_descending(tmp_path: Path) -> None:
    """Verify results are sorted by conditions_passed descending."""
    store, conn = await _make_store(tmp_path)

    # AAPL passes 2/3 conditions
    await _insert_event(
        conn, symbol="AAPL", strategy_id="orb_breakout",
        timestamp="2026-03-17T10:30:00",
        metadata={"conditions": [
            {"name": "volume", "passed": True},
            {"name": "range", "passed": True},
            {"name": "trend", "passed": False},
        ]},
    )

    # NVDA passes 1/3 conditions
    await _insert_event(
        conn, symbol="NVDA", strategy_id="orb_breakout",
        timestamp="2026-03-17T10:30:00",
        metadata={"conditions": [
            {"name": "volume", "passed": True},
            {"name": "range", "passed": False},
            {"name": "trend", "passed": False},
        ]},
    )

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    misses = await svc.get_closest_misses(tier="evaluating", date=TEST_DATE)

    assert len(misses) == 2
    assert misses[0]["symbol"] == "AAPL"
    assert misses[0]["conditions_passed"] == 2
    assert misses[1]["symbol"] == "NVDA"
    assert misses[1]["conditions_passed"] == 1
    await conn.close()


@pytest.mark.asyncio
async def test_closest_misses_limit_respected(tmp_path: Path) -> None:
    """Verify limit parameter caps the result count."""
    store, conn = await _make_store(tmp_path)

    for i, sym in enumerate(["AAPL", "NVDA", "TSLA", "MSFT", "GOOG"]):
        await _insert_event(
            conn, symbol=sym, strategy_id="orb_breakout",
            timestamp=f"2026-03-17T10:{30+i}:00",
            metadata={"conditions": [{"name": "vol", "passed": True}]},
        )

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    misses = await svc.get_closest_misses(
        tier="evaluating", limit=3, date=TEST_DATE,
    )
    assert len(misses) == 3
    await conn.close()


@pytest.mark.asyncio
async def test_closest_misses_condition_detail_present(tmp_path: Path) -> None:
    """Each entry includes a conditions_detail array with name/passed fields."""
    store, conn = await _make_store(tmp_path)

    await _insert_event(
        conn, symbol="AAPL",
        metadata={"conditions": [
            {"name": "volume", "passed": True, "actual_value": 1.5,
             "required_value": 1.0},
            {"name": "range", "passed": False, "actual_value": 0.8,
             "required_value": 1.2},
        ]},
    )

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    misses = await svc.get_closest_misses(tier="evaluating", date=TEST_DATE)

    assert len(misses) == 1
    detail = misses[0]["conditions_detail"]
    assert len(detail) == 2
    assert detail[0]["name"] == "volume"
    assert detail[0]["passed"] is True
    assert detail[0]["actual_value"] == 1.5
    await conn.close()


@pytest.mark.asyncio
async def test_closest_misses_empty_tier(tmp_path: Path) -> None:
    """Returns empty list when no events exist, not an error."""
    store, conn = await _make_store(tmp_path)

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    misses = await svc.get_closest_misses(tier="evaluating", date=TEST_DATE)
    assert misses == []
    await conn.close()


# ---------------------------------------------------------------------------
# Symbol journey tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_symbol_journey_chronological(tmp_path: Path) -> None:
    """Events are sorted by timestamp ascending."""
    store, conn = await _make_store(tmp_path)

    await _insert_event(conn, symbol="AAPL", timestamp="2026-03-17T10:35:00",
                        event_type="ENTRY_EVALUATION")
    await _insert_event(conn, symbol="AAPL", timestamp="2026-03-17T10:30:00",
                        event_type="TIME_WINDOW_CHECK")
    await _insert_event(conn, symbol="AAPL", timestamp="2026-03-17T10:40:00",
                        event_type="SIGNAL_GENERATED", result="PASS")

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    journey = await svc.get_symbol_journey(symbol="AAPL", date=TEST_DATE)

    assert len(journey) == 3
    assert journey[0]["event_type"] == "TIME_WINDOW_CHECK"
    assert journey[1]["event_type"] == "ENTRY_EVALUATION"
    assert journey[2]["event_type"] == "SIGNAL_GENERATED"
    await conn.close()


@pytest.mark.asyncio
async def test_symbol_journey_cross_strategy(tmp_path: Path) -> None:
    """Events from multiple strategies are included for the same symbol."""
    store, conn = await _make_store(tmp_path)

    await _insert_event(conn, symbol="AAPL", strategy_id="orb_breakout",
                        timestamp="2026-03-17T10:30:00")
    await _insert_event(conn, symbol="AAPL", strategy_id="vwap_reclaim",
                        timestamp="2026-03-17T11:00:00")

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    journey = await svc.get_symbol_journey(symbol="AAPL", date=TEST_DATE)

    strategies_seen = {e["strategy"] for e in journey}
    assert "orb_breakout" in strategies_seen
    assert "vwap_reclaim" in strategies_seen
    await conn.close()


@pytest.mark.asyncio
async def test_symbol_journey_unknown_symbol(tmp_path: Path) -> None:
    """Returns empty list for unknown symbol, not a 404."""
    store, conn = await _make_store(tmp_path)

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    journey = await svc.get_symbol_journey(symbol="DOESNOTEXIST", date=TEST_DATE)
    assert journey == []
    await conn.close()


# ---------------------------------------------------------------------------
# Session summary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_summary_aggregation(tmp_path: Path) -> None:
    """Totals match seeded data."""
    store, conn = await _make_store(tmp_path)

    # 3 entry evaluations
    for sym in ["AAPL", "NVDA", "TSLA"]:
        await _insert_event(conn, symbol=sym, event_type="ENTRY_EVALUATION")

    # 2 signals
    await _insert_event(conn, symbol="AAPL", event_type="SIGNAL_GENERATED",
                        result="PASS", timestamp="2026-03-17T10:31:00")
    await _insert_event(conn, symbol="NVDA", event_type="SIGNAL_GENERATED",
                        result="PASS", timestamp="2026-03-17T10:32:00")

    # 1 trade
    await _insert_event(conn, symbol="AAPL", event_type="QUALITY_SCORED",
                        result="INFO", timestamp="2026-03-17T10:33:00")

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    summary = await svc.get_session_summary(date=TEST_DATE)

    assert summary["total_evaluations"] == 3
    assert summary["total_signals"] == 2
    assert summary["total_trades"] == 1
    assert summary["symbols_evaluated"] == 3
    await conn.close()


@pytest.mark.asyncio
async def test_session_summary_top_blockers(tmp_path: Path) -> None:
    """Top 5 rejection reasons with percentages."""
    store, conn = await _make_store(tmp_path)

    # 3 evaluations with volume_check failing in 2, range_check in 1
    await _insert_event(
        conn, symbol="AAPL",
        metadata={"conditions": [
            {"name": "volume_check", "passed": False},
            {"name": "range_check", "passed": True},
        ]},
    )
    await _insert_event(
        conn, symbol="NVDA", timestamp="2026-03-17T10:31:00",
        metadata={"conditions": [
            {"name": "volume_check", "passed": False},
            {"name": "range_check", "passed": False},
        ]},
    )

    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    summary = await svc.get_session_summary(date=TEST_DATE)
    blockers = summary["top_blockers"]

    assert len(blockers) >= 1
    # volume_check should be the top blocker (2 rejections)
    assert blockers[0]["condition_name"] == "volume_check"
    assert blockers[0]["rejection_count"] == 2
    await conn.close()


# ---------------------------------------------------------------------------
# Config validation test
# ---------------------------------------------------------------------------


def test_observatory_config_validation() -> None:
    """Pydantic model recognizes all YAML keys."""
    from argus.analytics.config import ObservatoryConfig

    expected_fields = {
        "enabled", "ws_update_interval_ms", "timeline_bucket_seconds",
        "matrix_max_rows", "debrief_retention_days",
    }
    assert expected_fields == set(ObservatoryConfig.model_fields.keys())

    # Verify default values
    config = ObservatoryConfig()
    assert config.enabled is True
    assert config.ws_update_interval_ms == 1000
    assert config.timeline_bucket_seconds == 60
    assert config.matrix_max_rows == 100
    assert config.debrief_retention_days == 7


def test_observatory_config_from_yaml() -> None:
    """Config loads from YAML without silent key drops."""
    import yaml
    from argus.analytics.config import ObservatoryConfig

    yaml_snippet = """
    enabled: true
    ws_update_interval_ms: 1000
    timeline_bucket_seconds: 60
    matrix_max_rows: 100
    debrief_retention_days: 7
    """
    data = yaml.safe_load(yaml_snippet)
    config = ObservatoryConfig(**data)

    assert config.enabled is True
    assert config.ws_update_interval_ms == 1000


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_safe_json_loads_valid() -> None:
    """Valid JSON parses correctly."""
    assert _safe_json_loads('{"a": 1}') == {"a": 1}


def test_safe_json_loads_invalid() -> None:
    """Invalid JSON returns empty dict."""
    assert _safe_json_loads("not json") == {}
    assert _safe_json_loads(None) == {}
    assert _safe_json_loads("") == {}


def test_extract_conditions_format_conditions_array() -> None:
    """Conditions array format is parsed correctly."""
    metadata = {
        "conditions": [
            {"name": "vol", "passed": True, "actual_value": 1.5},
            {"name": "range", "passed": False, "required_value": 1.0},
        ],
    }
    result = _extract_conditions(metadata)
    assert len(result) == 2
    assert result[0]["name"] == "vol"
    assert result[0]["passed"] is True


def test_extract_conditions_format_checks_dict() -> None:
    """Checks dict format is parsed correctly."""
    metadata = {"checks": {"volume_check": True, "range_check": False}}
    result = _extract_conditions(metadata)
    assert len(result) == 2
    names = {c["name"] for c in result}
    assert "volume_check" in names
    assert "range_check" in names


def test_extract_conditions_empty_metadata() -> None:
    """Empty metadata returns empty list."""
    assert _extract_conditions({}) == []


# ---------------------------------------------------------------------------
# No-store graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_stages_no_store() -> None:
    """Service works gracefully with no telemetry store."""
    svc = ObservatoryService(
        telemetry_store=None,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    result = await svc.get_pipeline_stages(date=TEST_DATE)
    assert result["evaluating"] == 0
    assert result["signal"] == 0


@pytest.mark.asyncio
async def test_session_summary_no_store() -> None:
    """Session summary returns zeroes with no store."""
    svc = ObservatoryService(
        telemetry_store=None,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )
    result = await svc.get_session_summary(date=TEST_DATE)
    assert result["total_evaluations"] == 0
    assert result["top_blockers"] == []
    assert result["closest_miss"] is None

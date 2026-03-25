"""Tests for CounterfactualStore persistence and CounterfactualConfig.

Covers: table creation, write_open, write_close, query by date/strategy/stage,
retention enforcement, config YAML↔Pydantic validation, SystemConfig wiring.

Sprint 27.7, Session 2.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from argus.core.config import SystemConfig
from argus.core.fill_model import FillExitReason
from argus.intelligence.config import CounterfactualConfig
from argus.intelligence.counterfactual import CounterfactualPosition, RejectionStage
from argus.intelligence.counterfactual_store import CounterfactualStore

_ET = ZoneInfo("America/New_York")


def _make_position(
    position_id: str = "pos_001",
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
    opened_at: datetime | None = None,
    closed: bool = False,
) -> CounterfactualPosition:
    """Build a CounterfactualPosition for testing."""
    now = opened_at or datetime.now(_ET)
    return CounterfactualPosition(
        position_id=position_id,
        symbol=symbol,
        strategy_id=strategy_id,
        entry_price=100.0,
        stop_price=95.0,
        target_price=110.0,
        time_stop_seconds=1800,
        rejection_stage=RejectionStage.QUALITY_FILTER,
        rejection_reason="Grade below minimum",
        quality_score=42.0,
        quality_grade="B-",
        regime_vector_snapshot={"volatility": "normal"},
        signal_metadata={"pattern_strength": 0.7},
        opened_at=now,
        closed_at=now + timedelta(minutes=15) if closed else None,
        exit_price=108.0 if closed else None,
        exit_reason=FillExitReason.TARGET_HIT if closed else None,
        theoretical_pnl=8.0 if closed else None,
        theoretical_r_multiple=1.6 if closed else None,
        duration_seconds=900.0 if closed else None,
        max_adverse_excursion=2.0,
        max_favorable_excursion=9.0,
        bars_monitored=15 if closed else 0,
    )


@pytest.fixture
async def store(tmp_path: Path) -> CounterfactualStore:
    """Create an initialized CounterfactualStore in a temp directory."""
    db_path = str(tmp_path / "counterfactual.db")
    s = CounterfactualStore(db_path=db_path)
    await s.initialize()
    yield s  # type: ignore[misc]
    await s.close()


# --- 1. initialize creates table ---


@pytest.mark.asyncio
async def test_initialize_creates_table_and_indexes(tmp_path: Path) -> None:
    """initialize() creates counterfactual_positions table and indexes."""
    db_path = str(tmp_path / "cf.db")
    s = CounterfactualStore(db_path=db_path)
    await s.initialize()

    assert s._conn is not None
    # Verify table exists
    cursor = await s._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='counterfactual_positions'"
    )
    row = await cursor.fetchone()
    assert row is not None

    # Verify indexes
    cursor = await s._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_cf_%'"
    )
    indexes = {r["name"] for r in await cursor.fetchall()}
    assert indexes == {
        "idx_cf_opened_at",
        "idx_cf_strategy",
        "idx_cf_stage",
        "idx_cf_symbol",
    }

    await s.close()


# --- 2. write_open persists ---


@pytest.mark.asyncio
async def test_write_open_persists_position(store: CounterfactualStore) -> None:
    """write_open() persists a position with exit fields NULL."""
    pos = _make_position()
    await store.write_open(pos)

    rows = await store.query()
    assert len(rows) == 1
    row = rows[0]
    assert row["position_id"] == "pos_001"
    assert row["symbol"] == "AAPL"
    assert row["strategy_id"] == "orb_breakout"
    assert row["entry_price"] == 100.0
    assert row["rejection_stage"] == "quality_filter"
    assert row["closed_at"] is None
    assert row["exit_price"] is None
    assert row["exit_reason"] is None
    assert row["theoretical_pnl"] is None


# --- 3. write_close updates ---


@pytest.mark.asyncio
async def test_write_close_updates_exit_fields(store: CounterfactualStore) -> None:
    """write_close() updates exit fields on a previously opened position."""
    open_pos = _make_position()
    await store.write_open(open_pos)

    closed_pos = _make_position(closed=True)
    await store.write_close(closed_pos)

    rows = await store.query()
    assert len(rows) == 1
    row = rows[0]
    assert row["closed_at"] is not None
    assert row["exit_price"] == 108.0
    assert row["exit_reason"] == "target_hit"
    assert row["theoretical_pnl"] == 8.0
    assert row["theoretical_r_multiple"] == 1.6
    assert row["duration_seconds"] == 900.0
    assert row["bars_monitored"] == 15


# --- 4. query by date range ---


@pytest.mark.asyncio
async def test_query_by_date_range(store: CounterfactualStore) -> None:
    """query() filters by start_date and end_date on opened_at."""
    base = datetime(2026, 3, 25, 10, 0, tzinfo=_ET)

    pos_old = _make_position(position_id="old", opened_at=base - timedelta(days=5))
    pos_mid = _make_position(position_id="mid", opened_at=base)
    pos_new = _make_position(position_id="new", opened_at=base + timedelta(days=5))

    await store.write_open(pos_old)
    await store.write_open(pos_mid)
    await store.write_open(pos_new)

    # Query for mid date only
    results = await store.query(
        start_date=(base - timedelta(hours=1)).isoformat(),
        end_date=(base + timedelta(hours=1)).isoformat(),
    )
    assert len(results) == 1
    assert results[0]["position_id"] == "mid"


# --- 5. query by strategy ---


@pytest.mark.asyncio
async def test_query_by_strategy(store: CounterfactualStore) -> None:
    """query() filters by strategy_id."""
    await store.write_open(_make_position(position_id="p1", strategy_id="orb_breakout"))
    await store.write_open(_make_position(position_id="p2", strategy_id="vwap_reclaim"))

    results = await store.query(strategy_id="vwap_reclaim")
    assert len(results) == 1
    assert results[0]["strategy_id"] == "vwap_reclaim"


# --- 6. query by rejection_stage ---


@pytest.mark.asyncio
async def test_query_by_rejection_stage(store: CounterfactualStore) -> None:
    """query() filters by rejection_stage."""
    pos_qf = _make_position(position_id="qf")
    pos_rm = CounterfactualPosition(
        position_id="rm",
        symbol="TSLA",
        strategy_id="orb_breakout",
        entry_price=200.0,
        stop_price=190.0,
        target_price=220.0,
        time_stop_seconds=None,
        rejection_stage=RejectionStage.RISK_MANAGER,
        rejection_reason="Daily loss limit",
        quality_score=None,
        quality_grade=None,
        regime_vector_snapshot=None,
        signal_metadata={},
        opened_at=datetime.now(_ET),
        closed_at=None,
        exit_price=None,
        exit_reason=None,
        theoretical_pnl=None,
        theoretical_r_multiple=None,
        duration_seconds=None,
        max_adverse_excursion=0.0,
        max_favorable_excursion=0.0,
        bars_monitored=0,
    )

    await store.write_open(pos_qf)
    await store.write_open(pos_rm)

    results = await store.query(rejection_stage="risk_manager")
    assert len(results) == 1
    assert results[0]["position_id"] == "rm"


# --- 7. retention enforcement ---


@pytest.mark.asyncio
async def test_enforce_retention_deletes_old_records(store: CounterfactualStore) -> None:
    """enforce_retention() deletes old records, keeps recent ones."""
    old_time = datetime.now(_ET) - timedelta(days=100)
    recent_time = datetime.now(_ET) - timedelta(days=10)

    await store.write_open(_make_position(position_id="old", opened_at=old_time))
    await store.write_open(_make_position(position_id="recent", opened_at=recent_time))

    assert await store.count() == 2

    await store.enforce_retention(retention_days=90)

    assert await store.count() == 1
    rows = await store.query()
    assert rows[0]["position_id"] == "recent"


# --- 8. config: YAML → Pydantic validation ---


def test_config_yaml_keys_match_pydantic_fields() -> None:
    """All YAML keys under counterfactual match CounterfactualConfig fields."""
    yaml_path = Path("config/counterfactual.yaml")
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    yaml_keys = set(raw["counterfactual"].keys())
    model_fields = set(CounterfactualConfig.model_fields.keys())

    # No YAML keys absent from model
    missing = yaml_keys - model_fields
    assert not missing, f"YAML keys not in CounterfactualConfig: {missing}"

    # Verify exact match
    assert yaml_keys == model_fields


# --- 9. config: CounterfactualConfig on SystemConfig ---


def test_system_config_has_counterfactual_with_defaults() -> None:
    """SystemConfig() has counterfactual field with correct defaults."""
    config = SystemConfig()
    assert hasattr(config, "counterfactual")
    assert isinstance(config.counterfactual, CounterfactualConfig)
    assert config.counterfactual.enabled is True
    assert config.counterfactual.retention_days == 90
    assert config.counterfactual.no_data_timeout_seconds == 300
    assert config.counterfactual.eod_close_time == "16:00"


# --- 10. config: enabled=false ---


def test_counterfactual_config_enabled_false() -> None:
    """CounterfactualConfig(enabled=False) correctly disables."""
    config = CounterfactualConfig(enabled=False)
    assert config.enabled is False
    # Other defaults remain
    assert config.retention_days == 90
    assert config.no_data_timeout_seconds == 300


# --- 11. get_closed_positions convenience method ---


@pytest.mark.asyncio
async def test_get_closed_positions_returns_only_closed(
    store: CounterfactualStore,
) -> None:
    """get_closed_positions() only returns positions with closed_at set."""
    now = datetime.now(_ET)
    open_pos = _make_position(position_id="open", opened_at=now)
    closed_pos = _make_position(position_id="closed", opened_at=now, closed=True)

    await store.write_open(open_pos)
    await store.write_open(closed_pos)
    await store.write_close(closed_pos)

    results = await store.get_closed_positions(
        start_date=(now - timedelta(hours=1)).isoformat(),
        end_date=(now + timedelta(hours=1)).isoformat(),
    )
    assert len(results) == 1
    assert results[0]["position_id"] == "closed"


# --- 12. count method ---


@pytest.mark.asyncio
async def test_count_returns_total_records(store: CounterfactualStore) -> None:
    """count() returns the total number of records."""
    assert await store.count() == 0

    await store.write_open(_make_position(position_id="a"))
    await store.write_open(_make_position(position_id="b"))
    assert await store.count() == 2

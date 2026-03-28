"""Tests for OutcomeCollector.

Tests collection from trades-only, counterfactual-only, both sources,
empty databases, date/strategy filtering, and data quality preamble.

Sprint 28, Session 1.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import pytest

from argus.intelligence.learning.outcome_collector import OutcomeCollector

# --- Schema helpers ---

_TRADES_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'us_stocks',
    side TEXT NOT NULL,
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,
    exit_price REAL NOT NULL,
    exit_time TEXT NOT NULL,
    shares INTEGER NOT NULL,
    stop_price REAL NOT NULL,
    target_prices TEXT,
    exit_reason TEXT NOT NULL,
    gross_pnl REAL NOT NULL,
    commission REAL NOT NULL DEFAULT 0,
    net_pnl REAL NOT NULL,
    r_multiple REAL NOT NULL DEFAULT 0,
    hold_duration_seconds INTEGER NOT NULL DEFAULT 0,
    outcome TEXT NOT NULL,
    rationale TEXT,
    notes TEXT,
    quality_grade TEXT,
    quality_score REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_QUALITY_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS quality_history (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    scored_at TEXT NOT NULL,
    pattern_strength REAL NOT NULL,
    catalyst_quality REAL NOT NULL,
    volume_profile REAL NOT NULL,
    historical_match REAL NOT NULL,
    regime_alignment REAL NOT NULL,
    composite_score REAL NOT NULL,
    grade TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    calculated_shares INTEGER NOT NULL,
    signal_context TEXT,
    outcome_trade_id TEXT,
    outcome_realized_pnl REAL,
    outcome_r_multiple REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CF_SCHEMA = """
CREATE TABLE IF NOT EXISTS counterfactual_positions (
    position_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    target_price REAL NOT NULL,
    time_stop_seconds INTEGER,
    rejection_stage TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    quality_score REAL,
    quality_grade TEXT,
    regime_vector_snapshot TEXT,
    signal_metadata TEXT,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    exit_price REAL,
    exit_reason TEXT,
    theoretical_pnl REAL,
    theoretical_r_multiple REAL,
    duration_seconds REAL,
    max_adverse_excursion REAL DEFAULT 0.0,
    max_favorable_excursion REAL DEFAULT 0.0,
    bars_monitored INTEGER DEFAULT 0
)
"""


# --- Fixtures ---


@pytest.fixture()
def tmp_argus_db(tmp_path: Path) -> str:
    """Return path for a temporary argus.db."""
    return str(tmp_path / "argus.db")


@pytest.fixture()
def tmp_cf_db(tmp_path: Path) -> str:
    """Return path for a temporary counterfactual.db."""
    return str(tmp_path / "counterfactual.db")


async def _setup_argus_db(db_path: str) -> None:
    """Create trades + quality_history tables."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(_TRADES_SCHEMA)
        await conn.execute(_QUALITY_HISTORY_SCHEMA)
        await conn.commit()


async def _setup_cf_db(db_path: str) -> None:
    """Create counterfactual_positions table."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(_CF_SCHEMA)
        await conn.commit()


async def _insert_trade(
    db_path: str,
    trade_id: str,
    symbol: str,
    strategy_id: str,
    exit_time: str,
    net_pnl: float,
    r_multiple: float = 1.0,
    quality_score: float = 70.0,
    quality_grade: str = "B",
) -> None:
    """Insert a minimal trade row."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT INTO trades (
                id, strategy_id, symbol, side, entry_price, entry_time,
                exit_price, exit_time, shares, stop_price, exit_reason,
                gross_pnl, net_pnl, r_multiple, outcome,
                quality_grade, quality_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade_id, strategy_id, symbol, "buy", 150.0,
                "2026-03-15T10:00:00", 155.0, exit_time, 100, 148.0,
                "target_1", net_pnl, net_pnl, r_multiple,
                "win" if net_pnl > 0 else "loss",
                quality_grade, quality_score,
            ),
        )
        await conn.commit()


async def _insert_quality_history(
    db_path: str,
    qh_id: str,
    symbol: str,
    strategy_id: str,
    scored_at: str,
    pattern_strength: float = 80.0,
    catalyst_quality: float = 60.0,
    volume_profile: float = 70.0,
    historical_match: float = 50.0,
    regime_alignment: float = 75.0,
) -> None:
    """Insert a quality_history row."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT INTO quality_history (
                id, symbol, strategy_id, scored_at,
                pattern_strength, catalyst_quality, volume_profile,
                historical_match, regime_alignment,
                composite_score, grade, risk_tier,
                entry_price, stop_price, calculated_shares
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                qh_id, symbol, strategy_id, scored_at,
                pattern_strength, catalyst_quality, volume_profile,
                historical_match, regime_alignment,
                72.5, "B+", "B+", 150.0, 148.0, 100,
            ),
        )
        await conn.commit()


async def _insert_counterfactual(
    db_path: str,
    position_id: str,
    symbol: str,
    strategy_id: str,
    opened_at: str,
    closed_at: str,
    theoretical_pnl: float,
    theoretical_r_multiple: float = -0.5,
    rejection_stage: str = "quality_filter",
    rejection_reason: str = "Grade below minimum",
    quality_score: float = 45.0,
    quality_grade: str = "C+",
    regime_snapshot: dict[str, object] | None = None,
) -> None:
    """Insert a closed counterfactual position."""
    snapshot_json = json.dumps(regime_snapshot) if regime_snapshot else None
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT INTO counterfactual_positions (
                position_id, symbol, strategy_id, entry_price, stop_price,
                target_price, rejection_stage, rejection_reason,
                quality_score, quality_grade, regime_vector_snapshot,
                signal_metadata, opened_at, closed_at, exit_price,
                exit_reason, theoretical_pnl, theoretical_r_multiple,
                duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                position_id, symbol, strategy_id, 150.0, 148.0, 155.0,
                rejection_stage, rejection_reason,
                quality_score, quality_grade, snapshot_json,
                "{}", opened_at, closed_at, 147.0,
                "stop_loss", theoretical_pnl, theoretical_r_multiple, 300.0,
            ),
        )
        await conn.commit()


# --- Tests ---


class TestCollectTradesOnly:
    """Collect from trades database only."""

    @pytest.mark.asyncio()
    async def test_collect_trades(self, tmp_argus_db: str, tmp_cf_db: str) -> None:
        """Trades are collected with source='trade'."""
        await _setup_argus_db(tmp_argus_db)
        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb_breakout",
            "2026-03-15T14:30:00", 150.0, 1.5, 72.5, "B+",
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert len(records) == 1
        assert records[0].source == "trade"
        assert records[0].symbol == "AAPL"
        assert records[0].pnl == 150.0
        assert records[0].r_multiple == 1.5

    @pytest.mark.asyncio()
    async def test_trades_with_quality_dimensions(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Quality dimension scores are joined from quality_history."""
        await _setup_argus_db(tmp_argus_db)
        await _insert_quality_history(
            tmp_argus_db, "QH1", "AAPL", "orb_breakout",
            "2026-03-15T10:00:00",
            pattern_strength=85.0,
            catalyst_quality=60.0,
        )
        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb_breakout",
            "2026-03-15T14:30:00", 150.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert len(records) == 1
        assert records[0].dimension_scores["pattern_strength"] == 85.0
        assert records[0].dimension_scores["catalyst_quality"] == 60.0


class TestCollectCounterfactualOnly:
    """Collect from counterfactual database only."""

    @pytest.mark.asyncio()
    async def test_collect_counterfactual(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Counterfactual positions are collected with source='counterfactual'."""
        await _setup_cf_db(tmp_cf_db)
        await _insert_counterfactual(
            tmp_cf_db, "CF1", "TSLA", "vwap_reclaim",
            "2026-03-15T10:00:00", "2026-03-15T14:00:00",
            theoretical_pnl=-50.0,
            regime_snapshot={"primary_regime": "neutral_ranging"},
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert len(records) == 1
        assert records[0].source == "counterfactual"
        assert records[0].symbol == "TSLA"
        assert records[0].pnl == -50.0
        assert records[0].rejection_stage == "quality_filter"
        assert records[0].regime_context["primary_regime"] == "neutral_ranging"


class TestCollectBothSources:
    """Collect from both trades and counterfactual."""

    @pytest.mark.asyncio()
    async def test_combined_collection(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Records from both sources are combined and sorted."""
        await _setup_argus_db(tmp_argus_db)
        await _setup_cf_db(tmp_cf_db)

        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb_breakout",
            "2026-03-15T14:30:00", 150.0,
        )
        await _insert_counterfactual(
            tmp_cf_db, "CF1", "TSLA", "vwap_reclaim",
            "2026-03-15T10:00:00", "2026-03-15T11:00:00",
            theoretical_pnl=-50.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert len(records) == 2
        # Counterfactual closed earlier, should be first
        assert records[0].source == "counterfactual"
        assert records[1].source == "trade"


class TestEmptyDatabases:
    """Empty databases return empty list."""

    @pytest.mark.asyncio()
    async def test_empty_trades_db(self, tmp_argus_db: str, tmp_cf_db: str) -> None:
        """Empty trades DB returns no records."""
        await _setup_argus_db(tmp_argus_db)

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert records == []

    @pytest.mark.asyncio()
    async def test_missing_db_files(self, tmp_path: Path) -> None:
        """Non-existent DB files return empty list, no error."""
        collector = OutcomeCollector(
            str(tmp_path / "nonexistent_argus.db"),
            str(tmp_path / "nonexistent_cf.db"),
        )
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert records == []


class TestDateFiltering:
    """Date range filtering works correctly."""

    @pytest.mark.asyncio()
    async def test_date_filter_excludes_out_of_range(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Trades outside date range are excluded."""
        await _setup_argus_db(tmp_argus_db)
        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb",
            "2026-03-15T14:30:00", 100.0,
        )
        await _insert_trade(
            tmp_argus_db, "T2", "NVDA", "orb",
            "2026-04-15T14:30:00", 200.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert len(records) == 1
        assert records[0].symbol == "AAPL"


class TestStrategyFiltering:
    """Strategy filtering works correctly."""

    @pytest.mark.asyncio()
    async def test_strategy_filter(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Only records for the specified strategy are returned."""
        await _setup_argus_db(tmp_argus_db)
        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb_breakout",
            "2026-03-15T14:30:00", 100.0,
        )
        await _insert_trade(
            tmp_argus_db, "T2", "AAPL", "vwap_reclaim",
            "2026-03-15T15:00:00", 50.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
            strategy_id="orb_breakout",
        )

        assert len(records) == 1
        assert records[0].strategy_id == "orb_breakout"


class TestDataQualityPreamble:
    """DataQualityPreamble computation."""

    @pytest.mark.asyncio()
    async def test_preamble_empty_records(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Empty record list produces zero-count preamble."""
        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        preamble = await collector.build_data_quality_preamble([])

        assert preamble.trading_days_count == 0
        assert preamble.total_trades == 0
        assert preamble.total_counterfactual == 0
        assert preamble.effective_sample_size == 0
        assert preamble.earliest_date is None
        assert preamble.latest_date is None

    @pytest.mark.asyncio()
    async def test_preamble_with_both_sources(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Preamble correctly counts trades vs counterfactual."""
        await _setup_argus_db(tmp_argus_db)
        await _setup_cf_db(tmp_cf_db)

        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb",
            "2026-03-15T14:30:00", 100.0,
        )
        await _insert_trade(
            tmp_argus_db, "T2", "NVDA", "orb",
            "2026-03-16T14:30:00", -50.0,
        )
        await _insert_counterfactual(
            tmp_cf_db, "CF1", "TSLA", "vwap",
            "2026-03-15T10:00:00", "2026-03-15T14:00:00",
            theoretical_pnl=-30.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )
        preamble = await collector.build_data_quality_preamble(records)

        assert preamble.total_trades == 2
        assert preamble.total_counterfactual == 1
        assert preamble.effective_sample_size == 3
        assert preamble.trading_days_count == 2
        assert preamble.earliest_date is not None
        assert preamble.latest_date is not None

    @pytest.mark.asyncio()
    async def test_preamble_flags_no_counterfactual(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Preamble flags when no counterfactual data exists."""
        await _setup_argus_db(tmp_argus_db)
        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb",
            "2026-03-15T14:30:00", 100.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )
        preamble = await collector.build_data_quality_preamble(records)

        gap_text = " ".join(preamble.known_data_gaps)
        assert "counterfactual" in gap_text.lower()

    @pytest.mark.asyncio()
    async def test_preamble_flags_zero_quality_score(
        self, tmp_argus_db: str, tmp_cf_db: str
    ) -> None:
        """Preamble flags records with zero quality score."""
        await _setup_argus_db(tmp_argus_db)
        await _insert_trade(
            tmp_argus_db, "T1", "AAPL", "orb",
            "2026-03-15T14:30:00", 100.0,
            quality_score=0.0,
        )

        collector = OutcomeCollector(tmp_argus_db, tmp_cf_db)
        records = await collector.collect(
            start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
        )
        preamble = await collector.build_data_quality_preamble(records)

        gap_text = " ".join(preamble.known_data_gaps)
        assert "zero quality score" in gap_text.lower()

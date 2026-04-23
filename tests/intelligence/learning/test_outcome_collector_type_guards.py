"""Revert-proof type-guard tests for OutcomeCollector (DEF-185).

Both sites live inside ``try: ... except Exception: logger.warning(..., exc_info=True)``
wrappers, so a TypeError raised by the guard is caught by the outer except
and surfaces as a WARNING-level log record with the exception attached.

Test strategy:
  1. Real SQLite DB with proper schema + one valid row so the WHERE + JOIN
     machinery exercises cleanly.
  2. Monkey-patch ``aiosqlite.Row``-to-dict conversion at the collector's
     call site (via ``dict`` shadowing on the module) to yield a dict with
     the offending field replaced by a non-string integer.
  3. Assert the captured log record's ``exc_info`` holds a ``TypeError``
     with the exact message from the ``if not isinstance: raise`` guard.

Revert proof: restoring ``assert isinstance(x, str)`` changes the captured
exception class from ``TypeError`` → ``AssertionError`` (or under ``python -O``
the assert is stripped and ``datetime.fromisoformat`` raises a TypeError
with a DIFFERENT message: ``"fromisoformat: argument must be str"``). The
message-substring check catches both reversion modes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

from argus.intelligence.learning import outcome_collector as oc_module
from argus.intelligence.learning.outcome_collector import OutcomeCollector


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
    exit_time TEXT,
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


async def _seed_valid_trade(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(_TRADES_SCHEMA)
        await conn.execute(_QUALITY_HISTORY_SCHEMA)
        await conn.execute(
            """INSERT INTO trades (
                id, strategy_id, symbol, side, entry_price, entry_time,
                exit_price, exit_time, shares, stop_price, exit_reason,
                gross_pnl, net_pnl, r_multiple, outcome,
                quality_grade, quality_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "T1", "orb_breakout", "AAPL", "buy",
                150.0, "2026-03-15T10:00:00", 155.0,
                "2026-03-15T14:30:00",
                100, 148.0, "target_1", 500.0, 500.0, 1.5, "win",
                "B+", 72.5,
            ),
        )
        await conn.commit()


async def _seed_valid_counterfactual(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(_CF_SCHEMA)
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
                "P1", "AAPL", "orb_breakout", 150.0, 148.0, 155.0,
                "quality_filter", "grade low", 45.0, "C+", None, "{}",
                "2026-03-15T10:00:00",
                "2026-03-15T11:00:00",
                147.0, "stop_loss", -100.0, -0.5, 300.0,
            ),
        )
        await conn.commit()


class TestOutcomeCollectorTypeGuards:
    """Cover the 2 DEF-185 sites in argus/intelligence/learning/outcome_collector.py."""

    @pytest.mark.asyncio
    async def test_collect_trades_bad_exit_time_logs_typeerror(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        argus_db = str(tmp_path / "argus.db")
        cf_db = str(tmp_path / "counterfactual.db")
        await _seed_valid_trade(argus_db)

        # Shadow `dict` in the outcome_collector module so that
        # `dict(row)` (line 206) substitutes the exit_time field with a
        # non-string, exercising the runtime type guard at line 209.
        original_dict = dict

        def bad_dict(x: object = (), **kwargs: object) -> dict:
            d = original_dict(x, **kwargs)
            if "exit_time" in d:
                d["exit_time"] = 20260315  # non-string, triggers guard
            return d

        with patch.object(oc_module, "dict", bad_dict):
            collector = OutcomeCollector(argus_db, cf_db)
            with caplog.at_level(logging.WARNING):
                records = await collector.collect(
                    start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
                    end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
                )

        assert records == []  # Row skipped; outer except swallowed the guard

        trade_warnings = [
            r for r in caplog.records
            if "Failed to collect trades" in r.getMessage()
        ]
        assert len(trade_warnings) == 1
        captured = trade_warnings[0].exc_info
        assert captured is not None
        exc_type, exc_val, _ = captured
        # Revert-proof: restoring `assert isinstance(exit_time_str, str)`
        # would surface AssertionError, not TypeError.
        assert exc_type is TypeError, (
            f"Expected TypeError from guard, got {exc_type.__name__}: {exc_val}"
        )
        assert "Expected str for exit_time" in str(exc_val)

    @pytest.mark.asyncio
    async def test_collect_counterfactual_bad_closed_at_logs_typeerror(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        argus_db = str(tmp_path / "argus.db")
        cf_db = str(tmp_path / "counterfactual.db")
        # Empty argus.db (both required schemas present to avoid the
        # trade-collection branch masking the counterfactual warning we test).
        async with aiosqlite.connect(argus_db) as conn:
            await conn.execute(_TRADES_SCHEMA)
            await conn.execute(_QUALITY_HISTORY_SCHEMA)
            await conn.commit()
        await _seed_valid_counterfactual(cf_db)

        original_dict = dict

        def bad_dict(x: object = (), **kwargs: object) -> dict:
            d = original_dict(x, **kwargs)
            if "closed_at" in d:
                d["closed_at"] = 20260315
            return d

        with patch.object(oc_module, "dict", bad_dict):
            collector = OutcomeCollector(argus_db, cf_db)
            with caplog.at_level(logging.WARNING):
                records = await collector.collect(
                    start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
                    end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
                )

        assert records == []

        cf_warnings = [
            r for r in caplog.records
            if "Failed to collect counterfactual" in r.getMessage()
        ]
        assert len(cf_warnings) == 1
        captured = cf_warnings[0].exc_info
        assert captured is not None
        exc_type, exc_val, _ = captured
        assert exc_type is TypeError, (
            f"Expected TypeError from guard, got {exc_type.__name__}: {exc_val}"
        )
        assert "Expected str for closed_at" in str(exc_val)

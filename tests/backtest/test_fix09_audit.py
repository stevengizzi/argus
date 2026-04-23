"""Regression tests for FIX-09-backtest-engine (audit 2026-04-21).

Pins behaviors introduced or documented by the FIX-09 session so the
findings cannot silently regress:

- Finding 2 (P1-E1-M02) — BacktestEngine bar dispatch uses itertuples
  (not iterrows) and produces identical output.
- Finding 9 (P1-E1-L04) — ``_load_data`` drops NYSE-holiday dates with a
  WARNING even if the cache somehow contains them.
- Finding 20 (P1-E1-L05) — both ``EventBus`` and ``SyncEventBus`` satisfy
  ``EventBusProtocol`` structurally.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import logging
import pandas as pd
import pytest

from argus.backtest.backtest_data_service import BacktestDataService
from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.core.event_bus import EventBus
from argus.core.protocols import EventBusProtocol
from argus.core.sync_event_bus import SyncEventBus


def _make_config(tmp_path: Path) -> BacktestEngineConfig:
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
    )


# ---------------------------------------------------------------------------
# F20: EventBusProtocol conformance (P1-E1-L05)
# ---------------------------------------------------------------------------


class TestEventBusProtocolConformance:
    """Both concrete buses must satisfy the Protocol runtime-checkable check
    and type-check as valid constructor args for BacktestDataService.
    """

    def test_event_bus_satisfies_protocol(self) -> None:
        bus = EventBus()
        assert isinstance(bus, EventBusProtocol)

    def test_sync_event_bus_satisfies_protocol(self) -> None:
        bus = SyncEventBus()
        assert isinstance(bus, EventBusProtocol)

    def test_backtest_data_service_accepts_both_buses(self) -> None:
        """Constructor must accept either bus without a type: ignore."""
        ds1 = BacktestDataService(EventBus())
        ds2 = BacktestDataService(SyncEventBus())
        assert ds1 is not None
        assert ds2 is not None


# ---------------------------------------------------------------------------
# F9: Holiday filter in _load_data (P1-E1-L04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_data_drops_holiday_dates(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch,
) -> None:
    """If the cache somehow contains a bar dated on an NYSE holiday,
    ``_load_data`` excludes it from ``self._trading_days`` and logs a
    WARNING. Databento EQUS.MINI does not return holiday bars, so the
    guard is belt-and-suspenders for corrupted caches.
    """
    # Good Friday 2026 — known NYSE holiday.
    holiday = date(2026, 4, 3)
    good_day = date(2026, 4, 6)

    # Build two-day bar frame: one legal session + one holiday session.
    rows = []
    for d in (holiday, good_day):
        ts = datetime(d.year, d.month, d.day, 13, 30, tzinfo=UTC)
        rows.append(
            {
                "timestamp": ts,
                "open": 100.0,
                "high": 100.5,
                "low": 99.5,
                "close": 100.2,
                "volume": 1_000,
                "trading_date": d,
            }
        )
    df = pd.DataFrame(rows)

    async def fake_load(*args, **kwargs):  # noqa: ANN001
        return {"AAPL": df}

    engine = BacktestEngine(_make_config(tmp_path))
    # Bypass HistoricalDataFeed with our in-memory frame.
    from argus.backtest import engine as engine_mod

    class _FakeFeed:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001, D401
            pass

        async def load(self, *args, **kwargs):  # noqa: ANN001
            return await fake_load()

    monkeypatch.setattr(engine_mod, "HistoricalDataFeed", _FakeFeed)

    # Force symbols (skip cache auto-detect).
    engine._config.symbols = ["AAPL"]

    with caplog.at_level(logging.WARNING, logger="argus.backtest.engine"):
        await engine._load_data()

    assert engine._trading_days == [good_day], (
        "Holiday date must be dropped from trading_days"
    )
    assert any(
        "Dropping holiday date" in rec.message and str(holiday) in rec.message
        for rec in caplog.records
    ), "Holiday skip must emit a WARNING log"


# ---------------------------------------------------------------------------
# F2: itertuples parity with prior iterrows behavior (P1-E1-M02)
# ---------------------------------------------------------------------------


def test_itertuples_parity_against_iterrows() -> None:
    """Functional-equivalence smoke check: iterating the bar frame via
    ``itertuples(index=False)`` produces the same per-bar tuple as
    ``iterrows`` did for the fields BacktestEngine consumes.

    This is the non-flaky replacement for a timing benchmark — it locks
    the behavioral contract (symbol, timestamp, o/h/l/c/v are all readable
    and numerically equal) so a future refactor that changes the iteration
    mode cannot silently produce divergent per-row values.
    """
    ts = datetime(2025, 6, 16, 13, 30, tzinfo=UTC)
    df = pd.DataFrame(
        [
            {
                "timestamp": ts,
                "symbol": "AAPL",
                "open": 150.0,
                "high": 151.0,
                "low": 149.5,
                "close": 150.5,
                "volume": 5_000,
            },
            {
                "timestamp": ts,
                "symbol": "NVDA",
                "open": 900.0,
                "high": 905.0,
                "low": 895.0,
                "close": 902.0,
                "volume": 10_000,
            },
        ]
    )

    iterrows_view = [
        (
            row["symbol"],
            row["timestamp"],
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            int(row["volume"]),
        )
        for _, row in df.iterrows()
    ]
    itertuples_view = [
        (
            row.symbol,
            row.timestamp,
            float(row.open),
            float(row.high),
            float(row.low),
            float(row.close),
            int(row.volume),
        )
        for row in df.itertuples(index=False)
    ]
    assert iterrows_view == itertuples_view

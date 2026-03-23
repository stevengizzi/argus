"""Execution quality record for slippage model calibration.

Captures expected vs. actual fill prices for every executed order,
enabling slippage model validation and calibration (DEC-358 §5.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")

from argus.core.ids import generate_id
from argus.db.manager import DatabaseManager


@dataclass(frozen=True)
class ExecutionRecord:
    """Immutable record of execution quality for a single fill.

    Compares expected fill price (from signal) against actual fill price
    (from broker) to measure slippage relative to the backtest model.
    """

    record_id: str
    order_id: str
    symbol: str
    strategy_id: str
    side: str
    expected_fill_price: float
    expected_slippage_bps: float
    actual_fill_price: float
    actual_slippage_bps: float
    time_of_day: str
    order_size_shares: int
    avg_daily_volume: int | None
    bid_ask_spread_bps: float | None
    latency_ms: float | None
    slippage_vs_model: float
    created_at: str


def create_execution_record(
    order_id: str,
    symbol: str,
    strategy_id: str,
    side: str,
    expected_fill_price: float,
    actual_fill_price: float,
    order_size_shares: int,
    signal_timestamp: datetime,
    fill_timestamp: datetime,
    avg_daily_volume: int | None = None,
    bid_ask_spread_bps: float | None = None,
    expected_slippage_bps: float = 1.0,
) -> ExecutionRecord:
    """Create an ExecutionRecord with derived fields computed automatically.

    Args:
        order_id: The order that was filled.
        symbol: Ticker symbol.
        strategy_id: Strategy that originated the signal.
        side: "BUY" or "SELL".
        expected_fill_price: Price from SignalEvent.entry_price at signal time.
        actual_fill_price: Price from OrderFilledEvent.fill_price.
        order_size_shares: Number of shares in the order.
        signal_timestamp: When the signal was generated.
        fill_timestamp: When the broker confirmed the fill.
        avg_daily_volume: From Universe Manager reference data, if available.
        bid_ask_spread_bps: From L1 data, if available.
        expected_slippage_bps: Slippage assumed in backtest model (default 1.0).

    Returns:
        A frozen ExecutionRecord with all derived fields computed.

    Raises:
        ValueError: If expected_fill_price is zero (cannot compute slippage).
    """
    if expected_fill_price == 0.0:
        raise ValueError("expected_fill_price must be non-zero")

    actual_slippage_bps = (
        abs(actual_fill_price - expected_fill_price) / expected_fill_price * 10_000
    )
    slippage_vs_model = actual_slippage_bps - expected_slippage_bps

    time_of_day = fill_timestamp.astimezone(_ET).strftime("%H:%M:%S")

    latency_ms: float | None = None
    delta = fill_timestamp - signal_timestamp
    delta_ms = delta.total_seconds() * 1000
    if delta_ms >= 0:
        latency_ms = delta_ms

    return ExecutionRecord(
        record_id=generate_id(),
        order_id=order_id,
        symbol=symbol,
        strategy_id=strategy_id,
        side=side,
        expected_fill_price=expected_fill_price,
        expected_slippage_bps=expected_slippage_bps,
        actual_fill_price=actual_fill_price,
        actual_slippage_bps=actual_slippage_bps,
        time_of_day=time_of_day,
        order_size_shares=order_size_shares,
        avg_daily_volume=avg_daily_volume,
        bid_ask_spread_bps=bid_ask_spread_bps,
        latency_ms=latency_ms,
        slippage_vs_model=slippage_vs_model,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def save_execution_record(
    db_manager: DatabaseManager, record: ExecutionRecord
) -> None:
    """Persist an ExecutionRecord to the execution_records table.

    Args:
        db_manager: Initialized DatabaseManager instance.
        record: The execution record to save.
    """
    await db_manager.execute(
        """
        INSERT INTO execution_records (
            record_id, order_id, symbol, strategy_id, side,
            expected_fill_price, expected_slippage_bps,
            actual_fill_price, actual_slippage_bps,
            time_of_day, order_size_shares,
            avg_daily_volume, bid_ask_spread_bps, latency_ms,
            slippage_vs_model, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.record_id,
            record.order_id,
            record.symbol,
            record.strategy_id,
            record.side,
            record.expected_fill_price,
            record.expected_slippage_bps,
            record.actual_fill_price,
            record.actual_slippage_bps,
            record.time_of_day,
            record.order_size_shares,
            record.avg_daily_volume,
            record.bid_ask_spread_bps,
            record.latency_ms,
            record.slippage_vs_model,
            record.created_at,
        ),
    )
    await db_manager.commit()

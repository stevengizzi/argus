"""Counterfactual position tracking — shadow monitoring of rejected signals.

Tracks what would have happened to signals rejected by the Quality Engine,
Position Sizer, or Risk Manager. Each rejected signal becomes a
CounterfactualPosition that is monitored bar-by-bar using the same
evaluate_bar_exit() fill model as the BacktestEngine.

Sprint 27.7, Session 1: Core model and tracker logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from enum import StrEnum
from typing import TYPE_CHECKING

from ulid import ULID
from zoneinfo import ZoneInfo

from argus.core.fill_model import FillExitReason, ExitResult, evaluate_bar_exit

if TYPE_CHECKING:
    from argus.core.events import CandleEvent, SignalEvent
    from argus.data.intraday_candle_store import IntradayCandleStore

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class RejectionStage(StrEnum):
    """Where in the pipeline the signal was rejected."""

    QUALITY_FILTER = "quality_filter"
    POSITION_SIZER = "position_sizer"
    RISK_MANAGER = "risk_manager"
    SHADOW = "shadow"


@dataclass(frozen=True)
class CounterfactualPosition:
    """Immutable record of a counterfactual (shadow) position.

    Created when a position is closed. During monitoring, mutable state
    is held in _OpenPosition internally by the tracker.

    Attributes:
        position_id: ULID identifier.
        symbol: Stock symbol.
        strategy_id: Strategy that generated the signal.
        entry_price: Theoretical entry price from the signal.
        stop_price: Stop loss price from the signal.
        target_price: T1 target price (first element of signal.target_prices).
        time_stop_seconds: Optional time stop duration.
        rejection_stage: Where in the pipeline the signal was rejected.
        rejection_reason: Human-readable rejection reason.
        quality_score: Quality Engine score at rejection time (if available).
        quality_grade: Quality Engine grade at rejection time (if available).
        regime_vector_snapshot: RegimeVector.to_dict() at rejection time.
        signal_metadata: Signal context and additional metadata.
        opened_at: When the position was opened (ET naive).
        closed_at: When the position was closed (ET naive).
        exit_price: Fill price at close.
        exit_reason: Why the position was closed.
        theoretical_pnl: exit_price - entry_price (for LONG).
        theoretical_r_multiple: pnl / (entry_price - stop_price).
        duration_seconds: Time from open to close in seconds.
        max_adverse_excursion: Worst drawdown from entry (always >= 0).
        max_favorable_excursion: Best unrealized gain from entry (always >= 0).
        bars_monitored: Number of candles processed.
    """

    # Identity
    position_id: str

    # Signal data
    symbol: str
    strategy_id: str
    entry_price: float
    stop_price: float
    target_price: float
    time_stop_seconds: int | None

    # Rejection metadata
    rejection_stage: RejectionStage
    rejection_reason: str
    quality_score: float | None
    quality_grade: str | None
    regime_vector_snapshot: dict[str, object] | None
    signal_metadata: dict[str, object]

    # Timing
    opened_at: datetime
    closed_at: datetime | None

    # Outcome
    exit_price: float | None
    exit_reason: FillExitReason | None
    theoretical_pnl: float | None
    theoretical_r_multiple: float | None
    duration_seconds: float | None

    # Tracking
    max_adverse_excursion: float
    max_favorable_excursion: float
    bars_monitored: int


@dataclass
class _OpenPosition:
    """Mutable monitoring state for an open counterfactual position.

    Held by CounterfactualTracker while the position is being monitored.
    Converted to a frozen CounterfactualPosition on close.
    """

    position_id: str
    symbol: str
    strategy_id: str
    entry_price: float
    stop_price: float
    target_price: float
    time_stop_seconds: int | None

    rejection_stage: RejectionStage
    rejection_reason: str
    quality_score: float | None
    quality_grade: str | None
    regime_vector_snapshot: dict[str, object] | None
    signal_metadata: dict[str, object]

    opened_at: datetime

    # Mutable monitoring fields
    max_adverse_excursion: float = 0.0
    max_favorable_excursion: float = 0.0
    bars_monitored: int = 0
    last_bar_time: datetime | None = None
    last_known_price: float | None = None


class CounterfactualTracker:
    """Tracks rejected signals as shadow positions using bar-level fill model.

    Opens a counterfactual position for each rejected signal and monitors it
    bar-by-bar through the same evaluate_bar_exit() logic used by BacktestEngine.
    Supports IntradayCandleStore backfill at position open to catch exits that
    occurred between rejection and the next live candle.

    Args:
        candle_store: Optional IntradayCandleStore for historical backfill.
        eod_close_time: Market close time string in HH:MM format (ET).
        no_data_timeout_seconds: Seconds before a position with no data expires.
    """

    def __init__(
        self,
        candle_store: IntradayCandleStore | None = None,
        eod_close_time: str = "16:00",
        no_data_timeout_seconds: int = 300,
    ) -> None:
        """Initialize the counterfactual tracker.

        Args:
            candle_store: Optional IntradayCandleStore for backfill on track().
            eod_close_time: Market close time as HH:MM (ET).
            no_data_timeout_seconds: Timeout before marking position as EXPIRED.
        """
        self._candle_store = candle_store
        hours, minutes = eod_close_time.split(":")
        self._eod_close_time = dt_time(int(hours), int(minutes))
        self._no_data_timeout_seconds = no_data_timeout_seconds

        self._open_positions: dict[str, _OpenPosition] = {}
        self._closed_positions: list[CounterfactualPosition] = []
        self._symbols_to_positions: dict[str, set[str]] = {}

    def track(
        self,
        signal: SignalEvent,
        rejection_reason: str,
        rejection_stage: RejectionStage,
        metadata: dict[str, object] | None = None,
    ) -> str | None:
        """Open a counterfactual position for a rejected signal.

        Immediately queries IntradayCandleStore for historical bars since
        entry_time and processes them. If the position would already be
        closed (e.g., stop breached before rejection point), it's marked
        closed immediately.

        Args:
            signal: The rejected SignalEvent.
            rejection_reason: Human-readable reason for rejection.
            rejection_stage: Where in the pipeline the rejection occurred.
            metadata: Optional additional metadata to store.

        Returns:
            Position ID (ULID) if tracking started, None if skipped.
        """
        if not signal.target_prices:
            logger.warning(
                "Skipping counterfactual for %s/%s — empty target_prices",
                signal.strategy_id,
                signal.symbol,
            )
            return None

        position_id = str(ULID())
        now_et = datetime.now(_ET)

        signal_metadata: dict[str, object] = dict(signal.signal_context)
        if metadata:
            signal_metadata.update(metadata)

        pos = _OpenPosition(
            position_id=position_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            entry_price=signal.entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_prices[0],
            time_stop_seconds=signal.time_stop_seconds,
            rejection_stage=rejection_stage,
            rejection_reason=rejection_reason,
            quality_score=signal.quality_score if signal.quality_score else None,
            quality_grade=signal.quality_grade if signal.quality_grade else None,
            regime_vector_snapshot=(
                metadata.get("regime_vector_snapshot")  # type: ignore[union-attr]
                if metadata and "regime_vector_snapshot" in metadata
                else None
            ),
            signal_metadata=signal_metadata,
            opened_at=now_et,
            last_known_price=signal.entry_price,
        )

        self._open_positions[position_id] = pos
        if signal.symbol not in self._symbols_to_positions:
            self._symbols_to_positions[signal.symbol] = set()
        self._symbols_to_positions[signal.symbol].add(position_id)

        # Backfill from IntradayCandleStore if available
        if self._candle_store is not None and self._candle_store.has_bars(signal.symbol):
            bars = self._candle_store.get_bars(
                signal.symbol,
                start_time=signal.timestamp,
            )
            for bar in bars:
                if position_id not in self._open_positions:
                    break  # Already closed during backfill
                self._process_bar(
                    position_id,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.timestamp,
                )

        logger.info(
            "Counterfactual position opened: %s %s/%s entry=%.2f stop=%.2f "
            "target=%.2f stage=%s reason=%s",
            position_id,
            signal.strategy_id,
            signal.symbol,
            signal.entry_price,
            signal.stop_price,
            signal.target_prices[0],
            rejection_stage.value,
            rejection_reason,
        )

        return position_id

    async def on_candle(self, event: CandleEvent) -> None:
        """Process a candle for all open positions on this symbol.

        Uses evaluate_bar_exit() from the shared fill model. Updates MAE/MFE.

        Args:
            event: The CandleEvent to process.
        """
        position_ids = self._symbols_to_positions.get(event.symbol)
        if not position_ids:
            return

        # Copy the set to avoid mutation during iteration
        for pid in list(position_ids):
            if pid not in self._open_positions:
                continue
            self._process_bar(
                pid,
                event.high,
                event.low,
                event.close,
                event.timestamp,
            )

    async def close_all_eod(self) -> None:
        """Close all remaining open positions at EOD.

        Mark-to-market at last known price.
        """
        for pid in list(self._open_positions):
            pos = self._open_positions[pid]
            close_price = pos.last_known_price or pos.entry_price
            self._close_position(pos, FillExitReason.EOD_CLOSED, close_price)

    def check_timeouts(self) -> list[str]:
        """Check for positions that haven't received data within timeout.

        Returns:
            List of expired position_ids.
        """
        now = datetime.now(_ET)
        expired: list[str] = []

        for pid in list(self._open_positions):
            pos = self._open_positions[pid]
            ref_time = pos.last_bar_time or pos.opened_at
            elapsed = (now - ref_time).total_seconds()
            if elapsed >= self._no_data_timeout_seconds:
                close_price = pos.last_known_price or pos.entry_price
                self._close_position(pos, FillExitReason.EXPIRED, close_price)
                expired.append(pid)

        return expired

    def get_open_positions(self) -> list[_OpenPosition]:
        """Return all currently monitored positions.

        Returns:
            List of mutable open position states.
        """
        return list(self._open_positions.values())

    def get_closed_positions(
        self, since: datetime | None = None
    ) -> list[CounterfactualPosition]:
        """Return closed positions, optionally filtered by close time.

        Args:
            since: If provided, only return positions closed after this time.

        Returns:
            List of frozen CounterfactualPosition records.
        """
        if since is None:
            return list(self._closed_positions)
        return [
            p for p in self._closed_positions
            if p.closed_at is not None and p.closed_at >= since
        ]

    # --- Internal helpers ---

    def _process_bar(
        self,
        position_id: str,
        bar_high: float,
        bar_low: float,
        bar_close: float,
        bar_timestamp: datetime,
    ) -> None:
        """Process a single bar for an open position.

        Updates MAE/MFE and checks for exit via the shared fill model.

        Args:
            position_id: ID of the open position.
            bar_high: Bar high price.
            bar_low: Bar low price.
            bar_close: Bar close price.
            bar_timestamp: Bar timestamp.
        """
        pos = self._open_positions.get(position_id)
        if pos is None:
            return

        # Update monitoring state
        pos.bars_monitored += 1
        pos.last_bar_time = bar_timestamp
        pos.last_known_price = bar_close

        # Update MAE/MFE (for LONG positions)
        adverse = pos.entry_price - bar_low
        if adverse > pos.max_adverse_excursion:
            pos.max_adverse_excursion = adverse

        favorable = bar_high - pos.entry_price
        if favorable > pos.max_favorable_excursion:
            pos.max_favorable_excursion = favorable

        # Check time stop expiration
        time_stop_expired = False
        if pos.time_stop_seconds is not None:
            elapsed = (bar_timestamp - pos.opened_at).total_seconds()
            if elapsed >= pos.time_stop_seconds:
                time_stop_expired = True

        # Evaluate exit using shared fill model
        result = evaluate_bar_exit(
            bar_high=bar_high,
            bar_low=bar_low,
            bar_close=bar_close,
            stop_price=pos.stop_price,
            target_price=pos.target_price,
            time_stop_expired=time_stop_expired,
        )

        if result is not None:
            self._close_position(pos, result.exit_reason, result.exit_price)

    def _close_position(
        self,
        pos: _OpenPosition,
        exit_reason: FillExitReason,
        exit_price: float,
    ) -> None:
        """Close an open position and move it to closed list.

        Args:
            pos: The open position to close.
            exit_reason: Why the position was closed.
            exit_price: The fill price at close.
        """
        now_et = datetime.now(_ET)
        duration = (now_et - pos.opened_at).total_seconds()

        pnl = exit_price - pos.entry_price
        risk_per_share = pos.entry_price - pos.stop_price
        r_multiple = pnl / risk_per_share if risk_per_share != 0 else 0.0

        closed = CounterfactualPosition(
            position_id=pos.position_id,
            symbol=pos.symbol,
            strategy_id=pos.strategy_id,
            entry_price=pos.entry_price,
            stop_price=pos.stop_price,
            target_price=pos.target_price,
            time_stop_seconds=pos.time_stop_seconds,
            rejection_stage=pos.rejection_stage,
            rejection_reason=pos.rejection_reason,
            quality_score=pos.quality_score,
            quality_grade=pos.quality_grade,
            regime_vector_snapshot=pos.regime_vector_snapshot,
            signal_metadata=pos.signal_metadata,
            opened_at=pos.opened_at,
            closed_at=now_et,
            exit_price=exit_price,
            exit_reason=exit_reason,
            theoretical_pnl=pnl,
            theoretical_r_multiple=r_multiple,
            duration_seconds=duration,
            max_adverse_excursion=pos.max_adverse_excursion,
            max_favorable_excursion=pos.max_favorable_excursion,
            bars_monitored=pos.bars_monitored,
        )

        self._closed_positions.append(closed)

        # Remove from open tracking
        del self._open_positions[pos.position_id]
        symbol_pids = self._symbols_to_positions.get(pos.symbol)
        if symbol_pids:
            symbol_pids.discard(pos.position_id)
            if not symbol_pids:
                del self._symbols_to_positions[pos.symbol]

        logger.info(
            "Counterfactual position closed: %s %s/%s reason=%s "
            "pnl=%.2f R=%.2f bars=%d",
            pos.position_id,
            pos.strategy_id,
            pos.symbol,
            exit_reason.value,
            pnl,
            r_multiple,
            pos.bars_monitored,
        )

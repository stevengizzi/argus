"""Shared theoretical fill model for bar-level exit evaluation.

Extracts the worst-case-for-longs fill priority logic used by both
BacktestEngine and CounterfactualTracker. Pure functions — no side effects,
no state, no I/O.

Fill priority (worst-case-for-longs):
1. Stop loss — bar.low <= stop_price → fill at stop_price
2. Target — bar.high >= target_price → fill at target_price
3. Time stop — elapsed >= time_stop_seconds → fill at bar.close
   (but use stop_price if bar.low also hits stop)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FillExitReason(StrEnum):
    """Why a theoretical position was closed by the fill model."""

    STOPPED_OUT = "stopped_out"
    TARGET_HIT = "target_hit"
    TIME_STOPPED = "time_stopped"
    EOD_CLOSED = "eod_closed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ExitResult:
    """Result of a bar-level exit evaluation.

    Attributes:
        exit_reason: Why the position exited.
        exit_price: The fill price for the exit.
    """

    exit_reason: FillExitReason
    exit_price: float


def evaluate_bar_exit(
    bar_high: float,
    bar_low: float,
    bar_close: float,
    stop_price: float,
    target_price: float,
    time_stop_expired: bool,
) -> ExitResult | None:
    """Evaluate whether a bar triggers an exit for a long position.

    Implements worst-case-for-longs priority: when multiple exit conditions
    trigger on the same bar, the stop (worst outcome) wins.

    Args:
        bar_high: Bar high price.
        bar_low: Bar low price.
        bar_close: Bar close price.
        stop_price: Stop loss price.
        target_price: Target (take-profit) price.
        time_stop_expired: Whether the time stop has expired as of this bar.

    Returns:
        ExitResult if an exit triggered, None if position remains open.
    """
    # Priority 1: Stop loss (worst case for longs)
    # When both stop and target could trigger on the same bar, stop wins
    if bar_low <= stop_price:
        return ExitResult(FillExitReason.STOPPED_OUT, stop_price)

    # Priority 2: Target hit
    if bar_high >= target_price:
        return ExitResult(FillExitReason.TARGET_HIT, target_price)

    # Priority 3: Time stop
    # If time stop expired, check if stop also hit on this bar (worst case)
    if time_stop_expired:
        if bar_low <= stop_price:
            return ExitResult(FillExitReason.STOPPED_OUT, stop_price)
        return ExitResult(FillExitReason.TIME_STOPPED, bar_close)

    return None

"""Pure-function library for exit management math.

Stateless functions for computing trailing stop prices, escalation stop prices,
and effective (tightest) stop selection. Shared by Order Manager, BacktestEngine,
and CounterfactualTracker.

Design: same philosophy as fill_model.py — pure functions, no side effects,
no I/O, no state, no logging. Zero argus imports.
"""

from __future__ import annotations

from enum import StrEnum


class StopToLevel(StrEnum):
    """Target level for escalation stop phases (AMD-5).

    Each value represents the profit fraction at which the stop is placed
    relative to entry_price and high_watermark.
    """

    BREAKEVEN = "breakeven"
    QUARTER_PROFIT = "quarter_profit"
    HALF_PROFIT = "half_profit"
    THREE_QUARTER_PROFIT = "three_quarter_profit"


# Mapping from StopToLevel to the fraction of (high_watermark - entry_price)
_STOP_TO_FRACTION: dict[StopToLevel, float] = {
    StopToLevel.BREAKEVEN: 0.0,
    StopToLevel.QUARTER_PROFIT: 0.25,
    StopToLevel.HALF_PROFIT: 0.50,
    StopToLevel.THREE_QUARTER_PROFIT: 0.75,
}


def compute_trailing_stop(
    high_watermark: float,
    atr_value: float | None,
    trail_type: str,
    atr_multiplier: float = 2.5,
    trail_percent: float = 0.02,
    fixed_distance: float = 0.50,
    min_trail_distance: float = 0.05,
    enabled: bool = True,
) -> float | None:
    """Compute the trailing stop price from the high watermark.

    Args:
        high_watermark: Highest price reached since entry.
        atr_value: Current ATR value. Required when trail_type is "atr".
        trail_type: Trailing stop method — "atr", "percent", or "fixed".
        atr_multiplier: ATR multiplier for "atr" type (default 2.5).
        trail_percent: Percentage of high_watermark for "percent" type (default 0.02).
        fixed_distance: Fixed dollar distance for "fixed" type (default 0.50).
        min_trail_distance: Minimum trail distance floor applied to all types (default 0.05).
        enabled: Whether trailing stop is enabled (default True).

    Returns:
        Trailing stop price, or None if disabled or ATR is invalid.
    """
    if not enabled:
        return None

    if trail_type == "atr":
        # AMD-12: invalid ATR produces no trail price
        if atr_value is None or atr_value <= 0:
            return None
        trail_distance = atr_value * atr_multiplier
    elif trail_type == "percent":
        trail_distance = high_watermark * trail_percent
    elif trail_type == "fixed":
        trail_distance = fixed_distance
    else:
        raise ValueError(f"Unknown trail_type: {trail_type!r}. Expected 'atr', 'percent', or 'fixed'.")

    # Apply minimum floor
    trail_distance = max(trail_distance, min_trail_distance)

    return high_watermark - trail_distance


def compute_escalation_stop(
    entry_price: float,
    high_watermark: float,
    elapsed_seconds: float,
    time_stop_seconds: float | None,
    phases: list[tuple[float, str]],
    enabled: bool = True,
) -> float | None:
    """Compute the escalation stop price based on elapsed time and phases.

    As time progresses toward the time stop, the stop is ratcheted through
    escalation phases (AMD-5). Each phase specifies an elapsed-time threshold
    and a stop_to level.

    Args:
        entry_price: Original entry price of the position.
        high_watermark: Highest price reached since entry.
        elapsed_seconds: Seconds elapsed since entry.
        time_stop_seconds: Total time stop duration in seconds. None means no time stop.
        phases: List of (elapsed_pct_threshold, stop_to_level) tuples, sorted ascending
            by elapsed_pct_threshold. stop_to_level is a StopToLevel string value.
        enabled: Whether escalation is enabled (default True).

    Returns:
        Escalation stop price, or None if disabled, no time stop, or no phase reached.
    """
    if not enabled:
        return None

    if time_stop_seconds is None:
        return None

    if not phases:
        return None

    elapsed_pct = elapsed_seconds / time_stop_seconds

    # Find the latest phase where elapsed_pct >= phase threshold (phases sorted ascending)
    active_phase_stop_to: str | None = None
    for threshold, stop_to in phases:
        if elapsed_pct >= threshold:
            active_phase_stop_to = stop_to
        else:
            break

    if active_phase_stop_to is None:
        return None

    level = StopToLevel(active_phase_stop_to)
    fraction = _STOP_TO_FRACTION[level]
    return entry_price + fraction * (high_watermark - entry_price)


def compute_effective_stop(
    original_stop: float,
    trail_stop: float | None,
    escalation_stop: float | None,
) -> float:
    """Return the tightest (highest for longs) stop from all sources.

    The original stop is always present. Trail and escalation stops may be None
    if their respective features are disabled or conditions not met.

    Args:
        original_stop: The signal's original stop-loss price (always non-None).
        trail_stop: Trailing stop price, or None if not active.
        escalation_stop: Escalation stop price, or None if not active.

    Returns:
        The highest (tightest for longs) stop price among all non-None values.
    """
    candidates = [original_stop]
    if trail_stop is not None:
        candidates.append(trail_stop)
    if escalation_stop is not None:
        candidates.append(escalation_stop)
    return max(candidates)

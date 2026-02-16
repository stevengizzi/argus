"""Synthesize tick sequences from 1-minute bar OHLC data.

Generates 4 synthetic ticks per bar to drive the Order Manager's
tick-based exit evaluation. The tick order depends on bar direction
to simulate a conservative intra-bar price path for longs:

- Bullish bar (close >= open): O -> L -> H -> C
  (dip before rally - stop gets tested before target)
- Bearish bar (close < open): O -> H -> L -> C
  (rally before dip - target gets tested before stop)

This is the "worst-case for longs" ordering, which produces
conservative backtest results. Real intra-bar paths are more complex,
but this 4-tick model exercises the actual Order Manager code and is
sufficient for strategy validation.

Limitations (documented, accepted):
- Real ticks within a 1m bar can number in the hundreds/thousands.
- True intra-bar path may hit stop AND target - we can only detect one.
- Volume per tick is approximated as bar_volume / 4.

Decision reference: DEC-053 (Synthetic Tick Generation from Bar OHLC)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SyntheticTick:
    """A single synthetic tick derived from bar OHLC.

    Attributes:
        symbol: Ticker symbol.
        price: Tick price.
        volume: Approximate volume (bar_volume / 4).
        timestamp: Tick timestamp within the 1-minute bar.
    """

    symbol: str
    price: float
    volume: int
    timestamp: datetime


def synthesize_ticks(
    symbol: str,
    timestamp: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int,
) -> list[SyntheticTick]:
    """Generate 4 synthetic ticks from a bar's OHLC.

    Args:
        symbol: Ticker symbol.
        timestamp: Bar timestamp (start of the 1-minute bar).
        open_: Bar open price.
        high: Bar high price.
        low: Bar low price.
        close: Bar close price.
        volume: Bar volume.

    Returns:
        List of 4 SyntheticTick objects in the appropriate order.
        - Bullish (close >= open): O, L, H, C (dip first, conservative for longs)
        - Bearish (close < open): O, H, L, C (rally first, conservative for longs)
    """
    tick_volume = max(1, volume // 4)

    # Determine tick order based on bar direction
    # Bullish (close >= open): O -> L -> H -> C (dip first, conservative for longs)
    # Bearish (close < open): O -> H -> L -> C (rally first, conservative for longs)
    prices = [open_, low, high, close] if close >= open_ else [open_, high, low, close]

    # Space ticks ~15 seconds apart within the 1-minute bar
    ticks = []
    for i, price in enumerate(prices):
        tick_time = timestamp + timedelta(seconds=i * 15)
        ticks.append(
            SyntheticTick(
                symbol=symbol,
                price=price,
                volume=tick_volume,
                timestamp=tick_time,
            )
        )

    return ticks

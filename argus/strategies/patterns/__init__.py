"""Reusable pattern detection modules for ARGUS strategies.

Pattern modules encapsulate chart pattern detection logic (e.g., bull flag,
flat-top breakout) independently of strategy execution concerns. Each module
implements the PatternModule ABC and can be composed with PatternBasedStrategy
to create a fully functional trading strategy.
"""

from argus.strategies.patterns.abcd import ABCDPattern
from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.dip_and_rip import DipAndRipPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.patterns.gap_and_go import GapAndGoPattern
from argus.strategies.patterns.hod_break import HODBreakPattern
from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern


def __getattr__(name: str) -> object:
    """Lazy import to avoid circular dependency with pattern_strategy."""
    if name == "PatternBasedStrategy":
        from argus.strategies.pattern_strategy import PatternBasedStrategy

        return PatternBasedStrategy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ABCDPattern",
    "BullFlagPattern",
    "CandleBar",
    "DipAndRipPattern",
    "FlatTopBreakoutPattern",
    "GapAndGoPattern",
    "HODBreakPattern",
    "PatternBasedStrategy",
    "PatternDetection",
    "PatternModule",
    "PatternParam",
    "PreMarketHighBreakPattern",
]

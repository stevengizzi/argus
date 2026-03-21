"""Reusable pattern detection modules for ARGUS strategies.

Pattern modules encapsulate chart pattern detection logic (e.g., bull flag,
flat-top breakout) independently of strategy execution concerns. Each module
implements the PatternModule ABC and can be composed with PatternBasedStrategy
to create a fully functional trading strategy.
"""

from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule

__all__ = ["CandleBar", "PatternDetection", "PatternModule"]

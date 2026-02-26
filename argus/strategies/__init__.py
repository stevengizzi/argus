"""Strategy module for the Argus trading system.

This module contains the BaseStrategy ABC, OrbBaseStrategy (shared ORB logic),
and all concrete strategy implementations. Strategies follow a daily-stateful,
session-stateless model.
"""

from argus.strategies.afternoon_momentum import (
    AfternoonMomentumStrategy,
    ConsolidationState,
    ConsolidationSymbolState,
)
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.orb_base import OrbBaseStrategy, OrbSymbolState
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy, VwapState, VwapSymbolState

__all__ = [
    "AfternoonMomentumStrategy",
    "BaseStrategy",
    "ConsolidationState",
    "ConsolidationSymbolState",
    "OrbBaseStrategy",
    "OrbBreakoutStrategy",
    "OrbScalpStrategy",
    "OrbSymbolState",
    "VwapReclaimStrategy",
    "VwapState",
    "VwapSymbolState",
]

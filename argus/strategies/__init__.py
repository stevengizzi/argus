"""Strategy module for the Argus trading system.

This module contains the BaseStrategy ABC, OrbBaseStrategy (shared ORB logic),
and all concrete strategy implementations. Strategies follow a daily-stateful,
session-stateless model.
"""

from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.orb_base import OrbBaseStrategy, OrbSymbolState

__all__ = ["BaseStrategy", "OrbBaseStrategy", "OrbSymbolState"]

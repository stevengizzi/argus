"""Strategy module for the Argus trading system.

This module contains the BaseStrategy ABC and all concrete strategy
implementations. Strategies follow a daily-stateful, session-stateless model.
"""

from argus.strategies.base_strategy import BaseStrategy

__all__ = ["BaseStrategy"]

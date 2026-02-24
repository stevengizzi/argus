"""Strategy throttling and allocation types for the Orchestrator.

Defines throttle actions and strategy allocation data structures used
when the Orchestrator adjusts capital distribution across strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ThrottleAction(StrEnum):
    """Throttle action applied to a strategy.

    When a strategy underperforms or risk conditions warrant it,
    the Orchestrator can reduce or suspend its allocation.
    """

    NONE = "none"
    REDUCE = "reduce"
    SUSPEND = "suspend"


@dataclass
class StrategyAllocation:
    """Capital allocation for a single strategy.

    Represents the Orchestrator's allocation decision for one strategy,
    including the percentage of capital, dollar amount, any throttle
    action applied, and eligibility status.

    Attributes:
        strategy_id: Unique identifier for the strategy.
        allocation_pct: Percentage of deployable capital allocated (0.0 to 1.0).
        allocation_dollars: Dollar amount allocated to this strategy.
        throttle_action: Current throttle action applied.
        eligible: Whether the strategy is eligible to trade.
        reason: Explanation for the allocation decision.
    """

    strategy_id: str
    allocation_pct: float
    allocation_dollars: float
    throttle_action: ThrottleAction
    eligible: bool
    reason: str

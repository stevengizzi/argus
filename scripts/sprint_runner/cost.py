"""Cost tracking for the sprint runner.

Estimates token usage and cost, enforces cost ceiling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.sprint_runner.config import CostConfig
    from scripts.sprint_runner.state import RunState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Rough estimation: ~4 characters per token (common heuristic for English text)
CHARS_PER_TOKEN = 4


# ---------------------------------------------------------------------------
# Cost Tracker
# ---------------------------------------------------------------------------


class CostTracker:
    """Tracks token usage and cost across sprint sessions.

    Provides estimation methods and ceiling enforcement.
    """

    def __init__(self, config: CostConfig) -> None:
        """Initialize the cost tracker.

        Args:
            config: Cost configuration with rates and ceiling.
        """
        self.config = config

    def estimate_tokens(self, output: str) -> int:
        """Estimate token count from output string.

        Uses a rough heuristic of ~4 characters per token.

        Args:
            output: The output string to estimate.

        Returns:
            Estimated token count.
        """
        if not output:
            return 0

        # Use byte length for more accurate estimation
        byte_length = len(output.encode("utf-8"))
        return byte_length // CHARS_PER_TOKEN

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost from token counts.

        Args:
            input_tokens: Estimated input token count.
            output_tokens: Estimated output token count.

        Returns:
            Estimated cost in USD.
        """
        input_cost = input_tokens * self.config.rates.input_per_million / 1_000_000
        output_cost = output_tokens * self.config.rates.output_per_million / 1_000_000
        return input_cost + output_cost

    def update(
        self,
        session_id: str,
        output: str,
        run_state: RunState,
        input_estimate: int | None = None,
    ) -> tuple[int, float]:
        """Update run state with cost tracking for a session.

        Args:
            session_id: The session ID.
            output: The session output string.
            run_state: The run state to update.
            input_estimate: Optional input token estimate. If not provided,
                           estimates from output size (assuming similar sizes).

        Returns:
            Tuple of (estimated_tokens, estimated_cost_usd).
        """
        output_tokens = self.estimate_tokens(output)

        # Estimate input tokens if not provided
        # Heuristic: input is typically similar size to output for implementation sessions
        if input_estimate is None:
            input_estimate = output_tokens

        cost = self.estimate_cost(input_estimate, output_tokens)

        # Update session result if it exists
        if session_id in run_state.session_results:
            session_result = run_state.session_results[session_id]
            session_result.token_usage_estimate = input_estimate + output_tokens
            session_result.cost_estimate_usd = cost

        # Update run state totals
        run_state.cost.total_tokens_estimate += input_estimate + output_tokens
        run_state.cost.total_cost_estimate_usd += cost

        logger.debug(
            f"Session {session_id} cost: {output_tokens} output tokens, "
            f"${cost:.4f} estimated"
        )

        return (input_estimate + output_tokens, cost)

    def check_ceiling(self, run_state: RunState) -> bool:
        """Check if cost ceiling has been exceeded.

        Args:
            run_state: The run state with cost tracking.

        Returns:
            True if ceiling exceeded, False otherwise.
        """
        if not self.config.halt_on_ceiling:
            return False

        current_cost = run_state.cost.total_cost_estimate_usd
        ceiling = run_state.cost.ceiling_usd

        exceeded = current_cost > ceiling

        if exceeded:
            logger.warning(
                f"Cost ceiling exceeded: ${current_cost:.2f} > ${ceiling:.2f}"
            )

        return exceeded

    def get_remaining_budget(self, run_state: RunState) -> float:
        """Get remaining budget before ceiling.

        Args:
            run_state: The run state with cost tracking.

        Returns:
            Remaining budget in USD.
        """
        return max(0.0, run_state.cost.ceiling_usd - run_state.cost.total_cost_estimate_usd)

    def get_usage_percentage(self, run_state: RunState) -> float:
        """Get percentage of ceiling used.

        Args:
            run_state: The run state with cost tracking.

        Returns:
            Percentage of ceiling used (0-100+).
        """
        if run_state.cost.ceiling_usd <= 0:
            return 0.0

        return (run_state.cost.total_cost_estimate_usd / run_state.cost.ceiling_usd) * 100

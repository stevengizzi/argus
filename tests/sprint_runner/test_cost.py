"""Tests for cost tracking module."""

from __future__ import annotations

import pytest

from scripts.sprint_runner.config import CostConfig, CostRates
from scripts.sprint_runner.cost import CostTracker, CHARS_PER_TOKEN
from scripts.sprint_runner.state import (
    CostState,
    GitState,
    RunState,
    SessionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cost_config() -> CostConfig:
    """Create a test cost config."""
    return CostConfig(
        ceiling_usd=50.0,
        rates=CostRates(
            input_per_million=3.0,
            output_per_million=15.0,
            cached_input_per_million=0.30,
        ),
        halt_on_ceiling=True,
    )


@pytest.fixture
def cost_tracker(cost_config: CostConfig) -> CostTracker:
    """Create a cost tracker for testing."""
    return CostTracker(cost_config)


@pytest.fixture
def run_state() -> RunState:
    """Create a test run state."""
    state = RunState(
        sprint="23",
        git_state=GitState(branch="main"),
        cost=CostState(ceiling_usd=50.0),
    )
    state.session_results["S1"] = SessionResult()
    return state


# ---------------------------------------------------------------------------
# Token Estimation Tests
# ---------------------------------------------------------------------------


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimates_tokens_from_string(self, cost_tracker: CostTracker) -> None:
        """Estimates tokens from output string."""
        # 1000 characters should be ~250 tokens (4 chars per token)
        output = "x" * 1000
        tokens = cost_tracker.estimate_tokens(output)

        assert tokens == 1000 // CHARS_PER_TOKEN
        assert tokens == 250

    def test_empty_string_returns_zero_tokens(self, cost_tracker: CostTracker) -> None:
        """Empty string returns zero tokens."""
        tokens = cost_tracker.estimate_tokens("")
        assert tokens == 0

    def test_unicode_uses_byte_length(self, cost_tracker: CostTracker) -> None:
        """Unicode strings use byte length for estimation."""
        # Unicode characters take more bytes
        output = "你好" * 100  # 2 characters * 100 = 200 chars, but more bytes
        tokens = cost_tracker.estimate_tokens(output)

        # Each Chinese character is 3 bytes in UTF-8
        expected_bytes = 3 * 2 * 100  # 600 bytes
        expected_tokens = expected_bytes // CHARS_PER_TOKEN

        assert tokens == expected_tokens


# ---------------------------------------------------------------------------
# Cost Calculation Tests
# ---------------------------------------------------------------------------


class TestCostCalculation:
    """Tests for cost calculation."""

    def test_calculates_cost_from_tokens(self, cost_tracker: CostTracker) -> None:
        """Calculates USD cost from token counts."""
        input_tokens = 1000
        output_tokens = 500

        cost = cost_tracker.estimate_cost(input_tokens, output_tokens)

        # Input: 1000 * (3.0 / 1_000_000) = 0.003
        # Output: 500 * (15.0 / 1_000_000) = 0.0075
        # Total: 0.0105
        expected = (1000 * 3.0 / 1_000_000) + (500 * 15.0 / 1_000_000)
        assert cost == pytest.approx(expected)
        assert cost == pytest.approx(0.0105)

    def test_zero_tokens_zero_cost(self, cost_tracker: CostTracker) -> None:
        """Zero tokens results in zero cost."""
        cost = cost_tracker.estimate_cost(0, 0)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# Ceiling Check Tests
# ---------------------------------------------------------------------------


class TestCeilingCheck:
    """Tests for cost ceiling enforcement."""

    def test_ceiling_not_exceeded(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Returns False when ceiling not exceeded."""
        run_state.cost.total_cost_estimate_usd = 25.0
        run_state.cost.ceiling_usd = 50.0

        exceeded = cost_tracker.check_ceiling(run_state)
        assert exceeded is False

    def test_ceiling_exceeded(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Returns True when ceiling exceeded."""
        run_state.cost.total_cost_estimate_usd = 55.0
        run_state.cost.ceiling_usd = 50.0

        exceeded = cost_tracker.check_ceiling(run_state)
        assert exceeded is True

    def test_ceiling_check_disabled(self, run_state: RunState) -> None:
        """Returns False when halt_on_ceiling is False."""
        config = CostConfig(ceiling_usd=50.0, halt_on_ceiling=False)
        tracker = CostTracker(config)

        run_state.cost.total_cost_estimate_usd = 100.0
        run_state.cost.ceiling_usd = 50.0

        exceeded = tracker.check_ceiling(run_state)
        assert exceeded is False


# ---------------------------------------------------------------------------
# State Update Tests
# ---------------------------------------------------------------------------


class TestCostUpdate:
    """Tests for cost accumulation."""

    def test_updates_run_state_cost_totals(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Updates run state with accumulated costs."""
        initial_cost = run_state.cost.total_cost_estimate_usd
        initial_tokens = run_state.cost.total_tokens_estimate

        output = "x" * 4000  # ~1000 tokens

        tokens, cost = cost_tracker.update("S1", output, run_state)

        # Should have updated totals
        assert run_state.cost.total_tokens_estimate > initial_tokens
        assert run_state.cost.total_cost_estimate_usd > initial_cost

        # Should have updated session result
        assert run_state.session_results["S1"].token_usage_estimate is not None
        assert run_state.session_results["S1"].cost_estimate_usd is not None

    def test_accumulates_across_sessions(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Cost accumulates across multiple sessions."""
        run_state.session_results["S2"] = SessionResult()

        cost_tracker.update("S1", "x" * 4000, run_state)
        cost_after_s1 = run_state.cost.total_cost_estimate_usd

        cost_tracker.update("S2", "x" * 4000, run_state)
        cost_after_s2 = run_state.cost.total_cost_estimate_usd

        assert cost_after_s2 > cost_after_s1
        assert cost_after_s2 == pytest.approx(cost_after_s1 * 2, rel=0.01)


# ---------------------------------------------------------------------------
# Helper Method Tests
# ---------------------------------------------------------------------------


class TestHelperMethods:
    """Tests for helper methods."""

    def test_remaining_budget(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Calculates remaining budget correctly."""
        run_state.cost.total_cost_estimate_usd = 20.0
        run_state.cost.ceiling_usd = 50.0

        remaining = cost_tracker.get_remaining_budget(run_state)
        assert remaining == 30.0

    def test_remaining_budget_when_exceeded(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Returns 0 when budget exceeded."""
        run_state.cost.total_cost_estimate_usd = 60.0
        run_state.cost.ceiling_usd = 50.0

        remaining = cost_tracker.get_remaining_budget(run_state)
        assert remaining == 0.0

    def test_usage_percentage(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Calculates usage percentage correctly."""
        run_state.cost.total_cost_estimate_usd = 25.0
        run_state.cost.ceiling_usd = 50.0

        percentage = cost_tracker.get_usage_percentage(run_state)
        assert percentage == 50.0

    def test_usage_percentage_over_ceiling(
        self, cost_tracker: CostTracker, run_state: RunState
    ) -> None:
        """Usage percentage can exceed 100%."""
        run_state.cost.total_cost_estimate_usd = 75.0
        run_state.cost.ceiling_usd = 50.0

        percentage = cost_tracker.get_usage_percentage(run_state)
        assert percentage == 150.0

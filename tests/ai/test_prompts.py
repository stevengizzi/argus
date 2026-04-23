"""Tests for PromptManager."""

from __future__ import annotations

import pytest

from argus.ai.config import AIConfig
from argus.ai.prompts import PromptManager, estimate_tokens, truncate_to_token_budget


class TestTokenEstimation:
    """Test token estimation utilities."""

    def test_estimate_tokens_empty_string(self) -> None:
        """Test token estimation for empty string."""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_short_string(self) -> None:
        """Test token estimation for short string."""
        # 16 characters / 4 = 4 tokens
        assert estimate_tokens("Hello, World!123") == 4

    def test_estimate_tokens_longer_string(self) -> None:
        """Test token estimation for longer string."""
        text = "a" * 1000  # 1000 chars / 4 = 250 tokens
        assert estimate_tokens(text) == 250


class TestTruncateToTokenBudget:
    """Test truncation to token budget."""

    def test_no_truncation_needed(self) -> None:
        """Test that text within budget is not truncated."""
        text = "Hello, World!"  # ~3 tokens
        result = truncate_to_token_budget(text, budget=100)
        assert result == text

    def test_truncation_applied(self) -> None:
        """Test that text exceeding budget is truncated."""
        text = "a" * 1000  # ~250 tokens
        result = truncate_to_token_budget(text, budget=50)  # 50 * 4 = 200 chars max
        assert len(result) <= 200
        assert result.endswith("...")


class TestPromptManagerSystemPrompt:
    """Test PromptManager system prompt generation."""

    @pytest.fixture
    def manager(self) -> PromptManager:
        """Create a PromptManager with default config."""
        return PromptManager(AIConfig())

    def test_system_prompt_contains_required_sections(self, manager: PromptManager) -> None:
        """Test that system prompt contains all required sections."""
        prompt = manager.build_system_prompt()

        assert "ARGUS AI Copilot" in prompt
        assert "About ARGUS" in prompt
        assert "Active Strategies" in prompt
        assert "Current Configuration" in prompt
        assert "Your Role" in prompt
        assert "Tool Use — Mandatory for Configuration Changes" in prompt
        assert "Behavioral Guardrails" in prompt
        assert "ADVISORY ONLY" in prompt
        assert "NEVER recommend specific trade" in prompt

    def test_system_prompt_contains_mandatory_tool_use_directive(
        self, manager: PromptManager
    ) -> None:
        """Test that system prompt contains mandatory tool use instructions."""
        prompt = manager.build_system_prompt()

        # Check for explicit mandatory language
        assert "you MUST immediately use the corresponding tool" in prompt
        assert "Do not narrate your intention to use the tool" in prompt

        # Check all 5 tool types are mentioned
        assert "propose_allocation_change" in prompt
        assert "propose_risk_param_change" in prompt
        assert "propose_strategy_suspend" in prompt
        assert "propose_strategy_resume" in prompt
        assert "generate_report" in prompt

        # Check prohibition against narrating without calling
        assert 'Never respond with "Let me propose that"' in prompt

    def test_system_prompt_with_strategies(self, manager: PromptManager) -> None:
        """Test system prompt with strategy data."""
        strategies = [
            {
                "name": "ORB Breakout",
                "window": "9:45-11:30 ET",
                "hold_time": "30-60 min",
                "mechanic": "Opening range breakout with volume confirmation",
            },
            {
                "name": "VWAP Reclaim",
                "window": "10:00-12:00 ET",
                "hold_time": "15-45 min",
                "mechanic": "Mean reversion after VWAP pullback",
            },
        ]

        prompt = manager.build_system_prompt(strategies=strategies)

        assert "ORB Breakout" in prompt
        assert "9:45-11:30 ET" in prompt
        assert "VWAP Reclaim" in prompt

    def test_system_prompt_with_config(self, manager: PromptManager) -> None:
        """Test system prompt with system configuration."""
        config = {
            "risk_limits": {
                "daily_loss_limit_pct": "3%",
                "max_concurrent_positions": 10,
            },
            "allocation": {"method": "equal_weight"},
            "regime": "normal",
        }

        prompt = manager.build_system_prompt(system_config=config)

        assert "Daily loss limit: 3%" in prompt
        assert "equal_weight" in prompt
        assert "normal" in prompt


class TestPromptManagerPageContext:
    """Test PromptManager page context formatting."""

    @pytest.fixture
    def manager(self) -> PromptManager:
        """Create a PromptManager with default config."""
        return PromptManager(AIConfig())

    def test_dashboard_context(self, manager: PromptManager) -> None:
        """Test Dashboard page context formatting."""
        context_data = {
            "portfolio_summary": {
                "equity": 100000.0,
                "daily_pnl": 250.0,
                "open_positions": 3,
            },
            "positions": [
                {"symbol": "AAPL", "shares": 100, "avg_price": 175.50},
            ],
            "regime": "normal",
        }

        context = manager.build_page_context("Dashboard", context_data)

        assert "Dashboard" in context
        assert "Portfolio Summary" in context
        assert "$100,000.00" in context
        assert "AAPL" in context

    def test_trades_context(self, manager: PromptManager) -> None:
        """Test Trades page context formatting."""
        context_data = {
            "recent_trades": [
                {"symbol": "TSLA", "pnl": 150.0, "outcome": "win"},
                {"symbol": "NVDA", "pnl": -75.0, "outcome": "loss"},
            ],
            "filters": {"strategy": "orb_breakout"},
        }

        context = manager.build_page_context("Trades", context_data)

        assert "Trades" in context
        assert "Recent Trades" in context
        assert "TSLA" in context
        assert "+150.00" in context

    def test_context_truncation(self, manager: PromptManager) -> None:
        """Test that context is truncated to fit budget."""
        # Create very large context data
        large_context = {
            "recent_trades": [
                {"symbol": f"SYM{i}", "pnl": i * 10.0, "outcome": "win"}
                for i in range(1000)
            ]
        }

        context = manager.build_page_context("Trades", large_context)

        # Should be truncated to ~2000 tokens (~8000 chars)
        assert len(context) <= 8500  # Some buffer for truncation

    @pytest.mark.parametrize(
        "page,context_data,expected_substrings",
        [
            (
                "Performance",
                {
                    "metrics": {
                        "win_rate": 0.65,
                        "profit_factor": 1.8,
                        "sharpe_ratio": 1.2,
                        "net_pnl": 1234.56,
                    },
                    "timeframe": "Last 30 days",
                },
                [
                    "Performance Metrics",
                    "Win rate: 65.0%",
                    "Profit factor: 1.80",
                    "Sharpe ratio: 1.20",
                    "Net P&L: $1,234.56",
                    "Timeframe: Last 30 days",
                ],
            ),
            (
                "Orchestrator",
                {
                    "allocations": [{"strategy_id": "orb_breakout", "pct": 25.0}],
                    "regime": "trending_up",
                    "schedule_state": "active",
                },
                [
                    "Strategy Allocations",
                    "orb_breakout: 25.0%",
                    "Current Regime: trending_up",
                    "Schedule State: active",
                ],
            ),
            (
                "PatternLibrary",
                {
                    "selected_pattern": {
                        "name": "Bull Flag",
                        "stats": {"win_rate": 0.58, "sample_size": 120},
                    }
                },
                [
                    "Selected Pattern: Bull Flag",
                    "Win rate: 58.0%",
                    "Sample size: 120",
                ],
            ),
            (
                "Debrief",
                {
                    "today_summary": {"total_trades": 12, "net_pnl": 456.78},
                    "selected_conversation": "2026-04-22",
                },
                [
                    "Today's Summary",
                    "Total trades: 12",
                    "Net P&L: $456.78",
                    "Viewing conversation from: 2026-04-22",
                ],
            ),
            (
                "System",
                {
                    "health": {"status": "healthy", "uptime": "3d 4h"},
                    "connections": {"broker": "connected", "data_feed": "connected"},
                },
                [
                    "System Health",
                    "Status: healthy",
                    "Uptime: 3d 4h",
                    "Connection States",
                    "broker: connected",
                    "data_feed: connected",
                ],
            ),
        ],
    )
    def test_page_context_formatters(
        self,
        page: str,
        context_data: dict,
        expected_substrings: list[str],
        manager: PromptManager,
    ) -> None:
        """Each page formatter produces the expected section markers + data lines."""
        result = manager.build_page_context(page, context_data)
        assert f"## Current Page: {page}" in result
        for substring in expected_substrings:
            assert substring in result, (
                f"Expected {substring!r} in result for page {page}:\n{result}"
            )

    def test_unknown_page_falls_back_to_raw_context(self, manager: PromptManager) -> None:
        """Unknown page identifier falls through to the default ``Context data:`` line."""
        data = {"foo": "bar", "n": 42}
        result = manager.build_page_context("UnknownPage", data)
        assert "## Current Page: UnknownPage" in result
        assert "Context data:" in result
        assert "foo" in result and "bar" in result


class TestPromptManagerEdgeBranches:
    """Cover edge branches in prompt helpers that the existing happy-path tests miss."""

    def test_truncate_history_handles_non_string_content(self) -> None:
        """A history message whose ``content`` is a list (tool_use blocks) must be counted
        via ``str(content)`` rather than raising — exercises the ``else`` branch of
        ``isinstance(content, str)`` in ``_truncate_history``.
        """
        config = AIConfig(history_token_budget=1000, max_history_messages=100)
        manager = PromptManager(config)

        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Here is the data"},
                    {"type": "tool_use", "id": "t1", "name": "get_data", "input": {}},
                ],
            },
        ]

        system, messages = manager.build_conversation_messages(
            history=history,
            user_message="Thanks",
            system="Test",
            page_context="",
        )

        # Non-string content was counted (no exception raised) and kept within budget.
        assert len(messages) == 2
        assert messages[0]["content"] == history[0]["content"]

    def test_truncate_history_breaks_on_non_string_content_over_budget(self) -> None:
        """When non-string content exceeds the token budget on its own, the loop must
        break rather than including it — covers the ``374 -> 378`` branch where the
        non-string ``msg_tokens`` branch feeds directly into the budget check.
        """
        # AIConfig enforces ``ge=100`` on history_token_budget; exceed it with stringified
        # content large enough that a single message blows past the budget.
        config = AIConfig(history_token_budget=100, max_history_messages=100)
        manager = PromptManager(config)

        # Oversized list content: str(content) > 2000 chars → > 500 tokens, exceeds 100.
        big_blob = "x" * 3000
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": big_blob},
                    {"type": "tool_use", "id": "t1", "name": "get_data", "input": {"k": big_blob}},
                ],
            },
        ]

        system, messages = manager.build_conversation_messages(
            history=history,
            user_message="New",
            system="Test",
            page_context="",
        )

        # Oversized message dropped; only the new user message remains.
        assert len(messages) == 1
        assert messages[0]["content"] == "New"


class TestPromptManagerConversationMessages:
    """Test PromptManager conversation message assembly."""

    @pytest.fixture
    def manager(self) -> PromptManager:
        """Create a PromptManager with default config."""
        return PromptManager(AIConfig())

    def test_build_conversation_messages_basic(self, manager: PromptManager) -> None:
        """Test basic conversation message assembly."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        system, messages = manager.build_conversation_messages(
            history=history,
            user_message="How is the portfolio doing?",
            system="Test system prompt",
            page_context="## Page: Dashboard",
        )

        assert "Test system prompt" in system
        assert "## Page: Dashboard" in system
        assert len(messages) == 3  # 2 history + 1 new
        assert messages[-1]["content"] == "How is the portfolio doing?"

    def test_history_truncation_by_message_count(self, manager: PromptManager) -> None:
        """Test that history is truncated to max_history_messages."""
        # Create history with more than 20 messages
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(30)
        ]

        system, messages = manager.build_conversation_messages(
            history=history,
            user_message="New message",
            system="Test system",
            page_context="",
        )

        # Should have at most 21 messages (20 history + 1 new)
        assert len(messages) <= 21

    def test_history_truncation_by_token_budget(self) -> None:
        """Test that history is truncated by token budget."""
        # Create config with low token budget
        config = AIConfig(history_token_budget=100, max_history_messages=100)
        manager = PromptManager(config)

        # Create history with large messages
        history = [
            {"role": "user", "content": "x" * 200}  # ~50 tokens each
            for _ in range(10)
        ]

        system, messages = manager.build_conversation_messages(
            history=history,
            user_message="New message",
            system="Test system",
            page_context="",
        )

        # Should be truncated to fit ~100 tokens
        # At ~50 tokens per message, should keep ~2 messages + new message
        assert len(messages) <= 4

"""Prompt management for the ARGUS AI Copilot.

Handles system prompt construction, page context formatting, and conversation
history management with token budget enforcement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from argus.ai.config import AIConfig

# System prompt template - versioned in code
SYSTEM_PROMPT_TEMPLATE = """You are the ARGUS AI Copilot, an AI assistant integrated into the ARGUS automated day trading system.

## About ARGUS
ARGUS is a fully automated multi-strategy day trading system for US equities, operated by a single trader based in Taipei, Taiwan. Trading occurs during US market hours (9:30 AM-4:00 PM ET, which is 10:30 PM-5:00 AM Taipei time). The system is designed to generate household income for the operator's family.

## Active Strategies
{strategies_section}

## Current Configuration
{config_section}

## Your Role
- You are ADVISORY ONLY. You help the operator understand system behavior, analyze performance, and propose configuration changes.
- You NEVER recommend specific trade entries or exits. You do not tell the operator to buy or sell specific stocks.
- You ALWAYS caveat uncertainty. If you are unsure about data or analysis, say so explicitly.
- You reference ACTUAL portfolio data, trade history, and system state when available. NEVER fabricate positions, P&L figures, or trade data.
- When proposing actions (allocation changes, parameter updates, strategy suspend/resume), use the provided tools. The operator must approve all proposals before execution.
- You can generate reports (daily summaries, strategy analysis, risk reviews) which are saved to the Debrief for later review.

## Tool Use — Mandatory for Configuration Changes

When the operator requests, agrees to, or endorses any of the following, you MUST immediately use the corresponding tool. Do not narrate your intention to use the tool — call it directly.

- Allocation change → use `propose_allocation_change`
- Risk parameter change → use `propose_risk_param_change`
- Strategy suspension → use `propose_strategy_suspend`
- Strategy resumption → use `propose_strategy_resume`
- Report generation → use `generate_report`

Do NOT ask for additional confirmation after the operator has stated their intent. The approval workflow handles confirmation — that is its purpose. Your job is to create the proposal promptly so the operator can approve or reject it through the action card.

If you need clarification (e.g., the operator says "change the allocation" without specifying a number), ask ONE clarifying question, then use the tool as soon as you have sufficient information.

Never respond with "Let me propose that" or "I'll submit that" as text without actually invoking the tool in the same response.

## Behavioral Guardrails
- Do not provide generic financial advice. Your knowledge is specific to ARGUS and its strategies.
- Do not speculate about market direction. Focus on what the data shows.
- If asked about something outside your context (e.g., a stock not in the universe, a strategy not implemented), say so.
- Be concise but thorough. The operator is checking in during overnight hours and values efficient communication."""

# Default strategy section when no strategies are loaded
DEFAULT_STRATEGIES_SECTION = """No strategies currently active. System may be in pre-market or configuration mode."""

# Default config section when no config is available
DEFAULT_CONFIG_SECTION = """Configuration not available in current context."""


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string.

    Uses a rough heuristic of ~4 characters per token, which is
    conservative for English text.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    return len(text) // 4


def truncate_to_token_budget(text: str, budget: int) -> str:
    """Truncate text to fit within a token budget.

    Args:
        text: The text to truncate.
        budget: Maximum tokens allowed.

    Returns:
        Truncated text with ellipsis if truncation occurred.
    """
    estimated = estimate_tokens(text)
    if estimated <= budget:
        return text

    # Calculate approximate character limit
    char_limit = budget * 4
    if len(text) <= char_limit:
        return text

    return text[: char_limit - 3] + "..."


class PromptManager:
    """Manages prompt construction for Claude API calls.

    Handles:
    - System prompt generation with dynamic strategy/config sections
    - Page-specific context formatting with token budgets
    - Conversation history truncation
    """

    def __init__(self, config: AIConfig) -> None:
        """Initialize the PromptManager.

        Args:
            config: AI configuration with token budgets.
        """
        self._config = config

    def build_system_prompt(
        self,
        strategies: list[dict[str, Any]] | None = None,
        system_config: dict[str, Any] | None = None,
    ) -> str:
        """Build the system prompt with dynamic strategy and config sections.

        Args:
            strategies: List of strategy info dicts with keys:
                - name: Strategy display name
                - window: Operating window (e.g., "9:45-11:30 ET")
                - hold_time: Typical hold time
                - mechanic: Key mechanic description
            system_config: System configuration dict with keys:
                - risk_limits: Risk limit settings
                - allocation: Current allocation percentages
                - regime: Current regime classification

        Returns:
            Complete system prompt string.
        """
        # Build strategies section
        if strategies:
            strategy_lines = []
            for s in strategies:
                name = s.get("name", "Unknown")
                window = s.get("window", "N/A")
                hold_time = s.get("hold_time", "N/A")
                mechanic = s.get("mechanic", "N/A")
                strategy_lines.append(
                    f"- **{name}**: Window: {window}, Hold: {hold_time}, Mechanic: {mechanic}"
                )
            strategies_section = "\n".join(strategy_lines)
        else:
            strategies_section = DEFAULT_STRATEGIES_SECTION

        # Build config section
        if system_config:
            config_lines = []
            if "risk_limits" in system_config:
                rl = system_config["risk_limits"]
                config_lines.append(
                    f"- Daily loss limit: {rl.get('daily_loss_limit_pct', 'N/A')}"
                )
                config_lines.append(
                    f"- Max concurrent positions: {rl.get('max_concurrent_positions', 'N/A')}"
                )
            if "allocation" in system_config:
                alloc = system_config["allocation"]
                config_lines.append(f"- Allocation method: {alloc.get('method', 'N/A')}")
            if "regime" in system_config:
                config_lines.append(f"- Current regime: {system_config['regime']}")
            config_section = "\n".join(config_lines) if config_lines else DEFAULT_CONFIG_SECTION
        else:
            config_section = DEFAULT_CONFIG_SECTION

        # Format the template
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            strategies_section=strategies_section,
            config_section=config_section,
        )

        # Truncate if needed
        return truncate_to_token_budget(prompt, self._config.system_prompt_token_budget)

    def build_page_context(self, page: str, context_data: dict[str, Any]) -> str:
        """Format page-specific context within token budget.

        Args:
            page: Page identifier (e.g., "Dashboard", "Trades").
            context_data: Context data specific to the page.

        Returns:
            Formatted context string within budget.
        """
        context_lines = [f"## Current Page: {page}"]

        # Format context data based on page type
        if page == "Dashboard":
            context_lines.extend(self._format_dashboard_context(context_data))
        elif page == "Trades":
            context_lines.extend(self._format_trades_context(context_data))
        elif page == "Performance":
            context_lines.extend(self._format_performance_context(context_data))
        elif page == "Orchestrator":
            context_lines.extend(self._format_orchestrator_context(context_data))
        elif page == "PatternLibrary":
            context_lines.extend(self._format_pattern_library_context(context_data))
        elif page == "Debrief":
            context_lines.extend(self._format_debrief_context(context_data))
        elif page == "System":
            context_lines.extend(self._format_system_context(context_data))
        else:
            context_lines.append(f"Context data: {context_data}")

        context_str = "\n".join(context_lines)
        return truncate_to_token_budget(context_str, self._config.page_context_token_budget)

    def _format_dashboard_context(self, data: dict[str, Any]) -> list[str]:
        """Format Dashboard page context."""
        lines = []
        if "portfolio_summary" in data:
            ps = data["portfolio_summary"]
            lines.append(f"### Portfolio Summary")
            lines.append(f"- Equity: ${ps.get('equity', 'N/A'):,.2f}")
            lines.append(f"- Daily P&L: ${ps.get('daily_pnl', 'N/A'):,.2f}")
            lines.append(f"- Open positions: {ps.get('open_positions', 'N/A')}")
        if "positions" in data:
            lines.append(f"### Open Positions")
            for pos in data["positions"][:5]:  # Limit to 5
                lines.append(f"- {pos.get('symbol')}: {pos.get('shares')} shares @ ${pos.get('avg_price', 0):.2f}")
        if "regime" in data:
            lines.append(f"### Regime: {data['regime']}")
        return lines

    def _format_trades_context(self, data: dict[str, Any]) -> list[str]:
        """Format Trades page context."""
        lines = []
        if "recent_trades" in data:
            lines.append(f"### Recent Trades (last {len(data['recent_trades'])})")
            for trade in data["recent_trades"][:10]:  # Limit to 10
                symbol = trade.get("symbol", "?")
                pnl = trade.get("pnl", 0)
                outcome = trade.get("outcome", "?")
                lines.append(f"- {symbol}: ${pnl:+.2f} ({outcome})")
        if "filters" in data:
            lines.append(f"### Active Filters: {data['filters']}")
        return lines

    def _format_performance_context(self, data: dict[str, Any]) -> list[str]:
        """Format Performance page context."""
        lines = []
        if "metrics" in data:
            m = data["metrics"]
            lines.append("### Performance Metrics")
            lines.append(f"- Win rate: {m.get('win_rate', 0):.1%}")
            lines.append(f"- Profit factor: {m.get('profit_factor', 0):.2f}")
            lines.append(f"- Sharpe ratio: {m.get('sharpe_ratio', 0):.2f}")
            lines.append(f"- Net P&L: ${m.get('net_pnl', 0):,.2f}")
        if "timeframe" in data:
            lines.append(f"### Timeframe: {data['timeframe']}")
        return lines

    def _format_orchestrator_context(self, data: dict[str, Any]) -> list[str]:
        """Format Orchestrator page context."""
        lines = []
        if "allocations" in data:
            lines.append("### Strategy Allocations")
            for alloc in data["allocations"]:
                lines.append(f"- {alloc.get('strategy_id')}: {alloc.get('pct', 0):.1f}%")
        if "regime" in data:
            lines.append(f"### Current Regime: {data['regime']}")
        if "schedule_state" in data:
            lines.append(f"### Schedule State: {data['schedule_state']}")
        return lines

    def _format_pattern_library_context(self, data: dict[str, Any]) -> list[str]:
        """Format Pattern Library page context."""
        lines = []
        if "selected_pattern" in data:
            p = data["selected_pattern"]
            lines.append(f"### Selected Pattern: {p.get('name', 'None')}")
            if "stats" in p:
                lines.append(f"- Win rate: {p['stats'].get('win_rate', 0):.1%}")
                lines.append(f"- Sample size: {p['stats'].get('sample_size', 0)}")
        return lines

    def _format_debrief_context(self, data: dict[str, Any]) -> list[str]:
        """Format Debrief page context."""
        lines = []
        if "today_summary" in data:
            ts = data["today_summary"]
            lines.append("### Today's Summary")
            lines.append(f"- Total trades: {ts.get('total_trades', 0)}")
            lines.append(f"- Net P&L: ${ts.get('net_pnl', 0):,.2f}")
        if "selected_conversation" in data:
            lines.append(f"### Viewing conversation from: {data['selected_conversation']}")
        return lines

    def _format_system_context(self, data: dict[str, Any]) -> list[str]:
        """Format System page context."""
        lines = []
        if "health" in data:
            h = data["health"]
            lines.append("### System Health")
            lines.append(f"- Status: {h.get('status', 'unknown')}")
            lines.append(f"- Uptime: {h.get('uptime', 'N/A')}")
        if "connections" in data:
            lines.append("### Connection States")
            for conn, state in data["connections"].items():
                lines.append(f"- {conn}: {state}")
        return lines

    def build_conversation_messages(
        self,
        history: list[dict[str, Any]],
        user_message: str,
        system: str,
        page_context: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Assemble the final message list with history truncation.

        Args:
            history: Previous conversation messages.
            user_message: The new user message.
            system: The system prompt.
            page_context: The page-specific context.

        Returns:
            Tuple of (system_prompt_with_context, messages_list).
        """
        # Combine system prompt with page context
        full_system = f"{system}\n\n{page_context}"

        # Apply history truncation
        truncated_history = self._truncate_history(history)

        # Build message list
        messages = list(truncated_history)
        messages.append({"role": "user", "content": user_message})

        return (full_system, messages)

    def _truncate_history(
        self,
        history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Truncate history to fit within budgets.

        Applies two constraints:
        1. Maximum number of messages (max_history_messages)
        2. Maximum token count (history_token_budget)

        Keeps the most recent messages that fit.

        Args:
            history: Full conversation history.

        Returns:
            Truncated history list.
        """
        max_messages = self._config.max_history_messages
        token_budget = self._config.history_token_budget

        # First, apply message count limit
        if len(history) > max_messages:
            history = history[-max_messages:]

        # Then, apply token budget (most recent first)
        result: list[dict[str, Any]] = []
        total_tokens = 0

        for msg in reversed(history):
            content = msg.get("content", "")
            if isinstance(content, str):
                msg_tokens = estimate_tokens(content)
            else:
                # Handle list content (tool use etc)
                msg_tokens = estimate_tokens(str(content))

            if total_tokens + msg_tokens > token_budget:
                break

            result.insert(0, msg)
            total_tokens += msg_tokens

        return result

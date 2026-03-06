"""AIService — Main orchestration class for the AI Copilot.

Ties all AI components together and provides the primary interface for:
- Chat handling with tool use
- Action approval and execution
- Insight and summary generation
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from zoneinfo import ZoneInfo

from argus.ai.actions import ActionManager, ActionProposal
from argus.ai.executors import ExecutionError, ExecutorRegistry
from argus.ai.summary import DailySummaryGenerator
from argus.ai.tools import ARGUS_TOOLS, requires_approval

if TYPE_CHECKING:
    from argus.ai.cache import ResponseCache
    from argus.ai.client import ClaudeClient
    from argus.ai.config import AIConfig
    from argus.ai.context import SystemContextBuilder
    from argus.ai.conversations import ConversationManager
    from argus.ai.prompts import PromptManager
    from argus.ai.usage import UsageTracker
    from argus.api.dependencies import AppState

logger = logging.getLogger(__name__)


class AIService:
    """Main orchestration class for the AI Copilot.

    Coordinates all AI components to provide:
    - Chat conversations with tool use
    - Action proposal management (create, approve, reject, execute)
    - Dashboard insights
    - Daily summaries

    Usage:
        service = AIService(
            client=claude_client,
            prompt_manager=prompt_manager,
            context_builder=context_builder,
            conversation_manager=conversation_manager,
            usage_tracker=usage_tracker,
            action_manager=action_manager,
            executor_registry=executor_registry,
            summary_generator=summary_generator,
            cache=response_cache,
        )

        result = await service.handle_chat(
            conversation_id="...",
            message="How is the portfolio doing?",
            page="Dashboard",
            page_context={},
            app_state=app_state,
        )
    """

    def __init__(
        self,
        client: ClaudeClient,
        config: AIConfig,
        prompt_manager: PromptManager,
        context_builder: SystemContextBuilder,
        conversation_manager: ConversationManager,
        usage_tracker: UsageTracker,
        action_manager: ActionManager,
        executor_registry: ExecutorRegistry,
        summary_generator: DailySummaryGenerator,
        cache: ResponseCache,
    ) -> None:
        """Initialize the AI service.

        Args:
            client: ClaudeClient for API calls.
            config: AI configuration.
            prompt_manager: PromptManager for prompt construction.
            context_builder: SystemContextBuilder for context assembly.
            conversation_manager: ConversationManager for chat persistence.
            usage_tracker: UsageTracker for usage recording.
            action_manager: ActionManager for proposal lifecycle.
            executor_registry: ExecutorRegistry for action execution.
            summary_generator: DailySummaryGenerator for summaries/insights.
            cache: ResponseCache for response caching.
        """
        self._client = client
        self._config = config
        self._prompt_manager = prompt_manager
        self._context_builder = context_builder
        self._conversation_manager = conversation_manager
        self._usage_tracker = usage_tracker
        self._action_manager = action_manager
        self._executor_registry = executor_registry
        self._summary_generator = summary_generator
        self._cache = cache

    @property
    def enabled(self) -> bool:
        """Check if AI features are enabled."""
        return self._client.enabled

    async def handle_chat(
        self,
        conversation_id: str | None,
        message: str,
        page: str,
        page_context: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Handle a chat message with tool use support.

        Args:
            conversation_id: Existing conversation ID, or None to create new.
            message: User message content.
            page: Current page identifier.
            page_context: Page-specific context data.
            app_state: Application state.

        Returns:
            Dict with:
            - conversation_id: The conversation ID
            - message_id: The assistant message ID
            - content: The text response
            - tool_use: List of tool use blocks (if any)
            - proposals: List of created proposals (if any)
        """
        if not self.enabled:
            return {
                "conversation_id": conversation_id,
                "message_id": None,
                "content": "AI features are not available.",
                "tool_use": None,
                "proposals": [],
            }

        # Get or create conversation
        if conversation_id is None:
            et_tz = ZoneInfo("America/New_York")
            today_str = datetime.now(et_tz).strftime("%Y-%m-%d")
            tag = self._get_page_tag(page)
            conversation = await self._conversation_manager.create_conversation(today_str, tag)
            conversation_id = conversation["id"]
        else:
            conversation = await self._conversation_manager.get_conversation(conversation_id)
            if conversation is None:
                return {
                    "conversation_id": conversation_id,
                    "message_id": None,
                    "content": f"Conversation {conversation_id} not found.",
                    "tool_use": None,
                    "proposals": [],
                    "error": "conversation_not_found",
                }

        # Build context
        context = await self._context_builder.build_context(page, page_context, app_state)

        # Get conversation history
        history_messages = await self._conversation_manager.get_messages(conversation_id, limit=50)
        history = [{"role": msg["role"], "content": msg["content"]} for msg in history_messages]

        # Build prompts
        strategies_info = self._build_strategies_info(app_state)
        system_config = self._build_system_config(app_state)
        system_prompt = self._prompt_manager.build_system_prompt(strategies_info, system_config)
        formatted_page_context = self._prompt_manager.build_page_context(
            page, context.get("page_context", {})
        )

        # Assemble messages
        full_system, messages = self._prompt_manager.build_conversation_messages(
            history, message, system_prompt, formatted_page_context
        )

        # Persist user message
        await self._conversation_manager.add_message(
            conversation_id,
            "user",
            message,
            page_context=page_context,
        )

        # Call Claude API
        response, usage_record = await self._client.send_message(
            messages, full_system, tools=ARGUS_TOOLS, stream=False
        )

        # Check for error
        if response.get("type") == "error":
            return {
                "conversation_id": conversation_id,
                "message_id": None,
                "content": f"AI error: {response.get('message', 'Unknown error')}",
                "tool_use": None,
                "proposals": [],
                "error": response.get("error"),
            }

        # Extract content and tool_use blocks
        content_parts: list[str] = []
        tool_use_blocks: list[dict[str, Any]] = []

        for block in response.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_use_blocks.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input"),
                })

        full_content = "\n".join(content_parts)
        proposals: list[dict[str, Any]] = []

        # Handle tool_use blocks
        if tool_use_blocks:
            tool_results: list[dict[str, Any]] = []

            # Capture current state for re-check later
            current_regime = None
            current_equity = None
            if app_state.orchestrator is not None:
                current_regime = str(app_state.orchestrator.current_regime)
            if app_state.broker is not None:
                account = await app_state.broker.get_account()
                if account is not None:
                    current_equity = account.equity

            for tu in tool_use_blocks:
                tool_name = tu.get("name", "")
                tool_input = tu.get("input", {})
                tool_use_id = tu.get("id", "")

                # Add state snapshot to tool_input for re-check
                tool_input_with_state = dict(tool_input)
                if current_regime is not None:
                    tool_input_with_state["_regime_at_creation"] = current_regime
                if current_equity is not None:
                    tool_input_with_state["_equity_at_creation"] = current_equity

                executor = self._executor_registry.get(tool_name)

                if executor is None:
                    result_content = f"Unknown tool: {tool_name}"
                    tu["proposal_id"] = None
                elif not executor.requires_approval:
                    # Execute immediately (e.g., generate_report)
                    valid, error = await executor.validate(tool_input)
                    if not valid:
                        result_content = f"Validation failed: {error}"
                        tu["proposal_id"] = None
                    else:
                        try:
                            # Create a minimal proposal for execution
                            proposal = ActionProposal(
                                id="immediate",
                                conversation_id=conversation_id,
                                message_id=None,
                                tool_name=tool_name,
                                tool_use_id=tool_use_id,
                                tool_input=tool_input,
                                status="approved",
                                result=None,
                                failure_reason=None,
                                created_at=datetime.now(ZoneInfo("UTC")),
                                expires_at=datetime.now(ZoneInfo("UTC")),
                            )
                            result = await executor.execute(proposal, app_state)
                            result_content = f"Executed: {result}"
                            tu["result"] = result
                        except ExecutionError as e:
                            result_content = f"Execution failed: {e}"
                        tu["proposal_id"] = None
                elif requires_approval(tool_name):
                    # Validate first
                    valid, error = await executor.validate(tool_input_with_state)
                    if not valid:
                        result_content = f"Validation failed: {error}"
                        tu["proposal_id"] = None
                    else:
                        # Create proposal
                        proposal = await self._action_manager.create_proposal(
                            conversation_id=conversation_id,
                            message_id=None,
                            tool_name=tool_name,
                            tool_use_id=tool_use_id,
                            tool_input=tool_input_with_state,
                        )
                        result_content = (
                            f"Proposal #{proposal.id[:8]} created. Awaiting operator approval."
                        )
                        tu["proposal_id"] = proposal.id
                        proposals.append(proposal.to_dict())
                else:
                    result_content = "Tool does not require approval but no executor found."
                    tu["proposal_id"] = None

                tool_results.append({"tool_use_id": tool_use_id, "content": result_content})

            # Continue conversation with tool results
            if tool_results:
                messages.append({"role": "assistant", "content": response.get("content", [])})
                continuation_response, continuation_usage = (
                    await self._client.send_with_tool_results(
                        messages, full_system, ARGUS_TOOLS, tool_results
                    )
                )

                # Merge usage
                usage_record = type(usage_record)(
                    input_tokens=usage_record.input_tokens + continuation_usage.input_tokens,
                    output_tokens=usage_record.output_tokens + continuation_usage.output_tokens,
                    model=usage_record.model,
                    estimated_cost_usd=usage_record.estimated_cost_usd
                    + continuation_usage.estimated_cost_usd,
                )

                # Extract continuation content
                if continuation_response.get("type") != "error":
                    for block in continuation_response.get("content", []):
                        if block.get("type") == "text":
                            content_parts.append(block.get("text", ""))
                    full_content = "\n".join(content_parts)

        # Persist assistant message
        assistant_msg = await self._conversation_manager.add_message(
            conversation_id,
            "assistant",
            full_content,
            tool_use_data=tool_use_blocks if tool_use_blocks else None,
        )

        # Record usage
        await self._usage_tracker.record_usage(
            conversation_id,
            usage_record.input_tokens,
            usage_record.output_tokens,
            usage_record.model,
            usage_record.estimated_cost_usd,
        )

        return {
            "conversation_id": conversation_id,
            "message_id": assistant_msg["id"],
            "content": full_content,
            "tool_use": tool_use_blocks if tool_use_blocks else None,
            "proposals": proposals,
        }

    async def handle_approve(
        self,
        proposal_id: str,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Approve and execute a proposal.

        Args:
            proposal_id: The proposal ID to approve.
            app_state: Application state.

        Returns:
            Dict with:
            - proposal: The updated proposal
            - executed: Whether execution succeeded
            - result: Execution result (if successful)
            - error: Error message (if failed)
        """
        # Get and approve the proposal
        proposal = await self._action_manager.approve_proposal(proposal_id)

        # Get executor
        executor = self._executor_registry.get(proposal.tool_name)
        if executor is None:
            await self._action_manager.fail_proposal(
                proposal_id, f"No executor for tool: {proposal.tool_name}"
            )
            updated_proposal = await self._action_manager.get_proposal(proposal_id)
            return {
                "proposal": updated_proposal.to_dict() if updated_proposal else None,
                "executed": False,
                "result": None,
                "error": f"No executor for tool: {proposal.tool_name}",
            }

        # Run pre-execution re-check
        passed, reason = await executor.pre_execution_recheck(proposal, app_state)
        if not passed:
            await self._action_manager.fail_proposal(proposal_id, reason)
            updated_proposal = await self._action_manager.get_proposal(proposal_id)
            return {
                "proposal": updated_proposal.to_dict() if updated_proposal else None,
                "executed": False,
                "result": None,
                "error": reason,
            }

        # Execute
        try:
            result = await executor.execute(proposal, app_state)
            await self._action_manager.execute_proposal(proposal_id, result)
            updated_proposal = await self._action_manager.get_proposal(proposal_id)
            return {
                "proposal": updated_proposal.to_dict() if updated_proposal else None,
                "executed": True,
                "result": result,
                "error": None,
            }
        except ExecutionError as e:
            await self._action_manager.fail_proposal(proposal_id, str(e))
            updated_proposal = await self._action_manager.get_proposal(proposal_id)
            return {
                "proposal": updated_proposal.to_dict() if updated_proposal else None,
                "executed": False,
                "result": None,
                "error": str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error executing proposal {proposal_id}")
            await self._action_manager.fail_proposal(proposal_id, f"Unexpected error: {e}")
            updated_proposal = await self._action_manager.get_proposal(proposal_id)
            return {
                "proposal": updated_proposal.to_dict() if updated_proposal else None,
                "executed": False,
                "result": None,
                "error": f"Unexpected error: {e}",
            }

    async def handle_reject(
        self,
        proposal_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Reject a proposal.

        Args:
            proposal_id: The proposal ID to reject.
            reason: Optional rejection reason.

        Returns:
            Dict with:
            - proposal: The updated proposal
            - status: "rejected"
        """
        proposal = await self._action_manager.reject_proposal(proposal_id, reason)
        return {
            "proposal": proposal.to_dict(),
            "status": "rejected",
        }

    async def get_insight(self, app_state: AppState) -> dict[str, Any]:
        """Generate a Dashboard insight.

        Args:
            app_state: Application state.

        Returns:
            Dict with:
            - insight: The insight text
            - generated_at: Timestamp
            - cached: Whether result was from cache
        """
        if not self.enabled:
            return {
                "insight": None,
                "generated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "cached": False,
                "message": "AI not available",
            }

        # Check cache
        cache_key = "insight"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return {
                "insight": cached.get("insight"),
                "generated_at": cached.get("generated_at", datetime.now(ZoneInfo("UTC")).isoformat()),
                "cached": True,
            }

        # Generate insight
        insight = await self._summary_generator.generate_insight(app_state)
        generated_at = datetime.now(ZoneInfo("UTC")).isoformat()

        # Cache result
        await self._cache.set(cache_key, {"insight": insight, "generated_at": generated_at})

        return {
            "insight": insight,
            "generated_at": generated_at,
            "cached": False,
        }

    async def generate_daily_summary(
        self,
        date: str,
        app_state: AppState,
    ) -> dict[str, Any]:
        """Generate a daily trading summary.

        Args:
            date: Date in YYYY-MM-DD format.
            app_state: Application state.

        Returns:
            Dict with:
            - summary: The summary text
            - date: The date
            - generated_at: Timestamp
        """
        if not self.enabled:
            return {
                "summary": None,
                "date": date,
                "generated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "message": "AI not available",
            }

        summary = await self._summary_generator.generate(date, app_state)
        return {
            "summary": summary,
            "date": date,
            "generated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }

    def _get_page_tag(self, page: str) -> str:
        """Map page to conversation tag."""
        tag_map = {
            "Dashboard": "session",
            "Trades": "session",
            "Performance": "research",
            "Orchestrator": "session",
            "PatternLibrary": "research",
            "Debrief": "debrief",
            "System": "session",
        }
        return tag_map.get(page, "general")

    def _build_strategies_info(self, app_state: AppState) -> list[dict[str, Any]] | None:
        """Build strategies info for system prompt."""
        if not app_state.strategies:
            return None

        strategies_info: list[dict[str, Any]] = []
        for strategy_id, strategy in app_state.strategies.items():
            config = getattr(strategy, "_config", None)
            if config is None:
                continue

            info: dict[str, Any] = {"name": getattr(config, "name", strategy_id)}

            time_window = getattr(config, "time_window_display", None)
            if time_window:
                info["window"] = time_window

            desc = getattr(config, "description_short", None)
            if desc:
                info["mechanic"] = desc[:100]

            strategies_info.append(info)

        return strategies_info if strategies_info else None

    def _build_system_config(self, app_state: AppState) -> dict[str, Any] | None:
        """Build system config info for system prompt."""
        if app_state.config is None:
            return None

        config_info: dict[str, Any] = {}

        if app_state.risk_manager is not None:
            risk_config = getattr(app_state.risk_manager, "_config", None)
            if risk_config is not None:
                account_config = getattr(risk_config, "account", None)
                if account_config is not None:
                    config_info["risk_limits"] = {
                        "daily_loss_limit_pct": getattr(
                            account_config, "daily_loss_limit_pct", 0.03
                        ),
                        "max_concurrent_positions": getattr(
                            account_config, "max_concurrent_positions", 5
                        ),
                    }

        if app_state.orchestrator is not None:
            regime = getattr(app_state.orchestrator, "current_regime", None)
            if regime is not None:
                config_info["regime"] = str(regime)

        return config_info if config_info else None

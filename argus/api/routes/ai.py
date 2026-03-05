"""AI routes for the Command Center API.

Provides endpoints for AI chat, conversation history, usage tracking,
and context inspection. All endpoints are JWT-protected.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from argus.ai.tools import ARGUS_TOOLS, requires_approval
from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()


# Page tag mapping for conversation creation
PAGE_TAG_MAP: dict[str, str] = {
    "Dashboard": "session",
    "Trades": "session",
    "Performance": "research",
    "Orchestrator": "session",
    "PatternLibrary": "research",
    "Debrief": "debrief",
    "System": "session",
}


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    conversation_id: str | None = None
    message: str
    page: str
    page_context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    conversation_id: str
    message_id: str
    content: str
    tool_use: list[dict[str, Any]] | None = None


class ConversationSummary(BaseModel):
    """Summary of a conversation for list endpoint."""

    id: str
    date: str
    tag: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationsListResponse(BaseModel):
    """Response body for GET /conversations."""

    conversations: list[ConversationSummary]
    total: int


class MessageResponse(BaseModel):
    """A message in a conversation."""

    id: str
    conversation_id: str
    role: str
    content: str
    tool_use_data: dict[str, Any] | None = None
    page_context: dict[str, Any] | None = None
    is_complete: bool
    created_at: str


class ConversationDetailResponse(BaseModel):
    """Response body for GET /conversations/{conversation_id}."""

    conversation: ConversationSummary
    messages: list[MessageResponse]


class UsageStatsResponse(BaseModel):
    """Usage statistics for a period."""

    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    call_count: int


class AIStatusResponse(BaseModel):
    """Response body for GET /status."""

    enabled: bool
    model: str | None
    usage: dict[str, Any] | None = None


class AIUsageResponse(BaseModel):
    """Response body for GET /usage."""

    period: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    call_count: int
    daily_breakdown: list[dict[str, Any]] | None = None


# --- Helper Functions ---


def _ensure_ai_enabled(state: AppState) -> None:
    """Raise 503 if AI services are not available.

    Args:
        state: The application state.

    Raises:
        HTTPException 503: If AI is disabled or services are not initialized.
    """
    if state.ai_client is None or not state.ai_client.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not available",
        )


# --- Endpoints ---


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    request: ChatRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ChatResponse:
    """Non-streaming chat endpoint.

    Creates or continues a conversation with the AI copilot.
    If conversation_id is null, creates a new conversation for today.

    Returns the assistant's response with any tool_use blocks.
    """
    _ensure_ai_enabled(state)

    if state.conversation_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation service not available",
        )

    if state.prompt_manager is None or state.context_builder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI prompt services not available",
        )

    # Get or create conversation
    conversation_id = request.conversation_id
    if conversation_id is None:
        # Create new conversation with tag based on page
        tag = PAGE_TAG_MAP.get(request.page, "general")
        today_str = date.today().isoformat()
        conversation = await state.conversation_manager.create_conversation(today_str, tag)
        conversation_id = conversation["id"]
    else:
        # Verify conversation exists
        conversation = await state.conversation_manager.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )

    # Build context
    context = await state.context_builder.build_context(
        request.page,
        request.page_context,
        state,
    )

    # Get conversation history
    history_messages = await state.conversation_manager.get_messages(conversation_id, limit=50)
    history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history_messages
    ]

    # Build system prompt
    strategies_info = _build_strategies_info(state)
    system_config = _build_system_config_info(state)
    system_prompt = state.prompt_manager.build_system_prompt(strategies_info, system_config)
    page_context = state.prompt_manager.build_page_context(request.page, context.get("page_context", {}))

    # Assemble messages
    full_system, messages = state.prompt_manager.build_conversation_messages(
        history,
        request.message,
        system_prompt,
        page_context,
    )

    # Persist user message
    user_msg = await state.conversation_manager.add_message(
        conversation_id,
        "user",
        request.message,
        page_context=request.page_context,
    )

    # Call Claude API
    response, usage_record = await state.ai_client.send_message(
        messages,
        full_system,
        tools=ARGUS_TOOLS,
        stream=False,
    )

    # Check for error response
    if response.get("type") == "error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.get("message", "AI service error"),
        )

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

    # If tool_use blocks are present, handle them
    if tool_use_blocks:
        # Create tool results
        tool_results: list[dict[str, Any]] = []
        for tu in tool_use_blocks:
            tool_name = tu.get("name", "")
            if tool_name == "generate_report":
                result_content = "Report generation queued."
            else:
                # TODO(Session 3a): Wire ActionManager here
                result_content = "Proposal created. Awaiting operator approval."

            tool_results.append({
                "tool_use_id": tu["id"],
                "content": result_content,
            })

        # Add assistant message with tool_use to messages
        messages.append({
            "role": "assistant",
            "content": response.get("content", []),
        })

        # Continue conversation with tool results
        continuation_response, continuation_usage = await state.ai_client.send_with_tool_results(
            messages,
            full_system,
            ARGUS_TOOLS,
            tool_results,
        )

        # Merge usage
        usage_record = type(usage_record)(
            input_tokens=usage_record.input_tokens + continuation_usage.input_tokens,
            output_tokens=usage_record.output_tokens + continuation_usage.output_tokens,
            model=usage_record.model,
            estimated_cost_usd=usage_record.estimated_cost_usd + continuation_usage.estimated_cost_usd,
        )

        # Extract continuation content
        if continuation_response.get("type") != "error":
            for block in continuation_response.get("content", []):
                if block.get("type") == "text":
                    content_parts.append(block.get("text", ""))

            full_content = "\n".join(content_parts)

    # Persist assistant message
    assistant_msg = await state.conversation_manager.add_message(
        conversation_id,
        "assistant",
        full_content,
        tool_use_data=tool_use_blocks if tool_use_blocks else None,
    )

    # Record usage
    if state.usage_tracker is not None:
        await state.usage_tracker.record_usage(
            conversation_id,
            usage_record.input_tokens,
            usage_record.output_tokens,
            usage_record.model,
            usage_record.estimated_cost_usd,
        )

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=assistant_msg["id"],
        content=full_content,
        tool_use=tool_use_blocks if tool_use_blocks else None,
    )


@router.get("/conversations", response_model=ConversationsListResponse)
async def list_conversations(
    date_from: str | None = None,
    date_to: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ConversationsListResponse:
    """List conversations with optional filters.

    Query params:
    - date_from: Start date filter (YYYY-MM-DD)
    - date_to: End date filter (YYYY-MM-DD)
    - tag: Filter by conversation tag
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    if state.conversation_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation service not available",
        )

    conversations = await state.conversation_manager.list_conversations(
        date_from=date_from,
        date_to=date_to,
        tag=tag,
        limit=limit,
        offset=offset,
    )

    # Get total count (simple approach: query without pagination)
    all_conversations = await state.conversation_manager.list_conversations(
        date_from=date_from,
        date_to=date_to,
        tag=tag,
        limit=1000,  # Upper bound
        offset=0,
    )
    total = len(all_conversations)

    return ConversationsListResponse(
        conversations=[
            ConversationSummary(
                id=c["id"],
                date=c["date"],
                tag=c["tag"],
                title=c["title"],
                message_count=c["message_count"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
            for c in conversations
        ],
        total=total,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ConversationDetailResponse:
    """Get a conversation with its messages.

    Messages are returned oldest-first (chronological order).
    """
    if state.conversation_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation service not available",
        )

    conversation = await state.conversation_manager.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    messages = await state.conversation_manager.get_messages(
        conversation_id,
        limit=limit,
        offset=offset,
    )

    return ConversationDetailResponse(
        conversation=ConversationSummary(
            id=conversation["id"],
            date=conversation["date"],
            tag=conversation["tag"],
            title=conversation["title"],
            message_count=conversation["message_count"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
        ),
        messages=[
            MessageResponse(
                id=m["id"],
                conversation_id=m["conversation_id"],
                role=m["role"],
                content=m["content"],
                tool_use_data=m["tool_use_data"],
                page_context=m["page_context"],
                is_complete=m["is_complete"],
                created_at=m["created_at"],
            )
            for m in messages
        ],
    )


@router.get("/context/{page}")
async def get_context(
    page: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict[str, Any]:
    """Debug endpoint: inspect the context payload for a given page.

    Useful for debugging context injection and understanding
    what data the AI copilot receives.
    """
    if state.context_builder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI context service not available",
        )

    context = await state.context_builder.build_context(page, {}, state)
    return {
        "page": page,
        "context": context,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> AIStatusResponse:
    """Get AI service status and usage summary.

    Returns enabled state, model identifier, and usage stats
    for today and this month.
    """
    # Check if AI is enabled
    if state.ai_client is None or not state.ai_client.enabled:
        return AIStatusResponse(
            enabled=False,
            model=None,
            usage=None,
        )

    # Get model from config
    model = state.config.ai.model if state.config and state.config.ai else None

    # Get usage summary
    usage: dict[str, Any] | None = None
    if state.usage_tracker is not None:
        try:
            summary = await state.usage_tracker.get_usage_summary()
            usage = {
                "today": summary.get("today", {}),
                "this_month": summary.get("this_month", {}),
                "per_day_average": summary.get("per_day_average", {}).get("estimated_cost_usd", 0.0),
            }
        except Exception as e:
            logger.warning(f"Failed to get usage summary: {e}")

    return AIStatusResponse(
        enabled=True,
        model=model,
        usage=usage,
    )


@router.get("/usage", response_model=AIUsageResponse)
async def get_ai_usage(
    date_str: str | None = None,
    year: int | None = None,
    month: int | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> AIUsageResponse:
    """Get detailed usage statistics.

    Query params:
    - date: Single day in YYYY-MM-DD format
    - year + month: Get monthly usage (e.g., year=2026, month=3)

    If no params provided, returns today's usage.
    """
    if state.usage_tracker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Usage tracking not available",
        )

    if date_str is not None:
        # Daily usage
        usage = await state.usage_tracker.get_daily_usage(date_str)
        return AIUsageResponse(
            period=date_str,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            estimated_cost_usd=usage["estimated_cost_usd"],
            call_count=usage["call_count"],
            daily_breakdown=None,
        )
    elif year is not None and month is not None:
        # Monthly usage
        usage = await state.usage_tracker.get_monthly_usage(year, month)
        return AIUsageResponse(
            period=f"{year:04d}-{month:02d}",
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            estimated_cost_usd=usage["estimated_cost_usd"],
            call_count=usage["call_count"],
            daily_breakdown=usage.get("daily_breakdown"),
        )
    else:
        # Default: today's usage
        today_str = date.today().isoformat()
        usage = await state.usage_tracker.get_daily_usage(today_str)
        return AIUsageResponse(
            period=today_str,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            estimated_cost_usd=usage["estimated_cost_usd"],
            call_count=usage["call_count"],
            daily_breakdown=None,
        )


# --- Helper Functions for Building Context ---


def _build_strategies_info(state: AppState) -> list[dict[str, Any]] | None:
    """Build strategies info for system prompt.

    Args:
        state: Application state.

    Returns:
        List of strategy info dicts, or None if no strategies.
    """
    if not state.strategies:
        return None

    strategies_info: list[dict[str, Any]] = []
    for strategy_id, strategy in state.strategies.items():
        config = getattr(strategy, "_config", None)
        if config is None:
            continue

        info: dict[str, Any] = {
            "name": getattr(config, "name", strategy_id),
        }

        # Add time window if available
        time_window = getattr(config, "time_window_display", None)
        if time_window:
            info["window"] = time_window

        # Add description if available
        desc = getattr(config, "description_short", None)
        if desc:
            info["mechanic"] = desc[:100]  # Truncate for system prompt

        strategies_info.append(info)

    return strategies_info if strategies_info else None


def _build_system_config_info(state: AppState) -> dict[str, Any] | None:
    """Build system config info for system prompt.

    Args:
        state: Application state.

    Returns:
        Config info dict, or None if no config.
    """
    if state.config is None:
        return None

    config_info: dict[str, Any] = {}

    # Risk limits from risk manager config
    if state.risk_manager is not None:
        risk_config = getattr(state.risk_manager, "_config", None)
        if risk_config is not None:
            account_config = getattr(risk_config, "account", None)
            if account_config is not None:
                config_info["risk_limits"] = {
                    "daily_loss_limit_pct": getattr(account_config, "daily_loss_limit_pct", 0.03),
                    "max_concurrent_positions": getattr(account_config, "max_concurrent_positions", 5),
                }

    # Regime from orchestrator
    if state.orchestrator is not None:
        regime = getattr(state.orchestrator, "current_regime", None)
        if regime is not None:
            config_info["regime"] = str(regime)

    return config_info if config_info else None

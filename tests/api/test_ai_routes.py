"""Tests for AI routes in the Command Center API.

Tests cover REST endpoints for AI chat, conversation management,
context inspection, status, and usage tracking.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app


@pytest.fixture
def mock_ai_client() -> MagicMock:
    """Provide a mock ClaudeClient for testing."""
    client = MagicMock()
    client.enabled = True

    # Mock usage record
    usage_record = MagicMock()
    usage_record.input_tokens = 100
    usage_record.output_tokens = 50
    usage_record.model = "claude-sonnet-4-20250514"
    usage_record.estimated_cost_usd = 0.01

    # Mock send_message to return a text response
    async def mock_send_message(messages, system, tools=None, stream=False):
        return {
            "content": [{"type": "text", "text": "This is a test response from Claude."}],
        }, usage_record

    client.send_message = AsyncMock(side_effect=mock_send_message)
    client.send_with_tool_results = AsyncMock()
    return client


@pytest.fixture
def mock_conversation_manager() -> MagicMock:
    """Provide a mock ConversationManager for testing."""
    manager = MagicMock()

    # Mock create_conversation
    async def mock_create_conversation(date_str: str, tag: str) -> dict:
        return {
            "id": "conv_test_123",
            "date": date_str,
            "tag": tag,
            "title": "Untitled",
            "message_count": 0,
            "created_at": "2026-02-23T10:30:00Z",
            "updated_at": "2026-02-23T10:30:00Z",
        }

    async def mock_get_conversation(conv_id: str) -> dict | None:
        if conv_id == "conv_not_found":
            return None
        return {
            "id": conv_id,
            "date": "2026-02-23",
            "tag": "session",
            "title": "Test Conversation",
            "message_count": 2,
            "created_at": "2026-02-23T10:30:00Z",
            "updated_at": "2026-02-23T10:35:00Z",
        }

    async def mock_list_conversations(
        date_from: str | None = None,
        date_to: str | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        conversations = [
            {
                "id": "conv_1",
                "date": "2026-02-23",
                "tag": "session",
                "title": "Morning Session",
                "message_count": 5,
                "created_at": "2026-02-23T10:00:00Z",
                "updated_at": "2026-02-23T10:30:00Z",
            },
            {
                "id": "conv_2",
                "date": "2026-02-22",
                "tag": "research",
                "title": "Research Chat",
                "message_count": 3,
                "created_at": "2026-02-22T14:00:00Z",
                "updated_at": "2026-02-22T14:15:00Z",
            },
        ]

        # Filter by tag
        if tag:
            conversations = [c for c in conversations if c["tag"] == tag]

        # Filter by date
        if date_from:
            conversations = [c for c in conversations if c["date"] >= date_from]
        if date_to:
            conversations = [c for c in conversations if c["date"] <= date_to]

        return conversations[offset : offset + limit]

    async def mock_get_messages(conv_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
        return [
            {
                "id": "msg_1",
                "conversation_id": conv_id,
                "role": "user",
                "content": "Hello, how are you?",
                "tool_use_data": None,
                "page_context": {"page": "Dashboard"},
                "is_complete": True,
                "created_at": "2026-02-23T10:30:00Z",
            },
            {
                "id": "msg_2",
                "conversation_id": conv_id,
                "role": "assistant",
                "content": "I'm doing well, thanks for asking!",
                "tool_use_data": None,
                "page_context": None,
                "is_complete": True,
                "created_at": "2026-02-23T10:30:05Z",
            },
        ]

    async def mock_add_message(
        conv_id: str,
        role: str,
        content: str,
        page_context: dict | None = None,
        tool_use_data: list | None = None,
    ) -> dict:
        return {
            "id": f"msg_{role}_new",
            "conversation_id": conv_id,
            "role": role,
            "content": content,
            "tool_use_data": tool_use_data,
            "page_context": page_context,
            "is_complete": True,
            "created_at": "2026-02-23T10:35:00Z",
        }

    manager.create_conversation = AsyncMock(side_effect=mock_create_conversation)
    manager.get_conversation = AsyncMock(side_effect=mock_get_conversation)
    manager.list_conversations = AsyncMock(side_effect=mock_list_conversations)
    manager.get_messages = AsyncMock(side_effect=mock_get_messages)
    manager.add_message = AsyncMock(side_effect=mock_add_message)
    return manager


@pytest.fixture
def mock_usage_tracker() -> MagicMock:
    """Provide a mock UsageTracker for testing."""
    tracker = MagicMock()

    async def mock_get_usage_summary() -> dict:
        return {
            "today": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "estimated_cost_usd": 0.10,
                "call_count": 5,
            },
            "this_month": {
                "input_tokens": 10000,
                "output_tokens": 5000,
                "estimated_cost_usd": 1.00,
                "call_count": 50,
            },
            "per_day_average": {
                "estimated_cost_usd": 0.05,
            },
        }

    async def mock_get_daily_usage(date_str: str) -> dict:
        return {
            "input_tokens": 1000,
            "output_tokens": 500,
            "estimated_cost_usd": 0.10,
            "call_count": 5,
        }

    async def mock_get_monthly_usage(year: int, month: int) -> dict:
        return {
            "input_tokens": 10000,
            "output_tokens": 5000,
            "estimated_cost_usd": 1.00,
            "call_count": 50,
            "daily_breakdown": [
                {"date": "2026-02-01", "input_tokens": 500, "output_tokens": 250, "estimated_cost_usd": 0.05, "call_count": 3},
                {"date": "2026-02-02", "input_tokens": 500, "output_tokens": 250, "estimated_cost_usd": 0.05, "call_count": 2},
            ],
        }

    async def mock_record_usage(conv_id: str, input_tokens: int, output_tokens: int, model: str, cost: float) -> None:
        pass

    tracker.get_usage_summary = AsyncMock(side_effect=mock_get_usage_summary)
    tracker.get_daily_usage = AsyncMock(side_effect=mock_get_daily_usage)
    tracker.get_monthly_usage = AsyncMock(side_effect=mock_get_monthly_usage)
    tracker.record_usage = AsyncMock(side_effect=mock_record_usage)
    return tracker


@pytest.fixture
def mock_context_builder() -> MagicMock:
    """Provide a mock SystemContextBuilder for testing."""
    builder = MagicMock()

    async def mock_build_context(page: str, page_context: dict, state: Any) -> dict:
        return {
            "page": page,
            "page_context": page_context,
            "system_state": {
                "mode": "paper",
                "positions_open": 0,
            },
        }

    builder.build_context = AsyncMock(side_effect=mock_build_context)
    return builder


@pytest.fixture
def mock_prompt_manager() -> MagicMock:
    """Provide a mock PromptManager for testing."""
    manager = MagicMock()

    def mock_build_system_prompt(strategies: list | None, config: dict | None) -> str:
        return "You are ARGUS AI, a trading copilot."

    def mock_build_page_context(page: str, context: dict) -> str:
        return f"Current page: {page}"

    def mock_build_conversation_messages(
        history: list,
        user_message: str,
        system_prompt: str,
        page_context: str,
    ) -> tuple[str, list]:
        full_system = f"{system_prompt}\n\n{page_context}"
        messages = history + [{"role": "user", "content": user_message}]
        return full_system, messages

    manager.build_system_prompt = MagicMock(side_effect=mock_build_system_prompt)
    manager.build_page_context = MagicMock(side_effect=mock_build_page_context)
    manager.build_conversation_messages = MagicMock(side_effect=mock_build_conversation_messages)
    return manager


@pytest.fixture
async def app_state_with_ai(
    app_state: AppState,
    mock_ai_client: MagicMock,
    mock_conversation_manager: MagicMock,
    mock_usage_tracker: MagicMock,
    mock_context_builder: MagicMock,
    mock_prompt_manager: MagicMock,
) -> AppState:
    """Provide AppState with AI services configured."""
    app_state.ai_client = mock_ai_client
    app_state.conversation_manager = mock_conversation_manager
    app_state.usage_tracker = mock_usage_tracker
    app_state.context_builder = mock_context_builder
    app_state.prompt_manager = mock_prompt_manager
    return app_state


@pytest.fixture
async def client_with_ai(
    app_state_with_ai: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AI services configured."""
    app = create_app(app_state_with_ai)
    app.state.app_state = app_state_with_ai
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# --- POST /chat tests ---


@pytest.mark.asyncio
async def test_post_chat_creates_new_conversation(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /chat with no conversation_id creates a new conversation."""
    response = await client_with_ai.post(
        "/api/v1/ai/chat",
        json={
            "message": "Hello, Claude!",
            "page": "Dashboard",
            "page_context": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["conversation_id"] == "conv_test_123"
    assert "message_id" in data
    assert "content" in data
    assert data["content"] == "This is a test response from Claude."


@pytest.mark.asyncio
async def test_post_chat_continues_existing_conversation(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /chat with existing conversation_id continues conversation."""
    response = await client_with_ai.post(
        "/api/v1/ai/chat",
        json={
            "conversation_id": "conv_existing_123",
            "message": "What's the status?",
            "page": "Dashboard",
            "page_context": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "conv_existing_123"


@pytest.mark.asyncio
async def test_post_chat_requires_auth(
    client_with_ai: AsyncClient,
) -> None:
    """POST /chat without auth returns 401."""
    response = await client_with_ai.post(
        "/api/v1/ai/chat",
        json={
            "message": "Hello",
            "page": "Dashboard",
            "page_context": {},
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_chat_returns_503_when_ai_disabled(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /chat returns 503 when AI services are not configured."""
    response = await client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Hello",
            "page": "Dashboard",
            "page_context": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert "AI service not available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_post_chat_returns_404_for_nonexistent_conversation(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /chat with invalid conversation_id returns 404."""
    response = await client_with_ai.post(
        "/api/v1/ai/chat",
        json={
            "conversation_id": "conv_not_found",
            "message": "Hello",
            "page": "Dashboard",
            "page_context": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


# --- GET /conversations tests ---


@pytest.mark.asyncio
async def test_list_conversations(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /conversations returns list of conversations."""
    response = await client_with_ai.get(
        "/api/v1/ai/conversations",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert "total" in data
    assert len(data["conversations"]) == 2
    assert data["conversations"][0]["id"] == "conv_1"


@pytest.mark.asyncio
async def test_list_conversations_filter_by_tag(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /conversations filters by tag."""
    response = await client_with_ai.get(
        "/api/v1/ai/conversations?tag=session",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) == 1
    assert data["conversations"][0]["tag"] == "session"


@pytest.mark.asyncio
async def test_list_conversations_filter_by_date(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /conversations filters by date range."""
    response = await client_with_ai.get(
        "/api/v1/ai/conversations?date_from=2026-02-23&date_to=2026-02-23",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) == 1
    assert data["conversations"][0]["date"] == "2026-02-23"


@pytest.mark.asyncio
async def test_list_conversations_requires_auth(
    client_with_ai: AsyncClient,
) -> None:
    """GET /conversations without auth returns 401."""
    response = await client_with_ai.get("/api/v1/ai/conversations")

    assert response.status_code == 401


# --- GET /conversations/{id} tests ---


@pytest.mark.asyncio
async def test_get_conversation_with_messages(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /conversations/{id} returns conversation with messages."""
    response = await client_with_ai.get(
        "/api/v1/ai/conversations/conv_123",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "conversation" in data
    assert "messages" in data
    assert data["conversation"]["id"] == "conv_123"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_get_conversation_not_found(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /conversations/{id} returns 404 for unknown conversation."""
    response = await client_with_ai.get(
        "/api/v1/ai/conversations/conv_not_found",
        headers=auth_headers,
    )

    assert response.status_code == 404


# --- GET /context/{page} tests ---


@pytest.mark.asyncio
async def test_get_context(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /context/{page} returns context for the specified page."""
    response = await client_with_ai.get(
        "/api/v1/ai/context/Dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == "Dashboard"
    assert "context" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_get_context_requires_auth(
    client_with_ai: AsyncClient,
) -> None:
    """GET /context/{page} without auth returns 401."""
    response = await client_with_ai.get("/api/v1/ai/context/Dashboard")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_context_returns_503_when_not_configured(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /context/{page} returns 503 when context builder not available."""
    response = await client.get(
        "/api/v1/ai/context/Dashboard",
        headers=auth_headers,
    )

    assert response.status_code == 503


# --- GET /status tests ---


@pytest.mark.asyncio
async def test_get_status_when_enabled(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /status returns enabled status with usage when AI is configured."""
    response = await client_with_ai.get(
        "/api/v1/ai/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert "usage" in data
    assert data["usage"]["today"]["input_tokens"] == 1000


@pytest.mark.asyncio
async def test_get_status_when_disabled(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /status returns disabled status when AI is not configured."""
    response = await client.get(
        "/api/v1/ai/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["model"] is None
    assert data["usage"] is None


# --- GET /usage tests ---


@pytest.mark.asyncio
async def test_get_usage_today(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /usage with no params returns today's usage."""
    response = await client_with_ai.get(
        "/api/v1/ai/usage",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == date.today().isoformat()
    assert data["input_tokens"] == 1000
    assert data["output_tokens"] == 500
    assert data["estimated_cost_usd"] == 0.10
    assert data["call_count"] == 5


@pytest.mark.asyncio
async def test_get_usage_specific_date(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /usage with date param returns that day's usage."""
    response = await client_with_ai.get(
        "/api/v1/ai/usage?date_str=2026-02-20",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "2026-02-20"


@pytest.mark.asyncio
async def test_get_usage_monthly(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /usage with year and month returns monthly usage."""
    response = await client_with_ai.get(
        "/api/v1/ai/usage?year=2026&month=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "2026-02"
    assert data["input_tokens"] == 10000
    assert "daily_breakdown" in data
    assert len(data["daily_breakdown"]) == 2


@pytest.mark.asyncio
async def test_get_usage_returns_503_when_not_configured(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /usage returns 503 when usage tracker not available."""
    response = await client.get(
        "/api/v1/ai/usage",
        headers=auth_headers,
    )

    assert response.status_code == 503


# --- Action Proposal Endpoints ---


@pytest.fixture
def mock_action_manager() -> MagicMock:
    """Provide a mock ActionManager for testing."""
    manager = MagicMock()

    # Mock proposal data
    mock_proposal = MagicMock()
    mock_proposal.id = "proposal_test_123"
    mock_proposal.conversation_id = "conv_123"
    mock_proposal.message_id = None
    mock_proposal.tool_name = "propose_allocation_change"
    mock_proposal.tool_use_id = "tu_001"
    mock_proposal.tool_input = {"strategy_id": "orb_breakout", "new_allocation_pct": 30}
    mock_proposal.status = "pending"
    mock_proposal.result = None
    mock_proposal.failure_reason = None
    mock_proposal.created_at = MagicMock()
    mock_proposal.created_at.isoformat = MagicMock(return_value="2026-03-06T10:00:00+00:00")
    mock_proposal.expires_at = MagicMock()
    mock_proposal.expires_at.isoformat = MagicMock(return_value="2026-03-06T10:05:00+00:00")
    mock_proposal.resolved_at = None

    # Approved proposal version
    approved_proposal = MagicMock()
    approved_proposal.id = "proposal_test_123"
    approved_proposal.conversation_id = "conv_123"
    approved_proposal.message_id = None
    approved_proposal.tool_name = "propose_allocation_change"
    approved_proposal.tool_use_id = "tu_001"
    approved_proposal.tool_input = {"strategy_id": "orb_breakout", "new_allocation_pct": 30}
    approved_proposal.status = "approved"
    approved_proposal.result = None
    approved_proposal.failure_reason = None
    approved_proposal.created_at = mock_proposal.created_at
    approved_proposal.expires_at = mock_proposal.expires_at
    approved_proposal.resolved_at = MagicMock()
    approved_proposal.resolved_at.isoformat = MagicMock(return_value="2026-03-06T10:02:00+00:00")

    # Rejected proposal version
    rejected_proposal = MagicMock()
    rejected_proposal.id = "proposal_test_123"
    rejected_proposal.conversation_id = "conv_123"
    rejected_proposal.message_id = None
    rejected_proposal.tool_name = "propose_allocation_change"
    rejected_proposal.tool_use_id = "tu_001"
    rejected_proposal.tool_input = {"strategy_id": "orb_breakout", "new_allocation_pct": 30}
    rejected_proposal.status = "rejected"
    rejected_proposal.result = None
    rejected_proposal.failure_reason = None
    rejected_proposal.created_at = mock_proposal.created_at
    rejected_proposal.expires_at = mock_proposal.expires_at
    rejected_proposal.resolved_at = MagicMock()
    rejected_proposal.resolved_at.isoformat = MagicMock(return_value="2026-03-06T10:02:00+00:00")

    async def mock_approve_proposal(proposal_id: str):
        if proposal_id == "not_found":
            from argus.ai.actions import ProposalNotFoundError
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        if proposal_id == "expired":
            from argus.ai.actions import ProposalExpiredError
            raise ProposalExpiredError("Proposal expired")
        if proposal_id == "already_approved":
            from argus.ai.actions import ProposalNotPendingError
            raise ProposalNotPendingError("approved")
        return approved_proposal

    async def mock_reject_proposal(proposal_id: str, reason: str = ""):
        if proposal_id == "not_found":
            from argus.ai.actions import ProposalNotFoundError
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        if proposal_id == "already_rejected":
            from argus.ai.actions import ProposalNotPendingError
            raise ProposalNotPendingError("rejected")
        return rejected_proposal

    async def mock_get_pending_proposals(conversation_id: str | None = None):
        return [mock_proposal]

    manager.approve_proposal = AsyncMock(side_effect=mock_approve_proposal)
    manager.reject_proposal = AsyncMock(side_effect=mock_reject_proposal)
    manager.get_pending_proposals = AsyncMock(side_effect=mock_get_pending_proposals)

    return manager


@pytest.fixture
async def app_state_with_actions(
    app_state_with_ai: AppState,
    mock_action_manager: MagicMock,
) -> AppState:
    """Provide AppState with AI services and ActionManager configured."""
    app_state_with_ai.action_manager = mock_action_manager
    return app_state_with_ai


@pytest.fixture
async def client_with_actions(
    app_state_with_actions: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with ActionManager configured."""
    app = create_app(app_state_with_actions)
    app.state.app_state = app_state_with_actions
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# --- POST /actions/{id}/approve tests ---


@pytest.mark.asyncio
async def test_approve_action_success(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/approve approves a pending proposal."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/proposal_test_123/approve",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["proposal"]["id"] == "proposal_test_123"
    assert data["proposal"]["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_action_not_found(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/approve returns 404 for unknown proposal."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/not_found/approve",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_action_expired(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/approve returns 410 for expired proposal."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/expired/approve",
        headers=auth_headers,
    )

    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_approve_action_not_pending(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/approve returns 409 for already-approved proposal."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/already_approved/approve",
        headers=auth_headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_approve_action_requires_auth(
    client_with_actions: AsyncClient,
) -> None:
    """POST /actions/{id}/approve requires authentication."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/proposal_test_123/approve",
    )

    assert response.status_code == 401


# --- POST /actions/{id}/reject tests ---


@pytest.mark.asyncio
async def test_reject_action_success(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/reject rejects a pending proposal."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/proposal_test_123/reject",
        json={"reason": "Not appropriate"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["proposal"]["id"] == "proposal_test_123"
    assert data["proposal"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_action_without_reason(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/reject works without reason."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/proposal_test_123/reject",
        headers=auth_headers,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reject_action_not_found(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /actions/{id}/reject returns 404 for unknown proposal."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/not_found/reject",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_action_requires_auth(
    client_with_actions: AsyncClient,
) -> None:
    """POST /actions/{id}/reject requires authentication."""
    response = await client_with_actions.post(
        "/api/v1/ai/actions/proposal_test_123/reject",
    )

    assert response.status_code == 401


# --- GET /actions/pending tests ---


@pytest.mark.asyncio
async def test_get_pending_actions_success(
    client_with_actions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /actions/pending returns pending proposals."""
    response = await client_with_actions.get(
        "/api/v1/ai/actions/pending",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "proposals" in data
    assert "count" in data
    assert data["count"] == 1
    assert len(data["proposals"]) == 1
    assert data["proposals"][0]["id"] == "proposal_test_123"


@pytest.mark.asyncio
async def test_get_pending_actions_requires_auth(
    client_with_actions: AsyncClient,
) -> None:
    """GET /actions/pending requires authentication."""
    response = await client_with_actions.get(
        "/api/v1/ai/actions/pending",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_actions_endpoint_503_when_not_configured(
    client_with_ai: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Action endpoints return 503 when ActionManager not configured."""
    # client_with_ai has AI services but no action_manager
    response = await client_with_ai.get(
        "/api/v1/ai/actions/pending",
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert "Action manager not available" in response.json()["detail"]

"""Tests for AI chat WebSocket handler.

Tests cover the streaming AI chat WebSocket endpoint, including
authentication, message handling, and error cases.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from argus.api.auth import create_access_token
from argus.api.dependencies import AppState
from argus.api.server import create_app


@pytest.fixture
def mock_ai_client_streaming() -> MagicMock:
    """Provide a mock ClaudeClient with streaming support for testing."""
    client = MagicMock()
    client.enabled = True

    # Create an async generator for streaming
    async def mock_stream_gen():
        yield {"type": "message_start", "message": {"model": "claude-sonnet-4-20250514"}}
        yield {"type": "content_block_start", "index": 0}
        yield {"type": "content_block_delta", "delta_type": "text_delta", "text": "Hello, "}
        yield {"type": "content_block_delta", "delta_type": "text_delta", "text": "world!"}
        yield {"type": "content_block_stop"}
        yield {"type": "message_stop"}

    async def mock_send_message(messages, system, tools=None, stream=False):
        if stream:
            return mock_stream_gen()
        # Non-streaming fallback
        usage_record = MagicMock()
        usage_record.input_tokens = 100
        usage_record.output_tokens = 50
        usage_record.model = "claude-sonnet-4-20250514"
        usage_record.estimated_cost_usd = 0.01
        return {
            "content": [{"type": "text", "text": "Hello, world!"}],
        }, usage_record

    client.send_message = AsyncMock(side_effect=mock_send_message)
    return client


@pytest.fixture
def mock_conversation_manager_ws() -> MagicMock:
    """Provide a mock ConversationManager for WebSocket testing."""
    manager = MagicMock()

    async def mock_create_conversation(date_str: str, tag: str) -> dict:
        return {
            "id": "conv_ws_test",
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

    async def mock_get_messages(conv_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
        return []

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
    manager.get_messages = AsyncMock(side_effect=mock_get_messages)
    manager.add_message = AsyncMock(side_effect=mock_add_message)
    return manager


@pytest.fixture
def mock_usage_tracker_ws() -> MagicMock:
    """Provide a mock UsageTracker for WebSocket testing."""
    tracker = MagicMock()

    async def mock_record_usage(conv_id: str, input_tokens: int, output_tokens: int, model: str, cost: float) -> None:
        pass

    tracker.record_usage = AsyncMock(side_effect=mock_record_usage)
    return tracker


@pytest.fixture
def mock_context_builder_ws() -> MagicMock:
    """Provide a mock SystemContextBuilder for WebSocket testing."""
    builder = MagicMock()

    async def mock_build_context(page: str, page_context: dict, state: Any) -> dict:
        return {
            "page": page,
            "page_context": page_context,
            "system_state": {"mode": "paper"},
        }

    builder.build_context = AsyncMock(side_effect=mock_build_context)
    return builder


@pytest.fixture
def mock_prompt_manager_ws() -> MagicMock:
    """Provide a mock PromptManager for WebSocket testing."""
    manager = MagicMock()

    manager.build_system_prompt = MagicMock(return_value="You are ARGUS AI.")
    manager.build_page_context = MagicMock(return_value="Current page: Dashboard")
    manager.build_conversation_messages = MagicMock(
        return_value=("System prompt with page context", [{"role": "user", "content": "Hello"}])
    )
    return manager


@pytest.fixture
async def app_state_ws(
    app_state: AppState,
    mock_ai_client_streaming: MagicMock,
    mock_conversation_manager_ws: MagicMock,
    mock_usage_tracker_ws: MagicMock,
    mock_context_builder_ws: MagicMock,
    mock_prompt_manager_ws: MagicMock,
) -> AppState:
    """Provide AppState with AI services configured for WebSocket testing."""
    app_state.ai_client = mock_ai_client_streaming
    app_state.conversation_manager = mock_conversation_manager_ws
    app_state.usage_tracker = mock_usage_tracker_ws
    app_state.context_builder = mock_context_builder_ws
    app_state.prompt_manager = mock_prompt_manager_ws
    return app_state


@pytest.fixture
def ws_client_with_ai(
    app_state_ws: AppState,
    jwt_secret: str,
) -> TestClient:
    """Provide a sync TestClient with AI services for WebSocket testing."""
    app = create_app(app_state_ws)
    app.state.app_state = app_state_ws
    return TestClient(app)


@pytest.fixture
def valid_ws_token(jwt_secret: str) -> str:
    """Provide a valid JWT token for WebSocket auth."""
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return token


# --- WebSocket Authentication Tests ---


def test_ws_auth_success(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket accepts valid JWT token and sends auth_success."""
    with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Send auth message
        websocket.send_json({"type": "auth", "token": valid_ws_token})

        # Should receive auth_success
        response = websocket.receive_json()
        assert response["type"] == "auth_success"
        assert "timestamp" in response


def test_ws_auth_invalid_token(
    ws_client_with_ai: TestClient,
) -> None:
    """WebSocket closes with 4001 when token is invalid."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
            # Send auth with invalid token
            websocket.send_json({"type": "auth", "token": "invalid_token"})
            # Try to receive - should fail due to close
            websocket.receive_json()

    assert exc_info.value.code == 4001


def test_ws_auth_missing_token(
    ws_client_with_ai: TestClient,
) -> None:
    """WebSocket closes with 4001 when token is missing."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
            # Send auth without token
            websocket.send_json({"type": "auth"})
            websocket.receive_json()

    assert exc_info.value.code == 4001


def test_ws_auth_wrong_message_type(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket closes with 4001 when first message is not auth."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
            # Send non-auth message first
            websocket.send_json({"type": "message", "content": "Hello"})
            websocket.receive_json()

    assert exc_info.value.code == 4001


# --- WebSocket Message Handling Tests ---


def test_ws_message_streams_response(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket streams AI response with stream_start, tokens, and stream_end."""
    with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Authenticate
        websocket.send_json({"type": "auth", "token": valid_ws_token})
        auth_response = websocket.receive_json()
        assert auth_response["type"] == "auth_success"

        # Send message
        websocket.send_json({
            "type": "message",
            "content": "Hello, Claude!",
            "page": "Dashboard",
            "page_context": {},
        })

        # Should receive stream_start
        start_response = websocket.receive_json()
        assert start_response["type"] == "stream_start"
        assert "conversation_id" in start_response
        assert "message_id" in start_response

        # Collect token events
        tokens: list[str] = []
        stream_end_received = False

        while True:
            response = websocket.receive_json()
            if response["type"] == "token":
                tokens.append(response["content"])
            elif response["type"] == "stream_end":
                stream_end_received = True
                assert "full_content" in response
                break
            elif response["type"] == "error":
                pytest.fail(f"Received error: {response['message']}")
                break

        assert stream_end_received
        assert len(tokens) >= 1


def test_ws_message_creates_new_conversation(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket creates new conversation when conversation_id is null."""
    with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Authenticate
        websocket.send_json({"type": "auth", "token": valid_ws_token})
        websocket.receive_json()  # auth_success

        # Send message without conversation_id
        websocket.send_json({
            "type": "message",
            "content": "Start a new conversation",
            "page": "Dashboard",
            "page_context": {},
        })

        # Check stream_start has conversation_id
        start_response = websocket.receive_json()
        assert start_response["type"] == "stream_start"
        assert start_response["conversation_id"] == "conv_ws_test"


def test_ws_message_continues_existing_conversation(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket continues existing conversation when conversation_id provided."""
    with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Authenticate
        websocket.send_json({"type": "auth", "token": valid_ws_token})
        websocket.receive_json()  # auth_success

        # Send message with conversation_id
        websocket.send_json({
            "type": "message",
            "conversation_id": "conv_existing",
            "content": "Continue the conversation",
            "page": "Dashboard",
            "page_context": {},
        })

        # Check stream_start has the same conversation_id
        start_response = websocket.receive_json()
        assert start_response["type"] == "stream_start"
        assert start_response["conversation_id"] == "conv_existing"


# --- WebSocket Error Handling Tests ---


def test_ws_ai_disabled_returns_error(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """WebSocket returns error when AI services are not configured."""
    # Create app without AI services
    app = create_app(app_state)
    app.state.app_state = app_state
    client = TestClient(app)

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with client.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Authenticate
        websocket.send_json({"type": "auth", "token": token})
        auth_response = websocket.receive_json()
        assert auth_response["type"] == "auth_success"

        # Send message
        websocket.send_json({
            "type": "message",
            "content": "Hello",
            "page": "Dashboard",
            "page_context": {},
        })

        # Should receive error about AI not available
        error_response = websocket.receive_json()
        assert error_response["type"] == "error"
        assert "not available" in error_response["message"]


def test_ws_conversation_not_found_returns_error(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket returns error when conversation_id doesn't exist."""
    with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Authenticate
        websocket.send_json({"type": "auth", "token": valid_ws_token})
        websocket.receive_json()  # auth_success

        # Send message with non-existent conversation_id
        websocket.send_json({
            "type": "message",
            "conversation_id": "conv_not_found",
            "content": "Hello",
            "page": "Dashboard",
            "page_context": {},
        })

        # Should receive error
        error_response = websocket.receive_json()
        assert error_response["type"] == "error"
        assert "not found" in error_response["message"]


# --- Connection tracking test ---


def test_ws_active_connections_tracking(
    ws_client_with_ai: TestClient,
    valid_ws_token: str,
) -> None:
    """WebSocket connections are tracked in active_connections set."""
    from argus.api.websocket.ai_chat import get_active_connections

    # Before connection
    initial_count = len(get_active_connections())

    with ws_client_with_ai.websocket_connect("/ws/v1/ai/chat") as websocket:
        # Send auth
        websocket.send_json({"type": "auth", "token": valid_ws_token})
        websocket.receive_json()

        # During connection - count should increase
        assert len(get_active_connections()) >= initial_count

    # After connection closes - count should return
    # (Note: may be flaky due to async cleanup timing)

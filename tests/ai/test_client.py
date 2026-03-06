"""Tests for ClaudeClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.ai.client import ClaudeClient, UsageRecord
from argus.ai.config import AIConfig


@pytest.fixture
def disabled_config() -> AIConfig:
    """Create a disabled AIConfig."""
    return AIConfig(enabled=False, api_key="")


@pytest.fixture
def enabled_config() -> AIConfig:
    """Create an enabled AIConfig."""
    return AIConfig(api_key="test-key-123")


class TestClaudeClientDisabled:
    """Test ClaudeClient behavior when disabled."""

    @pytest.mark.asyncio
    async def test_send_message_returns_graceful_response(
        self, disabled_config: AIConfig
    ) -> None:
        """Test that send_message returns a graceful error when disabled."""
        client = ClaudeClient(disabled_config)

        response, usage = await client.send_message(
            messages=[{"role": "user", "content": "Hello"}],
            system="Test system prompt",
        )

        assert response["type"] == "error"
        assert response["error"] == "ai_disabled"
        assert "not available" in response["message"]
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.estimated_cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_send_with_tool_results_returns_graceful_response(
        self, disabled_config: AIConfig
    ) -> None:
        """Test that send_with_tool_results returns graceful error when disabled."""
        client = ClaudeClient(disabled_config)

        response, usage = await client.send_with_tool_results(
            messages=[{"role": "user", "content": "Hello"}],
            system="Test system prompt",
            tools=[],
            tool_results=[],
        )

        assert response["type"] == "error"
        assert response["error"] == "ai_disabled"

    @pytest.mark.asyncio
    async def test_streaming_returns_error_event_when_disabled(
        self, disabled_config: AIConfig
    ) -> None:
        """Test that streaming returns an error event when disabled."""
        client = ClaudeClient(disabled_config)

        stream = await client.send_message(
            messages=[{"role": "user", "content": "Hello"}],
            system="Test system prompt",
            stream=True,
        )

        events = [event async for event in stream]
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert events[0]["error"] == "ai_disabled"


class TestClaudeClientUsageTracking:
    """Test ClaudeClient usage and cost tracking."""

    def test_usage_record_creation(self, enabled_config: AIConfig) -> None:
        """Test UsageRecord dataclass creation."""
        record = UsageRecord(
            input_tokens=100,
            output_tokens=50,
            model="claude-opus-4-5-20250514",
            estimated_cost_usd=0.00525,
        )

        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.model == "claude-opus-4-5-20250514"
        assert record.estimated_cost_usd == 0.00525

    def test_cost_estimation(self, enabled_config: AIConfig) -> None:
        """Test that cost estimation is calculated correctly."""
        client = ClaudeClient(enabled_config)

        # 1M input tokens at $15/M = $15
        # 1M output tokens at $75/M = $75
        cost = client._estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(90.0)

        # 1000 input, 500 output
        cost = client._estimate_cost(1000, 500)
        expected = (1000 / 1_000_000) * 15.0 + (500 / 1_000_000) * 75.0
        assert cost == pytest.approx(expected)


class TestClaudeClientWithMockedAPI:
    """Test ClaudeClient with mocked Anthropic SDK."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, enabled_config: AIConfig) -> None:
        """Test successful message sending with mocked API."""
        client = ClaudeClient(enabled_config)

        # Create mock response
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Hello! How can I help?"

        mock_response = MagicMock()
        mock_response.id = "msg_123"
        mock_response.role = "assistant"
        mock_response.content = [mock_text_block]
        mock_response.model = "claude-opus-4-5-20250514"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = mock_usage

        # Mock the client
        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Hello"}],
                system="Test system prompt",
            )

        assert response["type"] == "message"
        assert response["role"] == "assistant"
        assert len(response["content"]) == 1
        assert response["content"][0]["type"] == "text"
        assert response["content"][0]["text"] == "Hello! How can I help?"

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.estimated_cost_usd > 0

    @pytest.mark.asyncio
    async def test_send_message_with_tools(self, enabled_config: AIConfig) -> None:
        """Test message sending with tool definitions."""
        client = ClaudeClient(enabled_config)

        # Create mock response with tool_use
        mock_usage = MagicMock()
        mock_usage.input_tokens = 150
        mock_usage.output_tokens = 75

        mock_tool_use_block = MagicMock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = "tool_123"
        mock_tool_use_block.name = "generate_report"
        mock_tool_use_block.input = {"report_type": "daily_summary"}

        mock_response = MagicMock()
        mock_response.id = "msg_456"
        mock_response.role = "assistant"
        mock_response.content = [mock_tool_use_block]
        mock_response.model = "claude-opus-4-5-20250514"
        mock_response.stop_reason = "tool_use"
        mock_response.usage = mock_usage

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        tools = [
            {
                "name": "generate_report",
                "description": "Generate a report",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Generate a daily report"}],
                system="Test system prompt",
                tools=tools,
            )

        assert response["stop_reason"] == "tool_use"
        assert response["content"][0]["type"] == "tool_use"
        assert response["content"][0]["name"] == "generate_report"
        assert response["content"][0]["input"] == {"report_type": "daily_summary"}

    @pytest.mark.asyncio
    async def test_error_handling_returns_structured_error(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that API errors are caught and returned as structured errors."""
        client = ClaudeClient(enabled_config)

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=Exception("API Error: Service unavailable")
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Hello"}],
                system="Test system prompt",
            )

        assert response["type"] == "error"
        assert "Exception" in response["error"]
        assert "Service unavailable" in response["message"]
        assert usage.input_tokens == 0


class TestStreamEventToDict:
    """Test ClaudeClient._stream_event_to_dict conversion."""

    def test_content_block_start_preserves_tool_use_fields(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that content_block_start events preserve content_block for tool_use."""
        client = ClaudeClient(enabled_config)

        # Mock content_block_start event with tool_use
        mock_content_block = MagicMock()
        mock_content_block.type = "tool_use"
        mock_content_block.id = "toolu_abc123"
        mock_content_block.name = "propose_allocation_change"

        mock_event = MagicMock()
        mock_event.type = "content_block_start"
        mock_event.content_block = mock_content_block
        mock_event.index = 0
        # Remove attributes that shouldn't exist
        del mock_event.delta
        del mock_event.message

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "content_block_start"
        assert result["index"] == 0
        assert "content_block" in result
        assert result["content_block"]["type"] == "tool_use"
        assert result["content_block"]["id"] == "toolu_abc123"
        assert result["content_block"]["name"] == "propose_allocation_change"

    def test_content_block_delta_preserves_partial_json(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that content_block_delta events preserve delta.partial_json."""
        client = ClaudeClient(enabled_config)

        # Mock content_block_delta event with input_json_delta
        mock_delta = MagicMock()
        mock_delta.type = "input_json_delta"
        mock_delta.partial_json = '{"strategy_id": "vwap_reclaim"'
        # Ensure text attribute doesn't exist
        del mock_delta.text
        del mock_delta.stop_reason

        mock_event = MagicMock()
        mock_event.type = "content_block_delta"
        mock_event.delta = mock_delta
        mock_event.index = 0
        # Remove attributes that shouldn't exist
        del mock_event.content_block
        del mock_event.message

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "content_block_delta"
        assert result["index"] == 0
        assert "delta" in result
        assert result["delta"]["type"] == "input_json_delta"
        assert result["delta"]["partial_json"] == '{"strategy_id": "vwap_reclaim"'
        # Also check backward-compatible top-level delta_type
        assert result["delta_type"] == "input_json_delta"

    def test_content_block_delta_preserves_text_delta(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that text_delta events preserve delta.text and backward-compatible fields."""
        client = ClaudeClient(enabled_config)

        # Mock content_block_delta event with text_delta
        mock_delta = MagicMock()
        mock_delta.type = "text_delta"
        mock_delta.text = "Hello, I can help you with that."
        # Ensure partial_json attribute doesn't exist
        del mock_delta.partial_json
        del mock_delta.stop_reason

        mock_event = MagicMock()
        mock_event.type = "content_block_delta"
        mock_event.delta = mock_delta
        mock_event.index = 0
        # Remove attributes that shouldn't exist
        del mock_event.content_block
        del mock_event.message

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "content_block_delta"
        assert "delta" in result
        assert result["delta"]["type"] == "text_delta"
        assert result["delta"]["text"] == "Hello, I can help you with that."
        # Check backward-compatible top-level fields
        assert result["text"] == "Hello, I can help you with that."
        assert result["delta_type"] == "text_delta"

    def test_content_block_start_preserves_text_block_fields(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that content_block_start events preserve content_block for text blocks."""
        client = ClaudeClient(enabled_config)

        # Mock content_block_start event with text block
        mock_content_block = MagicMock()
        mock_content_block.type = "text"
        mock_content_block.text = ""
        # Ensure tool_use-specific attributes don't exist
        del mock_content_block.id
        del mock_content_block.name

        mock_event = MagicMock()
        mock_event.type = "content_block_start"
        mock_event.content_block = mock_content_block
        mock_event.index = 0
        # Remove attributes that shouldn't exist
        del mock_event.delta
        del mock_event.message

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "content_block_start"
        assert "content_block" in result
        assert result["content_block"]["type"] == "text"

    def test_message_start_preserves_message_info(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that message_start events preserve message info."""
        client = ClaudeClient(enabled_config)

        # Mock message_start event
        mock_message = MagicMock()
        mock_message.id = "msg_123abc"
        mock_message.model = "claude-opus-4-5-20250514"

        mock_event = MagicMock()
        mock_event.type = "message_start"
        mock_event.message = mock_message
        # Remove attributes that shouldn't exist
        del mock_event.delta
        del mock_event.content_block
        del mock_event.index

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "message_start"
        assert "message" in result
        assert result["message"]["id"] == "msg_123abc"
        assert result["message"]["model"] == "claude-opus-4-5-20250514"

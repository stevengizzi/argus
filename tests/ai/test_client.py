"""Tests for ClaudeClient."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.ai.client import ClaudeClient, UsageRecord
from argus.ai.config import AIConfig


def _make_success_response() -> MagicMock:
    """Build a mock API response representing a successful assistant turn."""
    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 5

    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "ok"

    mock_response = MagicMock()
    mock_response.id = "msg_retry"
    mock_response.role = "assistant"
    mock_response.content = [mock_text_block]
    mock_response.model = "claude-opus-4-5-20250514"
    mock_response.stop_reason = "end_turn"
    mock_response.usage = mock_usage
    return mock_response


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

    def test_message_start_extracts_usage_input_tokens(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that message_start events extract usage.input_tokens."""
        client = ClaudeClient(enabled_config)

        # Mock message_start event with usage data
        mock_usage = MagicMock()
        mock_usage.input_tokens = 1500

        mock_message = MagicMock()
        mock_message.id = "msg_usage_test"
        mock_message.model = "claude-opus-4-5-20250514"
        mock_message.usage = mock_usage

        mock_event = MagicMock()
        mock_event.type = "message_start"
        mock_event.message = mock_message
        # Remove attributes that shouldn't exist
        del mock_event.delta
        del mock_event.content_block
        del mock_event.index
        del mock_event.usage

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "message_start"
        assert "usage" in result
        assert result["usage"]["input_tokens"] == 1500

    def test_message_delta_extracts_usage_output_tokens(
        self, enabled_config: AIConfig
    ) -> None:
        """Test that message_delta events extract usage.output_tokens."""
        client = ClaudeClient(enabled_config)

        # Mock message_delta event with usage data
        mock_usage = MagicMock()
        mock_usage.output_tokens = 750

        mock_delta = MagicMock()
        mock_delta.stop_reason = "end_turn"
        del mock_delta.type
        del mock_delta.text
        del mock_delta.partial_json

        mock_event = MagicMock()
        mock_event.type = "message_delta"
        mock_event.delta = mock_delta
        mock_event.usage = mock_usage
        # Remove attributes that shouldn't exist
        del mock_event.content_block
        del mock_event.index
        del mock_event.message

        result = client._stream_event_to_dict(mock_event)

        assert result["type"] == "message_delta"
        assert "usage" in result
        assert result["usage"]["output_tokens"] == 750


class TestGetClientImportGuard:
    """Cover the lazy anthropic-import guard in ``_get_client`` (lines 77-86)."""

    def test_get_client_raises_importerror_when_anthropic_missing(
        self,
        enabled_config: AIConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When ``anthropic`` is not importable, ``_get_client`` raises a
        clear ImportError with install guidance."""
        # Setting sys.modules[key] = None forces subsequent `import` to raise
        # (per CPython import-machinery semantics).
        monkeypatch.setitem(sys.modules, "anthropic", None)

        client = ClaudeClient(enabled_config)

        with pytest.raises(ImportError, match="anthropic.*package is required"):
            client._get_client()

    def test_get_client_caches_instance(
        self,
        enabled_config: AIConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Second call returns the cached client rather than re-instantiating.

        Covers lines 85-86 (``self._client = AsyncAnthropic(...)`` + return)
        and the cached short-circuit at line 77.

        Injects a fake ``anthropic`` module into ``sys.modules`` so the test
        runs in environments where the real package is not installed (notably
        CI — ``anthropic`` is an optional runtime dep not listed in
        pyproject.toml).
        """
        fake_anthropic = MagicMock()
        fake_anthropic.AsyncAnthropic = MagicMock(
            side_effect=lambda **kwargs: MagicMock(name="AsyncAnthropicInstance")
        )
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        client = ClaudeClient(enabled_config)
        assert client._client is None

        first = client._get_client()
        second = client._get_client()

        assert first is second, "Second _get_client() call should return the cached instance"
        assert client._client is first
        assert fake_anthropic.AsyncAnthropic.call_count == 1


class TestSendMessageRetryPaths:
    """Cover ``_send_message_non_stream`` rate-limit + API-error retry logic
    (lines 239, 243-262). All retry tests mock ``asyncio.sleep`` so each test
    finishes in milliseconds.
    """

    @pytest.mark.asyncio
    async def test_send_message_retries_on_rate_limit_then_succeeds(
        self,
        enabled_config: AIConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rate-limit exception on first attempt → retry → success on second."""
        mock_sleep = AsyncMock()
        monkeypatch.setattr("argus.ai.client.asyncio.sleep", mock_sleep)

        client = ClaudeClient(enabled_config)

        # Exception whose class name contains "RateLimitError" triggers the
        # rate-limit branch via the ``"RateLimitError" in error_name`` check.
        class RateLimitError(Exception):
            pass

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=[RateLimitError("rate limited"), _make_success_response()]
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Hi"}],
                system="Test",
            )

        assert response["type"] == "message"
        assert mock_anthropic_client.messages.create.await_count == 2
        mock_sleep.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_rate_limit_max_retries_returns_error_response(
        self,
        enabled_config: AIConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rate-limit on every attempt → error response after ``max_retries`` (3)."""
        monkeypatch.setattr("argus.ai.client.asyncio.sleep", AsyncMock())

        client = ClaudeClient(enabled_config)

        class RateLimitError(Exception):
            pass

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=RateLimitError("rate limited")
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Hi"}],
                system="Test",
            )

        assert response["type"] == "error"
        assert response["error"] == "RateLimitError"
        assert mock_anthropic_client.messages.create.await_count == 3

    @pytest.mark.asyncio
    async def test_send_message_retries_on_api_error_then_succeeds(
        self,
        enabled_config: AIConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """APIError exception on first attempt → retry → success."""
        monkeypatch.setattr("argus.ai.client.asyncio.sleep", AsyncMock())

        client = ClaudeClient(enabled_config)

        class APIError(Exception):
            pass

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=[APIError("api down"), _make_success_response()]
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Hi"}],
                system="Test",
            )

        assert response["type"] == "message"
        assert mock_anthropic_client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_send_message_api_error_max_retries_returns_error_response(
        self,
        enabled_config: AIConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """APIError on every attempt → error response after ``max_retries``."""
        monkeypatch.setattr("argus.ai.client.asyncio.sleep", AsyncMock())

        client = ClaudeClient(enabled_config)

        class APIError(Exception):
            pass

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=APIError("api down")
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            response, usage = await client.send_message(
                messages=[{"role": "user", "content": "Hi"}],
                system="Test",
            )

        assert response["type"] == "error"
        assert response["error"] == "APIError"
        assert mock_anthropic_client.messages.create.await_count == 3

    @pytest.mark.asyncio
    async def test_send_message_reraises_importerror(
        self, enabled_config: AIConfig
    ) -> None:
        """ImportError from ``_get_client`` propagates (line 239 re-raise)."""
        client = ClaudeClient(enabled_config)

        with patch.object(
            client, "_get_client", side_effect=ImportError("anthropic missing")
        ):
            with pytest.raises(ImportError, match="anthropic missing"):
                await client.send_message(
                    messages=[{"role": "user", "content": "Hi"}],
                    system="Test",
                )


class TestSendMessageStream:
    """Cover the streaming path (lines 195, 297, 317-319)."""

    @pytest.mark.asyncio
    async def test_send_message_stream_returns_async_generator(
        self, enabled_config: AIConfig
    ) -> None:
        """send_message(stream=True) returns an async generator (line 195)."""
        client = ClaudeClient(enabled_config)

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.stream = MagicMock(
            side_effect=Exception("stream setup failed")
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            stream = await client.send_message(
                messages=[{"role": "user", "content": "Hi"}],
                system="Test",
                stream=True,
            )

            assert hasattr(stream, "__aiter__")

    @pytest.mark.asyncio
    async def test_send_message_stream_yields_error_on_exception(
        self, enabled_config: AIConfig
    ) -> None:
        """Exception raised while setting up the stream → yields a single error event.

        Per the FIX-13c kickoff hazard 1, we do NOT try to mock the real async
        context manager. Instead, make ``client.messages.stream`` raise on call,
        which triggers the ``except Exception`` at line 317.
        """
        client = ClaudeClient(enabled_config)

        mock_anthropic_client = MagicMock()
        mock_anthropic_client.messages.stream = MagicMock(
            side_effect=Exception("stream boom")
        )

        with patch.object(client, "_get_client", return_value=mock_anthropic_client):
            stream = await client.send_message(
                messages=[{"role": "user", "content": "Hi"}],
                system="Test",
                stream=True,
            )
            events = [event async for event in stream]

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert events[0]["error"] == "Exception"
        assert "stream boom" in events[0]["message"]


class TestSendWithToolResults:
    """Cover ``send_with_tool_results`` enabled path (lines 347-358)."""

    @pytest.mark.asyncio
    async def test_send_with_tool_results_appends_tool_results_as_user_message(
        self, enabled_config: AIConfig
    ) -> None:
        """Tool results are appended as a single user message whose content
        is a list of ``tool_result`` blocks, then delegated to the non-stream path.
        """
        client = ClaudeClient(enabled_config)

        captured: dict[str, Any] = {}

        async def _capture_and_stub(
            msgs: list[dict[str, Any]],
            system: str,
            tools: list[dict[str, Any]] | None,
        ) -> tuple[dict[str, Any], UsageRecord]:
            captured["messages"] = msgs
            captured["system"] = system
            captured["tools"] = tools
            return (
                {"type": "message", "content": []},
                UsageRecord(
                    input_tokens=0,
                    output_tokens=0,
                    model="m",
                    estimated_cost_usd=0.0,
                ),
            )

        original_messages = [
            {"role": "user", "content": "Do the thing"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t1", "name": "foo", "input": {}},
                ],
            },
        ]
        tool_results = [{"tool_use_id": "t1", "content": "result text"}]

        with patch.object(
            client, "_send_message_non_stream", side_effect=_capture_and_stub
        ):
            response, usage = await client.send_with_tool_results(
                messages=original_messages,
                system="sys",
                tools=[{"name": "foo"}],
                tool_results=tool_results,
            )

        # The delegated call received the original messages plus one appended
        # user turn that encodes the tool_result content blocks.
        assert captured["messages"][: len(original_messages)] == original_messages
        appended = captured["messages"][-1]
        assert appended["role"] == "user"
        assert isinstance(appended["content"], list)
        assert appended["content"][0]["type"] == "tool_result"
        assert appended["content"][0]["tool_use_id"] == "t1"
        assert appended["content"][0]["content"] == "result text"
        assert response["type"] == "message"

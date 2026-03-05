"""Claude API client wrapper for ARGUS.

Provides a wrapper around the Anthropic Python SDK with rate limiting,
error handling, and usage tracking. All methods are no-ops when AI is disabled.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from argus.ai.config import AIConfig

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Token usage and cost tracking for an API call.

    Attributes:
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens generated.
        model: Model identifier used.
        estimated_cost_usd: Estimated cost in USD.
    """

    input_tokens: int
    output_tokens: int
    model: str
    estimated_cost_usd: float


class ClaudeClient:
    """Wrapper for the Anthropic Claude API.

    Provides async methods for sending messages to Claude with:
    - Tool use support for action proposals
    - Rate limiting with exponential backoff
    - Token usage tracking and cost estimation
    - Graceful degradation when AI is disabled

    All methods return structured responses; exceptions are caught and
    converted to error responses.
    """

    def __init__(self, config: AIConfig) -> None:
        """Initialize the Claude client.

        Args:
            config: AI configuration including API key and model settings.

        Note:
            No API calls are made during initialization.
        """
        self._config = config
        self._client: Any = None  # Lazy-loaded Anthropic client

    @property
    def enabled(self) -> bool:
        """Check if AI features are enabled."""
        return self._config.enabled

    def _get_client(self) -> Any:
        """Lazily load and return the Anthropic async client.

        Returns:
            The AsyncAnthropic client instance.

        Raises:
            ImportError: If the anthropic package is not installed.
        """
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                raise ImportError(
                    "The 'anthropic' package is required for AI features. "
                    "Install it with: pip install anthropic"
                ) from e
            self._client = AsyncAnthropic(api_key=self._config.api_key)
        return self._client

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate the cost of an API call in USD.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        input_cost = (input_tokens / 1_000_000) * self._config.cost_per_million_input_tokens
        output_cost = (output_tokens / 1_000_000) * self._config.cost_per_million_output_tokens
        return input_cost + output_cost

    def _create_usage_record(self, usage: Any) -> UsageRecord:
        """Create a UsageRecord from API response usage data.

        Args:
            usage: Usage object from the API response.

        Returns:
            UsageRecord with token counts and cost estimate.
        """
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        return UsageRecord(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._config.model,
            estimated_cost_usd=self._estimate_cost(input_tokens, output_tokens),
        )

    def _disabled_response(self) -> tuple[dict[str, Any], UsageRecord]:
        """Return a graceful response when AI is disabled.

        Returns:
            Tuple of (response dict, zero-usage record).
        """
        return (
            {
                "type": "error",
                "error": "ai_disabled",
                "message": "AI features are not available. Set ANTHROPIC_API_KEY to enable.",
            },
            UsageRecord(
                input_tokens=0,
                output_tokens=0,
                model=self._config.model,
                estimated_cost_usd=0.0,
            ),
        )

    def _error_response(self, error: Exception) -> tuple[dict[str, Any], UsageRecord]:
        """Return a structured error response.

        Args:
            error: The exception that occurred.

        Returns:
            Tuple of (error response dict, zero-usage record).
        """
        error_type = type(error).__name__
        return (
            {
                "type": "error",
                "error": error_type,
                "message": str(error),
            },
            UsageRecord(
                input_tokens=0,
                output_tokens=0,
                model=self._config.model,
                estimated_cost_usd=0.0,
            ),
        )

    async def send_message(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> tuple[dict[str, Any], UsageRecord] | AsyncGenerator[dict[str, Any], None]:
        """Send a message to Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: System prompt string.
            tools: Optional list of tool definitions for tool_use.
            stream: If True, return an async generator of events.

        Returns:
            If stream=False: Tuple of (response dict, usage record).
            If stream=True: Async generator yielding event dicts.

        Note:
            Returns a graceful error response (never raises) when:
            - AI is disabled (no API key)
            - API errors occur after retries exhausted
            - Rate limiting persists
        """
        if not self.enabled:
            if stream:
                return self._disabled_stream()
            return self._disabled_response()

        if stream:
            return self._send_message_stream(messages, system, tools)

        return await self._send_message_non_stream(messages, system, tools)

    async def _send_message_non_stream(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], UsageRecord]:
        """Send a non-streaming message with retries.

        Args:
            messages: Message list.
            system: System prompt.
            tools: Optional tools.

        Returns:
            Tuple of (response dict, usage record).
        """
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                client = self._get_client()
                kwargs: dict[str, Any] = {
                    "model": self._config.model,
                    "max_tokens": self._config.max_response_tokens,
                    "system": system,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools

                response = await client.messages.create(**kwargs)

                # Convert response to dict
                response_dict = self._response_to_dict(response)
                usage_record = self._create_usage_record(response.usage)

                return (response_dict, usage_record)

            except ImportError:
                raise
            except Exception as e:
                error_name = type(e).__name__
                if "RateLimitError" in error_name or "rate" in str(e).lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"Rate limited, retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(f"Rate limit exceeded after {max_retries} retries")
                    return self._error_response(e)

                if "APIError" in error_name or "Anthropic" in error_name:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"API error: {e}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(f"API error after {max_retries} retries: {e}")
                    return self._error_response(e)

                logger.error(f"Unexpected error sending message: {e}")
                return self._error_response(e)

        return self._error_response(Exception("Max retries exceeded"))

    async def _disabled_stream(self) -> AsyncGenerator[dict[str, Any], None]:
        """Return a disabled message as a stream.

        Yields:
            Single error event dict.
        """
        yield {
            "type": "error",
            "error": "ai_disabled",
            "message": "AI features are not available. Set ANTHROPIC_API_KEY to enable.",
        }

    async def _send_message_stream(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a streaming message.

        Args:
            messages: Message list.
            system: System prompt.
            tools: Optional tools.

        Yields:
            Event dicts from the stream.
        """
        if not self.enabled:
            async for event in self._disabled_stream():
                yield event
            return

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                "model": self._config.model,
                "max_tokens": self._config.max_response_tokens,
                "system": system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            async with client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    yield self._stream_event_to_dict(event)

        except Exception as e:
            logger.error(f"Error in streaming message: {e}")
            yield {
                "type": "error",
                "error": type(e).__name__,
                "message": str(e),
            }

    async def send_with_tool_results(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], UsageRecord]:
        """Continue a conversation after tool_use by appending tool results.

        Args:
            messages: Original message list (should end with assistant tool_use).
            system: System prompt string.
            tools: Tool definitions.
            tool_results: List of tool result dicts with 'tool_use_id' and 'content'.

        Returns:
            Tuple of (response dict, usage record).
        """
        if not self.enabled:
            return self._disabled_response()

        # Append tool results as user messages
        updated_messages = list(messages)
        updated_messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tr["tool_use_id"], "content": tr["content"]}
                    for tr in tool_results
                ],
            }
        )

        return await self._send_message_non_stream(updated_messages, system, tools)

    def _response_to_dict(self, response: Any) -> dict[str, Any]:
        """Convert an API response object to a dictionary.

        Args:
            response: The API response object.

        Returns:
            Dictionary representation of the response.
        """
        content_list = []
        for block in response.content:
            block_dict: dict[str, Any] = {"type": block.type}
            if block.type == "text":
                block_dict["text"] = block.text
            elif block.type == "tool_use":
                block_dict["id"] = block.id
                block_dict["name"] = block.name
                block_dict["input"] = block.input
            content_list.append(block_dict)

        return {
            "id": response.id,
            "type": "message",
            "role": response.role,
            "content": content_list,
            "model": response.model,
            "stop_reason": response.stop_reason,
        }

    def _stream_event_to_dict(self, event: Any) -> dict[str, Any]:
        """Convert a stream event to a dictionary.

        Args:
            event: The stream event object.

        Returns:
            Dictionary representation of the event.
        """
        event_dict: dict[str, Any] = {"type": event.type}

        if hasattr(event, "delta"):
            delta = event.delta
            if hasattr(delta, "text"):
                event_dict["text"] = delta.text
            if hasattr(delta, "type"):
                event_dict["delta_type"] = delta.type

        if hasattr(event, "index"):
            event_dict["index"] = event.index

        if hasattr(event, "message"):
            event_dict["message"] = {
                "id": event.message.id,
                "model": event.message.model,
            }

        return event_dict

"""AI Layer configuration for ARGUS.

Configures the Claude API integration including token budgets, rate limits,
and cost tracking. API key is read from environment variable at runtime.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, model_validator


class AIConfig(BaseModel):
    """Configuration for the AI Copilot layer.

    Attributes:
        enabled: Whether AI features are enabled. Auto-set True when api_key is non-empty.
        api_key: Anthropic API key (populated from ANTHROPIC_API_KEY env var).
        model: Claude model identifier to use.
        max_response_tokens: Maximum tokens in Claude's response.
        system_prompt_token_budget: Token budget for the system prompt.
        page_context_token_budget: Token budget for page-specific context.
        history_token_budget: Token budget for conversation history.
        max_history_messages: Maximum number of messages to include in history.
        rate_limit_requests_per_minute: Max API requests per minute.
        rate_limit_tokens_per_minute: Max tokens per minute.
        cache_ttl_seconds: TTL for cached responses (default 5 min).
        proposal_ttl_seconds: TTL for pending proposals (default 5 min).
        insight_refresh_interval_seconds: How often to refresh dashboard insights.
        cost_per_million_input_tokens: Cost in USD per 1M input tokens (Opus pricing).
        cost_per_million_output_tokens: Cost in USD per 1M output tokens (Opus pricing).
    """

    enabled: bool = False
    api_key: str = ""
    model: str = "claude-opus-4-5-20250514"
    max_response_tokens: int = Field(default=4096, ge=1)
    system_prompt_token_budget: int = Field(default=1500, ge=100)
    page_context_token_budget: int = Field(default=2000, ge=100)
    history_token_budget: int = Field(default=8000, ge=100)
    max_history_messages: int = Field(default=20, ge=1)
    rate_limit_requests_per_minute: int = Field(default=10, ge=1)
    rate_limit_tokens_per_minute: int = Field(default=50000, ge=1000)
    cache_ttl_seconds: int = Field(default=300, ge=1)
    proposal_ttl_seconds: int = Field(default=300, ge=1)
    insight_refresh_interval_seconds: int = Field(default=300, ge=1)
    cost_per_million_input_tokens: float = Field(default=15.0, ge=0)
    cost_per_million_output_tokens: float = Field(default=75.0, ge=0)

    @model_validator(mode="after")
    def auto_detect_enabled(self) -> AIConfig:
        """Auto-detect enabled state based on API key availability.

        If api_key is empty, attempt to read from ANTHROPIC_API_KEY env var.
        If api_key is non-empty after resolution, set enabled = True.
        """
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if self.api_key:
            self.enabled = True
        return self

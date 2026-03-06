"""Tests for AIConfig."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from argus.ai.config import AIConfig


class TestAIConfigDefaults:
    """Test AIConfig default values."""

    def test_default_values(self) -> None:
        """Test that AIConfig has correct defaults."""
        config = AIConfig()

        assert config.enabled is False
        assert config.api_key == ""
        assert config.model == "claude-opus-4-5-20251101"
        assert config.max_response_tokens == 4096
        assert config.system_prompt_token_budget == 1500
        assert config.page_context_token_budget == 2000
        assert config.history_token_budget == 8000
        assert config.max_history_messages == 20
        assert config.rate_limit_requests_per_minute == 10
        assert config.rate_limit_tokens_per_minute == 50000
        assert config.cache_ttl_seconds == 300
        assert config.proposal_ttl_seconds == 300
        assert config.insight_refresh_interval_seconds == 300
        assert config.cost_per_million_input_tokens == 15.0
        assert config.cost_per_million_output_tokens == 75.0


class TestAIConfigAutoDetection:
    """Test AIConfig auto-detection of enabled state."""

    def test_enabled_when_api_key_provided(self) -> None:
        """Test that enabled is True when api_key is provided."""
        config = AIConfig(api_key="test-key-123")
        assert config.enabled is True
        assert config.api_key == "test-key-123"

    def test_enabled_from_env_var(self) -> None:
        """Test that api_key is read from ANTHROPIC_API_KEY env var."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-456"}):
            config = AIConfig()
            assert config.enabled is True
            assert config.api_key == "env-key-456"

    def test_disabled_when_no_key(self) -> None:
        """Test that enabled is False when no API key is available."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure ANTHROPIC_API_KEY is not in environment
            os.environ.pop("ANTHROPIC_API_KEY", None)
            config = AIConfig()
            assert config.enabled is False
            assert config.api_key == ""


class TestAIConfigBackwardCompat:
    """Test backward compatibility with existing configs."""

    def test_system_config_without_ai_section(self) -> None:
        """Test that SystemConfig parses correctly without ai: section."""
        from argus.core.config import SystemConfig

        # Create config without ai section - should use defaults
        config = SystemConfig()
        assert config.ai is not None
        assert isinstance(config.ai, AIConfig)
        assert config.ai.enabled is False or config.ai.api_key != ""

    def test_argus_config_without_ai_section(self) -> None:
        """Test that ArgusConfig parses correctly without ai in system."""
        from argus.core.config import ArgusConfig

        # Create config from empty dict - should use all defaults
        config = ArgusConfig()
        assert config.system.ai is not None
        assert isinstance(config.system.ai, AIConfig)

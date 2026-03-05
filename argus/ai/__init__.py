"""ARGUS AI Layer.

Provides Claude API integration for analysis, advisory, and approved actions.

Public classes:
- AIConfig: Configuration for the AI layer
- ClaudeClient: Wrapper for the Anthropic Claude API
- PromptManager: Handles prompt construction and token budgets
- SystemContextBuilder: Assembles system state into context payloads
- ResponseCache: TTL-based caching for AI responses
- ConversationManager: Chat conversation persistence
- UsageTracker: API usage tracking and cost monitoring

Tool definitions:
- ARGUS_TOOLS: List of tool definitions for tool_use
- TOOLS_REQUIRING_APPROVAL: Set of tools that require operator approval
"""

from argus.ai.cache import ResponseCache
from argus.ai.client import ClaudeClient, UsageRecord
from argus.ai.config import AIConfig
from argus.ai.context import SystemContextBuilder
from argus.ai.conversations import ConversationManager
from argus.ai.prompts import PromptManager
from argus.ai.tools import ARGUS_TOOLS, TOOLS_REQUIRING_APPROVAL, get_tool_by_name, requires_approval
from argus.ai.usage import UsageTracker

__all__ = [
    # Config
    "AIConfig",
    # Client
    "ClaudeClient",
    "UsageRecord",
    # Prompts
    "PromptManager",
    # Context
    "SystemContextBuilder",
    # Cache
    "ResponseCache",
    # Persistence
    "ConversationManager",
    "UsageTracker",
    # Tools
    "ARGUS_TOOLS",
    "TOOLS_REQUIRING_APPROVAL",
    "get_tool_by_name",
    "requires_approval",
]

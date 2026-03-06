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
- ActionManager: Manages AI action proposals requiring approval
- ActionProposal: Data class for a single action proposal
- ActionExecutor: ABC for action executors
- ExecutorRegistry: Maps tool names to executor instances
- DailySummaryGenerator: Generates end-of-day summaries and insights
- AIService: Main orchestration service for AI features

Tool definitions:
- ARGUS_TOOLS: List of tool definitions for tool_use
- TOOLS_REQUIRING_APPROVAL: Set of tools that require operator approval
"""

from argus.ai.actions import (
    ActionManager,
    ActionProposal,
    ActionProposalError,
    InvalidToolError,
    ProposalExpiredError,
    ProposalNotFoundError,
    ProposalNotPendingError,
)
from argus.ai.cache import ResponseCache
from argus.ai.client import ClaudeClient, UsageRecord
from argus.ai.config import AIConfig
from argus.ai.context import SystemContextBuilder
from argus.ai.conversations import ConversationManager
from argus.ai.executors import (
    ActionExecutor,
    AllocationChangeExecutor,
    ExecutionError,
    ExecutorRegistry,
    GenerateReportExecutor,
    PreExecutionCheckError,
    RiskParamChangeExecutor,
    StrategyResumeExecutor,
    StrategySuspendExecutor,
    ValidationError,
)
from argus.ai.prompts import PromptManager
from argus.ai.service import AIService
from argus.ai.summary import DailySummaryGenerator
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
    # Actions
    "ActionManager",
    "ActionProposal",
    "ActionProposalError",
    "InvalidToolError",
    "ProposalExpiredError",
    "ProposalNotFoundError",
    "ProposalNotPendingError",
    # Executors
    "ActionExecutor",
    "AllocationChangeExecutor",
    "RiskParamChangeExecutor",
    "StrategySuspendExecutor",
    "StrategyResumeExecutor",
    "GenerateReportExecutor",
    "ExecutorRegistry",
    "ValidationError",
    "ExecutionError",
    "PreExecutionCheckError",
    # Summary
    "DailySummaryGenerator",
    # Service
    "AIService",
    # Tools
    "ARGUS_TOOLS",
    "TOOLS_REQUIRING_APPROVAL",
    "get_tool_by_name",
    "requires_approval",
]

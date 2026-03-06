"""Tests for AIService."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.ai.actions import ActionManager, ActionProposal
from argus.ai.cache import ResponseCache
from argus.ai.client import UsageRecord
from argus.ai.config import AIConfig
from argus.ai.context import SystemContextBuilder
from argus.ai.conversations import ConversationManager
from argus.ai.executors import ExecutorRegistry
from argus.ai.prompts import PromptManager
from argus.ai.service import AIService
from argus.ai.summary import DailySummaryGenerator
from argus.ai.usage import UsageTracker
from argus.core.event_bus import EventBus
from argus.db.manager import DatabaseManager


@dataclass
class MockStrategy:
    """Mock strategy for testing."""

    name: str = "test_strategy"
    is_active: bool = True
    allocated_capital: float = 25000.0
    _config: Any = None


@dataclass
class MockOrchestrator:
    """Mock orchestrator."""

    current_regime: str = "NEUTRAL"
    cash_reserve_pct: float = 0.20
    _strategies: dict[str, MockStrategy] = field(default_factory=dict)

    def get_strategy(self, strategy_id: str) -> MockStrategy | None:
        return self._strategies.get(strategy_id)


@dataclass
class MockBrokerAccount:
    """Mock broker account."""

    equity: float = 100000.0


class MockBroker:
    """Mock broker."""

    def __init__(self, equity: float = 100000.0) -> None:
        self._equity = equity

    async def get_account(self) -> MockBrokerAccount:
        return MockBrokerAccount(equity=self._equity)


@dataclass
class MockAppState:
    """Mock app state for testing."""

    strategies: dict[str, MockStrategy] = field(default_factory=dict)
    config: Any = None
    orchestrator: MockOrchestrator | None = None
    risk_manager: Any = None
    broker: MockBroker | None = None
    event_bus: Any = None
    ai_summary_generator: Any = None
    ai_client: Any = None


class MockClaudeClient:
    """Mock Claude client for testing."""

    def __init__(self, enabled: bool = True, response_text: str = "Test response.") -> None:
        self.enabled = enabled
        self._response_text = response_text
        self._tool_use_response = False
        self._tool_name = ""
        self._tool_input: dict[str, Any] = {}

    def set_tool_use_response(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Configure to return a tool_use response."""
        self._tool_use_response = True
        self._tool_name = tool_name
        self._tool_input = tool_input

    async def send_message(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> tuple[dict[str, Any], UsageRecord]:
        if self._tool_use_response:
            response = {
                "type": "message",
                "content": [
                    {"type": "text", "text": "I'll help you with that."},
                    {
                        "type": "tool_use",
                        "id": "tu_123",
                        "name": self._tool_name,
                        "input": self._tool_input,
                    },
                ],
            }
        else:
            response = {
                "type": "message",
                "content": [{"type": "text", "text": self._response_text}],
            }
        usage = UsageRecord(
            input_tokens=100,
            output_tokens=50,
            model="claude-sonnet-4-20250514",
            estimated_cost_usd=0.001,
        )
        return response, usage

    async def send_with_tool_results(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], UsageRecord]:
        response = {
            "type": "message",
            "content": [{"type": "text", "text": "Action proposal created."}],
        }
        usage = UsageRecord(
            input_tokens=50,
            output_tokens=30,
            model="claude-sonnet-4-20250514",
            estimated_cost_usd=0.0005,
        )
        return response, usage


@pytest.fixture
def ai_config() -> AIConfig:
    """Provide a test AIConfig."""
    return AIConfig(enabled=True, api_key="test-key")


@pytest.fixture
def mock_client() -> MockClaudeClient:
    """Provide a mock Claude client."""
    return MockClaudeClient(enabled=True)


@pytest.fixture
def mock_prompt_manager() -> MagicMock:
    """Provide a mock prompt manager."""
    manager = MagicMock(spec=PromptManager)
    manager.build_system_prompt.return_value = "System prompt"
    manager.build_page_context.return_value = "Page context"
    manager.build_conversation_messages.return_value = ("Full system", [{"role": "user", "content": "Test"}])
    return manager


@pytest.fixture
def mock_context_builder() -> MagicMock:
    """Provide a mock context builder."""
    builder = MagicMock(spec=SystemContextBuilder)
    builder.build_context = AsyncMock(return_value={"page_context": {}})
    return builder


@pytest.fixture
async def mock_conversation_manager(db: DatabaseManager) -> ConversationManager:
    """Provide an initialized conversation manager."""
    manager = ConversationManager(db)
    await manager.initialize()
    return manager


@pytest.fixture
def mock_usage_tracker() -> MagicMock:
    """Provide a mock usage tracker."""
    tracker = MagicMock(spec=UsageTracker)
    tracker.record_usage = AsyncMock()
    return tracker


@pytest.fixture
async def mock_action_manager(
    db: DatabaseManager,
    bus: EventBus,
    ai_config: AIConfig,
) -> ActionManager:
    """Provide an initialized action manager."""
    manager = ActionManager(db, bus, ai_config)
    await manager.initialize()
    return manager


@pytest.fixture
def mock_executor_registry() -> ExecutorRegistry:
    """Provide an executor registry."""
    return ExecutorRegistry()


@pytest.fixture
def mock_summary_generator() -> MagicMock:
    """Provide a mock summary generator."""
    generator = MagicMock(spec=DailySummaryGenerator)
    generator.generate = AsyncMock(return_value="Daily summary text")
    generator.generate_insight = AsyncMock(return_value="Test insight")
    return generator


@pytest.fixture
def mock_cache() -> ResponseCache:
    """Provide a response cache."""
    return ResponseCache(default_ttl=60)


@pytest.fixture
def ai_service(
    mock_client: MockClaudeClient,
    ai_config: AIConfig,
    mock_prompt_manager: MagicMock,
    mock_context_builder: MagicMock,
    mock_conversation_manager: ConversationManager,
    mock_usage_tracker: MagicMock,
    mock_action_manager: ActionManager,
    mock_executor_registry: ExecutorRegistry,
    mock_summary_generator: MagicMock,
    mock_cache: ResponseCache,
) -> AIService:
    """Provide an AI service instance."""
    return AIService(
        client=mock_client,
        config=ai_config,
        prompt_manager=mock_prompt_manager,
        context_builder=mock_context_builder,
        conversation_manager=mock_conversation_manager,
        usage_tracker=mock_usage_tracker,
        action_manager=mock_action_manager,
        executor_registry=mock_executor_registry,
        summary_generator=mock_summary_generator,
        cache=mock_cache,
    )


class TestAIServiceEnabled:
    """Test enabled property."""

    def test_enabled_when_client_enabled(
        self,
        ai_service: AIService,
    ) -> None:
        """enabled returns True when client is enabled."""
        assert ai_service.enabled is True

    def test_disabled_when_client_disabled(
        self,
        ai_config: AIConfig,
        mock_prompt_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_conversation_manager: ConversationManager,
        mock_usage_tracker: MagicMock,
        mock_action_manager: ActionManager,
        mock_executor_registry: ExecutorRegistry,
        mock_summary_generator: MagicMock,
        mock_cache: ResponseCache,
    ) -> None:
        """enabled returns False when client is disabled."""
        client = MockClaudeClient(enabled=False)
        service = AIService(
            client=client,
            config=ai_config,
            prompt_manager=mock_prompt_manager,
            context_builder=mock_context_builder,
            conversation_manager=mock_conversation_manager,
            usage_tracker=mock_usage_tracker,
            action_manager=mock_action_manager,
            executor_registry=mock_executor_registry,
            summary_generator=mock_summary_generator,
            cache=mock_cache,
        )

        assert service.enabled is False


class TestAIServiceHandleChat:
    """Test handle_chat method."""

    async def test_handle_chat_returns_response(
        self,
        ai_service: AIService,
    ) -> None:
        """handle_chat returns AI response with conversation_id."""
        app_state = MockAppState()

        result = await ai_service.handle_chat(
            conversation_id=None,
            message="Hello",
            page="Dashboard",
            page_context={},
            app_state=app_state,
        )

        assert result["conversation_id"] is not None
        assert result["content"] == "Test response."
        assert result["tool_use"] is None

    async def test_handle_chat_creates_conversation(
        self,
        ai_service: AIService,
        mock_conversation_manager: ConversationManager,
    ) -> None:
        """handle_chat creates new conversation when id is None."""
        app_state = MockAppState()

        result = await ai_service.handle_chat(
            conversation_id=None,
            message="Hello",
            page="Dashboard",
            page_context={},
            app_state=app_state,
        )

        # Verify conversation was created
        conversation = await mock_conversation_manager.get_conversation(result["conversation_id"])
        assert conversation is not None

    async def test_handle_chat_records_usage(
        self,
        ai_service: AIService,
        mock_usage_tracker: MagicMock,
    ) -> None:
        """handle_chat records API usage."""
        app_state = MockAppState()

        await ai_service.handle_chat(
            conversation_id=None,
            message="Hello",
            page="Dashboard",
            page_context={},
            app_state=app_state,
        )

        mock_usage_tracker.record_usage.assert_called_once()

    async def test_handle_chat_disabled_returns_error(
        self,
        ai_config: AIConfig,
        mock_prompt_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_conversation_manager: ConversationManager,
        mock_usage_tracker: MagicMock,
        mock_action_manager: ActionManager,
        mock_executor_registry: ExecutorRegistry,
        mock_summary_generator: MagicMock,
        mock_cache: ResponseCache,
    ) -> None:
        """handle_chat returns error when disabled."""
        client = MockClaudeClient(enabled=False)
        service = AIService(
            client=client,
            config=ai_config,
            prompt_manager=mock_prompt_manager,
            context_builder=mock_context_builder,
            conversation_manager=mock_conversation_manager,
            usage_tracker=mock_usage_tracker,
            action_manager=mock_action_manager,
            executor_registry=mock_executor_registry,
            summary_generator=mock_summary_generator,
            cache=mock_cache,
        )
        app_state = MockAppState()

        result = await service.handle_chat(
            conversation_id=None,
            message="Hello",
            page="Dashboard",
            page_context={},
            app_state=app_state,
        )

        assert "not available" in result["content"].lower()


class TestAIServiceInsight:
    """Test get_insight method."""

    async def test_get_insight_returns_insight(
        self,
        ai_service: AIService,
        mock_summary_generator: MagicMock,
    ) -> None:
        """get_insight returns generated insight."""
        app_state = MockAppState()

        result = await ai_service.get_insight(app_state)

        assert result["insight"] == "Test insight"
        assert result["cached"] is False

    async def test_get_insight_uses_cache(
        self,
        ai_service: AIService,
        mock_cache: ResponseCache,
    ) -> None:
        """get_insight returns cached insight if available."""
        await mock_cache.set("insight", {"insight": "Cached insight", "generated_at": "2026-03-06"})
        app_state = MockAppState()

        result = await ai_service.get_insight(app_state)

        assert result["insight"] == "Cached insight"
        assert result["cached"] is True

    async def test_get_insight_caches_result(
        self,
        ai_service: AIService,
        mock_cache: ResponseCache,
    ) -> None:
        """get_insight caches the generated insight."""
        app_state = MockAppState()

        await ai_service.get_insight(app_state)

        cached = await mock_cache.get("insight")
        assert cached is not None
        assert cached["insight"] == "Test insight"


class TestAIServiceDailySummary:
    """Test generate_daily_summary method."""

    async def test_generate_daily_summary_returns_summary(
        self,
        ai_service: AIService,
    ) -> None:
        """generate_daily_summary returns generated summary."""
        app_state = MockAppState()

        result = await ai_service.generate_daily_summary("2026-03-06", app_state)

        assert result["summary"] == "Daily summary text"
        assert result["date"] == "2026-03-06"

    async def test_generate_daily_summary_disabled_returns_error(
        self,
        ai_config: AIConfig,
        mock_prompt_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_conversation_manager: ConversationManager,
        mock_usage_tracker: MagicMock,
        mock_action_manager: ActionManager,
        mock_executor_registry: ExecutorRegistry,
        mock_summary_generator: MagicMock,
        mock_cache: ResponseCache,
    ) -> None:
        """generate_daily_summary returns error when disabled."""
        client = MockClaudeClient(enabled=False)
        service = AIService(
            client=client,
            config=ai_config,
            prompt_manager=mock_prompt_manager,
            context_builder=mock_context_builder,
            conversation_manager=mock_conversation_manager,
            usage_tracker=mock_usage_tracker,
            action_manager=mock_action_manager,
            executor_registry=mock_executor_registry,
            summary_generator=mock_summary_generator,
            cache=mock_cache,
        )
        app_state = MockAppState()

        result = await service.generate_daily_summary("2026-03-06", app_state)

        assert result["summary"] is None
        assert "not available" in result.get("message", "").lower()


class TestAIServiceHandleReject:
    """Test handle_reject method."""

    async def test_handle_reject_returns_rejected_proposal(
        self,
        ai_service: AIService,
        mock_action_manager: ActionManager,
    ) -> None:
        """handle_reject rejects the proposal."""
        # Create a proposal first
        proposal = await mock_action_manager.create_proposal(
            conversation_id="conv_123",
            message_id=None,
            tool_name="propose_allocation_change",
            tool_use_id="tu_123",
            tool_input={"strategy_id": "orb", "new_allocation_pct": 30, "reason": "test"},
        )

        result = await ai_service.handle_reject(proposal.id, reason="Not now")

        assert result["status"] == "rejected"
        assert result["proposal"]["status"] == "rejected"


class TestAIServicePageTags:
    """Test page tag mapping."""

    def test_dashboard_maps_to_session(
        self,
        ai_service: AIService,
    ) -> None:
        """Dashboard page maps to session tag."""
        assert ai_service._get_page_tag("Dashboard") == "session"

    def test_performance_maps_to_research(
        self,
        ai_service: AIService,
    ) -> None:
        """Performance page maps to research tag."""
        assert ai_service._get_page_tag("Performance") == "research"

    def test_unknown_maps_to_general(
        self,
        ai_service: AIService,
    ) -> None:
        """Unknown page maps to general tag."""
        assert ai_service._get_page_tag("UnknownPage") == "general"

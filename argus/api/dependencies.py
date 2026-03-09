"""FastAPI dependencies and shared state for the Command Center API.

AppState holds references to all core system components. It's created during
app startup and injected into routes via FastAPI's dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status

if TYPE_CHECKING:
    from argus.ai.actions import ActionManager
    from argus.ai.cache import ResponseCache
    from argus.ai.client import ClaudeClient
    from argus.ai.context import SystemContextBuilder
    from argus.ai.conversations import ConversationManager
    from argus.ai.executors import ExecutorRegistry
    from argus.ai.prompts import PromptManager
    from argus.ai.summary import DailySummaryGenerator
    from argus.ai.usage import UsageTracker
    from argus.analytics.debrief_service import DebriefService
    from argus.analytics.trade_logger import TradeLogger
    from argus.core.clock import Clock
    from argus.core.config import SystemConfig
    from argus.core.event_bus import EventBus
    from argus.core.events import WatchlistItem
    from argus.core.health import HealthMonitor
    from argus.core.orchestrator import Orchestrator
    from argus.core.risk_manager import RiskManager
    from argus.data.service import DataService
    from argus.data.universe_manager import UniverseManager
    from argus.execution.broker import Broker
    from argus.execution.order_manager import OrderManager
    from argus.intelligence.briefing import BriefingGenerator
    from argus.intelligence.storage import CatalystStorage
    from argus.strategies.base_strategy import BaseStrategy


@dataclass
class AppState:
    """Shared application state for the Command Center API.

    Holds references to all core system components. Created during app
    startup and attached to the FastAPI app.state.

    Attributes:
        event_bus: The system event bus for pub/sub.
        trade_logger: Service for logging and querying trades.
        broker: The active broker implementation.
        health_monitor: System health tracking and alerting.
        risk_manager: Risk evaluation gate for signals.
        order_manager: Position lifecycle management.
        data_service: Market data provider.
        orchestrator: Strategy lifecycle and capital allocation manager.
        strategies: Dict of strategy_id -> BaseStrategy instances.
        clock: Time provider (SystemClock or FixedClock for tests).
        config: System configuration.
        start_time: Unix timestamp of when the system started.
        debrief_service: Service for The Debrief page content.
        cached_watchlist: Cached scanner results for the current session.
        conversation_manager: AI chat conversation persistence.
        usage_tracker: AI API usage tracking.
        ai_client: Claude API client wrapper.
        prompt_manager: AI prompt construction and token budgets.
        context_builder: AI system context builder.
        action_manager: AI action proposal lifecycle manager.
        executor_registry: AI action executor registry.
        ai_summary_generator: AI summary and insight generator.
        ai_cache: AI response cache.
        universe_manager: Universe Manager for viable universe and routing.
        catalyst_storage: Storage for catalyst events and briefs.
        briefing_generator: Pre-market brief generator.
    """

    event_bus: EventBus
    trade_logger: TradeLogger
    broker: Broker
    health_monitor: HealthMonitor
    risk_manager: RiskManager
    order_manager: OrderManager
    data_service: DataService | None = None
    orchestrator: Orchestrator | None = None
    strategies: dict[str, BaseStrategy] = field(default_factory=dict)
    clock: Clock | None = None
    config: SystemConfig | None = None
    start_time: float = 0.0
    debrief_service: DebriefService | None = None
    cached_watchlist: list[WatchlistItem] = field(default_factory=list)
    conversation_manager: ConversationManager | None = None
    usage_tracker: UsageTracker | None = None
    ai_client: ClaudeClient | None = None
    prompt_manager: PromptManager | None = None
    context_builder: SystemContextBuilder | None = None
    action_manager: ActionManager | None = None
    executor_registry: ExecutorRegistry | None = None
    ai_summary_generator: DailySummaryGenerator | None = None
    ai_cache: ResponseCache | None = None
    universe_manager: UniverseManager | None = None
    catalyst_storage: CatalystStorage | None = None
    briefing_generator: BriefingGenerator | None = None


def get_app_state(request: Request) -> AppState:
    """FastAPI dependency to get the shared AppState.

    Args:
        request: The FastAPI request object.

    Returns:
        The AppState instance attached to app.state.

    Usage:
        @router.get("/status")
        async def get_status(state: AppState = Depends(get_app_state)):
            return {"broker_connected": state.broker.is_connected}
    """
    return request.app.state.app_state


def get_debrief_service(state: AppState = Depends(get_app_state)):  # noqa: B008
    """FastAPI dependency to get the DebriefService.

    Args:
        state: The AppState from which to retrieve the service.

    Returns:
        The DebriefService instance.

    Raises:
        HTTPException 503: If the debrief service is not available.
    """
    if state.debrief_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Debrief service not available",
        )
    return state.debrief_service

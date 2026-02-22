"""FastAPI dependencies and shared state for the Command Center API.

AppState holds references to all core system components. It's created during
app startup and injected into routes via FastAPI's dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.core.clock import Clock
    from argus.core.config import SystemConfig
    from argus.core.event_bus import EventBus
    from argus.core.health import HealthMonitor
    from argus.core.risk_manager import RiskManager
    from argus.data.service import DataService
    from argus.execution.broker import Broker
    from argus.execution.order_manager import OrderManager
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
        strategies: Dict of strategy_id -> BaseStrategy instances.
        clock: Time provider (SystemClock or FixedClock for tests).
        config: System configuration.
        start_time: Unix timestamp of when the system started.
    """

    event_bus: EventBus
    trade_logger: TradeLogger
    broker: Broker
    health_monitor: HealthMonitor
    risk_manager: RiskManager
    order_manager: OrderManager
    data_service: DataService | None = None
    strategies: dict[str, BaseStrategy] = field(default_factory=dict)
    clock: Clock | None = None
    config: SystemConfig | None = None
    start_time: float = 0.0


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

"""System context builder for the ARGUS AI Copilot.

Assembles relevant system state into context payloads for Claude API calls.
Combines per-page context with system-wide state.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from argus.api.dependencies import AppState


class SystemContextBuilder:
    """Builds context payloads for Claude API calls.

    Assembles system-wide state and page-specific context into a
    structured dict that PromptManager can format into text.
    """

    # Timezone references
    ET_TZ = ZoneInfo("America/New_York")
    CAPE_TOWN_TZ = ZoneInfo("Africa/Johannesburg")

    async def build_context(
        self,
        page: str,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Assemble full context payload for a Claude API call.

        Args:
            page: Page identifier (Dashboard, Trades, Performance, etc.).
            context_data: Page-specific context data from the frontend.
            app_state: The application state with system references.

        Returns:
            Combined context dict with system-wide and page-specific data.
        """
        # Build system-wide state
        system_state = await self._build_system_state(app_state)

        # Build page-specific context
        page_context = await self._build_page_context(page, context_data, app_state)

        return {
            "system": system_state,
            "page": page,
            "page_context": page_context,
        }

    async def _build_system_state(self, app_state: AppState) -> dict[str, Any]:
        """Build system-wide state shared across all pages.

        Args:
            app_state: The application state.

        Returns:
            Dict with system-wide state information.
        """
        now_utc = datetime.now(ZoneInfo("UTC"))
        now_et = now_utc.astimezone(self.ET_TZ)
        now_local = now_utc.astimezone(self.CAPE_TOWN_TZ)

        state: dict[str, Any] = {
            "current_time": {
                "utc": now_utc.isoformat(),
                "et": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
                "cape_town": now_local.strftime("%Y-%m-%d %H:%M:%S SAST"),
            },
            "active_strategy_count": len(app_state.strategies),
            "circuit_breakers": [],
        }

        # Get regime classification if orchestrator available
        if app_state.orchestrator is not None:
            regime = getattr(app_state.orchestrator, "current_regime", None)
            state["regime"] = str(regime) if regime else "unknown"
        else:
            state["regime"] = "unknown"

        # Get account equity from broker
        if app_state.broker is not None:
            try:
                account = await app_state.broker.get_account()
                if account:
                    state["account_equity"] = getattr(account, "equity", 0.0)
                else:
                    state["account_equity"] = 0.0
            except Exception as e:
                logger.warning("Failed to get account equity: %s", e)
                state["account_equity"] = 0.0
        else:
            state["account_equity"] = 0.0

        # Get daily P&L from trade logger
        if app_state.trade_logger is not None:
            try:
                daily_pnl = await app_state.trade_logger.get_todays_pnl()
                state["daily_pnl"] = daily_pnl
            except Exception as e:
                logger.warning("Failed to get daily P&L: %s", e)
                state["daily_pnl"] = 0.0
        else:
            state["daily_pnl"] = 0.0

        # Check for active circuit breakers
        if app_state.risk_manager is not None:
            try:
                circuit_breaker_active = getattr(
                    app_state.risk_manager, "circuit_breaker_active", False
                )
                if circuit_breaker_active:
                    state["circuit_breakers"].append(
                        {"type": "risk_manager", "reason": "Circuit breaker triggered"}
                    )
            except Exception as e:
                logger.warning("Failed to check circuit breaker status: %s", e)

        return state

    async def _build_page_context(
        self,
        page: str,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build page-specific context.

        Args:
            page: Page identifier.
            context_data: Context data provided by the frontend.
            app_state: Application state for additional lookups.

        Returns:
            Page-specific context dict.
        """
        # Route to page-specific builder
        builder_map = {
            "Dashboard": self._build_dashboard_context,
            "Trades": self._build_trades_context,
            "Performance": self._build_performance_context,
            "Orchestrator": self._build_orchestrator_context,
            "PatternLibrary": self._build_pattern_library_context,
            "Debrief": self._build_debrief_context,
            "System": self._build_system_page_context,
        }

        builder = builder_map.get(page)
        if builder:
            return await builder(context_data, app_state)

        # Default: return context_data as-is
        return context_data

    async def _build_dashboard_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build Dashboard page context.

        Context includes:
        - Portfolio summary (equity, daily P&L)
        - Open positions
        - Regime classification
        """
        result: dict[str, Any] = {}

        # Portfolio summary
        result["portfolio_summary"] = {
            "equity": context_data.get("equity", 0.0),
            "daily_pnl": context_data.get("daily_pnl", 0.0),
            "open_positions": context_data.get("open_positions_count", 0),
        }

        # Open positions
        if "positions" in context_data:
            result["positions"] = context_data["positions"]
        elif app_state.order_manager is not None:
            try:
                managed_positions = app_state.order_manager.get_managed_positions()
                positions_list = []
                for symbol, pos_list in managed_positions.items():
                    for pos in pos_list:
                        if not pos.is_fully_closed:
                            # Compute unrealized P&L if data service is available
                            unrealized = 0.0
                            if app_state.data_service is not None:
                                try:
                                    current_price = await app_state.data_service.get_current_price(
                                        symbol
                                    )
                                    if current_price is not None:
                                        unrealized = (
                                            current_price - pos.entry_price
                                        ) * pos.shares_remaining
                                except Exception:
                                    pass
                            positions_list.append({
                                "symbol": symbol,
                                "strategy_id": pos.strategy_id,
                                "shares": pos.shares_remaining,
                                "entry_price": pos.entry_price,
                                "unrealized_pnl": unrealized,
                                "realized_pnl": pos.realized_pnl,
                            })
                result["positions"] = positions_list
            except Exception as e:
                logger.warning("Failed to build Dashboard positions: %s", e)
                result["positions"] = []
        else:
            result["positions"] = []

        # Regime
        if app_state.orchestrator is not None:
            regime = getattr(app_state.orchestrator, "current_regime", None)
            result["regime"] = str(regime) if regime else "normal"
        else:
            result["regime"] = context_data.get("regime", "unknown")

        return result

    async def _build_trades_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build Trades page context.

        Context includes:
        - Recent trades (last 20)
        - Active filters
        """
        result: dict[str, Any] = {}

        # Recent trades
        if "recent_trades" in context_data:
            result["recent_trades"] = context_data["recent_trades"]
        elif app_state.trade_logger is not None:
            try:
                trades = await app_state.trade_logger.query_trades(limit=20)
                result["recent_trades"] = [
                    {
                        "symbol": t.get("symbol"),
                        "pnl": t.get("net_pnl", 0),
                        "outcome": t.get("outcome"),
                        "strategy_id": t.get("strategy_id"),
                    }
                    for t in trades
                ]
            except Exception as e:
                logger.warning("Failed to get recent trades: %s", e)
                result["recent_trades"] = []
        else:
            result["recent_trades"] = []

        # Filters
        result["filters"] = context_data.get("filters", {})

        return result

    async def _build_performance_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build Performance page context.

        Context includes:
        - Performance metrics
        - Selected timeframe
        """
        result: dict[str, Any] = {}

        # Metrics from context data (computed by frontend or API)
        if "metrics" in context_data:
            result["metrics"] = context_data["metrics"]
        else:
            result["metrics"] = {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "net_pnl": 0.0,
            }

        # Timeframe
        result["timeframe"] = context_data.get("timeframe", "all_time")

        return result

    async def _build_orchestrator_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build Orchestrator page context.

        Context includes:
        - Strategy allocations
        - Regime classification
        - Schedule state
        """
        result: dict[str, Any] = {}

        # Allocations
        if "allocations" in context_data:
            result["allocations"] = context_data["allocations"]
        elif app_state.orchestrator is not None:
            try:
                allocations = getattr(app_state.orchestrator, "allocations", {})
                result["allocations"] = [
                    {"strategy_id": sid, "pct": pct * 100}
                    for sid, pct in allocations.items()
                ]
            except Exception as e:
                logger.warning("Failed to get strategy allocations: %s", e)
                result["allocations"] = []
        else:
            result["allocations"] = []

        # Regime
        if app_state.orchestrator is not None:
            regime = getattr(app_state.orchestrator, "current_regime", None)
            result["regime"] = str(regime) if regime else "normal"
        else:
            result["regime"] = context_data.get("regime", "unknown")

        # Schedule state
        result["schedule_state"] = context_data.get("schedule_state", "unknown")

        return result

    async def _build_pattern_library_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build Pattern Library page context.

        Context includes:
        - Selected pattern
        - Pattern statistics
        """
        result: dict[str, Any] = {}

        if "selected_pattern" in context_data:
            result["selected_pattern"] = context_data["selected_pattern"]
        else:
            result["selected_pattern"] = None

        return result

    async def _build_debrief_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build Debrief page context.

        Context includes:
        - Today's summary data
        - Selected conversation
        """
        result: dict[str, Any] = {}

        # Today's summary
        if "today_summary" in context_data:
            result["today_summary"] = context_data["today_summary"]
        elif app_state.trade_logger is not None:
            try:
                daily_pnl = await app_state.trade_logger.get_todays_pnl()
                trades = await app_state.trade_logger.query_trades(limit=100)
                today_trades = [
                    t
                    for t in trades
                    if t.get("exit_time", "").startswith(
                        datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
                    )
                ]
                result["today_summary"] = {
                    "total_trades": len(today_trades),
                    "net_pnl": daily_pnl,
                }
            except Exception as e:
                logger.warning("Failed to build Debrief summary: %s", e)
                result["today_summary"] = {"total_trades": 0, "net_pnl": 0.0}
        else:
            result["today_summary"] = {"total_trades": 0, "net_pnl": 0.0}

        # Selected conversation
        result["selected_conversation"] = context_data.get("selected_conversation")

        return result

    async def _build_system_page_context(
        self,
        context_data: dict[str, Any],
        app_state: AppState,
    ) -> dict[str, Any]:
        """Build System page context.

        Context includes:
        - System health
        - Connection states
        - Configuration summary
        """
        result: dict[str, Any] = {}

        # Health
        if app_state.health_monitor is not None:
            try:
                status = getattr(app_state.health_monitor, "status", "unknown")
                result["health"] = {
                    "status": str(status),
                    "uptime": context_data.get("uptime", "N/A"),
                }
            except Exception as e:
                logger.warning("Failed to get health monitor status: %s", e)
                result["health"] = {"status": "unknown", "uptime": "N/A"}
        else:
            result["health"] = context_data.get("health", {"status": "unknown"})

        # Connections
        connections: dict[str, str] = {}

        if app_state.broker is not None:
            try:
                connected = getattr(app_state.broker, "is_connected", False)
                connections["broker"] = "connected" if connected else "disconnected"
            except Exception as e:
                logger.warning("Failed to check broker connection: %s", e)
                connections["broker"] = "unknown"

        if app_state.data_service is not None:
            try:
                connected = getattr(app_state.data_service, "is_connected", False)
                connections["data_feed"] = "connected" if connected else "disconnected"
            except Exception as e:
                logger.warning("Failed to check data feed connection: %s", e)
                connections["data_feed"] = "unknown"

        result["connections"] = connections

        return result

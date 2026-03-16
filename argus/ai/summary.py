"""Summary generation for the AI Copilot.

Provides:
- DailySummaryGenerator: End-of-day trading summaries
- Dashboard insight generation with caching
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from argus.ai.cache import ResponseCache
    from argus.ai.client import ClaudeClient
    from argus.ai.usage import UsageTracker
    from argus.api.dependencies import AppState

logger = logging.getLogger(__name__)


# System prompt additions for summary generation
DAILY_SUMMARY_SYSTEM_PROMPT = """Generate a concise end-of-day trading summary. Be factual. Reference specific trades and numbers. Note any unusual patterns or concerns. Keep it under 500 words."""

INSIGHT_SYSTEM_PROMPT = """Generate a brief (2-3 sentence) insight about the current trading session state. Be specific, not generic."""


class DailySummaryGenerator:
    """Generates end-of-day trading summaries using Claude.

    Assembles data from multiple sources:
    - Trade Logger: today's trades, P&L, R-multiples, hold durations
    - Orchestrator: regime classification, allocation changes, suspensions
    - Risk Manager: rejections, modifications, circuit breakers
    - Performance context: daily P&L vs target, weekly running total, win rate
    - Per-strategy breakdown
    """

    def __init__(
        self,
        client: ClaudeClient | None,
        usage_tracker: UsageTracker | None = None,
        cache: ResponseCache | None = None,
    ) -> None:
        """Initialize the summary generator.

        Args:
            client: ClaudeClient for API calls.
            usage_tracker: Optional usage tracker for recording API usage.
            cache: Optional response cache for insight caching.
        """
        self._client = client
        self._usage_tracker = usage_tracker
        self._cache = cache

    async def generate(self, date: str, app_state: AppState) -> str:
        """Generate a daily summary for the given date.

        Args:
            date: Date in YYYY-MM-DD format.
            app_state: Application state for data access.

        Returns:
            Generated summary text.
        """
        if self._client is None or not self._client.enabled:
            return "AI summary generation not available."

        # Assemble data from all sources
        data = await self._assemble_daily_data(date, app_state)

        # Build prompt
        prompt = self._build_daily_prompt(date, data)

        # Call Claude API
        messages = [{"role": "user", "content": prompt}]
        response, usage_record = await self._client.send_message(
            messages,
            system=DAILY_SUMMARY_SYSTEM_PROMPT,
            tools=None,
            stream=False,
        )

        # Record usage
        if self._usage_tracker is not None:
            await self._usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=usage_record.input_tokens,
                output_tokens=usage_record.output_tokens,
                model=usage_record.model,
                estimated_cost_usd=usage_record.estimated_cost_usd,
                endpoint="summary",
            )

        # Extract content
        if response.get("type") == "error":
            return f"Error generating summary: {response.get('message', 'Unknown error')}"

        content_parts = []
        for block in response.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))

        return "\n".join(content_parts) or "No summary generated."

    async def generate_insight(self, app_state: AppState) -> str:
        """Generate a brief insight for the Dashboard.

        Uses caching to avoid redundant API calls.

        Args:
            app_state: Application state for data access.

        Returns:
            Generated insight text.
        """
        if self._client is None or not self._client.enabled:
            return "AI insights not available."

        # Check cache first
        cache_key = "insight"
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Returning cached insight")
                return cached.get("insight", "")

        try:
            # Assemble lighter data
            data = await self._assemble_insight_data(app_state)

            # Build prompt
            prompt = self._build_insight_prompt(data)

            # Call Claude API
            messages = [{"role": "user", "content": prompt}]
            response, usage_record = await self._client.send_message(
                messages,
                system=INSIGHT_SYSTEM_PROMPT,
                tools=None,
                stream=False,
            )

            # Record usage
            if self._usage_tracker is not None:
                await self._usage_tracker.record_usage(
                    conversation_id=None,
                    input_tokens=usage_record.input_tokens,
                    output_tokens=usage_record.output_tokens,
                    model=usage_record.model,
                    estimated_cost_usd=usage_record.estimated_cost_usd,
                    endpoint="insight",
                )

            # Extract content
            if response.get("type") == "error":
                insight = f"Unable to generate insight: {response.get('message', 'Unknown error')}"
            else:
                content_parts = []
                for block in response.get("content", []):
                    if block.get("type") == "text":
                        content_parts.append(block.get("text", ""))
                insight = "\n".join(content_parts) or "No insight generated."

        except Exception as e:
            logger.error(f"Error generating insight: {e}")
            insight = "Insight temporarily unavailable."

        # Cache the result
        if self._cache is not None:
            await self._cache.set(cache_key, {"insight": insight})

        return insight

    async def _assemble_daily_data(self, date: str, app_state: AppState) -> dict[str, Any]:
        """Assemble all data needed for daily summary.

        Sources:
        a. Today's trades from Trade Logger
        b. Orchestrator decisions
        c. Risk events
        d. Performance context
        e. Per-strategy breakdown
        """
        data: dict[str, Any] = {"date": date}

        # a. Today's trades
        if app_state.trade_logger is not None:
            try:
                trades = await app_state.trade_logger.get_trades_by_date(date)
                data["trades"] = {
                    "count": len(trades),
                    "entries": [
                        {
                            "symbol": t.symbol,
                            "strategy_id": t.strategy_id,
                            "side": t.side.value,
                            "entry_price": t.entry_price,
                            "exit_price": t.exit_price,
                            "net_pnl": t.net_pnl,
                            "r_multiple": t.r_multiple,
                            "hold_duration_seconds": t.hold_duration_seconds,
                            "outcome": t.outcome.value,
                            "exit_reason": t.exit_reason.value,
                        }
                        for t in trades
                    ],
                    "total_pnl": sum(t.net_pnl for t in trades),
                    "winners": len([t for t in trades if t.net_pnl > 0]),
                    "losers": len([t for t in trades if t.net_pnl < 0]),
                    "breakeven": len([t for t in trades if t.net_pnl == 0]),
                }
            except Exception as e:
                logger.warning(f"Failed to get trades for summary: {e}")
                data["trades"] = {"count": 0, "entries": [], "total_pnl": 0}

        # b. Orchestrator decisions
        if app_state.trade_logger is not None:
            try:
                decisions, _ = await app_state.trade_logger.get_orchestrator_decisions(
                    limit=50,
                    date=date,
                )
                data["orchestrator_decisions"] = decisions
            except Exception as e:
                logger.warning(f"Failed to get orchestrator decisions: {e}")
                data["orchestrator_decisions"] = []

        # Current regime
        if app_state.orchestrator is not None:
            data["current_regime"] = str(app_state.orchestrator.current_regime)
        else:
            data["current_regime"] = "unknown"

        # c. Risk events (approximate from decisions)
        risk_events = []
        for decision in data.get("orchestrator_decisions", []):
            if decision.get("decision_type") in ("rejection", "modification", "circuit_breaker"):
                risk_events.append(decision)
        data["risk_events"] = risk_events

        # d. Performance context
        if app_state.trade_logger is not None:
            try:
                daily_summary = await app_state.trade_logger.get_daily_summary(date)
                data["performance"] = {
                    "daily_pnl": daily_summary.net_pnl,
                    "win_rate": daily_summary.win_rate,
                    "profit_factor": daily_summary.profit_factor,
                    "avg_r_multiple": daily_summary.avg_r_multiple,
                }
            except Exception as e:
                logger.warning(f"Failed to get performance context: {e}")
                data["performance"] = {}

        # e. Per-strategy breakdown
        strategy_breakdown: dict[str, dict[str, Any]] = {}
        if app_state.trade_logger is not None:
            try:
                trades = await app_state.trade_logger.get_trades_by_date(date)
                for trade in trades:
                    sid = trade.strategy_id
                    if sid not in strategy_breakdown:
                        strategy_breakdown[sid] = {
                            "trade_count": 0,
                            "pnl": 0.0,
                            "wins": 0,
                            "losses": 0,
                        }
                    strategy_breakdown[sid]["trade_count"] += 1
                    strategy_breakdown[sid]["pnl"] += trade.net_pnl
                    if trade.net_pnl > 0:
                        strategy_breakdown[sid]["wins"] += 1
                    elif trade.net_pnl < 0:
                        strategy_breakdown[sid]["losses"] += 1
            except Exception as e:
                logger.warning("Failed to build strategy breakdown: %s", e)

        # Calculate win rate per strategy
        for sid, stats in strategy_breakdown.items():
            total = stats["wins"] + stats["losses"]
            stats["win_rate"] = stats["wins"] / total if total > 0 else 0.0

        data["strategy_breakdown"] = strategy_breakdown

        return data

    async def _assemble_insight_data(self, app_state: AppState) -> dict[str, Any]:
        """Assemble lighter data for Dashboard insight.

        Includes:
        - Current positions
        - Daily P&L
        - Regime
        - Active alerts
        """
        data: dict[str, Any] = {}

        # Current time
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        data["current_time"] = now_et.strftime("%H:%M ET")

        market_open_minutes = 9 * 60 + 30  # 9:30 ET
        market_close_minutes = 16 * 60  # 16:00 ET
        now_minutes = now_et.hour * 60 + now_et.minute

        if now_minutes < market_open_minutes:
            data["market_open"] = False
            data["session_status"] = "pre_market"
            data["session_elapsed_minutes"] = None
            data["minutes_until_open"] = market_open_minutes - now_minutes
        elif now_minutes <= market_close_minutes:
            data["market_open"] = True
            data["session_status"] = "open"
            data["session_elapsed_minutes"] = now_minutes - market_open_minutes
            data["minutes_until_open"] = None
        else:
            data["market_open"] = False
            data["session_status"] = "closed"
            data["session_elapsed_minutes"] = None
            data["minutes_until_open"] = None

        # Current positions
        if app_state.order_manager is not None:
            try:
                managed = app_state.order_manager.get_managed_positions()
                positions = []
                for symbol, pos_list in managed.items():
                    for pos in pos_list:
                        if not pos.is_fully_closed:
                            # Compute unrealized P&L if data service available
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
                            positions.append({
                                "symbol": symbol,
                                "shares": pos.shares_remaining,
                                "unrealized_pnl": unrealized,
                                "strategy_id": pos.strategy_id,
                            })
                data["positions"] = positions
            except Exception as e:
                logger.warning(f"Error assembling positions for insight: {e}")
                data["positions"] = []
        else:
            data["positions"] = []

        # Daily P&L
        if app_state.trade_logger is not None:
            try:
                data["daily_pnl"] = await app_state.trade_logger.get_todays_pnl()
            except Exception as e:
                logger.warning("Failed to get daily P&L for insight: %s", e)
                data["daily_pnl"] = 0.0
        else:
            data["daily_pnl"] = 0.0

        # Regime
        if app_state.orchestrator is not None:
            data["regime"] = str(app_state.orchestrator.current_regime)
        else:
            data["regime"] = "unknown"

        # Active alerts (circuit breakers)
        alerts = []
        if app_state.risk_manager is not None:
            if app_state.risk_manager.circuit_breaker_active:
                alerts.append("Circuit breaker active")
        data["alerts"] = alerts

        return data

    def _build_daily_prompt(self, date: str, data: dict[str, Any]) -> str:
        """Build the prompt for daily summary generation."""
        lines = [f"Generate a trading summary for {date}.", ""]

        # Trade summary
        trades = data.get("trades", {})
        lines.append(f"## Trades ({trades.get('count', 0)} total)")
        lines.append(f"- Total P&L: ${trades.get('total_pnl', 0):,.2f}")
        lines.append(f"- Winners: {trades.get('winners', 0)}")
        lines.append(f"- Losers: {trades.get('losers', 0)}")
        lines.append("")

        # Individual trades
        if trades.get("entries"):
            lines.append("### Trade Details")
            for t in trades["entries"][:10]:  # Limit to 10 for prompt size
                hold_mins = t.get("hold_duration_seconds", 0) / 60
                lines.append(
                    f"- {t['symbol']} ({t['strategy_id']}): ${t['net_pnl']:+,.2f} "
                    f"({t['r_multiple']:.1f}R, {hold_mins:.0f}min, {t['exit_reason']})"
                )
            if len(trades["entries"]) > 10:
                lines.append(f"  ... and {len(trades['entries']) - 10} more trades")
            lines.append("")

        # Per-strategy breakdown
        breakdown = data.get("strategy_breakdown", {})
        if breakdown:
            lines.append("## Per-Strategy Breakdown")
            for sid, stats in breakdown.items():
                lines.append(
                    f"- {sid}: {stats['trade_count']} trades, "
                    f"${stats['pnl']:+,.2f}, {stats['win_rate']:.0%} win rate"
                )
            lines.append("")

        # Regime
        lines.append(f"## Market Regime: {data.get('current_regime', 'unknown')}")
        lines.append("")

        # Performance context
        perf = data.get("performance", {})
        if perf:
            lines.append("## Performance Metrics")
            lines.append(f"- Win Rate: {perf.get('win_rate', 0):.0%}")
            lines.append(f"- Profit Factor: {perf.get('profit_factor', 0):.2f}")
            lines.append(f"- Avg R-Multiple: {perf.get('avg_r_multiple', 0):.2f}")
            lines.append("")

        # Risk events
        risk_events = data.get("risk_events", [])
        if risk_events:
            lines.append(f"## Risk Events ({len(risk_events)})")
            for event in risk_events[:5]:
                lines.append(f"- {event.get('decision_type')}: {event.get('rationale', 'N/A')}")
            lines.append("")

        lines.append("Please provide a concise analysis of this trading day.")

        return "\n".join(lines)

    def _build_insight_prompt(self, data: dict[str, Any]) -> str:
        """Build the prompt for Dashboard insight generation."""
        lines = ["Current trading session state:", ""]

        # Time and market status
        lines.append(f"Time: {data.get('current_time', 'unknown')}")
        session_status = data.get("session_status", "unknown")
        lines.append(f"Market: {session_status}")
        elapsed = data.get("session_elapsed_minutes")
        if elapsed is not None:
            lines.append(f"Session elapsed: {elapsed} minutes (since 9:30 ET)")
        minutes_until = data.get("minutes_until_open")
        if minutes_until is not None:
            lines.append(f"Minutes until open: {minutes_until}")
        lines.append(f"Regime: {data.get('regime', 'unknown')}")
        lines.append("")

        # Positions
        positions = data.get("positions", [])
        if positions:
            lines.append(f"Open Positions ({len(positions)}):")
            for pos in positions[:5]:
                lines.append(
                    f"- {pos['symbol']}: {pos['shares']} shares, "
                    f"${pos.get('unrealized_pnl', 0):+,.2f} unrealized"
                )
        else:
            lines.append("No open positions.")
        lines.append("")

        # Daily P&L
        lines.append(f"Daily P&L: ${data.get('daily_pnl', 0):+,.2f}")
        lines.append("")

        # Alerts
        alerts = data.get("alerts", [])
        if alerts:
            lines.append("Active Alerts:")
            for alert in alerts:
                lines.append(f"- {alert}")

        lines.append("")
        lines.append("Provide a brief, specific insight about this session state.")

        return "\n".join(lines)

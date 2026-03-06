"""Tests for DailySummaryGenerator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.ai.cache import ResponseCache
from argus.ai.client import UsageRecord
from argus.ai.summary import DailySummaryGenerator


@dataclass
class MockTrade:
    """Mock trade for testing."""

    symbol: str = "AAPL"
    strategy_id: str = "orb_breakout"
    side: MagicMock = field(default_factory=lambda: MagicMock(value="long"))
    entry_price: float = 150.0
    exit_price: float = 152.0
    net_pnl: float = 200.0
    r_multiple: float = 2.0
    hold_duration_seconds: int = 600
    outcome: MagicMock = field(default_factory=lambda: MagicMock(value="win"))
    exit_reason: MagicMock = field(default_factory=lambda: MagicMock(value="target"))


@dataclass
class MockDailySummary:
    """Mock daily summary for testing."""

    net_pnl: float = 500.0
    win_rate: float = 0.6
    profit_factor: float = 2.0
    avg_r_multiple: float = 1.5


@dataclass
class MockOrchestrator:
    """Mock orchestrator for testing."""

    current_regime: str = "NEUTRAL"


@dataclass
class MockRiskManager:
    """Mock risk manager for testing."""

    circuit_breaker_active: bool = False


@dataclass
class MockOrderManager:
    """Mock order manager for testing."""

    def get_managed_positions(self) -> dict[str, list[Any]]:
        return {}


class MockClaudeClient:
    """Mock Claude client for testing."""

    def __init__(self, enabled: bool = True, response_text: str = "Test summary.") -> None:
        self.enabled = enabled
        self._response_text = response_text

    async def send_message(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> tuple[dict[str, Any], UsageRecord]:
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


class MockUsageTracker:
    """Mock usage tracker for testing."""

    def __init__(self) -> None:
        self.recorded_usages: list[dict[str, Any]] = []

    async def record_usage(
        self,
        conversation_id: str | None,
        input_tokens: int,
        output_tokens: int,
        model: str,
        estimated_cost_usd: float,
        endpoint: str | None = None,
    ) -> None:
        self.recorded_usages.append({
            "conversation_id": conversation_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "estimated_cost_usd": estimated_cost_usd,
            "endpoint": endpoint,
        })


class MockTradeLogger:
    """Mock trade logger for testing."""

    def __init__(
        self,
        trades: list[MockTrade] | None = None,
        daily_summary: MockDailySummary | None = None,
    ) -> None:
        self._trades = trades or [MockTrade()]
        self._daily_summary = daily_summary or MockDailySummary()

    async def get_trades_by_date(self, date: str) -> list[MockTrade]:
        return self._trades

    async def get_orchestrator_decisions(
        self,
        limit: int = 50,
        date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        return [], 0

    async def get_daily_summary(self, date: str) -> MockDailySummary:
        return self._daily_summary

    async def get_todays_pnl(self) -> float:
        return sum(t.net_pnl for t in self._trades)


@dataclass
class MockAppState:
    """Mock app state for testing."""

    trade_logger: MockTradeLogger | None = None
    orchestrator: MockOrchestrator | None = None
    risk_manager: MockRiskManager | None = None
    order_manager: MockOrderManager | None = None


class TestDailySummaryGeneratorGenerate:
    """Test DailySummaryGenerator.generate method."""

    async def test_generate_returns_summary_when_enabled(self) -> None:
        """generate returns AI-generated summary when client enabled."""
        client = MockClaudeClient(enabled=True, response_text="Today was a good trading day.")
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState(trade_logger=MockTradeLogger())

        result = await generator.generate("2026-03-06", app_state)

        assert result == "Today was a good trading day."

    async def test_generate_returns_unavailable_when_disabled(self) -> None:
        """generate returns unavailable message when client disabled."""
        client = MockClaudeClient(enabled=False)
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState()

        result = await generator.generate("2026-03-06", app_state)

        assert result == "AI summary generation not available."

    async def test_generate_returns_unavailable_when_no_client(self) -> None:
        """generate returns unavailable message when no client."""
        generator = DailySummaryGenerator(client=None)
        app_state = MockAppState()

        result = await generator.generate("2026-03-06", app_state)

        assert result == "AI summary generation not available."

    async def test_generate_records_usage(self) -> None:
        """generate records API usage via tracker."""
        client = MockClaudeClient(enabled=True)
        usage_tracker = MockUsageTracker()
        generator = DailySummaryGenerator(client=client, usage_tracker=usage_tracker)
        app_state = MockAppState(trade_logger=MockTradeLogger())

        await generator.generate("2026-03-06", app_state)

        assert len(usage_tracker.recorded_usages) == 1
        usage = usage_tracker.recorded_usages[0]
        assert usage["endpoint"] == "summary"
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50

    async def test_generate_handles_error_response(self) -> None:
        """generate handles error response from client."""
        client = MockClaudeClient(enabled=True)
        client.send_message = AsyncMock(return_value=(
            {"type": "error", "message": "API error"},
            UsageRecord(input_tokens=10, output_tokens=0, model="claude", estimated_cost_usd=0.0),
        ))
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState(trade_logger=MockTradeLogger())

        result = await generator.generate("2026-03-06", app_state)

        assert "Error generating summary" in result
        assert "API error" in result


class TestDailySummaryGeneratorInsight:
    """Test DailySummaryGenerator.generate_insight method."""

    async def test_insight_returns_ai_response(self) -> None:
        """generate_insight returns AI-generated insight."""
        client = MockClaudeClient(enabled=True, response_text="Markets are calm today.")
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState(
            trade_logger=MockTradeLogger(),
            orchestrator=MockOrchestrator(),
            risk_manager=MockRiskManager(),
            order_manager=MockOrderManager(),
        )

        result = await generator.generate_insight(app_state)

        assert result == "Markets are calm today."

    async def test_insight_uses_cache(self) -> None:
        """generate_insight returns cached insight if available."""
        client = MockClaudeClient(enabled=True, response_text="Fresh insight")
        cache = ResponseCache(default_ttl=60)
        await cache.set("insight", {"insight": "Cached insight"})
        generator = DailySummaryGenerator(client=client, cache=cache)
        app_state = MockAppState()

        result = await generator.generate_insight(app_state)

        assert result == "Cached insight"

    async def test_insight_caches_result(self) -> None:
        """generate_insight caches the generated insight."""
        client = MockClaudeClient(enabled=True, response_text="New insight to cache")
        cache = ResponseCache(default_ttl=60)
        generator = DailySummaryGenerator(client=client, cache=cache)
        app_state = MockAppState(
            trade_logger=MockTradeLogger(),
            orchestrator=MockOrchestrator(),
            risk_manager=MockRiskManager(),
            order_manager=MockOrderManager(),
        )

        await generator.generate_insight(app_state)

        cached = await cache.get("insight")
        assert cached is not None
        assert cached["insight"] == "New insight to cache"

    async def test_insight_returns_unavailable_when_disabled(self) -> None:
        """generate_insight returns unavailable when client disabled."""
        client = MockClaudeClient(enabled=False)
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState()

        result = await generator.generate_insight(app_state)

        assert result == "AI insights not available."

    async def test_insight_records_usage(self) -> None:
        """generate_insight records usage with 'insight' endpoint."""
        client = MockClaudeClient(enabled=True)
        usage_tracker = MockUsageTracker()
        generator = DailySummaryGenerator(client=client, usage_tracker=usage_tracker)
        app_state = MockAppState(
            trade_logger=MockTradeLogger(),
            orchestrator=MockOrchestrator(),
            risk_manager=MockRiskManager(),
            order_manager=MockOrderManager(),
        )

        await generator.generate_insight(app_state)

        assert len(usage_tracker.recorded_usages) == 1
        assert usage_tracker.recorded_usages[0]["endpoint"] == "insight"


class TestDailySummaryGeneratorDataAssembly:
    """Test data assembly methods."""

    async def test_assemble_daily_data_includes_trades(self) -> None:
        """_assemble_daily_data includes trade data."""
        client = MockClaudeClient(enabled=True)
        generator = DailySummaryGenerator(client=client)
        trades = [
            MockTrade(symbol="AAPL", net_pnl=100.0),
            MockTrade(symbol="TSLA", net_pnl=-50.0),
        ]
        app_state = MockAppState(trade_logger=MockTradeLogger(trades=trades))

        data = await generator._assemble_daily_data("2026-03-06", app_state)

        assert data["trades"]["count"] == 2
        assert data["trades"]["total_pnl"] == 50.0
        assert data["trades"]["winners"] == 1
        assert data["trades"]["losers"] == 1

    async def test_assemble_daily_data_includes_regime(self) -> None:
        """_assemble_daily_data includes current regime."""
        client = MockClaudeClient(enabled=True)
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState(
            trade_logger=MockTradeLogger(),
            orchestrator=MockOrchestrator(current_regime="RISK_ON"),
        )

        data = await generator._assemble_daily_data("2026-03-06", app_state)

        assert data["current_regime"] == "RISK_ON"

    async def test_assemble_insight_data_includes_positions(self) -> None:
        """_assemble_insight_data includes position data."""
        client = MockClaudeClient(enabled=True)
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState(
            trade_logger=MockTradeLogger(),
            orchestrator=MockOrchestrator(),
            risk_manager=MockRiskManager(),
            order_manager=MockOrderManager(),
        )

        data = await generator._assemble_insight_data(app_state)

        assert "positions" in data
        assert "daily_pnl" in data
        assert "regime" in data
        assert "alerts" in data

    async def test_assemble_insight_data_includes_circuit_breaker_alert(self) -> None:
        """_assemble_insight_data includes circuit breaker alert."""
        client = MockClaudeClient(enabled=True)
        generator = DailySummaryGenerator(client=client)
        app_state = MockAppState(
            trade_logger=MockTradeLogger(),
            orchestrator=MockOrchestrator(),
            risk_manager=MockRiskManager(circuit_breaker_active=True),
            order_manager=MockOrderManager(),
        )

        data = await generator._assemble_insight_data(app_state)

        assert "Circuit breaker active" in data["alerts"]

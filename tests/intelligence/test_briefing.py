"""Tests for BriefingGenerator.

Sprint 23.5 Session 4 — DEC-164
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from argus.intelligence.briefing import BriefingGenerator
from argus.intelligence.config import BriefingConfig
from argus.intelligence.models import (
    ClassifiedCatalyst,
    IntelligenceBrief,
    compute_headline_hash,
)
from argus.intelligence.storage import CatalystStorage

_ET = ZoneInfo("America/New_York")


@pytest.fixture
async def storage() -> CatalystStorage:
    """Create an in-memory storage instance."""
    s = CatalystStorage(":memory:")
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock ClaudeClient."""
    client = MagicMock()
    client.enabled = True
    return client


@pytest.fixture
def mock_usage_tracker() -> MagicMock:
    """Create a mock UsageTracker."""
    tracker = MagicMock()
    tracker.record_usage = AsyncMock()
    return tracker


@pytest.fixture
def briefing_config() -> BriefingConfig:
    """Create a briefing configuration."""
    return BriefingConfig(max_symbols=30)


def make_catalyst(
    symbol: str,
    headline: str,
    category: str = "news_sentiment",
    quality_score: float = 50.0,
    trading_relevance: str = "medium",
    hours_ago: int = 1,
) -> ClassifiedCatalyst:
    """Create a test catalyst."""
    now = datetime.now(_ET)
    return ClassifiedCatalyst(
        headline=headline,
        symbol=symbol,
        source="test",
        published_at=now - timedelta(hours=hours_ago),
        fetched_at=now,
        category=category,
        quality_score=quality_score,
        summary=f"Summary for {headline}",
        trading_relevance=trading_relevance,
        classified_by="test",
        classified_at=now,
        headline_hash=compute_headline_hash(headline),
    )


class TestBriefingGenerator:
    """Tests for BriefingGenerator."""

    @pytest.mark.asyncio
    async def test_generate_brief_with_catalysts_produces_5_section_markdown(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        briefing_config: BriefingConfig,
    ) -> None:
        """Generate brief with catalysts produces markdown with all 5 sections."""
        # Store catalysts of different categories
        catalysts = [
            make_catalyst("AAPL", "AAPL Q3 earnings beat", "earnings", 85, "high"),
            make_catalyst("TSLA", "CEO insider purchase", "insider_trade", 70, "high"),
            make_catalyst("NVDA", "Analyst upgrade to buy", "analyst_action", 65, "medium"),
            make_catalyst("GOOG", "FDA approval expected", "regulatory", 60, "medium"),
            make_catalyst("META", "Market sentiment positive", "news_sentiment", 50, "low"),
        ]
        for cat in catalysts:
            await storage.store_catalyst(cat)

        # Mock Claude response
        mock_response = {
            "type": "message",
            "content": [
                {
                    "type": "text",
                    "text": """## Top Catalysts
1. **AAPL** (earnings, 85): Q3 earnings beat expectations

## Earnings Calendar
- **AAPL**: Q3 earnings beat

## Insider Activity
- **TSLA**: CEO insider purchase

## Analyst Actions
- **NVDA**: Upgrade to buy rating

## Risk Alerts
None today.""",
                }
            ],
        }
        mock_usage = MagicMock()
        mock_usage.input_tokens = 500
        mock_usage.output_tokens = 200
        mock_usage.model = "claude-3-opus"
        mock_usage.estimated_cost_usd = 0.05

        mock_client.send_message = AsyncMock(return_value=(mock_response, mock_usage))

        generator = BriefingGenerator(
            mock_client, storage, mock_usage_tracker, briefing_config
        )

        symbols = ["AAPL", "TSLA", "NVDA", "GOOG", "META"]
        brief = await generator.generate_brief(symbols)

        assert brief is not None
        assert brief.brief_type == "premarket"
        assert brief.catalyst_count == 5
        assert len(brief.symbols_covered) == 5

        # Check markdown has all 5 sections
        assert "## Top Catalysts" in brief.content
        assert "## Earnings Calendar" in brief.content
        assert "## Insider Activity" in brief.content
        assert "## Analyst Actions" in brief.content
        assert "## Risk Alerts" in brief.content

    @pytest.mark.asyncio
    async def test_generate_brief_without_catalysts_produces_no_catalysts_message(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        briefing_config: BriefingConfig,
    ) -> None:
        """Generate brief without catalysts produces minimal message."""
        generator = BriefingGenerator(
            mock_client, storage, mock_usage_tracker, briefing_config
        )

        symbols = ["AAPL", "TSLA"]
        brief = await generator.generate_brief(symbols)

        assert brief is not None
        assert "No material catalysts detected" in brief.content
        assert brief.catalyst_count == 0
        assert brief.generation_cost_usd == 0.0

        # Claude should NOT be called for empty catalysts
        mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_cost_tracked_via_usage_tracker(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        briefing_config: BriefingConfig,
    ) -> None:
        """Generation cost is tracked via UsageTracker."""
        # Store a catalyst
        cat = make_catalyst("AAPL", "AAPL earnings", "earnings", 80, "high")
        await storage.store_catalyst(cat)

        # Mock Claude response
        mock_response = {
            "type": "message",
            "content": [{"type": "text", "text": "## Top Catalysts\n..."}],
        }
        mock_usage = MagicMock()
        mock_usage.input_tokens = 500
        mock_usage.output_tokens = 200
        mock_usage.model = "claude-3-opus"
        mock_usage.estimated_cost_usd = 0.05

        mock_client.send_message = AsyncMock(return_value=(mock_response, mock_usage))

        generator = BriefingGenerator(
            mock_client, storage, mock_usage_tracker, briefing_config
        )

        brief = await generator.generate_brief(["AAPL"])

        # Verify usage tracker was called
        mock_usage_tracker.record_usage.assert_called_once()
        call_args = mock_usage_tracker.record_usage.call_args

        # Check the call arguments
        assert call_args.kwargs["input_tokens"] == 500
        assert call_args.kwargs["output_tokens"] == 200
        assert call_args.kwargs["model"] == "claude-3-opus"
        assert call_args.kwargs["estimated_cost_usd"] == 0.05
        assert call_args.kwargs["endpoint"] == "briefing"

    @pytest.mark.asyncio
    async def test_symbols_capped_at_max_symbols_config(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
    ) -> None:
        """Symbols are capped at max_symbols from config."""
        # Config with max_symbols = 3
        config = BriefingConfig(max_symbols=3)

        # Store catalysts for 5 different symbols
        symbols = ["AAPL", "TSLA", "NVDA", "GOOG", "META"]
        for symbol in symbols:
            cat = make_catalyst(symbol, f"{symbol} news", "news_sentiment", 50, "medium")
            await storage.store_catalyst(cat)

        # Mock Claude response (won't be called since we check capping)
        mock_response = {
            "type": "message",
            "content": [{"type": "text", "text": "## Top Catalysts\n1. ..."}],
        }
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 100
        mock_usage.model = "claude-3-opus"
        mock_usage.estimated_cost_usd = 0.01

        mock_client.send_message = AsyncMock(return_value=(mock_response, mock_usage))

        generator = BriefingGenerator(mock_client, storage, mock_usage_tracker, config)

        # Pass all 5 symbols
        brief = await generator.generate_brief(symbols)

        # Only first 3 symbols should be processed (capped by max_symbols)
        # The brief's symbols_covered reflects catalysts found for capped symbols
        assert len(brief.symbols_covered) <= 3

    @pytest.mark.asyncio
    async def test_generate_brief_filters_to_last_24_hours(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        briefing_config: BriefingConfig,
    ) -> None:
        """Only catalysts from the last 24 hours are included."""
        # Store a recent catalyst (1 hour ago)
        recent = make_catalyst("AAPL", "Recent news", "earnings", 80, "high", hours_ago=1)
        await storage.store_catalyst(recent)

        # Store an old catalyst (48 hours ago)
        old = make_catalyst("AAPL", "Old news", "earnings", 80, "high", hours_ago=48)
        await storage.store_catalyst(old)

        # Mock Claude response
        mock_response = {
            "type": "message",
            "content": [{"type": "text", "text": "## Top Catalysts\n..."}],
        }
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 100
        mock_usage.model = "claude-3-opus"
        mock_usage.estimated_cost_usd = 0.01

        mock_client.send_message = AsyncMock(return_value=(mock_response, mock_usage))

        generator = BriefingGenerator(
            mock_client, storage, mock_usage_tracker, briefing_config
        )

        brief = await generator.generate_brief(["AAPL"])

        # Only 1 catalyst (the recent one) should be included
        assert brief.catalyst_count == 1

    @pytest.mark.asyncio
    async def test_generate_brief_with_claude_disabled_uses_fallback(
        self,
        storage: CatalystStorage,
        mock_usage_tracker: MagicMock,
        briefing_config: BriefingConfig,
    ) -> None:
        """When Claude is disabled, fallback brief is generated."""
        # Create disabled client
        mock_client = MagicMock()
        mock_client.enabled = False

        # Store a catalyst
        cat = make_catalyst("AAPL", "AAPL earnings beat", "earnings", 85, "high")
        await storage.store_catalyst(cat)

        generator = BriefingGenerator(
            mock_client, storage, mock_usage_tracker, briefing_config
        )

        brief = await generator.generate_brief(["AAPL"])

        assert brief is not None
        assert brief.catalyst_count == 1
        assert brief.generation_cost_usd == 0.0  # No Claude cost

        # Brief should still have sections (from fallback)
        assert "## Top Catalysts" in brief.content
        assert "## Earnings Calendar" in brief.content

    @pytest.mark.asyncio
    async def test_brief_stored_in_storage(
        self,
        storage: CatalystStorage,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        briefing_config: BriefingConfig,
    ) -> None:
        """Generated brief is stored in the storage."""
        # Store a catalyst
        cat = make_catalyst("AAPL", "AAPL news", "news_sentiment", 50, "medium")
        await storage.store_catalyst(cat)

        # Mock Claude response
        mock_response = {
            "type": "message",
            "content": [{"type": "text", "text": "## Top Catalysts\n..."}],
        }
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 100
        mock_usage.model = "claude-3-opus"
        mock_usage.estimated_cost_usd = 0.01

        mock_client.send_message = AsyncMock(return_value=(mock_response, mock_usage))

        generator = BriefingGenerator(
            mock_client, storage, mock_usage_tracker, briefing_config
        )

        today = datetime.now(_ET).date().isoformat()
        brief = await generator.generate_brief(["AAPL"])

        # Retrieve from storage
        stored = await storage.get_brief(today, "premarket")
        assert stored is not None
        assert stored.date == today
        assert stored.brief_type == "premarket"

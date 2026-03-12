"""Tests for the CatalystClassifier.

Sprint 23.5 Session 3 — DEC-164
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.ai.client import UsageRecord
from argus.intelligence.classifier import CatalystClassifier
from argus.intelligence.config import CatalystConfig
from argus.intelligence.models import CatalystRawItem, compute_headline_hash

_ET = ZoneInfo("America/New_York")


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
    tracker.get_daily_usage = AsyncMock(return_value={"estimated_cost_usd": 0.50})
    return tracker


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create a mock CatalystStorage."""
    storage = MagicMock()
    storage.get_cached_classification = AsyncMock(return_value=None)
    storage.is_cache_valid = AsyncMock(return_value=False)
    storage.cache_classification = AsyncMock()
    return storage


@pytest.fixture
def config() -> CatalystConfig:
    """Create a test config."""
    return CatalystConfig(
        enabled=True,
        max_batch_size=5,
        daily_cost_ceiling_usd=10.0,
        classification_cache_ttl_hours=24,
    )


@pytest.fixture
def raw_item() -> CatalystRawItem:
    """Create a sample raw catalyst item."""
    now = datetime.now(_ET)
    return CatalystRawItem(
        headline="AAPL beats Q3 earnings, revenue up 12%",
        symbol="AAPL",
        source="test",
        published_at=now,
        fetched_at=now,
    )


def _make_claude_response(classifications: list[dict[str, Any]]) -> tuple[dict[str, Any], UsageRecord]:
    """Create a mock Claude API response."""
    import json

    response = {
        "type": "message",
        "content": [{"type": "text", "text": json.dumps(classifications)}],
    }
    usage = UsageRecord(
        input_tokens=100,
        output_tokens=50,
        model="claude-3-haiku",
        estimated_cost_usd=0.01,
    )
    return response, usage


class TestClassifyBatch:
    """Tests for classify_batch method."""

    @pytest.mark.asyncio
    async def test_parses_claude_json_response_correctly(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Claude JSON response is parsed into correct classifications."""
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple exceeded expectations",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        assert results[0].category == "earnings"
        assert results[0].quality_score == 85
        assert results[0].summary == "Apple exceeded expectations"
        assert results[0].trading_relevance == "high"
        assert results[0].classified_by == "claude"

    @pytest.mark.asyncio
    async def test_dynamic_batching_respects_max_batch_size(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
    ) -> None:
        """Items are grouped into batches not exceeding max_batch_size."""
        # Create 7 items with max_batch_size=5 → should result in 2 batches
        now = datetime.now(_ET)
        items = [
            CatalystRawItem(
                headline=f"News headline {i}",
                symbol="TEST",
                source="test",
                published_at=now,
                fetched_at=now,
            )
            for i in range(7)
        ]

        # Mock response for each batch
        def make_batch_response(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], UsageRecord]:
            # Determine batch size from the message content
            import json
            classifications = [
                {
                    "category": "other",
                    "quality_score": 50,
                    "summary": "Test",
                    "trading_relevance": "low",
                }
                for _ in range(5)  # Max batch size
            ]
            return _make_claude_response(classifications)

        mock_client.send_message = AsyncMock(side_effect=make_batch_response)

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch(items)

        # Should have made 2 API calls (5 + 2)
        assert mock_client.send_message.call_count == 2
        assert len(results) == 7

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_classification(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Cached headline returns cached classification without API call."""
        from argus.intelligence.models import CatalystClassification

        cached = CatalystClassification(
            category="earnings",
            quality_score=90,
            summary="Cached result",
            trading_relevance="high",
            classified_by="claude",
            classified_at=datetime.now(_ET),
        )

        mock_storage.is_cache_valid = AsyncMock(return_value=True)
        mock_storage.get_cached_classification = AsyncMock(return_value=cached)

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        assert results[0].summary == "Cached result"
        # Should NOT have called Claude
        mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_claude_api(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Uncached headline triggers Claude API call."""
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Fresh classification",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        mock_client.send_message.assert_called_once()
        # Should have cached the result
        mock_storage.cache_classification.assert_called_once()


class TestFallbackClassifier:
    """Tests for fallback keyword-based classification."""

    @pytest.mark.asyncio
    async def test_fallback_earnings_keyword(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
    ) -> None:
        """Earnings keywords correctly map to earnings category."""
        mock_client.enabled = False  # Force fallback

        now = datetime.now(_ET)
        item = CatalystRawItem(
            headline="Company reports Q2 earnings beat",
            symbol="TEST",
            source="test",
            published_at=now,
            fetched_at=now,
        )

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config)
        results = await classifier.classify_batch([item])

        assert len(results) == 1
        assert results[0].category == "earnings"
        assert results[0].classified_by == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_insider_trade_keyword(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
    ) -> None:
        """Insider trade keywords correctly map to insider_trade category."""
        mock_client.enabled = False

        now = datetime.now(_ET)
        item = CatalystRawItem(
            headline="CEO purchases 10,000 shares via Form 4",
            symbol="TEST",
            source="test",
            published_at=now,
            fetched_at=now,
        )

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config)
        results = await classifier.classify_batch([item])

        assert results[0].category == "insider_trade"
        assert results[0].classified_by == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_analyst_action_keyword(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
    ) -> None:
        """Analyst action keywords correctly map to analyst_action category."""
        mock_client.enabled = False

        now = datetime.now(_ET)
        item = CatalystRawItem(
            headline="Bank upgrades stock with $150 price target",
            symbol="TEST",
            source="test",
            published_at=now,
            fetched_at=now,
        )

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config)
        results = await classifier.classify_batch([item])

        assert results[0].category == "analyst_action"

    @pytest.mark.asyncio
    async def test_fallback_unknown_headline_returns_other(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        config: CatalystConfig,
    ) -> None:
        """Headlines without matching keywords default to 'other' category."""
        mock_client.enabled = False

        now = datetime.now(_ET)
        item = CatalystRawItem(
            headline="Random news with no catalyst keywords",
            symbol="TEST",
            source="test",
            published_at=now,
            fetched_at=now,
        )

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config)
        results = await classifier.classify_batch([item])

        assert results[0].category == "other"
        assert results[0].quality_score == 25
        assert results[0].trading_relevance == "low"
        assert results[0].classified_by == "fallback"


class TestCostCeiling:
    """Tests for daily cost ceiling enforcement."""

    @pytest.mark.asyncio
    async def test_cost_ceiling_triggers_fallback(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        raw_item: CatalystRawItem,
    ) -> None:
        """When daily cost ceiling is reached, remaining items use fallback."""
        # Set cost ceiling very low
        config = CatalystConfig(
            enabled=True,
            max_batch_size=5,
            daily_cost_ceiling_usd=0.10,  # Very low ceiling
        )

        # Return cost that exceeds ceiling
        mock_usage_tracker.get_daily_usage = AsyncMock(return_value={"estimated_cost_usd": 0.15})

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        assert results[0].classified_by == "fallback"
        # Should NOT have called Claude
        mock_client.send_message.assert_not_called()


class TestMalformedResponse:
    """Tests for handling malformed Claude responses."""

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back_gracefully(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Malformed JSON response triggers fallback classifier."""
        # Return invalid JSON
        response = {
            "type": "message",
            "content": [{"type": "text", "text": "This is not valid JSON {{{"}],
        }
        usage = UsageRecord(
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
            estimated_cost_usd=0.01,
        )
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        assert results[0].classified_by == "fallback"


class TestQualityScoreRange:
    """Tests for quality score validation."""

    @pytest.mark.asyncio
    async def test_quality_score_clamped_to_valid_range(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Quality scores outside 0-100 are clamped to valid range."""
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 150,  # Over 100
                "summary": "Test",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert results[0].quality_score == 100  # Clamped to max

    @pytest.mark.asyncio
    async def test_negative_quality_score_clamped_to_zero(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Negative quality scores are clamped to 0."""
        response, usage = _make_claude_response([
            {
                "category": "other",
                "quality_score": -50,
                "summary": "Test",
                "trading_relevance": "low",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert results[0].quality_score == 0  # Clamped to min


class TestNoneUsageTracker:
    """Tests for classifier when usage_tracker is None."""

    @pytest.mark.asyncio
    async def test_classification_completes_with_none_usage_tracker(
        self,
        mock_client: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Classification succeeds without error when usage_tracker is None."""
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Apple exceeded expectations",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, None, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        assert results[0].category == "earnings"
        assert results[0].classified_by == "claude"


class TestCostCeilingBelowThreshold:
    """Tests for cost ceiling when daily cost is below the threshold."""

    @pytest.mark.asyncio
    async def test_cost_below_ceiling_uses_claude(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        raw_item: CatalystRawItem,
    ) -> None:
        """When daily cost is below ceiling, Claude classification proceeds."""
        config = CatalystConfig(
            enabled=True,
            max_batch_size=5,
            daily_cost_ceiling_usd=10.0,
        )

        # Return cost well below ceiling
        mock_usage_tracker.get_daily_usage = AsyncMock(
            return_value={"estimated_cost_usd": 1.00}
        )

        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Test",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        results = await classifier.classify_batch([raw_item])

        assert len(results) == 1
        assert results[0].classified_by == "claude"
        mock_client.send_message.assert_called_once()


class TestRecordUsageCalled:
    """Tests that record_usage is called after each Claude classification."""

    @pytest.mark.asyncio
    async def test_record_usage_called_after_claude_classification(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """record_usage is called once per Claude API batch call."""
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Test",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        await classifier.classify_batch([raw_item])

        mock_usage_tracker.record_usage.assert_called_once_with(
            conversation_id=None,
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
            estimated_cost_usd=0.01,
            endpoint="catalyst_classification",
        )

    @pytest.mark.asyncio
    async def test_record_usage_called_per_batch(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """record_usage is called once per batch (2 batches = 2 calls)."""
        config = CatalystConfig(
            enabled=True,
            max_batch_size=2,
            daily_cost_ceiling_usd=100.0,
        )

        now = datetime.now(_ET)
        items = [
            CatalystRawItem(
                headline=f"Unique headline number {i}",
                symbol="TEST",
                source="test",
                published_at=now,
                fetched_at=now,
            )
            for i in range(3)
        ]

        response_2, usage_2 = _make_claude_response([
            {"category": "other", "quality_score": 50, "summary": "T", "trading_relevance": "low"},
            {"category": "other", "quality_score": 50, "summary": "T", "trading_relevance": "low"},
        ])
        response_1, usage_1 = _make_claude_response([
            {"category": "other", "quality_score": 50, "summary": "T", "trading_relevance": "low"},
        ])
        mock_client.send_message = AsyncMock(
            side_effect=[(response_2, usage_2), (response_1, usage_1)]
        )

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)
        await classifier.classify_batch(items)

        assert mock_usage_tracker.record_usage.call_count == 2


class TestCycleCostLogging:
    """Tests for cycle cost logging output."""

    @pytest.mark.asyncio
    async def test_cycle_cost_logged_with_counts(
        self,
        mock_client: MagicMock,
        mock_usage_tracker: MagicMock,
        mock_storage: MagicMock,
        config: CatalystConfig,
        raw_item: CatalystRawItem,
    ) -> None:
        """Cycle cost log includes dollar amount and Claude/fallback counts."""
        response, usage = _make_claude_response([
            {
                "category": "earnings",
                "quality_score": 85,
                "summary": "Test",
                "trading_relevance": "high",
            }
        ])
        mock_client.send_message = AsyncMock(return_value=(response, usage))

        classifier = CatalystClassifier(mock_client, mock_usage_tracker, config, mock_storage)

        with patch("argus.intelligence.classifier.logger") as mock_logger:
            await classifier.classify_batch([raw_item])

            # Find the info call with cycle cost
            info_calls = mock_logger.info.call_args_list
            cost_log = [
                c for c in info_calls
                if "Classification cycle cost" in str(c)
            ]
            assert len(cost_log) == 1
            log_msg = cost_log[0][0][0] % cost_log[0][0][1:]
            assert "$0.0100" in log_msg
            assert "1 via Claude" in log_msg
            assert "0 via fallback" in log_msg

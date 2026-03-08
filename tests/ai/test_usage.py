"""Tests for UsageTracker."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from argus.ai.conversations import ConversationManager
from argus.ai.usage import UsageTracker
from argus.db.manager import DatabaseManager


@pytest.fixture
async def usage_tracker(db: DatabaseManager) -> UsageTracker:
    """Provide an initialized UsageTracker with temp database.

    Also initializes ConversationManager since ai_usage has a FK to ai_conversations.
    """
    # Initialize conversations first (FK target)
    conv_manager = ConversationManager(db)
    await conv_manager.initialize()

    tracker = UsageTracker(db)
    await tracker.initialize()
    return tracker


class TestUsageTrackerRecord:
    """Test usage recording."""

    async def test_record_usage_basic(self, usage_tracker: UsageTracker) -> None:
        """record_usage stores usage data and returns ID."""
        # Use None for conversation_id since it's nullable
        usage_id = await usage_tracker.record_usage(
            conversation_id=None,
            input_tokens=500,
            output_tokens=200,
            model="claude-opus-4-5-20250514",
            estimated_cost_usd=0.025,
        )

        assert usage_id is not None
        assert len(usage_id) == 26  # ULID length

    async def test_record_usage_without_conversation(
        self, usage_tracker: UsageTracker
    ) -> None:
        """record_usage works with None conversation_id."""
        usage_id = await usage_tracker.record_usage(
            conversation_id=None,
            input_tokens=1000,
            output_tokens=500,
            model="claude-opus-4-5-20250514",
            estimated_cost_usd=0.05,
            endpoint="insight",
        )

        assert usage_id is not None

    async def test_record_usage_custom_endpoint(self, usage_tracker: UsageTracker) -> None:
        """record_usage stores custom endpoint."""
        await usage_tracker.record_usage(
            conversation_id=None,
            input_tokens=100,
            output_tokens=50,
            model="claude-opus-4-5-20250514",
            estimated_cost_usd=0.01,
            endpoint="summary",
        )

        # Verify by getting daily usage
        # Use ET timezone to match how UsageTracker stores timestamps (DEC-276)
        today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        usage = await usage_tracker.get_daily_usage(today)
        assert usage["call_count"] == 1


class TestUsageTrackerDaily:
    """Test daily usage aggregation."""

    async def test_get_daily_usage_empty(self, usage_tracker: UsageTracker) -> None:
        """get_daily_usage returns zeros when no usage."""
        usage = await usage_tracker.get_daily_usage("2026-03-06")

        assert usage == {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "call_count": 0,
        }

    async def test_get_daily_usage_aggregates(self, usage_tracker: UsageTracker) -> None:
        """get_daily_usage correctly aggregates multiple calls."""
        # Record 3 usage events on the same day
        # We need to mock datetime to control the timestamp
        mock_time = datetime(2026, 3, 6, 10, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch("argus.ai.usage.datetime") as mock_dt:
            mock_dt.now.return_value = mock_time

            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=500,
                output_tokens=200,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.025,
            )
            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=300,
                output_tokens=100,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.015,
            )
            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=200,
                output_tokens=50,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.008,
            )

        usage = await usage_tracker.get_daily_usage("2026-03-06")

        assert usage["input_tokens"] == 1000  # 500 + 300 + 200
        assert usage["output_tokens"] == 350  # 200 + 100 + 50
        assert abs(usage["estimated_cost_usd"] - 0.048) < 0.001  # 0.025 + 0.015 + 0.008
        assert usage["call_count"] == 3


class TestUsageTrackerMonthly:
    """Test monthly usage aggregation."""

    async def test_get_monthly_usage_empty(self, usage_tracker: UsageTracker) -> None:
        """get_monthly_usage returns zeros when no usage."""
        usage = await usage_tracker.get_monthly_usage(2026, 3)

        assert usage == {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "call_count": 0,
            "daily_breakdown": [],
        }

    async def test_get_monthly_usage_with_daily_breakdown(
        self, usage_tracker: UsageTracker
    ) -> None:
        """get_monthly_usage returns totals and daily breakdown."""
        # Record usage on different days in March 2026
        with patch("argus.ai.usage.datetime") as mock_dt:
            # Day 1: March 5
            mock_dt.now.return_value = datetime(2026, 3, 5, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=1000,
                output_tokens=500,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.05,
            )

            # Day 2: March 6
            mock_dt.now.return_value = datetime(2026, 3, 6, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=2000,
                output_tokens=800,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.08,
            )
            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=500,
                output_tokens=200,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.02,
            )

        usage = await usage_tracker.get_monthly_usage(2026, 3)

        # Check totals
        assert usage["input_tokens"] == 3500  # 1000 + 2000 + 500
        assert usage["output_tokens"] == 1500  # 500 + 800 + 200
        assert abs(usage["estimated_cost_usd"] - 0.15) < 0.001
        assert usage["call_count"] == 3

        # Check daily breakdown
        breakdown = usage["daily_breakdown"]
        assert len(breakdown) == 2

        # March 5
        day1 = next(d for d in breakdown if d["date"] == "2026-03-05")
        assert day1["input_tokens"] == 1000
        assert day1["call_count"] == 1

        # March 6
        day2 = next(d for d in breakdown if d["date"] == "2026-03-06")
        assert day2["input_tokens"] == 2500
        assert day2["call_count"] == 2


class TestUsageTrackerSummary:
    """Test usage summary."""

    async def test_get_usage_summary_empty(self, usage_tracker: UsageTracker) -> None:
        """get_usage_summary returns zeros when no usage."""
        summary = await usage_tracker.get_usage_summary()

        assert summary["today"]["input_tokens"] == 0
        assert summary["today"]["call_count"] == 0
        assert summary["this_month"]["input_tokens"] == 0
        assert summary["this_month"]["call_count"] == 0
        # per_day_average with no data
        assert summary["per_day_average"]["input_tokens"] == 0

    async def test_get_usage_summary_with_data(self, usage_tracker: UsageTracker) -> None:
        """get_usage_summary returns correct data."""
        # Record usage for today
        today = datetime.now(ZoneInfo("America/New_York"))

        with patch("argus.ai.usage.datetime") as mock_dt:
            mock_dt.now.return_value = today

            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=1000,
                output_tokens=500,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.05,
            )

        summary = await usage_tracker.get_usage_summary()

        # Today should have data
        assert summary["today"]["input_tokens"] == 1000
        assert summary["today"]["output_tokens"] == 500
        assert summary["today"]["call_count"] == 1

        # This month should have same data
        assert summary["this_month"]["input_tokens"] == 1000
        assert summary["this_month"]["call_count"] == 1

        # Per-day average should match today (only one day)
        assert summary["per_day_average"]["input_tokens"] == 1000
        assert summary["per_day_average"]["call_count"] == 1


class TestUsageTrackerInitialization:
    """Test initialization and table creation."""

    async def test_initialize_creates_table(self, db: DatabaseManager) -> None:
        """initialize() creates ai_usage table."""
        # Initialize conversations first (FK target)
        conv_manager = ConversationManager(db)
        await conv_manager.initialize()

        tracker = UsageTracker(db)
        await tracker.initialize()

        # Verify table exists by recording usage
        usage_id = await tracker.record_usage(
            conversation_id=None,
            input_tokens=100,
            output_tokens=50,
            model="test-model",
            estimated_cost_usd=0.01,
        )
        assert usage_id is not None

    async def test_initialize_idempotent(self, db: DatabaseManager) -> None:
        """initialize() can be called multiple times safely."""
        # Initialize conversations first (FK target)
        conv_manager = ConversationManager(db)
        await conv_manager.initialize()

        tracker = UsageTracker(db)
        await tracker.initialize()
        await tracker.initialize()  # Should not raise

        # Should still work
        usage_id = await tracker.record_usage(
            conversation_id=None,
            input_tokens=100,
            output_tokens=50,
            model="test-model",
            estimated_cost_usd=0.01,
        )
        assert usage_id is not None


class TestUsageTrackerETTimezone:
    """Test ET timezone handling for usage timestamps."""

    async def test_record_usage_stores_et_timestamps(
        self, usage_tracker: UsageTracker, db: DatabaseManager
    ) -> None:
        """record_usage stores timestamps in ET timezone without offset."""
        # Record a usage event
        mock_time = datetime(2026, 3, 6, 10, 30, 0, tzinfo=ZoneInfo("America/New_York"))

        with patch("argus.ai.usage.datetime") as mock_dt:
            mock_dt.now.return_value = mock_time

            usage_id = await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=500,
                output_tokens=200,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.025,
            )

        # Query the raw timestamp from the database
        row = await db.fetch_one(
            "SELECT timestamp FROM ai_usage WHERE id = ?", (usage_id,)
        )
        assert row is not None
        stored_timestamp = row["timestamp"]

        # Verify it's stored as naive ET format (no timezone offset)
        assert stored_timestamp == "2026-03-06T10:30:00"
        assert "+" not in stored_timestamp
        assert "Z" not in stored_timestamp

    async def test_daily_usage_query_matches_et_timestamps(
        self, usage_tracker: UsageTracker
    ) -> None:
        """get_daily_usage correctly matches records stored with ET timestamps."""
        # Record usage at 3 PM ET on March 6
        mock_time = datetime(2026, 3, 6, 15, 0, 0, tzinfo=ZoneInfo("America/New_York"))

        with patch("argus.ai.usage.datetime") as mock_dt:
            mock_dt.now.return_value = mock_time

            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=1000,
                output_tokens=500,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.05,
            )

        # Query with the ET date
        usage = await usage_tracker.get_daily_usage("2026-03-06")

        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500
        assert usage["call_count"] == 1

    async def test_timezone_alignment_utc_vs_et_date_boundary(
        self, usage_tracker: UsageTracker
    ) -> None:
        """Usage recorded at 11 PM ET (next day UTC) is found by ET date query.

        At 11 PM ET, it's already the next day in UTC (4 AM UTC).
        The record should be found when querying by the ET date, not UTC date.
        """
        # 11 PM ET on March 6 = 4 AM UTC on March 7
        mock_time = datetime(2026, 3, 6, 23, 0, 0, tzinfo=ZoneInfo("America/New_York"))

        with patch("argus.ai.usage.datetime") as mock_dt:
            mock_dt.now.return_value = mock_time

            await usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=800,
                output_tokens=400,
                model="claude-opus-4-5-20250514",
                estimated_cost_usd=0.04,
            )

        # Query with ET date (March 6) should find the record
        et_usage = await usage_tracker.get_daily_usage("2026-03-06")
        assert et_usage["call_count"] == 1
        assert et_usage["input_tokens"] == 800

        # Query with UTC date (March 7) should NOT find the record
        utc_usage = await usage_tracker.get_daily_usage("2026-03-07")
        assert utc_usage["call_count"] == 0

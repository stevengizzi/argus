"""Tests for argus.intelligence.models."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from argus.intelligence.models import (
    CatalystClassification,
    CatalystRawItem,
    ClassifiedCatalyst,
    IntelligenceBrief,
    compute_headline_hash,
)

_ET = ZoneInfo("America/New_York")


def _now_et() -> datetime:
    return datetime.now(_ET)


class TestComputeHeadlineHash:
    def test_produces_64_char_hex_digest(self) -> None:
        result = compute_headline_hash("AAPL beats earnings by 10%")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_consistent_across_calls(self) -> None:
        headline = "Company X files 8-K with SEC"
        assert compute_headline_hash(headline) == compute_headline_hash(headline)

    def test_case_and_whitespace_normalized(self) -> None:
        assert compute_headline_hash("AAPL Beats Earnings") == compute_headline_hash(
            "  aapl beats earnings  "
        )

    def test_different_headlines_produce_different_hashes(self) -> None:
        assert compute_headline_hash("Headline A") != compute_headline_hash("Headline B")


class TestCatalystRawItem:
    def test_construction_with_all_fields(self) -> None:
        now = _now_et()
        item = CatalystRawItem(
            headline="TSLA discloses 8-K filing",
            symbol="TSLA",
            source="sec_edgar",
            source_url="https://sec.gov/filing/12345",
            filing_type="8-K",
            published_at=now,
            fetched_at=now,
            metadata={"form_id": "12345", "cik": "0001318605"},
        )
        assert item.headline == "TSLA discloses 8-K filing"
        assert item.symbol == "TSLA"
        assert item.source == "sec_edgar"
        assert item.source_url == "https://sec.gov/filing/12345"
        assert item.filing_type == "8-K"
        assert item.published_at == now
        assert item.fetched_at == now
        assert item.metadata["cik"] == "0001318605"

    def test_optional_fields_default_to_none(self) -> None:
        now = _now_et()
        item = CatalystRawItem(
            headline="NVDA reports earnings",
            symbol="NVDA",
            source="fmp_news",
            published_at=now,
            fetched_at=now,
        )
        assert item.source_url is None
        assert item.filing_type is None
        assert item.metadata == {}


class TestCatalystClassification:
    def test_construction_with_valid_values(self) -> None:
        now = _now_et()
        cls = CatalystClassification(
            category="earnings",
            quality_score=85.0,
            summary="AAPL beat Q1 EPS by 12% — strong iPhone demand.",
            trading_relevance="high",
            classified_by="claude",
            classified_at=now,
        )
        assert cls.category == "earnings"
        assert cls.quality_score == 85.0
        assert cls.trading_relevance == "high"
        assert cls.classified_by == "claude"

    def test_all_valid_categories_accepted(self) -> None:
        now = _now_et()
        valid_categories = [
            "earnings",
            "insider_trade",
            "sec_filing",
            "analyst_action",
            "corporate_event",
            "news_sentiment",
            "regulatory",
            "other",
        ]
        for category in valid_categories:
            cls = CatalystClassification(
                category=category,
                quality_score=50.0,
                summary="Test summary.",
                trading_relevance="medium",
                classified_by="fallback",
                classified_at=now,
            )
            assert cls.category == category

    def test_invalid_category_raises_value_error(self) -> None:
        now = _now_et()
        with pytest.raises(ValueError, match="Invalid category"):
            CatalystClassification(
                category="unknown_category",
                quality_score=50.0,
                summary="Test summary.",
                trading_relevance="medium",
                classified_by="claude",
                classified_at=now,
            )

    def test_invalid_trading_relevance_raises_value_error(self) -> None:
        now = _now_et()
        with pytest.raises(ValueError, match="Invalid trading_relevance"):
            CatalystClassification(
                category="earnings",
                quality_score=50.0,
                summary="Test summary.",
                trading_relevance="critical",
                classified_by="claude",
                classified_at=now,
            )

    def test_invalid_classified_by_raises_value_error(self) -> None:
        now = _now_et()
        with pytest.raises(ValueError, match="Invalid classified_by"):
            CatalystClassification(
                category="earnings",
                quality_score=50.0,
                summary="Test summary.",
                trading_relevance="high",
                classified_by="gpt4",
                classified_at=now,
            )


class TestClassifiedCatalyst:
    def _make_raw(self) -> CatalystRawItem:
        now = _now_et()
        return CatalystRawItem(
            headline="MSFT Insider Files Form 4",
            symbol="MSFT",
            source="sec_edgar",
            source_url="https://sec.gov/form4/99999",
            filing_type="Form 4",
            published_at=now,
            fetched_at=now,
        )

    def _make_classification(self) -> CatalystClassification:
        return CatalystClassification(
            category="insider_trade",
            quality_score=72.0,
            summary="MSFT executive purchased 5,000 shares.",
            trading_relevance="medium",
            classified_by="claude",
            classified_at=_now_et(),
        )

    def test_from_raw_and_classification(self) -> None:
        raw = self._make_raw()
        classification = self._make_classification()
        classified = ClassifiedCatalyst.from_raw_and_classification(raw, classification)

        assert classified.symbol == "MSFT"
        assert classified.category == "insider_trade"
        assert classified.quality_score == 72.0
        assert classified.source_url == "https://sec.gov/form4/99999"
        assert len(classified.headline_hash) == 64

    def test_headline_hash_matches_compute_function(self) -> None:
        raw = self._make_raw()
        classification = self._make_classification()
        classified = ClassifiedCatalyst.from_raw_and_classification(raw, classification)
        assert classified.headline_hash == compute_headline_hash(raw.headline)


class TestIntelligenceBrief:
    def test_construction_with_all_fields(self) -> None:
        now = _now_et()
        brief = IntelligenceBrief(
            date="2026-03-10",
            brief_type="premarket",
            content="## Pre-Market Intelligence\n\n- AAPL: Beat earnings by 12%.",
            symbols_covered=["AAPL", "MSFT"],
            catalyst_count=3,
            generated_at=now,
            generation_cost_usd=0.042,
        )
        assert brief.date == "2026-03-10"
        assert brief.brief_type == "premarket"
        assert brief.catalyst_count == 3
        assert brief.generation_cost_usd == 0.042
        assert "AAPL" in brief.symbols_covered

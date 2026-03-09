"""Data models for the NLP Catalyst Pipeline.

Defines the data structures for raw catalyst items, classifications,
classified catalysts, and intelligence briefs used throughout the
intelligence layer.

Sprint 23.5 — DEC-164
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


def compute_headline_hash(headline: str) -> str:
    """Compute a SHA-256 hash of a normalized headline.

    Args:
        headline: Raw headline string.

    Returns:
        Hex-encoded SHA-256 digest of the lowercased, stripped headline.
    """
    normalized = headline.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass
class CatalystRawItem:
    """A raw catalyst item from a data source before classification.

    Attributes:
        headline: The news or filing headline text.
        symbol: Stock ticker symbol this catalyst relates to.
        source: Data source identifier (e.g., "sec_edgar", "fmp_news", "finnhub").
        source_url: Direct URL to the original item, if available.
        filing_type: SEC filing type if applicable (e.g., "8-K", "Form 4").
        published_at: When the item was originally published (ET).
        fetched_at: When this item was fetched from the source (ET).
        metadata: Source-specific extra fields.
    """

    headline: str
    symbol: str
    source: str
    published_at: datetime
    fetched_at: datetime
    source_url: str | None = None
    filing_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CatalystClassification:
    """Classification output from the catalyst classifier.

    Attributes:
        category: Catalyst category (e.g., "earnings", "insider_trade").
        quality_score: Quality score in range 0–100.
        summary: One-sentence trading-relevant summary.
        trading_relevance: Relevance level ("high", "medium", "low", "none").
        classified_by: Which classifier produced this result ("claude", "fallback").
        classified_at: When classification was performed (ET).
    """

    VALID_CATEGORIES: frozenset[str] = field(
        default=frozenset({
            "earnings",
            "insider_trade",
            "sec_filing",
            "analyst_action",
            "corporate_event",
            "news_sentiment",
            "regulatory",
            "other",
        }),
        init=False,
        repr=False,
        compare=False,
    )
    VALID_RELEVANCE: frozenset[str] = field(
        default=frozenset({"high", "medium", "low", "none"}),
        init=False,
        repr=False,
        compare=False,
    )
    VALID_CLASSIFIERS: frozenset[str] = field(
        default=frozenset({"claude", "fallback"}),
        init=False,
        repr=False,
        compare=False,
    )

    category: str
    quality_score: float
    summary: str
    trading_relevance: str
    classified_by: str
    classified_at: datetime

    def __post_init__(self) -> None:
        """Validate field values after construction."""
        if self.category not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{self.category}'. "
                f"Must be one of: {sorted(self.VALID_CATEGORIES)}"
            )
        if self.trading_relevance not in self.VALID_RELEVANCE:
            raise ValueError(
                f"Invalid trading_relevance '{self.trading_relevance}'. "
                f"Must be one of: {sorted(self.VALID_RELEVANCE)}"
            )
        if self.classified_by not in self.VALID_CLASSIFIERS:
            raise ValueError(
                f"Invalid classified_by '{self.classified_by}'. "
                f"Must be one of: {sorted(self.VALID_CLASSIFIERS)}"
            )


@dataclass
class ClassifiedCatalyst:
    """A fully classified catalyst combining raw item and classification.

    Attributes:
        headline: The news or filing headline text.
        symbol: Stock ticker symbol this catalyst relates to.
        source: Data source identifier.
        source_url: Direct URL to the original item, if available.
        filing_type: SEC filing type if applicable.
        published_at: When the item was originally published (ET).
        fetched_at: When this item was fetched from the source (ET).
        metadata: Source-specific extra fields.
        category: Catalyst category from classification.
        quality_score: Quality score in range 0–100.
        summary: One-sentence trading-relevant summary.
        trading_relevance: Relevance level.
        classified_by: Which classifier produced this result.
        classified_at: When classification was performed (ET).
        headline_hash: SHA-256 of the normalized (lowercase, stripped) headline.
    """

    headline: str
    symbol: str
    source: str
    published_at: datetime
    fetched_at: datetime
    category: str
    quality_score: float
    summary: str
    trading_relevance: str
    classified_by: str
    classified_at: datetime
    headline_hash: str
    source_url: str | None = None
    filing_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw_and_classification(
        cls,
        raw: CatalystRawItem,
        classification: CatalystClassification,
    ) -> ClassifiedCatalyst:
        """Construct from a raw item and its classification.

        Args:
            raw: The raw catalyst item.
            classification: The classification result.

        Returns:
            A fully assembled ClassifiedCatalyst.
        """
        return cls(
            headline=raw.headline,
            symbol=raw.symbol,
            source=raw.source,
            source_url=raw.source_url,
            filing_type=raw.filing_type,
            published_at=raw.published_at,
            fetched_at=raw.fetched_at,
            metadata=raw.metadata,
            category=classification.category,
            quality_score=classification.quality_score,
            summary=classification.summary,
            trading_relevance=classification.trading_relevance,
            classified_by=classification.classified_by,
            classified_at=classification.classified_at,
            headline_hash=compute_headline_hash(raw.headline),
        )


@dataclass
class IntelligenceBrief:
    """A generated pre-market or intraday intelligence brief.

    Attributes:
        date: Trading date this brief covers (YYYY-MM-DD).
        brief_type: Brief category (e.g., "premarket").
        content: Markdown-formatted brief content.
        symbols_covered: List of symbols mentioned in the brief.
        catalyst_count: Number of catalysts summarized.
        generated_at: When the brief was generated (ET).
        generation_cost_usd: Estimated Claude API cost for generating the brief.
    """

    date: str
    brief_type: str
    content: str
    symbols_covered: list[str]
    catalyst_count: int
    generated_at: datetime
    generation_cost_usd: float


_ET = ZoneInfo("America/New_York")

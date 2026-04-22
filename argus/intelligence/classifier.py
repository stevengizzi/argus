"""Catalyst classifier using Claude API with fallback keyword matching.

Classifies raw catalyst items into trading-relevant categories with
quality scores. Uses Claude API for intelligent classification with
a fallback keyword-based classifier when the daily cost ceiling is
reached or API errors occur.

Sprint 23.5 Session 3 — DEC-164
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.intelligence.models import (
    CatalystClassification,
    CatalystRawItem,
    ClassifiedCatalyst,
    compute_headline_hash,
)

if TYPE_CHECKING:
    from argus.ai.client import ClaudeClient
    from argus.ai.usage import UsageTracker
    from argus.intelligence.config import CatalystConfig
    from argus.intelligence.storage import CatalystStorage

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

# Classification prompt for Claude API
_CLASSIFICATION_SYSTEM_PROMPT = """\
You are a trading catalyst classifier. Classify each headline into exactly \
one category and assess its trading relevance.

Categories:
- earnings: Quarterly/annual earnings reports, revenue, EPS, profit/loss
- insider_trade: Form 4 filings, insider purchases/sales, director/officer txns
- sec_filing: 8-K, 10-K, 10-Q filings, other SEC regulatory filings
- analyst_action: Upgrades, downgrades, price target changes, analyst ratings
- regulatory: FDA approvals, regulatory decisions, compliance matters
- corporate_event: M&A, IPOs, offerings, buyouts, restructuring, spin-offs
- news_sentiment: General news with market sentiment implications
- other: Items that don't fit other categories

For each headline, provide:
1. category: One of the categories above
2. quality_score: 0-100 rating of the catalyst's potential trading impact
3. summary: One sentence trading-relevant summary
4. trading_relevance: "high", "medium", "low", or "none"

Respond with a JSON array. Each item: category, quality_score, summary, relevance.

Examples:
Input: "AAPL beats Q3 earnings, revenue up 12%"
Output: {"category": "earnings", "quality_score": 85, \
"summary": "Apple exceeded expectations", "trading_relevance": "high"}

Input: "CEO of XYZ purchases 50,000 shares"
Output: {"category": "insider_trade", "quality_score": 72, \
"summary": "Significant insider buying signals confidence", \
"trading_relevance": "high"}

Input: "Company updates corporate governance policy"
Output: {"category": "corporate_event", "quality_score": 15, \
"summary": "Routine governance update", "trading_relevance": "none"}

Respond ONLY with a valid JSON array. No explanations or markdown."""


# Keyword patterns for fallback classifier
_FALLBACK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "earnings",
        re.compile(r"\b(earnings|revenue|EPS|profit|loss|quarter|Q[1-4])\b", re.I),
    ),
    (
        "insider_trade",
        re.compile(r"\b(insider|Form\s*4|purchase|sale|director|officer)\b", re.I),
    ),
    (
        "sec_filing",
        re.compile(r"\b(8-K|10-K|10-Q|SEC|filing|filed)\b", re.I),
    ),
    (
        "analyst_action",
        re.compile(r"\b(upgrade|downgrade|analyst|target|rating)\b", re.I),
    ),
    (
        "regulatory",
        re.compile(r"\b(FDA|approval|regulatory|compliance)\b", re.I),
    ),
    (
        "corporate_event",
        re.compile(r"\b(merger|acquisition|buyout|IPO|offering|spin-?off)\b", re.I),
    ),
]


class CatalystClassifier:
    """Classifies catalyst items using Claude API with fallback to keywords.

    Uses Claude API for intelligent classification with batching and caching.
    Falls back to keyword-based classification when:
    - Daily cost ceiling is reached
    - Claude API returns errors
    - Malformed responses are received

    All classifications are cached by headline hash with configurable TTL.
    """

    def __init__(
        self,
        client: ClaudeClient,
        usage_tracker: UsageTracker,
        config: CatalystConfig,
        storage: CatalystStorage | None = None,
    ) -> None:
        """Initialize the classifier.

        Args:
            client: Claude API client for sending classification requests.
            usage_tracker: Tracks API usage and costs.
            config: Catalyst pipeline configuration.
            storage: Optional storage for caching classifications.
        """
        self._client = client
        self._usage_tracker = usage_tracker
        self._config = config
        self._storage = storage

    async def classify_batch(
        self, items: list[CatalystRawItem]
    ) -> list[ClassifiedCatalyst]:
        """Classify a batch of raw catalyst items.

        Deduplicates items by headline hash, checks cache for existing
        classifications, batches uncached items for Claude API, and
        falls back to keyword classifier when cost ceiling is reached.

        Args:
            items: Raw catalyst items to classify.

        Returns:
            List of classified catalysts.
        """
        if not items:
            return []

        # Deduplicate by headline hash
        unique_items: dict[str, CatalystRawItem] = {}
        for item in items:
            headline_hash = compute_headline_hash(item.headline)
            if headline_hash not in unique_items:
                unique_items[headline_hash] = item

        logger.debug("Deduped %d items to %d unique headlines", len(items), len(unique_items))

        results: list[ClassifiedCatalyst] = []
        uncached_items: list[tuple[str, CatalystRawItem]] = []

        # Check cache for each unique item
        for headline_hash, item in unique_items.items():
            cached = await self._get_cached_classification(headline_hash)
            if cached is not None:
                result = ClassifiedCatalyst.from_raw_and_classification(item, cached)
                results.append(result)
                logger.debug("Cache hit for headline hash %s", headline_hash[:8])
            else:
                uncached_items.append((headline_hash, item))

        if not uncached_items:
            logger.debug("All %d items were cached", len(results))
            return results

        logger.debug("Need to classify %d uncached items", len(uncached_items))

        # Check daily cost ceiling
        daily_total = await self._get_daily_cost()
        ceiling = self._config.daily_cost_ceiling_usd

        # Classify uncached items in batches
        batch_size = self._config.max_batch_size
        fallback_count = 0
        claude_count = 0
        cycle_cost = 0.0

        for i in range(0, len(uncached_items), batch_size):
            batch = uncached_items[i:i + batch_size]

            # Check if we've hit the ceiling
            if daily_total >= ceiling:
                logger.warning(
                    "Daily cost ceiling reached ($%.2f >= $%.2f), using fallback",
                    daily_total,
                    ceiling,
                )
                for headline_hash, item in batch:
                    classification = self._classify_fallback(item)
                    await self._cache_classification(headline_hash, classification)
                    result = ClassifiedCatalyst.from_raw_and_classification(item, classification)
                    results.append(result)
                    fallback_count += 1
                continue

            # Try Claude API classification
            batch_classifications, call_cost = await self._classify_with_claude(batch)
            cycle_cost += call_cost

            if batch_classifications is None:
                # Claude failed, use fallback for entire batch
                for headline_hash, item in batch:
                    classification = self._classify_fallback(item)
                    await self._cache_classification(headline_hash, classification)
                    result = ClassifiedCatalyst.from_raw_and_classification(item, classification)
                    results.append(result)
                    fallback_count += 1
            else:
                # Process Claude results
                batch_pairs = zip(batch, batch_classifications, strict=False)
                for (headline_hash, item), classification in batch_pairs:
                    await self._cache_classification(headline_hash, classification)
                    raw_cls = ClassifiedCatalyst.from_raw_and_classification
                    result = raw_cls(item, classification)
                    results.append(result)
                    claude_count += 1

            # Update daily total
            daily_total = await self._get_daily_cost()

        logger.info(
            "Classification batch cost: $%.4f "
            "(%d via Claude, %d via fallback, %d cached)",
            cycle_cost,
            claude_count,
            fallback_count,
            len(results) - claude_count - fallback_count,
        )

        return results

    async def _classify_with_claude(
        self, batch: list[tuple[str, CatalystRawItem]]
    ) -> tuple[list[CatalystClassification] | None, float]:
        """Classify a batch of items using Claude API.

        Args:
            batch: List of (headline_hash, item) tuples to classify.

        Returns:
            Tuple of (classifications or None on error, cost in USD for this call).
        """
        if not self._client.enabled:
            logger.debug("Claude API disabled, cannot classify")
            return None, 0.0

        # Build the user message with all headlines
        headlines = [f"{i+1}. {item.headline}" for i, (_, item) in enumerate(batch)]
        user_content = "Classify these headlines:\n" + "\n".join(headlines)

        messages = [{"role": "user", "content": user_content}]

        try:
            response, usage = await self._client.send_message(
                messages=messages,
                system=_CLASSIFICATION_SYSTEM_PROMPT,
                stream=False,
            )

            call_cost = usage.estimated_cost_usd

            # Record usage
            if self._usage_tracker is not None:
                await self._usage_tracker.record_usage(
                    conversation_id=None,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    model=usage.model,
                    estimated_cost_usd=call_cost,
                    endpoint="catalyst_classification",
                )

            # Check for error response
            if response.get("type") == "error":
                logger.warning("Claude API error: %s", response.get("message"))
                return None, call_cost

            # Parse the response
            return self._parse_claude_response(response, len(batch)), call_cost

        except Exception as e:
            logger.error("Error calling Claude API: %s", e, exc_info=True)
            return None, 0.0

    def _parse_claude_response(
        self, response: dict, expected_count: int
    ) -> list[CatalystClassification] | None:
        """Parse Claude's JSON response into classifications.

        Args:
            response: The API response dict.
            expected_count: Expected number of classifications.

        Returns:
            List of classifications if parsing succeeds, None on error.
        """
        # Extract text content from response
        content = response.get("content", [])
        text_content = ""
        for block in content:
            if block.get("type") == "text":
                text_content += block.get("text", "")

        if not text_content:
            logger.warning("Empty response from Claude")
            return None

        # Try to parse as JSON
        try:
            # Handle potential markdown code fences
            text_content = text_content.strip()
            if text_content.startswith("```"):
                # Remove markdown fences
                lines = text_content.split("\n")
                text_content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            parsed = json.loads(text_content)

            # Handle both array and object responses
            if isinstance(parsed, dict):
                parsed = [parsed]

            if not isinstance(parsed, list):
                logger.warning("Claude response is not a list: %s", type(parsed))
                return None

            classifications: list[CatalystClassification] = []
            now = datetime.now(_ET)

            for item in parsed:
                try:
                    # Validate and normalize values
                    category = str(item.get("category", "other")).lower()
                    if category not in CatalystClassification.VALID_CATEGORIES:
                        category = "other"

                    quality_score = float(item.get("quality_score", 50))
                    quality_score = max(0, min(100, quality_score))  # Clamp to 0-100

                    summary = str(item.get("summary", ""))

                    relevance = str(item.get("trading_relevance", "low")).lower()
                    if relevance not in CatalystClassification.VALID_RELEVANCE:
                        relevance = "low"

                    classification = CatalystClassification(
                        category=category,
                        quality_score=quality_score,
                        summary=summary,
                        trading_relevance=relevance,
                        classified_by="claude",
                        classified_at=now,
                    )
                    classifications.append(classification)

                except (ValueError, KeyError, TypeError) as e:
                    logger.warning("Error parsing classification item: %s", e)
                    # Add a fallback for this item
                    classifications.append(
                        CatalystClassification(
                            category="other",
                            quality_score=25,
                            summary="Classification parsing failed",
                            trading_relevance="low",
                            classified_by="fallback",
                            classified_at=now,
                        )
                    )

            # If we got fewer classifications than expected, pad with fallbacks
            while len(classifications) < expected_count:
                classifications.append(
                    CatalystClassification(
                        category="other",
                        quality_score=25,
                        summary="No classification returned",
                        trading_relevance="low",
                        classified_by="fallback",
                        classified_at=now,
                    )
                )

            return classifications[:expected_count]

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Claude response as JSON: %s", e)
            return None

    def _classify_fallback(self, item: CatalystRawItem) -> CatalystClassification:
        """Classify an item using keyword matching.

        Args:
            item: The raw catalyst item to classify.

        Returns:
            A fallback classification based on keyword patterns.
        """
        headline = item.headline
        now = datetime.now(_ET)

        # Try each pattern in order
        for category, pattern in _FALLBACK_PATTERNS:
            if pattern.search(headline):
                # Assign score based on category relevance
                score_map = {
                    "earnings": 60,
                    "insider_trade": 55,
                    "analyst_action": 50,
                    "regulatory": 45,
                    "sec_filing": 40,
                    "corporate_event": 50,
                }
                quality_score = score_map.get(category, 30)

                relevance_map = {
                    "earnings": "medium",
                    "insider_trade": "medium",
                    "analyst_action": "medium",
                    "regulatory": "low",
                    "sec_filing": "low",
                    "corporate_event": "medium",
                }
                trading_relevance = relevance_map.get(category, "low")

                return CatalystClassification(
                    category=category,
                    quality_score=quality_score,
                    summary=f"Classified as {category} by keyword match",
                    trading_relevance=trading_relevance,
                    classified_by="fallback",
                    classified_at=now,
                )

        # Default: no pattern matched
        return CatalystClassification(
            category="other",
            quality_score=25,
            summary="No category pattern matched",
            trading_relevance="low",
            classified_by="fallback",
            classified_at=now,
        )

    async def _get_cached_classification(
        self, headline_hash: str
    ) -> CatalystClassification | None:
        """Get a cached classification if valid.

        Args:
            headline_hash: The headline hash to look up.

        Returns:
            Cached classification if found and valid, None otherwise.
        """
        if self._storage is None:
            return None

        ttl_hours = self._config.classification_cache_ttl_hours
        if not await self._storage.is_cache_valid(headline_hash, ttl_hours):
            return None

        return await self._storage.get_cached_classification(headline_hash)

    async def _cache_classification(
        self, headline_hash: str, classification: CatalystClassification
    ) -> None:
        """Cache a classification.

        Args:
            headline_hash: The headline hash to cache under.
            classification: The classification to cache.
        """
        if self._storage is None:
            return

        await self._storage.cache_classification(headline_hash, classification)

    async def _get_daily_cost(self) -> float:
        """Get today's total API cost.

        Returns:
            Today's total estimated cost in USD.
        """
        if self._usage_tracker is None:
            return 0.0
        today = datetime.now(_ET).date().isoformat()
        usage = await self._usage_tracker.get_daily_usage(today)
        return usage.get("estimated_cost_usd", 0.0)

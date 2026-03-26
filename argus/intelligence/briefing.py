"""Pre-market intelligence brief generator.

Generates structured markdown briefs from classified catalysts using
Claude API for narrative synthesis.

Sprint 23.5 Session 4 — DEC-164
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.intelligence.models import ClassifiedCatalyst, IntelligenceBrief

if TYPE_CHECKING:
    from argus.ai.client import ClaudeClient
    from argus.ai.usage import UsageTracker
    from argus.data.vix_data_service import VIXDataService
    from argus.intelligence.config import BriefingConfig
    from argus.intelligence.storage import CatalystStorage

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

# System prompt for brief generation
_BRIEFING_SYSTEM_PROMPT = """\
You are a trading intelligence analyst generating a concise pre-market briefing \
for an intraday equity trader. Your brief should be actionable and trading-focused.

Format your response as markdown with exactly these sections:
## Top Catalysts
Ranked by importance. Include symbol in **bold**, headline, quality score, and \
one-sentence trading implication.

## Earnings Calendar
Any earnings-related catalysts. Note if before/after market.

## Insider Activity
Form 4 filings, insider purchases/sales. Note if bullish/bearish signal.

## Analyst Actions
Upgrades, downgrades, price target changes.

## Risk Alerts
High-quality catalysts that suggest caution (regulatory issues, earnings misses, \
negative guidance).

If a section has no relevant items, write "None today."
Keep the brief concise but complete. Focus on trading implications.
"""


class BriefingGenerator:
    """Generates pre-market intelligence briefs from classified catalysts.

    Uses Claude API to synthesize catalyst data into a structured markdown
    brief with sections for top catalysts, earnings, insider activity,
    analyst actions, and risk alerts.

    Usage:
        generator = BriefingGenerator(client, storage, usage_tracker, config)
        brief = await generator.generate_brief(["AAPL", "TSLA", "NVDA"])
    """

    def __init__(
        self,
        client: ClaudeClient,
        storage: CatalystStorage,
        usage_tracker: UsageTracker,
        config: BriefingConfig,
        vix_data_service: VIXDataService | None = None,
    ) -> None:
        """Initialize the briefing generator.

        Args:
            client: Claude API client for generating narratives.
            storage: Catalyst storage for fetching and persisting briefs.
            usage_tracker: Tracks API usage and costs.
            config: Briefing configuration (max_symbols, model override).
            vix_data_service: Optional VIX data service for regime context.
        """
        self._client = client
        self._storage = storage
        self._usage_tracker = usage_tracker
        self._config = config
        self._vix_service = vix_data_service

    async def generate_brief(
        self,
        symbols: list[str],
        date: str | None = None,
    ) -> IntelligenceBrief:
        """Generate a pre-market intelligence brief.

        Fetches catalysts for the given symbols from the last 24 hours,
        groups them by category, and uses Claude to generate a structured
        markdown brief.

        Args:
            symbols: List of stock symbols to include in the brief.
            date: Trading date for the brief (YYYY-MM-DD). Defaults to today ET.

        Returns:
            Generated IntelligenceBrief with markdown content.
        """
        # Determine date
        now = datetime.now(_ET)
        if date is None:
            date = now.date().isoformat()

        # Cap symbols at max_symbols from config
        capped_symbols = symbols[: self._config.max_symbols]

        # Fetch catalysts for each symbol (last 24 hours)
        cutoff = now - timedelta(hours=24)
        all_catalysts: list[ClassifiedCatalyst] = []

        for symbol in capped_symbols:
            symbol_catalysts = await self._storage.get_catalysts_by_symbol(
                symbol, limit=100
            )
            # Filter to last 24 hours
            recent = [
                c for c in symbol_catalysts
                if self._is_within_cutoff(c.published_at, cutoff)
            ]
            all_catalysts.extend(recent)

        # Sort by quality score descending
        all_catalysts.sort(key=lambda c: c.quality_score, reverse=True)

        # Generate brief content
        if not all_catalysts:
            # No catalysts found - generate minimal brief
            content = f"# Pre-Market Brief for {date}\n\nNo material catalysts detected for {date}."
            generation_cost = 0.0
        else:
            # Group catalysts and generate via Claude
            content, generation_cost = await self._generate_with_claude(
                all_catalysts, date
            )

        # Create brief object
        brief = IntelligenceBrief(
            date=date,
            brief_type="premarket",
            content=content,
            symbols_covered=list(set(c.symbol for c in all_catalysts)),
            catalyst_count=len(all_catalysts),
            generated_at=datetime.now(_ET),
            generation_cost_usd=generation_cost,
        )

        # Store the brief
        await self._storage.store_brief(brief)

        logger.info(
            "Generated brief for %s: %d catalysts, %d symbols, $%.4f",
            date,
            len(all_catalysts),
            len(brief.symbols_covered),
            generation_cost,
        )

        return brief

    def _is_within_cutoff(self, dt: datetime, cutoff: datetime) -> bool:
        """Check if a datetime is within the cutoff.

        Handles timezone-aware and naive datetimes.

        Args:
            dt: The datetime to check.
            cutoff: The cutoff datetime (must have timezone).

        Returns:
            True if dt is after or equal to cutoff.
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_ET)
        return dt >= cutoff

    async def _generate_with_claude(
        self,
        catalysts: list[ClassifiedCatalyst],
        date: str,
    ) -> tuple[str, float]:
        """Generate brief content using Claude API.

        Args:
            catalysts: List of catalysts to include (already sorted by quality).
            date: Trading date for the header.

        Returns:
            Tuple of (markdown content, generation cost in USD).
        """
        if not self._client.enabled:
            # Claude disabled - generate simple fallback
            return self._generate_fallback(catalysts, date), 0.0

        # Group catalysts by category
        grouped = self._group_by_category(catalysts)

        # Build user message with catalyst data
        user_content = self._build_prompt(grouped, date)

        messages = [{"role": "user", "content": user_content}]

        try:
            response, usage = await self._client.send_message(
                messages=messages,
                system=_BRIEFING_SYSTEM_PROMPT,
                stream=False,
            )

            # Track usage
            await self._usage_tracker.record_usage(
                conversation_id=None,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                model=usage.model,
                estimated_cost_usd=usage.estimated_cost_usd,
                endpoint="briefing",
            )

            # Check for error response
            if response.get("type") == "error":
                logger.warning("Claude API error: %s", response.get("message"))
                return self._generate_fallback(catalysts, date), 0.0

            # Extract text content
            content = self._extract_content(response)
            if not content:
                return self._generate_fallback(catalysts, date), usage.estimated_cost_usd

            # Add header
            full_content = f"# Pre-Market Brief for {date}\n\n{content}"

            return full_content, usage.estimated_cost_usd

        except Exception as e:
            logger.error("Error generating brief with Claude: %s", e)
            return self._generate_fallback(catalysts, date), 0.0

    def _group_by_category(
        self,
        catalysts: list[ClassifiedCatalyst],
    ) -> dict[str, list[ClassifiedCatalyst]]:
        """Group catalysts by category.

        Args:
            catalysts: List of catalysts to group.

        Returns:
            Dict mapping category name to list of catalysts.
        """
        grouped: dict[str, list[ClassifiedCatalyst]] = {
            "earnings": [],
            "insider_trade": [],
            "analyst_action": [],
            "regulatory": [],
            "corporate_event": [],
            "sec_filing": [],
            "news_sentiment": [],
            "other": [],
        }

        for catalyst in catalysts:
            category = catalyst.category
            if category in grouped:
                grouped[category].append(catalyst)
            else:
                grouped["other"].append(catalyst)

        return grouped

    def _build_prompt(
        self,
        grouped: dict[str, list[ClassifiedCatalyst]],
        date: str,
    ) -> str:
        """Build the user prompt with catalyst data.

        Args:
            grouped: Catalysts grouped by category.
            date: Trading date.

        Returns:
            Formatted prompt string.
        """
        lines = [
            f"Generate a pre-market trading brief for {date}.",
            "",
            "Here are the classified catalysts:",
            "",
        ]

        # Top catalysts (first 10 by quality score)
        all_catalysts = []
        for category_list in grouped.values():
            all_catalysts.extend(category_list)
        all_catalysts.sort(key=lambda c: c.quality_score, reverse=True)

        lines.append("### Top Catalysts by Quality Score:")
        for i, cat in enumerate(all_catalysts[:10], 1):
            lines.append(
                f"{i}. **{cat.symbol}** ({cat.category}, score={cat.quality_score:.0f}): "
                f"{cat.headline}"
            )
            lines.append(f"   Summary: {cat.summary}")
        lines.append("")

        # Earnings
        if grouped["earnings"]:
            lines.append("### Earnings Catalysts:")
            for cat in grouped["earnings"][:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        lines.append("")

        # Insider activity
        if grouped["insider_trade"]:
            lines.append("### Insider Activity:")
            for cat in grouped["insider_trade"][:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        lines.append("")

        # Analyst actions
        if grouped["analyst_action"]:
            lines.append("### Analyst Actions:")
            for cat in grouped["analyst_action"][:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        lines.append("")

        # Risk alerts (high quality + high relevance)
        risk_alerts = [
            c for c in all_catalysts
            if c.quality_score > 70 and c.trading_relevance == "high"
        ]
        if risk_alerts:
            lines.append("### Potential Risk Alerts:")
            for cat in risk_alerts[:5]:
                lines.append(
                    f"- **{cat.symbol}** (score={cat.quality_score:.0f}): {cat.headline}"
                )
        lines.append("")

        # Append VIX context if available
        vix_context = self._build_vix_context()
        if vix_context is not None:
            lines.append(vix_context)
            lines.append("")

        return "\n".join(lines)

    def _build_vix_context(self) -> str | None:
        """Build VIX regime context section for the user message.

        Returns:
            Formatted VIX context string, or None if unavailable/stale.
        """
        if self._vix_service is None or not self._vix_service.is_ready:
            return None
        latest = self._vix_service.get_latest_daily()
        if latest is None:
            return None
        # Stale data has None for derived metrics — skip section
        if latest.get("variance_risk_premium") is None:
            return None

        vix_close = latest.get("vix_close", "N/A")
        data_date = latest.get("data_date", "unknown")
        vrp = latest.get("variance_risk_premium")
        vrp_str = f"{vrp:.1f}" if vrp is not None else "N/A"

        lines = [
            "### VIX Regime Context",
            f"- VIX Close: {vix_close} (as of {data_date})",
            f"- Variance Risk Premium: {vrp_str}",
        ]

        # Add optional regime classifications if present
        vol_of_vol = latest.get("vol_of_vol_ratio")
        if vol_of_vol is not None:
            lines.append(f"- Vol-of-Vol Ratio: {vol_of_vol:.2f}")

        vix_pct = latest.get("vix_percentile")
        if vix_pct is not None:
            lines.append(f"- VIX Percentile: {vix_pct:.0%}")

        term_proxy = latest.get("term_structure_proxy")
        if term_proxy is not None:
            lines.append(f"- Term Structure Proxy: {term_proxy:.3f}")

        return "\n".join(lines)

    def _extract_content(self, response: dict) -> str:
        """Extract text content from API response.

        Args:
            response: The API response dict.

        Returns:
            Extracted text content.
        """
        content_parts = []
        for block in response.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))
        return "\n".join(content_parts)

    def _generate_fallback(
        self,
        catalysts: list[ClassifiedCatalyst],
        date: str,
    ) -> str:
        """Generate a simple fallback brief without Claude.

        Args:
            catalysts: List of catalysts.
            date: Trading date.

        Returns:
            Simple markdown brief.
        """
        lines = [
            f"# Pre-Market Brief for {date}",
            "",
            "## Top Catalysts",
            "",
        ]

        # Top 10 by quality score
        sorted_cats = sorted(catalysts, key=lambda c: c.quality_score, reverse=True)
        for i, cat in enumerate(sorted_cats[:10], 1):
            lines.append(
                f"{i}. **{cat.symbol}** ({cat.category}, {cat.quality_score:.0f}): "
                f"{cat.headline}"
            )
        lines.append("")

        # Group remaining sections
        grouped = self._group_by_category(catalysts)

        # Earnings
        lines.append("## Earnings Calendar")
        if grouped["earnings"]:
            for cat in grouped["earnings"][:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        else:
            lines.append("None today.")
        lines.append("")

        # Insider activity
        lines.append("## Insider Activity")
        if grouped["insider_trade"]:
            for cat in grouped["insider_trade"][:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        else:
            lines.append("None today.")
        lines.append("")

        # Analyst actions
        lines.append("## Analyst Actions")
        if grouped["analyst_action"]:
            for cat in grouped["analyst_action"][:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        else:
            lines.append("None today.")
        lines.append("")

        # Risk alerts
        lines.append("## Risk Alerts")
        risk_alerts = [
            c for c in catalysts
            if c.quality_score > 70 and c.trading_relevance == "high"
        ]
        if risk_alerts:
            for cat in risk_alerts[:5]:
                lines.append(f"- **{cat.symbol}**: {cat.headline}")
        else:
            lines.append("None today.")

        return "\n".join(lines)

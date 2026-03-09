# Sprint 23.5: What This Sprint Does NOT Do

## Out of Scope

1. **Automated PreMarketEngine scheduler**: The full 4:00 AM → 9:25 AM automated pipeline that orchestrates scanning, catalyst research, and watchlist locking is deferred to Sprint 24. This sprint provides manual-trigger briefing generation only (`POST /api/v1/premarket/briefing/generate`). Why: PreMarketEngine requires integration with the Scanner and Universe Manager startup sequence, which is Sprint 24 scope alongside the Quality Engine.

2. **SignalEvent enrichment with catalyst data**: Strategies do not see catalyst data. SignalEvent gains no new fields. Quality Engine (Sprint 24) will subscribe to CatalystEvents and incorporate them into composite scoring. Why: AI layer strict separation (DEC-170) — intelligence enriches signals through the Quality Engine, not by modifying strategy internals.

3. **Dynamic position sizing based on catalyst quality**: Position sizing remains fixed risk_per_trade_pct. DynamicPositionSizer is Sprint 24 scope. Why: sizing requires the full Quality Engine pipeline, not just catalysts.

4. **Real-time sub-second news processing**: The pipeline polls on configurable intervals (15 min pre-market, 30 min session). This is batch processing, not streaming. Why: day trading catalysts are overwhelmingly overnight events. Sub-second latency adds complexity with negligible alpha for 5–30 minute hold strategies from Taipei (150–200ms structural latency).

5. **Finnhub WebSocket**: Only REST API polling. WebSocket was rejected for scanning (DEC-260, stale feeds). Why: REST polling at 30-min intervals is sufficient; WebSocket adds complexity and reliability risk.

6. **Intraday catalyst re-scanning with dynamic Databento subscription adds**: The pipeline does not trigger new Databento subscriptions when catalysts fire. That integration is part of the broader intraday universe expansion (Sprint 24+). Why: Databento subscription management is complex and entangled with the Universe Manager's routing table rebuild.

7. **FMP plan upgrade**: Stay on Starter ($22/mo). Premium/Ultimate features (earnings transcripts, 1-min intraday, bulk data) are not needed for this sprint's news + press release + earnings calendar scope. Why: evaluate whether Starter endpoints are sufficient before committing to higher cost.

8. **Order Flow integration**: Order Flow Model requires Databento Plus ($1,399/mo, DEC-238). Deferred to post-revenue. Why: cost.

9. **SEC EDGAR full-text search / filing content analysis**: The pipeline ingests filing metadata (type, date, items) but does not download and parse full filing content. Why: full-text analysis is expensive (bandwidth, Claude API tokens) and metadata classification covers the day trading use case (knowing that an 8-K was filed with Item 2.02 "Results of Operations" is sufficient signal).

10. **Catalyst-driven Orchestrator behavior changes**: The Orchestrator alert panel is display-only. The Orchestrator does not use catalyst data for allocation, throttling, or strategy activation decisions. Why: AI layer strict separation (DEC-170). Orchestrator behavior changes require adversarial review and are Sprint 24+ scope.

## Edge Cases to Reject

1. **Symbol not in Universe Manager's viable list AND not in FMP Scanner watchlist**: Do not fetch catalysts. Return empty. Log at DEBUG level only — this is the expected path for most of the ~8,000 US equities.

2. **SEC EDGAR CIK not found for a ticker**: Skip that symbol for SEC source. Log warning. Other sources (FMP, Finnhub) still provide coverage.

3. **Claude API returns malformed classification JSON**: Fallback to rule-based classifier for that batch. Log error with full API response for debugging. Do not retry — queue for next poll cycle.

4. **Claude API cost ceiling reached mid-poll**: Stop classifying. Queue remaining unclassified headlines. Publish raw (unclassified) items to storage with `quality_score=None` and `catalyst_type="unclassified"`. Resume classification on next day or when ceiling is manually raised.

5. **Duplicate headline from multiple sources**: Deduplicate by headline hash (SHA-256 of lowercase stripped headline). First source wins. Do not classify duplicates.

6. **Briefing requested when no catalysts exist**: Generate a brief with "No material catalysts detected" message. Do not return error.

7. **Briefing requested twice for same date**: Overwrite previous brief. Keep only the most recent generation per date.

8. **API rate limit hit (any source)**: Exponential backoff with jitter. Maximum 3 retries per poll cycle. If all retries fail, skip that source for this cycle. Log warning.

9. **Extremely long headline (>500 chars)**: Truncate to 500 chars for classification. Store full headline in `catalyst_events` table.

## Scope Boundaries

- **Do NOT modify:** `argus/ai/*`, `argus/strategies/*`, `argus/core/risk_manager.py`, `argus/core/orchestrator.py`, `argus/execution/*`, `argus/data/universe_manager.py`, `argus/data/fmp_scanner.py`, `argus/data/fmp_reference.py`, `argus/data/databento_data_service.py`, `argus/analytics/*`
- **Do NOT optimize:** Polling cadence (configurable but not auto-tuned). Classification prompt (V1 — optimization is a future concern). SQLite storage schema (simple, not performance-optimized for high volume).
- **Do NOT refactor:** Existing Debrief document storage. Existing Event Bus subscriber patterns. Existing API authentication middleware.
- **Do NOT add:** New Event Bus subscribers for CatalystEvent (the event is defined and published, but no component subscribes in this sprint — Quality Engine in Sprint 24 will be the first subscriber). WebSocket endpoint for catalyst streaming. AI Copilot integration with catalyst data.

## Interaction Boundaries

- This sprint does NOT change the behavior of: Event Bus (CatalystEvent is a new event type, additive only), API authentication, existing REST endpoints, AI Copilot WebSocket, Universe Manager, FMP Scanner, any strategy, Risk Manager, Orchestrator logic, Order Manager, Broker abstraction.
- This sprint does NOT affect: Live paper trading execution path (catalyst pipeline is parallel, not in the signal→order critical path). Existing Dashboard cards (catalyst badges are new additions, not replacements). Existing Debrief tabs (Intelligence Brief is a new section).

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Automated PreMarketEngine (4 AM → 9:25 AM) | Sprint 24 | DEF-NEW-1 |
| SignalEvent enrichment with catalyst quality | Sprint 24 | DEF-NEW-2 |
| Dynamic position sizing from catalyst quality | Sprint 24 | DEF-NEW-3 |
| Catalyst quality → Quality Engine integration | Sprint 24 | DEF-NEW-4 |
| Intraday catalyst re-scanning | Sprint 24+ | DEF-NEW-5 |
| FMP Premium/Ultimate upgrade evaluation | Sprint 24+ | DEF-NEW-6 |
| SEC EDGAR full-text filing analysis | Unscheduled | DEF-NEW-7 |
| Finnhub WebSocket (if REST proves insufficient) | Unscheduled | DEF-NEW-8 |
| Catalyst-driven Orchestrator behavior | Sprint 24+ | DEF-NEW-9 |
| CatalystEvent subscriber (Quality Engine) | Sprint 24 | DEF-NEW-10 |

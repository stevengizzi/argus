# Sprint 23.5: NLP Catalyst Pipeline

## Goal

Build the NLP Catalyst Pipeline — ARGUS's first intelligence module. Ingest news and filings from SEC EDGAR, FMP, and Finnhub; classify catalyst quality via Claude API with dynamic batch sizing; emit CatalystEvents on the Event Bus; generate pre-market intelligence briefs; and surface catalysts in the Command Center (Dashboard badges, Orchestrator alert panel, Debrief intelligence brief view). Config-gated with default disabled for backward compatibility.

## Scope

### Deliverables

1. **CatalystEvent + data models + Pydantic config**: New `argus/intelligence/` module with CatalystEvent on Event Bus, data models (CatalystRawItem, CatalystClassification, IntelligenceBrief), and CatalystConfig Pydantic model with full `catalyst:` config section in system.yaml.

2. **CatalystSource ABC + 3 client implementations**: Abstract base class for data source clients with concrete implementations for SEC EDGAR (8-K, Form 4 filings via data.sec.gov REST API), FMP News (stock news + press releases via existing Starter plan), and Finnhub (company news + analyst recommendations via free tier REST API). Each client: fetches raw items, deduplicates by headline hash, respects per-source rate limits, handles errors gracefully.

3. **CatalystClassifier**: Claude API batch classification with dynamic batch sizing (simple headlines in larger batches, complex in smaller, capped at `max_batch_size`). Classification output: category (8 types), quality_score (0–100), summary, trading_relevance. Headline hash cache prevents re-classification. Rule-based fallback when Claude API unavailable. Daily cost ceiling enforcement via UsageTracker (DEC-274).

4. **CatalystPipeline + storage**: Pipeline assembler wiring sources → dedup → classifier → SQLite storage → Event Bus publication. Two new tables: `catalyst_events` (all classified catalysts), `intelligence_briefs` (generated briefs). Classification cache stored in `catalyst_classifications` table.

5. **REST API endpoints**: `GET /api/v1/catalysts/{symbol}` (catalysts for a symbol), `GET /api/v1/catalysts/recent` (recent catalysts across all symbols), `GET /api/v1/premarket/briefing` (current briefing), `GET /api/v1/premarket/briefing/history` (past briefings), `POST /api/v1/premarket/briefing/generate` (trigger briefing generation).

6. **BriefingGenerator**: Claude API-powered narrative generation synthesizing overnight/pre-market catalysts for watchlist symbols. Structured sections: Top Catalysts, Earnings Calendar, Insider Activity, Analyst Actions, Risk Alerts. Stored to `intelligence_briefs` table and accessible via Debrief.

7. **Dashboard catalyst badges**: Small colored pills on watchlist entries showing catalyst type + count. Clicking opens catalyst detail. Empty state when no catalysts.

8. **Orchestrator catalyst alert panel**: Scrolling feed of recent CatalystEvents with quality scores, source indicators, and timestamps. Auto-refreshes during market hours.

9. **Debrief Intelligence Brief view**: Rendered markdown view of pre-market intelligence briefs. Date navigation to browse past briefs. Loading and empty states.

### Acceptance Criteria

1. **CatalystEvent + models + config:**
   - CatalystEvent class exists in `argus/core/events.py` with all specified fields
   - CatalystConfig Pydantic model validates all 14 config fields from system.yaml
   - Config validation test confirms no silently ignored YAML keys
   - `catalyst.enabled: false` is the default; system operates identically to pre-sprint when disabled

2. **CatalystSource clients:**
   - SEC EDGAR client parses 8-K and Form 4 filings from data.sec.gov JSON responses
   - SEC EDGAR client maps CIK to ticker using SEC company tickers endpoint
   - FMP News client fetches stock_news and press-releases endpoints
   - Finnhub client fetches company-news and recommendation-trends endpoints
   - Each client respects its rate limit (SEC: 10 req/sec, FMP: 300/min, Finnhub: 60/min)
   - Each client returns `list[CatalystRawItem]` conforming to the ABC contract
   - Each client handles API errors gracefully (returns empty list, logs error)
   - Each client can be independently disabled via config
   - System operates normally when any individual API key is missing

3. **CatalystClassifier:**
   - Classifies headlines into exactly 8 categories: `earnings`, `insider_trade`, `sec_filing`, `analyst_action`, `corporate_event`, `news_sentiment`, `regulatory`, `other`
   - Produces quality_score in range 0–100 for each headline
   - Batch sizes dynamically determined, never exceeding `max_batch_size` config
   - Identical headlines (by hash) return cached classification without Claude API call
   - Rule-based fallback produces valid classifications when Claude API unavailable
   - Daily cost ceiling prevents spend exceeding `daily_cost_ceiling_usd` config
   - Cost tracked via existing UsageTracker infrastructure

4. **CatalystPipeline + storage:**
   - Pipeline wires sources → dedup → classifier → storage → CatalystEvent publication
   - Duplicate headlines across sources are deduplicated before classification
   - `catalyst_events` table persists all classified catalysts with correct schema
   - `intelligence_briefs` table persists generated briefs
   - CatalystEvent published on Event Bus for each newly classified catalyst
   - Pipeline runs on configurable polling interval (pre-market vs session)

5. **REST API endpoints:**
   - `GET /api/v1/catalysts/{symbol}` returns catalysts for the given symbol, sorted by recency
   - `GET /api/v1/catalysts/recent` returns recent catalysts across all symbols with pagination
   - `GET /api/v1/premarket/briefing` returns the most recent briefing for today (or 404)
   - `GET /api/v1/premarket/briefing/history` returns past briefings with date filtering
   - `POST /api/v1/premarket/briefing/generate` triggers briefing generation and returns result
   - All endpoints require JWT authentication (existing auth middleware)
   - All endpoints return appropriate error responses for missing data

6. **BriefingGenerator:**
   - Generates structured markdown brief with 5 sections (Top Catalysts, Earnings Calendar, Insider Activity, Analyst Actions, Risk Alerts)
   - Brief focuses on watchlist symbols (max `briefing.max_symbols` from config)
   - Brief stored to `intelligence_briefs` table with date and content
   - Brief generation works with zero catalysts (produces "no material catalysts" message)
   - Brief generation cost tracked via UsageTracker

7. **Dashboard catalyst badges:**
   - Badges appear next to watchlist entries that have catalysts
   - Badge shows catalyst type icon/color and count
   - No badges shown for symbols without catalysts
   - Badges render correctly in loading and error states

8. **Orchestrator catalyst alert panel:**
   - Panel shows scrolling feed of recent catalyst events
   - Each entry shows: symbol, catalyst type, quality score, headline excerpt, source, time
   - Panel auto-refreshes every 30 seconds during market hours
   - Empty state displayed when no recent catalysts

9. **Debrief Intelligence Brief view:**
   - Brief content rendered as formatted markdown
   - Date picker/navigation allows browsing past briefs
   - Loading spinner during fetch, empty state when no brief for date
   - "Generate Brief" button triggers `POST /api/v1/premarket/briefing/generate`

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Single source poll (SEC EDGAR) | < 5 seconds for 30 symbols | pytest timing in integration test |
| Single source poll (FMP News) | < 3 seconds for 30 symbols | pytest timing in integration test |
| Single source poll (Finnhub) | < 5 seconds for 30 symbols | pytest timing in integration test |
| Batch classification (20 headlines) | < 10 seconds | pytest timing with mocked Claude response |
| Briefing generation | < 30 seconds | pytest timing with mocked Claude response |
| GET /api/v1/catalysts/{symbol} | < 100ms | pytest timing against SQLite |
| GET /api/v1/catalysts/recent | < 200ms | pytest timing against SQLite |
| Dashboard re-render with badges | No visual jank | Visual review |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `catalyst.enabled` | `CatalystConfig` | `enabled` | `false` |
| `catalyst.polling_interval_premarket_seconds` | `CatalystConfig` | `polling_interval_premarket_seconds` | `900` |
| `catalyst.polling_interval_session_seconds` | `CatalystConfig` | `polling_interval_session_seconds` | `1800` |
| `catalyst.max_batch_size` | `CatalystConfig` | `max_batch_size` | `20` |
| `catalyst.daily_cost_ceiling_usd` | `CatalystConfig` | `daily_cost_ceiling_usd` | `5.0` |
| `catalyst.classification_cache_ttl_hours` | `CatalystConfig` | `classification_cache_ttl_hours` | `24` |
| `catalyst.sources.sec_edgar.enabled` | `SECEdgarConfig` | `enabled` | `true` |
| `catalyst.sources.sec_edgar.filing_types` | `SECEdgarConfig` | `filing_types` | `["8-K", "4"]` |
| `catalyst.sources.fmp_news.enabled` | `FMPNewsConfig` | `enabled` | `true` |
| `catalyst.sources.fmp_news.api_key_env_var` | `FMPNewsConfig` | `api_key_env_var` | `"FMP_API_KEY"` |
| `catalyst.sources.finnhub.enabled` | `FinnhubConfig` | `enabled` | `true` |
| `catalyst.sources.finnhub.api_key_env_var` | `FinnhubConfig` | `api_key_env_var` | `"FINNHUB_API_KEY"` |
| `catalyst.briefing.model` | `BriefingConfig` | `model` | `null` (inherits `ai.model`) |
| `catalyst.briefing.max_symbols` | `BriefingConfig` | `max_symbols` | `30` |

## Dependencies

- Sprint 23 (Universe Manager) complete — CatalystPipeline reads viable symbols from UniverseManager
- Sprint 22 (AI Layer) complete — CatalystClassifier uses ClaudeClient and UsageTracker
- Sprint 21.7 (FMP Scanner) complete — FMP API key already configured
- `FMP_API_KEY` environment variable set (already active)
- `FINNHUB_API_KEY` environment variable set (new — free tier from finnhub.io)
- SEC EDGAR requires User-Agent header with contact email per SEC fair access policy

## Relevant Decisions

- DEC-164: Free sources first — SEC EDGAR, Finnhub free, FMP Starter. Paid upgrade trigger: >30% unclassified rate over 20 days.
- DEC-098: Claude Opus for all API calls — classifier and briefing use same model.
- DEC-263: Full-universe monitoring architecture — CatalystPipeline monitors Universe Manager symbols.
- DEC-257/258: Hybrid Databento+FMP architecture — FMP news endpoints already available on Starter.
- DEC-029: Event Bus sole streaming mechanism — CatalystEvent published via Event Bus.
- DEC-273: System prompt + guardrails — classifier prompt follows established patterns.
- DEC-274: Per-call cost tracking — classifier uses existing UsageTracker for daily ceiling.
- DEC-170: AI Copilot boundary — intelligence layer reads/publishes but never modifies core trading components.

## Relevant Risks

- RSK-NEW-1: Finnhub free tier reliability — DEC-260 noted stale WebSocket feeds; REST API may have similar issues. Mitigation: Finnhub is supplementary, not primary. System works without it.
- RSK-NEW-2: Claude API classification cost — dynamic batching reduces cost but unpredictable headline volume could spike usage. Mitigation: daily cost ceiling, UsageTracker monitoring.
- RSK-NEW-3: SEC EDGAR rate limiting — SEC enforces 10 req/sec and may block aggressive polling. Mitigation: built-in rate limiter, User-Agent compliance, conservative polling cadence.
- RSK-022: IBKR Gateway nightly resets — unrelated but CatalystPipeline runs during pre-market when reconnection may be active. Mitigation: pipeline operates independently of broker connection.

## Session Count Estimate

7 sessions estimated (6 main + 1 visual-review fix contingency). Rationale: 4 backend sessions (S1–S4) covering foundation, data ingestion, classification, and API/briefing. 2 frontend sessions (S5–S6) covering 3 pages. S6f budgets 0.5 session for visual fixes. S5 and S6 are parallelizable (disjoint file sets). Session count aligns with Sprint 22's density (6 main sessions for comparable backend+frontend scope) but with better compaction risk distribution (no session scores above 15).

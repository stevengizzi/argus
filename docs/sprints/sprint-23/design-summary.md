# Sprint 23 Design Summary

**Sprint Goal:** Replace the static pre-market watchlist with a Universe Manager that monitors the broad US equity universe (~8,000+ symbols via Databento ALL_SYMBOLS), caches FMP reference data (sector, market cap, float) for ~3,000–5,000 viable symbols, and routes candle events to strategies based on declarative `universe_filter` YAML config. This is the infrastructure foundation for the expanded vision (DEC-163, DEC-263).

**Session Breakdown:**

- **Session 1a:** FMP Reference Data Client
  - Creates: `argus/data/fmp_reference.py` (batch Company Profile + Share Float fetcher, caching, error handling)
  - Modifies: None
  - Integrates: N/A
  - Score: 13 (Medium)

- **Session 1b:** Universe Manager Core
  - Creates: `argus/data/universe_manager.py` (reference data cache, viable universe construction, system-level filters)
  - Modifies: None
  - Integrates: Session 1a (uses FMPReferenceClient)
  - Score: 11 (Medium)

- **Session 2a:** Universe Filter Config Model
  - Creates: None
  - Modifies: `argus/core/config.py` (add UniverseFilterConfig + UniverseManagerConfig Pydantic models)
  - Integrates: N/A
  - Score: 7 (Low)

- **Session 2b:** ORB Family Filter Declarations
  - Creates: None
  - Modifies: `config/strategies/orb_breakout.yaml`, `config/strategies/orb_scalp.yaml`
  - Integrates: Session 2a (uses UniverseFilterConfig)
  - Score: 8 (Low)

- **Session 2c:** VWAP + Afternoon Momentum Filter Declarations
  - Creates: None
  - Modifies: `config/strategies/vwap_reclaim.yaml`, `config/strategies/afternoon_momentum.yaml`
  - Integrates: Session 2a (uses UniverseFilterConfig)
  - Score: 8 (Low)

- **Session 3a:** Routing Table Construction
  - Creates: None
  - Modifies: `argus/data/universe_manager.py` (add routing table: symbol → set[strategy_id], `route_candle()` method)
  - Integrates: Sessions 1b + 2a/2b/2c (combines universe + filters into routing)
  - Score: 7 (Low)

- **Session 3b:** Databento Fast-Path + Event Integration
  - Creates: None
  - Modifies: `argus/data/databento_data_service.py` (fast-path discard for non-viable symbols), `argus/core/events.py` (add UniverseUpdateEvent if needed)
  - Integrates: Session 3a (routing table consulted on each candle)
  - Score: 13 (Medium)

- **Session 4a:** Universe Manager System Config
  - Creates: None
  - Modifies: `argus/core/config.py` (add UniverseManagerConfig to SystemConfig/ArgusConfig), `config/system.yaml` (add universe_manager section)
  - Integrates: N/A
  - Score: 7 (Low)

- **Session 4b:** Main.py Startup Wiring
  - Creates: None
  - Modifies: `argus/main.py` (replace scanner→set_watchlist→data_service.start flow with Universe Manager path when enabled; preserve backward compat for replay/backtest)
  - Integrates: All prior sessions into startup flow
  - Score: 12 (Medium)

- **Session 5a:** Backend API Endpoints for Universe Data
  - Creates: `argus/api/routes/universe.py` (GET /api/v1/universe/status, GET /api/v1/universe/symbols)
  - Modifies: `argus/api/dependencies.py` (expose universe_manager in AppState)
  - Integrates: Universe Manager into API layer
  - Score: 8 (Low)

- **Session 5b:** Frontend — Dashboard Universe Panel
  - Creates: New UI components (UniverseStatusCard or similar)
  - Modifies: Dashboard page (add universe stats panel), possibly watchlist integration
  - Integrates: Session 5a API endpoints
  - Score: 11 (Medium)

- **Session 5f:** Visual-review fixes — contingency, 0.5 session

**Key Decisions:**

- **ALL_SYMBOLS subscription:** Databento subscribes to ALL_SYMBOLS. Filtering happens in software via fast-path discard in DatabentoDataService (check viable universe set) and routing table (check strategy filters). Simpler than managing dynamic subscription lists.
- **FMP reference data:** Batch Company Profile + Share Float endpoints on existing Starter plan ($22/mo). Cached daily. ~80 API calls for 4,000 symbols via batch endpoint. Fallback to price-only filtering if FMP unavailable.
- **Cold-start indicators:** No batch warm-up for broad universe in Sprint 23. IndicatorEngine instances start cold. ATR/SMA converge after ~20–50 bars (~20–50 minutes). Acceptable for paper trading. Batch warm-up deferred to future sprint if needed.
- **Backward compatibility:** Universe Manager is config-gated (`universe_manager.enabled: true/false`). When disabled, existing scanner→set_watchlist→data_service.start flow is unchanged. Replay/backtest modes always use the old path.
- **No intraday re-scanning:** Pre-market universe is held for the full trading day. Dynamic intraday expansion deferred to Sprint 23.5+.
- **Sprint 23.5 scope (NOT this sprint):** NLP Catalyst Pipeline (SEC EDGAR, FMP news, Claude API), CatalystEvent, Pre-Market Intelligence Brief, catalyst badges, AI debrief narratives, intraday re-scanning.

**Scope Boundaries:**
- IN: Universe Manager, FMP reference data client, strategy universe_filter YAML schema for all 4 strategies, routing table, Databento ALL_SYMBOLS activation, fast-path event discard, main.py integration, system config, API endpoints, Dashboard universe panel
- OUT: Catalyst pipeline, SEC EDGAR, FMP news, intelligence brief, catalyst badges, AI narratives, intraday re-scanning, indicator warm-up for broad universe, FMP plan upgrade, Finnhub

**Regression Invariants:**
1. All existing tests pass (1,977 pytest + 377 Vitest)
2. When universe_manager.enabled=false, system behavior is identical to pre-Sprint-23
3. Strategies receive CandleEvents only for symbols matching their filters (no extra candles)
4. Risk Manager limits unaffected
5. ORB same-symbol mutual exclusion (DEC-261) still enforced
6. FMP Scanner still works as pre-market scanner (Universe Manager wraps it, doesn't replace it)
7. Backtesting/replay modes unchanged
8. AI Copilot (Sprint 22) unaffected

**File Scope:**
- Create: `argus/data/fmp_reference.py`, `argus/data/universe_manager.py`, `argus/api/routes/universe.py`, frontend universe components
- Modify: `argus/core/config.py`, `config/system.yaml`, `config/strategies/*.yaml` (×4), `argus/data/databento_data_service.py`, `argus/core/events.py`, `argus/main.py`, `argus/api/dependencies.py`, Dashboard UI
- Do not modify: `argus/ai/` (AI layer), `argus/core/orchestrator.py` (Orchestrator logic), `argus/core/risk_manager.py`, `argus/execution/` (Order Manager, brokers), `argus/analytics/` (Trade Logger), `argus/strategies/*.py` (strategy logic — only YAML configs change)

**Config Changes:**

System-level (system.yaml → UniverseManagerConfig):
| YAML Path | Pydantic Field | Default |
|-----------|---------------|---------|
| universe_manager.enabled | enabled | false |
| universe_manager.min_price | min_price | 5.0 |
| universe_manager.max_price | max_price | 10000.0 |
| universe_manager.min_avg_volume | min_avg_volume | 100000 |
| universe_manager.exclude_otc | exclude_otc | true |
| universe_manager.reference_cache_ttl_hours | reference_cache_ttl_hours | 24 |
| universe_manager.fmp_batch_size | fmp_batch_size | 50 |

Strategy-level (strategies/*.yaml → UniverseFilterConfig):
| YAML Path | Pydantic Field | Default |
|-----------|---------------|---------|
| universe_filter.min_price | min_price | None |
| universe_filter.max_price | max_price | None |
| universe_filter.min_market_cap | min_market_cap | None |
| universe_filter.max_market_cap | max_market_cap | None |
| universe_filter.min_float | min_float | None |
| universe_filter.min_avg_volume | min_avg_volume | None |
| universe_filter.sectors | sectors | [] |
| universe_filter.exclude_sectors | exclude_sectors | [] |

**Test Strategy:**
- Estimated ~97 new tests (~75 pytest + ~22 Vitest)
- Estimation: 2 new files × 5 = 10, 8 modified files × 3 = 24, 2 API endpoints × 2 = 4, base = 38. Infrastructure multiplier 2× on core sessions → ~76 backend. ~22 frontend.
- Key test categories: FMP batch mocking, universe construction, filter matching, routing correctness, config validation (YAML↔Pydantic), main.py integration (UM-enabled vs disabled), API endpoints, frontend components
- Config validation test: loads each YAML and verifies all keys recognized by Pydantic model

**Dependencies:**
- Sprint 22 complete (AI layer — no changes needed, but must not regress)
- FMP API key set in environment (existing from Sprint 21.7)
- Databento API key set in environment (existing from Sprint 12)
- No new external dependencies or plan upgrades

**Escalation Criteria:**
- Universe Manager adds >50ms latency to candle processing pipeline → ESCALATE
- FMP reference data fetch takes >5 minutes → ESCALATE (batch endpoint may not be on Starter)
- ALL_SYMBOLS subscription causes Databento session errors or rate limiting → ESCALATE
- Any existing strategy test fails after Session 4b → ESCALATE
- Memory usage exceeds 500MB above baseline with full universe loaded → ESCALATE

**Doc Updates Needed:**
- `docs/architecture.md` — new Universe Manager section in §3.2, updated Data Flow diagram in §3.2b
- `docs/project-knowledge.md` — Sprint 23 entry, updated "Current State" section
- `docs/decision-log.md` — new DECs for Universe Manager architecture, ALL_SYMBOLS decision, filter schema
- `docs/dec-index.md` — index new DECs
- `docs/sprint-history.md` — Sprint 23 entry
- `docs/roadmap.md` — mark Sprint 23 complete, update current state
- `CLAUDE.md` — update with Universe Manager context
- `docs/strategies/STRATEGY_*.md` — add universe_filter sections to each strategy spec sheet
- `config/system.yaml` — new universe_manager section (done during implementation)
- `config/strategies/*.yaml` — new universe_filter sections (done during implementation)

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates per session, scoring tables)
4. Sprint-Level Escalation Criteria
5. Sprint-Level Regression Checklist
6. Doc Update Checklist
7. Review Context File
8. Implementation Prompts ×11 (Sessions 1a, 1b, 2a, 2b, 2c, 3a, 3b, 4a, 4b, 5a, 5b)
9. Tier 2 Review Prompts ×11

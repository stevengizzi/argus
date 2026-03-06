# Sprint 23: Session Breakdown

## Session 1a: FMP Reference Data Client

**Objective:** Build the FMP batch reference data fetcher with caching and error handling.

**Creates:** `argus/data/fmp_reference.py`
**Modifies:** —
**Integrates:** N/A (standalone module)

**Scope:**
- `FMPReferenceClient` class with batch Company Profile fetch (comma-separated tickers, ~50 per call)
- Share Float batch fetch
- `SymbolReferenceData` dataclass: symbol, sector, market_cap, float_shares, exchange, prev_close, avg_volume
- In-memory cache with TTL
- Rate limiting (300 calls/min on Starter)
- Graceful degradation: returns partial data on failure, logs warnings
- Uses existing `FMP_API_KEY` environment variable

**Tests:** ~8
- Batch endpoint mocking (success, partial failure, full failure)
- Cache TTL behavior
- Rate limiting
- SymbolReferenceData validation

| Factor | Points |
|--------|--------|
| New files created (1 × 2) | 2 |
| Files modified (0) | 0 |
| Pre-flight context reads (2: fmp_scanner.py pattern, architecture doc) | 2 |
| New tests (8 × 0.5) | 4 |
| External API debugging (FMP batch) | 3 |
| Large file >150 lines (1 × 2) | 2 |
| **TOTAL** | **13 (Medium)** |

---

## Session 1b: Universe Manager Core

**Objective:** Build the UniverseManager class with viable universe construction and system-level filtering.

**Creates:** `argus/data/universe_manager.py`
**Modifies:** —
**Integrates:** Session 1a (`FMPReferenceClient`)

**Scope:**
- `UniverseManager` class
- `build_viable_universe()`: calls FMPReferenceClient, applies system-level filters (exclude OTC, price range, volume), returns set of viable symbols
- `viable_symbols` property: the current viable set
- `get_reference_data(symbol)`: lookup cached reference data for a symbol
- System-level filter logic: exclude_otc, min_price, max_price, min_avg_volume
- Graceful degradation: if FMP fails, viable universe = scanner results (existing 15 symbols)
- Logging: universe size, filter pass rates

**Tests:** ~8
- Viable universe construction (mock FMP data)
- System-level filter application (each filter)
- Graceful degradation (FMP failure)
- Empty universe handling

| Factor | Points |
|--------|--------|
| New files created (1 × 2) | 2 |
| Files modified (0) | 0 |
| Pre-flight context reads (3: fmp_reference.py, config.py, scanner.py) | 3 |
| New tests (8 × 0.5) | 4 |
| Large file >150 lines (1 × 2) | 2 |
| **TOTAL** | **11 (Medium)** |

---

## Session 2a: Universe Filter Config Model

**Objective:** Add the Pydantic config models for universe filtering.

**Creates:** —
**Modifies:** `argus/core/config.py`
**Integrates:** N/A (config models used by later sessions)

**Scope:**
- `UniverseFilterConfig` Pydantic model: min_price, max_price, min_market_cap, max_market_cap, min_float, min_avg_volume, sectors (list[str]), exclude_sectors (list[str]). All fields Optional with None default.
- `UniverseManagerConfig` Pydantic model: enabled, min_price, max_price, min_avg_volume, exclude_otc, reference_cache_ttl_hours, fmp_batch_size.
- Integrate `UniverseFilterConfig` as optional field on `StrategyConfig`
- Integrate `UniverseManagerConfig` into `SystemConfig`
- Config loading updates if needed

**Tests:** ~8
- UniverseFilterConfig validation (valid, edge cases, type errors)
- UniverseManagerConfig validation
- StrategyConfig with/without universe_filter
- SystemConfig with/without universe_manager
- YAML↔Pydantic field name match test for UniverseManagerConfig

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (1 × 1) | 1 |
| Pre-flight context reads (2: config.py, base_strategy.py) | 2 |
| New tests (8 × 0.5) | 4 |
| **TOTAL** | **7 (Low)** |

---

## Session 2b: ORB Family Filter Declarations

**Objective:** Add `universe_filter` YAML sections to ORB Breakout and ORB Scalp strategy configs.

**Creates:** —
**Modifies:** `config/strategies/orb_breakout.yaml`, `config/strategies/orb_scalp.yaml`
**Integrates:** Session 2a (uses UniverseFilterConfig)

**Scope:**
- Read each strategy's `.py` code to extract implicit filter assumptions (price ranges, volume thresholds, etc.)
- Add `universe_filter:` block to each YAML with appropriate values
- ORB family shared characteristics: higher volume requirements, momentum-stock price ranges
- Verify configs load and validate via Pydantic

**Tests:** ~6
- Config loading test for each strategy (2)
- Filter values match extracted implicit logic (2)
- YAML↔Pydantic field name match test per strategy (2)

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (2 × 1) | 2 |
| Pre-flight context reads (3: config.py, orb_breakout.yaml, orb_base.py) | 3 |
| New tests (6 × 0.5) | 3 |
| **TOTAL** | **8 (Low)** |

---

## Session 2c: VWAP + Afternoon Momentum Filter Declarations

**Objective:** Add `universe_filter` YAML sections to VWAP Reclaim and Afternoon Momentum strategy configs.

**Creates:** —
**Modifies:** `config/strategies/vwap_reclaim.yaml`, `config/strategies/afternoon_momentum.yaml`
**Integrates:** Session 2a (uses UniverseFilterConfig)

**Scope:**
- Read each strategy's `.py` code to extract implicit filter assumptions
- Add `universe_filter:` block to each YAML
- VWAP Reclaim: mean-reversion characteristics (possibly different market cap/volume profile)
- Afternoon Momentum: consolidation breakout characteristics (higher volume, specific price range)
- Verify configs load and validate via Pydantic

**Tests:** ~6
- Config loading test for each strategy (2)
- Filter values match extracted implicit logic (2)
- YAML↔Pydantic field name match test per strategy (2)

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (2 × 1) | 2 |
| Pre-flight context reads (3: config.py, vwap_reclaim.yaml, vwap_reclaim.py) | 3 |
| New tests (6 × 0.5) | 3 |
| **TOTAL** | **8 (Low)** |

---

## Session 3a: Routing Table Construction

**Objective:** Add routing table to Universe Manager — maps symbols to qualifying strategies.

**Creates:** —
**Modifies:** `argus/data/universe_manager.py`
**Integrates:** Sessions 1b + 2a/2b/2c (combines viable universe with strategy filter configs)

**Scope:**
- `build_routing_table(strategies: dict[str, StrategyConfig])` method: iterates viable symbols × strategy filters, builds `dict[str, set[str]]` (symbol → strategy_ids)
- `route_candle(symbol: str) -> set[str]`: O(1) dict lookup returning qualifying strategy IDs
- `get_strategy_universe_size(strategy_id: str) -> int`: count of symbols matching a strategy's filter
- Filter matching logic: check each UniverseFilterConfig field against SymbolReferenceData. None = pass.
- Sector matching: if `sectors` non-empty, symbol must be in list; if `exclude_sectors` non-empty, symbol must NOT be in list

**Tests:** ~8
- Routing correctness (symbol matches one strategy, multiple strategies, no strategies)
- Sector include/exclude logic
- None-field passthrough
- Empty universe
- Strategy with no filter (matches all viable symbols)

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (1 × 1) | 1 |
| Pre-flight context reads (2: universe_manager.py, config.py) | 2 |
| New tests (8 × 0.5) | 4 |
| **TOTAL** | **7 (Low)** |

---

## Session 3b: Databento Fast-Path + Event Integration

**Objective:** Add fast-path symbol discard to DatabentoDataService and wire Universe Manager into the event pipeline.

**Creates:** —
**Modifies:** `argus/data/databento_data_service.py`, `argus/core/events.py` (optional: UniverseUpdateEvent)
**Integrates:** Session 3a routing into event pipeline

**Scope:**
- DatabentoDataService: add `_viable_symbols: set[str] | None` field. When set, discard candle/tick events for symbols not in the set BEFORE IndicatorEngine processing. When None (Universe Manager disabled), process all symbols as today.
- `set_viable_universe(symbols: set[str])` method on DatabentoDataService
- Ensure IndicatorEngine only instantiated for viable symbols (saves memory)
- Optional: `UniverseUpdateEvent` on Event Bus when viable universe is refreshed (for logging/UI)
- Verify existing event flow unchanged when viable_symbols is None

**Tests:** ~8
- Fast-path discard (candle for non-viable symbol → not processed)
- Pass-through (candle for viable symbol → processed normally)
- None mode (no viable set → all symbols processed, backward compat)
- IndicatorEngine only created for viable symbols
- Event counts (verify no events lost for viable symbols)

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (2 × 1) | 2 |
| Pre-flight context reads (4: databento_data_service.py, universe_manager.py, events.py, event_bus.py) | 4 |
| New tests (8 × 0.5) | 4 |
| Complex integration wiring (3+: databento + universe_manager + event_bus + indicator_engine) | 3 |
| **TOTAL** | **13 (Medium)** |

---

## Session 4a: Universe Manager System Config

**Objective:** Wire UniverseManagerConfig into SystemConfig and add the YAML section.

**Creates:** —
**Modifies:** `argus/core/config.py` (add UniverseManagerConfig to SystemConfig/ArgusConfig), `config/system.yaml`
**Integrates:** N/A (config wiring used by Session 4b)

**Scope:**
- Add `universe_manager: UniverseManagerConfig` field to `SystemConfig` with `default_factory`
- Add `universe_manager:` section to `config/system.yaml` with defaults (enabled: false)
- Ensure `load_system_config()` handles missing section gracefully (defaults apply)
- YAML↔Pydantic field name verification test

**Tests:** ~6
- SystemConfig loads with universe_manager section
- SystemConfig loads without universe_manager section (defaults)
- Field name match test (YAML keys vs Pydantic model_fields)
- Invalid values rejected

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (2 × 1) | 2 |
| Pre-flight context reads (2: config.py, system.yaml) | 2 |
| New tests (6 × 0.5) | 3 |
| **TOTAL** | **7 (Low)** |

---

## Session 4b: Main.py Startup Wiring

**Objective:** Wire Universe Manager into the startup sequence, replacing the scanner→set_watchlist flow when enabled.

**Creates:** —
**Modifies:** `argus/main.py`
**Integrates:** All prior sessions into startup flow

**Scope:**
- When `universe_manager.enabled: true`:
  1. After scanner.scan() (Phase 7 in current startup), create UniverseManager
  2. Call `universe_manager.build_viable_universe()` (FMP reference data fetch)
  3. Build routing table from strategy configs
  4. Call `data_service.set_viable_universe(viable_symbols)`
  5. Start data_service with ALL_SYMBOLS mode
  6. Wire candle routing: on CandleEvent, consult routing table to determine which strategies receive the event
  7. Store universe_manager reference in AppState for API access
- When `universe_manager.enabled: false`:
  - Existing flow unchanged: scanner.scan() → set_watchlist() → data_service.start(symbols)
- Replay/backtest mode: always uses old flow regardless of config
- Update `_on_candle_for_strategies` to use routing table when UM enabled

**Tests:** ~8
- Startup with UM enabled (mock FMP, verify routing active)
- Startup with UM disabled (verify old flow)
- Startup with UM enabled but FMP fails (verify graceful degradation to scanner symbols)
- Candle routing: strategy receives candle only for matching symbols
- Backward compat: simulated broker mode uses old path

| Factor | Points |
|--------|--------|
| New files created (0) | 0 |
| Files modified (1 × 1) | 1 |
| Pre-flight context reads (4: main.py, universe_manager.py, databento_data_service.py, config.py) | 4 |
| New tests (8 × 0.5) | 4 |
| Complex integration wiring (3+: universe_manager + databento + strategies + event routing) | 3 |
| **TOTAL** | **12 (Medium)** |

---

## Session 5a: Backend API Endpoints for Universe Data

**Objective:** Expose universe status and symbol data via REST API.

**Creates:** `argus/api/routes/universe.py`
**Modifies:** `argus/api/dependencies.py` (expose universe_manager in AppState)
**Integrates:** Universe Manager into API layer

**Scope:**
- `GET /api/v1/universe/status`: returns JSON with total_symbols, viable_count, per_strategy_counts (dict[strategy_id, int]), last_refresh_timestamp, reference_data_age_minutes
- `GET /api/v1/universe/symbols?page=1&per_page=50&strategy_id=...`: paginated symbol list with reference data fields (symbol, sector, market_cap, float_shares, matching_strategies)
- Register routes in app
- When Universe Manager not enabled, endpoints return appropriate response (e.g., `{"enabled": false}`)
- JWT auth (existing middleware)

**Tests:** ~6
- Status endpoint (UM enabled, UM disabled)
- Symbols endpoint (pagination, strategy_id filter)
- Auth required

| Factor | Points |
|--------|--------|
| New files created (1 × 2) | 2 |
| Files modified (1 × 1) | 1 |
| Pre-flight context reads (2: routes/ pattern, dependencies.py) | 2 |
| New tests (6 × 0.5) | 3 |
| **TOTAL** | **8 (Low)** |

---

## Session 5b: Frontend — Dashboard Universe Panel

**Objective:** Add universe monitoring stats to the Dashboard page.

**Creates:** New React component(s) for universe display
**Modifies:** Dashboard page (integrate universe panel)
**Integrates:** Session 5a API endpoints

**Scope:**
- `UniverseStatusCard` component: shows total universe size, viable count, per-strategy match counts, reference data freshness
- Uses TanStack Query to fetch from `/api/v1/universe/status`
- Displays "Universe Manager not enabled" state when disabled
- Integrates with existing Dashboard layout (follows design patterns from Sprint 21d)
- Responsive — works on desktop and mobile (PWA)
- Follows existing styling: Tailwind CSS v4, Framer Motion for transitions

**Visual Review Items:**
1. Universe panel renders correctly on Dashboard (correct position, no overlap)
2. Per-strategy counts display clearly with strategy names
3. Disabled state ("Universe Manager not enabled") renders cleanly
4. Mobile responsive layout preserved

**Tests:** ~8 Vitest
- Component renders with mock data
- Loading state
- Error state
- Disabled state
- Per-strategy count display

| Factor | Points |
|--------|--------|
| New files created (1 × 2) | 2 |
| Files modified (2 × 1) | 2 |
| Pre-flight context reads (3: Dashboard components, API hooks pattern, existing cards) | 3 |
| New tests (8 × 0.5) | 4 |
| **TOTAL** | **11 (Medium)** |

---

## Session 5f: Visual Review Fixes (contingency, 0.5 session)

**Scope:** Fix any visual issues found during Session 5b review. Budget: 0.5 session. Unused if no issues found.

---

## Summary

| Session | Scope | Creates | Modifies | Integrates | Score | Risk |
|---------|-------|---------|----------|------------|-------|------|
| 1a | FMP Reference Data Client | fmp_reference.py | — | N/A | 13 | Medium |
| 1b | Universe Manager Core | universe_manager.py | — | 1a | 11 | Medium |
| 2a | Universe Filter Config Model | — | config.py | N/A | 7 | Low |
| 2b | ORB Family Filter Declarations | — | 2 strategy YAMLs | 2a | 8 | Low |
| 2c | VWAP+Afternoon Filter Declarations | — | 2 strategy YAMLs | 2a | 8 | Low |
| 3a | Routing Table Construction | — | universe_manager.py | 1b+2a/b/c | 7 | Low |
| 3b | Databento Fast-Path + Events | — | databento_ds.py, events.py | 3a | 13 | Medium |
| 4a | Universe Manager System Config | — | config.py, system.yaml | N/A | 7 | Low |
| 4b | Main.py Startup Wiring | — | main.py | All prior | 12 | Medium |
| 5a | Backend API Endpoints | universe.py | dependencies.py | UM→API | 8 | Low |
| 5b | Frontend Dashboard Panel | UI components | Dashboard page | 5a | 11 | Medium |
| 5f | Visual Review Fixes | — | UI components | 5b | — | contingency |

**Total sessions:** 11 + 0.5 contingency
**Estimated tests:** ~80 pytest + ~16 Vitest = ~96 total
**No session exceeds 13 (Medium threshold).**

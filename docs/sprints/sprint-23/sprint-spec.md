# Sprint 23: Universe Manager

## Goal
Replace the static pre-market watchlist (15 symbols from FMP Scanner) with a Universe Manager that monitors the broad US equity universe via Databento ALL_SYMBOLS, caches FMP reference data (sector, market cap, float) for viable symbols, and routes candle events to strategies based on declarative `universe_filter` YAML configs. This is the infrastructure foundation for full-universe strategy-specific monitoring (DEC-263).

## Scope

### Deliverables

1. **FMP Reference Data Client** (`argus/data/fmp_reference.py`): Batch Company Profile + Share Float fetcher using FMP Starter plan. Daily cache with configurable TTL. Graceful degradation when FMP unavailable.

2. **Universe Manager** (`argus/data/universe_manager.py`): Core class that orchestrates pre-market reference data fetch, builds the viable universe (system-level filters: not OTC, meets price/volume thresholds), constructs a routing table mapping symbols to qualifying strategies, and provides a `route_candle()` method for event dispatch.

3. **Universe Filter Config Schema**: `UniverseFilterConfig` Pydantic model (min/max price, min market cap, min float, min avg volume, sector include/exclude lists). `UniverseManagerConfig` Pydantic model (system-level filters, cache TTL, FMP batch size). Both integrated into existing config hierarchy.

4. **Strategy Filter Declarations**: All 4 active strategies (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum) gain explicit `universe_filter` YAML sections declaring their symbol requirements.

5. **Routing Table + Event Integration**: Pre-computed `symbol → set[strategy_id]` routing table. Fast-path discard in DatabentoDataService for symbols outside the viable universe. Candle routing via Universe Manager.

6. **Main.py Startup Integration**: Universe Manager replaces the scanner→set_watchlist→data_service.start flow when enabled. Config-gated (`universe_manager.enabled`). Backward compatible — replay/backtest modes use old path.

7. **Databento ALL_SYMBOLS Activation**: DatabentoDataService configured for ALL_SYMBOLS subscription. IndicatorEngine cold-starts on all viable symbols (no batch warm-up).

8. **API Endpoints**: `GET /api/v1/universe/status` (universe size, viable count, strategy filter counts). `GET /api/v1/universe/symbols` (paginated symbol list with reference data).

9. **Dashboard Universe Panel**: New UI panel showing universe monitoring stats — total symbols, viable count, per-strategy filter match counts, reference data freshness. Augments existing watchlist display.

### Acceptance Criteria

1. **FMP Reference Data Client:**
   - Batch fetches Company Profile for 4,000+ symbols in <2 minutes using comma-separated batch endpoint
   - Fetches Share Float data for viable symbols
   - Caches results with configurable TTL (default 24h)
   - Degrades to price-only filtering when FMP unavailable (logs warning, continues)
   - All FMP calls use existing FMP_API_KEY environment variable

2. **Universe Manager:**
   - Constructs viable universe from FMP reference data + system-level filters
   - System-level filters: exclude OTC, price range, minimum average volume (all configurable)
   - Routing table correctly maps each viable symbol to the set of strategies whose filters it matches
   - `route_candle(symbol)` returns the correct strategy set in O(1) via dict lookup
   - When `universe_manager.enabled: false`, system behaves identically to pre-Sprint-23

3. **Config Schema:**
   - `UniverseFilterConfig` validates all fields with appropriate types and constraints
   - `UniverseManagerConfig` validates all fields
   - YAML keys match Pydantic field names exactly (no silently ignored keys)
   - `None` values in strategy filters mean "no constraint" (inherit system defaults or accept all)

4. **Strategy Filter Declarations:**
   - Each of the 4 strategy YAML files has a `universe_filter:` section
   - Filter values are extracted from implicit logic currently in strategy code (price checks, volume checks)
   - Config loads and validates without errors

5. **Routing + Event Integration:**
   - Databento ALL_SYMBOLS subscription connects and receives data
   - Fast-path discard drops candles for non-viable symbols before IndicatorEngine processing
   - IndicatorEngine cold-starts for all viable symbols (no warm-up, converges within ~50 bars)
   - No candle events are lost for symbols in the viable universe

6. **Main.py Integration:**
   - Startup sequence: FMP reference fetch → viable universe → routing table → Databento ALL_SYMBOLS start → strategy activation
   - When `universe_manager.enabled: false`, startup uses existing scanner→set_watchlist flow unchanged
   - Replay and backtest modes are unaffected regardless of config setting

7. **API Endpoints:**
   - `/api/v1/universe/status` returns universe size, viable count, per-strategy match counts, last refresh timestamp
   - `/api/v1/universe/symbols` returns paginated symbol list with sector, market cap, float, and matching strategies

8. **Dashboard Universe Panel:**
   - Shows total universe size, viable count, per-strategy match counts
   - Shows reference data freshness (time since last FMP fetch)
   - Visually integrates with existing Dashboard layout without breaking other panels

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| FMP reference data fetch (4,000 symbols) | < 2 minutes | Timed in pre-market routine |
| Candle routing lookup | < 10μs per call | Profiled via cProfile on route_candle() |
| Fast-path discard overhead | < 1μs per non-viable symbol | Profiled on DatabentoDataService handler |
| Total per-candle processing overhead (Universe Manager) | < 50μs | End-to-end timing on candle handler |
| Memory overhead (4,000 IndicatorEngine instances) | < 50MB above baseline | Process memory comparison |
| Startup time increase (Universe Manager path vs old path) | < 3 minutes | Timed startup sequence |

### Config Changes

System-level (`config/system.yaml` → `UniverseManagerConfig`):

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| universe_manager.enabled | UniverseManagerConfig | enabled | false |
| universe_manager.min_price | UniverseManagerConfig | min_price | 5.0 |
| universe_manager.max_price | UniverseManagerConfig | max_price | 10000.0 |
| universe_manager.min_avg_volume | UniverseManagerConfig | min_avg_volume | 100000 |
| universe_manager.exclude_otc | UniverseManagerConfig | exclude_otc | true |
| universe_manager.reference_cache_ttl_hours | UniverseManagerConfig | reference_cache_ttl_hours | 24 |
| universe_manager.fmp_batch_size | UniverseManagerConfig | fmp_batch_size | 50 |

Strategy-level (`config/strategies/*.yaml` → `UniverseFilterConfig`):

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| universe_filter.min_price | UniverseFilterConfig | min_price | None |
| universe_filter.max_price | UniverseFilterConfig | max_price | None |
| universe_filter.min_market_cap | UniverseFilterConfig | min_market_cap | None |
| universe_filter.max_market_cap | UniverseFilterConfig | max_market_cap | None |
| universe_filter.min_float | UniverseFilterConfig | min_float | None |
| universe_filter.min_avg_volume | UniverseFilterConfig | min_avg_volume | None |
| universe_filter.sectors | UniverseFilterConfig | sectors | [] |
| universe_filter.exclude_sectors | UniverseFilterConfig | exclude_sectors | [] |

## Dependencies
- Sprint 22 complete (AI layer must not regress)
- FMP API key in environment (`FMP_API_KEY`, existing from Sprint 21.7)
- Databento API key in environment (`DATABENTO_API_KEY`, existing from Sprint 12)
- No new external dependencies or FMP plan upgrades required

## Relevant Decisions
- DEC-263: Full-universe strategy-specific monitoring architecture — primary driver of this sprint
- DEC-092: IndicatorEngine extraction — the shared engine that runs on all universe symbols
- DEC-248: EQUS.MINI consolidated feed — the Databento dataset for ALL_SYMBOLS
- DEC-258: FMP Starter for scanning — existing FMP integration we build on
- DEC-257: Hybrid Databento+FMP architecture — FMP for reference data, Databento for streaming
- DEC-082: Databento as primary data source — single session with Event Bus fan-out
- DEC-088: Databento threading model — reader thread → call_soon_threadsafe → asyncio
- DEC-261: ORB same-symbol mutual exclusion — must still work with broad universe

## Relevant Risks
- RSK-046: Broad-universe processing throughput at ensemble scale — mitigated by DEC-263 CPU analysis (2–4% utilization). Sprint 23 validates this empirically.

## Session Count Estimate
11 sessions estimated + 0.5 contingency = 11.5 sessions. Driven by compaction risk scoring: original 5-session plan scored 14–19 per session, requiring splits. Each session now scores ≤13. Frontend Session 5b has 0.5-session visual-review fix budget.

# Sprint 27.6: Adversarial Review Input Package

This document contains all context needed for the adversarial review. The reviewer should receive:
1. Sprint Spec (`sprint-spec.md`)
2. Specification by Contradiction (`spec-by-contradiction.md`)
3. This document

---

## Architecture Context

### Existing Regime Classification (core/regime.py — 327 lines)

The current system uses a single-dimension `RegimeClassifier`:
- **Inputs:** SPY daily bars (SMA-20, SMA-50, 5-day ROC, 20-day realized vol)
- **Output:** `MarketRegime` enum (5 values: BULLISH_TRENDING, BEARISH_TRENDING, RANGE_BOUND, HIGH_VOLATILITY, CRISIS)
- **Consumers:** Orchestrator (strategy activation via `allowed_regimes`), BacktestEngine (historical regime tagging), PerformanceThrottler (via Orchestrator state)
- **Refresh cadence:** 300s asyncio task in main.py (DEC-346), plus Orchestrator's own poll loop

The classifier computes a `RegimeIndicators` intermediate (SPY-specific) then applies a scoring system:
1. Trend score (-2 to +2) from SPY vs SMA-20/50
2. Volatility bucket from 20-day realized vol
3. Momentum confirmation from 5-day ROC
4. Decision matrix: crisis overrides → high vol + strong trend → trend-based → range-bound

### Orchestrator Regime Usage (core/orchestrator.py)

```python
# reclassify_regime() — called every 300s during market hours
indicators = self._regime_classifier.compute_indicators(spy_bars)
new_regime = self._regime_classifier.classify(indicators)

# Strategy activation — uses MarketRegime string
for sid, strategy in self._strategies.items():
    mcf = strategy.get_market_conditions_filter()
    if new_regime.value not in mcf.allowed_regimes:
        strategy.is_active = False
```

Key: strategies define `allowed_regimes` as `list[str]` of MarketRegime values. This must remain unchanged.

### BacktestEngine Regime Tagging (backtest/engine.py)

```python
# _compute_regime_tags() — historical, returns dict[date, str]
config = OrchestratorConfig()  # Uses default thresholds
classifier = RegimeClassifier(config)
for i, d in enumerate(dates):
    history = daily_bars.iloc[:i+1]
    indicators = classifier.compute_indicators(history)
    regime = classifier.classify(indicators)
    regime_tags[d] = regime.value
```

Returns MarketRegime.value strings. Used by `to_multi_objective_result()` to bucket trades into regime groups for `RegimeMetrics`.

### MultiObjectiveResult Regime Contract (analytics/evaluation.py)

```python
regime_results: dict[str, RegimeMetrics]  # String-keyed, not MarketRegime-keyed
```

Sprint 27.5 deliberately used string keys (not `MarketRegime` enum keys) for forward-compatibility with RegimeVector dimensions. This sprint must NOT change these keys.

### Existing CorrelationTracker (core/correlation.py) — NAMING COLLISION

**CRITICAL:** `argus/core/correlation.py` already exists. It contains a STRATEGY-LEVEL `CorrelationTracker` that tracks daily P&L per strategy for allocation correlation limits (DEC-116, referenced in Orchestrator config `correlation_enabled: true`).

Sprint 27.6's MARKET-LEVEL stock correlation tracker must use a different name and file:
- Class: `MarketCorrelationTracker`
- File: `argus/core/market_correlation.py`

### Event Bus Architecture (core/event_bus.py)

FIFO per subscriber, monotonic sequence numbers, no priority queues. In-process asyncio only (DEC-025). Subscribers receive events via async generator pattern. BreadthCalculator will subscribe to CandleEvent — it must not block or slow the candle processing path.

### Data Service Candle Flow (data/databento_data_service.py)

Databento reader thread → `_on_ohlcv()` → fast-path discard (non-viable symbols) → build CandleEvent → `call_soon_threadsafe()` → Event Bus publish.

BreadthCalculator subscribes to CandleEvents via Event Bus, NOT by modifying DatabentoDataService. It's a passive consumer.

### FMP Endpoints in Use

| Endpoint | Status on Starter | Used By |
|----------|-------------------|---------|
| `/stable/profile` | ✅ Works | Universe Manager |
| `/stable/shares-float` | ✅ Works | Universe Manager |
| `/stable/stock-list` | ✅ Works | Universe Manager |
| `/stable/historical-price-full` | ✅ Works | DatabentoDataService.fetch_daily_bars() |
| `/stable/stock_news` | ❌ 403 on Starter | FMPNewsSource (disabled) |
| `/stable/press_releases` | ❌ 403 on Starter | FMPNewsSource (disabled) |
| `/stable/sector-performance` | ❓ Unknown | SectorRotationAnalyzer (new, Sprint 27.6) |

The sector-performance endpoint's availability on Starter is unconfirmed. Circuit breaker pattern (DEC-323) handles 403 gracefully.

### Config-Gating Pattern (established)

```yaml
# Example: catalyst pipeline (Sprint 23.5)
catalyst:
  enabled: true

# Example: quality engine (Sprint 24)
quality_engine:
  enabled: true

# This sprint:
regime_intelligence:
  enabled: true
```

All feature gates follow `enabled: true` default, config-driven disable. When disabled, the feature's components are not instantiated and no code paths execute.

### Pre-Market Startup Sequence (main.py)

Current startup order (relevant phases):
1. Phase 1–5: Config, DB, logging
2. Phase 6: Data service
3. Phase 7: Strategies, risk manager
4. Phase 8: Orchestrator
5. Phase 9: API server
6. Phase 9.5: Universe Manager build routing table
7. Phase 10: Databento connection
8. Phase 11: Pre-market routine (regime classification, allocations)
9. Phase 12: Market hours monitoring

Sprint 27.6 needs to insert:
- After Phase 8: Create calculator instances (BreadthCalculator, MarketCorrelationTracker, SectorRotationAnalyzer, IntradayCharacterDetector), pass to RegimeClassifierV2
- After Phase 10 (Databento connected): Subscribe BreadthCalculator and IntradayCharacterDetector to Event Bus CandleEvents
- During Phase 11 (pre-market): Run MarketCorrelationTracker overnight compute + SectorRotationAnalyzer fetch

---

## Relevant DEC Entries

- **DEC-346:** Periodic regime reclassification — 300s interval, market hours only, `reclassify_regime()` public method
- **DEC-347:** FMP daily bars for regime classification — `fetch_daily_bars()` via FMP stable API
- **DEC-323:** FMP circuit breaker on 401/403 — prevents request spam on blocked endpoints
- **DEC-300:** Config-gated features — established `enabled: true` default pattern
- **DEC-277:** Fail-closed on missing reference data — missing data blocks signals, never silently passes
- **DEC-360:** All 7 strategies allow `bearish_trending` — only `crisis` universal block
- **DEC-358 §3:** Intelligence Architecture amendment — specifies RegimeVector, 6 dimensions, data sources, file structure
- **DEC-025:** Event Bus FIFO per subscriber, monotonic sequence numbers, no priority queues
- **DEC-088:** Databento threading — reader thread bridged via `call_soon_threadsafe()`

---

## Key Questions for Adversarial Review

1. **RegimeVector as frozen dataclass vs Pydantic model:** Is frozen dataclass the right choice? It's a runtime value object, not a config type. But Pydantic would give us automatic serialization and validation. Trade-off: dataclass is simpler and faster, Pydantic adds validation overhead on every construction (which happens every 300s — not critical, but unnecessary).

2. **BreadthCalculator Event Bus subscription pattern:** BreadthCalculator subscribes to ALL CandleEvents across ~4,000 symbols. Each candle triggers a dict lookup + deque append + counter update. Is there a risk of Event Bus backpressure? The Event Bus uses async generators — if BreadthCalculator's handler is slow, does it slow other subscribers?

3. **MarketCorrelationTracker compute timing:** Computing during pre-market using FMP daily bars for 50 symbols. This adds ~50 API calls × ~200ms each = ~10 seconds. Is this acceptable in the pre-market window? Should it be parallelized with asyncio.gather?

4. **IntradayCharacterDetector — SPY only vs broader analysis:** The amendment specifies SPY candles only for intraday character. Is SPY representative enough? For example, a tech-heavy session might have very different intraday character than SPY suggests. Is this a concern, or is it acceptable for V2?

5. **Config-gate granularity:** We have top-level `regime_intelligence.enabled` plus per-dimension `breadth.enabled`, `correlation.enabled`, etc. Is this the right granularity? Should there be a simpler "all or nothing" gate?

6. **BacktestEngine historical regime tagging — V2 parity:** V2 uses the same trend + vol logic as V1 for historical tagging. Should we explicitly test that V2 produces IDENTICAL tags for a known dataset (bit-for-bit comparison), or is behavioral equivalence (same regime for same conditions) sufficient?

7. **Operating conditions matching — eager inclusion or premature?** The matching logic has no consumer until Sprint 34+. Is it worth implementing now, or is there a risk of building to a spec that changes when micro-strategies are actually designed?

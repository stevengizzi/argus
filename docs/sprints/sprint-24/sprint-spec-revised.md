# Sprint 24: Setup Quality Engine + Dynamic Position Sizer

> **Post-adversarial-review revision.** See `revision-rationale.md` for all changes.

## Goal

Build the SetupQualityEngine (5-dimension 0–100 composite scoring) and DynamicPositionSizer (quality grade → risk tier → share count) that transform ARGUS from binary pass/fail signal filtering to intelligence-driven trade grading and sizing. Includes DEC-327 firehose pipeline refactoring, quality history recording infrastructure for Sprint 28's Learning Loop, and quality visibility across all 5 Command Center pages.

## Scope

### Deliverables

1. **SignalEvent enrichment** — Add `pattern_strength: float = 50.0`, `signal_context: dict`, `quality_score: float = 0.0`, `quality_grade: str = ""` fields to SignalEvent. Add `QualitySignalEvent` to events.py (informational event for UI consumers — does not participate in execution pipeline).

2. **Pattern strength scoring (4 strategies)** — All 4 active strategies produce meaningful 0–100 `pattern_strength` scores based on internal signal conditions already computed in `on_candle()`. Strategies set `share_count=0` (Dynamic Sizer calculates from scratch).
   - ORB Breakout/Scalp: volume ratio, ATR ratio, chase distance, VWAP position
   - VWAP Reclaim: state machine path quality, pullback depth, reclaim volume, distance-to-VWAP
   - Afternoon Momentum: entry condition margin depth, consolidation tightness, volume surge, time-in-window

3. **DEC-327 firehose source refactoring** — Finnhub: `GET /news?category=general` replaces per-symbol `/company-news` loop; symbol association via `related` field. SEC EDGAR: EFTS full-text search replaces per-CIK filing fetch; CIK→ticker reverse map. Per-symbol methods retained (existing code). `fetch_catalysts()` gains `firehose: bool` parameter. FMP news stays disabled (Starter plan, DEC-323).

4. **SetupQualityEngine** — 5-dimension 0–100 composite scorer with defined scoring rubrics (see Dimension Scoring Rubrics below). YAML-configurable weights and thresholds. Grade mapping: A+ (90–100) through C/C- (0–29). Risk tier assignment per grade (flat midpoint within grade).

5. **DynamicPositionSizer** — Quality grade → risk tier → share count. Calculates from scratch: `risk_pct = midpoint(grade_range)`, `risk_dollars = allocated_capital × risk_pct`, `shares = int(risk_dollars / risk_per_share)`. Buying power check. Returns 0 if position too small.

6. **Config models + YAML** — `QualityEngineConfig` (with `enabled` field), `QualityWeightsConfig`, `QualityThresholdsConfig`, `QualityRiskTiersConfig` Pydantic models. `quality_engine` section in SystemConfig. `config/quality_engine.yaml` with all weights, thresholds, risk tiers, min_grade_to_trade.

7. **quality_history DB table** — New table in `argus.db` recording full component breakdown per scored signal: symbol, strategy_id, timestamp, all 5 dimension scores, composite score, grade, risk tier, calculated shares, entry/stop prices, signal_context JSON, and outcome columns (NULL until trade closes). Sprint 28's Learning Loop consumes this directly.

8. **Signal flow wiring** — Quality Engine + Sizer inserted into `_on_candle_for_strategies()` between signal generation and Risk Manager evaluation. Includes **backtest bypass**: when `broker_source == BrokerSource.SIMULATED` or `quality_engine.enabled == false`, falls through to legacy strategy-calculated sizing. Includes **share_count=0 defensive guard** in Risk Manager (check 0).

9. **Server initialization** — Quality Engine and Sizer initialized in server.py lifespan. Firehose mode wired into CatalystPipeline.run() and polling loop. Quality engine startup factory in startup.py.

10. **API endpoints** — `GET /api/v1/quality/{symbol}` (current score + components), `GET /api/v1/quality/history` (filterable history), `GET /api/v1/quality/distribution` (today's grade distribution).

11. **Frontend: Trades page** — Quality grade column with QualityBadge component (reusable, grade-colored). Component breakdown visible per trade row.

12. **Frontend: Orchestrator page** — Live quality scores for recent/active signals.

13. **Frontend: Dashboard** — Quality distribution mini-card + Signal Quality Distribution panel + filtered signals counter ("Signals today: N passed / M filtered").

14. **Frontend: Performance page** — "By quality grade" chart showing performance breakdown per grade.

15. **Frontend: The Debrief** — Quality vs. outcome scatter plot.

### Dimension Scoring Rubrics

Each dimension scorer maps raw inputs to a 0–100 score:

**Pattern Strength (30%):** Direct passthrough from `signal.pattern_strength`. Strategy produces 0–100 during `on_candle()`.

**Catalyst Quality (25%):** Max `quality_score` from catalysts published in the last 24 hours for the symbol (queried from `catalyst.db` via `CatalystStorage.get_catalysts_by_symbol()`). One strong catalyst is sufficient — averaging would dilute. Empty list → 50 (neutral: absence of catalyst data is neutral, not bearish).

**Volume Profile (20%):** RVOL breakpoint mapping with linear interpolation between breakpoints:
| RVOL | Score |
|------|-------|
| ≤ 0.5 | 10 |
| 1.0 | 40 |
| 2.0 | 70 |
| ≥ 3.0 | 95 |
| None/unavailable | 50 |

**Historical Match (15%):** Constant 50 (V1 stub). Sprint 28 Learning Loop replaces with real data.

**Regime Alignment (10%):**
| Condition | Score |
|-----------|-------|
| Current regime in strategy's `allowed_regimes` | 80 |
| Current regime NOT in `allowed_regimes` | 20 |
| `allowed_regimes` empty (strategy accepts all) | 70 |

### Risk Tier Interpolation

Risk percentage is the **midpoint** of the grade's range, flat within the grade. A score of 80 and a score of 89 both map to grade A, which uses `(1.5% + 2.0%) / 2 = 1.75%` risk. Grade boundaries provide 8 levels of differentiation; intra-grade interpolation is deferred.

### Score Range Note

With Historical Match stubbed at 50 and weighted 15%, every score receives a constant +7.5 offset. Effective score range is ~7.5 to ~92.5. A+ (90+) requires near-perfect scores on all four live dimensions and will be rare during V1 paper trading. This is acceptable — the system operates conservatively in the B-/B/B+/A- range (0.25–1.5% risk) during initial validation. **Grade thresholds are PROVISIONAL** and should be recalibrated after Sprint 28 Learning Loop activation expands the effective range.

### Backtest Compatibility

When `broker_source == BrokerSource.SIMULATED` (Replay Harness, backtest mode), the quality pipeline is bypassed entirely. Signal flow falls through to a **legacy sizing path** that computes shares using the strategy's original formula: `allocated_capital × max_loss_per_trade_pct / risk_per_share`. Pattern strength is still calculated (it's on the signal) but quality scoring, dynamic sizing, quality history recording, and grade filtering are all skipped. This preserves existing backtest behavior identically. No `backtest/*` files are modified.

The same bypass activates when `quality_engine.enabled == false`.

### QualitySignalEvent Semantics

`QualitySignalEvent` is a **separate informational event** published to the Event Bus for UI consumers (Dashboard quality panels, Orchestrator live scores). It does NOT participate in the execution pipeline. The Risk Manager receives the standard enriched `SignalEvent` (same type, quality fields populated via `dataclasses.replace()`). No downstream execution components need to handle `QualitySignalEvent`.

### Acceptance Criteria

1. **SignalEvent enrichment:**
   - SignalEvent has `pattern_strength`, `signal_context`, `quality_score`, `quality_grade` fields with correct defaults
   - QualitySignalEvent defined as separate event type with score, grade, risk_tier, components, rationale
   - All existing tests pass without modification (frozen dataclass defaults preserve backward compatibility)

2. **Pattern strength scoring:**
   - All 4 strategies produce `pattern_strength` between 0–100 that varies across signal conditions (unit tests with varied inputs produce at least 3 distinct score buckets per strategy)
   - All 4 strategies set `share_count=0` in SignalEvent
   - `signal_context` dict populated with strategy-specific factor values
   - Pattern strength calculation has no side effects on signal generation logic

3. **Firehose sources:**
   - Finnhub `fetch_catalysts(symbols=[], firehose=True)` makes exactly 1 HTTP call to `/news?category=general`
   - SEC EDGAR `fetch_catalysts(symbols=[], firehose=True)` makes exactly 1 HTTP call to EFTS search
   - Both return `list[CatalystRawItem]` with correct symbol associations
   - Per-symbol mode (`firehose=False`) still works unchanged
   - Items without symbol association stored with empty symbol

4. **Quality Engine:**
   - `score_setup()` returns `SetupQuality` with score in [0, 100], valid grade, valid risk tier, components dict with all 5 dimensions, rationale string
   - Dimension scoring follows rubrics exactly (CQ = max 24h catalyst score or 50, VP = RVOL breakpoint mapping, RA = binary regime check)
   - Varied inputs produce scores across the full grade spectrum in unit tests
   - Weight sum validated at startup (Pydantic model_validator, tolerance ±0.001, startup fails on violation)

5. **Dynamic Sizer:**
   - Returns different share counts for different quality grades given identical entry/stop/capital
   - Risk percentage is midpoint of grade's range, flat within grade
   - A+ grade produces larger position than B grade
   - Returns 0 if calculated shares < 1 or if shares × entry_price > buying_power

6. **Signal flow:**
   - C/C- signals logged but never reach Risk Manager
   - Enriched signals reaching Risk Manager always have `share_count > 0`
   - Risk Manager rejects signals with `share_count <= 0` (defensive guard, check 0)
   - Risk Manager's existing gates still apply downstream
   - quality_history row created for every scored signal (passed and filtered)
   - QualitySignalEvent published for every scored signal
   - **Backtest bypass:** when `BrokerSource.SIMULATED`, legacy sizing used, quality pipeline skipped entirely
   - **Config bypass:** when `quality_engine.enabled == false`, same legacy path
   - Canary test: Replay Harness with BrokerSource.SIMULATED produces identical signal count and sizes to pre-sprint

7. **Config:**
   - `quality_engine` section loads correctly from both `system.yaml` and `system_live.yaml`
   - `quality_engine.enabled: true` present in both config files
   - All YAML keys recognized by Pydantic models (no silently ignored fields)
   - Weight sum validator rejects configs where weights don't sum to 1.0
   - Missing `quality_engine` section uses valid defaults (enabled=true)

8. **API:**
   - All 3 endpoints return correct JSON responses with JWT auth
   - `/quality/{symbol}` returns 404 for symbols with no quality history
   - `/quality/distribution` returns zero counts for grades with no data

9. **Frontend:**
   - QualityBadge renders on Trades, Orchestrator, Dashboard with grade-colored styling
   - Quality distribution chart shows real data from API
   - Filtered signals counter shows passed/filtered counts
   - All components handle empty/loading/error states gracefully

10. **Tests:**
    - All existing 2,532 pytest + 446 Vitest pass (zero regressions)
    - ~160–185 new tests added

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Quality scoring latency | < 10ms (including catalyst DB query) | Unit test with timer |
| Catalyst DB query | < 100ms | aiosqlite query timing |
| Firehose poll cycle | ≤ 3 API calls per source | Count in unit tests |
| API endpoint response | < 100ms p95 | Manual verification during paper trading |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `quality_engine` | `QualityEngineConfig` | (root) | — |
| `quality_engine.enabled` | `QualityEngineConfig` | `enabled` | `True` |
| `quality_engine.weights.pattern_strength` | `QualityWeightsConfig` | `pattern_strength` | `0.30` |
| `quality_engine.weights.catalyst_quality` | `QualityWeightsConfig` | `catalyst_quality` | `0.25` |
| `quality_engine.weights.volume_profile` | `QualityWeightsConfig` | `volume_profile` | `0.20` |
| `quality_engine.weights.historical_match` | `QualityWeightsConfig` | `historical_match` | `0.15` |
| `quality_engine.weights.regime_alignment` | `QualityWeightsConfig` | `regime_alignment` | `0.10` |
| `quality_engine.thresholds.a_plus` | `QualityThresholdsConfig` | `a_plus` | `90` |
| `quality_engine.thresholds.a` | `QualityThresholdsConfig` | `a` | `80` |
| `quality_engine.thresholds.a_minus` | `QualityThresholdsConfig` | `a_minus` | `70` |
| `quality_engine.thresholds.b_plus` | `QualityThresholdsConfig` | `b_plus` | `60` |
| `quality_engine.thresholds.b` | `QualityThresholdsConfig` | `b` | `50` |
| `quality_engine.thresholds.b_minus` | `QualityThresholdsConfig` | `b_minus` | `40` |
| `quality_engine.thresholds.c_plus` | `QualityThresholdsConfig` | `c_plus` | `30` |
| `quality_engine.risk_tiers.a_plus` | `QualityRiskTiersConfig` | `a_plus` | `[0.02, 0.03]` |
| `quality_engine.risk_tiers.a` | `QualityRiskTiersConfig` | `a` | `[0.015, 0.02]` |
| `quality_engine.risk_tiers.a_minus` | `QualityRiskTiersConfig` | `a_minus` | `[0.01, 0.015]` |
| `quality_engine.risk_tiers.b_plus` | `QualityRiskTiersConfig` | `b_plus` | `[0.0075, 0.01]` |
| `quality_engine.risk_tiers.b` | `QualityRiskTiersConfig` | `b` | `[0.005, 0.0075]` |
| `quality_engine.risk_tiers.b_minus` | `QualityRiskTiersConfig` | `b_minus` | `[0.0025, 0.005]` |
| `quality_engine.risk_tiers.c_plus` | `QualityRiskTiersConfig` | `c_plus` | `[0.0025, 0.0025]` |
| `quality_engine.min_grade_to_trade` | `QualityEngineConfig` | `min_grade_to_trade` | `"C+"` |

Regression item: "New quality_engine config fields verified against Pydantic model (no silently ignored keys)."

## Dependencies

- Sprint 23.9 complete (clean baseline: 2,532 pytest + 446 Vitest)
- CatalystStorage operational with `get_catalysts_by_symbol()` (Sprint 23.5+23.6+23.8)
- Universe Manager operational with viable universe (Sprint 23)
- RegimeClassifier accessible via `orchestrator.current_regime` (Sprint 17)
- IndicatorEngine providing RVOL via `data_service.get_indicator(symbol, "rvol")` (Sprint 12.5)
- Event Bus operational for QualitySignalEvent publishing (Sprint 1)
- ArgusDB manager with schema initialization (Sprint 1)

## Relevant Decisions

- DEC-239: Setup Quality Engine — 5 dimensions in V1, Order Flow added post-revenue. Weights: PS 30%, CQ 25%, VP 20%, HM 15%, RA 10%.
- DEC-027: Risk Manager modifications — approve-with-modification; never modify stops or entry. Still applies downstream.
- DEC-251: Absolute risk floor ($100). Risk Manager still enforces on sizer-calculated shares.
- DEC-249: Concentration approve-with-modification with 0.25R floor. Still applies.
- DEC-277: Fail-closed on missing reference data. Quality Engine follows same principle.
- DEC-327: Intelligence pipeline firehose architecture deferred to Sprint 24. Now in scope.
- DEC-300: Config-gated catalyst pipeline. Quality engine also config-gated (enabled: true default).
- DEC-303: Daily cost ceiling ($5/day). Firehose calls count against this.
- DEC-276: ET timestamps for intelligence layer. Quality history uses same convention.
- DEC-275: Compaction risk scoring. Applied to all sessions.
- DEC-328: Test suite tiering. Applied to session pre-flights and reviews.

## Relevant Risks

- RSK-044: Quality scoring produces meaningful differentiation — mitigated by varied unit test inputs and Gate 3 paper trading validation.
- RSK-045: Dynamic sizing amplifies losses when quality model misidentifies grade — mitigated by Risk Manager downstream gates, min risk floor, and conservative initial risk tiers.
- RSK-046: Free news sources miss catalysts — mitigated by neutral fallback (50) when data unavailable.
- RSK-056: External API concentration risk — mitigated by firehose reducing call volume.

## Session Count Estimate

13 sessions estimated (12 numbered + 0.5 contingency). Rationale: 8 backend sessions cover SignalEvent changes (1–2), firehose refactoring (3), quality engine core (4), sizer + config (5a–5b), pipeline wiring (6a), integration tests (6b), server init (7), and API routes (8). 3 frontend sessions cover components + trades (9), orchestrator + dashboard (10), and performance + debrief (11). Visual-review contingency (11f) at 0.5 session.

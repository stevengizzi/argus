# Sprint 27.6: Session Breakdown

## Dependency Chain

```
S1 → S2 → {S3, S4, S5} (parallel) → S6 → S7 → S8 → S9 → S10 [→ S10f contingency]
```

S1 establishes RegimeVector + V2 shell + config (foundation for everything).
S2 builds BreadthCalculator, establishing the Event Bus subscription pattern.
S3/S4/S5 build standalone calculators in parallel (no file overlaps).
S6 wires all calculators into V2 + Orchestrator + main.py startup.
S7 extends BacktestEngine.
S8 runs end-to-end integration tests.
S9 adds operating conditions matching (depends on S1 only, placed here for logical flow).
S10 extends Observatory frontend (depends on S6 for API data).
S10f is a contingency slot for visual-review fixes from S10.

---

## Session 1: RegimeVector + RegimeClassifierV2 Shell + Config

**Objective:** Establish the RegimeVector dataclass, a minimal RegimeClassifierV2 shell that produces it using only trend + vol (same as V1), and the full config infrastructure.

**Creates:**
- `config/regime.yaml`

**Modifies:**
- `argus/core/regime.py` — add `RegimeVector` frozen dataclass, `RegimeClassifierV2` class (shell: computes trend + vol dimensions, other dimensions use defaults, produces `primary_regime` identical to V1)
- `argus/core/config.py` — add `BreadthConfig`, `CorrelationConfig`, `SectorRotationConfig`, `IntradayConfig`, `RegimeIntelligenceConfig` Pydantic models; wire `RegimeIntelligenceConfig` into `SystemConfig`

**Integrates:** N/A (foundation)

**Parallelizable:** false (foundation session — everything depends on this)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (regime.yaml) | 2 |
| Files modified | 2 (regime.py, config.py) | 2 |
| Context reads | 3 (regime.py, config.py, orchestrator.yaml) | 3 |
| New tests | ~12 | 6 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 (RegimeVector ~80 lines, V2 shell ~60 lines — both in existing file) | 0 |
| **Total** | | **13** |

**Tests (~12):**
- RegimeVector construction with all fields
- RegimeVector frozen immutability
- RegimeVector to_dict / from_dict serialization (including None intraday fields)
- V2 backward compatibility: classify() returns same MarketRegime as V1 for 5 regime types
- V2 with default dimensions: produces valid RegimeVector
- RegimeIntelligenceConfig default loading
- Config validation (invalid thresholds rejected)
- Config file loading from regime.yaml
- SystemConfig with regime_intelligence field
- Config silently-ignored-key detection test

---

## Session 2: BreadthCalculator

**Objective:** Build BreadthCalculator as a standalone module that subscribes to CandleEvents via Event Bus and tracks intraday market breadth.

**Creates:**
- `argus/core/breadth.py`

**Modifies:** None

**Integrates:** N/A (standalone, wired in S6)

**Parallelizable:** false (establishes Event Bus subscription pattern for S5)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (breadth.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 3 (events.py for CandleEvent, regime.py for types, config.py for BreadthConfig) | 3 |
| New tests | ~14 | 7 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 1 (breadth.py ~150 lines) | 2 |
| **Total** | | **12** | | (medium — safe to proceed) |

**Tests (~14):**
- BreadthCalculator construction with config
- on_candle updates rolling MA per symbol
- breadth_score computation: all above MA → +1.0, all below → -1.0, mixed → between
- breadth_thrust: True when >80% above MA, False otherwise
- Configurable thrust_threshold
- Ramp-up period: < 20 bars → computed from available
- Pre-market (no candles) → score 0.0, thrust False
- Memory bounded: deque maxlen enforced
- Single symbol edge case
- Empty universe → score 0.0
- get_breadth_snapshot() returns current state
- Symbol removal / universe change
- Performance: O(1) per candle update assertion
- Reset for new trading day

---

## Session 3: MarketCorrelationTracker

**Objective:** Build MarketCorrelationTracker as a standalone module that computes rolling 20-day pairwise correlation for top N symbols during pre-market.

**Creates:**
- `argus/core/market_correlation.py`

**Modifies:** None

**Integrates:** N/A (standalone, wired in S6)

**Parallelizable:** true — no file overlap with S4 or S5. Creates a single new file, no modifications to shared files. Justification: S3 creates `market_correlation.py`, S4 creates `sector_rotation.py`, S5 creates `intraday_character.py` — all independent.

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (market_correlation.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 1 (config.py for CorrelationConfig) | 1 |
| New tests | ~10 | 5 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 1 (market_correlation.py ~150 lines) | 2 |
| **Total** | | **8** | | (low) |

**Tests (~10):**
- MarketCorrelationTracker construction with config
- compute_from_daily_bars with known correlation data → correct average
- correlation_regime classification: dispersed, normal, concentrated
- Edge case: single symbol → neutral defaults
- Edge case: all identical returns → correlation 1.0
- Edge case: insufficient history (< 20 days) → neutral defaults
- File cache write and read
- File cache same-day hit (no recomputation)
- File cache stale (next day → recompute)
- get_correlation_snapshot() returns current state

---

## Session 4: SectorRotationAnalyzer

**Objective:** Build SectorRotationAnalyzer as a standalone module that fetches FMP sector performance and classifies rotation phase.

**Creates:**
- `argus/core/sector_rotation.py`

**Modifies:** None

**Integrates:** N/A (standalone, wired in S6)

**Parallelizable:** true — same justification as S3. No file overlap.

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (sector_rotation.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 2 (config.py for SectorRotationConfig, fmp_reference.py for FMP client pattern) | 2 |
| New tests | ~10 | 5 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 1 (sector_rotation.py ~120 lines) | 2 |
| **Total** | | **9** | | (medium-low) |

**Tests (~10):**
- SectorRotationAnalyzer construction with config
- classify risk_on (tech + consumer discretionary leading)
- classify risk_off (utilities + healthcare leading)
- classify mixed (no clear pattern)
- classify transitioning (rotation from risk_on to risk_off)
- Leading/lagging sector identification (top 3 / bottom 3)
- FMP 403 graceful degradation → mixed, empty lists
- FMP timeout → mixed, empty lists
- Partial sector data (< 5 sectors) → mixed
- get_sector_snapshot() returns current state

---

## Session 5: IntradayCharacterDetector

**Objective:** Build IntradayCharacterDetector as a standalone module that classifies intraday market character from SPY candle data.

**Creates:**
- `argus/core/intraday_character.py`

**Modifies:** None

**Integrates:** N/A (standalone, wired in S6)

**Parallelizable:** true — same justification as S3/S4. No file overlap.

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (intraday_character.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 2 (config.py for IntradayConfig, regime.py for RegimeVector types) | 2 |
| New tests | ~12 | 6 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 1 (intraday_character.py ~150 lines) | 2 |
| **Total** | | **10** | | (medium-low) |

**Tests (~12):**
- IntradayCharacterDetector construction with config
- Classify trending: strong first bar + sustained VWAP slope
- Classify choppy: narrow first bar + oscillating VWAP
- Classify reversal: strong first bar in one direction + reversal
- Classify breakout: narrow first 30 min + expansion
- Pre-market (before 9:35) → all None
- Classification at 9:35 (only first bar data)
- Classification at 10:00 (first bar + early bars)
- Classification at 10:30 (first 30 min complete)
- opening_drive_strength computation (first bar range / ATR proxy)
- first_30min_range_ratio computation (30-min range / expected daily range)
- vwap_slope computation from candle data
- Reset for new trading day

---

## Session 6: Integration — Compose V2 + Orchestrator + main.py + RegimeHistoryStore

**Objective:** Wire all calculators into RegimeClassifierV2, integrate with Orchestrator's reclassify_regime(), set up startup initialization in main.py (including concurrent pre-market via asyncio.gather), and add RegimeHistoryStore SQLite persistence.

**Creates:**
- `argus/core/regime_history.py` (RegimeHistoryStore)

**Modifies:**
- `argus/core/regime.py` — V2 accepts calculator instances (all Optional), `compute_regime_vector()` composes all dimensions, `run_pre_market()` with `asyncio.gather()` for correlation + sector
- `argus/core/orchestrator.py` — uses V2 when config-enabled, enriched RegimeChangeEvent with `regime_vector_summary: Optional[dict]`, writes to RegimeHistoryStore
- `argus/main.py` — creates calculator instances at startup, passes to V2, Event Bus subscriptions for BreadthCalculator + IntradayCharacterDetector, RegimeHistoryStore init
- `argus/core/events.py` — add `regime_vector_summary: Optional[dict] = None` to `RegimeChangeEvent`

**Integrates:** S1 (RegimeVector + V2 shell), S2 (BreadthCalculator), S3 (MarketCorrelationTracker), S4 (SectorRotationAnalyzer), S5 (IntradayCharacterDetector)

**Parallelizable:** false (integration session — depends on all prior sessions)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (regime_history.py) | 2 |
| Files modified | 4 (regime.py, orchestrator.py, main.py, events.py) | 4 |
| Context reads | 5 (regime.py, orchestrator.py, main.py, events.py, config.py) | 5 |
| New tests | ~12 | 6 |
| Complex integration | 1 (wires 4+ components) | 3 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13** | | (medium — proceed with caution) |

**Tests (~12):**
- V2 compose: all calculators → full RegimeVector
- V2 compose: individual dimension disabled → that dimension defaults
- V2 compose: all calculators None (backtest mode) → only trend+vol populated
- V2 delegates to V1 for primary_regime (code inspection + test)
- V2 config-gate: enabled=false → V1 classify() only, no calculator invocation
- Orchestrator reclassify_regime with V2 → returns (old, new) tuple unchanged
- RegimeChangeEvent contains regime_vector_summary dict
- Startup init: calculators created and passed to V2
- BreadthCalculator + IntradayCharacterDetector Event Bus subscriptions verified
- Pre-market: run_pre_market() executes correlation + sector concurrently
- RegimeHistoryStore: write + query by trading_date + query by timestamp
- RegimeHistoryStore: fire-and-forget (write failure doesn't disrupt classification)
- RegimeHistoryStore: 7-day retention cleanup
- Config-gate bypass: zero new code paths when disabled

---

## Session 7: BacktestEngine Integration

**Objective:** Extend `_compute_regime_tags()` to use V2 for trend + vol dimensions. Verify identical results to V1.

**Creates:** None

**Modifies:**
- `argus/backtest/engine.py` — `_compute_regime_tags()` uses V2 when available

**Integrates:** S1 (RegimeVector), S6 (V2 composition)

**Parallelizable:** false (depends on S6)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (engine.py) | 1 |
| Context reads | 3 (engine.py, regime.py, evaluation.py) | 3 |
| New tests | ~8 | 4 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **8** | | (low) |

**Tests (~8):**
- _compute_regime_tags with V2: identical results to V1 for same SPY data
- Regime tags dict still has MarketRegime.value string values
- to_multi_objective_result produces valid regime_results with V2 tags
- V2 historical mode: only trend + vol dimensions populated
- Breadth/correlation/sector/intraday dimensions are defaults in historical mode
- BacktestEngine with regime_intelligence disabled: V1 behavior
- Existing backtest integration tests still pass (backward compat)
- RegimeVector from historical tagging has primary_regime matching V1

---

## Session 8: End-to-End Integration Tests + Cleanup

**Objective:** Comprehensive integration tests covering the full regime intelligence pipeline from startup through market hours. Clean up any rough edges.

**Creates:** None

**Modifies:** Test files only

**Integrates:** All prior sessions (end-to-end verification)

**Parallelizable:** false (depends on S7)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 0 (test files only, not counting toward score) | 0 |
| Context reads | 6 (regime.py, orchestrator.py, main.py, engine.py, breadth.py, config) | 6 |
| New tests | ~10 | 5 |
| Complex integration | 0 (testing only) | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **11** | | (medium) |

**Tests (~10):**
- E2E: pre-market startup → calculators initialized → RegimeVector produced
- E2E: market hours → candles flow → breadth updates → periodic reclassification → RegimeVector evolves
- E2E: config permutations (all enabled, all disabled, mixed)
- E2E: FMP unavailable → graceful degradation across all dimensions
- Golden-file parity: 100 trading days of SPY daily bars → V1 regime tags frozen as fixture → V2 produces bit-for-bit identical tags
- Stress test: BreadthCalculator with 5,000 symbols
- Config-gate complete isolation test (zero V2 imports when disabled)
- All new modules importable (no circular imports)
- RegimeVector JSON roundtrip (serialize → deserialize → equal)
- Multiple reclassification cycles (RegimeVector consistency)
- Cleanup: verify no TODO/FIXME/HACK left in new code

---

## Session 9: Operating Conditions Matching

**Objective:** Add `RegimeOperatingConditions` dataclass and `matches_conditions()` method to RegimeVector. Extend strategy YAML schema to accept `operating_conditions` section.

**Creates:** None

**Modifies:**
- `argus/core/regime.py` — add `RegimeOperatingConditions` dataclass, `RegimeVector.matches_conditions()` method
- `argus/models/strategy.py` — add `operating_conditions: RegimeOperatingConditions | None` to strategy model (or separate model)

**Integrates:** S1 (RegimeVector)

**Parallelizable:** false (sequential after S8 for logical flow)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 (regime.py, models/strategy.py) | 2 |
| Context reads | 2 (regime.py, models/strategy.py) | 2 |
| New tests | ~8 | 4 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **8** | | (low) |

**Tests (~8):**
- RegimeOperatingConditions construction with range constraints
- matches_conditions: all dimensions in range → True
- matches_conditions: one dimension out of range → False
- matches_conditions: None constraint (unconstrained dimension) → always matches
- matches_conditions: intraday_character string match
- matches_conditions: empty conditions → always matches (vacuously true)
- Strategy YAML with operating_conditions section parses correctly
- Strategy YAML without operating_conditions section → None (backward compat)

---

## Session 10: Observatory Regime Visualization

**Objective:** Extend Observatory session vitals bar to display RegimeVector dimensions. Show trend, vol, breadth, correlation, sector, intraday character as visual indicators.

**Creates:** None

**Modifies:**
- Observatory session vitals component (2–3 frontend files)

**Integrates:** S6 (V2 via API/WebSocket)

**Parallelizable:** false (frontend, after backend complete)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 3 (session vitals + regime display components) | 3 |
| Context reads | 3 (Observatory components, regime types, API hooks) | 3 |
| New tests | ~6 Vitest | 3 |
| Complex integration | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **8** | | (low) |

**Tests (~6 Vitest):**
- Regime vitals component renders with full RegimeVector data
- Handles None intraday fields (pre-market state)
- Handles missing/disabled dimensions
- Displays all 6 dimension indicators
- Updates on regime change
- No JS errors when RegimeVector unavailable

---

## Session 10f: Visual-Review Fixes (Contingency — 0.5 session)

**Objective:** Fix any visual issues discovered during S10 review. Only used if S10 review identifies frontend problems.

**Budget:** 0.5 session. If no issues found, slot unused.

---

## Summary Table

| Session | Scope | Creates | Modifies | Score | Parallel |
|---------|-------|---------|----------|-------|----------|
| S1 | RegimeVector + V2 shell + config | regime.yaml | regime.py, config.py | **13** | No |
| S2 | BreadthCalculator | breadth.py | — | **12** | No |
| S3 | MarketCorrelationTracker | market_correlation.py | — | **8** | Yes |
| S4 | SectorRotationAnalyzer | sector_rotation.py | — | **9** | Yes |
| S5 | IntradayCharacterDetector | intraday_character.py | — | **10** | Yes |
| S6 | V2 compose + Orchestrator + main.py + RegimeHistoryStore | regime_history.py | regime.py, orchestrator.py, main.py, events.py | **13** | No |
| S7 | BacktestEngine integration | — | engine.py | **8** | No |
| S8 | E2E integration tests + cleanup | — | test files | **11** | No |
| S9 | Operating conditions matching | — | regime.py, models/strategy.py | **8** | No |
| S10 | Observatory regime visualization | — | 2–3 frontend files | **8** | No |
| S10f | Visual-review fixes (contingency) | — | TBD | — | No |

**Estimated new tests:** ~94 pytest + ~6 Vitest = ~100 total
**All sessions ≤ 13.** No session requires splitting.

# Sprint 27.9: Session Breakdown

## Dependency Chain

```
S1 (VIXDataService) → S2 (Calculators + RegimeVector) → S3 (Pipeline Integration + REST) → S4 (Frontend)
                                                                                              → S4f (Visual fixes, contingency)
```

No parallelizable sessions — strict linear dependency.

---

## Session 1: VIX Data Service Foundation

**Objective:** Build the VIXDataService with SQLite persistence, yfinance integration, derived metric computation, staleness logic, and config model.

**Creates:**
- `argus/data/vix_data_service.py` (~200 lines)
- `argus/data/vix_config.py` (~80 lines — VixRegimeConfig, VolRegimeBoundaries, TermStructureBoundaries, VRPBoundaries Pydantic models)
- `config/vix_regime.yaml` (~50 lines)
- `tests/data/test_vix_data_service.py` (~12 tests)

**Modifies:**
- `argus/config/system_config.py` (add VixRegimeConfig import + field to SystemConfig)

**Integrates:** N/A (foundational)

**Parallelizable:** false (single deliverable chain)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 4 | 8 |
| Files modified | 1 | 1 |
| Pre-flight context reads | 3 (system_config.py, regime.py for pattern reference, existing data service for pattern) | 3 |
| New tests | 12 | 6 |
| Complex integration wiring | 0 | 0 |
| External API debugging (yfinance) | 1 | 3 |
| Large files (>150 lines) | 1 (vix_data_service.py) | 2 |
| **Total** | | **23** |

**⚠️ CRITICAL (23 points) — must split into 3 sub-sessions.**

### Session 1a: Config Model + VIXDataService Core

**Objective:** VixRegimeConfig Pydantic models, YAML config file, SystemConfig wiring, VIXDataService class skeleton with SQLite schema and persistence (no yfinance yet — test with synthetic data).

**Creates:**
- `argus/data/vix_config.py` (~80 lines)
- `config/vix_regime.yaml` (~50 lines)
- `argus/data/vix_data_service.py` (skeleton: __init__, SQLite schema, persist/load methods, `is_ready`, `is_stale`, `get_latest_daily()` — ~120 lines)
- `tests/data/test_vix_data_service.py` (6 tests: config validation, SQLite persist/load, staleness logic, get_latest_daily with synthetic data, weekend date logic)

**Modifies:**
- `argus/config/system_config.py`

| Factor | Count | Points |
|--------|-------|--------|
| New files | 4 | 8 |
| Modified files | 1 | 1 |
| Pre-flight reads | 2 | 2 |
| New tests | 6 | 3 |
| Large files | 0 | 0 |
| **Total** | | **14** |

**⚠️ HIGH (14) — borderline. Acceptable because 2 of the 4 "new files" are config (YAML + Pydantic model, low complexity).**

Actually, let me split further.

### Session 1a: Config Model + VIXDataService Skeleton (REVISED)

**Objective:** VixRegimeConfig Pydantic models + YAML config + SystemConfig wiring + VIXDataService skeleton with SQLite schema, persist/load, staleness, get_latest_daily. Tests with synthetic data only.

**Creates:**
- `argus/data/vix_config.py` (~80 lines)
- `config/vix_regime.yaml` (~50 lines)
- `argus/data/vix_data_service.py` (skeleton ~120 lines — no yfinance, no derived metrics yet)
- `tests/data/test_vix_data_service.py` (5 tests: config YAML→Pydantic validation, persist/load round-trip, staleness logic, get_latest_daily, weekend date)

**Modifies:**
- `argus/config/system_config.py`

| Factor | Count | Points |
|--------|-------|--------|
| New files | 4 | 8 |
| Modified files | 1 | 1 |
| Pre-flight reads | 2 (system_config.py, existing data service for pattern) | 2 |
| New tests | 5 | 2.5 |
| Large files | 0 | 0 |
| **Total** | | **13.5 → 13** |

**MEDIUM (13) — proceed with caution.** Config files are low-complexity, bringing effective risk down.

### Session 1b: yfinance Integration + Derived Metrics

**Objective:** Wire yfinance into VIXDataService (fetch_historical, fetch_incremental), implement all 5 derived metric computations, daily update asyncio task. Integration test with real yfinance call.

**Creates:**
- `tests/data/test_vix_derived_metrics.py` (7 tests: vol-of-vol ratio, percentile, term structure proxy, realized vol, VRP, edge cases for σ₆₀=0 and insufficient data, incremental update)

**Modifies:**
- `argus/data/vix_data_service.py` (add yfinance fetch methods + derived metric computation + daily task — ~80 additional lines)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Modified files | 1 | 1 |
| Pre-flight reads | 2 (vix_data_service.py, vix_config.py) | 2 |
| New tests | 7 | 3.5 |
| External API debugging (yfinance) | 1 | 3 |
| **Total** | | **11.5 → 12** |

**MEDIUM (12) — proceed with caution.** yfinance API debugging is the main risk.

---

### Session 2: Calculators + RegimeVector Expansion

**Objective:** Four calculator classes, RegimeVector 6→10+1 expansion, RegimeClassifierV2 wiring, RegimeHistoryStore migration, strategy YAML config updates.

**Creates:**
- `argus/core/vix_calculators.py` (~150 lines — 4 calculator classes)
- `tests/core/test_vix_calculators.py` (~14 tests: 4 calculators × ~3 tests + RegimeVector tests)

**Modifies:**
- `argus/core/regime.py` (RegimeVector dataclass + RegimeClassifierV2 wiring + RegimeOperatingConditions)
- `argus/core/regime_history.py` (vix_close column migration + recording)
- `config/regime.yaml` (new calculator config section)
- `config/strategies/orb_breakout.yaml`
- `config/strategies/orb_scalp.yaml`
- `config/strategies/vwap_reclaim.yaml`
- `config/strategies/afternoon_momentum.yaml`
- `config/strategies/red_to_green.yaml`
- `config/strategies/bull_flag.yaml`
- `config/strategies/flat_top_breakout.yaml`

| Factor | Count | Points |
|--------|-------|--------|
| New files | 2 | 4 |
| Modified files | 10 | 10 |
| Pre-flight reads | 4 (regime.py, regime_history.py, vix_data_service.py, existing calculator for pattern) | 4 |
| New tests | 14 | 7 |
| Complex integration wiring (calculators→RegimeClassifierV2→RegimeVector→RegimeHistory) | 1 | 3 |
| Large files (vix_calculators.py) | 1 | 2 |
| **Total** | | **30** |

**⚠️ CRITICAL (30) — must split into 3 sub-sessions.**

### Session 2a: RegimeVector Expansion + RegimeOperatingConditions

**Objective:** Extend RegimeVector frozen dataclass with 5 new Optional fields. Update `to_dict()`, `matches_conditions()`. Verify backward compatibility. Update RegimeHistoryStore with vix_close column migration.

**Creates:**
- `tests/core/test_regime_vector_expansion.py` (6 tests: construction with defaults, to_dict, matches_conditions match-any, backward compat, history store migration, old-row reading)

**Modifies:**
- `argus/core/regime.py` (RegimeVector + RegimeOperatingConditions)
- `argus/core/regime_history.py` (ALTER TABLE migration + vix_close recording)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Modified files | 2 | 2 |
| Pre-flight reads | 3 (regime.py, regime_history.py, events.py for RegimeVector usage) | 3 |
| New tests | 6 | 3 |
| **Total** | | **10** |

**MEDIUM (10) — proceed with caution.**

### Session 2b: Four Calculator Classes + RegimeClassifierV2 Wiring

**Objective:** Implement VolRegimePhaseCalculator, VolRegimeMomentumCalculator, TermStructureRegimeCalculator, VarianceRiskPremiumCalculator. Wire into RegimeClassifierV2. Tests for each calculator.

**Creates:**
- `argus/core/vix_calculators.py` (~150 lines)
- `tests/core/test_vix_calculators.py` (8 tests: 4 calculators × 2 — happy path + None-when-unavailable)

**Modifies:**
- `argus/core/regime.py` (RegimeClassifierV2 — wire 4 new calculators)
- `config/regime.yaml` (enable new calculators section)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 2 | 4 |
| Modified files | 2 | 2 |
| Pre-flight reads | 4 (regime.py, vix_data_service.py, vix_config.py, existing calculator for pattern) | 4 |
| New tests | 8 | 4 |
| Complex integration wiring (calculators→ClassifierV2→VIXDataService) | 1 | 3 |
| Large files (vix_calculators.py) | 1 | 2 |
| **Total** | | **19** |

**⚠️ CRITICAL (19).** The 4 calculators are structurally identical (same pattern), which makes this less risky than the score suggests. But to be safe, let me check: can I split calculators?

Actually — the 4 calculators are all in one file and follow the same pattern. The real complexity is the RegimeClassifierV2 wiring. Let me keep this as one session but note the structural repetition reduces effective risk.

**REVISED assessment: 19 points but 4 calculators are boilerplate-similar. Effective risk ~13.** Proceed with caution. If compaction hits, the fallback is: implement 2 calculators + wiring, defer 2 to a follow-up session.

### Session 2c: Strategy YAML Config Updates

**Objective:** Update all 7 strategy YAML configs with conservative defaults for new RegimeVector dimensions. Verify match-any semantics. Verify `primary_regime` unchanged.

**Creates:** None

**Modifies:**
- `config/strategies/orb_breakout.yaml`
- `config/strategies/orb_scalp.yaml`
- `config/strategies/vwap_reclaim.yaml`
- `config/strategies/afternoon_momentum.yaml`
- `config/strategies/red_to_green.yaml`
- `config/strategies/bull_flag.yaml`
- `config/strategies/flat_top_breakout.yaml`

| Factor | Count | Points |
|--------|-------|--------|
| New files | 0 | 0 |
| Modified files | 7 | 7 |
| Pre-flight reads | 3 (regime.py for conditions, one strategy yaml for pattern, regime.yaml) | 3 |
| New tests | 0 (regression verification via existing tests) | 0 |
| **Total** | | **10** |

**MEDIUM (10).** YAML-only changes, low risk.

---

### Session 3: Pipeline Integration + REST Endpoints

**Objective:** Wire VIXDataService into BriefingGenerator, Orchestrator, SetupQualityEngine (infrastructure only). Add REST endpoints. Server.py lifespan init. Integration tests.

**Creates:**
- `argus/api/routes/vix.py` (~60 lines)
- `tests/api/test_vix_routes.py` (4 tests: current endpoint, history endpoint, auth required, stale indicator)
- `tests/integration/test_vix_pipeline.py` (6 tests: briefing with VIX, briefing without VIX, orchestrator logging, quality engine unchanged, regime history with vix_close, end-to-end regime cycle)

**Modifies:**
- `argus/intelligence/briefing_generator.py` (add VIX section to brief context)
- `argus/core/orchestrator.py` (add pre-market VIX logging)
- `argus/analytics/setup_quality_engine.py` (infrastructure stub for regime_alignment phase-space awareness — no behavioral change)
- `argus/server.py` (lifespan: init VIXDataService, wire into RegimeClassifierV2)
- `argus/api/routes/__init__.py` (register vix router)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 3 | 6 |
| Modified files | 5 | 5 |
| Pre-flight reads | 5 (briefing_generator.py, orchestrator.py, setup_quality_engine.py, server.py, existing route for pattern) | 5 |
| New tests | 10 | 5 |
| Complex integration wiring (VIXDataService→5 consumers) | 1 | 3 |
| **Total** | | **24** |

**⚠️ CRITICAL (24) — must split.**

### Session 3a: Server Init + REST Endpoints

**Objective:** VIXDataService initialization in server.py lifespan, wire into RegimeClassifierV2's calculator registry, REST endpoints for VIX data.

**Creates:**
- `argus/api/routes/vix.py` (~60 lines)
- `tests/api/test_vix_routes.py` (4 tests)

**Modifies:**
- `argus/server.py` (lifespan init)
- `argus/api/routes/__init__.py` (router registration)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 2 | 4 |
| Modified files | 2 | 2 |
| Pre-flight reads | 3 (server.py, existing route for pattern, vix_data_service.py) | 3 |
| New tests | 4 | 2 |
| Complex integration wiring (VIXDataService→ClassifierV2→server) | 1 | 3 |
| **Total** | | **14** |

**HIGH (14) — borderline.** Server.py lifespan wiring is the main risk. Acceptable given the wiring follows established patterns (see intelligence startup).

**REVISED: Proceed.** The server.py init follows the intelligence startup factory pattern exactly.

### Session 3b: Pipeline Consumer Wiring + Integration Tests

**Objective:** Wire VIX data into BriefingGenerator, Orchestrator pre-market logging, SetupQualityEngine infrastructure stub. Integration tests for the full pipeline.

**Creates:**
- `tests/integration/test_vix_pipeline.py` (8 tests: briefing with/without VIX, orchestrator logging, quality engine unchanged, regime history with vix_close, staleness propagation, end-to-end)

**Modifies:**
- `argus/intelligence/briefing_generator.py`
- `argus/core/orchestrator.py`
- `argus/analytics/setup_quality_engine.py`

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Modified files | 3 | 3 |
| Pre-flight reads | 4 (briefing_generator.py, orchestrator.py, quality_engine.py, vix_data_service.py) | 4 |
| New tests | 8 | 4 |
| **Total** | | **13** |

**MEDIUM (13) — proceed with caution.**

---

### Session 4: Dashboard VIX Widget (Frontend)

**Objective:** VixRegimeCard component, useVixData hook, DashboardPage integration. Vitest.

**Creates:**
- `argus/ui/src/components/dashboard/VixRegimeCard.tsx` (~100 lines)
- `argus/ui/src/hooks/useVixData.ts` (~30 lines)
- `argus/ui/src/test/VixRegimeCard.test.tsx` (6 Vitest tests)

**Modifies:**
- `argus/ui/src/pages/DashboardPage.tsx`
- `argus/ui/src/api/endpoints.ts`

| Factor | Count | Points |
|--------|-------|--------|
| New files | 3 | 6 |
| Modified files | 2 | 2 |
| Pre-flight reads | 3 (DashboardPage.tsx, existing widget for pattern, endpoints.ts) | 3 |
| New tests | 6 | 3 |
| **Total** | | **14** |

**HIGH (14) — borderline.** Frontend sessions typically have lower compaction risk per point due to less context-heavy code. Proceed.

### Session 4f: Visual Review Fixes (Contingency, 0.5 session)

**Objective:** Fix any visual issues discovered during Session 4's visual review.

---

## Final Session Summary

| Session | Scope | Score | Status |
|---------|-------|-------|--------|
| 1a | Config model + VIXDataService skeleton + SQLite persistence | 13 | MEDIUM |
| 1b | yfinance integration + derived metrics + daily task | 12 | MEDIUM |
| 2a | RegimeVector expansion (6→11) + RegimeHistoryStore migration | 10 | MEDIUM |
| 2b | 4 calculator classes + RegimeClassifierV2 wiring | 19 (effective ~13) | MEDIUM-HIGH |
| 2c | Strategy YAML config updates + regression verification | 10 | MEDIUM |
| 3a | Server init + REST endpoints | 14 (pattern-following) | HIGH |
| 3b | Pipeline consumer wiring + integration tests | 13 | MEDIUM |
| 4 | Dashboard VIX widget + Vitest | 14 | HIGH |
| 4f | Visual review fixes (contingency) | — | CONTINGENCY |

**Total: 8 sub-sessions + 0.5 contingency = 8.5 sessions maximum.**

**Note on session 2b:** The 19-point score reflects 4 calculator classes + wiring. All 4 calculators follow an identical structural pattern (input from VIXDataService → threshold comparison → enum return). If compaction occurs, the fallback is to implement 2 calculators in 2b, defer 2 to a 2b-fix session. The reviewer should check all 4 are present.

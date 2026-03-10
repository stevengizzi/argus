# Sprint 23.6: Session Breakdown

## Dependency Chain

```
S1 ──┐
     ├──→ S2b ──→ S3a ──→ S3b ──→ S3c
S2a ─┘
S4a ──→ S4b (also depends on S3b for lifecycle context)
S5 (fully independent)
```

---

## Session 1: Storage Schema & Query Fixes (C2, S1, S2, M3)

**Objective:** Fix all CatalystStorage and intelligence API defects identified in Tier 3 review.

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/intelligence/storage.py`, `argus/api/routes/intelligence.py` |
| Integrates | N/A (standalone fixes) |
| Parallelizable | Yes (independent of S2a, S4a, S5) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Files in context loading | 3 (storage.py, routes/intelligence.py, models.py) | 3 |
| New tests | 12 | 6 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file (>150 lines) | No | 0 |
| **Total** | | **11 (Medium)** |

---

## Session 2a: Event & Source Fixes (C3, S6)

**Objective:** Fix CatalystEvent timezone defaults and add SEC EDGAR email validation.

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/core/events.py`, `argus/intelligence/sources/sec_edgar.py` |
| Integrates | N/A |
| Parallelizable | Yes (independent of S1) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Files in context loading | 3 (events.py, sec_edgar.py, config.py) | 3 |
| New tests | 5 | 2.5 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **7.5 (Low)** |

---

## Session 2b: Pipeline Batch Store + FMP Canary + Semantic Dedup + Publish Ordering

**Objective:** Integrate S1's batch store into pipeline, add FMP schema canary, implement semantic dedup (M1) and batch-then-publish ordering (M2).

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/intelligence/__init__.py`, `argus/data/fmp_reference.py`, `argus/intelligence/config.py` |
| Integrates | S1's `store_catalysts_batch()` into CatalystPipeline.run_poll() |
| Parallelizable | No (depends on S1) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 3 | 3 |
| Files in context loading | 4 (__init__.py, fmp_reference.py, config.py, storage.py) | 4 |
| New tests | 11 | 5.5 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **12.5 (Medium)** |

---

## Session 3a: Intelligence Startup Factory

**Objective:** Create standalone factory function that builds all intelligence pipeline components from config.

| Column | Value |
|--------|-------|
| Creates | `argus/intelligence/startup.py` |
| Modifies | — |
| Integrates | N/A (factory is standalone) |
| Parallelizable | No (depends on S1, S2a, S2b) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 0 | 0 |
| Files in context loading | 6 (intelligence/config.py, __init__.py, classifier.py, storage.py, briefing.py, sources/__init__.py) | 6 |
| New tests | 8 | 4 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **12 (Medium)** |

---

## Session 3b: App Lifecycle Wiring (Static)

**Objective:** Wire startup factory into FastAPI lifespan handler, populate AppState fields, handle shutdown cleanup. Add `catalyst: CatalystConfig` to `SystemConfig`.

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/api/server.py`, `argus/core/config.py` |
| Integrates | S3a's `create_intelligence_components()` into lifespan handler |
| Parallelizable | No (depends on S3a) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Files in context loading | 4 (server.py, config.py, dependencies.py, startup.py) | 4 |
| New tests | 8 | 4 |
| Complex integration wiring | Yes (connecting factory to lifespan, AppState, shutdown) | 3 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **13 (Medium)** |

---

## Session 3c: Polling Loop

**Objective:** Register scheduled asyncio task for pipeline polling with market-hours-aware interval switching.

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/intelligence/startup.py`, `argus/api/server.py` |
| Integrates | Pipeline's `run_poll()` into scheduled execution |
| Parallelizable | No (depends on S3b) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Files in context loading | 3 (startup.py, server.py, config.py) | 3 |
| New tests | 5 | 2.5 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **7.5 (Low)** |

---

## Session 4a: Reference Data Cache Layer

**Objective:** Add file-based caching to FMPReferenceClient for reference data persistence across restarts.

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/data/fmp_reference.py` |
| Integrates | N/A (cache is internal to FMPReferenceClient) |
| Parallelizable | Yes (independent of S1–S3c) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 | 1 |
| Files in context loading | 2 (fmp_reference.py, FMPReferenceConfig) | 2 |
| New tests | 10 | 5 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **8 (Low)** |

---

## Session 4b: Incremental Warm-Up Wiring

**Objective:** Wire cache layer into Universe Manager warm-up flow for incremental reference data fetching.

| Column | Value |
|--------|-------|
| Creates | — |
| Modifies | `argus/data/fmp_reference.py`, `argus/data/universe_manager.py` |
| Integrates | S4a's cache layer into the warm-up flow |
| Parallelizable | No (depends on S4a; benefits from S3b context but not strictly dependent) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Files in context loading | 3 (fmp_reference.py, universe_manager.py, config) | 3 |
| New tests | 8 | 4 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | No | 0 |
| **Total** | | **9 (Medium)** |

---

## Session 5: Runner Decomposition + Conformance Monitoring (S4, S5)

**Objective:** Extract CLI helpers from runner main.py into cli.py. Add conformance fallback counter.

| Column | Value |
|--------|-------|
| Creates | `scripts/sprint_runner/cli.py` |
| Modifies | `scripts/sprint_runner/main.py`, `scripts/sprint_runner/state.py`, `scripts/sprint_runner/conformance.py` |
| Integrates | N/A (runner is self-contained) |
| Parallelizable | Yes (fully independent of all other sessions) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 3 | 3 |
| Files in context loading | 3 (main.py, state.py, conformance.py) | 3 |
| New tests | 6 | 3 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large single file | 1 (main.py >150 lines) | 2 |
| **Total** | | **13 (Medium)** |

---

## Summary Table

| Session | Scope | Score | Risk | Depends On | Parallelizable |
|---------|-------|-------|------|------------|----------------|
| S1 | Storage fixes (C2, S1, S2, M3) | 11 | Medium | — | Yes |
| S2a | Event + source fixes (C3, S6) | 7.5 | Low | — | Yes |
| S2b | Pipeline + FMP + dedup + publish (M1, M2) | 12.5 | Medium | S1 | No |
| S3a | Intelligence startup factory | 12 | Medium | S1, S2a, S2b | No |
| S3b | App lifecycle wiring | 13 | Medium | S3a | No |
| S3c | Polling loop | 7.5 | Low | S3b | No |
| S4a | Reference data cache | 8 | Low | — | Yes |
| S4b | Incremental warm-up | 9 | Medium | S4a | No |
| S5 | Runner decomp + monitoring | 13 | Medium | — | Yes |

All sessions ≤ 13. No splits required.

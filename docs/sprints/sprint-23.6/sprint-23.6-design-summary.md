# Sprint 23.6 Design Summary

**Sprint Goal:** Comprehensively address all Tier 3 review findings from Sprints 23–23.5 before Sprint 24. Fix critical pipeline initialization gap (C1), storage/query defects (C2, S1, S2, M3), timezone trap (C3), source validation (S6, FMP canary), semantic dedup (M1), publish ordering (M2), warm-up optimization (S3/DEF-025), and runner maintenance (S4, S5).

**Execution Mode:** Human-in-the-loop

---

## Session Breakdown

- **Session 1:** Storage schema & query fixes (C2, S1, S2, M3)
  - Creates: —
  - Modifies: `argus/intelligence/storage.py`, `argus/api/routes/intelligence.py`
  - Integrates: N/A
  - Compaction: 0 + 2 + 3 + 6 = **11** (Medium)

- **Session 2a:** Event & source fixes (C3, S6)
  - Creates: —
  - Modifies: `argus/core/events.py`, `argus/intelligence/sources/sec_edgar.py`
  - Integrates: N/A
  - Compaction: 0 + 2 + 3 + 2.5 = **7.5** (Low)

- **Session 2b:** Pipeline batch store + FMP canary + semantic dedup + publish ordering (S2→pipeline, M1, M2, canary)
  - Creates: —
  - Modifies: `argus/intelligence/__init__.py`, `argus/data/fmp_reference.py`, `argus/intelligence/config.py`
  - Integrates: S1's `store_catalysts_batch()` into CatalystPipeline
  - Compaction: 0 + 3 + 4 + 5.5 = **12.5** (Medium)

- **Session 3a:** Intelligence startup factory
  - Creates: `argus/intelligence/startup.py`
  - Modifies: `argus/core/config.py` (add `catalyst: CatalystConfig` to `SystemConfig`)
  - Integrates: N/A (factory is standalone)
  - Compaction: 2 + 1 + 7 + 4 = **14** — wait, let me re-score...
  - Context reads: `intelligence/config.py`, `intelligence/__init__.py`, `intelligence/classifier.py`, `intelligence/storage.py`, `intelligence/briefing.py`, `intelligence/sources/__init__.py`, `core/config.py` = 7 files
  - Adjusted: 2(new file) + 1(modified) + 7(context) + 4(tests) = **14** ⚠️
  - **Must reduce scope.** Move the SystemConfig modification to S3b. Factory reads config as a parameter, doesn't need to be in SystemConfig yet.
  - Revised: 2(new file) + 0(modified) + 6(context, drop config.py) + 4(tests) = **12** (Medium) ✓

- **Session 3b:** App lifecycle wiring (static — no polling)
  - Creates: —
  - Modifies: `argus/api/server.py`, `argus/core/config.py` (add `catalyst: CatalystConfig` to `SystemConfig`)
  - Integrates: S3a's factory into lifespan handler (wires to storage, sources, classifier, pipeline, briefing generator, sets AppState)
  - Compaction: 0 + 2 + 4(server.py, config.py, dependencies.py, startup.py) + 3(tests) + 3(integration wiring) = **12** (Medium)

- **Session 3c:** Polling loop registration
  - Creates: —
  - Modifies: `argus/intelligence/startup.py` (add polling scheduler), `argus/api/server.py` (start/stop polling in lifespan)
  - Integrates: Pipeline's `run_poll()` into scheduled execution
  - Compaction: 0 + 2 + 3(startup.py, server.py, config.py) + 2.5(tests) = **7.5** (Low)

- **Session 4a:** Reference data cache layer
  - Creates: —
  - Modifies: `argus/data/fmp_reference.py`
  - Integrates: N/A (cache is internal to FMPReferenceClient)
  - Compaction: 0 + 1 + 2(fmp_reference.py, config) + 5(tests) = **8** (Low)

- **Session 4b:** Incremental warm-up wiring
  - Creates: —
  - Modifies: `argus/data/fmp_reference.py`, `argus/data/universe_manager.py`
  - Integrates: S4a's cache into warm-up flow
  - Compaction: 0 + 2 + 3(fmp_reference.py, universe_manager.py, config) + 4(tests) = **9** (Medium)

- **Session 5:** Runner decomposition + monitoring (S4, S5)
  - Creates: `scripts/sprint_runner/cli.py`
  - Modifies: `scripts/sprint_runner/main.py`, `scripts/sprint_runner/state.py`, `scripts/sprint_runner/conformance.py`
  - Integrates: N/A
  - Compaction: 2(new file) + 3(modified) + 3(context) + 3(tests) + 2(main.py is large file) = **13** (Medium)

**Session dependency chain:**
```
S1 ──┐
     ├──→ S2b ──→ S3a ──→ S3b ──→ S3c
S2a ─┘                  
S4a ──→ S4b (depends on S3b for app lifecycle, but S4a is independent)
S5 (fully independent)
```

**Parallelizable:** S5 (independent). S4a (independent of S1–S3c). S2a (independent of S1). S1 and S2a can run in parallel. In human-in-the-loop mode these are informational — run serially, but can skip ahead if a session has issues.

---

## Key Decisions

- **CatalystConfig added to SystemConfig** (S3b): Follows the pattern established by AIConfig and UniverseManagerConfig. Config loading from YAML happens automatically via Pydantic. New field: `catalyst: CatalystConfig = Field(default_factory=CatalystConfig)`.
- **Intelligence startup factory** (S3a): Standalone function `create_intelligence_components(config, event_bus, ai_client, usage_tracker, data_dir)` returns a dataclass of initialized components (or None if disabled). Follows the pattern of AI service initialization but extracted into a reusable function rather than inline in lifespan.
- **Polling loop** (S3c): `asyncio.create_task` with a while loop, sleeping per config interval. Market-hours check determines which interval. Task cancelled in lifespan shutdown. Symbols for polling come from Universe Manager's viable_symbols (if available) or cached watchlist.
- **Reference data cache** (S4a): JSON file at `data/reference_cache.json`. Dict of `{symbol: {data..., cached_at: ISO}}`. Atomic write (write to `.tmp`, rename). Loaded at FMPReferenceClient startup. Max age configurable (default 24h).
- **Incremental warm-up** (S4b): On startup: load cache → identify missing/stale symbols from stock list → fetch only the delta → merge with cache → save. Full fetch fallback if cache missing/corrupt.
- **Semantic dedup** (M1 in S2b): Post-classification pass. Key: `(symbol, category, 30-min window)`. Keep highest quality_score per key. Configurable window via `dedup_window_minutes`.
- **Publish ordering** (M2 in S2b): Batch store first (single transaction), then publish events in second loop with per-item error handling. Failed publish is logged but doesn't lose data.
- **Runner cli.py extraction** (S5): Move `Colors`, `print_header`, `print_progress`, `print_summary_table`, `print_error`, `print_warning`, `print_success`, argument parsing setup from `main.py` to `cli.py`. ~200 lines moved.

---

## Scope Boundaries

- **IN:** All Tier 3 review findings (C1, C2, C3, S1, S2, S3, S4, S5, S6, M1, M2, M3), FMP canary test, DEC logging, documentation updates
- **OUT:** New intelligence data sources, strategy code changes, Risk Manager/Orchestrator/execution modifications, intelligence router prefix change (DEF-036), UI/frontend changes, fuzzy dedup (embedding-based), new runner execution capabilities

---

## Regression Invariants

1. All 2,396 pytest + 435 Vitest tests pass
2. `catalyst.enabled: false` → zero intelligence initialization, endpoints return 503 (unchanged behavior)
3. `universe_manager.enabled: false` → Universe Manager unchanged
4. CatalystEvent schema unchanged (only default factories)
5. Runner execution behavior identical (S4 pure refactoring, S5 adds monitoring only)
6. No strategy, Risk Manager, Orchestrator, or execution behavior changes
7. FMP reference data fetch works with no cache file (first-run path)
8. All existing AI layer behavior unchanged

---

## File Scope

**Modify:**
- `argus/intelligence/storage.py` — S1: add fetched_at column, total count, batch store
- `argus/api/routes/intelligence.py` — C2: use count query; M3: push since to SQL
- `argus/core/events.py` — C3: CatalystEvent timezone defaults
- `argus/intelligence/sources/sec_edgar.py` — S6: email validation
- `argus/intelligence/__init__.py` — S2b/M1/M2: batch store, semantic dedup, publish ordering
- `argus/intelligence/config.py` — M1: add dedup_window_minutes
- `argus/data/fmp_reference.py` — canary, S4a/S4b: cache layer, incremental fetch
- `argus/core/config.py` — S3b: add catalyst field to SystemConfig
- `argus/api/server.py` — S3b/S3c: intelligence init in lifespan, polling start/stop
- `scripts/sprint_runner/main.py` — S4/S5: extract cli, refactor imports
- `scripts/sprint_runner/state.py` — S5: add conformance_fallback_count
- `scripts/sprint_runner/conformance.py` — S5: increment fallback counter

**Create:**
- `argus/intelligence/startup.py` — S3a: factory function
- `scripts/sprint_runner/cli.py` — S5: extracted CLI helpers

**Do not modify:**
- `argus/strategies/` — all strategy files
- `argus/core/orchestrator.py`
- `argus/core/risk_manager.py`
- `argus/execution/` — all execution files
- `argus/analytics/` — all analytics files
- `argus/backtest/` — all backtesting files
- `argus/ai/` — all AI layer files
- `argus/data/scanner.py`
- `argus/data/databento_data_service.py`
- `argus/ui/` — all frontend files

---

## Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `catalyst` (top-level) | `SystemConfig` | `catalyst` | `CatalystConfig()` |
| `catalyst.dedup_window_minutes` | `CatalystConfig` | `dedup_window_minutes` | `30` |

Note: `FMPReferenceConfig` is a dataclass (not in system.yaml). Cache fields added directly:
- `cache_file: str = "data/reference_cache.json"`
- `cache_max_age_hours: int = 24`

---

## Test Strategy

| Session | New Tests | Coverage |
|---------|-----------|----------|
| S1 | ~12 | total_count, fetched_at round-trip, batch_store, since-in-SQL |
| S2a | ~5 | CatalystEvent ET defaults, SEC email validation (empty, valid) |
| S2b | ~11 | FMP canary schema check, pipeline batch store, semantic dedup (same/different symbol, window edge), publish ordering (store-before-publish, publish failure recovery) |
| S3a | ~8 | Factory with enabled/disabled, source selection permutations, missing API key degradation, all-disabled returns None |
| S3b | ~8 | Lifespan with catalyst enabled, lifespan with disabled, AppState populated, shutdown cleanup |
| S3c | ~5 | Polling fires at interval, market-hours interval switch, polling graceful stop, polling with empty symbols |
| S4a | ~10 | Cache save/load round-trip, staleness detection, corrupt file fallback, first-run no-cache, atomic write, per-symbol cached_at |
| S4b | ~8 | Incremental fetch (cache hit + miss), full fallback on old cache, timing assertion, merge correctness |
| S5 | ~6 | cli module imports, existing runner tests pass unchanged, fallback counter increments, WARNING at threshold |

**Estimated total: ~73 new tests** (using guide: ~5/new file + ~3/modified file + ~2/endpoint, calibrated against actual test counts)

---

## Dependencies

- Sprint 23.5 merged to working branch
- All 2,396 pytest + 435 Vitest passing
- `ANTHROPIC_API_KEY` set (for AI client tests; pipeline tests can mock)
- `FMP_API_KEY` set (for canary test; can mock for unit tests)

---

## Escalation Criteria

1. Pipeline initialization (S3a/S3b) cannot find a clean way to wire into lifespan → ESCALATE (may need architectural guidance)
2. Cache layer (S4a) introduces test flakiness from filesystem operations → ESCALATE
3. Any session breaks >5 existing tests → ESCALATE
4. Runner refactoring (S5) changes any test outcome → ESCALATE (should be behavior-neutral)

---

## Doc Updates Needed

- `docs/project-knowledge.md` — Sprint 23.6 entry, updated active state
- `docs/decision-log.md` — DEC-308 through DEC-315+ (pipeline init, separate DB, semantic dedup, reference cache, SystemConfig catalyst field, etc.)
- `docs/dec-index.md` — new entries
- `docs/risk-register.md` — RSK-031 elevated, RSK-048 added
- `docs/sprint-history.md` — Sprint 23.6 entry
- `docs/architecture.md` — intelligence module initialization, polling loop, cache layer
- `CLAUDE.md` — deferred items updated

---

## Artifacts to Generate

1. ~~Design Summary~~ (this document)
2. Sprint Spec
3. Specification by Contradiction
4. Session Breakdown (with scoring tables)
5. Sprint-Level Escalation Criteria
6. Sprint-Level Regression Checklist
7. Doc Update Checklist
8. Review Context File
9. Implementation Prompts ×9 (S1, S2a, S2b, S3a, S3b, S3c, S4a, S4b, S5)
10. Tier 2 Review Prompts ×9
11. Work Journal Handoff Prompt

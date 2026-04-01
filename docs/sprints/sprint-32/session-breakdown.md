# Sprint 32: Session Breakdown

## Dependency Chain

```
S1 (Config Alignment) ──┐
                         ├──→ S3 (Runtime Wiring) ──┐
S2 (Factory+Fingerprint)─┤                          │
                         ├──→ S5 (Variant Spawner) ──┤
                         │                           ├──→ S8 (CLI+API+Server)
S4 (Data Model+Store) ──┼──→ S6 (Runner) ───────────┤
                         │                           │
                         └──→ S7 (Promotion) ────────┘
```

S1 and S2 have no dependencies and can run in parallel (zero file overlap).
S4 has no dependency on S1–S3 and can run after S2 (needs factory types).
S6 depends on S2 + S4 only.
S7 depends on S4 only (consumes store, comparison API is pre-existing).
S8 is the integration session — depends on S4+S5+S6+S7.

---

## Session 1: Pydantic Config Alignment

**Objective:** Add all missing detection parameter fields to the 6 incomplete PatternModule Pydantic config models so that every pattern constructor parameter has a corresponding, validated config field.

**Creates:** None

**Modifies:**
- `argus/core/config.py` — Add 28 fields across BullFlagConfig (3), FlatTopBreakoutConfig (2), HODBreakConfig (1), GapAndGoConfig (6), ABCDConfig (13), PreMarketHighBreakConfig (3)

**Integrates:** N/A

**Parallelizable:** Yes (zero file overlap with S2)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 | 1 |
| Context reads (config.py, 7 pattern .py files) | 8 | 8 |
| New tests (~8: one cross-validation per pattern + boundary tests) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13 (Medium)** |

**Tests:**
- `test_config_param_alignment.py`: For each of the 7 PatternModule patterns, instantiate the pattern class, call `get_default_params()`, verify every `PatternParam.name` exists as a field in the corresponding Pydantic config model
- Boundary tests: verify Pydantic rejects out-of-range values for new fields (e.g., `swing_lookback: -1`, `fib_b_min: 2.0`)
- Backward compatibility: verify all 7 existing YAML configs still load successfully with no changes

**Acceptance:** All 7 patterns' constructor parameters fully represented in Pydantic models. No silent drops possible for detection params.

---

## Session 2: Pattern Factory + Parameter Fingerprint

**Objective:** Create the generic pattern construction factory and parameter fingerprint utility. Both are pure functions with no side effects — highly testable in isolation.

**Creates:**
- `argus/strategies/patterns/factory.py` (~120 lines) — `build_pattern_from_config()`, `compute_parameter_fingerprint()`, `get_pattern_class()` registry, `extract_detection_params()` helper

**Modifies:** None

**Integrates:** N/A (standalone module, consumed by S3, S5, S6)

**Parallelizable:** Yes (zero file overlap with S1)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 0 | 0 |
| Context reads (base.py, config.py, bull_flag.py, abcd.py) | 4 | 4 |
| New tests (~10: factory per pattern, fingerprint determinism, edge cases) | 10 | 5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (factory.py ~120 lines — under threshold) | 0 | 0 |
| **Total** | | **11 (Medium)** |

**Tests:**
- Factory: construct each of 7 patterns from their default config, verify instance type and parameter values match
- Factory: construct with non-default params, verify values propagated
- Factory: unrecognized pattern class raises ValueError
- Fingerprint: identical configs → identical hash
- Fingerprint: different detection params → different hash
- Fingerprint: non-detection params (name, operating_window, etc.) don't affect hash
- Fingerprint: deterministic across calls (no randomness)
- `extract_detection_params()`: returns only fields matching PatternParam names

**Acceptance:** Factory constructs all 7 patterns. Fingerprint is deterministic, detection-param-only, and ≤16 hex chars.

---

## Session 3: Runtime Wiring

**Objective:** Replace hardcoded pattern constructors in `main.py` with factory calls, replace `_create_pattern_by_name()` in PatternBacktester with factory, wire fingerprint into trade records.

**Creates:** None

**Modifies:**
- `argus/main.py` — Replace 7× `SomePattern()` calls with `build_pattern_from_config()` calls (~7 surgical changes, each replacing 1 line)
- `argus/backtest/vectorbt_pattern.py` — Replace `_create_pattern_by_name()` body with factory call (~15 lines replaced with ~5)
- `argus/analytics/trade_logger.py` — Add `config_fingerprint TEXT` column to trades schema, populate from SignalEvent or strategy metadata

**Integrates:** S1 (config fields present in Pydantic models) + S2 (factory + fingerprint functions)

**Parallelizable:** No (depends on S1 + S2)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 3 | 3 |
| Context reads (main.py, vectorbt_pattern.py, trade_logger.py, factory.py) | 4 | 4 |
| New tests (~8: wiring integration, backtester all 7 patterns, fingerprint in DB) | 8 | 4 |
| Complex integration wiring (factory into 2 consumers + DB schema change) | 1 | 3 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **14 (High — borderline)** |

**Risk mitigation:** Each of the 3 file modifications is small and surgical. main.py changes are 7 one-line substitutions. vectorbt_pattern.py replaces a switch statement with a single function call. trade_logger.py adds one column and one field population. The "complex integration" score comes from touching 3 files, but each touch is minimal. Proceed with caution — if any single modification proves complex during implementation, halt and split.

**Tests:**
- Integration: start the system (or mock startup), verify all 7 patterns constructed with correct params
- PatternBacktester: call `_create_pattern_by_name()` (or replacement) for all 7 patterns including the 4 previously missing ones (dip_and_rip, hod_break, gap_and_go, premarket_high_break)
- Trade record: create a mock trade, verify `config_fingerprint` column populated
- Backward compat: existing YAML with no detection params → defaults used

**Acceptance:** All 7 patterns construct via factory. Backtester supports all 7. Every trade has a fingerprint. DEF-121 resolved.

---

## Session 4: Experiment Data Model + Registry Store

**Objective:** Create the experiment data model and SQLite-backed registry store. This is the persistence layer for the entire experiment pipeline.

**Creates:**
- `argus/intelligence/experiments/__init__.py` (~5 lines)
- `argus/intelligence/experiments/models.py` (~80 lines) — `ExperimentRecord`, `VariantDefinition`, `PromotionEvent`, `ExperimentStatus` enum
- `argus/intelligence/experiments/store.py` (~150 lines) — `ExperimentStore` (SQLite, WAL mode, fire-and-forget, retention, query API)

**Modifies:** None

**Integrates:** N/A (standalone, consumed by S5, S6, S7, S8)

**Parallelizable:** No strict dependency on S1/S2, but S2's fingerprint types are referenced in models. Run after S2.

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | 6 |
| Files modified | 0 | 0 |
| Context reads (learning_store.py pattern, evaluation.py, counterfactual_store.py) | 3 | 3 |
| New tests (~10: CRUD, retention, queries, edge cases) | 10 | 5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (store.py ~150 lines) | 0 | 0 |
| **Total** | | **14 (High — borderline)** |

**Risk mitigation:** This follows the exact DEC-345 pattern used 4+ times (learning_store, counterfactual_store, evaluation_store, regime_history). The SQLite boilerplate is well-established. models.py is small dataclasses. The risk is in the 3 new files, but they're independent and template-driven.

**Reduction option:** If compaction occurs, split models.py (create+test) from store.py (create+test). But this is likely unnecessary given the templated nature of the work.

**Tests:**
- Store: create experiment, retrieve by ID
- Store: query by pattern name, by fingerprint
- Store: update status (RUNNING → COMPLETED → PROMOTED)
- Store: retention enforcement (records older than 90 days purged)
- Store: WAL mode enabled
- Store: fire-and-forget writes don't raise
- Models: dataclass equality, serialization
- VariantDefinition: validation of required fields
- PromotionEvent: captures before/after state

**Acceptance:** Full CRUD on experiments.db. Query by pattern and fingerprint works. Follows DEC-345 pattern.

---

## Session 5: Variant Spawner + Startup Integration

**Objective:** Create the variant spawner that reads variant definitions from config, uses the factory to instantiate pattern variants, and registers them with the Orchestrator at startup.

**Creates:**
- `argus/intelligence/experiments/spawner.py` (~130 lines) — `VariantSpawner` class: parse variant config, deduplicate by fingerprint, instantiate via factory, register with Orchestrator
- `config/experiments.yaml` (~30 lines) — Default config with `enabled: false`, empty variants section, documented schema

**Modifies:**
- `argus/main.py` — Add spawner invocation after base strategy registration (~15 lines in startup sequence)

**Integrates:** S2 (factory for pattern construction) + S4 (registry for recording spawned variants)

**Parallelizable:** No (modifies main.py, depends on S2+S4)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 1 | 1 |
| Context reads (main.py, factory.py, store.py, orchestrator.py) | 4 | 4 |
| New tests (~8: spawner logic, startup integration, dedup, config parsing) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13 (Medium)** |

**Tests:**
- Spawner: given config with 2 bull_flag variants, creates 2 PatternBasedStrategy instances with correct params
- Spawner: duplicate fingerprint → skip with INFO log
- Spawner: variant with `mode: shadow` → registered strategy has mode "shadow"
- Spawner: variant with `mode: live` → registered strategy has mode "live"
- Spawner: `experiments.enabled: false` → zero variants spawned
- Spawner: variants receive same watchlist and reference data as base strategy
- Config: experiments.yaml loads with Pydantic validation
- Startup: main.py with experiments enabled registers base + variant strategies

**Acceptance:** Variants spawn from config, register with Orchestrator, respect mode setting, deduplicate by fingerprint.

---

## Session 6: Experiment Runner (Backtest Pre-Filter)

**Objective:** Create the experiment runner that generates parameter grids, runs BacktestEngine for each configuration, and stores results. This is the backtest pre-filter that prevents bad variants from consuming shadow resources.

**Creates:**
- `argus/intelligence/experiments/runner.py` (~180 lines) — `ExperimentRunner`: grid generation from PatternParam, BacktestEngine invocation per grid point, result storage, progress logging

**Modifies:** None

**Integrates:** S2 (factory for pattern construction) + S4 (store for result persistence)

**Parallelizable:** No strict need — can run after S2+S4.

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 0 | 0 |
| Context reads (BacktestEngine, factory.py, store.py, vectorbt_pattern.py grid gen) | 4 | 4 |
| New tests (~8: grid generation, mock backtest, result storage, pre-filter logic) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (runner.py ~180 lines — at threshold) | 1 | 2 |
| **Total** | | **12 (Medium)** |

**Tests:**
- Grid generation: BullFlagPattern with default PatternParam ranges → correct grid points
- Grid generation: subset of params (--params flag) → filtered grid
- Runner: mock BacktestEngine, verify called once per grid point
- Runner: results stored in ExperimentStore with correct fingerprints
- Pre-filter: config with negative expectancy → marked as FAILED, not eligible for spawning
- Pre-filter: config with insufficient trades → marked as FAILED
- Dry-run: --dry-run flag → grid computed and printed but no BacktestEngine calls
- Progress: logging emitted at each grid point completion

**Acceptance:** Grid generation from PatternParam metadata. BacktestEngine invoked per grid point. Results persisted. Pre-filter rejects bad configs.

---

## Session 7: Promotion Evaluator + Autonomous Loop

**Objective:** Create the promotion evaluator that compares shadow variant performance against live variants and autonomously promotes/demotes based on accumulated evidence.

**Creates:**
- `argus/intelligence/experiments/promotion.py` (~150 lines) — `PromotionEvaluator`: shadow data collection from CounterfactualTracker results, comparison via Pareto API, promotion/demotion decisions, mode update mechanism, event logging

**Modifies:**
- `argus/main.py` — Wire promotion evaluator check into SessionEndEvent handler (~10 lines, after Learning Loop trigger)

**Integrates:** S4 (store for promotion event logging) + existing `comparison.py` (Pareto dominance) + existing CounterfactualTracker (shadow results)

**Parallelizable:** No (modifies main.py)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads (comparison.py, counterfactual_store.py, store.py, main.py) | 4 | 4 |
| New tests (~8: promotion criteria, Pareto comparison, demotion, thresholds) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (promotion.py ~150 lines) | 0 | 0 |
| **Total** | | **11 (Medium)** |

**Tests:**
- Promotion: shadow variant with 30+ trades + Pareto-dominates live → promoted to live mode
- Promotion: shadow variant with 20 trades (below threshold) → skipped
- Promotion: shadow variant with 30+ trades but does NOT Pareto-dominate → remains shadow
- Demotion: live variant with deteriorating performance (below baseline) → demoted to shadow
- Demotion: live variant with no deterioration → remains live
- Hysteresis: variant promoted, then immediately underperforms → not demoted until min_shadow_days equivalent elapsed since promotion
- Mode update: strategy's config.mode changed from "shadow" to "live" and vice versa
- Logging: promotion/demotion events stored in ExperimentStore with full context

**Acceptance:** Autonomous promotion/demotion based on shadow performance vs live. Respects minimum threshold guards. Events logged.

---

## Session 8: CLI + REST API + Server Integration + Config Gating

**Objective:** Wire all experiment components into the server, create CLI entry point, expose REST API, and add config gating via ExperimentConfig in SystemConfig.

**Creates:**
- `scripts/run_experiment.py` (~60 lines) — CLI with --pattern, --cache-dir, --params, --dry-run
- `argus/api/routes/experiments.py` (~100 lines) — 4 REST endpoints (list, detail, baseline, run)
- `argus/intelligence/experiments/config.py` (~40 lines) — ExperimentConfig Pydantic model

**Modifies:**
- `argus/core/config.py` — Add ExperimentConfig to SystemConfig
- `argus/api/server.py` — Register experiments router, initialize ExperimentStore + PromotionEvaluator in lifespan

**Integrates:** S4 (store) + S5 (spawner) + S6 (runner) + S7 (promotion) — full server wiring

**Parallelizable:** No (final integration session)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | 6 |
| Files modified | 2 | 2 |
| Context reads (server.py, config.py, routes/learning.py pattern, store.py) | 4 | 4 |
| New tests (~8: API endpoints, CLI, config gating, server wiring) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **16 (High)** |

**Risk mitigation:** The 3 new files are all small (60+100+40 = 200 lines total). Each follows established patterns: CLI follows `run_learning_analysis.py`, routes follow `routes/learning.py`, config follows existing Pydantic pattern. The "high" score is driven by file count, not complexity. If compaction threatens, the CLI can be deferred to a Session 8b.

**Tests:**
- API: `GET /api/v1/experiments` returns list (empty when no experiments)
- API: `GET /api/v1/experiments/{id}` returns 404 for nonexistent
- API: `GET /api/v1/experiments/baseline/bull_flag` returns current baseline config
- API: `POST /api/v1/experiments/run` triggers sweep (mock BacktestEngine)
- API: all endpoints return 503 when `experiments.enabled: false`
- CLI: `--dry-run` flag prints grid without executing
- Config: ExperimentConfig loads from YAML, validates all fields
- Config: unrecognized keys in experiments.yaml rejected (verify against model)
- Server: ExperimentStore initialized in lifespan when experiments enabled
- Server: PromotionEvaluator wired to SessionEndEvent when `auto_promote: true`

**Acceptance:** Full experiment pipeline accessible via CLI and REST API. Config-gated. Server wiring complete.

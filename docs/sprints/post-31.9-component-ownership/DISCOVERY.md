# Post-Sprint-31.9: Component Ownership Consolidation — Pre-Sprint Discovery

> Pre-sprint architectural briefing. This doc captures what was learned about
> the `main.py` vs. `api/server.py` component-ownership split during the
> DEF-172/173 impromptu investigation on 2026-04-22. Read this before
> starting the refactor — it represents ~2 hours of investigation that would
> otherwise be re-done.
>
> **Status:** Pre-sprint discovery. NOT a sprint spec. Follow sprint-planning
> protocol (Phase A deep-think → Phase B design summary → Phase C spec)
> when ready to execute. This doc is the Phase A starting material.

## Context

During the Sprint 31.9 FIX-03 session, two DEFs were opened (DEF-172, DEF-173)
that both reduced to the same root cause: ArgusSystem and `api/server.py`
lifespan phases both construct components independently. FIX-03 declined to
fix either at the api/server.py boundary (scope exclusion).

During the follow-up impromptu on 2026-04-22, the investigation revealed
DEF-172 is one symptom of a broader pattern, not a localized issue.

## Current architecture (as of commit 24755ac)

### Components constructed in main.py (ArgusSystem.start)

- `self._catalyst_storage` (CatalystStorage, line 1011) — consumed by `_process_signal` for quality scoring
- `self._quality_engine` (SetupQualityEngine, line 996) — consumed by `_process_signal` signal path
- `self._position_sizer` (DynamicPositionSizer, ~line 996 area)
- `self._eval_store` (EvaluationEventStore, Phase 9 post-FIX-03)
- `self._candle_store` (IntradayCandleStore, Phase 10.4)
- `self._counterfactual_store` (CounterfactualStore, Phase ~10.7)
- `self._experiment_store` (ExperimentStore, Phase 9 post-FIX-03 — enforce_retention wired here)
- `self._regime_history_store` (RegimeHistoryStore)
- All strategies, orchestrator, risk manager, order manager, broker, data service, universe manager

### Components constructed in api/server.py lifespan

Per `_LIFESPAN_PHASES` registry in `argus/api/server.py`:

- `_init_ai_services` — AI client, prompt manager, context builder, action manager, executor registry, daily summary generator, response cache
- `_init_debrief_service` — DebriefService
- `_init_intelligence_pipeline` — CatalystPipeline (with its own CatalystStorage), BriefingGenerator, polling task
- `_init_quality_engine` — SetupQualityEngine + DynamicPositionSizer (second instances of both)
- `_init_telemetry_store` — TelemetryStore wiring for observatory
- `_init_observatory_service` — ObservatoryService (reads from quality_engine, counterfactual_store, evaluation_store)
- `_init_vix_data_service` — VIXDataService
- `_init_learning_loop` — LearningStore, OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, LearningService, ConfigProposalManager
- `_init_experiments` — ExperimentStore (second instance)
- `_init_historical_query_service` — HistoricalQueryService

### The duplication

| Component | main.py instance | api/server.py instance | Consumer split |
|---|---|---|---|
| CatalystStorage | `self._catalyst_storage` | `app_state.catalyst_storage` (via intelligence pipeline) | Signal path (main) vs. catalyst ingestion + REST (api) |
| SetupQualityEngine | `self._quality_engine` | `app_state.quality_engine` | Signal path (main) vs. observatory + REST (api) |
| DynamicPositionSizer | `self._position_sizer` | `app_state.position_sizer` | Same split |
| ExperimentStore | `self._experiment_store` (FIX-03) | `app_state.experiment_store` | Same split |

### The asymmetry

Components owned ONLY by api/server.py and referenced by `_process_signal` indirectly via AppState-like plumbing would cause timing bugs. The reason main.py constructs its own quality engine + catalyst storage at Phase 9.5 is exactly this: the signal path is wired BEFORE the API server starts, so it can't depend on api/server.py-created components.

This is WHY the duplication exists. Solving it requires making the API server's lifespan not be a construction site — pushing that construction work into ArgusSystem so it's available at Phase 9.5, and having api/server.py's `_init_*` functions become no-ops or simple AppState-reference-setters.

## Verified invariants (do not re-test these; investigation complete)

1. `SetupQualityEngine` is stateless — only holds `config` and `db_manager` refs. Two instances score identically for the same input. (Verified via `grep -n "self\._" argus/intelligence/quality_engine.py` — only `self._config` and `self._db`.)
2. `CatalystStorage` close paths both fire correctly (main.py FIX-03 step 5a + api/server.py `shutdown_intelligence`).
3. SQLite WAL mode enables safe multi-reader/single-writer against catalyst.db.
4. AppState is constructed by main.py at Phase 12 (line 1164), BEFORE FastAPI lifespan runs. AppState fields are pre-set for components main.py owns; fields populated DURING lifespan are set by the `_init_*` functions.
5. Lifespan ordering in `_LIFESPAN_PHASES` is fixed. `intelligence_pipeline` runs BEFORE `quality_engine`; both run BEFORE `observatory_service` (observatory depends on quality_engine).

## Recommended refactor approach

### Session 1 (~60-90 min): Intelligence pipeline + CatalystStorage to main.py

- Move `create_intelligence_components` call from `_init_intelligence_pipeline` into a new ArgusSystem Phase (call it 9.3 "Intelligence Pipeline")
- ArgusSystem stores `self._intelligence_components` + `self._catalyst_storage` (replaces current line 1011 duplicate)
- AppState gains `catalyst_storage`, `briefing_generator`, `intelligence_polling_task` as constructor args (main.py populates)
- `_init_intelligence_pipeline` becomes a no-op (deletable) or a sanity check that app_state.catalyst_storage is non-None when config.catalyst.enabled
- main.py's Phase 9.5 quality pipeline init consumes `self._catalyst_storage` (already does; just now there's only one)
- Shutdown consolidation — only main.py closes catalyst_storage; api/server.py teardown removes the redundant path

Risk: intelligence pipeline has a polling task that runs continuously. Moving its ownership to main.py means the task needs to be managed in main.py's shutdown sequence, not the API lifespan.

### Session 2 (~60-90 min): Quality engine + Learning loop + Experiments to main.py

- Move `_init_quality_engine` logic into main.py Phase 9.5 (mostly already there; just eliminate api/server.py duplicate)
- Move `_init_learning_loop` into main.py Phase (call it 9.7 "Learning Loop"); wire `enforce_retention` next to ExperimentStore's enforce_retention call. DEF-173's fix gets relocated here (and the api/server.py-side call added by this impromptu gets removed).
- Move `_init_experiments` fully into main.py (ExperimentStore side already there from FIX-03; just eliminate api/server.py duplicate)
- Observatory service stays in api/server.py for now (it's REST-scoped and only reads from already-populated app_state)

### Session 3 (~60 min): Remaining phases + validation

- Telemetry store, VIX data service, Historical query service — evaluate each; most should move
- Debrief service can stay (REST-specific)
- AI services probably stay (REST-specific adapters)
- Post-move integration test pass
- Update CLAUDE.md architecture summary
- Close DEF-175

### Tests to write

- Assert AppState fields are populated by main.py at the correct phase (not by lifespan)
- Assert `_init_*` functions that become no-ops are correctly gated (enabled check)
- Integration test: start ArgusSystem, assert `self._catalyst_storage is app_state.catalyst_storage` (same identity)
- Shutdown test: close paths don't double-close or leak handles

## Constraints

- Cannot break existing REST endpoints (all live, feature-flagged by config.catalyst.enabled, config.quality_engine.enabled, etc.)
- Cannot change SetupQualityEngine signature (has live callers in _process_signal)
- Must preserve lifespan ordering constraints (observatory needs quality_engine; learning needs experiment_store)
- Must preserve the config-gated disable paths (if intelligence pipeline disabled, downstream handles gracefully)

## Out of scope

- Renaming components or changing their public interfaces
- Changing DB schemas
- Adding new functionality
- Migrating OTHER dual-ownership patterns that aren't in the component-construction category (e.g., event subscriptions)

## Entry criteria (when ready to start the sprint)

- Sprint 31.9 fully closed (all 9 stages complete)
- Baseline pytest suite stable and understood
- Available weekend or off-trading day for uninterrupted work
- Follow sprint-planning protocol (Phase A → B → C → D) properly; do NOT execute as impromptus

## Exit criteria

- DEF-172 and DEF-175 closed as RESOLVED (not RESOLVED-VERIFIED)
- `api/server.py._init_*` phases reduced to API-adapter-only concerns
- `main.py` Phase numbering updated and documented in architecture.md
- Single CatalystStorage, single SetupQualityEngine, single LearningStore, single ExperimentStore instance at runtime
- Test suite passes with no new flakes

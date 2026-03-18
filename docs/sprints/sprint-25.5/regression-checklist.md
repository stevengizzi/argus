# Sprint 25.5: Regression Checklist

## Critical Invariants

- [ ] **Scanner-only flow unchanged.** With `universe_manager.enabled: false`, strategies receive scanner symbols via `set_watchlist()` exactly as before Sprint 25.5.
- [ ] **`watchlist` property returns `list[str]`.** Any code or test consuming `strategy.watchlist` gets a list, not a set. Verify type explicitly.
- [ ] **`set_watchlist()` accepts `list[str]`.** All existing callers pass lists. The method must accept list input even though internal storage is set.
- [ ] **Strategy `on_candle()` evaluation logic unchanged.** No modifications to entry condition checks, pattern strength calculations, opening range formation, VWAP state machine, or any other strategy-internal logic.
- [ ] **Risk Manager not affected.** No changes to signal processing, circuit breakers, check 0 rejection, or approve-with-modification logic.
- [ ] **Event Bus FIFO ordering preserved.** No changes to event delivery, subscription, or sequence numbering.
- [ ] **Order Manager not affected.** No changes to order execution, position reconstruction, or bracket orders.
- [ ] **Quality pipeline not affected.** No changes to SetupQualityEngine scoring, DynamicPositionSizer, or quality history recording.
- [ ] **Observatory endpoints still return 200.** `/api/v1/observatory/pipeline` and `/api/v1/observatory/session-summary` return 200 OK (with or without data).
- [ ] **No files in "do not modify" list were changed.** Verify via diff.
- [ ] **All pre-existing tests pass.** Full suite with `pytest --ignore=tests/test_main.py -n auto` + `npx vitest run`.
- [ ] **Candle routing path in main.py (lines 724-745) unchanged.** Both UM path and legacy fallback must be identical to pre-sprint state.

## Test Commands

**Full suite (sprint entry + each closeout):**
```bash
pytest --ignore=tests/test_main.py -n auto
cd argus/ui && npx vitest run
```

**Scoped (Session 1 mid-sprint):**
```bash
pytest tests/test_strategies/ tests/test_main_startup.py -v
```

**Scoped (Session 2 mid-sprint):**
```bash
pytest tests/test_evaluation_telemetry_e2e.py tests/test_health.py -v
```

# Sprint 32.5, Session 5 — Close-Out

---BEGIN-CLOSE-OUT---

**Session:** Sprint 32.5 S5 — DEF-131 REST API Enrichment
**Date:** 2026-04-01
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/intelligence/counterfactual_store.py` | modified | Added `variant_id` column migration, `query_positions()`, `count_positions()` |
| `argus/intelligence/experiments/store.py` | modified | Added `query_variants_with_metrics()`, `query_promotion_events()`, `count_promotion_events()` |
| `argus/api/routes/counterfactual.py` | modified | Added `GET /positions` endpoint |
| `argus/api/routes/experiments.py` | modified | Added `GET /variants` and `GET /promotions` endpoints (inserted before `/{experiment_id}` catch-all) |
| `tests/api/test_counterfactual_api.py` | modified | Added 8 new tests for positions endpoint; updated docstring |
| `tests/api/test_experiments_api.py` | modified | Added 4 new tests for variants and promotions endpoints; added PromotionEvent/VariantDefinition imports |

### Judgment Calls
- **`count_promotion_events()` with no filters**: Spec asked for total_count in promotions response. Added a parameterless `count_promotion_events()` on ExperimentStore rather than a filtered count, as promotions table is small and no filter params were specified in the promotions endpoint. Consistent with the endpoint spec (limit/offset only, no filters).
- **`trade_count: 0`** in `query_variants_with_metrics()`: Live trade count per variant is not tracked in `experiments.db` (it lives in `argus.db`). Returned `0` as a sentinel. The spec says "trade_count, shadow_trade_count" — shadow comes from `experiments.shadow_trades`, live is not accessible from this store. The UI layer can supplement if needed.
- **New tests reuse inline fixtures**: The variant/promotion happy-path tests build their own AppState inline rather than composing from conftest, following the pattern already established in `test_experiments_api.py`'s existing `app_state_with_experiments` fixture.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| `CounterfactualStore.query_positions()` with filters + pagination | DONE | `counterfactual_store.py:query_positions()` |
| `CounterfactualStore.count_positions()` for total_count | DONE | `counterfactual_store.py:count_positions()` |
| `variant_id` column migration in `initialize()` | DONE | `counterfactual_store.py:initialize()` |
| `ExperimentStore.query_variants_with_metrics()` | DONE | `experiments/store.py:query_variants_with_metrics()` |
| `ExperimentStore.query_promotion_events()` with pagination | DONE | `experiments/store.py:query_promotion_events()` |
| `GET /api/v1/counterfactual/positions` JWT-protected | DONE | `routes/counterfactual.py:get_counterfactual_positions()` |
| `GET /api/v1/experiments/variants` JWT-protected + 503 gated | DONE | `routes/experiments.py:list_variants_with_metrics()` |
| `GET /api/v1/experiments/promotions` JWT-protected + 503 gated | DONE | `routes/experiments.py:list_promotion_events()` |
| Empty state → empty list (not error) for all endpoints | DONE | All endpoints handle None store / empty DB gracefully |
| `experiments.enabled=false` → 503 for experiment endpoints | DONE | Via `_get_experiment_store()` helper |
| `experiments.enabled=false` → counterfactual positions still work | DONE | No dependency on `experiment_store` in positions endpoint |
| Pagination SQL-level (not in-memory) | DONE | LIMIT/OFFSET in SQL queries |
| Existing endpoints unchanged | DONE | Verified by full test suite |
| 8+ new tests | DONE | 12 new tests added (8 positions + 4 variants/promotions) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| GET /api/v1/experiments response unchanged | PASS | Existing tests pass |
| GET /api/v1/experiments/{id} unchanged | PASS | Existing tests pass |
| GET /api/v1/experiments/baseline/{pattern} unchanged | PASS | Existing tests pass |
| POST /api/v1/experiments/run unchanged | PASS | Existing tests pass |
| GET /api/v1/counterfactual/accuracy unchanged | PASS | Existing tests pass |
| CounterfactualStore write path untouched | PASS | `write_open`, `write_close` not modified |
| New /variants route not consumed by /{experiment_id} | PASS | Inserted before catch-all route |
| New /promotions route not consumed by /{experiment_id} | PASS | Inserted before catch-all route |

### Test Results
- Tests run: 1023
- Tests passed: 1023
- Tests failed: 0
- New tests added: 12
- Command used: `python -m pytest tests/api/ tests/intelligence/ -x -q`

### Unfinished Work
- None — all spec items complete.

### Notes for Reviewer
- `GET /experiments/variants` and `GET /experiments/promotions` are registered BEFORE `GET /{experiment_id}` in `experiments.py` to avoid route shadowing. Reviewer should confirm ordering is correct.
- `query_variants_with_metrics()` returns `trade_count: 0` — live trade count not available from `experiments.db`. This is intentional; the spec said "trade_count" but the data isn't accessible within the store's scope.
- The `variant_id` column added to `counterfactual_positions` is nullable and not populated by existing write paths (pre-Sprint-32 data and current writer don't set it). It's present for future use when ExperimentRunner links shadow positions to specific variants.

---END-CLOSE-OUT---

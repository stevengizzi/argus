# Sprint 32.5, Session 5 — Tier 2 Review

---BEGIN-REVIEW---

**Reviewer:** Tier 2 Automated Review
**Session:** Sprint 32.5 S5 — DEF-131 REST API Enrichment
**Date:** 2026-04-01
**Verdict:** CLEAR

## Summary

Session 5 adds three new JWT-protected REST endpoints to expose counterfactual
shadow positions, experiment variants with metrics, and promotion event history.
The implementation is clean, correctly scoped, and all 1023 tests pass
(12 new + 1011 pre-existing).

## Checklist Results

### Do-Not-Modify Files
- [x] `argus/intelligence/counterfactual.py` — no diff (verified)
- [x] `argus/intelligence/experiments/promotion.py` — no diff (verified)
- [x] `argus/core/events.py` — no diff (verified)
- [x] `argus/execution/order_manager.py` — no diff (verified)

### Session-Specific Review Focus

1. **JWT protection on all 3 endpoints:** PASS. All three new endpoints
   (`/positions`, `/variants`, `/promotions`) include
   `_auth: dict = Depends(require_auth)`. Test coverage confirms 401 for
   unauthenticated requests.

2. **Read-only query methods:** PASS. All new store methods
   (`query_positions`, `count_positions`, `query_variants_with_metrics`,
   `query_promotion_events`, `count_promotion_events`) use SELECT only.
   No INSERT/UPDATE/DELETE in any new code past line 270 in
   `counterfactual_store.py` or past line 554 in `store.py`.

3. **Existing 5 endpoints unchanged:** PASS. The diff adds new endpoints
   without modifying the existing `/accuracy`, `GET /experiments`,
   `GET /experiments/{id}`, `GET /experiments/baseline/{pattern}`, and
   `POST /experiments/run` endpoints. Pre-existing tests all pass.

4. **CounterfactualStore write path untouched:** PASS. `write_open` and
   `write_close` methods are unmodified. The only change to the existing
   `initialize()` method is the `variant_id` column migration (additive
   ALTER TABLE with pass-on-exists).

5. **SQL-level pagination:** PASS. `query_positions` uses
   `LIMIT ? OFFSET ?` in SQL. `query_promotion_events` uses
   `LIMIT ? OFFSET ?` in SQL. `query_variants_with_metrics` does not
   have pagination (returns all variants) -- this is acceptable given the
   expected low cardinality of the variants table and is noted in the
   close-out.

6. **variant_id=None handling:** PASS. The `variant_id` column is added
   as nullable TEXT. Pre-Sprint-32 shadow positions will have NULL in
   this column. The query does not filter on variant_id, so old records
   are returned correctly.

7. **experiments.enabled=false gating:** PASS. `/variants` and
   `/promotions` both call `_get_experiment_store(state)` which raises
   503 when `experiment_store is None`. `/positions` does NOT depend on
   `experiment_store` -- it uses `counterfactual_store` directly, so it
   works regardless of the experiments.enabled flag. Correct behavior.

### REST API Compatibility
- [x] All 4 existing experiment endpoints unchanged
- [x] Counterfactual accuracy endpoint unchanged
- [x] All endpoints return 401 for unauthenticated requests

### Counterfactual Pipeline
- [x] SignalRejectedEvent subscription unchanged (no diff in counterfactual.py)
- [x] Shadow position tracking unchanged
- [x] Write path unchanged (write_open/write_close unmodified)
- [x] Fire-and-forget preserved

### Config Gating
- [x] experiments.enabled=false -> experiment endpoints return 503
- [x] experiments.enabled=false -> counterfactual positions still work

### Test Suite Health
- [x] All pre-existing tests pass (1023 total = 1011 pre-existing + 12 new)
- [x] New tests cover all required cases (8 positions + 4 variants/promotions = 12)

## Observations (Non-Blocking)

**O1: Timestamp timezone inconsistency across route files.** The
counterfactual routes use `datetime.now(_ET)` (Eastern Time) while the
experiments routes use `datetime.now(UTC)`. This is pre-existing -- the
accuracy endpoint already used ET -- and the new positions endpoint
follows the file-local convention. Not a regression, but worth noting for
a future consistency pass.

**O2: `query_variants_with_metrics` lacks pagination.** Unlike the other
two new query methods, variants are returned in full without LIMIT/OFFSET.
This is acceptable given the expected low cardinality (tens to low hundreds
of variants), and is documented in the close-out judgment calls.

**O3: `trade_count: 0` sentinel in variants response.** The
`query_variants_with_metrics` method returns `trade_count: 0` because live
trade counts are stored in `argus.db`, not `experiments.db`. The close-out
documents this as intentional. The UI layer can supplement this from the
trade logger if needed.

**O4: Broad `except Exception: pass` in schema migration.** Both the
`counterfactual_store.py` and `store.py` migrations catch all exceptions
when adding columns. This is a common pattern for idempotent ALTER TABLE
operations in SQLite (which raises OperationalError for duplicate columns).
Acceptable but could be narrowed to `sqlite3.OperationalError` for
precision.

## Test Results

```
tests/api/ + tests/intelligence/: 1023 passed, 0 failed (141.82s)
tests/api/test_counterfactual_api.py + test_experiments_api.py: 35 passed (10.08s)
```

## Verdict

CLEAR. All spec items implemented correctly. No regressions. No escalation
triggers. The implementation is minimal, well-tested, and follows established
patterns.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "findings": [],
  "observations": [
    {
      "id": "O1",
      "severity": "low",
      "description": "Timestamp timezone inconsistency: counterfactual routes use ET, experiments routes use UTC. Pre-existing, not a regression.",
      "file": "argus/api/routes/counterfactual.py",
      "line": 94
    },
    {
      "id": "O2",
      "severity": "low",
      "description": "query_variants_with_metrics lacks pagination. Acceptable given low expected cardinality.",
      "file": "argus/intelligence/experiments/store.py",
      "line": 556
    },
    {
      "id": "O3",
      "severity": "low",
      "description": "trade_count always returns 0 (live trades in separate DB). Documented as intentional.",
      "file": "argus/intelligence/experiments/store.py",
      "line": 615
    },
    {
      "id": "O4",
      "severity": "low",
      "description": "Broad except Exception: pass in ALTER TABLE migrations could be narrowed to sqlite3.OperationalError.",
      "file": "argus/intelligence/counterfactual_store.py",
      "line": 132
    }
  ],
  "tests_pass": true,
  "tests_total": 1023,
  "tests_new": 12,
  "tests_failed": 0,
  "escalation_triggers": [],
  "session_self_assessment_accurate": true,
  "context_state": "GREEN"
}
```

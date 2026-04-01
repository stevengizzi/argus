# Sprint 32.5, Session 5: DEF-131 REST API Enrichment

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual_store.py` (existing query surface)
   - `argus/intelligence/counterfactual.py` (CounterfactualTracker — read-only, understand data model)
   - `argus/intelligence/experiments/store.py` (ExperimentStore — updated in S1)
   - `argus/intelligence/experiments/promotion.py` (PromotionEvaluator — understand promotion events)
   - `argus/api/routes/counterfactual.py` (existing accuracy endpoint)
   - `argus/api/routes/experiments.py` (existing 4 endpoints from Sprint 32)
2. Run the scoped test baseline (DEC-328):
   ```
   cd /Users/stevengizzi/argus && python -m pytest tests/api/ tests/intelligence/ -x -q
   ```
   Expected: all passing
3. Verify you are on branch: `main`
4. Create working branch: `git checkout -b sprint-32.5-session-5`

## Objective
Add 3 new JWT-protected REST endpoints that expose counterfactual shadow positions, experiment variant status with metrics, and promotion event history. These endpoints power the UI work in S6 and S7.

## Requirements

1. **In `argus/intelligence/counterfactual_store.py`:**
   - Add `query_positions(strategy_id: str | None, date_from: str | None, date_to: str | None, rejection_stage: str | None, limit: int = 500, offset: int = 0) -> list[dict]` method
   - Returns shadow positions (active + closed) with all fields: symbol, strategy_id, variant_id (nullable for pre-Sprint-32 data), entry_time, entry_price, exit_time, exit_price, theoretical_pnl, r_multiple, mfe_price, mae_price, mfe_r, mae_r, rejection_reason, rejection_stage, quality_grade, quality_score
   - Support pagination via limit/offset
   - Order by entry_time DESC (most recent first)

2. **In `argus/intelligence/experiments/store.py`:**
   - Add `query_variants_with_metrics() -> list[dict]` method
   - Returns all variant definitions with: variant_id, pattern_name, detection_params, exit_overrides (from S1), config_fingerprint, mode (live/shadow), status, trade_count, shadow_trade_count, and key metrics if available (win_rate, expectancy, sharpe)
   - Add `query_promotion_events(limit: int = 100, offset: int = 0) -> list[dict]` method
   - Returns promotion/demotion events with: event_id, variant_id, pattern_name, event_type (promote/demote), from_mode, to_mode, timestamp, trigger_reason, metrics_snapshot

3. **In `argus/api/routes/counterfactual.py`:**
   - Add `GET /api/v1/counterfactual/positions` endpoint
   - Query params: `strategy_id`, `date_from`, `date_to`, `rejection_stage`, `limit` (default 500), `offset` (default 0)
   - JWT-protected (same pattern as existing accuracy endpoint)
   - Returns JSON with `positions` list + `total_count` for pagination
   - Handle empty results gracefully (empty list, not error)

4. **In `argus/api/routes/experiments.py`:**
   - Add `GET /api/v1/experiments/variants` endpoint
   - JWT-protected, returns all variants with metrics
   - When `experiments.enabled=false`, return 503 (existing pattern)
   - Add `GET /api/v1/experiments/promotions` endpoint
   - Query params: `limit` (default 100), `offset` (default 0)
   - JWT-protected, returns promotion events
   - When `experiments.enabled=false`, return 503

5. **All endpoints:**
   - Follow existing response shape conventions (check other route files)
   - Return 401 for unauthenticated requests
   - Handle DB query errors gracefully (500 with error detail, not crash)

## Constraints
- Do NOT modify: `intelligence/counterfactual.py` (tracker write/subscription logic)
- Do NOT modify: `intelligence/experiments/promotion.py` (promotion logic)
- Do NOT modify: existing endpoint response schemas (4 experiment + 1 accuracy endpoints)
- Do NOT modify: core/events.py, execution/order_manager.py
- Query methods must be read-only — no writes to any DB from new methods

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **Positions endpoint — happy path:** seed data, query, verify response shape
  2. **Positions endpoint — filters:** strategy_id, date range, rejection_stage filters
  3. **Positions endpoint — pagination:** limit/offset work correctly
  4. **Positions endpoint — empty:** no data → empty list (not error)
  5. **Positions endpoint — auth:** no JWT → 401
  6. **Variants endpoint — happy path:** seed variants, query, verify shape
  7. **Variants endpoint — experiments disabled:** 503
  8. **Promotions endpoint — happy path:** seed events, query, verify shape
- Minimum new test count: 8
- Test command (scoped): `python -m pytest tests/api/ tests/intelligence/ -x -q`

## Definition of Done
- [ ] CounterfactualStore.query_positions() implemented with filters and pagination
- [ ] ExperimentStore.query_variants_with_metrics() implemented
- [ ] ExperimentStore.query_promotion_events() implemented with pagination
- [ ] GET /api/v1/counterfactual/positions endpoint working
- [ ] GET /api/v1/experiments/variants endpoint working
- [ ] GET /api/v1/experiments/promotions endpoint working
- [ ] All endpoints JWT-protected
- [ ] All endpoints handle empty state
- [ ] experiments.enabled=false → 503 for experiment endpoints
- [ ] Existing endpoints unchanged
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| GET /api/v1/experiments response unchanged | Compare response shape before/after |
| GET /api/v1/experiments/{id} unchanged | Same |
| GET /api/v1/experiments/baseline/{pattern} unchanged | Same |
| POST /api/v1/experiments/run unchanged | Same |
| GET /api/v1/counterfactual/accuracy unchanged | Same |
| CounterfactualStore write path untouched | grep for write operations, verify unchanged |

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-5-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command (scoped): `python -m pytest tests/api/ tests/intelligence/ -x -q`
5. Files NOT modified: `intelligence/counterfactual.py` (tracker logic), `intelligence/experiments/promotion.py`, `core/events.py`, `execution/order_manager.py`

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify all 3 new endpoints are JWT-protected (HTTPBearer pattern)
2. Verify query methods are read-only (no INSERT/UPDATE/DELETE)
3. Verify existing 5 endpoints have identical response schemas
4. Verify CounterfactualStore write path completely untouched (diff should show only new methods)
5. Verify pagination (limit/offset) is SQL-level, not in-memory slicing
6. Verify variant_id=None handled gracefully for pre-Sprint-32 shadow positions
7. Verify experiments.enabled=false → 503 for experiment endpoints but NOT for counterfactual positions (counterfactual ≠ experiments)

## Sprint-Level Regression Checklist (for @reviewer)

### REST API Compatibility
- [ ] All 4 existing experiment endpoints unchanged
- [ ] Counterfactual accuracy endpoint unchanged
- [ ] All endpoints return 401 for unauthenticated requests

### Counterfactual Pipeline
- [ ] SignalRejectedEvent subscription unchanged
- [ ] Shadow position tracking unchanged
- [ ] Write path unchanged
- [ ] Fire-and-forget preserved

### Config Gating
- [ ] experiments.enabled=false → experiment endpoints return 503
- [ ] experiments.enabled=false → counterfactual positions still work

### Test Suite Health
- [ ] All pre-existing pytest pass
- [ ] All pre-existing Vitest pass

## Sprint-Level Escalation Criteria (for @reviewer)

### Tier 3 Triggers
1. Fingerprint backward incompatibility
2. BacktestEngine reference data requires architectural changes
3. ExperimentConfig extra="forbid" conflict

### Scope Reduction Triggers
1. CounterfactualStore query >2s on 90-day data → add pagination (already included)

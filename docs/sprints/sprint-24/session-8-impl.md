# Sprint 24, Session 8: API Routes for Quality Data

## Pre-Flight Checks
1. Read: `argus/api/routes/__init__.py`, `argus/intelligence/quality_engine.py`, `argus/api/dependencies.py`, `argus/db/schema.sql` (quality_history table)
2. Scoped test: `python -m pytest tests/api/ -x -q`
3. Branch: `sprint-24`

## Objective
Create 3 quality API endpoints. Register in router.

## Requirements

### 1. Create `argus/api/routes/quality.py`:

**`GET /api/v1/quality/{symbol}`** — Most recent quality score for symbol.
- Query quality_history table WHERE symbol = ?, ORDER BY scored_at DESC, LIMIT 1
- Return: `{symbol, score, grade, risk_tier, components: {ps, cq, vp, hm, ra}, scored_at}`
- 404 if no history for symbol

**`GET /api/v1/quality/history`** — Paginated quality history.
- Query params: `symbol` (optional), `strategy_id` (optional), `grade` (optional), `start_date` (optional), `end_date` (optional), `limit` (default 50, max 200), `offset` (default 0)
- Return: `{items: [...], total: count, limit, offset}`

**`GET /api/v1/quality/distribution`** — Today's grade distribution.
- Query: `SELECT grade, COUNT(*) FROM quality_history WHERE scored_at >= today GROUP BY grade`
- Return: `{grades: {"A+": 0, "A": 2, "A-": 5, "B+": 8, ...}, total: N, filtered: M}`
  - `filtered` = count where grade below min_grade_to_trade (signals that were skipped)

All endpoints require JWT auth (use existing `get_current_user` dependency).

### 2. In `argus/api/routes/__init__.py`:
Register quality router with prefix `/api/v1/quality`.

## Constraints
- Do NOT modify: existing route files, server.py, quality_engine.py
- Follow existing route patterns (see intelligence.py, trades.py for examples)

## Test Targets
- `test_quality_symbol_returns_latest`: Insert 2 records, verify latest returned
- `test_quality_symbol_404`: No records → 404
- `test_quality_history_pagination`: Verify limit/offset
- `test_quality_history_filter_by_grade`: Filter grade="A" → only A records
- `test_quality_history_filter_by_symbol`: Filter symbol → correct records
- `test_quality_distribution_all_grades`: All grades present (zero counts for empty)
- `test_quality_distribution_includes_filtered_count`: Count of below-min-grade signals
- `test_quality_endpoints_require_auth`: 401 without JWT
- `test_quality_history_date_range_filter`: start_date/end_date filtering
- Minimum: 10
- Test command: `python -m pytest tests/api/test_quality.py -x -q`

## Definition of Done
- [ ] 3 endpoints working with correct responses
- [ ] JWT auth required
- [ ] Router registered
- [ ] 10+ new tests

## Close-Out
Write report to `docs/sprints/sprint-24/session-8-closeout.md`.


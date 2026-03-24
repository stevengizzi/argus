# Sprint 27.65, Session S5: Frontend + Observatory Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/analytics/observatory_service.py`
   - `argus/core/sector_rotation.py`
   - `argus/ui/src/` (explore Dashboard, Observatory, and query hook files)
   - `docs/sprints/sprint-27.65/S4-closeout.md` (verify S4 complete)
2. Run the test baseline (DEC-328 — final session, full suite):
   Full suite: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   Expected: ~3,337+ tests (S1-S4 added tests), all passing
   Also: `cd argus/ui && npx vitest run`
   Expected: ~631+ Vitest tests, all passing
3. Verify you are on the correct branch

## Objective
Fix frontend issues: Session Timeline missing 3 strategies, Observatory Funnel
returning all zeros, frontend polling frequency optimization. Clean up FMP
sector-performance error logging. Log ORB Scalp time-stop observation as DEF item.

## Requirements

### R1: Session Timeline — add 3 new strategies
1. Find the Session Timeline component on the Dashboard page.
   - It currently shows only 4 strategies: ORB Breakout, ORB Scalp, VWAP Reclaim,
     Afternoon Momentum.
   - It must show all 7: add Red-to-Green, Bull Flag, Flat-Top Breakout.
2. **Preferred approach:** Switch to dynamically pulling registered strategies
   from the API (`/api/v1/strategies` or equivalent) rather than a hardcoded list.
   If the strategies endpoint already exists, use it. If not, use the health
   endpoint which lists all registered strategies.
3. **Fallback approach:** If dynamic isn't feasible without larger refactoring,
   simply add the 3 missing strategies to the static list, matching the existing
   naming/color conventions.

### R2: Observatory Funnel — fix zero stage counts
1. Investigate `ObservatoryService.get_pipeline_stages()`:
   - The session-summary endpoint shows correct data (1,560 symbols, 77
     evaluations, 3 signals, 3 trades)
   - The pipeline endpoint returns all zeros
   - These use different methods — figure out why pipeline stages are empty
2. The funnel has 7 tiers: Universe → Viable → Routed → Evaluating →
   Near-trigger → Signal → Traded
   - **Static tiers** (Universe, Viable, Routed): should come from
     UniverseManager data (total symbols, viable after filters, routed to strategies)
   - **Dynamic tiers** (Evaluating, Near-trigger, Signal, Traded): should come
     from EvaluationEventStore or session state
3. Fix the data mapping so the pipeline endpoint returns correct counts.
   Verify the WebSocket push also sends updated pipeline data.

### R3: FMP sector-performance 403 log level
1. In `argus/core/sector_rotation.py`:
   - The FMP 403 is logged at ERROR level
   - Downgrade to WARNING with a clearer message:
     `"FMP sector-performance unavailable (Starter plan) — using fallback classification"`
   - This is a known limitation (Starter plan doesn't include sector performance),
     not an error condition
   - The circuit breaker already handles this correctly, so no behavioral change needed

### R4: Frontend polling frequency optimization
1. Find TanStack Query hooks that set `refetchInterval` for these endpoints:
   - `/api/v1/performance/month` — currently ~25 seconds, increase to 60 seconds
   - `/api/v1/observatory/pipeline` — reduce polling frequency to 10 seconds
     (currently appears to be every 2-3 seconds)
   - `/api/v1/observatory/session-summary` — same as pipeline, 10 seconds
2. Only adjust intervals for non-critical display data. Do NOT reduce frequency
   for trade-critical endpoints (positions, orders, health).

### R5: ORB Scalp time-stop observation (DEF item only)
1. Add a DEF item to `CLAUDE.md`:
   `DEF-XXX: ORB Scalp time-stop dominance — March 24 session showed 80% of
   scalp exits via 120s time-stop (vs target or stop). Parameters (120s window,
   0.3R target) may need tuning after more session data. Track over 5+ sessions
   before adjusting.`
2. No code changes for this item.

## Constraints
- Do NOT modify: backend strategy logic, Order Manager, Risk Manager
- Do NOT modify: Observatory 3D rendering (Three.js) — only fix data flow
- Do NOT modify: WebSocket message format (existing types)
- Frontend polling changes must not affect trade-critical data freshness
- Session Timeline must be visually consistent with existing strategy entries

## Visual Review
The developer should visually verify:
1. **Dashboard Session Timeline:** Shows 7 strategy rows with correct names,
   colors, and operating windows
2. **Observatory Funnel:** Shows non-zero counts at each tier when ARGUS is
   running with live data
3. **Observatory top bar:** Continues to show correct vitals (symbols,
   evaluations, signals, trades)

Verification conditions:
- ARGUS running in paper trading mode with Databento + IBKR connected
- At least 10 minutes after market open (to accumulate evaluation data)

## Test Targets
After implementation:
- Existing tests: all must still pass (full suite — final session)
- New tests to write:
  1. `test_observatory_pipeline_returns_nonzero_counts` — mock UniverseManager and EvaluationEventStore, verify pipeline endpoint returns counts
  2. `test_observatory_pipeline_static_tiers_from_universe_manager` — verify Universe/Viable/Routed come from UM
  3. `test_sector_rotation_403_logged_as_warning` — verify log level is WARNING not ERROR
  4. Vitest: `test_session_timeline_renders_all_strategies` — verify 7 strategy entries rendered
  5. Vitest: `test_session_timeline_dynamic_source` — verify strategies come from API (if dynamic approach used)
- Minimum new test count: 4 pytest + 2 Vitest
- Test commands:
  - `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
  - `cd argus/ui && npx vitest run`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Dashboard loads without errors | Visual check + console |
| Observatory loads and renders 3D views | Visual check |
| All existing frontend tests pass | `npx vitest run` |
| Observatory session-summary still works | API returns 200 with data |
| Sector rotation fallback still works | Log shows WARNING, not ERROR |

## Definition of Done
- [ ] Session Timeline shows all 7 strategies
- [ ] Observatory Funnel shows non-zero pipeline stages
- [ ] FMP 403 downgraded to WARNING
- [ ] Frontend polling intervals optimized
- [ ] DEF item logged for ORB Scalp observation
- [ ] All existing tests pass (full suite — final session)
- [ ] 4+ pytest + 2+ Vitest new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write close-out to: `docs/sprints/sprint-27.65/S5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S5-closeout.md`
3. Diff range: full sprint diff from sprint start
4. Test command (final session — full suite):
   - `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   - `cd argus/ui && npx vitest run`
5. Files NOT to modify: `argus/execution/`, `argus/core/risk_manager.py`, `argus/strategies/`

Write review to: `docs/sprints/sprint-27.65/S5-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify Session Timeline is dynamic (preferred) or complete (all 7 strategies)
2. Verify Observatory pipeline data mapping is correct (static vs dynamic tiers)
3. Verify polling interval changes don't affect trade-critical endpoints
4. Verify no console errors in frontend
5. Verify DEF item added to CLAUDE.md with correct format

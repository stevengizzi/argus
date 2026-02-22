# Sprint 14 — Code Review Handoff Briefs

> Paste the appropriate brief into a NEW conversation in the ARGUS project.
> Before starting: commit, push, and click "Sync now" on the project.

---

## Review A: After Session 5 (All REST Endpoints Complete)

```
ARGUS Sprint 14 — Code Review A (REST Endpoints)

I just completed Sessions 1-5 of Sprint 14 (Command Center API). The code is committed and pushed — please read directly from the repo, not transcripts.

Sessions completed:
1. Auth system (JWT, bcrypt, setup_password CLI, login/refresh endpoints)
2. Server factory (create_app, run_server, CORS) + account endpoint
3. Positions + trades endpoints + TradeLogger query methods
4. PerformanceCalculator extraction + performance endpoint
5. Health + strategies endpoints

All 7 REST endpoints are now implemented under /api/v1.

Please review these files:

**Core API layer:**
- argus/api/auth.py
- argus/api/dependencies.py
- argus/api/server.py
- argus/api/routes/ (all 7 route files + __init__.py)

**New shared module:**
- argus/analytics/performance.py

**Modifications to existing code:**
- argus/execution/order_manager.py (added get_managed_positions)
- argus/analytics/trade_log.py (added query_trades, count_trades, get_daily_pnl, get_todays_pnl, get_todays_trade_count)
- argus/config/ (ApiConfig addition to SystemConfig)
- argus/backtest/metrics.py (only if refactored to use shared PerformanceCalculator)

**Tests:**
- tests/api/ (all test files + conftest.py)
- tests/analytics/test_performance.py

I need you to check:

1. **Interface fidelity:** Compare implementations against .claude/rules/sprint-14.md contracts. Flag any drift in function signatures, field names, response shapes, or auth patterns. These must be fixed before Session 6 (WebSocket) builds on top.

2. **SQL safety in TradeLogger queries:** Are the new query methods using parameterized queries? Any injection risk? Edge cases with NULL fields or empty database?

3. **PerformanceCalculator:** Are the metric formulas correct? Does compute_metrics handle edge cases (empty input, all wins, all losses, division by zero in profit_factor/Sharpe)? If backtest/metrics.py was refactored to use it, did behavior stay identical?

4. **Test quality:** Are tests actually validating behavior, or are any tautological? Any critical paths untested? Are the conftest fixtures realistic enough?

5. **Architectural issues:** Anything that will cause problems for:
   - Session 6: WebSocket bridge subscribing to EventBus and serializing events
   - Session 7: main.py Phase 11 integration, dev state seeding
   - Sprint 15: React dashboard consuming these endpoints

6. **Follow-up prompts:** If anything needs fixing, draft exact Claude Code prompts I can run before starting Session 6. Keep each prompt self-contained (inline all needed context, don't reference the spec file).

7. **Current test count** should be around 870-880. Let me know if anything looks off.
```

---

## Review B: After Session 7 (Sprint Complete)

```
ARGUS Sprint 14 — Code Review B (Sprint Complete)

I just completed all 7 sessions of Sprint 14. The code is committed and pushed — please read directly from the repo.

Sessions 6-7 added:
6. WebSocket bridge (EventBus → WebSocket event streaming with tick throttling)
7. Dev state + main.py Phase 11 integration + React scaffolding + cleanup

Review A covered Sessions 1-5 (REST endpoints) and any issues were fixed.

Please review these new files:

**WebSocket:**
- argus/api/serializers.py
- argus/api/websocket/live.py (WebSocketBridge, ClientConnection, endpoint)
- tests/api/test_websocket.py

**Integration:**
- argus/api/dev_state.py (mock AppState with seeded data)
- argus/api/__main__.py (standalone --dev entry point)
- argus/main.py (Phase 11 addition + shutdown changes)

**React scaffolding:**
- argus/ui/src/api/ (client.ts, types.ts, ws.ts)
- argus/ui/src/stores/ (auth.ts, live.ts)
- argus/ui/src/pages/ (Login.tsx, ConnectionTest.tsx)
- argus/ui/src/App.tsx
- argus/ui/vite.config.ts, tailwind.config.js

**Updated docs:**
- CLAUDE.md
- docs/03_ARCHITECTURE.md (if updated)

I need you to check:

1. **WebSocket bridge:**
   - EventBus subscription correctness (right event types?)
   - Tick throttling logic (monotonic clock, position filtering, rate limiting)
   - Client lifecycle (add/remove, sender task cleanup, QueueFull handling)
   - Auth on connect (token via query param, close 4001 on failure)
   - Serializer handling of all event types (nested dataclasses, datetime conversion)

2. **main.py integration:**
   - Phase 11 startup ordering (after all trading components)
   - Graceful handling of missing ARGUS_JWT_SECRET
   - Shutdown ordering (API stops before trading components)
   - Signal handler conflict avoidance with uvicorn

3. **TypeScript ↔ Python contract:**
   - Do the TypeScript interfaces in src/api/types.ts exactly match the actual Python API response shapes from Sessions 1-5?
   - Any mismatches will cause silent runtime errors in Sprint 15

4. **Dev state quality:**
   - Is the seeded data realistic enough to develop the frontend against?
   - Are mock ManagedPositions properly constructed?
   - Does the ConnectionTest page have real data to show?

5. **Gate check:**
   - [ ] All tests pass, zero regressions from 811 baseline
   - [ ] ruff clean
   - [ ] python -m argus.api.setup_password works
   - [ ] python -m argus.api.server --dev starts
   - [ ] All 7 REST endpoints return valid JSON
   - [ ] WebSocket connects and receives events
   - [ ] cd argus/ui && npm run build succeeds
   - [ ] Login → ConnectionTest shows data
   - [ ] python -m argus.main still starts correctly

6. **Docs sync:** Draft complete copy-paste-ready updates for:
   - 05_DECISION_LOG.md — DEC-099 through DEC-103 (pre-drafted content exists in this project's earlier conversations, but verify against what actually got implemented and adjust if needed)
   - 02_PROJECT_KNOWLEDGE.md — Sprint 14 complete, actual test count, any new decisions
   - 03_ARCHITECTURE.md — Section 4 implementation status
   - 10_PHASE3_SPRINT_PLAN.md — Sprint 14 → completed table
   - CLAUDE.md — verify Session 7 updates are correct and complete

7. **Follow-up prompts:** If anything needs fixing, draft Claude Code prompts.

8. **Sprint 15 readiness:** Is the API solid enough to build the React dashboard against? Any endpoint changes you'd recommend before Sprint 15 starts? Any missing data that the dashboard will need?

Final test count should be ~890-910. Sprint 14 is complete after this review and any fixes.
```

# Sprint 28, Session 5: REST API + Auto Post-Session Trigger

## Pre-Flight Checks
1. Read: `argus/intelligence/learning/learning_service.py` (S3b), `argus/intelligence/learning/config_proposal_manager.py` (S4), `argus/api/server.py` (current lifespan), `argus/main.py` (EOD flatten section), `argus/core/events.py` (event types)
2. Run: `python -m pytest tests/intelligence/learning/ -x -q` (all prior sessions passing)
3. Verify correct branch, S3b and S4 both merged

## Objective
Expose the Learning Loop via REST endpoints, wire into server lifespan, and implement the auto post-session trigger via Event Bus (Amendment 13).

## Requirements

1. **Create `argus/api/routes/learning.py`:**
   - `POST /api/v1/learning/trigger` — runs analysis, returns report summary. 409 if already running.
   - `GET /api/v1/learning/reports` — list reports (query params: start_date, end_date, limit)
   - `GET /api/v1/learning/reports/{report_id}` — single report
   - `GET /api/v1/learning/proposals` — list proposals (query params: status, report_id)
   - `POST /api/v1/learning/proposals/{proposal_id}/approve` — body: {notes?: string}. Returns updated proposal. 400 for illegal transitions (e.g., SUPERSEDED → APPROVED per Amendment 6).
   - `POST /api/v1/learning/proposals/{proposal_id}/dismiss` — body: {notes?: string}
   - `POST /api/v1/learning/proposals/{proposal_id}/revert` — triggers apply_single_change revert. 400 if not APPLIED or already REVERTED.
   - `GET /api/v1/learning/config-history` — audit trail (query params: start_date, end_date)
   - All endpoints JWT-protected (existing auth pattern)

2. **Modify `argus/api/server.py`:**
   - In lifespan: initialize LearningStore, OutcomeCollector, analyzers, LearningService, ConfigProposalManager
   - **Startup:** Call `ConfigProposalManager.apply_pending()` during startup (Amendment 1)
   - Register learning routes
   - Config-gated: skip initialization when `learning_loop.enabled: false`

3. **Add `SessionEndEvent` to `argus/core/events.py` (Amendment 13):**
   - Simple event: `SessionEndEvent(timestamp, trading_day, trades_count, counterfactual_count)`

4. **Modify `argus/main.py`:**
   - After EOD flatten completes, publish `SessionEndEvent` on Event Bus
   - LearningService subscribes to `SessionEndEvent` in its initialization
   - **Auto trigger logic (in LearningService, not main.py):**
     - On `SessionEndEvent`: check `auto_trigger_enabled`
     - **Zero-trade guard (Amendment 10):** Skip if `trades_count == 0` AND `counterfactual_count == 0`. Log INFO. Run if counterfactual-only data exists.
     - `asyncio.wait_for(timeout=120)` on analysis
     - Fire-and-forget: exceptions logged at WARNING, never delays shutdown

## Constraints
- Do NOT modify any strategy files, risk manager, orchestrator, or order manager
- Do NOT modify execution pipeline behavior
- Auto trigger MUST use Event Bus subscription (Amendment 13), NOT direct callback
- `SessionEndEvent` publish point is the ONLY change to main.py's flatten logic

## Test Targets
- `test_learning_api.py`: each endpoint (trigger, reports list/detail, proposals list/approve/dismiss/revert, config-history), 409 on concurrent trigger, 400 on illegal state transitions (SUPERSEDED→APPROVED), JWT auth required
- `test_auto_trigger.py`: fires on SessionEndEvent, skips when disabled, skips on zero-trade+zero-counterfactual, runs on counterfactual-only, timeout enforcement, does not block shutdown
- Minimum: 12 new tests
- Test command: `python -m pytest tests/intelligence/learning/ tests/api/test_learning_api.py -x -q`

## Definition of Done
- [ ] 8 REST endpoints, all JWT-protected
- [ ] Server lifespan initializes Learning Loop components
- [ ] ConfigProposalManager.apply_pending() called at startup
- [ ] SessionEndEvent added to events.py (Amendment 13)
- [ ] Auto trigger via Event Bus subscription, not direct callback
- [ ] Zero-trade guard on auto trigger (Amendment 10)
- [ ] Config-gated (disabled = skip all initialization)
- [ ] ≥12 new tests
- [ ] Close-out to `docs/sprints/sprint-28/session-5-closeout.md`
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL:** Verify auto trigger uses Event Bus, not direct callback (Amendment 13)
2. Verify apply_pending() is called during server startup
3. Verify 400 response for SUPERSEDED → APPROVED transition
4. Verify auto trigger doesn't block shutdown (timeout + fire-and-forget)
5. Verify zero-trade guard (Amendment 10)
6. Verify all endpoints are JWT-protected
7. Verify SessionEndEvent is the ONLY change to main.py's flatten path

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*

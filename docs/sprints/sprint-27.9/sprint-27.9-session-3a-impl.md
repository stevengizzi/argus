# Sprint 27.9, Session 3a: Server Init + REST Endpoints

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/server.py` (lifespan function — note initialization order)
   - `argus/api/routes/__init__.py` (router registration pattern)
   - `argus/api/routes/health.py` or any existing route (pattern reference)
   - `argus/data/vix_data_service.py`
   - `argus/core/regime.py` (RegimeClassifierV2 constructor)
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/api/ -x -q
   ```
   Expected: all passing

## Objective
Initialize VIXDataService in server.py lifespan, wire into RegimeClassifierV2, create REST endpoints for VIX data.

## Requirements

1. **Modify `argus/server.py`** (lifespan function):
   - After existing regime initialization but before strategy initialization:
     - If `config.vix_regime.enabled`:
       - Create `VIXDataService(config=config.vix_regime)`
       - Call `await vix_data_service.initialize()` (non-blocking — if yfinance fails, log WARNING, continue boot)
       - Pass `vix_data_service` to `RegimeClassifierV2` constructor (or set via method)
       - Store reference for API route access (app state or dependency injection pattern matching existing ARGUS approach)
       - Start daily update task: `asyncio.create_task(vix_data_service._start_daily_update_task())`
     - If not enabled: skip entirely, RegimeClassifierV2 gets `vix_data_service=None`
   - **CRITICAL:** VIXDataService initialization must NOT block server startup. Wrap in try/except. If initialization fails (yfinance down), server still starts — VIX features degrade to None.
   - On shutdown: cancel daily update task if running.

2. **Create `argus/api/routes/vix.py`** (~60 lines):
   - `router = APIRouter(prefix="/api/v1/vix", tags=["vix"])`
   - `GET /current`:
     ```python
     @router.get("/current")
     async def get_vix_current(user=Depends(get_current_user)):
         # Get VIXDataService from app state
         latest = vix_service.get_latest_daily()
         if latest is None:
             return {"status": "unavailable", "message": "VIX data not available"}
         # Get regime classifications from RegimeClassifierV2 or calculators
         return {
             "status": "ok" if not vix_service.is_stale else "stale",
             "data_date": latest["data_date"].isoformat(),
             "vix_close": latest["vix_close"],
             "vol_of_vol_ratio": latest.get("vol_of_vol_ratio"),
             "vix_percentile": latest.get("vix_percentile"),
             "term_structure_proxy": latest.get("term_structure_proxy"),
             "realized_vol_20d": latest.get("realized_vol_20d"),
             "variance_risk_premium": latest.get("variance_risk_premium"),
             "regime": {
                 "vol_regime_phase": ...,
                 "vol_regime_momentum": ...,
                 "term_structure_regime": ...,
                 "vrp_tier": ...,
             },
             "is_stale": vix_service.is_stale,
             "last_updated": ...
         }
     ```
   - `GET /history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`:
     - Query params with defaults (last 30 days)
     - Return list of daily records with all derived metrics
     - JWT-protected
   - Both endpoints return 401 when unauthenticated (matching DEC-351 pattern)

3. **Modify `argus/api/routes/__init__.py`** (or wherever routers are registered):
   - Import and include vix router, gated on `config.vix_regime.enabled`

4. **Create `tests/api/test_vix_routes.py`** (4 tests):
   - `test_vix_current_returns_data`: Mock VIXDataService with data → 200 with expected fields
   - `test_vix_current_unavailable`: Mock VIXDataService returning None → 200 with status="unavailable"
   - `test_vix_history_date_filter`: Mock with date range → correct filtering
   - `test_vix_endpoints_require_auth`: Hit endpoints without JWT → 401

## Constraints
- Do NOT modify existing API routes or their behavior
- Do NOT add WebSocket endpoints
- Do NOT modify RegimeClassifierV2 logic beyond accepting VIXDataService parameter (done in 2b)
- Server startup must succeed even if yfinance is unreachable
- Follow existing ARGUS patterns for app state / dependency injection

## Test Targets
- Existing tests: all must still pass
- New tests: 4 in `tests/api/test_vix_routes.py`
- Test command: `python -m pytest tests/api/test_vix_routes.py -x -q`

## Definition of Done
- [ ] VIXDataService initialized in server.py lifespan (non-blocking)
- [ ] VIXDataService wired into RegimeClassifierV2
- [ ] Daily update task started and cancelled on shutdown
- [ ] 2 REST endpoints created and JWT-protected
- [ ] Server starts with vix_regime.enabled: true (R10)
- [ ] Server starts with vix_regime.enabled: false (R11)
- [ ] 4 new tests passing
- [ ] All existing tests pass
- [ ] Close-out written to `docs/sprints/sprint-27.9/session-3a-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R10: Server starts (enabled) | Integration test or manual: boot with config enabled |
| R11: Server starts (disabled) | Integration test: boot with config disabled |
| R15: Existing API endpoints | `python -m pytest tests/api/ -x -q` → all pass |
| Server boots when yfinance unreachable | Test with network mock → server starts, VIX=None |

## Close-Out
Write to: `docs/sprints/sprint-27.9/session-3a-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-3a-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/api/test_vix_routes.py tests/api/ -x -q`
5. Do-not-modify: `argus/strategies/`, `argus/execution/`, `argus/backtest/`, `argus/ai/`, `argus/intelligence/briefing_generator.py`, `argus/core/orchestrator.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify VIXDataService initialization is wrapped in try/except — MUST NOT block server startup
2. Verify daily update task is cancelled in shutdown
3. Verify both endpoints return 401 without JWT
4. Verify server.py initialization order doesn't create circular dependency
5. Verify existing API routes are not modified (diff check)
6. ESCALATION CHECK: If server fails to start with VIX enabled → ESCALATE (#7)

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as in review-context.md. R10, R11, R15 primary.

## Sprint-Level Escalation Criteria (for @reviewer)
1–7 as in review-context.md. #7 (server startup) most relevant.

# Sprint 23.8 Design Summary

**Sprint Goal:** Fix all intelligence pipeline bugs discovered during the March 12 live QA session — pipeline silent death, unmetered Claude API calls, source hang vulnerability, symbol scope mismatch, and Databento warm-up regression — to bring the Sprint 23.5/23.6 pipeline to operational readiness.

**Session Breakdown:**
- Session 1: Pipeline Resilience + Symbol Scope
  - Creates: None
  - Modifies: `argus/intelligence/startup.py`, `argus/intelligence/pipeline.py`, `argus/api/server.py`
  - Integrates: N/A
- Session 2: Cost Ceiling Enforcement + Classifier Guards
  - Creates: None
  - Modifies: `argus/intelligence/classifier.py`
  - Integrates: Session 1 (pipeline must be running for cost tracking to matter)
- Session 3: Source Hardening + Databento Warm-Up Fix
  - Creates: None
  - Modifies: `argus/intelligence/sources/sec_edgar.py`, `argus/intelligence/sources/finnhub.py`, `argus/intelligence/sources/fmp_news.py`, `argus/data/databento_data_service.py`
  - Integrates: N/A (independent fixes)

**Key Decisions:**
- DEC-319: `asyncio.wait_for()` 120s safety timeout wraps source gather — prevents single hanging source from blocking all polling forever
- DEC-320: Polling task `done_callback` + `app_state` reference — makes silent asyncio task death visible and prevents GC
- DEC-321: `get_symbols()` returns scanner watchlist, not full viable universe — 15 symbols vs 6,342 matches pipeline's cost model
- DEC-322: Explicit `sock_connect=10s` / `sock_read=20s` on all source HTTP clients — prevents DNS and silent-server hangs that `total` alone doesn't catch
- DEC-323: FMP news circuit breaker on 403 — first failure disables source for cycle, prevents 100+ wasted requests
- DEC-324: Cost ceiling enforcement wired into classifier — `daily_cost_ceiling_usd` checked before each Claude call, fallback to rule-based when exhausted
- DEC-325: `usage_tracker is not None` guards in classifier — prevents `AttributeError` when AI layer disabled
- DEC-326: Databento lazy warm-up `end` clamped to `now - 600s` — avoids 422 when historical API lags behind live stream
- DEC-327: Intelligence pipeline firehose architecture refactor deferred to Sprint 24 design — current per-symbol polling is architecturally wrong but functional with watchlist scoping

**Scope Boundaries:**
- IN: Bug fixes for pipeline resilience, cost enforcement, source timeouts, circuit breaker, warm-up clamping. Tests for all fixes. Revert live debug patches in favor of clean implementations.
- OUT: Pipeline architecture refactor (firehose model). Frontend changes. New features. Config schema changes.

**Regression Invariants:**
- All existing pytest tests pass (2,511 + new)
- All existing Vitest tests pass (435)
- Boot sequence completes all 12 steps without error
- Trading engine, strategies, orchestrator, order manager unaffected
- Pipeline starts cleanly when `catalyst.enabled: true`
- Pipeline skipped cleanly when `catalyst.enabled: false`
- Config-gated default-disabled behavior preserved

**File Scope:**
- Modify: `startup.py`, `pipeline.py`, `server.py`, `classifier.py`, `sec_edgar.py`, `finnhub.py`, `fmp_news.py`, `databento_data_service.py`
- Do not modify: `core/`, `strategies/`, `execution/`, `ui/`, `ai/` (except `classifier.py`), `backtest/`, `config/` (schema only — no Pydantic changes)

**Config Changes:**
No config changes. Existing fields (`max_batch_size`, `daily_cost_ceiling_usd`) are wired into code paths that weren't using them.

**Pre-existing test failure:** Config alignment test fails due to `system_live.yaml` modifications from the QA session (catalyst section added). Session 1 pre-flight must update the test fixture or account for this.

**Test Strategy:**
- ~5 new tests per session × 3 sessions = ~15 minimum new tests
- Session 1: polling task crash recovery, gather timeout, symbol scope (watchlist vs universe), empty watchlist fallback
- Session 2: cost ceiling enforcement, ceiling-reached fallback, usage_tracker=None path, cost logging
- Session 3: timeout config validation, FMP 403 circuit breaker, Databento end clamping, pre-market path unaffected

**Runner Compatibility:**
- Mode: Human-in-the-loop recommended (impromptu sprint, live debugging context)
- Parallelizable sessions: Session 3 can run parallel to Session 1 (no file overlap)
- Estimated token budget: ~45K per session
- Runner-specific escalation notes: If Session 1 fails to make the pipeline produce fetch activity, halt — the remaining sessions depend on a working poll loop

**Dependencies:**
- Sprint 23.5/23.6/23.7 code in place on `main`
- `system_live.yaml` with catalyst section added (from QA session)
- Live debug patches from QA session should be reverted before Session 1 begins (or Session 1 replaces them)

**Escalation Criteria:**
- Pipeline still hangs after Session 1 fixes → Tier 3 investigation of asyncio task scheduling
- Cost ceiling enforcement requires ClaudeClient interface changes → expand Session 2 scope
- Databento warm-up fix breaks pre-market boot path → rollback and investigate separately

**Doc Updates Needed:**
- `docs/decision-log.md`: DEC-319 through DEC-327
- `docs/dec-index.md`: 9 new entries
- `docs/sprint-history.md`: Sprint 23.8 entry with session details and test counts
- `docs/project-knowledge.md`: Update intelligence pipeline section, test counts, known issues
- `CLAUDE.md`: Update if startup behavior changes

**Artifacts to Generate:**
1. Sprint Spec (with Specification by Contradiction) ✅
2. Design Summary ✅
3. Implementation Prompt ×3
4. Review Prompt ×3
5. Review Context File
6. Escalation Criteria (in spec)
7. Regression Checklist (in review context)
8. Doc Update Checklist (in design summary)

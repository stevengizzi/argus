# Tier 2 Review: Sprint 23.8, Session 3

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-23.8-review-context.md`

## Tier 1 Close-Out Report
---BEGIN-CLOSE-OUT---

**Session:** Sprint 23.8 — Session 3: Source Hardening + Databento Warm-Up Fix
**Date:** 2026-03-12
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/intelligence/sources/fmp_news.py | modified | Circuit breaker: reset per cycle, skip remaining symbols after 403, log WARNING with skip count |
| argus/intelligence/sources/fmp_news.py | modified | Split 401/403 error handling — 403 gets distinct log message per spec |
| argus/intelligence/sources/fmp_news.py | modified | Added circuit breaker check between stock_news batches |
| argus/data/databento_data_service.py | modified | Clamp lazy warm-up `end` to `now - 600s` (DEC-326); skip if clamped end <= start |
| tests/intelligence/test_sources/test_sec_edgar.py | modified | +1 test: session timeout includes sock_connect=10, sock_read=20 |
| tests/intelligence/test_sources/test_finnhub.py | modified | +1 test: session timeout includes sock_connect=10, sock_read=20 |
| tests/intelligence/test_sources/test_fmp_news.py | modified | +3 tests: timeout, circuit breaker 403 skip, circuit breaker reset between cycles |
| tests/data/test_databento_data_service.py | modified | +3 tests: clamp end to now-600s, skip when clamped end < start, pre-market boot unaffected |

### Judgment Calls
- **Timeouts already present:** All three sources (sec_edgar, finnhub, fmp_news) already had `ClientTimeout(total=30.0, sock_connect=10.0, sock_read=20.0)` in their `start()` methods. No code changes needed for requirements 1–3 (timeout portion). Tests written to validate the existing behavior.
- **Circuit breaker scope within `_fetch_stock_news`:** Added a `_disabled_for_cycle` check between batches inside `_fetch_stock_news` so that if batch 1 returns 403, batch 2 is skipped. The spec focused on per-symbol skipping but batch-level skipping is the correct behavior for the batched endpoint.
- **`_HISTORICAL_LAG_BUFFER` as local constant:** Defined inside `_lazy_warmup_symbol` rather than as a module-level constant since it's only used in that one method.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| SEC Edgar: ClientTimeout(total=30, sock_connect=10, sock_read=20) | DONE | Already present at sec_edgar.py:94 |
| Finnhub: ClientTimeout(total=30, sock_connect=10, sock_read=20) | DONE | Already present at finnhub.py:84 |
| FMP News: ClientTimeout(total=30, sock_connect=10, sock_read=20) | DONE | Already present at fmp_news.py:82 |
| FMP News: circuit breaker first 403 sets flag | DONE | fmp_news.py:_make_request (line ~260) |
| FMP News: remaining symbols skipped after 403 | DONE | fmp_news.py:fetch_catalysts + _fetch_stock_news |
| FMP News: flag resets next cycle | DONE | fmp_news.py:fetch_catalysts resets at start |
| FMP News: ERROR log on first 403 | DONE | fmp_news.py:_make_request |
| FMP News: WARNING log with skip count | DONE | fmp_news.py:fetch_catalysts end |
| Databento: clamp end to now - 600s | DONE | databento_data_service.py:_lazy_warmup_symbol |
| Databento: skip if clamped end < start | DONE | databento_data_service.py:_lazy_warmup_symbol |
| Pre-market boot unaffected | DONE | No changes to _warm_up_indicators pre-market path |
| 7+ new tests | DONE | 8 new tests added |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| SEC Edgar source starts | PASS | start() logic unchanged, timeout already present |
| Finnhub source starts | PASS | start() logic unchanged, timeout already present |
| FMP news source starts (when enabled) | PASS | start() logic unchanged |
| Sources respect existing rate limits | PASS | Rate limit config untouched |
| Databento live streaming unaffected | PASS | Only lazy warm-up historical path modified |
| Pre-market boot skips warm-up | PASS | _warm_up_indicators pre-market path not modified; test confirms |
| No changes to data service public interface | PASS | Only internal _lazy_warmup_symbol modified |

### Test Results
- Tests run: 2,519 (2,486 excl. test_main.py pre-existing failures)
- Tests passed: 2,517 (2,486 excl. test_main.py)
- Tests failed: 2 (pre-existing in tests/test_main.py — confirmed by running on stashed clean state)
- New tests added: 8
- Command used: `python -m pytest tests/ -x -q -n auto`

### Unfinished Work
None

### Notes for Reviewer
- The 2 test failures in `tests/test_main.py` (`test_orchestrator_in_app_state`, `test_multiple_strategies_registered_with_orchestrator`) are pre-existing — confirmed by stashing all changes and running the same tests on the clean HEAD commit.
- The `docs/dec-index.md` and `docs/decision-log.md` diffs in `git status` are leftover uncommitted changes from Sessions 1–2 (DEC-327, DEC-328), not from this session.
- All three source timeouts were already correct before this session — the tests validate rather than implement them.

---END-CLOSE-OUT---

## Review Scope
- Diff to review: `git diff HEAD~1` (or the appropriate range for Session 3 commits)
- Test command: `python -m pytest tests/intelligence/sources/ tests/data/test_databento*.py -x -q`
- Files that should NOT have been modified: `startup.py`, `pipeline.py`, `server.py`, `classifier.py`, `storage.py`, `core/`, `strategies/`, `execution/`, `ui/`, `ai/`

## Session-Specific Review Focus
1. Verify all three source files use `ClientTimeout(total=30, sock_connect=10, sock_read=20)` — check that `sock_connect` and `sock_read` are explicit keyword arguments, not positional
2. Verify the FMP circuit breaker resets at the START of each `fetch_catalysts()` call — not in `__init__` or `start()`, which would only reset once
3. Verify the FMP circuit breaker activates on HTTP 403 specifically — not on all HTTP errors (a 500 or timeout should NOT trigger the circuit breaker, those are transient)
4. Verify the circuit breaker logs ERROR on the first 403 and WARNING with a skip count at cycle end — not the other way around
5. Verify the Databento `end` clamp uses `timedelta(seconds=600)` — not minutes, not a magic number without a comment referencing DEC-326
6. Verify the clamp ONLY applies to the mid-session lazy warm-up path — check that the pre-market boot path (DEC-316 skip) is completely unmodified
7. Verify that when clamped `end < start`, the warm-up is skipped gracefully (not errored) with a DEBUG-level log
8. Verify no changes to the Databento live streaming connection or the ALL_SYMBOLS subscription
9. Verify source rate limit configurations are unchanged — `sec_edgar.rate_limit_per_second`, `finnhub.rate_limit_per_minute` should be untouched
10. Verify no source fetch logic was changed — the same endpoints are called with the same parameters, only timeout and error handling changed

## Additional Context
The timeout changes address a real hang observed during QA: the polling loop entered and never produced output. The `asyncio.wait_for(120)` added in Session 1 is the safety net; the `sock_connect`/`sock_read` timeouts in this session are the precision fix. Together they provide defense-in-depth — individual requests timeout at 30s max, and the entire gather times out at 120s if something unexpected happens.

The FMP circuit breaker addresses 100+ wasted 403 requests observed in the QA log. The FMP news source is currently disabled in `system_live.yaml` (Starter plan doesn't include news endpoints), but the circuit breaker should work correctly for when/if the plan is upgraded.

The Databento warm-up fix addresses ~15 consecutive 422 errors observed during a mid-session boot. The historical API lags ~10 minutes behind the live stream. The 600s buffer is conservative. If Databento reduces their lag in the future, the buffer just means warm-up data ends a few minutes earlier — not a correctness issue, just slightly less warm-up data.

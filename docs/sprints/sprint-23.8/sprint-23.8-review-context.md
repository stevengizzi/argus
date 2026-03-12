# Sprint 23.8 Review Context

This file contains shared context for all Tier 2 review sessions in Sprint 23.8.

## Sprint Spec Reference
See `docs/sprints/sprint-23.8-spec.md` for full spec and specification by contradiction.

## Sprint-Level Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | All existing pytest tests pass | `python -m pytest tests/ -x -q` — expect 2,511+ passing (plus new tests from this sprint) |
| 2 | All existing Vitest tests pass | `cd argus/ui && npx vitest run` — expect 435 passing |
| 3 | Boot sequence completes 12 steps | `grep "ARGUS TRADING SYSTEM — RUNNING" logs/argus_*.log` after fresh start |
| 4 | Pipeline starts when enabled | `grep "Intelligence pipeline created" logs/argus_*.log` shows source count |
| 5 | Pipeline skipped when disabled | Set `catalyst.enabled: false`, boot, verify "Intelligence pipeline disabled" in log |
| 6 | No trading engine files modified | `git diff --name-only` shows no files in `core/`, `strategies/`, `execution/` (except test files) |
| 7 | No frontend files modified | `git diff --name-only` shows no files in `argus/ui/` |
| 8 | No config schema changes | `git diff argus/intelligence/config.py` shows no Pydantic model field additions/removals |
| 9 | Event Bus publishing contract preserved | `grep "publish" argus/intelligence/pipeline.py` — same signature and event type |
| 10 | catalyst.db schema unchanged | `git diff` shows no changes to table creation in `storage.py` |

## Sprint-Level Escalation Criteria

Escalate to Tier 3 (human review) if ANY of these are true:

1. **Pipeline still non-functional after Session 1:** The polling loop should produce fetch activity with 15 symbols. If it still hangs or crashes, the root cause is deeper than what was diagnosed.
2. **Cost ceiling requires ClaudeClient changes:** If enforcing the daily ceiling needs modifications to `ai/claude_client.py` or the shared AI layer, the scope has expanded beyond intelligence pipeline files.
3. **Databento warm-up fix breaks pre-market boot:** The pre-market path (skip warm-up entirely) must remain unaffected. If the clamping logic introduces a regression in the pre-market code path, rollback Session 3's warm-up changes.
4. **Test count drops:** If any existing test starts failing due to these changes (beyond the known `system_live.yaml` config alignment pre-existing failure), escalate.
5. **More than 8 files modified:** This sprint should touch exactly 8 files (plus test files). If scope creep causes modifications to additional production files, escalate.

## QA Session Findings (Full Reference)

These findings were discovered during the March 12, 2026 live QA session. Sprint 23.8 addresses findings #1–10. Findings #7, #8, #11 are deferred.

| # | Finding | Severity | Sprint 23.8 Session |
|---|---------|----------|-------------------|
| 1 | Cost ceiling not enforced — 336 Claude calls with zero tracking | CRITICAL | Session 2 |
| 2 | Polling loop silent death — no done_callback, no health monitoring | CRITICAL | Session 1 |
| 3 | `get_symbols()` returned full universe (6,342) instead of watchlist (15) | CRITICAL | Session 1 |
| 4 | `asyncio.gather()` had no timeout — hanging source blocked all polling | HIGH | Session 1 |
| 5 | HTTP source timeouts missing `sock_connect`/`sock_read` | HIGH | Session 3 |
| 6 | FMP news 403 spam — no circuit breaker after first auth failure | HIGH | Session 3 |
| 7 | Frontend catalyst 503 spam — no short-circuit when pipeline disabled | MEDIUM | Deferred → Sprint 23.9 (DEF-041) |
| 8 | Databento lazy warm-up 422 — `end` timestamp needs ~10min clamp | MEDIUM | Session 3 |
| 9 | `classifier.py` usage_tracker None guard missing | MEDIUM | Session 2 |
| 10 | `/debrief/briefings` still returning 503 | LOW | Deferred → Sprint 23.9 (DEF-043) |

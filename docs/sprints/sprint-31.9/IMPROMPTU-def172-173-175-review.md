# IMPROMPTU-def172-173-175 — Tier 2 Review Report

> Tier 2 review produced per `workflow/claude/skills/review.md`. Paste the
> fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-REVIEW---

**Session:** sprint-31.9 / IMPROMPTU-def172-173-175 (between Stage 2 and Stage 3)
**Date:** 2026-04-22
**Tier 2 Verdict:** CLEAR

## Scope compliance — PASS

- Modified: `CLAUDE.md`, `argus/api/server.py`, `docs/roadmap.md`, `docs/sprints/sprint-31.9/RUNNING-REGISTER.md`
- Added: `tests/api/test_init_learning_loop.py`, `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`, `docs/sprints/sprint-31.9/IMPROMPTU-def172-173-175-closeout.md` + this review
- Nothing outside declared scope touched.

## DEF-173 correctness — PASS

- `argus/api/server.py:460-465` — `await learning_store.enforce_retention(ll_config.report_retention_days)` immediately after `learning_store.initialize()` (line 453), wrapped in try/except with `logger.warning(..., exc_info=True)`.
- Test asserts `fake_store.enforce_retention.assert_awaited_once_with(90)` and does NOT re-test SQL semantics.
- Test passes in isolation (`0.02s`).

## DEF-172 verification — PASS on all 4 invariants

1. `main.py` — try/except around `await self._catalyst_storage.close()` in shutdown step 5a ✓
2. `argus/intelligence/startup.py:245` — `await components.storage.close()` in `shutdown_intelligence` ✓
3. `argus/api/server.py:257-259` — `await shutdown_intelligence(intelligence_components)` in teardown ✓
4. `argus/intelligence/storage.py:143` — `PRAGMA journal_mode = WAL` ✓

## DISCOVERY.md accuracy — PASS (3 claims spot-checked)

- `self._catalyst_storage` construction at `main.py:1011` ✓ (exact line match)
- `_LIFESPAN_PHASES` registry in `argus/api/server.py` with 11 `_init_*` phases ✓
- `SetupQualityEngine.__init__` holds `self._config` and `self._db` only ✓ (read-only property accessors are harmless)

## CLAUDE.md strikethrough pattern — PASS

- DEF-172: `| ~~DEF-172~~ | ~~...~~ | — | **RESOLVED-VERIFIED** (IMPROMPTU 2026-04-22). ...`
- DEF-173: `| ~~DEF-173~~ | ~~...~~ | — | **RESOLVED** (IMPROMPTU 2026-04-22). ...`
- DEF-174 and DEF-175: no strikethrough, as required.

## DEF-175 cross-references — PASS

- CLAUDE.md: 3 hits
- RUNNING-REGISTER.md: 5 hits
- docs/roadmap.md: 1 hit
- DISCOVERY.md: 2 hits

All 4 expected files reference DEF-175.

## Running register updated correctly — PASS

- DEF-172 and DEF-173 appear in "Resolved this campaign" table.
- DEF-175 appears in "Open with planned owner" table.
- The "Open with NO NATURAL OWNER" section is GONE (no longer a gap).
- IMPROMPTU row present in Session history.
- Stage status table includes IMPROMPTU row between Stage 2 Pass 3 and Stage 3.
- Stage-3 decision point about handling DEF-172/173 struck through (retained for trail).

## Test suite — PASS

- **4,965 passed, 0 failed in 150.12s** (baseline 4,964 + 1 new regression test).
- No flakes from DEF-150 / DEF-163 / DEF-171 surfaced in this run.

## Additional observations

- DEF-173 CLAUDE.md entry correctly notes the wiring is interim — the call will migrate to `main.py` as part of DEF-175 scope. Good scope-discipline telegraphing.
- DEF-175 description in CLAUDE.md correctly characterizes it as "no active runtime harm today" (correct — WAL handles the concurrency; SetupQualityEngine is stateless).
- Running register's `(pending)` commit IDs on the IMPROMPTU row are expected at review time; operator finalizes on commit.

---END-REVIEW---
```

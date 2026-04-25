# TEST-HYGIENE-01 Close-Out — pytest Date-Decay Fix (DEF-205)

> **Session:** TEST-HYGIENE-01 (Sprint 31.9, Stage 9C)
> **Date:** 2026-04-24
> **Baseline commit (pre-session):** `6583216` (IMPROMPTU-09 post-session register cleanup)
> **Session commit:** *pending this commit*
> **Verdict (self-assessment):** **CLEAN** — mechanical 2-helper conversion, no production code touched, no scope creep, +12 pytest restoring pre-tipping-point baseline.
> **Context state:** GREEN — no compaction; small focused session.

## 1 — Scope

DEF-205 — 12 pytest failures from hardcoded `2026-03-25T10:00:00` seeds
in two test helper functions falling outside `compute_filter_accuracy()`'s
rolling 30-day default window now that today is 2026-04-24. Sibling of
DEF-167 (Vitest counterpart, resolved in FIX-13a — same fix pattern
applied here).

## 2 — Aggregate Result

| Test File | Failures Pre | Failures Post |
|-----------|--------------|---------------|
| `tests/intelligence/test_filter_accuracy.py` | 11 | 0 |
| `tests/api/test_counterfactual_api.py` | 1 | 0 |
| **Total** | **12** | **0** |

Full suite: **5,068 pass + 12 fail → 5,080 pass + 0 fail** (+12, back to
pre-tipping-point baseline reported on 2026-04-23 post-IMPROMPTU-10 seal).

## 3 — Change Manifest

**Files modified (5):**

1. `tests/intelligence/test_filter_accuracy.py` (`:26-44`) — `_seed_position()` defaults `opened_at`/`closed_at` changed from hardcoded `"2026-03-25T..."` strings to `None`; resolved at call time from `(datetime.now() - timedelta(days=5)).replace(microsecond=0)` with `closed_at = opened_at + 30min`. `datetime`/`timedelta` were already imported (line 13).

2. `tests/api/test_counterfactual_api.py` — three edits:
   - `:11` — added `from datetime import datetime, timedelta` import.
   - `:57-63` — added new module-level `_seed_anchor()` helper returning `(datetime.now() - timedelta(days=5)).replace(microsecond=0)`. Centralized so test code that needs the same anchor (below) doesn't recompute `datetime.now()` on its own line and risk a 1-second drift.
   - `:65-100` — `_seed_cf_position()` accepts new optional `opened_at`/`closed_at` parameters; defaults resolved from `_seed_anchor()`.
   - `:243-272` — `test_date_range_filter` now derives `date_from`/`date_to` from `_seed_anchor().date()` so it continues to bracket the seeded position regardless of wall-clock date.

3. `CLAUDE.md` — DEF-205 row updated to strikethrough + RESOLVED context (TEST-HYGIENE-01, 2026-04-24).

4. `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — Last-updated header rewritten; Stage 9C row → ✅ COMPLETE; TEST-HYGIENE-01 session-history row updated; DEF-205 row moved from "Open with planned owner" to "Resolved this campaign"; baseline progression line extended to record the 5,068 → 5,080 restoration.

5. `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — Stage 9C TEST-HYGIENE-01 row → ✅ CLEAR with date 2026-04-24; post-Apr-24 DEF-205 row strikethrough.

**Files added (1):**

- `docs/sprints/sprint-31.9/TEST-HYGIENE-01-closeout.md` (this file).
- `docs/sprints/sprint-31.9/TEST-HYGIENE-01-review.md` (Tier 2, to be written after close-out).

**Files NOT modified (per kickoff constraints):**

- Any `argus/` source file — `git diff argus/` empty.
- Any `config/` file — `git diff config/` empty.
- Any test file other than the two named in the kickoff — `git diff tests/` shows only the two target files.
- `tests/intelligence/test_filter_accuracy.py:284-285` (assertion-target dates `"2026-03-25T..."`) — preserved per kickoff Requirement 4. The enclosing test (`test_only_positions_in_range_included`) passes explicit `start_date=datetime(2026, 3, 20)` and `end_date=datetime(2026, 3, 26)` to `compute_filter_accuracy`, so the date literals are part of the assertion target itself, not a seed.
- `workflow/` submodule — Universal RULE-018 respected.
- Audit doc back-annotations — out of scope.

## 4 — Judgment Calls

- **Default-resolve at call time, not at import.** Used `opened_at: str | None = None` with an `if opened_at is None: ...` resolution inside the helper body, instead of evaluating `datetime.now()` in the parameter-default expression. Default expressions evaluate once at module import; using `None` and resolving inside the body means each call gets a fresh anchor relative to the actual wall clock. This matters because pytest sessions can run for >5 seconds and the test suite imports test modules well before any single test executes.

- **5-day offset, not 0 or 1.** Picked `timedelta(days=5)` so the seeded `opened_at` lands comfortably within `compute_filter_accuracy()`'s default 30-day window without sitting on the boundary. `0` (today) was rejected because the kickoff explicitly warns against it ("some tests assert the seed is older than a threshold, and `0` would make those false-pass"). `30` would have sat on the boundary; `5` is well inside.

- **`closed_at = opened_at + 30min`, not a fixed string.** Preserved the prior 30-minute span between `opened_at` and `closed_at` so the seeded position has the same shape (open then close 30 minutes later) the original tests intended. The duration field on the INSERT is hardcoded to 1800.0 anyway, so this preservation is for shape consistency, not duration arithmetic.

- **Module-level `_seed_anchor()` helper in test_counterfactual_api.py.** Extracted the anchor computation to a module-level function so `test_date_range_filter` (which needs to pass the same anchor's date as a query parameter) can call it without recomputing `datetime.now()` on its own line. Reduces drift risk: if the test's `datetime.now()` resolves on a different second than the helper's `datetime.now()`, the date arithmetic could in principle land in different days near midnight. Centralizing eliminates the race entirely.

- **`test_only_positions_in_range_included` left untouched.** This test passes hardcoded literals on lines 278-279 and 284-285 *and* explicit `start_date=datetime(2026, 3, 20)` / `end_date=datetime(2026, 3, 26)` arguments. The hardcoded literals are not seeds against a rolling window — they are matched assertion targets against an explicit window. The test passes today and will continue to pass forever. Modifying it would be over-correction (kickoff Requirement 4).

- **No regression test added.** Kickoff Requirement 5 is "optional but encouraged." The grep-guard pattern proposed (regex over the test file) would have to be tuned carefully to not flag the still-present hardcoded dates in `test_only_positions_in_range_included` (which are intentional assertion targets), and the false-positive risk outweighs the marginal protection — DEF-205 is a once-per-year date-decay event with low recurrence probability. The kickoff's `Test Targets` section accepts +12 as a valid delta. Skipped to keep the diff tight.

## 5 — Verification Steps Run

```bash
# 1. Pre-session: confirmed baseline
$ python -m pytest tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py -q
12 failed, 17 passed in 4.96s

# 2. Post-fix targeted run (matches kickoff Requirement 2)
$ python -m pytest tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py -q
29 passed in 5.30s

# 3. Post-fix full suite (matches kickoff Requirement 3)
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5080 passed, 25 warnings in 56.86s
```

5,080 passed matches the pre-tipping-point baseline reported in
`RUNNING-REGISTER.md` as of post-IMPROMPTU-10 seal (2026-04-23).

## 6 — Scope Verification

Kickoff §Constraints checklist:

- ✅ DID NOT modify any production code (`git diff argus/` empty).
- ✅ DID NOT modify configs (`git diff config/` empty).
- ✅ DID NOT modify other test files (`git diff tests/` shows only the two target files).
- ✅ DID NOT modify `workflow/` submodule.
- ✅ DID NOT introduce new dependencies (`datetime`/`timedelta` are stdlib).
- ✅ Worked on `main`.

Kickoff §Regression Checklist:

| Check | How Verified | Result |
|-------|--------------|--------|
| All 12 failures resolved | Targeted pytest run | ✅ 0 fail |
| Full suite back to clean baseline | Full pytest run | ✅ 5,080 pass |
| No new failures introduced | Test count delta | ✅ +12 (5,068 → 5,080) |
| No production code modified | `git diff argus/` | ✅ empty |
| No config modified | `git diff config/` | ✅ empty |
| Only test files + docs modified | `git diff --name-only` | ✅ 5 files (2 tests + 3 docs) |
| DEF-205 strikethrough in CLAUDE.md | grep `~~DEF-205~~` | ✅ present |

## 7 — DEF Transitions

- **DEF-205 — RESOLVED.** Strikethrough applied in CLAUDE.md (line 433) and CAMPAIGN-COMPLETENESS-TRACKER.md (line 236); moved into the "Resolved this campaign" table in RUNNING-REGISTER.md.

No new DEFs opened. No other DEFs touched.

## 8 — Test Baseline Update

Pytest: **5,068 pass + 12 fail → 5,080 pass + 0 fail**, back to
pre-tipping-point baseline (post-IMPROMPTU-10).

Vitest: 866 (unchanged — frontend not touched).

`test_main.py` baseline tracked separately: 39 pass / 5 skip (unchanged).

## 9 — Next Step

SPRINT-CLOSE — last remaining session in Sprint 31.9.

## 10 — Tier 2 Review Profile

Standard. The session-specific focus items in the kickoff §Tier 2 Review:

1. Verify each date conversion preserves assertion semantics — applies to both helpers. Reviewer should confirm the `timedelta(days=5)` offset lands within `compute_filter_accuracy()`'s default 30-day window and outside any boundary the failing tests asserted against.
2. Verify no over-correction — `test_only_positions_in_range_included` still has hardcoded `2026-03-25` / `2026-03-01` literals because those are explicit assertion targets, not seeds. Reviewer should confirm.
3. Verify no scope creep — diff touches 5 files (2 tests + CLAUDE.md + RUNNING-REGISTER.md + CAMPAIGN-COMPLETENESS-TRACKER.md + this closeout). The kickoff cap was ≤5 modified files plus the closeout.
4. Verify regression test (if added) — not added; documented in §4 judgment-calls.

Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
Expected: `5080 passed`.

## 11 — Operator Handoff

`TEST-HYGIENE-01 complete. 12 dates converted (2 helper functions, 1 test query-param block). Test suite: 5,068 → 5,080 (DEF-205 closed). Commit: <pending>.`

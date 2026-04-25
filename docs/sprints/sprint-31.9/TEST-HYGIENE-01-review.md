# TEST-HYGIENE-01 — Tier 2 Review

**Reviewer:** @reviewer subagent (Tier 2, read-only)
**Review date:** 2026-04-24
**Commits under review:** `6f6a72b` (fix) + `1f9f61c` (SHA backfill) on `main`
**Diff range:** `6583216..1f9f61c`
**CI run cited:** *not yet cited in close-out (operator handoff item)*
**Close-out read:** `docs/sprints/sprint-31.9/TEST-HYGIENE-01-closeout.md` (CLEAN self-assessment)

---BEGIN-REVIEW---

## Summary

TEST-HYGIENE-01 closes DEF-205 (12 pytest failures from hardcoded
`2026-03-25T10:00:00` seeds in two test helpers falling outside
`compute_filter_accuracy()`'s rolling 30-day default window). The fix is
mechanical: `_seed_position()` and `_seed_cf_position()` now default
`opened_at` / `closed_at` to `None` and resolve them at call time from
`(datetime.now() - timedelta(days=5)).replace(microsecond=0)`. A new
module-level `_seed_anchor()` helper in `test_counterfactual_api.py`
centralizes the anchor so `test_date_range_filter` can derive its
`date_from` / `date_to` query params from the same reference and continue
to bracket the seed correctly.

The diff is precisely scoped: 6 files total (2 tests + CLAUDE.md +
RUNNING-REGISTER + CAMPAIGN-COMPLETENESS-TRACKER + new closeout). Zero
production code touched (`git diff argus/` empty). Zero config touched
(`git diff config/` empty). Zero workflow touched (`git diff workflow/`
empty). The hardcoded `2026-03-25` / `2026-03-01` literals at
`tests/intelligence/test_filter_accuracy.py:285-286,291-292` are
correctly preserved — they are explicit assertion targets paired with
explicit `start_date=datetime(2026, 3, 20)` / `end_date=datetime(2026, 3, 26)`
arguments to `compute_filter_accuracy`, not seeds. Full pytest suite green
at **5,080 passed** (+12 vs pre-session baseline of 5,068; back to
pre-tipping-point baseline post-IMPROMPTU-10 seal).

**Verdict: CLEAR.**

## Session-specific review focus (kickoff §"Session-Specific Review Focus")

### Check 1 — Each date conversion preserves assertion semantics

Read both helpers carefully:

- `tests/intelligence/test_filter_accuracy.py:26-69` — `_seed_position()`:
  signature changed from `opened_at: str = "2026-03-25T10:00:00"` /
  `closed_at: str = "2026-03-25T10:30:00"` to `... | None = None`. Body
  resolves `None` defaults to `(datetime.now() - timedelta(days=5)).replace(microsecond=0).isoformat()`
  for `opened_at` and `(anchor + timedelta(minutes=30)).isoformat()` for
  `closed_at`. The 23-column INSERT shape, parameter binding order, and
  all other column values are unchanged. Call sites in
  `TestCorrectRejection`, `TestIncorrectRejection`, `TestByStage`, etc.
  pass no `opened_at` / `closed_at` (they relied on the previous default),
  so the new default-resolution path runs and the seed lands at
  `now - 5 days`. `compute_filter_accuracy()` (default window:
  `[now_et - 30d, now_et]`) at `argus/intelligence/filter_accuracy.py:202-205`
  contains the seed. The 5-day offset sits comfortably inside the 30-day
  window with ~25 days of margin on each side, well clear of any boundary.

- `tests/api/test_counterfactual_api.py:65-100` — `_seed_cf_position()`:
  same pattern. Signature gains `opened_at: str | None = None` /
  `closed_at: str | None = None` parameters; defaults resolve via
  `_seed_anchor()`. INSERT shape and binding order unchanged.

- `tests/api/test_counterfactual_api.py:268-292` — `test_date_range_filter`:
  query params `date_from` / `date_to` rebuilt from
  `_seed_anchor().date()` and `seed_day + timedelta(days=1)`. The
  inclusion window `[seed_day T00:00:00, seed_day T23:59:59]` brackets a
  position whose `opened_at` is `~10:xx:xx` of `seed_day`; the exclusion
  window `[next_day T00:00:00, +∞)` correctly excludes it. Bracket
  semantics preserved exactly.

The implementation uses `datetime.now(_ET)` while the seed uses naive
`datetime.now()`. Both reference the same wall clock, so the comparison
is consistent within ~5 hours of timezone offset — far less than the
5-day buffer chosen.

**Status: CLEAR.** All conversions preserve assertion semantics with ample
margin against the rolling-window boundary.

### Check 2 — No over-correction

Post-fix grep for hardcoded March 2026 dates in the two test files:

```
$ grep -n "2026-03-2[0-9]\|2026-03-1[0-9]" tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py
tests/intelligence/test_filter_accuracy.py:285:            opened_at="2026-03-01T10:00:00",
tests/intelligence/test_filter_accuracy.py:286:            closed_at="2026-03-01T10:30:00",
tests/intelligence/test_filter_accuracy.py:291:            opened_at="2026-03-25T10:00:00",
tests/intelligence/test_filter_accuracy.py:292:            closed_at="2026-03-25T10:30:00",
```

These four lines live in `test_only_positions_in_range_included` (lines
278-302). The test passes:

```python
start = datetime(2026, 3, 20)
end = datetime(2026, 3, 26)
report = await compute_filter_accuracy(
    store, start_date=start, end_date=end, min_sample_count=1,
)
assert report.total_positions == 1
assert report.by_stage[0].incorrect_rejections == 1
```

The `2026-03-01` seed is intentionally outside `[2026-03-20, 2026-03-26]`
and the `2026-03-25` seed is intentionally inside. Both windows and both
seeds are explicit assertion targets — converting them to dynamic dates
would invalidate the test (which checks "positions outside the date
range are excluded"). Correctly preserved per kickoff Requirement 4.

**Status: CLEAR.** No over-correction. The four preserved hardcoded dates
are exactly the ones the kickoff identified as off-limits.

### Check 3 — No scope creep

Diff scope:

```
$ git diff 6583216..1f9f61c --stat
 CLAUDE.md                                          |   2 +-
 docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md   |   4 +-
 docs/sprints/sprint-31.9/RUNNING-REGISTER.md       |  13 +-
 docs/sprints/sprint-31.9/TEST-HYGIENE-01-closeout.md | 150 ++++++ (new)
 tests/api/test_counterfactual_api.py               |  33 ++++-
 tests/intelligence/test_filter_accuracy.py         |  11 +-
```

- `argus/`: empty. No production code modified.
- `config/`: empty. No config modified.
- `workflow/`: empty. Submodule respected (Universal RULE-018).
- Test files: only the two named in the kickoff. No other test files
  modified.
- Other DEFs: not touched. CLAUDE.md change is a single row (DEF-205)
  strikethrough plus the resolution context block; no other DEF rows
  modified.
- Audit docs: not touched.

Test code-line delta: 37 insertions / 7 deletions across 2 files. This
exceeds the kickoff's "12-15 lines" threshold but the additional volume
is fully justified by two judgment calls in close-out §4:

1. Default-resolve at call time (not at parameter-default expression
   evaluation) — adds ~6 lines per helper but is a Python correctness
   requirement (parameter defaults evaluate once at module import; using
   `None` and resolving inside the body ensures each call gets a fresh
   anchor relative to the actual wall clock).

2. Module-level `_seed_anchor()` helper in `test_counterfactual_api.py`
   — adds ~9 lines but eliminates a midnight-race hazard where two
   independent `datetime.now()` calls in the same test could resolve to
   different dates if the test happens to straddle midnight.

Both are correct engineering with clear rationale. No actual scope creep
(no extra files, no extra DEFs, no production changes).

**Status: CLEAR.** Diff is mechanical and within stated scope.

### Check 4 — Regression test decision

Close-out §4 explicitly skips the optional regression test from kickoff
Requirement 5. Stated rationale:

> The grep-guard pattern proposed (regex over the test file) would have
> to be tuned carefully to not flag the still-present hardcoded dates in
> `test_only_positions_in_range_included` (which are intentional
> assertion targets), and the false-positive risk outweighs the marginal
> protection — DEF-205 is a once-per-year date-decay event with low
> recurrence probability.

This is a reasonable trade-off. Any grep guard against `2026-03-2[0-9]`
in these two files would either (a) exclude exactly the four lines that
must be preserved (requiring a fragile pin to line numbers or an
`ALLOW: assertion target` comment guard), or (b) be too broad and
false-positive on every refactor of `test_only_positions_in_range_included`.
DEF-205 is also a one-shot, calendar-driven event — the failure surfaced
when "today" crossed `2026-04-24` (i.e., 30+ days after `2026-03-25`),
and the converted dynamic seed will track the calendar forever. The
recurrence path requires someone to revert the dynamic seeds back to
hardcoded literals, which is a deliberate act, not an accident. Skipping
the optional regression guard is the right call.

**Status: CLEAR.** The skip is well-reasoned and documented.

## Scope verification

| Boundary | Verified | Result |
|----------|----------|--------|
| `git diff argus/` | empty | ✅ |
| `git diff config/` | empty | ✅ |
| `git diff workflow/` | empty | ✅ |
| Other test files modified | none | ✅ |
| Other DEFs touched | none | ✅ |
| `audit-2026-04-21/` modified | not present in diff | ✅ |
| Hardcoded dates preserved at L285-286, L291-292 | grep confirmed | ✅ |
| New dependencies | none (`datetime`/`timedelta` are stdlib) | ✅ |

## Test command + result

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5080 passed, 25 warnings in 57.24s
```

**5,080 passed, 0 failed** — exactly the expected post-session baseline
(5,068 + 12 = 5,080). Test delta `+12` matches kickoff §Test Targets and
close-out §2/§8.

Warning count 25 sits inside the DEF-192 documented `[25, 31]`
xdist-variance band; no new warning category introduced.

## Cross-checks

### Close-out §3 change manifest vs git stat

| Close-out Claim | Git Stat | Match? |
|-----------------|----------|--------|
| `tests/intelligence/test_filter_accuracy.py` modified | 11 lines (9 ins / 2 del) | ✅ |
| `tests/api/test_counterfactual_api.py` modified (3 sub-edits) | 33 lines (28 ins / 5 del) | ✅ |
| `CLAUDE.md` DEF-205 strikethrough | 2 lines | ✅ |
| `RUNNING-REGISTER.md` updated | 13 lines | ✅ |
| `CAMPAIGN-COMPLETENESS-TRACKER.md` updated | 4 lines | ✅ |
| `TEST-HYGIENE-01-closeout.md` added | 150 lines (new) | ✅ |

All claims match.

### Close-out §6 regression checklist vs actual diff state

| Check | Close-out Says | Reviewer Verifies |
|-------|----------------|-------------------|
| All 12 failures resolved | ✅ 0 fail | ✅ confirmed via full suite (5,080 pass) |
| Full suite back to clean baseline | ✅ 5,080 pass | ✅ confirmed |
| No new failures introduced | ✅ +12 (5,068 → 5,080) | ✅ confirmed |
| No production code modified | ✅ empty | ✅ `git diff argus/` empty |
| No config modified | ✅ empty | ✅ `git diff config/` empty |
| Only test files + docs modified | ✅ 5 files (2 tests + 3 docs) | ✅ 6 paths total (incl. new closeout) |
| DEF-205 strikethrough in CLAUDE.md | ✅ present | ✅ confirmed at line 433 |

All checks reconcile.

### DEF-205 transition

CLAUDE.md row updated:

```
-| DEF-205 | **Date-decay test failures (pytest sibling of DEF-167).** ...
+| ~~DEF-205~~ | ~~**Date-decay test failures (pytest sibling of DEF-167).**~~ | — | **RESOLVED** (TEST-HYGIENE-01, 2026-04-24). ...
```

Strikethrough applied per `.claude/rules/doc-updates.md` § Numbering Hygiene
("Resolved DEFs use ~~strikethrough~~ in CLAUDE.md's DEF table"). Resolution
context block documents the helper functions, the 5-day offset rationale,
the `test_only_positions_in_range_included` preservation, and the
`test_date_range_filter` query-param update. No DEC entries
created/modified (none warranted; this is mechanical test hygiene).

**Status: CLEAR.**

## Findings

None. Verdict CLEAR.

## Sign-off

TEST-HYGIENE-01 is a textbook mechanical test-hygiene fix. The diff is
small, surgical, and well-justified. The close-out's CLEAN
self-assessment is accurate. Ready for SPRINT-CLOSE.

**CI verification (Universal RULE-050):** the close-out does not yet
cite a green CI run link. Operator handoff item — confirm green CI on
`1f9f61c` before treating the session as fully complete. Local pytest
(`5,080 passed`) is consistent with that expectation but does not
substitute for CI.

---END-REVIEW---

```json:structured-verdict
{
  "session_id": "TEST-HYGIENE-01",
  "sprint": "31.9",
  "stage": "9C",
  "verdict": "CLEAR",
  "commits_reviewed": ["6f6a72b", "1f9f61c"],
  "diff_range": "6583216..1f9f61c",
  "files_changed": 6,
  "production_code_touched": false,
  "config_touched": false,
  "workflow_touched": false,
  "test_count_pre": 5068,
  "test_count_post": 5080,
  "test_count_delta": 12,
  "expected_delta": 12,
  "delta_matches_expected": true,
  "warnings_count": 25,
  "warnings_in_def192_band": true,
  "defs_resolved": ["DEF-205"],
  "defs_opened": [],
  "defs_other_touched": [],
  "decs_added": [],
  "escalation_triggered": false,
  "escalation_reasons": [],
  "ci_link_cited_in_closeout": false,
  "ci_link_pending": "operator handoff item",
  "session_specific_focus_checks": {
    "1_assertion_semantics_preserved": "CLEAR",
    "2_no_over_correction": "CLEAR",
    "3_no_scope_creep": "CLEAR",
    "4_regression_test_decision": "CLEAR (skip well-reasoned)"
  },
  "findings": [],
  "context_state": "GREEN"
}
```

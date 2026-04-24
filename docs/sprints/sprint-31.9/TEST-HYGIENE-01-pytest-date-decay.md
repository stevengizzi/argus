# Sprint 31.9 TEST-HYGIENE-01: pytest Date-Decay Fix (DEF-205)

> Drafted post-IMPROMPTU-11. Paste into a fresh Claude Code session.
> Mechanical fix session — convert hardcoded date seeds to dynamic patterns.

## Scope

**Finding addressed:** DEF-205 — 12 pytest failures from hardcoded date seeds
that have crossed the rolling 30-day window. Sibling of DEF-167 (Vitest
counterpart, resolved in FIX-13a). Pure mechanical conversion, no design
decisions.

**Affected sites (12 total):**
- `tests/intelligence/test_filter_accuracy.py` — 11 failures, primary seed at
  line 36 (`opened_at: str = "2026-03-25T10:00:00"`)
- `tests/api/test_counterfactual_api.py::TestCounterfactualAccuracyEndpoint::test_returns_200_with_data` — 1 failure (likely shares the same seed pattern; verify)

**Fix pattern (from FIX-13a precedent):**
- Replace hardcoded ISO-8601 strings with `(datetime.now() - timedelta(days=N)).isoformat()` where `N` is chosen so the seed lands within the assertion's expected window
- Replace hardcoded `date.today()` references with `datetime.now().date()` if any exist
- For tests asserting "this happened N days ago," use `timedelta(days=N)` arithmetic from `datetime.now()`

**Files touched:**
- `tests/intelligence/test_filter_accuracy.py` (test file)
- `tests/api/test_counterfactual_api.py` (test file — investigate which test method needs the fix)
- `CLAUDE.md` — DEF-205 strikethrough with commit SHA
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — DEF-205 moved to Resolved
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — Stage 9C TEST-HYGIENE-01 row → CLEAR

**Safety tag:** `safe-during-trading`. Test-file changes; no production code.

## Pre-Session Verification (REQUIRED)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Expected: 5,068 passed, 12 failed (DEF-205 baseline)
```

### 3. Branch & workspace

```bash
git checkout main && git pull --ff-only
git status  # Expected: clean
```

### 4. Reference precedent

Read `docs/sprints/sprint-31.9/FIX-13a-*.md` (or whatever resolved DEF-167) to
confirm the dynamic-date pattern that was used for the Vitest fix. Apply the
same pattern to pytest.

## Diagnostic Phase

### 1. Identify all date-decay sites

```bash
# Primary seed
grep -n "2026-03-25\|2026-03-2[0-9]\|2026-03-1[0-9]" tests/intelligence/test_filter_accuracy.py
grep -n "2026-03-25\|2026-03-2[0-9]\|2026-03-1[0-9]" tests/api/test_counterfactual_api.py

# Wider scan in case other test files have the same pattern (out of scope unless they're failing)
grep -rn "2026-03-25" tests/ --include="*.py"
```

### 2. Read each failing test

For each of the 12 failures, identify:
- The hardcoded date(s) feeding the test
- The assertion semantics (e.g., "this should be within last 30 days")
- The dynamic equivalent

### 3. Check for shared fixtures

If multiple tests share a fixture that defines the date seed, fix the fixture
once rather than each test individually.

## Fix Phase

### Requirement 1: Convert hardcoded dates to dynamic patterns

For each affected line, replace patterns like:

```python
# Before:
opened_at: str = "2026-03-25T10:00:00"

# After (assuming the test wants "30 days ago" semantics):
opened_at: str = (datetime.now() - timedelta(days=30)).isoformat()
# OR if the test wants "exactly 5 days ago" semantics:
opened_at: str = (datetime.now() - timedelta(days=5)).isoformat()
```

The exact `N` depends on assertion semantics. Read each test's assertion to
pick the right offset. **DO NOT use `0` (today) blindly** — some tests assert
the seed is older than a threshold, and `0` would make those false-pass.

### Requirement 2: Verify the fix

```bash
python -m pytest tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py -v 2>&1 | tail -20
# Expected: all 12 previously-failing tests now pass
```

### Requirement 3: Full-suite green

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Expected: 5,080 passed, 0 failed (back to pre-tipping-point baseline)
```

### Requirement 4: Verify no over-correction

Some hardcoded dates may be intentional (e.g., a test that asserts "the
parser handles 2026-03-25 specifically as a known historical input"). Read
the test purpose; only convert dates that drive assertion semantics, not
dates that are part of the assertion target itself.

A grep across tests for `2026-03-25` should now show only assertion-target
dates (if any), not seed dates.

### Requirement 5: Regression test for the date-decay class

Optional but encouraged — add one regression test that asserts:

```python
def test_no_hardcoded_seed_dates_in_test_filter_accuracy():
    """Catch DEF-205-class regressions: no hardcoded ISO date seeds in date-window-sensitive tests."""
    import re
    with open("tests/intelligence/test_filter_accuracy.py") as f:
        content = f.read()
    # Allow strings inside docstrings or comments; only flag uncommented assignments
    assert not re.search(r'^\s*\w+.*=.*"2026-\d{2}-\d{2}', content, re.MULTILINE), \
        "Hardcoded date seed detected — use datetime.now() - timedelta(...)"
```

## Definition of Done

- [ ] All 12 previously-failing tests pass
- [ ] Full pytest suite back to 5,080 passing / 0 failing (or +1 if regression test added)
- [ ] No `2026-03-25` hardcoded seed dates remain in test files (assertion targets okay if any)
- [ ] CLAUDE.md DEF-205 strikethrough with commit SHA
- [ ] RUNNING-REGISTER.md DEF-205 moved to Resolved
- [ ] CAMPAIGN-COMPLETENESS-TRACKER.md Stage 9C TEST-HYGIENE-01 row → CLEAR
- [ ] Close-out at `docs/sprints/sprint-31.9/TEST-HYGIENE-01-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/TEST-HYGIENE-01-review.md`

## Regression Checklist

| Check | How to Verify |
|-------|---------------|
| All 12 failures resolved | Targeted pytest run |
| Full suite back to clean baseline | Full pytest run |
| No new failures introduced | pytest suite delta = +12 (or +13 with regression test) |
| No production code modified | `git diff argus/` empty |
| No config modified | `git diff config/` empty |
| Only test files + docs modified | `git diff --name-only` ≤5 files |
| DEF-205 strikethrough in CLAUDE.md | grep `~~DEF-205~~` |

## Constraints

- DO NOT modify any production code (`argus/`)
- DO NOT modify configs
- DO NOT modify other test files unless they share the same date seed pattern AND are failing
- DO NOT modify `workflow/` submodule
- DO NOT introduce new dependencies
- Work on `main`

## Test Targets

- All 12 currently-failing tests pass
- Full pytest suite delta: +12 (5,068 → 5,080) or +13 if regression test added
- Vitest count unchanged

## Tier 2 Review (Mandatory)

Standard profile. Provide:
1. This kickoff
2. Close-out path
3. Diff range
4. Files that should NOT have been modified:
   - Any `argus/` file
   - Any `config/` file
   - Other test files (unless shared seed)
   - `workflow/` submodule
5. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Session-Specific Review Focus (for @reviewer)

1. **Verify each date conversion preserves assertion semantics.** A test that
   said "30 days ago" and is now `timedelta(days=0)` is wrong even if it
   passes. Read each converted test's assertions.
2. **Verify no over-correction.** Hardcoded dates that are assertion *targets*
   (not seeds) should remain hardcoded. Spot-check via the post-fix grep.
3. **Verify no scope creep.** This is a 12-line mechanical fix; if the diff
   touches >5 files, question why.
4. **Verify regression test (if added) actually regresses.** Revert one date
   conversion, confirm the regression test fails.

## Escalation Criteria

Trigger ESCALATE if ANY of:
- Production code (`argus/`) modified
- More than 12-15 lines of test changes (suggests scope creep)
- Other DEFs touched
- Test-suite count changes by anything other than +12 or +13
- `workflow/` modified

## Operator Handoff

1. Close-out
2. Review
3. Test count delta confirmed
4. DEF-205 strikethrough confirmed
5. One-line summary: `TEST-HYGIENE-01 complete. {N} dates converted. Test suite: 5,068 → 5,080 (DEF-205 closed). Commit: {SHA}.`

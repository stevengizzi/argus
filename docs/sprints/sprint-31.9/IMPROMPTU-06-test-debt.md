# Sprint 31.9 IMPROMPTU-06: Test-Debt & Warning-Cleanup Bundle

> Drafted Phase 1b. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Findings addressed:**
- **DEF-176** — Remove deprecated `OrderManager(auto_cleanup_orphans=...)` kwarg. FIX-04 added a `DeprecationWarning` when the legacy kwarg is used without `reconciliation_config=`. 3 reconciliation test files still pass the kwarg. Migrate the tests; then delete the kwarg + guard + docstring entry from `OrderManager.__init__`.
- **DEF-185** — Convert 5 remaining `assert isinstance(...)` sites to explicit `if not isinstance: raise TypeError(...)` guards (DEF-106 follow-on). Sites: `argus/analytics/ensemble_evaluation.py` × 3 + `argus/intelligence/learning/outcome_collector.py` × 2.
- **DEF-192 PARTIAL remainder** — 4 of 5 test runtime warning categories:
  - (i) aiosqlite "Event loop is closed" (~3 sites)
  - (ii) AsyncMock coroutine-never-awaited (~8 sites, intermittent under xdist)
  - (iii) `websockets.legacy` deprecation (transitive dep)
  - (iv) `OrderManager(auto_cleanup_orphans=...)` deprecation — folded into DEF-176 above
  - Category (v) `TestBaseline` stays **MONITOR** (workflow submodule, RULE-018 blocker).
- **DEF-166** — `test_speed_benchmark` flaky under `pytest-cov`. The test was already superseded by `test_functional_equivalence` at `tests/backtest/test_walk_forward_engine.py:565`. Close-with-verification: confirm the old name is gone (it should be) and annotate the DEF accordingly.
- **DEF-048** — 4 `test_main.py` xdist failures (same `load_dotenv` / `AIConfig` race as closed DEF-046). Fix via autouse fixture pattern or explicit env isolation.
- **DEF-049** — `test_orchestrator_uses_strategies_from_registry` isolation failure (passes in full suite, fails in isolation). Diagnose + fix.
- **Non-DEF** — `TestOverflowConfigYamlAlignment` no-op test after `system.yaml` overflow removal (`tests/intelligence/test_config.py`). Delete or rewrite.
- **Non-DEF** — `tests/test_main.py` stale mocks covering older subsystems. Touch-up opportunistic to the DEF-048 work.

**Files touched:**
- `argus/execution/order_manager.py` — remove deprecated `auto_cleanup_orphans` kwarg + guard (DEF-176 final)
- `argus/analytics/ensemble_evaluation.py` — 3 `assert isinstance` → `if not isinstance: raise TypeError` (DEF-185)
- `argus/intelligence/learning/outcome_collector.py` — 2 `assert isinstance` → same (DEF-185)
- `tests/execution/order_manager/test_reconciliation.py` — may contain `auto_cleanup_orphans` call sites (DEF-176)
- `tests/execution/order_manager/test_reconciliation_redesign.py` — 3+ `auto_cleanup_orphans` sites (DEF-176)
- `tests/execution/order_manager/test_sprint2875.py` — 1 `auto_cleanup_orphans` site (DEF-176)
- `tests/test_main.py` — autouse env-isolation fixture (DEF-048/049)
- `tests/intelligence/test_config.py` — delete `TestOverflowConfigYamlAlignment` (non-DEF)
- Various test files — warning cleanup (DEF-192 i-iii)

**Safety tag:** `safe-during-trading` — test-only changes except for the DEF-176 guard removal (one-line deletion in production code, zero behavior change because production already passes `reconciliation_config=` per FIX-04).

**Theme:** Consolidate test-hygiene debt accumulated over Sprint 31.9. Most items are small but they share the "test-only, safe-during-trading, easy-to-review-together" shape. One production micro-change (DEF-176 kwarg deletion) is gated on the test migration completing.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue. Test-only changes.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)

# Separately run test_main.py to get the xdist-isolated count (DEF-048 context):
python -m pytest tests/test_main.py -q 2>&1 | tail -5
```

**Expected baseline:** Post-IMPROMPTU-04/05 count. Obtain precise count from those close-outs. Some `test_main.py` tests have been failing under `-n auto` since Sprint 23.9; that's DEF-048's scope.

### 3. Warning baseline capture

Capture the warning-category histogram BEFORE any changes:
```bash
python -m pytest --ignore=tests/test_main.py -n auto -q -W default 2>&1 \
  | grep -E "^[^:]+Warning:|DeprecationWarning:|ResourceWarning:|PendingDeprecationWarning:" \
  | sort | uniq -c | sort -rn > /tmp/warnings-baseline.txt
wc -l /tmp/warnings-baseline.txt
head -10 /tmp/warnings-baseline.txt
```

Save this baseline — you'll diff against it at close-out to confirm the 4 categories dropped.

### 4. Branch & workspace

```bash
git checkout main
git pull --ff-only
git log --oneline -5
git status  # Expected: clean working tree
```

## Pre-Flight Context Reading

1. Read these files:
   - `CLAUDE.md` DEF-176, DEF-185, DEF-192, DEF-166, DEF-048, DEF-049 entries
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"IMPROMPTU-06"
   - `argus/execution/order_manager.py` lines 180–240 — DEF-176 kwarg + deprecation guard + fallback
   - `argus/analytics/ensemble_evaluation.py` lines 185–210 — 3 assert sites (roughly 189, 196, 204)
   - `argus/intelligence/learning/outcome_collector.py` lines 205–310 — 2 assert sites (209, 303)
   - `tests/execution/order_manager/test_reconciliation_redesign.py` — understand the kwarg migration pattern from FIX-04
   - `tests/test_main.py` lines 1–50 — the current env-isolation scheme for `ANTHROPIC_API_KEY`
   - `tests/backtest/test_walk_forward_engine.py:565` — confirm `test_functional_equivalence` exists and supersedes the old flaky benchmark

2. Review DEF-106's resolution pattern (FIX-07, commit `7b70390`) for reference on DEF-185:
   ```python
   # BEFORE (DEF-106 anti-pattern):
   assert isinstance(x, SomeType), f"expected SomeType, got {type(x)}"

   # AFTER (DEF-106 pattern):
   if not isinstance(x, SomeType):
       raise TypeError(f"expected SomeType, got {type(x).__name__}")
   ```
   Apply the same transformation to each of the 5 remaining sites.

## Objective

Clean up 6 test-hygiene DEFs + 2 non-DEF items in one bundle, delete the
DEF-176 deprecated kwarg from production, drop 4 of 5 DEF-192 warning
categories (the 5th stays MONITOR). All changes are test-only except the
single-line kwarg deletion gated on test migration.

## Requirements

### Requirement 1: DEF-176 — `auto_cleanup_orphans` kwarg removal

1. For each of the 3 reconciliation test files, migrate call sites from
   the legacy kwarg to the typed config:
   - `tests/execution/order_manager/test_reconciliation.py` (verify with grep; may not have any sites)
   - `tests/execution/order_manager/test_reconciliation_redesign.py` (3+ known sites)
   - `tests/execution/order_manager/test_sprint2875.py` (1 known site at line 501)

   Migration pattern:
   ```python
   # BEFORE:
   order_manager = OrderManager(
       ...
       auto_cleanup_orphans=False,
       ...
   )

   # AFTER:
   from argus.execution.reconciliation import ReconciliationConfig  # if not already imported
   order_manager = OrderManager(
       ...
       reconciliation_config=ReconciliationConfig(auto_cleanup_orphans=False),
       ...
   )
   ```
   
   Preserve any assertions about behavior (e.g., `test_legacy_auto_cleanup_orphans_still_works` in `test_reconciliation_redesign.py:543` is an explicit backward-compat test; either delete it with a note "no longer applicable — kwarg removed" or keep it testing the `ReconciliationConfig` field path directly).

2. After all test migrations land and pass, delete from `argus/execution/order_manager.py`:
   - Line ~186: the `auto_cleanup_orphans: bool = False,` parameter
   - Line ~202-204: the docstring entry for `auto_cleanup_orphans`
   - Line ~224-232: the `if auto_cleanup_orphans and reconciliation_config is None:` `DeprecationWarning` guard
   - Line ~233: the `ReconciliationConfig(auto_cleanup_orphans=auto_cleanup_orphans)` fallback

3. Confirm via grep that no remaining references exist:
   ```bash
   grep -rn "auto_cleanup_orphans" argus/ tests/ | grep -v "reconciliation\.py\|# legacy\|# DEF-"
   # Expected: zero matches except in ReconciliationConfig itself and migration-note comments
   ```

### Requirement 2: DEF-185 — Analytics assert-isinstance conversion

Convert each of the 5 sites using the DEF-106 pattern:

1. `argus/analytics/ensemble_evaluation.py:189` — `assert isinstance(data_range_raw, list)` → `if not isinstance(data_range_raw, list): raise TypeError(f"Expected list for data_range_raw, got {type(data_range_raw).__name__}")`
2. `argus/analytics/ensemble_evaluation.py:196` — `assert isinstance(mc_raw, dict)` → same pattern with `dict`
3. `argus/analytics/ensemble_evaluation.py:204` — `assert isinstance(baseline_raw, dict)` → same pattern
4. `argus/intelligence/learning/outcome_collector.py:209` — `assert isinstance(exit_time_str, str)` → same pattern with `str`
5. `argus/intelligence/learning/outcome_collector.py:303` — `assert isinstance(closed_at_str, str)` → same pattern

For each site, write ONE regression test asserting that the TypeError fires
with a specific wrong type. Place tests at:
- `tests/analytics/test_ensemble_evaluation_type_guards.py` (new, 3 tests)
- `tests/intelligence/learning/test_outcome_collector_type_guards.py` (new, 2 tests)

5 new tests total. These tests must FAIL if the `assert` is restored (revert-proof).

### Requirement 3: DEF-192 remainder — warning cleanup

Address the 4 remaining warning categories:

**Category (i) — aiosqlite "Event loop is closed" (~3 sites):**
1. Identify the ~3 sites from the baseline warning capture (Pre-Session Verification step 3). Likely in tests that use aiosqlite connections without proper fixture teardown.
2. Fix by adding explicit `await db.close()` in fixture teardown, or wrapping the operation in `async with aiosqlite.connect(...) as db:` blocks.
3. Confirm the warning no longer fires in the warning baseline.

**Category (ii) — AsyncMock coroutine-never-awaited (~8 sites, intermittent under xdist):**
1. Identify the ~8 sites. The pattern is typically:
   ```python
   mock_fn = AsyncMock()
   result = mock_fn(...)  # Coroutine created but not awaited
   ```
   Fix: either `await mock_fn(...)` or use `MagicMock` instead if the code doesn't actually await it.
2. The intermittent-under-xdist nature suggests some sites are order-dependent. Fix all identifiable ones; the remaining intermittent count should drop significantly.

**Category (iii) — `websockets.legacy` deprecation (transitive dep):**
1. This is emitted by `websockets>=10` when code uses the old API. Check if argus uses the websockets library directly or only via transitives (uvicorn, etc.).
2. If argus uses it directly, migrate to `websockets.asyncio.server.serve(...)` per the v10+ API.
3. If purely transitive, this is a library version bump concern — pin `websockets>=11,<13` in `pyproject.toml` and accept that the deprecation warning may persist until upstream libs update. Document in the close-out.

**Category (iv) — `OrderManager(auto_cleanup_orphans=...)` deprecation:**
Automatically resolved by Requirement 1 above. Confirm zero matches in the warning baseline post-fix.

**Post-fix warning baseline:**
Re-run the warning capture:
```bash
python -m pytest --ignore=tests/test_main.py -n auto -q -W default 2>&1 \
  | grep -E "^[^:]+Warning:|DeprecationWarning:|ResourceWarning:|PendingDeprecationWarning:" \
  | sort | uniq -c | sort -rn > /tmp/warnings-after.txt
diff /tmp/warnings-baseline.txt /tmp/warnings-after.txt
```

Expected reduction: from ~26–40 warnings (current range) to ≤10 warnings.
The remaining warnings should be exclusively category (v) TestBaseline (blocked
on RULE-018). Document the final count in the close-out.

### Requirement 4: DEF-166 — `test_speed_benchmark` close-with-verification

1. Confirm via grep:
   ```bash
   grep -rn "test_speed_benchmark" tests/
   # Expected: only found in docstring comments, not as an actual test function
   ```
2. Confirm `test_functional_equivalence` at `tests/backtest/test_walk_forward_engine.py:565` exists and exercises equivalent coverage.
3. In the close-out, annotate DEF-166 as RESOLVED-VERIFIED (the test is already replaced; the DEF was a stale observation).

### Requirement 5: DEF-048 — `test_main.py` xdist failures (4 tests)

1. Identify the 4 tests that fail under `-n auto`. Run:
   ```bash
   python -m pytest tests/test_main.py -q 2>&1 | grep "FAIL"
   ```
2. The root cause per CLAUDE.md is the same as closed DEF-046: `load_dotenv()` race re-populating `ANTHROPIC_API_KEY` from `.env`, flipping `AIConfig.auto_detect_enabled` to True mid-test.
3. Add or extend an autouse fixture in `tests/conftest.py` or `tests/test_main.py` that explicitly sets `ANTHROPIC_API_KEY=""` via `monkeypatch.setenv(...)` (not `delenv` — setting to empty prevents `load_dotenv` re-pickup per the existing FIX-03 pattern at `tests/test_main.py:16-18`).
4. Migrate the 4 failing tests to use the fixture.
5. Verify all 4 pass under `-n auto` after the fix.

### Requirement 6: DEF-049 — `test_orchestrator_uses_strategies_from_registry` isolation

1. Reproduce the failure in isolation:
   ```bash
   python -m pytest tests/test_main.py::test_orchestrator_uses_strategies_from_registry -v
   ```
2. Read the test and understand what state it depends on that's only set up by another test running first in the full suite.
3. Fix by either:
   - Making the test self-contained (set up its own fixtures)
   - Using a fixture from `conftest.py` that provides the missing state
4. Verify isolated + full-suite both pass post-fix.

### Requirement 7: Non-DEF cleanups

1. **Delete `TestOverflowConfigYamlAlignment`** from `tests/intelligence/test_config.py`. This test became a no-op after Sprint 32.x removed the `overflow:` key from `system.yaml`. Grep first to confirm it's safe to delete:
   ```bash
   grep -rn "TestOverflowConfigYamlAlignment" tests/
   # Expected: only the definition itself, no cross-references
   ```

2. **`tests/test_main.py` stale mocks** — opportunistic touch-up. If, while fixing DEF-048/049, you encounter mocks that reference classes or functions that no longer exist (e.g., `_reconstruct_strategy_state` or `BrokerRouter`), delete or update them. Do NOT make this a broad refactor — scope is "if it crosses your vision during other work, fix it; otherwise leave."

## Constraints

- **Do NOT modify** any argus production code other than the 2 files in Requirement 2 (DEF-185) and the single kwarg deletion in Requirement 1 (DEF-176). In particular, do NOT touch `OrderManager` methods beyond the `__init__` deprecated-kwarg deletion.
- **Do NOT change** the `ReconciliationConfig` dataclass, its defaults, or its constructor signature.
- **Do NOT reintroduce** any `assert isinstance` patterns elsewhere in argus. The 5 sites in Requirement 2 are the full known set; if you find others, log as a new DEF — don't fix in-session.
- **Do NOT modify** category (v) TestBaseline — workflow submodule, RULE-018.
- **Do NOT modify** the `workflow/` submodule (Universal RULE-018).
- **Do NOT touch** any audit-2026-04-21 doc back-annotations.
- Work directly on `main`.

## Test Targets

After implementation:
- All existing tests pass
- New tests: +5 (DEF-185 type-guard regression tests)
- Net test delta: **+5** (if DEF-176 legacy test is kept as backward-compat for `ReconciliationConfig`) OR **+4** (if the legacy test is deleted as no-longer-applicable) OR **+5–9** depending on DEF-048/049 fixture additions
- Expected final count: baseline + 5–9
- Test command:
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  python -m pytest tests/test_main.py -q  # separately to verify DEF-048/049 fixes
  ```

## Definition of Done

- [ ] All 7 requirements implemented
- [ ] All existing tests pass
- [ ] New type-guard regression tests (Requirement 2) added and each FAILS if the corresponding `raise TypeError` is reverted to `assert`
- [ ] Warning baseline diff in close-out showing reduction to ≤10 warnings
- [ ] `grep -rn "auto_cleanup_orphans" argus/ tests/` returns only expected matches (ReconciliationConfig + migration notes; no legacy-kwarg calls)
- [ ] `grep -rn "assert isinstance" argus/analytics/ argus/intelligence/learning/` returns zero
- [ ] All 4 `test_main.py` xdist failures pass under `-n auto`
- [ ] `test_orchestrator_uses_strategies_from_registry` passes in isolation and in full suite
- [ ] `TestOverflowConfigYamlAlignment` deleted
- [ ] `CLAUDE.md` DEF-048, DEF-049, DEF-166, DEF-176, DEF-185, DEF-192 entries updated with strikethrough + commit SHA (DEF-192 stays PARTIAL with category (v) deferred)
- [ ] `RUNNING-REGISTER.md` updated: DEFs moved to "Resolved this campaign" table
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` Stage 9B row for IMPROMPTU-06 marked CLEAR
- [ ] Close-out report at `docs/sprints/sprint-31.9/IMPROMPTU-06-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-06-review.md`
- [ ] Green CI URL cited in close-out (P25 rule)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| OrderManager constructor no longer accepts `auto_cleanup_orphans` | `grep "auto_cleanup_orphans" argus/execution/order_manager.py` returns zero |
| Legacy tests have been migrated to `ReconciliationConfig` | Grep + spot-check each migrated file |
| ReconciliationConfig API unchanged | Diff shows only test files changed, not the config class |
| 5 type-guard tests pass; revert → fail | Manually revert one assertion and confirm test fails with clear message |
| Warning count dropped to ≤10 | `/tmp/warnings-after.txt` line count |
| category (v) TestBaseline still listed in remaining warnings | Confirm MONITOR status preserved |
| xdist failures in test_main.py resolved | `pytest tests/test_main.py -n auto` all pass |
| Isolation failure in test_orchestrator resolved | `pytest tests/test_main.py::test_orchestrator_uses_strategies_from_registry -v` passes |
| Full suite net delta ≥ +4 (new type-guard tests minus deletions) | Test count comparison |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

Write the close-out report to:
`docs/sprints/sprint-31.9/IMPROMPTU-06-closeout.md`

Include:
1. **DEF-176 migration table:** per-file list of call sites migrated + post-fix grep verification
2. **DEF-185 type-guard test table:** 5 new tests with 1-line assertion for each (each FAILS revert-proof)
3. **DEF-192 warning diff:** baseline vs post-fix categories + final count
4. **DEF-048/049 fix explanation:** root cause + 1-sentence fix rationale
5. **DEF-166 verification annotation:** proof that `test_functional_equivalence` supersedes `test_speed_benchmark`
6. **Green CI URL** for final commit SHA

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke @reviewer after close-out writes.

Provide:
1. Review context: this kickoff file + CLAUDE.md DEF entries
2. Close-out path: `docs/sprints/sprint-31.9/IMPROMPTU-06-closeout.md`
3. Diff range: `git diff HEAD~N`
4. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q` + `python -m pytest tests/test_main.py -q`
5. Files that should NOT have been modified:
   - Any argus/ runtime file OTHER than the 3 files listed in Requirements 1 + 2
   - `argus/execution/reconciliation.py` (ReconciliationConfig must be untouched)
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation
   - `config/experiments.yaml`
   - Any frontend UI file

The @reviewer writes to `docs/sprints/sprint-31.9/IMPROMPTU-06-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify the DEF-176 migration is complete.** Grep-audit: no `auto_cleanup_orphans=` as a call-site kwarg anywhere in tests/ or argus/ (except inside ReconciliationConfig usage).
2. **Verify the DEF-185 conversions preserve semantics.** Each `raise TypeError` must fire on the same type-mismatch condition the `assert` caught; not a weaker or stronger check.
3. **Verify the DEF-185 regression tests are revert-proof.** For each test, mentally revert the fix and confirm the test would fail with a clear type-mismatch message.
4. **Verify the DEF-192 warning baseline diff is real.** Run the warning-capture command yourself and confirm the diff.
5. **Verify DEF-048/049 fixes don't hide other failures.** Run `tests/test_main.py` with `-n auto` and `-n 0` separately; both must pass.
6. **Verify category (v) TestBaseline is explicitly documented as MONITOR.** The close-out must state this clearly.
7. **Verify green CI URL for final commit.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta ≥ +4
- Vitest count unchanged (no UI touch)
- No scope boundary violation
- CLAUDE.md DEF strikethroughs present for DEF-048, 049, 166, 176, 185; DEF-192 annotated PARTIAL → mostly-resolved

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- `auto_cleanup_orphans=` as a legacy-kwarg call site found anywhere after the session
- Any `assert isinstance` remaining in `argus/analytics/ensemble_evaluation.py` or `argus/intelligence/learning/outcome_collector.py`
- Warning count INCREASED or flat vs baseline
- DEF-048 fixture pattern doesn't match FIX-03's existing `ANTHROPIC_API_KEY` isolation style
- `ReconciliationConfig` modified
- pytest net delta < +4
- Green CI URL missing or CI red
- Audit-report back-annotation modified
- category (v) TestBaseline silently "fixed" (RULE-018 violation)

## Post-Review Fix Documentation

Standard protocol per the implementation-prompt template.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Warning diff summary:** baseline → after count
4. **Migration summary:** 3 test files × auto_cleanup_orphans migrated; 5 assert-isinstance sites converted
5. Green CI URL
6. One-line summary: `Session IMPROMPTU-06 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {pre} → {post}. CI: {URL}. DEFs closed: DEF-048, DEF-049, DEF-166, DEF-176, DEF-185; DEF-192 4-of-5 categories closed (category v stays MONITOR per RULE-018).`

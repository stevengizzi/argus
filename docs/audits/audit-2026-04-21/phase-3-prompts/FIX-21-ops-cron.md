# Fix Session FIX-21-ops-cron: ops — cron / scheduled tasks

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 1
**Files touched:** `docs/live-operations.md`
**Safety tag:** `safe-during-trading`
**Theme:** Scheduling fix for an ops cron task (historical cache monthly update per CLAUDE.md 'horizon' item).

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Verify paper trading is stable (no active alerts in session debrief).
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK for safe-during-trading"

# This session is safe-during-trading. Code paths touched here do NOT
# affect live signal/order flow. You may proceed during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-21): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `docs/live-operations.md`: 1 finding

## Findings to Fix

### Finding 1: `DEF-097+162` [LOW]

**File/line:** crontab + docs/live-operations.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Monthly cache update cron (populate + consolidate pair)

**Impact:**

> Cache grows stale month-over-month; manual update required

**Suggested fix:**

> Schedule paired cron: populate_historical_cache.py --update && consolidate_parquet_cache.py --resume

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-21-ops-cron**`.

## Post-Session Verification

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-21-ops-cron** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-21-ops-cron**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-21): ops cron scheduling

Addresses audit findings:
- DEF-097+162 [LOW]: Monthly cache update cron (populate + consolidate pair)

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions
- [ ] Commit pushed to `main` with the exact message format above
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-21-ops-cron**`

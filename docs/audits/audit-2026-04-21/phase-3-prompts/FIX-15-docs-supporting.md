# Fix Session FIX-15-docs-supporting: docs/ — supporting documents

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 28
**Files touched:** `docs/amendments/roadmap-amendment-experiment-infrastructure.md`, `docs/amendments/roadmap-amendment-intelligence-architecture.md`, `docs/archived/10_PHASE3_SPRINT_PLAN.md`, `docs/backtesting/BACKTEST_RUN_LOG.md`, `docs/backtesting/DATA_INVENTORY.md`, `docs/decision-log.md`, `docs/ibc-setup.md`, `docs/live-operations.md`, `docs/paper-trading-guide.md`, `docs/process-evolution.md`, `docs/project-bible.md`, `docs/roadmap.md`, `docs/sprint-campaign.md`, `docs/strategies/STRATEGY_ABCD.md`, `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`, `docs/strategies/STRATEGY_BULL_FLAG.md`, `docs/strategies/STRATEGY_DIP_AND_RIP.md`, `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md`, `docs/strategies/STRATEGY_GAP_AND_GO.md`, `docs/strategies/STRATEGY_HOD_BREAK.md`, `docs/strategies/STRATEGY_MICRO_PULLBACK.md`, `docs/strategies/STRATEGY_NARROW_RANGE_BREAKOUT.md`, `docs/strategies/STRATEGY_ORB_SCALP.md`, `docs/strategies/STRATEGY_PREMARKET_HIGH_BREAK.md`, `docs/strategies/STRATEGY_RED_TO_GREEN.md`, `docs/strategies/STRATEGY_VWAP_BOUNCE.md`, `docs/strategies/STRATEGY_VWAP_RECLAIM.md`, `docs/strategy-template.md`
**Safety tag:** `safe-during-trading`
**Theme:** Updates to supporting docs: sprint history, DEC log, strategy spec sheets, protocols, audit records.

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
marker (`audit(FIX-15): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `docs/amendments/roadmap-amendment-experiment-infrastructure.md`: 1 finding
- `docs/amendments/roadmap-amendment-intelligence-architecture.md`: 1 finding
- `docs/archived/10_PHASE3_SPRINT_PLAN.md`: 1 finding
- `docs/backtesting/BACKTEST_RUN_LOG.md`: 1 finding
- `docs/backtesting/DATA_INVENTORY.md`: 1 finding
- `docs/decision-log.md`: 1 finding
- `docs/ibc-setup.md`: 1 finding
- `docs/live-operations.md`: 1 finding
- `docs/paper-trading-guide.md`: 1 finding
- `docs/process-evolution.md`: 1 finding
- `docs/project-bible.md`: 1 finding
- `docs/roadmap.md`: 1 finding
- `docs/sprint-campaign.md`: 1 finding
- `docs/strategies/STRATEGY_ABCD.md`: 1 finding
- `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`: 1 finding
- `docs/strategies/STRATEGY_BULL_FLAG.md`: 1 finding
- `docs/strategies/STRATEGY_DIP_AND_RIP.md`: 1 finding
- `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md`: 1 finding
- `docs/strategies/STRATEGY_GAP_AND_GO.md`: 1 finding
- `docs/strategies/STRATEGY_HOD_BREAK.md`: 1 finding
- `docs/strategies/STRATEGY_MICRO_PULLBACK.md`: 1 finding
- `docs/strategies/STRATEGY_NARROW_RANGE_BREAKOUT.md`: 1 finding
- `docs/strategies/STRATEGY_ORB_SCALP.md`: 1 finding
- `docs/strategies/STRATEGY_PREMARKET_HIGH_BREAK.md`: 1 finding
- `docs/strategies/STRATEGY_RED_TO_GREEN.md`: 1 finding
- `docs/strategies/STRATEGY_VWAP_BOUNCE.md`: 1 finding
- `docs/strategies/STRATEGY_VWAP_RECLAIM.md`: 1 finding
- `docs/strategy-template.md`: 1 finding

## Findings to Fix

### Finding 1: `H1B-07` [MEDIUM]

**File/line:** docs/amendments/roadmap-amendment-experiment-infrastructure.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Header says "Proposal — not yet adopted" but Sprints 27.5 + 32.5 shipped

**Impact:**

> Doc state contradicts project state

**Suggested fix:**

> Update header to "ADOPTED — see Sprints 27.5, 32.5"; or move to docs/archived/

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 2: `H1B-08` [MEDIUM]

**File/line:** docs/amendments/roadmap-amendment-intelligence-architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Same "not yet adopted" stamp; 27.6 + 27.7 shipped; 33.5 pending

**Impact:**

> Doc state contradicts project state

**Suggested fix:**

> Update header; partial adoption noted explicitly

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 3: `H1B-24` [LOW]

**File/line:** docs/archived/10_PHASE3_SPRINT_PLAN.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Referenced by 43 historical sprint files (1-21.5); needs "Last active: Sprint 21.5" note in archived index

**Impact:**

> Cross-reference hygiene

**Suggested fix:**

> Add note to archived/ index indicating last-active sprint

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 4: `H1B-22` [LOW]

**File/line:** docs/backtesting/BACKTEST_RUN_LOG.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Final entry Run 8 (Feb 17). Pre-live artifact, 63 days stale

**Impact:**

> Not being maintained

**Suggested fix:**

> Move to docs/archived/

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 5: `H1B-23` [LOW]

**File/line:** docs/backtesting/DATA_INVENTORY.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Feb 17. Describes Alpaca IEX feed; superseded by Databento + Sprint 31.85 parquet-cache-layout.md

**Impact:**

> Stale data source description

**Suggested fix:**

> Move to docs/archived/; parquet-cache-layout.md is the current reference

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 6: `H1B-10` [MEDIUM]

**File/line:** docs/decision-log.md:2907
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Same 2 broken refs as H1B-09 + 1 reference to never-existed file

**Impact:**

> Broken links in authoritative DEC record

**Suggested fix:**

> Repair archived/ prefix; remove never-existed file ref

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 7: `H1B-25` [COSMETIC]

**File/line:** docs/ibc-setup.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Does not mention Sprint 32.75 post-reconnect 3s hardcoded delay

**Impact:**

> Minor documentation drift

**Suggested fix:**

> Add cross-ref to pre-live-transition-checklist.md where 3s delay is documented

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 8: `DEF-164` [LOW]

**File/line:** docs/live-operations.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Late-night ARGUS boot collides with after-hours auto-shutdown

**Impact:**

> Boot between 22:30 ET and pre-market may fail due to auto-shutdown timing

**Suggested fix:**

> Doc fix: add warning to docs/live-operations.md (code fix is weekend-only followup)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 9: `H1B-01` [CRITICAL]

**File/line:** docs/paper-trading-guide.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Paper-trading guide describes obsolete Alpaca broker; 33 Alpaca references, --paper flag, ALPACA_BASE_URL

**Impact:**

> Rewrite from Alpaca-based to IBKR paper (ARGUS current state). Any operator following this guide today will fail.

**Suggested fix:**

> Rewrite entire doc for IBKR paper per pre-live-transition-checklist.md + live-operations.md

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 10: `H1B-03` [MEDIUM]

**File/line:** docs/process-evolution.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Doc stops at Sprint 21.5; missing Sprints 22-31.85 (~52 days). No lifecycle decision.

**Impact:**

> Either durable historical narrative or stale artifact; operator decides

**Suggested fix:**

> Option A: FREEZE with explicit "frozen at Sprint 21.5" header. Option B: refresh through Sprint 31.85.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 11: `H1B-27` [COSMETIC]

**File/line:** docs/project-bible.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> §4.2 strategy roster missing Micro Pullback, VWAP Bounce, Narrow Range Breakout

**Impact:**

> Minor content drift

**Suggested fix:**

> Add 3 new strategies to roster

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 12: `H1B-09` [MEDIUM]

**File/line:** docs/roadmap.md:6
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> 2 broken supersession refs (missing archived/ prefix)

**Impact:**

> Broken links

**Suggested fix:**

> Repair archived/ prefix on 2 refs

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 13: `H1B-02` [MEDIUM]

**File/line:** docs/sprint-campaign.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Header says "Updated: Sprint 28 complete, Sprint 28.5 next" — ~15 sprints stale

**Impact:**

> Misleads readers who check the header for currency

**Suggested fix:**

> Update header to current state; or reframe doc as process template with explicit "not a sprint queue"

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 14: `H1B-11` [LOW]

**File/line:** docs/strategies/STRATEGY_ABCD.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub doc; no PROVISIONAL marker; aware of Sprint 32.9 shadow demotion

**Impact:**

> Operator cannot distinguish validated from unvalidated strategy docs

**Suggested fix:**

> Add PROVISIONAL caveat; note shadow mode status

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 15: `H1B-04` [MEDIUM]

**File/line:** docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Regime section omits bearish_trending; DEC-360 adds it to all strategies

**Impact:**

> Doc contradicts code

**Suggested fix:**

> Add bearish_trending to allowed_regimes section

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 16: `H1B-05` [MEDIUM]

**File/line:** docs/strategies/STRATEGY_BULL_FLAG.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Same bearish_trending omission as H1B-04

**Impact:**

> Doc contradicts code

**Suggested fix:**

> Add bearish_trending to allowed_regimes section

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 17: `H1B-12` [LOW]

**File/line:** docs/strategies/STRATEGY_DIP_AND_RIP.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; no mention of 2 shadow variants (v2/v3) in experiments.yaml

**Impact:**

> Operators do not see variant deployment state

**Suggested fix:**

> Add shadow variant section listing active variants

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 18: `H1B-13` [LOW]

**File/line:** docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Aware of Sprint 32.9 shadow demotion; backtest placeholder unfilled

**Impact:**

> Doc partially current

**Suggested fix:**

> Fill backtest placeholder OR mark explicitly as pending

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 19: `H1B-14` [LOW]

**File/line:** docs/strategies/STRATEGY_GAP_AND_GO.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; notes pre-DEF-152 sweep invalid; no updated validation

**Impact:**

> Needs post-DEF-152 re-sweep results

**Suggested fix:**

> Update with post-fix sweep results OR mark explicitly pending

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 20: `H1B-15` [LOW]

**File/line:** docs/strategies/STRATEGY_HOD_BREAK.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; no backtest results; no PROVISIONAL caveat

**Impact:**

> Inconsistent with other strategy docs

**Suggested fix:**

> Add PROVISIONAL caveat + explicit "backtest pending"

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 21: `H1B-16` [LOW]

**File/line:** docs/strategies/STRATEGY_MICRO_PULLBACK.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; Sprint 31A S3 aware; 24-sym sweep noted non-qualifying

**Impact:**

> Documentation aware but incomplete

**Suggested fix:**

> Expand per strategy-template.md; add shadow variant section

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 22: `H1B-17` [LOW]

**File/line:** docs/strategies/STRATEGY_NARROW_RANGE_BREAKOUT.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; Sprint 31A S5 aware; 2-trade sweep noted

**Impact:**

> Same as H1B-16

**Suggested fix:**

> Expand per strategy-template.md; mark PROVISIONAL

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 23: `H1B-18` [LOW]

**File/line:** docs/strategies/STRATEGY_ORB_SCALP.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> VectorBT results mixed; no walk-forward; PROVISIONAL present

**Impact:**

> Needs walk-forward results

**Suggested fix:**

> Add walk-forward entry OR mark "walk-forward pending"

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 24: `H1B-19` [LOW]

**File/line:** docs/strategies/STRATEGY_PREMARKET_HIGH_BREAK.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; no backtest validation

**Impact:**

> Same as H1B-15

**Suggested fix:**

> Add PROVISIONAL caveat + explicit "backtest pending"

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 25: `H1B-06` [MEDIUM]

**File/line:** docs/strategies/STRATEGY_RED_TO_GREEN.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Same bearish_trending omission (code has it hardcoded)

**Impact:**

> Doc contradicts code

**Suggested fix:**

> Add bearish_trending to allowed_regimes section

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 26: `H1B-20` [LOW]

**File/line:** docs/strategies/STRATEGY_VWAP_BOUNCE.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Stub; DEF-154 param rework documented; no PROVISIONAL

**Impact:**

> Documentation aware but incomplete

**Suggested fix:**

> Add PROVISIONAL caveat

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 27: `H1B-21` [LOW]

**File/line:** docs/strategies/STRATEGY_VWAP_RECLAIM.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Full template; backtest placeholders unfilled

**Impact:**

> Placeholders in an otherwise complete doc

**Suggested fix:**

> Fill backtest placeholders with current values

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

### Finding 28: `H1B-26` [COSMETIC]

**File/line:** docs/strategy-template.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing optional sections for Shadow Mode status, Experiment Variant ID, Quality Grade calibration

**Impact:**

> Template could be more helpful

**Suggested fix:**

> Add optional sections per project-knowledge current state

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-15-docs-supporting**`.

## Post-Session Verification (before commit)

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
| ... | ~~description~~ **RESOLVED FIX-15-docs-supporting** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-15-docs-supporting**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-15` (full ID: `FIX-15-docs-supporting`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-15-docs-supporting**` | | |
| Every DEF closure recorded in CLAUDE.md | | |
| Every new DEF/DEC referenced in commit message bullets | | |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | | |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | | |

### Output format

Render the close-out inside a fenced markdown code block (triple backticks
with `markdown` language hint) bracketed by `---BEGIN-CLOSE-OUT---` /
`---END-CLOSE-OUT---` markers, followed by the `json:structured-closeout`
JSON appendix. Exact format per the close-out.md skill.

The operator will copy this block into the Work Journal conversation on
Claude.ai. Do NOT summarize or modify the format — the conversation parses
these blocks by structure.

### Self-assessment gate

Per close-out.md:
- **CLEAN:** all findings resolved, no unexpected decisions, all tests pass, all regression checks pass
- **MINOR_DEVIATIONS:** all findings addressed but minor judgment calls needed
- **FLAGGED:** any partial finding, test failures, regression check failures, scope exceeded, architectural concerns

**Proceed to the Commit section below UNLESS self-assessment is FLAGGED.**
If FLAGGED, pause. Surface the flag to the operator with a clear
description. Do not push. Wait for operator direction.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-15): supporting docs refresh

Addresses audit findings:
- H1B-07 [MEDIUM]: Header says "Proposal — not yet adopted" but Sprints 27
- H1B-08 [MEDIUM]: Same "not yet adopted" stamp; 27
- H1B-24 [LOW]: Referenced by 43 historical sprint files (1-21
- H1B-22 [LOW]: Final entry Run 8 (Feb 17)
- H1B-23 [LOW]: Feb 17
- H1B-10 [MEDIUM]: Same 2 broken refs as H1B-09 + 1 reference to never-existed file
- H1B-25 [COSMETIC]: Does not mention Sprint 32
- DEF-164 [LOW]: Late-night ARGUS boot collides with after-hours auto-shutdown
- H1B-01 [CRITICAL]: Paper-trading guide describes obsolete Alpaca broker; 33 Alpaca references, --paper flag, ALPACA_BASE_URL
- H1B-03 [MEDIUM]: Doc stops at Sprint 21
- H1B-27 [COSMETIC]: §4
- H1B-09 [MEDIUM]: 2 broken supersession refs (missing archived/ prefix)
- H1B-02 [MEDIUM]: Header says "Updated: Sprint 28 complete, Sprint 28
- H1B-11 [LOW]: Stub doc; no PROVISIONAL marker; aware of Sprint 32
- H1B-04 [MEDIUM]: Regime section omits bearish_trending; DEC-360 adds it to all strategies
- H1B-05 [MEDIUM]: Same bearish_trending omission as H1B-04
- H1B-12 [LOW]: Stub; no mention of 2 shadow variants (v2/v3) in experiments
- H1B-13 [LOW]: Aware of Sprint 32
- H1B-14 [LOW]: Stub; notes pre-DEF-152 sweep invalid; no updated validation
- H1B-15 [LOW]: Stub; no backtest results; no PROVISIONAL caveat
- H1B-16 [LOW]: Stub; Sprint 31A S3 aware; 24-sym sweep noted non-qualifying
- H1B-17 [LOW]: Stub; Sprint 31A S5 aware; 2-trade sweep noted
- H1B-18 [LOW]: VectorBT results mixed; no walk-forward; PROVISIONAL present
- H1B-19 [LOW]: Stub; no backtest validation
- H1B-06 [MEDIUM]: Same bearish_trending omission (code has it hardcoded)
- H1B-20 [LOW]: Stub; DEF-154 param rework documented; no PROVISIONAL
- H1B-21 [LOW]: Full template; backtest placeholders unfilled
- H1B-26 [COSMETIC]: Missing optional sections for Shadow Mode status, Experiment Variant ID, Quality Grade calibration

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Tier 2 Review (REQUIRED after commit — follows `workflow/claude/skills/review.md`)

After the commit above is pushed, invoke the Tier 2 reviewer in this same
session:

```
@reviewer

Please follow workflow/claude/skills/review.md to review the changes from
this session.

Inputs:
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-15-docs-supporting)
- **Close-out report:** the ---BEGIN-CLOSE-OUT--- block produced before commit
- **Regression checklist:** the 8 campaign-level checks embedded in the close-out
- **Escalation criteria:** trigger ESCALATE verdict if ANY of:
  - any CRITICAL severity finding
  - pytest net delta < 0
  - scope boundary violation (file outside declared Scope modified)
  - different test failure surfaces (not the expected DEF-150 flake)
  - Rule-4 sensitive file touched without authorization
  - audit-report back-annotation missing or incorrect
  - (FIX-01 only) Step 1G fingerprint checkpoint failed before pipeline edits proceeded

Produce the ---BEGIN-REVIEW--- block with verdict CLEAR / CONCERNS /
ESCALATE, followed by the json:structured-verdict JSON appendix. Do NOT
modify any code.
```

The reviewer produces its report in the format specified by review.md
(fenced markdown block, `---BEGIN-REVIEW---` markers, structured JSON
verdict). The operator copies this block into the Work Journal conversation
alongside the close-out.

## Operator Handoff

After both close-out and review reports are produced, display to the operator:

1. **The close-out markdown block** (for Work Journal paste)
2. **The review markdown block** (for Work Journal paste)
3. **A one-line summary:** `Session FIX-15 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai
conversation. The summary line is for terminal visibility only.

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions (DEF-150 flake is the only expected failure)
- [ ] Close-out report produced per `workflow/claude/skills/close-out.md` (`---BEGIN-CLOSE-OUT---` block + `json:structured-closeout` appendix)
- [ ] Self-assessment CLEAN or MINOR_DEVIATIONS (FLAGGED → pause and escalate before commit)
- [ ] Commit pushed to `main` with the exact message format above (unless FLAGGED)
- [ ] Tier 2 `@reviewer` subagent invoked per `workflow/claude/skills/review.md`; `---BEGIN-REVIEW---` block produced
- [ ] Close-out block + review block displayed to operator for Work Journal paste
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-15-docs-supporting**`

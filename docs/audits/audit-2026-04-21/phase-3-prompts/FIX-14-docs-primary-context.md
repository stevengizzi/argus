# Fix Session FIX-14-docs-primary-context: docs/ — primary Claude context files

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 20
**Files touched:** `CLAUDE.md`, `docs/architecture.md`, `docs/project-knowledge.md`
**Safety tag:** `safe-during-trading`
**Theme:** Updates to CLAUDE.md, docs/project-knowledge.md, docs/architecture.md, docs/roadmap.md — the primary documents Claude reads at every session start.

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
marker (`audit(FIX-14): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `CLAUDE.md`: 9 findings
- `docs/project-knowledge.md`: 9 findings
- `docs/architecture.md`: 2 findings

## Findings to Fix

### Finding 1: `H1A-01` [MEDIUM]

**File/line:** CLAUDE.md:10-24
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Relocate 5 sprint follow-on paragraphs (31.85, 31.75, 31.8, Apr 3-5, 31.5) to sprint-history.md

**Impact:**

> Claude reads CLAUDE.md on every session; archaeology bloats context by ~4KB per session

**Suggested fix:**

> Cut paragraphs at L:10, 12, 14, 16, 18 from CLAUDE.md; append full text to sprint-history.md if not already there

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 2: `H1A-02` [MEDIUM]

**File/line:** CLAUDE.md:20-24
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Relocate Sprint 31A.75/31A.5/31A "Previous" paragraphs to sprint-history.md

**Impact:**

> Same as H1A-01 — sprint-level detail in context-load file

**Suggested fix:**

> Remove L:20-24; verify sprint-history.md has the same content; add a single-line link back

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 3: `H1A-03` [MEDIUM]

**File/line:** CLAUDE.md:26-37
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Trim roadmap amendments + build track section; replace with "Next: 31B" + link to roadmap.md

**Impact:**

> Build track with ~23 strikethrough entries; roadmap.md is authoritative

**Suggested fix:**

> Remove L:26-37; replace with single pointer line to docs/roadmap.md#current-queue

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 4: `H1A-04` [MEDIUM]

**File/line:** CLAUDE.md:54
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Split "Infrastructure" megaline (~4.1KB in one line) into structured bullets or relocate to project-knowledge.md

**Impact:**

> One-line walls of prose are unreadable and duplicate project-knowledge.md

**Suggested fix:**

> Break into ~20 short bullets OR relocate to project-knowledge.md L:130 area (which already hosts similar content)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 5: `H1A-05` [MEDIUM]

**File/line:** CLAUDE.md:263-416
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Collapse ~80 resolved DEF rows from full descriptions to one-line strikethrough pointers

**Impact:**

> DEF table is 153 rows; ~80 are strikethrough with multi-line descriptions. Each description belongs in sprint-history.md

**Suggested fix:**

> For each strikethrough DEF row, replace full description with "~~DEF-NNN~~ Brief name — RESOLVED Sprint X (see sprint-history)"; move detail to sprint-history.md

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 6: `H1A-06` [LOW]

**File/line:** CLAUDE.md:265-269
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Remove archaeological DEF-001/002/005 entries (resolved ~19 sprints ago, purely historical)

**Impact:**

> No informational value in main context file

**Suggested fix:**

> Delete L:265, 266, 269 entirely; retain in sprint-history.md

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 7: `H1A-07` [LOW]

**File/line:** CLAUDE.md:45-46
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Remove resolved issues with strikethrough from Known Issues section

**Impact:**

> Resolved issues are clutter in an operational section

**Suggested fix:**

> Delete strikethrough lines under "Known Issues"; they belong in resolved DEF records

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 8: `H1A-08` [LOW]

**File/line:** CLAUDE.md:246-253
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Trim Testing section; point to .claude/rules/testing.md (already authoritative)

**Impact:**

> Duplication between CLAUDE.md testing guidance and the authoritative rule file

**Suggested fix:**

> Reduce to one-line pointer: "See `.claude/rules/testing.md` for all testing guidance"

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 9: `H1A-20` [LOW]

**File/line:** CLAUDE.md + project-knowledge.md + architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Fix broken links / relative paths identified in P1-H1A Q7

**Impact:**

> Broken links degrade navigation

**Suggested fix:**

> Repair per P1-H1A Q7 inventory

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 10: `H1A-09` [MEDIUM]

**File/line:** docs/project-knowledge.md:19-101
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Collapse Sprint History table (83 rows) — keep last 10-15 for context, replace pre-Sprint 25 with single pointer

**Impact:**

> Duplicates sprint-history.md which already has all 83 rows

**Suggested fix:**

> Replace L:21-60 with single line "Sprints 1-24: see `docs/sprint-history.md`"; keep most-recent rows for context

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 11: `H1A-10` [MEDIUM]

**File/line:** docs/project-knowledge.md:105
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Split Build Track Queue megaline (~4KB in one paragraph) into structured bullets or 5-line summary

**Impact:**

> Unreadable wall of prose

**Suggested fix:**

> Replace with top-5 upcoming sprints + link to docs/roadmap.md

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 12: `H1A-11` [MEDIUM]

**File/line:** docs/project-knowledge.md:130
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Split completed-infrastructure megaline (~3.5KB in one paragraph); overlaps with CLAUDE.md L:54

**Impact:**

> Duplicate inventory in two files

**Suggested fix:**

> Keep in project-knowledge.md only; remove from CLAUDE.md (or vice versa — operator choice)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 13: `H1A-12` [MEDIUM]

**File/line:** docs/project-knowledge.md:146-169
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Trim Key Components megalines (strategies, patterns, observatory, regime, VIX, market calendar, orchestrator, risk manager, data service, UM, broker, backtesting, evaluation, counterfactual, learning loop, event bus, order manager, exit management, experiment pipeline, historical query, arena — ~20 megaline paragraphs of 2-4KB each)

**Impact:**

> Each component megaline duplicates architecture.md with minor drift; unreadable format

**Suggested fix:**

> Reduce each to 3-4 bullets + pointer to arch.md §3.x; detail stays in arch.md

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 14: `H1A-13` [LOW]

**File/line:** docs/project-knowledge.md:180-204
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Remove File Structure tree; duplicates CLAUDE.md L:59-96

**Impact:**

> Duplicate between two primary-context files

**Suggested fix:**

> Delete L:180-204; CLAUDE.md already has it

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 15: `H1A-14` [MEDIUM]

**File/line:** docs/project-knowledge.md:286-338
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Trim "Key Active Decisions" section; each subsection lists 5-15 DEC numbers, but dec-index.md is authoritative

**Impact:**

> Duplicate between project-knowledge.md and dec-index.md

**Suggested fix:**

> Replace all per-sprint DEC listings with pointer to `docs/dec-index.md`; maybe keep top 5 most-cited DECs

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 16: `H1A-15` [LOW]

**File/line:** docs/project-knowledge.md:342-379
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Trim Workflow section; 12 lines of runner detail belong in workflow/protocols/autonomous-sprint-runner.md

**Impact:**

> Duplicate between project-knowledge and the workflow submodule

**Suggested fix:**

> Reduce to summary + pointer

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 17: `H1A-16` [LOW]

**File/line:** docs/project-knowledge.md:420-424
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Relocate Sprint 31A-era learnings (lookback_bars, PMH, 24-sym set) to sprint-history.md Sprint 31A section

**Impact:**

> Key Learnings should be timeless; sprint-specific lessons accumulate unbounded

**Suggested fix:**

> Move to sprint-history.md; retain in project-knowledge only if genuinely durable pattern

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 18: `H1A-17` [LOW]

**File/line:** docs/project-knowledge.md:427-441
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Filter Sprint 31.85 learnings (10 bullets) — keep 2-3 durable ones; relocate sprint-specific ones

**Impact:**

> Same pattern as H1A-16 — Key Learnings growing unbounded

**Suggested fix:**

> Keep durable learnings (e.g., "ARGUS late-night boot collides with auto-shutdown"); relocate sprint-specific ones

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 19: `H1A-18` [MEDIUM]

**File/line:** docs/architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Rewrite §3.9 startup phase sequence — architecture.md lists 12 phases, actual main.py has 17 (adds 8.5, 10.25, 10.3, 10.5 Event Routing, 10.7)

**Impact:**

> Architecture.md is silently wrong; any new contributor builds incorrect mental model

**Suggested fix:**

> Enumerate all 17 actual phases; cross-ref main.py:204-1361

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

### Finding 20: `H1A-19` [MEDIUM]

**File/line:** docs/architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Architecture.md target: ~1,500 lines (from 2,819). Triage 60+ sections: ~30 KEEP, 20 TRIM, 8 RELOCATE, 5 REMOVE

**Impact:**

> 2,819 lines is a compression target itself — reference doc that has accumulated archaeology

**Suggested fix:**

> Section-level triage per P1-H1A Q4 table; relocate DEC-log content, remove sprint-specific narrative

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-14-docs-primary-context**`.

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
| ... | ~~description~~ **RESOLVED FIX-14-docs-primary-context** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-14-docs-primary-context**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-14): primary Claude-context docs refresh

Addresses audit findings:
- H1A-01 [MEDIUM]: Relocate 5 sprint follow-on paragraphs (31
- H1A-02 [MEDIUM]: Relocate Sprint 31A
- H1A-03 [MEDIUM]: Trim roadmap amendments + build track section; replace with "Next: 31B" + link to roadmap
- H1A-04 [MEDIUM]: Split "Infrastructure" megaline (~4
- H1A-05 [MEDIUM]: Collapse ~80 resolved DEF rows from full descriptions to one-line strikethrough pointers
- H1A-06 [LOW]: Remove archaeological DEF-001/002/005 entries (resolved ~19 sprints ago, purely historical)
- H1A-07 [LOW]: Remove resolved issues with strikethrough from Known Issues section
- H1A-08 [LOW]: Trim Testing section; point to
- H1A-20 [LOW]: Fix broken links / relative paths identified in P1-H1A Q7
- H1A-09 [MEDIUM]: Collapse Sprint History table (83 rows) — keep last 10-15 for context, replace pre-Sprint 25 with single pointer
- H1A-10 [MEDIUM]: Split Build Track Queue megaline (~4KB in one paragraph) into structured bullets or 5-line summary
- H1A-11 [MEDIUM]: Split completed-infrastructure megaline (~3
- H1A-12 [MEDIUM]: Trim Key Components megalines (strategies, patterns, observatory, regime, VIX, market calendar, orchestrator, risk manag
- H1A-13 [LOW]: Remove File Structure tree; duplicates CLAUDE
- H1A-14 [MEDIUM]: Trim "Key Active Decisions" section; each subsection lists 5-15 DEC numbers, but dec-index
- H1A-15 [LOW]: Trim Workflow section; 12 lines of runner detail belong in workflow/protocols/autonomous-sprint-runner
- H1A-16 [LOW]: Relocate Sprint 31A-era learnings (lookback_bars, PMH, 24-sym set) to sprint-history
- H1A-17 [LOW]: Filter Sprint 31
- H1A-18 [MEDIUM]: Rewrite §3
- H1A-19 [MEDIUM]: Architecture

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-14-docs-primary-context**`

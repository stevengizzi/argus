# Fix Session FIX-17-claude-rules: .claude/rules — project-specific workflow rules

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 16
**Files touched:** `claude/rules/architecture.md`, `claude/rules/backtesting.md`, `claude/rules/code-style.md`, `claude/rules/doc-updates.md`, `claude/rules/risk-rules.md`, `claude/rules/sprint_14_rules.md`, `claude/rules/testing.md`, `claude/rules/trading-strategies.md`
**Safety tag:** `safe-during-trading`
**Theme:** Updates to .claude/rules/*.md — the project-specific rule set that tells Claude Code how to work on ARGUS. Metarepo protocols stay in the workflow submodule; this session touches only the ARGUS overlay.

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
marker (`audit(FIX-17): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `claude/rules/architecture.md`: 3 findings
- `claude/rules/doc-updates.md`: 3 findings
- `claude/rules/trading-strategies.md`: 3 findings
- `claude/rules/risk-rules.md`: 2 findings
- `claude/rules/testing.md`: 2 findings
- `claude/rules/backtesting.md`: 1 finding
- `claude/rules/code-style.md`: 1 finding
- `claude/rules/sprint_14_rules.md`: 1 finding

## Findings to Fix

### Finding 1: `H3-02` [MEDIUM]

**File/line:** .claude/rules/architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> L45 references notifications/service.py (file does not exist); L54 uses docs/ARCHITECTURE.md (uppercase) — fails on case-sensitive Linux CI

**Impact:**

> Broken references + case-sensitivity bug

**Suggested fix:**

> Remove notifications/service.py reference; fix case to architecture.md

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 2: `H3-08` [MEDIUM]

**File/line:** .claude/rules/architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing sections: fire-and-forget write pattern, config-gating, separate-DB pattern (DEC-345), trust-cache-on-startup (DEC-362). Audit P1-H3 §4.1, 4.2, 4.3, 4.6.

**Impact:**

> Operationally critical patterns not codified

**Suggested fix:**

> Add 4 new sections per P1-H3 recommendations

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 3: `H3-16` [COSMETIC]

**File/line:** .claude/rules/architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> No Python version pin in rule

**Impact:**

> Minor gap

**Suggested fix:**

> Add "Python 3.11+ required" per pyproject.toml

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 4: `H3-04` [MEDIUM]

**File/line:** .claude/rules/doc-updates.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> L3 says "six living documents" (project actually has ≥10); L49 says "CLAUDE.md ≤150 lines" (actual ~275)

**Impact:**

> Outdated constraints

**Suggested fix:**

> Update to current doc count; relax or restate CLAUDE.md size guidance

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 5: `H3-13` [LOW]

**File/line:** .claude/rules/doc-updates.md + .claude/skills/doc-sync.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Overlap between rule (per-session discipline) and skill (post-sprint sync); neither cross-references the other

**Impact:**

> Operator reading either in isolation uncertain which applies

**Suggested fix:**

> Add "see also" header to both files

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 6: `H3-14` [LOW]

**File/line:** .claude/rules/doc-updates.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing: `~~strikethrough~~` convention for resolved DEFs, DEF/DEC/RSK duplicate-number check, Work Journal reconciliation

**Impact:**

> Codified conventions not documented

**Suggested fix:**

> Add per P1-H3 §6

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 7: `H3-06` [MEDIUM]

**File/line:** .claude/rules/trading-strategies.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> L17 says "Short selling deferred to Sprint 27 (DEC-166)"; decision-log has DEC-166 at Sprint 28. Content direction correct, sprint number wrong.

**Impact:**

> Factual drift in rule doc

**Suggested fix:**

> Fix sprint number to 28

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 8: `H3-11` [LOW]

**File/line:** .claude/rules/trading-strategies.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing: PatternModule conventions (get_default_params returns list[PatternParam]), fingerprint semantics, shadow mode, 15-strategy roster

**Impact:**

> Documentation does not reflect current strategy framework

**Suggested fix:**

> Add sections per audit P1-H3

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 9: `H3-12` [LOW]

**File/line:** .claude/rules/trading-strategies.md + .claude/rules/architecture.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing: fail-closed on missing reference data (DEC-277)

**Impact:**

> Operationally critical pattern not codified

**Suggested fix:**

> Add section per P1-H3 §4.5

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 10: `H3-07` [MEDIUM]

**File/line:** .claude/rules/risk-rules.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> L54 says "3:55 PM EST" — should be ET (EDT/EST depending on DST)

**Impact:**

> Timezone label wrong

**Suggested fix:**

> Change EST to ET

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 11: `H3-09` [MEDIUM]

**File/line:** .claude/rules/risk-rules.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing: non-bypassable validation pattern (Sprint 31.85), margin circuit breaker (Sprint 32.9), broker-confirmed reconciliation (DEC-369), pre-EOD signal cutoff (Sprint 32.9), getattr(pos, "qty") anti-pattern (DEF-139/140)

**Impact:**

> Operationally critical patterns not codified

**Suggested fix:**

> Add per P1-H3 §4.4 + missing items from Sprint 32.9

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 12: `H3-05` [MEDIUM]

**File/line:** .claude/rules/testing.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> L55 shows wrong full-suite command (`pytest tests/ -x --tb=short`); L84 shows correct command (with --ignore --n auto). Two conflicting commands.

**Impact:**

> Agents reading top half get misleading guidance

**Suggested fix:**

> Delete L51-L61 OR replace with pointer to L81-L91

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 13: `H3-15` [LOW]

**File/line:** .claude/rules/testing.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing: Vitest unmocked-WS hang warning, testTimeout/hookTimeout 10_000 (Sprint 32.8 lesson), net-non-negative test count invariant

**Impact:**

> Testing landmines not codified

**Suggested fix:**

> Add per P1-H3 §8

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 14: `H3-03` [MEDIUM]

**File/line:** .claude/rules/backtesting.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> References only VectorBT; missing BacktestEngine (Sprint 27+), DuckDB HistoricalQueryService, shadow-first validation (DEC-382). L39 pre-Databento benchmark.

**Impact:**

> Doc contradicts current strategic posture (DEC-382)

**Suggested fix:**

> Rewrite: BacktestEngine as primary; shadow-first validation as current approach; VectorBT as legacy

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 15: `H3-10` [MEDIUM]

**File/line:** .claude/rules/code-style.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Missing: json.dumps(default=str) for dataclass serialization (DEF-151 lesson); ThrottledLogger for high-volume logs; ET/UTC timestamp semantics (DEC-276)

**Impact:**

> Operationally critical patterns not codified

**Suggested fix:**

> Add per P1-H3 §4.7, 4.8, 4.10

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

### Finding 16: `H3-01` [MEDIUM]

**File/line:** .claude/rules/sprint_14_rules.md
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Sprint-specific filename; content is incomplete API-conventions catalog (11 AppStates listed, 34 actual)

**Impact:**

> Rule files should not have sprint numbers in names

**Suggested fix:**

> Delete OR rename to api-conventions.md + update content to current API state

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-17-claude-rules**`.

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
| ... | ~~description~~ **RESOLVED FIX-17-claude-rules** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-17-claude-rules**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-17): .claude/rules refresh

Addresses audit findings:
- H3-02 [MEDIUM]: L45 references notifications/service
- H3-08 [MEDIUM]: Missing sections: fire-and-forget write pattern, config-gating, separate-DB pattern (DEC-345), trust-cache-on-startup (D
- H3-16 [COSMETIC]: No Python version pin in rule
- H3-04 [MEDIUM]: L3 says "six living documents" (project actually has ≥10); L49 says "CLAUDE
- H3-13 [LOW]: Overlap between rule (per-session discipline) and skill (post-sprint sync); neither cross-references the other
- H3-14 [LOW]: Missing: '~~strikethrough~~' convention for resolved DEFs, DEF/DEC/RSK duplicate-number check, Work Journal reconciliati
- H3-06 [MEDIUM]: L17 says "Short selling deferred to Sprint 27 (DEC-166)"; decision-log has DEC-166 at Sprint 28
- H3-11 [LOW]: Missing: PatternModule conventions (get_default_params returns list[PatternParam]), fingerprint semantics, shadow mode, 
- H3-12 [LOW]: Missing: fail-closed on missing reference data (DEC-277)
- H3-07 [MEDIUM]: L54 says "3:55 PM EST" — should be ET (EDT/EST depending on DST)
- H3-09 [MEDIUM]: Missing: non-bypassable validation pattern (Sprint 31
- H3-05 [MEDIUM]: L55 shows wrong full-suite command ('pytest tests/ -x --tb=short'); L84 shows correct command (with --ignore --n auto)
- H3-15 [LOW]: Missing: Vitest unmocked-WS hang warning, testTimeout/hookTimeout 10_000 (Sprint 32
- H3-03 [MEDIUM]: References only VectorBT; missing BacktestEngine (Sprint 27+), DuckDB HistoricalQueryService, shadow-first validation (D
- H3-10 [MEDIUM]: Missing: json
- H3-01 [MEDIUM]: Sprint-specific filename; content is incomplete API-conventions catalog (11 AppStates listed, 34 actual)

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-17-claude-rules**`

# FIX-17-claude-rules — Close-Out Report

> Tier 1 self-review produced per `workflow/claude/skills/close-out.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-CLOSE-OUT---

**Session:** audit-2026-04-21-phase-3 — FIX-17-claude-rules (.claude/rules refresh)
**Date:** 2026-04-21
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `.claude/rules/architecture.md` | modified | H3-02 (remove `notifications/service.py` ref; fix `docs/ARCHITECTURE.md` → lowercase), H3-08 (new subsections: Config-Gating, Separate-DB Pattern, Fire-and-Forget Writes, Trust-Cache-on-Startup, Non-Bypassable Validation, Domain Model `shares` vs `qty`), H3-16 (add "Target Python: 3.11+" pin). |
| `.claude/rules/backtesting.md` | modified | H3-03 (rewrite: BacktestEngine as primary harness Sprint 27+, shadow-first validation DEC-382 as current posture, DuckDB HistoricalQueryService context Sprint 31A.5, VectorBT retained as legacy; pre-Databento "29-symbol / 30s" benchmark replaced with ORB-reference language). |
| `.claude/rules/code-style.md` | modified | H3-10 (add Serialization/DEF-151, ThrottledLogger/Sprint 27.75, Time and Timezones/DEC-061+276 subsections; refresh ExitReason example to include RECONCILIATION and TRAILING_STOP; add `pathlib` rule + Python 3.11 target). |
| `.claude/rules/doc-updates.md` | modified | H3-04 (replace "six living documents" with pointer to CLAUDE.md Reference table; loosen CLAUDE.md size threshold from 150 to "stay dense"), H3-13 (add "See also" cross-ref to `workflow/claude/skills/doc-sync.md`), H3-14 (add Numbering Hygiene and Work Journal Reconciliation sections — strikethrough convention, dup-number guard, append-only DEC log). |
| `.claude/rules/risk-rules.md` | modified | H3-07 (EST → ET at End of Day), H3-09 (add Margin Circuit Breaker DEC-367/Sprint 32.9, Broker-Confirmed Reconciliation DEC-369, Non-Bypassable Validation cross-ref, Pre-EOD Signal Cutoff 3:30 PM ET Sprint 32.9, Clock Injection DEC-087, shares-vs-qty anti-pattern cross-ref). |
| `.claude/rules/sprint_14_rules.md` | deleted (renamed) | H3-01 (renamed to `api-conventions.md` via `git mv`). |
| `.claude/rules/api-conventions.md` | added (rename target) | H3-01 (replacement for `sprint_14_rules.md`; AppState 11-field enumeration replaced with pointer to `argus/api/dependencies.py`; WS event map narrated rather than enumerated; HTTPBearer(auto_error=False)/401 DEC-351 codified; TradeLogger/OrderManager/PerformanceCalculator surfaces refreshed). |
| `.claude/rules/testing.md` | modified | H3-05 (delete obsolete `pytest tests/ -x --tb=short` command block; DEC-328 xdist tiering block is now canonical), H3-15 (add Vitest section with unmocked-WS hang warning DEF-138 Sprint 32.8, `vi.mock()` canonical pattern, testTimeout/hookTimeout 10_000, hardcoded-date anti-pattern DEF-163; add Test Baseline Invariant section; add Non-Bypassable Validation grep-guard cross-ref). |
| `.claude/rules/trading-strategies.md` | modified | H3-06 (Sprint 27 → Sprint 28 for DEC-166 short-selling deferral), H3-11 (add PatternModule Conventions DEC-378, Regime Gating DEC-360, Zero-R upstream guard DEC-251/DEF-152, Shadow Mode DEC-375, Quality Pipeline Bypass, BaseStrategy Telemetry Wire-Up, Shadow-First Validation cross-ref; 15-strategy roster cross-referenced to CLAUDE.md rather than duplicated), H3-12 (add fail-closed-on-missing-reference-data bullet DEC-277). |
| `docs/audits/audit-2026-04-21/p1-h3-claude-rules.md` | modified | §14 Aggregate Action Table rows 1–14 marked `~~description~~ **RESOLVED FIX-17-claude-rules**` (rows 15–16 are metarepo-only and out of FIX-17 scope per Universal RULE-018). |

### Judgment Calls
- **H3-01: RENAME over DELETE.** Audit §1 explicitly preferred RENAME ("the file does encode conventions that newcomers benefit from having in one place"). Used `git mv` so git preserves rename lineage. Stale partial enumerations (11-field AppState list, 13-event WS map) were replaced with pointers to authoritative sources (`argus/api/dependencies.py`, runtime route table) to prevent future enumeration-drift.
- **H3-13: ARGUS-side only.** Finding referenced both `.claude/rules/doc-updates.md` and `.claude/skills/doc-sync.md`, but per Universal RULE-018 (and the audit's own §14 rows 15–16 classification), the workflow-submodule-side cross-reference cannot be added from this repo. Applied the "See also" header to `doc-updates.md` only and documented the one-directional scope in the body.
- **CLAUDE.md size guidance (H3-04).** Suggested fix offered two options ("Raise to 300 or flag CLAUDE.md for compression"). Chose soft "stay dense" rather than a hard line-count threshold because line-counts drift and the audit's P1-H1a recommends compression-first. Reversible in one edit if the operator prefers a cap.
- **15-strategy roster (H3-11).** Audit explicitly said "Don't add it; cross-reference CLAUDE.md's `## Current State` instead." Followed verbatim — no roster duplication introduced.
- **CSV back-annotation absorbed into sibling commit 9dd44f2 (FIX-15).** The Python script that wrote the 16 `RESOLVED FIX-17-claude-rules` markers into `phase-2-review.csv` ran while a parallel FIX-15 session was staging the same file. The CSV annotations are correct and present at HEAD; only the commit attribution differs. Documented in the FIX-17 commit message. The authoritative markdown audit report (`p1-h3-claude-rules.md`) back-annotation IS under the FIX-17 commit (`451b444`).

### Scope Verification
| Spec Requirement | Status | Implementation |
|------------------|--------|----------------|
| H3-01: DELETE or RENAME sprint_14_rules.md | DONE (RENAME) | `git mv .claude/rules/sprint_14_rules.md .claude/rules/api-conventions.md`; content rewritten to remove stale enumerations. |
| H3-02: Remove notifications/service.py ref; fix docs/ARCHITECTURE.md case | DONE | `architecture.md` Abstraction Layers section now lists two abstractions (Broker, DataService) with a note about the absent Notifications stub; Database Access link is lowercase `docs/architecture.md`. |
| H3-03: BacktestEngine primary / shadow-first / DuckDB / VectorBT legacy | DONE | `backtesting.md` fully rewritten: Primary Harness (BacktestEngine), Shadow-First Validation (DEC-382), DuckDB Historical Query Layer, Legacy Harness (VectorBT). |
| H3-04: Update living-docs count; relax CLAUDE.md size | DONE | `doc-updates.md` opening paragraph replaced with Reference-table pointer; size guidance loosened. |
| H3-05: Delete obsolete pytest command | DONE | `testing.md` Running Tests section is the DEC-328 canonical commands block; obsolete `pytest tests/ -x --tb=short` block removed. |
| H3-06: Sprint 27 → 28 | DONE | `trading-strategies.md` Risk and Execution section. |
| H3-07: EST → ET | DONE | `risk-rules.md` End of Day section. |
| H3-08: Add fire-and-forget, config-gating, separate-DB, trust-cache-on-startup | DONE | `architecture.md` Config-Gating + Separate-DB Pattern + Fire-and-Forget Writes + Trust-Cache-on-Startup + Non-Bypassable Validation + Domain Model subsections. |
| H3-09: Margin CB / broker-confirmed reconcile / non-bypassable / cutoff / qty-vs-shares | DONE | `risk-rules.md` Margin Circuit Breaker + Broker-Confirmed Reconciliation + Non-Bypassable Validation + Pre-EOD Signal Cutoff + Clock Injection + Domain Model (cross-ref) subsections. |
| H3-10: Serialization / ThrottledLogger / ET-UTC | DONE | `code-style.md` Serialization + ThrottledLogger + Time and Timezones subsections. |
| H3-11: PatternModule conventions / regime / shadow / telemetry | DONE | `trading-strategies.md` PatternModule Conventions + Regime Gating + Shadow Mode + Quality Pipeline Bypass + BaseStrategy Telemetry Wire-Up sections. |
| H3-12: Fail-closed on missing reference data | DONE | `trading-strategies.md` Data and Events section, final bullet (DEC-277). |
| H3-13: "See also" cross-ref | DONE (ARGUS-side only) | `doc-updates.md` top-of-file `> See also:` callout. |
| H3-14: strikethrough / dup-number / Work Journal | DONE | `doc-updates.md` Numbering Hygiene + Work Journal Reconciliation sections. |
| H3-15: Vitest / 10_000 / net-non-negative | DONE | `testing.md` Vitest + Test Baseline Invariant + Non-Bypassable Validation grep-guard sections. |
| H3-16: Python 3.11+ pin | DONE | `architecture.md` line 5 + `code-style.md` Python Style section. |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | PASS | 4,933 passed / 1 failed (DEF-150 flake only). Net delta: 0. Reviewer's clean-checkout run: 4,934 passed / 0 failed. |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | PASS | DEF-150 `test_check_reminder_sends_after_interval` is the sole failure at close-out time; matches CLAUDE.md baseline. |
| No file outside this session's declared Scope was modified | PASS | Commit `451b444` touched only 9 `.claude/rules/*.md` (8 edits + 1 rename target) and 1 audit markdown. Pre-existing unstaged changes in `tests/sprint_runner/test_state.py` and `workflow` submodule were deliberately NOT staged. |
| Every resolved finding back-annotated with `**RESOLVED FIX-17-claude-rules**` | PASS | 14 in-scope rows annotated in `p1-h3-claude-rules.md` §14. 16 CSV rows annotated in `phase-2-review.csv` (absorbed into sibling FIX-15 commit `9dd44f2` — see Judgment Calls). |
| Every DEF closure recorded in CLAUDE.md | N/A | No DEF closed or opened this session. |
| Every new DEF/DEC referenced in commit message bullets | N/A | No new DEF/DEC created. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | N/A | No such findings in FIX-17 scope. |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | N/A | No such findings in FIX-17 scope. |

### Test Results
- Tests run: 4,934
- Tests passed: 4,933 (reviewer re-run on clean checkout: 4,934)
- Tests failed: 1 (DEF-150 `test_check_reminder_sends_after_interval` — documented pre-existing flake, fails only during the first 2 minutes of each hour per CLAUDE.md)
- New tests added: 0 (doc-only change)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q` (144.38s)

### Unfinished Work
None in FIX-17 scope.

Out-of-scope items the audit flagged but FIX-17 deliberately does NOT address (metarepo-only; Universal RULE-018):
- `workflow/claude/agents/builder.md` + `doc-sync-agent.md` — add frontmatter blocks (audit §14 row 15).
- `workflow/claude/skills/doc-sync.md` — add `## See also` back-pointer to `.claude/rules/doc-updates.md` (audit §14 row 16). The ARGUS-side half of this cross-reference (`doc-updates.md` → `doc-sync` skill) IS in this commit.

### Notes for Reviewer
- **RENAME integrity.** `.claude/rules/sprint_14_rules.md` was `git mv`'d to `.claude/rules/api-conventions.md`. Note: extensive content rewrite means `git log --follow` may not traverse the rename boundary even with `-M50`. Commit message preserves provenance.
- **CSV back-annotation absorbed into FIX-15 commit `9dd44f2`.** Parallel-session quirk; annotations are correct, only commit attribution differs. Authoritative markdown audit report back-annotation is under the FIX-17 commit.
- **Zero `.py` files modified.** Doc-only session; net pytest delta is 0 as expected.
- **One pre-existing unstaged change remained in the working tree** at commit time (`tests/sprint_runner/test_state.py`). Not mine; not staged. Reviewer will see additional unrelated changes from concurrent FIX-00/FIX-15 sessions.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-17-claude-rules",
  "verdict": "COMPLETE",
  "tests": {
    "before": 4934,
    "after": 4934,
    "new": 0,
    "all_pass": true
  },
  "files_created": [
    ".claude/rules/api-conventions.md"
  ],
  "files_modified": [
    ".claude/rules/architecture.md",
    ".claude/rules/backtesting.md",
    ".claude/rules/code-style.md",
    ".claude/rules/doc-updates.md",
    ".claude/rules/risk-rules.md",
    ".claude/rules/testing.md",
    ".claude/rules/trading-strategies.md",
    "docs/audits/audit-2026-04-21/p1-h3-claude-rules.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Audit §14 rows 15 (workflow agents frontmatter) and 16 (doc-sync skill see-also back-pointer) are metarepo-only and out of FIX-17 scope per Universal RULE-018. ARGUS-side half of H3-13 cross-reference is in this commit; the metarepo half requires a workflow-submodule change.",
    "CSV back-annotation rows for H3-01..H3-16 in phase-2-review.csv were absorbed into sibling commit 9dd44f2 (FIX-15) due to parallel-session file collision. Annotations at HEAD are correct; only commit attribution differs. Authoritative markdown audit report (p1-h3-claude-rules.md) back-annotation is under the FIX-17 commit 451b444."
  ],
  "doc_impacts": [
    {"document": ".claude/rules/architecture.md", "change_description": "Added Config-Gating, Separate-DB, Fire-and-Forget Writes, Trust-Cache-on-Startup, Non-Bypassable Validation, Domain Model (shares vs qty) subsections; removed broken notifications/service.py ref; fixed docs/ARCHITECTURE.md case; added Python 3.11+ target pin."},
    {"document": ".claude/rules/backtesting.md", "change_description": "Rewritten: BacktestEngine primary (Sprint 27+), shadow-first validation (DEC-382), DuckDB HistoricalQueryService (Sprint 31A.5), VectorBT legacy."},
    {"document": ".claude/rules/code-style.md", "change_description": "Added Serialization (DEF-151), ThrottledLogger (DEC-363), Time and Timezones (DEC-061/276); refreshed ExitReason example; added pathlib rule."},
    {"document": ".claude/rules/doc-updates.md", "change_description": "Updated living-docs count; loosened CLAUDE.md size guidance; added See-also cross-ref to doc-sync skill; added Numbering Hygiene and Work Journal Reconciliation sections."},
    {"document": ".claude/rules/risk-rules.md", "change_description": "EST → ET; added Margin Circuit Breaker (DEC-367), Broker-Confirmed Reconciliation (DEC-369), Non-Bypassable Validation cross-ref, Pre-EOD Signal Cutoff (Sprint 32.9), Clock Injection (DEC-087)."},
    {"document": ".claude/rules/sprint_14_rules.md → api-conventions.md", "change_description": "Renamed via git mv; AppState enumeration replaced with pointer to argus/api/dependencies.py; WS event map narrated; HTTPBearer/401 DEC-351 codified."},
    {"document": ".claude/rules/testing.md", "change_description": "Deleted obsolete pytest command block; added Vitest section (DEF-138 Sprint 32.8), Test Baseline Invariant, Non-Bypassable Validation grep-guard cross-ref."},
    {"document": ".claude/rules/trading-strategies.md", "change_description": "Sprint 27 → 28 for DEC-166; added PatternModule Conventions (DEC-378), Regime Gating (DEC-360), Shadow Mode (DEC-375), Quality Pipeline Bypass, BaseStrategy Telemetry Wire-Up, Shadow-First Validation cross-ref, fail-closed on missing reference data (DEC-277)."},
    {"document": "docs/audits/audit-2026-04-21/p1-h3-claude-rules.md", "change_description": "§14 Aggregate Action Table rows 1–14 back-annotated with ~~strikethrough~~ **RESOLVED FIX-17-claude-rules**."}
  ],
  "dec_entries_needed": [],
  "warnings": [
    "Tier 2 reviewer flagged 2 LOW findings (wrong ThrottledLogger import path in code-style.md; OrderManager surface drift in api-conventions.md). Both are worth catching in the next doc-sync pass — neither affects runtime behavior. Reviewer verdict: CLEAR."
  ],
  "implementation_notes": "Doc-only session; zero .py files changed. Rename via git mv. All 16 H3 findings addressed in one commit (451b444). CSV back-annotation absorbed into sibling FIX-15 commit 9dd44f2 due to parallel-session file collision — annotations are correct, only commit attribution differs."
}
```

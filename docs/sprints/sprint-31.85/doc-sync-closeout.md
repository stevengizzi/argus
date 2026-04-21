---BEGIN-DOC-SYNC---

**Sprint:** 31.85 (Parquet Cache Consolidation — impromptu, single session)
**Date:** 2026-04-20

### Pre-flight: Sprint 31.8 Sync Completeness

Verified before starting. `docs/sprints/sprint-31.8/session-5-doc-sync-closeout.md` confirms full sync
completed on 2026-04-20 (commit 9bdef1b for file reorg; project-knowledge, dec-index, decision-log,
CLAUDE, sprint-history, roadmap all updated; integrity checks clean). No 31.8 gaps carried into this
sync pass.

### Checklist Status

| Item | Status | Notes |
|------|--------|-------|
| `CLAUDE.md` — header date, new 31.85 follow-on paragraph, test count 4,919 → 4,934, Known Issues expanded for DEF-163 + DEF-150 reconfirmation, Infrastructure bullet adds consolidation tooling, DEF table marks DEF-161 resolved and adds DEF-162/163, DEF-150 description updated, decision-log reference footer updated to 383 DECs | **DONE** | Verified line-by-line. |
| `docs/project-knowledge.md` — header date, test count, sprints-completed list, active sprint line, Sprint History table adds 31.85 row, "Next" line marks DEF-161 resolved, three new key-learnings bullets (Parquet cache separation / non-bypassable validation / read-only invariant test) | **DONE** | |
| `docs/sprint-history.md` — header totals updated (45 sub-sprints, 10 impromptus), AW quick-ref row added, full Sprint 31.85 narrative section inserted between Session 4 and Sprint Statistics, Sprint Statistics totals refreshed (pytest 4,934; decisions 383; sessions ~555+; impromptus 10) | **DONE** | |
| `docs/risk-register.md` — RSK-051 (DuckDB unusable on 983K-file cache) Mitigation rewritten to point to Sprint 31.85 resolution; Status now "Mitigated — pending operator activation" | **DONE** | No DEF tracking in this doc; DEFs live in `CLAUDE.md`. |
| `docs/dec-index.md` — header regeneration date updated; new "Sprint 31.85 — Parquet Cache Consolidation" section stating "No new DECs" with pattern-alignment rationale (5 bullets); "Next DEC: 384" unchanged | **DONE** | DEC count 383 unchanged. |
| `docs/roadmap.md` — "Current state" line updated to Sprint 31.85 + 4,934 pytest; Sprint 31B "Prerequisite" note rewritten from "blocked by DEF-161" to "Prerequisite cleared (Sprint 31.85)" | **DONE** | |
| `docs/architecture.md` — Cache Separation subsection promoted into §3.8.2 (Historical Query Service); Cache Separation table, invariant text, and consolidation-tooling paragraph added ahead of the existing Design/Query Methods content; no structural reordering of other sections | **DONE** | As recommended in the session-1 prompt. |
| Auto memory `MEMORY.md` — Current State block adds Sprint 31.85 summary; open-DEF list updated (161 resolved; 162/163 added); test count refreshed; full sprint-specific "Sprint 31.85 additions" paragraph added to Key Architecture Notes; four new Key Learnings entries | **DONE** | |

### New Entries Created

- **DEF-162** (opened): Monthly re-consolidation cron scheduling for `scripts/consolidate_parquet_cache.py`. Companion to DEF-097 (`populate_historical_cache.py --update` cron). Priority: LOW.
- **DEF-163** (opened): Date-decay test hygiene batch — covers `test_get_todays_pnl_excludes_unrecoverable` (DEF-159-adjacent) and `test_history_store_migration` (reconfirmed-decay despite Sprint 32.8 partial fix). Same root-cause class as DEF-137. Priority: LOW.
- **DEF-150** (description updated, not newly created): reconfirmed pre-existing during Sprint 31.85 Tier 2 review.
- **DEF-161** (marked resolved): Sprint 31.85 delivers `scripts/consolidate_parquet_cache.py` + tests + `docs/operations/parquet-cache-layout.md`.
- **No new DECs.** Cache separation, output layout, non-bypassable validation posture, and repoint-as-operator-action all follow established patterns (DEC-345 storage-separation, regexp_extract continuity, DEC-300 config-gating posture).
- **No new RSKs.** RSK-051 was open for this exact failure mode and is now marked Mitigated.
- **No new ASMs.**

### Compression Recommendations

None needed. CLAUDE.md (~500 lines), project-knowledge.md (~450 lines), sprint-history.md (~2,950
lines — historical, append-only) all remain proportionate to project complexity. The Deferred Items
table in CLAUDE.md continues to grow as resolved DEFs are struck through rather than removed, which
is intentional (provides an auditable trail of what's been fixed and when).

### New Rules Added

None. No rule-worthy patterns emerged from Sprint 31.85 that aren't already captured. The non-
bypassable-validation posture is project-specific rather than universal and is documented inline in
`docs/operations/parquet-cache-layout.md` and the `test_no_bypass_flag_exists` regression test.

### Integrity Issues Found

- **Stale DEC count in `sprint-history.md` Sprint Statistics section.** Previous sync left "Total
  decisions: 381" — corrected to 383 (DEC-382/383 were added in Sprint 31.75 but the summary line
  was not touched). Fixed in this sync.
- **CLAUDE.md Reference table previously said "All 381 DEC entries"** — corrected to "All 383 DEC
  entries" in this sync.
- **Sprint 31.8 sync left `sprint-history.md` header at "34 full sprints + 44 sub-sprints + 9
  impromptus"** (the body table and Statistics section show different totals). Updated header to
  "45 sub-sprints + 10 impromptus" to match the Statistics section (which now also reflects the
  31.85 +1). The 44→45 delta is because 31.75 was already counted in the Statistics list but not
  the header sentence.
- No duplicate DEC/RSK/DEF numbers. No broken cross-references. Superseded decisions remain
  correctly marked.

### Work Journal Reconciliation

Work Journal Close-Out not provided — the session-1 prompt and close-out named DEF-162 and DEF-163
as the new items, which this sync assigned accordingly (next available after DEF-161). DEF-150
description was updated in place rather than duplicated. The developer should verify DEF-162/163
numbering matches any work-journal record they keep separately.

---END-DOC-SYNC---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "Sprint 31.85",
  "session": "doc-sync",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5780,
    "after": 5780,
    "new": 0,
    "all_pass": "n/a (documentation-only session)",
    "pytest_count": 4934,
    "vitest_count": 846
  },
  "files_created": [
    "docs/sprints/sprint-31.85/doc-sync-closeout.md"
  ],
  "files_modified": [
    "CLAUDE.md",
    "docs/project-knowledge.md",
    "docs/sprint-history.md",
    "docs/risk-register.md",
    "docs/dec-index.md",
    "docs/roadmap.md",
    "docs/architecture.md",
    "/Users/stevengizzi/.claude/projects/-Users-stevengizzi-Documents-Coding-Projects-argus/memory/MEMORY.md"
  ],
  "files_should_not_have_modified": [
    "config/historical_query.yaml",
    "argus/**",
    "tests/**",
    "scripts/consolidate_parquet_cache.py",
    "docs/operations/parquet-cache-layout.md"
  ],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [
    "DEF-161 resolved across CLAUDE.md, risk-register.md (RSK-051 mitigated), roadmap.md (Sprint 31B prerequisite cleared), architecture.md (Cache Separation promoted into §3.8.2), project-knowledge.md",
    "DEF-162 opened in CLAUDE.md",
    "DEF-163 opened in CLAUDE.md; 3 pre-existing failures now cross-referenced (DEF-163 × 2 + DEF-150 × 1)",
    "DEF-150 description updated in CLAUDE.md with Sprint 31.85 reconfirmation",
    "Sprint 31.85 section added to sprint-history.md + AW quick-ref row",
    "Cache Separation table promoted from docs/operations/parquet-cache-layout.md into docs/architecture.md §3.8.2"
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Documentation-only session. No runtime code, no tests, no config files modified. Operator repoint of config/historical_query.yaml remains a post-sprint action outside this doc-sync's scope."
}
```

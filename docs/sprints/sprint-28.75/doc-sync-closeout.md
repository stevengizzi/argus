# Sprint 28.75 Doc Sync Close-Out

```markdown
---BEGIN-DOC-SYNC---

**Sprint:** 28.75
**Date:** 2026-03-30

### Checklist Status
| Item | Status | Notes |
|------|--------|-------|
| CLAUDE.md — header, active sprint, build track | DONE | Updated to Sprint 28.75 |
| CLAUDE.md — test counts | DONE | 3,955→3,966 pytest, 680→688 Vitest |
| CLAUDE.md — DEF-102 marked resolved | DONE | Subsumed by DEF-117 |
| CLAUDE.md — DEF-111 through DEF-120 added | DONE | All 10 marked resolved with strikethrough |
| CLAUDE.md — reference table updated | DONE | Sprint history 1–28.75, DEC note updated |
| docs/project-knowledge.md — current state | DONE | Tests, sprints completed, sub-sprint count |
| docs/project-knowledge.md — sprint history table | DONE | Row added for 28.75 |
| docs/project-knowledge.md — build track queue | DONE | ~~28.75~~ ✅ added |
| docs/project-knowledge.md — Order Manager section | DONE | Flatten-pending timeout, ThrottledLogger |
| docs/project-knowledge.md — VIX Data Service section | DONE | Config wiring note (system.yaml, not standalone) |
| docs/project-knowledge.md — Exit Management section | DONE | Trailing stop config status note |
| docs/project-knowledge.md — Frontend mentions | DONE | Covered in Order Manager + sprint table (no separate Frontend section exists) |
| docs/architecture.md — Order Manager section | DONE | Flatten-pending timeout paragraph added |
| docs/architecture.md — API routes | DONE | GET /api/v1/trades/stats added |
| docs/architecture.md — VIX config reference | DONE | Standalone YAML note updated |
| docs/sprint-history.md — Sprint 28.75 entry | DONE | Full entry with both sessions + market observations |
| docs/sprint-history.md — statistics | DONE | 36 sub-sprints, ~453 sessions, 4,654 tests |
| docs/sprint-history.md — timeline overview | DONE | AB phase row added |
| docs/decision-log.md — no changes needed | DONE | No new DECs in Sprint 28.75 |
| docs/dec-index.md — no changes needed | DONE | No new DECs |
| docs/roadmap.md — no changes needed | DONE | Sprint 28.75 doesn't affect roadmap |

### New Entries Created
- DEF-111: Trail stops not firing in live session (RESOLVED)
- DEF-112: Flatten-pending orders hang indefinitely (RESOLVED)
- DEF-113: "flatten already pending" log spam (RESOLVED)
- DEF-114: "IBKR portfolio snapshot missing" log spam (RESOLVED)
- DEF-115: Closed positions tab capped at 50 (RESOLVED)
- DEF-116: TodayStats win rate shows 0% (RESOLVED)
- DEF-117: Trades page stats freeze + filter bug (RESOLVED)
- DEF-118: Avg R missing from Trades page summary (RESOLVED)
- DEF-119: Open positions colored P&L + exit price (RESOLVED)
- DEF-120: VixRegimeCard fills entire viewport (RESOLVED)
- DEF-102: Marked RESOLVED (subsumed by DEF-117)

### Compression Recommendations
**CLAUDE.md** is at 370 lines, well above the ~150 line guidance. The DEF table
alone exceeds 100 entries (many resolved with strikethrough). Recommend:
1. Archive all resolved DEF items (strikethrough rows) to a separate
   `docs/def-archive.md` file, keeping only open/partially-resolved items in
   CLAUDE.md. This would remove ~60+ rows.
2. Consider moving the full DEF table to `docs/deferred-items.md` and keeping
   only a summary count + link in CLAUDE.md.
This is a pre-existing concern — not introduced by Sprint 28.75.

### New Rules Added
None — Sprint 28.75 introduced no patterns warranting new rules.

### Integrity Issues Found
None — all references intact. DEF numbers 111–120 assigned per Work Journal,
no conflicts. DEC count remains 377. Sprint history consistent across all docs.

### Work Journal Reconciliation
- DEF assignments matched: YES — DEF-111 through DEF-120 assigned exactly as
  specified in the Work Journal Close-Out section of the sprint prompt.
- Resolved items excluded: YES — all 10 DEF items are RESOLVED; created as
  resolved entries with strikethrough (not as new open items).
- DEF-102 marked resolved as specified (subsumed by DEF-117).
- New items beyond Work Journal: None.

---END-DOC-SYNC---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "28.75",
  "session": "doc-sync",
  "verdict": "COMPLETE",
  "tests": {
    "before": 4635,
    "after": 4654,
    "new": 0,
    "all_pass": true
  },
  "files_created": [
    "docs/sprints/sprint-28.75/doc-sync-closeout.md"
  ],
  "files_modified": [
    "CLAUDE.md",
    "docs/project-knowledge.md",
    "docs/sprint-history.md",
    "docs/architecture.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "CLAUDE.md at 370 lines — DEF table compression recommended (archive resolved items)"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Documentation-only session. All 10 DEF items (111-120) created as resolved entries per Work Journal. DEF-102 marked resolved (subsumed by DEF-117). VIX config wiring fix documented in VIX Data Service sections. Pre-sprint VIX fix noted in sprint-history entry. No source code, tests, or config files modified."
}
```

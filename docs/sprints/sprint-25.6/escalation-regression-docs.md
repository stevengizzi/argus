# Sprint 25.6 — Escalation Criteria

## Tier 3 Escalation Triggers
1. **DB separation causes data corruption:** If moving to `evaluation.db` results in any data loss or corruption in `argus.db` (trades, quality_history, orchestrator_decisions), halt immediately and escalate.
2. **Regime reclassification excludes strategies unexpectedly:** If the periodic regime update causes strategies to be excluded that were previously active (and the exclusion was not triggered by the operator or circuit breaker), escalate.
3. **Frontend changes break API contract:** If any frontend change requires a corresponding backend API change not scoped in this sprint, escalate rather than making unplanned backend changes.
4. **Test count drops by more than 5:** If tests are deleted or disabled beyond the `test_count_tolerance` of 50, escalate.

## Session-Level Halt Conditions
- Any session that modifies a file listed in the "Do not modify" list
- Any session that introduces new config fields (none planned)
- Pre-flight test failures not attributable to prior session changes

---

# Sprint 25.6 — Regression Checklist

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| 1 | Trades still logged to `argus.db` | `sqlite3 data/argus.db "SELECT COUNT(*) FROM trades"` — count unchanged | S1 |
| 2 | Quality history still in `argus.db` | `sqlite3 data/argus.db "SELECT COUNT(*) FROM quality_history"` — count unchanged | S1 |
| 3 | Catalyst events still in `catalyst.db` | `sqlite3 data/catalyst.db "SELECT COUNT(*) FROM catalyst_events"` — count unchanged | S1 |
| 4 | Evaluation events write to `evaluation.db` | `sqlite3 data/evaluation.db "SELECT COUNT(*) FROM evaluation_events"` — non-zero after candle processing | S1 |
| 5 | No "EvaluationEventStore initialized" spam in logs | `grep "EvaluationEventStore initialized" logs/*.jsonl \| wc -l` — at most 2 (startup) | S1 |
| 6 | Regime reclassifies during market hours | Log shows "Regime reclassified" or "Regime unchanged" entries after 9:35 ET | S2 |
| 7 | Regime does NOT update outside market hours | No regime log entries before 9:30 or after 16:00 ET | S2 |
| 8 | All 4 strategies register and run | Health monitor shows 4/4 strategies healthy | S1, S2 |
| 9 | Trades page shows all trades (no missing rows) | Compare count with `SELECT COUNT(*) FROM trades WHERE ...` | S3 |
| 10 | Trades page summary metrics match full query | Win rate / Net P&L consistent regardless of scroll position | S3 |
| 11 | Dashboard renders all cards without errors | No console errors, all cards visible | S5 |
| 12 | Positions card visible without scrolling on 1080p | Visual verification | S5 |
| 13 | EOD flatten + auto-shutdown still functions | `grep "EOD flatten triggered" logs/*.jsonl` | All |
| 14 | `npx tsc --noEmit` clean | No TypeScript errors | S3, S4, S5 |
| 15 | Full pytest suite passes | `python -m pytest tests/ --ignore=tests/test_main.py -n auto` | Final |
| 16 | Full Vitest suite passes | `cd argus/ui && npx vitest run` | Final |

---

# Sprint 25.6 — Doc Update Checklist

| Document | Updates Needed | Session |
|----------|---------------|---------|
| `docs/project-knowledge.md` | Update test counts, add Sprint 25.6 to history table, add DEC references | Post-sprint |
| `docs/decision-log.md` | New DEC entries: evaluation.db separation, regime reclassification task | Post-sprint |
| `docs/dec-index.md` | Index new DEC entries | Post-sprint |
| `docs/sprint-history.md` | Add Sprint 25.6 entry with session details | Post-sprint |
| `CLAUDE.md` | Resolve DEF-065 through DEF-073, add any new DEF items | Post-sprint |
| `docs/architecture.md` | Note `evaluation.db` as third database file (alongside `argus.db`, `catalyst.db`) | Post-sprint |

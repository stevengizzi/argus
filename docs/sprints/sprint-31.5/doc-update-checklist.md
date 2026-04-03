# Sprint 31.5 — Doc Update Checklist

## Documents to Update After Sprint Completion

| Document | What to Update |
|----------|---------------|
| `docs/project-knowledge.md` | Sprint history table: add Sprint 31.5 row with test counts, date, key changes. Build track queue: mark 31.5 complete. Current State section: update test baseline. Experiment Pipeline description: add parallel execution, programmatic universe filtering, `max_workers` config. ExperimentRunner description: note `workers` param and `universe_filter` param. DEF-146 status: RESOLVED. |
| `CLAUDE.md` | Update test counts. Add Sprint 31.5 to sprint reference. Note `--workers` and `--universe-filter` delegation changes. |
| `docs/sprint-history.md` | Add Sprint 31.5 entry with full session details, scope, test deltas. |
| `docs/roadmap.md` | Update build track: mark 31.5 complete, advance pointer to next sprint. |
| `config/experiments.yaml` | Add `max_workers: 4` field (done during implementation, confirmed during doc sync). |

## Documents That Should NOT Be Changed
| Document | Reason |
|----------|--------|
| `docs/architecture.md` | No architectural changes — parallelism is internal to ExperimentRunner |
| `docs/decision-log.md` | No new DECs anticipated (established patterns only) |
| `docs/risk-register.md` | No new risks |
| `docs/pre-live-transition-checklist.md` | No live-trading-relevant changes |

## DEF Status Updates
| DEF | Current Status | New Status |
|-----|---------------|------------|
| DEF-146 | OPEN | ✅ RESOLVED (universe filtering wired into ExperimentRunner) |

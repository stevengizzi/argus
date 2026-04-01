# Sprint 32: Doc Update Checklist

## Documents to Update After Sprint Completion

| Document | Updates Needed |
|----------|---------------|
| `docs/project-knowledge.md` | Add Experiment Pipeline section under Key Components. Update Active Strategies table (note variant capability). Update Build Track Queue (Sprint 32 ✓, 32.5 merged). Update sprint history table. Update test counts. Update Monthly Costs if applicable. Add new DEF/DEC references. Update Key Learnings with experiment pipeline insights. |
| `CLAUDE.md` | Add new DEF items (DEF-129 through DEF-133). Add new DEC entries if any decisions made during implementation. Update test counts. Add experiment pipeline to system overview. |
| `docs/architecture.md` | Add "Experiment Pipeline" section covering: Pattern Factory, Parameter Fingerprint, Variant Spawner, Experiment Runner, Promotion Evaluator, ExperimentStore. Add data flow diagram for variant lifecycle (spawn → shadow → promote → live → demote → shadow). |
| `docs/roadmap.md` | Mark Sprint 32 complete. Note Sprint 32.5 merged into Sprint 32. Update next sprint references. |
| `docs/sprint-history.md` | Add Sprint 32 entry with: goal, session count, test delta, key deliverables, DECs/DEFs created. |
| `docs/decision-log.md` | Add any DEC entries from decisions made during implementation. At minimum: factory design, fingerprint algorithm, promotion criteria, variant spawning mechanism. |
| `docs/dec-index.md` | Add index entries for any new DECs. |
| `docs/pre-live-transition-checklist.md` | Add experiment pipeline config items: `experiments.enabled` (paper: true, live: TBD), `auto_promote` (paper: true for testing, live: TBD), `max_shadow_variants_per_pattern` (paper: 5, live: TBD). |
| `config/experiments.yaml` | Created during sprint — document schema in comments. |

## DEC/DEF Reservations

- DEF-129: Non-PatternModule strategy variant support (deferred)
- DEF-130: Intraday parameter adaptation (deferred)
- DEF-131: Experiments UI page (deferred)
- DEF-132: Variant-specific exit management (deferred)
- DEF-133: Per-variant capital allocation (deferred)
- DEC range: Reserve DEC-382 through DEC-395 for Sprint 32 decisions

## Post-Sprint Doc Sync Process

Use the doc-sync automation prompt template from the workflow metarepo:
`templates/doc-sync-automation-prompt.md`

Clone latest branch from GitHub and produce surgical find/replace instructions for each document.

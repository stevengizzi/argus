# Sprint 32.5: Doc Update Checklist

## Documents to Update

| Document | What to Update | Session |
|----------|---------------|---------|
| `docs/project-knowledge.md` | Sprint 32.5 in history table, test counts, build track queue advancement, experiment pipeline section (exit params, all 7 patterns, UI), 9th page in page list, new endpoints in API section, DEF closures (131, 132, 134), new DEF items from deferred scope, Experiments Dashboard component description | S8 |
| `CLAUDE.md` | Test counts, DEF closures, new DEF items, max DEC/DEF numbers, active strategy table (no change expected), new page reference | S8 |
| `docs/roadmap.md` | 32.5 complete, next sprint advancement, Adaptive Capital Intelligence vision referenced, deferred items noted | S8 |
| `docs/sprint-history.md` | Sprint 32.5 entry with session details, test delta, key deliverables | S8 |
| `docs/decision-log.md` | Any new DECs from implementation (if any emerge) | S8 |
| `docs/dec-index.md` | Index entries for any new DECs | S8 |
| `docs/architecture.md` | Experiment pipeline section updated (exit params, all 7 patterns), 9th page added to frontend section, new REST endpoints documented, allocation-intelligence-vision.md referenced | S8 |
| `docs/sprint-campaign.md` | Sprint 32.5 complete, next sprint | S8 |

## New Documents Created

| Document | Purpose | Session |
|----------|---------|---------|
| `docs/architecture/allocation-intelligence-vision.md` | Adaptive Capital Intelligence architectural vision | S8 |

## Documents NOT Modified (Verification)

These documents should NOT be modified by this sprint:

- `docs/pre-live-transition-checklist.md` — no new paper trading overrides
- `docs/live-operations.md` — no operational procedure changes
- `docs/risk-register.md` — no new risks (ABCD perf is DEF-122, already tracked)
- `docs/process-evolution.md` — no workflow changes
- `docs/strategies/STRATEGY_*.md` — no strategy behavior changes
- `docs/ui/ux-feature-backlog.md` — items completed, not added (may remove completed items)

## DEF Item Tracking

### Closed by This Sprint
- DEF-131: Experiments + Counterfactual Visibility (S5 + S6 + S7)
- DEF-132: Exit Parameters as Variant Dimensions (S1 + S2)
- DEF-133: Adaptive Capital Intelligence Vision Document (S8)
- DEF-134: BacktestEngine All 7 Patterns (S3 + S4)

### New DEF Items (Expected)
Track during implementation. Likely candidates from spec-by-contradiction deferred items:
- Parameter space heatmap visualization
- Real-time experiment monitoring WebSocket
- Experiment runner UI trigger
- Fingerprint migration for existing variants
- Variant promote/demote from UI

### DEC/DEF Number Ranges
- Current max DEC: 381
- Current max DEF: 134
- Reserve DEF-135 through DEF-145 for this sprint (11 slots)
- Reserve DEC-382 through DEC-392 for this sprint (11 slots, if needed)

# Sprint 28.5: Doc Update Checklist

Documents to update after sprint completion (via doc-sync prompt from Work Journal).

---

## Required Updates

- [ ] **`docs/project-knowledge.md`**
  - Add Exit Management subsection under Key Components (exit_math.py, ExitManagementConfig, trailing stop engine, escalation engine)
  - Update Order Manager description to include trailing stop + escalation
  - Update BacktestEngine description to include trail/escalation state
  - Update CounterfactualTracker description to include trail/escalation state
  - Update SignalEvent description to include `atr_value` field
  - Add `config/exit_management.yaml` to Config files list
  - Add Sprint 28.5 to Sprint History table
  - Update Build Track Queue (mark 28.5 complete)
  - Add new DEC references to Key Active Decisions section
  - Update Key Learnings if applicable

- [ ] **`docs/architecture.md`**
  - Add Exit Management section (exit_math.py, config structure, trailing stop engine, escalation, belt-and-suspenders pattern)
  - Update Order Manager architecture section
  - Update BacktestEngine architecture section
  - Update File Structure diagram (exit_math.py location)

- [ ] **`docs/decision-log.md`**
  - Add DEC-378 through DEC-385 (as used) with full rationale

- [ ] **`docs/dec-index.md`**
  - Add new DEC entries to quick-reference index

- [ ] **`docs/sprint-history.md`**
  - Add Sprint 28.5 entry with session details, test counts, key outcomes

- [ ] **`docs/roadmap.md`**
  - Mark Sprint 28.5 complete
  - Update Phase 6 Gate description (Exit Management now delivered)
  - Update "Current state" paragraph

- [ ] **`CLAUDE.md`**
  - Update next sprint reference
  - Add `config/exit_management.yaml` to config file list
  - Add exit management operational notes
  - Update test counts

- [ ] **`docs/pre-live-transition-checklist.md`**
  - Add exit management config review items:
    - Review trailing stop parameters for each strategy
    - Review escalation schedules
    - Verify trail distances appropriate for live position sizes
    - Confirm belt-and-suspenders pattern behavior with real IBKR

## Conditional Updates

- [ ] **`docs/risk-register.md`** — Only if new risks identified during implementation (e.g., trail + IBKR interaction risks)

- [ ] **Strategy spec sheets (`docs/strategies/STRATEGY_*.md`)** — Update strategies that opt into trailing stop or escalation with new config parameters

## Not Updated

- `docs/ui/ux-feature-backlog.md` — No frontend changes
- `docs/live-operations.md` — No operational procedure changes (trail is automatic)
- `docs/process-evolution.md` — No workflow changes

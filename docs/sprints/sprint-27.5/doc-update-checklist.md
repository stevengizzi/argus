# Sprint 27.5: Doc Update Checklist

Documents to update after sprint completion (doc-sync session or work journal deliverable).

## Must Update

- [ ] **`docs/project-knowledge.md`**
  - Sprint history table: add Sprint 27.5 row (name, test counts, date, key DECs)
  - Build Track Queue: strike through Sprint 27.5, bold next sprint (27.6)
  - Architecture → Analytics section: add Evaluation Framework subsection describing `MultiObjectiveResult`, `EnsembleResult`, comparison API, slippage model
  - Key Active Decisions: add DEC-363 through DEC-368 (as issued)
  - Test counts: update pytest + Vitest totals

- [ ] **`docs/sprint-history.md`**
  - Add Sprint 27.5 entry with full scope, session details, test delta, DEC references

- [ ] **`docs/decision-log.md`**
  - Add DEC-363 through DEC-368 entries (as issued during sprint)
  - Expected decisions: evaluation data model fields, confidence tier thresholds, string-keyed regime results, Pareto comparison metric set, ensemble evaluation method, slippage model integration approach

- [ ] **`docs/dec-index.md`**
  - Add DEC-363 through DEC-368 index entries with status and sprint reference

- [ ] **`docs/architecture.md`**
  - Add Evaluation Framework section under Analytics tier
  - Document: `MultiObjectiveResult` as universal evaluation currency, `EnsembleResult` for cohort evaluation, comparison API functions, regime tagging in BacktestEngine, slippage model calibration
  - Update BacktestEngine section: note `to_multi_objective_result()` capability and optional slippage model

- [ ] **`CLAUDE.md`**
  - Update test counts
  - Add evaluation framework to analytics component list
  - Note `slippage_model_path` config option on BacktestEngineConfig

## May Update (If Applicable)

- [ ] **`docs/roadmap.md`**
  - Update Sprint 27.5 status to ✅ complete in Phase 6 section
  - Update "Current state" paragraph in §3 (Velocity Baseline)

- [ ] **`docs/risk-register.md`**
  - Only if new risks identified during sprint (none expected)

## No Update Needed

- `docs/live-operations.md` — no operational changes
- `docs/ui/ux-feature-backlog.md` — no frontend changes
- `docs/strategies/STRATEGY_*.md` — no strategy changes
- `docs/protocols/market-session-debrief.md` — no debrief changes

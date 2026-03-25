# Sprint 27.7: Doc Update Checklist

All doc updates happen via a doc-sync session after the sprint is complete. This checklist defines what needs updating.

## Must Update

- [ ] **`docs/project-knowledge.md`**
  - Add Counterfactual Engine subsection to Key Components (under Intelligence Layer)
  - Add TheoreticalFillModel to Core section (shared fill priority logic)
  - Add Shadow Strategy Mode to Active Strategies section notes
  - Update Sprint History table (Sprint 27.7 row with test counts, date, key DECs)
  - Update Build Track Queue (strike through 27.7)
  - Update test counts in Current State
  - Add new DEC entries to Key Active Decisions quick reference
  - Add `counterfactual.yaml` to config listing if present
  - Update File Structure if new directories/files warrant it

- [ ] **`docs/decision-log.md`**
  - New entries: DEC-379 through DEC-385 (as used during sprint)
  - Expected decisions: shared fill model extraction, SignalRejectedEvent architecture, counterfactual.db separation, config gating approach, shadow mode routing design, T1-only target tracking, generic tracker interface

- [ ] **`docs/dec-index.md`**
  - Add DEC-379–385 entries with status and one-line descriptions

- [ ] **`docs/sprint-history.md`**
  - Sprint 27.7 entry with: goal, session count, test delta, key deliverables, any DEF items generated

- [ ] **`docs/architecture.md`**
  - Add Counterfactual Engine to Intelligence Layer section
  - Add `fill_model.py` to Core section (shared fill priority module)
  - Add `SignalRejectedEvent` to Event Bus event listing
  - Note shadow strategy mode in strategy lifecycle/routing description
  - Add `data/counterfactual.db` to data stores listing

- [ ] **`CLAUDE.md`**
  - Add counterfactual config awareness (counterfactual.enabled, per-strategy mode field)
  - Note `data/counterfactual.db` file
  - Add shadow mode operator instructions if relevant

## May Update (If Relevant)

- [ ] **`docs/roadmap.md`** — Mark Sprint 27.7 complete, update any downstream sprint descriptions that reference the Counterfactual Engine as "planned"
- [ ] **`docs/risk-register.md`** — If any new risks identified during sprint
- [ ] **`docs/live-operations.md`** — If counterfactual system has operational implications for live trading (likely: note that counterfactual.db grows and needs retention enforcement)
- [ ] **`docs/ui/ux-feature-backlog.md`** — If any UI ideas surface during implementation (e.g., counterfactual outcomes in Copilot context)

## Do Not Update During Doc Sync

- Strategy spec sheets (`docs/strategies/STRATEGY_*.md`) — No strategy logic changes in this sprint
- `docs/protocols/market-session-debrief.md` — Counterfactual data doesn't change the debrief protocol
- `docs/process-evolution.md` — No workflow changes

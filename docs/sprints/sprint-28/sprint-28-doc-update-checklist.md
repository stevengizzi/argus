# Sprint 28: Doc Update Checklist

## Documents to Update After Sprint Completion

### 1. `docs/project-knowledge.md`
- [ ] Add Sprint 28 to Sprint History table (name, test counts, date, key DECs)
- [ ] Update test counts in "Current State" section (~3,693+55 pytest + 645+15 Vitest)
- [ ] Update "Active sprint" → None, "Next sprint" → 28.5 (Exit Management)
- [ ] Add Learning Loop components to Key Components section (OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, LearningService, ConfigProposalManager, LearningStore)
- [ ] Add Learning Loop config to Config Changes subsection
- [ ] Update Build Track Queue (mark Sprint 28 complete)
- [ ] Add any new DECs to Quick Reference section

### 2. `docs/architecture.md`
- [ ] Add Learning Loop section to AI Layer / Intelligence Layer area (OutcomeCollector, analyzers, LearningService, ConfigProposalManager)
- [ ] Add `data/learning.db` to database inventory
- [ ] Add Learning REST endpoints to API section
- [ ] Add auto post-session trigger to application lifecycle section
- [ ] Add ConfigProposalManager to config management section (first module that writes config programmatically)

### 3. `docs/decision-log.md`
- [ ] Add new DEC entries for Sprint 28 decisions (DEC numbers TBD — check current max before assigning)
- [ ] Candidate DECs: advisory-only V1 design, ConfigProposalManager safety model, auto post-session trigger, LearningLoopConfig config-gating, Performance page as UI home, adaptive regime analysis, LearningStore separate DB

### 4. `docs/dec-index.md`
- [ ] Add Sprint 28 DEC entries to index

### 5. `docs/sprint-history.md`
- [ ] Add Sprint 28 entry with full session details, test deltas, key decisions, scope delivered

### 6. `docs/roadmap.md`
- [ ] Mark Sprint 28 as ✅ Complete with actual session count and test delta
- [ ] Update "Current state" in Section 3 (Velocity Baseline)
- [ ] Verify Sprint 28.5 (Exit Management) is correctly described as next sprint

### 7. `docs/sprint-campaign.md`
- [ ] Mark Sprint 28 as ✅ Complete (should already be correctly numbered from pre-sprint doc sync)
- [ ] Update calendar timeline with actual completion date

### 8. `CLAUDE.md`
- [ ] Add any new DEF items discovered during implementation
- [ ] Update deferred items list if any were resolved
- [ ] Add Learning Loop operational notes (e.g., `scripts/run_learning_analysis.py` usage)

### 9. `docs/pre-live-transition-checklist.md`
- [ ] Add Learning Loop config items that need adjustment before live trading (if any — e.g., `auto_trigger_enabled` default, `max_weight_change_per_cycle` guard value)

## Pre-Doc-Sync Verification
- [ ] All new DEC numbers are sequential (check `docs/decision-log.md` for current max)
- [ ] All new DEF numbers are sequential (check `CLAUDE.md` for current max)
- [ ] No document references stale sprint numbers
- [ ] Cross-references between documents are consistent

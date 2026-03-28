# Sprint 28: Regression Checklist

Run these checks during implementation (close-out) and review (Tier 2). Every item must pass.

## Quality Engine Invariants

- [ ] Quality Engine produces identical scores for the same input when no ConfigProposals have been applied
- [ ] `quality_engine.yaml` weights still sum to 1.0 after any ConfigProposal application
- [ ] All 7 strategies continue to emit `share_count=0` signals with `pattern_strength` scores
- [ ] `_process_signal()` in main.py still runs quality pipeline (score → filter → size → enrich)
- [ ] Risk Manager Check 0 still rejects `share_count ≤ 0`
- [ ] `min_grade_to_trade` continues to function (C+ default blocks sub-C+ signals)

## Config Safety

- [ ] New `learning_loop.*` YAML keys all recognized by `LearningLoopConfig` Pydantic model (no silently ignored fields)
- [ ] `config/learning_loop.yaml` loads without error with default values
- [ ] `config/quality_engine.yaml` round-trips through ConfigProposalManager without data loss (read → write → read produces identical content, minus formatting)
- [ ] Pydantic validation rejects invalid config values (negative weights, weights > 1.0, non-existent grade strings)
- [ ] ConfigProposalManager does NOT write to any config file other than `quality_engine.yaml`

## Execution Pipeline

- [ ] All existing API endpoints return expected responses (no route conflicts from `/api/v1/learning/*`)
- [ ] Post-session shutdown completes within normal timeout even when auto trigger fires
- [ ] Counterfactual tracking continues unaffected (SignalRejectedEvent → CounterfactualTracker path unchanged)
- [ ] Overflow routing continues unaffected (broker_capacity threshold still respected)
- [ ] Reconciliation safety continues unaffected (broker-confirmed positions still immune)

## Data Access

- [ ] OutcomeCollector queries do NOT modify any data in argus.db, counterfactual.db, or evaluation.db
- [ ] LearningStore creates `data/learning.db` without affecting other SQLite databases
- [ ] `data/learning.db` uses WAL mode
- [ ] Report retention enforcement only deletes from learning.db (never touches other DBs)

## Frontend

- [ ] Performance page existing content (charts, tables, trade log tab) renders correctly with Learning sections added
- [ ] Dashboard existing cards and layout unaffected by Learning summary card addition
- [ ] All Learning UI components render gracefully when `learning_loop.enabled: false` (hidden, not error)
- [ ] All Learning UI components render gracefully when no reports exist (empty state, not error)
- [ ] Approve/dismiss buttons require JWT authentication

## Test Suite

- [ ] Full pytest suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- [ ] Full Vitest suite passes: `cd argus/ui && npm test`
- [ ] No test hangs (previous test suite had 0 hangs — must remain 0)
- [ ] New tests are added (target: ~55 pytest + ~15 Vitest)

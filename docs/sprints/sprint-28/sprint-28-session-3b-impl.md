# Sprint 28, Session 3b: LearningService + CLI

## Pre-Flight Checks
1. Read: All S1 files (`models.py`, `outcome_collector.py`), S2a files (`weight_analyzer.py`, `threshold_analyzer.py`), S2b file (`correlation_analyzer.py`), S3a file (`learning_store.py`), `config/quality_engine.yaml`
2. Run: `python -m pytest tests/intelligence/learning/ -x -q` (S1+S2+S3a tests passing)
3. Verify correct branch

## Objective
Build the LearningService orchestrator that wires all components into a pipeline, plus the CLI entry point for manual analysis triggers.

## Requirements

1. **Create `argus/intelligence/learning/learning_service.py`:**
   - `LearningService` class
   - Constructor takes: `LearningLoopConfig`, `OutcomeCollector`, `WeightAnalyzer`, `ThresholdAnalyzer`, `CorrelationAnalyzer`, `LearningStore`
   - `_running: bool` guard to prevent concurrent execution
   - `async run_analysis(window_days=None, strategy_id=None) -> LearningReport`:
     1. Check `_running` guard → raise if already running
     2. Read current weights/thresholds from `quality_engine.yaml`
     3. Collect outcomes via OutcomeCollector
     4. Build data quality preamble
     5. Run WeightAnalyzer (overall + per-regime)
     6. Run ThresholdAnalyzer
     7. Run CorrelationAnalyzer
     8. Assemble LearningReport
     9. Persist to LearningStore
     10. **Auto-supersede prior PENDING proposals (Amendment 6):** Call `store.supersede_proposals(report_id)`
     11. Generate ConfigProposals for actionable recommendations (above MODERATE confidence)
     12. Save proposals to store
     13. Log summary at INFO level (analysis duration, recommendation count, data quality summary)
     14. Return report
   - Config-gated: if `config.enabled == False`, `run_analysis()` returns None with INFO log

2. **Create `scripts/run_learning_analysis.py`:**
   - CLI entry point using argparse
   - Flags: `--window-days N` (override default), `--strategy-id ID` (filter), `--dry-run` (print report to stdout, don't persist)
   - Initializes OutcomeCollector, analyzers, LearningStore, LearningService
   - Reads LearningLoopConfig from `config/learning_loop.yaml` (or defaults if file doesn't exist yet — S4 creates it)
   - Exit code 0 on success, 1 on error
   - Prints report summary to stdout (recommendation count, data quality, key findings)

3. **Update `argus/intelligence/learning/__init__.py`:** Add LearningService to exports.

## Constraints
- Do NOT modify any files outside `argus/intelligence/learning/` and `scripts/`
- Do NOT wire into server.py or main.py (that's S5)
- Do NOT create config/learning_loop.yaml (that's S4)
- CLI should work with defaults if config file doesn't exist

## Test Targets
- `test_learning_service.py`: full pipeline happy path (mock components), sparse data path (empty collector), config-disabled returns None, concurrent guard rejects, proposal supersession called, CLI flags parsing, dry-run mode
- Minimum: 10 new tests
- Test command: `python -m pytest tests/intelligence/learning/ -x -q`

## Definition of Done
- [ ] LearningService orchestrates full pipeline: collect → analyze → report → persist → propose
- [ ] Concurrent guard prevents simultaneous runs
- [ ] Proposal auto-supersession on new report (Amendment 6)
- [ ] Config-gated (returns None when disabled)
- [ ] CLI script works with --dry-run, --window-days, --strategy-id
- [ ] ≥10 new tests
- [ ] Close-out to `docs/sprints/sprint-28/session-3b-closeout.md`
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. Verify concurrent guard (`_running` flag) with proper try/finally
2. Verify proposal supersession is called BEFORE new proposals are created
3. Verify config-gated behavior (enabled=false → no analysis, no error)
4. Verify CLI --dry-run doesn't persist to DB
5. Verify LearningReport.version is set (forward-compat for Sprint 32.5)

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*

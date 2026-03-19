# Sprint 25.6, Session 2: Periodic Regime Reclassification

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/orchestrator.py` (focus on `_classify_regime()`, `run_pre_market_routine()`, and regime-related attributes)
   - `argus/main.py` (search for `_run_evaluation_health_check` as a pattern for periodic asyncio tasks)
   - Strategy config files: `grep -rn "allowed_regimes" argus/strategies/`
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/core/test_orchestrator.py -x -v
   ```
   Expected: all passing
3. Verify Session 1 changes are committed.

## Objective
Add a periodic asyncio task that re-evaluates market regime during market hours (~5 min interval) using the orchestrator's existing classification logic. Currently, regime is set once at startup via `run_pre_market_routine()` and never updated, even though SPY data flows continuously after market open.

## Additional fix from S1 review (hardcoded path in server.py):
In `argus/api/server.py`, the standalone/dev mode EvaluationEventStore initialization hardcodes the path `"data/evaluation.db"`. This should use the config-driven path to match `main.py`. Change line ~267 from:
`pythondb_path = str(Path("data/evaluation.db"))`

to:
`pythondb_path = str(Path(config.system.data_dir) / "evaluation.db")`

where `config` is the SystemConfig already available in the lifespan scope. This ensures both initialization paths (main.py and standalone server.py) resolve to the same location if `data_dir` is ever customized. No new tests needed — existing S1 tests cover the store initialization; this is a one-line config consistency fix.

## Requirements

### 1. Investigate existing regime logic
First, read `argus/core/orchestrator.py` to understand:
- How `_classify_regime()` works (what data it needs, what it returns)
- Where the regime is stored (likely `self._current_regime` or similar)
- What happens when SPY data is unavailable (the "SPY data unavailable" fallback path)
- Whether there's already a mechanism for periodic updates that's just not wired

### 2. Add periodic regime update task
In `argus/main.py`:
- Create a new method `_run_regime_reclassification(self)` as an asyncio task
- Pattern: same structure as `_run_evaluation_health_check()` — loop with `asyncio.sleep(300)` (5 minutes)
- Guard: only run between 9:30 AM and 4:00 PM ET (same market hours check pattern)
- Call the orchestrator's regime classification method
- Log the result:
  - If regime changed: `logger.info("Regime reclassified: %s → %s", old, new)`
  - If regime unchanged: `logger.debug("Regime unchanged: %s", current)` (DEBUG, not INFO — avoid noise)
  - If SPY data still unavailable: `logger.warning("Regime reclassification: SPY data unavailable, retaining %s", current)`
- Start the task during startup (in the same area where health check tasks are started)
- Cancel the task during shutdown

### 3. Expose reclassification on orchestrator
If `_classify_regime()` is a private method or embedded in `run_pre_market_routine()`:
- Extract or expose a public method `reclassify_regime()` that can be called at any time
- The method should: get current SPY data → classify → update internal state → return (old_regime, new_regime) tuple
- Handle SPY data unavailability gracefully (return current regime, don't crash)

## Constraints
- Do NOT modify strategy files or their `allowed_regimes` lists
- Do NOT change how strategies respond to regime changes (they check regime at evaluation time, which is correct)
- Do NOT add new config fields (5-minute interval can be hardcoded; config-gating deferred if needed)
- Do NOT modify `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`

## Test Targets
After implementation:
- Existing orchestrator tests: all must still pass
- New tests:
  1. Test that reclassification produces a valid regime when SPY data is available (mock SPY indicators)
  2. Test that reclassification retains current regime when SPY data is unavailable
  3. Test that the periodic task only runs during market hours (mock clock)
  4. Test that regime change is logged at INFO level, unchanged at DEBUG
- Minimum new test count: 4
- Test command: `python -m pytest tests/core/test_orchestrator.py -x -v`

## Definition of Done
- [ ] Regime reclassification runs every ~5 minutes during market hours
- [ ] Regime does NOT update outside market hours
- [ ] SPY data unavailability handled gracefully (no crash, retains current regime)
- [ ] Log entries confirm regime updates
- [ ] All existing tests pass
- [ ] 4+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 4 strategies still register | Grep startup logs for "Registered strategy" — 4 entries |
| Regime classification doesn't crash on missing data | Test with mocked unavailable SPY |
| Pre-market routine still works | Startup logs show "Pre-market routine complete" |
| No strategy files modified | `git diff --name-only` shows no strategy file changes |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-25.6/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-25.6/review-context.md`
2. Close-out report: `docs/sprints/sprint-25.6/session-2-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (scoped): `python -m pytest tests/core/test_orchestrator.py -x -v`
5. Files that should NOT have been modified: strategy files, `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, `trade_logger.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS, follow the fix documentation procedure in the template.

## Session-Specific Review Focus (for @reviewer)
1. Verify reclassification only runs during market hours (9:30–16:00 ET)
2. Verify SPY unavailability doesn't crash the task or change regime to None
3. Verify no strategy `allowed_regimes` lists were modified
4. Verify the asyncio task is properly cancelled during shutdown
5. Check that regime reclassification log entries use appropriate levels (INFO for changes, DEBUG for unchanged)

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)

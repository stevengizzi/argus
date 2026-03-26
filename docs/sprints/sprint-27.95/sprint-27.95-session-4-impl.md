# Sprint 27.95, Session 4: Startup Zombie Cleanup

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/main.py` or `server.py` — startup sequence, position reconstruction logic (search for "Reconstructed position")
   - `argus/execution/order_manager.py` — position tracking, broker interaction
   - Existing startup tests (if any)
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/execution/ tests/test_main* -x -q
   ```
   Expected: all passing (full suite confirmed by Session 2 close-out)
3. Verify Sessions 1a, 1b, and 2 changes are committed

## Objective
At startup, flatten IBKR positions that have no matching ARGUS internal record (zombie positions from prior sessions). Config-gated with default enabled. Also fix script permissions.

## Requirements

1. **Find the startup position reconstruction logic** (search for "Reconstructed position" in main.py or server.py — this is where IBKR portfolio is queried and unknown positions are currently reconstructed as RECO entries).

2. **Replace reconstruction-of-unknowns with conditional flatten:**
   - After broker connects and IBKR portfolio is queried, for each IBKR position:
     - If symbol exists in ARGUS internal position tracking → leave it alone (known position)
     - If symbol does NOT exist in ARGUS tracking:
       - If `startup.flatten_unknown_positions` is True:
         - Submit a market SELL order for the full share count via the broker abstraction
         - Log INFO "Startup cleanup: flattened unknown position {symbol} ({shares} shares)"
         - Do NOT create a RECO position entry — the position is being closed immediately
       - If `startup.flatten_unknown_positions` is False:
         - Log WARNING "Unknown IBKR position at startup: {symbol} ({shares} shares) — manual cleanup required"
         - Optionally still create the RECO entry for UI visibility (maintain existing behavior)

3. **Handle IBKR portfolio query failure gracefully:**
   - If the broker's portfolio query throws an exception or returns None: log WARNING "IBKR portfolio query failed at startup — skipping zombie cleanup", continue startup normally

4. **Add config field:**
   - Add `flatten_unknown_positions: bool = True` to a StartupConfig Pydantic model (or add to an existing appropriate config section)
   - Wire into SystemConfig
   - Add YAML entry to `config/system.yaml` and `config/system_live.yaml`

5. **Fix script permissions:**
   - Run `chmod +x scripts/ibkr_close_all_positions.py`
   - Verify the shebang line is present (e.g., `#!/usr/bin/env python3`)
   - Commit the permission change

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/intelligence/`
- Do NOT change: the startup sequence order (broker connect → portfolio query → data service start), broker abstraction interface, normal position tracking for known positions
- Startup flatten must complete BEFORE market data streaming begins (positions should be closed before signals start generating)
- The flatten orders go through the broker abstraction (not raw IBKR calls) for consistency

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~8):
  1. Startup with unknown IBKR positions + flatten enabled → positions closed, INFO logged
  2. Startup with unknown IBKR positions + flatten disabled → WARNING logged, no close
  3. Startup with empty IBKR portfolio → no action
  4. Startup with only known ARGUS positions in IBKR → no action
  5. Startup with mix of known + unknown positions → only unknown flattened
  6. IBKR portfolio query failure → graceful skip, WARNING logged
  7. Config field recognized by Pydantic model
  8. Script has executable permission (can stat the file)
- Minimum new test count: 8
- Test command: `python -m pytest tests/execution/ tests/test_main* -x -q`

## Config Validation
Write a test verifying `startup.flatten_unknown_positions` is recognized:
| YAML Key | Model Field |
|----------|-------------|
| `flatten_unknown_positions` | `flatten_unknown_positions` |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Config validation test passing
- [ ] Script has +x permission and shebang
- [ ] Close-out report written to `docs/sprints/sprint-27.95/session-4-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Startup sequence order unchanged | Verify broker connect → portfolio → data start order in code |
| Known positions not affected by startup cleanup | Test with known position present |
| Normal startup without IBKR positions works | Test empty portfolio path |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.
**Write the close-out report to:** `docs/sprints/sprint-27.95/session-4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-27.95/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.95/session-4-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ tests/test_main* -x -q`
5. Files NOT modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/data/`

Review report: `docs/sprints/sprint-27.95/session-4-review.md`

## Post-Review Fix Documentation
If CONCERNS reported and fixed, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify flatten happens BEFORE market data streaming starts
2. Verify flatten uses broker abstraction (not raw IBKR calls)
3. Verify known ARGUS positions are never touched by startup cleanup
4. Verify portfolio query failure is handled gracefully (no crash)
5. Startup flatten closes positions that should be kept → ESCALATE (matching logic wrong)

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Startup sequence unchanged for normal operation
- [ ] Known positions preserved
- [ ] Config field recognized by Pydantic
- [ ] Full test suite passes, no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. Startup flatten closes positions that should be kept → halt, fix matching logic
2. Pre-flight test failures → investigate

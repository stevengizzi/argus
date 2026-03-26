# Sprint 27.95, Session 1a: Reconciliation Redesign

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/order_manager.py` — current reconciliation logic, position tracking, fill handling
   - `argus/core/events.py` — SignalRejectedEvent, position events
   - `tests/` — find existing reconciliation tests (grep for "reconcil")
2. Run the test baseline (full suite, Session 1 of sprint):
   ```bash
   python -m pytest tests/ --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~3,610 tests, all passing
3. Verify you are on the correct branch: `main`

## Objective
Prevent reconciliation auto-cleanup from destroying positions with confirmed IBKR entry fills. Add broker-confirmed tracking per position and a consecutive miss counter for unconfirmed positions, making auto-cleanup safe and correct.

## Requirements

1. **In `argus/execution/order_manager.py`**, add broker-confirmed tracking:
   - Add `_broker_confirmed: dict[str, bool]` instance variable — tracks whether each symbol's position has a confirmed IBKR entry fill
   - In the entry fill callback (wherever "Position opened" is logged), set `_broker_confirmed[symbol] = True`
   - On position close (wherever position is removed from tracking), clean up: `_broker_confirmed.pop(symbol, None)`

2. **In `argus/execution/order_manager.py`**, add consecutive miss counter:
   - Add `_reconciliation_miss_count: dict[str, int]` instance variable — tracks consecutive portfolio snapshot misses per symbol
   - On position close, clean up: `_reconciliation_miss_count.pop(symbol, None)`

3. **In the reconciliation cycle** (find the method that compares ARGUS positions vs IBKR portfolio), redesign the cleanup logic:
   - For each ARGUS position NOT found in IBKR portfolio snapshot:
     - If `_broker_confirmed.get(symbol, False)` is True: log WARNING "IBKR portfolio snapshot missing confirmed position {symbol} — snapshot may be stale". Do NOT clean up. Reset miss count to 0 (snapshot miss is not a concern for confirmed positions).
     - If NOT broker-confirmed AND `auto_cleanup_unconfirmed` config is True:
       - Increment `_reconciliation_miss_count[symbol]`
       - If miss count >= `consecutive_miss_threshold`: clean up the position (existing cleanup logic). Log WARNING with miss count.
       - If miss count < threshold: log INFO "Unconfirmed position {symbol} missing from IBKR snapshot (miss {count}/{threshold})"
     - If NOT broker-confirmed AND `auto_cleanup_unconfirmed` is False: log WARNING only (current warn-only behavior)
   - For each ARGUS position FOUND in IBKR portfolio snapshot: reset `_reconciliation_miss_count[symbol] = 0`

4. **In config Pydantic models**, add ReconciliationConfig fields:
   - Find where reconciliation config is defined (may be part of an existing config model or need a new one)
   - Add `auto_cleanup_unconfirmed: bool = False`
   - Add `consecutive_miss_threshold: int = 3` with validator `ge=1`
   - Wire into SystemConfig if not already present
   - Add YAML entries to `config/system.yaml` and `config/system_live.yaml` under `reconciliation:` section

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/intelligence/`
- Do NOT change: the reconciliation cycle frequency (60s), the IBKR portfolio query mechanism, the position close/trade logging path (that's Session 1b), EOD flatten behavior
- Do NOT remove: existing reconciliation mismatch logging (count summaries)
- Preserve: the `_flatten_pending` guard (DEC-363), bracket amendment logic (DEC-366)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~10):
  1. Confirmed position not cleaned up when missing from snapshot (WARNING logged)
  2. Unconfirmed position cleaned up after N consecutive misses (auto_cleanup_unconfirmed=True)
  3. Unconfirmed position NOT cleaned up before reaching threshold
  4. Miss counter resets to 0 when position found in snapshot
  5. Mixed batch: confirmed + unconfirmed positions in same reconciliation cycle
  6. `auto_cleanup_unconfirmed=False` → no cleanup of any kind (warn-only)
  7. Broker-confirmed flag set on entry fill callback
  8. Broker-confirmed flag cleared on position close
  9. Miss counter cleared on position close
  10. Config fields recognized by Pydantic model (no silently ignored keys)
- Minimum new test count: 10
- Test command: `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`

## Config Validation
Write a test that loads the YAML config and verifies reconciliation keys are recognized:
1. Load config and extract `reconciliation` section keys
2. Compare against ReconciliationConfig model_fields.keys()
3. Assert no unrecognized keys

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `auto_cleanup_unconfirmed` | `auto_cleanup_unconfirmed` |
| `consecutive_miss_threshold` | `consecutive_miss_threshold` |
| (plus any existing reconciliation fields) | |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 10+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Normal position lifecycle unchanged | Run existing position lifecycle tests |
| Entry fill still triggers "Position opened" log | Grep tests for position open assertions |
| Position close still cleans up all tracking state | Verify no leaked entries in _broker_confirmed or _miss_count after close |
| Reconciliation mismatch summary logging preserved | Verify existing log format assertions still pass |
| `_flatten_pending` guard intact | Run existing flatten tests |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-27.95/session-1a-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.95/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.95/session-1a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/ tests/test_config* -x -q`
5. Files that should NOT have been modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/data/`

The @reviewer will write its report to: `docs/sprints/sprint-27.95/session-1a-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same session, update both the close-out and review files per the Post-Review Fix Documentation protocol in the implementation prompt template.

## Session-Specific Review Focus (for @reviewer)
1. Verify `_broker_confirmed` is set ONLY on confirmed IBKR entry fill (not on order submission)
2. Verify confirmed positions are NEVER auto-closed regardless of config settings
3. Verify miss counter resets when position reappears in snapshot
4. Verify cleanup of tracking dicts on position close (no memory leaks over a full trading day)
5. Verify `auto_cleanup_unconfirmed=False` makes reconciliation fully warn-only

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Normal position lifecycle unchanged
- [ ] Risk Manager gating logic unchanged
- [ ] Quality Engine pipeline unchanged
- [ ] EOD flatten still works
- [ ] CounterfactualTracker shadow mode still works
- [ ] `_flatten_pending` guard (DEC-363) intact
- [ ] Bracket amendment (DEC-366) intact
- [ ] Reconciliation periodic task (60s) still runs
- [ ] New config fields verified against Pydantic model
- [ ] Full test suite passes, no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. Reconciliation change breaks position lifecycle tests → halt, escalate
2. Pre-flight test failures not present at sprint entry → investigate
3. Test hang (>10 minutes) → halt

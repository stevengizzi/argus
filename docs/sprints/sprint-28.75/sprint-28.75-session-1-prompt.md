# Sprint 28.75, Session 1: Backend Operational Fixes

**Additional context:** The operator changed trailing_stop.enabled from false
to true in config/exit_management.yaml WHILE Argus was already running on
March 30. ARGUS loads config at startup only — no hot-reload. This likely
explains why 0 trail events fired: the running instance had enabled=false.
Verify this hypothesis first: check if exit_management.yaml currently has
enabled: true, and if so, confirm via a test that the trail path fires
end-to-end. If the config was the sole issue, R1 becomes a verification
task rather than a bug fix.

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md` (current project state)
   - `argus/execution/order_manager.py` (primary modification target)
   - `argus/core/config.py` (ExitManagementConfig, TrailingStopConfig)
   - `argus/core/exit_math.py` (compute_trailing_stop, compute_escalation_stop)
   - `config/exit_management.yaml` (exit management config)
2. Run the test baseline:
   Full suite: python -m pytest tests/ -n auto --ignore=tests/test_main.py -q
   Expected: ~3,955 tests, all passing
3. Verify you are on branch: main (create branch sprint-28.75 from main)
4. Confirm config/exit_management.yaml exists and has trailing_stop.enabled: true

## Objective
Fix four operational issues found in the March 30 market session: trailing
stops not firing (likely config timing — verify), flatten-pending orders
hanging indefinitely, and excessive log spam from flatten-pending and
reconciliation-missing messages.

## Requirements

### R1: Diagnose and fix trailing stops not firing (DEF-111)
The March 30 session had 183 T1 hits but ZERO trail stop activations. The
config has `trailing_stop.enabled: true` and `activation: after_t1`. However,
the operator changed this from `false` to `true` mid-session — ARGUS only
loads config at startup, so the running instance likely had `enabled: false`.

Diagnosis steps (do BEFORE any code changes):
1. Confirm `config/exit_management.yaml` currently has `trailing_stop.enabled: true`.
   If so, the running config at boot time was likely `false` (changed mid-session).
2. Even if the config was the sole issue, verify the full trail path works
   end-to-end with a test:
   a. Trace the T1 fill handler in order_manager.py. After T1 fill, does it
      set `position.trail_active = True`? Check the condition gate around line 1113.
   b. Check whether `position.exit_config` is populated when positions are
      created. Trace from `_handle_entry_fill()` through to ManagedPosition
      construction. If `exit_config` is None, the trail can never activate.
   c. Check the `on_tick()` trail check (around line 620+). Verify the trail
      distance computation succeeds when `atr_value` is provided.
   d. Check if `atr_value` from SignalEvent reaches the ManagedPosition. Trail
      type is "atr" — if atr_value is None, compute_trailing_stop might return
      0 or skip.
3. Report findings. If the config timing was the sole issue, document it and
   write the verification test. If there's an actual code bug, fix it.

### R2: Add flatten-pending timeout (DEF-112)
The SWMR position had a market sell order (IBKR #3509) placed at 12:56 PM ET
that never filled. The `_flatten_pending` guard correctly prevented duplicates,
but the position was stuck for 2+ hours until shutdown.

Implementation:
1. Add a `flatten_pending_timeout_seconds` config field to OrderManagerConfig
   (default: 120 seconds).
2. In the poll loop (the 5-second fallback poll), check each entry in
   `_flatten_pending`: if the flatten order was placed more than
   `flatten_pending_timeout_seconds` ago, cancel it and resubmit a new
   market sell order.
3. Track the timestamp when each flatten order is placed in `_flatten_pending`
   (change from `dict[str, str]` to `dict[str, tuple[str, float]]` where
   float is `time.monotonic()` at placement time).
4. When the stale flatten is cancelled and a new one placed, update the
   `_flatten_pending` entry with the new order ID and timestamp.
5. Log at WARNING level: "Flatten order for {symbol} timed out after {N}s.
   Resubmitting." Rate-limit to 1 per symbol per timeout cycle.
6. Add a max_flatten_retries (default: 3) — after N timeouts, log at ERROR
   and stop retrying (position will be caught by EOD flatten or manual
   intervention). Do NOT leave an infinite retry loop.

### R3: Rate-limit "flatten already pending" log messages (DEF-113)
The March 30 session produced 2,003 "flatten already pending" messages (every
5 seconds per stuck symbol). Use the ThrottledLogger pattern: log the first
occurrence, then suppress for 60 seconds per symbol, with a summary count
on resume.

### R4: Rate-limit "IBKR portfolio snapshot missing confirmed position" (DEF-114)
Same pattern as R3. SWMR generated this warning every 60 seconds for 2.5 hours.
Rate-limit to once per 10 minutes per symbol (first occurrence logs immediately).

## Constraints
- Do NOT modify: argus/strategies/*.py, argus/core/events.py, argus/data/,
  argus/analytics/, argus/intelligence/, argus/ai/, argus/api/, any frontend files
- Do NOT change the flatten-pending guard logic (DEC-363) — only add the
  timeout mechanism alongside it
- Do NOT change any exit_math.py functions — if the trail isn't firing, the
  bug is in how config/data reaches the computation, not in the math itself
- Preserve all existing OrderManager behavior — these are additive fixes

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - test_flatten_pending_timeout: verify a stale flatten order is cancelled
    and resubmitted after timeout
  - test_flatten_pending_max_retries: verify retries stop after max
  - test_flatten_pending_timestamp_tracking: verify timestamp is recorded
    and updated on resubmission
  - test_trail_activation_after_t1: verify trail_active is set True after
    T1 fill when config says after_t1
  - test_trail_stop_computed_on_tick: verify on_tick computes and checks
    trail stop when trail_active is True
  - test_throttled_flatten_pending_log: verify log suppression
  - test_throttled_reconciliation_log: verify log suppression
- Minimum new test count: 7
- Test command: python -m pytest tests/ -n auto --ignore=tests/test_main.py -q

## Definition of Done
- [ ] Trailing stop root cause identified and documented (verified with test)
- [ ] Flatten-pending timeout mechanism implemented and tested
- [ ] Log rate-limiting applied to both message types
- [ ] All existing tests pass
- [ ] New tests written and passing (minimum 7)
- [ ] Close-out report written to docs/sprints/sprint-28.75/session-1-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| DEC-117: All managed positions have bracket orders | grep test_bracket_orders in tests, verify passing |
| DEC-363: Flatten-pending guard still prevents duplicates | New test: submit two flattens for same symbol, only one placed |
| DEC-372: Stop resubmission cap still works | grep test_stop.*retry in tests, verify passing |
| DEC-374: Duplicate fill dedup unchanged | grep test_duplicate_fill in tests, verify passing |
| Exit management config loads correctly | Add assertion: position.exit_config is not None after entry fill |
| Trailing stop activates after T1 | New test (above) |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-28.75/session-1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: docs/sprints/sprint-28.75/review-context.md
2. The close-out report path: docs/sprints/sprint-28.75/session-1-closeout.md
3. The diff range: git diff main..sprint-28.75
4. The test command: python -m pytest tests/execution/ -x -q
5. Files that should NOT have been modified: argus/strategies/, argus/core/events.py, argus/data/, argus/analytics/, argus/api/, argus/ui/

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix them, update both the close-out
and review files per the standard protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify trail activation actually fires after T1 fill — trace the code path
2. Verify flatten-pending timeout doesn't create a race with _flatten_pending guard
3. Verify new order ID is tracked after flatten resubmission (no orphaned entries)
4. Verify max_flatten_retries prevents infinite loops
5. Verify log rate-limiting uses ThrottledLogger or equivalent per-symbol suppression
6. Verify no changes to exit_math.py pure functions

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if: changes to the flatten-pending guard logic (DEC-363) beyond
  adding timeout; changes to bracket order creation flow; changes to risk
  manager or quality engine; any modification to exit_math.py
- CONCERNS if: trail fix requires changes outside order_manager.py (indicates
  deeper architectural issue); flatten timeout interacts with EOD flatten
  in unexpected ways

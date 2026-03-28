# Sprint 27.95, Session 5: Carry-Forward Cleanup

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/order_manager.py` (focus on `_close_position`, `_flatten_unknown_position`, `_resubmit_stop_with_retry`, `reconstruct_from_broker`)
   - `argus/core/config.py` (focus on `OrderManagerConfig`, `ReconciliationConfig`, `StartupConfig`)
   - `docs/sprints/sprint-27.95/review-context.md`
2. Run the scoped test baseline:
   ```
   python -m pytest tests/execution/ -x -q
   ```
   Expected: all passing (full suite confirmed by Session 3c close-out)
3. Verify you are on the correct branch (same working tree as Sessions 1a–3c)

## Objective
Fix three carry-forward issues identified during Sprint 27.95 reviews. All changes are in files already modified this sprint. No new blast radius.

## Requirements

### Fix 1: Zero-qty guard in startup zombie cleanup (F-004, MEDIUM)

In `argus/execution/order_manager.py`, in `reconstruct_from_broker()`, in the loop that iterates broker positions classified as zombies (no associated orders):

1. Before calling `_flatten_unknown_position()`, add a guard: if `abs(position.quantity)` (or however the broker position qty is accessed) is 0 or less, log a DEBUG message like `"Skipping flatten for zero-quantity position {symbol}"` and skip the flatten call.
2. This prevents noisy log entries when all bracket orders filled before restart left a zero-qty ghost in the broker portfolio.

### Fix 2: Direct attribute access on normal close path (F-002, LOW)

In `argus/execution/order_manager.py`, in `_close_position()`:

1. Session 1b added `getattr(position, "original_stop_price", 0.0)` (and similar for `t1_price`, `t2_price`) for ALL close paths. These fields are guaranteed to exist on `ManagedPosition` (required dataclass fields).
2. Refactor so that:
   - **Normal close path** (not reconciliation): uses direct attribute access — `position.original_stop_price`, `position.t1_price`, `position.t2_price`
   - **Reconciliation close path** (`is_reconciliation=True`): keeps the defensive `getattr()` with fallback to `entry_price` / `0.0`
3. Add a brief inline comment on the reconciliation branch explaining why `getattr` is used there (defensive against incomplete ManagedPosition state during reconciliation).

### Fix 3: Split `stop_retry_max` into two config fields (INFO)

In `argus/core/config.py`, on `OrderManagerConfig`:

1. Keep `stop_retry_max: int = Field(default=3, ge=0)` — this controls the existing `_submit_stop_order` internal retry loop (broker connectivity failures).
2. Add `stop_cancel_retry_max: int = Field(default=3, ge=0)` — this controls the new `_resubmit_stop_with_retry` cancel-event retry loop (IBKR cancels the stop).
3. Add a docstring or inline comment on each field clarifying which retry path it governs.

In `argus/execution/order_manager.py`, in `_resubmit_stop_with_retry()`:

4. Change the reference from `self._config.stop_retry_max` to `self._config.stop_cancel_retry_max`.
5. Update any log messages that reference the config field name to use the new name.

In `config/system.yaml` and `config/system_live.yaml`:

6. Add `stop_cancel_retry_max: 3` to the `order_manager:` section (alongside existing `stop_retry_max`).

## Constraints
- Do NOT modify any files in `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/analytics/evaluation.py`
- Do NOT change the behavior of any existing rejection paths, quality pipeline, or risk manager
- Do NOT change the `_submit_stop_order` internal retry loop — only `_resubmit_stop_with_retry` references the new config field
- Do NOT rename `stop_retry_max` (it's used by the existing `_submit_stop_order` path; renaming would be a breaking change)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **Zero-qty guard test:** Mock a broker position with qty=0 classified as zombie → verify `_flatten_unknown_position` is NOT called, DEBUG log emitted
  2. **Config split test:** Verify `OrderManagerConfig` has both `stop_retry_max` and `stop_cancel_retry_max` fields with correct defaults
  3. **Config YAML alignment test:** Verify `system.yaml` and `system_live.yaml` `order_manager:` keys match `OrderManagerConfig.model_fields.keys()`
  4. **Cancel retry uses new config:** Verify `_resubmit_stop_with_retry` respects `stop_cancel_retry_max` (not `stop_retry_max`). Can adapt existing test from Session 2.
- Minimum new test count: 4
- Test command: `python -m pytest tests/execution/ tests/core/test_config.py -x -q`

## Config Validation
Write a test (or extend existing) that loads `config/system.yaml` and verifies all keys under `order_manager:` are recognized by `OrderManagerConfig.model_fields.keys()`. Specifically verify `stop_cancel_retry_max` is present in both the YAML and the model.

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `stop_retry_max` | `stop_retry_max` |
| `stop_cancel_retry_max` | `stop_cancel_retry_max` |

## Definition of Done
- [ ] Zero-qty guard added before `_flatten_unknown_position()`
- [ ] Normal close path uses direct attribute access; reconciliation path keeps `getattr()`
- [ ] `stop_cancel_retry_max` field added to `OrderManagerConfig`
- [ ] `_resubmit_stop_with_retry` uses `stop_cancel_retry_max`
- [ ] YAML files updated with new field
- [ ] All existing tests pass
- [ ] 4+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
After implementation, verify each of these:
| Check | How to Verify |
|-------|---------------|
| Normal close path still produces correct stop_price/t1/t2 values | Run existing trade logging tests |
| Reconciliation close still works with defensive defaults | Run `test_order_manager_reconciliation_redesign.py` |
| Stop retry cap (Session 2) still triggers emergency flatten at correct threshold | Run `test_order_manager_hardening.py` |
| Startup zombie cleanup correctly flattens non-zero-qty zombies | Run existing Session 4 tests |
| Startup zombie cleanup skips zero-qty positions | New test |
| `_submit_stop_order` still uses `stop_retry_max` | Grep or read the method |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-27.95/session-5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.95/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.95/session-5-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/ tests/core/test_config.py -x -q`
5. Files that should NOT have been modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/analytics/evaluation.py`

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-27.95/session-5-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the standard protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify the zero-qty guard fires BEFORE `_flatten_unknown_position()` is called, not after
2. Verify normal (non-reconciliation) close path uses direct `position.original_stop_price` access — no `getattr`
3. Verify reconciliation close path still uses `getattr` with fallback
4. Verify `_resubmit_stop_with_retry` references `stop_cancel_retry_max`, NOT `stop_retry_max`
5. Verify `_submit_stop_order` still references `stop_retry_max` (unchanged)
6. Verify both YAML files have the new `stop_cancel_retry_max` field

## Sprint-Level Regression Checklist (for @reviewer)
| Check | Expected |
|-------|----------|
| Normal position lifecycle unchanged | All existing position lifecycle tests pass |
| Reconciliation redesign (S1a) intact | `test_order_manager_reconciliation_redesign.py` passes |
| Trade logger fix (S1b) intact | `test_trade_logger_reconciliation.py` passes |
| Order mgmt hardening (S2) intact | `test_order_manager_hardening.py` passes |
| Startup zombie cleanup (S4) intact | S4 tests in `test_order_manager.py` pass |
| Overflow routing (S3b) intact | `test_overflow_routing.py` passes |
| Overflow → counterfactual (S3c) intact | `test_counterfactual_overflow.py` passes |
| Full test suite passes, no hangs | All scoped tests pass |

## Sprint-Level Escalation Criteria (for @reviewer)
1. Any change breaks position lifecycle tests
2. Any change breaks the reconciliation redesign from Session 1a
3. Stop resubmission cap (Session 2) no longer triggers emergency flatten at correct threshold
4. Startup flatten closes positions that should be kept
5. Test hang (>10 minutes)

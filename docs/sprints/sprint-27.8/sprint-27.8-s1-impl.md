# Sprint 27.8, Session 1: Ghost Position Reconciliation Fix + Health Inconsistency + Config-Coupled Tests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/order_manager.py` (full file — focus on `reconcile_positions()` at ~L1601, `on_cancel()` at ~L425, `_close_position_and_log()` at ~L1420)
   - `argus/core/events.py` (ExitReason enum at ~L40)
   - `argus/main.py` (per-strategy health reporting at ~L663–690, reconciliation task at ~L1113–1159)
   - `config/system_live.yaml`
   - `tests/execution/test_order_manager_reconciliation_log.py`
   - `tests/execution/test_order_manager_safety.py`
   - `tests/backtest/test_engine_sizing.py` (lines ~216–273 — paper-coupled assertions)
   - `tests/core/test_config.py` (lines ~1156–1168 — paper-coupled assertions)
2. Run the test baseline (DEC-328 — full suite, Session 1 of sprint):
   ```
   python -m pytest --ignore=tests/test_main.py -n auto -x -q
   ```
   Expected: ~3,528 tests, all passing
3. Verify you are on the correct branch: `main`

## Objective
Fix the ghost position reconciliation issue (DEF-099) by adding config-gated auto-cleanup of orphaned positions, fix the 6/7 vs 7/7 health monitor inconsistency, and decouple test assertions from paper-trading config values (DEF-101).

## Requirements

### Part 1: ExitReason Extension
1. In `argus/core/events.py`, add `RECONCILIATION = "reconciliation"` to the `ExitReason` enum (after `EMERGENCY`).

### Part 2: Reconciliation Auto-Cleanup
2. In `argus/execution/order_manager.py`, add `auto_cleanup_orphans: bool = False` parameter to `__init__()`. Store as `self._auto_cleanup_orphans`.

3. In `reconcile_positions()`, add cleanup logic AFTER the existing discrepancy detection loop. When `self._auto_cleanup_orphans is True` and a discrepancy shows `internal_qty > 0` and `broker_qty == 0`:
   - Find matching `ManagedPosition` entries in `self._managed_positions[symbol]`
   - For each: set `shares_remaining = 0`, set `realized_pnl = 0.0`
   - Call `_close_position_and_log()` with `exit_price=position.entry_price`, `exit_reason=ExitReason.RECONCILIATION`
   - Log at WARNING: "Reconciliation cleanup: closed orphaned position %s (%d shares, strategy=%s)"
   - The `_close_position_and_log()` call handles Trade logging, PositionClosedEvent publishing, and _managed_positions cleanup

4. Do NOT modify the existing warn-only discrepancy detection logic. The cleanup is an additive step that runs after detection, gated by `self._auto_cleanup_orphans`.

### Part 3: Bracket Exhaustion Detection
5. In `on_cancel()`, after the existing stop-order resubmission logic (lines ~454–466), add bracket exhaustion detection:
   - When a `target` order (pending.order_type == "t1_target") is cancelled, find the matching ManagedPosition
   - Check if BOTH `stop_order_id is None` AND `t1_order_id is None` (all bracket legs gone)
   - If both are None: log WARNING "All bracket legs cancelled for %s — position unprotected, attempting flatten"
   - Call `_flatten_position(position, reason="bracket_exhausted")` to attempt a cleanup sell
   - The flatten may fail silently for ghost positions (IBKR has no position). That's OK — the reconciliation cycle (60s) will catch it and run orphan cleanup.
   - Also clear `t1_order_id = None` on the position when a t1_target cancel is received (matching the existing pattern for stop orders at line 459)

### Part 4: Config Wiring
6. In `config/system_live.yaml`, add under a new `reconciliation:` section:
   ```yaml
   reconciliation:
     auto_cleanup_orphans: true
   ```

7. In `argus/main.py`, where OrderManager is constructed (~Phase 4 in startup), pass `auto_cleanup_orphans=True` when the config flag is set. Read from system config. If the config key doesn't exist, default to `False`.

### Part 5: Health Monitor Inconsistency Fix
8. In `argus/main.py`, replace the per-strategy health reporting block (lines ~663–690). Instead of unconditionally reporting HEALTHY for each strategy, loop over the `strategies` dict and check `strategy.is_active`:
   ```python
   for strategy_id, strategy in strategies.items():
       status = ComponentStatus.HEALTHY if strategy.is_active else ComponentStatus.DEGRADED
       label = "active" if strategy.is_active else "regime-filtered"
       self._health_monitor.update_component(
           f"strategy_{strategy_id}",
           status,
           message=f"{strategy.config.name} {label}",
       )
   ```
   This replaces the 7 individual `if` blocks with a single loop. The aggregate count at line 655 is correct and must NOT be changed.

### Part 6: Decouple Tests from Paper-Trading Config Values (DEF-101)
9. In `tests/backtest/test_engine_sizing.py`:
   - `test_risk_overrides_empty_uses_production` (line ~216): Replace `assert risk_config.account.min_position_risk_dollars == 10.0` with a config-reading assertion: load `config/risk_limits.yaml` via `yaml.safe_load()`, extract the `account.min_position_risk_dollars` value, and assert `risk_config.account.min_position_risk_dollars == yaml_value`. This way the test verifies "engine loads production config correctly" without hardcoding the value.
   - `test_risk_overrides_unknown_key_warns` (line ~253): Same treatment — replace `== 10.0` with reading the YAML and asserting match.
   - Update the docstrings/comments on these tests: remove "currently paper-trading: 10.0" annotations.

10. In `tests/core/test_config.py`:
   - `test_quality_engine_risk_tiers_loaded_from_yaml` (line ~1156): Replace the three specific-value assertions with ordering invariant assertions:
     ```python
     # Assert tiers are ordered: A+ > A > B+ > B > C+ > C (all positive)
     assert config.risk_tiers.a_plus[1] > 0  # A+ max is positive
     assert max(config.risk_tiers.a_plus) > config.risk_tiers.a  # A+ max > A
     assert config.risk_tiers.a > max(config.risk_tiers.b_plus)  # A > B+ max
     assert max(config.risk_tiers.b_plus) >= min(config.risk_tiers.b)  # B+ max >= B min
     assert min(config.risk_tiers.b) > max(config.risk_tiers.c_plus)  # B min > C+ max
     assert min(config.risk_tiers.c_plus) > config.risk_tiers.c  # C+ min > C
     assert config.risk_tiers.c > 0  # C is positive (not zero)
     ```
     This verifies the structural invariant (higher grades = higher risk allocation) regardless of whether the config has paper or live values.

## Constraints
- Do NOT modify: `_flatten_position()`, `on_fill()`, `on_tick()`, `_submit_stop_order()`, `_submit_bracket_orders()`
- Do NOT modify: the aggregate health count logic at line 655
- Do NOT change: ExitReason values for existing enum members
- Do NOT add: any new config Pydantic models (use dict-style config access from system config for the reconciliation flag — this is a simple boolean, not worth a model)
- Do NOT import ExitReason in any new location that could create circular imports
- Do NOT change test logic for `test_risk_overrides_applied` (line ~200) — that test uses explicit override values and is already config-independent
- The `_close_position_and_log()` is an async method — ensure calls from `reconcile_positions()` are awaited (reconcile_positions may need to become async, or the cleanup can be deferred via a list of positions to clean and processed after the detection loop)

## Canary Tests
Before making any changes, verify:
- `python -m pytest tests/execution/test_order_manager_reconciliation_log.py -x -q` — all 3 pass
- `python -m pytest tests/execution/test_order_manager_safety.py -x -q` — all 25 pass

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/execution/test_order_manager_reconciliation.py`:
  1. `test_reconciliation_cleanup_disabled_by_default` — orphan detected but not cleaned up when auto_cleanup_orphans=False
  2. `test_reconciliation_cleanup_closes_orphan` — orphan detected AND cleaned up when auto_cleanup_orphans=True, verify Trade logged with ExitReason.RECONCILIATION
  3. `test_reconciliation_cleanup_skips_real_positions` — position where broker_qty > 0 is NOT cleaned up
  4. `test_reconciliation_cleanup_sets_zero_pnl` — synthetic close record has realized_pnl=0 and exit_price=entry_price
  5. `test_bracket_exhaustion_triggers_flatten` — cancel of last bracket leg triggers flatten attempt
  6. `test_bracket_exhaustion_single_cancel_no_flatten` — cancel of stop with t1 still active does NOT trigger flatten
  7. `test_exit_reason_reconciliation_exists` — ExitReason.RECONCILIATION is a valid enum member
- New tests in `tests/test_main_health.py` (or extend existing):
  8. `test_per_strategy_health_reflects_regime_filtering` — inactive strategy reports DEGRADED, active reports HEALTHY
- Rewritten tests (DEF-101 — same count, different assertions):
  9. `test_risk_overrides_empty_uses_production` — now reads YAML and asserts match (not hardcoded value)
  10. `test_risk_overrides_unknown_key_warns` — same treatment
  11. `test_quality_engine_risk_tiers_loaded_from_yaml` — now asserts ordering invariant (A+ > A > B+ > B > C+ > C, all positive)
- Minimum new test count: 8 new + 3 rewritten
- Test command: `python -m pytest tests/execution/test_order_manager_reconciliation.py tests/execution/test_order_manager_reconciliation_log.py tests/execution/test_order_manager_safety.py tests/execution/test_order_manager.py tests/backtest/test_engine_sizing.py tests/core/test_config.py -x -q`

## Definition of Done
- [ ] ExitReason.RECONCILIATION added
- [ ] Reconciliation auto-cleanup implemented and config-gated
- [ ] Bracket exhaustion detection in on_cancel()
- [ ] Config wired in system_live.yaml and main.py
- [ ] Per-strategy health reporting uses is_active
- [ ] Test assertions decoupled from paper-trading config values (DEF-101)
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing, 3 rewritten
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing reconciliation warn-only unchanged when disabled | Run `test_reconciliation_cleanup_disabled_by_default` |
| OM fill handling unchanged | `python -m pytest tests/execution/test_order_manager.py -x -q` |
| OM safety features unchanged | `python -m pytest tests/execution/test_order_manager_safety.py -x -q` |
| ExitReason backward compatible | `python -c "from argus.core.events import ExitReason; print(list(ExitReason))"` |
| No circular imports | `python -c "from argus.execution.order_manager import OrderManager"` |
| Rewritten tests still pass with current config | `python -m pytest tests/backtest/test_engine_sizing.py tests/core/test_config.py -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-27.8/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: docs/sprints/sprint-27.8/sprint-27.8-review-context.md
2. The close-out report path: docs/sprints/sprint-27.8/session-1-closeout.md
3. The diff range: git diff HEAD~1
4. The test command: `python -m pytest tests/execution/ tests/backtest/test_engine_sizing.py tests/core/test_config.py -x -q`
5. Files that should NOT have been modified: anything in `argus/strategies/`, `argus/analytics/`, `argus/ai/`, `argus/intelligence/`, `argus/ui/`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail so it reflects reality:

1. **Append a "Post-Review Fixes" section to the close-out report file:**
   Open docs/sprints/sprint-27.8/session-1-closeout.md and append:

   ### Post-Review Fixes
   The following findings from the Tier 2 review were addressed in this session:
   | Finding | Fix | Commit |
   |---------|-----|--------|
   | [description from review] | [what you changed] | [short hash] |

   Commit the updated close-out file.

2. **Append a "Resolved" annotation to the review report file:**
   Open docs/sprints/sprint-27.8/session-1-review.md and append after
   the structured verdict:

   ### Post-Review Resolution
   The following findings were addressed by the implementation session
   after this review was produced:
   | Finding | Status |
   |---------|--------|
   | [description] | ✅ Fixed in [short hash] |

   Update the structured verdict JSON: change `"verdict": "CONCERNS"` to
   `"verdict": "CONCERNS_RESOLVED"` and add a `"post_review_fixes"` array.
   Commit the updated review file.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.
ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)
1. Verify auto-cleanup is gated by `self._auto_cleanup_orphans` — NEVER reachable when False
2. Verify synthetic close records use `exit_price=entry_price` and `realized_pnl=0`
3. Verify bracket exhaustion detection only fires when ALL bracket legs are None (not just one)
4. Verify per-strategy health loop doesn't change aggregate count logic
5. Verify `_close_position_and_log()` calls are properly awaited (async correctness)
6. Verify no race conditions between reconciliation cleanup and `on_tick()`/`on_fill()` — the reconciliation runs every 60s and modifies `_managed_positions`; concurrent access from tick/fill handlers must be safe
7. Verify rewritten test assertions in test_engine_sizing.py and test_config.py are truly config-value-independent — they should pass regardless of whether config has paper or live values

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| Existing reconciliation warn-only mode unchanged when config disabled | `python -m pytest tests/execution/test_order_manager_reconciliation_log.py -x -q` |
| Order Manager fill handling unchanged | `python -m pytest tests/execution/test_order_manager.py -x -q` |
| Order Manager safety features unchanged | `python -m pytest tests/execution/test_order_manager_safety.py -x -q` |
| ExitReason enum backward compatible | `python -m pytest tests/ -k "ExitReason" -x -q` |

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if: synthetic close record path could execute for non-orphan positions
- ESCALATE if: auto_cleanup code path is reachable when config flag is False
- ESCALATE if: any changes to bracket order submission, stop resubmission, or fill handling logic
- ESCALATE if: reconciliation changes affect the `_managed_positions` dict in ways that could race with `on_tick()` or `on_fill()`

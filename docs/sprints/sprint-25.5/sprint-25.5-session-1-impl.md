# Sprint 25.5, Session 1: Watchlist Wiring + List-to-Set Performance Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/main.py` (focus on lines 395-520 — strategy creation, watchlist, routing table)
   - `argus/strategies/base_strategy.py` (focus on `_watchlist`, `set_watchlist`, `watchlist` property, `reset_daily_state`)
   - `argus/data/universe_manager.py` (focus on `get_strategy_symbols()` method, line ~483)
   - `argus/strategies/orb_base.py` (line 504 — the `_watchlist` check in `on_candle`)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```bash
   pytest --ignore=tests/test_main.py -n auto
   ```
   Expected: ~2,765 tests, all passing
3. Verify you are on the correct branch: `main`

## Objective
Populate strategy watchlists from the Universe Manager routing table when UM is enabled, so that candles routed to each strategy pass the `on_candle()` watchlist gate. Convert `_watchlist` from `list` to `set` for O(1) membership checks at 2,100+ symbol scale. Preserve backward compatibility when UM is disabled.

## Requirements

1. **In `argus/strategies/base_strategy.py`:**
   - Change `self._watchlist: list[str] = []` (line 66) to `self._watchlist: set[str] = set()`
   - Update `set_watchlist(self, symbols: list[str])` to store as set: `self._watchlist = set(symbols)`. Keep the method signature accepting `list[str]` — callers should not need to change.
   - Update `reset_daily_state()`: change `self._watchlist = []` (line 210) to `self._watchlist = set()`
   - Update `watchlist` property (line 303-305) to return `list(self._watchlist)` — the public API contract returns `list[str]`
   - Update the debug log in `set_watchlist` to include source info. Change the format string to accept an optional `source` parameter: `def set_watchlist(self, symbols: list[str], source: str = "scanner") -> None:` and log `"%s: watchlist set to %d symbols (source: %s)"`. This is additive — existing callers without `source` get the default.

2. **In `argus/main.py`:**
   - After the routing table is built (Phase 9.5, after line 521 `self._universe_manager.build_routing_table(strategy_configs)`), add a new block that populates each strategy's watchlist from the UM routing:
     ```python
     # Populate strategy watchlists from Universe Manager routing
     for strategy_id, strategy in strategies.items():
         um_symbols = self._universe_manager.get_strategy_symbols(strategy_id)
         strategy.set_watchlist(list(um_symbols), source="universe_manager")
     ```
   - Log a summary at INFO level after the loop: `logger.info("Strategy watchlists populated from Universe Manager routing")`
   - The existing `if not use_universe_manager:` blocks at lines 402-403, 416-417, 430-431, 444-445 remain unchanged — they handle the scanner fallback path.

## Constraints
- Do NOT modify: `argus/data/universe_manager.py`, `argus/strategies/orb_base.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/order_manager.py`, `argus/analytics/observatory_service.py`, any config YAML files, any frontend files
- Do NOT change: the candle routing path in main.py (lines 724-745), strategy `on_candle()` evaluation logic, Risk Manager gating, Event Bus delivery
- Do NOT add: new API endpoints, config fields, database tables, or frontend components
- The `watchlist` property MUST return `list[str]`, not `set[str]`

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (in `tests/strategies/test_base_strategy.py` or a new file as appropriate):
  1. `test_set_watchlist_stores_as_set` — call `set_watchlist(['A', 'B', 'C'])`, verify internal `_watchlist` is a set
  2. `test_set_watchlist_accepts_list` — call with list input, no error
  3. `test_watchlist_property_returns_list` — `strategy.watchlist` returns `list[str]`, not `set`
  4. `test_on_candle_passes_watchlisted_symbol` — set watchlist with symbol, send candle, verify it is not early-returned (mock strategy to track calls past the watchlist check)
  5. `test_on_candle_rejects_non_watchlisted_symbol` — send candle for symbol not in watchlist, verify `None` returned without processing
  6. `test_reset_daily_state_clears_watchlist` — after `set_watchlist()`, call `reset_daily_state()`, verify watchlist empty
  7. `test_set_watchlist_deduplicates` — call with `['A', 'A', 'B']`, verify watchlist has 2 symbols
  8. `test_watchlist_populated_from_universe_manager` — integration test: create a mock UM with routing table, run the main.py startup path (or simulate it), verify each strategy's watchlist matches UM routing
- Minimum new test count: 8
- Test command: `pytest tests/strategies/test_base_strategy.py -v`

## Definition of Done
- [ ] `_watchlist` is `set[str]` internally
- [ ] `set_watchlist()` accepts `list[str]`, stores as set, logs source
- [ ] `watchlist` property returns `list[str]`
- [ ] `reset_daily_state()` clears to empty set
- [ ] main.py populates watchlists from UM routing after `build_routing_table()`
- [ ] Scanner fallback path (UM disabled) unchanged
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| `watchlist` property returns `list[str]` | `assert isinstance(strategy.watchlist, list)` in test |
| `set_watchlist(['A','B'])` works (list input) | Existing callers don't change; new test |
| Scanner path still calls `set_watchlist` when UM disabled | grep for `if not use_universe_manager:` — all 4 blocks still present |
| `on_candle` passes watchlisted symbol | Test sends candle for watchlisted symbol, gets past gate |
| `on_candle` rejects non-watchlisted symbol | Test sends candle for non-watchlisted symbol, returns None |
| Candle routing in main.py lines 724-745 unchanged | `git diff` shows no changes in that range |

## Sprint-Level Regression Checklist
- [ ] Scanner-only flow unchanged (UM disabled → strategies get scanner symbols)
- [ ] `watchlist` property returns `list[str]` (not set)
- [ ] `set_watchlist()` accepts `list[str]` input
- [ ] Strategy `on_candle()` evaluation logic unchanged
- [ ] Risk Manager not affected
- [ ] Event Bus FIFO ordering preserved
- [ ] Order Manager not affected
- [ ] Quality pipeline not affected
- [ ] Observatory endpoints return 200
- [ ] No files in "do not modify" list were changed
- [ ] All pre-existing tests pass
- [ ] Candle routing path in main.py (lines 724-745) unchanged

## Sprint-Level Escalation Criteria
1. Performance degradation: heartbeat candle counts drop significantly or API latency degrades
2. More than 5 existing tests break from list→set conversion
3. Evaluation events not in SQLite despite ring buffer being populated
4. Observatory endpoints empty despite evaluation_events having rows
- Session 1 specific: pre-flight failure unrelated to scope → halt; `get_strategy_symbols()` unexpected results → halt

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-25.5/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-25.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-25.5/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped, non-final session): `pytest tests/strategies/test_base_strategy.py -v`
5. Files that should NOT have been modified: `argus/data/universe_manager.py`, `argus/strategies/orb_base.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/order_manager.py`, `argus/analytics/observatory_service.py`, any config YAML files, any frontend files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-25.5/session-1-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail:

1. Append a "Post-Review Fixes" section to `docs/sprints/sprint-25.5/session-1-closeout.md`
2. Append a "Resolved" annotation to `docs/sprints/sprint-25.5/session-1-review.md` and update the structured verdict to `CONCERNS_RESOLVED`

If the reviewer reports CLEAR or ESCALATE, skip this step.

## Session-Specific Review Focus (for @reviewer)
1. Verify `_watchlist` is `set[str]` in base_strategy.py — not list
2. Verify `watchlist` property returns `list(self._watchlist)` — not the set directly
3. Verify main.py calls `set_watchlist()` with UM symbols AFTER `build_routing_table()` — ordering matters
4. Verify the 4 existing `if not use_universe_manager:` blocks are UNCHANGED — scanner fallback preserved
5. Verify no changes to candle routing path (lines 724-745 of main.py)
6. Verify `set_watchlist` signature adds `source` parameter with default — existing callers unaffected

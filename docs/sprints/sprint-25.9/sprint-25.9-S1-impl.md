# Sprint 25.9, Session 1: Regime Fixes + Operational Visibility

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md` (current state, strategy table, architecture)
   - `docs/sprints/sprint-25.9/sprint-25.9-review-context.md` (sprint spec)
   - `argus/core/orchestrator.py` (regime filtering in `_calculate_allocations`)
   - `argus/main.py` (regime reclassification task, startup banner)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~3,051 tests, all passing
3. Verify you are on branch `main`

## Objective
Fix the `bearish_trending` regime gap that caused a complete dead session on March 23 2026, improve regime reclassification visibility, and correct the misleading "Watching N symbols" display.

## Requirements

### E1: Add `bearish_trending` to All Strategy `allowed_regimes` (DEC-360)

1. Locate each strategy's `allowed_regimes` definition. These are in each strategy's `get_market_conditions_filter()` method or equivalent. Update all 7 strategies:

   | Strategy | File | Add |
   |----------|------|-----|
   | ORB Breakout | `argus/strategies/orb_breakout.py` | `bearish_trending` |
   | ORB Scalp | `argus/strategies/orb_scalp.py` | `bearish_trending` |
   | VWAP Reclaim | `argus/strategies/vwap_reclaim.py` | `bearish_trending` |
   | Afternoon Momentum | `argus/strategies/afternoon_momentum.py` | `bearish_trending` |
   | Red-to-Green | `argus/strategies/red_to_green.py` | `bearish_trending` |
   | Bull Flag | Check `argus/strategies/patterns/bull_flag.py` or config | `bearish_trending` |
   | Flat-Top Breakout | Check `argus/strategies/patterns/flat_top_breakout.py` or config | `bearish_trending` |

   **Important:** For Bull Flag and Flat-Top Breakout, these use the `PatternBasedStrategy` wrapper. Check whether `allowed_regimes` is defined in the pattern module, the wrapper, or a YAML config file. Add `bearish_trending` wherever the list is defined.

   The `MarketRegime` enum should already include `bearish_trending` — verify it exists. If not, that would explain why no strategy lists it. In that case, add it to the enum first.

2. In `argus/core/orchestrator.py`, in the method that filters strategies by regime (likely `_calculate_allocations` around line ~327), add a WARNING log when regime filtering results in 0 active strategies during market hours:

   ```python
   # After regime filtering, before returning allocations:
   if not active_strategies and self._is_market_hours():
       logger.warning(
           "Regime filtering resulted in 0 active strategies. "
           "Current regime: %s. No capital will be allocated.",
           current_regime.value
       )
   ```

   **Guard condition:** Only log during market hours (9:30–16:00 ET). Do NOT log during pre-market or post-market — zero active strategies is expected then.

   If there is no existing `_is_market_hours()` helper, check for an equivalent or use the market phase / session state that the Orchestrator already tracks.

### E2: Regime Reclassification INFO Logging

3. In `argus/main.py`, find `_run_regime_reclassification()` (around line ~886). Currently, when the regime is unchanged, it logs at DEBUG level. Change to:

   - **Every 6th check (every ~30 minutes):** Log at INFO with regime value + key indicator summary
   - **Other unchanged checks:** Keep at DEBUG
   - **Any regime change:** Log at INFO (this should already be the case)

   Implementation approach:
   ```python
   # Add a counter attribute or use a simple modulo on the check count
   self._regime_check_count = getattr(self, '_regime_check_count', 0) + 1
   
   if new_regime != old_regime:
       logger.info("Regime changed: %s → %s", old_regime.value, new_regime.value)
   elif self._regime_check_count % 6 == 0:
       logger.info(
           "Regime unchanged: %s (check #%d, SPY vol: %.4f)",
           new_regime.value, self._regime_check_count, spy_volatility_or_indicator
       )
   else:
       logger.debug("Regime unchanged: %s", new_regime.value)
   ```

   Adapt the indicator summary to whatever data is available at the reclassification point (e.g., SPY volatility value, the metric that drives regime classification). The goal is: an operator reading INFO logs can confirm (a) the task is running, and (b) what the regime is.

### E4: "Watching N symbols" Display Fix

4. In `argus/main.py`, find the startup log around line 792 that reports "Watching {len(symbols)} symbols". When Universe Manager is enabled and has built the routing table:
   - The displayed count should reflect the actual number of symbols in the Universe Manager's viable universe (i.e., symbols that passed system-level filters), NOT the scanner result count
   - Something like:
     ```python
     if universe_manager and universe_manager.is_enabled:
         symbol_count = universe_manager.viable_count  # or equivalent attribute
         logger.info("Watching %d symbols (Universe Manager)", symbol_count)
     else:
         logger.info("Watching %d symbols (scanner)", len(symbols))
     ```
   - Check what attributes/methods `UniverseManager` exposes for the viable symbol count. Use the appropriate one.

## Constraints
- Do NOT modify any strategy logic beyond `allowed_regimes` — no changes to entry conditions, exit logic, pattern detection, position sizing, or signal generation
- Do NOT modify `Risk Manager`, `Order Manager`, or `Event Bus`
- Do NOT modify the `_calculate_allocations` logic beyond adding the zero-active warning log
- Do NOT modify any frontend code
- Do NOT change the `MarketRegime` enum values or add new regimes (only verify `bearish_trending` exists)
- Do NOT change the regime classification algorithm

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:

  1. **Per-strategy regime test:** For each of the 7 strategies, test that `bearish_trending` is in `allowed_regimes` (or equivalent). This can be a parameterized test.
  2. **Regime filtering still works:** Test that a strategy with a restricted `allowed_regimes` list (e.g., only `bullish_trending`) is correctly filtered out in other regimes. Ensures we haven't broken the filtering mechanism.
  3. **Zero-active warning:** Test that the Orchestrator logs a WARNING when regime filtering produces 0 active strategies during market hours.
  4. **Zero-active no-warning outside market hours:** Test that the warning does NOT fire during pre-market.
  5. **Regime reclassification logging:** Test that the INFO log fires every 6th check and on regime changes. Test that non-6th unchanged checks remain DEBUG.

- Minimum new test count: 5
- Test command (scoped for mid-sprint):
  ```
  python -m pytest tests/strategies/ tests/core/test_orchestrator.py tests/test_main.py -x -q
  ```
  Note: If `test_main.py` is problematic (DEF-048), exclude it and test the main.py changes via the other test files or a new focused test file.
- Close-out test command (full suite):
  ```
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 7 strategies include `bearish_trending` | `grep -r "bearish_trending" argus/strategies/` shows 7+ hits |
| Strategies still filter correctly for OTHER regimes | Run parameterized test with regime not in allowed list → strategy inactive |
| Regime reclassification task still runs on 300s interval | Check `_run_regime_reclassification` call site unchanged |
| Startup banner still works | Check main.py startup log section compiles and runs |
| No changes to strategy signal/entry/exit logic | `git diff` shows only `allowed_regimes` and logging changes in strategy files |

## Definition of Done
- [ ] All 7 strategies include `bearish_trending` in their allowed_regimes
- [ ] Zero-active-strategy WARNING added to Orchestrator (market hours only)
- [ ] Regime reclassification logs at INFO every ~30 minutes
- [ ] "Watching N symbols" reflects Universe Manager viable count
- [ ] All existing tests pass
- [ ] ≥5 new tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-25.9/session-1-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-25.9/session-1-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-25.9/sprint-25.9-review-context.md`
2. The close-out report path: `docs/sprints/sprint-25.9/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped, non-final session): `python -m pytest tests/strategies/ tests/core/test_orchestrator.py -x -q`
5. Files that should NOT have been modified: anything in `argus/execution/`, `argus/analytics/`, `argus/ai/`, `argus/intelligence/`, `argus/ui/`, `argus/backtest/`, `argus/data/`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-25.9/session-1-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the standard
post-review fix protocol (see implementation-prompt template for full details).

## Session-Specific Review Focus (for @reviewer)
1. Verify `bearish_trending` was added ONLY to `allowed_regimes` — no other strategy config was changed
2. Verify the zero-active warning log is guarded by a market-hours check
3. Verify regime reclassification logging uses a counter, not a timer (avoid drift)
4. Verify "Watching N symbols" fix doesn't break the non-Universe-Manager code path
5. Verify no changes to files outside the declared scope (strategies, orchestrator, main.py)

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| All 7 strategies still respond to regime changes | Test: strategy deactivates in a regime NOT in its allowed list |
| Regime filtering still works for non-bearish regimes | Test: strategy with only `bullish_trending` is inactive in `range_bound` |
| Zero-active warning only fires during market hours | Test: no warning during pre-market or post-market phases |
| Full test suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` |

## Sprint-Level Escalation Criteria (for @reviewer)
Escalate to Tier 3 if:
1. Changes to startup sequence (main.py Phases 7–9.5) affect component initialization order
2. Any change to Risk Manager, Order Manager, or Event Bus behavior
3. Strategy changes go beyond `allowed_regimes` (e.g., modifying signal logic, entry conditions, position sizing)

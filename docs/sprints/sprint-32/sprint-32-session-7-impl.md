# Sprint 32, Session 7: Promotion Evaluator + Autonomous Loop

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/store.py` (S4 — ExperimentStore, save_promotion_event)
   - `argus/intelligence/experiments/models.py` (S4 — PromotionEvent, VariantDefinition)
   - `argus/analytics/comparison.py` (compare(), ComparisonVerdict, pareto_frontier())
   - `argus/intelligence/counterfactual_store.py` (query API for shadow results)
   - `argus/intelligence/filter_accuracy.py` (FilterAccuracy — shadow performance reference)
   - `argus/main.py` (SessionEndEvent handler — where Learning Loop trigger lives, ~search for "SessionEndEvent")
   - `argus/analytics/trade_logger.py` (query API for live trade results)
2. Run the test baseline (DEC-328 — Session 2+):
   Scoped: `python -m pytest tests/intelligence/experiments/ -v`
   Expected: all passing
3. Verify Sessions 1–6 committed

## Objective
Create the promotion evaluator that compares shadow variant performance against live variants using accumulated data and Pareto comparison. Wire it to run autonomously at session end (after Learning Loop, gated by `auto_promote` config flag).

## Requirements

1. Create `argus/intelligence/experiments/promotion.py` with **`PromotionEvaluator`**:

   a. `__init__(self, store: ExperimentStore, counterfactual_store, trade_logger, config: dict)`:
      - Accepts counterfactual store and trade logger as duck-typed dependencies
      - Config contains promotion thresholds (min_shadow_days, min_shadow_trades)

   b. `async def evaluate_all_variants(self) -> list[PromotionEvent]`:
      - Get all active variants from store
      - Group by base_pattern
      - For each pattern:
        - Get the live variant(s) and shadow variant(s)
        - For each shadow variant, call `_evaluate_for_promotion()`
        - For each live variant (non-base), call `_evaluate_for_demotion()`
      - Return all promotion/demotion events generated

   c. `async def _evaluate_for_promotion(self, shadow_variant: VariantDefinition, live_variants: list[VariantDefinition]) -> PromotionEvent | None`:
      - Query counterfactual store for shadow variant's results (keyed by strategy_id)
      - Check minimum thresholds: `shadow_trades >= promotion_min_shadow_trades` AND shadow trading days >= `promotion_min_shadow_days`
      - If thresholds not met → return None
      - Build a simplified MultiObjectiveResult from shadow data (expectancy, trade count, win rate)
      - For each live variant, build MultiObjectiveResult from trade logger data
      - Call `compare()` — if shadow DOMINATES any live variant → promote
      - If promoting: create PromotionEvent with action="promote", update variant mode to "live" in store
      - Return PromotionEvent or None

   d. `async def _evaluate_for_demotion(self, live_variant: VariantDefinition, baseline: ExperimentRecord | None) -> PromotionEvent | None`:
      - Query trade logger for live variant's recent performance
      - If no baseline exists → skip (can't compare)
      - Build MultiObjectiveResult from live data
      - Compare against baseline's backtest_result
      - If live is DOMINATED by baseline → demote to shadow
      - Add hysteresis: don't demote within first `promotion_min_shadow_days` days of being promoted (check promotion_events for last promote timestamp)
      - If demoting: create PromotionEvent with action="demote", update variant mode to "shadow" in store
      - Return PromotionEvent or None

   e. `_build_result_from_trades(self, strategy_id: str, ...) -> MultiObjectiveResult | None`:
      - Query trade logger for trades with matching strategy_id
      - Compute: trade count, win rate, expectancy, profit factor, Sharpe estimate
      - Return None if insufficient trades

   f. `_build_result_from_shadow(self, strategy_id: str, ...) -> MultiObjectiveResult | None`:
      - Query counterfactual store for shadow positions with matching strategy_id
      - Compute same metrics from theoretical P&L
      - Return None if insufficient data

2. In `argus/main.py`, wire the evaluator into the SessionEndEvent handler:
   - After the existing Learning Loop trigger (search for `LearningService` or `SessionEndEvent`)
   - Gated by `experiments.enabled AND experiments.auto_promote`
   - Call `evaluate_all_variants()`
   - For each PromotionEvent:
     - If promote: find the strategy in the Orchestrator's registered strategies, update its config mode
     - If demote: same — update config mode to "shadow"
     - Log at INFO level: "Promoted variant {id} from shadow to live" or "Demoted variant {id}"
   - Wrap in try/except — promotion failure should NOT prevent session cleanup

3. **Mode update mechanism:**
   - The strategy's `config.mode` field is a string that's read in `_process_signal()` (main.py ~line 1379–1382)
   - Updating `strategy.config.mode = "live"` or `"shadow"` at runtime changes the routing for subsequent signals
   - This is the first intraday adaptation mechanism in ARGUS — document it clearly in comments

## Constraints
- Do NOT modify `comparison.py` or `evaluation.py` — use their existing public APIs
- Do NOT modify `counterfactual.py` or `counterfactual_store.py` — use their query APIs
- Do NOT modify `trade_logger.py` beyond what S3 already changed
- Promotion/demotion must be idempotent — promoting an already-live variant is a no-op
- All PromotionEvents must be persisted to ExperimentStore before mode changes take effect

## Test Targets
After implementation:
- New tests in `tests/intelligence/experiments/test_promotion.py`:
  - Shadow variant with 30+ trades that dominates live → PromotionEvent(action="promote")
  - Shadow variant with 20 trades (below threshold) → None
  - Shadow variant that doesn't dominate → None
  - Live variant dominated by baseline → PromotionEvent(action="demote")
  - Hysteresis: recently promoted variant not immediately demoted
  - Promote already-live variant → no-op
  - Mode update: strategy.config.mode changed from "shadow" to "live"
  - PromotionEvent persisted to store
- Minimum new test count: 8
- Test command: `python -m pytest tests/intelligence/experiments/test_promotion.py -v`

## Definition of Done
- [ ] `promotion.py` created with evaluate/promote/demote logic
- [ ] Wired into SessionEndEvent handler in main.py (gated)
- [ ] Pareto comparison drives promotion decisions
- [ ] Hysteresis prevents oscillation
- [ ] PromotionEvents persisted before mode changes
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| R6: Shadow mode routing still works | Existing shadow tests pass |
| R7: CounterfactualTracker handles shadow signals | No changes to counterfactual code |
| R11: experiments disabled → no promotion runs | Config gate check |
| Promotion failure doesn't block session cleanup | try/except verified |

## Close-Out
**Write the close-out report to:** docs/sprints/sprint-32/session-7-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-7-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/intelligence/experiments/test_promotion.py -v`
5. Files that should NOT have been modified: `comparison.py`, `evaluation.py`, `counterfactual.py`, `counterfactual_store.py`, any strategy file

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify Pareto comparison is used (not custom comparison logic)
2. Verify hysteresis prevents oscillation (check for minimum days since last promotion)
3. Verify PromotionEvents saved BEFORE mode changes (atomic safety)
4. Verify mode update targets the correct attribute (`strategy.config.mode` is read at signal time)
5. Verify promotion failure wrapped in try/except (no session cleanup disruption)
6. Verify this is the first intraday mode change mechanism and it's documented in comments

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

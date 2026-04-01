# Sprint 32, Session 7 — Close-Out Report

## Session Objective
Create the promotion evaluator that compares shadow variant performance against
live variants using accumulated counterfactual/trade data and Pareto comparison.
Wire it to run autonomously at session end, gated by `auto_promote` config flag.

---

## Change Manifest

### New Files
| File | Description |
|------|-------------|
| `argus/intelligence/experiments/promotion.py` | `PromotionEvaluator` class — promotion + demotion logic, result builders, hysteresis |
| `tests/intelligence/experiments/test_promotion.py` | 8 new tests covering all spec requirements |

### Modified Files
| File | Change |
|------|--------|
| `argus/main.py` | +2 instance variables (`_promotion_evaluator`, `_experiments_auto_promote`), evaluator construction in startup block, autonomous evaluation in `_publish_session_end_event()` |

---

## Judgment Calls

1. **`_compute_result` uses `sqrt(n)` as Sharpe scaling proxy** — no time-series
   available from trade dicts; `sqrt(n)` gives a trade-count-scaled metric that
   remains consistent for comparison between two results built the same way.

2. **`_evaluate_for_demotion` queries `list_promotion_events` (newest first)**
   — uses `next()` on the first `action=="promote"` entry (most recent). Since
   the store returns descending order by timestamp, this is correct.

3. **PromotionEvaluator stored as `object | None`** — follows the established
   pattern for counterfactual_store and counterfactual_tracker. The local import
   of `PromotionEvaluator` at the call site provides the typed reference needed
   for `mypy` without requiring a top-level import.

4. **`_experiments_auto_promote` stored as a separate bool** — avoids re-parsing
   the YAML dict at session end, and is set to `False` by default so the gate is
   always explicit.

5. **In-memory mode update uses `hasattr(matching, 'config')`** — same duck-typed
   pattern used throughout `_process_signal()` for shadow mode routing. Avoids
   importing StrategyConfig at the call site.

---

## Scope Verification

| Requirement | Status |
|-------------|--------|
| `promotion.py` with evaluate/promote/demote logic | ✅ |
| Wired into SessionEndEvent handler in main.py | ✅ |
| Gated by `experiments.enabled AND experiments.auto_promote` | ✅ |
| Pareto comparison (compare()) drives promotion decisions | ✅ |
| Hysteresis prevents oscillation | ✅ |
| PromotionEvents persisted BEFORE mode changes | ✅ |
| In-memory strategy mode updated after persistence | ✅ |
| Promotion failure wrapped in try/except | ✅ |
| First intraday mode adaptation documented in comments | ✅ |
| Files NOT modified: comparison.py, evaluation.py, counterfactual.py, counterfactual_store.py | ✅ |

---

## Post-Review Fixes (Tier 2 review: CONCERNS → CLEAR)

**F1 (MEDIUM) — Fixed:** Added `if self._counterfactual_store is None: return None` guard
in `_build_result_from_shadow()` and `_count_shadow_trading_days()`. When the counterfactual
subsystem is disabled, promotion simply finds no shadow data and produces no events.

**F2 (LOW) — Fixed:** The `live_variants` update after promotion was a no-op list comprehension
(promoted shadow variant was not in the live list). Changed to `live_variants + [newly_promoted]`
so subsequent shadow variants in the same pattern correctly compare against the updated live set.

A 9th test was added: `test_none_counterfactual_store_returns_no_events`.

## Test Results

```
tests/intelligence/experiments/test_promotion.py   9 passed
tests/intelligence/experiments/                   51 passed
Full suite (--ignore=tests/test_main.py -n auto)  4373 passed, 0 failed
```

Delta: +9 new tests.

---

## Regression Checklist

| Check | Result |
|-------|--------|
| R6: Shadow mode routing still works (existing shadow tests) | ✅ pass |
| R7: CounterfactualTracker handles shadow signals (no changes to counterfactual code) | ✅ no changes |
| R11: experiments disabled → no promotion runs (`_promotion_evaluator` only set when enabled) | ✅ verified by gate |
| Promotion failure doesn't block session cleanup (try/except in `_publish_session_end_event`) | ✅ |

---

## Self-Assessment

**CLEAN** — All 8 spec requirements implemented, all tests pass, no regressions,
no files outside scope modified.

## Context State

GREEN — session completed well within context limits.

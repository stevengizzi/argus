# Close-Out Report — Sprint 28, Session S6cf-3

**Objective:** Replace StrategyHealthBands placeholder heuristic with real per-strategy metrics (Sharpe, win rate, expectancy) computed from OutcomeRecords in the LearningService pipeline.

## Change Manifest

| File | Change |
|------|--------|
| `argus/intelligence/learning/models.py` | Added `StrategyMetricsSummary` frozen dataclass (6 fields); added `strategy_metrics` field to `LearningReport` with `default_factory=dict`; added `from_dict()` deserialization for `strategy_metrics` (backward-compatible); restored `field` import |
| `argus/intelligence/learning/learning_service.py` | Added `_compute_strategy_metrics()` static method (source selection, win rate, expectancy, Sharpe); wired as Step 4.5 in `_execute_analysis()`; imported `OutcomeRecord` and `StrategyMetricsSummary` |
| `argus/intelligence/learning/__init__.py` | Exported `StrategyMetricsSummary` |
| `argus/ui/src/api/learningApi.ts` | Added `StrategyMetricsSummary` interface; added `strategy_metrics` to `LearningReport` |
| `argus/ui/src/components/learning/StrategyHealthBands.tsx` | Removed `extractStrategyMetrics` placeholder heuristic; reads from `report.strategy_metrics`; strategy name strips `strat_` prefix + title-cases |
| `argus/ui/src/components/learning/StrategyHealthBands.test.tsx` | Rewrote to use `strategy_metrics` instead of `WeightRecommendation` proxies |
| `argus/ui/src/components/learning/LearningDashboardCard.test.tsx` | Added `strategy_metrics: {}` to report fixtures |
| `argus/ui/src/components/learning/LearningInsightsPanel.test.tsx` | Added `strategy_metrics: {}` to report fixture |
| `tests/intelligence/learning/test_models.py` | Added 2 tests: strategy_metrics round-trip + backward compatibility |
| `tests/intelligence/learning/test_learning_service.py` | Added 4 tests: win rate/expectancy, Sharpe with multiple days, combined source, insufficient data; extended `_make_outcome` with `r_multiple`/`timestamp` params |

## Judgment Calls

- Named timezone variable `eastern` instead of `_ET` per ruff N806 (prompt used `_ET`).
- No changes needed to `test_learning_store.py` — `default_factory=dict` makes it backward-compatible without fixture changes.

## Scope Verification

- [x] `StrategyMetricsSummary` dataclass in `models.py`
- [x] `strategy_metrics` field on `LearningReport` with `default_factory=dict`
- [x] `from_dict()` deserializes `strategy_metrics` (backward-compatible: empty dict if absent)
- [x] `_compute_strategy_metrics` in `LearningService` with source preference, win rate, expectancy, Sharpe
- [x] Wired into `_execute_analysis` pipeline (Step 4.5)
- [x] TS `StrategyMetricsSummary` interface + `strategy_metrics` on `LearningReport`
- [x] StrategyHealthBands reads from `report.strategy_metrics` (placeholder heuristic removed)
- [x] Strategy name display uses `strat_` prefix stripping
- [x] Tests updated: StrategyHealthBands Vitest + backend pytest fixtures
- [x] No regressions: all pytest + Vitest pass

## Test Results

- **Backend:** 141 learning tests passed (135 → 141, +6 new); 3836 total passed; 8 pre-existing failures (AI config race, backtest engine, counterfactual wiring — all unrelated)
- **Frontend:** 680 Vitest tests passed (680 → 680, 0 new tests net — 3 tests rewritten)
- **Ruff:** 0 new warnings on modified files (2 pre-existing in learning_service.py)

## Deferred Items

None discovered.

## Self-Assessment: CLEAN

## Context State: GREEN

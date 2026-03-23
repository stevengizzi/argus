# Sprint 27.5 Design Summary

**Sprint Goal:** Build the universal evaluation framework — `MultiObjectiveResult`, `EnsembleResult`, confidence tiers, Pareto comparison API, and slippage calibration — that becomes the shared currency for all downstream optimization and experiment infrastructure (Sprints 28, 32.5, 33, 34, 38, 40, 41).

**Session Breakdown:**
- Session 1: Core data models — MultiObjectiveResult, RegimeMetrics, ConfidenceTier, serialization, factory
  - Creates: `argus/analytics/evaluation.py`
  - Modifies: —
  - Integrates: N/A
- Session 2: Regime tagging in BacktestEngine — SPY daily bars from Parquet, regime assignment, `to_multi_objective_result()`
  - Creates: —
  - Modifies: `argus/backtest/engine.py`
  - Integrates: S1
- Session 3: Individual comparison API — compare(), pareto_frontier(), soft_dominance(), is_regime_robust()
  - Creates: `argus/analytics/comparison.py`
  - Modifies: —
  - Integrates: S1
- Session 4: Ensemble evaluation — EnsembleResult, MarginalContribution, cohort addition, deadweight
  - Creates: `argus/analytics/ensemble_evaluation.py`
  - Modifies: —
  - Integrates: S1 + S3
- Session 5: Slippage model calibration — StrategySlippageModel, DB query, time/size adjustments
  - Creates: `argus/analytics/slippage_model.py`
  - Modifies: —
  - Integrates: N/A (standalone)
- Session 6: Integration wiring + E2E tests — slippage into engine, execution_quality_adjustment, full pipeline
  - Creates: —
  - Modifies: `argus/backtest/engine.py`, `argus/backtest/config.py`
  - Integrates: S1–S5

**Key Decisions:**
- String-keyed regime results (not MarketRegime enum) for Sprint 27.6 forward-compat
- SPY daily bars from Parquet cache (not FMP API) — fully reproducible backtests
- `from_backtest_result()` factory bridge — BacktestResult unchanged, MOR is additional output
- No REST API endpoints — no consumers yet
- `execution_quality_adjustment` nullable — None until sufficient execution records
- Slippage model as optional BacktestEngineConfig param — zero behavioral change by default
- Ensemble aggregation uses metric-level approximation (not trade-level) — documented as such
- 5 comparison metrics: Sharpe, max_drawdown_pct, profit_factor, win_rate, expectancy_per_trade

**Scope Boundaries:**
- IN: All data models, comparison functions, regime tagging, slippage calibration, JSON serialization, comprehensive tests
- OUT: No experiment registry (32.5), no FDR/p-values (33), no frontend, no promotion, no Learning Loop integration (28), no RegimeVector (27.6), no counterfactual (27.7), no API endpoints

**Regression Invariants:**
- BacktestResult remains primary return type — unchanged
- All existing metrics functions produce identical results
- walk_forward.py untouched
- No strategy, Risk Manager, or Event Bus changes
- Existing 3,071 pytest + 620 Vitest must not decrease

**File Scope:**
- Create: evaluation.py, comparison.py, ensemble_evaluation.py, slippage_model.py
- Modify: backtest/engine.py, backtest/config.py
- Do not modify: metrics.py, walk_forward.py, regime.py, performance.py, all strategies, all frontend

**Config Changes:**
- `BacktestEngineConfig.slippage_model_path: str | None = None` (constructor only, not YAML)

**Test Strategy:**
- ~70 new pytest tests across 6 sessions
- S1: ~12, S2: ~10, S3: ~15, S4: ~12, S5: ~6, S6: ~10

**Runner Compatibility:**
- Mode: human-in-the-loop
- Parallelizable sessions: S3 (after S1), S5 (after S1)

**Dependencies:**
- Sprint 27 (BacktestEngine) ✅
- Sprint 21.6 (execution_records) ✅
- RegimeClassifier (existing)
- Parquet cache (existing)

**Escalation Criteria:**
- BacktestEngine regression, circular imports, BacktestResult interface change required
- MOR schema diverges from DEC-357, ConfidenceTier miscalibration, >80% single-regime concentration

**Doc Updates Needed:**
- project-knowledge.md, sprint-history.md, decision-log.md, dec-index.md, architecture.md, CLAUDE.md, roadmap.md

# Sprint 32 Design Summary

**Sprint Goal:** Build the complete parameter externalization + experiment pipeline for PatternModule strategies — from YAML→constructor wiring through variant spawning, backtest pre-filtering, shadow tracking, and autonomous promotion/demotion. When complete, ARGUS can instantiate multiple parameterized variants of each pattern template, run them all (one live, rest shadow), and autonomously promote/demote based on accumulated evidence.

**Execution Mode:** Human-in-the-loop.

**Session Breakdown:**

- Session 1: Pydantic Config Alignment
  - Creates: nothing
  - Modifies: `argus/core/config.py` (add 28 missing detection param fields across 6 pattern configs)
  - Integrates: N/A
  - Score: 13 (Medium)

- Session 2: Pattern Factory + Parameter Fingerprint
  - Creates: `argus/strategies/patterns/factory.py`
  - Modifies: nothing
  - Integrates: N/A (standalone, consumed by S3+S5+S6)
  - Score: 13 (Medium)

- Session 3: Runtime Wiring
  - Creates: nothing
  - Modifies: `argus/main.py` (7 pattern constructors → factory), `argus/backtest/vectorbt_pattern.py` (`_create_pattern_by_name` → factory), `argus/analytics/trade_logger.py` (fingerprint column + population)
  - Integrates: S1 (config fields) + S2 (factory + fingerprint)
  - Score: 14 (High — borderline, proceed with caution)

- Session 4: Experiment Data Model + Registry Store
  - Creates: `argus/intelligence/experiments/__init__.py`, `argus/intelligence/experiments/models.py`, `argus/intelligence/experiments/store.py`
  - Modifies: nothing
  - Integrates: N/A (standalone, consumed by S5+S6+S7)
  - Score: 12 (Medium)

- Session 5: Variant Spawner + Startup Integration
  - Creates: `argus/intelligence/experiments/spawner.py`
  - Modifies: `argus/main.py` (variant instantiation at startup), `config/experiments.yaml`
  - Integrates: S2 (factory) + S4 (registry)
  - Score: 13 (Medium)

- Session 6: Experiment Runner (Backtest Pre-Filter)
  - Creates: `argus/intelligence/experiments/runner.py`
  - Modifies: nothing
  - Integrates: S2 (factory) + S4 (store)
  - Score: 11 (Medium)

- Session 7: Promotion Evaluator + Autonomous Loop
  - Creates: `argus/intelligence/experiments/promotion.py`
  - Modifies: `argus/main.py` (promotion check in session-end handler)
  - Integrates: S4 (store) + S6 (runner results) + existing `comparison.py`
  - Score: 12 (Medium)

- Session 8: CLI + REST API + Server Integration + Config Gating
  - Creates: `scripts/run_experiment.py`, `argus/api/routes/experiments.py`, `argus/intelligence/experiments/config.py`
  - Modifies: `argus/core/config.py` (ExperimentConfig in SystemConfig), `argus/api/server.py`
  - Integrates: S4 (store) + S5 (spawner) + S6 (runner) + S7 (promotion)
  - Score: 13 (Medium)

**Key Decisions:**

- **Startup-only config loading for base parameters; intraday promotion/demotion for variant mode changes.** Base pattern parameters load from YAML at startup (consistent with ConfigProposalManager). But a variant's mode (live↔shadow) can change intraday via the promotion evaluator. This is the first step toward full intraday adaptation.
- **Generic factory using PatternParam introspection.** The factory queries `get_default_params()` to discover valid parameter names, then extracts matching fields from the Pydantic config. No hardcoded switch statements. Adding a new pattern automatically works.
- **Variant spawner reads variant definitions from YAML.** Each pattern template can define N variant configs. Variants get unique strategy IDs (e.g., `strat_bull_flag__v2`). The spawner registers all variants with the Orchestrator — live variants generate real orders, shadow variants feed CounterfactualTracker.
- **Non-zero-sum deployment.** Variants don't compete for slots. Any number can be live simultaneously. The capital allocation layer (Risk Manager concentration limits + overflow routing) manages aggregate exposure.
- **Backtest pre-filter.** Before a variant is spawned as shadow, it must pass a minimum backtest bar (positive expectancy, minimum trade count) using BacktestEngine against the Parquet cache. This prevents wasting shadow compute on clearly bad configs.
- **Promotion via shadow performance, not backtest alone.** The promotion evaluator compares shadow variants against live variants using accumulated CounterfactualTracker data + the Pareto comparison API. A variant graduates to live when it demonstrates sustained edge in live market conditions.
- **Anti-fragility / degradation detection deferred to Sprint 33.5.** Premature without promotion history data.
- **ParameterFingerprint on every trade.** Stable hash of detection parameters, stored in trades table. Enables retroactive grouping of historical sessions by config and comparative analysis.

**Scope Boundaries:**

- IN: YAML→constructor wiring for 7 PatternModule patterns, generic factory, fingerprinting, variant spawning, experiment registry, backtest pre-filter, shadow-based promotion evaluator, CLI, REST API
- OUT: Non-PatternModule strategy variants (ORB, VWAP, AfMo, R2G), hot-reload, anti-fragility/rollback, actual parameter tuning, UI changes, ABCD O(n³) optimization, new patterns, Learning Loop V2 auto-approval, novel strategy discovery

**Regression Invariants:**

- All 12 existing strategies instantiate and register correctly with unchanged behavior
- Existing YAML configs with no detection params still work (Pydantic defaults match constructor defaults)
- PatternBacktester functions for all previously supported patterns (bull_flag, flat_top, abcd)
- Non-PatternModule strategies are completely untouched
- Shadow mode routing (Sprint 27.7) continues to work
- CounterfactualTracker continues to track rejected signals
- Test suite passes (4,212 pytest + 700 Vitest)
- Config validation catches invalid values at startup (fail-closed)
- Paper trading data-capture overrides (Sprint 29.5) unaffected

**File Scope:**

- Modify: `argus/core/config.py`, `argus/main.py`, `argus/backtest/vectorbt_pattern.py`, `argus/analytics/trade_logger.py`, `argus/api/server.py`
- Create: `argus/strategies/patterns/factory.py`, `argus/intelligence/experiments/` package (5 modules), `argus/api/routes/experiments.py`, `scripts/run_experiment.py`, `config/experiments.yaml`, `argus/intelligence/experiments/config.py`
- Do not modify: Any non-PatternModule strategy file, `argus/core/orchestrator.py` (strategies register through existing API), `argus/intelligence/learning/` (existing Learning Loop V1), `argus/intelligence/counterfactual.py` (existing tracker — we consume it, don't change it), frontend files

**Config Changes:**

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| experiments.enabled | ExperimentConfig | enabled | false |
| experiments.max_shadow_variants_per_pattern | ExperimentConfig | max_shadow_variants_per_pattern | 5 |
| experiments.backtest_min_trades | ExperimentConfig | backtest_min_trades | 20 |
| experiments.backtest_min_expectancy | ExperimentConfig | backtest_min_expectancy | 0.0 |
| experiments.promotion_min_shadow_days | ExperimentConfig | promotion_min_shadow_days | 5 |
| experiments.promotion_min_shadow_trades | ExperimentConfig | promotion_min_shadow_trades | 30 |
| experiments.cache_dir | ExperimentConfig | cache_dir | "data/databento_cache" |
| + 28 missing detection param fields across 6 pattern configs | Various *Config classes | See Session 1 detail | Match constructor defaults |

**Test Strategy:**

- Session 1: ~8 tests (cross-validation of config fields vs constructor params per pattern)
- Session 2: ~10 tests (factory construction, fingerprint stability, edge cases)
- Session 3: ~8 tests (end-to-end wiring, backtester extension, fingerprint in trades)
- Session 4: ~10 tests (store CRUD, retention, query API)
- Session 5: ~8 tests (spawner variant creation, startup registration, config parsing)
- Session 6: ~8 tests (runner orchestration, grid generation, result storage)
- Session 7: ~8 tests (promotion criteria, Pareto comparison, demotion logic)
- Session 8: ~8 tests (API endpoints, CLI, server wiring, config gating)
- Estimated total: ~68 new tests → ~4,280 pytest post-sprint

**Runner Compatibility:**

- Mode: Human-in-the-loop
- Parallelizable sessions: S4 ∥ S6 possible (create independent files, both depend on S2 only), informational only
- Runner-specific escalation notes: N/A (HITL mode)

**Dependencies:**

- Sprint 29.5 complete (✓)
- Full-universe Parquet cache populated (✓ — 44.73 GB)
- BacktestEngine functional (✓ — Sprint 27)
- CounterfactualTracker functional (✓ — Sprint 27.7)
- Evaluation Framework comparison API functional (✓ — Sprint 27.5)

**Escalation Criteria:**

- If variant spawning causes > 2× memory increase at startup → Tier 3
- If shadow variant processing causes > 10% throughput degradation to live strategies → Tier 3
- If factory construction fails for any existing pattern with current defaults → HALT (regression)
- If fingerprint produces different hashes for identical configs → HALT (determinism violation)

**Doc Updates Needed:**

- `docs/project-knowledge.md` (architecture sections, sprint history, strategy count, build track)
- `CLAUDE.md` (new DEF/DEC entries)
- `docs/architecture.md` (experiment pipeline section)
- `docs/roadmap.md` (Sprint 32 completion, 32.5 merged)
- `docs/sprint-history.md` (Sprint 32 entry)
- `docs/decision-log.md` + `docs/dec-index.md` (new DECs)
- `docs/pre-live-transition-checklist.md` (experiment config defaults for paper vs live)

**Artifacts to Generate:**

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates per session)
4. Implementation Prompt ×8
5. Review Prompt ×8
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff Prompt

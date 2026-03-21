# Sprint 26: Session Breakdown

## Session Summary

| Session | Title | Creates | Modifies | Integrates | Score | Parallelizable |
|---------|-------|---------|----------|------------|-------|----------------|
| S1 | PatternModule ABC + Package | 2 files | — | N/A | 12 | false |
| S2 | R2G Config + State Machine Skeleton | 2 files | 2 files | N/A | 13 | false |
| S3 | R2G Entry/Exit/PatternStrength Completion | — | 1 file | S2 | 12 | false |
| S4 | PatternBasedStrategy Wrapper | 1 file | 1 file | S1 | 13 | false |
| S5 | BullFlagPattern + Config | 2 files | 2 files | S1, S4 | 13 | false |
| S6 | FlatTopBreakoutPattern + Config | 2 files | 2 files | S1, S4 | 13 | false |
| S7 | VectorBT R2G + Walk-Forward | 1 file | — | S3 | 10 | false |
| S8 | Generic VectorBT Pattern Backtester | 1 file | — | S5, S6 | 11 | false |
| S9 | Integration Wiring | — | 2 files | S3, S5, S6 | 13 | false |
| S10 | UI — Pattern Library Cards | — | 4 files | S9 | 12 | false |
| S10f | Visual Review Fix Contingency | — | TBD | S10 | (0.5) | — |

**Dependency chain:**
```
S1 ───────────→ S4 → S5 → S6 ──→ S8 ─┐
S2 → S3 ──────────────────────→ S7 ─┤→ S9 → S10 → S10f
                                      │
       (S5, S6 also feed into S9) ───┘
```

**Sequential execution order:** S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8 → S9 → S10 → S10f

Note: S1 and S2 are independent (no shared dependencies). S1 builds the patterns ABC; S2 builds R2G as a BaseStrategy subclass. They could theoretically be swapped, but S1→S2→S3→S4→S5→S6 provides the cleanest context flow.

---

## Session 1: PatternModule ABC + Package

**Objective:** Create the `argus/strategies/patterns/` package with the PatternModule abstract base class and supporting data classes.

**Creates:**
- `argus/strategies/patterns/__init__.py` — Package init, exports PatternModule, PatternDetection
- `argus/strategies/patterns/base.py` — PatternModule ABC + PatternDetection dataclass

**Modifies:** —

**Integrates:** N/A (foundation)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 0 | 0 |
| Context reads (base_strategy.py, events.py, quality_engine.py) | 3 | 3 |
| New tests (~10) | 10 | 5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **12** |

**Tests:** ~10 (ABC enforcement, PatternDetection dataclass, abstract method signatures, score bounds, get_default_params)

**Parallelizable:** false

---

## Session 2: RedToGreenConfig + State Machine Skeleton

**Objective:** Create the RedToGreenStrategy skeleton with 5-state machine, config model, YAML config, and state transition tests. This session builds the state machine shell and per-symbol state tracking — entry criteria details are completed in S3.

**Creates:**
- `argus/strategies/red_to_green.py` — R2G strategy class with state machine (WATCHING/GAP_DOWN_CONFIRMED/TESTING_LEVEL/ENTERED/EXHAUSTED), per-symbol state dataclass, init, basic on_candle routing to state handlers, reset_daily_state, reconstruct_state stub
- `config/strategies/red_to_green.yaml` — Full config with all parameters, operating window, risk limits, benchmarks, universe_filter, backtest_summary

**Modifies:**
- `argus/core/config.py` — Add RedToGreenConfig(StrategyConfig) class + model_validator + `load_red_to_green_config()` loader
- `argus/strategies/__init__.py` — Add R2G import

**Integrates:** N/A (R2G is a BaseStrategy subclass, independent of PatternModule ABC)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 2 | 2 |
| Context reads (base_strategy.py, vwap_reclaim.py, config.py, events.py) | 4 | 4 |
| New tests (~6: config validation, state transitions, state dataclass) | 6 | 3 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (red_to_green.py skeleton ~300 lines) | 0 | 0 |
| **Total** | | **13** |

**Tests:** ~8 (RedToGreenConfig validation, min/max gap validator, state machine transitions WATCHING→GAP_DOWN_CONFIRMED, GAP_DOWN_CONFIRMED→TESTING_LEVEL, TESTING_LEVEL→EXHAUSTED, reset_daily_state, config load from YAML with key verification)

**Parallelizable:** false (but independent of S1)

---

## Session 3: R2G Entry/Exit/PatternStrength Completion

**Objective:** Complete the RedToGreenStrategy with full entry criteria checking, exit rules, `_calculate_pattern_strength()`, scanner criteria, market conditions filter, and comprehensive edge case tests.

**Creates:** —

**Modifies:**
- `argus/strategies/red_to_green.py` — Complete TESTING_LEVEL→ENTERED transition logic (level proximity check, volume confirmation, chase guard, operating window check), `_calculate_pattern_strength()`, `get_exit_rules()`, `get_scanner_criteria()`, `get_market_conditions_filter()`, `calculate_position_size()`, evaluation telemetry `record_evaluation()` calls, `reconstruct_state()` full implementation

**Integrates:** S2 (extends R2G skeleton)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 | 1 |
| Context reads (red_to_green.py from S2, base_strategy.py, vwap_reclaim.py entry/exit reference, config.py, events.py) | 5 | 5 |
| New tests (~12: entry criteria, exit rules, pattern_strength, scanner, market filter, edge cases) | 12 | 6 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **12** |

**Tests:** ~12 (entry criteria with mock candles: volume confirmation, chase guard, operating window, level proximity for VWAP/premarket_low/prior_close; exit rules validation; pattern_strength scoring with various inputs; scanner criteria; market conditions filter; gap-up rejection; max gap exhaustion; re-test after level break)

**Parallelizable:** false

---

## Session 4: PatternBasedStrategy Wrapper

**Objective:** Create the generic PatternBasedStrategy that wraps any PatternModule and implements all BaseStrategy abstract methods.

**Creates:**
- `argus/strategies/pattern_strategy.py` — PatternBasedStrategy(BaseStrategy) that takes a PatternModule in constructor; delegates on_candle→detect(), _calculate_pattern_strength→score(); implements operating window from config, signal generation, evaluation telemetry, daily state management

**Modifies:**
- `argus/strategies/patterns/__init__.py` — Export PatternBasedStrategy for convenience

**Integrates:** S1 (wraps PatternModule ABC)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads (patterns/base.py, base_strategy.py, config.py, events.py) | 4 | 4 |
| New tests (~10: delegation, operating window, signal generation, telemetry, edge cases) | 10 | 5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (pattern_strategy.py ~200 lines) | 1 | 2 |
| **Total** | | **14** |

⚠️ **Score is 14 — at the "must split" boundary.** Mitigation: pattern_strategy.py follows a very well-established pattern (mirrors BaseStrategy implementations in vwap_reclaim.py and afternoon_momentum.py). The delegation model is straightforward. The large file score is conservative — the wrapper may be under 150 lines since it delegates heavily. Proceeding at 14 with the understanding that if compaction occurs, the session should be split at the test-writing boundary. **If implementation time suggests this will compact, halt and split before tests.**

**Tests:** ~10 (PatternBasedStrategy with mock PatternModule: detect→signal generation, detect→None silence, operating window enforcement, pattern_strength delegation, daily state reset, evaluation telemetry recording, config-driven targets/stops, scanner criteria passthrough, market conditions filter passthrough, edge case: detect returns None repeatedly)

**Parallelizable:** false

---

## Session 5: BullFlagPattern + Config

**Objective:** Implement the Bull Flag pattern detection module with pole detection, flag consolidation validation, breakout confirmation, and config.

**Creates:**
- `argus/strategies/patterns/bull_flag.py` — BullFlagPattern(PatternModule) with detect(), score(), get_default_params()
- `config/strategies/bull_flag.yaml` — Full config with pattern params, operating_window, risk_limits, benchmarks, universe_filter

**Modifies:**
- `argus/core/config.py` — Add BullFlagConfig(StrategyConfig) + `load_bull_flag_config()` loader
- `argus/strategies/patterns/__init__.py` — Add BullFlagPattern export

**Integrates:** S1 (implements PatternModule), S4 (used by PatternBasedStrategy)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 2 | 2 |
| Context reads (patterns/base.py, pattern_strategy.py, config.py) | 3 | 3 |
| New tests (~8: detection logic, scoring, edge cases, config) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13** |

**Tests:** ~8 (bull flag detection with synthetic candle sequences: valid pole+flag+breakout, pole too short, pole move too small, flag retrace too deep, flag too long, no volume on breakout, score ranges, config validation with YAML key verification)

**Parallelizable:** false

---

## Session 6: FlatTopBreakoutPattern + Config

**Objective:** Implement the Flat-Top Breakout pattern detection module with resistance detection, consolidation validation, breakout confirmation, and config.

**Creates:**
- `argus/strategies/patterns/flat_top_breakout.py` — FlatTopBreakoutPattern(PatternModule) with detect(), score(), get_default_params()
- `config/strategies/flat_top_breakout.yaml` — Full config with pattern params, operating_window, risk_limits, benchmarks, universe_filter

**Modifies:**
- `argus/core/config.py` — Add FlatTopBreakoutConfig(StrategyConfig) + `load_flat_top_breakout_config()` loader
- `argus/strategies/patterns/__init__.py` — Add FlatTopBreakoutPattern export

**Integrates:** S1 (implements PatternModule), S4 (used by PatternBasedStrategy)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 2 | 2 |
| Context reads (patterns/base.py, pattern_strategy.py, config.py) | 3 | 3 |
| New tests (~8: detection logic, scoring, edge cases, config) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13** |

**Tests:** ~8 (flat-top detection: valid resistance+consolidation+breakout, insufficient touches, tolerance exceeded, no consolidation, no volume on breakout, score ranges, config validation with YAML key verification)

**Parallelizable:** false

---

## Session 7: VectorBT R2G + Walk-Forward

**Objective:** Build the VectorBT backtest module for Red-to-Green and run walk-forward validation.

**Creates:**
- `argus/backtest/vectorbt_red_to_green.py` — R2G-specific VectorBT implementation: gap-down detection, level identification, entry/exit signal generation, parameter sweep across min_gap_down, level_proximity, volume_confirmation, time_stop; walk-forward validation with WFE calculation

**Modifies:** —

**Integrates:** S3 (backtests R2G strategy logic)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 0 | 0 |
| Context reads (red_to_green.py, vectorbt_vwap_reclaim.py reference, walk_forward.py, config) | 4 | 4 |
| New tests (~5: sweep, walk-forward, report) | 5 | 2.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (vectorbt module ~800–1000 lines) | 1 | 2 |
| **Total** | | **10.5** |

**Tests:** ~5 (parameter sweep execution, walk-forward validation runs, WFE calculation, report generation, edge case with insufficient data)

**Parallelizable:** false

**Human review point:** After S7 completes, review VectorBT results. If WFE < 0.3, discuss before proceeding with S9 integration wiring. R2G can be wired in as `enabled: false` / `pipeline_stage: "exploration"`.

---

## Session 8: Generic VectorBT Pattern Backtester

**Objective:** Build a reusable VectorBT backtester for PatternModule-based strategies and run walk-forward for Bull Flag and Flat-Top.

**Creates:**
- `argus/backtest/vectorbt_pattern.py` — Generic pattern backtester: takes PatternModule + config, applies pattern detection to historical candles, generates entry/exit signals from defaults, parameter sweep, walk-forward. Runs for both Bull Flag and Flat-Top.

**Modifies:** —

**Integrates:** S5 (Bull Flag), S6 (Flat-Top)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 0 | 0 |
| Context reads (patterns/base.py, bull_flag.py, flat_top_breakout.py, vectorbt_vwap_reclaim.py reference, walk_forward.py) | 5 | 5 |
| New tests (~6: generic backtester, walk-forward per pattern) | 6 | 3 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (vectorbt_pattern.py ~600–800 lines) | 1 | 2 |
| **Total** | | **12** |

**Tests:** ~6 (generic backtester with mock pattern, Bull Flag walk-forward, Flat-Top walk-forward, parameter sweep mechanics, report generation, edge case with no detections)

**Parallelizable:** false

**Human review point:** After S8, review Bull Flag and Flat-Top backtest results. Same WFE < 0.3 escalation applies.

---

## Session 9: Integration Wiring

**Objective:** Wire all 3 new strategies/patterns into main.py, Orchestrator registration, and universe filter configs. Verify all 7 strategies appear in API responses.

**Creates:** —

**Modifies:**
- `argus/main.py` — Add R2G strategy creation in Phase 8 (optional, config-gated like VWAP/AfMo), add Bull Flag and Flat-Top as PatternBasedStrategy instances, register all 3 with Orchestrator
- `argus/strategies/__init__.py` — Ensure all necessary imports

**Integrates:** S3 (R2G), S5 (Bull Flag), S6 (Flat-Top) → main.py → Orchestrator

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Context reads (main.py, config.py, red_to_green.py, pattern_strategy.py) | 4 | 4 |
| New tests (~8: strategy creation, registration, UM routing, API response) | 8 | 4 |
| Complex integration wiring (main→strategies→orchestrator→UM) | 1 | 3 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13** |

**Tests:** ~8 (R2G strategy creation from config, Bull Flag PatternBasedStrategy creation, Flat-Top PatternBasedStrategy creation, all 3 registered with Orchestrator, UM routing table includes new strategies, API /strategies returns 7, disabled strategy not created, integration test with mock candle routing)

**Parallelizable:** false

---

## Session 10: UI — Pattern Library Cards

**Objective:** Ensure the Pattern Library page correctly displays 3 new strategy/pattern cards using existing component infrastructure.

**Creates:** —

**Modifies:**
- `argus/ui/src/api/types.ts` — Verify StrategiesResponse type handles new families (may need no changes if type is generic)
- `argus/ui/src/features/patterns/PatternCard.tsx` — Verify rendering handles new strategy families (may need family color/icon additions)
- `argus/ui/src/features/patterns/PatternDetail.tsx` — Verify detail panel handles new strategies
- `argus/ui/src/pages/PatternLibraryPage.tsx` — Verify page renders with 7 strategies (likely no changes needed)

**Integrates:** S9 (API serves all 7 strategies)

**Compaction Risk Scoring:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 4 (conservative — may be fewer) | 4 |
| Context reads (PatternLibraryPage.tsx, PatternCard.tsx, PatternDetail.tsx, api/types.ts) | 4 | 4 |
| New tests (~8 Vitest) | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **12** |

**Tests:** ~8 Vitest (3 new cards render with correct names, family badges display, pipeline stage badges display, backtest summary shows, PatternDetail tabs work for new strategies, responsive layout with 7 cards, search/filter includes new strategies)

**Parallelizable:** false

**Visual review items** (for developer verification after session):
1. Pattern Library shows 7 cards (4 existing + 3 new)
2. New cards display correct family label and color
3. Card grid layout is not broken by 7 cards
4. Clicking new card opens detail panel with correct tabs
5. Pipeline stage filter includes new strategies at correct stage

---

## Session 10f: Visual Review Fix Contingency (0.5 session)

**Objective:** Fix any visual issues discovered during S10 developer review.

**Creates:** —
**Modifies:** Frontend components as needed
**Integrates:** S10
**Score:** Contingency — unused if visual review passes

---

## DEC/RSK/DEF Number Reservations

- **DEC-357 through DEC-370** reserved for Sprint 26 decisions
- **RSK-055 through RSK-058** reserved for Sprint 26 risks
- **DEF-088 through DEF-095** reserved for Sprint 26 deferred items

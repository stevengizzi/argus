# Sprint 26 Design Summary

**Sprint Goal:** Add Red-to-Green reversal strategy, PatternModule ABC infrastructure, Bull Flag and Flat-Top Breakout pattern modules, VectorBT backtesting for all three, integration wiring, and Pattern Library UI cards — bringing ARGUS from 4 to 7 active strategies/patterns.

**Execution Mode:** Human-in-the-loop (VectorBT backtest results require human judgment for parameter selection; R2G is the first reversal strategy, benefiting from trading intuition review).

## Session Breakdown

- **Session 1:** PatternModule ABC + `patterns/` package
  - Creates: `argus/strategies/patterns/__init__.py`, `argus/strategies/patterns/base.py`
  - Modifies: —
  - Integrates: N/A (foundation)
  - Score: 12 (Low→Medium)
  - Parallelizable: false

- **Session 2:** RedToGreenConfig + R2G state machine skeleton + state transition tests
  - Creates: `argus/strategies/red_to_green.py`, `config/strategies/red_to_green.yaml`
  - Modifies: `argus/core/config.py` (RedToGreenConfig class + loader), `argus/strategies/__init__.py`
  - Integrates: N/A (independent of S1; R2G is a BaseStrategy subclass, not PatternModule-based)
  - Score: 13 (Medium)
  - Parallelizable: false (but independent of S1)

- **Session 3:** R2G entry criteria + exit rules + `_calculate_pattern_strength()` + scanner criteria + market conditions filter + remaining tests
  - Creates: —
  - Modifies: `argus/strategies/red_to_green.py` (completes implementation)
  - Integrates: S2 (extends R2G skeleton)
  - Score: 12 (Medium)
  - Parallelizable: false

- **Session 4:** PatternBasedStrategy generic wrapper + tests
  - Creates: `argus/strategies/pattern_strategy.py`
  - Modifies: `argus/strategies/patterns/__init__.py`
  - Integrates: S1 (wraps PatternModule ABC)
  - Score: 13 (Medium)
  - Parallelizable: false (depends on S1)

- **Session 5:** BullFlagPattern + config + tests
  - Creates: `argus/strategies/patterns/bull_flag.py`, `config/strategies/bull_flag.yaml`
  - Modifies: `argus/core/config.py` (BullFlagConfig class + loader), `argus/strategies/patterns/__init__.py`
  - Integrates: S1 (implements PatternModule), S4 (used by PatternBasedStrategy)
  - Score: 13 (Medium)
  - Parallelizable: false

- **Session 6:** FlatTopBreakoutPattern + config + tests
  - Creates: `argus/strategies/patterns/flat_top_breakout.py`, `config/strategies/flat_top_breakout.yaml`
  - Modifies: `argus/core/config.py` (FlatTopBreakoutConfig class + loader), `argus/strategies/patterns/__init__.py`
  - Integrates: S1 (implements PatternModule), S4 (used by PatternBasedStrategy)
  - Score: 13 (Medium)
  - Parallelizable: false

- **Session 7:** VectorBT Red-to-Green backtest + walk-forward validation
  - Creates: `argus/backtest/vectorbt_red_to_green.py`
  - Modifies: —
  - Integrates: S3 (backtests R2G strategy)
  - Score: 10 (Low→Medium)
  - Parallelizable: false

- **Session 8:** Generic VectorBT Pattern Backtester + walk-forward for Bull Flag and Flat-Top
  - Creates: `argus/backtest/vectorbt_pattern.py`
  - Modifies: —
  - Integrates: S5, S6 (backtests both pattern modules via PatternBasedStrategy)
  - Score: 11 (Medium)
  - Parallelizable: false

- **Session 9:** Integration wiring (main.py, API registration, universe filters) + integration tests
  - Creates: —
  - Modifies: `argus/main.py`, `argus/strategies/__init__.py`
  - Integrates: S3 (R2G), S5 (Bull Flag), S6 (Flat-Top) → main.py registration + Orchestrator
  - Score: 13 (Medium)
  - Parallelizable: false

- **Session 10:** UI updates — 3 new Pattern Library cards + frontend tests
  - Creates: —
  - Modifies: Pattern Library components (PatternCard.tsx, PatternDetail.tsx, etc.), api/types.ts
  - Integrates: S9 (API serves all 7 strategies)
  - Score: 12 (Medium)
  - Parallelizable: false

- **Session 10f:** Visual review fix contingency (0.5 session)
  - Creates: —
  - Modifies: frontend components as needed
  - Integrates: S10
  - Contingency — unused if visual review passes

**Dependency chain:**
```
S1 ────────→ S4 → S5 → S6 ──→ S8 ─┐
S2 → S3 ──────────────────→ S7 ─┤→ S9 → S10 → S10f
                                    │
   (S5, S6 also feed into S9) ─────┘
```

## Key Decisions

1. **Option A: PatternModule ABC + PatternBasedStrategy wrapper.** PatternModule ABC defines `detect()`, `score()`, `get_default_params()`. PatternBasedStrategy extends BaseStrategy, takes a PatternModule, delegates detection. Reduces per-pattern boilerplate from ~400+ lines to ~100. BacktestEngine-compatible. Existing strategies untouched.

2. **R2G is a standalone BaseStrategy subclass** (like VWAP Reclaim), NOT a PatternModule-based strategy. It has its own state machine and is too complex for the generic wrapper. The PatternBasedStrategy wrapper is for simpler pattern detection modules (Bull Flag, Flat-Top).

3. **R2G state machine: 5 states** — WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED → EXHAUSTED. Similar architecture to VWAP Reclaim's 5-state machine.

4. **Gap-down detection is dynamic, not a universe filter.** UniverseFilterConfig stays unchanged. R2G's `on_candle` checks gap direction dynamically. FMP Scanner already provides biggest-losers for scanner-mode fallback.

5. **Backtesting uses VectorBT + walk-forward** (last sprint before BacktestEngine). Results are provisional per DEC-132. Walk-forward validation mandatory (DEC-047, WFE > 0.3).

6. **PatternBasedStrategy operating window and exit rules come from config YAML.** Each pattern config (bull_flag.yaml, flat_top_breakout.yaml) includes operating_window, risk_limits, and pattern-specific parameters. The PatternBasedStrategy reads these from its StrategyConfig.

7. **Adversarial review warranted** for PatternModule ABC interface design (foundational for 15+ future patterns).

## Scope Boundaries

- **IN:** PatternModule ABC, PatternBasedStrategy wrapper, RedToGreenStrategy (stages 1–2), BullFlagPattern, FlatTopBreakoutPattern, VectorBT backtest modules for all three, walk-forward validation, integration wiring (main.py, configs, UM routing), Pattern Library UI cards (3 new), strategy spec sheets (3 new), ~80 new tests
- **OUT:** Replay Harness cross-validation (stage 3, deferred to post-BacktestEngine Sprint 27), short selling, pattern parameterization/templates (Sprint 32), ensemble orchestration (Sprint 32–38), BacktestEngine integration (Sprint 27), Learning Loop weight optimization (Sprint 28), FMP Premium upgrade (DEC-356), historical data purchase (DEC-353)

## Regression Invariants

1. Existing 4 strategies produce signals correctly (no code changes to their files)
2. Quality Engine scores existing strategies correctly (pattern_strength flow unchanged)
3. BaseStrategy abstract interface unchanged
4. SignalEvent schema unchanged
5. Universe Manager routing works for existing strategies
6. Pattern Library UI displays existing 4 cards correctly
7. Risk Manager gating unchanged
8. All existing ~2,815 pytest + ~611 Vitest pass
9. Orchestrator capital allocation handles 7 strategies (was 4)
10. API endpoints return all registered strategies

## File Scope

**Create:**
- `argus/strategies/patterns/__init__.py`
- `argus/strategies/patterns/base.py`
- `argus/strategies/pattern_strategy.py`
- `argus/strategies/red_to_green.py`
- `argus/strategies/patterns/bull_flag.py`
- `argus/strategies/patterns/flat_top_breakout.py`
- `config/strategies/red_to_green.yaml`
- `config/strategies/bull_flag.yaml`
- `config/strategies/flat_top_breakout.yaml`
- `argus/backtest/vectorbt_red_to_green.py`
- `argus/backtest/vectorbt_pattern.py`
- `docs/strategies/STRATEGY_RED_TO_GREEN.md`
- `docs/strategies/STRATEGY_BULL_FLAG.md`
- `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md`

**Modify:**
- `argus/core/config.py` (3 new config classes + loaders)
- `argus/strategies/__init__.py` (imports)
- `argus/strategies/patterns/__init__.py` (imports, across sessions)
- `argus/main.py` (strategy creation + registration in Phase 8)
- Frontend: `PatternCard.tsx`, `PatternDetail.tsx`, `api/types.ts` (minor — new cards render from existing API data)

**Do not modify:**
- `argus/strategies/base_strategy.py`
- `argus/strategies/orb_base.py`, `orb_breakout.py`, `orb_scalp.py`
- `argus/strategies/vwap_reclaim.py`, `afternoon_momentum.py`
- `argus/core/events.py` (SignalEvent)
- `argus/intelligence/quality_engine.py`, `position_sizer.py`
- `argus/core/orchestrator.py`, `risk_manager.py`
- `argus/data/universe_manager.py`, `fmp_scanner.py`
- Existing strategy config files (`orb_breakout.yaml`, `orb_scalp.yaml`, `vwap_reclaim.yaml`, `afternoon_momentum.yaml`)

## Config Changes

| YAML File | YAML Key | Pydantic Model | Field |
|-----------|----------|----------------|-------|
| `config/strategies/red_to_green.yaml` | `min_gap_down_pct` | `RedToGreenConfig` | `min_gap_down_pct` |
| | `max_gap_down_pct` | | `max_gap_down_pct` |
| | `level_proximity_pct` | | `level_proximity_pct` |
| | `min_level_test_bars` | | `min_level_test_bars` |
| | `volume_confirmation_multiplier` | | `volume_confirmation_multiplier` |
| | `max_chase_pct` | | `max_chase_pct` |
| | `target_1_r` | | `target_1_r` |
| | `target_2_r` | | `target_2_r` |
| | `time_stop_minutes` | | `time_stop_minutes` |
| | `stop_buffer_pct` | | `stop_buffer_pct` |
| `config/strategies/bull_flag.yaml` | `pole_min_bars` | `BullFlagConfig` | `pole_min_bars` |
| | `pole_min_move_pct` | | `pole_min_move_pct` |
| | `flag_max_bars` | | `flag_max_bars` |
| | `flag_max_retrace_pct` | | `flag_max_retrace_pct` |
| | `breakout_volume_multiplier` | | `breakout_volume_multiplier` |
| | `target_1_r` | | `target_1_r` |
| | `target_2_r` | | `target_2_r` |
| | `time_stop_minutes` | | `time_stop_minutes` |
| `config/strategies/flat_top_breakout.yaml` | `resistance_touches` | `FlatTopBreakoutConfig` | `resistance_touches` |
| | `resistance_tolerance_pct` | | `resistance_tolerance_pct` |
| | `consolidation_min_bars` | | `consolidation_min_bars` |
| | `breakout_volume_multiplier` | | `breakout_volume_multiplier` |
| | `target_1_r` | | `target_1_r` |
| | `target_2_r` | | `target_2_r` |
| | `time_stop_minutes` | | `time_stop_minutes` |

All three inherit `StrategyConfig` base fields (strategy_id, name, version, enabled, operating_window, risk_limits, benchmarks, universe_filter, backtest_summary).

Regression checklist item: Config validation test per new YAML file.

## Test Strategy

- **~76 new pytest + ~8 new Vitest ≈ 84 new tests**
- Per-session breakdown:
  - S1: ~10 pytest (ABC interface, abstract method enforcement, default implementations)
  - S2: ~8 pytest (R2G config validation, state machine transitions)
  - S3: ~10 pytest (R2G entry criteria, exit rules, pattern_strength, edge cases)
  - S4: ~10 pytest (PatternBasedStrategy wrapper, delegation, operating window)
  - S5: ~8 pytest (Bull Flag detection, edge cases, config)
  - S6: ~8 pytest (Flat-Top detection, edge cases, config)
  - S7: ~5 pytest (VectorBT R2G sweep, walk-forward)
  - S8: ~5 pytest (VectorBT pattern backtester, walk-forward)
  - S9: ~10 pytest (integration wiring, strategy registration, UM routing)
  - S10: ~8 Vitest (Pattern Library cards, rendering, data display)
- Target total: ~2,891 pytest + ~619 Vitest (2,815+76 / 611+8)

## Runner Compatibility

- Mode: Human-in-the-loop
- Parallelizable sessions: none (all sequential)
- Work journal handoff prompt: YES (required for HITL)
- Runner config: SKIP (not generating)

## Dependencies

- Alpaca historical data available for VectorBT sweeps (existing data source)
- All existing tests passing on main branch
- Phase 5 Gate doc sync completed (confirmed March 21)

## Escalation Criteria

- If PatternModule ABC interface design is challenged during adversarial review, halt prompt generation
- If VectorBT walk-forward validation fails (WFE < 0.3) for any strategy/pattern: wire it in disabled/incubator state, document results, do not promote to paper trading
- If R2G state machine has fundamental design issues after S2, halt S3 for design review
- If integration wiring (S9) causes existing strategy test failures, escalate before proceeding

## Doc Updates Needed

- `docs/project-knowledge.md` — sprint history, test counts, build track, strategy count, active decisions
- `docs/architecture.md` — PatternModule ABC, PatternBasedStrategy, patterns/ package
- `CLAUDE.md` — active sprint, test counts, infrastructure list, project structure
- `docs/roadmap.md` — Sprint 26 marked complete, Sprint 27 context
- `docs/sprint-history.md` — Sprint 26 entry
- `docs/decision-log.md` — new DEC entries (PatternModule ABC, PatternBasedStrategy, R2G design, etc.)
- `docs/dec-index.md` — new DEC index entries
- `docs/strategies/STRATEGY_RED_TO_GREEN.md` — new spec sheet
- `docs/strategies/STRATEGY_BULL_FLAG.md` — new spec sheet
- `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md` — new spec sheet
- `docs/risk-register.md` — any new risks from R2G (reversal strategy risk profile)
- `docs/ui/ux-feature-backlog.md` — mark completed items, add any new items

## Artifacts to Generate

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with scoring tables)
4. Escalation Criteria
5. Regression Checklist
6. Doc Update Checklist
7. Adversarial Review Input Package
8. Review Context File
9. Implementation Prompts ×10
10. Tier 2 Review Prompts ×10
11. Work Journal Handoff Prompt

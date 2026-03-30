# Sprint 29 Design Summary

**Sprint Goal:** Add 5 new PatternModule strategies (Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, Pre-Market High Break) and introduce the PatternParam structured type (DEF-088) with machine-readable parameter metadata for all patterns. Reach 12 active strategies. Pre-Market High Break is stretch — droppable if velocity requires.

**Execution Mode:** Human-in-the-loop.

**Session Breakdown:**

- **S1: PatternParam Core + Reference Data Hook** (score: 8, Low)
  - Creates: PatternParam dataclass in `base.py`
  - Modifies: `strategies/patterns/base.py` (PatternParam + ABC signature + optional `set_reference_data()` with default no-op), `strategies/pattern_strategy.py` (call reference data hook during init)
  - Integrates: N/A (foundation)

- **S2: Retrofit Existing Patterns + PatternBacktester** (score: 12, Medium)
  - Creates: none
  - Modifies: `strategies/patterns/bull_flag.py`, `strategies/patterns/flat_top_breakout.py`, `backtest/vectorbt_pattern.py`
  - Integrates: S1's PatternParam into existing patterns and backtester grid generation

- **S3: Dip-and-Rip Pattern** (score: 12 adjusted, Medium)
  - Creates: `strategies/patterns/dip_and_rip.py`, `config/strategies/dip_and_rip.yaml`, `config/universe_filters/dip_and_rip.yaml`
  - Modifies: `config/exit_management.yaml`, strategy registration
  - Integrates: S1's PatternParam

- **S4: HOD Break Pattern** (score: 12 adjusted, Medium)
  - Creates: `strategies/patterns/hod_break.py`, `config/strategies/hod_break.yaml`, `config/universe_filters/hod_break.yaml`
  - Modifies: `config/exit_management.yaml`, strategy registration
  - Integrates: S1's PatternParam

- **S5: Gap-and-Go Pattern** (score: 13 adjusted, Medium)
  - Creates: `strategies/patterns/gap_and_go.py`, `config/strategies/gap_and_go.yaml`, `config/universe_filters/gap_and_go.yaml`
  - Modifies: `config/exit_management.yaml`, strategy registration
  - Integrates: S1's PatternParam + S1's reference data hook (first user of `set_reference_data()` for prior close)

- **S6a: ABCD Core — Swing Detection + Pattern Logic** (score: 15, High — justified: zero modifications, self-contained algorithm)
  - Creates: `strategies/patterns/abcd.py`
  - Modifies: none
  - Integrates: S1's PatternParam

- **S6b: ABCD Config + Wiring** (score: 9 adjusted, Low)
  - Creates: `config/strategies/abcd.yaml`, `config/universe_filters/abcd.yaml`
  - Modifies: `config/exit_management.yaml`, strategy registration
  - Integrates: S6a into full strategy pipeline

- **S7: Pre-Market High Break Pattern** (score: 13 adjusted, Medium) [STRETCH]
  - Creates: `strategies/patterns/premarket_high_break.py`, `config/strategies/premarket_high_break.yaml`, `config/universe_filters/premarket_high_break.yaml`
  - Modifies: `config/exit_management.yaml`, strategy registration
  - Integrates: S1's PatternParam + S1's reference data hook

- **S8: Integration Verification + Smoke Backtests** (score: ~10, Medium)
  - Creates: integration test file (if needed)
  - Modifies: none (fixes only if issues found)
  - Integrates: All S3–S7 patterns verified end-to-end

**Dependency Chain:** S1 → S2 → S3 → S4 → S5 → S6a → S6b → S7 → S8 (strictly serial)

**Key Decisions:**

- PatternParam frozen dataclass with fields: `name`, `param_type`, `default`, `min_value`, `max_value`, `step`, `description`, `category`. The `step` field enables Sprint 32 StrategyTemplate grid generation. The `category` field enables Sprint 31B Research Console grouping.
- `get_default_params()` return type changes from `dict[str, Any]` to `list[PatternParam]`. PatternBacktester updated to generate grids from PatternParam ranges.
- Optional `set_reference_data(data: dict[str, Any])` on PatternModule (default no-op). PatternBasedStrategy calls it during initialization with UM reference data (company profiles, prior closes). Used by Gap-and-Go (prior close for gap calculation) and Pre-Market High Break (prior close context).
- Pre-Market High Break computes PM high from candles already in PatternBasedStrategy's deque (pre-window accumulation from Sprint 27.65 fix). EQUS.MINI delivers extended-hours candles (4:00 AM–9:30 AM ET). No external data source needed.
- ABCD swing detection stays internal to `abcd.py` — not extracted as shared utility until Sprint 31A when more harmonic patterns exist.
- Adjusted compaction scoring for templated pattern sessions: config YAML <30 lines = +1 (not +2), filter YAML <15 lines = +1 (not +2), PatternModule template pattern .py = no "large file" surcharge.
- Walk-forward validation is post-sprint. In-sprint: smoke backtest per pattern (5 symbols × 6 months via PatternBacktester). Full WF via `scripts/validate_all_strategies.py` with `--cache-dir data/databento_cache` after sprint close.

**Pattern Specifications:**

| Pattern | Window | Key Mechanic | Scoring Weights | Exit Profile |
|---------|--------|-------------|-----------------|-------------|
| Dip-and-Rip | 9:45–11:30 | Sharp intraday dip + rapid recovery, VWAP/support interaction | 30 dip severity / 25 recovery velocity / 25 volume / 20 level interaction | ATR trail 1.5×, partial 1.5R, 30 min time stop |
| HOD Break | 10:00–15:30 | HOD consolidation + breakout, volume confirmation, multi-test resistance | 30 consolidation quality / 25 breakout volume / 25 prior HOD tests / 20 VWAP distance | ATR trail 2.0×, partial 2R, 60 min time stop |
| Gap-and-Go | 9:35–10:30 | Gap-up continuation, relative volume, VWAP hold, first pullback or direct breakout | 30 gap size/ATR / 30 volume ratio / 20 VWAP hold / 20 catalyst presence | Percent trail 1.5%, partial 1R, 20 min time stop |
| ABCD | 10:00–15:00 | Harmonic Fibonacci legs (AB-BC-CD), swing detection, completion zone entry | 35 Fibonacci precision / 25 leg symmetry / 20 volume pattern / 20 trend context | ATR trail 2.5×, partial 1.5R, 90 min time stop |
| Pre-Market High Break | 9:35–10:30 | PM high breakout, PM volume qualification, gap context | 30 PM high quality / 25 breakout volume / 25 gap context / 20 VWAP distance | ATR trail 1.5×, partial 1.5R, 30 min time stop |

**Universe Filters:**

| Pattern | min_price | max_price | min_avg_volume | Special |
|---------|-----------|-----------|----------------|---------|
| Dip-and-Rip | 5.0 | 200.0 | 500,000 | min_relative_volume: 1.5 |
| HOD Break | 5.0 | 500.0 | 300,000 | — |
| Gap-and-Go | 3.0 | 150.0 | 200,000 | min_gap_percent: 3.0 |
| ABCD | 10.0 | 300.0 | 500,000 | — |
| PM High Break | 5.0 | 200.0 | 300,000 | min_premarket_volume: 50,000 |

**Scope Boundaries:**
- IN: PatternParam type + retrofit, 5 new PatternModule patterns, strategy configs, universe filters, exit management overrides, unit/integration tests, smoke backtests, strategy registration
- OUT: Walk-forward validation (post-sprint), parameter optimization (Sprint 32), short selling (Sprint 30), frontend changes, Quality Engine recalibration, Learning Loop config changes, swing detection extraction as shared utility (Sprint 31A)

**Regression Invariants:**
1. Existing 7 strategies unchanged behavior
2. PatternModule ABC backward compatible
3. PatternBacktester produces identical results for Bull Flag / Flat-Top (grid backward compat in S2)
4. Exit Management per-strategy override merge (deep_update) unaffected
5. Universe Manager routing includes new patterns without disrupting existing routes
6. Quality Engine, Counterfactual Engine, Learning Loop automatically process new pattern signals
7. Event Bus FIFO ordering unaffected by additional strategy subscriptions

**File Scope:**
- Modify: `strategies/patterns/base.py`, `strategies/pattern_strategy.py`, `strategies/patterns/bull_flag.py`, `strategies/patterns/flat_top_breakout.py`, `backtest/vectorbt_pattern.py`, `config/exit_management.yaml`, strategy registration config
- Create: `strategies/patterns/dip_and_rip.py`, `strategies/patterns/hod_break.py`, `strategies/patterns/gap_and_go.py`, `strategies/patterns/abcd.py`, `strategies/patterns/premarket_high_break.py`, 5× strategy YAML, 5× filter YAML
- Do not modify: `core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `analytics/evaluation.py`, `intelligence/learning/`, `intelligence/counterfactual.py`, `core/fill_model.py`, `strategies/pattern_strategy.py` (after S1), `strategies/patterns/base.py` (after S1), `ui/` (entire frontend)

**Config Changes:**
- 5 new strategy YAML files → use existing PatternBasedStrategy config model (shared). Fields: `pattern_class`, `operating_window`, `allowed_regimes`, `mode`. No new Pydantic fields needed.
- 5 new universe filter YAML files → use existing UniverseFilter model. Gap-and-Go adds `min_gap_percent` — verify field exists in model or add. PM High Break adds `min_premarket_volume` — verify or add. Both require Pydantic model validation.
- `exit_management.yaml` → 5 new entries under `strategy_exit_overrides` → existing ExitManagementConfig model, no new fields.
- Regression checklist: "All new config fields verified against Pydantic model (no silently ignored keys)."

**Test Strategy:**
- ~84 new tests estimated across 9 sessions
- Per-pattern: ~10–14 tests (detection, scoring, edge cases, PatternParam, config parsing)
- PatternParam + retrofit: ~16 tests
- Integration verification: ~10 tests
- Smoke backtest runs (not counted as tests — CLI invocations)

**Runner Compatibility:**
- Mode: Human-in-the-loop
- Parallelizable sessions: none (shared exit_management.yaml modifications)
- Runner config: not generated

**Dependencies:**
- Sprint 28.5 complete (exit management infrastructure)
- PatternModule ABC, PatternBasedStrategy, PatternBacktester all operational
- Full-universe Parquet cache available for smoke backtests

**Escalation Criteria:**
- ABCD swing detection produces >50% false positive rate on manual spot-check → Tier 3
- Any existing pattern behavior changes detected → halt, investigate
- PatternBacktester grid generation produces different results for existing patterns → halt S2
- New universe filter field silently ignored by Pydantic → halt, fix model

**Doc Updates Needed:**
- `docs/project-knowledge.md` — add 5 strategies to Active Strategies table, update test counts, add sprint to history
- `CLAUDE.md` — strategy count, PatternParam reference, new pattern files
- `docs/sprint-history.md` — Sprint 29 entry
- `docs/decision-log.md` — DEC-382+ entries
- `docs/dec-index.md` — new DEC references
- `docs/strategies/` — 5 new STRATEGY_*.md spec sheets
- `docs/roadmap.md` — mark Sprint 29 complete

**DEC/DEF/RSK Reservations:**
- DEC-382 through DEC-395 (14 slots)
- DEF-109+ for deferred items
- RSK-049+ for new risks

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with scoring tables)
4. Implementation Prompts ×9 (S1, S2, S3, S4, S5, S6a, S6b, S7, S8)
5. Tier 2 Review Prompts ×9
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff Prompt

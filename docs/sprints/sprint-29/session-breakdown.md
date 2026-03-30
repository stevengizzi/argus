# Sprint 29: Session Breakdown

**Dependency chain:** S1 → S2 → S3 → S4 → S5 → S6a → S6b → S7 → S8 (strictly serial)
**Parallelizable sessions:** None (shared exit_management.yaml + strategy registration across pattern sessions)
**Adjusted scoring:** Templated pattern sessions use reduced scoring for boilerplate config/filter YAMLs (see rationale below)

---

## Adjusted Scoring Rationale

Standard compaction scoring (DEC-275) was calibrated against Sprint 22's AI Layer, where each new file was a deeply interconnected component. Pattern additions follow a rigid PatternModule template. The config YAML (<30 lines, identical structure) and filter YAML (<15 lines, identical structure) files have near-zero compaction risk. Adjustment:
- Config YAML following template: +1 instead of +2
- Universe filter YAML following template: +1 instead of +2
- Pattern .py following PatternModule template: no "large file" surcharge

ABCD (S6a) uses STANDARD scoring because its swing detection infrastructure is genuinely novel.

---

## S1: PatternParam Core + Reference Data Hook

**Objective:** Define the PatternParam dataclass, update PatternModule ABC signature, add optional reference data hook.

**Creates:**
- PatternParam dataclass in `strategies/patterns/base.py` (not a new file — addition to existing)

**Modifies:**
- `strategies/patterns/base.py` — add PatternParam dataclass, change `get_default_params()` return type to `list[PatternParam]`, add `set_reference_data(data: dict[str, Any])` with default no-op
- `strategies/pattern_strategy.py` — call `self._pattern.set_reference_data(reference_data)` during initialization when UM reference data available

**Integrates:** N/A (foundation session)

**Parallelizable:** false

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Context reads (base.py, pattern_strategy.py, CandleBar/PatternDetection) | 3 | 3 |
| Tests (~6: PatternParam construction, validation, type checking, range semantics, reference data no-op, reference data override) | 6 | 3 |
| Complex integration (3+) | No | 0 |
| External API | No | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **8 (Low)** |

**Acceptance criteria:**
- PatternParam frozen dataclass with 8 fields importable from `strategies.patterns.base`
- `get_default_params()` ABC returns `list[PatternParam]`
- `set_reference_data()` exists with default no-op
- PatternBasedStrategy calls `set_reference_data()` during init
- All existing tests pass (Bull Flag/Flat-Top temporarily broken until S2 — acceptable if caught by S2)
- 6 new tests pass

---

## S2: Retrofit Existing Patterns + PatternBacktester Grid Generation

**Objective:** Convert Bull Flag and Flat-Top to PatternParam returns. Update PatternBacktester to generate grids from PatternParam metadata.

**Creates:** None

**Modifies:**
- `strategies/patterns/bull_flag.py` — `get_default_params()` returns `list[PatternParam]`
- `strategies/patterns/flat_top_breakout.py` — `get_default_params()` returns `list[PatternParam]`
- `backtest/vectorbt_pattern.py` — grid generation from PatternParam ranges instead of ±20%/±40%

**Integrates:** S1's PatternParam into existing patterns and backtester

**Parallelizable:** false

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 3 | 3 |
| Context reads (base.py with PatternParam, bull_flag.py, flat_top.py, vectorbt_pattern.py) | 4 | 4 |
| Tests (~10: BF params ×2, FT params ×2, grid generation ×3, backward compat ×3) | 10 | 5 |
| Complex integration (3+) | No | 0 |
| External API | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **12 (Medium)** |

**Acceptance criteria:**
- Bull Flag `get_default_params()` returns ≥8 PatternParam with complete metadata
- Flat-Top `get_default_params()` returns ≥8 PatternParam with complete metadata
- Every PatternParam has non-empty description, valid param_type, non-None min/max for numeric
- PatternBacktester generates grids from PatternParam ranges
- PatternBacktester on Bull Flag completes without error
- All existing Bull Flag / Flat-Top tests pass
- 10 new tests pass

---

## S3: Dip-and-Rip Pattern

**Objective:** Implement Dip-and-Rip PatternModule. Sharp intraday dip + rapid recovery.

**Creates:**
- `strategies/patterns/dip_and_rip.py` (~180 lines)
- `config/strategies/dip_and_rip.yaml` (~15 lines)
- `config/universe_filters/dip_and_rip.yaml` (~10 lines)

**Modifies:**
- `config/exit_management.yaml` — add dip_and_rip override
- Strategy registration config — add dip_and_rip entry

**Integrates:** S1's PatternParam (implements `get_default_params()` with PatternParam list)

**Parallelizable:** false (shared exit_management.yaml)

| Factor (adjusted) | Count | Points |
|--------|-------|--------|
| New files: pattern.py | 1 | 2 |
| New files: config YAML (template) | 1 | 1 |
| New files: filter YAML (template) | 1 | 1 |
| Files modified | 2 | 2 |
| Context reads (base.py, bull_flag.py ref, pattern_strategy.py, exit_management.yaml) | 4 | 4 |
| Tests (~10) | 10 | 5 |
| Complex integration | No | 0 |
| External API | No | 0 |
| Large file surcharge (template pattern) | 0 | 0 |
| **Total (adjusted)** | | **15 → 12 (Medium)** |
| **Total (standard)** | | **15** |

**Acceptance criteria:**
- `DipAndRipPattern` implements all 5 PatternModule abstract members
- Detects sharp dip (configurable % threshold) followed by rapid recovery
- Differentiates from R2G: requires dip after 9:35 AM (intraday only)
- VWAP/support level interaction scored
- Volume confirmation on recovery
- Score returns 0–100 with 30/25/25/20 weighting
- Config YAML parses, filter YAML routes, exit override applies
- Registered in orchestrator
- Smoke backtest on 5 symbols × 6 months completes
- 10 new tests pass

**Key design notes:**
- Operating window: 9:45–11:30 AM
- Universe filter: min_price 5.0, max_price 200.0, min_avg_volume 500,000, min_relative_volume 1.5
- Exit: ATR trail 1.5×, partial 1.5R, 30 min time stop
- Verify `min_relative_volume` exists in UniverseFilterConfig Pydantic model

---

## S4: HOD Break Pattern

**Objective:** Implement HOD Break PatternModule. High-of-day breakout continuation.

**Creates:**
- `strategies/patterns/hod_break.py` (~180 lines)
- `config/strategies/hod_break.yaml` (~15 lines)
- `config/universe_filters/hod_break.yaml` (~10 lines)

**Modifies:**
- `config/exit_management.yaml` — add hod_break override
- Strategy registration config — add hod_break entry

**Integrates:** S1's PatternParam

**Parallelizable:** false

| Factor (adjusted) | Count | Points |
|--------|-------|--------|
| Same structure as S3 | | |
| **Total (adjusted)** | | **12 (Medium)** |

**Acceptance criteria:**
- `HODBreakPattern` implements all 5 PatternModule abstract members
- Dynamic HOD tracking updates on each candle
- Consolidation detection near HOD (configurable proximity %)
- Breakout requires minimum hold duration above HOD (default 2 bars)
- Volume confirmation on breakout
- Multi-test resistance scoring (more prior touches = higher score)
- Score returns 0–100 with 30/25/25/20 weighting
- Config, filter, exit, registration, smoke backtest all pass
- 10 new tests pass

**Key design notes:**
- Operating window: 10:00–15:30
- Universe filter: min_price 5.0, max_price 500.0, min_avg_volume 300,000
- Exit: ATR trail 2.0×, partial 2R, 60 min time stop
- No special universe filter fields needed

---

## S5: Gap-and-Go Pattern

**Objective:** Implement Gap-and-Go PatternModule. Gap-up continuation. First pattern to use reference data hook.

**Creates:**
- `strategies/patterns/gap_and_go.py` (~200 lines)
- `config/strategies/gap_and_go.yaml` (~15 lines)
- `config/universe_filters/gap_and_go.yaml` (~10 lines)

**Modifies:**
- `config/exit_management.yaml` — add gap_and_go override
- Strategy registration config — add gap_and_go entry

**Integrates:** S1's PatternParam + S1's `set_reference_data()` (first consumer of reference data hook)

**Parallelizable:** false

| Factor (adjusted) | Count | Points |
|--------|-------|--------|
| New files: pattern.py | 1 | 2 |
| New files: config YAML (template) | 1 | 1 |
| New files: filter YAML (template) | 1 | 1 |
| Files modified | 2 | 2 |
| Context reads (base.py, ref pattern, pattern_strategy.py, exit_management.yaml, red_to_green.py for prior close pattern) | 5 | 5 |
| Tests (~12) | 12 | 6 |
| Complex integration | No | 0 |
| External API | No | 0 |
| **Total (adjusted)** | | **17 → 13 (Medium, ceiling)** |

**Acceptance criteria:**
- `GapAndGoPattern` implements all 5 PatternModule abstract members
- Overrides `set_reference_data()` to extract prior close per symbol
- Gap calculated as `(open - prior_close) / prior_close * 100`
- Returns None when prior close unavailable for symbol
- Rejects gaps below min_gap_percent threshold (default 3%)
- Relative volume confirmation
- VWAP hold validation
- Two entry modes: first-pullback and direct-breakout (configurable)
- Score returns 0–100 with 30/30/20/20 weighting
- Config, filter, exit, registration, smoke backtest all pass
- Verify `min_gap_percent` exists in UniverseFilterConfig Pydantic model
- 12 new tests pass

**Key design notes:**
- Operating window: 9:35–10:30
- Universe filter: min_price 3.0, max_price 150.0, min_avg_volume 200,000, min_gap_percent 3.0
- Exit: percent trail 1.5%, partial 1R, 20 min time stop

---

## S6a: ABCD Core — Swing Detection + Pattern Logic

**Objective:** Build ABCD pattern algorithm: swing point detection, Fibonacci validation, leg ratio checking, completion zone. Self-contained — no config wiring.

**Creates:**
- `strategies/patterns/abcd.py` (~300 lines, genuinely complex — standard scoring)

**Modifies:** None

**Integrates:** S1's PatternParam

**Parallelizable:** false (S6b depends on output)

| Factor (STANDARD) | Count | Points |
|--------|-------|--------|
| New files: abcd.py | 1 | 2 |
| Large file (genuinely novel, ~300 lines) | 1 | 2 |
| Files modified | 0 | 0 |
| Context reads (base.py, CandleBar, ref pattern, PatternDetection) | 4 | 4 |
| Tests (~14: swing peaks ×2, valleys ×2, lookback config, noise filter, B retrace ×2, C retrace ×2, leg ratios ×2, completion zone, full detect, incomplete rejection, PatternParam) | 14 | 7 |
| Complex integration | No | 0 |
| External API | No | 0 |
| **Total (standard)** | | **15 (High — justified)** |

**Justification for proceeding at 15:** Zero file modifications, zero integration wiring. All points from algorithm complexity + tests. Session is completely self-contained — builds and tests the ABCD algorithm in isolation. Splitting the algorithm itself (e.g., swing detection in one session, Fibonacci in another) would lose critical mathematical context.

**Acceptance criteria:**
- `ABCDPattern` implements all 5 PatternModule abstract members
- Swing detection: identifies local peaks/valleys with configurable lookback (default 5 bars) and min_swing_size (default 0.5× ATR)
- Fibonacci validation: B retracement 38.2–61.8% of AB (configurable), C retracement 61.8–78.6% of BC (configurable)
- Leg ratio: CD leg ≈ AB leg in price (configurable tolerance, default 0.8–1.2×) and time (configurable, default 0.5–2.0×)
- Completion zone: calculates entry price from CD projection
- Incomplete patterns (AB only, ABC without CD completion) return None
- Score returns 0–100 with 35/25/20/20 weighting
- `get_default_params()` returns PatternParam list with ≥12 params (Fib levels, tolerances, lookbacks, ratios)
- 14 new tests pass

---

## S6b: ABCD Config + Wiring + Integration

**Objective:** Create ABCD config/filter/exit files, register strategy, run smoke backtest.

**Creates:**
- `config/strategies/abcd.yaml` (~15 lines)
- `config/universe_filters/abcd.yaml` (~10 lines)

**Modifies:**
- `config/exit_management.yaml` — add abcd override
- Strategy registration config — add abcd entry

**Integrates:** S6a's ABCD pattern into full strategy pipeline

**Parallelizable:** false

| Factor (adjusted) | Count | Points |
|--------|-------|--------|
| New files: config YAML | 1 | 1 |
| New files: filter YAML | 1 | 1 |
| Files modified | 2 | 2 |
| Context reads (base.py, abcd.py from S6a, pattern_strategy.py, exit_management.yaml) | 4 | 4 |
| Tests (~6: config parse, filter route, exit override, integration, backtest smoke, orchestrator) | 6 | 3 |
| **Total (adjusted)** | | **11 → 9 (Low)** |

**Acceptance criteria:**
- ABCD config YAML parses without error
- Universe filter routes symbols correctly (min_price 10.0, max_price 300.0, min_avg_volume 500,000)
- Exit overrides applied (ATR trail 2.5×, partial 1.5R, 90 min time stop)
- Registered in orchestrator, loads at startup
- Smoke backtest on 5 symbols × 6 months completes
- 6 new tests pass

---

## S7: Pre-Market High Break Pattern [STRETCH]

**Objective:** Implement PM High Break PatternModule. Pre-market high computation from extended-hours candles in deque.

**Creates:**
- `strategies/patterns/premarket_high_break.py` (~200 lines)
- `config/strategies/premarket_high_break.yaml` (~15 lines)
- `config/universe_filters/premarket_high_break.yaml` (~10 lines)

**Modifies:**
- `config/exit_management.yaml` — add premarket_high_break override
- Strategy registration config — add premarket_high_break entry

**Integrates:** S1's PatternParam + S1's `set_reference_data()`

**Parallelizable:** false

| Factor (adjusted) | Count | Points |
|--------|-------|--------|
| New files: pattern.py | 1 | 2 |
| New files: config YAML (template) | 1 | 1 |
| New files: filter YAML (template) | 1 | 1 |
| Files modified | 2 | 2 |
| Context reads (base.py, ref pattern, pattern_strategy.py, exit_management.yaml, gap_and_go.py for ref data pattern) | 5 | 5 |
| Tests (~12: PM high calc, breakout detection, volume confirm, no PM candles, low PM volume, PM high quality, gap context, multi-touch, PatternParam, ref data, time window, PM candle filter) | 12 | 6 |
| **Total (adjusted)** | | **17 → 13 (Medium, ceiling)** |

**Acceptance criteria:**
- `PreMarketHighBreakPattern` implements all 5 PatternModule abstract members
- PM high computed from candles in deque with timestamps 4:00 AM–9:30 AM ET
- Returns None when <3 pre-market candles available
- PM volume qualification: total PM volume must exceed `min_premarket_volume`
- Breakout detection: price exceeds PM high with volume confirmation
- Gap context scoring: gapping up into PM high scores higher
- Score returns 0–100 with 30/25/25/20 weighting
- Config, filter, exit, registration, smoke backtest all pass
- Verify `min_premarket_volume` exists in UniverseFilterConfig Pydantic model
- 12 new tests pass

**Key design notes:**
- Operating window: 9:35–10:30
- Universe filter: min_price 5.0, max_price 200.0, min_avg_volume 300,000, min_premarket_volume 50,000
- Exit: ATR trail 1.5×, partial 1.5R, 30 min time stop
- Pre-market candle identification: candles with timestamp hour < 9 or (hour == 9 and minute < 30) in ET

---

## S8: Integration Verification + Smoke Backtests

**Objective:** Verify all new patterns load and function correctly in the full system. Cross-pattern integration checks. Final smoke backtests.

**Creates:**
- `tests/test_sprint29_integration.py` (if needed — may use existing test infrastructure)

**Modifies:** None (fixes only if issues found — any fix must be documented in close-out)

**Integrates:** All S3–S7 patterns verified end-to-end in full system context

**Parallelizable:** false

| Factor | Count | Points |
|--------|-------|--------|
| New files | 0–1 | 0–2 |
| Files modified | 0 | 0 |
| Context reads (orchestrator config, 5 pattern configs, exit_management.yaml, registration) | ~8 | 8 |
| Tests (~10: all strategies load, per-config parse ×5, smoke backtests ×5) | 10 | 5 |
| Complex integration (5 patterns + orchestrator) | Yes | 3 |
| **Total** | | **16 → ~10 effective (read-only verification)** |

**Effective score adjustment:** 16 by formula, but session performs zero writes in the success path. Context reads are checking existing files, not loading them for modification. Compaction risk is minimal because the session produces nothing new — it only validates.

**Acceptance criteria:**
- Orchestrator startup loads all 12 strategies without error
- Each new pattern's config parses correctly
- Each new pattern's universe filter routes at least 1 symbol in test universe
- Each new pattern's exit override applies correctly (verified via config inspection)
- Smoke backtest per pattern (5 symbols × 6 months) completes without error and produces >0 signals
- No existing strategy behavior changed (run existing test suite — 0 regressions)
- All pre-existing pytest + Vitest pass (0 failures)

---

## Summary

| Session | Scope | Score | Risk | Tests | Parallelizable |
|---------|-------|-------|------|-------|----------------|
| S1 | PatternParam + reference data hook | 8 | Low | ~6 | false |
| S2 | Retrofit BF/FT + backtester grid | 12 | Medium | ~10 | false |
| S3 | Dip-and-Rip | 12 adj | Medium | ~10 | false |
| S4 | HOD Break | 12 adj | Medium | ~10 | false |
| S5 | Gap-and-Go | 13 adj | Medium | ~12 | false |
| S6a | ABCD core algorithm | 15 std | High (justified) | ~14 | false |
| S6b | ABCD config + wiring | 9 adj | Low | ~6 | false |
| S7 | Pre-Market High Break [STRETCH] | 13 adj | Medium | ~12 | false |
| S8 | Integration verification | ~10 eff | Medium | ~10 | false |
| **Total** | | | | **~90** | |

**Estimated test delta:** +90 tests (~84 new + ~6 integration), bringing total to ~4,045 pytest + 680 Vitest.

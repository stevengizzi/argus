# Sprint 29: What This Sprint Does NOT Do

## Out of Scope

1. **Walk-forward validation:** Full walk-forward validation (WFE > 0.3) for new patterns is NOT run during this sprint. Only smoke backtests (5 symbols × 6 months) are in scope. Full WF validation is a post-sprint pass using `scripts/validate_all_strategies.py` with the 96-month Parquet cache.

2. **Strategy parameter optimization:** Sprint 29 defines parameters with PatternParam metadata (ranges, steps) but does NOT run parameter optimization sweeps. That is Sprint 32 (Parameterized Strategy Templates) and Sprint 34 (Systematic Search).

3. **Short selling variants:** No bearish/short versions of any pattern. Sprint 30 (Short Selling + Parabolic Short) handles this.

4. **Frontend changes:** No new Command Center pages, no Observatory changes, no Performance page additions, no UI components for new patterns. Patterns integrate automatically through existing Quality Engine / Trade Logger / Observatory pipelines.

5. **Quality Engine weight recalibration:** Adding 5 new patterns does not trigger recalibration of the 5-dimension scoring weights. The existing weights (pattern 30% / catalyst 25% / volume 20% / historical 15% / regime 10%) apply to new patterns automatically.

6. **Learning Loop configuration changes:** No changes to `learning_loop.yaml`. New patterns are automatically included in Learning Loop analysis via the existing OutcomeCollector / WeightAnalyzer pipeline.

7. **Swing detection extraction as shared utility:** The ABCD pattern's swing detection algorithm stays internal to `abcd.py`. Extraction to a shared `core/swing_detection.py` module is deferred to Sprint 31A when additional harmonic patterns (Gartley, Butterfly, Three Drives) would reuse it.

8. **PatternModule ABC refactoring beyond PatternParam:** No changes to `detect()`, `score()`, `name`, or `lookback_bars` abstract members. Only `get_default_params()` return type and the new optional `set_reference_data()` are touched.

9. **Catalyst pipeline integration for new patterns:** No new catalyst sources or classifiers. New patterns benefit from existing catalyst data through the Quality Engine's catalyst_quality dimension automatically.

10. **Pre-Market High Break as a hard requirement:** PM High Break is stretch scope. If velocity requires, it is dropped without the sprint being considered incomplete. The sprint delivers 11 strategies minimum (current 7 + Dip-and-Rip, HOD Break, Gap-and-Go, ABCD).

11. **Strategy-specific Pydantic config models:** New patterns use the shared `PatternStrategyConfig` model. No per-pattern config model subclasses. Pattern-specific parameters live in PatternParam metadata, not YAML config.

12. **Pre-market data from external sources:** PM High Break computes PM high from candles in PatternBasedStrategy's deque (EQUS.MINI extended hours). No FMP or other external source integration for pre-market data.

## Edge Cases to Reject

1. **ABCD pattern with only AB leg formed:** Do not signal. Return None from `detect()`. Only complete ABCD patterns (all 4 points identified, CD leg reaching completion zone) produce signals.

2. **ABCD pattern with ambiguous swing points (multiple valid interpretations):** Take the most recent valid interpretation. Do not attempt to track multiple concurrent ABCD patterns on the same symbol.

3. **Gap-and-Go with no prior close data:** Return None from `detect()`. Log at DEBUG level. Do not attempt to estimate gap from other sources.

4. **PM High Break with zero pre-market candles:** Return None from `detect()`. This is expected for symbols with no extended-hours trading.

5. **Dip-and-Rip dip occurring before 9:35 AM (pre-market):** Do not detect. The dip must occur during market hours to differentiate from R2G gap-based mechanics.

6. **HOD Break false breakout (price exceeds HOD then immediately reverses):** Detection requires minimum hold duration above HOD (configurable, default 2 bars / 2 minutes) before signaling. The hold duration is a PatternParam.

7. **Multiple patterns firing on same symbol simultaneously:** Allowed. Cross-strategy exclusion is limited to ORB family (DEC-261). New patterns have no mutual exclusion constraints.

8. **Pattern detection on symbols with <lookback_bars candle history:** Return None from `detect()`. PatternBasedStrategy already handles this via deque length check. Each pattern's `lookback_bars` property defines the minimum.

9. **PatternParam with `param_type=bool`:** `min_value`/`max_value`/`step` should be None. Grid generation skips bool params (no sweep — just True/False).

10. **PatternParam with `param_type=int` and float step:** `step` is rounded to nearest int during grid generation. The PatternParam itself stores float for uniformity.

## Scope Boundaries

- **Do NOT modify:** `core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `analytics/evaluation.py`, `intelligence/learning/` (entire directory), `intelligence/counterfactual.py`, `core/fill_model.py`, `ui/` (entire frontend), `api/` (no new endpoints), `ai/` (no AI layer changes)
- **Do NOT modify after S1:** `strategies/patterns/base.py`, `strategies/pattern_strategy.py` — locked after S1 completes
- **Do NOT modify after S2:** `strategies/patterns/bull_flag.py`, `strategies/patterns/flat_top_breakout.py`, `backtest/vectorbt_pattern.py` — locked after S2 completes
- **Do NOT optimize:** Pattern detection performance beyond <10ms/candle. Sub-millisecond optimization is Sprint 32+ territory.
- **Do NOT refactor:** PatternBasedStrategy wrapper. It works. New patterns must conform to the existing interface.
- **Do NOT add:** New REST API endpoints, new WebSocket channels, new frontend components, new database tables, new event types on the event bus.

## Interaction Boundaries

- This sprint does NOT change the behavior of: Event Bus, Order Manager, Risk Manager, Quality Engine scoring logic, Counterfactual Engine tracking logic, Learning Loop analysis logic, Observatory service, AI Copilot, Catalyst Pipeline.
- This sprint does NOT affect: Existing 7 strategies' detection logic, scoring weights, operating windows, or exit profiles. Existing universe filter routing for current strategies.
- This sprint does NOT change: The PatternBasedStrategy wrapper behavior (beyond calling `set_reference_data()` during init, which is a no-op for patterns that don't override it).

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Walk-forward validation for Sprint 29 patterns | Post-sprint (immediate) | — |
| Swing detection extraction as shared utility | Sprint 31A | DEF-109 (new) |
| PatternParam enum type support (for categorical params) | Sprint 32 | DEF-110 (new) |
| Per-pattern Pydantic config subclasses | Sprint 32 (if needed) | — |
| Short selling variants of new patterns | Sprint 30 | — |
| Pre-Market High Break (if dropped as stretch) | Sprint 31A | — |
| Parameter optimization sweeps | Sprint 32 + Sprint 34 | — |

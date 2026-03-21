# Sprint 26: Adversarial Review — Revision Rationale

> Inline adversarial review conducted during planning. 7 findings, all resolved.

## Findings and Resolutions

### F1 — `candles: list[dict]` type safety (CRITICAL) → ACCEPTED
**Problem:** Raw dict loses type safety for the most-called interface in the pattern system.
**Resolution:** Define `CandleBar` frozen dataclass in `patterns/base.py`. PatternModule.detect() signature becomes `detect(candles: list[CandleBar], indicators: dict) -> PatternDetection | None`. PatternBasedStrategy converts CandleEvent → CandleBar. BacktestEngine (Sprint 27) constructs CandleBar directly from historical arrays.

### F2 — Window size contract (SIGNIFICANT) → ACCEPTED
**Problem:** No specification of how much candle history detect() receives.
**Resolution:** Add `lookback_bars` abstract property to PatternModule. PatternBasedStrategy maintains a per-symbol deque(maxlen=lookback_bars) of CandleBars and passes only the window. BacktestEngine uses the same property for its sliding window.

### F3 — Missing target_prices in PatternDetection (SIGNIFICANT) → ACCEPTED
**Problem:** Pattern-specific natural targets (e.g., measured move for Bull Flag) lost.
**Resolution:** Add `target_prices: tuple[float, ...] = ()` to PatternDetection. PatternBasedStrategy uses these if present, falls back to R-multiple from config if empty.

### F4 — S4 compaction risk at 14 (SIGNIFICANT) → ACCEPTED (partial)
**Problem:** Protocol requires split at 14+.
**Resolution:** Move 3 edge-case tests (reconstruct_state delegation, scanner criteria passthrough, market conditions filter passthrough) from S4 to S5. These are naturally tested with the first real pattern anyway. S4 revised score: ~11. S5 revised score: ~13 (absorbs 3 tests, +1.5 points).

### F5 — R2G re-test path underspecified (MODERATE) → ACCEPTED
**Problem:** TESTING_LEVEL → GAP_DOWN_CONFIRMED transition logic unclear.
**Resolution:** Add `max_level_attempts: int = 2` to RedToGreenConfig. After testing max_level_attempts levels, transition to EXHAUSTED. Each level test failure returns to GAP_DOWN_CONFIRMED to try next level.

### F6 — `get_default_params()` return type (MODERATE) → DEFERRED
**Problem:** dict return type loses parameter range information.
**Resolution:** Keep `dict` for Sprint 26. Document as DEF-088: Refine to `list[PatternParam]` in Sprint 27 when BacktestEngine parameter sweep needs structured param definitions.

### F7 — No 7-strategy allocation test (MODERATE) → ACCEPTED
**Problem:** Orchestrator allocation not tested with 7 strategies.
**Resolution:** Add integration test in S9: create Orchestrator with 7 strategies, run pre_market(), verify each receives allocated_capital > 0 and sum equals total.

## Summary of Spec Changes

1. **PatternModule ABC** (sprint-spec.md deliverable 1): detect() takes `list[CandleBar]` not `list[dict]`. Add `lookback_bars` abstract property. Add `CandleBar` dataclass.
2. **PatternDetection** (sprint-spec.md deliverable 1): Add `target_prices: tuple[float, ...] = ()`.
3. **RedToGreenConfig** (sprint-spec.md deliverable 4): Add `max_level_attempts: int = 2`.
4. **Session 4** (session-breakdown.md): Score reduced from 14 to ~11 by moving 3 tests to S5.
5. **Session 5** (session-breakdown.md): Absorbs 3 PatternBasedStrategy edge case tests.
6. **Session 9** (session-breakdown.md): Add 7-strategy allocation integration test.
7. **DEF-088** reserved for PatternParam structured type refinement (Sprint 27).

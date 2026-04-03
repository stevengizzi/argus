# Sprint 31A: Escalation Criteria

## Tier 3 Escalation Triggers

These conditions require halting implementation and escalating to a Claude.ai architectural discussion:

1. **DEF-143 fix breaks existing backtest results.** If replacing no-arg constructors with `build_pattern_from_config()` using default config produces different BacktestEngine output (different trade count, different Sharpe) for any existing pattern, the factory's `extract_detection_params()` may not be extracting the same defaults as the no-arg constructor. STOP — this indicates a Pydantic config default vs PatternParam default divergence that needs analysis.

2. **min_detection_bars change alters existing pattern behavior.** If any existing PatternBasedStrategy pattern (not PMH) produces different signal counts or timing after the `min_detection_bars` change, the default property (`return self.lookback_bars`) is not working correctly. STOP — the change must be backward-compatible for all 9 existing PatternModule patterns.

3. **New pattern detection logic produces signals outside operating window.** PatternBasedStrategy's operating window check is at line ~269. If signals appear outside the configured window, there's a fundamental control flow issue. STOP.

4. **Any session causes test count to decrease.** Tests can be added but never removed. A decrease indicates accidental test deletion or test file corruption. STOP and investigate.

5. **Parameter sweep reveals BacktestEngine still ignoring config_overrides after DEF-143 fix.** If S6 shows identical results across different parameter configurations for any pattern, the fix is incomplete. STOP — do not populate experiments.yaml with unreliable data.

## Session-Level Escalation (handle within session)

These are handled by the implementer or reviewer without Tier 3 escalation:

- **Cross-validation test failure** (PatternParam ranges vs Pydantic Field bounds): Fix the divergent value. Trust the constructor default over the spec if they conflict.
- **EMA/VWAP indicator not available** for new pattern: Check `data_service.get_indicator()` returns for the needed indicator. If unavailable, compute from candle data within the pattern (self-contained, like PMH's `_compute_atr()`).
- **S2 reference data wiring exceeds session budget:** Defer main.py wiring to a micro-session S2b. Log as carry-forward in work journal.
- **Individual pattern sweep produces 0 qualifying variants:** Document results. Do not lower qualification thresholds. Pattern remains in base configuration.
- **ABCD sweep takes >30 minutes per config:** Expected due to DEF-122. Document timing. Do not optimize within this sprint.

## DEF/DEC Number Reservations

- **DEF range:** DEF-145 through DEF-155 reserved for Sprint 31A
- **DEC range:** No new DECs expected (all decisions follow established patterns). If needed: DEC-382 through DEC-390 reserved.

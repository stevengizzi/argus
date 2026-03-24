# Sprint 27.6, Session 5: IntradayCharacterDetector

## Pre-Flight Checks
1. Read: `argus/core/config.py` (IntradayConfig — note all threshold fields), `argus/core/regime.py` (RegimeVector intraday fields)
2. Scoped test: `python -m pytest tests/core/test_regime.py tests/core/test_breadth.py -x -q`
3. Verify branch

## Objective
Build IntradayCharacterDetector — classifies intraday market character from SPY 1-minute candles at configurable timestamps. Concrete classification rules with configurable thresholds per adversarial review C3.

## Requirements

1. Create `argus/core/intraday_character.py` with class `IntradayCharacterDetector`:
   - Constructor: `(config: IntradayConfig)`
   - `on_candle(event: CandleEvent) -> None`: Accept SPY candles only (filter by symbol). Accumulate bars. At classification times (default 9:35, 10:00, 10:30 ET), run classification.
   - `get_intraday_snapshot() -> dict`: Returns `{"opening_drive_strength": float|None, "first_30min_range_ratio": float|None, "vwap_slope": float|None, "direction_change_count": int|None, "intraday_character": str|None}`
   - `set_prior_day_range(range_value: float) -> None`: Set prior day's full range for ratio computation.
   - `set_atr_20(atr_value: float) -> None`: Set 20-day ATR for drive strength normalization.
   - `reset() -> None`: Clear state for new trading day.

2. Intermediate metrics:
   - `opening_drive_strength`: `abs(close_at_N_min - open_930) / atr_20`, clamped [0.0, 1.0]
   - `first_30min_range_ratio`: `(high_30min - low_30min) / prior_day_range`
   - `vwap_slope`: Linear regression slope of VWAP over accumulated bars, normalized by price
   - `direction_change_count`: Number of 5-bar close direction flips

3. Classification rules (priority order — first match wins):
   - **Breakout**: `first_30min_range_ratio >= range_ratio_breakout` (1.2) AND `opening_drive_strength >= drive_strength_breakout` (0.5)
   - **Reversal**: `opening_drive_strength >= drive_strength_reversal` (0.3) AND `direction_change_count >= 1` AND VWAP slope sign flipped vs first 5 bars
   - **Trending**: `opening_drive_strength >= drive_strength_trending` (0.4) AND `direction_change_count <= max_direction_changes_trending` (2) AND `abs(vwap_slope) >= vwap_slope_trending` (0.0002)
   - **Choppy**: default fallback

4. All thresholds read from IntradayConfig (not hardcoded). If < `min_spy_bars` (3) candles at classification time → return None, retry at next time.

## Constraints
- Do NOT modify any existing files
- SPY symbol filtering: compare against configurable spy_symbol (default "SPY")
- Standalone module, wired in S6

## Test Targets
- New tests (~12) in `tests/core/test_intraday_character.py`:
  - Construction with config
  - Classify trending: strong open, sustained drift, few direction changes
  - Classify breakout: wide range + strong drive
  - Classify reversal: strong open + VWAP cross
  - Classify choppy: oscillating, many direction changes
  - Priority: breakout > reversal > trending > choppy (overlap test)
  - Pre-market (before 9:35) → all None
  - Insufficient bars at classification time → None
  - opening_drive_strength computation and clamping
  - first_30min_range_ratio computation
  - vwap_slope computation
  - direction_change_count computation
  - Reset clears state
- Minimum: 12
- Test command: `python -m pytest tests/core/test_intraday_character.py -x -q -v`

## Definition of Done
- [ ] IntradayCharacterDetector with all metrics and classification rules
- [ ] All thresholds configurable via IntradayConfig
- [ ] Priority ordering correct
- [ ] 12+ tests passing
- [ ] Close-out: `docs/sprints/sprint-27.6/session-5-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-5-closeout.md`
3. Test command: `python -m pytest tests/core/test_intraday_character.py -x -q -v`
4. Files NOT to modify: all existing files

## Session-Specific Review Focus
1. Verify all thresholds read from config (grep for hardcoded numbers)
2. Verify priority order: Breakout > Reversal > Trending > Choppy
3. Verify None returned when insufficient data (not a default classification)
4. Verify SPY-only filtering
5. Verify VWAP slope computation is mathematically sound

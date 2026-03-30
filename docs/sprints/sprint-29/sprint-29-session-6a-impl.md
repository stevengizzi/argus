# Sprint 29, Session 6a: ABCD Core — Swing Detection + Pattern Logic

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam, CandleBar, PatternDetection)
   - `argus/strategies/patterns/bull_flag.py` (reference for detect/score/get_default_params structure)
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
   Expected: all passing
3. Verify you are on branch `sprint-29`

## Objective
Build the ABCD harmonic pattern algorithm: swing point detection, Fibonacci retracement validation, leg ratio checking, and completion zone calculation. This is the algorithm-heavy session — no config wiring or strategy registration (that's S6b). Self-contained implementation and testing.

**Compaction note:** This session is pre-approved at score 15 (High) because it creates genuinely novel algorithmic infrastructure (swing detection). Zero file modifications, zero integration wiring — all complexity is in the algorithm itself.

## Requirements

### 1. Pattern Implementation: `argus/strategies/patterns/abcd.py`

Create `ABCDPattern` implementing PatternModule ABC:

**`name`** property: `"abcd"`

**`lookback_bars`** property: 60 (ABCD patterns need substantial price history — legs take time to form)

**Swing Point Detection (internal helper methods):**

Implement `_find_swing_highs()` and `_find_swing_lows()`:
- A swing high is a candle whose `high` is greater than the highs of the `swing_lookback` (default 5) candles on each side
- A swing low is a candle whose `low` is less than the lows of the `swing_lookback` candles on each side
- Minimum swing size: the swing must represent at least `min_swing_atr_mult` (default 0.5) × ATR price movement from neighboring swings
- Returns list of `(index, price)` tuples, ordered chronologically
- Edge handling: candles within `swing_lookback` of the start/end of the list cannot be swing points

**`detect(candles: list[CandleBar]) -> PatternDetection | None`:**

Scan for complete ABCD patterns in the candle history:
1. **Identify A point:** Start from a swing low (for bullish ABCD — buying at D completion)
2. **Identify B point:** Next swing high after A. B must be higher than A.
3. **Validate BC retracement:** C is next swing low after B. C must retrace between `fib_b_min` (default 0.382) and `fib_b_max` (default 0.618) of the AB leg. C must be higher than A (higher low).
4. **Validate CD leg formation:** D is the projected completion point. CD leg should extend to where D approximately equals A + AB distance (measured move).
5. **Check leg ratios:**
   - Price ratio: CD leg size should be between `leg_price_ratio_min` (default 0.8) and `leg_price_ratio_max` (default 1.2) × AB leg size
   - Time ratio: CD duration should be between `leg_time_ratio_min` (default 0.5) and `leg_time_ratio_max` (default 2.0) × AB duration
6. **Completion zone:** D point should be within `completion_tolerance_percent` (default 1.0%) of the projected completion price
7. **Signal only on completion:** Return PatternDetection only when the current price enters the D completion zone. Do NOT signal on incomplete patterns.

For bullish ABCD (default): A=low, B=high, C=higher_low, D=higher_high (projected).
Entry: at D completion zone.
Stop: below C point minus `stop_buffer_atr_mult` (default 0.5) × ATR.
Target: D + (B - A) × `target_extension` (default 1.272) — Fibonacci extension.

**Important edge cases:**
- If multiple valid ABCD interpretations exist, use the most recent one (closest to current bar)
- If AB leg is detected but BC hasn't completed, return None (do not track partial patterns)
- If BC retracement is outside Fibonacci bounds, reject the entire pattern
- If the candle list has fewer than `lookback_bars` candles, return None

**`score(candles: list[CandleBar], detection: PatternDetection) -> int`:**
- 0–100 with weights:
  - Fibonacci precision (35): how close B and C retracements are to ideal levels (0.618 for B, 0.786 for C). Perfect = 35 points, at boundary = 15 points.
  - Leg symmetry (25): how close CD/AB ratio is to 1.0 in both price and time. Perfect symmetry = 25 points.
  - Volume pattern (20): declining volume in BC leg, expanding in CD leg = higher. Volume ratio CD_avg/BC_avg > 1.2 = full points.
  - Trend context (20): ABCD in direction of higher-timeframe trend (e.g., bullish ABCD when 20-bar MA is rising) = full points.

**`get_default_params() -> list[PatternParam]`:**
≥14 PatternParam entries:
- Detection: `swing_lookback` (int, 3–10, step 1), `min_swing_atr_mult` (float, 0.3–1.0, step 0.1)
- Fibonacci: `fib_b_min` (float, 0.300–0.500, step 0.05), `fib_b_max` (float, 0.500–0.750, step 0.05), `fib_c_min` (float, 0.500–0.700, step 0.05), `fib_c_max` (float, 0.700–0.900, step 0.05)
- Leg ratios: `leg_price_ratio_min`, `leg_price_ratio_max`, `leg_time_ratio_min`, `leg_time_ratio_max`
- Completion: `completion_tolerance_percent`
- Trade: `stop_buffer_atr_mult`, `target_extension`
- All with description, category, appropriate type/range/step

## Constraints
- Do NOT modify: any file other than `argus/strategies/patterns/abcd.py` and test files
- Do NOT create config YAMLs, filter YAMLs, or register the strategy (that's S6b)
- The swing detection algorithm stays INTERNAL to abcd.py — do not create a separate utility module
- Focus on correctness over performance — <10ms per candle is the target, not sub-millisecond

## Test Targets
1. Swing high detection: finds peaks in known price sequence
2. Swing low detection: finds valleys in known price sequence
3. Swing detection respects min_swing_atr_mult (filters noise)
4. Swing detection respects lookback window (edge candles excluded)
5. Fibonacci B retracement: accepts value in range → valid
6. Fibonacci B retracement: rejects value outside range → None
7. Fibonacci C retracement: accepts value in range → valid
8. Fibonacci C retracement: rejects value outside range → None
9. Leg price ratio: accepts symmetric legs → valid
10. Leg time ratio: accepts proportional legs → valid
11. Complete ABCD detection on synthetic price data → PatternDetection
12. Incomplete pattern (ABC only, no D completion) → None
13. Insufficient candle history → None
14. Score Fibonacci precision: perfect 0.618 scores higher than boundary 0.382
15. PatternParam list completeness (≥14 params, all with metadata)
- Minimum new test count: 14 (some tests may combine related assertions)
- Test command: `python -m pytest tests/strategies/patterns/test_abcd.py -x -q --timeout=30`

**Synthetic test data guidance:** Build test candle sequences that create known ABCD patterns. For example:
- A at $100, B at $110, C at $104.18 (0.618 retracement of AB), D at $114.18 (AB=CD measured move)
- This gives deterministic, verifiable test data for all Fibonacci and leg ratio checks

## Definition of Done
- [ ] ABCDPattern implements all 5 PatternModule abstract members
- [ ] Swing detection finds local peaks/valleys with configurable lookback and min size
- [ ] Fibonacci validation at B (38.2–61.8%) and C (61.8–78.6%) with configurable bounds
- [ ] Leg ratio checking (price and time) with configurable tolerance
- [ ] Completion zone calculation produces valid entry level
- [ ] Incomplete patterns return None
- [ ] Score weights 35/25/20/20
- [ ] ≥14 PatternParam entries with complete metadata
- [ ] 14+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No files modified except abcd.py + tests | `git diff --stat` shows only new files |
| base.py unchanged | `git diff argus/strategies/patterns/base.py` — empty |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-6a-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-6a-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/test_abcd.py -x -q --timeout=30`
5. Do not modify: everything except `abcd.py` and test files

## Session-Specific Review Focus (for @reviewer)
1. Verify swing detection edge handling (first/last `swing_lookback` candles correctly excluded)
2. Verify Fibonacci retracement calculation is mathematically correct: `(B - C) / (B - A)` for bullish
3. Verify leg ratio uses both price AND time dimensions
4. Verify incomplete patterns (AB only, ABC without D) return None — not partial signals
5. Verify completion zone tolerance is percentage-based, not absolute
6. Verify no off-by-one errors in candle indexing (common in sliding-window algorithms)
7. Verify score weights sum to 100
8. Verify synthetic test data creates mathematically valid ABCD patterns

## Sprint-Level Regression Checklist / Escalation Criteria
See `docs/sprints/sprint-29/review-context.md`

# Sprint 29, Session 4: HOD Break Pattern

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam)
   - `argus/strategies/patterns/bull_flag.py` (reference implementation)
   - `argus/strategies/pattern_strategy.py` (wrapper)
   - `config/exit_management.yaml` (current structure with S3 additions)
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
   Expected: all passing
3. Verify you are on branch `sprint-29`

## Objective
Implement the HOD Break pattern as a PatternModule. This pattern detects high-of-day breakout continuations — stocks consolidating near their session high then breaking out with volume. Primary midday coverage provider (10:00–15:30 window).

## Requirements

### 1. Pattern Implementation: `argus/strategies/patterns/hod_break.py`

Create `HODBreakPattern` implementing PatternModule ABC:

**`name`** property: `"hod_break"`

**`lookback_bars`** property: 60 (needs substantial price history to establish meaningful HOD)

**`detect(candles: list[CandleBar]) -> PatternDetection | None`:**
- Track high-of-day (HOD) dynamically across all candles:
  - HOD = maximum high across all candles received so far
  - Track HOD touch count: number of candles where high comes within `hod_proximity_percent` (default 0.3%) of HOD
- Consolidation detection near HOD:
  - Last `consolidation_min_bars` (default 5) bars must have a range ≤ `consolidation_max_range_atr` (default 0.8) × ATR
  - At least `consolidation_min_bars` / 2 bars must have highs within `hod_proximity_percent` of HOD
- Breakout confirmation:
  - Current candle's close exceeds HOD by at least `breakout_margin_percent` (default 0.1%)
  - Candle must hold above HOD for at least `min_hold_bars` (default 2) consecutive bars (this prevents false breakout signals — detection only fires after the hold duration)
- Volume confirmation:
  - Breakout bar volume ≥ `min_breakout_volume_ratio` (default 1.5) × average volume of consolidation bars
- Entry: at breakout confirmation price
- Stop: below consolidation low minus `stop_buffer_atr_mult` (default 0.5) × ATR
- Target: measured move (consolidation range × `target_ratio`, default 2.0) from breakout point

**`score(candles: list[CandleBar], detection: PatternDetection) -> int`:**
- 0–100 with weights:
  - Consolidation quality (30): tighter range + longer duration = higher
  - Breakout volume (25): higher volume ratio = higher
  - Prior HOD tests (25): more touches of HOD before breakout = stronger resistance = stronger break
  - VWAP distance (20): not too extended from VWAP = healthier, within 2% = full points, >5% = minimum

**`get_default_params() -> list[PatternParam]`:**
~12 PatternParam entries covering detection, scoring, filtering categories.

### 2. Strategy Config: `config/strategies/hod_break.yaml`
```yaml
pattern_class: "HODBreakPattern"
operating_window:
  start: "10:00"
  end: "15:30"
allowed_regimes:
  - bullish_trending
  - bearish_trending
  - neutral
  - high_volatility
mode: "live"
```

### 3. Universe Filter: `config/universe_filters/hod_break.yaml`
```yaml
min_price: 5.0
max_price: 500.0
min_avg_volume: 300000
```
No special filter fields needed — standard UniverseFilterConfig fields only.

### 4. Exit Management Override
Add to `config/exit_management.yaml` under `strategy_exit_overrides`:
```yaml
hod_break:
  trailing_stop:
    enabled: true
    mode: "atr"
    atr_multiplier: 2.0
    activation_r: 0.75
  partial_profit:
    enabled: true
    targets:
      - r_multiple: 2.0
        percent: 50
  time_escalation:
    enabled: true
    phases:
      - after_minutes: 40
        tighten_stop_percent: 25
      - after_minutes: 60
        action: "flatten"
```

### 5. Strategy Registration
Register HOD Break in orchestrator/system config following existing pattern.

## Constraints
- Do NOT modify: `base.py`, `pattern_strategy.py`, any existing pattern files, `core/`, `execution/`, `ui/`, `api/`, `intelligence/`
- The `min_hold_bars` parameter is critical — detection MUST NOT fire on the initial breakout bar alone. It must wait for the hold duration to pass.

## Test Targets
New tests to write:
1. Detect HOD breakout after consolidation → PatternDetection
2. Reject: no consolidation near HOD (range too wide) → None
3. Reject: breakout without hold duration (false breakout) → None
4. Reject: breakout without volume confirmation → None
5. HOD tracking updates correctly across candles
6. HOD touch count accumulation
7. Score weights: 30/25/25/20 verified
8. Score VWAP distance scaling (within 2% vs >5%)
9. PatternParam completeness
10. Config + exit override parse correctly
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`

## Definition of Done
- [ ] HODBreakPattern implements all 5 PatternModule abstract members
- [ ] Dynamic HOD tracking across candles
- [ ] Consolidation detection with range and proximity checks
- [ ] Breakout requires min_hold_bars hold duration (anti-false-breakout)
- [ ] Volume confirmation on breakout
- [ ] Multi-test resistance scoring (HOD touch count)
- [ ] Config, filter, exit, registration all correct
- [ ] 10+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing patterns unchanged | `git diff argus/strategies/patterns/` — only new file + exit_management |
| Exit management existing entries preserved | `git diff config/exit_management.yaml` — only additions |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-4-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
5. Do not modify: `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`

## Session-Specific Review Focus (for @reviewer)
1. Verify min_hold_bars is enforced in detection (not just entry)
2. Verify HOD tracking is truly dynamic (updates on each candle, not computed once)
3. Verify consolidation range uses ATR, not fixed percentage
4. Verify VWAP distance scoring degrades gracefully when VWAP unavailable
5. Verify no modifications to locked files

## Sprint-Level Regression Checklist / Escalation Criteria
See `docs/sprints/sprint-29/review-context.md`

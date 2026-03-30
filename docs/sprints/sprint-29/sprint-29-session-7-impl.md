# Sprint 29, Session 7: Pre-Market High Break Pattern [STRETCH]

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam, set_reference_data)
   - `argus/strategies/patterns/gap_and_go.py` (S5 output — reference for set_reference_data usage)
   - `argus/strategies/pattern_strategy.py` (wrapper — note candle deque accumulates pre-window bars per Sprint 27.65)
   - `config/exit_management.yaml` (current structure)
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
   Expected: all passing
3. Verify you are on branch `sprint-29`

## Objective
Implement the Pre-Market High Break pattern as a PatternModule. This pattern detects breakouts above the pre-market session high. The PM high is computed from extended-hours candles already present in PatternBasedStrategy's candle deque (EQUS.MINI delivers 4:00 AM–9:30 AM ET candles, and Sprint 27.65's fix accumulates bars before the operating window check).

**STRETCH scope:** If this session is being skipped due to velocity concerns, document the skip in the close-out and proceed to S8. The sprint is complete at 11 strategies without this pattern.

## Requirements

### 1. Pattern Implementation: `argus/strategies/patterns/premarket_high_break.py`

Create `PreMarketHighBreakPattern` implementing PatternModule ABC:

**`name`** property: `"premarket_high_break"`

**`lookback_bars`** property: 30 (includes pre-market candles in deque + first few market-hours bars)

**Override `set_reference_data(data: dict[str, Any])`:**
- Extract `prior_closes: dict[str, float]` from data dict (for gap context scoring)
- Store as `self._prior_closes`

**`detect(candles: list[CandleBar]) -> PatternDetection | None`:**

**Pre-market high computation:**
- Scan candles in the deque for pre-market bars: candles with timestamp where hour < 9 or (hour == 9 and minute < 30) in ET (America/New_York)
- Important: CandleBar timestamps — verify the timezone convention used. If timestamps are UTC, convert to ET for the pre-market window check. If already ET, use directly.
- PM high = maximum `high` across all pre-market candles
- PM volume = sum of `volume` across all pre-market candles
- If fewer than `min_pm_candles` (default 3) pre-market candles: return None
- If PM volume < threshold (from universe filter `min_premarket_volume`): return None — but note this is a universe-level filter, so the pattern should also have its own `min_pm_volume` param as a detection-level check

**Breakout detection:**
- After market open (9:30 AM ET), monitor for candle close above PM high by at least `breakout_margin_percent` (default 0.15%)
- Volume confirmation: breakout bar volume ≥ `min_breakout_volume_ratio` (default 1.5) × average PM bar volume
- Hold confirmation: price must stay above PM high for `min_hold_bars` (default 2) consecutive bars (same anti-false-breakout pattern as HOD Break)

**PM high quality assessment (for scoring):**
- Count number of PM candles that touched or exceeded `pm_high_proximity_percent` (default 0.2%) of PM high — more touches = stronger resistance = better breakout
- Track how long PM high was established (first touch to market open) — longer = more significant

**Gap context:**
- If prior close available (from `set_reference_data`): calculate gap percent
- Gapping up into PM high (gap > 0 and open near PM high) = better setup than gapping down

**Entry:** At breakout confirmation (after hold bars)
**Stop:** Below PM high minus `stop_buffer_atr_mult` (default 0.5) × ATR
**Target:** PM high range (PM high - PM low) × `target_ratio` (default 1.5) above PM high

**`score(candles: list[CandleBar], detection: PatternDetection) -> int`:**
- 0–100 with weights:
  - PM high quality (30): more touches + longer establishment = higher
  - Breakout volume (25): higher volume ratio = higher
  - Gap context (25): gapping up into PM high = highest, flat open = moderate, gapping down = lowest
  - VWAP distance (20): breakout near VWAP = healthy, too extended = risky

**`get_default_params() -> list[PatternParam]`:**
~13 PatternParam entries:
- Detection: `min_pm_candles`, `min_pm_volume`, `breakout_margin_percent`, `min_breakout_volume_ratio`, `min_hold_bars`, `pm_high_proximity_percent`
- Scoring: weight params if configurable
- Trade: `stop_buffer_atr_mult`, `target_ratio`
- All with complete metadata

### 2. Strategy Config: `config/strategies/premarket_high_break.yaml`
```yaml
pattern_class: "PreMarketHighBreakPattern"
operating_window:
  start: "09:35"
  end: "10:30"
allowed_regimes:
  - bullish_trending
  - bearish_trending
  - neutral
  - high_volatility
mode: "live"
```

### 3. Universe Filter: `config/universe_filters/premarket_high_break.yaml`
```yaml
min_price: 5.0
max_price: 200.0
min_avg_volume: 300000
min_premarket_volume: 50000
```
**CRITICAL:** Verify `min_premarket_volume` exists in UniverseFilterConfig Pydantic model. If missing, ADD it with `min_premarket_volume: int | None = None`. Write a verification test.

### 4. Exit Management Override
```yaml
premarket_high_break:
  trailing_stop:
    enabled: true
    mode: "atr"
    atr_multiplier: 1.5
    activation_r: 0.5
  partial_profit:
    enabled: true
    targets:
      - r_multiple: 1.5
        percent: 50
  time_escalation:
    enabled: true
    phases:
      - after_minutes: 20
        tighten_stop_percent: 25
      - after_minutes: 30
        action: "flatten"
```

### 5. Strategy Registration

## Constraints
- Do NOT modify: `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`
- Pre-market high MUST be computed from candles already in the deque — do NOT add FMP or external data calls
- Timezone handling must be correct — verify CandleBar timestamp convention before coding the PM window filter

## Test Targets
1. PM high computation from pre-market candles → correct high value
2. PM high with <3 PM candles → None
3. PM high with insufficient PM volume → None
4. Breakout detection above PM high → PatternDetection
5. Reject breakout without volume confirmation → None
6. Reject breakout without hold duration → None
7. PM high quality: more touches = higher score
8. Gap context scoring: gap up > flat > gap down
9. set_reference_data() extracts prior closes correctly
10. PatternParam completeness (~13 params)
11. Config + filter + exit parse correctly
12. min_premarket_volume verified in UniverseFilterConfig
- Minimum new test count: 12
- Test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`

**Test data note:** Build synthetic candle sequences with explicit timestamps. Pre-market candles (e.g., 7:00–9:29 AM ET) establishing a high, then market-hours candles (9:35+) breaking above it. This tests the timestamp-based PM candle identification.

## Config Validation
Verify `min_premarket_volume` in UniverseFilterConfig:
1. Locate model
2. Check field existence
3. If missing: add `min_premarket_volume: int | None = None`
4. Test: YAML keys recognized by model

## Definition of Done
- [ ] PreMarketHighBreakPattern implements all 5 PatternModule abstract members
- [ ] PM high computed from deque candles (timestamp-based PM window filter)
- [ ] Returns None for insufficient PM candles or volume
- [ ] Breakout detection with volume + hold confirmation
- [ ] Gap context scoring from prior close via set_reference_data
- [ ] min_premarket_volume verified in UniverseFilterConfig
- [ ] Config, filter, exit, registration all correct
- [ ] 12+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing patterns unchanged | `git diff argus/strategies/patterns/` — only new file + exit_management |
| UniverseFilterConfig change backward compatible | Existing filters parse |
| Timezone handling correct | Test with known ET timestamps |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-7-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-7-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
5. Do not modify: `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`

## Session-Specific Review Focus (for @reviewer)
1. Verify PM candle identification uses correct timezone (ET, not UTC)
2. Verify PM high is computed from candle `high` field, not `close`
3. Verify min_hold_bars enforced (anti-false-breakout, same pattern as HOD Break)
4. Verify set_reference_data handles missing prior_closes gracefully
5. Verify min_premarket_volume in UniverseFilterConfig is not silently ignored
6. Verify the pattern does NOT make external API calls for PM data

## Sprint-Level Regression Checklist / Escalation Criteria
See `docs/sprints/sprint-29/review-context.md`

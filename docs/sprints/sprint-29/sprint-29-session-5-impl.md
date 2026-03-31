# Sprint 29, Session 5: Gap-and-Go Pattern

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam, set_reference_data)
   - `argus/strategies/patterns/bull_flag.py` (reference implementation)
   - `argus/strategies/pattern_strategy.py` (wrapper — note reference data hook from S1)
   - `argus/strategies/red_to_green.py` (reference for prior close pattern: `initialize_prior_closes()`)
   - `config/exit_management.yaml` (current structure)
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
   Expected: all passing
3. Verify you are on branch `main`

## Objective
Implement the Gap-and-Go pattern as a PatternModule. This pattern detects gap-up continuations — stocks gapping up on high relative volume that maintain momentum after the open. This is the FIRST pattern to use the `set_reference_data()` hook for prior close data.

## Requirements

### 1. Pattern Implementation: `argus/strategies/patterns/gap_and_go.py`

Create `GapAndGoPattern` implementing PatternModule ABC:

**`name`** property: `"gap_and_go"`

**`lookback_bars`** property: 15 (tight window — gap plays are fast)

**Override `set_reference_data(data: dict[str, Any])`:**
- Extract `prior_closes: dict[str, float]` from data dict
- Store as `self._prior_closes` instance variable
- If `prior_closes` key missing, store empty dict

**`detect(candles: list[CandleBar]) -> PatternDetection | None`:**
- Gap calculation:
  - Get prior close for this symbol from `self._prior_closes`
  - If no prior close available: return None (cannot calculate gap)
  - Gap percent = `(first_candle_open - prior_close) / prior_close * 100`
  - Reject if gap < `min_gap_percent` (default 3.0%)
- Volume confirmation:
  - First N bars' average volume ≥ `min_relative_volume` (default 2.0) × prior day average volume
  - If prior day volume unavailable (from reference data), use 20-bar rolling average as proxy
- VWAP hold:
  - Price must stay above VWAP for at least `min_vwap_hold_bars` (default 3) of the first `vwap_check_window` (default 8) bars
- Entry mode (configurable `entry_mode`, default "first_pullback"):
  - **first_pullback**: Wait for first pullback (close below prior bar close), then re-entry on close above pullback high. Safer entry.
  - **direct_breakout**: Enter when price breaks above first 5-min high. More aggressive.
- Stop: below VWAP or first 5-min low, whichever is tighter (configurable `stop_mode`)
- Target: gap size × `target_ratio` (default 1.0) from entry

**`score(candles: list[CandleBar], detection: PatternDetection) -> int`:**
- 0–100 with weights:
  - Gap size relative to ATR (30): larger gap (in ATR terms) = higher score, cap at 5× ATR
  - Volume ratio (30): higher relative volume = higher
  - VWAP hold (20): more bars above VWAP = higher
  - Catalyst presence (20): if quality_data available via PatternDetection metadata, catalyst present = higher; else base score

**`get_default_params() -> list[PatternParam]`:**
~14 PatternParam entries. Include `entry_mode` as a string param (note: PatternParam supports str type for categorical params — min/max/step should be None, document valid values in description).

### 2. Strategy Config: `config/strategies/gap_and_go.yaml`
```yaml
pattern_class: "GapAndGoPattern"
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

### 3. Universe Filter: `config/universe_filters/gap_and_go.yaml`
```yaml
min_price: 3.0
max_price: 150.0
min_avg_volume: 200000
min_gap_percent: 3.0
```
**CRITICAL:** Verify `min_gap_percent` exists in UniverseFilterConfig Pydantic model. If missing, ADD it. This is a universe-level filter — symbols below this gap threshold should not be routed to Gap-and-Go at all.

### 4. Exit Management Override
```yaml
gap_and_go:
  trailing_stop:
    enabled: true
    mode: "percent"
    percent: 1.5
    activation_r: 0.3
  partial_profit:
    enabled: true
    targets:
      - r_multiple: 1.0
        percent: 50
  time_escalation:
    enabled: true
    phases:
      - after_minutes: 15
        tighten_stop_percent: 30
      - after_minutes: 20
        action: "flatten"
```

### 5. Strategy Registration

## Constraints
- Do NOT modify: `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`
- Pattern MUST return None when prior close unavailable (not crash, not estimate)
- `set_reference_data()` must handle missing `prior_closes` key gracefully

## Test Targets
1. Detect gap-up above threshold with volume confirmation → PatternDetection
2. Reject gap below min_gap_percent → None
3. Reject no prior close data → None (not crash)
4. Reject insufficient volume → None
5. Reject VWAP not held → None
6. First pullback entry mode detection
7. Direct breakout entry mode detection
8. set_reference_data() stores prior closes correctly
9. set_reference_data() handles missing key gracefully
10. Score weights: 30/30/20/20 verified
11. PatternParam completeness (including string entry_mode param)
12. Config + filter + exit parse correctly; min_gap_percent verified in model
- Minimum new test count: 12
- Test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`

## Config Validation
Verify `min_gap_percent` exists in UniverseFilterConfig:
1. Locate UniverseFilterConfig model
2. Check for `min_gap_percent` field
3. If missing: add `min_gap_percent: float | None = None` to model
4. Write test verifying YAML keys recognized by model

## Definition of Done
- [ ] GapAndGoPattern implements all 5 PatternModule abstract members
- [ ] Overrides set_reference_data() for prior close extraction
- [ ] Gap calculation from prior close (returns None if unavailable)
- [ ] Two entry modes (first_pullback, direct_breakout)
- [ ] min_gap_percent verified in UniverseFilterConfig
- [ ] Config, filter, exit, registration all correct
- [ ] 12+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing patterns unchanged | `git diff argus/strategies/patterns/` — only new file + exit_management |
| base.py/pattern_strategy.py unchanged | `git diff` confirms no changes |
| UniverseFilterConfig change (if any) backward compatible | Existing filter YAMLs still parse |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
5. Do not modify: `base.py`, `pattern_strategy.py`, existing patterns, `core/`, `execution/`, `ui/`, `api/`

## Session-Specific Review Focus (for @reviewer)
1. Verify set_reference_data() handles missing `prior_closes` key (empty dict, not KeyError)
2. Verify detect() returns None (not exception) when no prior close for symbol
3. Verify gap calculation: `(open - prior_close) / prior_close * 100` (not inverted)
4. Verify entry_mode parameter actually changes detection behavior (not just stored)
5. Verify min_gap_percent in UniverseFilterConfig is actively used (not silently ignored)
6. Verify VWAP hold check handles case where VWAP not yet computed (early bars)

## Sprint-Level Regression Checklist / Escalation Criteria
See `docs/sprints/sprint-29/review-context.md`

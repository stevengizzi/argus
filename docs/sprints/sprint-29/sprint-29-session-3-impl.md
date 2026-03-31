# Sprint 29, Session 3: Dip-and-Rip Pattern

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam, CandleBar, PatternDetection)
   - `argus/strategies/patterns/bull_flag.py` (reference implementation for PatternModule pattern)
   - `argus/strategies/pattern_strategy.py` (PatternBasedStrategy wrapper)
   - `config/exit_management.yaml` (current exit config structure)
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
   Expected: all passing
3. Verify you are on branch `main`

## Objective
Implement the Dip-and-Rip pattern as a PatternModule. This pattern detects sharp intraday dips followed by rapid recoveries — a momentum reversal play. Includes strategy config YAML, universe filter, exit management override, and strategy registration.

## Requirements

### 1. Pattern Implementation: `argus/strategies/patterns/dip_and_rip.py`

Create `DipAndRipPattern` implementing PatternModule ABC:

**`name`** property: `"dip_and_rip"`

**`lookback_bars`** property: 30 (needs ~30 minutes of 1-min candles to detect dip + recovery)

**`detect(candles: list[CandleBar]) -> PatternDetection | None`:**
- Scan recent candles for a sharp dip:
  - Calculate rolling high from last N bars (configurable `dip_lookback`, default 10)
  - Dip = price drops ≥ `min_dip_percent` (default 2.0%) from rolling high within `max_dip_bars` (default 5) bars
  - The dip must occur after 9:35 AM ET (differentiation from R2G which handles gap-based reversals)
- Validate rapid recovery:
  - After dip low, price recovers ≥ `min_recovery_percent` (default 50%) of the dip within `max_recovery_bars` (default 8) bars
  - Recovery velocity: recovery must happen faster than the dip (recovery_bars ≤ dip_bars × `max_recovery_ratio`, default 1.5)
- Volume confirmation:
  - Volume on recovery bars must be ≥ `min_recovery_volume_ratio` (default 1.3) × average volume of dip bars
- Level interaction (optional enhancement):
  - Check if dip found support at VWAP or a round number level
  - This is scored, not required for detection
- Entry: at confirmation of recovery (close above `entry_threshold_percent` of dip range, default 60%)
- Stop: below dip low minus `stop_buffer_atr_mult` (default 0.3) × ATR
- Target: measured move (dip range × `target_ratio`, default 1.5) from dip low

**`score(candles: list[CandleBar], detection: PatternDetection) -> int`:**
- 0–100 with weights:
  - Dip severity/speed (30): deeper + faster dip = higher score
  - Recovery velocity (25): faster recovery = higher score
  - Volume profile (25): higher recovery volume ratio = higher
  - Level interaction (20): dip at VWAP/support = higher, no level = base score

**`get_default_params() -> list[PatternParam]`:**
Return PatternParam list for all configurable parameters (expect ~12 params):
- Detection category: `dip_lookback`, `min_dip_percent`, `max_dip_bars`, `min_recovery_percent`, `max_recovery_bars`, `max_recovery_ratio`, `entry_threshold_percent`
- Filtering category: `min_recovery_volume_ratio`
- Scoring category: scoring weight params if configurable
- Each param: name, param_type (int or float), default, min_value, max_value, step, description, category

### 2. Strategy Config: `config/strategies/dip_and_rip.yaml`
```yaml
pattern_class: "DipAndRipPattern"
operating_window:
  start: "09:45"
  end: "11:30"
allowed_regimes:
  - bullish_trending
  - bearish_trending
  - neutral
  - high_volatility
mode: "live"
```

### 3. Universe Filter: `config/universe_filters/dip_and_rip.yaml`
```yaml
min_price: 5.0
max_price: 200.0
min_avg_volume: 500000
min_relative_volume: 1.5
```
**CRITICAL:** Verify `min_relative_volume` exists as a field in the UniverseFilterConfig Pydantic model. If it does not exist, ADD it to the model with appropriate type and default. Do NOT proceed with a YAML key that Pydantic will silently ignore.

### 4. Exit Management Override
Add to `config/exit_management.yaml` under `strategy_exit_overrides`:
```yaml
dip_and_rip:
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
Register the Dip-and-Rip strategy in the orchestrator/system config so it loads at startup. Follow the same registration pattern as Bull Flag and Flat-Top Breakout.

## Constraints
- Do NOT modify: `argus/strategies/patterns/base.py`, `argus/strategies/pattern_strategy.py` (locked after S1)
- Do NOT modify: `core/events.py`, `execution/order_manager.py`, `ui/`, `api/`, `intelligence/`
- Do NOT modify: existing pattern files (bull_flag.py, flat_top_breakout.py)
- Pattern MUST use PatternParam for `get_default_params()` (not dict)
- Detection MUST reject dips occurring before 9:35 AM ET

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Detect sharp dip meeting threshold → PatternDetection returned
  2. Reject insufficient dip (below min_dip_percent) → None
  3. Reject slow recovery (exceeds max_recovery_bars) → None
  4. Reject recovery with insufficient volume → None
  5. Reject dip before 9:35 AM (R2G differentiation) → None
  6. Score weights: verify 30/25/25/20 weighting
  7. Score with VWAP level interaction → higher score
  8. PatternParam list completeness (all params have description, range, step)
  9. Config YAML parses correctly
  10. Exit override applies correctly via deep_update
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`

## Config Validation
Verify `min_relative_volume` exists in UniverseFilterConfig Pydantic model:
1. Locate the UniverseFilterConfig model
2. Check if `min_relative_volume` is a recognized field
3. If missing: add `min_relative_volume: float | None = None` to the model
4. Write a test that loads `config/universe_filters/dip_and_rip.yaml` and verifies all keys are recognized by the model

## Definition of Done
- [ ] DipAndRipPattern implements all 5 PatternModule abstract members
- [ ] Detection logic handles dip + recovery + volume + level interaction
- [ ] Differentiates from R2G (intraday only, no pre-market dips)
- [ ] Score returns 0–100 with 30/25/25/20 weights
- [ ] get_default_params() returns list[PatternParam] with ~12 params
- [ ] Config YAML, filter YAML, exit override all parse correctly
- [ ] min_relative_volume verified in Pydantic model
- [ ] Registered in orchestrator
- [ ] 10+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing patterns unchanged | `git diff argus/strategies/patterns/bull_flag.py` — no changes |
| base.py unchanged | `git diff argus/strategies/patterns/base.py` — no changes |
| pattern_strategy.py unchanged | `git diff argus/strategies/pattern_strategy.py` — no changes |
| Exit management existing entries preserved | `git diff config/exit_management.yaml` — only additions |
| Config field not silently ignored | Config validation test passes |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-29/review-context.md`
2. Close-out: `docs/sprints/sprint-29/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/ -x -q --timeout=30`
5. Do not modify: `base.py`, `pattern_strategy.py`, `bull_flag.py`, `flat_top_breakout.py`, `core/`, `execution/`, `ui/`, `api/`

## Session-Specific Review Focus (for @reviewer)
1. Verify dip detection rejects pre-9:35 AM dips (R2G differentiation)
2. Verify recovery velocity check (not just recovery size)
3. Verify volume confirmation uses recovery bars vs dip bars ratio
4. Verify PatternParam list has complete metadata for all params
5. Verify min_relative_volume is actually checked by UniverseFilterConfig (not silently ignored)
6. Verify exit override structure matches ExitManagementConfig schema

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-29/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-29/review-context.md`

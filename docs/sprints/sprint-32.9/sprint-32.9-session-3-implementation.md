# Sprint 32.9, Session 3: Position Safety + Quality Recalibration + Strategy Triage

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/main.py` (focus on `_process_signal()` and signal dispatch flow)
   - `argus/core/orchestrator.py` (signal processing, config model)
   - `argus/intelligence/quality_engine.py` (scoring dimensions, especially `_score_historical_match()`)
   - `argus/intelligence/config.py` (QualityWeightsConfig with sum-to-1.0 validator, QualityThresholdsConfig)
   - `config/quality_engine.yaml`
   - `config/risk_limits.yaml`
   - `config/overflow.yaml`
   - `config/orchestrator.yaml`
   - `config/strategies/abcd.yaml`
   - `config/strategies/flat_top_breakout.yaml`
   - `config/experiments.yaml`
   - `docs/pre-live-transition-checklist.md`
   - Session 2 close-out: `docs/sprints/sprint-32.9/session-2-closeout.md`
2. Run the scoped test baseline:
   `python -m pytest tests/core/ tests/intelligence/ -x -q`
   Expected: all passing (full suite confirmed by S2 close-out)
3. Verify you are on branch `main` with Sessions 1-2 committed

## Objective
Add pre-EOD signal cutoff to reduce position count before market close. Recalibrate quality engine to actually differentiate between setups (currently all signals score B). Enable position limits. Demote underperforming strategies to shadow mode. Enable experiment pipeline for future parameter optimization.

## Requirements

### 1. Pre-EOD Signal Cutoff

In the signal processing path (`_process_signal()` in `argus/main.py` or wherever signals are dispatched to the quality pipeline / order manager):

a) Before processing any new signal, check current ET time against `signal_cutoff_time`:
   ```python
   if self._signal_cutoff_enabled:
       et_tz = ZoneInfo("America/New_York")
       now_et = self._clock.now().astimezone(et_tz)
       cutoff = time.fromisoformat(self._signal_cutoff_time)
       if now_et.time() >= cutoff:
           if not self._cutoff_logged:
               logger.info(
                   "Pre-EOD signal cutoff active at %s ET — "
                   "no new entries until next session",
                   now_et.time().isoformat()[:5],
               )
               self._cutoff_logged = True
           return  # Skip signal, do NOT publish rejection event
   ```
   
b) Add instance variable `self._cutoff_logged: bool = False` — reset at daily state reset.

c) This does NOT affect existing position management: trailing stops, time stops, bracket fills, flatten orders all continue normally.

d) Config: Add to `OrchestratorConfig` (or whichever Pydantic model configures signal processing):
   - `signal_cutoff_enabled: bool = True`
   - `signal_cutoff_time: str = "15:30"`
   Add corresponding keys to `config/orchestrator.yaml`.

### 2. Enable Max Concurrent Positions

In `config/risk_limits.yaml`:
- Change `max_concurrent_positions: 0` → `max_concurrent_positions: 50`
- This activates the existing DEC-367 check in Risk Manager (line ~293 of risk_manager.py)
- Verify the check works: it calls `broker.get_positions()` and rejects signals when `len(positions) >= 50`

### 3. Reduce Overflow Broker Capacity

In `config/overflow.yaml`:
- Change `broker_capacity: 60` → `broker_capacity: 50`
- This aligns with max_concurrent_positions — both gates use 50 as the limit

### 4. Quality Engine Recalibration

**Problem:** Three of five scoring dimensions produce constant values:
- `_score_historical_match()` → hardcoded `return 50.0` (stub, 15% weight)
- `_score_catalyst_quality()` → returns 50.0 when no recent catalysts (true for most symbols)
- `_score_regime_alignment()` → returns 80.0 when regime matches (true for all strategies today)

Result: 50% of weight produces fixed scores. All 10,683 signals on April 2 scored between B- and B+ (41.7-66.8). Zero A or C grades.

**Fix — Weight redistribution:**

In `config/quality_engine.yaml`, change weights:
```yaml
weights:
  pattern_strength: 0.375   # was 0.30 — absorbed half of historical_match
  catalyst_quality: 0.25    # unchanged
  volume_profile: 0.275     # was 0.20 — absorbed half of historical_match
  historical_match: 0.0     # was 0.15 — stub returning constant 50, zero information
  regime_alignment: 0.10    # unchanged
```
Sum = 0.375 + 0.25 + 0.275 + 0.0 + 0.10 = 1.0 ✓

**Fix — Threshold recalibration:**

With the new weights, the effective score range is approximately 35-77 (vs theoretical 0-100). Recalibrate thresholds to distribute grades across this actual range:

```yaml
thresholds:
  a_plus: 72    # was 90 — now achievable with exceptional pattern + volume
  a: 66         # was 80
  a_minus: 61   # was 70
  b_plus: 56    # was 60
  b: 51         # was 50
  b_minus: 46   # was 40
  c_plus: 40    # was 30
```

**Add code comment** in `config/quality_engine.yaml`:
```yaml
# Weights recalibrated Sprint 32.9: historical_match zeroed (stub returning constant 50).
# Weight redistributed to pattern_strength and volume_profile — the dimensions that
# actually differentiate. Restore historical_match weight when it has real data
# (post-Learning Loop V2 or historical match implementation).
#
# Thresholds recalibrated for actual score distribution (~35-77 range).
# Previous thresholds were calibrated for theoretical 0-100 range, causing all
# signals to cluster in B grade. These thresholds distribute grades across the
# actual signal population.
```

### 5. Strategy Shadow Demotion

In `config/strategies/abcd.yaml`:
- Change `mode: live` → `mode: shadow`
- Add comment: `# Demoted Sprint 32.9 — 567 trades at 21.9% win rate. Evaluate for promotion after parameter optimization via Experiment Pipeline.`

In `config/strategies/flat_top_breakout.yaml`:
- Change `mode: live` → `mode: shadow`
- Add comment: `# Demoted Sprint 32.9 — 96 trades at 18.8% win rate, avg R -0.71. Evaluate for promotion after parameter optimization.`

Both strategies continue generating counterfactual data in shadow mode. Zero data loss.

### 6. Enable Experiment Pipeline

In `config/experiments.yaml`:
- Change `enabled: false` → `enabled: true`
- Leave `auto_promote: false` (operator-approved promotions for now)
- Leave `variants: {}` (no variants configured yet — infrastructure initializes and sits ready)

Add comment:
```yaml
# Enabled Sprint 32.9. With variants: {} this is a no-op — infrastructure
# initializes but spawns 0 variants. Configure variants after running
# parameter sweeps via scripts/run_experiment.py.
```

### 7. Update Pre-Live Transition Checklist

In `docs/pre-live-transition-checklist.md`, add section:

```markdown
## Sprint 32.9 additions
- [ ] `max_concurrent_positions`: review 50 for live (may need adjustment based on capital and margin)
- [ ] `overflow.broker_capacity`: review 50 for live (should match or exceed max_concurrent_positions)
- [ ] `signal_cutoff_time`: review "15:30" for live (consider market close dynamics)
- [ ] `signal_cutoff_enabled`: keep true for live
- [ ] `margin_rejection_threshold`: review 10 for live (may need adjustment)
- [ ] `margin_circuit_reset_positions`: review 20 for live
- [ ] `eod_flatten_timeout_seconds`: review 30 for live
- [ ] `strat_abcd` mode: evaluate for promotion after parameter optimization
- [ ] `strat_flat_top_breakout` mode: evaluate for promotion after parameter optimization
- [ ] Quality engine weights: restore `historical_match` weight when real data available
- [ ] Quality engine thresholds: re-evaluate after observing grade distribution with new weights
- [ ] `experiments.enabled`: keep true, configure `auto_promote` based on confidence
```

## Constraints
- Do NOT modify: `order_manager.py` (Sessions 1-2 own this), strategy detection logic, BacktestEngine, UI
- Do NOT change: quality engine scoring CODE (only config — the `_score_*` methods are unchanged)
- Do NOT change: strategy parameters (that's experiment pipeline territory)
- Preserve: all existing shadow mode mechanics, overflow routing behavior, QualityWeightsConfig validator

## Test Targets
New tests to write:
1. `test_signal_cutoff_blocks_after_time` — mock clock to 15:31 ET, submit signal, verify skipped
2. `test_signal_cutoff_allows_before_time` — mock clock to 15:29 ET, submit signal, verify processed
3. `test_signal_cutoff_disabled` — set `signal_cutoff_enabled: false`, mock past cutoff, verify signals process
4. `test_signal_cutoff_logs_once` — submit 10 signals past cutoff, verify only 1 log message
5. `test_quality_weights_sum_to_one` — load quality_engine.yaml, verify QualityWeightsConfig validates (sum = 1.0)
6. `test_quality_grades_differentiate` — create mock signals with varying pattern_strength (20, 50, 80) and volume_profile (10, 50, 90), score them, verify grades span A through C (not all B)
7. `test_max_concurrent_positions_loaded` — load risk_limits.yaml, verify value is 50
8. `test_overflow_capacity_loaded` — load overflow.yaml, verify value is 50
9. `test_strategy_shadow_mode` — load abcd.yaml and flat_top_breakout.yaml, verify mode is "shadow"
10. `test_experiments_enabled` — load experiments.yaml, verify enabled is true

Minimum new test count: 8
Test command (FINAL SESSION — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Config Validation
Write tests that verify:
- `signal_cutoff_enabled` and `signal_cutoff_time` → OrchestratorConfig fields
- Quality weights sum to 1.0 with new values (existing validator covers this)
- All new config keys in system_live.yaml recognized by their Pydantic models

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| EOD flatten from S1 still works | `python -m pytest tests/execution/ -x -q` |
| Margin circuit breaker from S2 still works | `python -m pytest tests/execution/ -x -q` |
| Non-shadow strategies unaffected (10 still mode=live) | Verify config files |
| Shadow strategies generate counterfactual data | Existing shadow mode tests |
| Quality weights sum validator passes | New test |
| Quality engine scoring code unchanged | Diff check — only YAML modified |
| Experiment pipeline boots without error | Log check at boot |
| Pre-live checklist complete | Manual review |

## Definition of Done
- [ ] Signal cutoff implemented and tested
- [ ] max_concurrent_positions=50 active
- [ ] overflow broker_capacity=50 active
- [ ] Quality weights redistributed (historical_match=0.0)
- [ ] Quality thresholds recalibrated for actual range
- [ ] Quality grades differentiate (A through C appear in tests)
- [ ] ABCD and Flat-Top in shadow mode
- [ ] Experiment pipeline enabled
- [ ] Pre-live checklist updated
- [ ] All 8+ new tests passing
- [ ] Full test suite passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
**Write the close-out report to:** docs/sprints/sprint-32.9/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: Sprint 32.9 scope
2. Close-out report: docs/sprints/sprint-32.9/session-3-closeout.md
3. Diff range: `git diff HEAD~1`
4. Test command (FINAL SESSION): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified: `argus/execution/order_manager.py`, `argus/strategies/patterns/`, `argus/ui/`, `argus/backtest/`

## Session-Specific Review Focus (for @reviewer)
1. Verify signal cutoff is in the processing path, not the generation path (strategies still evaluate)
2. Verify quality engine YAML weights sum to 1.0 — load and validate with Pydantic
3. Verify quality thresholds actually produce A/B/C grades with test signals (not all B)
4. Verify max_concurrent_positions=50 is loaded by Risk Manager (not silently ignored)
5. Verify overflow broker_capacity aligns with max_concurrent_positions
6. Verify shadow mode configs use correct YAML syntax (mode: shadow, not mode: "shadow" if YAML parser differs)
7. Verify experiments.yaml enabled=true boots cleanly with empty variants
8. Verify pre-live checklist is complete with all new items
9. Full test suite passes with zero regressions

## Sprint-Level Escalation Criteria
- Any change to bracket order logic
- Any change to how existing positions are managed mid-session
- Any modification to the broker abstraction interface
- Test count drops by more than 5 from baseline

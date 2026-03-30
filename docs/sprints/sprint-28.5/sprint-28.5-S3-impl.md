# Sprint 28.5, Session S3: Strategy ATR Emission + main.py Config Loading

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` (SignalEvent with atr_value from S2)
   - `argus/strategies/orb_breakout.py` (representative signal emission)
   - `argus/strategies/pattern_strategy.py` (PatternBasedStrategy — may not have IndicatorEngine ATR)
   - `argus/main.py` (startup sequence, config loading pattern)
   - `config/exit_management.yaml` (from S2)
2. Run scoped test baseline:
   ```
   python -m pytest tests/unit/core/test_exit_math.py tests/unit/core/test_exit_management_config.py -x -q
   ```
3. Verify branch: `sprint-28.5`

## Objective
Wire all 7 strategies to emit `atr_value` on SignalEvent using ATR(14) via IndicatorEngine (AMD-9). Load `exit_management.yaml` in main.py and pass ExitManagementConfig to OrderManager. Log deprecated config warning if legacy fields active (AMD-10).

## Requirements

1. **Strategy ATR emission (all 7 strategies):** In each strategy's signal emission code, add `atr_value=` parameter to the SignalEvent constructor:
   - For strategies with IndicatorEngine access: emit `atr_value=self._indicators.atr(symbol, period=14)` or equivalent ATR(14) on 1-min bars. Add a code comment: `# ATR(14) on 1-min bars per AMD-9 standardization`
   - For PatternBasedStrategy: if it doesn't have ATR access, emit `atr_value=None`. Add comment: `# No IndicatorEngine ATR access — trail falls back to percent mode`
   - Strategies to modify: `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py`, `pattern_strategy.py` (covers Bull Flag + Flat-Top)
   - Check if RedToGreenStrategy has IndicatorEngine access — if not, emit None with comment.

2. **main.py config loading:** In the startup sequence (near where order_manager.yaml is loaded):
   - Load `exit_management.yaml` via `load_yaml_file()`
   - Parse into `ExitManagementConfig(**yaml_data)`
   - Pass to OrderManager constructor as a new parameter (OrderManager won't use it until S4a — just store it)
   - **AMD-10 deprecated warning:** After loading order_manager.yaml, check if `enable_trailing_stop` is True or `trailing_stop_atr_multiplier` differs from 2.0. If so, log WARNING: "Legacy trailing stop config detected (enable_trailing_stop / trailing_stop_atr_multiplier). These fields are deprecated — use config/exit_management.yaml instead. Legacy fields are ignored."

3. **OrderManager constructor update:** Add `exit_config: ExitManagementConfig | None = None` parameter to OrderManager.__init__(). Store as `self._exit_config`. No behavioral changes yet (S4a/S4b).

## Constraints
- Do NOT modify exit behavior in Order Manager (just accept and store config)
- Do NOT modify fill_model.py, risk_manager.py
- Strategy changes are single-line additions (atr_value param) — keep changes minimal

## Test Targets
- New test file: `tests/unit/strategies/test_atr_emission.py`
- Minimum new test count: 6
- Tests:
  1. ORB Breakout emits non-None atr_value on signal
  2. VWAP Reclaim emits non-None atr_value on signal
  3. PatternBasedStrategy emits atr_value (None if no ATR access)
  4. main.py loads exit_management.yaml without error
  5. OrderManager accepts exit_config parameter
  6. AMD-10: deprecated config warning logged when enable_trailing_stop=true
- Test command: `python -m pytest tests/unit/strategies/test_atr_emission.py -x -q -v`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All existing strategy tests pass | Run strategy test suite |
| Signal emission still works for all strategies | Existing tests pass |
| main.py startup sequence unchanged for non-exit-config paths | Existing main.py tests pass |

## Definition of Done
- [ ] All 7 strategies emit atr_value on SignalEvent (with AMD-9 code comments)
- [ ] main.py loads exit_management.yaml and passes to OrderManager
- [ ] AMD-10 deprecated config warning implemented
- [ ] OrderManager accepts exit_config parameter (stored, not used yet)
- [ ] 6+ new tests passing
- [ ] Close-out report written to `docs/sprints/sprint-28.5/session-S3-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
The close-out report MUST include a structured JSON appendix fenced with ```json:structured-closeout.
**Write to:** `docs/sprints/sprint-28.5/session-S3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-28.5/review-context.md`
2. Close-out: `docs/sprints/sprint-28.5/session-S3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/unit/strategies/test_atr_emission.py -x -q -v`
5. Files NOT to modify: fill_model.py, risk_manager.py, order_manager exit logic

## Session-Specific Review Focus (for @reviewer)
1. Verify AMD-9: all strategies with IndicatorEngine emit ATR(14), code comments present
2. Verify AMD-10: deprecated config warning fires when legacy fields active
3. Verify OrderManager constructor change is additive only (default None, no behavioral change)
4. Verify no strategy signal generation logic changed (only atr_value addition)

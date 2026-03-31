# Sprint 29.5, Session 7: ORB Scalp Exclusion Fix

## Pre-Flight Checks
1. Read: `argus/strategies/orb_base.py` (focus on `_orb_family_triggered_symbols`, `_check_breakout`, `_reset_daily_state`), `argus/strategies/orb_breakout.py`, `argus/strategies/orb_scalp.py`, `argus/core/config.py` (OrchestratorConfig), `config/orchestrator.yaml`
2. Run scoped baseline: `python -m pytest tests/strategies/test_orb_base.py tests/strategies/test_orb_scalp.py tests/strategies/test_orb_breakout.py -x -q`
3. Verify branch: `sprint-29.5`
4. This is the **final session** of the sprint. Full suite must pass at close-out.

## Objective
Make the DEC-261 ORB family same-symbol mutual exclusion configurable so ORB Scalp can generate independent signals during paper trading for data capture.

## Requirements

1. **Add config flag** in `argus/core/config.py`:
   - Add `orb_family_mutual_exclusion: bool = True` to `OrchestratorConfig`

2. **Add config value** in `config/orchestrator.yaml`:
   - Add `orb_family_mutual_exclusion: false` with comment: `# PAPER TRADING: Disabled to allow both ORB strategies to fire on same symbol. Restore to true before live.`

3. **Wire config to strategies** in `argus/main.py`:
   - After constructing OrchestratorConfig, set a class variable on OrbBaseStrategy:
     `OrbBaseStrategy.mutual_exclusion_enabled = config.orb_family_mutual_exclusion`
   - OR pass via constructor — check which pattern is cleaner given that `_orb_family_triggered_symbols` is a ClassVar.

4. **Conditional exclusion check** in `argus/strategies/orb_base.py`:
   - Add `mutual_exclusion_enabled: ClassVar[bool] = True` class variable
   - In `_check_breakout()` (~line 604), wrap the exclusion check:
     ```python
     if OrbBaseStrategy.mutual_exclusion_enabled and symbol in OrbBaseStrategy._orb_family_triggered_symbols:
         # existing exclusion logic
     ```
   - In `orb_breakout.py` and `orb_scalp.py`, wrap the `_orb_family_triggered_symbols.add(symbol)` call:
     ```python
     if OrbBaseStrategy.mutual_exclusion_enabled:
         OrbBaseStrategy._orb_family_triggered_symbols.add(symbol)
     ```

5. **Update pre-live checklist** in `docs/pre-live-transition-checklist.md`:
   - Add entry: `orb_family_mutual_exclusion: true` (restore for live)

## Constraints
- Do NOT remove the exclusion mechanism — just make it configurable
- Do NOT modify the ORB strategy signal generation logic beyond the exclusion gate
- Preserve DEC-261 as the default behavior (True)
- Do NOT change any strategy parameters or scoring logic

## Test Targets
- New tests:
  1. `test_orb_exclusion_enabled_blocks_scalp` — with exclusion=True, Breakout fires, Scalp blocked on same symbol
  2. `test_orb_exclusion_disabled_both_fire` — with exclusion=False, both strategies can fire on same symbol
  3. `test_orb_exclusion_disabled_no_add_to_set` — with exclusion=False, triggered_symbols set stays empty
  4. `test_orb_exclusion_config_default_true` — config loads with default True
- Minimum: 4 new tests
- Test command (final session — FULL SUITE):
  `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Config Validation
| YAML Key | Model Field |
|----------|-------------|
| `orb_family_mutual_exclusion` | `OrchestratorConfig.orb_family_mutual_exclusion` |

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| ORB Breakout still fires normally | Existing ORB breakout tests pass |
| Daily state reset still clears exclusion set | test_daily_reset clears _orb_family_triggered_symbols |
| Config backward compatible | Old YAML without new field → default True |

## Definition of Done
- [ ] All requirements implemented
- [ ] **ALL** existing tests pass (full suite — final session)
- [ ] 4+ new tests
- [ ] Config validation test passing
- [ ] Pre-live checklist updated
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-7-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent (full suite)

## Close-Out
Write to: `docs/sprints/sprint-29.5/session-7-closeout.md`

## Tier 2 Review (FINAL SESSION — full suite)
Invoke @reviewer with:
1. Review context: `docs/sprints/sprint-29.5/review-context.md`
2. Close-out: `docs/sprints/sprint-29.5/session-7-closeout.md`
3. Test command (FULL SUITE): `python -m pytest --ignore=tests/test_main.py -n auto -q`
4. Files NOT modified: `argus/intelligence/`, `argus/backtest/`, `argus/analytics/evaluation.py`, `argus/strategies/patterns/`

## Session-Specific Review Focus
1. Verify ClassVar pattern doesn't create test isolation issues (class variable shared across tests)
2. Verify exclusion flag is set BEFORE strategy instances are created in main.py
3. Verify both ORB strategies can independently fire on the same symbol when disabled
4. Verify _orb_family_triggered_symbols is NOT populated when exclusion disabled

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-29.5/review-context.md`
(Full checklist — all 10 items verified since this is the final session)

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-29.5/review-context.md`

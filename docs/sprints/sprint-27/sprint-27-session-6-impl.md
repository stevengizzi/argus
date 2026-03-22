# Sprint 27, Session 6: Walk-Forward Integration + Equivalence Validation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` (S5 output — complete engine with CLI)
   - `argus/backtest/walk_forward.py` (existing WF infrastructure — focus on OOS execution path, around lines 210-500)
   - `argus/backtest/config.py` (WalkForwardConfig, BacktestEngineConfig)
   - `docs/sprints/sprint-27/design-summary.md`
2. Run the test baseline (DEC-328 — Session 2+, scoped):
   ```bash
   python -m pytest tests/backtest/test_engine.py tests/backtest/test_walk_forward.py -x -q
   ```
   Expected: all passing (S5 close-out confirmed)
3. Verify you are on the correct branch: `main`

## Objective
Wire the BacktestEngine into walk_forward.py as an alternative OOS validation engine (preserving the existing Replay Harness path), add oos_engine attribution to results (AR-4), and write directional equivalence tests comparing BacktestEngine against Replay Harness on the same data.

## Requirements

1. **Add `oos_engine` field to `WindowResult` and `WalkForwardResult`:**
   In `argus/backtest/walk_forward.py`:
   - Add `oos_engine: str = "replay_harness"` field to `WindowResult` dataclass (AR-4)
   - Add `oos_engine: str = "replay_harness"` field to `WalkForwardResult` dataclass
   - These default to "replay_harness" so existing code paths are unaffected

2. **Add `oos_engine` parameter to `WalkForwardConfig`:**
   ```python
   # OOS validation engine
   oos_engine: str = "replay_harness"  # "replay_harness" or "backtest_engine"
   ```

3. **Create BacktestEngine OOS execution path:**
   In the OOS execution function (find where the Replay Harness runs OOS windows — this is typically in `_run_oos_window()` or similar):
   - Add a conditional: if `config.oos_engine == "backtest_engine"`, use BacktestEngine instead of ReplayHarness
   - The BacktestEngine path:
     a. Create `BacktestEngineConfig` from the WF window parameters (start_date, end_date, symbols, strategy, cash, slippage)
     b. Apply the best IS parameters as config_overrides
     c. Create `BacktestEngine(config)` and run it
     d. Extract metrics from BacktestResult
     e. Set `window_result.oos_engine = "backtest_engine"`
   - The existing Replay Harness path must remain completely unchanged
   - Both paths produce the same `WindowResult` fields

4. **Add `--oos-engine` CLI flag to walk_forward.py:**
   In the argument parser, add:
   ```python
   parser.add_argument("--oos-engine", default="replay_harness",
                       choices=["replay_harness", "backtest_engine"],
                       help="Engine for OOS validation")
   ```
   Wire this into `WalkForwardConfig.oos_engine`.

5. **Record oos_engine in JSON output:**
   The walk-forward results are saved as JSON. Ensure `oos_engine` appears in the output for both WindowResult and WalkForwardResult.

6. **Write directional equivalence tests:**
   These tests run BOTH engines on the same small dataset and verify directional agreement (not exact match). Use mocked/fixture data, not live Databento.

## Constraints
- Do NOT modify: the Replay Harness OOS execution path itself (only add a conditional before it)
- Do NOT change: existing WalkForwardConfig fields, existing CLI behavior when `--oos-engine` is not specified
- Do NOT break: any existing walk_forward.py test
- Do NOT add: any live API calls in tests

## Test Targets
After implementation:
- Existing tests: all must still pass (full suite — this is the final session)
- New tests to write in `tests/backtest/test_walk_forward_engine.py` (new file to avoid bloating existing test file):
  1. `test_wf_backtest_engine_produces_window_result` — BacktestEngine OOS path produces valid WindowResult
  2. `test_wf_engine_selection_backtest_engine` — oos_engine="backtest_engine" routes to BacktestEngine
  3. `test_wf_engine_selection_replay_harness` — oos_engine="replay_harness" routes to ReplayHarness (default)
  4. `test_wf_existing_modes_unchanged` — existing WF CLI modes (no --oos-engine flag) produce same output as before
  5. `test_wf_replay_harness_path_unchanged` — ReplayHarness OOS path still works identically
  6. `test_oos_engine_field_in_window_result` — WindowResult.oos_engine set correctly
  7. `test_oos_engine_field_in_walk_forward_result` — WalkForwardResult.oos_engine set correctly
  8. `test_equivalence_orb_trade_count` — ORB Breakout on same 1-month data → BacktestEngine and Replay Harness produce trade count within 20% of each other
  9. `test_equivalence_orb_pnl_direction` — same-sign gross P&L (both positive or both negative)
  10. `test_equivalence_vwap_directional` — VWAP Reclaim: similar trade count direction
  11. `test_divergence_documented` — test that explicitly asserts: BacktestEngine fill prices may differ from Replay Harness due to bar-level vs tick-synthesis fills (documentary test)
  12. `test_speed_benchmark` — BacktestEngine ≥5x faster than Replay Harness on same mocked data (timed)
  13. `test_wf_config_oos_engine_default` — WalkForwardConfig().oos_engine == "replay_harness"
- Minimum new test count: 13
- **Final session test command (DEC-328 — full suite):**
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```
  Expected: ≥3,005 tests (2,925 baseline + ~80 new), all passing

## Definition of Done
- [ ] oos_engine field added to WindowResult and WalkForwardResult (AR-4)
- [ ] BacktestEngine OOS path added to walk_forward.py
- [ ] Existing Replay Harness OOS path completely unchanged
- [ ] --oos-engine CLI flag added
- [ ] Directional equivalence tests pass (trade count within 20%, same P&L sign)
- [ ] Speed benchmark passes (≥5x)
- [ ] ALL existing tests pass (full suite — final session)
- [ ] 13 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing WF CLI modes unchanged | Run existing WF commands → same output |
| Replay Harness OOS path unmodified | Read the conditional — existing path must be the `else` branch, completely unchanged |
| Replay Harness file unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| All VectorBT files unchanged | `git diff HEAD argus/backtest/vectorbt_*.py` → no changes |
| Full test suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` |
| oos_engine defaults to replay_harness | WalkForwardConfig() without oos_engine → "replay_harness" |

## Close-Out
Write to: docs/sprints/sprint-27/session-6-closeout.md

This is the **final session** of Sprint 27. The close-out should include:
- Final test counts (pytest + Vitest)
- Speed benchmark results
- Equivalence test results summary
- Any new DEF items identified

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-27/review-context.md`
2. Close-out: `docs/sprints/sprint-27/session-6-closeout.md`
3. Diff: `git diff HEAD~1`
4. **Test command (final session — full suite):**
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
5. Do-not-modify: `argus/backtest/replay_harness.py`, `argus/backtest/vectorbt_*.py`, `argus/strategies/`, `argus/ui/`

@reviewer writes to: docs/sprints/sprint-27/session-6-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix findings within this session,
update both close-out and review files per template instructions.

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL: Verify existing Replay Harness OOS path is completely unchanged.** The new BacktestEngine path must be additive — a conditional branch that leaves the existing code untouched.
2. Verify oos_engine defaults to "replay_harness" everywhere (WindowResult, WalkForwardResult, WalkForwardConfig, CLI)
3. Verify directional equivalence tests use the same data for both engines
4. Verify speed benchmark methodology is fair (same data, same strategy, same machine, same run)
5. Verify --oos-engine CLI flag doesn't appear in output of `--help` for existing WF modes (it's a new optional flag)
6. Verify JSON output includes oos_engine field
7. **Full regression check** — this is the final session, all R1–R19 checks apply

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| R1 | Production EventBus unchanged | `git diff HEAD argus/core/event_bus.py` → no changes |
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| R3 | BacktestDataService unchanged | `git diff HEAD argus/backtest/backtest_data_service.py` → no changes |
| R4 | All VectorBT files unchanged | `git diff HEAD argus/backtest/vectorbt_*.py` → no changes |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` → no changes |
| R6 | No frontend files modified | `git diff HEAD argus/ui/` → no changes |
| R7 | No API files modified | `git diff HEAD argus/api/` → no changes |
| R8 | No system.yaml changes | `git diff HEAD config/system.yaml config/system_live.yaml` → no changes |
| R9 | Existing pytest count ≥ 2,925 | Full suite count |
| R10 | Vitest count = 620 | `cd argus/ui && npx vitest run` |
| R11 | No test hangs | Full suite completes within 10 minutes |
| R12 | xdist compatibility | `-n auto` passes |
| R13–R19 | All config/backtest checks | Per checklist |

## Sprint-Level Escalation Criteria (for @reviewer)
1–10: All escalation criteria from the sprint-level list apply to the final session review.

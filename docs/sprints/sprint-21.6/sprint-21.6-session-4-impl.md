# Sprint 21.6, Session 4: Results Analysis + YAML Updates + Validation Report

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `data/backtest_runs/validation/` — list all JSON files, read each one
   - `config/strategies/orb_breakout.yaml` — example of current `backtest_summary` format
   - Read ALL 7 strategy YAML configs to understand current baselines
2. Run scoped test baseline (DEC-328 — Session 4):
   ```
   python -m pytest tests/backtest/test_revalidation_harness.py -x -q
   ```
   Expected: all passing
3. Verify you are on branch: `main`
4. **Critical pre-condition:** Verify that 7 JSON result files exist in `data/backtest_runs/validation/` (one per strategy). If any are missing, STOP and note which strategies were not validated. Proceed with available results.

## Objective
Analyze all 7 validation result JSONs. Compare Databento-era results against provisional Alpaca-era baselines. Update all strategy YAML `backtest_summary` sections with new metrics. If divergence exceeds thresholds, document findings and recommend parameter changes (but only change parameters if the evidence is clear and the WFE justifies it). Produce the final validation comparison report.

## Requirements

1. **Read all validation result JSONs** from `data/backtest_runs/validation/`:
   - `orb_validation.json` (or `orb_breakout_validation.json`)
   - `orb_scalp_validation.json`
   - `vwap_reclaim_validation.json`
   - `afternoon_momentum_validation.json`
   - `red_to_green_validation.json`
   - `bull_flag_validation.json`
   - `flat_top_breakout_validation.json`

   Parse each and extract: status, new metrics (oos_sharpe, wfe_pnl, total_trades, avg_win_rate, avg_profit_factor), divergence flags.

2. **Update all 7 strategy YAML `backtest_summary` sections.** For each strategy config at `config/strategies/{name}.yaml`, update the `backtest_summary` block:

   ```yaml
   backtest_summary:
     status: "databento_validated"  # or "databento_wfe_below_threshold" or "databento_zero_trades"
     data_source: "databento_ohlcv_1m"
     oos_sharpe: <new value>
     wfe_pnl: <new value>
     wfe_sharpe: <new value if available>
     total_trades: <new OOS trade count>
     avg_win_rate: <new value>
     avg_profit_factor: <new value>
     data_months: <computed from date range>
     last_run: "<today's date YYYY-MM-DD>"
     prior_baseline:
       source: "alpaca_provisional"
       oos_sharpe: <old value or null>
       wfe_pnl: <old value or null>
       total_trades: <old value or null>
   ```

   Preserve the `prior_baseline` sub-block so the historical comparison is recorded in the YAML itself. This is informational — no code reads it.

   **IMPORTANT:** Do NOT modify any other section of the YAML — only `backtest_summary`. Leave `risk_limits`, `operating_window`, `benchmarks`, strategy-specific parameters, `universe_filter` unchanged unless divergence analysis specifically warrants a parameter change.

3. **If any strategy shows significant divergence** (Sharpe diff > 0.5, win rate > 10pp, PF > 0.5):
   - Document the divergence in the validation report with full metric comparison
   - Analyze whether the divergence is due to data quality differences (Alpaca vs Databento), date range differences, or genuine strategy underperformance
   - If WFE > 0.3 despite the divergence: the strategy is still validated, just with different absolute numbers. Update the summary but keep current parameters.
   - If WFE < 0.3: flag as needing re-optimization. Do NOT change parameters in this session — document the recommendation in the report for a follow-up sprint.
   - If WFE < 0.1: this is an escalation trigger (see escalation criteria). Document prominently in the report.

4. **Create `docs/sprints/sprint-21.6/validation-report.md`** with:

   a. **Header:** Sprint 21.6 Validation Report, date, data source, date range

   b. **Summary Table:**
   ```
   | Strategy | Status | OOS Sharpe (Old→New) | WFE PnL (Old→New) | Trades | Divergence |
   |----------|--------|---------------------|--------------------| -------|------------|
   | ORB Breakout | VALIDATED | 0.34 → X.XX | 0.56 → X.XX | 137 → XXX | None |
   | ... | ... | ... | ... | ... | ... |
   ```

   c. **Per-Strategy Detail Sections:** For each strategy:
      - Old vs new metric comparison (table)
      - Walk-forward window results summary
      - WFE assessment (pass/fail against DEC-047 threshold of 0.3)
      - Notes on data source differences
      - Recommendation (validated / needs investigation / needs re-optimization)

   d. **Overall Assessment:** How many strategies validated successfully? Any systemic issues? Confidence level in the Databento-era results.

   e. **Forward-Compatibility Notes:**
      - Sprint 27.5 will convert these results to `MultiObjectiveResult` format
      - Sprint 27.5's `RegimeMetrics` should accommodate multi-dimensional regime vectors
      - Execution logging (Sessions 1–2) is now collecting calibration data for Sprint 27.5's slippage model

   f. **DEC-132 Resolution Status:** Can DEC-132 be marked as resolved? Only if ALL 7 strategies have been validated (WFE > 0.3 or documented with remediation plan).

## Constraints
- Do NOT modify: any strategy `.py` file, any file in `argus/backtest/`, `argus/core/`, `argus/ui/`, `argus/api/`
- Do NOT modify: strategy YAML sections other than `backtest_summary`
- Do NOT change strategy parameters unless divergence analysis conclusively warrants it AND WFE supports the change
- This is the final session — full test suite in review

## Test Targets
After implementation:
- Existing tests: all must still pass
- No new tests in this session (YAML updates are validated by existing config loading tests)
- Full test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Expected: ~3,023+ tests, all passing

## Definition of Done
- [ ] All 7 strategy YAML `backtest_summary` sections updated with Databento-era metrics
- [ ] Validation report at `docs/sprints/sprint-21.6/validation-report.md` is complete
- [ ] Report includes per-strategy comparison tables and overall assessment
- [ ] DEC-132 resolution status documented
- [ ] All existing tests still pass (full suite)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent (FINAL SESSION — full suite)

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Only backtest_summary sections changed in YAMLs | `git diff config/strategies/` — verify no changes outside `backtest_summary:` blocks |
| All 7 YAMLs are valid | `python -c "from argus.core.config import load_yaml_file; [load_yaml_file(f'config/strategies/{s}.yaml') for s in ['orb_breakout','orb_scalp','vwap_reclaim','afternoon_momentum','red_to_green','bull_flag','flat_top_breakout']]"` |
| No strategy .py files modified | `git diff argus/strategies/` is empty |
| No backtest .py files modified | `git diff argus/backtest/` is empty |
| Validation report exists | `test -f docs/sprints/sprint-21.6/validation-report.md` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-21.6/session-4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent) — FINAL SESSION
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-21.6/review-context.md`
2. The close-out report path: `docs/sprints/sprint-21.6/session-4-closeout.md`
3. The diff range: `git diff HEAD~3` (covers all Sprint 21.6 changes)
4. The test command (FINAL SESSION — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified: any `.py` file in `argus/strategies/`, `argus/backtest/`, `argus/core/`, `argus/ui/`, `argus/api/`

The @reviewer will write its report to:
`docs/sprints/sprint-21.6/session-4-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings, update both files per the protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify ONLY `backtest_summary` sections changed in strategy YAMLs — no operating parameters, risk limits, or universe filters modified (unless explicitly justified in the validation report)
2. Verify all 7 YAML files load successfully with their respective Pydantic config models
3. Verify validation report has a per-strategy section for all 7 strategies
4. Verify DEC-132 resolution status is documented
5. Verify no source code files were modified (only YAML configs and markdown report)
6. Full test suite passes (this is the final session)

## Sprint-Level Regression Checklist
*(See `docs/sprints/sprint-21.6/review-context.md`)*

## Sprint-Level Escalation Criteria
*(See `docs/sprints/sprint-21.6/review-context.md`)*

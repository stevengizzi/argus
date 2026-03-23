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
Analyze all 7 validation result JSONs from the 28-symbol Databento OHLCV-1m backtest. Update all strategy YAML `backtest_summary` sections. Produce the validation comparison report with full context on the small-universe limitation. Document DEC-132 resolution as partial.

## Known Context (from Human Step)
The results were produced with a **28-symbol curated universe** (from `config/backtest_universe.yaml`), not the full 3,000–4,000 symbol production universe. This fundamentally constrains the results:
- Strategies dependent on scanner selectivity (ORB, AfMo, R2G) are tested without their key edge — daily selection from thousands of candidates
- Trade counts, Sharpe ratios, and WFE values are NOT production-representative
- The primary value is proving the BacktestEngine pipeline works end-to-end with Databento data

**Actual results:**

| Strategy | Status | Trades | Win Rate | PF | Sharpe | WFE PnL |
|----------|--------|--------|----------|------|--------|---------|
| ORB Breakout | WFE_BELOW_THRESHOLD | 290 | 47.1% | 0.77 | -2.62 | -0.27 |
| ORB Scalp | WFE_BELOW_THRESHOLD | 390 | 47.1% | 0.71 | -5.33 | -0.35 |
| VWAP Reclaim | DIVERGENT | 308 | 43.2% | 1.08 | -1.16 | 1.08 |
| Afternoon Momentum | ZERO_TRADES | 0 | — | — | — | 0.00 |
| Red to Green | ZERO_TRADES | 0 | — | — | — | — |
| Bull Flag | NEW_BASELINE | 40 | 57.5% | 1.55 | 2.78 | — |
| Flat Top Breakout | NEW_BASELINE | 2,444 | 45.4% | 0.77 | -3.97 | — |

## Requirements

### 1. Read all validation result JSONs

Read all 7 JSONs from `data/backtest_runs/validation/`. Parse each and extract: status, new metrics, divergence flags. Cross-reference against the table above.

### 2. Update all 7 strategy YAML `backtest_summary` sections

For each strategy config at `config/strategies/{name}.yaml`, update the `backtest_summary` block using these status categories:

- **`"databento_validated"`** — WFE > 0.3 or genuinely good first baseline. Use for: **Bull Flag** (Sharpe 2.78, 57.5% WR).
- **`"databento_preliminary"`** — Pipeline works, but results are constrained by 28-symbol universe and not production-representative. Use for: **ORB Breakout**, **ORB Scalp**, **VWAP Reclaim**, **Flat Top Breakout**.
- **`"databento_insufficient_data"`** — Zero trades due to small universe, not strategy failure. Use for: **Afternoon Momentum**, **Red to Green**.

Template for each YAML:

```yaml
backtest_summary:
  status: "<status from above>"
  data_source: "databento_ohlcv_1m"
  universe_size: 28
  universe_note: "Curated large-cap universe; full-universe re-validation pending"
  oos_sharpe: <new value or null>
  wfe_pnl: <new value or null>
  total_trades: <new OOS trade count>
  avg_win_rate: <new value or null>
  avg_profit_factor: <new value or null>
  data_range: "2023-04-01 to 2025-03-01"
  data_months: 23
  last_run: "2026-03-23"
  prior_baseline:
    source: "alpaca_provisional"
    oos_sharpe: <old value or null>
    wfe_pnl: <old value or null>
    total_trades: <old value or null>
```

For strategies with `ZERO_TRADES`, set all metric fields to `null`.

**IMPORTANT:** Do NOT modify any other section of the YAML — only `backtest_summary`. Leave `risk_limits`, `operating_window`, `benchmarks`, strategy-specific parameters, `universe_filter` unchanged.

### 3. Create the validation report

Create `docs/sprints/sprint-21.6/validation-report.md` with these sections:

#### a. Header
Sprint 21.6 Validation Report, date, data source (Databento EQUS.MINI OHLCV-1m), date range (2023-04-01 to 2025-03-01), universe (28 symbols from `config/backtest_universe.yaml`).

#### b. Universe Limitation Context
A clear explanation that these results use a 28-symbol curated universe, NOT the full production universe. Explain why:
- Production scanner pulls from 3,000–4,000 symbols via FMP
- ScannerSimulator with 28 symbols loses the selectivity edge — daily watchlists are constrained
- Strategies dependent on gap-based scanner selection (ORB, AfMo, R2G) are most affected
- Results prove pipeline correctness, not production-level performance

#### c. Summary Table
The results table from the Known Context section above.

#### d. Per-Strategy Analysis
For each of the 7 strategies, a section containing:
- Old vs new metric comparison (table with prior baseline from YAML)
- Walk-forward window results summary (if applicable)
- WFE assessment: pass/fail against DEC-047 threshold of 0.3 — but with note that WFE < 0.3 is expected given the small universe
- Universe impact analysis: how much does scanner selectivity matter for this strategy?
- Status assignment rationale
- Recommendation: one of "validated", "re-validate with full universe", "investigate parameters"

Specific per-strategy notes to incorporate:

- **ORB Breakout / ORB Scalp:** Negative Sharpe and WFE are expected — ORB depends on scanner selecting stocks with strong opening range gaps. With 28 pre-selected symbols and all-symbols-fallback, many entries lack setup quality. Recommend: re-validate with full universe.
- **VWAP Reclaim:** WFE of 1.08 is positive (OOS outperformed IS). Negative Sharpe may be absolute performance on 28 symbols, not strategy failure. DIVERGENT flag on Sharpe difference from prior baseline. Recommend: promising, re-validate with full universe.
- **Afternoon Momentum:** Zero trades expected — consolidation breakouts are rare events even in 4,000-symbol universe. 28 symbols produces near-zero opportunities. Recommend: re-validate with full universe, not a strategy concern.
- **Red to Green:** Zero trades expected — gap-down reversals on 28 large-cap symbols over 23 months ≈ zero opportunities. BacktestEngine-only path (no WFE). Recommend: re-validate with full universe.
- **Bull Flag:** 40 trades, 57.5% WR, Sharpe 2.78, PF 1.55. Genuinely good results even on 28 symbols — the pattern detection finds real bull flags in liquid large-caps. First Databento-era baseline. Status: validated.
- **Flat Top Breakout:** 2,444 trades with 45.4% WR and -3.97 Sharpe suggests the detection threshold is too permissive — the pattern fires too often on the 28-symbol universe with all-symbols-fallback. Recommend: investigate detection parameters after full-universe re-validation.

#### e. Escalation Triggers — Acknowledged and Contextualized
Document that the WFE < 0.1 trigger fired for 3 strategies (ORB -0.27, ORB Scalp -0.35, AfMo 0.00). Explain why Tier 3 escalation was NOT pursued:
- Root cause is the 28-symbol universe, not strategy or engine failure
- The BacktestEngine pipeline is proven to work (signals generated, trades executed, metrics computed)
- WFE values on 28 symbols are not indicative of production behavior
- Full-universe re-validation is the correct remediation, not architectural review

#### f. DEC-132 Resolution Status
DEC-132 ("All pre-Databento parameter optimization requires re-validation") is **PARTIALLY RESOLVED**:
- Pipeline proven: BacktestEngine + walk-forward + Databento OHLCV-1m data works end-to-end ✅
- Bull Flag validated with first Databento-era baseline ✅
- Remaining 6 strategies require full-universe re-validation before DEC-132 can be marked fully resolved
- No parameter changes warranted based on current results

#### g. Forward-Compatibility Notes
- Sprint 27.5 will convert these results to `MultiObjectiveResult` format
- Sprint 27.5's `RegimeMetrics` should accommodate multi-dimensional regime vectors (Sprint 27.6)
- ExecutionRecord logging (Sessions 1–2) is now collecting calibration data for Sprint 27.5's slippage model
- Full-universe re-validation will produce metrics suitable for Sprint 28's Learning Loop

#### h. Data Infrastructure Requirements
Document these items for follow-up (from Work Journal tracking):
1. **Full-universe cache population** — 3,000–4,000 symbols × 23+ months needed for production-representative backtesting
2. **Continuous cache maintenance** — no automated process exists; new months and new symbols need manual download
3. **Download optimization** — current sequential approach (~2.5 min/symbol-month) needs parallelization investigation
4. **Storage planning** — estimate disk requirements for full universe; evaluate local vs cloud storage
5. **XNAS.ITCH + XNYS.PILLAR expansion** — 8 years of history available at $0 (DEC-358), needs HistoricalDataFeed mode addition (~0.5 session, currently scoped for Sprint 33.5)
6. **Roadmap prioritization** — should full-universe cache population be a dedicated sprint or background process?
7. **Cache integrity** — interrupted downloads, partial Parquet detection, manifest tracking for reproducibility
8. **Databento API rate limits** — verify concurrency limits before attempting parallel downloads
9. **Cost verification at scale** — $0 confirmed for spot checks; verify for bulk queries across thousands of symbols

#### i. Sprint 21.6 Bug Fixes Applied
Document the bugs discovered and fixed during this sprint:
- **Sprint 21.6.1:** BacktestEngine position sizing gap (`share_count=0` → Risk Manager Check 0 rejection), VectorBT file naming mismatch, symbols auto-detection from cache
- **Sprint 21.6.2:** BacktestEngine risk overrides for single-strategy backtesting (DEC-359 — production risk limits too restrictive for isolated validation)
- **Capital fix:** Increased revalidation script `initial_cash` to $1M for non-binding single-strategy validation
- **Strategy ID mismatch:** `compute_metrics` queried `self._config.strategy_id` instead of `self._strategy.strategy_id`

## Constraints
- Do NOT modify: any strategy `.py` file, any file in `argus/backtest/`, `argus/core/`, `argus/ui/`, `argus/api/`
- Do NOT modify: strategy YAML sections other than `backtest_summary`
- Do NOT change strategy parameters — no divergence analysis warrants parameter changes given the small-universe constraint
- This is the final session — full test suite in review

## Test Targets
After implementation:
- Existing tests: all must still pass
- No new tests in this session (YAML updates validated by existing config loading tests)
- Full test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Expected: ~3,050+ tests, all passing

## Definition of Done
- [ ] All 7 strategy YAML `backtest_summary` sections updated with Databento-era metrics
- [ ] Validation report at `docs/sprints/sprint-21.6/validation-report.md` is complete
- [ ] Report includes per-strategy analysis, universe limitation context, escalation context, DEC-132 status, data infrastructure items, and bug fix documentation
- [ ] All existing tests still pass (full suite)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent (FINAL SESSION — full suite)

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Only backtest_summary sections changed in YAMLs | `git diff config/strategies/` — verify no changes outside `backtest_summary:` blocks |
| All 7 YAMLs are valid and loadable | `python -c "from argus.core.config import load_yaml_file; [load_yaml_file(f'config/strategies/{s}.yaml') for s in ['orb_breakout','orb_scalp','vwap_reclaim','afternoon_momentum','red_to_green','bull_flag','flat_top_breakout']]"` |
| No strategy .py files modified | `git diff argus/strategies/` is empty |
| No backtest .py files modified | `git diff argus/backtest/` is empty |
| Validation report exists and is complete | `test -f docs/sprints/sprint-21.6/validation-report.md` |

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
3. The diff range: `git diff HEAD~1`
4. The test command (FINAL SESSION — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified: any `.py` file in `argus/strategies/`, `argus/backtest/`, `argus/core/`, `argus/ui/`, `argus/api/`

The @reviewer will write its report to:
`docs/sprints/sprint-21.6/session-4-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings, update both files per the protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify ONLY `backtest_summary` sections changed in strategy YAMLs — no operating parameters, risk limits, or universe filters modified
2. Verify all 7 YAML files load successfully with their respective Pydantic config models
3. Verify validation report has a per-strategy section for all 7 strategies
4. Verify DEC-132 resolution status is documented as PARTIAL (not fully resolved)
5. Verify no source code files were modified (only YAML configs and markdown report)
6. Verify the status categories are correctly applied (databento_validated for Bull Flag only, databento_preliminary for strategies with trades, databento_insufficient_data for zero-trade strategies)
7. Full test suite passes (this is the final session)

## Sprint-Level Regression Checklist
*(See `docs/sprints/sprint-21.6/review-context.md`)*

## Sprint-Level Escalation Criteria
*(See `docs/sprints/sprint-21.6/review-context.md`)*
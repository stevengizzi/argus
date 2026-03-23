# Sprint 21.6: Backtest Re-Validation + Execution Logging

## Goal

Re-validate all 7 active strategies using BacktestEngine with Databento OHLCV-1m data, satisfying DEC-132 (all pre-Databento parameter optimization requires re-validation). Additionally, add ExecutionRecord logging to OrderManager per DEC-358 §5.1 to begin collecting slippage calibration data for Sprint 27.5's slippage model.

## Scope

### Deliverables

1. **ExecutionRecord infrastructure** — dataclass, `execution_records` DB table, fire-and-forget logging in OrderManager fill handlers.
2. **Re-validation harness script** — CLI tool (`scripts/revalidate_strategy.py`) that runs BacktestEngine + fixed-parameter walk-forward for any of the 7 strategies, compares results against YAML `backtest_summary` baselines, and outputs structured JSON results.
3. **Strategy re-validation results** — All 7 active strategies validated with Databento OHLCV-1m data (March 2023 – present). Walk-forward with `oos_engine="backtest_engine"`.
4. **Updated strategy YAML configs** — `backtest_summary` sections updated for all 7 strategies with Databento-era metrics. Parameters updated if divergence exceeds thresholds.
5. **Validation comparison report** — `docs/sprints/sprint-21.6/validation-report.md` documenting old vs new metrics per strategy with divergence analysis.

### Acceptance Criteria

1. **ExecutionRecord infrastructure:**
   - `ExecutionRecord` dataclass exists at `argus/execution/execution_record.py` with all fields from DEC-358 §5.1 (order_id, symbol, strategy_id, side, expected_fill_price, expected_slippage_bps, actual_fill_price, actual_slippage_bps, time_of_day, order_size_shares, avg_daily_volume, bid_ask_spread_bps, latency_ms, slippage_vs_model)
   - `execution_records` table exists in `argus/db/schema.sql` with matching columns
   - `DatabaseManager._apply_schema()` creates the table via `CREATE TABLE IF NOT EXISTS`
   - `PendingManagedOrder` carries `expected_fill_price` and `signal_timestamp` fields (set in `on_approved()`)
   - `OrderManager._handle_entry_fill()` creates and persists an `ExecutionRecord` on every entry fill
   - All execution record operations are wrapped in try/except — exceptions are logged at WARNING level, never propagate to disrupt order management
   - 8+ new tests covering: record creation with all fields, DB persistence round-trip, error isolation (DB failure does not break fill handling), nullable fields (bid_ask_spread, latency_ms, avg_daily_volume)

2. **Re-validation harness script:**
   - `scripts/revalidate_strategy.py` exists as a runnable CLI with `--strategy`, `--start`, `--end`, `--output-dir` arguments
   - Supports all 7 strategy types via `StrategyType` enum values
   - Runs fixed-parameter walk-forward using `run_fixed_params_walk_forward()` with `oos_engine="backtest_engine"`
   - Reads current parameters from strategy YAML configs
   - Compares results against `backtest_summary` baseline in the same YAML
   - Outputs structured JSON result file per strategy to `{output-dir}/{strategy_name}_validation.json`
   - Flags divergence when: Sharpe diff > 0.5, OR win rate diff > 10pp, OR profit factor diff > 0.5
   - 5+ new tests covering: config loading, baseline extraction, divergence detection logic

3. **Strategy re-validation results:**
   - JSON result files exist for all 7 strategies
   - Every strategy that had prior walk-forward results shows a comparison
   - Strategies with `status: "exploration"` (Bull Flag, Flat-Top Breakout) get their first Databento-era results
   - Walk-forward validation run for all strategies; WFE computed for each

4. **Updated strategy YAML configs:**
   - All 7 configs have `backtest_summary` sections updated with: `status`, `data_source: "databento_ohlcv_1m"`, `oos_sharpe`, `wfe_pnl`, `total_trades`, `data_months`, `last_run`
   - If any strategy's parameters were changed: old and new values documented in validation report, rationale provided

5. **Validation comparison report:**
   - Markdown report at `docs/sprints/sprint-21.6/validation-report.md`
   - Per-strategy table: old metrics | new metrics | divergence | status (VALIDATED / DIVERGENT / NEW)
   - Summary section with overall validation assessment
   - Forward-compatibility notes for Sprint 27.5

### Performance Benchmarks

Not applicable — this is a validation sprint, not a performance sprint. BacktestEngine runtime is data-dependent (~5-30 min per strategy depending on trade frequency and date range).

### Config Changes

No new config fields. Existing `backtest_summary` values in 7 strategy YAMLs are updated with new metric values. No Pydantic model changes.

## Dependencies

- BacktestEngine (Sprint 27) — ✅ Complete
- Walk-forward with `oos_engine="backtest_engine"` (Sprint 27) — ✅ Integrated
- Databento OHLCV-1m available at $0 via XNAS.ITCH + XNYS.PILLAR (DEC-358) — ✅ Confirmed
- Databento API key configured in environment for historical data downloads
- `HistoricalDataFeed` Parquet caching operational (Sprint 27)

## Relevant Decisions

- **DEC-132:** All pre-Databento parameter optimization requires re-validation — this sprint's raison d'être
- **DEC-047:** Walk-forward validation mandatory, WFE > 0.3 — validation gate for every strategy
- **DEC-358 §5.1:** ExecutionRecord spec and Sprint 21.6 execution logging scope
- **DEC-353:** Historical data purchase deferred — free OHLCV-1m confirmed on Standard plan
- **DEC-354:** Phase 6 compression — BacktestEngine pulled to Sprint 27 (prerequisite)
- **DEC-054:** Fixed slippage model ($0.01/share) — current BacktestEngine default, unchanged

## Relevant Risks

- **RSK-DATA-01 (new):** Strategy may produce zero trades with Databento data if scanner simulation doesn't match Databento symbol universe. Mitigation: `scanner_fallback_all_symbols=True` is the default. If zero trades persist, investigate symbol filtering.
- **RSK-VAL-01 (new):** WFE < 0.3 for one or more strategies on Databento data. Mitigation: Document the failure, don't auto-suspend. Proceed with full re-optimization in a follow-up if needed.

## Forward-Compatibility Notes

- Sprint 27.5's `RegimeMetrics` should be designed to accommodate multi-dimensional regime vectors (Sprint 27.6's RegimeVector). No implementation in 21.6 — flagged as a design-time note for 27.5 planning.
- Sprint 21.6's BacktestEngine results will be retroactively structured into `MultiObjectiveResult` format by Sprint 27.5. This sprint's JSON outputs capture the raw metrics needed for that conversion.
- ExecutionRecord fields are a superset of what Sprint 27.5 needs. The `slippage_vs_model` field defaults to 0.0 until a calibrated model exists.

## DEC/DEF Reservations

- **DEC range:** 359–361 (3 reserved — minimal, this is primarily a validation sprint). If used, Sprint 27.5's range shifts from 359–368 to 362–371.
- **DEF range:** DEF-090–091 (2 reserved for any deferred items discovered during validation)

## Session Count Estimate

3 Claude Code sessions + 1 human-executed data collection step. Estimated ~2 days total including backtest run time.
- Session 1: ExecutionRecord infrastructure (~1h)
- Session 2: Re-validation harness script + tests (~1h)
- Human step: Run backtests for all 7 strategies (~2-8h depending on data cache state)
- Session 3: Results analysis + YAML updates + validation report (~1h)

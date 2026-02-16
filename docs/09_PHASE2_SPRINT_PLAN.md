# ARGUS — Phase 2 Sprint Plan (Backtesting Validation)

> *Version 1.0 | February 16, 2026*
> *This is the canonical plan for Phase 2 (Backtesting Validation). It follows the same conventions as `07_PHASE1_SPRINT_PLAN.md`. If reality diverges from this plan, update the plan — don't operate from memory.*

---

## Phase 2 Goal

Validate the ORB Breakout strategy against historical data. Confirm that the strategy logic implemented in Phase 1 produces sensible results on past market data before risking real capital. Deliver three capabilities:

1. **Replay Harness:** Feed historical Parquet data through the production Event Bus, Strategy, Risk Manager, and (simulated) Order Manager. The most trustworthy backtest because it runs your actual code.
2. **VectorBT Parameter Sweeps:** Fast vectorized exploration of parameter sensitivity (opening range duration, confirmation thresholds, profit targets, stop placement). Not a full simulation — an approximation for directional guidance.
3. **Analysis & Reporting Tooling:** Scripts and notebooks to visualize backtest results, compute performance metrics, detect overfitting risk, and produce a formal parameter validation report.

**Exit criteria for Phase 2:**
- Replay Harness produces a trade log for 6+ months of historical data that matches what the strategy *should* have done (verified by manual spot-check of 20+ trades against charts)
- VectorBT parameter sweeps identify the sensitivity of key parameters (which matter most, which are stable)
- Walk-forward analysis shows the strategy doesn't catastrophically degrade on out-of-sample data
- A written Parameter Validation Report documents findings and recommended parameter values for Phase 3 live trading

**Non-goals:**
- Achieving a specific win rate or profit factor (we're validating, not optimizing for a number)
- Backtrader integration (dropped — see rationale below)
- Live trading or real money decisions

---

## Architectural Decisions for Phase 2

### Why No Backtrader

The original plan called for three backtesting layers: VectorBT, Backtrader, and the Replay Harness. Backtrader has been dropped because:

1. The Replay Harness runs your *actual production code* — same Event Bus, same OrbBreakout strategy, same Risk Manager. There's zero translation gap. Backtrader would require reimplementing the strategy as a Backtrader Strategy subclass, creating a parallel implementation that could diverge from production.
2. VectorBT covers the "fast parameter exploration" use case that Backtrader partially served.
3. The engineering effort for Backtrader integration (adapter layer, data feed translation, result extraction) provides no unique value that the Replay Harness + VectorBT combination doesn't cover.

If the Replay Harness proves too slow for iterative parameter work (unlikely for 6–12 months of 1-minute data on a single strategy), we'll reassess. Tracked as a contingency, not a planned sprint.

### Data Strategy

Historical 1-minute bar data for US equities is required. Sources:

- **Alpaca Historical Data API** (free tier with account): Provides 1-minute bars. The free plan has rate limits but is sufficient for batch downloads. This is the primary source.
- **Polygon.io** (fallback): If Alpaca's free tier depth or rate limits are insufficient, Polygon.io offers deep historical data. The basic plan ($29/month, pay for one month) provides 5+ years of 1-minute data. Decision deferred to Sprint 1 — try Alpaca first.

Data is stored as Parquet files (DEC-038), one file per symbol per date range. The ReplayDataService from Sprint 3 already reads Parquet.

### Overfitting Defense: Walk-Forward Analysis

This is non-negotiable. Every parameter optimization must use walk-forward validation:

1. **In-sample period:** Train/optimize parameters on months 1–N.
2. **Out-of-sample period:** Test those parameters on months N+1 to N+M (data the optimizer never saw).
3. **Roll forward:** Slide the window and repeat.

If performance degrades sharply on out-of-sample data, the parameters are overfit. We report this honestly rather than hiding it.

Minimum split: 70% in-sample / 30% out-of-sample. For 12 months of data, that's 8 months optimize, 4 months validate.

### Directory Structure

```
argus/
├── backtest/
│   ├── __init__.py
│   ├── data_fetcher.py       # Historical data download from Alpaca/Polygon
│   ├── replay_harness.py     # Feeds Parquet through production pipeline
│   ├── vectorbt_orb.py       # VectorBT ORB parameter sweeps
│   ├── metrics.py            # Performance metric calculations
│   ├── walk_forward.py       # Walk-forward analysis framework
│   └── report_generator.py   # Generate HTML/PDF validation reports
├── data/
│   └── historical/           # Downloaded Parquet files (gitignored)
│       ├── manifest.json     # Tracks what's been downloaded
│       └── 1m/               # 1-minute bars
│           ├── AAPL/
│           │   ├── AAPL_2025-03.parquet
│           │   ├── AAPL_2025-04.parquet
│           │   └── ...
│           ├── TSLA/
│           │   └── ...
│           └── ...
├── docs/
│   └── backtesting/
│       ├── DATA_INVENTORY.md     # What data we have, source, date ranges
│       ├── BACKTEST_RUN_LOG.md   # Log of every backtest run with parameters and results
│       └── PARAMETER_VALIDATION_REPORT.md  # Final findings (Phase 2 deliverable)
└── tests/
    └── test_backtest/
        ├── test_data_fetcher.py
        ├── test_replay_harness.py
        ├── test_vectorbt_orb.py
        ├── test_metrics.py
        └── test_walk_forward.py
```

---

## Sprint Overview

| Sprint | Scope | Estimated Duration | Dependencies |
|--------|-------|--------------------|--------------|
| 6 | Historical Data Acquisition | 1 day | Alpaca account (already have) |
| 7 | Replay Harness | 1–2 days | Sprint 6 data |
| 8 | VectorBT Parameter Sweeps (6 params, 18K combos/symbol) | 1–2 days | Sprint 6 data, pre-sprint harness fixes |
| 9 | Walk-Forward + Analysis Tooling | 1–2 days | Sprints 7 and 8 |
| 10 | Parameter Validation Report | 1 day (analysis-mode, not build-mode) | Sprints 7, 8, 9 |

**Total estimated build time:** 5–8 days.
**Total calendar time:** Runs in parallel with paper trading validation, so 1–2 weeks wall clock.

Sprint numbers continue from Phase 1 (which ended at Sprint 5) to maintain a single sequence.

---

## Sprint Details

### Sprint 6 — Historical Data Acquisition ✅ COMPLETE
**Tests:** 55 new (417 total)
**Data:** 28 symbols × 11 months (March 2025 – January 2026), 2,231,905 bars, 52 MB

**Goal:** Download and store 6–12 months of 1-minute bar data for a universe of liquid US stocks. Build the tooling to make future downloads easy and track what you have.

**Delivered:**

- **DataFetcher** (`argus/backtest/data_fetcher.py`): Async download from Alpaca `StockHistoricalDataClient.get_stock_bars()`, rate limiting (150 req/min sliding window), retry on 429, saves as Parquet, manifest tracking, resume capability, CLI with `--symbols`, `--start`, `--end`, `--force`.
- **DataFetcherConfig** (`argus/backtest/config.py`): Pydantic model for storage, rate limits, adjustment, feed.
- **Manifest** (`argus/backtest/manifest.py`): `Manifest` + `SymbolMonthEntry` dataclasses with JSON save/load, resume detection, data inventory queries.
- **Data Validator** (`argus/backtest/data_validator.py`): 5-point quality checks — OHLC consistency, zero-volume bars, timestamp timezone, duplicate timestamps, missing trading days.
- **Symbol Universe** (`config/backtest_universe.yaml`): 28 active symbols (SQ removed — no IEX coverage; PYPL replacement pending).
- **Data Inventory** (`docs/backtesting/DATA_INVENTORY.md`): Updated with actual download results.

**Micro-decisions resolved:**
- MD-6-1: Per-symbol-per-month Parquet files. Path: `data/historical/1m/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet` (DEC-048)
- MD-6-2: 150 req/min throttle on Alpaca free tier (200 limit). Full download completes in ~10 minutes for 28 symbols × 11 months (DEC-051)
- MD-6-3: Split-adjusted prices via `Adjustment.SPLIT`. No dividend adjustment for intraday strategies (DEC-050)
- MD-6-4: Store timestamps in UTC. Convert to ET at read time in consumers (DEC-049)

**Data quality notes:**
- March 10, 2025 missing for all symbols — IEX feed gap (minor impact, one trading day)
- SQ returned no data (IEX doesn't cover this ticker). Removed from universe. Replaced with PYPL.
- alpaca-py `BarSet.__contains__` bug: `symbol in bars` returns False even when data exists. Fixed by using `bars.df` property instead. Note: `alpaca_data_service.py` line 317 has the same pattern (`if symbol not in bars:`) — latent bug to investigate on paper trading track.

**After this sprint:** `data/historical/` contains 308 Parquet files covering 28 symbols × 11 months of validated 1-minute bar data, with manifest tracking and quality report.

---

### Sprint 7 — Replay Harness ✅ COMPLETE
**Tests:** 56 new (473 total)

**Goal:** Build the Replay Harness that feeds historical Parquet data through the production trading pipeline. This is the highest-fidelity backtest — it runs your actual code with simulated time.

**Scope:**

- **ReplayHarness** (`argus/backtest/replay_harness.py`):
  - Orchestrates a complete backtest run using production components:
    - EventBus (real)
    - FixedClock (injected, advancing with each bar)
    - ReplayDataService (already built in Sprint 3 — reads Parquet, publishes CandleEvents)
    - OrbBreakoutStrategy (real production code)
    - RiskManager (real, with SimulatedBroker)
    - SimulatedBroker (real, from Sprint 2)
    - OrderManager (real production code — but may need modifications, see below)
    - TradeLogger (real, writing to a separate backtest database)
  - **Clock advancing:** The FixedClock advances with each bar timestamp. All components that use `clock.now()` see the simulated time. This is why we invested in clock injection.
  - **Daily lifecycle:** For each trading day in the data:
    1. Reset strategy state (`reset_daily_state()`)
    2. Reset Risk Manager daily state
    3. Feed the day's bars through the pipeline in order
    4. Force EOD flatten at 3:50 PM ET (simulated)
    5. Log daily summary
  - **Scanner simulation:** Since we can't run the pre-market scanner against historical data (we don't have pre-market data in our Parquet files), the harness either:
    - (a) Uses a pre-computed watchlist per day (derived from gap data if available), OR
    - (b) Feeds ALL symbols in the universe and lets the strategy decide which ones to watch based on early price action.
    - Decision: MD-7-1.
  - **Output:** A separate SQLite database per backtest run (`data/backtest_runs/run_YYYYMMDD_HHMMSS.db`) with the same schema as the production database. This means all existing SQL queries for analyzing trades work on backtest output.
  - **Configuration:** Takes a config override dict so you can run the same harness with different parameters without modifying YAML files.
  - **CLI:** `python -m argus.backtest.replay_harness --data-dir data/historical/1m --start 2025-06-01 --end 2025-12-31 --config-override '{"orb_breakout": {"opening_range_minutes": 15}}'`

- **Order Manager Adaptation:**
  - The production Order Manager is tick-driven (subscribes to TickEvents). In replay mode, we only have 1-minute bars, not tick data.
  - Two options:
    - (a) Synthesize TickEvents from each bar's OHLC (simulate intra-bar price path: open → high → low → close, or open → low → high → close depending on close vs open direction). This lets the Order Manager work unmodified.
    - (b) Create a simplified replay-mode Order Manager that evaluates exits on each bar close using bar high/low to determine if stops or targets were hit.
  - Decision: MD-7-2. Leaning toward (a) — synthetic ticks from bars — because it tests the actual Order Manager code.

- **Metrics Calculation** (`argus/backtest/metrics.py`):
  - Compute standard backtest metrics from the trade log:
    - Total trades, win rate, loss rate
    - Profit factor (gross wins / gross losses)
    - Average R-multiple per trade
    - Maximum drawdown (peak-to-trough equity decline)
    - Sharpe ratio (annualized, using daily returns)
    - Average hold duration
    - Largest win, largest loss
    - Consecutive wins/losses (max streak)
    - Profit by time of day (are ORB trades better at 9:45 vs 10:30?)
    - Profit by day of week
    - Recovery factor (net profit / max drawdown)

**Micro-decisions resolved:**
- MD-7-1: Scanner simulation via gap computation from prev_close → day_open. Apply gap/price filters; fall back to all symbols (with price filter still applied) if no gaps pass (DEC-052).
- MD-7-2: Synthetic ticks from bars — 4 ticks per bar: O→L→H→C (bullish) or O→H→L→C (bearish). Tests actual Order Manager code (DEC-053).
- MD-7-3: No special handling — strategy's `on_candle()` accumulates OR bars naturally when fed in timestamp order.
- MD-7-4: Fixed $0.01/share slippage, configured via `BacktestConfig.slippage_per_share` (DEC-054).
- MD-7-5: Database naming: `data/backtest_runs/{strategy}_{start}_{end}_{timestamp}.db` (DEC-056).
- MD-7-6: New BacktestDataService (step-driven) reusing IndicatorState from ReplayDataService (DEC-055).
- MD-7-7: Harness publishes OrderFilledEvents after calling `simulate_price_update()`. SimulatedBroker unchanged.
- MD-7-8: Pre-market data gap deferred (DEF-007). IEX feed only provides regular hours.

**Delivered:**
- **BacktestConfig** (`argus/backtest/config.py`): Extended with date range, slippage, scanner settings, config_overrides.
- **TickSynthesizer** (`argus/backtest/tick_synthesizer.py`): `SyntheticTick` dataclass + `synthesize_ticks()` function. 7 tests.
- **ScannerSimulator** (`argus/backtest/scanner_simulator.py`): `DailyWatchlist` dataclass + `ScannerSimulator` class with `compute_watchlists()`. 10 tests.
- **BacktestDataService** (`argus/backtest/backtest_data_service.py`): Step-driven DataService ABC implementation. Reuses `IndicatorState` from `replay_data_service.py`. Methods: `feed_bar()`, `publish_tick()`, `reset_daily_state()`. 13 tests.
- **BacktestMetrics** (`argus/backtest/metrics.py`): `BacktestResult` dataclass + `compute_metrics()`, `compute_sharpe_ratio()`, `compute_max_drawdown()`. 12 tests.
- **ReplayHarness** (`argus/backtest/replay_harness.py`): Main orchestrator with `run()`, `_load_data()`, `_setup()`, `_run_trading_day()`, `_process_bracket_triggers()`. CLI entry point with argparse. 10 tests.
- **Test fixtures** (`tests/backtest/conftest.py`): Synthetic Parquet generators for harness tests.

**After this sprint:** `python -m argus.backtest.replay_harness --start 2025-06-01 --end 2025-12-31` runs the complete production pipeline on historical data and outputs a SQLite database with the same schema as production. All existing SQL queries work on backtest output.

---

### Sprint 8 — VectorBT Parameter Sweeps ✅ COMPLETE
**Tests:** 22 new (510 total)

**Goal:** Build fast parameter exploration tooling using vectorized operations. This is an approximation — it won't match the Replay Harness exactly, but it can test thousands of parameter combinations in minutes instead of hours.

**Pre-Sprint Fixes (completed before spec):**
- **Timezone bug (DEC-061):** OrbBreakout compared UTC time against ET constants, preventing OR formation. Fixed. 8 regression tests added. 481 → 483 tests.
- **Fill price bug:** SimulatedBroker used `limit_price or 0.0` for market orders, giving $0.01 fills. Fixed with `_current_prices` cache + `set_price()`. 2 tests added. 483 → 485 tests.
- **Trade logging bug:** Order Manager waited for async `OrderFilledEvent` that SimulatedBroker never published. Fixed with synchronous fill detection. 485 tests.
- **Data integrity:** Stop price recorded final (moved) stop instead of original. P&L calculation incorrect for partial exits. Fixed with `original_stop_price` field and weighted average exit. 5 tests added. 485 → 488 tests.
- **strategy_id mismatch:** BacktestConfig default didn't match YAML. Aligned. 488 tests.

**7-Month Harness Validation (gate check):**
- Default params: 5 trades in 148 days. `max_range_atr_ratio` (default ~2.0) rejected 98.5% of ORs.
- Relaxed params (5.0): 59 trades. Confirmed `max_range_atr_ratio` is the dominant parameter.

**Delivered:**

- **VectorBT ORB Implementation** (`argus/backtest/vectorbt_orb.py`):
  - Pure NumPy/Pandas implementation (VectorBT had numba/coverage compatibility issues, used fallback per MD-8-1)
  - Simplified ORB logic (no VWAP, no volume filter, no T1/T2 split) for fast parameter exploration
  - **6 parameters, 18,000 combinations per symbol:**
    - `opening_range_minutes`: [5, 10, 15, 20, 30]
    - `profit_target_r`: [1.0, 1.5, 2.0, 2.5, 3.0]
    - `stop_buffer_pct`: [0.0, 0.1, 0.2, 0.5]
    - `max_hold_minutes`: [15, 30, 45, 60, 90, 120]
    - `min_gap_pct`: [1.0, 1.5, 2.0, 3.0, 5.0]
    - `max_range_atr_ratio`: [0.3, 0.5, 0.75, 1.0, 1.5, 999.0] (updated from [2.0–8.0] per DEC-065)
  - Core functions: `load_symbol_data()`, `compute_atr()`, `compute_qualifying_days()`, `compute_opening_ranges()`, `run_single_symbol_sweep()`, `run_sweep()`
  - Output: Per-symbol Parquet + cross-symbol summary Parquet (`sweep_summary.parquet`)

- **Heatmap & Visualization** (`generate_heatmaps()`):
  - Static heatmaps (matplotlib + seaborn, PNG) in `static/` subdirectory
  - Interactive heatmaps (plotly, HTML) in `interactive/` subdirectory
  - 15 parameter pairs × 2 formats = 30 heatmaps per symbol subset
  - Default: top 5 symbols by trade count + aggregate; `--all-symbols` for all 28

- **CLI:** `python -m argus.backtest.vectorbt_orb --data-dir data/historical/1m --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31 --output-dir data/backtest_runs/sweeps`

- **Tests** (`tests/backtest/test_vectorbt_orb.py`): 22 tests covering data loading, ATR computation, gap filtering, OR computation, breakout detection, sweep logic, heatmap generation, and CLI.

**Performance (final):**
- Full sweep: 29 symbols × 18K combos = 522K combinations in **53 seconds** (M1 MacBook Pro)
- ATR gradient: 0.3 → 25%, 0.5 → 65%, 0.75 → 84%, 1.0 → 89%, 1.5 → 92%, 999.0 → 100%
- 513 tests passing, ruff clean

**Micro-decisions (all resolved):**
- MD-8-1: VectorBT open-source attempted; fell back to pure NumPy/Pandas due to numba/coverage compatibility (DEC-057)
- MD-8-2: Gap scan pre-filter, same logic as ScannerSimulator (DEC-058)
- MD-8-3: Per-symbol sweeps then aggregate cross-symbol (DEC-059)
- MD-8-4: Dual visualization — static PNG + interactive HTML (DEC-060)
- MD-8-5: `max_range_atr_ratio` as 6th sweep parameter (DEC-062)

**Deferred to Sprint 9:**
- Cross-validation of VectorBT results against Replay Harness (compare trade counts for matching parameters on one symbol)
- Removal of `_simulate_trades_for_day_slow()` legacy function (kept for diff-testing reference)

**After this sprint:** You have heatmaps showing which ORB parameters are robust and which are fragile. You know whether a 15-minute opening range is clearly better than 10 or 20, or whether it doesn't matter much. You know the optimal `max_range_atr_ratio` range for trade volume vs quality tradeoff. This informs which parameters to "lock in" vs which to keep experimenting with.

---

### Sprint 9 — Walk-Forward Analysis + Reporting ✅ COMPLETE
**Tests:** 28 new (541 total)

**Goal:** Build the walk-forward framework to test for overfitting, and build the reporting tooling that generates the final Parameter Validation Report.

**Delivered:**

- **Walk-Forward Engine** (`argus/backtest/walk_forward.py`):
  - `WalkForwardConfig` dataclass with IS/OOS periods, step size, optimization metric, min_trades floor
  - `WindowResult` and `WalkForwardResult` dataclasses for structured output
  - `compute_windows()` — generates rolling IS/OOS date ranges
  - `optimize_in_sample()` — runs VectorBT sweep, selects best params by Sharpe with min_trades floor
  - `validate_out_of_sample()` — runs Replay Harness with selected params
  - `compute_wfe()` — Walk-Forward Efficiency calculation (OOS Sharpe / IS Sharpe)
  - `compute_parameter_stability()` — mode and consistency analysis across windows
  - `run_walk_forward()` — full orchestration with JSON output
  - `cross_validate_single_symbol()` — DEF-009 resolution, compares VectorBT vs Replay trade counts
  - CLI entry point with argparse
  - 14 tests

- **Report Generator** (`argus/backtest/report_generator.py`):
  - `ReportConfig` dataclass supporting multiple data sources (replay DB, sweep dir, walk-forward dir)
  - Modular section generators: `generate_equity_curve()`, `generate_monthly_table()`, `generate_trade_distribution()`, `generate_time_analysis()`, `generate_parameter_sensitivity()`, `generate_walk_forward_section()`, `generate_trade_tables()`
  - Uses Plotly for interactive charts embedded in HTML
  - Self-contained HTML output with inline CSS
  - CLI: `python -m argus.backtest.report_generator --db data/backtest_runs/run_xxx.db --output reports/orb_validation.html`
  - 14 tests

- **DEF-009 Resolved:** Cross-validation function implemented. VectorBT >= Replay trades = PASS (DEC-069)
- **DEF-010 Resolved:** `_simulate_trades_for_day_slow()` removed from vectorbt_orb.py. Test wrapper uses vectorized functions (DEC-070)

**Micro-decisions resolved:**
- MD-9-1: Sharpe ratio with min_trades floor (default 20) as optimization metric (DEC-066)
- MD-9-2: HTML-only reports, PDF deferred (DEC-067)
- MD-9-3: Plotly primary, matplotlib fallback (DEC-068)

**After this sprint:** The full analysis toolkit is complete. Walk-forward analysis, polished HTML reports, and cross-validation tooling are ready for the analysis phase (Sprint 10).

---

### Sprint 10 — Analysis & Parameter Validation Report ⬜ PENDING
**Estimated tests:** 0 new tests (this is analysis work, not code)

**Goal:** Use the tools built in Sprints 6–9 to actually run backtests, interpret results, tune parameters, and produce the formal Parameter Validation Report.

**This sprint operates in analysis mode, not build mode.** There are no specs or test targets. Instead, it's a structured workflow:

**Step 1: Baseline Backtest**
- Run the Replay Harness with the current production ORB parameters (from `config/orb_breakout.yaml`) on the full dataset.
- Generate the report. This is the "how does the strategy perform as-built?" baseline.
- Manually spot-check 20+ trades against real charts (use TradingView or similar). Do the entries and exits make sense? Are there obvious errors in the replay logic?

**Step 2: Parameter Sensitivity**
- Run VectorBT sweeps across all key parameters.
- Identify which parameters have high sensitivity (small changes = big performance swings) and which are stable.
- Document findings in the backtest run log.

**Step 3: Walk-Forward Validation**
- Run walk-forward analysis with the baseline parameters.
- Run walk-forward analysis with VectorBT's "best" parameters.
- Compare walk-forward efficiency. If the "optimized" parameters show much worse walk-forward efficiency than baseline, you've confirmed overfitting.

**Step 4: Parameter Recommendations**
- Based on Steps 1–3, recommend final parameter values for Phase 3 live trading.
- Prioritize robustness over maximum backtest return.
- Document the reasoning for every parameter choice.

**Step 5: Write the Report**
- Produce `docs/backtesting/PARAMETER_VALIDATION_REPORT.md`
- This document is the formal deliverable of Phase 2. It should contain:
  - Dataset description (symbols, date range, data source)
  - Baseline performance metrics
  - Parameter sensitivity findings
  - Walk-forward validation results
  - Recommended parameter values with justification
  - Known limitations and caveats
  - Risk assessment: what market conditions would this strategy struggle in?
  - Recommendation for Phase 3 live sizing

**After this sprint:** Phase 2 is complete. You have a written, evidence-based case for (or against) proceeding to live trading with the ORB strategy, including specific parameter recommendations and an honest assessment of the strategy's strengths and weaknesses.

---

## What Changed From the Original Phase 2 Plan

| Change | Why |
|--------|-----|
| Backtrader dropped | Replay Harness provides higher-fidelity backtesting with production code. VectorBT covers fast parameter exploration. Backtrader adds engineering cost with no unique value. |
| Explicit walk-forward requirement added | Overfitting defense is the most important aspect of backtesting. Making it a first-class sprint item ensures it's not skipped. |
| Analysis mode (Sprint 10) separated from build mode (Sprints 6–9) | Building tools and using tools require different workflows. Sprint 10 is collaborative analysis between the user and Claude, not spec-driven implementation. |
| Formal Parameter Validation Report added | Phase 2's deliverable isn't code — it's a decision document. Making this explicit prevents the common trap of "we built the tools but never wrote up the findings." |

---

## Post-Phase 2 Transition to Phase 3

Phase 3 (Live Validation) begins when:
1. Paper trading validation is complete (from the parallel track)
2. The Parameter Validation Report is written and its recommendations are incorporated into config
3. The user has consulted with their CPA on capital/risk implications (DEF-004)
4. The user makes an explicit decision to proceed with real capital

Phase 3 will use the same system with these changes:
- Switch from paper to live Alpaca account
- Start with minimum position sizes (e.g., 10–25 shares regardless of what sizing model says)
- Run the Shadow System (paper trading in parallel with live) for comparison
- Minimum 20 trading days before scaling up position sizes

---

*End of Phase 2 Sprint Plan v1.0*
*Update this document when sprint scope changes or sprints complete.*

# Sprint 9 — Walk-Forward Analysis + Reporting — Implementation Spec

> **Version:** 1.0 | **Date:** February 16, 2026
> **Pre-requisites:** Sprint 8 complete (513 tests), Sprint 7 Replay Harness functional, historical data available (28 symbols × 11 months)
> **Starting test count:** 513 | **Target test count:** ~530–535

---

## Goal

Build the walk-forward analysis framework to test for overfitting, and build the reporting tooling that generates polished HTML reports for backtest analysis. Together, these complete Phase 2's analytical toolkit and set the stage for Sprint 10's Parameter Validation Report.

This sprint also resolves two deferred items from Sprint 8:
- **DEF-009:** Cross-validation of VectorBT results against Replay Harness
- **DEF-010:** Removal of `_simulate_trades_for_day_slow()` legacy function

---

## Micro-Decisions (Locked)

| ID | Decision | Rationale | DEC |
|----|----------|-----------|-----|
| MD-9-1 | Sharpe ratio with configurable minimum trade count floor (default 20) as walk-forward IS optimization metric. Parameter sets producing fewer than `min_trades` in IS window are disqualified. | Pure Sharpe can be gamed by rare-but-lucky parameter sets. VectorBT sweep showed as few as 5 trades with tight filters. Hard floor is simpler and more transparent than composite score. | DEC-066 |
| MD-9-2 | HTML-only reports. PDF deferred. | HTML supports interactive Plotly charts, is easier to generate, and sufficient for personal use. PDF adds weasyprint/headless Chrome dependency with no unique value now. | DEC-067 |
| MD-9-3 | Plotly as primary chart library, matplotlib as fallback. | Plotly provides interactive hover tooltips on equity curves and trade markers. Already installed from Sprint 8. Consistent with Sprint 8's dual-output pattern. | DEC-068 |

---

## Deliverable 1: Walk-Forward Engine

### File: `argus/backtest/walk_forward.py`

### Concept

Walk-forward analysis is the overfitting defense. It splits the historical data into rolling windows, optimizes parameters on the in-sample (IS) portion, then tests those parameters on the out-of-sample (OOS) portion that the optimizer never saw. If IS performance is great but OOS performance is terrible, the parameters are overfit.

Key metric: **Walk-Forward Efficiency (WFE)** = OOS Sharpe / IS Sharpe. Per DEC-047, WFE > 0.3 required. Values above 0.5 suggest good generalization.

### Configuration

```python
@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward analysis."""
    # Window sizing
    in_sample_months: int = 4
    out_of_sample_months: int = 2
    step_months: int = 2  # How far to slide the window each iteration
    
    # Data
    data_dir: str = "data/historical/1m"
    symbols: list[str] | None = None  # None = auto-detect from data_dir
    
    # Optimization
    optimization_metric: str = "sharpe"  # What to maximize in IS
    min_trades: int = 20  # Minimum trades to qualify (DEC-066)
    
    # Parameter grid (same as VectorBT sweep)
    or_minutes_values: list[int] = field(default_factory=lambda: [5, 10, 15, 20, 30])
    target_r_values: list[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 2.5, 3.0])
    stop_buffer_values: list[float] = field(default_factory=lambda: [0.0, 0.1, 0.2, 0.5])
    hold_minutes_values: list[int] = field(default_factory=lambda: [15, 30, 45, 60, 90, 120])
    min_gap_values: list[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 3.0, 5.0])
    max_range_atr_values: list[float] = field(default_factory=lambda: [0.3, 0.5, 0.75, 1.0, 1.5, 999.0])
    
    # Output
    output_dir: str = "data/backtest_runs/walk_forward"
    
    # Replay Harness settings (for OOS validation)
    initial_cash: float = 100_000.0
    slippage_per_share: float = 0.01
```

### Data Classes

```python
@dataclass
class WindowResult:
    """Results for a single walk-forward window."""
    window_number: int
    
    # Date ranges
    is_start: date
    is_end: date
    oos_start: date
    oos_end: date
    
    # Best IS parameters (from VectorBT sweep)
    best_params: dict  # e.g., {"or_minutes": 15, "target_r": 2.0, ...}
    
    # IS metrics (from VectorBT sweep with best params)
    is_total_trades: int
    is_win_rate: float
    is_profit_factor: float
    is_sharpe: float
    is_total_pnl: float
    is_max_drawdown: float
    
    # OOS metrics (from Replay Harness with best params)
    oos_total_trades: int
    oos_win_rate: float
    oos_profit_factor: float
    oos_sharpe: float
    oos_total_pnl: float
    oos_max_drawdown: float
    
    # Walk-forward efficiency
    wfe_sharpe: float  # oos_sharpe / is_sharpe (handle div-by-zero)
    wfe_pnl: float  # oos_total_pnl / is_total_pnl (handle div-by-zero)


@dataclass
class WalkForwardResult:
    """Aggregate results across all walk-forward windows."""
    config: WalkForwardConfig
    windows: list[WindowResult]
    
    # Aggregate metrics
    avg_wfe_sharpe: float
    avg_wfe_pnl: float
    parameter_stability: dict  # How much best params vary across windows
    
    # Overall assessment
    total_oos_trades: int
    overall_oos_sharpe: float
    overall_oos_pnl: float
    
    # Timestamps
    run_started: datetime
    run_completed: datetime
    run_duration_seconds: float
```

### Core Functions

```python
def compute_windows(
    data_start: date,
    data_end: date,
    config: WalkForwardConfig,
) -> list[tuple[date, date, date, date]]:
    """
    Compute (is_start, is_end, oos_start, oos_end) tuples for each window.
    
    For 11 months of data (2025-03 to 2026-01) with 4/2/2 config:
    Window 1: IS=Mar-Jun 2025, OOS=Jul-Aug 2025
    Window 2: IS=May-Aug 2025, OOS=Sep-Oct 2025
    Window 3: IS=Jul-Oct 2025, OOS=Nov-Dec 2025
    Window 4: IS=Sep-Dec 2025, OOS=Jan 2026
    
    Returns empty list if data range is too short for even one window.
    """

async def optimize_in_sample(
    is_start: date,
    is_end: date,
    config: WalkForwardConfig,
) -> tuple[dict, dict]:
    """
    Run VectorBT sweep on IS period. Return (best_params, is_metrics).
    
    Uses vectorbt_orb.run_sweep() with the IS date range.
    Selects best parameter set by optimization_metric, subject to min_trades floor.
    
    Returns:
        best_params: dict with keys matching VectorBT parameter names
        is_metrics: dict with sharpe, win_rate, profit_factor, total_pnl, etc.
    
    Raises:
        NoQualifyingParamsError: if no parameter set meets min_trades threshold
    """

async def validate_out_of_sample(
    oos_start: date,
    oos_end: date,
    best_params: dict,
    config: WalkForwardConfig,
) -> dict:
    """
    Run Replay Harness on OOS period with the IS-optimized parameters.
    
    This is the high-fidelity validation: actual production code (OrbBreakout strategy,
    Risk Manager, Order Manager, SimulatedBroker) processes the OOS data.
    
    Translates VectorBT param names to production config:
    - or_minutes → opening_range_minutes
    - target_r → profit_target_r (converted to actual R-multiple for bracket orders)
    - stop_buffer → stop_buffer_pct
    - hold_minutes → max_hold_minutes
    - min_gap → min_gap_pct (in scanner config)
    - max_range_atr → max_range_atr_ratio
    
    Returns dict with: total_trades, win_rate, profit_factor, sharpe, total_pnl,
    max_drawdown, avg_r_multiple, trades list.
    """

async def run_walk_forward(config: WalkForwardConfig) -> WalkForwardResult:
    """
    Execute the full walk-forward analysis.
    
    For each window:
    1. Run VectorBT sweep on IS period
    2. Select best parameters (by optimization_metric, min_trades floor)
    3. Run Replay Harness on OOS period with those parameters
    4. Compute WFE metrics
    
    After all windows:
    5. Compute aggregate metrics
    6. Assess parameter stability (how much do best params vary?)
    7. Save results to output_dir
    
    Logs progress per window. Expected runtime: ~4-8 minutes for 4 windows
    (4 × VectorBT sweep ~53s each + 4 × Replay Harness runs).
    """

def compute_parameter_stability(windows: list[WindowResult]) -> dict:
    """
    Analyze how much the best parameters vary across windows.
    
    For each parameter, compute:
    - values_chosen: list of values selected in each window
    - mode: most frequently chosen value
    - stability_score: fraction of windows that chose the mode
    
    High stability (e.g., or_minutes=15 in 4/4 windows) suggests the parameter
    is robust. Low stability (different value each window) suggests sensitivity
    or overfitting.
    
    Returns: {param_name: {"values": [...], "mode": val, "stability": float}}
    """

def save_walk_forward_results(result: WalkForwardResult, output_dir: str) -> str:
    """
    Save results as JSON + per-window detail CSVs.
    
    Files created:
    - walk_forward_summary.json: WalkForwardResult as JSON
    - walk_forward_windows.csv: One row per window with all metrics
    - walk_forward_params.csv: Best params per window for stability analysis
    
    Returns path to summary JSON.
    """
```

### CLI

```bash
python -m argus.backtest.walk_forward \
    --data-dir data/historical/1m \
    --is-months 4 --oos-months 2 --step-months 2 \
    --min-trades 20 \
    --metric sharpe \
    --output-dir data/backtest_runs/walk_forward \
    --initial-cash 100000
```

### Error Handling

- **NoQualifyingParamsError**: If no parameter set meets `min_trades` in an IS window, log a warning, record the window as "no qualifying params," and continue to the next window. Do not fail the entire run.
- **Replay Harness failures**: If OOS validation fails for a window (e.g., zero trades produced), record OOS metrics as zero/NaN and continue. Log the issue clearly.
- **Data gaps**: If a window's date range has no data for certain symbols, proceed with available symbols. Log which symbols were excluded.

---

## Deliverable 2: Report Generator

### File: `argus/backtest/report_generator.py`

### Concept

Generates a self-contained HTML report that can be opened in any browser. The report aggregates data from Replay Harness runs (SQLite databases), VectorBT sweep results (Parquet files), and walk-forward analysis results (JSON/CSV files).

### Input Sources

The report generator accepts multiple input types and composes sections based on what's available:

```python
@dataclass
class ReportConfig:
    """Configuration for report generation."""
    # Required: at least one of these must be provided
    replay_db_path: str | None = None  # Path to Replay Harness SQLite DB
    sweep_dir: str | None = None  # Path to VectorBT sweep output directory
    walk_forward_dir: str | None = None  # Path to walk-forward results directory
    
    # Report metadata
    strategy_name: str = "ORB Breakout"
    report_title: str | None = None  # Auto-generated if None
    
    # Output
    output_path: str = "reports/orb_validation.html"
    
    # Chart settings
    chart_library: str = "plotly"  # "plotly" or "matplotlib"
    embed_charts: bool = True  # Embed as base64 in HTML (vs separate files)
    chart_height: int = 400
    chart_width: int = 900
```

### Report Sections

The report is modular — sections are included based on available data:

**Section 1: Executive Summary** (always present)
- Report metadata: strategy name, date range, generation timestamp
- Key metrics table: total trades, win rate, profit factor, Sharpe, max drawdown, total P&L
- Overall assessment: one-paragraph summary with traffic-light indicator (green/yellow/red)

**Section 2: Equity Curve** (requires `replay_db_path`)
- Interactive Plotly line chart of cumulative P&L over time
- Drawdown overlay (secondary y-axis or separate panel)
- Hover tooltips showing date, cumulative P&L, drawdown %

**Section 3: Monthly P&L Breakdown** (requires `replay_db_path`)
- HTML table: rows = months, columns = trades, wins, losses, net P&L, win rate
- Color-coded: green for profitable months, red for losing months
- Monthly P&L bar chart

**Section 4: Trade Distribution** (requires `replay_db_path`)
- Histogram of R-multiples (or raw P&L)
- Win/loss distribution overlay
- Key stats: avg winner, avg loser, largest winner, largest loser, expectancy

**Section 5: Time Analysis** (requires `replay_db_path`)
- Average P&L by entry hour (bar chart)
- Average P&L by day of week (bar chart)
- Trade count by hour and day (heatmap)

**Section 6: Parameter Sensitivity** (requires `sweep_dir`)
- Embed or link to VectorBT heatmaps (the interactive HTML ones from Sprint 8)
- Summary table: for each parameter, show the value that maximizes Sharpe across the sweep
- Sensitivity ranking: which parameters have the highest variance in outcomes

**Section 7: Walk-Forward Results** (requires `walk_forward_dir`)
- Table: one row per window showing IS metrics, OOS metrics, WFE
- Chart: IS vs OOS Sharpe per window (grouped bar chart)
- Parameter stability analysis from `compute_parameter_stability()`
- Overall WFE assessment with DEC-047 threshold (0.3 minimum, 0.5 target)

**Section 8: Trade Tables** (requires `replay_db_path`)
- Worst 10 trades: entry time, symbol, entry price, exit price, P&L, R-multiple, exit reason
- Best 10 trades: same columns
- These exist for manual spot-checking against real charts

### Core Functions

```python
def load_replay_data(db_path: str) -> dict:
    """
    Load trade data from Replay Harness SQLite database.
    
    Reads from the trades table (same schema as production).
    Returns dict with:
    - trades: list of trade dicts
    - daily_pnl: list of (date, cumulative_pnl) tuples
    - monthly_summary: list of monthly aggregates
    """

def load_sweep_data(sweep_dir: str) -> dict:
    """
    Load VectorBT sweep results from Parquet files.
    
    Reads cross-symbol summary and per-symbol results.
    Returns dict with:
    - summary_df: cross-symbol aggregated DataFrame
    - heatmap_paths: list of paths to existing heatmap HTML files
    """

def load_walk_forward_data(wf_dir: str) -> WalkForwardResult | None:
    """
    Load walk-forward results from JSON/CSV files.
    Returns WalkForwardResult or None if files don't exist.
    """

def generate_equity_curve(trades: list[dict], config: ReportConfig) -> str:
    """
    Generate equity curve chart.
    Returns: HTML string (embedded Plotly chart) or base64 PNG (matplotlib).
    """

def generate_monthly_table(monthly_data: list[dict]) -> str:
    """Generate HTML table of monthly P&L breakdown."""

def generate_trade_distribution(trades: list[dict], config: ReportConfig) -> str:
    """Generate R-multiple histogram chart. Returns HTML string."""

def generate_time_analysis(trades: list[dict], config: ReportConfig) -> str:
    """Generate time-of-day and day-of-week analysis charts. Returns HTML string."""

def generate_parameter_sensitivity(sweep_data: dict, config: ReportConfig) -> str:
    """
    Generate parameter sensitivity section.
    Embeds existing heatmap HTML files via iframe or links.
    Generates summary sensitivity ranking table.
    """

def generate_walk_forward_section(wf_result: WalkForwardResult, config: ReportConfig) -> str:
    """
    Generate walk-forward analysis section.
    IS vs OOS comparison charts + parameter stability analysis.
    """

def generate_trade_tables(trades: list[dict], n: int = 10) -> str:
    """Generate best/worst trade tables as HTML."""

def generate_report(config: ReportConfig) -> str:
    """
    Main entry point. Loads all available data, generates all applicable sections,
    assembles into a single self-contained HTML file.
    
    Returns path to generated HTML file.
    """
```

### HTML Template Structure

The report uses a simple HTML template with embedded CSS (no external dependencies). Plotly charts are embedded inline. The template should be clean, professional, and printer-friendly.

```html



    {report_title}
    
    
        /* Clean, professional styling */
        body { font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .metric-card { display: inline-block; padding: 15px; margin: 5px; border: 1px solid #ddd; border-radius: 8px; }
        .positive { color: #16a34a; }
        .negative { color: #dc2626; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { padding: 8px 12px; text-align: right; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .section { margin: 40px 0; }
        .section h2 { border-bottom: 2px solid #333; padding-bottom: 8px; }
        @media print { .no-print { display: none; } }
    


    {report_title}
    Generated {timestamp} | Strategy: {strategy_name}
    
    
    ...
    
    
    {sections}


```

### CLI

```bash
# From Replay Harness DB only
python -m argus.backtest.report_generator \
    --db data/backtest_runs/orb_20250601_20251231_20260216.db \
    --output reports/orb_baseline.html

# Full report with all data sources
python -m argus.backtest.report_generator \
    --db data/backtest_runs/orb_20250601_20251231_20260216.db \
    --sweep-dir data/backtest_runs/sweeps \
    --walk-forward-dir data/backtest_runs/walk_forward \
    --output reports/orb_full_validation.html
```

---

## Deliverable 3: DEF-009 Resolution (Cross-Validation)

### What

Pick one symbol (TSLA recommended — good trade volume), run the Replay Harness with `or_minutes=15`, `target_r=2.0`, default other params. Compare trade count against VectorBT sweep results for the same parameter combination.

### Expected Outcome

VectorBT should produce **more** trades than the Replay Harness for the same parameters, because:
- VectorBT uses simplified logic (no volume confirmation, no VWAP filter, no Risk Manager)
- Replay Harness runs full production code with all filters active

If VectorBT produces **fewer** trades, something is wrong and needs investigation before walk-forward analysis is trustworthy.

### Implementation

Add a validation function in `walk_forward.py` (or a standalone script):

```python
async def cross_validate_single_symbol(
    symbol: str,
    start: date,
    end: date,
    params: dict,
    data_dir: str = "data/historical/1m",
) -> dict:
    """
    Run both VectorBT and Replay Harness with identical parameters on one symbol.
    Compare trade counts, directions, and approximate P&L.
    
    Returns comparison dict with trade counts, overlap analysis, and assessment.
    """
```

Add a CLI command or integrate into the walk-forward CLI:

```bash
python -m argus.backtest.walk_forward --cross-validate \
    --symbol TSLA --start 2025-06-01 --end 2025-12-31 \
    --or-minutes 15 --target-r 2.0
```

### Test

One integration test that runs cross-validation on synthetic data and verifies VectorBT trades >= Replay Harness trades.

---

## Deliverable 4: DEF-010 Resolution (Legacy Cleanup)

### What

Remove `_simulate_trades_for_day_slow()` from `vectorbt_orb.py`. This was the pre-vectorization row-by-row implementation kept for diff-testing.

### When

After the cross-validation (DEF-009) confirms the vectorized path is correct. If cross-validation reveals issues, keep the slow path until they're resolved.

### Implementation

- Delete the function
- Remove any imports or references to it
- Update any tests that reference it (there should be a diff-test that compares slow vs fast — this test gets removed)
- Verify all existing tests still pass

---

## Test Plan

### Walk-Forward Engine Tests (`tests/test_backtest/test_walk_forward.py`)

| # | Test | What It Validates |
|---|------|-------------------|
| 1 | `test_compute_windows_basic` | 11 months of data with 4/2/2 config produces 4 windows with correct date ranges |
| 2 | `test_compute_windows_insufficient_data` | Data range too short for one window returns empty list |
| 3 | `test_compute_windows_edge_month_boundaries` | Windows align to month boundaries correctly |
| 4 | `test_compute_windows_custom_config` | Non-default IS/OOS/step values produce correct windows |
| 5 | `test_optimize_in_sample_returns_best` | Given sweep results, selects parameter set with highest Sharpe that meets min_trades |
| 6 | `test_optimize_in_sample_min_trades_filter` | Parameter set with highest Sharpe but <20 trades is skipped; next-best is selected |
| 7 | `test_optimize_in_sample_no_qualifying` | All parameter sets below min_trades raises NoQualifyingParamsError |
| 8 | `test_validate_oos_translates_params` | VectorBT param names correctly mapped to production config names |
| 9 | `test_walk_forward_efficiency_calculation` | WFE = OOS Sharpe / IS Sharpe, handle zero IS Sharpe gracefully |
| 10 | `test_parameter_stability_all_same` | All windows choose same params → stability = 1.0 |
| 11 | `test_parameter_stability_all_different` | Each window chooses different params → low stability score |
| 12 | `test_save_and_load_results` | Save to JSON/CSV, reload, verify round-trip fidelity |
| 13 | `test_cross_validate_vectorbt_ge_replay` | VectorBT trade count >= Replay Harness trade count for same params (DEF-009) |

### Report Generator Tests (`tests/test_backtest/test_report_generator.py`)

| # | Test | What It Validates |
|---|------|-------------------|
| 14 | `test_load_replay_data_from_db` | Reads trades from SQLite, computes daily P&L and monthly summaries |
| 15 | `test_load_replay_data_empty_db` | Empty database returns zero trades, zero P&L |
| 16 | `test_generate_equity_curve_html` | Plotly equity curve renders as valid HTML with chart div |
| 17 | `test_generate_monthly_table` | Monthly table has correct row count, P&L values, color coding |
| 18 | `test_generate_trade_distribution` | Histogram renders, bin counts match trade data |
| 19 | `test_generate_report_replay_only` | Report with only replay DB generates sections 1-5 and 8, skips 6-7 |
| 20 | `test_generate_report_full` | Report with all data sources generates all 8 sections |
| 21 | `test_report_html_valid` | Output HTML is well-formed (no unclosed tags, Plotly script loads) |
| 22 | `test_trade_tables_top_bottom` | Worst/best 10 trades sorted correctly, P&L values match |

**Total new tests: ~22** (target 530-535 total)

---

## Implementation Order

Claude Code should implement in this sequence:

1. `WalkForwardConfig` and `WindowResult`/`WalkForwardResult` dataclasses
2. `compute_windows()` + tests 1-4
3. `optimize_in_sample()` + tests 5-7 (mocks VectorBT sweep, tests selection logic)
4. `validate_out_of_sample()` + test 8 (mocks Replay Harness, tests param translation)
5. WFE calculation + test 9
6. `compute_parameter_stability()` + tests 10-11
7. `save_walk_forward_results()` / load + test 12
8. `run_walk_forward()` (orchestrator function) — integration of steps 3-7
9. Walk-forward CLI (`__main__` block)
10. DEF-009: `cross_validate_single_symbol()` + test 13 + CLI flag
11. DEF-010: Remove `_simulate_trades_for_day_slow()` (only after DEF-009 passes)
12. `ReportConfig` dataclass
13. `load_replay_data()` + tests 14-15
14. `load_sweep_data()` and `load_walk_forward_data()`
15. Report section generators: equity curve, monthly table, trade distribution, time analysis (tests 16-18)
16. Report section generators: parameter sensitivity, walk-forward section
17. `generate_trade_tables()` + test 22
18. `generate_report()` assembler + tests 19-21
19. Report CLI
20. Full test suite pass + ruff clean

---

## Integration Notes

### VectorBT Sweep Integration

The walk-forward engine calls `vectorbt_orb.run_sweep()` (or the equivalent function) for each IS window. This function already exists from Sprint 8. The walk-forward engine:
- Passes the IS date range as `--start` and `--end`
- Reads the output Parquet to find the best parameter set
- No modifications to `vectorbt_orb.py` needed (aside from DEF-010 cleanup)

### Replay Harness Integration

The OOS validation calls the Replay Harness programmatically (not via subprocess). This means importing and calling the harness's Python API:
- Create a temporary config YAML with the IS-optimized parameters
- Instantiate and run the harness for the OOS date range
- Read metrics from the resulting SQLite database
- Clean up temporary config and DB (or keep DB in output_dir for later inspection)

### Report Data Flow

```
VectorBT Sweep (Sprint 8)
    ↓ Parquet files
Report Generator → Parameter Sensitivity Section

Replay Harness (Sprint 7)
    ↓ SQLite database
Report Generator → Sections 1-5, 8 (equity curve, monthly, distribution, time, trades)

Walk-Forward Engine (this sprint)
    ↓ JSON + CSV
Report Generator → Section 7 (walk-forward analysis)
```

---

## What NOT To Build

- **No PDF export** — HTML only (DEC-067)
- **No new parameters in the sweep** — use Sprint 8's existing 6-parameter grid
- **No modifications to production strategy code** — this is analysis tooling
- **No multi-strategy support** — ORB only for now
- **No automated parameter recommendation** — Sprint 10 handles this manually
- **No dashboard/web server** — static HTML files only
- **No new data acquisition** — use existing 28 symbols × 11 months

---

## Definition of Done

1. `argus/backtest/walk_forward.py` implements all functions described above
2. `argus/backtest/report_generator.py` generates self-contained HTML reports
3. Walk-forward CLI works: `python -m argus.backtest.walk_forward --data-dir data/historical/1m --output-dir data/backtest_runs/walk_forward`
4. Report CLI works: `python -m argus.backtest.report_generator --db <path> --output reports/orb_validation.html`
5. Cross-validation (DEF-009) passes: VectorBT trades >= Replay Harness trades for matching params
6. `_simulate_trades_for_day_slow()` removed (DEF-010) — only if DEF-009 confirms vectorized path is correct
7. ~22 new tests passing
8. All existing tests still pass (513 + ~22 = ~535 total)
9. Ruff clean
10. No changes to production strategy code

---

## Notes for Claude Code

- **Plotly CDN**: Use `https://cdn.plot.ly/plotly-latest.min.js` in report HTML. Online fine for V1.
- **Large HTML files**: If report with embedded Plotly exceeds ~10MB, switch to linking charts as separate files.
- **Walk-forward runtime**: Expected ~4–8 minutes for 4 windows. Log progress per window.
- **Replay Harness API**: If no clean programmatic API exists (CLI only), create a thin wrapper. Don't use `subprocess` — import and call Python functions directly.
- **Month boundaries**: Use `dateutil.relativedelta` or manual month arithmetic. Don't assume 30-day months.
- **Timezone awareness**: All dates treated as Eastern Time for trading day boundaries (DEC-061).

---

*End of Sprint 9 Implementation Spec*

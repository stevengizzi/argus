# Sprint 31.75, Session 4: Full-Universe Sweeps (Operational)

> This is NOT a Claude Code session. It uses the infrastructure from S1–S3.

---

## Pre-Launch Checklist

### 1. Symbol Resolution
```bash
python3 scripts/resolve_sweep_symbols.py \
    --all-patterns \
    --cache-dir data/databento_cache \
    --date-range 2025-01-01,2025-12-31 \
    --persist-db data/historical_query.duckdb \
    --output-dir data/sweep_logs
```

**Verify:** Each pattern has hundreds+ symbols (not 24–50). Expected ranges:
| Pattern | Expected Symbols | Notes |
|---------|:----------------:|-------|
| micro_pullback | 800–1,500 | min_avg_volume 500K |
| dip_and_rip | 800–1,500 | min_avg_volume 300K |
| hod_break | 800–1,500 | min_avg_volume 300K |
| abcd | 800–1,500 | min_avg_volume 200K |
| narrow_range_breakout | 800–1,500 | min_avg_volume 300K |
| vwap_bounce | 800–1,500 | min_avg_volume 500K |
| flat_top_breakout | 500–1,000 | stricter filters |
| bull_flag (momentum) | 800–1,500 | min_avg_volume 500K |
| bull_flag (trend) | 500–1,000 | tighter price range |
| gap_and_go | 500–1,000 | min_avg_volume 500K |
| premarket_high_break | 300–800 | needs PM data |

### 2. PMH Pre-Market Coverage Check

```bash
# Check how many resolved PMH symbols have pre-market (4:00–9:30 AM) bars
python3 -c "
from argus.data.historical_query_service import HistoricalQueryService
from argus.data.historical_query_config import HistoricalQueryConfig
svc = HistoricalQueryService(HistoricalQueryConfig(
    enabled=True,
    cache_dir='data/databento_cache',
    persist_db='data/historical_query.duckdb',
))
symbols = open('data/sweep_logs/symbols_premarket_high_break.txt').read().splitlines()
# Sample: check 10 symbols for PM bars
for sym in symbols[:10]:
    df = svc.query(
        'SELECT COUNT(*) AS bars FROM historical WHERE symbol=? AND HOUR(ts_event) < 9',
        [sym]
    )
    print(f'{sym}: {df.iloc[0][\"bars\"]} pre-market bars')
svc.close()
"
```

If <50% of resolved PMH symbols have pre-market data, note this as a data
limitation in S5 analysis. PMH requires pre-market bars for detection.

### 3. Dry Runs (Grid Size Verification)

```bash
for pattern in micro_pullback dip_and_rip hod_break abcd narrow_range_breakout \
               vwap_bounce flat_top_breakout bull_flag gap_and_go premarket_high_break; do
    echo "=== $pattern ==="
    python3 scripts/run_experiment.py \
        --pattern "$pattern" \
        --cache-dir data/databento_cache \
        --symbols "@data/sweep_logs/symbols_${pattern}.txt" \
        --date-range 2025-01-01,2025-12-31 \
        --dry-run
done
```

**Action:** If any grid > 200 points, restrict with `--params` to the 2–3
most impactful parameters. Priority params by pattern:
- micro_pullback: `min_impulse_pct`, `min_impulse_bars`
- dip_and_rip: `dip_min_pct`, `recovery_min_pct`
- hod_break: `consolidation_atr_mult`, `touch_count_min`
- abcd: `fib_b_low`, `fib_b_high` (highest parameterization density)
- vwap_bounce: `min_approach_distance_pct`, `min_bounce_follow_through_bars`, `min_prior_trend_bars`
- flat_top_breakout: `resistance_tolerance_pct`, plus `--exit-sweep-params` for `target_ratio`
- bull_flag: `pole_min_move_pct`, `flag_max_bars`
- gap_and_go: `min_gap_percent`, `min_relative_volume`
- premarket_high_break: `min_gap_percent`, `min_pm_volume`

### 4. Bull Flag Dual Universe

Run bull_flag on BOTH universes:
```bash
# Momentum universe (already confirmed dead on 38-symbol sample)
python3 scripts/run_experiment.py \
    --pattern bull_flag \
    --cache-dir data/databento_cache \
    --symbols "@data/sweep_logs/symbols_bull_flag.txt" \
    --date-range 2025-01-01,2025-12-31 \
    --workers 2 > data/sweep_logs/sweep_bull_flag_momentum.log 2>&1

# Trend-following universe
python3 scripts/run_experiment.py \
    --pattern bull_flag \
    --cache-dir data/databento_cache \
    --symbols "@data/sweep_logs/symbols_bull_flag_trend.txt" \
    --date-range 2025-01-01,2025-12-31 \
    --workers 2 > data/sweep_logs/sweep_bull_flag_trend.log 2>&1
```

(The `resolve_sweep_symbols.py --all-patterns` should have created
`symbols_bull_flag_trend.txt` if the `bull_flag_trend.yaml` filter was picked up
via directory glob. If not, run it separately:
```bash
python3 scripts/resolve_sweep_symbols.py \
    --pattern bull_flag_trend \
    --cache-dir data/databento_cache \
    --date-range 2025-01-01,2025-12-31
```
)

### 5. Flat-Top Exit Axis Sweep

Run flat_top_breakout with exit_sweep_params targeting target_ratio:
```bash
python3 scripts/run_experiment.py \
    --pattern flat_top_breakout \
    --cache-dir data/databento_cache \
    --symbols "@data/sweep_logs/symbols_flat_top_breakout.txt" \
    --date-range 2025-01-01,2025-12-31 \
    --workers 2 > data/sweep_logs/sweep_flat_top_exit.log 2>&1
```
(Ensure `config/experiments.yaml` has `exit_sweep_params` configured for
flat_top_breakout with `target_ratio: [2.0, 2.5, 3.0, 3.5, 4.0]`.)

### 6. Launch Batch

```bash
nohup bash scripts/run_sweep_batch.sh > data/sweep_logs/batch_run.log 2>&1 &
echo $! > data/sweep_logs/batch_pid.txt
```

**Monitor:**
```bash
# Check progress
ls -la data/sweep_logs/*_progress.json

# Check completion
cat data/sweep_logs/batch_complete.json 2>/dev/null || echo "Still running"

# Tail current pattern log
tail -f data/sweep_logs/sweep_*.log
```

**Expected wall-clock time:** 8–16 hours depending on universe sizes and grid
complexity. Each pattern with 800 symbols × 30 grid points ≈ 2–4 hours with
2 workers.

---

# Sprint 31.75, Session 5: Analysis + Variant Promotions

> Manual analysis session. Use Python scripts + SQLite queries + the data
> from S4's overnight runs.

---

## Analysis Framework

### 1. Per-Pattern Summary Table

For each pattern, compile:

| Metric | Source |
|--------|--------|
| Symbol count | `wc -l data/sweep_logs/symbols_{pattern}.txt` |
| Grid size | Count records in experiments.db for this pattern |
| Qualifying configs | Records with `status = 'completed'` |
| Best Sharpe | Max `sharpe_ratio` from `backtest_result` JSON |
| Best avg R | Max `expectancy_per_trade` from `backtest_result` JSON |
| Best win rate | Max `win_rate` from `backtest_result` JSON |
| Total trades | Sum of `total_trades` across qualifying configs |

```python
import sqlite3, json

db = sqlite3.connect("data/experiments.db")
rows = db.execute("""
    SELECT pattern_name, parameter_fingerprint, status,
           backtest_result
    FROM experiment_records
    ORDER BY pattern_name, created_at DESC
""").fetchall()

for pattern in sorted(set(r[0] for r in rows)):
    pattern_rows = [r for r in rows if r[0] == pattern]
    completed = [r for r in pattern_rows if r[2] == 'completed']
    # Parse backtest_result JSON for each...
```

### 2. PMH NVDA Concentration Test

For the top PMH config from S4:
1. Find the fingerprint with the best expectancy
2. Query the per-run DB for that fingerprint
3. Count trades by symbol
4. Calculate NVDA's share of total trades
5. If NVDA > 20%: re-run the same config with `--symbols` excluding NVDA
6. Compare: if avg R drops below 0.10 without NVDA, the pattern is
   NVDA-dependent and not deployable

### 3. Flat-Top target_ratio Verdict

Compare flat_top_breakout results across exit sweep configs:
- Did any target_ratio produce positive expectancy?
- Did higher target_ratio improve or worsen results?
- If no target_ratio works: flat-top is confirmed dead
- If a specific target_ratio works: flat-top is promotable with that exit config

### 4. Bull Flag Universe Comparison

Side-by-side comparison:
| Metric | Momentum Universe | Trend Universe |
|--------|:--:|:--:|
| Symbol count | | |
| Best avg R | | |
| Best win rate | | |
| Qualifying configs | | |

If trend universe shows promise where momentum died: bull flag is alive but
needed a different population. Update the default `bull_flag.yaml` to match
the trend filter criteria.

### 5. Gap-and-Go First Valid Results

With DEF-152 fixed:
- Verify no degenerate R-multiples in the results
- Assess if gap_and_go has genuine edge
- Compare results to the corrupted Apr 3–5 data (should be dramatically different)

### 6. VWAP Bounce Signal Density Verification

With DEF-154 fixed:
- Count signals per symbol per day across the sweep
- Target: 0.5–3 signals/symbol/day (was 2–22 before)
- If still too high: min_approach_distance_pct default needs raising

### 7. Definitive Pattern Verdicts

Update verdicts from "small-sample" to "full-universe":

| Pattern | Verdict | Action |
|---------|---------|--------|
| micro_pullback | (from data) | Update experiments.yaml if new variants qualify |
| premarket_high_break | (from data) | Note NVDA concentration status |
| hod_break | (from data) | Full sweep now (was killed mid-sweep before) |
| abcd | (from data) | Near-zero edge may confirm with more data |
| narrow_range_breakout | (from data) | Was "too selective" — larger universe may help |
| vwap_bounce | (from data) | First valid results with corrected axes |
| flat_top_breakout | (from data) | target_ratio exit axis verdict |
| bull_flag | (from data) | Momentum vs trend comparison |
| gap_and_go | (from data) | First valid results (DEF-152 fixed) |
| dip_and_rip | (from data) | Already has 2 qualifying variants — validate |

### 8. Update experiments.yaml

For all qualifying variants:
- Add to `config/experiments.yaml` with appropriate mode (shadow)
- Include exit_overrides if the qualifying config uses non-default exits
- Document the parameter config and performance metrics in comments

### 9. Write sweep_summary_final.md

Create `data/sweep_logs/sweep_summary_final.md` with:
- Date, symbol counts per pattern, date range
- Full results table (replaces sweep_summary_20260404.md)
- Definitive verdicts per pattern
- NVDA concentration analysis for PMH
- Bull flag universe comparison
- Gap-and-go first valid results
- VWAP Bounce signal density verification
- Recommendations for next sprint (what patterns to invest in vs abandon)
- Key learnings

---

## Post-Sprint: Doc-Sync Prompt

After S5 is complete, generate a doc-sync prompt covering:
1. Sprint history entry for Sprint 31.75 (S1–S5)
2. DEF-152, DEF-153, DEF-154 status → RESOLVED
3. Test count update (should be ~4,880–4,900 pytest, 846 Vitest)
4. Full-universe sweep results (replace small-sample verdicts)
5. New variant promotions in experiments.yaml
6. New scripts: resolve_sweep_symbols.py, run_sweep_batch.sh
7. DuckDB persistence option documented
8. bull_flag_trend.yaml documented
9. Key Learnings from full-universe analysis
10. Build track advancement: sweep impromptu → complete
11. Update "sweep symbol representativeness" active constraint
12. Any new DEFs discovered during S4/S5

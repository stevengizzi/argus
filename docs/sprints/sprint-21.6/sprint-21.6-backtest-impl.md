# Sprint 21.6, Human Step: Run All 7 Strategy Backtests

## Context
You are executing the "Human Step" of Sprint 21.6. Sessions 1–3 are complete. The re-validation harness script (`scripts/revalidate_strategy.py`) is built and tested. Your job is to run it for all 7 strategies, collect the JSON outputs, and report results.

This is NOT a code implementation session. Do NOT modify any source files. You are only running CLI commands and collecting output.

## Pre-Flight Checks
1. Verify the script exists and is runnable:
   ```
   python scripts/revalidate_strategy.py --help
   ```
2. Verify the output directory exists (create if not):
   ```
   mkdir -p data/backtest_runs/validation
   ```
3. Verify Databento API key is set:
   ```
   python -c "import os; key = os.environ.get('DATABENTO_API_KEY', ''); print(f'Key present: {bool(key)}, length: {len(key)}')"
   ```
   If the key is not set, STOP and report. The backtests cannot run without it.
4. Check existing Parquet cache state (this determines runtime):
   ```
   ls data/databento_cache/ 2>/dev/null | head -20 && echo "---" && du -sh data/databento_cache/ 2>/dev/null || echo "No cache directory — first run will download all data"
   ```

## Execution Plan

Run strategies in this exact order. ORB Breakout is first as a smoke test.

**Date range:** 2023-03-01 to 2025-03-01 (24 months of Databento-era data)

### Step 1: Smoke Test — ORB Breakout
```bash
python scripts/revalidate_strategy.py \
  --strategy orb \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

After this completes:
- Check exit code: `echo $?` (must be 0)
- Verify JSON output exists: `ls -la data/backtest_runs/validation/orb*`
- Read the JSON and check for `"status"` — any value other than an error/crash means the harness works
- If this fails, STOP and report the full error. Do not proceed with remaining strategies.

### Step 2: Remaining Walk-Forward Strategies (3)
Run these sequentially. Each one should complete faster than ORB since much of the data will be cached.

```bash
python scripts/revalidate_strategy.py \
  --strategy orb_scalp \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level WARNING
```

```bash
python scripts/revalidate_strategy.py \
  --strategy vwap_reclaim \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level WARNING
```

```bash
python scripts/revalidate_strategy.py \
  --strategy afternoon_momentum \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level WARNING
```

### Step 3: BacktestEngine-Only Strategies (3)
These use the BacktestEngine fallback path (no VectorBT IS evaluation). Watch for `config_overrides` format errors — if these fail with config-related errors, the dotted-path key format in `run_backtest_engine_fallback()` may need adjustment (reviewer finding C-3).

```bash
python scripts/revalidate_strategy.py \
  --strategy red_to_green \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level WARNING
```

```bash
python scripts/revalidate_strategy.py \
  --strategy bull_flag \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level WARNING
```

```bash
python scripts/revalidate_strategy.py \
  --strategy flat_top_breakout \
  --start 2023-03-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level WARNING
```

## After All 7 Complete

1. **List all output files:**
   ```bash
   ls -la data/backtest_runs/validation/*.json
   ```
   Expect 7 JSON files.

2. **Print a summary of each result** (status + key metrics):
   ```bash
   for f in data/backtest_runs/validation/*.json; do
     echo "=== $(basename $f) ==="
     python -c "
   import json, sys
   with open('$f') as fh:
       d = json.load(fh)
   print(f\"  Status: {d.get('status', 'UNKNOWN')}\")
   nr = d.get('new_results', {})
   print(f\"  OOS Sharpe: {nr.get('oos_sharpe', 'N/A')}\")
   print(f\"  WFE PnL: {nr.get('wfe_pnl', 'N/A')}\")
   print(f\"  Total Trades: {nr.get('total_trades', 'N/A')}\")
   print(f\"  Walk-Forward: {d.get('walk_forward_available', 'N/A')}\")
   div = d.get('divergence', {})
   if div:
       for k, v in div.items():
           if v: print(f\"  DIVERGENCE: {k} = {v}\")
   print()
   "
   done
   ```

3. **Check for escalation triggers:**
   - More than 3 strategies with `"status": "ZERO_TRADES"`? → ESCALATE
   - Any strategy with WFE < 0.1? → ESCALATE
   - More than 3 strategies with `"status": "DIVERGENT"`? → ESCALATE

4. **Commit the results** (JSON files only, no source changes):
   ```bash
   git add data/backtest_runs/validation/*.json
   git commit -m "Sprint 21.6 Human Step: 7 strategy validation results (Databento OHLCV-1m)"
   ```

## Error Handling

- **Databento download timeout or rate limit:** Wait 60 seconds and retry the failed strategy. HistoricalDataFeed has built-in retry logic, but network issues can still cause failures.
- **config_overrides format error (C-3):** If bull_flag, flat_top_breakout, or red_to_green fails with a config/override-related error, report the full traceback. This is a known risk from the S3 review.
- **Zero trades for a strategy:** This is a valid result, not an error. Record it and continue.
- **Memory error:** BacktestEngine can be memory-intensive with large symbol universes. If OOM, try running with `--log-level DEBUG` to see how many symbols are being processed.

## Constraints
- Do NOT modify any source files (no `.py`, `.yaml`, `.sql`, `.tsx` changes)
- Do NOT modify the revalidation script
- Do NOT install or upgrade any packages
- If a strategy fails and you cannot resolve it by retrying, skip it and document the failure — Session 4 will work with whatever results are available

## Deliverable
After all runs complete (or as many as succeed), report:
1. Which strategies completed successfully
2. Which strategies failed (with error summary)
3. The summary output from the loop above
4. Any escalation triggers hit
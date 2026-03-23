# Sprint 21.6 — Re-Run All 7 Strategy Backtests (Post-Fix)

## Context
Sprint 21.6.1 fixed three bugs that caused all strategies to produce zero trades:
1. BacktestEngine now applies legacy position sizing for `share_count=0` signals
2. VectorBT `load_symbol_data()` accepts both Databento and legacy Parquet naming
3. BacktestEngine auto-detects symbols from cache when `config.symbols=None`

The data cache is warm: 28 symbols × 23 months = 672 Parquet files in `data/databento_cache/`. No downloads needed — this is a re-run only.

This is NOT a code implementation session. Do NOT modify any source files. You are only running CLI commands and collecting output.

## Pre-Flight Checks

1. Verify the fixes are on the current branch:
   ```bash
   git log --oneline -3
   ```
   Expect to see the 21.6.1 commit(s) at HEAD.

2. Verify data cache is populated:
   ```bash
   find data/databento_cache/ -name "*.parquet" -not -path "*/1m/*" | wc -l
   ```
   Expect ~672 files (excluding any legacy `1m/` subdirectory files).

3. Clean the previous (zero-trade) results:
   ```bash
   rm -f data/backtest_runs/validation/*.json
   ls data/backtest_runs/validation/
   ```
   Expect empty directory.

4. Verify Databento API key is set (needed for cost verification even with cached data):
   ```bash
   # Check .env file
   grep "DATABENTO" .env
   ```
   Export it for the session:
   ```bash
   export DATABENTO_API_KEY="$(grep DATABENTO_API_KEY .env | cut -d= -f2 | tr -d '\"')"
   ```

## Execution

Run all 7 strategies sequentially. The cache is warm so each should complete in minutes, not hours.

**Date range:** 2023-04-01 to 2025-03-01 (matching the first run — EQUS.MINI starts 2023-03-28)

### Walk-Forward Strategies (4)

```bash
python scripts/revalidate_strategy.py \
  --strategy orb \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

```bash
python scripts/revalidate_strategy.py \
  --strategy orb_scalp \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

```bash
python scripts/revalidate_strategy.py \
  --strategy vwap_reclaim \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

```bash
python scripts/revalidate_strategy.py \
  --strategy afternoon_momentum \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

After each strategy completes, briefly check the result:
```bash
python -c "
import json
with open('data/backtest_runs/validation/<STRATEGY>_validation.json') as f:
    d = json.load(f)
print(f'Status: {d[\"status\"]}')
print(f'Trades: {d.get(\"new_results\", {}).get(\"total_trades\", \"N/A\")}')
"
```
Replace `<STRATEGY>` with the strategy name. If the first strategy (ORB) still shows ZERO_TRADES, STOP and report — the fix didn't work as expected.

### BacktestEngine-Only Strategies (3)

```bash
python scripts/revalidate_strategy.py \
  --strategy red_to_green \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

```bash
python scripts/revalidate_strategy.py \
  --strategy bull_flag \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

```bash
python scripts/revalidate_strategy.py \
  --strategy flat_top_breakout \
  --start 2023-04-01 \
  --end 2025-03-01 \
  --output-dir data/backtest_runs/validation/ \
  --log-level INFO
```

## After All 7 Complete

1. **List all output files:**
   ```bash
   ls -la data/backtest_runs/validation/*.json
   ```
   Expect 7 JSON files.

2. **Print full summary:**
   ```bash
   for f in data/backtest_runs/validation/*.json; do
     echo "=== $(basename $f) ==="
     python -c "
   import json
   with open('$f') as fh:
       d = json.load(fh)
   print(f\"  Status: {d.get('status', 'UNKNOWN')}\")
   nr = d.get('new_results', {})
   print(f\"  OOS Sharpe: {nr.get('oos_sharpe', 'N/A')}\")
   print(f\"  WFE PnL: {nr.get('wfe_pnl', 'N/A')}\")
   print(f\"  Total Trades: {nr.get('total_trades', 'N/A')}\")
   print(f\"  Win Rate: {nr.get('avg_win_rate', nr.get('win_rate', 'N/A'))}\")
   print(f\"  Profit Factor: {nr.get('avg_profit_factor', nr.get('profit_factor', 'N/A'))}\")
   print(f\"  Walk-Forward: {d.get('walk_forward_available', 'N/A')}\")
   div = d.get('divergence', {})
   if div:
       for k, v in div.items():
           if v: print(f\"  DIVERGENCE: {k} = {v}\")
   print()
   "
   done
   ```

3. **Check escalation triggers:**
   ```bash
   python -c "
   import json, glob
   zero = 0; divergent = 0; low_wfe = 0
   for f in sorted(glob.glob('data/backtest_runs/validation/*.json')):
       with open(f) as fh:
           d = json.load(fh)
       s = d.get('status', '')
       if s == 'ZERO_TRADES': zero += 1
       if s == 'DIVERGENT': divergent += 1
       nr = d.get('new_results', {})
       wfe = nr.get('wfe_pnl', 1.0)
       if wfe is not None and wfe < 0.1: low_wfe += 1
   print(f'ZERO_TRADES: {zero}/7 (escalate if >3)')
   print(f'DIVERGENT: {divergent}/7 (escalate if >3)')
   print(f'WFE < 0.1: {low_wfe}/7 (escalate if any)')
   "
   ```

4. **Commit the results:**
   ```bash
   git add data/backtest_runs/validation/*.json
   git commit -m "Sprint 21.6: 7 strategy re-validation results (Databento OHLCV-1m, post-fix)"
   ```

## Error Handling

- **ORB still shows ZERO_TRADES:** STOP — the position sizing fix may not have taken effect. Run `git log --oneline -5` and verify 21.6.1 is on the branch.
- **BacktestEngine-only strategies fail with config_overrides error:** Report the traceback (reviewer finding C-3 from S3).
- **Any strategy crashes:** Report the full error. Continue with remaining strategies.
- **Some strategies have zero trades but others don't:** This is a valid outcome — some strategies may genuinely not trigger on the 28-symbol universe. Document and continue.

## Constraints
- Do NOT modify any source files
- Do NOT modify the revalidation script
- Do NOT install or upgrade any packages
- Do NOT re-download data — the cache is warm

## Deliverable
Report:
1. Which strategies completed successfully (with trade counts)
2. Which strategies failed or produced zero trades
3. The full summary output
4. Any escalation triggers hit
5. The commit hash of the results
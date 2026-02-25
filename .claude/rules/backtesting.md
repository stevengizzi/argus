# Backtesting Rules

## VectorBT Sweep Architecture (MANDATORY)

All VectorBT parameter sweep implementations MUST follow the precompute + vectorize pattern
established in `vectorbt_orb.py` and `vectorbt_vwap_reclaim.py`. Never use the naive
per-combination approach.

### Required Architecture

1. **Precompute entries per day ONCE** — Entry candidate detection is parameter-independent.
   Compute all potential entries for each qualifying day in a single pass. Store results with
   NumPy arrays for post-entry price data.

2. **Filter entries by parameters at runtime** — The outer parameter loop only filters the
   precomputed entries by (pullback depth, bars, volume, etc.), never re-detects entries.

3. **Vectorized exit detection** — Use NumPy boolean masks to find stop/target/time-stop/EOD
   exits. Never use `iterrows()` or per-bar Python loops in the exit path.

### Antipatterns to AVOID

```python
# WRONG — 500x slower. Per-combination Python loops with DataFrame operations.
for params in param_combos:           # 768 iterations
    for day in trading_days:           # ~700 days
        trades = simulate_day(df, params)  # iterrows() inside

# CORRECT — Precompute + vectorize
entries = precompute_entries_for_day(day_df)  # ONCE per day, NumPy arrays
for params in param_combos:
    filtered = [e for e in entries if passes_filter(e, params)]
    for entry in filtered:
        trade = find_exit_vectorized(entry.highs, entry.lows, ...)  # NumPy masks
```

### Performance Expectations

- 29-symbol, 35-month sweep should complete in under 30 seconds
- If a sweep takes more than 2 minutes for the standard dataset, the architecture is wrong
- Always benchmark against the ORB sweep (~53 seconds for the full grid)

### Exit Priority (Worst-Case-for-Longs)

When multiple exit conditions trigger on the same bar, priority order is:
1. **Stop loss** — always uses stop price (worst case)
2. **Target** — uses target price
3. **Time stop** — uses close, BUT check if stop also hit (use stop price if so)
4. **EOD** — uses close, BUT check if stop also hit (use stop price if so)

This ensures backtest results are conservative (never better than reality).

# Sprint 11 — Extended Backtest & Walk-Forward Revalidation

> **Phase 3 (Comprehensive Validation), Track A**
> **Estimated effort:** 1–2 days build + analysis
> **Runs in parallel with:** Paper Trading (Track B)
> **Prerequisite:** Phase 2 complete (Sprint 10 ✅), Parameter Validation Report written

---

## Goal

Extend historical data from 11 months to ~3 years, re-run the VectorBT parameter sweep and walk-forward validation, and produce a definitive answer on whether the ORB strategy's recommended parameters generalize beyond the original test period.

The Phase 2 walk-forward was inconclusive (Scenario C) because 11 months produced only 3 walk-forward windows — well below the 8–12 minimum needed for statistical reliability. This sprint fixes that by acquiring enough data to run a proper walk-forward analysis.

---

## Steps

### Step 1: Extend Historical Data

Download 1-minute bar data back to March 2023 (or as far as Alpaca's free-tier IEX feed provides) for all 29 symbols in `config/backtest_universe.yaml`.

```bash
python -m argus.backtest.data_fetcher \
    --start 2023-03-01 --end 2025-02-28 \
    --symbols config/backtest_universe.yaml
```

This fills in the gap between the new start and the existing data (which covers March 2025 – January 2026). The existing data does not need to be re-downloaded.

**Expected outcome:** ~3 years of data (March 2023 – January 2026), ~700+ Parquet files, ~6M+ bars.

**Validation:** Run the data validator on all new files. Document any missing days, symbols with no coverage, or quality issues. Update `docs/backtesting/DATA_INVENTORY.md`.

**Potential issues:**
- Alpaca's free-tier IEX feed may not go back to 2023. If data availability starts later (e.g., 2024), use whatever is available and document the actual range.
- Some symbols may not have been publicly traded in 2023 (e.g., ARM IPO'd in September 2023). These will naturally have shorter histories — that's fine.
- Rate limiting: ~30 months × 29 symbols = ~870 additional file downloads. At 150 req/min, this takes ~6 minutes.

### Step 2: Re-run VectorBT Parameter Sweep

Run the full sweep on the extended dataset:

```bash
python -m argus.backtest.vectorbt_orb \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs/sweeps_extended \
    --start 2023-03-01 --end 2026-01-31
```

**Compare to Phase 2 sweep results:**
- Do the same parameters dominate? (or=5, hold=15 should still be top if the edge is real)
- Does the sensitivity classification change?
- Are the top-5 sets stable or did they shift?
- Does adding 2+ years of data change the optimal `min_gap_pct`?

**Record:** Top-10 parameter sets with Sharpe, trade count, PF. Sensitivity classification table. Any changes from Phase 2 findings.

### Step 3: Re-run Walk-Forward Validation

Run walk-forward with 4-month IS / 2-month OOS / 2-month step (same window config as Phase 2, but now spanning ~3 years instead of 11 months):

```bash
python -m argus.backtest.walk_forward \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs/walk_forward_extended \
    --start 2023-03-01 \
    --end 2026-01-31
```

**Expected:** ~15 walk-forward windows (vs. 3 in Phase 2). This is well above the 8–12 minimum.

Also run fixed-params walk-forward with the recommended parameters (DEC-076):

```bash
python -m argus.backtest.walk_forward \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs/walk_forward_extended_fixed \
    --start 2023-03-01 \
    --end 2026-01-31 \
    --config-override opening_range_minutes=5 \
    --config-override max_hold_minutes=15 \
    --config-override min_gap_pct=2.0 \
    --config-override stop_buffer_pct=0.0 \
    --config-override target_r=2.0 \
    --config-override max_range_atr_ratio=999.0
```

**Evaluate per DEC-047:**
- Mean WFE across all windows
- Min/max WFE per window
- Windows with WFE ≥ 0.3 (pass threshold)
- Windows with WFE ≥ 0.5 (good generalization)
- OOS total P&L and Sharpe

### Step 4: Interpret Results and Decide

**Scenario A — WFE ≥ 0.3 (Confirmed):**
Parameters generalize. Proceed with paper trading confidently. Update DEC-076 status to "Validated." Update the Parameter Validation Report with extended results.

**Scenario B — WFE < 0.3, but sweep finds different optimal params:**
Phase 2 parameters were overfit to the 11-month period. Revise DEC-076 with new recommendations. Re-run final validation with revised params. Update report.

**Scenario C — WFE < 0.3, no parameter set generalizes:**
The ORB strategy may not have a durable edge — at least not with the current entry/exit logic. This doesn't mean "stop paper trading" (forward data is still valuable), but it means expectations should be calibrated to "exploring whether an edge exists" rather than "validating a known edge."

**Scenario D — Insufficient extended data (Alpaca doesn't go back far enough):**
If we can only get 18–20 months instead of 36, we'll have ~7–8 windows — borderline but much better than 3. Document what we got and evaluate accordingly.

### Step 5: Update Documentation

- Update `docs/backtesting/PARAMETER_VALIDATION_REPORT.md` with extended results (new subsections or revised sections as appropriate)
- Update `docs/strategies/STRATEGY_ORB_BREAKOUT.md` — walk-forward table, parameter sensitivity, known limitations
- Update `docs/backtesting/DATA_INVENTORY.md` with new data range and statistics
- Update `10_PHASE3_SPRINT_PLAN.md` — mark Sprint 11 complete with result summary
- Update `CLAUDE.md` and `02_PROJECT_KNOWLEDGE.md` with current state
- Add DEC entry for any parameter changes
- Update `01_PROJECT_BIBLE.md` and `config/strategies/orb_breakout.yaml` only if parameters change

---

## Definition of Done

1. Historical data extended to 2023 (or Alpaca's limit), validated, inventory updated
2. VectorBT sweep complete on extended dataset, sensitivity compared to Phase 2
3. Walk-forward validation complete with 8+ windows
4. Walk-forward results interpreted and documented
5. Parameter Validation Report updated with extended findings
6. `STRATEGY_ORB_BREAKOUT.md` updated with extended walk-forward results and any parameter changes
7. `10_PHASE3_SPRINT_PLAN.md` updated: Sprint 11 marked ✅ COMPLETE with result summary
8. All other documentation updates from "Documentation Updates Expected" section complete
9. Sprint 11 marked ✅ COMPLETE

---

## Documentation Updates Expected

After this sprint:
- **`10_PHASE3_SPRINT_PLAN.md`:** Mark Sprint 11 ✅ COMPLETE. Record walk-forward result (WFE, window count, scenario classification).
- **`docs/backtesting/PARAMETER_VALIDATION_REPORT.md`:** Add new subsections or revise Sections 2, 4, 5, 7, and 9 with extended data results. Section 2 dataset description expands. Section 5 walk-forward gets a definitive result. If parameters change, Sections 6 and 7 need revision.
- **`docs/strategies/STRATEGY_ORB_BREAKOUT.md`:** Update the Walk-Forward Analysis table with extended results. Update Pipeline Stage if applicable. Update Parameter Sensitivity table if sweep results differ. Update Known Limitations (remove "insufficient data" items if resolved).
- **`docs/backtesting/DATA_INVENTORY.md`:** Update date range, total bars, file count, disk usage, and any new data quality findings.
- **`02_PROJECT_KNOWLEDGE.md` (project instructions):** Update current state if parameters change. Update Sprint 11 status in Build Phases.
- **`CLAUDE.md`:** Update current state with Sprint 11 result.
- **`05_DECISION_LOG.md`:** Add DEC-078+ for any parameter changes. Update DEC-076 status from "pending revalidation" to "validated" or "revised."
- **`01_PROJECT_BIBLE.md`:** Update ORB parameter table if recommendations change.
- **`config/strategies/orb_breakout.yaml`:** Update only if parameters change based on extended walk-forward results.

---

## What This Sprint Does NOT Include

- New strategy code or test infrastructure (all tools exist from Sprints 6–9)
- Paper trading operations (that's Track B, running in parallel)
- Parameter changes to the live paper trading config (paper trading uses DEC-076 params; if Sprint 11 finds better params, they're staged for the next paper trading cycle, not hot-swapped)
- Multi-strategy analysis
- Regime-conditional backtesting (future enhancement, but extended data makes this feasible later)

---

*End of Sprint 11 Spec*

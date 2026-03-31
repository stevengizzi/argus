# Sprint 29.5: What This Sprint Does NOT Do

## Out of Scope
1. **Time-of-day signal conditioning**: The 10:00 AM hour being the worst-performing period is noted but NOT addressed here. Requires new per-strategy config schema and backtesting validation. Deferred to Sprint 32 (Parameterized Templates).
2. **Regime-strategy interaction profiles**: Per-strategy regime sensitivity tuning is NOT in scope. Requires RegimeVector × strategy performance matrix. Deferred to Sprint 32.5.
3. **Sprint 29 strategy activation**: DipAndRip, HODBreak, GapAndGo, ABCD, and PreMarketHighBreak will activate automatically on next Argus restart from latest `main`. No code changes needed — just confirm in next session.
4. **Virtual scrolling for trades table**: Raising the limit from 250→1000 is the quick fix. Full virtual scrolling (react-virtual) is NOT implemented here. Deferred if 1000 becomes insufficient.
5. **Learning Loop threshold adjustments**: The conflicting Grade B recommendation is NOT acted on. Data collection continues.
6. **Automated weight application**: Learning Loop V2 (Sprint 40) scope. Not touched.
7. **Short selling infrastructure**: Sprint 30 scope. Not touched.
8. **Backtest re-validation of parameter changes**: Config value changes (risk limits, throttler) are paper-trading-only and do NOT require backtesting.
9. **Pre-live transition checklist updates**: These config changes are paper-trading-only. The pre-live checklist already covers restoration — no new entries needed until values stabilize.

## Edge Cases to Reject
1. **IBKR error 404 on BUY orders**: Only SELL orders need the re-query-qty fix. BUY error 404 should log WARNING and let existing retry handle it.
2. **Startup flatten for short positions**: `_flatten_unknown_position` only handles long positions (positive qty). Short positions at startup should log ERROR and skip — short selling infrastructure is Sprint 30.
3. **MFE/MAE for counterfactual positions**: CounterfactualTracker already tracks MAE/MFE internally. This sprint adds MFE/MAE only to real managed positions. No changes to counterfactual tracking.
4. **WS position updates for closed positions**: `position.updated` events for closing trades should NOT update the positions cache — let the REST backstop handle the transition from open→closed list.

## Scope Boundaries
- Do NOT modify: `argus/intelligence/learning/` (Learning Loop V1 — no changes)
- Do NOT modify: `argus/backtest/` (BacktestEngine — no changes)
- Do NOT modify: `argus/analytics/evaluation.py` (Evaluation Framework — no changes)
- Do NOT modify: `argus/intelligence/counterfactual.py` (shadow tracking logic — no changes except MFE/MAE field pass-through if needed)
- Do NOT modify: `argus/strategies/patterns/` (PatternModule implementations — no changes)
- Do NOT optimize: Query performance of trades endpoint — raising limit is sufficient
- Do NOT refactor: PerformanceThrottler internal logic — just add bypass flag
- Do NOT add: New REST endpoints (all changes use existing endpoints or WS channels)

## Interaction Boundaries
- This sprint does NOT change the behavior of: Quality Engine scoring, catalyst pipeline, regime classification, BacktestEngine, CounterfactualTracker shadow logic
- This sprint does NOT affect: Strategy signal generation logic (except ORB exclusion toggle), indicator calculations, universe manager routing

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Time-of-day signal conditioning | Sprint 32 | DEF-125 |
| Regime-strategy interaction profiles | Sprint 32.5 | DEF-126 |
| Virtual scrolling for trades table | Unscheduled | DEF-127 |
| IBKR error 404 root cause: multi-position qty divergence prevention | Sprint 30 | DEF-128 |

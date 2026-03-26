# Sprint 27.9: What This Sprint Does NOT Do

## Out of Scope

1. **SINDy fitting / pysindy dependency** — Threshold-based classification provides the same regime labels. SINDy's flow field, trajectory estimation, and analytical parameters (k, Ω, R², div(F)) are deferred. The R² ~0.03 on VIX phase space means SINDy adds questionable predictive value at this stage.
2. **PhaseSpaceCanvas / particle advection animation** — Pure visualization with zero trading impact. Deferred to post-Learning-Loop reward sprint.
3. **VIX Landscape page (full 5-panel layout)** — Same rationale as above. ~3 sessions of frontend work without pipeline value.
4. **VIX-enriched volatility blending** — Blending VIX into the existing intraday SPY volatility dimension hardcodes an interaction assumption. Better to keep VIX as independent RegimeVector dimensions and let the Learning Loop discover correlations.
5. **Trajectory modulation activation** — Wired structurally (quality engine infrastructure) but not user-configurable. Requires Learning Loop calibration data.
6. **Momentum phase space (Dean's paper)** — Intraday trade-level dynamics, not macro regime. Different scope entirely.
7. **3D phase space with SKEW/SDEX** — 2D phase spaces only.
8. **Real-time intraday VIX updates** — Daily closes only.
9. **VIX futures term structure data** — Using VIX/VIX_MA₆₃ proxy.
10. **BacktestEngine phase space integration** — Phase space dimensions not available during backtests.
11. **WebSocket push for VIX data** — TanStack Query polling sufficient for daily data.
12. **Mobile/PWA Canvas optimization** — No Canvas in this sprint.
13. **FMP Premium upgrade** — yfinance provides complete coverage.
14. **Learning Loop integration** — Sprint 28 scope. This sprint records data.

## Edge Cases to Reject

1. **VIX = 0** — Reject, use last valid observation. Log WARNING.
2. **σ₆₀ = 0 (zero volatility over 60 days)** — Guard with epsilon (1e-10), log WARNING, return None for vol-of-vol ratio.
3. **< 252 historical observations (initial backfill insufficient)** — VIX percentile returns None. Calculators that depend on percentile return None. Log WARNING.
4. **Both yfinance and FMP fail** — Serve stale cache if within `max_staleness_days`. If stale beyond threshold, return None for all derived metrics. DEGRADED health status.
5. **VIX percentile before 252-day lookback available** — Return None for percentile-dependent metrics.
6. **Strategy config specifies phase-space conditions but VIX disabled** — match-any semantics (None matches everything).
7. **BriefingGenerator called when VIX unavailable** — Omit VIX section entirely, produce valid brief without it.
8. **VIX data stale (> max_staleness_days)** — ALL consumers get None. BriefingGenerator omits section. Regime history records null for vix_close. Dashboard widget shows "Data unavailable."
9. **Weekend/holiday boot** — `get_latest_daily()` returns last trading day's data. `data_date` field makes this explicit.
10. **RegimeVector constructed with only original 6 fields** — New fields default to None. No construction error.
11. **RegimeHistoryStore reads pre-sprint rows** — Missing columns return NULL via SQLite. No migration error.
12. **Reclassification task fires before VIXDataService ready** — VIX calculators check `is_ready`, return None. Match-any semantics. No error.

## Scope Boundaries

- **Do NOT modify:** `argus/core/events.py`, `argus/strategies/*.py` (strategy source code — config-only changes to YAML files), `argus/execution/order_manager.py`, `argus/data/databento_data_service.py`, `argus/backtest/backtest_engine.py`, `argus/ui/src/pages/ObservatoryPage.tsx`, `argus/ai/` (AI layer), `argus/intelligence/counterfactual.py`, `argus/intelligence/catalyst_pipeline.py`, `argus/intelligence/catalyst_classifier.py`
- **Do NOT optimize:** yfinance download speed, derived metric computation beyond correctness
- **Do NOT refactor:** RegimeClassifierV2 calculator registration pattern, existing 6 RegimeVector dimension implementations, BriefingGenerator prompt template structure
- **Do NOT add:** Real-time VIX streaming, pysindy dependency, new Event Bus event types, new WebSocket endpoints, new navigation pages, Canvas 2D components

## Interaction Boundaries

- This sprint does NOT change: existing 6 RegimeVector dimensions, `primary_regime` property, strategy activation logic (conservative match-any defaults), quality scoring output (trajectory modulation OFF, regime_alignment enhancement dormant), position sizing output, volatility classification, any existing API/WebSocket endpoint behavior
- This sprint does NOT affect: Order Manager, Broker abstraction, Trade Logger, BacktestEngine, AI Layer, Catalyst Pipeline, Scanner, Indicator Engine, DatabentoDataService, CounterfactualTracker behavior (SignalRejectedEvent automatically carries extended RegimeVector but tracker logic unchanged)

## Deferred to Future Sprints

| Item | Target | DEF |
|------|--------|-----|
| SINDy phase space analysis + pysindy | Unscheduled | DEF-NEW |
| VIX Landscape visualization page | Unscheduled | DEF-NEW |
| PhaseSpaceCanvas particle advection | Unscheduled (same sprint as above) | DEF-NEW |
| VIX-enriched volatility blending | Post-Sprint 28 analysis | DEF-NEW |
| Trajectory modulation activation | Post-Sprint 28 calibration | DEF-NEW |
| 3D phase space (SKEW/SDEX) | Unscheduled | DEF-NEW |
| Momentum phase space (Dean paper intraday) | Unscheduled | DEF-NEW |
| BacktestEngine phase space integration | Unscheduled | DEF-NEW |
| Mobile/PWA Canvas optimization | Unscheduled | DEF-NEW |
| yfinance → FMP VIX migration | When FMP confirms Starter covers ^VIX, or on FMP Premium upgrade | DEF-NEW |
| Rolling-window SINDy parameter drift tracking | Unscheduled | DEF-NEW |
| Dashboard VIX widget: sparkline chart | Unscheduled (enhancement) | DEF-NEW |

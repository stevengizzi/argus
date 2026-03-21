# Sprint 26: What This Sprint Does NOT Do

## Out of Scope

1. **Replay Harness cross-validation (Stage 3):** Deferred to post-BacktestEngine (Sprint 27 builds BacktestEngine, Sprint 21.6 re-validates all strategies). Replay Harness was stage 3 of the incubator pipeline, but BacktestEngine replaces it for production-code replay.

2. **Short selling infrastructure:** Red-to-Green is a LONG strategy (buying gap-down reversals). Short selling is Sprint 29–31. Do NOT add short-side SignalEvent support, negative share_count, or short position tracking.

3. **Pattern parameterization / templates:** Sprint 32 introduces parameterized strategy templates. This sprint creates fixed-parameter patterns. Do NOT build parameter range exploration UI, template gallery, or systematic search infrastructure.

4. **Ensemble orchestration between patterns:** Sprint 32–38 territory. Do NOT add cross-pattern signal aggregation, ensemble scoring, or multi-pattern entry rules.

5. **BacktestEngine integration:** Sprint 27. PatternModule ABC should be BacktestEngine-friendly (simple detect/score interface) but do NOT import or reference BacktestEngine code. Do NOT build a HistoricalDataFeed adapter.

6. **Learning Loop weight optimization:** Sprint 28. Quality Engine weights remain static defaults. Do NOT build feedback loops from pattern outcomes to quality weights.

7. **FMP Premium upgrade or FMP news integration:** DEC-356 defers FMP Premium. R2G catalyst integration uses Finnhub + SEC EDGAR only. Do NOT add FMP news source activation logic or Premium endpoint calls.

8. **Historical data purchase from Databento:** DEC-353 defers this. VectorBT uses existing Alpaca historical data. Do NOT add Databento historical data download logic.

9. **Observable Observatory integration for new strategies:** The existing Observatory automatically handles any registered strategy. Do NOT modify Observatory code, ObservatoryService, or Observatory WebSocket for new strategies.

10. **Order Flow analysis for R2G:** The order flow model is deferred to post-revenue (DEC-238). R2G entry logic uses candle-level data only. Do NOT integrate Level 2/3 order book data.

## Edge Cases to Reject

1. **R2G on gap-UP stocks:** Strategy receives candle events for all symbols on its watchlist. If a symbol gapped up (positive gap), `on_candle()` should return `None` immediately (WATCHING state never transitions). Do NOT attempt to trade gap-up stocks as reversals.

2. **R2G gap exceeding max_gap_down_pct:** If a stock gaps down more than max_gap_down_pct (e.g., >10%), transition directly to EXHAUSTED state with reason "gap_too_large". Do NOT attempt to find support levels on massive gaps.

3. **Bull Flag / Flat-Top on insufficient data:** If `detect()` receives fewer bars than needed (e.g., < pole_min_bars for Bull Flag), return `None`. Do NOT pad or interpolate missing data.

4. **Pattern detection outside operating window:** PatternModule.detect() runs regardless of time. PatternBasedStrategy enforces operating window before generating signals. Do NOT add time-awareness to the pattern detection interface itself.

5. **Multiple simultaneous pattern detections on same symbol:** If both Bull Flag and Flat-Top detect on the same symbol, both can fire independently. ALLOW_ALL cross-strategy policy (DEC-121/160) applies. Do NOT add pattern-level mutual exclusion.

6. **VectorBT WFE < 0.3:** If walk-forward validation fails, set the strategy's `pipeline_stage` to `"exploration"` in its config YAML. Wire the strategy into main.py as config-gated (`enabled: false` for production). Do NOT delete the strategy code or prevent registration. Document the results in the backtest_summary config section and strategy spec sheet.

7. **R2G with no VWAP indicator data:** If VWAP is not yet computed (e.g., very early in session), VWAP cannot be used as a support level. R2G should still check prior close and premarket low levels. Do NOT block R2G entirely for lack of VWAP — it has multiple support level types.

8. **PatternBasedStrategy with disabled pattern module:** If pattern config has `enabled: false`, the strategy should not be created in main.py. Do NOT create disabled PatternBasedStrategy instances that consume Event Bus subscriptions.

## Scope Boundaries

- **Do NOT modify:**
  - `argus/strategies/base_strategy.py` — abstract interface is frozen
  - `argus/strategies/orb_base.py`, `orb_breakout.py`, `orb_scalp.py` — existing ORB family
  - `argus/strategies/vwap_reclaim.py` — existing VWAP strategy
  - `argus/strategies/afternoon_momentum.py` — existing AfMo strategy
  - `argus/core/events.py` — SignalEvent, CandleEvent schemas are frozen
  - `argus/intelligence/quality_engine.py` — scoring logic unchanged
  - `argus/intelligence/position_sizer.py` — sizing logic unchanged
  - `argus/core/orchestrator.py` — registration/activation logic unchanged
  - `argus/core/risk_manager.py` — gating logic unchanged
  - `argus/data/universe_manager.py` — routing logic unchanged
  - `argus/data/fmp_scanner.py` — scanner unchanged
  - Existing config files: `orb_breakout.yaml`, `orb_scalp.yaml`, `vwap_reclaim.yaml`, `afternoon_momentum.yaml`

- **Do NOT optimize:**
  - VectorBT backtest execution speed — correctness over performance
  - PatternModule.detect() latency — target <1ms but do not optimize at expense of clarity
  - Pattern Library page rendering — existing component infrastructure is sufficient

- **Do NOT refactor:**
  - Existing strategy creation pattern in main.py — add new strategies following the same if/else pattern
  - Config loader architecture — add new loaders following existing pattern
  - BaseStrategy abstract method signatures — new strategies conform to existing interface

- **Do NOT add:**
  - New Event types (no PatternDetectionEvent — patterns are internal to strategy logic)
  - New API endpoints (existing `/api/v1/strategies` serves all registered strategies)
  - New WebSocket channels (existing Observatory WS handles new strategies automatically)
  - New database tables (pattern detection results are transient, not persisted)
  - AI Copilot context for new strategies (existing SystemContextBuilder handles dynamically)
  - New frontend pages or navigation routes

## Interaction Boundaries

- This sprint does NOT change the behavior of: BaseStrategy abstract interface, SignalEvent schema, Quality Engine scoring algorithm, Risk Manager gating logic, Orchestrator activation/allocation logic, Universe Manager routing algorithm, Event Bus subscription model, Order Manager lifecycle
- This sprint does NOT affect: Dashboard page, Trades page, Performance page, Orchestrator page, Debrief page, System page, Observatory page, AI Copilot behavior, WebSocket protocol, JWT authentication, Databento data pipeline, IBKR broker adapter

## Deferred to Future Sprints

| Item | Target Sprint | Notes |
|------|--------------|-------|
| Replay Harness cross-validation | Sprint 27 (BacktestEngine replaces) | Stage 3 validation deferred |
| BacktestEngine integration | Sprint 27 | PatternModule ABC designed to be compatible |
| Backtest re-validation with Databento data | Sprint 21.6 (after 27) | VectorBT results are provisional (DEC-132) |
| Learning Loop weight optimization | Sprint 28 | Quality Engine weights stay static |
| Pattern parameterization / templates | Sprint 32 | Fixed-parameter patterns for now |
| Ensemble pattern orchestration | Sprint 32–38 | Patterns fire independently |
| Short selling infrastructure | Sprint 29–31 | R2G is long-only |
| FMP Premium for news | Unscheduled (DEC-356) | Catalyst pipeline uses Finnhub + EDGAR |
| Pattern detection DB persistence | Unscheduled | Detections are transient strategy-internal state |
| R2G order flow integration | Post-revenue (DEC-238) | Requires Databento Plus tier |

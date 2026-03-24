# Sprint 27.6: What This Sprint Does NOT Do

## Out of Scope

1. **ML-based regime classification:** V2 is rules-based like V1 (amendment §3). ML regime classification is Sprint 40+ territory, contingent on proving the rules-based approach insufficient.

2. **Real-time correlation computation:** O(N²) on every candle is too expensive. Correlation is computed during pre-market only. If real-time correlation proves critical, it would require a fundamentally different approach (e.g., exponentially-weighted streaming correlation).

3. **VIX futures term structure:** Requires additional data subscription (deferred post-revenue per DEC-238). The `volatility_direction` dimension in RegimeVector uses a 5-day vs 20-day realized vol ratio as a term-structure proxy — this is computed from existing data.

4. **Automatic strategy deactivation based on RegimeVector dimensions:** The Orchestrator continues to use `primary_regime` (MarketRegime) for existing `allowed_regimes` filtering. RegimeVector dimensions inform future consumers (Learning Loop, Experiment Registry, micro-strategies), not current strategy gating. Strategy activation remains unchanged.

5. **Strategy operating conditions wiring:** The operating conditions matching logic (schema + `matches_conditions()`) is implemented and tested, but no strategy is wired to use it. Strategies continue to use `get_market_conditions_filter().allowed_regimes`. Wiring is Sprint 34+ when micro-strategies exist.

6. **Breadth/correlation/sector/intraday in historical backtest regime tagging:** BacktestEngine's `_compute_regime_tags()` uses V2 for trend + vol dimensions only (identical to V1 logic). Computing historical breadth from OHLCV-1m across the full backtest universe is theoretically possible but would require per-symbol MA computation for thousands of symbols per day — significant compute cost best deferred to when backtesting actually needs multi-dimensional regime conditioning.

7. **Changes to `MultiObjectiveResult.regime_results` key structure:** Keys remain `MarketRegime.value` strings. The RegimeVector is additional metadata layered on top, not a replacement for the existing regime bucketing. Changing the keys would break the comparison API and ensemble evaluation.

8. **Observatory deep-dive regime page:** Only the session vitals bar extension is in scope. A full dedicated regime analysis view is a future UI sprint.

9. **Sector-level strategy allocation:** RegimeVector captures sector rotation for informational purposes. Using sector data to bias strategy allocation (e.g., "sector rotation favoring tech → increase ORB weight on tech stocks") requires allocation strategy changes that are Sprint 36+ (Ensemble Orchestrator V2).

10. **Breadth divergence signals:** BreadthCalculator tracks breadth level but does not generate divergence signals (e.g., "SPY making new highs but breadth declining"). Divergence detection is a Learning Loop consumer, not a regime classification concern.

11. **RegimeVector history analytics or visualization:** The persistence layer (RegimeHistoryStore) writes raw snapshots. Aggregation (e.g., "what % of time was the market trending today?"), trend analysis, and visualization are Sprint 28+ consumers. This sprint only stores the data.

## Edge Cases to Reject

1. **BreadthCalculator with < 50 symbols:** Compute breadth from available symbols but lower `regime_confidence`. Do NOT attempt to estimate "true" market breadth from a small sample.

2. **MarketCorrelationTracker with < 5 symbols having 20+ days history:** Return neutral defaults (`average_correlation = 0.4`, `correlation_regime = "normal"`). Do NOT attempt correlation estimation with insufficient data.

3. **SectorRotationAnalyzer with partial sector data:** Classify only available sectors. Do NOT impute missing sector performance. If fewer than 5 sectors available, degrade to `"mixed"`.

4. **IntradayCharacterDetector called before 9:35 AM ET:** Return None for all intraday fields. Do NOT attempt pre-market character classification.

5. **IntradayCharacterDetector on half-day/early close:** Use the same classification logic. Do NOT implement special half-day handling (low frequency, not worth the complexity).

6. **Multiple simultaneous regime reclassifications:** The existing 300s asyncio task ensures single-threaded access. Do NOT add locking — rely on asyncio's cooperative scheduling.

7. **RegimeVector serialization of None intraday fields:** Serialize as null/None in JSON. Do NOT omit keys — consumers expect all fields present.

## Scope Boundaries

- **Do NOT modify:** `argus/analytics/evaluation.py`, `argus/analytics/comparison.py`, `argus/analytics/ensemble_evaluation.py`, `argus/data/databento_data_service.py`, `argus/strategies/*.py` (no strategy files), `argus/intelligence/*.py`, `argus/execution/*.py`, `argus/ai/*.py`
- **Do NOT optimize:** BreadthCalculator for extreme scale (> 10,000 symbols). Current design handles ~5,000 viable symbols. Scale optimization deferred.
- **Do NOT refactor:** Existing `RegimeClassifier` V1 code. V1 remains in `regime.py` alongside V2 for config-gate bypass. Remove V1 only when V2 is proven in production (Sprint 28+ timeframe).
- **Do NOT add:** Any new data subscriptions or API integrations beyond existing FMP Starter + Databento Standard.

## Interaction Boundaries

- This sprint does NOT change the behavior of: `allowed_regimes` filtering, strategy activation/suspension logic, Risk Manager regime checks, `MultiObjectiveResult` comparison/ensemble APIs, signal processing pipeline, quality scoring pipeline.
- This sprint does NOT affect: `argus/intelligence/` (catalyst pipeline), `argus/ai/` (copilot), `argus/execution/` (order management), `argus/data/universe_manager.py` (universe filtering).
- BreadthCalculator subscribes to Event Bus CandleEvents — it does NOT modify DatabentoDataService. It is a passive listener.

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| ML-based regime classification | Sprint 40+ | — |
| Real-time correlation | Unscheduled | — |
| VIX futures term structure | Post-revenue | — |
| Strategy operating conditions wiring | Sprint 34+ | — |
| Historical breadth in backtest regime tagging | Unscheduled | DEF-091 |
| Sector-level strategy allocation | Sprint 36+ (Ensemble Orchestrator V2) | — |
| Breadth divergence signals | Sprint 28 (Learning Loop) | — |
| Observatory dedicated regime analysis page | Unscheduled | DEF-092 |
| Remove V1 RegimeClassifier (after V2 proven) | Sprint 28+ | DEF-093 |
| RegimeVector aggregation/analytics views | Sprint 28+ (Learning Loop consumer) | DEF-094 |

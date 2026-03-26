# Sprint 27.9: Review Context File

> This file is referenced by all session review prompts. It contains the Sprint Spec,
> Specification by Contradiction, Regression Checklist, and Escalation Criteria.
> The reviewer reads this file once per review session.

---

## Sprint Spec

# Sprint 27.9: VIX Regime Intelligence

## Goal
Deliver VIX-based regime intelligence infrastructure — a VIX data service with SQLite persistence, 4 new threshold-based RegimeVector dimensions, and pipeline integration across briefing, regime history, and orchestrator — so the Learning Loop (Sprint 28) has VIX context available from day one of paper trading data collection.

## Scope

### Deliverables

1. **VIXDataService** — `VIXDataService` class (`argus/data/vix_data_service.py`) that ingests VIX + SPX daily OHLC from Yahoo Finance (via `yfinance`), computes 5 derived metrics, persists to SQLite (`data/vix_landscape.db`), and runs a daily update task during market hours. Follows trust-cache-on-startup pattern (DEC-362): on boot, loads from SQLite immediately; fetches only missing days incrementally. One-time historical backfill (22 years) on first run only. Exposes `get_latest_daily()` returning last completed trading day's data with `data_date` field. Self-disables when data exceeds `max_staleness_days` (default: 3 trading days) — returns None to all consumers instead of stale values.

   Derived metrics: vol-of-vol ratio (σ₁₀/σ₆₀), VIX percentile rank (252-day), term structure proxy (VIX/VIX_MA₆₃), 20-day realized volatility (annualized), variance risk premium (VIX² − RV₂₀²).

2. **Four Threshold-Based Calculators** — VolRegimePhaseCalculator (CALM/TRANSITION/VOL_EXPANSION/CRISIS), VolRegimeMomentumCalculator (STABILIZING/NEUTRAL/DETERIORATING), TermStructureRegimeCalculator (CONTANGO_LOW/CONTANGO_HIGH/BACKWARDATION_LOW/BACKWARDATION_HIGH), VarianceRiskPremiumCalculator (COMPRESSED/NORMAL/ELEVATED/EXTREME + continuous value). All return None when VIX data unavailable or stale.

3. **RegimeVector Expansion (6→11 fields)** — 4 new Optional enum fields + `vix_close: Optional[float]`. `primary_regime` unchanged. `matches_conditions()` treats None as match-any.

4. **RegimeOperatingConditions Update** — Extended for new dimensions. Strategy YAMLs updated with conservative defaults (match-any = zero behavior change).

5. **RegimeHistoryStore Migration** — ALTER TABLE ADD COLUMN vix_close. Nullable for pre-sprint rows.

6. **Pipeline Integration** — BriefingGenerator VIX section (user context, not system prompt), Orchestrator pre-market VIX logging, SetupQualityEngine regime_alignment infrastructure (dormant), regime history VIX enrichment.

7. **REST Endpoints** — `GET /api/v1/vix/current`, `GET /api/v1/vix/history`. JWT-protected.

8. **Dashboard VIX Widget** — VixRegimeCard showing VIX close, VRP tier, regime phase, momentum arrow. Hidden when disabled.

### Boundary Definitions

**Vol-of-vol phase space (σ₁₀/σ₆₀ vs VIX_percentile):**
- CALM: x ≤ 1.0 AND y ≤ 0.50
- TRANSITION: not CALM, x ≤ 1.3 AND y ≤ 0.70
- CRISIS: y ≥ 0.85
- VOL_EXPANSION: everything else

**Term structure phase space (VIX/VIX_MA₆₃ vs VIX_percentile):**
- CONTANGO: x ≤ 1.0, BACKWARDATION: x > 1.0
- LOW/HIGH split: y below/above 0.50

**VRP tiers:** COMPRESSED ≤ 0, NORMAL 0–50, ELEVATED 50–150, EXTREME > 150

### Config Gate
Single gate: `vix_regime.enabled`. No separate VIX-enriched volatility or trajectory modulation flags.

---

## Specification by Contradiction (Summary)

**Out of scope:** SINDy/pysindy, PhaseSpaceCanvas/particle advection, VIX Landscape page, VIX-enriched volatility blending, trajectory modulation activation, momentum phase space, 3D phase space, real-time VIX, BacktestEngine integration, new WebSocket endpoints, new Event Bus events.

**Do NOT modify:** `argus/core/events.py`, `argus/strategies/*.py` (source code), `argus/execution/order_manager.py`, `argus/data/databento_data_service.py`, `argus/backtest/backtest_engine.py`, `argus/ui/src/pages/ObservatoryPage.tsx`, `argus/ai/`, `argus/intelligence/counterfactual.py`, `argus/intelligence/catalyst_pipeline.py`

**Does NOT change:** existing 6 RegimeVector dims, `primary_regime`, strategy activation, quality scoring, position sizing, volatility classification, existing API/WS endpoints.

---

## Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | `primary_regime` identical to pre-sprint | Unit test: original 6 fields → same enum |
| R2 | RegimeVector construction with original fields works | Unit test: no new fields → no error, defaults None |
| R3 | `matches_conditions()` None = match-any | Unit test: conditions specify phase, vector=None → match |
| R4 | `to_dict()` includes all 11 fields | Unit test |
| R5 | RegimeHistoryStore reads pre-sprint rows | Integration test: old row → no error, vix_close=None |
| R6 | All 7 strategies activate same as before | Regression test with conservative YAML defaults |
| R7 | Quality scores unchanged (trajectory modulation OFF) | Integration test: same input → same output |
| R8 | Position sizes unchanged | Integration test |
| R9 | BriefingGenerator valid when VIX unavailable | Unit test: None → brief without VIX section |
| R10 | Server starts with vix_regime.enabled: true | Integration test |
| R11 | Server starts with vix_regime.enabled: false | Integration test |
| R12 | Existing 6 RegimeVector dims same values | Regression test |
| R13 | Config YAML keys match Pydantic model fields | Config validation test |
| R14 | Dashboard loads when VIX disabled | Vitest |
| R15 | Existing API endpoints unaffected | Existing test suite |

---

## Escalation Criteria

1. yfinance cannot fetch ^VIX/^GSPC → ESCALATE
2. RegimeVector extension breaks `primary_regime` → ESCALATE
3. Existing calculator behavior changes → ESCALATE
4. Strategy activation conditions change → ESCALATE
5. Quality scores or position sizes change → ESCALATE
6. SINDy complexity creep (pysindy, ODE fitting, flow fields) → ESCALATE
7. Server startup fails with VIX enabled → ESCALATE

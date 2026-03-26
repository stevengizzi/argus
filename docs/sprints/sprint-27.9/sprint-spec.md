# Sprint 27.9: VIX Regime Intelligence

## Goal
Deliver VIX-based regime intelligence infrastructure — a VIX data service with SQLite persistence, 4 new threshold-based RegimeVector dimensions, and pipeline integration across briefing, regime history, and orchestrator — so the Learning Loop (Sprint 28) has VIX context available from day one of paper trading data collection.

## Scope

### Deliverables

1. **VIXDataService** — `VIXDataService` class (`argus/data/vix_data_service.py`) that ingests VIX + SPX daily OHLC from Yahoo Finance (via `yfinance`), computes 5 derived metrics, persists to SQLite (`data/vix_landscape.db`), and runs a daily update task during market hours. Follows trust-cache-on-startup pattern (DEC-362): on boot, loads from SQLite immediately; fetches only missing days incrementally. One-time historical backfill (22 years) on first run only. Exposes `get_latest_daily()` returning last completed trading day's data with `data_date` field. Self-disables when data exceeds `max_staleness_days` (default: 3 trading days) — returns None to all consumers instead of stale values.

   **Derived metrics:**
   - Vol-of-vol ratio: σ₁₀(VIX) / σ₆₀(VIX)
   - VIX percentile rank: 252-day rolling percentile
   - Term structure proxy: VIX / VIX_MA₆₃
   - 20-day realized volatility: annualized σ₂₀(SPX log returns)
   - Variance risk premium: VIX² − RV₂₀²

2. **Four Threshold-Based Calculators** — Four new calculator classes in `argus/core/vix_calculators.py`, following Sprint 27.6's calculator pattern, wired into `RegimeClassifierV2`:

   - **VolRegimePhaseCalculator:** Classifies position in vol-of-vol phase space (σ₁₀/σ₆₀, VIX_percentile) into `VolRegimePhase` enum: CALM / TRANSITION / VOL_EXPANSION / CRISIS. Boundary thresholds configurable in YAML.
   - **VolRegimeMomentumCalculator:** Computes 5-day directional change in vol-of-vol coordinate space → `VolRegimeMomentum` enum: STABILIZING / NEUTRAL / DETERIORATING. Threshold for significance configurable.
   - **TermStructureRegimeCalculator:** Classifies position in term structure phase space (VIX/VIX_MA₆₃, VIX_percentile) into `TermStructureRegime` enum: CONTANGO_LOW / CONTANGO_HIGH / BACKWARDATION_LOW / BACKWARDATION_HIGH.
   - **VarianceRiskPremiumCalculator:** Classifies VRP into `VRPTier` enum: COMPRESSED / NORMAL / ELEVATED / EXTREME. Also provides continuous VRP value.

   All calculators return None when VIXDataService data is unavailable or stale. All boundary coordinates configurable in `config/vix_regime.yaml`.

3. **RegimeVector Expansion (6→10 dimensions)** — 4 new `Optional[...]` fields on `RegimeVector` frozen dataclass with `default=None`:
   - `vol_regime_phase: Optional[VolRegimePhase]`
   - `vol_regime_momentum: Optional[VolRegimeMomentum]`
   - `term_structure_regime: Optional[TermStructureRegime]`
   - `variance_risk_premium: Optional[VRPTier]`

   Plus a `vix_close: Optional[float]` field for direct VIX close pass-through. `primary_regime` property unchanged. `to_dict()` includes all 11 fields. `matches_conditions()` treats None as match-any for new dimensions.

4. **RegimeOperatingConditions Update** — `matches_conditions()` extended for new dimensions. Strategy YAML configs updated with conservative defaults: new dimension fields absent or null → match-any semantics → zero behavior change.

5. **RegimeHistoryStore Migration** — `ALTER TABLE ADD COLUMN vix_close REAL` migration at startup when column missing. New regime history records include VIX close (nullable). Old records read without error.

6. **Pipeline Integration:**
   - **BriefingGenerator:** VIX/VRP section added to intelligence brief context (user message, not system prompt). Includes: yesterday's VIX close, VRP value and tier, vol regime phase, momentum direction. Graceful omission when VIX data unavailable or stale.
   - **Regime History Enrichment:** `vix_close` field recorded with each regime history entry. Nullable for pre-sprint rows and stale-data periods. Gives Learning Loop the ability to distinguish "setup during low-VIX calm" from "setup during high-VIX calm."
   - **Orchestrator Pre-Market Logging:** Before first candle, log VIX regime context (phase, momentum, VRP tier). Operational visibility only.
   - **SetupQualityEngine:** regime_alignment dimension infrastructure prepared for future phase-space-aware scoring. Functionally dormant until strategies specify phase space conditions in their operating conditions (documented explicitly as post-Sprint 28 activation).

7. **REST Endpoints:**
   - `GET /api/v1/vix/current` — Latest VIX daily data + all regime classifications + staleness info
   - `GET /api/v1/vix/history?start_date=&end_date=` — Historical VIX data with derived metrics

   Both JWT-protected.

8. **Dashboard VIX Widget** — `VixRegimeCard` component on Dashboard page. Shows: VIX close, VRP tier badge, vol regime phase label, momentum direction arrow (↑↗→↘↓). Hidden when `vix_regime.enabled: false`. TanStack Query polling at 60s interval. Dark card styling matching existing Dashboard widgets.

### Acceptance Criteria

1. **VIXDataService:**
   - Fetches ≥5,000 daily observations of ^VIX and ^GSPC from yfinance on initial backfill
   - All 5 derived metrics compute correctly (unit tests with known input → expected output)
   - `get_latest_daily()` returns last completed trading day's data with correct `data_date`
   - Weekend/holiday queries return Friday (or last trading day) data
   - SQLite persistence with atomic writes; subsequent boots load from cache, fetch only missing days
   - When data older than `max_staleness_days`: `is_stale` property returns True, `get_latest_daily()` returns None for derived metrics
   - Config-gated via `vix_regime.enabled`
   - `is_ready` property: False until initial load complete

2. **Calculators:**
   - Each calculator returns correct enum for known inputs (e.g., vol-of-vol ratio 0.8, VIX percentile 0.15 → CALM)
   - Each calculator returns None when VIXDataService unavailable or stale
   - Boundary thresholds configurable and validated by Pydantic
   - VRP calculator returns both tier (enum) and continuous value

3. **RegimeVector Expansion:**
   - `RegimeVector` has 11 fields (6 original + 4 new enum + `vix_close`)
   - `primary_regime` returns identical value as pre-sprint for any input
   - `to_dict()` includes all 11 fields with proper None→null serialization
   - `matches_conditions()` treats None/missing new dims as match-any
   - Construction with only original 6 fields still works (new fields default None)

4. **Pipeline Integration:**
   - BriefingGenerator produces VIX section when data available, omits gracefully when not
   - Regime history records include vix_close (nullable for pre-sprint rows)
   - Orchestrator logs VIX context before first candle during market hours
   - Quality scores identical to pre-sprint (trajectory modulation OFF, regime_alignment dormant)
   - Position sizes identical to pre-sprint

5. **REST Endpoints:**
   - `GET /api/v1/vix/current` returns 200 with latest data or 200 with stale indicator
   - `GET /api/v1/vix/history` returns 200 with date-filtered results
   - Both return 401 when unauthenticated

6. **Dashboard Widget:**
   - Renders VIX close, VRP badge, regime phase, momentum arrow
   - Hidden when `vix_regime.enabled: false`
   - Shows "Data unavailable" state when VIX data stale or service not ready

### Performance Benchmarks

| Metric | Target | Measurement |
|--------|--------|-------------|
| Historical backfill (first run) | <60s for 22 years | Timer in backfill method |
| Daily update cycle | <15s | Timer in update task |
| `get_latest_daily()` latency | <10ms | SQLite read, cached in memory |
| Derived metric computation | <1s for full history | pytest benchmark |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `vix_regime.enabled` | `VixRegimeConfig` | `enabled` | `true` |
| `vix_regime.yahoo_symbol_vix` | `VixRegimeConfig` | `yahoo_symbol_vix` | `"^VIX"` |
| `vix_regime.yahoo_symbol_spx` | `VixRegimeConfig` | `yahoo_symbol_spx` | `"^GSPC"` |
| `vix_regime.vol_short_window` | `VixRegimeConfig` | `vol_short_window` | `10` |
| `vix_regime.vol_long_window` | `VixRegimeConfig` | `vol_long_window` | `60` |
| `vix_regime.percentile_window` | `VixRegimeConfig` | `percentile_window` | `252` |
| `vix_regime.ma_window` | `VixRegimeConfig` | `ma_window` | `63` |
| `vix_regime.rv_window` | `VixRegimeConfig` | `rv_window` | `20` |
| `vix_regime.update_interval_seconds` | `VixRegimeConfig` | `update_interval_seconds` | `3600` |
| `vix_regime.history_years` | `VixRegimeConfig` | `history_years` | `22` |
| `vix_regime.max_staleness_days` | `VixRegimeConfig` | `max_staleness_days` | `3` |
| `vix_regime.fmp_fallback_enabled` | `VixRegimeConfig` | `fmp_fallback_enabled` | `false` |
| `vix_regime.momentum_window` | `VixRegimeConfig` | `momentum_window` | `5` |
| `vix_regime.momentum_threshold` | `VixRegimeConfig` | `momentum_threshold` | `0.05` |
| `vix_regime.vol_regime_boundaries.calm_max_x` | `VolRegimeBoundaries` | `calm_max_x` | `1.0` |
| `vix_regime.vol_regime_boundaries.calm_max_y` | `VolRegimeBoundaries` | `calm_max_y` | `0.50` |
| `vix_regime.vol_regime_boundaries.transition_max_x` | `VolRegimeBoundaries` | `transition_max_x` | `1.3` |
| `vix_regime.vol_regime_boundaries.transition_max_y` | `VolRegimeBoundaries` | `transition_max_y` | `0.70` |
| `vix_regime.vol_regime_boundaries.crisis_min_y` | `VolRegimeBoundaries` | `crisis_min_y` | `0.85` |
| `vix_regime.term_structure_boundaries.contango_threshold` | `TermStructureBoundaries` | `contango_threshold` | `1.0` |
| `vix_regime.term_structure_boundaries.low_high_percentile_split` | `TermStructureBoundaries` | `low_high_percentile_split` | `0.50` |
| `vix_regime.vrp_boundaries.compressed_max` | `VRPBoundaries` | `compressed_max` | `0.0` |
| `vix_regime.vrp_boundaries.normal_max` | `VRPBoundaries` | `normal_max` | `50.0` |
| `vix_regime.vrp_boundaries.elevated_max` | `VRPBoundaries` | `elevated_max` | `150.0` |

**Boundary definitions (vol-of-vol phase space):**
- CALM: σ₁₀/σ₆₀ ≤ 1.0 AND VIX_percentile ≤ 0.50
- TRANSITION: not CALM, σ₁₀/σ₆₀ ≤ 1.3 AND VIX_percentile ≤ 0.70
- CRISIS: VIX_percentile ≥ 0.85 (regardless of x)
- VOL_EXPANSION: everything else (high vol-of-vol ratio and/or high percentile, not yet crisis)

**Boundary definitions (term structure phase space):**
- CONTANGO: VIX/VIX_MA₆₃ ≤ 1.0 (VIX below moving average)
- BACKWARDATION: VIX/VIX_MA₆₃ > 1.0 (VIX above moving average)
- LOW/HIGH split: VIX_percentile below/above 0.50

**VRP tiers:**
- COMPRESSED: VRP ≤ 0 (realized vol exceeds implied)
- NORMAL: 0 < VRP ≤ 50
- ELEVATED: 50 < VRP ≤ 150
- EXTREME: VRP > 150

All boundaries configurable in YAML. These defaults are derived from empirical VIX behavior and QuantSymplectic's published phase space annotations. They should be treated as initial calibration; the Learning Loop can optimize them post-Sprint 28.

## Dependencies

- **Python packages:** `yfinance` (pip install)
- **Existing infrastructure:** RegimeClassifierV2 (Sprint 27.6), RegimeHistoryStore (Sprint 27.6), SetupQualityEngine (Sprint 24), BriefingGenerator (Sprint 23.5), Orchestrator
- **Data:** Yahoo Finance (free, unofficial), FMP Starter (if ^VIX available — verify pre-Session 1)
- **Pre-Session 1 verification:** Hit FMP `/stable/historical-price-full/^VIX` endpoint with API key. If 403, set `fmp_fallback_enabled: false` (default) and proceed with yfinance only.

## Relevant Decisions

- DEC-300 (config-gating pattern)
- DEC-345 (separate SQLite DB per subsystem)
- DEC-346 (300s regime reclassification task)
- DEC-362 (trust-cache-on-startup pattern)
- DEC-342 (strategy observability — ring buffer pattern)
- DEC-328 (test suite tiering)
- DEC-277 (fail-closed on missing data)

## Relevant Risks

- RSK-NEW: yfinance reliability as unofficial scraping library — mitigated by SQLite cache + staleness self-disable + optional FMP fallback
- RSK-NEW: Regime boundary calibration — initial thresholds are empirically informed estimates; Learning Loop data will enable optimization

## Session Count Estimate

4 sessions + 0.5 contingency + 0.5 visual-review fix budget = 5 sessions maximum. Strict dependency chain: S1→S2→S3→S4.

## Methodology Attribution

Phase space regime classification approach inspired by Bruce H. Dean, Ph.D. (@QuantSymplectic). VIX regime regions derived from public posts (Mar 2026). This sprint implements threshold-based classification only; SINDy-based flow field analysis deferred.

# Sprint 27.6: Regime Intelligence

> *Post-adversarial-review revision. Changes from review: C1 (confidence formula), C2 (breadth rename + semantics), C3 (intraday thresholds), I1–I7 (clarifications), new deliverable §12 (RegimeHistoryStore).*

## Goal

Replace the single-dimension `MarketRegime` enum with a multi-dimensional `RegimeVector` that captures trend, volatility, breadth, correlation, sector rotation, and intraday character — all computed from existing data sources (Databento + FMP) at zero additional cost. This is the data-quality foundation for the entire intelligence architecture (DEC-358 §3): every downstream consumer (Learning Loop, Experiment Registry, Counterfactual Engine) depends on accurate regime labels.

## Scope

### Deliverables

1. **`RegimeVector` frozen dataclass** with 6 dimensions: trend (score + conviction), volatility (level + direction), breadth (`universe_breadth_score` + thrust), correlation (average + regime string), sector rotation (phase + leading/lagging sectors), intraday character (opening drive + 30min range ratio + VWAP slope + direction change count + character classification). Includes backward-compatible `primary_regime: MarketRegime` and `regime_confidence: float`.

2. **`BreadthCalculator`** — subscribes to 1-minute CandleEvents via Event Bus, maintains per-symbol rolling close in fixed-size deques (`ma_period` bars, default 20 = 20 minutes), produces `universe_breadth_score` (-1.0 to +1.0) and `breadth_thrust` (bool when thrust threshold exceeded). This measures **intraday universe participation breadth** — the fraction of the tradeable universe participating in the current intraday move — NOT traditional multi-day market breadth (which would require daily bars). The metric answers: "how broad is the current intraday move across the symbols ARGUS can actually trade?" Field naming uses `universe_breadth_score` to prevent confusion with traditional breadth indicators. Returns `None` for all outputs until `min_bars_for_valid` candles (default 10) have been accumulated per symbol — see I1 ramp-up handling in acceptance criteria.

3. **`MarketCorrelationTracker`** — computes rolling 20-day pairwise correlation from daily return data for the top N symbols ranked by average daily volume from the Universe Manager's reference cache (no additional API calls for symbol selection). Daily return data fetched via FMP `fetch_daily_bars()` during pre-market, parallelized with `asyncio.gather()`. File-based JSON cache keyed by calendar date to avoid recomputation on same-day restart; cache auto-invalidates when current date > cache date.

4. **`SectorRotationAnalyzer`** — fetches FMP `/stable/sector-performance` during pre-market. Classifies rotation phase (risk_on / risk_off / mixed / transitioning). Identifies top 3 leading and bottom 3 lagging sectors. Circuit breaker on 403 (DEC-323 pattern).

5. **`IntradayCharacterDetector`** — analyzes SPY 1-minute candles from Databento stream to classify intraday character at configurable timestamps (default: 9:35, 10:00, 10:30 AM ET). Subscribes to CandleEvents filtered to SPY only.

   **Intermediate metrics (computed, exposed as fields):**
   - `opening_drive_strength` (float, 0.0–1.0): Magnitude of the first N minutes' directional move relative to the stock's ATR. `abs(close[9:30+N] - open[9:30]) / atr_20`. Clamped to [0.0, 1.0].
   - `first_30min_range_ratio` (float, >0.0): Range of first 30 minutes relative to prior day's full range. `(high_30min - low_30min) / prior_day_range`. Values >1.0 indicate an unusually wide opening.
   - `vwap_slope` (float): Linear regression slope of VWAP over accumulated bars, normalized by price. Positive = upward drift, negative = downward drift. Near-zero = flat.
   - `direction_change_count` (int): Number of times the 5-bar close direction flips sign within the classification window.

   **Classification rules (applied at each classification timestamp):**
   - **Trending:** `opening_drive_strength >= 0.4` AND `direction_change_count <= 2` AND `abs(vwap_slope) >= vwap_slope_trending_threshold` (default 0.0002)
   - **Breakout:** `first_30min_range_ratio >= 1.2` AND `opening_drive_strength >= 0.5` (wide range + strong drive — a gap-and-go or range expansion day)
   - **Reversal:** `opening_drive_strength >= 0.3` AND `direction_change_count >= 1` AND current price has crossed back through VWAP (sign of vwap_slope flipped vs first 5 bars)
   - **Choppy:** None of the above conditions met (default/fallback)
   - Priority order: Breakout > Reversal > Trending > Choppy (first match wins when multiple conditions overlap)

   **All classification thresholds are configurable via `IntradayConfig`.**

   Returns `None` for all fields before the first classification timestamp. If insufficient SPY candle data at a classification time (< `min_spy_bars` candles since 9:30, default 3), that classification returns `None` and retries at the next timestamp with accumulated data.

6. **`RegimeClassifierV2`** — composes all 5 calculators + existing trend/vol logic. Produces full `RegimeVector`. V2's `classify()` method delegates to V1's `RegimeClassifier.classify()` internally for `primary_regime` computation — it does NOT reimplement the V1 logic. V2 holds a V1 `RegimeClassifier` instance and calls it with the same SPY inputs. This makes backward compatibility trivially provable: same code path, same result. The V2 layer then queries its calculators to populate the remaining RegimeVector dimensions around the V1-produced `primary_regime`.

   `RegimeClassifierV2` accepts all calculator instances as `Optional` constructor parameters (default `None`). When a calculator is `None`, that RegimeVector dimension uses default/neutral values. This enables backtest mode: `RegimeClassifierV2(config, breadth=None, correlation=None, sector=None, intraday=None)` produces RegimeVectors with only trend+vol populated (identical to V1 behavior). Live mode: all calculators injected at construction in main.py.

   Pre-market initialization: `RegimeClassifierV2.run_pre_market()` runs `MarketCorrelationTracker.compute()` and `SectorRotationAnalyzer.fetch()` concurrently via `asyncio.gather()`. Total pre-market addition: ~10–15 seconds (parallel), not ~35 seconds (sequential).

7. **Config: `config/regime.yaml`** + `RegimeIntelligenceConfig` Pydantic model wired into `SystemConfig`. Config-gated via `regime_intelligence.enabled`. Per-dimension enable/disable.

8. **Orchestrator integration** — `reclassify_regime()` uses V2 when enabled. `RegimeChangeEvent` gains an optional `regime_vector_summary: Optional[dict]` field containing the output of `RegimeVector.to_dict()`. Existing consumers ignore this field (backward compatible). Event Bus message size increase is negligible (~500 bytes of JSON per regime change, occurring at most every 300s). `primary_regime` used for existing `allowed_regimes` filtering (unchanged).

9. **BacktestEngine integration** — `_compute_regime_tags()` extended to use V2 for trend + vol dimensions (identical results to V1 for those dimensions). BacktestEngine constructs `RegimeClassifierV2` with all calculators as `None` — verified that this produces identical results to V1. Breadth/correlation/sector/intraday not available in historical backtest.

10. **`RegimeOperatingConditions`** dataclass + `matches_conditions()` method on `RegimeVector` — range-based matching for future micro-strategy operating windows. Strategy YAML schema extension. No strategy wiring yet (Sprint 34+ consumers).

11. **Observatory regime visualization** — extend session vitals bar to display RegimeVector dimensions.

12. **`RegimeHistoryStore`** — SQLite persistence for RegimeVector snapshots in `data/regime_history.db` (separate DB file, following evaluation.db separation pattern from DEC-345). Writes one row per `reclassify_regime()` call (~every 300s during market hours, ~78 rows/day). Schema:

    | Column | Type | Description |
    |--------|------|-------------|
    | id | TEXT (ULID) | Primary key |
    | timestamp | TEXT (ISO 8601) | ET timestamp of classification |
    | trading_date | TEXT (YYYY-MM-DD) | ET trading date |
    | primary_regime | TEXT | MarketRegime.value string |
    | regime_confidence | REAL | 0.0–1.0 |
    | trend_score | REAL | Trend dimension score |
    | trend_conviction | REAL | Trend conviction |
    | volatility_level | TEXT | Vol bucket string |
    | volatility_direction | REAL | Vol direction ratio |
    | universe_breadth_score | REAL | Nullable — None during ramp-up |
    | breadth_thrust | INTEGER | 0/1, nullable |
    | avg_correlation | REAL | Nullable |
    | correlation_regime | TEXT | Nullable |
    | sector_rotation_phase | TEXT | Nullable |
    | intraday_character | TEXT | Nullable |
    | regime_vector_json | TEXT | Full RegimeVector.to_dict() as JSON blob (escape hatch for future dimensions) |

    Indexes: `(trading_date)`, `(primary_regime, trading_date)`. 7-day retention (matching evaluation.db pattern). Cleanup runs on startup.

    Query API: `get_regime_history(trading_date: str) -> list[dict]`, `get_regime_at_time(timestamp: datetime) -> Optional[dict]`, `get_regime_summary(trading_date: str) -> dict` (returns dominant regime, transition count, avg confidence for the day).

    Write path: Called from `reclassify_regime()` in Orchestrator after RegimeVector construction. Fire-and-forget with try/except guard — write failures logged at WARNING, never disrupt regime classification. Rate-limited warning (1 per 60s) on write failure, matching evaluation telemetry pattern.

    Config-gated: only writes when `regime_intelligence.enabled: true` AND `regime_intelligence.persist_history: true` (default `true`).

### Acceptance Criteria

1. **RegimeVector:**
   - All 6 dimensions present with correct types and ranges
   - `primary_regime` matches V1 classification for identical inputs
   - `regime_confidence` computed (0.0–1.0) as the product of two factors:
     1. **Signal clarity** (0.0–1.0): How unambiguously the V1 trend/vol inputs map to a single regime.
        - Crisis override active → 0.95
        - Strong trend (abs(trend_score) >= 2) + clear vol bucket → 0.85
        - Moderate trend (abs(trend_score) == 1) + confirming vol → 0.70
        - Conflicting signals (e.g., bullish trend + high vol) → 0.50
        - Indeterminate / range-bound fallback → 0.40
     2. **Data completeness** (0.0–1.0): Fraction of enabled RegimeVector dimensions that have real (non-default) data.
        - `data_completeness = dimensions_with_real_data / enabled_dimensions`
        - If all enabled dimensions have data: 1.0
        - If only trend+vol have data (breadth/correlation/sector/intraday defaulted): ~0.33 (2/6)
     - Final: `regime_confidence = signal_clarity * data_completeness`
     - Clamped to [0.0, 1.0]
   - Serialization to/from dict works (JSON-compatible)
   - Frozen (immutable after construction)

2. **BreadthCalculator:**
   - Correctly tracks % of symbols above intraday rolling MA (1-minute bars, `ma_period` default 20)
   - `universe_breadth_score` range: -1.0 to +1.0
   - `breadth_thrust = True` when thrust threshold exceeded (configurable, default 80%)
   - Handles pre-market (no candles) → returns `None` for all outputs
   - Handles ramp-up period via `min_bars_for_valid` threshold (default 10):
     - A symbol only contributes to breadth computation once it has accumulated >= `min_bars_for_valid` candles
     - If fewer than `min_symbols` symbols have sufficient bars, all breadth outputs return `None`
     - Once thresholds are met, breadth is computed from the symbols that qualify
     - Breadth data unavailable for approximately the first 10 minutes of trading (9:30–9:40 AM) — acceptable because ORB strategies fire at 9:35+ and can operate without breadth data via `regime_confidence` degradation
   - Memory bounded: fixed-size deques per symbol
   - Does not block candle processing (O(1) per candle update)

3. **MarketCorrelationTracker:**
   - Produces average pairwise correlation for top N symbols (ranked by avg daily volume from Universe Manager reference cache)
   - `correlation_regime` correctly classified: dispersed (<0.3), normal (0.3–0.6), concentrated (>0.6)
   - File cache keyed by calendar date (ET): reuses cache if `cache_date == today`, recomputes if `cache_date < today`
   - Cache stored at `data/correlation_cache.json` with schema `{"date": "YYYY-MM-DD", "symbols": [...], "average_correlation": float, "correlation_regime": str}`
   - On cache miss or stale date: full recomputation via FMP daily bars
   - Graceful degradation when daily bars unavailable → neutral defaults
   - Handles edge cases: single symbol, all identical returns, missing data

4. **SectorRotationAnalyzer:**
   - Correctly classifies risk_on / risk_off / mixed / transitioning
   - Identifies top 3 leading and bottom 3 lagging sectors by relative strength
   - Circuit breaker on FMP 403: degrades to `mixed` with empty leading/lagging
   - Does not crash or block startup if FMP unavailable

5. **IntradayCharacterDetector:**
   - Classifies intraday character at configurable timestamps (default 9:35, 10:00, 10:30 AM ET)
   - All intraday fields `None` before first classification time
   - If insufficient SPY candle data at a classification time (< `min_spy_bars`, default 3), returns `None` and retries at next timestamp
   - Classification matches rules for known test vectors:
     - SPY opens strong (+0.5%), drifts higher with 1 pullback → Trending
     - SPY gaps up 1.5%, continues higher with wide range → Breakout
     - SPY opens down 0.4%, reverses through VWAP by 10:00 → Reversal
     - SPY oscillates +/-0.1% with 4+ direction changes → Choppy
   - Priority ordering: Breakout > Reversal > Trending > Choppy verified when multiple conditions overlap
   - All thresholds are read from IntradayConfig (not hardcoded)
   - Uses SPY candles only (not full universe)

6. **RegimeClassifierV2:**
   - Composes all calculators into unified RegimeVector
   - `classify()` returns identical `MarketRegime` as V1 for identical SPY inputs
   - V2 internally delegates to V1 `RegimeClassifier` for `primary_regime` — verified by code inspection (no reimplementation of trend/vol scoring)
   - Golden-file parity test: 100 trading days of SPY daily bars → V1 regime tags frozen as fixture → V2 must produce bit-for-bit identical tags
   - Config-gated: `enabled: false` → V1 behavior, zero V2 code paths execute
   - Individual dimension disable → that dimension uses defaults, others compute
   - All calculator parameters Optional (default None) — backtest mode works with no calculators

7. **Config:**
   - `config/regime.yaml` loads correctly
   - All YAML fields match Pydantic model fields (no silently ignored keys)
   - Defaults are sensible (system works out-of-box without regime.yaml)

8. **Orchestrator integration:**
   - `reclassify_regime()` uses V2 when enabled, V1 when disabled
   - `RegimeChangeEvent` contains `regime_vector_summary: Optional[dict]`
   - `allowed_regimes` filtering unchanged (uses `primary_regime`)
   - Existing strategy activation/suspension logic unchanged

9. **BacktestEngine:**
   - `_compute_regime_tags()` returns identical results for existing test data
   - Uses V2 trend + vol dimensions (same logic as V1)
   - BacktestEngine constructs `RegimeClassifierV2` with all calculators as `None` — verified identical to V1
   - Golden-file parity: same 100-day SPY fixture as §6 golden-file test
   - No regression in backtest results

10. **Operating Conditions:**
    - `RegimeOperatingConditions` supports range constraints on all RegimeVector float dimensions
    - `RegimeVector.matches_conditions()` returns True/False correctly for known test cases
    - Strategy YAML schema accepts `operating_conditions` section (parsed, not wired)

11. **Observatory:**
    - Session vitals bar displays regime dimensions
    - Handles None/missing dimensions gracefully
    - No JavaScript errors when RegimeVector data unavailable

12. **RegimeHistoryStore:**
    - Writes one row per reclassify_regime() call during market hours
    - Query by trading_date returns all snapshots for that day in chronological order
    - Query by timestamp returns the most recent snapshot at or before that time
    - 7-day retention enforced on startup
    - Write failures do not affect regime classification (fire-and-forget)
    - Config-gate: `persist_history: false` → zero writes, store not initialized
    - Separate DB file (`data/regime_history.db`) — no write contention with argus.db or evaluation.db

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| BreadthCalculator per-candle update | < 1ms | Timer in test with 5,000 symbols |
| Pre-market V2 initialization (correlation + sector) | < 20 seconds (parallel) | Timer in integration test wrapping `run_pre_market()` |
| SectorRotationAnalyzer startup | < 5 seconds (including FMP call) | Timer in test |
| RegimeVector construction | < 0.1ms | Timer in unit test |
| Config-gate overhead when disabled | 0 (no new code paths) | Code inspection + test |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `regime_intelligence.enabled` | `RegimeIntelligenceConfig` | `enabled` | `True` |
| `regime_intelligence.persist_history` | `RegimeIntelligenceConfig` | `persist_history` | `True` |
| `regime_intelligence.breadth.enabled` | `BreadthConfig` | `enabled` | `True` |
| `regime_intelligence.breadth.ma_period` | `BreadthConfig` | `ma_period` | `20` |
| `regime_intelligence.breadth.thrust_threshold` | `BreadthConfig` | `thrust_threshold` | `0.80` |
| `regime_intelligence.breadth.min_symbols` | `BreadthConfig` | `min_symbols` | `50` |
| `regime_intelligence.breadth.min_bars_for_valid` | `BreadthConfig` | `min_bars_for_valid` | `10` |
| `regime_intelligence.correlation.enabled` | `CorrelationConfig` | `enabled` | `True` |
| `regime_intelligence.correlation.lookback_days` | `CorrelationConfig` | `lookback_days` | `20` |
| `regime_intelligence.correlation.top_n_symbols` | `CorrelationConfig` | `top_n_symbols` | `50` |
| `regime_intelligence.correlation.dispersed_threshold` | `CorrelationConfig` | `dispersed_threshold` | `0.30` |
| `regime_intelligence.correlation.concentrated_threshold` | `CorrelationConfig` | `concentrated_threshold` | `0.60` |
| `regime_intelligence.sector_rotation.enabled` | `SectorRotationConfig` | `enabled` | `True` |
| `regime_intelligence.intraday.enabled` | `IntradayConfig` | `enabled` | `True` |
| `regime_intelligence.intraday.first_bar_minutes` | `IntradayConfig` | `first_bar_minutes` | `5` |
| `regime_intelligence.intraday.classification_times` | `IntradayConfig` | `classification_times` | `["09:35", "10:00", "10:30"]` |
| `regime_intelligence.intraday.min_spy_bars` | `IntradayConfig` | `min_spy_bars` | `3` |
| `regime_intelligence.intraday.drive_strength_trending` | `IntradayConfig` | `drive_strength_trending` | `0.4` |
| `regime_intelligence.intraday.drive_strength_breakout` | `IntradayConfig` | `drive_strength_breakout` | `0.5` |
| `regime_intelligence.intraday.drive_strength_reversal` | `IntradayConfig` | `drive_strength_reversal` | `0.3` |
| `regime_intelligence.intraday.range_ratio_breakout` | `IntradayConfig` | `range_ratio_breakout` | `1.2` |
| `regime_intelligence.intraday.vwap_slope_trending` | `IntradayConfig` | `vwap_slope_trending` | `0.0002` |
| `regime_intelligence.intraday.max_direction_changes_trending` | `IntradayConfig` | `max_direction_changes_trending` | `2` |

## Dependencies

- Sprint 27.5 (Evaluation Framework) — complete. `RegimeMetrics` in `MultiObjectiveResult` uses string keys, forward-compatible with RegimeVector.
- Databento EQUS.MINI feed — existing subscription, no changes.
- FMP Starter plan — existing subscription. `/stable/sector-performance` endpoint availability unconfirmed on Starter (may return 403 like news endpoints). Circuit breaker handles graceful degradation.
- FMP `fetch_daily_bars()` — existing method in `DatabentoDataService`, used by MarketCorrelationTracker for pre-market daily bar retrieval.
- Universe Manager reference cache — used by MarketCorrelationTracker for top-N-by-volume symbol selection (no additional API calls).

## Relevant Decisions

- DEC-358 §3: Intelligence Architecture amendment — specifies RegimeVector multi-dimensional classification, 6 dimensions, data sources, file structure, session breakdown.
- DEC-346: Periodic regime reclassification — 300s interval, market hours only. V2 hooks into this existing cadence.
- DEC-347: FMP daily bars for regime classification — `fetch_daily_bars()` via FMP stable API.
- DEC-323: FMP circuit breaker on 401/403 — pattern for SectorRotationAnalyzer graceful degradation.
- DEC-300: Config-gated features — established pattern for `regime_intelligence.enabled`.
- DEC-277: Fail-closed on missing reference data.
- DEC-345: Evaluation telemetry DB separation — pattern for `regime_history.db`.
- DEC-360: All 7 strategies allow `bearish_trending` regime — only `crisis` is a universal block.

## Relevant Risks

- RSK-022: IBKR Gateway nightly resets — not directly affected, but regime reclassification must handle data gaps during gateway reconnection.
- New risk: FMP `/stable/sector-performance` may not be available on Starter plan. Impact: SectorRotationAnalyzer degrades to neutral. Mitigation: circuit breaker + graceful degradation.

## Session Count Estimate

10 sessions + 0.5 contingency for visual-review fixes. RegimeHistoryStore persistence absorbed into S6 (integration session). Golden-file parity test absorbed into S8 (E2E tests). All sessions <= 13 on compaction risk scale. S3 + S4 + S5 are parallelizable.

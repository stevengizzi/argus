# Sprint 24 — Adversarial Review Revision Rationale

> Records all spec changes resulting from the adversarial review.
> Generated after adversarial review, before Phase D (prompt generation).

---

## Finding 1: Backtest Compatibility — ACCEPTED (Hybrid A+C)

**Change:** Added backtest bypass to signal flow wiring. When `broker_source == BrokerSource.SIMULATED`, the quality pipeline is skipped and legacy strategy-calculated sizing is used. The bypass computes shares using the strategy's original formula (`allocated_capital × risk_per_trade_pct / risk_per_share`) from `signal.pattern_strength` context data. `backtest/*` files remain unmodified — the bypass lives in `main.py`.

**Spec-by-Contradiction updated:** Carve-out added permitting backtest detection in main.py signal flow. `backtest/*` files still protected.

**Session impact:** Session 6a scope expanded to include legacy bypass branch. Session 6b includes bypass verification tests.

---

## Finding 2: Config Gating — ACCEPTED

**Change:** Added `quality_engine.enabled: true` (default true). When disabled, signal flow falls through to legacy sizing path (same code branch as backtest bypass). Provides rollback during paper trading and A/B comparison at Sprint 28.

**Config impact:** New field in `QualityEngineConfig`. Added to both `system.yaml` and `system_live.yaml`.

**Design Summary update:** Removed "no config gating" decision. Replaced with "config-gated, default enabled."

---

## Finding 3: On-Demand Catalyst Lookup — ACCEPTED (Simplified to DB Query)

**Change:** On-demand live API fetch concept REMOVED from scope. At signal time, the Quality Engine queries `catalyst.db` via `CatalystStorage.get_catalysts_by_symbol()`. This is a local SQLite query (<100ms). The firehose polling loop is responsible for keeping catalyst.db current. If no catalyst data exists for a symbol, catalyst dimension scores 50 (neutral).

**Scope reduction:** `on_demand_catalyst_lookup` and `catalyst_freshness_minutes` config fields removed. Session 7 simplified: no on-demand fetch method on Quality Engine, no timeout logic. Per-symbol source methods still retained (existing code, not new work) but not called from quality engine.

**Session impact:** Session 7 scope reduced. Score drops from 14.5 to ~11.

---

## Finding 4: CQ Aggregation — ACCEPTED (Dimension Scoring Rubrics Added)

**Change:** Added explicit scoring rubrics for all 5 dimensions to the Sprint Spec:

- **Pattern Strength (30%):** Passthrough from `signal.pattern_strength` (0–100).
- **Catalyst Quality (25%):** Max `quality_score` from catalysts published in last 24h for symbol. Empty list → 50 (neutral). Rationale: one strong catalyst is sufficient; averaging dilutes.
- **Volume Profile (20%):** RVOL breakpoint mapping with linear interpolation. RVOL ≤0.5→10, 1.0→40, 2.0→70, ≥3.0→95. None→50.
- **Historical Match (15%):** Constant 50 (V1 stub).
- **Regime Alignment (10%):** Current regime in strategy's allowed_regimes → 80. Not in list → 20. Empty allowed_regimes (accepts all) → 70.

---

## Finding 5: Score Range Compression — ACCEPTED (Documentation)

**Change:** Config YAML comment added noting effective range ~7.5–92.5 with HM stub. Thresholds marked as PROVISIONAL pending Sprint 28 recalibration. Spec notes A+ rarity is acceptable for initial paper trading validation.

---

## Finding 6: share_count=0 Downstream Guard — ACCEPTED

**Change:** Risk Manager `evaluate_signal()` gets a check 0 (before circuit breaker): reject if `signal.share_count <= 0`. One-line defensive guard.

**Spec-by-Contradiction updated:** Carve-out added permitting this specific one-line guard on `risk_manager.py`.

**Session impact:** Added to Session 6a scope. Tests include zero-share rejection.

---

## Finding 7: Session 6 Split — ACCEPTED

**Change:** Session 6 split into:
- **6a (Pipeline Wiring + Unit Tests):** main.py wiring, legacy bypass, RM guard, record_quality_history, unit tests per branch. Score: 14.
- **6b (Integration Tests + Error Paths):** Full pipeline integration tests, error paths, backtest bypass verification. Score: 8.

Total session count: 13 sessions + contingency (was 12).

---

## Finding 8: Weight Sum Validation — ACCEPTED (Clarified)

**Change:** Spec explicitly states: Pydantic `@model_validator` on `QualityWeightsConfig` validates `sum(weights) == 1.0` (±0.001). Startup fails with `ValidationError`. Consistent with DEC-032.

---

## Finding 9: Risk Tier Interpolation — ACCEPTED (Flat Midpoint)

**Change:** Spec clarified: risk percentage is the midpoint of the grade's range, flat within the grade. Score of 80 and 89 both get `(1.5+2.0)/2 = 1.75%`. Simpler to implement and debug. Grade boundaries provide 8 levels of differentiation.

---

## Finding 10: QualitySignalEvent Clarification — ACCEPTED

**Change:** Spec clarified: QualitySignalEvent is a separate informational event for UI consumers, published in addition to the enriched SignalEvent. It does not participate in the execution pipeline. Risk Manager receives the standard enriched SignalEvent (same type, quality fields populated).

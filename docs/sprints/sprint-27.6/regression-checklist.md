# Sprint 27.6: Regression Checklist

## Critical Invariants

- [ ] **V1 backward compatibility:** `RegimeClassifier.classify()` returns identical `MarketRegime` for all 5 regime types given identical SPY inputs. V2 delegates to V1 internally (no reimplementation). Run V1 and V2 side-by-side on test data and assert equality.

- [ ] **Golden-file parity:** 100 trading days of SPY daily bars → V1 regime tags frozen as fixture → V2 must produce bit-for-bit identical tags. Same fixture used in both V2 unit tests and BacktestEngine integration tests.

- [ ] **Orchestrator allowed_regimes unchanged:** Strategy activation/suspension uses `primary_regime` from RegimeVector (or MarketRegime from V1 when disabled). No strategy sees different allowed_regimes behavior.

- [ ] **RegimeChangeEvent contract preserved:** `old_regime` and `new_regime` fields remain `str` (MarketRegime.value). Any new fields are additive (optional), not breaking.

- [ ] **BacktestEngine regime tags identical:** `_compute_regime_tags()` returns same `dict[date, str]` for existing test data with V2 as with V1.

- [ ] **MultiObjectiveResult unmodified:** `evaluation.py`, `comparison.py`, `ensemble_evaluation.py` have zero changes. `regime_results` key structure unchanged.

- [ ] **Config-gate isolation:** When `regime_intelligence.enabled: false`:
  - No BreadthCalculator, MarketCorrelationTracker, SectorRotationAnalyzer, or IntradayCharacterDetector instances are created
  - No Event Bus subscriptions for new components
  - No FMP calls for sector performance or daily bars beyond existing usage
  - `reclassify_regime()` uses V1 `RegimeClassifier` only
  - Zero performance impact

- [ ] **No candle processing degradation:** BreadthCalculator Event Bus subscription does not add measurable latency to the candle processing path. Test with 5,000 symbols.

- [ ] **Pre-market startup bounded:** MarketCorrelationTracker + SectorRotationAnalyzer run concurrently via asyncio.gather(), combined < 20 seconds.

- [ ] **RegimeHistoryStore fire-and-forget:** Write failures in regime_history.db do not affect reclassify_regime() return value or timing. Rate-limited warning (1 per 60s).

- [ ] **New config fields verified against Pydantic model:** All keys in `config/regime.yaml` are recognized by `RegimeIntelligenceConfig` and sub-models. No silently ignored fields. Test loads YAML and verifies all keys match model fields.

- [ ] **All existing tests pass:** Full suite: 3,177 pytest + 620 Vitest, 0 failures.

## Component-Level Checks

- [ ] **BreadthCalculator memory bounded:** Fixed-size deques enforce per-symbol memory limit. No unbounded growth with increasing symbol count.

- [ ] **MarketCorrelationTracker file cache deterministic:** Same input data → same cache file → same correlation values on reload.

- [ ] **SectorRotationAnalyzer circuit breaker:** FMP 403 → graceful degradation, no crash, no retry spam.

- [ ] **IntradayCharacterDetector time boundaries:** No classification before 9:35 AM ET. All intraday fields None pre-market.

- [ ] **RegimeVector immutability:** Frozen dataclass prevents mutation after construction.

- [ ] **RegimeVector serialization roundtrip:** `from_dict(rv.to_dict()) == rv` for all field combinations including None intraday fields.

- [ ] **No circular imports:** All new modules importable without circular dependency errors.

- [ ] **Do-not-modify files untouched:** `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, `databento_data_service.py`, all `strategies/*.py`, all `intelligence/*.py`, all `execution/*.py`, all `ai/*.py`.

## Frontend Checks (S10)

- [ ] **Observatory session vitals displays regime dimensions:** All 6 dimensions rendered.
- [ ] **Handles None/missing data:** No JS errors when RegimeVector unavailable or intraday fields null.
- [ ] **No regression in existing Observatory views:** Funnel, Radar, Matrix, Timeline still functional.

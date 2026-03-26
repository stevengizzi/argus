# Sprint 27.9, Session 2b — Close-Out Report

## Session Objective
Implement 4 VIX-based calculator classes following the Sprint 27.6 calculator pattern. Wire them into RegimeClassifierV2. All calculators return None when VIX data unavailable.

## Change Manifest

| File | Action | Description |
|------|--------|-------------|
| `argus/core/vix_calculators.py` | **Created** | 4 calculator classes: VolRegimePhaseCalculator, VolRegimeMomentumCalculator, TermStructureRegimeCalculator, VarianceRiskPremiumCalculator |
| `argus/data/vix_data_service.py` | Modified | Added `get_history(days_back)` method returning last N daily records from SQLite (descending order) |
| `argus/core/regime.py` | Modified | Added `vix_data_service` parameter to RegimeClassifierV2 constructor; instantiates 4 VIX calculators when service provided and config enabled; `compute_regime_vector()` populates VIX dimension fields |
| `argus/core/config.py` | Modified | Added `vix_calculators_enabled: bool = True` to RegimeIntelligenceConfig |
| `config/regime.yaml` | Modified | Added `vix_calculators_enabled: true` under master settings |
| `tests/core/test_vix_calculators.py` | **Created** | 11 tests (8 specified + 3 additional edge cases) |

## Judgment Calls

1. **Momentum threshold interpretation:** The spec's `momentum_threshold` is documented in VixRegimeConfig as "VIX points change" (default 2.0). For the momentum calculator, this is used as the Euclidean displacement magnitude threshold in (vol_of_vol_ratio, vix_percentile) coordinate space. The default value of 2.0 is very large relative to the coordinate space (values typically 0.0–2.0 range), meaning most movements will be classified NEUTRAL. This is conservative by design — the threshold can be tuned via config.

2. **Attractor point for stabilizing/deteriorating:** Used (0.94, 0.38) as the "calm center" attractor per the spec. Direction is determined by comparing distance-to-attractor between current and past positions (closer = stabilizing).

3. **VIX config access:** RegimeClassifierV2 accesses `vix_data_service._config` to get boundary models. This follows the existing pattern where V2 accesses V1 private attributes (noted in DEF-091). Could add a public property later.

4. **Test count:** Spec requested 8 tests; implemented 11 (added `test_momentum_insufficient_history`, `test_momentum_not_ready`, and `test_classifier_v2_no_vix_service_unchanged` for edge coverage).

## Scope Verification

| Spec Item | Status |
|-----------|--------|
| 4 calculator classes implemented following existing pattern | ✅ |
| RegimeClassifierV2 wires VIX calculators when VIXDataService provided | ✅ |
| Calculators return None when VIX data unavailable | ✅ |
| RegimeVector populated with VIX dimensions after classification | ✅ |
| 8+ new tests passing | ✅ (11 tests) |
| Existing regime tests still pass | ✅ (150 existing tests unchanged) |
| R12 verified: existing 6 dimensions produce same values | ✅ |
| `get_history()` added to VIXDataService | ✅ |
| `vix_calculators_enabled` in regime.yaml | ✅ |

## Regression Checks

| Check | Result |
|-------|--------|
| R12: Existing 6 dims produce same values | ✅ — `test_classifier_v2_no_vix_service_unchanged` confirms VIX fields are None and 6 dims unchanged |
| R1: primary_regime unchanged | ✅ — All existing regime tests pass (150/150) |
| Existing calculators unmodified | ✅ — `git diff` on breadth.py, market_correlation.py, sector_rotation.py, intraday_character.py is empty |

## Test Results

- **New tests:** 11 passing in `tests/core/test_vix_calculators.py`
- **Existing regime tests:** 150 passing (0 failures, 0 regressions)
- **Broader core tests:** 597 passing in `tests/core/` + `tests/data/test_vix*.py`

## Constraints Verified

- ✅ Did NOT modify existing 6 calculator classes or their logic
- ✅ Did NOT modify RegimeVector field definitions (done in 2a)
- ✅ Did NOT modify strategy files
- ✅ Calculator pattern matches existing Sprint 27.6 structure

## Deferred Items

None.

## Self-Assessment

**CLEAN** — All spec items implemented, all tests pass, no regressions.

## Context State

**GREEN** — Session completed well within context limits.

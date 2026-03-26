# Sprint 27.9, Session 2b — Tier 2 Review Report

---BEGIN-REVIEW---

## Summary

Session 2b implements four VIX-based calculator classes (`VolRegimePhaseCalculator`,
`VolRegimeMomentumCalculator`, `TermStructureRegimeCalculator`,
`VarianceRiskPremiumCalculator`) in a new file `argus/core/vix_calculators.py`, wires
them into `RegimeClassifierV2`, adds `get_history()` to `VIXDataService`, and adds the
`vix_calculators_enabled` config flag. 11 new tests cover the calculators and V2
integration. All 161 regime-related tests pass.

## Review Focus Findings

### 1. CRISIS check priority in VolRegimePhaseCalculator
**PASS.** Line 77 of `vix_calculators.py` checks `y >= bounds.crisis_min_y` before
CALM and TRANSITION checks. Comment "# CRISIS check first (highest priority)" is
present. Matches the spec exactly.

### 2. All 4 calculators return None when VIXDataService returns None
**PASS.** Each calculator's `classify()` method:
- Checks `is_ready` and `is_stale` first (returns None if not ready or stale)
- Checks `get_latest_daily()` result for None (returns None)
- Checks individual metric fields for None (returns None)
The momentum calculator additionally returns None when history has < 2 records.

### 3. Existing 6 calculator outputs identical with and without VIXDataService
**PASS.** Test `test_classifier_v2_no_vix_service_unchanged` explicitly verifies that
when `vix_data_service=None`, all 5 VIX fields are None while existing dimensions
(`trend_score`, `volatility_level`, `primary_regime`) remain populated. The diff shows
VIX calculator results are only populated after the existing 6-dimension computation
block, with no modifications to existing logic paths.

### 4. RegimeClassifierV2 constructor accepts VIXDataService=None gracefully
**PASS.** The constructor initializes all 4 calculator references to None. The conditional
`if vix_data_service is not None and regime_config.vix_calculators_enabled:` gates
calculator instantiation. No exception path when None is passed.

### 5. Momentum calculator handles insufficient history
**PASS.** Line 127: `if history is None or len(history) < 2: return None`. Test
`test_momentum_insufficient_history` covers the single-record case. Test
`test_momentum_not_ready` covers the `is_ready=False` case.

### 6. All 4 calculators present (compaction check)
**PASS.** Close-out reports GREEN context state. All 4 calculators are present in
`vix_calculators.py` (lines 35, 89, 166, 217). The file is 273 lines total, well-formed.

## Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R1 | `primary_regime` identical to pre-sprint | PASS -- 161 regime tests pass, no changes to V1 classification |
| R12 | Existing 6 dims produce same values | PASS -- explicit test + no modification to existing compute path |
| R15 | Existing API endpoints unaffected | PASS -- no API route files modified |

## Do-Not-Modify Verification

`git diff HEAD -- argus/core/breadth.py argus/core/market_correlation.py argus/core/sector_rotation.py argus/core/intraday_character.py argus/strategies/ argus/execution/` produced empty output. All protected files are unmodified.

## Escalation Criteria Check

| # | Criterion | Triggered? |
|---|-----------|------------|
| 1 | yfinance cannot fetch | N/A (no yfinance changes this session) |
| 2 | RegimeVector extension breaks primary_regime | No |
| 3 | Existing calculator behavior changes | No -- zero diff on existing calculator files |
| 4 | Strategy activation conditions change | No |
| 5 | Quality scores or position sizes change | No |
| 6 | SINDy complexity creep | No |
| 7 | Server startup fails with VIX enabled | N/A (no startup wiring this session) |

## Findings

### F1: Private attribute access on VIXDataService (LOW)
`regime.py` line 691 accesses `vix_data_service._config` to extract boundary models.
The close-out acknowledges this as a judgment call consistent with the existing DEF-091
pattern (V2 already accesses V1 private attributes). This is acceptable for now but
compounds the DEF-091 debt. A `@property config` accessor on `VIXDataService` would be
the clean fix.

### F2: Momentum threshold default likely too large (INFORMATIONAL)
The close-out correctly flags that the default `momentum_threshold=2.0` is very large
relative to the (vol_of_vol_ratio, vix_percentile) coordinate space where typical
values are 0.0--2.0. Most real-world movements will classify as NEUTRAL. This is
conservative by design and tunable via config. No action needed now, but worth noting
for calibration during paper trading.

### F3: TermStructureBoundaries docstring inconsistency (INFORMATIONAL, pre-existing)
`vix_config.py` line 107 describes `contango_threshold` as "Ratio above which term
structure is contango" but the calculator uses `x <= contango_threshold` for contango
classification (matching the spec). The docstring should read "at or below which."
This is a Session 1a artifact, not introduced in 2b.

## Test Results

161 tests passed in 0.45s. No failures, no warnings (aside from standard
pytest-asyncio deprecation notice).

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "F1",
      "severity": "low",
      "category": "code-quality",
      "description": "Private attribute access on VIXDataService._config from regime.py, compounding DEF-091 debt",
      "recommendation": "Add @property config accessor to VIXDataService in a future cleanup session"
    },
    {
      "id": "F2",
      "severity": "informational",
      "category": "configuration",
      "description": "Default momentum_threshold=2.0 likely classifies most movements as NEUTRAL",
      "recommendation": "Calibrate during paper trading with real VIX data"
    },
    {
      "id": "F3",
      "severity": "informational",
      "category": "documentation",
      "description": "TermStructureBoundaries.contango_threshold docstring misleading (pre-existing from Session 1a)",
      "recommendation": "Fix docstring in future cleanup"
    }
  ],
  "tests_passed": 161,
  "tests_failed": 0,
  "regression_clear": true,
  "escalation_triggered": false,
  "session": "Sprint 27.9, Session 2b",
  "reviewer": "Tier 2 Automated Review"
}
```

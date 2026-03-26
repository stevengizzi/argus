# Sprint 27.9: Regression Checklist

## Critical Invariants

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R1 | `primary_regime` returns identical value as pre-sprint | Unit test: construct RegimeVector with original 6 fields only, assert `primary_regime` matches expected enum | 2a |
| R2 | RegimeVector construction with only original 6 fields still works | Unit test: `RegimeVector(trend=..., volatility=..., ...)` without new fields → no error, new fields are None | 2a |
| R3 | `matches_conditions()` treats None new dims as match-any | Unit test: conditions specify `vol_regime_phase=CALM`, vector has `vol_regime_phase=None` → should match | 2a |
| R4 | `to_dict()` includes all 11 fields | Unit test: assert all field names present in dict output | 2a |
| R5 | RegimeHistoryStore reads pre-sprint rows without error | Integration test: insert row without vix_close column, read back → no error, vix_close is None | 2a |
| R6 | All 7 strategies activate under same conditions as before | Regression test: with conservative YAML defaults, verify strategy activation matches pre-sprint behavior | 2c |
| R7 | Quality scores unchanged when trajectory modulation OFF | Integration test: same input → same quality_score and quality_grade | 3b |
| R8 | Position sizes unchanged | Integration test: same input → same share_count | 3b |
| R9 | BriefingGenerator produces valid brief when VIX unavailable | Unit test: mock VIXDataService returning None → brief generated without VIX section, no error | 3b |
| R10 | Server starts successfully with `vix_regime.enabled: true` | Integration test: boot with config enabled, verify startup completes | 3a |
| R11 | Server starts successfully with `vix_regime.enabled: false` | Integration test: boot with config disabled, verify no VIX components initialized | 3a |
| R12 | Existing 6 RegimeVector dimensions produce same values | Regression test: same SPY data → same trend, volatility, breadth, correlation, sector_rotation, intraday_character | 2b |
| R13 | New config fields verified against Pydantic model (no silently ignored keys) | Config validation test: load vix_regime.yaml, compare keys against VixRegimeConfig.model_fields | 1a |
| R14 | Dashboard loads without error when VIX disabled | Vitest: render DashboardPage with vix_regime.enabled=false → VixRegimeCard not rendered, no error | 4 |
| R15 | Existing API endpoints unaffected | Run existing API test suite → all pass | 3a |

## Test Commands

**Full suite (Session 1a pre-flight + all close-outs):**
```bash
python -m pytest --ignore=tests/test_main.py -n auto -x -q
```

**Scoped commands (Session 2+ pre-flights):**
```bash
# Session 1b
python -m pytest tests/data/test_vix_data_service.py tests/data/test_vix_derived_metrics.py -x -q

# Session 2a
python -m pytest tests/core/test_regime_vector_expansion.py -x -q

# Session 2b
python -m pytest tests/core/test_vix_calculators.py tests/core/test_regime_vector_expansion.py -x -q

# Session 2c
python -m pytest tests/core/ -x -q

# Session 3a
python -m pytest tests/api/test_vix_routes.py -x -q

# Session 3b
python -m pytest tests/integration/test_vix_pipeline.py tests/api/test_vix_routes.py -x -q

# Session 4
cd argus/ui && npx vitest run --reporter=verbose
```

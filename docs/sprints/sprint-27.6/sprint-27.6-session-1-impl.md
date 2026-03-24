# Sprint 27.6, Session 1: RegimeVector + RegimeClassifierV2 Shell + Config

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/regime.py` (current RegimeClassifier, MarketRegime, RegimeIndicators)
   - `argus/core/config.py` (SystemConfig, OrchestratorConfig — pattern for new config models)
   - `config/orchestrator.yaml` (existing regime config pattern)
   - `config/quality_engine.yaml` (example of feature config file)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```
   python -m pytest --ignore=tests/test_main.py -x -q -n auto
   ```
   Expected: ~3,177 tests, all passing
3. Verify you are on the correct branch: `main` (or sprint-27.6 if created)

## Objective
Establish the RegimeVector frozen dataclass, a minimal RegimeClassifierV2 shell that produces it using only trend+vol (same as V1 via delegation), and the full config infrastructure for regime intelligence.

## Requirements

1. In `argus/core/regime.py`, add `RegimeVector` frozen dataclass with these fields:
   - `computed_at: datetime`
   - `trend_score: float` (-1.0 to +1.0, continuous)
   - `trend_conviction: float` (0.0–1.0)
   - `volatility_level: float` (annualized realized vol, continuous)
   - `volatility_direction: float` (-1.0 to +1.0, vol term structure proxy)
   - `universe_breadth_score: float | None` (renamed per adversarial review C2)
   - `breadth_thrust: bool | None`
   - `average_correlation: float | None`
   - `correlation_regime: str | None` ("dispersed", "normal", "concentrated")
   - `sector_rotation_phase: str | None` ("risk_on", "risk_off", "mixed", "transitioning")
   - `leading_sectors: list[str]` (default empty)
   - `lagging_sectors: list[str]` (default empty)
   - `opening_drive_strength: float | None`
   - `first_30min_range_ratio: float | None`
   - `vwap_slope: float | None`
   - `direction_change_count: int | None`
   - `intraday_character: str | None` ("trending", "choppy", "reversal", "breakout")
   - `primary_regime: MarketRegime` (backward-compatible)
   - `regime_confidence: float` (0.0–1.0)
   Add `to_dict()` and `from_dict()` methods for JSON-compatible serialization. Handle None fields (serialize as null, deserialize as None).

2. In `argus/core/regime.py`, add `RegimeClassifierV2` class:
   - Constructor: `(config: OrchestratorConfig, regime_config: RegimeIntelligenceConfig, breadth=None, correlation=None, sector=None, intraday=None)`. All calculator params Optional, default None.
   - Holds a V1 `RegimeClassifier` instance internally — delegates to it for primary_regime.
   - `classify(indicators: RegimeIndicators) -> MarketRegime`: delegates to `self._v1_classifier.classify(indicators)`. Identical result by construction.
   - `compute_regime_vector(indicators: RegimeIndicators) -> RegimeVector`: calls V1 classify for primary_regime, computes trend_score/trend_conviction/volatility_level/volatility_direction from indicators, computes regime_confidence (signal_clarity × data_completeness per C1 spec), fills remaining dimensions from calculators (or defaults if None).
   - `compute_indicators(daily_bars) -> RegimeIndicators`: delegates to V1.

3. Implement `regime_confidence` computation per adversarial review C1:
   - Signal clarity: crisis→0.95, strong trend+clear vol→0.85, moderate+confirming→0.70, conflicting→0.50, indeterminate→0.40
   - Data completeness: dimensions_with_real_data / enabled_dimensions
   - Final: signal_clarity × data_completeness, clamped [0.0, 1.0]

4. In `argus/core/config.py`, add Pydantic models:
   - `BreadthConfig(enabled=True, ma_period=20, thrust_threshold=0.80, min_symbols=50, min_bars_for_valid=10)`
   - `CorrelationConfig(enabled=True, lookback_days=20, top_n_symbols=50, dispersed_threshold=0.30, concentrated_threshold=0.60)`
   - `SectorRotationConfig(enabled=True)`
   - `IntradayConfig(enabled=True, first_bar_minutes=5, classification_times=["09:35","10:00","10:30"], min_spy_bars=3, drive_strength_trending=0.4, drive_strength_breakout=0.5, drive_strength_reversal=0.3, range_ratio_breakout=1.2, vwap_slope_trending=0.0002, max_direction_changes_trending=2)`
   - `RegimeIntelligenceConfig(enabled=True, persist_history=True, breadth=BreadthConfig(), correlation=CorrelationConfig(), sector_rotation=SectorRotationConfig(), intraday=IntradayConfig())`
   - Wire into `SystemConfig`: `regime_intelligence: RegimeIntelligenceConfig = Field(default_factory=RegimeIntelligenceConfig)`

5. Create `config/regime.yaml` with all fields matching the Pydantic models. Use comments explaining each section.

## Constraints
- Do NOT modify: `argus/analytics/evaluation.py`, `argus/analytics/comparison.py`, `argus/core/orchestrator.py`, `argus/main.py`, `argus/strategies/*.py`
- Do NOT remove or rename V1 `RegimeClassifier` — it remains for config-gate bypass
- V2 must NOT reimplement V1 trend/vol scoring — delegate only

## Config Validation
Write a test that loads `config/regime.yaml` and verifies all keys under `regime_intelligence` are recognized by `RegimeIntelligenceConfig` and sub-models. No silently ignored fields.

## Test Targets
- Existing tests: all must still pass
- New tests to write (~12):
  - RegimeVector construction with all fields
  - RegimeVector frozen immutability
  - RegimeVector to_dict/from_dict roundtrip (including None intraday fields)
  - V2 backward compat: classify() returns same MarketRegime as V1 for all 5 regime types
  - V2 with all calculators None: produces valid RegimeVector with defaults
  - regime_confidence: signal_clarity × data_completeness for multiple scenarios
  - RegimeIntelligenceConfig default loading
  - Config validation (invalid thresholds rejected)
  - Config file loading from regime.yaml
  - SystemConfig with regime_intelligence field
  - Config silently-ignored-key detection test
  - V2 compute_regime_vector produces correct trend_score from indicators
- Minimum new test count: 12
- Test command: `python -m pytest tests/core/test_regime.py -x -q -v`

## Definition of Done
- [ ] RegimeVector frozen dataclass with all 6 dimensions + serialization
- [ ] RegimeClassifierV2 with V1 delegation and Optional calculators
- [ ] regime_confidence formula implemented (signal_clarity × data_completeness)
- [ ] All Pydantic config models + config/regime.yaml
- [ ] All existing tests pass
- [ ] 12+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| V1 RegimeClassifier unchanged | `grep -n "class RegimeClassifier:" argus/core/regime.py` — still exists, unmodified |
| V2 delegates to V1 | Code inspection: V2.__init__ creates V1 instance, classify() calls self._v1_classifier.classify() |
| SystemConfig backward compat | Existing config tests still pass |
| No circular imports | `python -c "from argus.core.regime import RegimeVector, RegimeClassifierV2"` succeeds |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
Write the close-out report to: `docs/sprints/sprint-27.6/session-1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context file: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.6/session-1-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/core/test_regime.py tests/core/test_config.py -x -q -v`
5. Files NOT to modify: `evaluation.py`, `comparison.py`, `orchestrator.py`, `main.py`, `strategies/*.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify V2 delegates to V1 for primary_regime — no reimplementation of trend/vol scoring
2. Verify RegimeVector is frozen (immutable after construction)
3. Verify regime_confidence uses the two-factor formula (signal_clarity × data_completeness)
4. Verify all Pydantic model field names match YAML keys exactly
5. Verify V1 RegimeClassifier is completely unchanged

## Sprint-Level Regression Checklist
*(See review-context.md)*

## Sprint-Level Escalation Criteria
*(See review-context.md)*

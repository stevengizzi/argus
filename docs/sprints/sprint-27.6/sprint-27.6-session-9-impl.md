# Sprint 27.6, Session 9: Operating Conditions Matching

## Pre-Flight Checks
1. Read: `argus/core/regime.py` (RegimeVector), `argus/models/strategy.py` (MarketConditionsFilter)
2. Scoped test: `python -m pytest tests/core/test_regime.py tests/models/ -x -q`
3. Verify branch

## Objective
Add `RegimeOperatingConditions` dataclass and `matches_conditions()` method to RegimeVector. Extend strategy model to accept `operating_conditions` in YAML. No strategy wiring — schema + logic only.

## Requirements

1. In `argus/core/regime.py`, add `RegimeOperatingConditions` dataclass:
   - Optional range constraints for each float dimension of RegimeVector:
     - `trend_score: tuple[float, float] | None = None` (min, max range)
     - `trend_conviction: tuple[float, float] | None = None`
     - `volatility_level: tuple[float, float] | None = None`
     - `universe_breadth_score: tuple[float, float] | None = None`
     - `average_correlation: tuple[float, float] | None = None`
     - `regime_confidence: tuple[float, float] | None = None`
   - Optional string match for classification dimensions:
     - `correlation_regime: list[str] | None = None`
     - `sector_rotation_phase: list[str] | None = None`
     - `intraday_character: list[str] | None = None`
   - None means unconstrained (always matches)

2. Add `RegimeVector.matches_conditions(conditions: RegimeOperatingConditions) -> bool`:
   - For each non-None range: check value is within [min, max] inclusive. If the RegimeVector field is None (e.g., pre-market intraday), treat as non-matching for that constraint.
   - For each non-None string list: check value is in the list. None RegimeVector field → non-matching.
   - Empty conditions (all None) → always matches (vacuously true)
   - All conditions must match (AND logic)

3. In `argus/models/strategy.py`, add `operating_conditions: RegimeOperatingConditions | None = None` field to an appropriate model (or as a standalone parsed field in strategy config). Strategy YAML files can optionally include an `operating_conditions:` section. If absent → None (backward compat).

## Constraints
- Do NOT wire operating_conditions into any strategy's `get_market_conditions_filter()` or activation logic
- Do NOT modify existing strategy files
- This is schema + matching logic only

## Test Targets
- New tests (~8) in `tests/core/test_operating_conditions.py`:
  - RegimeOperatingConditions construction
  - matches: all dimensions in range → True
  - matches: one float dimension out of range → False
  - matches: string dimension not in list → False
  - matches: None constraint → always matches
  - matches: None RegimeVector field with non-None constraint → False
  - matches: empty conditions → True (vacuously)
  - Strategy YAML with operating_conditions parses correctly
  - Strategy YAML without operating_conditions → None (backward compat)
- Minimum: 8
- Test command: `python -m pytest tests/core/test_operating_conditions.py -x -q -v`

## Definition of Done
- [ ] RegimeOperatingConditions + matches_conditions() implemented
- [ ] Strategy YAML schema extended
- [ ] Backward compatible (no existing strategy affected)
- [ ] 8+ tests passing
- [ ] Close-out: `docs/sprints/sprint-27.6/session-9-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-9-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-9-closeout.md`
3. Test command: `python -m pytest tests/core/test_operating_conditions.py tests/models/ -x -q -v`
4. Files NOT to modify: `strategies/*.py`, `orchestrator.py`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.6/session-9-review.md`

## Session-Specific Review Focus
1. Verify no strategy wiring (operating_conditions parsed but not used in activation)
2. Verify None RegimeVector fields treated as non-matching (not as "always matches")
3. Verify AND logic (all conditions must match)
4. Verify backward compat (missing operating_conditions in YAML → None)

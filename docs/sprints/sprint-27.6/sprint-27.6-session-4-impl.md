# Sprint 27.6, Session 4: SectorRotationAnalyzer

## Pre-Flight Checks
1. Read: `argus/core/config.py` (SectorRotationConfig), `argus/data/fmp_reference.py` (FMP client pattern, circuit breaker pattern from DEC-323)
2. Scoped test: `python -m pytest tests/core/test_regime.py tests/core/test_breadth.py tests/core/test_market_correlation.py -x -q`
3. Verify branch

## Objective
Build SectorRotationAnalyzer — fetches FMP `/stable/sector-performance` during pre-market, classifies rotation phase, identifies leading/lagging sectors. Circuit breaker on 403.

## Requirements

1. Create `argus/core/sector_rotation.py` with class `SectorRotationAnalyzer`:
   - Constructor: `(config: SectorRotationConfig, fmp_base_url: str, fmp_api_key: str | None)`
   - `async def fetch(self) -> None`: Fetch `/stable/sector-performance?apikey=KEY`. Parse sector performance data. Classify rotation phase. Circuit breaker: on 403 → set `_circuit_open = True`, degrade gracefully. On timeout (10s) → degrade.
   - `get_sector_snapshot() -> dict`: Returns `{"sector_rotation_phase": str, "leading_sectors": list[str], "lagging_sectors": list[str]}`
   - Classification rules:
     - `risk_on`: Top 3 sectors include ≥2 of {Technology, Consumer Discretionary, Communication Services, Financials}
     - `risk_off`: Top 3 sectors include ≥2 of {Utilities, Healthcare, Consumer Staples, Real Estate}
     - `transitioning`: Mix of risk-on and risk-off sectors in top 3 AND bottom 3 is inverted from top 3 pattern
     - `mixed`: None of the above (default/fallback)
   - Leading: top 3 by performance. Lagging: bottom 3.
   - Degradation: 403 or timeout → phase="mixed", leading=[], lagging=[]

## Constraints
- Do NOT modify any existing files
- Use `aiohttp` or `httpx` for async HTTP (check which is already in project dependencies)
- Standalone module, wired in S6

## Test Targets
- New tests (~10) in `tests/core/test_sector_rotation.py`:
  - Construction
  - Classify risk_on (tech + consumer disc leading)
  - Classify risk_off (utilities + healthcare leading)
  - Classify mixed
  - Classify transitioning
  - Leading/lagging identification (top 3 / bottom 3)
  - FMP 403 → graceful degradation
  - FMP timeout → graceful degradation
  - Partial sector data (< 5 sectors) → mixed
  - get_sector_snapshot returns current state
- Minimum: 10
- Test command: `python -m pytest tests/core/test_sector_rotation.py -x -q -v`

## Definition of Done
- [ ] SectorRotationAnalyzer with async fetch, classification, circuit breaker
- [ ] 10+ tests passing
- [ ] Close-out: `docs/sprints/sprint-27.6/session-4-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-4-closeout.md`
3. Test command: `python -m pytest tests/core/test_sector_rotation.py -x -q -v`
4. Files NOT to modify: all existing files

## Session-Specific Review Focus
1. Verify circuit breaker on 403 (no retry spam)
2. Verify graceful degradation (never raises on FMP failure)
3. Verify sector classification rules match spec
4. Verify no hardcoded API keys

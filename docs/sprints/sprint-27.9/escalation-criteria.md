# Sprint 27.9: Escalation Criteria

## Tier 3 Escalation Triggers

The following conditions require halting implementation and escalating to human review:

1. **yfinance cannot fetch ^VIX or ^GSPC historical data** — If `yfinance.download("^VIX")` returns empty DataFrame or raises an exception that persists after 3 retries with backoff, ESCALATE. This is the sole data source for the sprint's core deliverable.

2. **RegimeVector extension breaks `primary_regime`** — If adding new Optional fields to the frozen dataclass causes `primary_regime` to return a different value for any input, ESCALATE. This would change strategy activation behavior.

3. **RegimeClassifierV2 existing calculator behavior changes** — If wiring new VIX calculators alters the output of existing 6 dimensions (trend, volatility, breadth, correlation, sector_rotation, intraday_character), ESCALATE.

4. **Strategy activation conditions change** — If any of the 7 strategies activates/deactivates under different conditions than pre-sprint (with conservative YAML defaults), ESCALATE.

5. **Quality scores or position sizes change** — If SetupQualityEngine output differs from pre-sprint for the same input when trajectory modulation is OFF, ESCALATE.

6. **SINDy complexity creep** — If any session attempts to add `pysindy` as a dependency, fit ODEs, compute flow fields, or introduce analytical parameters (k, Ω, R², div(F)), ESCALATE. These are explicitly out of scope.

7. **Server startup fails with VIX service enabled** — If VIXDataService initialization prevents ARGUS from starting (blocking startup), ESCALATE. VIX service must be non-blocking (trust-cache-on-startup pattern).

## Non-Escalation Conditions (Handle In-Session)

- yfinance returns partial data (< 22 years) — proceed with available data, log WARNING
- FMP fallback endpoint returns 403 — set `fmp_fallback_enabled: false`, proceed
- Derived metric computation produces NaN for specific dates — guard with None, log WARNING
- Compaction occurs in Session 2b — implement 2 of 4 calculators, defer 2 to fix session

# Sprint 27.9: Revision Rationale

> Documents the changes made to the sprint scope following the adversarial review conducted on March 26, 2026.

## Original Scope (Sprint 27.9 "Phase Space Intelligence")

7.5 sessions delivering: VIXDataService + PhaseSpaceAnalyzer (SINDy) + RegimeVector 6→10 + VIX-enriched volatility + pipeline integration + PhaseSpaceCanvas particle advection + VIX Landscape page (9th page, 5-panel layout) + Dashboard phase space widget.

## Revised Scope (Sprint 27.9 "VIX Regime Intelligence")

8.5 sessions (8 sub-sessions + 0.5 contingency) delivering: VIXDataService + 4 threshold-based calculators + RegimeVector 6→11 + pipeline integration (briefing, regime history, orchestrator, quality engine infrastructure) + REST endpoints + Dashboard VIX data card.

## Changes and Rationale

### Major Scope Reductions

| Cut | Adversarial Finding | Rationale |
|-----|-------------------|-----------|
| SINDy fitting / pysindy | A2 (R² ~0.03 viability) | At 3% deterministic fraction, SINDy's flow field is barely distinguishable from noise. Threshold-based classification provides the same regime labels without the dependency or uncertainty. |
| PhaseSpaceCanvas + VIX Landscape page | R1 (sprint too large) + strategic prioritization | ~3 sessions of frontend work with zero trading pipeline impact. Critical path to revenue runs through Sprint 28 (Learning Loop). This work deferred to post-Learning-Loop reward sprint. |
| VIX-enriched volatility blending | Strategic decision | Blending VIX into the existing intraday SPY volatility dimension hardcodes an interaction assumption. Independent RegimeVector dimensions let the Learning Loop discover the actual relationship. |
| Trajectory modulation user-configurability | Dependency on Learning Loop | Wired structurally but not exposed as config. Requires calibration data from Sprint 28. |

### Adversarial Findings Addressed

| Finding | Severity | Resolution |
|---------|----------|-----------|
| A1: No max staleness threshold | CRITICAL | Added `max_staleness_days: 3` config. When exceeded, all consumers get None. BriefingGenerator omits section. Regime history records null. Dashboard shows "unavailable." |
| A2: SINDy at R² ~0.03 | SIGNIFICANT | SINDy cut entirely. Threshold-based classification decoupled from any fitting. |
| A4: FMP VIX coverage unverified | MODERATE | Added pre-Session-1 verification step. `fmp_fallback_enabled: false` default. yfinance is primary/sole source. |
| F1: Init ordering race | SIGNIFICANT | VIXDataService `is_ready` property. Calculators check before use, return None if not ready. |
| F2: Stale SINDy fit | MODERATE | N/A — SINDy cut. No fit to go stale. |
| G1: Regime boundary coordinates missing | SIGNIFICANT | Full boundary definitions added to spec with configurable YAML thresholds. Defaults documented with empirical rationale. |
| G2: Config interaction matrix | SIGNIFICANT | Simplified to single gate: `vix_regime.enabled`. No separate VIX-enriched volatility or trajectory modulation flags. |
| G3: `get_latest_daily()` semantics | MODERATE | Returns last completed trading day with `data_date` field. Weekend/holiday behavior specified. |
| I1: RegimeHistoryStore migration | MODERATE | ALTER TABLE migration at startup specified. |
| I3: Regime alignment dormant | MINOR | Documented explicitly: enhancement activates only when strategies specify phase-space conditions post-Sprint 28. |
| R1: Sprint too large | SIGNIFICANT | Reduced from 7.5→8.5 sessions but with dramatically simpler scope. Original had 2 distinct deliverables (pipeline + full page); revised has single focus (pipeline + minimal frontend). |
| R3: No DEC range | MINOR | Reserved DEC-369–378. |

### Net Impact

- **Sessions:** 7.5 → 8.5 (more sub-sessions but dramatically less total work per session due to compaction risk splitting)
- **Effective development time:** ~5 days → ~3 days (sub-sessions are smaller and faster)
- **Dependencies removed:** pysindy, Canvas 2D performance concerns, 3-session frontend build
- **Risks reduced:** No R² ~0.03 uncertainty, no yfinance-as-production-dependency-for-flow-field (still used for daily data, but simpler failure mode), no server.py init race with SINDy fitting
- **Value preserved:** All Learning Loop inputs (VIX regime data in RegimeVector, VIX close in regime history, VRP in briefings) delivered identically

# Sprint 27.9 Design Summary

**Sprint Goal:** Deliver VIX regime intelligence — a VIX data service, 4 new RegimeVector dimensions via threshold-based phase space classification, and pipeline integration (briefing enrichment, regime history enrichment, orchestrator logging) — so the Learning Loop (Sprint 28) has VIX context from day one.

**Session Breakdown:**
- Session 1: VIXDataService + SQLite persistence + config model + staleness logic
  - Creates: `argus/data/vix_data_service.py`, `argus/data/vix_config.py`, `config/vix_regime.yaml`, `tests/data/test_vix_data_service.py`
  - Modifies: `argus/config/system_config.py` (add VixRegimeConfig to SystemConfig)
  - Integrates: N/A (foundational)
- Session 2: 4 calculator classes + RegimeVector expansion (6→10) + RegimeClassifierV2 wiring + RegimeHistoryStore migration + strategy YAML config updates
  - Creates: `argus/core/vix_calculators.py`, `tests/core/test_vix_calculators.py`
  - Modifies: `argus/core/regime.py` (RegimeVector + RegimeClassifierV2 + RegimeOperatingConditions), `argus/core/regime_history.py` (vix_close column), `config/regime.yaml`, `config/strategies/*.yaml` (7 files)
  - Integrates: Session 1 (VIXDataService → calculators)
- Session 3: Pipeline integration (BriefingGenerator VIX section, Orchestrator logging, quality engine infrastructure, SignalRejectedEvent automatic) + REST endpoints + integration tests
  - Creates: `argus/api/routes/vix.py`, `tests/api/test_vix_routes.py`, `tests/integration/test_vix_pipeline.py`
  - Modifies: `argus/intelligence/briefing_generator.py`, `argus/core/orchestrator.py`, `argus/analytics/setup_quality_engine.py`, `argus/api/routes/__init__.py` (or router registration), `argus/server.py` (lifespan init)
  - Integrates: Sessions 1+2 (VIXDataService + calculators → pipeline consumers)
- Session 4: Dashboard VIX widget (frontend) + Vitest + polish
  - Creates: `argus/ui/src/components/dashboard/VixRegimeCard.tsx`, `argus/ui/src/hooks/useVixData.ts`, `argus/ui/src/test/VixRegimeCard.test.tsx`
  - Modifies: `argus/ui/src/pages/DashboardPage.tsx`, `argus/ui/src/api/endpoints.ts`
  - Integrates: Session 3 (REST endpoints → frontend hooks)
- Session 4f: visual-review fixes — contingency, 0.5 session

**Key Decisions:**
- No SINDy: threshold-based regime classification gives same regime labels without pysindy dependency or R²~0.03 uncertainty. Flow field/trajectory deferred to future sprint.
- No VIX-enriched volatility blending: keep VIX as independent RegimeVector dimensions; let Learning Loop discover interactions rather than hardcoding a blending formula.
- yfinance primary, FMP secondary (if Starter plan covers ^VIX): one-time historical backfill persisted to SQLite, incremental daily updates only.
- max_staleness_days: 3 — when exceeded, all downstream consumers get None instead of stale values.
- Config: single gate `vix_regime.enabled`. No separate VIX-enriched volatility flag. Trajectory modulation wired OFF, not user-configurable until post-Sprint 28.

**Scope Boundaries:**
- IN: VIXDataService, 4 calculators (VolRegimePhase, VolRegimeMomentum, TermStructureRegime, VarianceRiskPremium), RegimeVector 6→10, threshold-based regime classification, BriefingGenerator VIX section, regime history VIX enrichment, orchestrator pre-market VIX logging, REST endpoints, Dashboard VIX widget
- OUT: SINDy fitting, pysindy dependency, PhaseSpaceCanvas/particle advection, VIX Landscape page, VIX-enriched volatility blending, trajectory modulation activation, BacktestEngine integration, WebSocket push, mobile Canvas optimization

**Regression Invariants:**
- `primary_regime` property returns identical value as pre-sprint
- All 7 strategies activate under same conditions as before (match-any on new dims)
- Quality scores unchanged (trajectory modulation OFF, regime_alignment enhancement dormant)
- Position sizes unchanged
- Existing 6 RegimeVector dimensions unmodified
- RegimeHistoryStore reads old data without error (nullable new columns)
- BriefingGenerator produces valid brief when VIX data unavailable

**File Scope:**
- Modify: `argus/core/regime.py`, `argus/core/regime_history.py`, `argus/config/system_config.py`, `config/regime.yaml`, `config/strategies/*.yaml` (7 files), `argus/intelligence/briefing_generator.py`, `argus/core/orchestrator.py`, `argus/analytics/setup_quality_engine.py`, `argus/server.py`, `argus/api/routes/__init__.py`, `argus/ui/src/pages/DashboardPage.tsx`, `argus/ui/src/api/endpoints.ts`
- Do not modify: `argus/core/events.py`, `argus/strategies/*.py` (strategy source code), `argus/execution/order_manager.py`, `argus/data/databento_data_service.py`, `argus/backtest/backtest_engine.py`, `argus/ui/src/pages/ObservatoryPage.tsx`, `argus/ai/`, `argus/intelligence/counterfactual.py`, `argus/intelligence/catalyst_pipeline.py`

**Config Changes:**
| YAML Key | Pydantic Field | Model | Default |
|----------|---------------|-------|---------|
| `vix_regime.enabled` | `enabled` | `VixRegimeConfig` | `true` |
| `vix_regime.yahoo_symbol_vix` | `yahoo_symbol_vix` | `VixRegimeConfig` | `"^VIX"` |
| `vix_regime.yahoo_symbol_spx` | `yahoo_symbol_spx` | `VixRegimeConfig` | `"^GSPC"` |
| `vix_regime.vol_short_window` | `vol_short_window` | `VixRegimeConfig` | `10` |
| `vix_regime.vol_long_window` | `vol_long_window` | `VixRegimeConfig` | `60` |
| `vix_regime.percentile_window` | `percentile_window` | `VixRegimeConfig` | `252` |
| `vix_regime.ma_window` | `ma_window` | `VixRegimeConfig` | `63` |
| `vix_regime.rv_window` | `rv_window` | `VixRegimeConfig` | `20` |
| `vix_regime.update_interval_seconds` | `update_interval_seconds` | `VixRegimeConfig` | `3600` |
| `vix_regime.history_years` | `history_years` | `VixRegimeConfig` | `22` |
| `vix_regime.max_staleness_days` | `max_staleness_days` | `VixRegimeConfig` | `3` |
| `vix_regime.fmp_fallback_enabled` | `fmp_fallback_enabled` | `VixRegimeConfig` | `false` |
| `vix_regime.vol_regime_boundaries` | `vol_regime_boundaries` | `VixRegimeConfig` | `{see spec}` |
| `vix_regime.term_structure_boundaries` | `term_structure_boundaries` | `VixRegimeConfig` | `{see spec}` |
| `vix_regime.vrp_boundaries` | `vrp_boundaries` | `VixRegimeConfig` | `{see spec}` |
| `vix_regime.momentum_window` | `momentum_window` | `VixRegimeConfig` | `5` |
| `vix_regime.momentum_threshold` | `momentum_threshold` | `VixRegimeConfig` | `0.05` |

**Test Strategy:**
- Session 1: ~12 tests (VIXDataService unit: fetch, persist, staleness, incremental update, get_latest_daily, config validation)
- Session 2: ~18 tests (4 calculators × ~3 tests each + RegimeVector extension tests + matches_conditions + history migration)
- Session 3: ~15 tests (2 REST endpoints × 2 tests + briefing integration + orchestrator logging + quality engine no-change + pipeline integration)
- Session 4: ~8 Vitest (VixRegimeCard rendering, loading, error, hidden-when-disabled)
- Estimated total: ~53 new tests (~45 pytest + ~8 Vitest)

**Runner Compatibility:**
- Mode: human-in-the-loop (pending confirmation)
- Parallelizable sessions: none (strict dependency chain S1→S2→S3→S4)
- Estimated token budget: ~200K tokens across 4 sessions

**Dependencies:**
- yfinance Python package (pip install)
- FMP Starter plan index endpoint (^VIX) — verify before Session 1
- Sprint 27.6 RegimeClassifierV2 + RegimeVector (complete)
- Sprint 27.65 RegimeHistoryStore (complete)

**Escalation Criteria:**
- yfinance cannot fetch ^VIX historical data → ESCALATE (need alternative data source)
- RegimeVector extension breaks existing regime classification → ESCALATE
- SINDy-like complexity creep (any attempt to fit ODEs or introduce pysindy) → ESCALATE

**Doc Updates Needed:**
- `docs/project-knowledge.md` (architecture, strategy table, config, decisions)
- `docs/architecture.md` (VIX data service, regime intelligence update)
- `docs/decision-log.md` (DEC-369 through DEC-37x)
- `docs/dec-index.md`
- `docs/sprint-history.md`
- `CLAUDE.md` (any new DEF items)
- `docs/roadmap.md` (if any deferred items affect queue)

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with compaction scoring)
4. Escalation Criteria
5. Regression Checklist
6. Doc Update Checklist
7. Revision Rationale (from adversarial review)
8. Review Context File
9. Implementation Prompt ×4
10. Review Prompt ×4
11. Work Journal Handoff Prompt

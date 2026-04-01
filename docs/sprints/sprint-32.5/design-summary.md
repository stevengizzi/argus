# Sprint 32.5 Design Summary

**Sprint Goal:** Close three critical experiment pipeline gaps (DEF-131 visibility, DEF-132 exit params as variant dimensions, DEF-134 BacktestEngine all 7 patterns) and produce the Adaptive Capital Intelligence vision document (DEF-133).

**Session Breakdown:**

- Session 1: DEF-132 data model — expand VariantDefinition with exit_overrides, expand parameter fingerprint to include exit params via namespaced canonical JSON, update ExperimentStore schema.
  - Creates: N/A (modifications only)
  - Modifies: `experiments/config.py`, `strategies/patterns/factory.py`, `experiments/store.py`
  - Integrates: N/A (foundational)
  - Score: 11 (Medium)

- Session 2: DEF-132 spawner + runner grid — VariantSpawner applies exit overrides via strategy_exit_overrides deep merge, ExperimentRunner grid generation includes exit dimensions, ExperimentConfig gains exit sweep metadata.
  - Creates: N/A (modifications only)
  - Modifies: `experiments/spawner.py`, `experiments/runner.py`
  - Integrates: S1 (VariantDefinition.exit_overrides, expanded fingerprint)
  - Score: 12 (Medium)

- Session 3: DEF-134 straightforward patterns — BacktestEngine support for dip_and_rip, hod_break, abcd via factory mapping + strategy type wiring.
  - Creates: N/A (modifications only)
  - Modifies: `experiments/runner.py` (pattern mapping), possibly `backtest/backtest_engine.py`
  - Integrates: N/A (independent from S1/S2)
  - Score: 12 (Medium)

- Session 4: DEF-134 reference-data patterns — BacktestEngine support for gap_and_go and premarket_high_break with prior close / PM high context supply via set_reference_data().
  - Creates: N/A (modifications only)
  - Modifies: `backtest/backtest_engine.py` (reference data supply mechanism), `experiments/runner.py`
  - Integrates: S3 (pattern mapping established)
  - Score: 12 (Medium)

- Session 5: DEF-131 REST API enrichment — 3 new endpoints: counterfactual positions (active + closed with filters), experiment variants (status + metrics), promotion event history.
  - Creates: N/A (extends existing route files)
  - Modifies: `counterfactual_store.py`, `experiments/store.py`, `api/routes/counterfactual.py`
  - Integrates: S1 (VariantDefinition schema for API responses)
  - Score: 12 (Medium)

- Session 6: DEF-131 Shadow Trades UI — new tab on Trade Log page showing all shadow/counterfactual positions with rejection stage/reason, theoretical P&L, MFE/MAE, quality grade. Summary stats computed client-side.
  - Creates: `ShadowTradesTab.tsx`, `useShadowTrades.ts` (or similar)
  - Modifies: Trade Log page (add tab), trade type definitions
  - Integrates: S5 (counterfactual positions API)
  - Score: 13 (Medium)

- Session 6f: visual-review fixes — contingency, 0.5 session

- Session 7: DEF-131 Experiments Dashboard — 9th page with variant status table (mode, fingerprint, trade count, key metrics), promotion event log (chronological), basic pattern-level comparison. No parameter heatmap in MVP.
  - Creates: `ExperimentsPage.tsx`, `useExperiments.ts` (or similar)
  - Modifies: Router/nav config (2 files)
  - Integrates: S5 (experiments variants + promotions API)
  - Score: 13 (Medium)

- Session 7f: visual-review fixes — contingency, 0.5 session

- Session 8: DEF-133 Adaptive Capital Intelligence vision document + full doc-sync.
  - Creates: `docs/architecture/allocation-intelligence-vision.md`
  - Modifies: project-knowledge.md, roadmap.md, sprint-history.md, decision-log.md, dec-index.md, CLAUDE.md, architecture.md, sprint-campaign.md
  - Integrates: All (vision informed by implementation; doc-sync covers full sprint)
  - Score: 10 (Medium)

**Dependency Chain:**
```
S1 ──→ S2 ──┐
             ├──→ S5 ──→ S6 ──→ S6f ──┐
S3 ──→ S4 ──┘         └──→ S7 ──→ S7f ──┼──→ S8
```
S1 ∥ S3 safe (zero file overlap). S6 ∥ S7 safe (different pages).

**Parallel execution (preferred — 6 waves):**
- Wave 1: S1 ∥ S3
- Wave 2: S2 → S4 (sequential, both touch runner.py)
- Wave 3: S5
- Wave 4: S6 ∥ S7
- Wave 5: S6f + S7f (contingency)
- Wave 6: S8

**Serial fallback:** S1 → S3 → S2 → S4 → S5 → S6 → S6f → S7 → S7f → S8

**Key Decisions:**

- Fingerprint expansion uses namespaced canonical JSON: `{"detection": {...}, "exit": {...}}`. When exit_overrides is None/empty, omit the "exit" key entirely for backward-compatible hash equality with pre-expansion variants.
- Shadow summary stats computed client-side (TanStack Query pattern) — no dedicated /summary endpoint. Reduces API surface by 1 endpoint without losing functionality.
- Experiments Dashboard is 9th page (not Observatory extension) — experiments are a distinct operational workflow.
- Parameter heatmap deferred from MVP — variant table + promotion log + basic comparison is the right first cut.
- No migration of existing experiment fingerprints — pre-expansion variants keep detection-only fingerprints. New variants with exit_overrides get expanded fingerprints. Both schemes coexist.
- ABCD O(n³) documented but not optimized (DEF-122 remains open).
- BacktestEngine reference data for gap_and_go/premarket_high_break: prior day close and PM high derived from Parquet OHLCV-1m data. First day of range skipped with logged warning if prior day unavailable.

**Scope Boundaries:**

- IN: DEF-131 (visibility — API + 2 UI surfaces), DEF-132 (exit params as variant dimensions — model + spawner + runner), DEF-134 (BacktestEngine all 7 patterns), DEF-133 (vision document only)
- OUT: Standalone strategy retrofit to variant framework, ABCD optimization, new patterns, real-time experiment monitoring, 3D experiment viz, live position management from UI, fingerprint migration, Adaptive Capital Intelligence implementation

**Regression Invariants:**

1. Fingerprint backward compat: detection-only variants produce identical fingerprint before and after expansion
2. experiments.yaml backward compat: configs without exit_overrides load without error
3. BacktestEngine existing patterns: bull_flag + flat_top_breakout backtesting unchanged
4. Trade Log functionality: existing trades, filtering, detail panels unaffected by shadow tab
5. Navigation: 9th page doesn't break routing, shortcuts, or page transitions
6. Config gating: experiments.enabled=false disables all experiment features gracefully
7. REST API: all existing endpoints unchanged response schemas
8. Counterfactual pipeline: new query surface doesn't affect write path or tracking
9. Shadow strategy mode: LIVE/SHADOW behavior unchanged for existing strategies

**File Scope:**

- Modify: experiments/config.py, experiments/store.py, experiments/spawner.py, experiments/runner.py, strategies/patterns/factory.py, backtest/backtest_engine.py, counterfactual_store.py, api/routes/counterfactual.py, api/routes/experiments.py, Trade Log page, router/nav config, trade type definitions
- Do not modify: core/events.py, core/regime.py, execution/order_manager.py, intelligence/counterfactual.py (tracker logic), strategies/ (any strategy logic), core/exit_math.py, core/config.py (ExitManagementConfig is read-only reference)

**Config Changes:**

| YAML Field | Pydantic Field | Type | Default |
|-----------|---------------|------|---------|
| `experiments.yaml` → variant definitions → `exit_overrides` | `VariantDefinition.exit_overrides` | `dict[str, Any] \| None` | `None` |
| `experiments.yaml` → `exit_sweep_params` | `ExperimentConfig.exit_sweep_params` | `list[ExitSweepParam] \| None` | `None` |

ExperimentConfig already has `extra="forbid"` — unrecognized keys will raise, not silently drop.

**Test Strategy:**

- ~36 new pytest, ~8 new Vitest → estimated 4,441 + 708 total
- S1: fingerprint backward compat (golden hash comparison), fingerprint with exit, empty exit = no exit, VariantDef serialization roundtrip
- S2: spawner exit override application via deep merge, grid generation with/without exit dims, combined grid size validation
- S3: 3 × (factory construct + backtest produces trades)
- S4: 2 × (factory construct + ref data supply + backtest produces trades), missing prior day edge case
- S5: endpoint response shape, auth, empty state, filter params
- S6/S7: component rendering, empty state, data display
- Full suite at S1 pre-flight and all close-outs (DEC-328 tiering)

**Runner Compatibility:**

- Mode: Human-in-the-loop
- Parallelizable sessions: S1 ∥ S3, S6 ∥ S7 (informational only)
- Runner config: not generated (HITL mode)

**Dependencies:**

- Sprint 32 complete (experiments infrastructure exists)
- All Sprint 32 cleanup items already applied
- git main branch up to date

**Escalation Criteria:**

- Fingerprint expansion breaks backward compat (golden hash test fails) → Tier 3
- BacktestEngine reference data mechanism requires architectural changes beyond backtest_engine.py → Tier 3
- CounterfactualStore query performance on accumulated data causes >2s response times → scope reduction (add pagination, defer complex queries)
- Frontend pages exceed 13 compaction score after visual review fixes → split into additional sessions

**Doc Updates Needed:**

- project-knowledge.md (tests, sprint history, build track, expanded vision, experiment pipeline section)
- CLAUDE.md (DEF closures, test counts, new page)
- roadmap.md (32.5 complete, next sprint)
- sprint-history.md (32.5 entry)
- decision-log.md (any new DECs)
- dec-index.md (any new DECs)
- architecture.md (experiment pipeline expansion, new page)
- sprint-campaign.md (32.5 complete)

**Artifacts to Generate:**

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates per session)
4. Implementation Prompt ×8 (S1–S8, S6f/S7f use S6/S7 prompts with fix scope)
5. Review Prompt ×8
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff Prompt

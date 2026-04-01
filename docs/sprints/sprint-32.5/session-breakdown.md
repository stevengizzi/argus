# Sprint 32.5: Session Breakdown

## Dependency Chain

```
S1 ──→ S2 ──┐
             ├──→ S5 ──→ S6 ──→ S6f ──┐
S3 ──→ S4 ──┘         └──→ S7 ──→ S7f ──┼──→ S8
```

Parallelizable pairs (informational, HITL mode): S1 ∥ S3, S6 ∥ S7.

## Execution Order

### Parallel (preferred — 6 waves)

| Wave | Sessions | Rationale |
|------|----------|-----------|
| 1 | S1 ∥ S3 | Zero file overlap (config+factory vs runner+backtest_engine) |
| 2 | S2 → S4 | Sequential — both touch runner.py; S2 depends on S1, S4 depends on S3 |
| 3 | S5 | Depends on S1 data model |
| 4 | S6 ∥ S7 | Zero file overlap (different pages) |
| 5 | S6f + S7f | Contingency — if needed |
| 6 | S8 | Depends on all |

### Serial (fallback — single Claude Code session)

S1 → S3 → S2 → S4 → S5 → S6 → S6f → S7 → S7f → S8

Rationale: S1 and S3 are independent; running S3 before S2 avoids the runner.py conflict. S2 after S3 means S4 can immediately follow without file conflicts.

---

## Session 1: DEF-132 Data Model + Fingerprint Expansion

**Objective:** Expand VariantDefinition with exit_overrides field. Expand parameter fingerprint to include exit params via namespaced canonical JSON. Update ExperimentStore schema.

**Creates:** N/A (modifications only)

**Modifies:**
- `argus/intelligence/experiments/config.py` — VariantDefinition gains `exit_overrides: dict[str, Any] | None`, ExperimentConfig gains `exit_sweep_params: list[ExitSweepParam] | None`, new `ExitSweepParam` Pydantic model
- `argus/strategies/patterns/factory.py` — `compute_parameter_fingerprint()` expanded to accept optional exit_overrides, produce namespaced hash
- `argus/intelligence/experiments/store.py` — schema migration for exit_overrides column on variant_definitions table

**Integrates:** N/A (foundational)

**Parallelizable:** true (with S3 — zero file overlap)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | config.py, factory.py, store.py | 3 |
| Pre-flight reads | config.py, factory.py, store.py, `core/config.py` (ExitManagementConfig reference), `config/exit_management.yaml` | 5 |
| New tests | ~6 (fingerprint backward compat golden hash, fingerprint with exit overrides, empty exit = no exit, VariantDef serialization roundtrip, ExitSweepParam validation, store schema migration) | 3 |
| **Total** | | **11 (Medium)** |

---

## Session 2: DEF-132 Spawner + Runner Grid Expansion

**Objective:** VariantSpawner applies exit overrides via strategy_exit_overrides deep merge. ExperimentRunner grid generation includes exit dimensions when configured.

**Creates:** N/A (modifications only)

**Modifies:**
- `argus/intelligence/experiments/spawner.py` — `_apply_variant_params()` extended to apply exit_overrides via deep_update into strategy_exit_overrides
- `argus/intelligence/experiments/runner.py` — `generate_parameter_grid()` expanded to optionally include exit sweep dimensions from ExperimentConfig

**Integrates:** S1 (VariantDefinition.exit_overrides, ExitSweepParam, expanded fingerprint)

**Parallelizable:** false (depends on S1; runner.py shared with S4)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | spawner.py, runner.py | 2 |
| Pre-flight reads | spawner.py, runner.py, config.py (from S1), factory.py, `core/config.py`, `config/exit_management.yaml` | 6 |
| New tests | ~8 (spawner exit override apply, deep merge precedence, grid with exit dims, grid without exit dims, combined grid size, integration spawn+fingerprint, integration run+exit grid, exit override conflict edge case) | 4 |
| **Total** | | **12 (Medium)** |

---

## Session 3: DEF-134 Straightforward Patterns (dip_and_rip, hod_break, abcd)

**Objective:** Add BacktestEngine/ExperimentRunner support for 3 patterns that don't require reference data: dip_and_rip, hod_break, abcd.

**Creates:** N/A (modifications only)

**Modifies:**
- `argus/intelligence/experiments/runner.py` — add 3 entries to `_PATTERN_TO_STRATEGY_TYPE` mapping (or equivalent factory delegation)
- `argus/backtest/backtest_engine.py` — if pattern mapping lives here, add entries

**Integrates:** N/A (independent from DEF-132 track)

**Parallelizable:** true (with S1 — zero file overlap)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | runner.py, possibly backtest_engine.py | 2 |
| Pre-flight reads | runner.py, backtest_engine.py, `dip_and_rip.py`, `hod_break.py`, `abcd.py`, `pattern_strategy.py`, factory.py | 7 |
| New tests | ~6 (3× factory construct + backtest produces trades) | 3 |
| **Total** | | **12 (Medium)** |

---

## Session 4: DEF-134 Reference-Data Patterns (gap_and_go, premarket_high_break)

**Objective:** Add BacktestEngine/ExperimentRunner support for 2 patterns that require reference data (prior close, PM high). Build reference data supply mechanism in BacktestEngine.

**Creates:** N/A (modifications only)

**Modifies:**
- `argus/backtest/backtest_engine.py` — reference data supply mechanism: derive prior day close and PM high from Parquet OHLCV-1m data, pass to pattern via set_reference_data()
- `argus/intelligence/experiments/runner.py` — add 2 entries to pattern mapping

**Integrates:** S3 (pattern mapping mechanism established)

**Parallelizable:** false (depends on S3; runner.py shared with S2)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | backtest_engine.py (reference data mechanism), runner.py | 2 |
| Pre-flight reads | backtest_engine.py, runner.py, `gap_and_go.py`, `premarket_high_break.py`, factory.py, pattern_strategy.py | 6 |
| New tests | ~8 (reference data derivation, 2× construct + ref data + backtest, missing prior day edge, sparse PM candle edge, ref data doesn't affect non-ref-data patterns) | 4 |
| **Total** | | **12 (Medium)** |

---

## Session 5: DEF-131 REST API Enrichment

**Objective:** Add 3 new JWT-protected REST endpoints exposing counterfactual positions, experiment variant status, and promotion event history.

**Creates:** N/A (extends existing route files)

**Modifies:**
- `argus/intelligence/counterfactual_store.py` — add `query_positions()` method (active + closed, with filters)
- `argus/intelligence/experiments/store.py` — add `query_variants_with_metrics()` and `query_promotion_events()` methods
- `argus/api/routes/counterfactual.py` — add `GET /api/v1/counterfactual/positions` endpoint

**Integrates:** S1 (VariantDefinition schema for variant API responses)

**Parallelizable:** false (depends on S1)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| Files modified | counterfactual_store.py, experiments/store.py, api/routes/counterfactual.py | 3 |
| Pre-flight reads | counterfactual.py, counterfactual_store.py, experiments/store.py, promotion.py, existing route files | 5 |
| New tests | ~8 (3 endpoints × response shape + auth + empty state + filters) | 4 |
| **Total** | | **12 (Medium)** |

---

## Session 6: DEF-131 Shadow Trades UI

**Objective:** Add Shadow Trades tab to Trade Log page showing all counterfactual/shadow positions with rejection metadata, theoretical P&L, MFE/MAE, and quality grade.

**Creates:**
- `argus/ui/src/pages/trades/ShadowTradesTab.tsx` (or similar path following existing pattern)
- `argus/ui/src/hooks/useShadowTrades.ts` (TanStack Query hook)

**Modifies:**
- Trade Log page component (add tab)
- Trade type definitions (shadow trade type)

**Integrates:** S5 (counterfactual positions API endpoint)

**Parallelizable:** true (with S7 — different pages, zero overlap)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files | ShadowTradesTab.tsx, useShadowTrades.ts | 4 |
| Files modified | Trade Log page, trade types | 2 |
| Pre-flight reads | Trade Log page, existing trade hooks, API type patterns | 3 |
| New tests | ~4 Vitest (component render, empty state, data display, tab switching) | 2 |
| Large file | ShadowTradesTab.tsx (~150+ lines) | 2 |
| **Total** | | **13 (Medium)** |

---

## Session 6f: Visual Review Fixes (Contingency)

**Objective:** Fix visual/UX issues discovered during Shadow Trades tab review.

Contingency session (0.5). Used only if S6 visual review surfaces issues. If no issues found, session is skipped.

---

## Session 7: DEF-131 Experiments Dashboard

**Objective:** Build 9th page: Experiments Dashboard with variant status table (mode, fingerprint, trade count, key metrics), promotion event log (chronological), and pattern-level variant comparison.

**Creates:**
- `argus/ui/src/pages/experiments/ExperimentsPage.tsx` (or similar path)
- `argus/ui/src/hooks/useExperiments.ts` (TanStack Query hooks for variants + promotions)

**Modifies:**
- Router/navigation config (2 files — add 9th page route + nav entry)

**Integrates:** S5 (experiments variants + promotions API endpoints)

**Parallelizable:** true (with S6 — different pages, zero overlap)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files | ExperimentsPage.tsx, useExperiments.ts | 4 |
| Files modified | Router config, nav config | 2 |
| Pre-flight reads | Existing page patterns (for structure reference), API types, nav config | 3 |
| New tests | ~4 Vitest (component render, empty state, data display, nav integration) | 2 |
| Large file | ExperimentsPage.tsx (~200+ lines) | 2 |
| **Total** | | **13 (Medium)** |

---

## Session 7f: Visual Review Fixes (Contingency)

**Objective:** Fix visual/UX issues discovered during Experiments Dashboard review.

Contingency session (0.5). Used only if S7 visual review surfaces issues. If no issues found, session is skipped.

---

## Session 8: DEF-133 Vision Document + Doc-Sync

**Objective:** Write the Adaptive Capital Intelligence architectural vision document. Perform full doc-sync for Sprint 32.5.

**Creates:**
- `docs/architecture/allocation-intelligence-vision.md`

**Modifies:**
- `docs/project-knowledge.md`
- `docs/roadmap.md`
- `docs/sprint-history.md`
- `docs/decision-log.md`
- `docs/dec-index.md`
- `CLAUDE.md`
- `docs/architecture.md`
- `docs/sprint-campaign.md`

**Integrates:** All (vision informed by implementation; doc-sync covers full sprint)

**Parallelizable:** false (depends on all prior sessions)

**Compaction Risk:**

| Factor | Detail | Points |
|--------|--------|--------|
| New files | allocation-intelligence-vision.md | 2 |
| Files modified | 8 documentation files | 8 |
| **Total** | | **10 (Medium)** |

---

## Summary Table

| # | Session | DEF | Creates | Modifies | Integrates | Score | Parallel |
|---|---------|-----|---------|----------|------------|-------|----------|
| S1 | Data Model + Fingerprint | 132 | — | 3 files | — | 11 | ✓ (S3) |
| S2 | Spawner + Runner Grid | 132 | — | 2 files | S1 | 12 | — |
| S3 | 3 Straightforward Patterns | 134 | — | 2 files | — | 12 | ✓ (S1) |
| S4 | 2 Reference-Data Patterns | 134 | — | 2 files | S3 | 12 | — |
| S5 | REST API Enrichment | 131 | — | 3 files | S1 | 12 | — |
| S6 | Shadow Trades UI | 131 | 2 files | 2 files | S5 | 13 | ✓ (S7) |
| S6f | Visual Review Fixes | 131 | — | TBD | S6 | contingency | — |
| S7 | Experiments Dashboard | 131 | 2 files | 2 files | S5 | 13 | ✓ (S6) |
| S7f | Visual Review Fixes | 131 | — | TBD | S7 | contingency | — |
| S8 | Vision Doc + Doc-Sync | 133 | 1 file | 8 files | all | 10 | — |

# Sprint 25.6 — Session Breakdown

## Session 1: Telemetry Store DB Separation + Log Hygiene

**Objective:** Move evaluation events to dedicated `data/evaluation.db`, reuse store instance in health check loop, and suppress log spam from repeated write failures.

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | `argus/strategies/telemetry_store.py`, `argus/main.py`, `argus/api/server.py` |
| Integrates | N/A (self-contained) |
| Parallelizable | No (S2 depends on `main.py` changes settling) |

**Compaction Risk:**

| Factor | Points |
|--------|--------|
| New files created | 0 |
| Files modified (3) | 3 |
| Context reads (4: telemetry_store.py, main.py, server.py, intelligence/storage.py) | 4 |
| New tests (~5) | 2.5 |
| Complex integration wiring (DB separation + store passing + health check) | 3 |
| **Total** | **12.5 (Medium)** |

---

## Session 2: Periodic Regime Reclassification

**Objective:** Add asyncio task that re-evaluates market regime every ~5 minutes during market hours using existing orchestrator classification logic.

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | `argus/core/orchestrator.py`, `argus/main.py` |
| Integrates | N/A (self-contained) |
| Parallelizable | No (touches `main.py` which S1 also modifies) |

**Compaction Risk:**

| Factor | Points |
|--------|--------|
| New files created | 0 |
| Files modified (2) | 2 |
| Context reads (3: orchestrator.py, main.py, strategy configs) | 3 |
| New tests (~4) | 2 |
| **Total** | **7 (Low)** |

---

## Session 3: Trades Page Fixes (DEF-067/068/069/073)

**Objective:** Replace pagination with scroll, fix metrics scope to full dataset, fix filter state persistence on page re-entry, enable sortable columns.

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | `argus/ui/src/pages/TradesPage.tsx`, trade hooks/components (~2 additional files) |
| Integrates | N/A (self-contained frontend) |
| Parallelizable | Yes — independent of S1/S2 (no backend dependencies); independent of S4/S5 (different pages). Justification: modifies only Trades page files, no overlap with other sessions. |

**Compaction Risk:**

| Factor | Points |
|--------|--------|
| New files created | 0 |
| Files modified (~3) | 3 |
| Context reads (3: TradesPage, types, hooks) | 3 |
| New tests (~4 Vitest) | 2 |
| **Total** | **8 (Low)** |

**Visual Review Items:**
- Trades table scrolls (no pagination controls)
- Summary metrics stay constant while scrolling
- Navigate away, return: filter + data match
- Click column header: sort indicator + reorder

---

## Session 4: Orchestrator Timeline Fixes (DEF-070/071)

**Objective:** Fix "Afternoon Momentum" label truncation and investigate/fix VWAP Reclaim shown as throttled during its operating window.

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | `argus/ui/src/features/orchestrator/StrategyCoverageTimeline.tsx`, possibly `argus/api/routes/orchestrator.py` or `argus/utils/strategyConfig.ts` |
| Integrates | N/A (self-contained) |
| Parallelizable | Yes — independent page from S3/S5. Justification: touches only Orchestrator components, no file overlap. |

**Compaction Risk:**

| Factor | Points |
|--------|--------|
| New files created | 0 |
| Files modified (~2) | 2 |
| Context reads (3: StrategyCoverageTimeline, strategyConfig, orchestrator routes) | 3 |
| New tests (~2 Vitest) | 1 |
| **Total** | **6 (Low)** |

**Visual Review Items:**
- "Afternoon Momentum" fully readable on desktop
- VWAP Reclaim shows solid bar during operating window (not hatched)

---

## Session 5: Dashboard Layout Restructure (DEF-072)

**Objective:** Promote Positions card to Row 2 (below financial scoreboard), reorganize remaining cards so Positions is visible without scrolling on 1080p desktop.

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | `argus/ui/src/pages/DashboardPage.tsx`, possibly 1–2 component files |
| Integrates | N/A (self-contained) |
| Parallelizable | Yes — independent page from S3/S4. Justification: touches only Dashboard page, no file overlap. |

**Compaction Risk:**

| Factor | Points |
|--------|--------|
| New files created | 0 |
| Files modified (~3) | 3 |
| Context reads (4: DashboardPage, component files) | 4 |
| New tests (~2 Vitest) | 1 |
| **Total** | **8 (Low)** |

**Visual Review Items:**
- Positions card visible without scrolling on 1080p
- Financial scoreboard still Row 1
- All cards render with correct data (no missing or broken cards)

---

## Session 5f: Visual Review Fixes (Contingency)

**Objective:** Address any visual issues found during S3–S5 visual review. Contingency — skip if no issues.

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | TBD based on visual review findings |
| Integrates | N/A |
| Parallelizable | No |

**Compaction Risk:** TBD (expected Low if needed)

---

## Dependency Chain

```
S1 (telemetry) → S2 (regime) [both touch main.py]
S3 (Trades page) — independent
S4 (Orchestrator) — independent
S5 (Dashboard) — independent
S5f (contingency) — after S3/S4/S5 visual review
```

S3, S4, S5 can run in any order and are independent of S1/S2. Recommended sequence: S1 → S2 → S3 → S4 → S5 → S5f.

# Sprint 25: Session Breakdown

## Session Dependency Chain

```
S1 (Backend API) → S2 (Backend WS) → S3 (Page Shell) → S4a (Detail Panel Core) → S4b (Candlestick + Hooks)
                                                       → S5a (Matrix Core) → S5b (Matrix Polish)
                                                       → S6a (Three.js Scene) → S6b (Particles) → S7 (Radar)
                                                       → S8 (Timeline)
S3 + all views + S4a/b → S9 (Vitals + Debrief)
All → S10 (Integration Polish)
```

Dependency summary: S1 before S2. S1+S2 before S3. S3 before all frontend sessions. S4a before S4b. S5a before S5b. S6a before S6b before S7. All sessions complete before S10. S9 depends on S2 (WS) + S1 (REST) + S3 (layout) but can run after S3 in parallel with view sessions.

## Sessions

### S1: Backend — Observatory API Endpoints
**Scope:** Create ObservatoryService and REST endpoints for session summary, pipeline stage counts, closest-miss ranking, and per-symbol pipeline journey.

| Column | Detail |
|--------|--------|
| Creates | `argus/analytics/observatory_service.py`, `argus/api/routes/observatory.py` |
| Modifies | `argus/api/__init__.py` (register routes), `server.py` (wire service into AppState) |
| Integrates | Reads from existing EvaluationEventStore, UniverseManager, SetupQualityEngine |
| Parallelizable | false |
| Tests | ~15 pytest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 2 | 2 |
| Context reads | 4 (EventStore, UM, QE, existing routes) | 4 |
| Tests to write | 15 | 7.5 |
| Complex integration (3+ components) | Yes (EventStore + UM + QE) | 3 |
| External API debugging | No | 0 |
| Large files (>150 lines) | 1 (observatory_service.py) | 2 |
| **Total** | | **12.5 — Medium** |

---

### S2: Backend — WebSocket Live Updates
**Scope:** Create Observatory WebSocket endpoint that pushes pipeline stage counts, tier transitions, and evaluation summaries at configurable interval.

| Column | Detail |
|--------|--------|
| Creates | `argus/api/websocket/observatory_ws.py` |
| Modifies | `server.py` (mount WS endpoint) |
| Integrates | S1's ObservatoryService |
| Parallelizable | false |
| Tests | ~10 pytest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads | 3 (existing WS pattern, ObservatoryService, server.py) | 3 |
| Tests to write | 10 | 5 |
| Complex integration | No | 0 |
| External API debugging | Yes (WebSocket) | 3 |
| Large files | 0 | 0 |
| **Total** | | **12 — Medium** |

Config changes in this session:

| YAML Key | Pydantic Field |
|----------|----------------|
| observatory.enabled | ObservatoryConfig.enabled |
| observatory.ws_update_interval_ms | ObservatoryConfig.ws_update_interval_ms |
| observatory.timeline_bucket_seconds | ObservatoryConfig.timeline_bucket_seconds |
| observatory.matrix_max_rows | ObservatoryConfig.matrix_max_rows |
| observatory.debrief_retention_days | ObservatoryConfig.debrief_retention_days |

---

### S3: Frontend — Page Shell, Routing, Keyboard System
**Scope:** Create Observatory page with full-bleed canvas layout, register in navigation/routing, implement keyboard shortcut hook with all documented shortcuts, create ObservatoryLayout with canvas zone + tier selector + detail panel placeholder zones.

| Column | Detail |
|--------|--------|
| Creates | `ObservatoryPage.tsx`, `useObservatoryKeyboard.ts`, `ObservatoryLayout.tsx`, `TierSelector.tsx` |
| Modifies | Navigation/routing config (add page 8) |
| Integrates | Existing Command Center navigation and routing |
| Parallelizable | false |
| Tests | ~8 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 4 | 8 |
| Files modified | 2 | 2 |
| Context reads | 3 | 3 |
| Tests to write | 8 | 4 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 1 (useObservatoryKeyboard.ts) | 2 |
| **Total** | | **13 — Medium** |

Visual review items: Page accessible from sidebar, full-bleed layout renders, tier selector visible, keyboard shortcuts trigger view switching (even though views are placeholder divs at this stage).

---

### S3f: Visual Review Fixes — Contingency (0.5 session)

---

### S4a: Frontend — Detail Panel Shell + Condition Grid + Strategy History
**Scope:** Create the slide-out detail panel component with pipeline position badge, per-strategy condition check grid (pass/fail with values), chronological strategy history list. Wire into ObservatoryLayout.

| Column | Detail |
|--------|--------|
| Creates | `SymbolDetailPanel.tsx`, `SymbolConditionGrid.tsx`, `SymbolStrategyHistory.tsx` |
| Modifies | `ObservatoryLayout.tsx` (wire panel) |
| Integrates | S1's API endpoints (per-symbol journey), S3's layout |
| Parallelizable | false |
| Tests | ~7 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | 6 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 7 | 3.5 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 1 (SymbolDetailPanel.tsx) | 2 |
| **Total** | | **10 — Medium** |

Visual review items: Panel slides out from right, condition grid renders with correct colors, strategy history shows chronological events.

---

### S4b: Frontend — Candlestick Chart + Data Hooks
**Scope:** Create Lightweight Charts candlestick component for the detail panel and the TanStack Query data hook for symbol detail data. Wire chart into the detail panel.

| Column | Detail |
|--------|--------|
| Creates | `SymbolCandlestickChart.tsx`, `useSymbolDetail.ts` |
| Modifies | `SymbolDetailPanel.tsx` (add chart section) |
| Integrates | S4a's panel shell, existing Lightweight Charts dependency |
| Parallelizable | false |
| Tests | ~5 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 5 | 2.5 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **9 — Medium** |

Visual review items: Candlestick chart renders with real or mock data, updates when symbol changes, proper sizing within panel.

---

### S4f: Visual Review Fixes — Contingency (0.5 session)

---

### S5a: Frontend — Matrix View Core
**Scope:** Create the condition heatmap Matrix view with symbol rows and condition columns. Rows display symbol ticker, condition pass/fail cells with color coding. Basic rendering without virtualization.

| Column | Detail |
|--------|--------|
| Creates | `MatrixView.tsx`, `MatrixRow.tsx` |
| Modifies | `ObservatoryPage.tsx` (register view) |
| Integrates | S1's closest-miss endpoint, S3's keyboard system (view key `2`) |
| Parallelizable | false |
| Tests | ~6 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 6 | 3 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 1 (MatrixView.tsx) | 2 |
| **Total** | | **10 — Medium** |

Visual review items: Matrix renders with rows and columns, pass/fail colors correct, inactive strategy conditions show gray "–".

---

### S5b: Frontend — Matrix Virtual Scrolling + Live Sort + Interaction
**Scope:** Add virtualized scrolling for large row counts, live-updating sort order (proximity to trigger), click-to-select row (populates detail panel), keyboard integration (`Tab`/`Shift+Tab` within Matrix rows).

| Column | Detail |
|--------|--------|
| Creates | `useMatrixData.ts` |
| Modifies | `MatrixView.tsx` (add virtualization, sort, interaction) |
| Integrates | S4a/S4b detail panel (click row → populate), S3's keyboard system |
| Parallelizable | false |
| Tests | ~4 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 4 | 2 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **8 — Low** |

Visual review items: Scroll through 100+ rows smoothly, sort order changes when data updates, clicking row opens detail panel.

---

### S5f: Visual Review Fixes — Contingency (0.5 session)

---

### S6a: Frontend — Three.js Funnel Scene Setup
**Scope:** Create Three.js canvas component and scene: camera, lighting, 7 translucent tier discs at perspective angles forming a cone/funnel shape, orbit controls (drag rotate, scroll zoom), and ambient/directional lighting. Code-split via React.lazy.

| Column | Detail |
|--------|--------|
| Creates | `FunnelView.tsx`, `FunnelScene.ts` |
| Modifies | `ObservatoryPage.tsx` (register view with lazy loading) |
| Integrates | S3's keyboard system (view key `1`, `R` reset, `F` fit) |
| Parallelizable | false |
| Tests | ~3 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 3 | 1.5 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 1 (FunnelScene.ts) | 2 |
| **Total** | | **9.5 — Medium** |

Visual review items: 3D funnel renders with translucent tier discs, orbit controls work, camera reset works.

---

### S6b: Frontend — Funnel Symbol Particles
**Scope:** Create instanced mesh manager for symbol particles. Position particles on their tier disc. Implement tier transition animations (symbol moves between discs). Click particle to select (populates detail panel). Hover tooltip with ticker + tier. LOD: labels visible when zoomed in.

| Column | Detail |
|--------|--------|
| Creates | `FunnelSymbolManager.ts` |
| Modifies | `FunnelScene.ts` (integrate particle manager) |
| Integrates | S1/S2 endpoints for tier populations, S4a/S4b detail panel (click → populate) |
| Parallelizable | false |
| Tests | ~3 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads | 4 (FunnelScene, WS data, API data, detail panel) | 4 |
| Tests to write | 3 | 1.5 |
| Complex integration | Yes (WS + API + panel + Three.js scene) | 3 |
| External API debugging | No | 0 |
| Large files | 1 (FunnelSymbolManager.ts) | 2 |
| **Total** | | **11.5 — Medium** |

Visual review items: Particles visible on tier discs, 3,000+ particles at 30+ fps, click selects particle, hover shows tooltip, LOD labels appear on zoom.

---

### S6f: Visual Review Fixes — Contingency (0.5 session)

---

### S7: Frontend — Radar View (Camera Animation)
**Scope:** Create Radar view that smoothly animates camera from current position to bottom-up perspective. Add concentric ring labels and center "TRIGGER" indicator visible only in radar mode. Pressing `1` (Funnel) animates camera back.

| Column | Detail |
|--------|--------|
| Creates | `RadarView.tsx`, `useCameraTransition.ts` |
| Modifies | `FunnelScene.ts` (add radar-mode label sprites/overlays) |
| Integrates | S6a/S6b's Three.js scene, S3's keyboard system (view key `4`) |
| Parallelizable | false |
| Tests | ~4 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 4 | 2 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **8 — Low** |

Visual review items: Press `4` — camera smoothly rotates to bottom-up. Concentric ring labels appear. Press `1` — camera smoothly returns to perspective. Transition is smooth (no jumps).

---

### S8: Frontend — Timeline View
**Scope:** Create horizontal session timeline with 4 strategy lanes spanning the full trading day. Event marks at 4 severity levels. Active strategy windows visually indicated. Click event populates detail panel.

| Column | Detail |
|--------|--------|
| Creates | `TimelineView.tsx`, `TimelineLane.tsx`, `useTimelineData.ts` |
| Modifies | `ObservatoryPage.tsx` (register view, key `3`) |
| Integrates | S1's per-symbol journey endpoint, S3's keyboard system, S4a/S4b detail panel |
| Parallelizable | false |
| Tests | ~8 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | 6 |
| Files modified | 1 | 1 |
| Context reads | 3 | 3 |
| Tests to write | 8 | 4 |
| Complex integration | Yes (API + keyboard + detail panel) | 3 |
| External API debugging | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **13 — Medium** |

Visual review items: 4 strategy lanes render with correct time axis (9:30–4:00 ET), event marks appear at correct positions, strategy windows visually highlighted, click event populates detail panel.

---

### S8f: Visual Review Fixes — Contingency (0.5 session)

---

### S9: Frontend — Session Vitals + Debrief Mode
**Scope:** Create session vitals bar (connection status, counts, market time, top blocker). Create date picker for debrief mode that switches all data hooks from live WS to historical REST queries.

| Column | Detail |
|--------|--------|
| Creates | `SessionVitalsBar.tsx`, `useSessionVitals.ts`, `useDebriefMode.ts` |
| Modifies | `ObservatoryLayout.tsx` (wire vitals bar), all data hooks (add date parameter for historical queries) |
| Integrates | S2's WebSocket for live mode, S1's REST endpoints for debrief mode |
| Parallelizable | false |
| Tests | ~8 Vitest |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | 6 |
| Files modified | 3 | 3 |
| Context reads | 4 | 4 |
| Tests to write | 8 | 4 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **13 — Medium** |

Visual review items: Vitals bar shows connection status dots, market time, counters. Date picker opens and selects a past date. All views switch to historical data. "Live" indicator changes.

---

### S9f: Visual Review Fixes — Contingency (0.5 session)

---

### S10: Integration Polish + Keyboard Refinement
**Scope:** End-to-end integration testing of all keyboard flows across all views. Loading states, error states, empty states. Transition smoothness between views. Edge cases in keyboard navigation (first/last symbol, empty tier, panel open/close timing).

| Column | Detail |
|--------|--------|
| Creates | None |
| Modifies | All Observatory components as needed for polish |
| Integrates | Full end-to-end keyboard flow |
| Parallelizable | false |
| Tests | ~6 Vitest (integration-level) |

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 6 | 6 |
| Context reads | 6 | 6 |
| Tests to write | 6 | 3 |
| Complex integration | No | 0 |
| External API debugging | No | 0 |
| Large files | 0 | 0 |
| **Total** | | **12 — Medium** |

Visual review items: Complete keyboard flow across all views without mouse. All loading/error/empty states render correctly. Transitions smooth. No visual glitches.

---

## Summary

| Session | Scope | Score | Risk |
|---------|-------|-------|------|
| S1 | Backend API endpoints | 12.5 | Medium |
| S2 | Backend WebSocket | 12 | Medium |
| S3 | Page shell + routing + keyboard | 13 | Medium |
| S3f | Visual fixes (contingency) | — | — |
| S4a | Detail panel core | 10 | Medium |
| S4b | Candlestick chart + hooks | 9 | Medium |
| S4f | Visual fixes (contingency) | — | — |
| S5a | Matrix view core | 10 | Medium |
| S5b | Matrix virtual scroll + interaction | 8 | Low |
| S5f | Visual fixes (contingency) | — | — |
| S6a | Three.js scene setup | 9.5 | Medium |
| S6b | Symbol particles | 11.5 | Medium |
| S6f | Visual fixes (contingency) | — | — |
| S7 | Radar view (camera animation) | 8 | Low |
| S8 | Timeline view | 13 | Medium |
| S8f | Visual fixes (contingency) | — | — |
| S9 | Session vitals + debrief mode | 13 | Medium |
| S9f | Visual fixes (contingency) | — | — |
| S10 | Integration polish | 12 | Medium |

**All sessions ≤ 13. No sessions require splitting.**

**Total: 13 implementation + 5 contingency = up to 18 sessions.**
**Estimated new tests: ~25 pytest + ~67 Vitest = ~92 total.**

# Sprint 25 Design Summary

**Sprint Goal:** Build "The Observatory" — a new Command Center page (page 8) providing immersive, real-time and post-session visualization of the entire trading pipeline. Four switchable views (Funnel, Radar, Matrix, Timeline) with keyboard-first navigation, a persistent detail panel with live candlestick charts, and session vitals. Enables the operator to understand and diagnose system behavior at every level of granularity — from the full 8,000-symbol universe down to individual per-candle condition checks.

**Session Breakdown:**

- S1: Backend Observatory API endpoints (session summary, pipeline stage counts, closest-miss ranking, per-symbol journey)
  - Creates: `argus/api/routes/observatory.py`, `argus/analytics/observatory_service.py`
  - Modifies: `argus/api/__init__.py`, `server.py`
  - Integrates: Reads from existing EvaluationEventStore, UniverseManager, SetupQualityEngine

- S2: Backend WebSocket live-update endpoint (pipeline stage counts, tier transitions, evaluation summaries at configurable interval)
  - Creates: `argus/api/websocket/observatory_ws.py`
  - Modifies: `server.py`
  - Integrates: S1's ObservatoryService

- S3: Frontend page shell, routing, keyboard shortcut system, Observatory layout (canvas + tier selector + detail panel zones)
  - Creates: `ObservatoryPage.tsx`, `useObservatoryKeyboard.ts`, `ObservatoryLayout.tsx`
  - Modifies: Navigation/routing config
  - Integrates: Existing Command Center navigation

- S3f: Visual review fixes — contingency, 0.5 session

- S4a: Frontend detail panel shell + condition grid + strategy history
  - Creates: `SymbolDetailPanel.tsx`, `SymbolConditionGrid.tsx`, `SymbolStrategyHistory.tsx`
  - Modifies: `ObservatoryLayout.tsx`
  - Integrates: S1's API endpoints, S3's layout

- S4b: Frontend detail panel candlestick chart + data hooks
  - Creates: `SymbolCandlestickChart.tsx`, `useSymbolDetail.ts`
  - Modifies: `SymbolDetailPanel.tsx`
  - Integrates: S4a's panel shell, existing Lightweight Charts dependency

- S4f: Visual review fixes — contingency, 0.5 session

- S5a: Frontend Matrix view core — condition heatmap with rows sorted by proximity to trigger
  - Creates: `MatrixView.tsx`, `MatrixRow.tsx`
  - Modifies: `ObservatoryPage.tsx`
  - Integrates: S1's closest-miss endpoint, S3's keyboard system

- S5b: Frontend Matrix virtualized scrolling + live-update sort + keyboard integration + click-to-detail
  - Creates: `useMatrixData.ts`
  - Modifies: `MatrixView.tsx`
  - Integrates: S4a/S4b detail panel (click row → populate panel)

- S5f: Visual review fixes — contingency, 0.5 session

- S6a: Frontend Three.js Funnel view — scene setup, tier rings as translucent discs, orbit controls, camera
  - Creates: `FunnelView.tsx`, `FunnelScene.ts`
  - Modifies: `ObservatoryPage.tsx`
  - Integrates: S3's keyboard system

- S6b: Frontend Funnel symbol particles — instanced mesh, position management, tier transition animations, click interaction
  - Creates: `FunnelSymbolManager.ts`
  - Modifies: `FunnelScene.ts`
  - Integrates: S1/S2 endpoints for tier populations, S4a/S4b detail panel (click particle → populate panel)

- S6f: Visual review fixes — contingency, 0.5 session

- S7: Frontend Radar view — camera animation from current perspective to bottom-up, concentric ring labels, center TRIGGER label
  - Creates: `RadarView.tsx`, `useCameraTransition.ts`
  - Modifies: `FunnelScene.ts` (radar-mode labels)
  - Integrates: S6a/S6b's Three.js scene, S3's keyboard system (view key `4`)

- S8: Frontend Timeline view — strategy lane timeline with event marks at evaluation/near-miss/signal/trade severity
  - Creates: `TimelineView.tsx`, `TimelineLane.tsx`, `useTimelineData.ts`
  - Modifies: `ObservatoryPage.tsx`
  - Integrates: S1's per-symbol journey endpoint, S3's keyboard system, S4a/S4b detail panel

- S8f: Visual review fixes — contingency, 0.5 session

- S9: Frontend session vitals bar + debrief mode (date picker, historical data loading)
  - Creates: `SessionVitalsBar.tsx`, `useSessionVitals.ts`, `useDebriefMode.ts`
  - Modifies: `ObservatoryLayout.tsx`, all data hooks (add date parameter)
  - Integrates: S2's WebSocket for live mode, S1's REST endpoints for debrief mode

- S9f: Visual review fixes — contingency, 0.5 session

- S10: Integration polish — keyboard edge cases, transition smoothness, loading/error states, end-to-end flow
  - Creates: None
  - Modifies: All Observatory components
  - Integrates: Full end-to-end keyboard flow across all views

**Key Decisions:**

- Observatory is a read-only visualization layer — does not modify any trading pipeline behavior
- Four views (Funnel, Radar, Matrix, Timeline) share the same page layout; only canvas content changes
- Funnel and Radar are the same Three.js scene with different camera positions; switching from Funnel to Radar animates the camera smoothly
- Three.js instanced meshes for symbol particles (efficient for 3,000+ symbols), LOD for ticker labels (visible only when zoomed in)
- Lightweight Charts for per-symbol candlestick chart in detail panel (already in stack)
- WebSocket endpoint for live pipeline updates separate from existing `/ws/v1/ai/chat`
- Config-gated via `observatory.enabled` (default: true) following DEC-300 pattern
- Keyboard-first interaction: all navigation possible without mouse
- Debrief mode reads from same EvaluationEventStore with date parameter (7-day retention already exists from Sprint 24.5)
- Code-split Three.js bundle to avoid degrading load time on other pages
- Virtual scrolling for Matrix view when tier has hundreds of symbols

**Scope Boundaries:**

- IN: New Observatory page, 4 views (Funnel/Radar/Matrix/Timeline), detail panel with candlestick chart, backend aggregation endpoints, WebSocket live updates, keyboard shortcuts, debrief mode, session vitals
- OUT: No new strategies (Red-to-Green deferred), no modifications to strategy logic, no changes to evaluation telemetry schema, no Quality Engine changes, no trading functionality changes, no replacement of existing pages, no order flow visualization, no historical replay animation (debrief is static snapshots not animated playback), no Synapse/3D strategy clustering

**Regression Invariants:**

- All 7 existing Command Center pages render and function unchanged
- Evaluation telemetry ring buffer and SQLite persistence unmodified
- No new Event Bus subscribers (reads from DB/API only)
- Existing WebSocket `/ws/v1/ai/chat` unaffected
- Strategy logic completely untouched
- All existing API endpoints unmodified
- Page load time for non-Observatory pages not degraded (Three.js code-split)

**File Scope:**

- Create (backend): `argus/api/routes/observatory.py`, `argus/analytics/observatory_service.py`, `argus/api/websocket/observatory_ws.py`
- Create (frontend, ~20 files): `ObservatoryPage.tsx`, `ObservatoryLayout.tsx`, `useObservatoryKeyboard.ts`, `SymbolDetailPanel.tsx`, `SymbolConditionGrid.tsx`, `SymbolStrategyHistory.tsx`, `SymbolCandlestickChart.tsx`, `useSymbolDetail.ts`, `MatrixView.tsx`, `MatrixRow.tsx`, `useMatrixData.ts`, `FunnelView.tsx`, `FunnelScene.ts`, `FunnelSymbolManager.ts`, `RadarView.tsx`, `useCameraTransition.ts`, `TimelineView.tsx`, `TimelineLane.tsx`, `useTimelineData.ts`, `SessionVitalsBar.tsx`, `useSessionVitals.ts`, `useDebriefMode.ts`
- Modify: `server.py`, `argus/api/__init__.py`, navigation/routing config, `ObservatoryPage.tsx` (multiple sessions wire views), `ObservatoryLayout.tsx` (multiple sessions wire components), `FunnelScene.ts` (radar labels added in S7)
- Do not modify: Any file in `argus/strategies/`, `argus/core/`, `argus/execution/`, `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/data/`, any existing page components, evaluation telemetry schema

**Config Changes:**

```yaml
observatory:
  enabled: true                    # ObservatoryConfig.enabled: bool
  ws_update_interval_ms: 1000      # ObservatoryConfig.ws_update_interval_ms: int
  timeline_bucket_seconds: 60      # ObservatoryConfig.timeline_bucket_seconds: int
  matrix_max_rows: 100             # ObservatoryConfig.matrix_max_rows: int
  debrief_retention_days: 7        # ObservatoryConfig.debrief_retention_days: int
```

Regression checklist item: "New observatory config fields verified against ObservatoryConfig Pydantic model (no silently ignored keys)."

**Test Strategy:**

- Backend: ~25 pytest (S1: 15 + S2: 10)
- Frontend: ~67 Vitest across S3–S10 (S3:8 + S4a:7 + S4b:5 + S5a:6 + S5b:4 + S6a:3 + S6b:3 + S7:4 + S8:8 + S9:8 + S10:6 + fix sessions:~5)
- Total estimated: ~25 pytest + ~67 Vitest = ~92 new tests
- Three.js sessions focus on data binding and interaction logic tests, not WebGL rendering
- Matrix view tests cover sort ordering, condition state mapping, keyboard navigation

**Runner Compatibility:**

- Mode: Human-in-the-loop
- Parallelizable sessions: None (heavy visual judgment dependencies)
- Runner-specific escalation notes: N/A (HITL mode)

**Dependencies:**

- Sprint 24.5 evaluation telemetry (EvaluationEventStore, ring buffer, REST endpoint) must be on main
- Three.js already in `package.json` (DEC-215)
- Lightweight Charts already in `package.json` (DEC-104)
- TanStack Query already configured

**Escalation Criteria:**

- Three.js performance below 30fps with 3,000+ symbol particles → escalate to optimize instancing/LOD before continuing
- WebSocket endpoint causes measurable degradation to existing `/ws/v1/ai/chat` → escalate
- Bundle size increase exceeds 500KB gzipped for Observatory chunk → escalate to optimize code-splitting
- Any modification to strategy logic, Event Bus, or trading pipeline discovered necessary → STOP and escalate to Tier 3

**Doc Updates Needed:**

- `docs/project-knowledge.md` — add Observatory to architecture, page list (8 pages), command reference
- `docs/architecture.md` — Observatory section, WebSocket endpoint documentation
- `docs/roadmap.md` — Sprint 25 status update, Phase 5 Gate results
- `CLAUDE.md` — current state update, test counts, new files
- `docs/sprint-history.md` — Sprint 25 entry
- `docs/dec-index.md` — new DEC entries
- `docs/decision-log.md` — full DEC rationale
- `docs/ui/ux-feature-backlog.md` — Observatory features marked as delivered

**Artifacts to Generate:**

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates and compaction scoring per session)
4. Sprint-Level Escalation Criteria
5. Sprint-Level Regression Checklist
6. Doc Update Checklist
7. Review Context File
8. Implementation Prompts ×13 (S1, S2, S3, S4a, S4b, S5a, S5b, S6a, S6b, S7, S8, S9, S10)
9. Review Prompts ×13
10. Work Journal Handoff Prompt

# Sprint 25: The Observatory

## Goal
Build a new Command Center page providing immersive, real-time and post-session visualization of the entire ARGUS trading pipeline — from the full 8,000-symbol universe through strategy evaluation to individual per-candle condition checks — enabling the operator to understand and diagnose system behavior at every level of granularity. This is the missing link between building the system and trusting the system.

## Scope

### Deliverables

1. **Observatory API endpoints** — REST endpoints providing session summary aggregation, pipeline stage counts (symbols per funnel tier), closest-miss ranking (symbols that passed the most conditions before rejection, sorted by proximity to trigger), and per-symbol pipeline journey (chronological evaluation history across all strategies for a given symbol and date).

2. **Observatory WebSocket endpoint** — Real-time push of pipeline stage counts, tier transition events, and evaluation summary updates at a configurable interval (`observatory.ws_update_interval_ms`, default 1000ms).

3. **Observatory page shell** — New Command Center page (page 8) with full-bleed canvas layout, collapsible sidebar, persistent tier selector, slide-out detail panel, session vitals bar, and four-view switching via keyboard shortcuts (`1` `2` `3` `4`).

4. **Keyboard-first interaction system** — Complete keyboard navigation: `Tab`/`Shift+Tab` cycle symbols within tier, `[`/`]` navigate tiers, `Enter` select symbol (opens detail panel), `Esc` deselect/close panel, `1`–`4` switch views, `/` symbol search, `R` reset camera, `F` fit view, `?` show shortcut overlay.

5. **Detail panel with live candlestick chart** — Right slide-out panel showing selected symbol's pipeline position, per-strategy condition check grid (green=pass, red=fail with actual vs. required values), quality score, market data snapshot, catalyst summary, chronological strategy history, and live-updating candlestick chart via Lightweight Charts. Panel persists across view switches and symbol changes; content live-updates when a different symbol is selected via keyboard or click.

6. **Funnel view (Three.js)** — 3D cone with horizontal translucent disc tiers representing pipeline stages. Symbols rendered as instanced mesh particles positioned on their current tier. Orbit controls for rotation/zoom. LOD: ticker labels visible only when zoomed in. Tier transition animations when symbols move between stages.

7. **Radar view** — Camera animated smoothly from current Funnel perspective to bottom-up view, transforming the funnel into concentric rings with the trigger point at center. Concentric ring labels and center "TRIGGER" indicator visible only in radar mode. Same Three.js scene as Funnel — different camera position.

8. **Matrix view** — Full-screen condition heatmap. Rows = symbols on currently-selected tier, sorted by proximity to trigger (most conditions passed at top). Columns = entry conditions for the relevant strategy. Cells color-coded green (pass) / red (fail) / gray (not applicable — strategy window inactive). Live-updating sort order as new evaluation data arrives. Virtualized scrolling for tiers with hundreds of symbols. Click row to populate detail panel.

9. **Timeline view** — Horizontal session timeline spanning the full trading day (9:30 AM – 4:00 PM ET). Each strategy gets a lane. Events plotted as marks at severity levels: faint dots (evaluations), medium marks (near-misses, 5+ conditions passed), bright marks (signals generated), large marks (trades executed). Click event to populate detail panel with context.

10. **Session vitals bar** — Top bar showing: connection status (Databento, IBKR), viable symbol count, total evaluations this session, market time, signals generated, trades executed, closest miss summary, top blocking condition with percentage.

11. **Debrief mode** — Date picker in vitals bar switches all data from live WebSocket to historical REST queries against persisted evaluation telemetry (7-day retention from Sprint 24.5). All four views populate from historical data for the selected date.

12. **ObservatoryConfig** — Pydantic config model with YAML-driven settings, config-gated via `observatory.enabled` (default: true).

### Acceptance Criteria

1. Observatory API endpoints:
   - `GET /api/v1/observatory/pipeline` returns tier counts for all 7 pipeline stages with accurate numbers
   - `GET /api/v1/observatory/closest-misses?tier={tier}&limit={n}` returns symbols sorted by conditions-passed descending, each with condition detail array
   - `GET /api/v1/observatory/symbol/{symbol}/journey?date={date}` returns chronological evaluation events across all strategies
   - `GET /api/v1/observatory/session-summary?date={date}` returns aggregated session metrics (total evaluations, signals, trades, top blockers)
   - All endpoints JWT-protected

2. Observatory WebSocket:
   - `WS /ws/v1/observatory` accepts connection with JWT token
   - Pushes pipeline stage count updates at configured interval
   - Pushes tier transition events when symbols move between stages
   - Does not interfere with existing `/ws/v1/ai/chat` endpoint

3. Observatory page:
   - Accessible from sidebar navigation
   - Renders full-bleed canvas (no card/grid layout)
   - Four views switch with `1` `2` `3` `4` keys with smooth transitions
   - Tier selector visible in all views with live counts
   - Detail panel slides out from right when symbol selected
   - Panel stays open across view and symbol changes
   - Code-split: Three.js bundle lazy-loaded, does not affect other page load times

4. Keyboard system:
   - All documented shortcuts functional
   - `Tab`/`Shift+Tab` cycle through symbols on current tier; detail panel live-updates
   - `[`/`]` change selected tier; Matrix view updates, Funnel highlights tier
   - `Enter`/`Esc` open/close detail panel
   - `/` opens symbol search overlay; typing filters, Enter jumps to symbol
   - `?` shows keyboard shortcut reference overlay

5. Detail panel:
   - Condition grid shows pass/fail for each condition with actual vs. required values
   - Candlestick chart renders with live-updating candles (1-minute bars)
   - Strategy history shows chronological evaluation events with timestamps
   - Quality score and grade badge displayed
   - Catalyst summary displayed (if available)
   - Market data (price, change, volume, ATR, VWAP, relative volume) displayed

6. Funnel view:
   - Renders 7 tier discs in perspective 3D
   - Symbol particles rendered via instanced mesh (handles 3,000+ without frame drops)
   - Orbit controls responsive (drag to rotate, scroll to zoom)
   - Symbol labels appear on hover/zoom via LOD
   - Click symbol particle selects it (populates detail panel)
   - Tier transition: symbols animate between tiers when their stage changes
   - Maintains 30+ fps with 3,000+ particles

7. Radar view:
   - Pressing `4` smoothly animates camera from current position to bottom-up
   - Concentric rings visible with tier labels
   - Center "TRIGGER" indicator visible
   - Symbols positioned by distance from center = distance from trigger
   - Pressing `1` (back to Funnel) smoothly animates camera to default perspective

8. Matrix view:
   - Rows sorted by conditions-passed descending (most promising at top)
   - Sort order updates live as new evaluation data arrives
   - Columns match the relevant strategy's entry conditions for that tier
   - Strategy window inactive shows "–" cells (not red)
   - Virtual scrolling handles 500+ rows without performance degradation
   - Click row selects symbol (populates detail panel)

9. Timeline view:
   - 4 strategy lanes spanning 9:30 AM – 4:00 PM ET
   - Event marks at 4 severity levels with distinct visual treatment
   - Click event mark populates detail panel with evaluation context
   - Active strategy windows visually indicated on each lane

10. Session vitals:
    - Connection status shows green/yellow/red for Databento and IBKR
    - All counters update in real-time via WebSocket
    - Top blocker shows most frequent rejection condition with percentage

11. Debrief mode:
    - Date picker switches data source from WebSocket to REST
    - All four views render correctly from historical data
    - "Market closed" indicator shown when viewing past dates
    - Date limited to 7-day retention window

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Three.js frame rate with 3,000+ particles | ≥ 30 fps | Chrome DevTools Performance tab |
| Matrix view scroll with 500 rows | Smooth, no jank | Manual scroll test, DevTools |
| View switch transition time | < 500ms | Visual observation |
| Detail panel update on symbol change | < 100ms | TanStack Query cache + React render |
| Observatory page initial load (code-split) | < 2s additional over base CC load | Network tab, throttled to Fast 3G |
| WebSocket update latency | < ws_update_interval_ms + 100ms | Timestamp comparison |
| Non-Observatory page load impact | < 50ms increase | Lighthouse before/after |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| observatory.enabled | ObservatoryConfig | enabled | true |
| observatory.ws_update_interval_ms | ObservatoryConfig | ws_update_interval_ms | 1000 |
| observatory.timeline_bucket_seconds | ObservatoryConfig | timeline_bucket_seconds | 60 |
| observatory.matrix_max_rows | ObservatoryConfig | matrix_max_rows | 100 |
| observatory.debrief_retention_days | ObservatoryConfig | debrief_retention_days | 7 |

## Dependencies

- Sprint 24.5 evaluation telemetry on main (EvaluationEventStore, BaseStrategy.eval_buffer, REST endpoint `GET /api/v1/strategies/{id}/decisions`)
- Three.js in `package.json` (added DEC-215, Sprint 21d)
- Lightweight Charts in `package.json` (added DEC-104, Sprint 15)
- TanStack Query configured (Sprint 21a+)
- Zustand store configured
- JWT auth middleware on API routes

## Relevant Decisions

- DEC-342: Strategy evaluation telemetry — ring buffer, SQLite persistence, REST endpoint. Provides the raw data Observatory consumes.
- DEC-104/215: Chart library decisions — Lightweight Charts for candlestick, Three.js for 3D. Both already in stack.
- DEC-169: Seven-page Command Center architecture. Observatory adds page 8.
- DEC-109: Design north star ("Bloomberg Terminal meets modern fintech, portal not tool"). Observatory is the most ambitious expression of this principle.
- DEC-328: Test suite tiering — full suite at sprint entry and closeout, scoped tests mid-sprint.
- DEC-300: Config-gating pattern — new features default-enabled but gated. Observatory follows this pattern.
- DEC-329: Frontend hooks gated on health status — Observatory WS hooks should handle disconnection gracefully.

## Relevant Risks

- RSK-046: Broad-universe processing throughput — Observatory reads from the same data but does not add processing load to the trading pipeline (read-only).
- RSK-036: AI Copilot latency — Observatory WebSocket is separate from Copilot WebSocket, no interference expected.
- New implicit risk: Three.js performance with thousands of particles. Mitigated by instanced meshes and LOD. Escalation criteria: < 30 fps triggers optimization before continuing.

## Session Count Estimate

13 implementation sessions + 5 visual-review fix contingency slots = up to 18 sessions. Rationale: 2 backend sessions, 11 frontend sessions (heavy UI/visualization work with Three.js, Lightweight Charts, virtual scrolling, and keyboard interaction). Iterative Judgment Loop applies — each frontend session includes visual review items. Fix slots budgeted per protocol at 0.5 sessions each for sessions S3, S4(a+b), S5(a+b), S6(a+b), S8, S9.

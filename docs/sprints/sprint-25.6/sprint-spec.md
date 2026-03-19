# Sprint 25.6: Bug Sweep

## Goal
Fix all operational bugs discovered during the March 19, 2026 live trading session — the first session after Sprint 25.5 watchlist wiring fix. Nine DEF items (065–073) plus one debrief finding (regime stagnation) and one log hygiene issue.

## Scope

### Deliverables
1. **Telemetry store DB separation** — Move `evaluation_events` table to dedicated `data/evaluation.db`, eliminating SQLite write contention with main DB
2. **Health check store reuse** — Pass existing `EvaluationEventStore` instance to health check loop instead of creating/destroying one per cycle
3. **Telemetry log spam suppression** — Rate-limit "Failed to write evaluation event" warning to once per minute
4. **Periodic regime reclassification** — Add asyncio task that re-evaluates market regime during market hours using accumulated SPY data
5. **Trades page: scroll replaces pagination** — Replace pagination with scrollable table body (20 visible rows, scroll for more)
6. **Trades page: metrics computed on full dataset** — Win rate and Net P&L derived from all trades matching the active time filter, not just visible rows
7. **Trades page: filter state persistence** — Time filter toggle drives both visual state and query parameters on page re-entry
8. **Trades page: sortable columns** — Column headers clickable for ascending/descending sort
9. **Orchestrator: AfMo label truncation** — Fix "Afternoon Momentum" displaying as "on Momentum" in Strategy Coverage timeline
10. **Orchestrator: throttled status accuracy** — Investigate and fix VWAP Reclaim shown as throttled during its operating window
11. **Dashboard: layout restructure** — Promote Positions card to Row 2 (immediately below financial scoreboard), reorganize remaining cards

### Acceptance Criteria
1. Telemetry store DB separation:
   - `EvaluationEventStore` connects to `data/evaluation.db`, not `data/argus.db`
   - Table and indexes created in `evaluation.db`
   - No "database is locked" errors under concurrent candle processing
   - Main DB operations (trades, quality_history, orchestrator_decisions) unaffected
2. Health check store reuse:
   - `_run_evaluation_health_check()` receives store instance, does not call `EvaluationEventStore()` or `initialize()`
   - No repeated "EvaluationEventStore initialized" log entries every 60s
3. Log spam suppression:
   - Repeated telemetry write failures logged at most once per 60 seconds
   - First failure in any window still logged with full traceback
4. Regime reclassification:
   - Regime updates at least every 5 minutes during market hours (9:30–16:00 ET)
   - Regime does NOT update outside market hours
   - Log entry on each reclassification: "Regime reclassified: {old} → {new}" (or "Regime unchanged: {current}" at DEBUG level)
   - If SPY data still unavailable, log warning and retain current regime (do not crash)
5. Trades page scroll:
   - No pagination controls visible
   - Table scrolls vertically when more than 20 rows
   - All rows accessible via scrolling
6. Trades page metrics:
   - Win rate and Net P&L computed from full query result for active time filter
   - Values do not change when scrolling
7. Trades page filter persistence:
   - Navigate away from Trades, return: toggle visual state AND table data match
   - Switching filter updates both toggle and query immediately
8. Trades page sorting:
   - Clicking column header sorts ascending; clicking again sorts descending
   - Sort indicator visible on active column
   - At minimum: Symbol, Strategy, P&L, R, Time columns sortable
9. AfMo label:
   - "Afternoon Momentum" fully visible on desktop (≥1024px), no truncation
   - Short name used on tablet/mobile breakpoints
10. Throttled status:
    - Active strategies within their operating window shown with solid (non-hatched) bars
    - Hatched/striped rendering ONLY for actually throttled or suspended strategies
11. Dashboard layout:
    - Positions card visible without scrolling on 1080p desktop viewport
    - Financial scoreboard (Account Equity / Daily P&L / Monthly Goal) remains Row 1
    - Positions immediately below in Row 2
    - All existing cards still render with correct data

### Performance Benchmarks
N/A — bug fix sprint, no new performance-sensitive components.

### Config Changes
No config changes in this sprint.

## Dependencies
- Sprint 25.5 complete (watchlist wiring — confirmed)
- March 19 session debrief complete (findings documented)
- ARGUS repo at current HEAD (`fbffe39`)

## Relevant Decisions
- DEC-309: Separate `catalyst.db` for catalyst storage (pattern for DEF-065)
- DEC-328: Test suite tiering (scoped tests for mid-sprint sessions)
- DEC-342: Strategy evaluation telemetry (ring buffer + SQLite persistence)
- DEC-329: Gate frontend hooks on pipeline health status

## Relevant Risks
- RSK-022: IBKR Gateway nightly resets (regime reclassification must handle disconnects gracefully)

## Session Count Estimate
5 sessions + 0.5 contingency for visual review fixes. All scored ≤13 on compaction risk. Total estimated implementation time: 2–3 hours.

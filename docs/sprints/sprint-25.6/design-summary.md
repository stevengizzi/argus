# Sprint 25.6 Design Summary

**Sprint Goal:** Fix all operational bugs discovered during the March 19 live trading session — telemetry store contention, regime stagnation, Trades page UX, Orchestrator display, and Dashboard layout.

**Session Breakdown:**
- Session 1: Telemetry store DB separation (DEF-065 + DEF-066) + log spam suppression
  - Creates: None
  - Modifies: `argus/strategies/telemetry_store.py`, `argus/main.py`, `argus/api/server.py`
  - Integrates: N/A (self-contained fix)
- Session 2: Periodic regime reclassification during market hours
  - Creates: None
  - Modifies: `argus/core/orchestrator.py`, `argus/main.py`
  - Integrates: N/A (self-contained fix)
- Session 3: Trades page fixes (DEF-067/068/069/073 — scroll, metrics, filter sync, sorting)
  - Creates: None
  - Modifies: `argus/ui/src/pages/TradesPage.tsx`, related hooks/components
  - Integrates: N/A (self-contained frontend fixes)
- Session 4: Orchestrator timeline fixes (DEF-070/071 — label truncation, throttled status)
  - Creates: None
  - Modifies: `argus/ui/src/features/orchestrator/StrategyCoverageTimeline.tsx`, possibly `argus/api/routes/orchestrator.py`
  - Integrates: N/A (self-contained fixes)
- Session 5: Dashboard layout restructure (DEF-072 — promote Positions above fold)
  - Creates: None
  - Modifies: `argus/ui/src/pages/DashboardPage.tsx`, possibly component files
  - Integrates: N/A (self-contained layout change)
- Session 5f: Visual review fixes — contingency, 0.5 session

**Key Decisions:**
- DEF-065 fix uses dedicated `data/evaluation.db` (proven pattern from `catalyst.db` / DEC-309)
- Regime reclassification runs as periodic asyncio task (~5 min interval) using existing `_classify_regime()` logic, only during market hours
- Log spam fix: rate-limit the "Failed to write evaluation event" warning to at most once per minute (after DB fix, this should rarely fire, but defense in depth)
- Health check reuses the store instance created in `server.py` lifespan rather than constructing a new one per cycle

**Scope Boundaries:**
- IN: DEF-065 through DEF-073, regime reclassification, telemetry log spam fix
- OUT: Trade performance tuning, Observatory frontend visualization fixes (need data flowing first), new features, parameter changes, Learning Loop

**Regression Invariants:**
- All existing trades still logged to `argus.db` (trade_logger unchanged)
- Quality history still written to `argus.db` (quality_history table unchanged)
- Catalyst events still written to `catalyst.db` (unchanged)
- All 4 strategies still register and run
- EOD flatten + auto-shutdown still functions
- Frontend: all existing pages render without errors
- All API endpoints return same response schemas

**File Scope:**
- Modify: `telemetry_store.py`, `main.py`, `server.py`, `orchestrator.py`, `TradesPage.tsx`, `StrategyCoverageTimeline.tsx`, `DashboardPage.tsx`, related hooks/components
- Do not modify: `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, strategy files (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`), `trade_logger.py`, `catalyst_pipeline.py`, DB manager (`db/manager.py`)

**Config Changes:** No config changes.

**Test Strategy:**
- S1: ~5 new pytest (DB separation, store reuse, log suppression)
- S2: ~4 new pytest (regime update task, classification call, market hours guard)
- S3: ~4 new Vitest (scroll behavior, metrics source, filter persistence, sort)
- S4: ~2 new Vitest (label rendering, status mapping)
- S5: ~2 new Vitest (layout order, Positions visibility)
- Total estimate: ~17 new tests

**Runner Compatibility:**
- Mode: Human-in-the-loop
- Parallelizable sessions: S3, S4, S5 are independent frontend sessions (could run in parallel, but HITL mode makes this moot)
- No runner config needed

**Dependencies:**
- Sprint 25.5 complete (watchlist wiring fix — confirmed working)
- March 19 session debrief findings documented (done — `def-items-2026-03-19.md` and `session-debrief-2026-03-19.md`)

**Escalation Criteria:**
- S1: If `evaluation.db` connection interferes with `argus.db` operations → escalate (unexpected cross-DB issue)
- S2: If regime reclassification logic doesn't exist in orchestrator and needs to be built from scratch → rescope to design session first
- S3–S5: No escalation expected (straightforward frontend changes)

**Doc Updates Needed:**
- `docs/project-knowledge.md` — update test counts, add DEC references
- `docs/decision-log.md` — new DEC entries for DB separation and regime reclassification
- `docs/dec-index.md` — index new DECs
- `docs/sprint-history.md` — add Sprint 25.6 entry
- `CLAUDE.md` — resolve DEF-065 through DEF-073

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown
4. Implementation Prompt ×5
5. Review Prompt ×5
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff Prompt

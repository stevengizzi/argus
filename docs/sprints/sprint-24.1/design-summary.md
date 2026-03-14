# Sprint 24.1 Design Summary

**Sprint Goal:** Clean up 13 accumulated housekeeping items (DEF-050 through DEF-062) from Sprint 24 reviews before the Phase 5 Gate strategic check-in. No new features, no architectural changes.

**Execution Mode:** Human-in-the-loop

**DEC Range Reserved:** DEC-342 through DEC-345 (contingency only)

**Session Breakdown:**

- Session 1a: Wire quality_grade/quality_score through trades persistence chain (schema → Trade model → ManagedPosition → TradeLogger). Compaction score: 16 (High — accepted; 4 surgical file modifications along single logical chain).
  - Creates: nothing
  - Modifies: `argus/db/schema.sql`, `argus/models/trading.py`, `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`
  - Integrates: N/A (completes backend chain; API routes + frontend already pre-wired in Sprint 24)
  - Items: 2 (DEF-058)
  - Tests: ~8 (ManagedPosition quality fields, Trade model optional fields, TradeLogger INSERT/read with quality, _row_to_trade with quality present and absent)

- Session 1b: Trivial backend fixes — CatalystStorage log level, SetupQualityEngine public accessors, EFTS URL diagnostic, PROVISIONAL comments, seed script guard. Compaction score: 13.5 (Medium).
  - Creates: nothing
  - Modifies: `argus/main.py` (1 line), `argus/intelligence/quality_engine.py` (add @property methods), `argus/api/routes/quality.py` (use public accessors), `config/system.yaml` (comment), `config/system_live.yaml` (comment), `scripts/seed_quality_data.py` (guard)
  - Integrates: N/A (independent fixes)
  - Items: 1, 3, 4, 12, 13 (DEF-057, DEF-060, DEF-061, DEF-062)
  - Tests: ~4 (accessor properties, seed script guard)

- Session 2: True ArgusSystem e2e integration test exercising full quality pipeline (strategy signal → quality engine score → dynamic sizer → risk manager evaluate). Plus EFTS URL live validation diagnostic. Compaction score: 17.5 (High — accepted; creates 1 file, modifies 0, high score from context reads only).
  - Creates: `tests/test_argus_e2e_quality.py` (or `tests/integration/test_quality_pipeline_e2e.py`)
  - Modifies: possibly `argus/intelligence/sources/sec_edgar.py` (only if EFTS URL broken)
  - Integrates: Exercises Session 1a's quality wiring through full system
  - Items: 8, 4 (DEF-050, DEF-057)
  - Tests: ~8 (e2e test with multiple assertions covering signal emission, quality scoring, sizing, RM evaluation)

- Session 3: Fix all 22 pre-existing TypeScript strict-mode build errors. Compaction score: 12 (Medium).
  - Creates: nothing
  - Modifies: ~8 files — `src/api/types.ts` (add missing fields to StrategyInfo), `src/components/CatalystAlertPanel.tsx`, `src/features/copilot/ChatMessage.tsx`, `src/features/copilot/StreamingMessage.tsx`, `src/features/copilot/CopilotPanel.tsx`, `src/features/copilot/TickerText.tsx`, `src/features/dashboard/AIInsightCard.tsx`, `src/features/dashboard/PositionDetailPanel.tsx`, `src/features/debrief/journal/ConversationBrowser.tsx`, `src/pages/PatternLibraryPage.tsx`, `src/pages/TradesPage.tsx`
  - Integrates: N/A
  - Items: 7 (DEF-059)
  - Tests: 0 new (validation = `npx tsc --noEmit` exits 0 + Vitest passes)

- Session 4a: Frontend layout fixes — Orchestrator 3-column layout, QualityOutcomeScatter relocation from Debrief to Performance. Compaction score: 7 (Low).
  - Creates: nothing
  - Modifies: `src/pages/OrchestratorPage.tsx`, Debrief page/tabs (remove Quality tab, remove 'q' shortcut), Performance page/tabs (add scatter to Distribution tab)
  - Integrates: N/A
  - Items: 5, 6 (DEF-055, DEF-056)
  - Tests: ~2

- Session 4b: Frontend interactivity — dashboard quality card tooltips/legend, quality column in Dashboard tables, clickable Orchestrator signal rows. Compaction score: 11.5 (Medium).
  - Creates: 1 file (signal detail panel/modal component)
  - Modifies: Dashboard quality cards (QualityDistributionCard, SignalQualityPanel), Dashboard Positions table, Dashboard Recent Trades table, Orchestrator RecentSignals component
  - Integrates: N/A
  - Items: 9, 10, 11 (DEF-052, DEF-053, DEF-054)
  - Tests: ~3

- Session 4f: Visual review fixes — contingency, 0.5 session. Covers any issues found during Session 4a/4b visual review.

**Key Decisions:**
- Accept S1a at compaction score 16 (High) because the 4 modified files form a single logical chain that cannot be split without creating half-wired state.
- Accept S2 at compaction score 17.5 (High) because it creates only 1 file and modifies 0 — compaction risk is from context reads, not dangerous modifications.
- EFTS validation is a diagnostic (run curl, document result, fix only if broken) — scored as +1.5, not +3 for external API debugging.
- Donut chart clickable segments (filter to grade) are stretch goal for item 9 — deferred if not trivial.

**Scope Boundaries:**
- IN: 13 cleanup items from Sprint 24 reviews (DEF-050 through DEF-062). Backend quality wiring, trivial fixes, TypeScript errors, frontend layout/interactivity polish.
- OUT: No new features. No architectural changes. No strategy logic changes. No Intelligence Pipeline polling/classification changes. No new API endpoints. No new database tables. No dependency upgrades. No config schema changes (only YAML comments).

**Regression Invariants:**
- Order Manager position lifecycle must not change behavior (entry fills, bracket orders, position closing)
- Existing trades with NULL quality_grade/quality_score must display correctly (no crashes)
- TradeLogger must handle both quality-present and quality-absent Trade objects
- Schema migration must be idempotent (ALTER TABLE ADD COLUMN IF NOT EXISTS or equivalent)
- Quality engine disabled path (BrokerSource.SIMULATED or enabled=false) must still work — signals pass through with empty quality fields
- All 2,686 pytest + 497 Vitest must continue to pass
- TypeScript fixes must not change runtime behavior (strict-mode only)
- Frontend layout changes must not break mobile/PWA rendering

**File Scope:**
- Modify (backend): `argus/db/schema.sql`, `argus/models/trading.py`, `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`, `argus/main.py`, `argus/intelligence/quality_engine.py`, `argus/api/routes/quality.py`, `config/system.yaml`, `config/system_live.yaml`, `scripts/seed_quality_data.py`
- Modify (frontend): ~8 TS/TSX files for type fixes + ~6 for layout/interactivity
- Create: 1 test file (e2e), possibly 1 UI component (signal detail panel)
- Do not modify: `argus/core/events.py`, `argus/strategies/`, `argus/intelligence/__init__.py` (pipeline), `argus/intelligence/classifier.py`, `argus/intelligence/sources/`, `argus/core/risk_manager.py`, `argus/data/`, config schema structure

**Config Changes:** No config schema changes. Only adding PROVISIONAL comments to `system.yaml` and `system_live.yaml` quality_engine sections.

**Test Strategy:**
- Session 1a: ~8 new tests (Trade model quality fields, ManagedPosition fields, TradeLogger round-trip with quality present/absent)
- Session 1b: ~4 new tests (accessor properties, seed script guard, EFTS diagnostic)
- Session 2: ~8 new tests (ArgusSystem e2e: signal → quality → sizer → RM, multiple assertion points)
- Session 3: 0 new tests (validation = `tsc --noEmit` exits 0)
- Sessions 4a/4b: ~5 new tests (component renders, detail panel)
- Total estimated: ~25 new tests
- Pre-flight: full suite with `-n auto` for S1a, scoped for subsequent sessions
- Close-out: full suite for all sessions

**Runner Compatibility:**
- Mode: Human-in-the-loop
- Parallelizable sessions: S3 (TypeScript fixes) is independent of all others. S4a/S4b can run after S3 but are independent of S1a/S1b/S2. However, flagging as non-parallel since human-in-the-loop.
- Runner config: not generated

**Dependencies:**
- S1a must complete before S2 (e2e test exercises S1a's wiring)
- S1b is independent of S1a (can run in any order)
- S3 is independent of all backend sessions
- S4a/S4b depend on S3 (TS errors should be fixed before adding more frontend code)
- S4f depends on S4a/S4b

**Escalation Criteria:**
- ALTER TABLE migration fails on existing database with trade data
- Order Manager behavior changes detected (any test involving position lifecycle)
- ArgusSystem e2e test reveals quality pipeline wiring bugs that require architectural changes
- EFTS URL is fundamentally broken and requires SEC EDGAR API redesign

**Doc Updates Needed:**
- `docs/project-knowledge.md` — update test counts, sprint history, DEF status
- `docs/sprint-history.md` — add Sprint 24.1 entry
- `docs/dec-index.md` — add any new DECs (if any emerge)
- `CLAUDE.md` — update test counts

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with scoring tables)
4. Sprint-Level Escalation Criteria
5. Sprint-Level Regression Checklist
6. Doc Update Checklist
7. Review Context File
8. Implementation Prompts ×7 (S1a, S1b, S2, S3, S4a, S4b, S4f)
9. Review Prompts ×7
10. Work Journal Handoff Prompt

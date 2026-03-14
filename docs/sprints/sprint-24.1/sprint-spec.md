# Sprint 24.1: Post-Sprint Cleanup & Housekeeping

## Goal
Clean up 13 accumulated housekeeping items (DEF-050 through DEF-062) from Sprint 24 reviews before the Phase 5 Gate strategic check-in. No new features or architectural changes — purely executing deferred cleanup items to reduce technical debt.

## Scope

### Deliverables

1. **Trades DB quality columns (DEF-058):** Quality grade and score persisted through the full trades chain — ManagedPosition → Trade model → trades table → TradeLogger. Frontend Trades table shows actual quality badges instead of "—".
2. **SetupQualityEngine public accessors (DEF-061):** API routes use `engine.db` and `engine.config` instead of private `_db` and `_config` attributes.
3. **CatalystStorage init log level:** `logger.debug` → `logger.warning` on CatalystStorage initialization failure in `argus/main.py` Phase 10.25.
4. **EFTS URL live validation (DEF-057):** Diagnostic curl against SEC EDGAR EFTS endpoint without `q` parameter. Document result. Fix URL if broken.
5. **Orchestrator 3-column layout (DEF-055):** Decision Log, Catalyst Alerts, and Recent Signals in a shared 3-column row on desktop instead of Recent Signals taking a full row.
6. **QualityOutcomeScatter relocation (DEF-056):** Move scatter plot from Debrief Quality tab to Performance Distribution tab. Remove Quality tab from Debrief (revert to 5 sections, remove 'q' shortcut, update docstring).
7. **TypeScript build errors (DEF-059):** Fix all 22 pre-existing `tsc --noEmit` strict-mode errors across ~8 frontend files.
8. **ArgusSystem e2e integration test (DEF-050):** Single test exercising the full quality pipeline through real ArgusSystem init: strategy emits signal → quality engine scores → dynamic sizer calculates shares → risk manager evaluates.
9. **Dashboard quality card interactivity (DEF-052):** Hover tooltips on donut chart segments and histogram bars. Legend on donut chart. Clickable segments are stretch goal.
10. **Quality column in Dashboard tables (DEF-053):** QualityBadge column in Positions table and Recent Trades table on Dashboard page.
11. **Orchestrator clickable signal rows (DEF-054):** Click a Recent Signals row to show quality breakdown, entry/stop prices, pattern strength components.
12. **PROVISIONAL comment in system YAMLs (DEF-060):** Add PROVISIONAL note to `quality_engine` sections in `system.yaml` and `system_live.yaml`.
13. **Seed script production guard (DEF-062):** Refuse to run without `--i-know-this-is-dev` flag.

### Acceptance Criteria

1. **Trades DB quality columns:**
   - `trades` table has `quality_grade TEXT` and `quality_score REAL` columns (nullable)
   - `ManagedPosition` dataclass has `quality_grade: str = ""` and `quality_score: float = 0.0` fields
   - `Trade` model has optional `quality_grade: str = ""` and `quality_score: float = 0.0` fields
   - `TradeLogger.log_trade()` persists quality fields to DB
   - `TradeLogger._row_to_trade()` reads quality fields from DB rows
   - `_handle_entry_fill()` populates quality fields from signal onto ManagedPosition
   - `_close_position()` passes quality fields from ManagedPosition to Trade
   - Existing trades with NULL quality columns load without error
   - Schema migration is idempotent (safe to run on existing DB)

2. **SetupQualityEngine public accessors:**
   - `SetupQualityEngine` has `@property` methods `db` and `config`
   - `argus/api/routes/quality.py` uses `engine.db` and `engine.config` (no `_db`/`_config`)
   - No `# type: ignore[union-attr]` comments remain for these accesses

3. **CatalystStorage init log level:**
   - Line 559 of `argus/main.py` uses `logger.warning` not `logger.debug`

4. **EFTS URL validation:**
   - Live curl executed against `https://efts.sec.gov/LATEST/search-index?dateRange=custom&startdt={date}&forms=8-K,4`
   - Result documented in close-out report
   - If URL returns error: fix applied and tested. If URL works: no code changes.

5. **Orchestrator 3-column layout:**
   - Desktop view shows Decision Log, Catalyst Alerts, and Recent Signals in a single 3-column row
   - Mobile view stacks them vertically (responsive)

6. **QualityOutcomeScatter relocation:**
   - Scatter plot renders in Performance Distribution tab
   - Debrief page has exactly 5 sections (no Quality tab)
   - 'q' keyboard shortcut removed from Debrief navigation
   - DebriefPage docstring updated

7. **TypeScript build errors:**
   - `npx tsc --noEmit -p tsconfig.app.json` exits with 0 errors
   - No runtime behavior changes (Vitest passes)

8. **ArgusSystem e2e integration test:**
   - Test creates ArgusSystem with quality engine enabled and BrokerSource != SIMULATED
   - Test feeds a SignalEvent through `_process_signal()`
   - Assertions verify: quality engine `score_setup()` was called, sizer `calculate_shares()` was called, risk manager `evaluate_signal()` was called with enriched signal containing quality_grade and quality_score
   - Test passes in CI (no external API calls — all mocked)

9. **Dashboard quality card interactivity:**
   - Donut chart segments show tooltip on hover with grade name and count
   - Donut chart has a legend
   - Histogram bars show tooltip on hover with score range and count

10. **Quality column in Dashboard tables:**
    - Positions table shows QualityBadge column
    - Recent Trades table shows QualityBadge column
    - Null/empty quality gracefully shows "—"

11. **Orchestrator clickable signal rows:**
    - Clicking a Recent Signals row expands/opens a detail view
    - Detail view shows: quality grade, quality score, score breakdown by dimension, entry price, stop price, pattern strength

12. **PROVISIONAL comment:**
    - Both `config/system.yaml` and `config/system_live.yaml` have a comment in the quality_engine section noting thresholds are PROVISIONAL

13. **Seed script guard:**
    - Running `python scripts/seed_quality_data.py` without `--i-know-this-is-dev` prints a warning and exits non-zero
    - Running with the flag proceeds normally

### Performance Benchmarks
Not applicable — no performance-sensitive changes.

### Config Changes
No config schema changes in this sprint. Only YAML comment additions (PROVISIONAL note).

## Dependencies
- Sprint 24 complete and merged to main (confirmed)
- Quality engine, quality API routes, and frontend quality components all exist
- Frontend Trade type already has quality_grade/quality_score fields
- API trades routes already read quality columns from DB (return null when columns missing)

## Relevant Decisions
- DEC-330 (SignalEvent enrichment): quality_score/quality_grade fields exist on SignalEvent — this sprint completes the persistence chain
- DEC-331 (pattern_strength + share_count=0): strategies emit share_count=0; quality pipeline enriches
- DEC-336 (pipeline wiring + RM check 0): _process_signal() flow is the context for trades wiring
- DEC-277 (fail-closed on missing data): quality fields should be nullable/optional, not required
- DEC-328 (test suite tiering): applies to pre-flight/close-out test commands

## Relevant Risks
- RSK-022 (IBKR Gateway resets): not directly relevant but Order Manager changes must not affect reconnection
- Schema migration on existing DB with trade data: use ALTER TABLE ADD COLUMN (SQLite supports this safely)

## Session Count Estimate
6 sessions + 0.5 contingency = 6.5 sessions. Higher than typical cleanup sprint due to true ArgusSystem e2e test (complex context) and frontend work requiring visual review cycle.

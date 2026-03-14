# Sprint 24.1 — Regression Checklist

Every session close-out and review must verify these invariants hold.

## Critical Invariants

- [ ] **Order Manager position lifecycle unchanged:** Entry fills create ManagedPosition with correct bracket order IDs. Stop execution, T1/T2 fills, and position closing all work identically to pre-sprint behavior. The only addition is quality data passthrough — no logic changes.
- [ ] **TradeLogger handles both quality-present and quality-absent trades:** A Trade with quality_grade="" and quality_score=0.0 inserts and reads back correctly. A Trade with quality_grade="B+" and quality_score=72.5 inserts and reads back correctly. NULL values from pre-sprint trades load without error.
- [ ] **Schema migration is idempotent:** Running the schema creation/migration against an existing database with trade records does not lose data, and running it twice does not fail.
- [ ] **Quality engine bypass path intact:** When BrokerSource.SIMULATED or quality_engine.enabled=false, _process_signal() uses legacy sizing. No quality fields populated on signal. Trades still log successfully with empty quality data.
- [ ] **All 2,686 pytest pass** (full suite with `-n auto`)
- [ ] **All 497 Vitest pass** (`npm test` in argus/ui)
- [ ] **TypeScript build clean:** `npx tsc --noEmit -p tsconfig.app.json` exits 0 (after S3)
- [ ] **API response shapes unchanged:** `/api/v1/trades` already returns quality_grade and quality_score fields (as null). After S1a, they return actual values for new trades. No field additions/removals to any API response.
- [ ] **Frontend renders without console errors:** No new React warnings or errors in browser console after frontend sessions.

## Per-Session Regression Focus

### Session 1a
- [ ] Existing tests in `tests/execution/test_order_manager*.py` pass without modification
- [ ] Existing tests in `tests/analytics/test_trade_logger.py` pass (may need minor update for new columns)
- [ ] `tests/db/test_manager.py` passes (schema changes compatible)

### Session 1b
- [ ] Quality API routes (`/api/v1/quality/*`) return same responses as before
- [ ] Seed script with `--i-know-this-is-dev` flag produces same output as before
- [ ] Seed script without flag exits with non-zero code

### Session 2
- [ ] No existing tests modified (e2e test is additive only)
- [ ] E2E test does not require external network access (all mocked)

### Session 3
- [ ] No runtime behavior changes — only type annotations/casts modified
- [ ] Vitest passes (runtime correctness unchanged)
- [ ] `tsc --noEmit` exits 0

### Sessions 4a/4b
- [ ] Debrief page loads with 5 sections (no Quality tab)
- [ ] Performance page loads with scatter plot in Distribution tab
- [ ] Orchestrator page loads with 3-column layout
- [ ] Dashboard tables show quality badges where data exists, "—" where null
- [ ] All existing Vitest component tests pass

# Sprint 24.1, Session 2: ArgusSystem E2E Quality Test + EFTS Validation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context (this session requires deep understanding of the system init):
   - `argus/main.py` — `ArgusSystem` class, especially `__init__()`, `start()`, and `_process_signal()` method
   - `argus/intelligence/quality_engine.py` — `SetupQualityEngine` class, `score_setup()` method
   - `argus/intelligence/position_sizer.py` — `DynamicPositionSizer.calculate_shares()`
   - `argus/core/risk_manager.py` — `evaluate_signal()` method signature
   - `argus/core/events.py` — `SignalEvent`, `QualitySignalEvent`, `OrderApprovedEvent` dataclasses
   - `argus/execution/order_manager.py` — understand what happens after RM approval
   - `config/system.yaml` and `config/quality_engine.yaml` — config structure for quality engine
   - `argus/intelligence/sources/sec_edgar.py` — EFTS URL at line 53 and `_fetch_firehose_filings()` at line 177
2. Run the scoped test baseline:
   ```
   python -m pytest tests/intelligence/ -x -q
   ```
   Expected: all passing
3. Verify you are on branch `sprint-24.1`

## Objective
Write a true end-to-end integration test that exercises the full quality pipeline through real ArgusSystem initialization. Also validate the SEC EDGAR EFTS URL works without a `q` parameter.

## Requirements

### Part 1: ArgusSystem E2E Quality Test

Create `tests/integration/test_quality_pipeline_e2e.py` (create the `tests/integration/` directory if it doesn't exist).

The test should:

1. **Set up a real ArgusSystem** with:
   - Quality engine **enabled** (`quality_engine.enabled: true`)
   - `BrokerSource` that is NOT `SIMULATED` (so the quality pipeline is exercised, not bypassed)
   - A mock/fake broker (not real IBKR) — use `unittest.mock.AsyncMock` or a test double
   - A mock data service (no real Databento)
   - In-memory SQLite databases for both argus.db and catalyst.db
   - At least one strategy that can emit a signal
   - Config loaded from test fixtures (not production config files)

2. **Feed a SignalEvent** through `_process_signal()`:
   - Create a SignalEvent with realistic fields (symbol, strategy_id, entry_price, stop_price, target_prices)
   - Set `share_count=0` and `pattern_strength` > 0 (as strategies do after Sprint 24)
   - Call `await argus_system._process_signal(signal, strategy)` directly

3. **Assert the pipeline ran correctly:**
   - Quality engine's `score_setup()` was called (mock/spy it to verify)
   - The score result has a valid `grade` and `score`
   - DynamicPositionSizer's `calculate_shares()` was called with the quality result
   - Risk Manager's `evaluate_signal()` was called with an enriched signal that has `quality_grade` and `quality_score` populated
   - Quality history was recorded (check `quality_history` table has a row)

4. **Test the bypass path too:**
   - Create a second test with `quality_engine.enabled: false`
   - Feed the same signal
   - Assert: quality engine NOT called, legacy sizing used, signal still reaches RM

5. **Test the grade filter:**
   - Create a test where quality engine returns a grade below `min_grade_to_trade`
   - Assert: signal is filtered (does not reach RM), quality history records `shares=0`

**Key implementation challenge:** ArgusSystem.__init__() and start() do a LOT of initialization. You'll need to carefully mock out:
- Databento data service (use a mock that doesn't connect)
- IBKR broker (use AsyncMock with `get_account()` returning a mock account with buying_power)
- Scanner (mock or disable)
- Orchestrator (can be real if it doesn't need external data, or mock `current_regime`)
- Event bus (use real event bus — it's in-process asyncio)

Consider whether you can call `_process_signal()` directly without a full `start()` — you may be able to construct ArgusSystem, set up the quality engine and sizer manually, and test the method in isolation while still using the real code path.

### Part 2: EFTS URL Validation

Run a live diagnostic (as part of the session, not as a test):
```bash
curl -s -o /dev/null -w "%{http_code}" "https://efts.sec.gov/LATEST/search-index?dateRange=custom&startdt=2026-03-13&forms=8-K,4"
```

Document the result in the close-out report:
- If 200: URL works without `q` parameter. No code changes needed.
- If 4xx/5xx: Document the error. Check if adding `&q=*` or similar fixes it. If fix is a simple URL parameter change in `sec_edgar.py`, apply it. If fix requires architectural changes, document and defer.

## Constraints
- Do NOT modify: `argus/main.py`, `argus/intelligence/quality_engine.py`, `argus/core/risk_manager.py`, or any production code (this session creates tests only)
- Exception: `argus/intelligence/sources/sec_edgar.py` MAY be modified if EFTS URL is broken (simple URL fix only)
- Do NOT create tests that require network access — all external services must be mocked
- Do NOT modify existing test files

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. E2E: quality pipeline happy path (signal → score → size → RM)
  2. E2E: bypass path (quality disabled → legacy sizing → RM)
  3. E2E: grade filter (below minimum → signal filtered, history recorded with shares=0)
  4. E2E: quality data enrichment (RM receives signal with quality_grade and quality_score populated)
  5. E2E: quality history recording (row exists in quality_history table)
  6–8. Additional edge case tests as discovered during implementation
- Minimum new test count: 5
- Test command: `python -m pytest tests/integration/test_quality_pipeline_e2e.py -x -v`

## Definition of Done
- [ ] E2E test file created with 5+ tests
- [ ] Tests exercise real ArgusSystem code paths (not just unit mocks)
- [ ] Quality pipeline happy path, bypass path, and grade filter all tested
- [ ] All tests pass without network access
- [ ] EFTS URL diagnostic documented in close-out
- [ ] All existing tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No production code modified | `git diff --name-only` shows only test files (+ possibly sec_edgar.py for EFTS) |
| E2E tests don't require network | Tests pass with no internet access |
| Existing tests unaffected | `python -m pytest tests/intelligence/ tests/execution/ -x -q` — same count, all pass |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-2-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

**IMPORTANT:** Include the EFTS diagnostic result in the close-out report under a dedicated section.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session):
   ```
   python -m pytest tests/integration/test_quality_pipeline_e2e.py -x -v
   ```
5. Files that should NOT have been modified:
   - `argus/main.py`
   - `argus/intelligence/quality_engine.py`
   - `argus/core/risk_manager.py`
   - `argus/execution/order_manager.py`
   - Any existing test files
   - Exception: `argus/intelligence/sources/sec_edgar.py` MAY be modified if EFTS URL was broken

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-24.1/session-2-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **No production code modified:** This session should only create test files (and possibly fix sec_edgar.py). Verify the diff contains no other production code changes.
2. **Test exercises real code paths:** Verify the e2e test calls actual ArgusSystem._process_signal() (or equivalent real method), not just mocked stand-ins.
3. **No network access:** Verify all external services are mocked. Tests must pass offline.
4. **Bypass path tested:** Verify there's a test with quality_engine.enabled=false that confirms legacy sizing.
5. **Grade filter tested:** Verify there's a test where quality grade is below minimum that confirms the signal is filtered.
6. **Quality enrichment verified:** Verify the test checks that the signal reaching Risk Manager has quality_grade and quality_score populated.
7. **EFTS diagnostic documented:** Check the close-out report for the EFTS URL validation result.
8. **Test isolation:** Verify tests clean up after themselves (in-memory DB, no file system side effects).

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Order Manager position lifecycle unchanged
- [ ] TradeLogger handles quality-present and quality-absent trades
- [ ] Schema migration idempotent, no data loss
- [ ] Quality engine bypass path intact (SIMULATED or enabled=false)
- [ ] All pytest pass (full suite with `-n auto`)
- [ ] All Vitest pass
- [ ] API response shapes unchanged
- [ ] Frontend renders without console errors

## Sprint-Level Escalation Criteria (for @reviewer)
### Critical (Halt immediately)
1. E2E test reveals quality pipeline cannot be exercised without live external services — mocking gap requires architectural changes to init path
2. Quality pipeline bypass path broken

### Warning (Proceed with caution, document)
3. EFTS URL broken — document response, apply simple fix if possible, defer if not
4. ArgusSystem init is too complex to test without full start() — document the specific blocker

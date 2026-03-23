# Sprint 21.6, Session 1: ExecutionRecord Dataclass + DB Schema

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/db/schema.sql` — current DB schema, understand table patterns
   - `argus/db/manager.py` — migration pattern (try/except for ALTER TABLE)
   - `argus/core/events.py` lines 159–187 — SignalEvent and OrderApprovedEvent fields (entry_price, stop_price, etc.)
   - `argus/execution/order_manager.py` lines 57–108 — PendingManagedOrder and ManagedPosition dataclasses
   - `docs/amendments/roadmap-amendment-intelligence-architecture.md` lines 401–431 — ExecutionRecord spec (DEC-358 §5.1)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~3,010 tests, all passing
3. Verify you are on branch: `main`

## Objective
Create the ExecutionRecord data model and `execution_records` database table. This is the foundation for execution quality logging — a purely additive data model with no behavioral changes to any existing component.

## Requirements

1. **Create `argus/execution/execution_record.py`** with:

   a. `ExecutionRecord` dataclass (frozen=True) with these fields per DEC-358 §5.1:
      - `record_id: str` — ULID, generated at creation time
      - `order_id: str` — links to the order that was filled
      - `symbol: str`
      - `strategy_id: str`
      - `side: str` — "BUY" or "SELL"
      - `expected_fill_price: float` — price from SignalEvent.entry_price at signal time
      - `expected_slippage_bps: float` — the slippage assumed in backtest (default 1.0 bps, i.e., $0.01 on a $100 stock)
      - `actual_fill_price: float` — price from OrderFilledEvent.fill_price
      - `actual_slippage_bps: float` — computed: `abs(actual_fill_price - expected_fill_price) / expected_fill_price * 10000`
      - `time_of_day: str` — ISO time string from fill timestamp (HH:MM:SS)
      - `order_size_shares: int`
      - `avg_daily_volume: int | None` — from Universe Manager reference data if available, else None
      - `bid_ask_spread_bps: float | None` — from L1 data if available, else None (Standard plan = None)
      - `latency_ms: float | None` — signal-to-fill round-trip if measurable, else None
      - `slippage_vs_model: float` — `actual_slippage_bps - expected_slippage_bps` (positive = worse than model)
      - `created_at: str` — ISO-8601 datetime

   b. A factory function `create_execution_record(...)` that accepts the raw inputs (order_id, symbol, strategy_id, side, expected_fill_price, actual_fill_price, order_size_shares, signal_timestamp, fill_timestamp, avg_daily_volume, bid_ask_spread_bps) and computes the derived fields (actual_slippage_bps, slippage_vs_model, time_of_day, latency_ms, record_id, created_at). Use `expected_slippage_bps=1.0` as default (matches BacktestEngine's $0.01/share on ~$100 stocks).

   c. An async function `save_execution_record(db_manager: DatabaseManager, record: ExecutionRecord) -> None` that persists the record to the `execution_records` table via INSERT. Must be safe to call with `:memory:` databases (for testing).

   d. Import `generate_id` from `argus.models.trading` for ULID generation.

2. **Modify `argus/db/schema.sql`** — add at the end (before any comments about deferred tables):

   ```sql
   -- ---------------------------------------------------------------------------
   -- Execution Records Table
   -- ---------------------------------------------------------------------------
   -- Execution quality logging for slippage model calibration (DEC-358 §5.1)
   CREATE TABLE IF NOT EXISTS execution_records (
       record_id TEXT PRIMARY KEY,
       order_id TEXT NOT NULL,
       symbol TEXT NOT NULL,
       strategy_id TEXT NOT NULL,
       side TEXT NOT NULL,
       expected_fill_price REAL NOT NULL,
       expected_slippage_bps REAL NOT NULL,
       actual_fill_price REAL NOT NULL,
       actual_slippage_bps REAL NOT NULL,
       time_of_day TEXT NOT NULL,
       order_size_shares INTEGER NOT NULL,
       avg_daily_volume INTEGER,
       bid_ask_spread_bps REAL,
       latency_ms REAL,
       slippage_vs_model REAL NOT NULL,
       created_at TEXT NOT NULL DEFAULT (datetime('now'))
   );

   CREATE INDEX IF NOT EXISTS idx_execution_records_order ON execution_records(order_id);
   CREATE INDEX IF NOT EXISTS idx_execution_records_strategy ON execution_records(strategy_id);
   CREATE INDEX IF NOT EXISTS idx_execution_records_symbol ON execution_records(symbol);
   CREATE INDEX IF NOT EXISTS idx_execution_records_created ON execution_records(created_at);
   ```

3. **Modify `argus/db/manager.py`** — no migration block needed. The `CREATE TABLE IF NOT EXISTS` in `schema.sql` handles both fresh databases and existing ones. Just verify that `_apply_schema()` runs `executescript()` which processes the new table definition. No code change unless the existing migration pattern requires an explicit ALTER TABLE approach — check if the existing quality_grade migration was needed because the column was added to an EXISTING table (trades) rather than a new table. The `execution_records` table is entirely new, so `CREATE TABLE IF NOT EXISTS` suffices.

   **Only add a migration block if** the schema.sql approach fails on an existing database (it shouldn't, since this is a new table). Document this reasoning in a code comment.

## Constraints
- Do NOT modify: any file in `argus/strategies/`, `argus/backtest/`, `argus/core/events.py`, `argus/ui/`, `argus/api/`
- Do NOT modify: `argus/execution/order_manager.py` (that's Session 2)
- Do NOT add: API endpoints, frontend components, or slippage model logic
- Do NOT import: anything from `argus/execution/order_manager.py` (avoid circular imports)
- The `ExecutionRecord` dataclass must be importable independently of OrderManager

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/execution/test_execution_record.py`:
  1. `test_create_execution_record_computes_slippage` — verify actual_slippage_bps computation is correct (e.g., expected=100.0, actual=100.05 → 5.0 bps)
  2. `test_create_execution_record_computes_latency` — verify latency_ms computed from signal_timestamp and fill_timestamp
  3. `test_create_execution_record_nullable_fields` — verify avg_daily_volume=None, bid_ask_spread_bps=None work correctly
  4. `test_save_execution_record_round_trip` — save to :memory: DB, read back, verify all fields match
  5. `test_execution_records_table_exists` — verify table created in schema
- Minimum new test count: 5
- Test command: `python -m pytest tests/execution/test_execution_record.py -x -q`

## Definition of Done
- [ ] `argus/execution/execution_record.py` exists with ExecutionRecord dataclass, create function, save function
- [ ] `execution_records` table in `schema.sql` with correct columns and indexes
- [ ] All 5+ new tests passing
- [ ] All existing tests still pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing tables not modified | `grep -c "ALTER TABLE" argus/db/schema.sql` returns 0 |
| Schema applies cleanly on fresh DB | Run `test_save_execution_record_round_trip` (uses :memory:) |
| No imports of order_manager in execution_record.py | `grep "order_manager" argus/execution/execution_record.py` returns nothing |
| execution_record.py is independently importable | `python -c "from argus.execution.execution_record import ExecutionRecord"` succeeds |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-21.6/session-1-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-21.6/review-context.md`
2. The close-out report path: `docs/sprints/sprint-21.6/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/test_execution_record.py tests/db/ -x -q`
5. Files that should NOT have been modified: any file in `argus/strategies/`, `argus/backtest/`, `argus/core/events.py`, `argus/execution/order_manager.py`, `argus/ui/`, `argus/api/`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-21.6/session-1-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same session, update both the close-out and review report files per the Post-Review Fix Documentation protocol in the implementation prompt template.

## Session-Specific Review Focus (for @reviewer)
1. Verify `actual_slippage_bps` computation handles edge case of `expected_fill_price=0` (should not divide by zero)
2. Verify `save_execution_record` uses parameterized SQL (no string interpolation / SQL injection)
3. Verify `execution_records` table schema matches `ExecutionRecord` dataclass fields 1:1
4. Verify no circular import between `execution_record.py` and `order_manager.py`
5. Verify `CREATE TABLE IF NOT EXISTS` is used (not `CREATE TABLE`)

## Sprint-Level Regression Checklist
*(See `docs/sprints/sprint-21.6/review-context.md` for the full checklist)*

## Sprint-Level Escalation Criteria
*(See `docs/sprints/sprint-21.6/review-context.md` for the full criteria)*

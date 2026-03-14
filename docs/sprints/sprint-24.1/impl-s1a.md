# Sprint 24.1, Session 1a: Trades Quality Column Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` — verify SignalEvent has `quality_grade` and `quality_score` fields
   - `argus/db/schema.sql` — current trades table schema (lines 12–35)
   - `argus/models/trading.py` — Trade model (class at line 179)
   - `argus/execution/order_manager.py` — ManagedPosition dataclass (line 57), `_handle_entry_fill()` (line 468), `_close_position()` area (~line 1185)
   - `argus/analytics/trade_logger.py` — `log_trade()` (line 48) and `_row_to_trade()` (line 739)
2. Run the test baseline (full suite, first session of sprint):
   ```
   python -m pytest -x -q -n auto
   ```
   Expected: ~2,686 tests, all passing
3. Verify you are on branch `sprint-24.1` (create from main if it doesn't exist)

## Objective
Wire `quality_grade` and `quality_score` through the full trades persistence chain so completed trades store quality data in the database. The API routes and frontend already read these fields — this session completes the backend chain.

## Requirements

1. **In `argus/db/schema.sql`**: Add two columns to the `trades` table:
   ```sql
   quality_grade TEXT,          -- e.g., 'B+', 'A-', '' for legacy
   quality_score REAL,          -- 0-100, NULL for legacy trades
   ```
   Also add a migration helper. Since SQLite doesn't support `ADD COLUMN IF NOT EXISTS`, use a pattern like:
   - Add the columns in the CREATE TABLE definition (for fresh databases)
   - In `argus/db/manager.py` (or wherever schema initialization happens), add ALTER TABLE statements wrapped in try/except to handle existing databases:
     ```python
     # Migration: add quality columns to trades (Sprint 24.1)
     try:
         await self.execute("ALTER TABLE trades ADD COLUMN quality_grade TEXT")
     except Exception:
         pass  # Column already exists
     try:
         await self.execute("ALTER TABLE trades ADD COLUMN quality_score REAL")
     except Exception:
         pass  # Column already exists
     ```
   Find the appropriate location in `DatabaseManager.initialize()` for these migration statements.

2. **In `argus/models/trading.py`**: Add optional quality fields to the `Trade` model (after `notes` field, before `model_post_init`):
   ```python
   quality_grade: str = ""
   quality_score: float = 0.0
   ```

3. **In `argus/execution/order_manager.py`**:
   a. Add quality fields to `ManagedPosition` dataclass (in the "Optional fields with defaults" section):
      ```python
      quality_grade: str = ""     # From signal, set at entry fill
      quality_score: float = 0.0  # From signal, set at entry fill
      ```
   b. In `_handle_entry_fill()` (~line 500, where ManagedPosition is constructed): populate from the signal:
      ```python
      quality_grade=signal.quality_grade,
      quality_score=signal.quality_score,
      ```
   c. In the trade creation section of `_close_position()` (~line 1190, where `Trade(...)` is constructed): pass quality from ManagedPosition to Trade:
      ```python
      quality_grade=position.quality_grade,
      quality_score=position.quality_score,
      ```

4. **In `argus/analytics/trade_logger.py`**:
   a. In `log_trade()`: add `quality_grade` and `quality_score` to the INSERT statement's column list and VALUES placeholders. Add to the params tuple:
      ```python
      trade.quality_grade,
      trade.quality_score if trade.quality_score else None,
      ```
      (Use None for quality_score when 0.0 to distinguish "not scored" from "scored zero" — though 0.0 is effectively impossible with the scoring algorithm.)
   b. In `_row_to_trade()`: read quality fields from the row with fallback:
      ```python
      quality_grade=r.get("quality_grade", "") or "",
      quality_score=float(r["quality_score"]) if r.get("quality_score") is not None else 0.0,
      ```

## Constraints
- Do NOT modify: `argus/core/events.py`, `argus/strategies/*`, `argus/api/routes/trades.py` (already wired), `argus/core/risk_manager.py`
- Do NOT change: Order Manager position management logic (bracket orders, stop execution, T1/T2 fills). Only add quality data passthrough.
- Do NOT change: Trade model's `model_post_init()` logic (P&L, R-multiple, outcome calculations)
- Do NOT change: Any existing Trade model field names or types
- Preserve backward compatibility: existing trades with NULL quality columns must load without error

## Test Targets
After implementation:
- Existing tests: all must still pass (especially `tests/execution/test_order_manager*.py`, `tests/analytics/test_trade_logger.py`, `tests/db/test_manager.py`)
- New tests to write:
  1. `ManagedPosition` with quality fields populated — verify dataclass works
  2. `ManagedPosition` with default quality fields — verify defaults
  3. `Trade` model with quality fields — verify construction and serialization
  4. `Trade` model without quality fields — verify defaults/backward compat
  5. `TradeLogger.log_trade()` with quality data — verify INSERT succeeds and round-trips
  6. `TradeLogger.log_trade()` without quality data — verify INSERT succeeds with defaults
  7. `TradeLogger._row_to_trade()` with NULL quality columns — verify no crash, defaults used
  8. Schema migration on existing DB — verify ALTER TABLE succeeds or is no-op on repeat
- Minimum new test count: 8
- Test command (scoped): `python -m pytest tests/execution/test_order_manager*.py tests/analytics/test_trade_logger.py tests/db/ -x -q`

## Definition of Done
- [ ] trades table has quality_grade and quality_score columns in schema.sql
- [ ] Migration adds columns to existing databases safely
- [ ] ManagedPosition stores quality data from signal
- [ ] Trade model accepts quality fields
- [ ] TradeLogger persists and reads quality data
- [ ] Existing trades with NULL quality load without error
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Order Manager position lifecycle unchanged | `python -m pytest tests/execution/test_order_manager*.py -x -q` — all pass, no modifications to these test files |
| TradeLogger round-trip with quality data | New test: insert Trade with quality_grade="B+", quality_score=72.5, read back, verify fields match |
| TradeLogger round-trip without quality data | New test: insert Trade with defaults, read back, verify quality_grade="" and quality_score=0.0 |
| Schema migration idempotent | New test: run migration twice, no error |
| NULL quality in existing rows | New test: insert row with raw SQL (no quality columns), read via _row_to_trade, verify defaults |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `. See the close-out skill for the full schema.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-1a-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-1a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session):
   ```
   python -m pytest tests/execution/test_order_manager*.py tests/analytics/test_trade_logger.py tests/db/ -x -q
   ```
5. Files that should NOT have been modified:
   - `argus/core/events.py`
   - `argus/strategies/*`
   - `argus/api/routes/trades.py`
   - `argus/core/risk_manager.py`
   - `argus/intelligence/*`

The @reviewer will produce its review report (including a structured JSON
verdict fenced with ` ```json:structured-verdict `) and write it to:
`docs/sprints/sprint-24.1/session-1a-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **Schema migration safety:** Verify ALTER TABLE ADD COLUMN statements are wrapped in try/except and are idempotent.
2. **ManagedPosition backward compatibility:** Verify new fields have defaults so existing code still works.
3. **Trade model backward compatibility:** Verify new fields have defaults. `model_post_init()` must not reference quality fields.
4. **TradeLogger NULL handling:** Verify `_row_to_trade()` handles NULL values from pre-sprint rows.
5. **TradeLogger INSERT completeness:** Verify INSERT column count matches VALUES placeholder count.
6. **Order Manager passthrough only:** Verify quality fields are only stored and passed through — no logic branches.
7. **Signal field access:** Verify `_handle_entry_fill()` reads `signal.quality_grade` and `signal.quality_score`.
8. **Test coverage:** Verify tests cover: quality-present round-trip, quality-absent round-trip, NULL from legacy rows, schema migration idempotency.

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Order Manager position lifecycle unchanged (entry fills, stops, T1/T2, closing)
- [ ] TradeLogger handles quality-present and quality-absent trades
- [ ] Schema migration idempotent, no data loss
- [ ] Quality engine bypass path intact (SIMULATED or enabled=false)
- [ ] All pytest pass (full suite with `-n auto`)
- [ ] All Vitest pass
- [ ] API response shapes unchanged
- [ ] Frontend renders without console errors

## Sprint-Level Escalation Criteria (for @reviewer)
### Critical (Halt immediately)
1. Order Manager behavioral change — position lifecycle tests fail
2. Schema migration data loss
3. Quality pipeline bypass path broken

### Warning (Proceed with caution, document)
4. TypeScript errors increase (only relevant for frontend sessions)

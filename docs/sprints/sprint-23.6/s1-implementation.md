# Sprint 23.6, Session 1: Storage Schema & Query Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/storage.py`
   - `argus/intelligence/models.py`
   - `argus/api/routes/intelligence.py`
   - `tests/intelligence/test_storage.py`
   - `tests/api/test_intelligence_routes.py`
2. Run the test suite: `python -m pytest tests/intelligence/ tests/api/test_intelligence_routes.py -x -q`
   Expected: all passing
3. Verify you are on the correct branch: `sprint-23.6`

## Objective
Fix four CatalystStorage and intelligence API defects identified in the Tier 3 review: replace the 10K-row total count fetch with `SELECT COUNT(*)` (C2), persist and round-trip the `fetched_at` timestamp (S1), add transactional batch insert (S2), and push the `since` datetime filter to SQL (M3).

## Requirements

1. **In `argus/intelligence/storage.py`**, add a `get_total_count()` method:
   ```python
   async def get_total_count(self) -> int:
   ```
   Execute `SELECT COUNT(*) FROM catalyst_events` and return the integer result.

2. **In `argus/intelligence/storage.py`**, handle the `fetched_at` column:
   - In `initialize()`, after creating the `catalyst_events` table, execute:
     ```sql
     ALTER TABLE catalyst_events ADD COLUMN fetched_at TEXT
     ```
     Wrap in try/except (column may already exist on fresh DBs — `CREATE TABLE` should include `fetched_at TEXT` in the schema, and `ALTER TABLE` is for upgrading existing DBs where the column is missing).
   - Add `fetched_at TEXT` to the `_CATALYST_EVENTS_TABLE_SQL` string (after `created_at`).
   - In `store_catalyst()`, include `catalyst.fetched_at.isoformat()` in the INSERT values.
   - In `_row_to_catalyst()`, read `fetched_at` from the row. If the column is NULL (old data), fall back to `created_at`. Replace the comment `# Use created_at as fetched_at`.

3. **In `argus/intelligence/storage.py`**, add a `store_catalysts_batch()` method:
   ```python
   async def store_catalysts_batch(self, catalysts: list[ClassifiedCatalyst]) -> list[str]:
   ```
   Insert all catalysts in a single transaction using `executemany` or a loop within one `BEGIN`/`COMMIT` pair. Return the list of generated ULID IDs. Single `commit()` at the end, not per-row.

4. **In `argus/intelligence/storage.py`**, add a `since` parameter to `get_catalysts_by_symbol()`:
   ```python
   async def get_catalysts_by_symbol(
       self, symbol: str, limit: int = 50, since: datetime | None = None
   ) -> list[ClassifiedCatalyst]:
   ```
   When `since` is provided, add `AND published_at >= ?` to the SQL WHERE clause.

5. **In `argus/api/routes/intelligence.py`**, update `get_recent_catalysts()`:
   - Replace the 10K-row fetch with a call to `state.catalyst_storage.get_total_count()`.
   - Remove the `all_catalysts` variable and the `len(all_catalysts)` pattern.

6. **In `argus/api/routes/intelligence.py`**, update `get_catalysts_by_symbol()`:
   - Pass the `since` parameter to `storage.get_catalysts_by_symbol(symbol, limit=limit, since=since_dt)`.
   - Remove the Python-side list comprehension filter that currently applies `since` post-fetch.
   - Keep the `since` parameter validation (parse, handle ValueError).

## Constraints
- Do NOT modify any file outside `argus/intelligence/storage.py` and `argus/api/routes/intelligence.py`
- Do NOT change the `catalyst_classifications_cache` or `intelligence_briefs` table schemas
- Do NOT change the `ClassifiedCatalyst` dataclass (the `fetched_at` field already exists)
- Do NOT remove backward compatibility — existing DBs without `fetched_at` column must still work

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/intelligence/test_storage.py`:
  1. `test_get_total_count_empty` — returns 0 on fresh DB
  2. `test_get_total_count_after_inserts` — returns correct count after storing N catalysts
  3. `test_fetched_at_round_trip` — store a catalyst, read it back, verify `fetched_at` matches original
  4. `test_fetched_at_null_fallback` — simulate old data with NULL fetched_at, verify falls back to created_at
  5. `test_store_catalysts_batch_success` — batch insert 5 catalysts, verify all stored with correct IDs
  6. `test_store_catalysts_batch_single_transaction` — verify single commit (e.g., batch of 3 all appear or none)
  7. `test_store_catalysts_batch_empty` — empty list returns empty list, no errors
  8. `test_get_catalysts_by_symbol_since` — store 3 catalysts with different published_at, query with since, verify correct filter
  9. `test_get_catalysts_by_symbol_since_none` — since=None returns all (unchanged behavior)
- New tests in `tests/api/test_intelligence_routes.py`:
  10. `test_recent_catalysts_total_count` — verify response `total` field uses count query
  11. `test_catalysts_by_symbol_since_parameter` — verify since parameter filters correctly via API
  12. `test_schema_migration_alter_table` — create DB without fetched_at column, re-initialize, verify column added
- Minimum new test count: 12
- Test command: `python -m pytest tests/intelligence/test_storage.py tests/api/test_intelligence_routes.py -x -q`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 12+ new tests written and passing
- [ ] `fetched_at` column added to schema (fresh and migration paths)
- [ ] `get_total_count()` returns correct count via SQL COUNT(*)
- [ ] `store_catalysts_batch()` uses single transaction
- [ ] `since` filter applied in SQL, not Python
- [ ] No ruff lint errors: `ruff check argus/intelligence/storage.py argus/api/routes/intelligence.py`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing storage tests pass | `python -m pytest tests/intelligence/test_storage.py -x -q` |
| Existing API tests pass | `python -m pytest tests/api/test_intelligence_routes.py -x -q` |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/core/ argus/execution/ argus/ai/` returns empty |
| Full test suite still passes | `python -m pytest tests/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md` — Escalation Criteria section.

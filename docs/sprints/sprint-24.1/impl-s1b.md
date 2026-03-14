# Sprint 24.1, Session 1b: Trivial Backend Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/main.py` — line ~559 (CatalystStorage init, logger.debug)
   - `argus/intelligence/quality_engine.py` — class definition, find `_db` and `_config` attributes
   - `argus/api/routes/quality.py` — lines 87, 155, 220, 242, 272 (private attribute access)
   - `scripts/seed_quality_data.py` — current argparse setup
2. Run the scoped test baseline:
   ```
   python -m pytest tests/intelligence/test_quality_engine.py tests/api/test_quality.py -x -q
   ```
   Expected: all passing (full suite confirmed by S1a close-out)
3. Verify you are on branch `sprint-24.1`

## Objective
Execute 5 small independent backend fixes: change a log level, add public property accessors, add PROVISIONAL config comments, and add a production guard to the seed script.

## Requirements

1. **CatalystStorage init log level (Item 1):**
   In `argus/main.py`, find the CatalystStorage initialization block (~line 559):
   ```python
   logger.debug("CatalystStorage not available for quality pipeline")
   ```
   Change to:
   ```python
   logger.warning("CatalystStorage not available for quality pipeline")
   ```

2. **SetupQualityEngine public accessors (Item 3):**
   a. In `argus/intelligence/quality_engine.py`, add two `@property` methods to `SetupQualityEngine`:
      ```python
      @property
      def db(self):
          """Public accessor for database manager."""
          return self._db

      @property
      def config(self):
          """Public accessor for quality engine config."""
          return self._config
      ```
   b. In `argus/api/routes/quality.py`, replace all private attribute access:
      - Line 87: `state.quality_engine._db` → `state.quality_engine.db`
      - Line 155: `state.quality_engine._db` → `state.quality_engine.db`
      - Line 220: `state.quality_engine._db` → `state.quality_engine.db`
      - Line 242: `state.quality_engine._config` → `state.quality_engine.config`
      - Line 272: `state.quality_engine._db` → `state.quality_engine.db`
      - Remove associated `# type: ignore[union-attr]` comments on these lines

3. **PROVISIONAL comment (Item 12):**
   In `config/system.yaml`, add a comment above or within the `quality_engine:` section:
   ```yaml
   # NOTE: Thresholds are PROVISIONAL — recalibrate after Sprint 28
   # when historical match has real data.
   ```
   Add the same comment in `config/system_live.yaml`.

4. **Seed script production guard (Item 13):**
   In `scripts/seed_quality_data.py`, modify the argparse setup to add a required flag:
   ```python
   parser.add_argument(
       "--i-know-this-is-dev",
       action="store_true",
       help="Required safety flag to confirm this is a dev environment",
   )
   ```
   After parsing args, before any database operations:
   ```python
   if not args.i_know_this_is_dev and not args.cleanup:
       print("ERROR: This script inserts synthetic data and is for development only.")
       print("Pass --i-know-this-is-dev to confirm, or use --cleanup to remove seed data.")
       sys.exit(1)
   ```
   Note: `--cleanup` should still work without the dev flag (it removes data, doesn't add it).

## Constraints
- Do NOT modify: `argus/core/events.py`, `argus/strategies/*`, `argus/intelligence/__init__.py`, `argus/core/risk_manager.py`
- Do NOT change: Quality engine scoring logic, quality API response shapes, config schema structure
- Item 2 changes are property accessors only — do not change the internal attribute names `_db` and `_config`

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `SetupQualityEngine.db` property returns the database manager instance
  2. `SetupQualityEngine.config` property returns the config instance
  3. Seed script without `--i-know-this-is-dev` exits with non-zero code
  4. Seed script with `--i-know-this-is-dev` does not exit early (can mock DB operations)
- Minimum new test count: 4
- Test command (scoped): `python -m pytest tests/intelligence/test_quality_engine.py tests/api/test_quality.py -x -q`

## Definition of Done
- [ ] CatalystStorage init uses logger.warning
- [ ] SetupQualityEngine has public db and config properties
- [ ] quality.py routes use public accessors, no private attribute access
- [ ] Both system YAMLs have PROVISIONAL comment
- [ ] Seed script requires --i-know-this-is-dev flag
- [ ] All existing tests pass
- [ ] 4+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Quality API routes return same data | `python -m pytest tests/api/test_quality.py -x -q` — all pass |
| Quality engine init unchanged | `python -m pytest tests/intelligence/test_quality_engine.py -x -q` — all pass |
| Seed script with flag works | `python scripts/seed_quality_data.py --i-know-this-is-dev --db /tmp/test.db` — runs (or mock test) |
| Seed script without flag rejects | `python scripts/seed_quality_data.py --db /tmp/test.db` — exits 1 |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-1b-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-1b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session):
   ```
   python -m pytest tests/intelligence/test_quality_engine.py tests/api/test_quality.py -x -q
   ```
5. Files that should NOT have been modified:
   - `argus/core/events.py`
   - `argus/strategies/*`
   - `argus/intelligence/__init__.py`
   - `argus/core/risk_manager.py`
   - `argus/execution/order_manager.py`
   - `argus/analytics/trade_logger.py`
   - `argus/models/trading.py`
   - `argus/db/schema.sql`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-24.1/session-1b-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **Log level change:** Verify `main.py` line ~559 uses `logger.warning`, not `logger.debug`. Only that one line changed.
2. **Property accessor correctness:** Verify `@property def db` returns `self._db` and `@property def config` returns `self._config`. No logic, no side effects.
3. **Routes updated completely:** Verify ALL 5 occurrences of `._db` and `._config` in `quality.py` are replaced. No remaining private attribute access. No `# type: ignore[union-attr]` comments on these lines.
4. **PROVISIONAL comments:** Verify comment text matches `config/quality_engine.yaml` and is added to both `system.yaml` and `system_live.yaml`.
5. **Seed script guard logic:** Verify `--cleanup` still works without the dev flag. Verify `sys.exit(1)` on missing flag.
6. **No collateral damage:** These are 5 independent trivial fixes. Verify no other changes leaked in.

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
1. Order Manager behavioral change
2. Schema migration data loss
3. Quality pipeline bypass path broken

### Warning (Proceed with caution, document)
4. Quality API routes return different data than before

# Sprint 31.75, Session 3b: Sweep Tooling Scripts

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `scripts/run_experiment.py` (updated in S3a with --persist-db, --rebuild)
   - `config/universe_filters/bull_flag.yaml`
   - `argus/data/historical_query_config.py` (updated in S3a with persist_path)
   - `data/sweep_logs/` (check what operational artifacts exist)
2. Run the scoped test baseline (DEC-328):
   `python -m pytest tests/data/ tests/intelligence/experiments/ -x -q`
   Expected: all passing (full suite confirmed by S3a close-out)
3. Verify you are on the `main` branch
4. Verify S3a close-out was committed

## Objective
Create the operational tooling needed for reliable overnight full-universe
sweeps: a symbol pre-resolution script (separates the slow DuckDB step from
the fast backtest step), a robust batch sweep script with error isolation, and
an alternative universe filter for bull flag trend-following candidates.

## Requirements

### 1. Create `scripts/resolve_sweep_symbols.py`

Create a standalone CLI script that:

a. Accepts arguments:
   - `--pattern` (required): pattern name
   - `--all-patterns`: resolve all 10 patterns in one invocation
   - `--cache-dir` (default: `data/databento_cache`): Parquet cache path
   - `--date-range` (required): `start,end` ISO dates
   - `--output-dir` (default: `data/sweep_logs`): where to write symbol files
   - `--persist-db` (default: `data/historical_query.duckdb`): persistent DB path
   - `--min-bars` (default: `100`): minimum bar count for coverage validation

b. For each pattern:
   1. Load `config/universe_filters/{pattern}.yaml`
   2. Instantiate HistoricalQueryService with persistent DB
   3. Apply static filters (min_price, max_price, min_avg_volume) via
      the same `_apply_universe_filter()` logic from run_experiment.py
      (import or duplicate — prefer import if clean)
   4. Validate coverage for the date range via `validate_symbol_coverage()`
   5. Write the resolved symbol list to `{output_dir}/symbols_{pattern}.txt`
      (one symbol per line, sorted alphabetically)
   6. Print a summary line:
      ```
      {pattern}: {cache_total} in cache → {after_filter} after filter → {after_coverage} after coverage → symbols_{pattern}.txt
      ```

c. When `--all-patterns` is used:
   - Discover all `.yaml` files in `config/universe_filters/`
   - Process each in alphabetical order
   - Print a grand total summary at the end
   - Reuse the same HistoricalQueryService instance (one DuckDB open)

d. Add `#!/usr/bin/env python3` and make the file executable.

e. Import `_apply_universe_filter` and `_DYNAMIC_FILTER_FIELDS` from
   `scripts/run_experiment.py` if possible. If circular import issues arise,
   extract the shared logic into a helper module at
   `argus/intelligence/experiments/universe_utils.py` (keep it minimal — just
   the filter application SQL and dynamic field constants).

### 2. Create `scripts/run_sweep_batch.sh`

Create a bash script that orchestrates overnight sweep runs:

a. Configuration section at the top:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail

   # --- Configuration ---
   CACHE_DIR="${CACHE_DIR:-data/databento_cache}"
   DATE_RANGE="${DATE_RANGE:-2025-01-01,2025-12-31}"
   WORKERS="${WORKERS:-2}"
   LOG_DIR="data/sweep_logs"
   PERSIST_DB="data/historical_query.duckdb"
   PATTERNS=(
       micro_pullback
       dip_and_rip
       hod_break
       abcd
       narrow_range_breakout
       vwap_bounce
       flat_top_breakout
       bull_flag
       gap_and_go
       premarket_high_break
   )
   ```

b. Pre-flight checks:
   - Verify `$CACHE_DIR` exists
   - Verify `python3` is available
   - Create `$LOG_DIR` if it doesn't exist

c. Phase 1 — Symbol resolution:
   ```bash
   echo "=== Phase 1: Resolving symbols ==="
   python3 scripts/resolve_sweep_symbols.py \
       --all-patterns \
       --cache-dir "$CACHE_DIR" \
       --date-range "$DATE_RANGE" \
       --persist-db "$PERSIST_DB" \
       --output-dir "$LOG_DIR"
   ```

d. Phase 2 — Validate symbol files exist:
   ```bash
   for pattern in "${PATTERNS[@]}"; do
       symfile="$LOG_DIR/symbols_${pattern}.txt"
       if [[ ! -f "$symfile" ]]; then
           echo "WARNING: No symbol file for $pattern — skipping"
           continue
       fi
       count=$(wc -l < "$symfile")
       echo "  $pattern: $count symbols"
   done
   ```

e. Phase 3 — Run sweeps with per-pattern error isolation:
   ```bash
   for pattern in "${PATTERNS[@]}"; do
       symfile="$LOG_DIR/symbols_${pattern}.txt"
       [[ ! -f "$symfile" ]] && continue

       logfile="$LOG_DIR/sweep_${pattern}_$(date +%Y%m%d).log"
       progress_file="$LOG_DIR/${pattern}_progress.json"

       echo "=== Starting: $pattern ==="
       python3 scripts/run_experiment.py \
           --pattern "$pattern" \
           --cache-dir "$CACHE_DIR" \
           --symbols "@${symfile}" \
           --date-range "$DATE_RANGE" \
           --workers "$WORKERS" \
           > "$logfile" 2>&1 || {
           echo "FAILED: $pattern (see $logfile)"
           echo "{\"status\": \"failed\", \"pattern\": \"$pattern\"}" > "$progress_file"
           continue
       }
       echo "COMPLETED: $pattern"
       echo "{\"status\": \"completed\", \"pattern\": \"$pattern\"}" > "$progress_file"
   done
   ```
   Key design choices:
   - Output redirection ONLY (no `tee` — prevents pipe-death hangs)
   - `|| continue` for error isolation (one pattern's crash doesn't kill batch)
   - Progress sentinel files per pattern

f. Phase 4 — Completion sentinel:
   ```bash
   echo "{\"completed\": true, \"timestamp\": \"$(date -Iseconds)\"}" \
       > "$LOG_DIR/batch_complete.json"
   echo "=== Batch complete ==="
   ```

g. Support optional `--patterns` argument to run a subset:
   ```bash
   if [[ $# -gt 0 ]]; then
       PATTERNS=("$@")
   fi
   ```

h. Make the file executable: `chmod +x scripts/run_sweep_batch.sh`

### 3. Create `config/universe_filters/bull_flag_trend.yaml`

Create a trend-following universe filter for bull flag testing (alternative to
the momentum-focused `bull_flag.yaml`):

```yaml
# Bull Flag — trend-following universe (lower beta, higher market cap)
# Hypothesis: bull flags may work better on steadier trend-following names
# vs the high-momentum universe where they were confirmed dead.
min_price: 20.0
max_price: 300.0
min_avg_volume: 300000
```

This gives us two universes for bull flag comparison in S4:
- `bull_flag.yaml`: momentum ($10–500, 500K vol) — already confirmed dead
- `bull_flag_trend.yaml`: trend-following ($20–300, 300K vol) — to be tested

### 4. Move sweep analysis script to scripts/

If `data/sweep_logs/analyze_sweeps.py` exists from the sweep impromptu:
- Copy it to `scripts/analyze_sweeps.py`
- Add `#!/usr/bin/env python3`
- Add a brief docstring
- Make executable
- Do NOT refactor or polish — just relocate for discoverability

If the file doesn't exist, skip this step.

## Constraints
- Do NOT modify: `argus/intelligence/experiments/runner.py`
- Do NOT modify: `argus/intelligence/experiments/store.py`
- Do NOT modify: `argus/data/historical_query_service.py` (already updated in S3a)
- Do NOT modify: any pattern files
- Do NOT modify: any frontend files
- Do NOT modify: existing `config/universe_filters/bull_flag.yaml` (the
  momentum filter stays as-is)
- `run_sweep_batch.sh` must work on macOS (zsh-compatible bash)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:

  1. `test_resolve_sweep_symbols_parse_args` — verify CLI arg parsing for
     `resolve_sweep_symbols.py`.
  2. `test_resolve_sweep_symbols_single_pattern` — mock HistoricalQueryService,
     verify output file is written with correct symbols.
  3. `test_resolve_sweep_symbols_all_patterns` — verify `--all-patterns`
     iterates all filter configs.
  4. `test_bull_flag_trend_yaml_valid` — load `config/universe_filters/bull_flag_trend.yaml`,
     verify it parses into UniverseFilterConfig.
  5. `test_run_sweep_batch_exists_and_executable` — verify script exists at
     `scripts/run_sweep_batch.sh` and has executable bit set.

- Minimum new test count: 4
- Test command: `python -m pytest tests/intelligence/experiments/ tests/data/ -x -q`

## Definition of Done
- [ ] scripts/resolve_sweep_symbols.py created and working
- [ ] --all-patterns flag resolves all 10 patterns in one invocation
- [ ] Symbol files written to data/sweep_logs/symbols_{pattern}.txt
- [ ] scripts/run_sweep_batch.sh created with error isolation per pattern
- [ ] Output redirection only (no tee) in batch script
- [ ] Progress sentinel files written per pattern
- [ ] Completion sentinel written at end
- [ ] config/universe_filters/bull_flag_trend.yaml created
- [ ] analyze_sweeps.py relocated (if exists)
- [ ] All existing tests pass
- [ ] 4+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| run_experiment.py still works | `python scripts/run_experiment.py --pattern bull_flag --dry-run` exits 0 |
| All 10 filter YAMLs valid | Load each in a test via UniverseFilterConfig |
| No changes to runner or store | `git diff argus/intelligence/experiments/` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.75/session-3b-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.75/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.75/session-3b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (FINAL SESSION — full suite):
   `python -m pytest tests/ -x -q -n auto`
5. Files that should NOT have been modified: `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/store.py`, `argus/data/historical_query_service.py`, any pattern files, any `ui/` files, `config/universe_filters/bull_flag.yaml`

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.75/session-3b-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the standard
protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `resolve_sweep_symbols.py` reuses a single HistoricalQueryService
   instance in `--all-patterns` mode (not creating/destroying per pattern).
2. Verify `run_sweep_batch.sh` uses `> logfile 2>&1` (not `| tee`) for output.
3. Verify the batch script uses `|| continue` (not `|| exit`) for error isolation.
4. Verify `bull_flag_trend.yaml` has DIFFERENT criteria from `bull_flag.yaml`
   (otherwise the comparison in S4 is meaningless).
5. Verify no code was added that imports from `ui/` or modifies frontend files.
6. Verify `run_sweep_batch.sh` is compatible with macOS default bash (no bashisms
   that require bash 4+ — macOS ships with bash 3.2).

## Sprint-Level Regression Checklist (for @reviewer)
(See review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(See review-context.md)

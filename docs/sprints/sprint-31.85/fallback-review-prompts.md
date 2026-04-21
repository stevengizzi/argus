# Sprint 31.85 — Fallback Tier 2 Review Prompts

> Use these ONLY if the @reviewer subagent invocation fails.
> Primary path: @reviewer is invoked at the end of each implementation session.

---

## Tier 2 Review: Sprint 31.85, Session 1

### Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict.

**Write the review report to:**
`docs/sprints/sprint-31.85/session-1-review.md`

Create the file, write the full report, and commit it. This is the ONE permitted write.

### Review Context
Read: `docs/sprints/sprint-31.85/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-31.85/session-1-closeout.md`

If this file does not exist: flag as CONCERNS immediately (close-out is required per DEC-330).

### Review Scope
- Diff: `git diff HEAD~1`
- Test command (final and only session of sprint — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Expected test count: ≥ 4,932 (baseline 4,919 + at least 13 new).
- Files that should NOT have been modified:
  - `argus/data/historical_query_service.py`
  - `argus/data/historical_query_config.py`
  - `config/historical_query.yaml`
  - Anything under `argus/backtest/`
  - Anything under `data/databento_cache/`
  - `scripts/resolve_symbols_fast.py`, `scripts/populate_historical_cache.py`, `scripts/run_experiment.py`

### Session-Specific Review Focus

1. **Row-count validation non-bypassable.** No `--skip-validation` flag. No `try/except` that swallows row-count mismatches silently. Mismatch produces exit code 1 and prevents output write.
2. **Original cache byte-unmodified.** No writes, renames, unlinks, or any mutation under `args.source_dir`. The `test_original_cache_is_unmodified` test uses `os.stat` comparisons (size + mtime), not just existence checks.
3. **`symbol` column correctness and source.** Column embedded in every consolidated file. Values equal the expected symbol for every row. Value comes from worker's known-symbol context (directory name), NOT parsing Parquet content or filename regex. Tested per-symbol, not just one sample.
4. **Atomic write.** Uses `.tmp` + `os.rename` pattern. Validation runs before the rename. Interruption simulation test exists. On validation failure, `.tmp` is deleted (no orphan files accumulate on retry).
5. **DuckDB benchmark references consolidated cache.** `--verify` SQL targets `{dest_dir}`, not `{source_dir}`. Real DuckDB connection. `time.perf_counter` timing.
6. **HistoricalQueryService untouched.** `git diff HEAD~1 -- argus/data/historical_query_service.py argus/data/historical_query_config.py config/historical_query.yaml` produces no output.
7. **Documentation accuracy.** `docs/operations/parquet-cache-layout.md` correctly states BacktestEngine → original cache, HistoricalQueryService → consolidated cache. No ambiguity about which script is run when. Operator's repoint steps reference `config/historical_query.yaml` correctly.
8. **Exit code.** Any row-count failure → exit 1. Any disk-space preflight failure → exit 1. No silent exit-0 on corruption.
9. **Disk-space preflight default is 60 GB.** `--force-no-disk-check` is test-only and not advertised in `docs/operations/parquet-cache-layout.md`.
10. **Resume validation.** Default `--resume` re-reads existing consolidated files and validates row counts, not just checks existence.

### Sprint-Level Escalation Criteria

See `docs/sprints/sprint-31.85/review-context.md` under "Sprint-Level Escalation Criteria". Summary:

- Any mutation of `data/databento_cache/` → ESCALATE.
- Any bypass of row-count validation → ESCALATE.
- Modifications to `HistoricalQueryService`, its config, or `historical_query.yaml` → ESCALATE.
- `symbol` column computed from filename regex inside the write path → ESCALATE (re-introduces the exact fragility we are eliminating).
- Per-symbol worker memory exceeds ~2 GB on large symbols → ESCALATE (flag for streaming rewrite).
- Any existing test weakened or skipped to make the suite pass → ESCALATE.

### Additional Context

This script will be run manually by the operator (Steven) once, then occasionally after `populate_historical_cache.py --update` adds new months. It is never invoked from ARGUS runtime code paths. All verification is via the script's own `--verify` mode or via starting ARGUS with the consolidated cache path in `historical_query.yaml`.

This sprint does NOT modify `historical_query.yaml` — that's an operator action post-consolidation. If the close-out claims it was modified, flag as CONCERNS.

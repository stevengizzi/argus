# Sprint 31.5 — Regression Checklist

## Critical Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Sequential execution produces identical results | Test: `run_sweep(workers=1)` and compare output records against current (pre-sprint) sequential behavior. Fingerprints, statuses, and backtest_result dicts must match. |
| 2 | ExperimentStore writes are main-process only | Code review: no `ExperimentStore` import or `save_experiment()` call in any worker function. Workers return dicts, not store objects. |
| 3 | Fingerprint dedup still works | Test: run sweep twice with same params; second run should skip all grid points (SKIPPED status). Verify dedup happens before worker dispatch. |
| 4 | CLI unchanged when no new flags used | Test: `run_experiment.py --pattern bull_flag --dry-run` produces same output as before sprint. No new required arguments. |
| 5 | `--dry-run` does not spawn workers | Test: `run_experiment.py --pattern bull_flag --dry-run --workers 8` completes instantly, no process pool created. |
| 6 | `ExperimentConfig(extra="forbid")` still works | Test: load `config/experiments.yaml` with new `max_workers` field into `ExperimentConfig`. Verify no `ValidationError`. Verify adding an unknown field raises `ValidationError`. |
| 7 | New `max_workers` config field matches Pydantic model | Test: YAML key `max_workers` → `ExperimentConfig.max_workers`. Verify value roundtrips correctly. |
| 8 | DEF-146 filtering produces same symbols as CLI filtering | Test: compare symbol lists from runner's internal filtering vs CLI's `_apply_universe_filter()` + `_validate_coverage()` for the same inputs. Must be identical. |
| 9 | All 4,823 pytest pass | `python -m pytest -x -q --tb=short -n auto` |
| 10 | All 846 Vitest pass | `cd ui && npx vitest run` |
| 11 | Existing experiment sweep tests unchanged | `python -m pytest tests/intelligence/experiments/ -x -q` |
| 12 | `run_experiment.py` existing flags still work | Test: `--pattern`, `--cache-dir`, `--params`, `--dry-run`, `--date-range`, `--symbols`, `--universe-filter` all function as before. |

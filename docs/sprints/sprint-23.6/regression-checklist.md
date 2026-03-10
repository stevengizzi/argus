# Sprint 23.6: Regression Checklist

Run after each session. All checks must pass before proceeding.

## Core System Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | All pytest tests pass | `python -m pytest tests/ -x -q` |
| 2 | All Vitest tests pass | `cd argus/ui && npx vitest run` |
| 3 | No ruff lint errors in modified files | `ruff check argus/ scripts/` |
| 4 | Strategy files untouched | `git diff HEAD -- argus/strategies/` returns empty |
| 5 | Risk Manager untouched | `git diff HEAD -- argus/core/risk_manager.py` returns empty |
| 6 | Orchestrator untouched | `git diff HEAD -- argus/core/orchestrator.py` returns empty |
| 7 | Execution layer untouched | `git diff HEAD -- argus/execution/` returns empty |
| 8 | Analytics untouched | `git diff HEAD -- argus/analytics/` returns empty |
| 9 | Backtesting untouched | `git diff HEAD -- argus/backtest/` returns empty |
| 10 | AI layer untouched | `git diff HEAD -- argus/ai/` returns empty |
| 11 | Frontend untouched | `git diff HEAD -- argus/ui/` returns empty |

## Config Integrity

| # | Check | How to Verify |
|---|-------|---------------|
| 12 | SystemConfig loads existing system.yaml | `python -c "from argus.core.config import load_config; c = load_config('config/system.yaml'); print(c.catalyst.enabled)"` prints `False` |
| 13 | SystemConfig loads system_live.yaml | Same as above with `system_live.yaml` (if it exists and has catalyst section) |
| 14 | New config fields match Pydantic model | Test verifies `catalyst` YAML keys are recognized by `CatalystConfig.model_fields` |
| 15 | CatalystConfig default matches YAML default | `catalyst.enabled` is `False`, `catalyst.dedup_window_minutes` is `30` |

## Pipeline Behavior

| # | Check | How to Verify |
|---|-------|---------------|
| 16 | Pipeline disabled by default | With `catalyst.enabled: false`, AppState.catalyst_storage is None |
| 17 | Endpoints return 503 when disabled | `GET /api/v1/catalysts/recent` returns 503 when catalyst_storage is None |
| 18 | CatalystEvent defaults are ET | `from argus.core.events import CatalystEvent; e = CatalystEvent(); assert e.published_at.tzinfo.key == "America/New_York"` |

## Storage Integrity

| # | Check | How to Verify |
|---|-------|---------------|
| 19 | Existing catalyst.db compatible | Test creates DB with old schema, then runs initialize() — column added via ALTER TABLE |
| 20 | Fresh DB has fetched_at column | Test creates fresh DB, inserts and reads back fetched_at successfully |
| 21 | Batch store is transactional | Test inserts batch with one invalid item — either all succeed or none do |

## Cache Integrity (after S4a)

| # | Check | How to Verify |
|---|-------|---------------|
| 22 | No cache file → full fetch | Test runs warm-up with no cache file, all symbols fetched |
| 23 | Corrupt cache → full fetch + WARNING | Test runs warm-up with malformed JSON file, falls back gracefully |
| 24 | Cache file permissions | Cache written with standard permissions, readable on next startup |

## Runner Integrity (after S5)

| # | Check | How to Verify |
|---|-------|---------------|
| 25 | All 188 runner tests pass | `python -m pytest tests/sprint_runner/ -x -q` |
| 26 | Runner main.py still executable | `python scripts/sprint-runner.py --help` exits 0 |
| 27 | CLI extraction complete | `from scripts.sprint_runner.cli import Colors, build_argument_parser` succeeds |

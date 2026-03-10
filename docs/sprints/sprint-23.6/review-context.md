# Sprint 23.6 Review Context

This file contains the shared context for all Tier 2 reviews in Sprint 23.6.
Individual session review prompts reference this file by path.

---

## Sprint Spec

> **Sprint 23.6: Tier 3 Review Remediation + Pipeline Integration + Warm-Up Optimization**
>
> **Goal:** Address all findings from the Tier 3 architectural review of Sprints 23–23.5: fix storage/query defects, wire the NLP Catalyst Pipeline into the running application with scheduled polling, optimize the 27-minute pre-market warm-up via reference data caching, add semantic deduplication and safe publish ordering, and improve runner maintainability. Clears the path for Sprint 24 with zero known issues.
>
> **Deliverables:**
> 1. Storage schema & query fixes (fetched_at, COUNT(*), batch store, since-in-SQL)
> 2. CatalystEvent timezone alignment (UTC defaults → ET)
> 3. SEC EDGAR email validation (ValueError on empty)
> 4. FMP canary test (schema validation at startup)
> 5. Post-classification semantic dedup (symbol + category + time window)
> 6. Batch-then-publish ordering (store all, then publish all)
> 7. Intelligence startup factory (standalone factory function)
> 8. App lifecycle wiring (lifespan handler, AppState, shutdown)
> 9. Polling loop (asyncio task, market-hours intervals)
> 10. Reference data file cache (JSON, atomic writes, per-symbol staleness)
> 11. Incremental warm-up (cache → diff → delta fetch → merge)
> 12. Runner CLI extraction (cli.py from main.py)
> 13. Conformance fallback monitoring (counter + WARNING)

---

## Specification by Contradiction

**Do NOT modify:** `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/analytics/`, `argus/backtest/`, `argus/ai/`, `argus/data/scanner.py`, `argus/data/databento_data_service.py`, `argus/ui/` (entire frontend).

**Do NOT add:** New Event Bus event types, new API endpoints beyond existing intelligence routes, new Pydantic models in `argus/core/config.py` beyond the single `catalyst` field.

**Do NOT change behavior of:** Event Bus (FIFO, sequence numbers), WebSocket bridge, AI layer, any strategy's `on_candle()` or signal generation, Risk Manager gating, Orchestrator allocation, Order Manager lifecycle, Databento data flow, IBKR connectivity, trade logging, performance calculation, backtesting.

**Edge cases to reject:** Concurrent poll cycles (wait, don't overlap). Cache file locked by another process (treat as corrupt). All sources disabled but pipeline enabled (empty results, WARNING). Universe Manager disabled but catalyst enabled (use cached watchlist).

---

## Escalation Criteria

1. Lifecycle integration failure — cannot cleanly follow AI service initialization pattern
2. Config loading failure — adding CatalystConfig breaks existing YAML loading
3. >5 pre-existing tests broken by any session
4. Runner behavior change after S5 refactoring
5. Cache corruption propagation — anything worse than WARNING + fallback
6. Polling loop interference with Event Bus or WebSocket
7. Storage migration failure on existing catalyst.db
8. Cross-session dependency breakage

---

## Regression Checklist

### Core System Invariants
| # | Check | How to Verify |
|---|-------|---------------|
| 1 | All pytest tests pass | `python -m pytest tests/ -x -q` |
| 2 | All Vitest tests pass | `cd argus/ui && npx vitest run` |
| 3 | No ruff lint errors | `ruff check argus/ scripts/` |
| 4 | Strategy files untouched | `git diff HEAD -- argus/strategies/` empty |
| 5 | Risk Manager untouched | `git diff HEAD -- argus/core/risk_manager.py` empty |
| 6 | Orchestrator untouched | `git diff HEAD -- argus/core/orchestrator.py` empty |
| 7 | Execution layer untouched | `git diff HEAD -- argus/execution/` empty |
| 8 | Analytics untouched | `git diff HEAD -- argus/analytics/` empty |
| 9 | Backtesting untouched | `git diff HEAD -- argus/backtest/` empty |
| 10 | AI layer untouched | `git diff HEAD -- argus/ai/` empty |
| 11 | Frontend untouched | `git diff HEAD -- argus/ui/` empty |

### Config Integrity
| # | Check | How to Verify |
|---|-------|---------------|
| 12 | SystemConfig loads system.yaml | Load config, verify `catalyst.enabled` is False |
| 13 | New config fields match model | Test: YAML keys recognized by `CatalystConfig.model_fields` |

### Pipeline Behavior
| # | Check | How to Verify |
|---|-------|---------------|
| 14 | Pipeline disabled by default | `catalyst.enabled: false` → AppState.catalyst_storage is None |
| 15 | Endpoints 503 when disabled | `GET /catalysts/recent` returns 503 |
| 16 | CatalystEvent defaults are ET | `CatalystEvent().published_at.tzinfo.key == "America/New_York"` |

### Storage & Cache
| # | Check | How to Verify |
|---|-------|---------------|
| 17 | Existing DB compatible | ALTER TABLE succeeds on old schema |
| 18 | No cache → full fetch | Warm-up without cache file fetches all symbols |
| 19 | Corrupt cache → fallback | Malformed JSON triggers WARNING + full fetch |

### Runner
| # | Check | How to Verify |
|---|-------|---------------|
| 20 | All runner tests pass | `python -m pytest tests/sprint_runner/ -x -q` |
| 21 | Runner still executable | `python scripts/sprint-runner.py --help` exits 0 |

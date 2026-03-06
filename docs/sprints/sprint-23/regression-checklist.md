# Sprint 23: Regression Checklist

Verify each of these after every session's implementation. The "How to Verify" column provides the exact command or assertion.

## Core Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | All existing pytest tests pass | `python -m pytest tests/ -x -q` — expect 1,977+ passing (pre-sprint count) |
| R2 | All existing Vitest tests pass | `cd argus/ui && npx vitest run` — expect 377+ passing (pre-sprint count) |
| R3 | Ruff linting passes | `python -m ruff check argus/` — expect 0 errors |
| R4 | System starts with `universe_manager.enabled: false` using existing flow | Start app with UM disabled, verify scanner→set_watchlist→data_service.start path executes (check logs for "StaticScanner" or "FMPScanner" messages, NOT "UniverseManager") |
| R5 | System starts with `universe_manager.enabled: true` using UM flow | Start app with UM enabled, verify UniverseManager path executes (check logs for "UniverseManager" messages) |

## Strategy Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| R6 | ORB Breakout config loads with universe_filter | `python -c "from argus.core.config import load_orb_config; c = load_orb_config('config/strategies/orb_breakout.yaml'); print(c.universe_filter)"` — should print filter values, not None |
| R7 | ORB Scalp config loads with universe_filter | Same as R6 with orb_scalp.yaml |
| R8 | VWAP Reclaim config loads with universe_filter | Same as R6 with vwap_reclaim.yaml and `load_vwap_reclaim_config` |
| R9 | Afternoon Momentum config loads with universe_filter | Same as R6 with afternoon_momentum.yaml and `load_afternoon_momentum_config` |
| R10 | ORB same-symbol mutual exclusion intact | Run test: `python -m pytest tests/ -k "orb" -k "exclusion" -v` (or equivalent exclusion test) |
| R11 | Strategy YAML keys match Pydantic model fields | Dedicated test: load YAML, compare keys against model_fields, assert no unrecognized keys |

## Data Flow Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| R12 | DatabentoDataService starts in ALL_SYMBOLS mode (when UM enabled) | Check logs for subscription message showing ALL_SYMBOLS |
| R13 | Fast-path discard active for non-viable symbols | Unit test: send CandleEvent for symbol NOT in viable set, verify IndicatorEngine NOT created for it |
| R14 | Candles for viable symbols still processed | Unit test: send CandleEvent for viable symbol, verify IndicatorEngine updated and event published |
| R15 | DatabentoDataService backward compat (UM disabled) | Unit test: start with specific symbol list (no viable set), verify all symbols processed |

## Config Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| R16 | system.yaml loads with universe_manager section | `python -c "from argus.core.config import load_system_config; c = load_system_config('config/system.yaml'); print(c.universe_manager)"` |
| R17 | system.yaml loads WITHOUT universe_manager section (defaults) | Copy system.yaml, remove universe_manager section, load — should use defaults |
| R18 | No Pydantic silently ignored keys in universe_manager config | Dedicated test: add fake key to universe_manager YAML, verify it's detected |
| R19 | No Pydantic silently ignored keys in universe_filter configs | Dedicated test per strategy: add fake key to universe_filter YAML, verify detected |

## UI Invariants

| # | Check | How to Verify |
|---|-------|---------------|
| R20 | Dashboard page loads without errors (UM enabled) | Visual: open Dashboard in browser, no console errors, universe panel visible |
| R21 | Dashboard page loads without errors (UM disabled) | Visual: open Dashboard, no console errors, universe panel shows "not enabled" state |
| R22 | All other Command Center pages unaffected | Visual: navigate to each of the 7 pages, verify no regressions |

## Non-Regression (Must NOT Change)

| # | Check | How to Verify |
|---|-------|---------------|
| R23 | AI Copilot functional | Visual: open Copilot, send a message, verify streaming response |
| R24 | Backtesting/replay mode unaffected | `python -m pytest tests/ -k "replay" -v` — all pass |
| R25 | Risk Manager behavior unchanged | `python -m pytest tests/ -k "risk" -v` — all pass |
| R26 | API endpoints (non-universe) unchanged | `python -m pytest tests/ -k "api" -v` — all existing pass |

# Sprint 23, Session 5a: Backend API Endpoints for Universe Data

## Pre-Flight Checks
1. Read: `argus/api/routes/` (any existing route file for pattern reference — e.g., `trades.py` or `system.py`), `argus/api/dependencies.py` (AppState, get_app_state), `argus/data/universe_manager.py` (get_universe_stats, get_reference_data)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Create REST API endpoints to expose universe status and symbol data for the Dashboard frontend.

## Requirements

1. Create `argus/api/routes/universe.py`:

   a. `GET /api/v1/universe/status`:
      - Returns JSON:
        ```json
        {
          "enabled": true,
          "total_symbols": 4200,
          "viable_count": 3100,
          "per_strategy_counts": {
            "strat_orb_breakout": 1850,
            "strat_orb_scalp": 1850,
            "strat_vwap_reclaim": 2200,
            "strat_afternoon_momentum": 1600
          },
          "last_refresh": "2026-03-08T08:15:00-05:00",
          "reference_data_age_minutes": 45.2
        }
        ```
      - When Universe Manager disabled: `{"enabled": false}`
      - JWT auth required (use existing auth dependency)

   b. `GET /api/v1/universe/symbols?page=1&per_page=50&strategy_id=strat_orb_breakout`:
      - Returns paginated symbol list with reference data:
        ```json
        {
          "symbols": [
            {
              "symbol": "AAPL",
              "sector": "Technology",
              "market_cap": 3200000000000,
              "float_shares": 15200000000,
              "avg_volume": 62000000,
              "matching_strategies": ["strat_orb_breakout", "strat_orb_scalp", "strat_vwap_reclaim"]
            }
          ],
          "total": 3100,
          "page": 1,
          "per_page": 50,
          "pages": 62
        }
        ```
      - Optional `strategy_id` filter: only symbols matching that strategy
      - JWT auth required
      - When Universe Manager disabled: return empty list with enabled=false

2. Register routes in the app (follow existing pattern — likely in `argus/api/app.py` or wherever routes are mounted).

3. In `argus/api/dependencies.py`, verify `universe_manager` field exists on `AppState` (added in Session 4b). If not, add it: `universe_manager: UniverseManager | None = None`.

## Constraints
- Do NOT modify existing API endpoints
- Do NOT add WebSocket streaming for universe data (REST is sufficient)
- Follow existing route patterns exactly (auth, error handling, response format)

## Test Targets
- New tests:
  1. `test_universe_status_enabled`: mock AppState with UM, verify response shape
  2. `test_universe_status_disabled`: mock AppState without UM, verify {"enabled": false}
  3. `test_universe_symbols_paginated`: verify pagination parameters work
  4. `test_universe_symbols_strategy_filter`: filter by strategy_id
  5. `test_universe_endpoints_require_auth`: 401 without JWT
  6. `test_universe_status_counts_accurate`: verify per_strategy_counts match routing table
- Minimum: 6 tests
- Command: `python -m pytest tests/api/ -k "universe" -v`

## Definition of Done
- [ ] Two API endpoints created and registered
- [ ] JWT auth on both endpoints
- [ ] Graceful disabled state
- [ ] All existing API tests pass
- [ ] 6+ new tests passing

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3, R26 (existing API endpoints unchanged).

## Sprint-Level Escalation Criteria
E11: AI Copilot affected → ESCALATE. E12: Modifying "Do not modify" files → ESCALATE.

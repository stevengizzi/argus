# Sprint 25, Session 1: Backend — Observatory API Endpoints

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md`
   - `docs/sprints/sprint-25/spec-by-contradiction.md`
   - `argus/analytics/` (existing analytics module structure)
   - `argus/api/routes/` (existing route patterns)
   - `argus/api/__init__.py` (route registration pattern)
   - `argus/intelligence/quality_engine.py` (SetupQualityEngine interface — read-only, DO NOT modify)
   - `argus/data/universe_manager.py` (UniverseManager interface — read-only, DO NOT modify)
   - `argus/strategies/base_strategy.py` (StrategyEvaluationBuffer, EvaluationEventStore — read-only)
   - `server.py` (lifespan pattern, AppState wiring)
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`
   Expected: ~2,768 tests, all passing
   Vitest: `cd argus/ui && npx vitest run`
   Expected: ~523 tests, all passing
3. Verify you are on the correct branch: `main` (or sprint-25 branch if created)

## Objective
Create ObservatoryService (analytics/aggregation layer) and 4 REST endpoints that provide the data foundation for all Observatory frontend views: pipeline stage counts, closest-miss ranking, per-symbol pipeline journey, and session summary.

## Requirements

1. **Create `argus/analytics/observatory_service.py`:**

   Class `ObservatoryService` initialized with references to:
   - `EvaluationEventStore` (for evaluation telemetry queries)
   - `UniverseManager` (for pipeline stage counts — viable symbols, routed symbols)
   - `SetupQualityEngine` (for quality scores on near-trigger symbols)
   - Strategy registry (for active strategy list and their evaluation buffers)

   Methods:

   a. `get_pipeline_stages(date: str | None = None) -> dict`:
      Returns counts for each pipeline tier:
      - `universe`: Total symbols in Databento feed (from DatabentoDataService or config)
      - `viable`: Symbols passing system filters (from UniverseManager.viable_count or equivalent)
      - `routed`: Symbols routed to ≥1 strategy (from UniverseManager routing table count)
      - `evaluating`: Symbols with evaluation events in the current session (query EvaluationEventStore for distinct symbols with events today)
      - `near_trigger`: Symbols that passed ≥ 50% of any strategy's conditions in their most recent evaluation (derived from evaluation events)
      - `signal`: Symbols that generated a signal today (query evaluation events with type SIGNAL_GENERATED)
      - `traded`: Symbols that were traded today (query trades table or evaluation events with type ORDER_PLACED or similar)

   b. `get_closest_misses(tier: str, limit: int = 20, date: str | None = None) -> list[dict]`:
      For the specified tier, return symbols sorted by how many conditions they passed (descending).
      Each entry includes: `symbol`, `strategy`, `conditions_passed`, `conditions_total`, `conditions_detail` (list of {name, passed: bool, actual_value, required_value}).
      Derive this from the most recent ENTRY_EVALUATION events in EvaluationEventStore.
      Parse the evaluation event metadata to extract individual condition results.

   c. `get_symbol_journey(symbol: str, date: str | None = None) -> list[dict]`:
      Return chronological evaluation events for a given symbol across all strategies.
      Each entry: `timestamp`, `strategy`, `event_type`, `result`, `metadata` (condition details, pattern strength, etc).
      Query EvaluationEventStore filtered by symbol and date.

   d. `get_session_summary(date: str | None = None) -> dict`:
      Aggregate metrics: `total_evaluations`, `total_signals`, `total_trades`, `symbols_evaluated` (distinct count), `top_blockers` (list of {condition_name, rejection_count, percentage} — the most frequent rejection reasons, top 5), `closest_miss` summary (symbol + strategy + conditions_passed + conditions_total for the single closest miss).

   Date parameter: If None, use today (ET timezone). If provided, query historical data for that date.

2. **Create `argus/api/routes/observatory.py`:**

   Register 4 endpoints, all JWT-protected:

   a. `GET /api/v1/observatory/pipeline?date={date}` → calls `get_pipeline_stages()`
   b. `GET /api/v1/observatory/closest-misses?tier={tier}&limit={limit}&date={date}` → calls `get_closest_misses()`
   c. `GET /api/v1/observatory/symbol/{symbol}/journey?date={date}` → calls `get_symbol_journey()`
   d. `GET /api/v1/observatory/session-summary?date={date}` → calls `get_session_summary()`

   Follow the existing route patterns in `argus/api/routes/`. Use Pydantic response models for each endpoint.

3. **Create `argus/config/observatory_config.py` (or add to existing config structure):**

   Pydantic model `ObservatoryConfig`:
   ```python
   class ObservatoryConfig(BaseModel):
       enabled: bool = True
       ws_update_interval_ms: int = 1000
       timeline_bucket_seconds: int = 60
       matrix_max_rows: int = 100
       debrief_retention_days: int = 7
   ```

   Wire into `SystemConfig` following the pattern used by `CatalystConfig` and `QualityEngineConfig`.

4. **Modify `argus/api/__init__.py`:**
   Register observatory routes (gated on `observatory.enabled`).

5. **Modify `server.py`:**
   Create `ObservatoryService` in lifespan, add to `AppState`. Follow the pattern used for `DebriefService` and `SetupQualityEngine` initialization.

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/core/`, `argus/execution/`, `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/intelligence/catalyst/`, `argus/data/`, `argus/ai/`, any existing page components
- Do NOT add Event Bus subscribers — ObservatoryService reads from DB/API only
- Do NOT change the EvaluationEventStore schema or any existing table
- Do NOT modify any existing API endpoint behavior

## Config Validation
Write a test that loads `config/system.yaml` (after adding the observatory section) and verifies:
1. All keys under `observatory:` are recognized by `ObservatoryConfig.model_fields.keys()`
2. No YAML keys are silently ignored by Pydantic

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| enabled | enabled |
| ws_update_interval_ms | ws_update_interval_ms |
| timeline_bucket_seconds | timeline_bucket_seconds |
| matrix_max_rows | matrix_max_rows |
| debrief_retention_days | debrief_retention_days |

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~15):
  - `test_pipeline_stages_returns_all_tiers` — verify all 7 tier keys present
  - `test_pipeline_stages_counts_accurate` — with seeded evaluation data, verify counts
  - `test_pipeline_stages_with_date_filter` — historical date returns different counts
  - `test_closest_misses_sorted_descending` — verify sort order
  - `test_closest_misses_limit_respected` — verify limit parameter
  - `test_closest_misses_condition_detail_present` — each entry has condition array
  - `test_closest_misses_empty_tier` — returns empty list, not error
  - `test_symbol_journey_chronological` — events sorted by timestamp
  - `test_symbol_journey_cross_strategy` — events from multiple strategies included
  - `test_symbol_journey_unknown_symbol` — returns empty list, not 404
  - `test_session_summary_aggregation` — totals match seeded data
  - `test_session_summary_top_blockers` — top 5 rejection reasons with percentages
  - `test_observatory_endpoints_require_auth` — 401 without JWT
  - `test_observatory_config_validation` — Pydantic model recognizes all YAML keys
  - `test_observatory_disabled_no_routes` — when enabled=false, endpoints return 404
- Minimum new test count: 15
- Test command: `python -m pytest tests/analytics/test_observatory_service.py tests/api/test_observatory_routes.py -x -q`

## Definition of Done
- [ ] ObservatoryService created with 4 methods
- [ ] 4 REST endpoints registered and JWT-protected
- [ ] ObservatoryConfig Pydantic model created and wired into SystemConfig
- [ ] Config-gated: disabled config → no routes mounted
- [ ] All existing tests pass
- [ ] 15+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No trading pipeline files modified | `git diff --name-only \| grep -E 'strategies/\|core/\|execution/\|data/'` returns empty |
| No existing API endpoints changed | Existing API tests pass |
| No Event Bus subscribers added | `grep -r "subscribe" argus/ --include="*.py" \| wc -l` unchanged |
| Config backward-compatible | System starts without observatory section in YAML |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-25/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-25/review-context.md`
2. The close-out report path: `docs/sprints/sprint-25/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/analytics/test_observatory_service.py tests/api/test_observatory_routes.py -x -q`
5. Files that should NOT have been modified: `argus/strategies/`, `argus/core/`, `argus/execution/`, `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/data/`, `argus/ai/`, existing page components

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-25/session-1-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the template protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify ObservatoryService reads from EvaluationEventStore and UniverseManager without modifying them
2. Verify no Event Bus subscribers were added
3. Verify condition detail parsing from evaluation event metadata is robust (handles missing fields gracefully)
4. Verify date parameter defaults to today (ET timezone) when not provided
5. Verify ObservatoryConfig follows the same pattern as CatalystConfig/QualityEngineConfig
6. Verify config-gating: endpoints not mounted when observatory.enabled = false

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-25/regression-checklist.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-25/escalation-criteria.md`

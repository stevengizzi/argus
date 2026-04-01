# Sprint 32, Session 4: Experiment Data Model + Registry Store

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/learning/learning_store.py` (DEC-345 SQLite pattern to follow)
   - `argus/intelligence/counterfactual_store.py` (another DEC-345 example)
   - `argus/analytics/evaluation.py` (MultiObjectiveResult — referenced in models)
   - `argus/analytics/comparison.py` (ComparisonVerdict — referenced in promotion events)
2. Run the test baseline (DEC-328 — Session 2+):
   Scoped: `python -m pytest tests/test_runtime_wiring.py tests/strategies/patterns/test_factory.py -v`
   Expected: all passing
3. Verify Sessions 1–3 committed

## Objective
Create the experiment data model and SQLite-backed registry store following the DEC-345 pattern. This is the persistence layer for the entire experiment pipeline — variants, backtest results, and promotion history.

## Requirements

1. Create `argus/intelligence/experiments/__init__.py`:
   - Export key classes: `ExperimentStore`, `ExperimentRecord`, `VariantDefinition`, `PromotionEvent`, `ExperimentStatus`

2. Create `argus/intelligence/experiments/models.py` with:

   a. **`ExperimentStatus`** — StrEnum: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `PROMOTED`, `DEMOTED`, `ACTIVE_SHADOW`, `ACTIVE_LIVE`

   b. **`VariantDefinition`** — frozen dataclass:
      - `variant_id: str` — unique ID (e.g., `strat_bull_flag__v2_aggressive`)
      - `base_pattern: str` — pattern template name (e.g., `bull_flag`)
      - `parameter_fingerprint: str` — hash from factory
      - `parameters: dict[str, Any]` — full detection param dict
      - `mode: str` — "live" or "shadow"
      - `source: str` — how this variant was created ("manual", "grid_sweep", "learning_loop")
      - `created_at: datetime`

   c. **`ExperimentRecord`** — dataclass:
      - `experiment_id: str` — ULID
      - `pattern_name: str`
      - `parameter_fingerprint: str`
      - `parameters: dict[str, Any]`
      - `status: ExperimentStatus`
      - `backtest_result: dict | None` — serialized MultiObjectiveResult
      - `shadow_trades: int`
      - `shadow_expectancy: float | None`
      - `is_baseline: bool`
      - `created_at: datetime`
      - `updated_at: datetime`

   d. **`PromotionEvent`** — frozen dataclass:
      - `event_id: str` — ULID
      - `variant_id: str`
      - `action: str` — "promote" or "demote"
      - `previous_mode: str`
      - `new_mode: str`
      - `reason: str` — human-readable explanation
      - `comparison_verdict: str | None` — serialized ComparisonVerdict
      - `shadow_trades: int`
      - `shadow_expectancy: float | None`
      - `timestamp: datetime`

3. Create `argus/intelligence/experiments/store.py` with **`ExperimentStore`**:
   - Constructor: `__init__(self, db_path: str = "data/experiments.db")`
   - Follow DEC-345 pattern: WAL mode, fire-and-forget writes with rate-limited warnings, `aiosqlite` for async
   - 3 tables: `experiments`, `variants`, `promotion_events`
   - `async def initialize(self)` — create tables if not exist
   - `async def save_experiment(self, record: ExperimentRecord) -> None`
   - `async def get_experiment(self, experiment_id: str) -> ExperimentRecord | None`
   - `async def list_experiments(self, pattern_name: str | None = None, limit: int = 50) -> list[ExperimentRecord]`
   - `async def get_baseline(self, pattern_name: str) -> ExperimentRecord | None` — returns the record marked `is_baseline=True`
   - `async def set_baseline(self, experiment_id: str) -> None` — marks as baseline, unmarks previous
   - `async def save_variant(self, variant: VariantDefinition) -> None`
   - `async def list_variants(self, pattern_name: str | None = None) -> list[VariantDefinition]`
   - `async def get_variant(self, variant_id: str) -> VariantDefinition | None`
   - `async def update_variant_mode(self, variant_id: str, new_mode: str) -> None`
   - `async def save_promotion_event(self, event: PromotionEvent) -> None`
   - `async def list_promotion_events(self, variant_id: str | None = None, limit: int = 50) -> list[PromotionEvent]`
   - `async def enforce_retention(self, max_age_days: int = 90) -> int` — delete old records, return count deleted
   - `async def close(self) -> None`
   - Retention enforcement called at initialization and periodically

## Constraints
- Do NOT modify any existing files
- Do NOT import MultiObjectiveResult or ComparisonVerdict directly — store them as serialized JSON dicts to avoid circular dependencies
- Use `python-ulid` for ID generation (consistent with DEC-026)
- Follow the exact same SQLite patterns as `learning_store.py` — WAL mode, fire-and-forget, rate-limited warning logs
- Separate DB file: `data/experiments.db` (not in `argus.db`)

## Test Targets
After implementation:
- New tests in `tests/intelligence/experiments/test_store.py`:
  - Save + retrieve experiment
  - List experiments by pattern name
  - Get/set baseline
  - Save + retrieve variant
  - List variants, update mode
  - Save + list promotion events
  - Retention enforcement (create old records, enforce, verify deleted)
  - WAL mode enabled
  - Fire-and-forget writes don't raise on DB errors
  - ExperimentStatus enum values
- Minimum new test count: 10
- Test command: `python -m pytest tests/intelligence/experiments/ -v`

## Definition of Done
- [ ] 3 files created in `argus/intelligence/experiments/`
- [ ] All CRUD operations working
- [ ] Retention enforcement working
- [ ] DEC-345 pattern followed (WAL, fire-and-forget, separate DB)
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` shows only new files |
| No circular imports | `python -c "from argus.intelligence.experiments import ExperimentStore"` succeeds |

## Close-Out
**Write the close-out report to:** docs/sprints/sprint-32/session-4-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-4-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/intelligence/experiments/ -v`
5. Files that should NOT have been modified: everything outside `argus/intelligence/experiments/` and `tests/intelligence/experiments/`

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify WAL mode is explicitly enabled
2. Verify fire-and-forget pattern (try/except around writes, WARNING log, never raises)
3. Verify retention enforcement deletes records older than max_age_days
4. Verify JSON serialization of backtest_result and comparison_verdict (not pickle)
5. Verify ULID usage for IDs (not UUID)
6. Verify separate DB file path (data/experiments.db)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

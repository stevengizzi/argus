# Sprint 32, Session 8: CLI + REST API + Server Integration + Config Gating

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/store.py` (S4)
   - `argus/intelligence/experiments/runner.py` (S6)
   - `argus/intelligence/experiments/promotion.py` (S7)
   - `argus/intelligence/experiments/spawner.py` (S5)
   - `argus/api/routes/learning.py` (REST route pattern to follow)
   - `argus/api/server.py` (lifespan initialization, router registration)
   - `argus/core/config.py` (SystemConfig — where ExperimentConfig will be added)
   - `scripts/run_learning_analysis.py` (CLI pattern to follow)
2. Run the test baseline (DEC-328 — final session, full suite):
   Full suite: `python -m pytest tests/ -n auto -q`
   Expected: ~4,270+ tests, all passing
3. Verify Sessions 1–7 committed

## Objective
Wire the complete experiment pipeline into the server, create CLI entry point, expose REST API endpoints, and add ExperimentConfig to SystemConfig with proper config gating. This is the final integration session.

## Requirements

1. Create `argus/intelligence/experiments/config.py` with **`ExperimentConfig`** Pydantic model:
   ```python
   class ExperimentConfig(BaseModel):
       model_config = ConfigDict(extra="forbid")
       enabled: bool = False
       auto_promote: bool = False
       max_shadow_variants_per_pattern: int = Field(default=5, ge=1, le=50)
       backtest_min_trades: int = Field(default=20, ge=1)
       backtest_min_expectancy: float = Field(default=0.0)
       promotion_min_shadow_days: int = Field(default=5, ge=1)
       promotion_min_shadow_trades: int = Field(default=30, ge=1)
       cache_dir: str = "data/databento_cache"
       variants: dict = Field(default_factory=dict)
   ```

2. In `argus/core/config.py`, add to **SystemConfig**:
   ```python
   experiments: ExperimentConfig = Field(default_factory=ExperimentConfig)
   ```
   Import ExperimentConfig from the experiments config module.

3. Create `argus/api/routes/experiments.py` with 4 JWT-protected endpoints:

   a. `GET /api/v1/experiments` — list experiments, optional `?pattern=bull_flag` filter
      - Returns: list of ExperimentRecord dicts with status, pattern, fingerprint, metrics
      - 503 if experiments disabled

   b. `GET /api/v1/experiments/{experiment_id}` — experiment detail
      - Returns: full ExperimentRecord including backtest_result
      - 404 if not found, 503 if disabled

   c. `GET /api/v1/experiments/baseline/{pattern_name}` — current baseline for a pattern
      - Returns: ExperimentRecord marked as baseline, or 404 if no baseline set

   d. `POST /api/v1/experiments/run` — trigger a sweep
      - Body: `{"pattern": "bull_flag", "param_subset": ["pole_min_move_pct"], "dry_run": false}`
      - Returns: `{"experiment_count": N, "grid_size": M}` on success
      - Launches sweep as background task (non-blocking)
      - 503 if disabled, 400 if invalid pattern

   Follow the same patterns as `routes/learning.py`: router prefix, JWT dependency, error handling.

4. In `argus/api/server.py`:
   - Import and register experiments router: `app.include_router(experiments_router)`
   - In lifespan, if `config.system.experiments.enabled`:
     - Initialize ExperimentStore
     - Store reference on app.state for route access
   - Pass experiment store and config to routes

5. Create `scripts/run_experiment.py` CLI:
   ```
   python scripts/run_experiment.py --pattern bull_flag --cache-dir data/databento_cache
   python scripts/run_experiment.py --pattern bull_flag --params pole_min_move_pct,flag_max_bars --dry-run
   ```
   - `--pattern` (required): pattern name
   - `--cache-dir` (optional): override from config
   - `--params` (optional): comma-separated param subset to sweep
   - `--dry-run` (optional): print grid, don't run
   - `--date-range` (optional): start,end dates
   - Uses ExperimentRunner directly (no server needed)
   - Prints summary table at end: fingerprint | status | trades | expectancy | Sharpe

6. Write a **config validation test** ensuring `experiments.yaml` keys match `ExperimentConfig` model fields (no silent drops).

## Constraints
- Do NOT modify any experiment pipeline files from S4–S7 (only consume their APIs)
- Do NOT add any frontend files
- REST endpoints return 503 when `experiments.enabled: false` (not 404)
- CLI must work standalone (no running server required)
- Background task for sweep must not block the API response
- All routes JWT-protected (follow existing pattern)

## Config Validation
This session adds ExperimentConfig to SystemConfig. Write a test that:
1. Loads `config/experiments.yaml`
2. Compares keys against `ExperimentConfig.model_fields.keys()`
3. Asserts no unrecognized keys

Expected mapping:

| YAML Key | Model Field |
|----------|-------------|
| enabled | enabled |
| auto_promote | auto_promote |
| max_shadow_variants_per_pattern | max_shadow_variants_per_pattern |
| backtest_min_trades | backtest_min_trades |
| backtest_min_expectancy | backtest_min_expectancy |
| promotion_min_shadow_days | promotion_min_shadow_days |
| promotion_min_shadow_trades | promotion_min_shadow_trades |
| cache_dir | cache_dir |
| variants | variants |

## Test Targets
After implementation:
- New tests in `tests/api/test_experiments_api.py` and `tests/test_experiment_cli.py`:
  - API: GET /experiments returns empty list
  - API: GET /experiments/{id} returns 404 for nonexistent
  - API: GET /experiments/baseline/bull_flag returns 404 when no baseline
  - API: POST /experiments/run triggers sweep (mock runner)
  - API: all endpoints return 503 when disabled
  - API: all endpoints require JWT
  - CLI: --dry-run prints grid without executing
  - Config: ExperimentConfig validates all fields
  - Config: experiments.yaml keys match model
  - Server: ExperimentStore initialized when enabled
- Minimum new test count: 8
- Test command (final session — full suite): `python -m pytest tests/ -n auto -q`

## Definition of Done
- [ ] ExperimentConfig Pydantic model created
- [ ] ExperimentConfig wired into SystemConfig
- [ ] 4 REST endpoints created and JWT-protected
- [ ] CLI script created with --pattern, --cache-dir, --params, --dry-run
- [ ] Server wiring: store initialized in lifespan, router registered
- [ ] Config validation test passes
- [ ] All existing tests pass
- [ ] All new tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| R9: Full test suite passes | `python -m pytest tests/ -n auto -q` — all pass |
| R11: experiments disabled → system unchanged | Start with `enabled: false`, verify no ExperimentStore init, 503 from endpoints |
| R12: Paper trading overrides unaffected | No changes to risk/orchestrator/loss limit configs |
| R13: No silently ignored config keys | Config validation test passes |

## Close-Out
**Write the close-out report to:** docs/sprints/sprint-32/session-8-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-8-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (final session): `python -m pytest tests/ -n auto -q`
5. Files that should NOT have been modified: any file in `argus/intelligence/experiments/` from S4–S7, any strategy file, any frontend file

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify ExperimentConfig has `extra="forbid"` (prevents silent key drops)
2. Verify REST endpoints return 503 (not 404) when experiments disabled
3. Verify POST /experiments/run uses background task (non-blocking)
4. Verify CLI works standalone without server
5. Verify JWT protection on all endpoints
6. Verify server lifespan initializes store only when experiments enabled
7. Verify config validation test is programmatic (not hardcoded key lists)
8. Run full regression checklist (final session of sprint)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

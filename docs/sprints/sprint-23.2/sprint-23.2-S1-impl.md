# Sprint 23.2, Session 1: Config + State + Lock + CLI Skeleton

## Pre-Flight Checks
1. Read these files to load context:
   - `docs/protocols/schemas/runner-config-schema.md` (canonical config schema — implement this)
   - `docs/protocols/schemas/run-state-schema.md` (state schema — implement this)
   - `docs/protocols/autonomous-sprint-runner.md` (lines 1–100: overview, state machine, lock file)
2. Run: `python -m pytest tests/ -x -q` — expect 2,101+ passing
3. Create branch: `git checkout -b sprint-23.2`
4. Verify `scripts/sprint_runner/` does NOT exist yet

## Objective
Create the runner package foundation: Pydantic config models matching the canonical schema, run-state persistence with atomic writes, PID-based lock file, and CLI skeleton with argparse.

## Requirements

1. **Create `scripts/sprint_runner/__init__.py`**: Package init with `__version__ = "1.0.0"` and module docstring.

2. **Create `scripts/sprint_runner/config.py`**: Pydantic models matching `runner-config-schema.md` EXACTLY.
   - Top-level `RunnerConfig(BaseModel)` with sections: `sprint`, `execution`, `git`, `notifications`, `cost`, `run_log`, `triage`, `conformance`, `doc_sync`.
   - Extension sections (optional, not in base schema): `session_metadata: dict[str, SessionMetadata] | None`, `protected_files: list[str] | None`, `forbidden_patterns: list[ForbiddenPattern] | None`.
   - `SessionMetadata(BaseModel)`: title, compaction_score, expected_test_delta, test_command, parallelizable, parallel_group, depends_on, has_visual_review, contingency, auto_split. All optional with sensible defaults.
   - `AutoSplitConfig(BaseModel)`: trigger, splits (list of SplitDef with id, title, scope).
   - Class method `RunnerConfig.from_yaml(path: str) -> RunnerConfig` to load and validate.
   - Implement environment variable overrides per schema doc: `ARGUS_RUNNER_MODE`, `ARGUS_RUNNER_SPRINT_DIR`, `NTFY_TOPIC`, `ARGUS_COST_CEILING`.
   - Validation: `notifications.tiers.HALTED` must be true, `notifications.tiers.COMPLETED` must be true, `execution.max_retries` must be 0–5, `cost.ceiling_usd` must be > 0, `sprint.directory` existence checked at load time.

3. **Create `scripts/sprint_runner/state.py`**: RunState matching `run-state-schema.md`.
   - `RunState(BaseModel)` with all fields from schema: schema_version, sprint, mode, status, halt_reason, current_session, current_phase, session_plan, session_results, git_state, cost, test_baseline, issues_count, timestamps, review_context_hash, notifications_sent.
   - `RunState.save(path)` — atomic write: write to `{path}.tmp`, then `os.rename` to `{path}`.
   - `RunState.load(path)` — load and validate. Raise clear error on invalid JSON or schema mismatch.
   - `RunState.create_initial(config: RunnerConfig) -> RunState` — create from config with NOT_STARTED status.
   - `SessionPlanEntry(BaseModel)`: session_id, title, status, depends_on, parallelizable, prompt_file, review_prompt_file, inserted_by.
   - `SessionResult(BaseModel)`: all fields from schema (implementation_verdict, review_verdict, conformance_verdict, triage_verdict, retries, tests_before, tests_after, etc.)
   - Status enum: NOT_STARTED, RUNNING, HALTED, COMPLETED, COMPLETED_WITH_WARNINGS, FAILED.
   - Phase enum: PRE_FLIGHT, IMPLEMENTATION, CLOSEOUT_PARSE, REVIEW, VERDICT_PARSE, TRIAGE, CONFORMANCE_CHECK, GIT_COMMIT, FIX_SESSION, DOC_SYNC, COMPLETE.

4. **Create `scripts/sprint_runner/lock.py`**: Lock file manager.
   - `LockFile` class with `acquire(sprint: str)`, `release()`, `is_locked() -> bool`, `validate_or_clear() -> bool` (for --resume: check PID, clear if stale).
   - Lock file at `.sprint-runner.lock` in repo root. Contains JSON: `{pid, started, sprint, host}`.
   - On acquire: if lock exists and PID is running → raise error. If lock exists and PID not running → warning + clear.
   - PID check: `os.kill(pid, 0)` (doesn't actually kill, just checks existence).

5. **Create `scripts/sprint_runner/main.py`**: CLI skeleton with argparse.
   - `def main()` — argparse with: `--config` (required), `--resume`, `--pause`, `--dry-run`, `--from-session`, `--skip-session`, `--stop-after`, `--mode` (override execution.mode).
   - In this session: parse args, load config, print "Runner initialized. Config loaded." then exit. The actual loop comes in S3.

6. **Create `scripts/sprint-runner.py`**: Thin entry point.
   ```python
   #!/usr/bin/env python3
   """ARGUS Autonomous Sprint Runner — entry point."""
   from sprint_runner.main import main
   if __name__ == "__main__":
       main()
   ```

## Constraints
- Do NOT modify anything under `argus/` or existing `scripts/*.py`
- Do NOT import any ARGUS trading system modules
- Use stdlib only for lock file (os, json, socket for hostname)
- Use Pydantic v2 (BaseModel, field_validator) matching existing ARGUS patterns

## Test Targets
New tests in `tests/sprint_runner/`:
- `test_config.py`: valid config, invalid config, defaults, env overrides, Sprint 23.5 config loads (~5)
- `test_state.py`: create, save, load, atomic write, resume validation, status transitions (~5)
- `test_lock.py`: acquire, release, stale detection, PID validation (~4)
- `test_main.py`: CLI arg parsing (--help, --config, --resume) (~1)
- Minimum: 15 new tests
- Command: `python -m pytest tests/sprint_runner/ -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass (2,101+)
- [ ] New tests passing (≥15)
- [ ] `python scripts/sprint-runner.py --help` works
- [ ] Sprint 23.5 runner-config.yaml loads without error
- [ ] Ruff linting passes

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No argus/ files modified | `git diff --name-only` shows only scripts/ and tests/ |
| Entry point works | `python scripts/sprint-runner.py --help` |
| Sprint 23.5 config loads | Test exists and passes |

## Close-Out
Follow `.claude/skills/close-out.md`. Include structured JSON appendix.

## Sprint-Level Regression Checklist
R1–R8 from `docs/sprints/sprint-23.2/review-context.md`

## Sprint-Level Escalation Criteria
Items 1–6 from `docs/sprints/sprint-23.2/review-context.md`

# Sprint 23.2, Session 6: Parallel + Auto-Split + Resume + CLI Flags + Polish

## Pre-Flight Checks
1. Read: `scripts/sprint_runner/main.py` (S3–S5 — full current state), `scripts/sprint_runner/state.py`, `scripts/sprint_runner/executor.py`, `docs/protocols/autonomous-sprint-runner.md` (interruption recovery section, halt and resume section)
2. Run: `python -m pytest tests/ -x -q` — all passing

## Objective
Complete the runner with parallel session execution, auto-split on compaction, resume-from-checkpoint, all CLI flags, and doc-sync automation. This is the final polish session.

## Requirements

1. **Create `scripts/sprint_runner/parallel.py`**: Parallel session execution.
   - **`async run_parallel_group(sessions: list[SessionPlanEntry], executor, git_ops, state, ...) -> list[SessionResult]`**: Run sessions concurrently via `asyncio.gather`. Each session gets its own executor call. Collect all results. Git commits serialized after all parallel sessions complete (each commits in order).
   - Sessions are grouped by `parallel_group` from session_metadata. Only sessions where ALL dependencies are met AND `parallelizable: true` run in parallel.
   - If any parallel session fails (ESCALATE or HALT), all results are saved but the run halts.

2. **Modify `scripts/sprint_runner/main.py`**: Integrate parallel execution.
   - Before processing each session, check if it's part of a parallel group. If multiple sessions in the same group are ready (all deps met), dispatch them together via `parallel.run_parallel_group()`.
   - Sequential sessions (parallelizable: false) execute normally.

3. **Auto-split on compaction**: In the executor result handling:
   - If `compaction_likely` is True AND session_metadata has `auto_split` config:
     - Insert sub-sessions from `auto_split.splits` into the session plan.
     - Rollback to checkpoint.
     - Re-execute from first sub-session.
   - If `compaction_likely` but no auto_split config: halt.
   - Track split events in run-state and notifications.

4. **Resume from checkpoint**: Implement full `--resume` logic in main.py:
   - Load existing run-state.json.
   - Validate schema_version, git SHA matches, test baseline within tolerance.
   - Clear stale lock file (PID validation).
   - Determine resume point from current_session + current_phase:
     - IMPLEMENTATION phase: rollback to checkpoint, re-run full session.
     - REVIEW phase+: check if implementation output exists in run-log. If yes, resume from REVIEW. If no, re-run from IMPLEMENTATION.
   - Create new lock file.
   - Continue loop from resume point.

5. **CLI flags** (modify main.py argparse + loop logic):
   - `--dry-run`: Print what would happen without invoking Claude Code. Use executor's dry_run mode.
   - `--from-session S3`: Skip all sessions before S3. Mark skipped sessions as SKIPPED.
   - `--skip-session S4`: Mark S4 as SKIPPED, execute all others. Validate dependencies still met.
   - `--pause`: Set a flag that halts gracefully after current session completes.
   - `--stop-after S2`: Halt after S2 completes. Mark as explicit stop, not failure.
   - `--mode autonomous|human-in-the-loop`: Override config execution.mode.

6. **Doc sync automation**: After all sessions COMPLETE:
   - If `doc_sync.enabled`, read doc-sync prompt template.
   - Build doc-sync prompt with accumulated issues, scope changes, and doc update checklist.
   - Invoke Claude Code.
   - Save output to run-log. DO NOT auto-commit — log notification that doc-sync output is ready for developer review.

7. **Polish:**
   - Terminal output: clean, colored status lines during execution (use ANSI codes or simple print formatting).
   - Progress indicator: "Session 3/6: Core Loop [RUNNING]" style output.
   - Summary at completion: table of sessions with verdict, test delta, duration.
   - Error messages: clear, actionable, include resume command when relevant.

## Constraints
- Do NOT modify anything under `argus/`.
- Parallel tests: verify timing or mock tracking to confirm concurrent execution.
- Resume tests: create run-state fixtures representing halted states at each phase.

## Test Targets
- `test_parallel.py`: 2-session concurrent (verify via timing or mock call tracking), git serialized commits, one parallel session fails → halt (~3)
- `test_auto_split.py`: compaction + auto_split → sub-sessions inserted, no config → halt, split succeeds and re-executes (~3)
- `test_resume.py`: resume from IMPLEMENTATION (rollback + re-run), resume from REVIEW (check output exists), stale lock cleared, SHA mismatch → error (~4)
- `test_cli_flags.py`: --dry-run (no executor calls), --from-session, --skip-session, --stop-after, --pause (~5)
- Minimum: 13 tests (some may overlap with existing test_loop.py updates)
- Command: `python -m pytest tests/sprint_runner/ -v`

## Definition of Done
- [ ] All features implemented. All tests pass (≥13 new, ≥80 total new across sprint).
- [ ] `python scripts/sprint-runner.py --config path/to/23.5/config --dry-run` prints session plan without executing.
- [ ] Runner is functionally complete per protocol spec.

## Close-Out
Follow `.claude/skills/close-out.md`. Include structured JSON appendix.

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-23.2/review-context.md`

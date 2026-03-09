# Sprint 23.2, Session 3: Core Execution Loop

## Pre-Flight Checks
1. Read:
   - `scripts/sprint_runner/config.py`, `state.py`, `lock.py` (S1)
   - `scripts/sprint_runner/executor.py`, `git_ops.py` (S2)
   - `docs/protocols/autonomous-sprint-runner.md` (full Execution Loop section — Steps 1–9)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Verify S2: executor and git_ops tests passing

## Objective
Implement the core state machine in `main.py` — the full sequential session execution loop that wires config, state, lock, executor, and git ops into the orchestrated flow per the protocol document.

## Requirements

1. **Rewrite `scripts/sprint_runner/main.py`**: Replace the skeleton with the full execution engine.
   - **Startup sequence:** Parse CLI args → load config → check lock file → load or create run-state → verify git branch + clean state → run initial test baseline → start execution loop.
   - **Session loop (for each session in session_plan):**
     - **Pre-flight (Step 1):** Dynamic test baseline patching from previous session. Run tests. Verify git SHA matches state. Pre-session file validation (DEC-292). Review context hash check (DEC-297, first session stores, subsequent sessions verify).
     - **Git checkpoint (Step 2):** Save checkpoint SHA to state.
     - **Implementation (Step 3):** Read prompt file. Patch test baseline into prompt. Call `executor.run_session()`. Save full output to run-log.
     - **Close-out extraction (Step 4):** Extract structured closeout. Handle missing (retry per failure classification). Validate schema. Save JSON + markdown to run-log.
     - **Independent test verification (Step 4b, DEC-291):** Run tests independently. Compare to closeout claims. Halt on mismatch.
     - **Diff validation (Step 4c, DEC-294):** Check changed files against protected list. Halt on violation. Check expected creates/modifies against actual diff. Save diff as patch.
     - **Review (Step 5):** Read review prompt. Inject closeout report into placeholder. Call executor. Save output.
     - **Verdict extraction (Step 6):** Extract structured verdict. Validate schema. Save.
     - **Decision gate (Step 7):** Automatic escalation checks (files_not_modified, regression_checklist, spec_conformance). Then verdict routing: CLEAR → proceed to conformance check (placeholder for S5), CONCERNS → placeholder for triage (S5), ESCALATE → halt.
     - **Cost check (Step 8):** Update cost estimate. Check ceiling. Halt if exceeded.
     - **Git commit (after CLEAR):** Commit with formatted message.
     - **State update:** Update session_results, advance to next session, save state atomically.
   - **Post-loop:** Set status COMPLETED (or COMPLETED_WITH_WARNINGS if warnings accumulated). Save final state.
   - **Halt handler:** On any halt condition — save state, save patch if uncommitted changes, rollback to checkpoint, set status HALTED with reason.
   - **--pause flag:** After current session completes, halt gracefully with reason "Manual pause requested."
   - **--stop-after flag:** After specified session completes, halt gracefully.
   - **Note:** Triage, conformance, notifications, parallel, auto-split, resume, doc-sync are PLACEHOLDERS in this session. They get real implementations in S4–S6. The decision gate should have clear `# TODO: S5 — wire triage` and `# TODO: S4 — send notification` comments.

2. **Run-log structure:** Create `{run_log.base_directory}/run-log/{session_id}/` for each session. Save: `implementation-output.md`, `closeout-structured.json`, `closeout-report.md`, `review-output.md`, `review-verdict.json`, `git-diff.patch`.

## Constraints
- Do NOT modify anything under `argus/`
- ALL executor calls must be mocked in tests
- The loop must be testable with 3 mock sessions (CLEAR, CLEAR, CLEAR) completing successfully
- Placeholders for triage/conformance/notifications must be clearly marked TODO

## Test Targets
- `test_loop.py`:
  1. Happy path: 3 sessions, all CLEAR → COMPLETED
  2. ESCALATE in session 2 → HALTED at session 2
  3. CONCERNS in session 2 → HALTED (triage placeholder halts)
  4. Test baseline patched between sessions (2101 → 2116 → 2131)
  5. Pre-flight catches missing file → HALTED
  6. Protected file violation in diff → HALTED
  7. Independent test verification mismatch → HALTED
  8. Cost ceiling exceeded → HALTED
  9. --stop-after S2 → HALTED after S2 with "Manual pause" reason
  10. Run-log files created in correct directory structure
  11. State transitions: NOT_STARTED → RUNNING → COMPLETED
  12. State transitions: NOT_STARTED → RUNNING → HALTED
  13. Atomic state writes (state.json exists after each session)
  14. Close-out retry on transient failure (mock first call fails, second succeeds)
  15. LLM-compliance retry prepends reinforcement instruction
- Minimum: 15 tests
- Command: `python -m pytest tests/sprint_runner/test_loop.py -v`

## Definition of Done
- [ ] Full execution loop runs with mocked executor. All existing + new tests pass (≥15 new).
- [ ] Run-log directory structure created correctly. State persisted atomically.
- [ ] Placeholders for triage/conformance/notifications clearly marked.

## Close-Out
Follow `.claude/skills/close-out.md`. Include structured JSON appendix.

## Sprint-Level Regression Checklist
R1–R8 from `docs/sprints/sprint-23.2/review-context.md`

## Sprint-Level Escalation Criteria
Items 1–6 from `docs/sprints/sprint-23.2/review-context.md`

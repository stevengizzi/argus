# Sprint 23.2: Autonomous Sprint Runner

## Goal

Implement the Autonomous Sprint Runner — a Python orchestrator that drives sprint execution by invoking Claude Code CLI, parsing structured close-out and review verdict JSON, making rule-based proceed/halt decisions, and maintaining full run-logs on disk. Full feature set per Sprint 23.1 protocol documents. Config format follows `runner-config-schema.md` with per-session metadata extensions.

## Scope

### Deliverables

1. **RunnerConfig Pydantic model** (`config.py`): Validates runner-config.yaml against the canonical schema from runner-config-schema.md. Includes base schema sections (sprint, execution, git, notifications, cost, run_log, triage, conformance, doc_sync) plus extension sections (session_metadata, protected_files, forbidden_patterns). Environment variable overrides.

2. **RunState persistence** (`state.py`): Manages run-state.json matching run-state-schema.md. Atomic writes (tmp → rename). Session plan tracking, session results, git state, cost accumulation, test baseline, issue counts, timestamps, notification log. Resume validation (schema version, git SHA, test baseline).

3. **Lock file** (`lock.py`): PID-based lock at `.sprint-runner.lock`. Acquire/release, stale detection, crash recovery. Prevents concurrent runs.

4. **Claude Code CLI executor** (`executor.py`): Invoke Claude Code via subprocess. Capture full output. Timeout support. Retry with exponential backoff (base × 4^n). Structured output extraction via regex for `json:structured-closeout` and `json:structured-verdict` blocks. Schema validation against structured-closeout-schema.md and structured-review-verdict-schema.md. Differentiate transient vs. LLM-compliance failures (DEC-295). Compaction detection heuristic (DEC-293).

5. **Git operations** (`git_ops.py`): Branch verification, checkpoint SHA capture, rollback to checkpoint, diff generation (file list + full patch), commit with formatted message, pre-session file existence validation (DEC-292), session boundary diff validation against protected files (DEC-294), review context hash verification (DEC-297).

6. **Core execution loop** (`main.py`): The full state machine per autonomous-sprint-runner.md protocol. Sequential session processing: pre-flight → git checkpoint → implementation → close-out extraction → independent test verification (DEC-291) → diff validation → review → verdict extraction → decision gate → triage/conformance → git commit → cost check → next session. Decision gate: CLEAR → conformance → commit, CONCERNS → Tier 2.5 triage, ESCALATE → halt.

7. **Notifications** (`notifications.py`): ntfy.sh (primary), Slack webhook + SMTP email (secondary). 5 notification tiers (HALTED, SESSION_COMPLETE, PHASE_TRANSITION, WARNING, COMPLETED). Quiet hours suppression. Halted reminder escalation. Message formatting per notification-protocol.md templates.

8. **Tier 2.5 triage** (`triage.py`): Invoke Claude Code subagent with triage prompt template. Parse TriageVerdict JSON. Route: INSERT_FIX → generate fix prompt + insert session, DEFER → log, HALT → halt, LOG_WARNING → warn. Max auto-fixes enforcement. Fix session insertion into session plan.

9. **Spec conformance check** (`conformance.py`): Invoke Claude Code subagent with conformance prompt template. Parse conformance verdict. Route: CONFORMANT → proceed, DRIFT-MINOR → warn (configurable halt), DRIFT-MAJOR → halt. Cumulative diff tracking.

10. **Cost tracking** (`cost.py`): Token estimation from output length. Cost calculation using configured rates. Ceiling enforcement (configurable halt). Per-session and cumulative tracking in run-state.

11. **Parallel execution** (`parallel.py`): Sessions with matching `parallel_group` and `parallelizable: true` run concurrently via asyncio. Each parallel session gets independent subprocess. Results collected via `asyncio.gather`. Git operations serialized (parallel sessions commit sequentially after all complete).

12. **Auto-split on compaction** (in `main.py`): When compaction detected (output exceeds threshold), check session_metadata for auto_split config. If splits defined, insert sub-sessions into plan and re-run from the split point. If no splits defined, halt.

13. **Resume from checkpoint** (in `main.py`): `--resume` flag validates run-state, clears stale lock, continues from halted session/phase. Phase-aware: if halted during IMPLEMENTATION, rollback and re-run. If halted during REVIEW, check if implementation output exists and proceed accordingly.

14. **CLI interface** (`main.py`): argparse with flags: `--config`, `--resume`, `--pause`, `--dry-run`, `--from-session`, `--skip-session`, `--stop-after`, `--mode`.

15. **Doc sync automation** (in `main.py`): Post-sprint, invoke Claude Code with doc-sync prompt template. Never auto-committed — developer reviews first.

16. **Entry point** (`scripts/sprint-runner.py`): Thin wrapper that imports and runs `sprint_runner.main`.

### Acceptance Criteria

1. **Config:** RunnerConfig loads and validates the Sprint 23.5 runner-config.yaml. Invalid configs produce clear Pydantic validation errors. Environment variable overrides work.
2. **State:** RunState round-trips through JSON. Atomic writes verified (tmp file created then renamed). Resume validation catches SHA mismatches and test count divergence.
3. **Lock:** Concurrent run prevented. Stale lock (PID not running) cleared on --resume.
4. **Executor:** Mock Claude Code CLI returns structured output → correctly extracted. Missing structured block → classified as transient or LLM-compliance failure. Retries use exponential backoff.
5. **Git:** Checkpoint → modify → rollback restores original state. Protected file modification detected. Pre-session file validation catches missing files.
6. **Loop:** 3-session happy path (all CLEAR) completes with correct state transitions. ESCALATE halts. CONCERNS triggers triage. Test baseline dynamically patched between sessions.
7. **Notifications:** HALTED notification sent with priority 5. SESSION_COMPLETE sent with priority 3. Quiet hours suppress low-priority. Reminder fires after configured interval.
8. **Triage:** Mock subagent returns INSERT_FIX → fix session appears in plan. Returns HALT → runner halts. max_auto_fixes exceeded → halt.
9. **Conformance:** CONFORMANT → proceed. DRIFT-MAJOR → halt. DRIFT-MINOR with warn config → warning logged.
10. **Cost:** Ceiling exceeded → halt (when halt_on_ceiling: true). Cost accumulates correctly across sessions.
11. **Parallel:** Two parallelizable sessions with same group run concurrently (verified via timing or mock tracking).
12. **Auto-split:** Compaction detected + auto_split config → sub-sessions inserted. No auto_split config → halt.
13. **Resume:** After halt, --resume continues from correct phase. Git state validated.
14. **CLI:** All flags produce expected behavior. --dry-run doesn't invoke Claude Code. --stop-after halts after specified session.
15. **Doc-sync:** Invoked after last session. Output saved but not committed.
16. **Sprint 23.5 compatibility:** Runner loads Sprint 23.5 runner-config.yaml and session prompts without error.

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Config load + validate | < 100ms | pytest timing |
| State atomic write | < 50ms | pytest timing |
| Output extraction (regex) | < 10ms for 100KB output | pytest timing |
| Full loop overhead per session (excluding Claude Code) | < 2 seconds | pytest timing with mocked executor |

### Config Changes

No changes to `config/system.yaml`. Runner uses its own config format.

## Dependencies

- Sprint 23.1 complete ✅ — all protocol documents, schemas, templates exist
- Claude Code CLI installed and authenticated
- Git available in PATH
- Python 3.11+ with asyncio support
- `aiohttp` already in requirements (for ntfy.sh HTTP POST)

## Relevant Decisions

- DEC-278: Autonomous Sprint Runner architecture
- DEC-279: ntfy.sh for notifications
- DEC-280: Structured close-out schema
- DEC-281: Structured review verdict schema
- DEC-282: Tier 2.5 automated triage
- DEC-283: Spec conformance check
- DEC-284/285: Run state schema
- DEC-286: Retry classification (transient vs. LLM-compliance)
- DEC-287: Cost tracking with ceiling
- DEC-291: Independent test verification
- DEC-292: Pre-session file validation
- DEC-293: Compaction detection heuristic
- DEC-294: Session boundary diff validation
- DEC-295: Exponential backoff for retries
- DEC-297: Review context hash verification

## Relevant Risks

- RSK: Claude Code CLI interface may change — subprocess invocation syntax must be verified against current CLI version.
- RSK: Large structured output (>100KB) may cause regex extraction to be slow — tested with 100KB fixture.

## Session Count Estimate

6 sessions estimated. Rationale: 6 focused backend sessions covering config/state/lock (S1), executor/git (S2), core loop (S3), notifications (S4), triage/conformance/cost (S5), parallel/resume/polish (S6). No frontend, no visual review. Work journal handoff prompt generated for human-in-the-loop mode.

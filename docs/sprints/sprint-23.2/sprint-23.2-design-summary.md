# Sprint 23.2 Design Summary

**Sprint Goal:** Implement the Autonomous Sprint Runner (`scripts/sprint-runner.py`) — a Python orchestrator that drives sprint execution by invoking Claude Code CLI, parsing structured output, making rule-based proceed/halt decisions, and maintaining full run-logs on disk. Full feature set per the Sprint 23.1 protocol documents. This is the last sprint executed manually — every sprint after uses this runner.

**Execution Mode:** Human-in-the-loop (the irony is acknowledged)

---

## Session Breakdown

- **Session 1:** Config models + State management + Lock file + CLI skeleton
  - Creates: `scripts/sprint_runner/__init__.py`, `scripts/sprint_runner/config.py`, `scripts/sprint_runner/state.py`, `scripts/sprint_runner/lock.py`, `scripts/sprint_runner/main.py` (skeleton with argparse), `scripts/sprint-runner.py` (thin entry point)
  - Modifies: (none)
  - Integrates: N/A (foundation session)
  - Compaction score: ~15 (High — 6 files, but straightforward Pydantic models and JSON I/O)

- **Session 2:** Executor (Claude Code CLI invocation + structured output extraction) + Git operations
  - Creates: `scripts/sprint_runner/executor.py`, `scripts/sprint_runner/git_ops.py`
  - Modifies: (none)
  - Integrates: S1 config models (executor reads config for timeouts, retries)
  - Compaction score: ~14 (High — subprocess management + git operations, but independent modules)

- **Session 3:** Core execution loop — the state machine wiring S1+S2 into the full session loop
  - Creates: (none — all implementation in existing files)
  - Modifies: `scripts/sprint_runner/main.py` (major rewrite: full state machine loop per protocol)
  - Integrates: S1 config + state + lock → S2 executor + git_ops → orchestrated loop with decision gates
  - Compaction score: ~16 (High — heavy integration, but the pseudocode is in the protocol doc)

- **Session 4:** Notifications — ntfy.sh, Slack, email, all 5 tiers, quiet hours, reminder escalation
  - Creates: `scripts/sprint_runner/notifications.py`
  - Modifies: `scripts/sprint_runner/main.py` (add notification calls at each state transition)
  - Integrates: S3 loop emits notification events → S4 notifications module delivers them
  - Compaction score: ~10 (Medium — single module, well-specced in notification-protocol.md)

- **Session 5:** Triage + Conformance + Fix session insertion + Cost tracking
  - Creates: `scripts/sprint_runner/triage.py`, `scripts/sprint_runner/conformance.py`, `scripts/sprint_runner/cost.py`
  - Modifies: `scripts/sprint_runner/main.py` (wire triage/conformance into decision gates, cost checks)
  - Integrates: S3 loop → triage subagent (at CONCERNS), conformance subagent (at CLEAR), cost ceiling check (at session boundary)
  - Compaction score: ~14 (High — 3 new files + integration, but each module is focused)

- **Session 6:** Parallel execution + Auto-split + Compaction detection + Doc-sync + Resume logic + all CLI flags
  - Creates: `scripts/sprint_runner/parallel.py`
  - Modifies: `scripts/sprint_runner/main.py` (add --resume/--pause/--dry-run/--skip-session/--from-session), `scripts/sprint_runner/state.py` (resume validation), `scripts/sprint_runner/executor.py` (parallel dispatch)
  - Integrates: S3 loop gains parallel execution path, auto-split on compaction, resume-from-checkpoint
  - Compaction score: ~17 (High — many features, but each is small and independent)

---

## Key Decisions

- **Package structure over single file:** `scripts/sprint_runner/` package with focused modules rather than one monolithic script. Easier to test, maintain, and extend.
- **Pydantic for config and state:** RunnerConfig and RunState both validated by Pydantic models at load time. Config schema matches `docs/protocols/schemas/runner-config-schema.md` exactly.
- **Atomic state writes:** All run-state.json writes go through write-to-tmp → rename pattern. Prevents corruption on crash.
- **subprocess for Claude Code:** Use `subprocess.run` (sync) for sequential sessions, `asyncio.create_subprocess_exec` for parallel sessions. Mock both in tests.
- **Regex extraction for structured output:** `json:structured-closeout` and `json:structured-verdict` blocks extracted via regex per protocol spec. Validated against JSON Schema.
- **ntfy.sh as primary notification:** HTTP POST to configurable endpoint. No authentication required for public topics. Private topics use auth_token header.
- **Triage + conformance via Claude Code subagent:** The runner invokes Claude Code CLI with the triage/conformance prompt templates, passing close-out and review data as context. Same subprocess mechanism as implementation sessions.
- **Cost tracking is estimation only:** The runner estimates cost from token counts using configured rates. It cannot read actual API billing. Ceiling enforcement halts the run.
- **Parallel execution via asyncio:** Sessions marked `parallelizable: true` with same `parallel_group` run concurrently. Each parallel session gets its own subprocess. Results collected via `asyncio.gather`.

---

## Scope Boundaries

**IN:**
- Full state machine per autonomous-sprint-runner.md protocol
- Config loading + Pydantic validation matching runner-config-schema.md
- Run state persistence (run-state.json) with atomic writes
- Lock file with PID validation
- Claude Code CLI invocation via subprocess
- Structured output extraction (closeout + verdict)
- Verdict-based proceed/halt decision gate (CLEAR/CONCERNS/ESCALATE routing)
- Git checkpoint, rollback, commit, branch verification, diff validation (DEC-294)
- Independent test verification (DEC-291)
- Pre-session file validation (DEC-292)
- Review context hash verification (DEC-297)
- Compaction detection heuristic (DEC-293)
- ntfy.sh notifications (all 5 tiers)
- Slack + email optional secondary channels
- Quiet hours + halted reminder escalation
- Tier 2.5 automated triage (subagent invocation + verdict parsing)
- Spec conformance check (subagent invocation + verdict parsing)
- Fix session auto-insertion with max_auto_fixes limit
- Cost estimation + ceiling enforcement
- Parallel session execution (asyncio)
- Auto-split on compaction detection
- Doc sync automation (post-sprint)
- Resume from checkpoint (--resume)
- CLI flags: --resume, --pause, --dry-run, --from-session, --skip-session, --stop-after
- Interruption recovery (sleep, WiFi drop, power failure, rate limit)

**OUT:**
- GUI / web interface for runner monitoring (terminal output only)
- Real-time token usage from Anthropic API (estimation only)
- Automatic sprint planning (runner executes, doesn't plan)
- Integration with CI/CD systems
- Windows support (Linux/macOS only — subprocess, asyncio, git)
- Modifications to any ARGUS trading system code

---

## Regression Invariants

1. All 2,101 existing pytest tests pass (runner is additive — new files in scripts/)
2. All 392 existing Vitest tests pass (no frontend changes)
3. No modifications to any file under `argus/` (trading system untouched)
4. No modifications to any existing file under `scripts/` (diagnostic scripts untouched)
5. Runner operates correctly with Sprint 23.5 package format

---

## File Scope

**Modify:** Nothing existing. All new files.
**Do NOT modify:** Anything under `argus/`, existing `scripts/*.py`, `config/`, `docs/` (except adding runner tests)

---

## Config Changes

No changes to `config/system.yaml`. The runner has its own config file format (per runner-config-schema.md) read from the sprint package directory. No Pydantic model overlap with ARGUS trading system configs.

---

## Test Strategy

- **S1:** ~15 tests — RunnerConfig validation (valid, invalid, defaults, env overrides), RunState CRUD (create, update, read, atomic write, resume validation), LockFile (acquire, release, stale detection, PID validation)
- **S2:** ~15 tests — Executor (mock subprocess, timeout, retry, output capture), output parser (valid closeout, valid verdict, missing block, malformed JSON), git_ops (checkpoint, rollback, diff, commit, branch verify — using tmp git repo fixture)
- **S3:** ~15 tests — Full loop (mock executor, 3-session happy path, ESCALATE halts, CONCERNS triggers triage, test baseline patch, pre-flight validation, file existence check, review context hash)
- **S4:** ~10 tests — Notification formatting (all 5 tiers), ntfy.sh delivery (mock HTTP), quiet hours suppression, reminder escalation, Slack/email secondary channels (mock)
- **S5:** ~12 tests — Triage invocation (mock subagent), triage verdict parsing, fix session insertion, max_auto_fixes enforcement, conformance check (mock subagent), conformance verdict routing, cost estimation, cost ceiling halt
- **S6:** ~13 tests — Parallel execution (2 sessions concurrent, mock subprocess), auto-split trigger, resume from each phase, CLI flags (--dry-run, --from-session, --skip-session, --pause, --stop-after), compaction detection, doc-sync invocation
- **Estimated total: ~80 new pytest tests**

---

## Runner Compatibility

- **Mode:** Human-in-the-loop (last time!)
- **Parallelizable sessions:** None (sequential for runner build)
- **Estimated token budget:** ~6 sessions × ~30K tokens = ~180K tokens
- **No runner-specific escalation notes** (this IS the runner)

---

## Dependencies

- Sprint 23.1 (Autonomous Runner Protocol Integration) complete ✅ — all protocol docs exist
- Claude Code CLI installed and authenticated (verified manually before S2)
- Git available in PATH
- Python 3.11+ with asyncio
- `aiohttp` for ntfy.sh notifications (already in requirements from Sprint 23)
- No new pip dependencies needed (subprocess, asyncio, json, hashlib, argparse are stdlib)

---

## Escalation Criteria

- Any modification to files under `argus/` (trading system)
- Runner fails to parse the Sprint 23.5 runner-config.yaml format
- Test count falls below 60 (target ~80)
- Any session compacts (manual split needed since no runner to auto-split yet!)

---

## Doc Updates Needed

- `docs/project-knowledge.md` — Update sprint count, test count, add runner to "Key Components"
- `docs/sprint-history.md` — Add Sprint 23.2 entry
- `CLAUDE.md` — Add `scripts/sprint_runner/` to file structure, add runner CLI usage
- `docs/architecture.md` — Section 3.Z Sprint Runner: update from "planned" to "implemented"
- `docs/decision-log.md` — New DEC entries for implementation decisions made during the sprint
- `docs/roadmap.md` — Note runner implementation as prerequisite met

---

## Artifacts to Generate

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with scoring tables)
4. Sprint-Level Escalation Criteria
5. Sprint-Level Regression Checklist
6. Doc Update Checklist
7. Review Context File
8. Implementation Prompts ×6 (S1–S6)
9. Tier 2 Review Prompts ×6
10. Work Journal Handoff Prompt (human-in-the-loop mode)

No adversarial review (Type A, builds on well-specced protocols).
No runner configuration (we ARE building the runner).
No visual review (no frontend).

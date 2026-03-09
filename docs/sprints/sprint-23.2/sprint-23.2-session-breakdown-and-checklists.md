# Sprint 23.2: Session Breakdown

## Dependency Chain
```
S1 (config/state/lock/CLI) → S2 (executor/git) → S3 (core loop) → S4 (notifications)
                                                                  → S5 (triage/conformance/cost)
                                                                  → S6 (parallel/resume/polish)
```
S4 and S5 both depend on S3 but are independent of each other. However, for simplicity in the last manual sprint, execute sequentially.

---

## Session 1: Config + State + Lock + CLI Skeleton

| Column | Value |
|--------|-------|
| **Creates** | `scripts/sprint_runner/__init__.py`, `scripts/sprint_runner/config.py`, `scripts/sprint_runner/state.py`, `scripts/sprint_runner/lock.py`, `scripts/sprint_runner/main.py` (skeleton), `scripts/sprint-runner.py` (entry) |
| **Modifies** | (none) |
| **Integrates** | N/A |
| **Parallelizable** | false |

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 6 | +12 |
| Files modified | 0 | +0 |
| Context reads | 3 (runner-config-schema.md, run-state-schema.md, protocol doc) | +3 |
| New tests | ~15 | +7.5 |
| Complex wiring | 0 | +0 |
| External API | 0 | +0 |
| Large files | 1 (config.py ~200 lines) | +2 |
| **Total** | | **24.5** |

Risk: Critical on paper. But these are pure data model files — Pydantic schemas, JSON I/O, no external APIs, no complex logic. The 23.1 schemas are explicit enough that this is transcription work.

**Tests (~15):** RunnerConfig valid/invalid/defaults/env-overrides ×5, RunState CRUD/atomic-write/resume-validation ×5, LockFile acquire/release/stale/PID ×4, CLI arg parsing ×1.

---

## Session 2: Executor + Git Operations

| Column | Value |
|--------|-------|
| **Creates** | `scripts/sprint_runner/executor.py`, `scripts/sprint_runner/git_ops.py` |
| **Modifies** | (none) |
| **Integrates** | S1 config (executor reads timeout, retries from RunnerConfig) |
| **Parallelizable** | false |

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | +4 |
| Files modified | 0 | +0 |
| Context reads | 4 (config.py, closeout-schema, verdict-schema, protocol doc) | +4 |
| New tests | ~15 | +7.5 |
| Complex wiring | 0 | +0 |
| External API | 1 (subprocess/CLI — mocked) | +3 |
| Large files | 1 (executor.py ~250 lines) | +2 |
| **Total** | | **20.5** |

Risk: High. Subprocess mocking and git fixture setup are the main challenges.

**Tests (~15):** Executor: mock CLI success/timeout/retry/structured-extraction/missing-block/malformed/LLM-compliance ×7. Git: checkpoint/rollback/diff/commit/branch-verify/file-validation/protected-check/context-hash ×8.

---

## Session 3: Core Execution Loop

| Column | Value |
|--------|-------|
| **Creates** | (none) |
| **Modifies** | `scripts/sprint_runner/main.py` (major: full state machine) |
| **Integrates** | S1 config+state+lock + S2 executor+git → full orchestrated loop |
| **Parallelizable** | false |

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | +0 |
| Files modified | 1 | +1 |
| Context reads | 6 (config.py, state.py, lock.py, executor.py, git_ops.py, protocol doc) | +6 |
| New tests | ~15 | +7.5 |
| Complex wiring | 1 (full state machine) | +3 |
| External API | 0 | +0 |
| Large files | 1 (main.py ~400 lines after this session) | +2 |
| **Total** | | **19.5** |

Risk: Critical — this is the integration session. The protocol doc's pseudocode is the spec.

**Tests (~15):** 3-session happy path, ESCALATE halts, CONCERNS triggers triage placeholder, test baseline patching, pre-flight validation, decision gate routing (CLEAR/CONCERNS/ESCALATE), state transitions, dynamic test count adjustment.

---

## Session 4: Notifications

| Column | Value |
|--------|-------|
| **Creates** | `scripts/sprint_runner/notifications.py` |
| **Modifies** | `scripts/sprint_runner/main.py` (add notify calls at state transitions) |
| **Integrates** | S3 loop emits events → S4 delivers notifications |
| **Parallelizable** | false |

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | +2 |
| Files modified | 1 | +1 |
| Context reads | 3 (notification-protocol.md, config.py, main.py) | +3 |
| New tests | ~10 | +5 |
| Complex wiring | 0 | +0 |
| External API | 1 (HTTP POST to ntfy — mocked) | +3 |
| Large files | 0 | +0 |
| **Total** | | **14** |

Risk: High threshold but straightforward — HTTP POST with headers.

**Tests (~10):** Format all 5 tiers, ntfy delivery (mock HTTP), quiet hours suppression, reminder timer, Slack webhook (mock), email SMTP (mock), disabled tier skipped, priority mapping.

---

## Session 5: Triage + Conformance + Cost

| Column | Value |
|--------|-------|
| **Creates** | `scripts/sprint_runner/triage.py`, `scripts/sprint_runner/conformance.py`, `scripts/sprint_runner/cost.py` |
| **Modifies** | `scripts/sprint_runner/main.py` (wire triage into CONCERNS path, conformance into CLEAR path, cost check at boundary) |
| **Integrates** | S3 decision gate → triage/conformance subagents; cost checked at each session boundary |
| **Parallelizable** | false |

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | +6 |
| Files modified | 1 | +1 |
| Context reads | 5 (triage protocol, conformance protocol, templates, config.py, main.py) | +5 |
| New tests | ~12 | +6 |
| Complex wiring | 1 (triage routing + fix insertion) | +3 |
| External API | 1 (subagent via CLI — mocked) | +3 |
| Large files | 0 | +0 |
| **Total** | | **24** |

Risk: Critical. Three modules + integration. But each module is small (~80–120 lines) and follows the same pattern (invoke CLI → parse JSON → route decision).

**Tests (~12):** Triage: INSERT_FIX/DEFER/HALT/LOG_WARNING routing ×4, max_auto_fixes ×1, fix session insertion ×1. Conformance: CONFORMANT/DRIFT-MINOR/DRIFT-MAJOR routing ×3. Cost: estimation ×1, ceiling halt ×1, accumulation ×1.

---

## Session 6: Parallel + Auto-Split + Resume + CLI Flags + Polish

| Column | Value |
|--------|-------|
| **Creates** | `scripts/sprint_runner/parallel.py` |
| **Modifies** | `scripts/sprint_runner/main.py` (CLI flags, parallel dispatch, auto-split, resume logic), `scripts/sprint_runner/state.py` (resume validation enhancements), `scripts/sprint_runner/executor.py` (parallel dispatch support) |
| **Integrates** | Parallel into loop, auto-split into compaction path, resume into startup |
| **Parallelizable** | false |

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | +2 |
| Files modified | 3 | +3 |
| Context reads | 5 (parallel.py, main.py, state.py, executor.py, protocol doc) | +5 |
| New tests | ~13 | +6.5 |
| Complex wiring | 1 (parallel + resume + auto-split) | +3 |
| External API | 0 | +0 |
| Large files | 0 | +0 |
| **Total** | | **19.5** |

Risk: High. Many features but each is small and independent. The main risk is the number of modifications to main.py.

**Tests (~13):** Parallel: 2-session concurrent ×1, git serialize ×1. Auto-split: compaction + config → insert ×1, no config → halt ×1. Resume: from each phase ×3, stale lock clear ×1. CLI: --dry-run ×1, --from-session ×1, --skip-session ×1, --pause ×1, --stop-after ×1.

---

## Summary

| Session | Scope | Score | Est. Tests |
|---------|-------|-------|------------|
| S1 | Config + State + Lock + CLI | 24.5 | ~15 |
| S2 | Executor + Git | 20.5 | ~15 |
| S3 | Core Loop | 19.5 | ~15 |
| S4 | Notifications | 14 | ~10 |
| S5 | Triage + Conformance + Cost | 24 | ~12 |
| S6 | Parallel + Resume + Polish | 19.5 | ~13 |
| **Total** | | | **~80** |

Note: All sessions score above 14. This is expected — the runner is a complex tool with many features. Each session's high score comes from the breadth of features, not from integration complexity. The protocol docs provide detailed pseudocode that reduces implementation risk.

---
---

# Sprint 23.2: Escalation Criteria

## Automatic ESCALATE
1. Any modification to files under `argus/` or existing `scripts/*.py`
2. Runner fails to load Sprint 23.5 runner-config.yaml
3. Existing test regression (2,101 pytest + 392 Vitest)
4. Any live API calls in tests (all subprocess, HTTP, and CLI calls must be mocked)

## Conditional ESCALATE
5. Test count below 60 (target ~80)
6. Any session compacts (manual split required)
7. Structured output regex fails on the provided schema examples
8. Run-state atomic write doesn't survive simulated crash (kill during write)

## Runner HALT Conditions
N/A — we ARE building the runner. These criteria trigger Tier 3 review via the work journal.

---
---

# Sprint 23.2: Regression Checklist

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R1 | All existing pytest tests pass | `python -m pytest tests/ -x -q` — 2,101+ passing | All |
| R2 | All existing Vitest tests pass | `cd argus/ui && npx vitest run` — 392+ passing | All |
| R3 | No files modified under argus/ | `git diff --name-only` shows only scripts/ and tests/ files | All |
| R4 | No existing scripts modified | `git diff scripts/*.py` returns empty (only new files in scripts/sprint_runner/) | All |
| R5 | Sprint 23.5 config loads | `python -c "from sprint_runner.config import RunnerConfig; RunnerConfig.from_yaml('path/to/23.5/config')"` succeeds | S1 |
| R6 | Ruff linting passes | `ruff check scripts/sprint_runner/` | All |
| R7 | All subprocess calls mocked in tests | `grep -r "subprocess.run\|create_subprocess" tests/sprint_runner/` — only in mock contexts | S2, S3 |
| R8 | Entry point works | `python scripts/sprint-runner.py --help` prints usage | S1 |

---
---

# Sprint 23.2: Doc Update Checklist

- [ ] `docs/project-knowledge.md` — Update test counts, sprint count, add runner to Key Components
- [ ] `docs/sprint-history.md` — Add Sprint 23.2 entry
- [ ] `CLAUDE.md` — Add `scripts/sprint_runner/` to file structure, add runner CLI usage
- [ ] `docs/architecture.md` — Section 3.Z: update from planned to implemented
- [ ] `docs/decision-log.md` — DEC entries for any implementation decisions
- [ ] `docs/roadmap.md` — Note Sprint 23.2 complete, runner prerequisite met

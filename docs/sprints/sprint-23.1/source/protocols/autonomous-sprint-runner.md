# Protocol: Autonomous Sprint Runner

**Context:** Python orchestrator (`scripts/sprint-runner.py`) + Claude Code CLI
**Frequency:** Once per sprint (execution phase)
**Output:** Completed sprint with full run-log, or structured halt with diagnostics

---

## Overview

The Autonomous Sprint Runner is a Python-based orchestrator that drives the
sprint execution loop by invoking Claude Code CLI programmatically. It replaces
the manual paste-prompt → read-output → paste-into-review → read-verdict cycle
with a deterministic state machine that makes rule-based proceed/halt decisions.

The runner operates in two modes:
- **Autonomous mode:** Full automated execution with human gates only at
  ESCALATE verdicts, cost ceiling breaches, and retry exhaustion.
- **Human-in-the-loop mode:** The runner provides structured output, run
  logging, and record-keeping while the developer manually drives sessions.

## Prerequisites

Before running:
1. Sprint package is complete (all prompts, review context, spec artifacts)
2. Runner config file exists (`config/runner.yaml`)
3. Claude Code CLI is installed and authenticated
4. Git repo is clean (no uncommitted changes)
5. Test suite passes at baseline
6. ntfy app installed on phone (for notifications)

## State Machine

```
┌──────────────┐
│  NOT_STARTED  │
└──────┬───────┘
       │ runner start
       ▼
┌──────────────┐
│   RUNNING     │◄──────────────────────────────┐
└──────┬───────┘                                 │
       │                                         │
       ▼                                         │
┌──────────────────────────────────────┐         │
│  FOR EACH SESSION IN SESSION_PLAN:    │         │
│                                       │         │
│  1. Pre-flight checks                 │         │
│  2. Git checkpoint                    │         │
│  3. Run implementation (Claude Code)  │         │
│  4. Extract structured close-out      │         │
│  5. Run review (Claude Code)          │         │
│  6. Extract structured verdict        │         │
│  7. Decision gate:                    │         │
│     ├─ CLEAR → conformance check      │         │
│     │   ├─ CONFORMANT → git commit    │         │
│     │   ├─ DRIFT-MINOR → warn, commit │         │
│     │   └─ DRIFT-MAJOR → HALT ──────────────┐  │
│     ├─ CONCERNS → Tier 2.5 triage     │     │  │
│     │   ├─ Insert fix → run fix ──────────┐ │  │
│     │   ├─ Defer → log, continue      │  │ │  │
│     │   └─ Halt → HALT ──────────────────┼─┤  │
│     └─ ESCALATE → HALT ─────────────────┼─┤  │
│  8. Check cost ceiling                 │  │ │  │
│     └─ Exceeded → HALT ─────────────────┼─┤  │
│  9. Next session                       │  │ │  │
└──────────────────────────────────────┘  │ │ │  │
       │ all sessions done                 │ │ │  │
       ▼                                   │ │ │  │
┌──────────────┐    ┌──────────┐          │ │ │  │
│   DOC SYNC    │    │  HALTED   │◄─────────┘─┘─┘  │
└──────┬───────┘    └────┬─────┘                   │
       │                  │ human resolves           │
       ▼                  └──────────────────────────┘
┌──────────────┐
│  COMPLETED    │
└──────────────┘
```

## Lock File

The runner creates a lock file at `.sprint-runner.lock` in the repo root on
startup and removes it on clean completion or clean halt. The lock file is
global (not sprint-scoped) to prevent accidental concurrent runs across
different sprints. The lock file contains:

```json
{
  "pid": 12345,
  "started": "2026-03-07T14:00:00Z",
  "sprint": "23",
  "host": "Stevens-MacBook"
}
```

**Lock file rules:**
- If `.sprint-runner.lock` exists when the runner starts a new run: refuse to
  start. Print "Another runner instance may be active (Sprint {N}). If the
  previous run crashed, use --resume to clear the stale lock and continue."
- If `.sprint-runner.lock` exists when `--resume` is used: validate the PID.
  If the PID is not running, clear the lock and proceed. If the PID is running,
  refuse.
- On clean COMPLETED or HALTED: remove the lock file.
- On crash (no clean exit): lock file remains. Cleared on next `--resume`.

This prevents accidental double-runs (including across different sprints) and
signals to other processes (and the developer) that the runner is active. Do
NOT touch the repo while the lock file exists.

## Interruption Recovery

The runner is designed to survive any interruption and resume cleanly.

### Laptop Sleep / Process Suspension

The Claude Code CLI process gets suspended (SIGSTOP). On wake, it either
resumes or has been killed by the OS.

- **If process resumes:** Execution continues normally. Claude Code may have
  lost its API connection; the CLI handles reconnection internally.
- **If process was killed:** The runner was not running — `run-state.json`
  reflects the last completed phase. The lock file remains (stale).
  Developer runs `--resume`, which clears the stale lock, validates git state,
  and continues from the last checkpoint.

### WiFi / Network Interruption

Claude Code CLI is making API calls to Anthropic's servers. A mid-stream
network drop means the session produces partial or no output.

- **Partial output (no structured close-out):** Runner's extraction step
  finds no `json:structured-closeout` block. Classified as transient failure.
  Retried up to `max_retries` times, each retry starting from the git
  checkpoint (clean state). If retries exhausted, runner halts.
- **No output at all (CLI error/timeout):** Same treatment — transient
  failure, retry from checkpoint.

### Claude Code Rate Limit / Usage Exhaustion

The CLI returns an error indicating rate limiting or usage cap.

- Runner catches this as a transient failure. Retries after
  `retry_delay_seconds` (default: 30s).
- If the rate limit is long-duration (hourly/daily reset), 2 retries at
  30-second intervals won't help. Runner halts after retry exhaustion.
- Notification: "Retry exhaustion: Claude Code CLI returned rate limit error.
  Resume after limit resets."
- Developer waits for limit reset, then runs `--resume`.

### Power Failure / Hard Crash

The machine loses power or the process is killed without cleanup.

- **run-state.json integrity:** All writes use atomic pattern (write to
  `.tmp`, rename). The file is always in a valid state — either the old
  version or the new version, never partial.
- **Git state:** The last committed session's changes are safe. Any
  in-progress uncommitted changes are in the working directory.
- **On restart:** Developer runs `--resume`. Runner reads `run-state.json`,
  validates git SHA matches, and determines recovery action:
  - If phase was IMPLEMENTATION: saves any partial output as a `.patch` file,
    rolls back to checkpoint SHA, re-runs the full session.
  - If phase was REVIEW or later: checks if implementation output exists in
    run-log. If yes, proceeds from REVIEW. If no, re-runs from IMPLEMENTATION.
  - Lock file is stale — `--resume` clears it after PID validation.

### Human Error (Manual Git Operations During Run)

Someone runs `git commit`, `git pull`, `git checkout`, etc. while the runner
is active.

- **Detection:** Runner validates `git rev-parse HEAD` against
  `run_state.git_state.current_sha` at every session boundary.
- **Mismatch:** Runner halts immediately with: "Git state diverged from
  run-state. Expected SHA {expected}, found {actual}. Manual git operations
  were performed while the runner was active."
- **Prevention:** The lock file signals "do not touch." The runner prints
  a warning at startup: "Runner is active. Do not perform manual git
  operations until the run completes or halts."

### Summary: Recovery by Failure Mode

| Failure Mode | Data Lost | Recovery |
|-------------|-----------|---------|
| Laptop sleep (process resumes) | Nothing | Automatic |
| Laptop sleep (process killed) | Current session's partial output | `--resume`, re-run session |
| WiFi drop mid-session | Current session's partial output | Auto-retry (up to max_retries) |
| WiFi drop between sessions | Nothing | Auto-retry on next session start |
| Rate limit hit | Nothing | Auto-retry, then halt. Resume after reset. |
| Power failure | Current session's uncommitted changes | `--resume`, re-run from checkpoint |
| Human git operations | Nothing (detected before damage) | Halt. Developer resolves, then `--resume`. |
| Runner bug / Python exception | Depends on where | `--resume` from last checkpoint |

## Execution Loop (Detailed)

### Step 1: Pre-Flight

For each session:

```python
# Dynamic test baseline patching
if previous_session_result:
    expected_tests = previous_session_result.tests_after
else:
    expected_tests = initial_test_baseline

# Run test suite
actual_tests = run_tests()
assert actual_tests == expected_tests, f"Test baseline mismatch: {actual_tests} != {expected_tests}"
assert all_pass, "Test suite has failures before session start"

# Verify git state
assert git_sha() == run_state.git_state.current_sha
assert git_is_clean()

# Pre-session file existence validation (DEC-292)
# Verify all files from prior sessions' "Creates" columns exist
for prior_session in completed_sessions:
    for created_file in session_breakdown[prior_session].creates:
        assert os.path.exists(created_file) and os.path.getsize(created_file) > 0, \
            f"File {created_file} (created by {prior_session}) is missing or empty"

# Verify all files in current session's pre-flight reads exist
for context_file in session.pre_flight_reads:
    assert os.path.exists(context_file), f"Context file {context_file} not found"

# Review context file hash verification (DEC-297)
# On first session: compute and store hash
# On subsequent sessions: verify hash hasn't changed
current_hash = sha256(review_context_file)
if run_state.review_context_hash is None:
    run_state.review_context_hash = current_hash
elif current_hash != run_state.review_context_hash:
    warn(f"Review context file has changed since sprint start")
    # Log but don't halt — change may be intentional (halt resolution)
```

### Step 2: Git Checkpoint

```python
checkpoint_sha = git_sha()
run_state.git_state.checkpoint_sha = checkpoint_sha
save_run_state()
```

### Step 3: Implementation

```python
prompt = read_file(session.prompt_file)

# Dynamic patching
prompt = patch_test_baseline(prompt, expected_tests)

# Invoke Claude Code (CLI syntax is pseudocode — see runner implementation
# for the actual subprocess call, validated against the current CLI version)
output = claude_code_run(prompt, timeout=session_timeout)

# Save full output immediately
save_to_run_log(session_id, "implementation-output.md", output)

# Compaction detection heuristic (DEC-293)
output_size = len(output.encode('utf-8'))
compaction_likely = output_size > config.compaction_threshold_bytes  # default: 100KB
if compaction_likely:
    warn(f"Session output is {output_size} bytes — compaction likely")
    run_state.session_results[session_id].compaction_likely = True
    run_state.session_results[session_id].output_size_bytes = output_size
```

### Step 4: Close-Out Extraction

```python
structured = extract_json_block(output, "structured-closeout")

if structured is None:
    # Differentiate transient vs. LLM-compliance failure (DEC-286, DEC-295)
    has_prose_closeout = "---BEGIN-CLOSE-OUT---" in output and "---END-CLOSE-OUT---" in output

    if has_prose_closeout:
        # LLM-compliance failure: implementation likely complete but JSON missing
        failure_type = "llm_compliance"
    else:
        # Transient failure: no meaningful output at all
        failure_type = "transient"

    if retries < max_retries:
        # Exponential backoff (DEC-295)
        delay = retry_delay_seconds * (4 ** retries)  # 30s, 120s
        if failure_type == "llm_compliance":
            # Prepend reinforcement instruction on retry
            prompt = "IMPORTANT: You MUST include the structured close-out JSON appendix.\n\n" + prompt
        rollback_to_checkpoint()
        sleep(delay)
        retry()
    else:
        if failure_type == "llm_compliance":
            halt(f"Implementation may be complete but structured output missing after "
                 f"{max_retries} retries. Review saved output manually.")
        else:
            halt(f"No output after {max_retries} retries")

validate_schema(structured, "structured-closeout-schema")
save_to_run_log(session_id, "closeout-structured.json", structured)

# Also save the human-readable portion
closeout_md = extract_before_json_block(output, "structured-closeout")
save_to_run_log(session_id, "closeout-report.md", closeout_md)
```

### Step 4b: Independent Test Verification (DEC-291)

```python
# Run test suite independently — do not trust close-out claims
actual_tests, actual_all_pass = run_tests()

if actual_all_pass != structured.tests.all_pass:
    halt(f"Close-out claims all_pass={structured.tests.all_pass} but "
         f"independent verification shows all_pass={actual_all_pass}")

if abs(actual_tests - structured.tests.after) > config.test_count_tolerance:
    halt(f"Close-out claims {structured.tests.after} tests but "
         f"independent verification found {actual_tests}")
```

### Step 4c: Session Boundary Diff Validation (DEC-294)

```python
# Quick filesystem check before spending tokens on review
diff_files = git_diff_stat()  # returns list of changed files

# Check "do not modify" violations — immediate ESCALATE
do_not_modify = session_breakdown.get_do_not_modify(session_id)
violations = [f for f in diff_files if f in do_not_modify]
if violations:
    halt(f"Files modified that are on do-not-modify list: {violations}")

# Check expected creates/modifies against actual diff
expected_creates = session_breakdown[session_id].creates
missing_creates = [f for f in expected_creates if f not in diff_files]
if missing_creates:
    # Log as context for review, don't halt
    warn(f"Expected files not in diff: {missing_creates}")

# Save diff as patch file
save_to_run_log(session_id, "git-diff.patch", git_diff_full())
```

### Step 5: Review

```python
review_prompt = read_file(session.review_prompt_file)

# Inject close-out report into placeholder
review_prompt = review_prompt.replace(
    "[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]",
    closeout_md
)

review_output = claude_code_run(review_prompt, timeout=session_timeout)
save_to_run_log(session_id, "review-output.md", review_output)
```

### Step 6: Verdict Extraction

```python
verdict = extract_json_block(review_output, "structured-verdict")
validate_schema(verdict, "structured-review-verdict-schema")
save_to_run_log(session_id, "review-verdict.json", verdict)
```

### Step 7: Decision Gate

```python
# Automatic escalation overrides
if not verdict.files_not_modified_check.passed:
    halt("Files modified that should not have been")
if not verdict.regression_checklist.all_passed:
    halt("Regression checklist failed")
if verdict.spec_conformance.status == "MAJOR_DEVIATION":
    halt("Major spec deviation detected")

# Verdict-based routing
if verdict.verdict == "ESCALATE":
    halt(f"Review escalated: {verdict.escalation_triggers}")

elif verdict.verdict == "CONCERNS":
    triage_result = run_tier_2_5_triage(structured, sprint_spec, spec_by_contradiction)
    handle_triage_result(triage_result)  # may insert fix sessions, defer, or halt

elif verdict.verdict == "CLEAR":
    if structured.scope_gaps or structured.prior_session_bugs:
        triage_result = run_tier_2_5_triage(structured, sprint_spec, spec_by_contradiction)
        handle_triage_result(triage_result)  # may insert fix sessions, defer, or halt

# Conformance check runs for ALL non-halted paths (CLEAR or CONCERNS-resolved)
# This ensures cumulative drift is checked even after triage inserts fixes
run_conformance_check()
git_commit(session)
```

### Step 8: Cost Check

```python
update_cost_estimate(session_token_usage)
if run_state.cost.total_cost_estimate_usd > run_state.cost.ceiling_usd:
    halt(f"Cost ceiling exceeded: ${total} > ${ceiling}")
```

### Step 9: Fix Session Insertion

When Tier 2.5 triage recommends inserting a fix session:

```python
fix_id = f"{session_id}-fix-{fix_count}"
fix_prompt = generate_fix_prompt(issue, sprint_spec)

# Insert into session plan immediately after current session
insert_session(fix_id, after=session_id, prompt=fix_prompt)

# Execute the fix session through the same loop
execute_session(fix_id)
```

Fix sessions go through the same implementation → review → verdict → conformance
loop as planned sessions. They get their own run-log subdirectory.

### Step 10: Doc Sync (Post-Sprint)

After all sessions complete:

```python
if doc_sync_enabled:
    doc_sync_prompt = generate_doc_sync_prompt(
        doc_sync_queue="issues.jsonl + scope-changes.jsonl + doc-sync-queue.jsonl",
        doc_update_checklist=sprint_doc_checklist,
        target_documents=config.doc_sync.target_documents
    )
    doc_sync_output = claude_code_run(doc_sync_prompt)
    # Doc sync is NEVER auto-committed — developer reviews first
    notify("COMPLETED", "Sprint run complete. Doc sync output ready for review.")
```

## Halt and Resume

### Halt Behavior

When the runner halts:
1. Save current state to `run-state.json` (atomic write)
2. Save all accumulated output (nothing is lost)
3. If git has uncommitted changes, save as `.patch` file and rollback to
   checkpoint SHA
4. Send HALTED notification with:
   - Sprint and session identifier
   - Halt reason (specific, actionable)
   - Path to run-log directory for details
   - Resume command
5. Set `run_state.status = "HALTED"`
6. Remove lock file (clean halt — developer may want to inspect the repo)

### Resume Behavior

To resume after a halt:
1. Developer resolves the issue (code fix, DEC decision, architectural call)
2. Developer runs: `python scripts/sprint-runner.py --resume`
3. Runner checks for stale lock file (clears if PID not running)
4. Runner creates new lock file
5. Runner validates git state matches `run-state.json`
6. Runner continues from the halted session's phase
7. If the session needs re-running (implementation was the failure point),
   the runner rolls back to checkpoint and re-runs

### Manual Override

The developer can also:
- `--skip-session S3a` — skip a session (marks as SKIPPED, updates dependencies)
- `--pause` — halt gracefully after the current session completes
- `--dry-run` — run the full loop but don't invoke Claude Code (for testing)
- `--from-session S3a` — start from a specific session (skip earlier ones)

## Integration with Existing Protocols

| Existing Protocol | Runner Integration |
|-------------------|--------------------|
| sprint-planning.md | Produces the sprint package the runner consumes. No changes to planning workflow. |
| implementation-prompt.md | Prompts now include structured close-out requirement. Runner reads them as-is. |
| review-prompt.md | Prompts now include structured verdict requirement. Runner injects close-out. |
| in-flight-triage.md | Category 1-2 handled by Tier 2.5 auto-triage. Category 3-4 cause halts. |
| tier-3-review.md | Unchanged. ESCALATE verdicts halt the runner; developer brings to Claude.ai. |
| adversarial-review.md | Unchanged. Happens during planning, before runner execution. |
| close-out skill | Extended with structured JSON appendix. |
| review skill | Extended with structured JSON verdict. |

## Anti-Patterns

1. **Disabling Tier 2.5 to speed up the run.** The triage layer catches
   real issues. Disabling it to avoid halts means those issues compound.

2. **Setting cost ceiling too high.** A $200 ceiling on a 6-session sprint
   suggests something is wrong. Investigate, don't just raise the limit.

3. **Skipping conformance checks.** Small drift in session 2 becomes large
   drift by session 8. The check is cheap; the fix after drift compounds is not.

4. **Running in autonomous mode on untested sprint packages.** The first run
   of a new sprint package should use human-in-the-loop mode to validate the
   prompts produce the expected structured output.

5. **Ignoring COMPLETED_WITH_WARNINGS.** Warnings are issues that didn't
   block progress but need attention. Review them before the next sprint.

6. **Auto-inserting too many fix sessions.** If `max_auto_fixes` is hit,
   the sprint planning was insufficient. Halt and re-plan, don't keep patching.

7. **Performing manual git operations while the runner is active.** The lock
   file exists for a reason. Wait for the run to complete or halt before
   touching the repo.

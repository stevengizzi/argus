# Decision Log Entries: Autonomous Sprint Runner

> These entries should be appended to `docs/decision-log.md`.
> DEC-277 is the current max (Sprint 23.05, fail-closed on missing reference data).
> Runner entries begin at DEC-278.

---

**DEC-278:** Autonomous Sprint Runner Architecture
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Build a Python-based orchestrator (`scripts/sprint-runner.py`) that drives the
sprint execution loop by invoking Claude Code CLI programmatically. The runner
is a deterministic state machine — it does not use LLM tokens for coordination
logic. It reads sprint package files from disk, invokes Claude Code for each
session, parses structured output, makes rule-based proceed/halt decisions, and
maintains full state on disk for resume-from-checkpoint capability.

The runner supports two modes:
- **Autonomous mode:** Runner executes the full session loop, halting only on
  ESCALATE verdicts, transient failure exhaustion, or cost ceiling breach.
- **Human-in-the-loop mode (default):** The existing manual workflow remains
  unchanged. The runner infrastructure (structured output, run logs) can
  optionally be used for better record-keeping even in manual mode.

**Alternatives Rejected:**
1. LLM-based orchestrator (Claude.ai or Claude Code as the coordinator):
   Rejected because coordination logic is deterministic — it doesn't need
   language understanding, and using an LLM wastes tokens on "read file,
   paste into prompt, check output" logic that a Python script handles
   perfectly. Also avoids compaction risk in the orchestrator itself.
2. Agent teams as the orchestrator: Rejected because sprint sessions are
   inherently sequential (session N depends on session N-1). Agent teams
   excel at parallel work, not sequential coordination. Agent teams are
   used selectively *within* sessions when parallelizable, not *across*
   sessions.
3. Third-party orchestration framework (LangChain, CrewAI, etc.): Rejected
   for unnecessary dependency complexity. The orchestration logic is simple
   enough for a single Python script with no external framework.

**Rationale:**
Sprint packages are already machine-readable. Implementation prompts, review
prompts, session ordering, and acceptance criteria are all in files. The only
missing piece is a coordinator that reads these files, invokes Claude Code,
and makes proceed/halt decisions. A Python script is the simplest, most
reliable, and most debuggable solution. It produces zero LLM cost for
coordination and is immune to compaction.

**Constraints:**
- Must work with Claude Code CLI (`claude` command)
- Must support resume from any checkpoint (power failure, rate limit, etc.)
- Must preserve all session output for audit trail
- Must not require changes to Claude Code internals

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-275 (compaction risk scoring), DEC-290 (Claude.ai role)
- Related risks: RSK-TBD (runner misclassification)

---

**DEC-279:** Notification via ntfy.sh
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Use ntfy.sh as the primary notification channel for runner events. Mobile push
notifications via the ntfy app on iPhone. Single HTTP POST per notification,
no API keys, no OAuth, no server to maintain.

Five notification tiers:
- HALTED (priority: high) — needs human decision, always enabled
- SESSION_COMPLETE (priority: normal) — session done, review CLEAR
- PHASE_TRANSITION (priority: low) — phase start/finish within session
- WARNING (priority: low) — non-blocking issue logged
- COMPLETED (priority: normal) — sprint finished, always enabled

Tier-level enable/disable configuration allows progressive trust: start with
all tiers enabled, disable PHASE_TRANSITION once trust is established.
HALTED and COMPLETED cannot be disabled.

Optional redundancy channels (Slack webhook, email via Gmail) can be configured
but are not required.

**Alternatives Rejected:**
1. Slack webhook only: Rejected because Slack requires app setup, OAuth, and
   a running Slack client. ntfy is lighter and works via native mobile push.
2. Email only: Rejected because email lacks urgency tiers and may not be
   checked promptly during overnight US market hours.
3. SMS via Twilio: Rejected for cost and complexity. ntfy provides equivalent
   mobile push with zero marginal cost.

**Rationale:**
The runner operates while Steven is away from the computer (potentially
sleeping during US market hours). Notifications must reach his iPhone
reliably. ntfy.sh provides this with the simplest possible integration
(one HTTP POST, no authentication required for private topics).

**Constraints:**
- Must work on iPhone (ntfy app available on iOS)
- Must support priority levels for triage
- Must not require running a server
- Quiet hours configuration to prevent non-critical notifications during sleep

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner architecture)

---

**DEC-280:** Structured Close-Out Appendix
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Extend the close-out skill to produce a machine-parseable JSON block appended
to the existing human-readable close-out report. The JSON block is fenced with
` ```json:structured-closeout ` for reliable extraction by the runner. The
human-readable report remains unchanged and is always produced first.

The structured appendix contains: session identifier, verdict enum, test counts
(before/after/new/all_pass), files created/modified, scope additions, scope
gaps (with category, blocking info, and suggested action), prior-session bugs,
deferred observations, doc impacts, and DEC entries needed.

**Alternatives Rejected:**
1. Separate structured file (not appended to close-out): Rejected because it
   creates two artifacts to maintain per session. Appending keeps it atomic.
2. YAML instead of JSON: Rejected because JSON is more reliably parseable
   and has stricter syntax (less ambiguity for automated extraction).
3. Replace human-readable close-out entirely with structured format: Rejected
   because human readability is essential for manual mode and for developer
   review of session outcomes.

**Rationale:**
The runner needs machine-parseable session outcomes to make proceed/halt
decisions. The existing close-out report is prose-oriented and would require
fragile NLP parsing. A structured appendix gives the runner reliable data
while preserving the human-readable report for manual mode and audit.

**Constraints:**
- Must not break existing close-out report format
- Must be extractable via simple regex on the fence marker
- Must validate against the structured-closeout-schema

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner architecture), DEC-282 (Tier 2.5 triage)

---

**DEC-281:** Structured Review Verdict
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Extend the review skill to produce a machine-parseable JSON block appended to
the existing human-readable review report. Fenced with
` ```json:structured-verdict ` for extraction. Contains: verdict enum
(CLEAR / CONCERNS / ESCALATE), findings array with severity and category,
files reviewed, spec-conformance assessment, and recommended actions.

**Alternatives Rejected:**
1. Parse verdict from prose: Rejected — fragile and error-prone.
2. Structured-only output: Rejected — human readability needed for manual mode.

**Rationale:**
Same as DEC-280. The runner needs a reliable signal to decide proceed vs. halt.

**Constraints:**
- Must not break existing review report format
- CLEAR/CONCERNS/ESCALATE enum must be unambiguous

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-280 (structured close-out), DEC-278 (runner)

---

**DEC-282:** Tier 2.5 Automated Triage Layer
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Insert an automated triage step between Tier 2 review and human escalation.
When a structured close-out contains non-empty scope_gaps or prior_session_bugs,
the runner invokes a separate Claude Code session with a triage prompt. The
triage session classifies each issue using the Category 1–4 system from
in-flight-triage.md and recommends: insert fix session, defer to post-sprint,
or halt for human decision.

The triage session is read-only (no file modifications). Its output is a
structured JSON block with classifications and recommendations. The runner
acts on the recommendations: auto-inserting fix sessions for Category 1–2,
halting and notifying for Category 3 (substantial) and Category 4.

**Alternatives Rejected:**
1. Rule-based classification only (no LLM): Rejected because scope gap
   severity requires understanding the gap's description and its relationship
   to upcoming sessions — this needs language understanding.
2. Always halt for human triage: Rejected because this eliminates most of
   the autonomy benefit. Category 1–2 issues are routine and predictable.
3. Never halt (full autonomy): Rejected because Category 3–4 issues involve
   architectural judgment that the runner cannot reliably make.

**Rationale:**
The Tier 2.5 layer handles the middle-severity cases that don't warrant
waking the developer but aren't simple enough for regex rules. It uses LLM
judgment in a constrained, auditable way (structured prompt, structured output,
logged decisions). Its decisions are reviewable after the fact.

**Constraints:**
- Read-only: must not modify any files
- Must receive sprint spec + spec-by-contradiction for context
- Must produce structured output matching the triage-verdict schema
- Decisions must be logged to issues.jsonl for audit trail

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-280 (structured close-out)
- Related protocols: in-flight-triage.md (Category 1–4 definitions)

---

**DEC-283:** Spec Conformance Check at Session Boundaries
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
After each session receives a CLEAR verdict, the runner invokes a spec
conformance check via Claude Code subagent. The check compares the cumulative
git diff (from sprint start to current HEAD) against the sprint spec and
spec-by-contradiction. Output: CONFORMANT / DRIFT-MINOR / DRIFT-MAJOR with
specific findings.

CONFORMANT and DRIFT-MINOR: runner proceeds (DRIFT-MINOR logged as WARNING).
DRIFT-MAJOR: runner halts and notifies.

**Alternatives Rejected:**
1. No conformance check (trust session-level reviews): Rejected because small
   deviations compound across sessions. A session can pass its own review while
   contributing to cumulative drift.
2. Conformance check only at sprint end: Rejected because drift caught early
   is cheap to fix; drift caught after 8 sessions is expensive.
3. AST-based automated checking: Rejected — too complex to implement for the
   value, and naming/convention drift requires semantic understanding.

**Rationale:**
Individual session reviews verify that the session did what it was supposed to.
Conformance checks verify that the cumulative result still matches the overall
sprint design. This catches emergent drift that no single session review would
flag.

**Constraints:**
- Must use cumulative diff, not per-session diff
- Must reference both sprint spec AND spec-by-contradiction
- Must be lightweight (small prompt, fast execution)

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-281 (structured verdict)

---

**DEC-284:** Run-Log Architecture
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Every byte of runner output is written to disk immediately in a structured
run-log directory. Directory structure:

```
docs/sprints/sprint-{N}/run-log/
├── run-state.json              # Orchestrator checkpoint state
├── session-{id}/
│   ├── implementation-output.md
│   ├── closeout-structured.json
│   ├── closeout-report.md
│   ├── review-output.md
│   ├── review-verdict.json
│   └── git-diff.patch
├── issues.jsonl                # Append-only issue log
├── scope-changes.jsonl         # Append-only scope change log
├── doc-sync-queue.jsonl        # Items needing doc updates
└── work-journal.md             # Auto-generated narrative
```

All `.jsonl` files are append-only. The work-journal.md is a derived artifact,
auto-generated from structured data after each session. No LLM context ever
holds full sprint history — the run-log on disk is the single source of truth.

**Alternatives Rejected:**
1. In-memory state (write at end): Rejected — a crash mid-sprint would lose
   all progress and session outputs.
2. Database (SQLite): Rejected — overkill for append-only logs. JSONL files
   are simpler, human-readable, and git-friendly.
3. Claude.ai conversation as state: Rejected — subject to compaction, not
   machine-parseable, not resumable.

**Rationale:**
The run-log architecture solves the compaction problem permanently. No single
LLM invocation needs the full sprint history because state lives on disk, not
in context. Each session gets a fresh context window. The orchestrator (Python)
maintains state via files. Doc-sync reads pre-digested JSONL, not raw transcripts.

**Constraints:**
- All writes must be atomic (write to temp, rename) to prevent corruption
- Run-log must be committed to git after each session for backup
- JSONL format must be one JSON object per line (standard JSONL)

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-275 (compaction risk scoring)

---

**DEC-285:** Git Hygiene Protocol for Autonomous Runner
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
The runner manages git state as follows:
- Before each session: create a branch checkpoint (`git stash` or tagged commit)
- After CLEAR verdict + conformance check: commit with standardized message
  format `[Sprint N] Session {id}: {title}`
- After ESCALATE verdict: rollback to last clean commit (the checkpoint)
- After fix session insertion: fix session gets its own commit
- Resume: validate current git SHA matches run-state.json before continuing

All session diffs are saved as `.patch` files in the run-log regardless of
verdict, ensuring no work is ever truly lost.

**Alternatives Rejected:**
1. One big commit at sprint end: Rejected — loses per-session atomicity and
   makes rollback impossible.
2. Feature branches per session: Rejected — unnecessary branch proliferation
   for sequential work. Checkpoints on a single branch are sufficient.

**Rationale:**
Clean git state is a prerequisite for session isolation. If session 4 fails,
we need to roll back to session 3's committed state before running a fix
session. Per-session commits also provide a clean audit trail.

**Constraints:**
- Must never leave the repo in a dirty state between sessions
- Must preserve all work (even from failed sessions) via .patch files

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-284 (run-log)

---

**DEC-286:** Runner Retry Policy
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
The runner retries a session up to 2 times when the failure appears transient:
- No output at all (CLI error, timeout, network drop)
- Test suite timeout (not test failure — timeout specifically)
- Git operation failure (lock contention, network)
- Claude Code CLI non-zero exit without structured output

Retries use exponential backoff: first retry at `retry_delay_seconds` (default:
30s), second retry at `retry_delay_seconds × 4` (default: 120s). If the CLI
returns a rate-limit error with a "retry after" indication, the runner respects
that duration instead of the configured delay.

**LLM-compliance failure differentiation:** If the session produces full output
(including human-readable close-out markers `---BEGIN-CLOSE-OUT---` /
`---END-CLOSE-OUT---`) but the structured JSON block is missing, this is
classified as an LLM-compliance failure, not a transient failure. On the first
retry, the runner prepends a reinforcement instruction to the prompt:
"IMPORTANT: You MUST include the structured close-out JSON appendix." On the
second retry failure, the runner halts with a message noting the implementation
may be complete but structured output is missing — the developer should review
the saved output manually.

After 2 retries of either type, the runner halts and notifies with HALTED
priority. Each retry is logged in run-state.json with the failure reason and
classification (transient vs. LLM-compliance).

Non-transient failures (test assertion failures, ESCALATE verdict, structured
output with INCOMPLETE verdict) are never retried — they halt immediately
or trigger Tier 2.5 triage.

**Alternatives Rejected:**
1. No retries (halt on any failure): Rejected — transient failures from API
   timeouts or flaky tests would cause unnecessary developer interruption.
2. Unlimited retries: Rejected — could burn tokens indefinitely on a
   genuinely broken session.
3. Retry with modified prompt: Rejected — the runner should not modify prompts.
   If the prompt doesn't work, that's a planning issue for a human to resolve.

**Rationale:**
Transient failures are common in systems involving API calls and test suites.
Two retries is enough to survive a momentary hiccup without wasting significant
resources on a genuinely broken session.

**Constraints:**
- Retry count must be configurable in runner-config.yaml
- Each retry must start from a clean git state (rollback to checkpoint)

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-285 (git hygiene)

---

**DEC-287:** Cost Tracking and Ceiling
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
The runner tracks estimated token usage per session (extracted from Claude Code
CLI output) and maintains a running cost estimate in run-state.json. A
configurable cost ceiling in runner-config.yaml triggers a HALTED notification
if the estimated cumulative cost exceeds the threshold.

Cost estimates use the published API token pricing as a proxy even when running
via subscription (Max plan), because token counts still indicate resource
consumption relative to rate limits.

**Alternatives Rejected:**
1. No cost tracking: Rejected — running 8+ sessions autonomously could hit
   rate limits or accumulate unexpected costs without visibility.
2. Hard kill (not just halt): Rejected — a halt with notification gives the
   developer the option to continue if the cost is justified.

**Rationale:**
Autonomous execution removes the natural cost awareness that comes from manual
pacing. The runner needs a circuit breaker to prevent runaway consumption.

**Constraints:**
- Cost ceiling default: $50 per sprint run (configurable)
- Token counts extracted from Claude Code CLI stdout/stderr

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-274 (AI layer cost tracking)

---

**DEC-288:** Dynamic Test Baseline Patching
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Implementation prompts include a pre-flight check "Expected: N tests, all
passing." In autonomous mode, the runner dynamically patches this value based
on the previous session's actual test count from its structured close-out.
The original (planning-time) expected count is preserved in the prompt for
audit; the runner adds a comment with the dynamically adjusted count.

In human-in-the-loop mode, the developer manually notes the current test
count during pre-flight (as they do today).

**Alternatives Rejected:**
1. Static counts only: Rejected — session 1 adds 35 tests, making session 2's
   static "Expected: 1977" incorrect. This causes false-positive failures in
   pre-flight checks.
2. Remove test count from pre-flight entirely: Rejected — knowing the expected
   count is a valuable sanity check. Dynamic patching preserves the check
   while keeping it accurate.

**Rationale:**
Sequential sessions accumulate tests. Static prompts can't predict the exact
count after prior sessions run. Dynamic patching keeps pre-flight checks
meaningful without requiring prompt regeneration.

**Constraints:**
- Original planning-time count must be preserved (not overwritten) for audit
- Patching uses structured close-out test.after field from previous session

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-280 (structured close-out)

---

**DEC-289:** Session Parallelizable Flag
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
Add a `parallelizable` field (boolean, default: false) to the Session Breakdown
artifact in sprint planning. When true, the runner may invoke Claude Code with
agent teams enabled for that session, allowing internal parallelism (e.g., one
teammate handles backend, another handles frontend, a third writes tests).

Setting this flag requires that the session's Creates list contains clearly
independent outputs that don't modify the same files. The sprint planner must
justify the flag in the session breakdown.

In human-in-the-loop mode, the parallelizable flag is informational only — the
developer may choose to use agent teams manually or ignore it.

**Alternatives Rejected:**
1. Always use agent teams: Rejected — agent teams use 3–4× more tokens than
   sequential execution and add coordination overhead. Most sessions don't
   benefit from internal parallelism.
2. Never use agent teams: Rejected — some sessions (especially those creating
   both backend and frontend files) genuinely benefit from parallel execution.
3. Runner decides at runtime: Rejected — parallelizability is a planning
   decision that depends on understanding the session's scope, not something
   a runtime heuristic can reliably determine.

**Rationale:**
Agent teams are powerful but expensive. Making parallelism an explicit
planning-time decision ensures it's used only when justified and gives the
runner clear instructions.

**Constraints:**
- Default is false (opt-in only)
- Sessions scoring 14+ on compaction risk should NOT be parallelized (they
  should be split instead — parallelism is not a substitute for splitting)

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-275 (compaction risk scoring)

---

**DEC-290:** Claude.ai Role in Autonomous Mode
**Date:** 2026-03-07
**Sprint:** Pre-Sprint 23.5

**Decision:**
In autonomous mode, Claude.ai's role shifts from real-time sprint participant
to exception handler and strategic layer. Specifically:

**Stays in Claude.ai (unchanged):**
- Sprint planning (all phases)
- Adversarial review
- Tier 3 architectural review (triggered by ESCALATE)
- Strategic check-ins
- Codebase health audits
- Discovery (for new projects)

**Moves to runner + Claude Code:**
- Work journal triage → replaced by structured close-out + Tier 2.5 triage
- Impromptu fix session generation → runner auto-generates from templates
- Session-to-session orchestration → Python state machine
- Doc-sync execution → Claude Code session with accumulated JSONL input

**Stays in Claude Code (unchanged):**
- Implementation sessions
- Review sessions

In human-in-the-loop mode, Claude.ai retains its current role (work journal,
impromptu triage conversations, etc.).

**Alternatives Rejected:**
1. Remove Claude.ai entirely: Rejected — sprint planning, adversarial review,
   and Tier 3 review require multi-turn exploratory reasoning that Claude.ai
   handles better than Claude Code's task-oriented mode.
2. Keep Claude.ai in the real-time loop: Rejected — the mechanical parts
   (copy close-out, paste into review, read verdict, proceed) don't need
   language understanding. They waste tokens and developer time.

**Rationale:**
Claude.ai's strengths are in exploratory reasoning, design iteration, and
adversarial analysis. These are planning-time and exception-time activities.
The execution loop between sessions is mechanical coordination that a Python
script handles more reliably and at zero LLM cost.

**Constraints:**
- Claude.ai must remain the venue for all architectural decisions
- The runner must never make decisions that would normally require a DEC entry

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-282 (Tier 2.5 triage)

---

**DEC-291:** Independent Test Verification at Session Boundaries
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
The runner independently runs the test suite after implementation completes
and before invoking the review, comparing actual results against the structured
close-out's claimed test counts. If the close-out claims `all_pass: true` but
the runner's independent run shows failures, or if the test count diverges by
more than a configurable tolerance (default: 0), the session is flagged.

This addresses a specific compaction risk: when a session hits context limits,
the LLM may produce a close-out based on memory of an earlier passing test
run rather than the final state. The runner's independent verification catches
this before the review wastes tokens on a false-positive clean session.

If verification fails: the runner saves the discrepancy in the run-log, marks
the close-out as unreliable, and either retries the session (if the test
failures appear to be from incomplete implementation) or halts (if the close-out
is fundamentally misrepresenting the session's outcome).

**Alternatives Rejected:**
1. Trust close-out claims entirely: Rejected — compaction-induced false positives
   are a known failure mode from Sprint 22 experience.
2. Always re-run tests in the review session: Rejected — the review already
   runs tests, but it trusts the close-out for comparison. If the close-out
   is wrong, the review's baseline is wrong too.

**Rationale:**
The close-out is produced by the same LLM that did the implementation. In a
compaction scenario, both the implementation and the close-out may be degraded.
An independent test run by the orchestrator (Python, not LLM) provides a
ground-truth check that is immune to compaction.

**Constraints:**
- Test verification must use the same commands as pre-flight (pytest + vitest)
- Test count comparison tolerance is configurable (default: 0)

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-280 (structured close-out), DEC-275 (compaction risk)

---

**DEC-292:** Pre-Session File Existence Validation
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
Before running each session, the runner validates that all files listed in
prior sessions' "Creates" columns actually exist on disk. This catches the
case where a session received a CLEAR verdict but didn't actually produce all
planned files — perhaps due to the reviewer not checking, or the file being
created but empty/truncated.

Additionally, the runner validates that all files listed in the current
session's pre-flight "Read these files" list exist and are non-empty.

If validation fails: the runner halts with a specific message identifying
which files are missing and which session was supposed to create them.

**Alternatives Rejected:**
1. Trust CLEAR verdict means all files exist: Rejected — CLEAR means the
   review passed, not that every planned artifact was produced.

**Rationale:**
File existence is trivially checkable (zero LLM cost) and catches a class of
failure that would otherwise cause the next session to fail mid-implementation,
wasting tokens and requiring a more complex recovery.

**Constraints:**
- Checks file existence and non-zero size, not content correctness
- Uses the session breakdown's Creates columns as the source of truth

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner)

---

**DEC-293:** Compaction Detection Heuristic
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
The runner tracks implementation output size (in bytes) per session and flags
sessions where the output exceeds a configurable threshold (default: 100KB)
as "compaction-likely." For compaction-likely sessions:

1. Independent test verification (DEC-291) is mandatory (it can be optional
   for shorter sessions in a future optimization)
2. The output size and compaction-likely flag are logged in run-state.json
3. A WARNING notification is sent

Over time, this data is used to calibrate DEC-275's compaction risk scoring
system. If sessions consistently trigger compaction-likely at scores below
the current threshold (14), the threshold should be lowered. The runner logs
the planning-time compaction score alongside the actual output size to enable
this calibration.

**Alternatives Rejected:**
1. No compaction tracking: Rejected — the runner has empirical data that the
   planning-time scoring system lacks. Not collecting it wastes an opportunity.
2. Automatic session splitting on compaction detection: Rejected — splitting
   requires planning-time decisions about scope. The runner can detect
   compaction but not remedy it autonomously.

**Rationale:**
Compaction risk scoring (DEC-275) is currently based on pre-implementation
estimates. The runner can provide post-implementation ground truth, creating
a feedback loop that improves future scoring accuracy.

**Constraints:**
- Threshold is configurable in runner-config.yaml
- Data is logged for calibration but does not trigger halts by itself

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-275 (compaction risk scoring), DEC-291 (test verification)

---

**DEC-294:** Session Boundary Diff Validation
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
After implementation completes and before running the review, the runner
performs a `git diff --stat HEAD` and compares the list of changed files
against the session breakdown's planned Creates/Modifies columns. This is
a fast, zero-LLM-cost check that catches gross failures:

- A file that should have been created but wasn't
- A file that shouldn't have been touched but was
- No changes at all (empty session)

If the diff shows files on the "do not modify" list were changed, the runner
escalates immediately without invoking the review (saving tokens on what
would inevitably be an ESCALATE verdict).

If the diff shows missing expected files, the runner logs this as context
for the review but does not halt — the review may determine the omission
was justified.

**Alternatives Rejected:**
1. Rely entirely on the review to catch file-scope issues: Rejected — the
   review costs tokens. A free filesystem check that pre-empts obvious
   ESCALATEs is strictly better.

**Rationale:**
File-level diff checking is instantaneous and catches the highest-severity
class of errors (scope violations, missing deliverables) before spending
tokens on a review that would produce the same finding.

**Constraints:**
- Check is filesystem-only (no LLM cost)
- "Do not modify" violations trigger immediate ESCALATE
- Missing expected files are logged as review context, not auto-escalated

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-283 (spec conformance)

---

**DEC-295:** Exponential Retry Backoff
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
Runner retries use exponential backoff rather than flat delay: first retry at
`retry_delay_seconds` (default: 30s), second retry at `retry_delay_seconds × 4`
(default: 120s). If the CLI output contains a rate-limit-specific error with a
"retry after" duration, that duration is used instead of the configured delay.

This supersedes the flat-delay retry behavior implied in the original DEC-286.
DEC-286 has been amended to reflect this change.

**Alternatives Rejected:**
1. Flat delay (original design): Rejected — a 30s delay is often insufficient
   for hourly rate limits but wasteful for 5-second transient hiccups.
2. Parse API response headers for exact retry-after: Rejected — the runner
   invokes Claude Code CLI, not the API directly. Rate limit info may be in
   stderr text, not structured headers.

**Rationale:**
Exponential backoff is the standard approach for retry logic interacting with
rate-limited APIs. It's simple to implement and significantly improves the
odds of the second retry succeeding.

**Constraints:**
- Backoff multiplier: 4× (30s → 120s with defaults)
- Rate-limit detection: grep for "rate limit" or "429" in CLI stderr

**Supersedes:** N/A (amends DEC-286)

**Cross-References:**
- Related decisions: DEC-286 (retry policy), DEC-278 (runner)

---

**DEC-296:** Planning-Time Mode Declaration
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
Sprint planning Phase A adds a mode declaration step: "Declare execution mode:
autonomous / human-in-the-loop / undecided." This affects downstream artifact
generation:

- **Autonomous:** Skip work journal handoff prompt generation. Generate runner
  config as a sprint package artifact. Parallelizable assessment is mandatory.
- **Human-in-the-loop:** Skip runner config generation. Work journal handoff
  prompt is generated. Parallelizable flags are informational only.
- **Undecided:** Generate both work journal handoff and runner config. This is
  the safe default for sprints where the mode hasn't been decided yet.

This prevents wasted planning effort (generating artifacts that won't be used)
and ensures mode-specific artifacts are always present when needed.

**Alternatives Rejected:**
1. Always generate everything: Rejected — the work journal handoff prompt is
   substantial effort, and generating a runner config for a manual sprint is
   busywork.
2. Decide mode after planning: Rejected — mode affects artifact generation
   during planning. Deciding afterward means regenerating artifacts.

**Rationale:**
The current planning protocol generates all artifacts regardless of execution
mode. Once dual-mode is common, this creates unnecessary work. Declaring mode
early allows the planner to skip irrelevant artifacts.

**Constraints:**
- Default is "undecided" (generates everything) — safe for transition period
- Mode declaration does not affect spec-level artifacts (only prompt-level)

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-290 (Claude.ai role)

---

**DEC-297:** Review Context File Hash Verification
**Date:** 2026-03-09
**Sprint:** Pre-Sprint 23.5

**Decision:**
The runner computes a SHA-256 hash of the review context file at sprint start
and stores it in run-state.json. Before each review invocation, it re-hashes
the file and compares. If the hash has changed:

- Log a WARNING with the change detection
- Proceed with the review (the change may be intentional — e.g., spec revision
  during halt resolution)
- The warning is included in the session's run-log entry for post-sprint audit

This prevents a subtle class of bugs where the review checks against a spec
that differs from what the implementation was coded against. If the spec was
intentionally revised during a halt, the warning provides an audit trail. If
it was accidentally modified, the warning catches it.

**Alternatives Rejected:**
1. Halt on any change: Rejected — legitimate spec revisions during halt
   resolution would require manual override every time.
2. No verification: Rejected — the review context file is the spec-of-record.
   Undetected changes undermine the entire review process.

**Rationale:**
The review context file is referenced by path by all review prompts. It's the
single shared document that defines "what correct looks like." Verifying its
integrity is a cheap (one hash per session) defense-in-depth measure.

**Constraints:**
- Hash algorithm: SHA-256
- Hash is stored in run-state.json under `review_context_hash`
- Change detection is a WARNING, not a HALT

**Supersedes:** N/A

**Cross-References:**
- Related decisions: DEC-278 (runner), DEC-284 (run-log)

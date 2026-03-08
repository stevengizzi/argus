# Guide: Autonomous Sprint Execution

> Complete step-by-step process for running a sprint with the autonomous runner.
> For the human-in-the-loop equivalent, see `human-in-the-loop-process-guide.md`.

---

## Who Does What

| Actor | Responsibilities |
|-------|-----------------|
| **You (Developer)** | Sprint planning, adversarial review, ESCALATE resolution, post-sprint review, go/no-go on doc-sync, strategic decisions |
| **Claude.ai** | Sprint planning conversations, adversarial review, Tier 3 review, strategic check-ins |
| **Autonomous Runner** | Session orchestration, structured output parsing, proceed/halt decisions, fix session insertion, notifications, run-log management |
| **Claude Code** | Implementation, review, triage, conformance check, doc-sync (each as isolated invocations) |

---

## Phase 1: Sprint Planning (Unchanged)

This phase is identical to the human-in-the-loop process. All planning happens
in Claude.ai conversations, producing the standard sprint package.

### Step 1.1: Plan the Sprint

Open a Claude.ai conversation and follow the `sprint-planning.md` protocol:

1. **Phase A (Think):** Requirements, edge cases, scope boundaries, session
   decomposition, compaction risk scoring, config changes, regression assessment.

   **New for autonomous mode:**
   - Assign `parallelizable` flag for each session (default: false)
   - Confirm all session deliverables have machine-parseable acceptance criteria
   - Estimate token budget for the full sprint run

2. **Phase B (Checkpoint):** Produce design summary (compaction insurance).

3. **Phase C (Spec Artifacts):** Generate Sprint Spec, Spec-by-Contradiction,
   Session Breakdown (with Parallelizable column), Escalation Criteria,
   Regression Checklist, Doc Update Checklist.

4. **Phase C-1 (Adversarial Review):** If warranted, run in separate conversation.

5. **Phase D (Prompts):** Generate Review Context File, Implementation Prompts
   (with `<!-- STRUCTURED-CLOSEOUT -->` marker), Review Prompts (with
   `<!-- STRUCTURED-VERDICT -->` marker), Work Journal Handoff Prompt.

6. **Phase E (Verify):** Cross-check all artifacts against design summary.

### Step 1.2: Configure the Runner

Create or update `config/runner.yaml`:

```yaml
sprint:
  directory: "docs/sprints/sprint-23"
  session_order: ["S1a", "S1b", "S2a", "S3a", "S4a"]
  review_context_file: "docs/sprints/sprint-23/review-context.md"

execution:
  mode: "autonomous"
  max_retries: 2

notifications:
  primary:
    type: "ntfy"
    endpoint: "https://ntfy.sh/argus-sprint-runner"

cost:
  ceiling_usd: 50.0

triage:
  enabled: true
  max_auto_fixes: 3

conformance:
  enabled: true
```

### Step 1.3: Pre-Flight Validation

Before launching, verify manually:

- [ ] All prompt files exist at the paths referenced in runner config
- [ ] Review context file exists and is complete
- [ ] Git repo is clean (no uncommitted changes)
- [ ] Test suite passes: `pytest` and `npx vitest run`
- [ ] Claude Code CLI is authenticated: `claude --version`
- [ ] ntfy app is installed and subscribed to your topic
- [ ] Runner config validates: `python scripts/sprint-runner.py --validate`

---

## Phase 2: Autonomous Execution

### Step 2.1: Launch the Runner

```bash
python scripts/sprint-runner.py --config config/runner.yaml
```

The runner will:
1. Validate config and pre-flight checks
2. Create the run-log directory
3. Initialize `run-state.json`
4. Begin executing sessions in order

### Step 2.2: Walk Away

The runner operates autonomously. You can:
- Sleep (if it's overnight during US market hours)
- Work on other tasks
- Monitor progress via the ntfy app notifications

The runner will notify you when:
- **HALTED:** Something needs your decision (phone will buzz)
- **COMPLETED:** Sprint finished successfully
- **WARNING:** Non-blocking issue logged (low-priority notification)

### Step 2.3: What Happens Per Session (Automatic)

For each session in the plan, the runner executes this loop:

```
1. PRE-FLIGHT
   - Verify git state matches run-state
   - Run test suite, verify count matches expected baseline
   - Dynamic-patch test count in implementation prompt

2. GIT CHECKPOINT
   - Record current SHA as rollback point

3. IMPLEMENTATION (Claude Code)
   - Invoke: claude --prompt implementation-S{n}.md
   - Save full output to run-log/session-S{n}/implementation-output.md

4. CLOSE-OUT EXTRACTION
   - Extract ```json:structured-closeout block from output
   - Validate against schema
   - Save to run-log/session-S{n}/closeout-structured.json
   - If missing: retry (up to max_retries), then halt

5. REVIEW (Claude Code)
   - Inject close-out report into review prompt placeholder
   - Invoke: claude --prompt review-S{n}.md
   - Save full output to run-log/session-S{n}/review-output.md

6. VERDICT EXTRACTION
   - Extract ```json:structured-verdict block
   - Validate against schema
   - Save to run-log/session-S{n}/review-verdict.json

7. DECISION GATE
   ├─ Automatic ESCALATE if:
   │   - Protected files were modified
   │   - Regression checklist failed
   │   - Major spec deviation
   │
   ├─ CLEAR (and no issues in close-out):
   │   → Conformance check → commit → next session
   │
   ├─ CLEAR (but close-out has scope_gaps or prior_session_bugs):
   │   → Tier 2.5 triage → may insert fix sessions → continue
   │
   ├─ CONCERNS:
   │   → Tier 2.5 triage → classify findings → may insert fixes or halt
   │
   └─ ESCALATE:
       → Halt immediately, notify developer

8. CONFORMANCE CHECK (Claude Code subagent)
   - Cumulative diff vs sprint spec + spec-by-contradiction
   - CONFORMANT → proceed
   - DRIFT-MINOR → warn, proceed
   - DRIFT-MAJOR → halt

9. GIT COMMIT
   - Commit with: [Sprint N] Session S{n}: {title}
   - Update run-state with new SHA and test counts

10. COST CHECK
    - Update running cost estimate
    - If ceiling exceeded → halt

11. APPEND TO WORK JOURNAL
    - Auto-generate narrative entry from structured data

12. NEXT SESSION (or DOC SYNC if all done)
```

### Step 2.4: Fix Session Insertion (Automatic)

When Tier 2.5 triage recommends a fix session:

1. Runner generates a fix prompt from template
2. Fix session is inserted into the plan immediately before the dependent session
3. Fix session executes through the same loop (implementation → review → conformance)
4. Fix session gets its own run-log subdirectory (e.g., `session-S2a-fix-1/`)
5. If the fix session also has issues → halt (cascading fixes = planning problem)

Maximum auto-inserted fixes per sprint: `triage.max_auto_fixes` (default: 3).

---

## Phase 3: Handling Halts

### When You Get a HALTED Notification

1. **Read the notification.** It tells you:
   - Which session and phase
   - Why it halted
   - Where to find details

2. **Open the run-log.** Check:
   - `run-log/session-S{n}/closeout-report.md` — human-readable close-out
   - `run-log/session-S{n}/review-verdict.json` — what the review found
   - `run-log/issues.jsonl` — accumulated issues

3. **Diagnose.** Common halt reasons:

   | Halt Reason | Typical Resolution |
   |-------------|-------------------|
   | ESCALATE verdict | Bring to Claude.ai for Tier 3 review. May need DEC entry. |
   | Regression checklist failed | Fix the regression. May need to modify the session prompt. |
   | DRIFT-MAJOR | Review the drift. May need to adjust the sprint spec. |
   | Cost ceiling exceeded | Review cost estimates. Raise ceiling or optimize remaining sessions. |
   | Retry exhaustion | Session prompt may be too complex. Split it or revise. |
   | Max auto-fixes reached | Sprint planning was insufficient. Re-plan remaining sessions. |
   | Category 3 Substantial gap | Decide: insert session, defer, or re-scope. |

4. **Resolve.** Make the necessary fix or decision:
   - Code fixes: make them manually or via a targeted Claude Code session
   - DEC entries: log them
   - Prompt adjustments: edit the prompt file

5. **Resume:**
   ```bash
   python scripts/sprint-runner.py --resume
   ```

---

## Phase 4: Post-Sprint (Mostly Unchanged)

### Step 4.1: Review Auto-Generated Doc Sync

The runner executes a doc-sync session automatically, but the output is
**never auto-committed.** You review it:

1. Check the doc-sync output in `run-log/doc-sync/doc-sync-output.md`
2. Review proposed changes to each target document
3. Commit what's correct, revise what's not

### Step 4.2: Review Accumulated Issues

Open `run-log/issues.jsonl` and `run-log/deferred-observations.jsonl`:
- Were auto-resolved issues handled correctly?
- Do any deferred items need DEF entries?
- Are there patterns that suggest planning improvements?

### Step 4.3: Review Work Journal

Open `run-log/work-journal.md` for a narrative summary of the full sprint.
This is your single-document overview of what happened.

### Step 4.4: Calibrate

After your first few autonomous sprints:
- Review Tier 2.5 triage agreement rate
- Check if conformance checks caught real drift
- Adjust cost ceiling based on actual costs
- Tune `max_auto_fixes` based on experience
- Note any systematic issues for protocol improvements

### Step 4.5: Tier 3 Review

If warranted (sprint complete, periodic cadence, or accumulated concerns):
Bring the sprint results to a Claude.ai conversation for Tier 3 architectural
review. Use the run-log artifacts as input instead of individual session reports.

---

## Quick Reference: Developer Touchpoints

In a typical autonomous sprint run, you touch the system at these points:

| When | What | Time |
|------|------|------|
| Sprint start | Planning (Claude.ai) | 2–4 hours |
| Sprint start | Runner config + pre-flight | 15 minutes |
| Sprint start | Launch runner | 1 minute |
| During run | Handle HALTED notifications (0–2 expected) | 15–60 min each |
| Sprint end | Review doc-sync output | 30–60 minutes |
| Sprint end | Review issues and work journal | 15–30 minutes |
| Sprint end | Tier 3 review (if warranted) | 1–2 hours |

**Total developer time:** ~4–8 hours (compared to ~12–20 hours in manual mode)

The savings come from eliminating the mechanical orchestration work: copying
close-outs, pasting into reviews, reading verdicts, managing git state, and
context-switching between tools.

---

## Fallback: Switching Mid-Sprint

If autonomous mode is not working for a particular sprint (too many halts,
unexpected issues, new territory), you can switch to human-in-the-loop mode
at any point:

```bash
python scripts/sprint-runner.py --pause
```

Then continue manually using the standard prompts. The run-log preserves
everything completed so far. You can resume autonomous mode later:

```bash
python scripts/sprint-runner.py --resume
```

# Guide: Human-in-the-Loop Sprint Execution

> Complete step-by-step process for running a sprint manually with the
> developer driving each session. This is the original workflow, updated to
> support structured output and optional run-log record-keeping.
>
> For the autonomous equivalent, see `autonomous-process-guide.md`.

---

## Who Does What

| Actor | Responsibilities |
|-------|-----------------|
| **You (Developer)** | Everything: planning, session execution, review interpretation, triage, doc-sync, go/no-go decisions at every step |
| **Claude.ai** | Sprint planning conversations, work journal triage, adversarial review, Tier 3 review, strategic check-ins |
| **Claude Code** | Implementation and review (invoked by you via paste) |
| **Runner (optional)** | Structured logging and run-log generation (passive mode) |

---

## Phase 1: Sprint Planning (Identical to Autonomous)

Follow the `sprint-planning.md` protocol in a Claude.ai conversation:

1. **Phase A (Think):** Requirements, edge cases, scope boundaries, session
   decomposition, compaction risk scoring, config changes, regression assessment.
   - Parallelizable flags are informational only in this mode
   - Runner compatibility assessment is optional but recommended for future-proofing

2. **Phase B (Checkpoint):** Produce design summary.
3. **Phase C (Spec Artifacts):** All standard artifacts.
4. **Phase C-1 (Adversarial Review):** If warranted.
5. **Phase D (Prompts):** Implementation prompts, review prompts, review context
   file, work journal handoff prompt.
6. **Phase E (Verify):** Cross-check all artifacts.

---

## Phase 2: Sprint Setup

### Step 2.1: Open the Work Journal

Paste the Work Journal Handoff Prompt into a fresh Claude.ai conversation.
This conversation persists for the duration of the sprint. You bring issues
here for classification and triage.

If the work journal conversation grows long enough to risk compaction, start
a fresh conversation with the handoff prompt plus a brief "issues so far"
summary.

### Step 2.2: Verify Pre-Flight

Before the first session:
- [ ] Git repo is clean
- [ ] Correct branch checked out
- [ ] Test suite passes: record the baseline count
- [ ] All sprint package files accessible

---

## Phase 3: Session Execution Loop

For each session in the session breakdown, execute this cycle:

### Step 3.1: Pre-Flight Checks

1. Note the current test count (it changes with each session)
2. Verify git is clean
3. Verify you're on the correct branch

### Step 3.2: Run Implementation

1. Open Claude Code
2. Paste the implementation prompt for the current session
3. Wait for completion
4. Read the close-out report produced by the close-out skill

The close-out now includes a **structured JSON appendix** at the end (fenced
with `` ```json:structured-closeout ``). This is produced automatically by the
updated close-out skill. In manual mode, you can ignore it — it's there for
record-keeping and optional tooling. Focus on the human-readable report above it.

### Step 3.3: Triage Issues (If Any)

Read the close-out report. If it contains:

**Scope additions (small, in-scope):** Noted in the report. Acceptable if
justified. The Tier 2 review will evaluate.

**Scope gaps:** Bring to the work journal conversation:
```
"I'm in Session S2a. I found this scope gap:
[describe the gap]
My instinct: Category 3 Small / Substantial"
```
The work journal will classify and advise.

**Prior-session bugs:** Bring to the work journal:
```
"While in Session S3a, I noticed a bug from Session S1b:
[describe the bug]
It affects: [files]
My instinct: Category 2"
```
Do NOT fix prior-session bugs in the current session.

**Feature ideas:** Note in the work journal for deferred triage.

### Step 3.4: Run Review

1. Open the review prompt for the current session
2. Copy the close-out report (the human-readable part)
3. Paste it into the placeholder in the review prompt
4. Paste the complete review prompt into Claude Code
5. Wait for completion
6. Read the review report

The review now includes a **structured JSON verdict** at the end (fenced
with `` ```json:structured-verdict ``). In manual mode, focus on the
human-readable report. The structured block is for record-keeping.

### Step 3.5: Act on Review Verdict

| Verdict | Action |
|---------|--------|
| **CLEAR** | Proceed to the next session |
| **CLEAR with observations** | Note observations, proceed |
| **CONCERNS** | Evaluate findings. If minor, proceed. If significant, generate a targeted fix prompt. |
| **ESCALATE** | Stop. Bring to Claude.ai for Tier 3 review. |

### Step 3.6: Handle Fix Sessions (If Needed)

For Category 2 bugs or Category 3 gaps that need fixing before the next session:

1. Work with the work journal to generate a targeted fix prompt
2. The fix prompt should be minimal: bug description, affected files, proposed
   fix, regression test
3. Run the fix prompt in Claude Code
4. Review the fix (it gets its own close-out and review)
5. Proceed to the next planned session

### Step 3.7: Git Commit

After a CLEAR verdict:
```bash
git add -A
git commit -m "[Sprint 23] Session S2a: FMP Integration"
```

### Step 3.8: Repeat

Move to the next session in the session breakdown. Update your mental test
baseline with the new count from the close-out.

---

## Phase 4: Post-Sprint

### Step 4.1: Tier 3 Review (If Warranted)

Bring the sprint results to a Claude.ai conversation:
- All close-out reports
- All review reports
- The sprint spec and spec-by-contradiction
- Current architecture context

Follow the `tier-3-review.md` protocol.

### Step 4.2: Doc Sync

This is a manual process in human-in-the-loop mode. Work through the doc
update checklist from sprint planning:

1. Update `docs/project-knowledge.md` — sprint history, test counts, current state
2. Update `docs/architecture.md` — if new modules or patterns introduced
3. Update `docs/decision-log.md` — add any DEC entries from the sprint
4. Update `docs/dec-index.md` — add new DECs to the quick-reference
5. Update `docs/sprint-history.md` — add the sprint entry
6. Update `CLAUDE.md` — deferred items, operational context
7. Any other documents on the checklist

You can optionally use the doc-sync automation prompt in Claude Code to
accelerate this. The prompt is in the sprint package and takes the accumulated
issues and scope changes as input.

### Step 4.3: Triage Deferred Items

Review all Category 4 items from the work journal:
- Some become DEF entries
- Some become Sprint N.5 or N+1 scope
- Some get dropped as not worth the effort

### Step 4.4: Close Sprint

- [ ] All sessions completed and reviewed
- [ ] All fix sessions completed and reviewed
- [ ] Tier 3 review done (if warranted)
- [ ] All documents updated (doc sync complete)
- [ ] Deferred items triaged
- [ ] Git is clean, all changes committed

---

## Optional: Enhanced Logging Mode

You can run the runner in human-in-the-loop mode for structured record-keeping
without autonomous execution:

```yaml
# config/runner.yaml
execution:
  mode: "human-in-the-loop"
```

```bash
python scripts/sprint-runner.py --config config/runner.yaml
```

In this mode, the runner:
- Creates the run-log directory structure
- Watches for session output files you save to the run-log
- Validates structured close-out and verdict JSON if present
- Maintains `run-state.json` with your progress
- Auto-generates the work journal from structured data
- Accumulates the doc-sync queue

But it does NOT:
- Invoke Claude Code
- Make proceed/halt decisions
- Insert fix sessions
- Send notifications
- Commit to git

This gives you the audit trail and structured record-keeping benefits without
ceding control of the execution loop.

---

## Quick Reference: Developer Touchpoints

In a typical human-in-the-loop sprint, you touch the system at these points:

| When | What | Time |
|------|------|------|
| Sprint start | Planning (Claude.ai) | 2–4 hours |
| Per session | Paste prompt, wait, read close-out | 15–30 min |
| Per session | Triage issues (work journal) | 5–15 min |
| Per session | Paste review prompt, read verdict | 10–20 min |
| Per session | Git commit, pre-flight for next | 5 min |
| Per fix session | Generate fix prompt, execute, review | 15–30 min |
| Sprint end | Tier 3 review (Claude.ai) | 1–2 hours |
| Sprint end | Doc sync (manual or assisted) | 1–2 hours |
| Sprint end | Deferred item triage | 15–30 min |

**Total developer time per session:** ~45–90 minutes
**Total developer time per sprint (8 sessions):** ~12–20 hours

---

## Transitioning to Autonomous Mode

When you're ready to transition a sprint to autonomous mode:

1. Ensure the sprint package was planned with runner compatibility
   (structured output markers, parallelizable flags)
2. Configure `config/runner.yaml` with `mode: "autonomous"`
3. Run pre-flight validation: `python scripts/sprint-runner.py --validate`
4. Launch: `python scripts/sprint-runner.py`

The first autonomous sprint should be run in **shadow mode** — the runner
executes alongside you. After each session, compare:
- Did the runner make the same proceed/halt decision you would have?
- Did the Tier 2.5 triage classify issues the same way the work journal would?
- Did the conformance check catch anything you wouldn't have noticed?

After 1–2 shadow sprints with >90% agreement, switch to full autonomous mode.

---

## Comparison: Human-in-the-Loop vs. Autonomous

| Aspect | Human-in-the-Loop | Autonomous |
|--------|-------------------|-----------|
| **Session execution** | Developer pastes prompts | Runner invokes CLI |
| **Close-out reading** | Developer reads prose | Runner parses JSON |
| **Review handoff** | Developer copies close-out | Runner injects automatically |
| **Verdict interpretation** | Developer reads, decides | Runner parses, applies rules |
| **Issue triage** | Work journal conversation (Claude.ai) | Tier 2.5 subagent (Claude Code) |
| **Fix sessions** | Developer generates prompt (work journal) | Runner generates from template |
| **Git management** | Developer commits manually | Runner commits on CLEAR |
| **Notifications** | Not needed (developer is present) | ntfy.sh mobile push |
| **Doc sync** | Manual or assisted | Automated (human reviews) |
| **Run log** | Optional (enhanced logging mode) | Always produced |
| **Cost visibility** | Developer tracks manually | Runner tracks automatically |
| **Quality assurance** | Developer judgment at every step | Structured gates + human for exceptions |
| **Best for** | New sprint types, complex sprints, first run of new patterns | Well-understood sprints, routine execution, overnight runs |

# Sprint 31.9 IMPROMPTU-11: A2/C12 Cascade Mechanism Diagnostic

> Drafted Phase 2 post-Apr-24-debrief. Paste into a fresh Claude Code session.
> **Read-only session** — no code changes land here. Diagnostic report only.

## Scope

**Finding addressed:** A2/C12 from Apr 24 debrief — 44 unexpected short positions
accumulated through the session via an unidentified upstream mechanism, independent
of DEF-199. Today's `ibkr_close_all_positions.py` covered 14,249 shares across 44
symbols. Not DEC-372 stop-retry exhaustion (only 4/44 overlap), not network-
triggered reconnect snapshot (no such event today), not orphan bracket-leg fills
(only 6 total). The reconciliation mismatch count grew gradually 3 → 5 → 7 → 44
through the day rather than jumping in a single event.

**Critical re-framing from Apr 24 debrief §A2/C12:**
> Today's raw upstream cascade is ~2.0× worse than yesterday's (14,249 vs 6,949
> pre-doubling shares) despite a much lighter network event profile. A1 was the
> downstream amplifier; when it's removed, we see the upstream cascade at its
> true scale — and the true scale is larger than yesterday's. This is **prompt
> hypothesis (3)**: IMPROMPTU-04 addressed one trigger, but there are multiple
> upstream triggers flipping positions short, and the dominant one today is not
> the one A1 addressed.

**Priority:** Critical safety. Paper trading produces ~14K shares/day of
unintended short exposure; the A1 fix now correctly refuses to amplify these
at EOD and escalates to operator, but the upstream mechanism must be identified
before a real fix can be scoped.

**Scope posture: READ-ONLY DIAGNOSTIC.** This session does NOT fix DEF-204. The
fix is scoped to the new `post-31.9-reconciliation-drift` named horizon sprint
where it can receive adversarial review and the safe-during-trading constraint
doesn't apply. This session produces a mechanism report with evidence.

**Files touched (all new or doc-only):**
- `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` (NEW — the main deliverable)
- `CLAUDE.md` — DEF-204 entry may be refined with mechanism findings; DEF-204 stays OPEN (fix deferred)
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — IMPROMPTU-11 row complete
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — Stage 9C row for IMPROMPTU-11

**Safety tag:** `safe-during-trading` — read-only log + code analysis. Paper trading continues.

## Pre-Session Verification (REQUIRED)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue.
```

### 2. Verify dependencies

```bash
grep -c "DEF-204" CLAUDE.md  # Expected: ≥1 (opened in Apr 24 integration commit)
ls -la docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md  # Expected: exists
```

### 3. Branch & workspace

```bash
git checkout main && git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading (REQUIRED)

Read **in this order** before any analysis:

1. `docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md` — full today's debrief. §A2 + §C12 are the primary targets.
2. `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md` — yesterday's triage (C4 stop-retry, C11 non-network trigger analysis).
3. `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` — Monday's triage (baseline cascade pattern).
4. `CLAUDE.md` — DEF-199 (closed), DEF-204 (new, open), DEF-196 (stop-retry, different family), DEF-158 (dup-SELL prevention — relevant because today's IMSR 200-vs-100 evidence).
5. `argus/execution/order_manager.py` — focus on reconciliation paths, bracket-leg accounting, partial-fill handling.

## Objective

Produce a mechanism diagnostic report for the A2/C12 cascade. For each
candidate mechanism, record:

- **Hypothesis** (one-line description of the proposed mechanism)
- **Code paths implicated** (specific file:line references)
- **Evidence from today's log** (grep output, line numbers, timestamps)
- **Consistency score** (how well does this mechanism explain the 44-symbol, 14,249-share, gradual-drift pattern?)
- **Verdict** (LIKELY / PARTIAL / UNLIKELY / DISPROVEN)

End with a ranked list of the most likely mechanisms + a recommendation for
which to prioritize investigation in `post-31.9-reconciliation-drift`.

Do NOT modify production code, tests, or configs. Do NOT attempt a fix.
Do NOT open new DEFs unless a new, unrelated issue surfaces in the course
of investigation (in which case it gets its own DEF number).

## Requirements

### Requirement 1: Hypothesis enumeration

Generate at minimum the following candidate hypotheses and evaluate each:

1. **Partial-position bracket-leg accounting drift** (initial hypothesis from Apr 24 §A2). Evidence anchor: IMSR 200-vs-100 flatten-qty mismatch at 16:17 UTC. Proposed mechanism: ARGUS tracks full bracket target/stop quantities but broker fills partial, producing a gradual delta.
2. **Silent reconciliation re-harmonization** where `reconcile_positions()` treats an unexpected short as "true state" and adopts it rather than flagging it.
3. **Stop fill + late order cancel race** where the stop fills (closing the position), then the cancel-stop + resubmit sequence re-opens the order, filling AGAIN in the wrong direction.
4. **Bracket target leg firing after position closed** — the debrief noted 6 orphan WARNINGs today; verify those are all the same symbol or distributed, and whether orphan-fill-classification is missing some cases.
5. **Manual flatten path with stale qty** — the `_flatten_pending` retry logic in IMPROMPTU-CI + Sprint 29.5 hardening may not have caught all stale-qty paths.
6. **Scanner re-entry on symbols with open shorts** — ARGUS scanner doesn't check short-flag, opens long, "long" leg actually closes the unexpected short, new long fills are correctly accounted but the underlying short from hours earlier was never detected.

Add additional hypotheses as code inspection suggests them.

### Requirement 2: Evidence collection discipline

For each hypothesis, collect grep evidence from today's log:

```bash
# Examples of diagnostic greps:
grep -n "IMSR" logs/argus_20260424.jsonl | head -50
grep -n "reconciliation.*mismatch" logs/argus_20260424.jsonl | head -30
grep -n "fill for .* but no matching position" logs/argus_20260424.jsonl
grep -n "position_opened.*side.*SHORT" logs/argus_20260424.jsonl | head
# Etc.
```

Every hypothesis conclusion must be backed by concrete grep output or a
specific code-path trace. "This feels like X" is inadmissible — either the
evidence is in the log or it isn't.

### Requirement 3: Mechanism signature analysis

The debrief established that the cascade grew gradually 3 → 5 → 7 → 44 across
~6 hours. A correct hypothesis must explain:

- **Why gradual**, not single-event (rules out any reconnect-triggered snapshot)
- **Why 44 symbols**, not a single symbol compounding
- **Why ~325 shares/symbol average** (14,249 / 44)
- **Why only 4/44 overlap with DEC-372 stop-retry** (rules out that as primary driver)
- **Why no orphan-fill WARNINGs for 38 of the 44 symbols** (rules out bracket-leg orphan path as primary)

A hypothesis that can't explain all five must be partial at best.

### Requirement 4: Cross-reference IMSR evidence

IMSR is the **forensic anchor**. The debrief captured `Flatten qty mismatch for
IMSR: ARGUS=200, IBKR=100 — using IBKR qty` at 16:17 UTC. This is DEF-158
dup-SELL prevention working correctly — but it's also evidence that ARGUS
thought it held 200 shares of IMSR when the broker showed 100. That 100-share
delta is exactly the kind of drift that could accumulate into today's 44-symbol
cascade if it happens 44 times across the session without every instance being
caught by DEF-158.

Trace IMSR's full position lifecycle through today's log:
- First position_opened
- All fills
- All reconciliation events
- Cancel/resubmit paths for brackets
- The 16:17 flatten-qty mismatch
- The final EOD state

Use IMSR as the detailed case study. If the mechanism is bracket-leg drift,
IMSR should show it clearly.

### Requirement 5: Top-3 ranking + prioritization recommendation

End the report with a Top-3 ranking of most-likely mechanisms, scored by how
well they explain all five required patterns (§Requirement 3). For the #1
mechanism, produce a brief "what fix would look like" paragraph (not an
implementation — a direction) for `post-31.9-reconciliation-drift` scoping.

### Requirement 6: P26 candidate capture

At the end of the report, add a **§Retrospective Candidate** section noting:

> **P26 candidate (for next campaign's RETRO-FOLD):** When validating a fix
> against a recurring symptom, verify against the mechanism signature (e.g.,
> 2.00× doubling ratio), not the symptom aggregate (e.g., "shorts at EOD").
> Yesterday's 2.00× math was the correct discriminator; without it, today's
> 44-symbol cascade would have been misattributed to DEF-199 regression and
> IMPROMPTU-04 would have been incorrectly reopened. Origin: Apr 24 debrief
> validation moment. Generalization: any fix-validation session should
> explicitly identify the mechanism signature before running the validation.

SPRINT-CLOSE will pick this up and route to the next campaign's RETRO-FOLD.

## Constraints

- DO NOT modify any argus code, tests, or configs
- DO NOT attempt to fix DEF-204 — the fix is scoped to `post-31.9-reconciliation-drift`
- DO NOT re-run paper session, pattern sweeps, or backtests
- DO NOT modify the Apr 22 / Apr 23 / Apr 24 debrief documents
- DO NOT modify `workflow/` submodule (RULE-018)
- Work on `main`

## Test Targets

- No new tests (read-only session)
- Full pytest suite run at close-out as sanity check (same baseline as post-IMPROMPTU-10: 5,080 pytest)

## Definition of Done

- [ ] Mechanism diagnostic at `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`
- [ ] Minimum 6 hypotheses evaluated (from §R1) + any additional emergent
- [ ] IMSR detailed case-study section present
- [ ] Each hypothesis has concrete grep evidence or coded-path trace
- [ ] Top-3 ranking with "what fix would look like" paragraph for #1
- [ ] §Retrospective Candidate with P26 note
- [ ] CLAUDE.md DEF-204 entry updated with mechanism findings (stays OPEN)
- [ ] `RUNNING-REGISTER.md` IMPROMPTU-11 row complete
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` Stage 9C IMPROMPTU-11 row → CLEAR
- [ ] No production code modified (`git diff argus/` empty)
- [ ] Close-out at `docs/sprints/sprint-31.9/IMPROMPTU-11-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-11-review.md`

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Minimum 6 hypotheses evaluated | Count sections in report |
| Each hypothesis has concrete evidence | Per-section read |
| IMSR case study present | Dedicated section |
| Top-3 ranking present | §Summary ranking |
| P26 retrospective candidate present | §Retrospective Candidate |
| No argus/ code modified | `git diff argus/` empty |
| No config/ modified | `git diff config/` empty |
| No tests/ modified | `git diff tests/` empty |
| Full pytest suite still passes | 5,080 pytest |

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke after close-out. Provide:
1. This kickoff
2. Close-out path: `docs/sprints/sprint-31.9/IMPROMPTU-11-closeout.md`
3. Diagnostic report path: `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`
4. Diff range
5. Files that should NOT have been modified:
   - Any `argus/` code file
   - Any `config/` file
   - Any `tests/` file
   - The Apr 22 / Apr 23 / Apr 24 debrief triage documents
   - Any `workflow/` submodule file

## Session-Specific Review Focus (for @reviewer)

1. **Verify read-only discipline.** `git diff` should show only: IMPROMPTU-11 report (new), CLAUDE.md DEF-204 refinement, RUNNING-REGISTER, CAMPAIGN-COMPLETENESS-TRACKER. Any other modified file is an escalation.
2. **Verify each hypothesis has concrete evidence.** A hypothesis marked "LIKELY" without a grep output or code-path trace is inadmissible.
3. **Verify IMSR case study.** The forensic anchor from Apr 24 debrief §A2 must be a dedicated trace, not a passing mention.
4. **Verify Top-3 ranking is defensible.** The #1 mechanism's "consistency score" must explain all five patterns from §R3.
5. **Verify P26 candidate is captured** with Origin citation + generalization.
6. **Verify no fix attempt.** This is diagnostic-only. Any code change = escalation.

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = 0
- Vitest count unchanged
- No scope boundary violation
- CLAUDE.md DEF-204 refinement (not closure) present

## Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- Any argus/ or tests/ or config/ file modified
- DEF-204 marked closed (should remain OPEN — fix deferred to post-31.9)
- DEF-199 reopened (today's debrief proved it's working — don't regress this conclusion)
- Any debrief triage doc modified
- Fewer than 6 hypotheses evaluated
- No IMSR case study
- No P26 retrospective candidate
- Full pytest suite broken

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Top-3 mechanisms** (ranked by consistency)
4. **Recommended fix direction** for `post-31.9-reconciliation-drift`
5. One-line summary: `IMPROMPTU-11 complete. Close-out: {verdict}. Review: {verdict}. Top mechanism: {name}. Fix routed to post-31.9-reconciliation-drift. Commits: {SHAs}. Report: docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md.`

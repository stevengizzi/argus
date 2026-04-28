# Sprint 31.91 — Tier 3 #2 Disposition Execution Runbook

> **Audience:** Operator (Steven). Step-by-step for executing the Tier 3 #2 amended verdict's disposition: workflow-metarepo amendment, ARGUS pre-impromptu doc-sync, then back into the Work Journal conversation for Impromptu A.
>
> **Generated:** 2026-04-28, alongside the amended Tier 3 #2 verdict + the two Claude Code prompts.
>
> **Total wall-clock estimate:** 30–60 minutes operator time, plus Claude Code execution time per prompt (~5–15 minutes each).

---

## Prerequisites

Confirm the following before beginning:

- [ ] You are between Work Journal sessions (no active Claude Code session running).
- [ ] No uncommitted changes in either repo:
  ```bash
  cd /path/to/argus && git status
  cd /path/to/claude-workflow && git status
  ```
- [ ] Both repos are on `main` and up-to-date with `origin/main`:
  ```bash
  cd /path/to/argus && git pull --ff-only
  cd /path/to/claude-workflow && git pull --ff-only
  ```
- [ ] The Tier 3 #2 conversation (this Claude.ai conversation) is still accessible if you need to refer back.
- [ ] You have ALL FOUR generated artifacts in hand:
  1. **`tier-3-review-2-verdict-AMENDED.md`** — the amended verdict (replaces existing verdict in repo)
  2. **`workflow-protocol-amendment-prompt.md`** — Claude Code prompt #1 (run first)
  3. **`pre-impromptu-doc-sync-prompt.md`** — Claude Code prompt #2 (run second)
  4. **This runbook** — your reference

---

## Step 1 — Land the amended Tier 3 #2 verdict in the ARGUS repo

This is a manual, one-file operation, NOT a Claude Code prompt. It's small and surgical enough that running it through Claude Code would be overkill.

```bash
cd /path/to/argus
cp /path/to/tier-3-review-2-verdict-AMENDED.md \
   docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md
git add docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md
git commit -m "docs(sprint-31.91): amend Tier 3 #2 verdict per operator disposition

Routes DEF-217/218/219/220/221/223/224/225 as RESOLVED-IN-SPRINT
(Impromptus A+B+C + Session 5c) instead of cross-sprint deferrals.
Defers DEC-388 materialization from Tier 3 #2 to sprint-close so the
DEC documents the architecture AFTER Impromptu C resolves the
cross-referenced DEFs. Tightens Session 5c entry condition to require
Impromptus A and B landed CLEAR. References workflow v1.3.0
amendments (mid-sprint doc-sync coordination + structural anchors)
landing in this disposition cycle.

Carry-forward map reduced to genuine cross-sprint items only:
DEF-222 (gated by future producers), DEF-175 (existing
post-31.9-component-ownership scope, annotated), workflow protocol
amendment (separate metarepo flow).
"
git push origin main
```

**Verify:**
```bash
git log -1 --stat docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md
```

The amended verdict is now on `main`. Proceed to Step 2.

---

## Step 2 — Run the workflow-metarepo amendment prompt

This bumps the metarepo to workflow v1.3.0 with two amendments: structural-anchor requirement for impl prompts, and the new `protocols/mid-sprint-doc-sync.md` protocol formalizing the multi-sync coordination pattern.

**Why this runs FIRST (before ARGUS pre-sync):** the 3 new impromptu impl prompts (Impromptu A, B, C) and the amended S5c prompt are all written in the new structural-anchor format defined by this metarepo amendment. If ARGUS pre-sync runs first, the impl prompts will reference a format the metarepo doesn't yet document — auditable but awkward.

### Execution

1. Open a new Claude Code session against the `claude-workflow` repo:
   ```bash
   cd /path/to/claude-workflow
   claude
   ```

2. Paste the contents of `workflow-protocol-amendment-prompt.md` into the Claude Code session.

3. Claude Code will:
   - Clone fresh / verify clean state
   - Apply ~10 file edits across protocols/, templates/, schemas/, bootstrap-index.md
   - Create the new `protocols/mid-sprint-doc-sync.md` file
   - Bump version markers (1.2.0 → 1.3.0) in headers of touched files
   - Commit the changes with a structured message
   - Run any verification (e.g., bootstrap-index Protocol Index table reconciliation)

### Verification

After the Claude Code session completes:

```bash
cd /path/to/claude-workflow
git log -1 --stat
```

Expected: a single commit (or 2-3 logical commits) touching:
- NEW: `protocols/mid-sprint-doc-sync.md`
- MODIFIED: `bootstrap-index.md`, `protocols/sprint-planning.md`, `protocols/in-flight-triage.md`, `protocols/tier-3-review.md`, `protocols/impromptu-triage.md`, `templates/doc-sync-automation-prompt.md`, `templates/work-journal-closeout.md`, `templates/implementation-prompt.md`, `schemas/structured-closeout-schema.md`

```bash
grep -l "workflow-version: 1.3.0" .
```

Expected: every file with a `workflow-version` header now shows 1.3.0.

```bash
grep -E "mid-sprint-doc-sync\.md" bootstrap-index.md
```

Expected: at least 2 hits (Protocol Index table + Conversation Type → What to Read section).

### Push

```bash
git push origin main
```

The metarepo is now at v1.3.0 with both amendments live. Proceed to Step 3.

### Failure recovery

If the workflow amendment Claude Code session fails partway through:
- Use `git status` + `git diff` to inspect partial state.
- If the failure is in a single file edit, manually finish that file and `git add` it; let the next session continue.
- If multiple files are inconsistent, `git checkout .` to discard, then re-run the prompt from scratch.
- The amendment prompt is idempotent — running it twice on a clean repo produces the same result.
- Do NOT proceed to Step 3 until the metarepo is on v1.3.0; the ARGUS pre-sync depends on it.

---

## Step 3 — Run the ARGUS pre-impromptu doc-sync prompt

This is the largest of the prompts. It produces ~12 file edits in the ARGUS repo, including 3 new impl prompt files, the amended S5c impl prompt, the pre-impromptu doc-sync manifest, the work-journal-handoff document, and updates to CLAUDE.md / work-journal-register.md / sprint-spec.md.

### Execution

1. Open a new Claude Code session against the ARGUS repo:
   ```bash
   cd /path/to/argus
   claude
   ```

2. Paste the contents of `pre-impromptu-doc-sync-prompt.md` into the Claude Code session.

3. Claude Code will:
   - Verify clean state on `main` at HEAD `<latest>` (post-Tier-3-#2-amendment commit).
   - Read the amended Tier 3 #2 verdict to confirm starting state.
   - Apply 9 new DEF rows to CLAUDE.md (status: OPEN-with-routing).
   - Update work-journal-register.md (session order, DEF table, watchlist, DEC reservations).
   - Amend sprint-spec.md (D15 + D16 + AC blocks + D9b policy table extension).
   - Annotate DEF-175 in CLAUDE.md with main.py exceptions + set_order_manager motivators.
   - CREATE: `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-a-alert-hardening-impl.md`
   - CREATE: `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-b-databento-heartbeat-impl.md`
   - CREATE: `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-c-migration-framework-sweep-impl.md`
   - MODIFY: `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md` (add DEF-220 disposition).
   - CREATE: `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` (mechanical handoff to sprint-close).
   - CREATE: `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md` (narrative handoff to Work Journal conversation).
   - Commit in 1-3 logical groupings.

### Verification

After the Claude Code session completes:

```bash
cd /path/to/argus
git log --oneline -5
```

Expected: 1-3 new commits since the Tier 3 #2 verdict amendment, with messages like "docs(sprint-31.91): pre-impromptu doc-sync — Tier 3 #2 disposition" and possibly "feat(sprint-31.91): impromptu A/B/C impl prompts (workflow v1.3.0)".

```bash
ls docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-*-impl.md
```

Expected: 3 files (Impromptu A, B, C).

```bash
ls docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md
ls docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md
```

Expected: both files exist.

```bash
grep -E "DEF-21[7-9]|DEF-22[0-5]" CLAUDE.md
```

Expected: 9 hits (one per new DEF), each with status="OPEN" and a routing tag like "Impromptu A" / "Impromptu B" / "Session 5c" / "Impromptu C" / "DEFERRED".

```bash
grep "Impromptu A\|Impromptu B\|Impromptu C" docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
```

Expected: rows in the Session Order table for each impromptu in the correct positions.

```bash
git diff HEAD~3..HEAD --stat
```

Expected: the cumulative diff shows ~12 files touched, no unexpected files.

### Push

```bash
git push origin main
```

The ARGUS repo is now in pre-impromptu state. The 3 impl prompts are ready for the Work Journal to consume. Proceed to Step 4.

### Failure recovery

If the ARGUS pre-sync Claude Code session fails partway through:
- Use `git status` + `git diff` to inspect partial state.
- The prompt is structured to fail-stop on any verification mismatch (e.g., expected file content not found at structural anchor) — it should NOT leave the repo in an inconsistent state.
- If a partial commit landed, `git revert <sha>` (do NOT `git reset --hard` — the commit is already shared expectation).
- Re-run the prompt; it's idempotent for the un-applied portions.

---

## Step 4 — Switch back to the Work Journal conversation

The Work Journal conversation is the operating context for Sprint 31.91. After the pre-sync lands, return to it.

### What to paste into the Work Journal

The work-journal-handoff document at `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md` is designed as a self-contained primer for the Work Journal conversation. Paste its contents (or just its summary section) as your first message to the Work Journal conversation.

The handoff includes:
- What changed since the last register refresh (post-S5b, commit `07070e2`).
- New session order (Impromptu A → Impromptu B → S5c → Impromptu C → S5d → S5e → close).
- Updated state of work-journal-register.md (which is now authoritative on disk).
- File map: where every relevant artifact now lives.
- Sprint-close coordination: how the manifest is consumed at sprint-close.
- Cross-references to: this Tier 3 #2 conversation, the amended verdict, the workflow-metarepo amendment.

### What to do next in the Work Journal

The Work Journal will, in order:

1. Acknowledge the handoff context.
2. Confirm the pre-impromptu doc-sync landed and the manifest is in place.
3. Refresh its register-of-record by reading the on-disk `work-journal-register.md` (now updated by the pre-sync).
4. Begin Impromptu A:
   - Read the impl prompt at `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-a-alert-hardening-impl.md`
   - Spawn a fresh Claude Code session for the implementer
   - Hand the impl prompt to the implementer
5. After Impromptu A's Tier 2 inline review CLEAR: refresh register, proceed to Impromptu B.
6. Continue through the new session order.

### Sprint-close coordination (forward-looking)

When Impromptu A through S5e have all landed CLEAR, the Work Journal triggers sprint-close. The sprint-close doc-sync (which uses the standard `templates/doc-sync-automation-prompt.md` template, now augmented per workflow v1.3.0 to read mid-sprint manifests) will:

1. Read `pre-impromptu-doc-sync-manifest.md` to learn what transitions are owed.
2. Transition DEF-217 through DEF-225 from OPEN to RESOLVED status in CLAUDE.md (with sprint+session attribution).
3. Mark DEF-014 as fully CLOSED.
4. Mark DEF-213 + DEF-214 as RESOLVED (already verified by pre-sync, transitioned at sprint-close).
5. Write DEC-385 to `decision-log.md` with full text from the Tier 3 #1 verdict + S2d closeout.
6. Write DEC-388 to `decision-log.md` with the draft text from the amended Tier 3 #2 verdict.
7. Refresh CLAUDE.md test count baseline (currently cites 5,080; post-sprint will be 5,232+ depending on impromptu test deltas).
8. Update sprint-history.md with Sprint 31.91 entry covering all sessions + impromptus + Tier 3 reviews.
9. Update architecture.md with final alert observability section + migration framework adoption note.
10. Verify pre-live-transition-checklist.md reflects DEF-217 + DEF-221 RESOLVED status.

The sprint-close prompt is generated by the Work Journal at sprint-close time (not pre-generated here) because it depends on the actual session deltas at that point.

---

## Step 5 (final) — Confirm both repos are in expected state

After Step 4 completes (Work Journal acknowledges handoff and is ready to begin Impromptu A), do a final sanity check:

```bash
cd /path/to/claude-workflow && git log -1 --oneline
# Expected: commit at v1.3.0 amendment

cd /path/to/argus && git log -3 --oneline
# Expected: (1) Tier 3 #2 verdict amendment, (2) pre-impromptu doc-sync, possibly (3) impl prompts as separate commit
```

Both repos are now at the correct state for Sprint 31.91 to proceed via the new flow.

---

## Quick-reference: where everything lives

| Artifact | Location |
|---|---|
| Amended Tier 3 #2 verdict | `argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` |
| Pre-impromptu doc-sync manifest | `argus/docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` |
| Work-journal-handoff document | `argus/docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md` |
| Impromptu A impl prompt | `argus/docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-a-alert-hardening-impl.md` |
| Impromptu B impl prompt | `argus/docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-b-databento-heartbeat-impl.md` |
| Impromptu C impl prompt | `argus/docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-c-migration-framework-sweep-impl.md` |
| Amended S5c impl prompt | `argus/docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md` |
| Updated work-journal-register | `argus/docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` |
| Updated CLAUDE.md (DEF table) | `argus/CLAUDE.md` |
| Updated sprint-spec.md | `argus/docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` |
| New `mid-sprint-doc-sync.md` protocol | `claude-workflow/protocols/mid-sprint-doc-sync.md` |
| Updated workflow protocols | `claude-workflow/protocols/{sprint-planning,in-flight-triage,tier-3-review,impromptu-triage}.md` |
| Updated workflow templates | `claude-workflow/templates/{implementation-prompt,doc-sync-automation-prompt,work-journal-closeout}.md` |

---

## When to escalate (if something goes unexpectedly wrong)

- **Step 1 (verdict commit):** Trivial; if it fails, re-do manually. No escalation needed.
- **Step 2 (workflow amendment):** If multiple verification commands fail or files are inconsistent, do NOT proceed to Step 3. The metarepo is shared infrastructure; partial state is bad. Stash the partial state for inspection (`git stash`), reset, and re-run.
- **Step 3 (ARGUS pre-sync):** If the pre-sync produces unexpected files or unexpected content, the manifest will be wrong, which will break sprint-close. Stop and inspect. The ARGUS repo's state must match the manifest's claims.
- **Step 4 (Work Journal handoff):** If the Work Journal can't reconcile its understanding of the register with the on-disk register, paste the handoff document content directly and explicitly tell the Work Journal "the on-disk register is authoritative."
- **Sprint-close (eventual):** If the sprint-close doc-sync prompt cannot find or parse the manifest, that's a workflow protocol violation — escalate to a Tier 3 #3 review of the multi-sync coordination protocol.

---

*Runbook generated 2026-04-28 alongside Tier 3 #2 amended verdict.*
*Companion artifacts: `tier-3-review-2-verdict-AMENDED.md`, `workflow-protocol-amendment-prompt.md`, `pre-impromptu-doc-sync-prompt.md`.*

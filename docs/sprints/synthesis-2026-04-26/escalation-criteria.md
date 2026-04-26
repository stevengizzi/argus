# Sprint synthesis-2026-04-26: Sprint-Level Escalation Criteria

> Tier 2 reviewer (the @reviewer subagent invoked at session close) decides whether a session's verdict is **CLEAR**, **CONCERNS**, or **ESCALATE**. This document defines the conditions under which the verdict MUST be ESCALATE rather than CONCERNS.
>
> Escalation routes the issue to operator (Steven) for judgment rather than allowing in-session auto-fix. Use ESCALATE when the failure mode is structural (touches sealed content, defeats the sprint's purpose, violates a hard kickoff constraint) — not for surface-level quality issues that can be resolved within the session via the @reviewer's CONCERNS feedback loop.

---

## Escalation Triggers — must produce ESCALATE verdict

### Category A: Hard constraint violations (kickoff-mandated)

#### A1. ARGUS runtime code, tests, or configuration modified

**Detection:** Any commit in this sprint touches a path under `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`.

**Verification:**
```bash
git log <session-start-sha>..HEAD -- argus/argus/ argus/tests/ argus/config/ argus/scripts/
```
Should return empty. Non-empty result is an immediate escalation.

**Why escalate:** The kickoff explicitly excluded ARGUS runtime work from this sprint. The constraint is operator-set, not @reviewer-overridable. Even if the change "looks safe," it requires operator judgment about whether to absorb it (extending sprint scope) or revert it.

**Operator action after escalation:** Decide whether to: (a) revert the change in a fix commit, (b) extend the sprint scope to include the change with explicit acceptance and updated regression tests, or (c) split the change into a separate ARGUS-side impromptu sprint.

---

#### A2. Evolution-note body modified

**Detection:** `git diff <session-start-sha>..HEAD -- workflow/evolution-notes/2026-04-21-*.md` shows changes to lines below the metadata block (the body content).

**Verification:** For each evolution note, the diff must contain ONLY the additive `**Synthesis status:**` line in the metadata block. Any change to a body line — including whitespace-only changes, typo "fixes," or Markdown formatting normalizations — escalates.

**Why escalate:** The 3 evolution notes are the audit trail. The kickoff explicitly preserves their bodies. If the @reviewer detects body changes, the session's diff cannot be safely landed without operator review.

**Operator action:** Verify whether the body change was accidental (revert) or intentional (operator decides whether the audit-trail-modification cost is justified).

---

#### A3. RETRO-FOLD content semantically regressed

**Detection:** `git diff <session-start-sha>..HEAD -- workflow/claude/rules/universal.md` shows changes to RULE-038 through RULE-050 bodies that are not the explicitly-permitted RULE-038 5th sub-bullet addition.

**Verification:**
- Pre-sprint state: RULE-038 has 4 sub-bullets; RULEs 039–050 are byte-for-byte preserved.
- Post-Session-1 state: RULE-038 has 5 sub-bullets (the new sub-bullet is the only addition); RULEs 039–050 are byte-for-byte unchanged; new RULEs 051–053 appended in new sections after RULE-050.
- Post-Sessions-2–6: same as post-Session-1 for the universal.md content.

**Why escalate:** RETRO-FOLD's P1–P25 synthesis is sealed by `RETRO-FOLD-closeout.md` and metarepo commit `63be1b6`. The kickoff explicitly forbids re-derivation. Any semantic change requires operator authorization.

**Operator action:** Verify whether the change is a wording fix (low-stakes; operator may approve in-place), a semantic change (escalates further to "should we open a strategic check-in to revisit RETRO-FOLD?"), or accidental (revert).

---

### Category B: Sprint-level structural failures

#### B1. Keystone Pre-Flight wiring missing or advisory

**Detection:** After Session 1 close-out, `templates/implementation-prompt.md` Pre-Flight Checks section does NOT contain a step explicitly reading `.claude/rules/universal.md`, OR the step's wording is advisory ("you may," "consider," "if helpful") rather than imperative ("read," "treat as binding for this session").

**Verification:**
```bash
grep -A5 "Pre-Flight Checks" workflow/templates/implementation-prompt.md | grep -E "(read .claude/rules/universal\.md|.claude/rules/universal\.md.*binding)"
```
Must return ≥ 1 line with imperative phrasing. Same check for `templates/review-prompt.md`.

**Why escalate:** The keystone Pre-Flight wiring is the single highest-leverage edit in the sprint. Without it, RETRO-FOLD's P1–P25 RULE coverage remains weakly wired (only RULE-039 is inline-cited from a template) and every new RULE in this sprint has the same problem. Missing or advisory phrasing is sprint failure.

**Operator action:** Verify the keystone is present + imperative; if missing, Session 1 must be redone (cannot proceed to Session 2+ without it stable).

---

#### B2. Bootstrap routing miss

**Detection:** A new protocol file (`campaign-orchestration.md` or `operational-debrief.md`) is committed but `bootstrap-index.md` does not have:
- A "Conversation Type → What to Read" entry pointing at the new protocol, AND
- A row in the Protocol Index table

OR a new template file (`stage-flow.md` or `scoping-session-prompt.md`) is committed but `bootstrap-index.md` Template Index does not have a row for it.

**Verification:**
- After Session 3: `grep -i "campaign.orchestration\|campaign.absorption" workflow/bootstrap-index.md` must return matches in BOTH the "Conversation Type → What to Read" section AND the Protocol Index table.
- After Session 4: same for `operational-debrief`.
- After Session 5: `grep "stage-flow\|scoping-session" workflow/bootstrap-index.md` must return matches in the Template Index table.

**Why escalate:** A new protocol without a routing entry is a sit-there doc — exactly the failure mode this sprint is designed to prevent. Per the auto-effect principle (Phase A pushback round 1), unrouted protocols defeat the sprint's purpose.

**Operator action:** Add the missing routing entry as a follow-on commit in the same session, OR escalate to a separate "bootstrap-index sweep" session if multiple entries are missing.

---

#### B3. Safety-tag taxonomy reintroduced

**Detection:** Any new metarepo content (in any session, any file) contains a 4-tag safety taxonomy (`safe-during-trading` / `weekend-only` / `read-only-no-fix-needed` / `deferred-to-defs`) or its core+modifier expansion as a *recommended* mechanism — rather than as a *rejected pattern* documented in `codebase-health-audit.md` Phase 2's `### Anti-pattern (do not reinvent)` addendum.

**Verification:** For each session, search the new content:
```bash
grep -E "(safe-during-trading|weekend-only|read-only-no-fix-needed|deferred-to-defs)" workflow/protocols/*.md workflow/templates/*.md workflow/claude/skills/*.md workflow/scripts/*.py
```
Acceptable matches: ONLY in the rejected-pattern addendum section of `codebase-health-audit.md` Phase 2 (with explicit framing: "do not reinvent," "empirically overruled," etc.). Any other location is escalation.

**Why escalate:** The safety-tag rejection was an explicit operator decision in Phase A pushback round 2, based on Sprint 31.9 execution evidence. Reintroduction would silently undo that decision and propagate a pattern that didn't earn its load-bearing role.

**Operator action:** Remove the reintroduced content; verify the rejected-pattern addendum is correctly framed; if the reintroduction was the @reviewer noticing an "obvious gap," escalate further to operator review of whether the rejection should actually be revisited (very unlikely outcome but theoretically possible).

---

#### B4. F1–F10 finding not addressed

**Detection:** Session 6 close-out does NOT enumerate which file/section addresses each F# finding from the synthetic-stakeholder pass, OR a Tier 2 review of any session detects ARGUS-specific terminology in new metarepo content that is not contextually framed (e.g., "trading session" used universally, "DEF" used universally, "Work Journal conversation" used universally without "or equivalent coordination surface").

**Verification:**
- Session 6 close-out must contain a table mapping F1–F10 to their addressing file/section.
- Session 6 Tier 2 review must include a focus item: "verify generalized terminology coverage."
- Any session's diff that introduces new ARGUS-specific terminology without contextual framing escalates.

**Why escalate:** The F1–F10 findings were first-class deliverables (deliverable 14 in the sprint spec). Missing coverage means the synthetic-stakeholder pass was wasted work and the new protocols ship as ARGUS-specific despite the design intent.

**Operator action:** Verify which F# findings are missed; either fix them in a follow-on commit within Session 6, or split into a "F1–F10 generalized-terminology pass" follow-on session.

---

### Category C: Acceptance/quality failures

#### C1. Workflow-version regression

**Detection:** Any modified file's `<!-- workflow-version: X.Y.Z -->` header is bumped DOWNWARD, OR `protocols/codebase-health-audit.md` is modified in Session 6 but not bumped to 2.0.0, OR a new file lacks a workflow-version header.

**Verification:**
```bash
for f in $(git diff --name-only <session-start-sha>..HEAD -- workflow/); do
    pre=$(git show <session-start-sha>:$f 2>/dev/null | grep "workflow-version" | head -1)
    post=$(git show HEAD:$f | grep "workflow-version" | head -1)
    echo "$f: pre=$pre post=$post"
done
```
Manually verify each file's version monotonically advances; new files have `1.0.0`.

**Why escalate:** Versions are how downstream consumers detect protocol changes. A regression breaks that signal. `codebase-health-audit.md` specifically must reach 2.0.0 because the Phase 2/3 expansion materially changes the protocol's scope.

**Operator action:** Bump versions correctly in a follow-on commit; verify monotonic advancement.

---

#### C2. `phase-2-validate.py` invocation phrased advisorially

**Detection:** `protocols/codebase-health-audit.md` Phase 2 references `scripts/phase-2-validate.py` but the wording is advisory ("you may run...", "consider running...", "the validator can be run...") rather than imperative gate-language ("Phase 2 cannot complete until phase-2-validate.py exits zero," "before proceeding to Phase 3, run...").

**Verification:**
```bash
grep -B2 -A5 "phase-2-validate" workflow/protocols/codebase-health-audit.md
```
The surrounding wording must be imperative. Advisory phrasing escalates.

**Why escalate:** A validator invoked advisorially is not a gate — it's a suggestion. The whole point of `scripts/phase-2-validate.py` is to make CSV integrity non-bypassable. Advisory phrasing converts a structural defense into operator-memory-dependent guidance, defeating the auto-effect goal.

**Operator action:** Rewrite the wording as imperative; verify by re-grep.

---

#### C3. Compaction-driven regression detected by Tier 2

**Detection:** During Tier 2 review of any session, the @reviewer detects evidence that the implementer's context was compacted mid-session (incomplete edits, contradictory changes within the same file, references to non-existent files, repeated stub content, or any other signal that internal session state was lost). This is distinct from "the implementer made a mistake" — it's specifically the compaction failure mode.

**Verification:** Judgment-based. The @reviewer's review report should explicitly note compaction signals if detected.

**Why escalate:** Compaction-driven regressions can cascade in non-obvious ways. A fresh session is the only reliable remediation. Continuing the same session risks compounding the problem.

**Operator action:** Discard the session's commits; restart the session in a fresh Claude Code conversation with the same prompt + the close-out from the failed attempt as context.

---

#### C4. Forward-dependency unresolved by Session 5 close-out

**Detection:** Session 3's `protocols/impromptu-triage.md` extension references `templates/scoping-session-prompt.md`, which is created in Session 5. After Session 5 close-out, the file path referenced in `impromptu-triage.md` does NOT resolve to an actual file in the repo.

**Verification:**
```bash
grep -oE "templates/scoping-session-prompt\.md" workflow/protocols/impromptu-triage.md
ls workflow/templates/scoping-session-prompt.md
```
Both must succeed.

**Why escalate:** A forward-reference that never resolves is a broken-link bug. Pattern (a) was operator-approved with the understanding that Session 5 closes the loop. If Session 5 fails to close it, the impromptu-triage extension has a dead reference until a follow-on commit lands.

**Operator action:** Either create the missing file (if Session 5's scope was incomplete) or redact the reference from impromptu-triage.md (if the scope was correctly Session 5 but the file got dropped).

---

### Category D: Process failures

#### D1. Session 0 not landed before Session 1 begins

**Detection:** Session 1 implementation prompt is invoked, but `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` does not contain P28+P29 entries.

**Verification:** Session 1 pre-flight should grep for P28/P29 in SUMMARY.md and halt if not found.

**Why escalate:** Session 1+ reference the synthesis input set as stable. If P28+P29 aren't in SUMMARY.md, the inputs are not stable; metarepo work would land citing artifacts that don't yet exist on the argus side.

**Operator action:** Halt Session 1; complete Session 0 first; then resume.

---

#### D2. Tier 2 reviewer cannot determine acceptance gate state

**Detection:** A session's close-out claims COMPLETE but the @reviewer cannot verify acceptance gates (e.g., the close-out doesn't include the grep results, the diff is malformed, the close-out is missing).

**Verification:** Each session's close-out must contain explicit verification commands + their outputs. Missing or unverifiable outputs escalate.

**Why escalate:** Without verifiable gates, the @reviewer cannot produce a defensible verdict. CONCERNS would be paper-only; ESCALATE forces operator to actually verify.

**Operator action:** Verify each gate manually; produce a corrected close-out; re-run @reviewer.

---

#### D3. Sprint scope creep beyond the 18 OUT items

**Detection:** Any session's diff touches a file or introduces a feature that is explicitly listed in `spec-by-contradiction.md` §"Out of Scope" or §"Do NOT modify."

**Verification:** Each Tier 2 review must include a "scope-boundary check": cross-reference the diff against the OUT list. Any match escalates.

**Why escalate:** Scope discipline is operator-set in spec-by-contradiction. Even seemingly-helpful additions (e.g., "while I was here, I cleaned up the heading hierarchy in `codebase-health-audit.md`") require operator authorization. The kickoff explicitly excluded restructurings, and the spec listed 18 OUT items deliberately.

**Operator action:** Either revert the out-of-scope change or extend the sprint scope explicitly with updated regression tests and an addendum to the spec.

---

## What does NOT escalate (Tier 2 resolves via CONCERNS)

The following are CONCERNS-level issues. The @reviewer notes them in the review report; the implementer fixes them within the same session via the post-review-fix loop:

- **Markdown formatting inconsistencies** (table alignment, heading-level drift within a section, inline-code vs fenced-code style). Minor cosmetic; fix in-session.
- **Origin footnote wording variance** (citing "Sprint 31.9 retro" vs "synthesis-2026-04-26 evolution note 1" — both are acceptable as long as the citation is unambiguous). Style-level; fix only if ambiguous.
- **Cross-reference path typos** (linking to `protocols/campaign-orhestration.md` instead of `campaign-orchestration.md`). Fixable; flag in CONCERNS.
- **Missing one example in a multi-example section** (e.g., the fingerprint pattern has 2 non-trading examples instead of the F5-required 3). CONCERNS unless ALL non-trading examples are missing (which would be an F5 failure → escalates per B4).
- **Imprecise wording** ("the operator should..." vs "the operator must...") that doesn't change semantic intent. Style.
- **Section ordering within a new file** (e.g., placing the appendix before the decision matrix). Re-order in CONCERNS.
- **Workflow-version bump correctness when ambiguous** (e.g., is `templates/implementation-prompt.md` getting a 1.2.0 → 1.2.1 patch bump or 1.2.0 → 1.3.0 minor bump?). Tier 2 picks the conservative interpretation and notes it; operator can override later.
- **Test-count delta in close-outs that don't apply** (the metarepo has no test suite; close-outs that include test-count fields can leave them as `N/A` rather than escalating).

These are all in-session fixable. The @reviewer's CONCERNS verdict triggers the post-review-fix loop in the implementer's same session per `templates/implementation-prompt.md` §"Post-Review Fix Documentation."

---

## Tier 3 review handling

If any Category A or B trigger fires, the failure mode is structural enough to warrant a **Tier 3 architectural review** in addition to operator escalation. Tier 3 review (`protocols/tier-3-review.md`) examines whether the failure indicates a flaw in the sprint design itself (e.g., the keystone wiring concept was wrong) versus a pure execution error (e.g., the implementer dropped the keystone step).

Tier 3 should be invoked if:
- B1 fires AND the implementation prompt was structurally defective (the keystone instruction was unclear or misplaced)
- B2 fires for 2+ sessions consecutively (suggests bootstrap routing pattern itself is hard to follow)
- A3 fires (RETRO-FOLD content regression at any scope; the sealed-content boundary was crossed; needs structural review of how RETRO-FOLD is protected)

For all other escalations, operator review without Tier 3 is sufficient.

---

## Escalation Procedure

1. **@reviewer subagent produces ESCALATE verdict** in its structured JSON appendix:
   ```json
   {
     "verdict": "ESCALATE",
     "escalation_triggers": ["A1" | "A2" | ... | "D3"],
     "findings": [{ "severity": "CRITICAL", "category": "...", ... }]
   }
   ```
2. **The session's close-out is preserved.** Do NOT amend the close-out to "fix" the escalation in the same session — escalation means operator review is required.
3. **Operator (Steven) reads the review report + close-out** in the work journal conversation.
4. **Operator decides:** revert / fix-in-place / extend-scope / split-to-followon-session / accept-with-rationale.
5. **Decision logged** as a DEC entry (this sprint reserves no new DEC numbers, so any escalation-driven decision is logged in the sprint close-out's "judgment calls" section + a follow-on DEC if the decision has cross-sprint implications).
6. **If accepted:** sprint continues. **If reverted/redone:** the affected session re-runs from scratch.

The work journal handoff prompt (Phase D artifact) explicitly instructs the operator on this procedure so escalations don't surprise the workflow.

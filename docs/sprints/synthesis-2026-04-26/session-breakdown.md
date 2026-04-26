# Sprint synthesis-2026-04-26: Session Breakdown

> **Note on session count:** Phase A initially proposed a 3-session structure. Strict application of the compaction-risk scoring per `protocols/sprint-planning.md` Phase A step 5 produces a 6-session structure (Session 0 + 5 metarepo sessions), with each session scoring ≤13 (MEDIUM or below).
>
> Two of the proposed 3 sessions exceeded thresholds: Session 1 at ~15 (HIGH) and Session 2 at ~38 (CRITICAL). The protocol mandates splitting any session at 14+. The expanded structure below honors that mandate, at the cost of higher session count (~6.5 hours operator time vs the originally-pitched ~3.75 hours).
>
> Trade-off accepted because: (a) the protocol's scoring exists specifically to prevent compaction-driven regressions in implementation sessions, and the synthesis sprint's whole goal is making protocol guidance auto-fire — exempting *this* sprint from the protocol would be hypocritical; (b) doc-heavy sessions can still hit context limits when they require cross-referencing many source files (the 3 evolution notes + RETRO-FOLD-closeout + ARGUS campaign artifacts + design summary + sprint spec all must be in context for content sessions); (c) multiple smaller sessions land more incrementally, reducing blast radius if any single session needs to be redone.

---

## Session Index

| # | Name | Scope summary | Score | Tier |
|---|---|---|---|---|
| 0 | Argus-side input-set backfill | P28+P29 in SUMMARY.md + optional CLAUDE.md `## Rules` | 3 | LOW |
| 1 | Keystone wiring + RULE additions + close-out strengthening | universal.md / close-out.md / implementation-prompt.md / review-prompt.md | 11 | MEDIUM |
| 2 | Mechanical housekeeping + scaffold + evolution-notes | work-journal-closeout / doc-sync-automation-prompt / scaffold/CLAUDE.md / evolution-notes/README + 3 status stamps | 12 | MEDIUM |
| 3 | New protocol: campaign-orchestration + impromptu-triage extension | campaign-orchestration.md (NEW) + impromptu-triage.md ext + bootstrap routing | 13 | MEDIUM |
| 4 | New protocol: operational-debrief | operational-debrief.md (NEW) + bootstrap routing | 11 | MEDIUM |
| 5 | New templates + validator script | stage-flow.md (NEW) + scoping-session-prompt.md (NEW) + phase-2-validate.py (NEW) + bootstrap Template Index | 13 | MEDIUM |
| 6 | Codebase-health-audit major expansion + sprint-planning cross-ref | codebase-health-audit.md (1.0.0 → 2.0.0) + sprint-planning.md cross-ref | 13 | MEDIUM |

**Total operator-attended time:** ~15 + 75 + 60 + 90 + 60 + 75 + 90 = **~465 minutes (~7.75 hours).** Sessions 1–6 can be spread across multiple days; Session 0 must precede all of them.

**Dependency chain:** 0 → 1 → 2 → 3 → 4 → 5 → 6 (strict serial; see "Parallelism notes" below).

---

## Session 0: Argus-side Input-Set Backfill

**Scope (1 sentence):** Append P28 + P29 retrospective candidates to `SPRINT-31.9-SUMMARY.md` §Campaign Lessons + optionally add a `## Rules` section to ARGUS's `CLAUDE.md` if not already present, ensuring the synthesis input set is durable before metarepo work begins.

**Creates:** None.

**Modifies:**
- `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` (append P28 + P29 entries to §Campaign Lessons; preserve existing P26 + P27 entries verbatim)
- *Optional:* `argus/CLAUDE.md` (add `## Rules` section pointing at `.claude/rules/universal.md` if not present — Phase B's question 10 from Phase A)

**Integrates:** N/A (foundational; no upstream session).

**Acceptance gates:**
- `grep -c "P28 candidate\|P29 candidate" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` ≥ 2
- Existing P26 + P27 entries unchanged (verifiable via diff)
- *Optional:* `grep "## Rules" argus/CLAUDE.md` ≥ 1 (if section was added)

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 0 | 0 |
| Files modified | 1–2 | 1–2 |
| Files in pre-flight reads | 1 (the kickoff context already in conversation; SUMMARY.md itself) | 1 |
| New tests to write | 0 | 0 |
| Complex integration wiring | None | 0 |
| External API debugging | None | 0 |
| Large new files | None | 0 |
| **Total** | | **3** |

**Tier:** LOW (≤8). Proceed.

**Parallelizable:** false. Foundational input-set commit; Session 1 reads the result.

---

## Session 1: Keystone Wiring + RULE Additions + Close-Out Strengthening

**Scope (1 sentence):** Land the keystone Pre-Flight rule-loading wiring in `templates/implementation-prompt.md` and `templates/review-prompt.md`, add three new universal RULEs (RULE-051/052/053 from P26/P27/P29), append a 5th sub-bullet to RULE-038 (P28), and strengthen close-out.md Step 3 (FLAGGED blocks both commit and push).

**Creates:** None.

**Modifies:**
- `claude/rules/universal.md` (add RULE-051/052/053 in new sections §16/§17 as needed; append 5th sub-bullet to RULE-038; bump version 1.0 → 1.1; preserve RULE-001 through RULE-050 bodies byte-for-byte)
- `claude/skills/close-out.md` (strengthen Step 3 FLAGGED wording from "Do NOT push" to "Do NOT commit, stage, or push" — block earlier in the pipeline)
- `templates/implementation-prompt.md` (insert keystone Pre-Flight step 1 reading `.claude/rules/universal.md`; add Operator Choice subsection with checkbox-block pattern; add No-Cross-Referencing rule to Constraints; add Section-Order discipline note; bump version 1.2.0 → 1.3.0)
- `templates/review-prompt.md` (insert keystone Pre-Flight step reading `.claude/rules/universal.md`; bump version 1.1.0 → 1.2.0)

**Integrates:** Session 0's stable input set (synthesis is now referencing P26-P29 with all four captured durably).

**Acceptance gates:**
- `grep -c "^RULE-05[123]:" workflow/claude/rules/universal.md` = 3 (exact)
- `grep -A2 "Pre-Flight Checks" workflow/templates/implementation-prompt.md | grep -c "universal.md"` ≥ 1
- Same for `review-prompt.md`
- `git diff origin/main workflow/claude/rules/universal.md` shows additions only between RULE-050 and EOF (or new section appended); RULE-038–050 bodies unchanged except for RULE-038's 5th sub-bullet
- All 4 modified files have version-header bumps

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 0 | 0 |
| Files modified | 4 | 4 |
| Files in pre-flight reads | 6 (design-summary, sprint-spec, spec-by-contradiction, regression-checklist [TBD], RETRO-FOLD-closeout, current implementation-prompt structure to know where keystone insertion goes) | 6 |
| New tests to write | 0 | 0 |
| Complex integration wiring | Keystone affects all downstream sessions but is a 1-line additive Pre-Flight step, not a 3+-component integration | 1 |
| External API debugging | None | 0 |
| Large new files | None | 0 |
| **Total** | | **11** |

**Tier:** MEDIUM (9–13). Proceed with caution.

**Parallelizable:** false. Session 2+ depend on stable RULE numbering (51/52/53) and the keystone Pre-Flight wiring being committed.

**Risk notes:** The single highest-leverage session in the sprint. Failure here is sprint failure. Tier 2 review must verify the keystone Pre-Flight wording is imperative ("read `.claude/rules/universal.md` and treat its contents as binding for this session") not advisory.

---

## Session 2: Mechanical Housekeeping + Scaffold + Evolution-Notes

**Scope (1 sentence):** Extend `templates/work-journal-closeout.md` with a Hybrid Mode section, extend `templates/doc-sync-automation-prompt.md` with a Between-Session Doc-Sync section, add a `## Rules` section to `scaffold/CLAUDE.md` as defensive backup wiring, document the synthesis-status convention in `evolution-notes/README.md`, and stamp the 3 evolution notes with their `**Synthesis status:**` header.

**Creates:** None.

**Modifies:**
- `templates/work-journal-closeout.md` (add Hybrid Mode section per N3.6; bump version)
- `templates/doc-sync-automation-prompt.md` (add Between-Session Doc-Sync section per P34; bump version)
- `scaffold/CLAUDE.md` (add `## Rules` section per Phase B Q9; defensive backup for the keystone wiring)
- `evolution-notes/README.md` (add synthesis-status convention; document the format `**Synthesis status:** SYNTHESIZED in <sprint-name> (commit <SHA>)`)
- `evolution-notes/2026-04-21-argus-audit-execution.md` (additive metadata header line; bodies unchanged)
- `evolution-notes/2026-04-21-debrief-absorption.md` (additive metadata header line; bodies unchanged)
- `evolution-notes/2026-04-21-phase-3-fix-generation-and-execution.md` (additive metadata header line; bodies unchanged)

**Integrates:** Session 1's keystone Pre-Flight wiring (Hybrid Mode in work-journal-closeout references that universal rules apply via the keystone, no need to re-document them).

**Acceptance gates:**
- `grep "Hybrid Mode" workflow/templates/work-journal-closeout.md` ≥ 1
- `grep "Between-Session" workflow/templates/doc-sync-automation-prompt.md` ≥ 1
- `grep "## Rules" workflow/scaffold/CLAUDE.md` ≥ 1
- `grep -c "**Synthesis status:**" workflow/evolution-notes/2026-04-21-*.md` = 3
- For each evolution note: `git diff origin/main workflow/evolution-notes/2026-04-21-*.md` shows ONLY metadata-block additions (body lines unchanged)

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 0 | 0 |
| Files modified | 7 | 7 |
| Files in pre-flight reads | 5 (design-summary, sprint-spec, spec-by-contradiction, regression-checklist, current evolution-notes/README structure) | 5 |
| New tests to write | 0 | 0 |
| Complex integration wiring | Mechanical edits only | 0 |
| External API debugging | None | 0 |
| Large new files | None | 0 |
| **Total** | | **12** |

**Tier:** MEDIUM. Proceed with caution.

**Parallelizable:** false. Sessions 3+ may reference Hybrid Mode pattern from work-journal-closeout.md; the 3 evolution notes need the synthesis-status header stable before they're cited as "synthesized" by downstream content.

**Risk notes:** The 3 evolution-note edits are surgically additive (one metadata line each). Tier 2 review explicitly verifies bodies untouched (regression-checklist item).

---

## Session 3: campaign-orchestration.md + impromptu-triage Extension + Bootstrap Routing

**Scope (1 sentence):** Create `protocols/campaign-orchestration.md` covering campaign absorption / supersession / cross-track close-out / pre-execution gate / naming conventions / DEBUNKED status / decision matrix / two-session SPRINT-CLOSE option / 7-point-check appendix; extend `protocols/impromptu-triage.md` with the two-session scoping variant; add bootstrap-index.md routing entries for campaign-orchestration.

**Creates:**
- `protocols/campaign-orchestration.md` (NEW; expected ~250–350 lines; large file)

**Modifies:**
- `protocols/impromptu-triage.md` (add two-session scoping variant section referencing `templates/scoping-session-prompt.md` [created in Session 5]; bump version)
- `bootstrap-index.md` ("Conversation Type → What to Read" entry for "Campaign Orchestration / Absorption / Close"; Protocol Index row for `campaign-orchestration.md`)

**Integrates:** Sessions 1+2 (RULE numbering for cross-references; keystone Pre-Flight applies in any session prompts the new protocol generates; Hybrid Mode reference in work-journal-closeout.md; the synthesis-status convention is now in place so the new protocol can cite "see synthesis-2026-04-26 evolution notes for origin").

**Forward dependency:** `templates/scoping-session-prompt.md` is referenced from `impromptu-triage.md` extension but doesn't exist yet (created in Session 5). Reference is by path only. Two acceptable patterns: (a) reference the path proactively with a "Created in synthesis-2026-04-26 Session 5" note for the brief window between sessions, or (b) hold the impromptu-triage edit until Session 5. **Decision: pattern (a)** — keeps Session 3 cohesive; the path reference is correct ahead of file creation. Tier 2 review of Session 3 acknowledges the forward dep; Tier 2 review of Session 5 verifies the file now exists.

**Acceptance gates:**
- `protocols/campaign-orchestration.md` exists, has workflow-version 1.0.0
- File contains all 9 required sections: campaign absorption, supersession, authoritative-record preservation, cross-track close-out, pre-execution gate, naming conventions, DEBUNKED status, absorption-vs-sequential decision matrix, 7-point-check appendix
- File uses generalized terminology (per F1: "campaign coordination surface" not "Work Journal conversation"; per F6: generalized absorption axes; per F10: appendix conditional framing)
- `grep "two-session scoping" workflow/protocols/impromptu-triage.md` ≥ 1
- `bootstrap-index.md` has new routing entry + Protocol Index row
- All edits include Origin footnotes citing source notes / P-numbers / SPRINT-31.9 artifacts

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 1 | 2 |
| Files modified | 2 | 2 |
| Files in pre-flight reads | 7 (design-summary, sprint-spec, spec-by-contradiction, regression-checklist, RETRO-FOLD-closeout, evolution-note-2 [debrief-absorption], ARGUS CAMPAIGN-CLOSE-PLAN.md) | 7 |
| New tests to write | 0 | 0 |
| Complex integration wiring | The new protocol cites several existing protocols — but as references, not wiring | 0 |
| External API debugging | None | 0 |
| Large new files | 1 (campaign-orchestration.md expected >150 lines) | 2 |
| **Total** | | **13** |

**Tier:** MEDIUM (at upper edge). Proceed with caution.

**Parallelizable:** false. Session 4 (operational-debrief) cross-references campaign-orchestration's debrief-absorption section. Session 5 (templates) creates `scoping-session-prompt.md` referenced by Session 3's impromptu-triage extension.

**Risk notes:** The largest single design-judgment session. Implementation prompt structures the work into 4 sub-phases: (a) skeleton + main sections, (b) appendix + decision matrix, (c) impromptu-triage extension with scoping-session reference, (d) bootstrap-index routing entry. Each sub-phase is a natural checkpoint. If compaction surfaces mid-session, can resume cleanly from the design summary + sprint spec + last completed sub-phase.

---

## Session 4: operational-debrief.md + Bootstrap Routing

**Scope (1 sentence):** Create `protocols/operational-debrief.md` covering the 3 recurring-event-driven knowledge-stream patterns (periodic operational debrief / event-driven debrief / periodic review without a cycle), the execution-anchor-commit correlation pattern (replacing the rejected safety-tag taxonomy), and references to project-specific debrief implementations; add bootstrap-index.md routing entry.

**Creates:**
- `protocols/operational-debrief.md` (NEW; expected ~150–200 lines; borderline large)

**Modifies:**
- `bootstrap-index.md` ("Conversation Type → What to Read" entry for "Operational Debrief"; Protocol Index row)

**Integrates:** Session 3's `campaign-orchestration.md` debrief-absorption section (operational-debrief should cross-reference campaign-orchestration for the absorption flow).

**Acceptance gates:**
- `protocols/operational-debrief.md` exists, workflow-version 1.0.0
- Contains all 3 recurring-event patterns (periodic / event-driven / periodic-without-cycle) with at least 1 worked example each
- Uses "execution-anchor commit" terminology, not "boot commit" (per F3)
- Reflects current ARGUS reality (operator manually records); has explicit "Recommended automation: project-specific" subsection
- 3 non-trading examples present (deploy retrospective, post-incident review, weekly health review) per F2
- `bootstrap-index.md` updated
- Cross-reference to `campaign-orchestration.md` debrief-absorption section present
- Origin footnotes cite evolution-note-2 (debrief-absorption) + Phase A pushback round 2 (safety-tag rejection)

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Files in pre-flight reads | 6 (design-summary, sprint-spec, spec-by-contradiction, regression-checklist, ARGUS market-session-debrief.md, evolution-note-2 [debrief-absorption]) | 6 |
| New tests to write | 0 | 0 |
| Complex integration wiring | None | 0 |
| External API debugging | None | 0 |
| Large new files | 1 (borderline; expected ~150 lines) | 2 |
| **Total** | | **11** |

**Tier:** MEDIUM. Proceed with caution.

**Parallelizable:** false. Cross-references campaign-orchestration.md from Session 3.

**Risk notes:** Lighter session; primary risk is over-applying ARGUS-specific framing. Tier 2 review explicitly checks F2 (recurring-event-driven framing, not daily-cycle assumption) and F3 (execution-anchor-commit terminology).

---

## Session 5: Templates + Validator Script + Bootstrap Template Index

**Scope (1 sentence):** Create `templates/stage-flow.md` (DAG artifact template with ASCII / Mermaid / ordered-list formats), `templates/scoping-session-prompt.md` (read-only scoping template producing dual artifacts), `scripts/phase-2-validate.py` (CSV linter, ~50 lines), and add bootstrap-index.md Template Index rows for the 2 new templates.

**Creates:**
- `templates/stage-flow.md` (NEW; expected ~80–120 lines; not large)
- `templates/scoping-session-prompt.md` (NEW; expected ~80–120 lines; not large)
- `scripts/phase-2-validate.py` (NEW; expected ~50 lines)

**Modifies:**
- `bootstrap-index.md` (Template Index rows for `stage-flow.md` and `scoping-session-prompt.md`)

**Integrates:** Sessions 3+4 (the 2 new templates are referenced by the new protocols; impromptu-triage extension from Session 3 has a forward reference to scoping-session-prompt that this session resolves).

**Acceptance gates:**
- `templates/stage-flow.md` exists, workflow-version 1.0.0, contains 3 format variants (ASCII / Mermaid / ordered-list) per F7, each with worked example
- `templates/scoping-session-prompt.md` exists, workflow-version 1.0.0, contains read-only constraints + dual-artifact requirement (findings + generated fix prompt) + structured findings template (code-path map / hypothesis verification / race conditions / root-cause statement / fix proposal / test strategy / risk assessment)
- `scripts/phase-2-validate.py` exists, executable, contains 6 documented checks (row column-count / decision-value canonical / fix-now has fix_session_id / FIX-NN-kebab-name / 2 row-integrity checks). Does NOT validate safety tags.
- Manual smoke test passes against ARGUS Sprint 31.9 audit Phase 2 CSV (catches 9 known column-drift rows). Smoke-test invocation + output captured in close-out.
- Manual edge-case test passes against malformed test CSV (each check produces row-by-row report).
- `bootstrap-index.md` Template Index has 2 new rows
- Session 3's forward dependency on `templates/scoping-session-prompt.md` is now resolved (path exists)

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 3 | 6 |
| Files modified | 1 | 1 |
| Files in pre-flight reads | 6 (design-summary, sprint-spec, spec-by-contradiction, regression-checklist, current bootstrap-index.md, ARGUS audit Phase 2 CSV [for validator smoke testing]) | 6 |
| New tests to write | 0 (manual smoke check, not automated) | 0 |
| Complex integration wiring | None | 0 |
| External API debugging | None | 0 |
| Large new files | 0 (none expected to exceed 150 lines) | 0 |
| **Total** | | **13** |

**Tier:** MEDIUM (at upper edge). Proceed with caution.

**Parallelizable:** false. Session 6 references all 3 new templates/scripts.

**Risk notes:** The validator script is the only Python in the sprint. Implementer should verify Python 3.x compatibility, no external dependencies beyond stdlib (csv module), and that the script handles non-UTF-8 input gracefully. Smoke test must be run AND the output captured in the close-out.

---

## Session 6: Codebase-Health-Audit Major Expansion + Sprint-Planning Cross-Reference

**Scope (1 sentence):** Major-expand `protocols/codebase-health-audit.md` (1.0.0 → 2.0.0) with full Phase 1/2/3 content covering all dispositions from notes 1+3 + the rejected-safety-tag-taxonomy addendum + the `phase-2-validate.py` non-bypassable gate + tiered hot-files operationalizations + 3 non-trading fingerprint examples + generalized terminology per F1/F4/F5/F8/F9; add a one-line cross-reference from `protocols/sprint-planning.md` to `protocols/campaign-orchestration.md`.

**Creates:** None.

**Modifies:**
- `protocols/codebase-health-audit.md` (major expansion 1.0.0 → 2.0.0; expected to grow from 87 lines to ~400–500 lines; restructure into clear Phase 1 / Phase 2 / Phase 3 sections)
- `protocols/sprint-planning.md` (one-line cross-reference to `protocols/campaign-orchestration.md`; minor version bump)

**Integrates:** All prior sessions. Audit protocol references RULE numbering from Session 1; uses Hybrid Mode pattern from Session 2's work-journal-closeout extension; cites campaign-orchestration.md from Session 3; cites operational-debrief.md from Session 4; references stage-flow.md, scoping-session-prompt.md, and phase-2-validate.py from Session 5; uses generalized terminology per F1/F4/F5/F8/F9.

**Acceptance gates:**
- `codebase-health-audit.md` workflow-version is 2.0.0
- File has explicit Phase 1, Phase 2, Phase 3 sections (vs current Phase-1-only structure)
- Phase 1 contains: DEF Health Spot-Check (S1.1) using "closed-item" terminology (F8); custom-structure rule (S1.2); session-count budget (S1.3); references the 3 evolution notes for origin
- Phase 2 contains: CSV integrity + override table (N3.2); scale-tiered tooling (OQ3.2); operator-judgment-commit pattern (N1.4); approval-heavy with hot-file carve-out (N1.5); combined doc-sync (ID1.1); in-flight triage amendment (ID1.3); tiered hot-files operationalizations per F4 (5 tiers: recent-bug / recent-churn / post-incident / maintained-list / code-ownership); `### Anti-pattern (do not reinvent)` addendum for rejected safety-tag taxonomy with rationale citing this synthesis sprint; `phase-2-validate.py` non-bypassable gate phrased imperatively ("Phase 2 cannot complete until phase-2-validate.py exits zero")
- Phase 3 contains: file-overlap-only DAG scheduling (N3.1 minus safety-matrix half); fingerprint-before-behavior-change with 3 non-trading examples (pricing engine / A/B test / ML model) per F5; sort_findings_by_file (ID3.2); coordination-surface branch per F1; scope-extension home; contiguous numbering (ID1.4); git-commit-body-as-state-oracle as OPTIONAL with squash-merge caveat per F9; fix-group cardinality (OQ3.4); references to scoping-session-prompt for low-confidence root-cause work
- Drops: safety-tag core+modifier taxonomy, action-type routing N3.3, safety-tag session resolution ID3.3
- All ARGUS-specific terminology (DEF, boot commit, trading session) is generalized or contextually framed per F1–F10
- `protocols/sprint-planning.md` has cross-reference to `campaign-orchestration.md`
- All new content has Origin footnotes

**Compaction-risk scoring:**

| Factor | Count | Points |
|---|---|---|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Files in pre-flight reads | 8 (design-summary, sprint-spec, spec-by-contradiction, regression-checklist, current codebase-health-audit.md, evolution-note-1 [audit-execution], evolution-note-3 [phase-3-fix-generation], ARGUS CAMPAIGN-COMPLETENESS-TRACKER.md) | 8 |
| New tests to write | 0 | 0 |
| Complex integration wiring | Cross-references many other protocols + the rejected-pattern addendum requires careful framing | 1 |
| External API debugging | None | 0 |
| Large new files | 0 (no creates) | 0 |
| Large modification (audit going from 87 → 400+ lines) | 1 | 2 |
| **Total** | | **13** |

**Tier:** MEDIUM (at upper edge). Proceed with caution.

**Parallelizable:** false. Final session; depends on all prior outputs.

**Risk notes:** The single largest content-generation session in the sprint (a 5x expansion of an existing protocol). Implementation prompt structures the work into 4 sub-phases by Phase: (a) Phase 1 expansion, (b) Phase 2 expansion (including rejected-pattern addendum, hot-files tiers, validator gate), (c) Phase 3 expansion (including 3 non-trading fingerprint examples, file-overlap-only DAG, generalized terminology pass), (d) sprint-planning.md cross-reference + final F1–F10 verification pass. Each sub-phase is a natural checkpoint.

The Tier 2 review for this session should be **especially thorough** — the rejected-pattern addendum is the structural defense against a future audit reinventing the safety-tag taxonomy, and its wording is load-bearing.

---

## Cross-Session Dependency Chain

```
Session 0 (argus SUMMARY backfill)
    │
    ▼
Session 1 (keystone wiring + RULEs + close-out strengthening)
    │  produces: stable RULE numbering 51/52/53, keystone Pre-Flight wiring,
    │            close-out FLAGGED-blocks-commit-and-push semantics
    ▼
Session 2 (housekeeping templates + scaffold + evolution-notes)
    │  produces: Hybrid Mode in work-journal-closeout, Between-Session Doc-Sync,
    │            scaffold/CLAUDE.md ## Rules, evolution-notes README convention,
    │            3 evolution notes status-stamped
    ▼
Session 3 (campaign-orchestration + impromptu-triage + bootstrap routing)
    │  produces: campaign-orchestration.md (1 large new), impromptu-triage extension,
    │            bootstrap-index Conversation Type entry + Protocol Index row
    │  forward-dep: scoping-session-prompt.md (resolved in Session 5)
    ▼
Session 4 (operational-debrief + bootstrap routing)
    │  produces: operational-debrief.md (1 borderline-large new),
    │            bootstrap-index Conversation Type entry + Protocol Index row,
    │            cross-reference to campaign-orchestration debrief-absorption section
    ▼
Session 5 (templates + validator + bootstrap Template Index)
    │  produces: stage-flow.md, scoping-session-prompt.md, phase-2-validate.py,
    │            bootstrap-index Template Index rows.
    │            RESOLVES Session 3's forward-dep on scoping-session-prompt.md
    ▼
Session 6 (codebase-health-audit major expansion + sprint-planning cross-ref)
   produces: codebase-health-audit.md 1.0.0 → 2.0.0, sprint-planning.md cross-ref.
            Final integration session — references all prior sessions' outputs.
```

## Parallelism Notes

All sessions flagged `parallelizable: false`. Justifications:

- **S0 → S1:** S1 references the synthesis input set captured in S0
- **S1 → S2:** S2's Hybrid Mode section may reference the keystone Pre-Flight wiring; the 3 evolution-note status headers cite the synthesis sprint name which only stabilizes after S1 commits
- **S2 → S3:** S3's campaign-orchestration may reference the synthesis-status convention from S2 + Hybrid Mode pattern from S2's work-journal-closeout
- **S3 → S4:** S4's operational-debrief cross-references campaign-orchestration debrief-absorption section
- **S4 → S5:** No direct dependency, but S6 needs both, so serial keeps the dependency chain clean
- **S5 → S6:** S6's audit expansion references all 3 templates/scripts created in S5

For human-in-the-loop mode, the parallelizable flags are informational only. Operator runs sessions sequentially and can pause between any pair.

## Test Suite Tiering (DEC-328 application)

This sprint creates no executable code beyond `phase-2-validate.py` (smoke-tested manually). The metarepo has no test suite. Therefore:

- **No pytest-based test tiering applies.** DEC-328's full-vs-scoped command distinction is a no-op for this sprint.
- Sessions verify completion via grep-based assertions on the diff (acceptance gates per session).
- Tier 2 reviews verify acceptance gates, not test counts.

If `phase-2-validate.py` smoke testing in Session 5 surfaces a Python issue, it's flagged in close-out and resolved within Session 5.

## Visual Review Items

None. No frontend / UI work in this sprint.

## Compaction-Risk Calibration Note

The compaction-risk thresholds (Low ≤8, Medium 9–13, High 14–17, Critical 18+) appear calibrated for code-heavy sessions. Pure doc-work sessions may have lower actual compaction risk per file than the formula suggests, because:

1. Each doc edit is "read once, edit once, done" (no read-debug-rewrite-test cycle)
2. Most edits are additive sections at known locations
3. The spec specifies exact wording for many edits
4. No external state (DB schemas, API endpoints) to track

Under that interpretation, the 6-session structure may be conservative. However, applying judgment exceptions to the protocol's risk formula erodes the protocol — and this sprint's goal is the opposite (making protocol guidance auto-fire, not exempting itself). The 6-session structure is therefore the recommended path; if execution evidence later suggests doc-work calibration should be adjusted, that's a strategic-check-in topic, not a unilateral exception.

If the operator nonetheless decides to compress to 4 or 5 sessions for time-budget reasons, the compaction-risk scores must be explicitly noted in each consolidated session's implementation prompt + close-out, and the @reviewer subagent must be alert to compaction-driven regressions specifically.

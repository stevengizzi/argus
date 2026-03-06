# ARGUS Retrofit Advisory
# Prepared: March 4, 2026
# Context: Planning document for retrofitting ARGUS into the metarepo workflow system.
# This advisory is consumed in the ARGUS Claude.ai project, not executed here.

---

## 1. Executive Assessment

ARGUS is the most mature of the three source projects and, paradoxically, the easiest retrofit. The meta-analysis reveals that ARGUS organically evolved to Phase D/E practices -- sprint packages, structured kickoff prompts, decision log discipline, and even a .claude/rules/ file (backtesting.md). The retrofit is not an archaeology project (that work is already done via 17 days of disciplined doc maintenance). It is an **alignment and tooling installation** -- bringing existing practices into conformance with the metarepo artifact system and filling the specific gaps that ARGUS never developed.

**Estimated total effort:** 3-4 conversations in the ARGUS Claude.ai project, plus 1-2 Claude Code sessions for file installation.

**What ARGUS already has that maps directly to the metarepo system:**
- Decision Log (249 entries) -- the most comprehensive of any project
- Sprint package format (from Sprint 18+) -- close to the sprint-spec template
- Kickoff prompt format -- close to the implementation-prompt template
- DEC/RSK/DEF numbering with cross-references and supersession markers
- .claude/rules/backtesting.md -- already using the rules directory
- Repo access for code review (established Sprint 14+)

**What ARGUS is missing:**
- Three-tier review system (currently ad-hoc review, no formal close-out protocol)
- Skills files (close-out.md, review.md, diagnostic.md, doc-sync.md, canary-test.md)
- Agents files (reviewer.md)
- universal.md in .claude/rules/
- Two-tier documentation architecture (Project Knowledge is monolithic and approaching size limits)
- Formal doc-sync checklist (currently manual, 1000+ lines per sprint by 21d)

---

## 2. The Decision Log Question (249 DECs)

### Do the 249 DECs need audit?

**Short answer: No full audit. Spot-check only.**

The meta-analysis describes the decision log as "the project's superpower" and notes that "decisions never got relitigated because they were always documented." This is not a decision log in disrepair -- it is the most well-maintained artifact in any of the three projects.

However, the DECs were written before the metarepo's decision-entry template existed. The template requires: decision, rationale, alternatives considered, and scope of impact. Early ARGUS DECs (especially DEC-001 through ~DEC-050) likely have thinner rationale sections because the format was still evolving.

### Recommended approach:

**Do NOT audit all 249 DECs.** That would be 3-5 conversations of pure archaeology with minimal ROI. Instead:

1. **Spot-check 10 DECs from each phase** (Phase A: 1-5, Phase B: 6-11, Phase C: 12-13, Phase D: 14-20, Phase E: 21+). That is ~40-50 DECs reviewed in a single conversation. The goal is not to rewrite them but to assess whether the existing format is "close enough" or needs a migration pass.

2. **Apply the new format going forward only.** Starting with the next sprint after retrofit, all new DECs use the decision-entry template. Old DECs retain their original format unless specifically revisited during future work.

3. **Check for supersession completeness.** The meta-analysis mentions that DEC/RSK/DEF numbering evolved to include supersession markers. Verify that superseded DECs are properly marked. If Sprint 18.75's DEC renumbering incident (DEC-133 to DEC-136 offset) left any orphaned references, clean those up.

**Estimated effort for DEC work:** 1 conversation (the spot-check), ~30 minutes.

---

## 3. The Conversation History Question (65 Conversations)

### What to mine, what to skip?

**Short answer: Skip almost everything. The meta-analysis already did the excavation.**

The meta-analysis report is itself the product of mining those 65 conversations. It identified every significant pattern, failure mode, process evolution, and decision point. Re-mining the raw conversations would duplicate work that has already been done more thoroughly than a retrofit would justify.

### What is specifically worth revisiting:

1. **Nothing for archaeology purposes.** The meta-analysis is comprehensive.

2. **Sprint 21.5 and any conversations after the meta-analysis date (March 3, 2026).** These were not covered by the analysis and may contain decisions or patterns that need to be captured before the retrofit "resets" the workflow.

3. **The Project Knowledge document itself.** This is the live working document that grew to extraordinary length. It needs restructuring (see Section 5 below), and understanding its current structure requires reading it -- but that is reading one document, not mining 65 conversations.

### What to explicitly NOT do:

- Do not re-read old sprint planning conversations. Their outputs (specs, prompts, decisions) are already in the docs.
- Do not re-read old review conversations. Their findings were already actioned.
- Do not attempt to extract "missed" decisions from early conversations. If a decision was important enough to matter now, it either made it into the DEC log or it was implicitly superseded.

**Estimated effort for conversation mining:** 0 dedicated conversations. Any needed context will surface naturally during the doc restructuring conversation.

---

## 4. Sprint Numbering Strategy

### Recommendation: Continue from the current number. Do not offset or restart.

ARGUS is at Sprint 21.5 (Live Integration). The numbering system is deeply embedded in the decision log (249 entries reference sprint numbers), the codebase (commit messages), and the project's mental model.

**Options considered:**

**Option A: Continue from 22.** The retrofit itself is not a sprint -- it is infrastructure work. The next implementation sprint after retrofit is Sprint 22 (or whatever the next planned work is). This preserves all existing cross-references and requires zero renumbering.

**Option B: Offset (e.g., start at 100).** This would create a clean visual break between "pre-metarepo" and "post-metarepo" sprints. But it would mean every future DEC that references an old sprint needs mental translation, and the gap (22-99) would be confusing in any log or timeline view.

**Option C: Fresh start from 1.** This would break every existing cross-reference and create ambiguity whenever someone (human or Claude) encounters "Sprint 5" -- is that the original Sprint 5 or the new Sprint 5?

**Verdict: Option A.** Continue numbering. The retrofit is a non-sprint activity. Add a DEC entry (DEC-250) documenting the metarepo retrofit and marking it as the process transition point. Future readers can use DEC-250 as the "before/after" marker.

The sub-numbering convention (21a, 21b, 21.5) should also continue -- it is already well-established and matches how the metarepo sprint-spec template handles session decomposition.

---

## 5. Documentation Restructuring (The Big Lift)

This is the most substantial part of the retrofit. The meta-analysis flagged that ARGUS's Project Knowledge document "grew to extraordinary length" and is "approaching limits where information gets lost in the volume."

### The problem:

ARGUS currently has a single-tier documentation system. Project Knowledge serves as both Claude-optimized operational context (Tier A) and human-readable project record (Tier B). This worked when the project was small but is now the binding constraint.

### The restructuring plan:

**Step 1: Triage the current Project Knowledge into Tier A and Tier B.**

Tier A (stays in Claude.ai Project Knowledge, goes into .claude/rules/ and CLAUDE.md):
- Current system architecture (what exists now, not history)
- Active constraints and rules (the backtesting rules, strategy behavior contracts, etc.)
- Current phase/status
- Active risk register items
- The "Key Decisions Made" section, but compressed to decision + one-line rationale only (not full alternatives/history)

Tier B (moves to repo as docs/, human-readable):
- Full decision log with complete rationale and alternatives
- Sprint history and evolution narrative
- Process evolution arc (Phase A through E)
- Superseded decisions and their context
- The meta-analysis report itself

**Step 2: Estimate size reduction.**

The goal is to get Tier A under ~50% of the current Project Knowledge size. Based on the meta-analysis description, the "Key Decisions Made" section alone is massive. Compressing 249 DECs from full entries to one-line summaries (with the full entries living in repo docs) should cut the largest section by 70-80%.

**Step 3: Create the .claude/ directory structure.**

```
.claude/
  rules/
    universal.md          (from metarepo -- the file we just built)
    backtesting.md        (already exists -- keep as-is)
    trading-strategies.md (new -- extract strategy-specific constraints from Project Knowledge)
  skills/
    close-out.md          (from metarepo)
    review.md             (from metarepo)
    diagnostic.md         (from metarepo)
    doc-sync.md           (from metarepo)
    canary-test.md        (from metarepo)
    bootstrap-repo.md     (not needed -- ARGUS already exists)
  agents/
    reviewer.md           (from metarepo)
```

**Estimated effort for doc restructuring:** 2 conversations. Conversation 1 does the triage and produces the compressed Tier A document. Conversation 2 verifies the Tier A doc against the codebase reality and produces the Tier B repo docs.

---

## 6. Review System Installation

ARGUS currently uses ad-hoc review: transcript-based (early sprints) evolving to repo-access review (Sprint 14+). The three-tier review system needs to be installed.

### What changes:

1. **Tier 1 (Close-Out):** Every future implementation prompt gets the close-out appendix. This is a template change -- the sprint planning conversation in ARGUS simply uses the implementation-prompt template from the metarepo, which already includes the close-out section.

2. **Tier 2 (Diff-Based Review):** The reviewer agent file gets installed into .claude/agents/. Future sprint planning conversations generate a Tier 2 review prompt alongside each implementation prompt. Steven runs the reviewer agent after each session.

3. **Tier 3 (Architectural Review):** This already happens informally -- the meta-analysis notes that sprint completions triggered review conversations in Claude.ai. The change is formalizing the trigger criteria: Tier 2 ESCALATE verdict, sprint completion, or every 3-5 sprints on cadence.

### What does NOT change:

- The repo remains public for review access (already established)
- The sprint package format stays close to what it already is -- it just gains the review prompt as an additional output

**Estimated effort:** 0 dedicated conversations. This is installed as part of the doc restructuring (Conversation 2) and activated automatically with the next sprint planning conversation.

---

## 7. Existing Docs: Reuse vs. Rewrite

| Document | Verdict | Rationale |
|----------|---------|-----------|
| Decision Log (249 DECs) | **Reuse as-is.** Move full log to Tier B (repo). Produce compressed index for Tier A. | Already the project's strongest artifact. Do not risk breaking it. |
| Project Knowledge | **Restructure.** Triage into Tier A (compact) and Tier B (full). | Too large for a single document. The restructuring IS the retrofit. |
| Risk Register | **Reuse, refresh.** Check for stale items and archive resolved risks. | Likely has some items from Sprint 8-era that are long resolved. |
| Architecture docs | **Reuse, verify.** Spot-check against current codebase state. | May have drifted since Sprint 21d; a quick verification pass suffices. |
| Sprint Plan / Roadmap | **Rewrite.** Produce a fresh forward-looking sprint plan post-retrofit. | The old plan is a historical record. The new plan starts from current state. |
| CLAUDE.md files | **Rewrite.** Regenerate from the Tier A Project Knowledge. | These should be derived from the compressed Tier A document, not maintained independently. |
| .claude/rules/backtesting.md | **Reuse as-is.** | Already project-specific, already in the right location. |

---

## 8. Concrete Session Plan

### Conversation R1: Survey and Triage (in ARGUS Claude.ai project)

**Input:** Current Project Knowledge document, decision log, risk register, meta-analysis report.
**Objective:** Produce the Tier A / Tier B split plan.

Steps:
1. Run the retrofit-survey protocol from the metarepo (paste it in as the conversation starter).
2. Read the current Project Knowledge and produce a triage list: what stays in Tier A, what moves to Tier B, what gets archived.
3. Spot-check 40-50 DECs across all phases for format quality.
4. Identify any post-meta-analysis decisions (Sprint 21.5+) that need to be captured.
5. Produce the compressed Tier A Project Knowledge document (draft).
6. Produce the DEC index (one-line summaries of all 249 entries, for Tier A).

**Output:** Draft Tier A document, DEC index, triage plan, list of any issues found.

### Conversation R2: Doc Restructuring and Tooling Installation (in ARGUS Claude.ai project)

**Input:** R1 outputs, metarepo artifact files (skills, agents, universal.md).
**Objective:** Finalize Tier A, produce Tier B, install the artifact system.

Steps:
1. Review and finalize the Tier A Project Knowledge document.
2. Produce the Tier B documentation package (full decision log, sprint history, architecture narrative) as repo docs.
3. Generate the .claude/ directory file contents: universal.md, skills files, agent files, updated CLAUDE.md.
4. Produce DEC-250: "Metarepo workflow retrofit. Process transition point. All future sprints use the metarepo sprint planning protocol, three-tier review system, and close-out protocol."
5. Refresh the risk register (archive resolved items, add any new ones).
6. Produce a fresh forward-looking sprint plan from current state.

**Output:** Final Tier A doc, Tier B package, all .claude/ files ready for installation, DEC-250, refreshed risk register, new sprint plan.

### Claude Code Session R3: File Installation (in terminal)

**Input:** All files from R2.
**Objective:** Install the artifact system into the ARGUS repo.

Steps:
1. Create/update .claude/rules/universal.md
2. Create .claude/rules/trading-strategies.md (if produced in R2)
3. Create .claude/skills/ directory with all skill files
4. Create .claude/agents/reviewer.md
5. Update CLAUDE.md files in all relevant locations
6. Create docs/ directory structure for Tier B documents
7. Commit with message: "[Retrofit] Install metarepo workflow system"

**Estimated time:** 15-20 minutes. This is a pure file-copy session.

### Conversation R4 (Optional): First Sprint Planning Under New System

**Input:** The new Tier A Project Knowledge, the sprint plan from R2, the metarepo sprint-planning protocol.
**Objective:** Plan the next real sprint (Sprint 22 or whatever follows) using the full metarepo workflow.

This conversation serves as the validation that the retrofit worked. If the sprint planning protocol runs smoothly against the restructured docs, the retrofit is complete. If it surfaces gaps, those become immediate fixes.

---

## 9. Risks and Mitigations

**Risk: Tier A compression loses critical operational context.**
Mitigation: Conversation R1 produces the draft; R2 reviews it. Steven also reviews the Tier A document before installation. The Tier B docs in the repo serve as the safety net -- nothing is deleted, only reorganized.

**Risk: Sprint numbering confusion during transition.**
Mitigation: DEC-250 is the explicit marker. Any future conversation that encounters ambiguity can reference DEC-250 as the transition point.

**Risk: Old conversations in the ARGUS project reference the pre-retrofit Project Knowledge.**
Mitigation: This is unavoidable. The old Project Knowledge will exist in older conversation contexts. But since each new conversation loads the current Project Knowledge, this is self-correcting -- the first conversation after retrofit will see the new Tier A document.

**Risk: The 249-entry DEC index is itself very large.**
Mitigation: The index is one line per DEC. At ~80 characters per line, 249 entries is ~20KB -- large but manageable. If it proves too large for Tier A, it can be moved to a separate Project Knowledge file that Claude.ai loads, or split into "active DECs" (last 50) and "archived DECs" (the rest).

---

## 10. What This Advisory Does NOT Cover

- **Running the actual retrofit.** This advisory is planning guidance. The retrofit happens inside the ARGUS Claude.ai project using the session plan above.
- **MuseFlow or Grove retrofits.** Those will need their own advisories, though they are simpler (less history, fewer DECs). MuseFlow is the next most complex; Grove is the simplest.
- **Ongoing ARGUS development decisions.** Whether to continue Sprint 21.5, start Sprint 22, or do something else is a product decision, not a process decision.
- **The content of ARGUS-specific rules files.** The trading-strategies.md rule file (if needed) should be produced during R2 based on what the Tier A triage reveals about strategy-specific constraints that are currently buried in Project Knowledge.
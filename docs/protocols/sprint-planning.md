# Protocol: Sprint Planning

**Context:** Claude.ai conversation(s)
**Frequency:** Once per sprint
**Output:** Complete Sprint Package (spec, prompts, review infrastructure, checklists)

---

## When to Use
At the start of every sprint. This is the single most important conversation in
the sprint cycle -- it produces everything the implementation and review phases need.

## Conversation Structure

This protocol follows the Compaction-Resistant Planning Protocol (Template Section 3.1.1).

### Phase A: Think

Start the conversation with the sprint context:

    "We are planning Sprint [N] for [Project Name].

    Current state: [brief status -- what the last sprint accomplished]
    Sprint goal: [what this sprint should deliver]
    Relevant decisions: [DEC references that constrain this sprint]
    Known risks: [RSK references relevant to this sprint]

    Let us design this sprint. Before we generate any artifacts, I want to
    think through the requirements, edge cases, and session breakdown."

During Phase A, work through:

1. **Requirements clarification** -- What exactly does this sprint deliver?
   What are the acceptance criteria? Are there performance benchmarks?

2. **Edge cases and boundaries** -- What inputs, states, or conditions could
   cause problems? What should the system do in each case?

3. **Scope boundaries** -- What does this sprint explicitly NOT do?
   (This becomes the Specification by Contradiction.)

4. **Session decomposition** -- How many Claude Code sessions? What is the
   scope of each? What is the dependency order?

   For each session, explicitly answer:
   - **Creates:** What new files does this session produce?
   - **Modifies:** What existing files does this session change?
   - **Integrates:** Which prior session's output does this session wire into
     calling code? (A module that is created but never integrated is dead code.
     Every "Creates" entry in one session must have a corresponding "Integrates"
     entry in a later session, unless it is self-contained.)

5. **Compaction risk assessment** -- For each proposed session, score compaction
   risk using the point system below. The score determines whether the session
   must be split.

   | Factor | Points |
   |--------|--------|
   | Each new file created | +2 per file |
   | Each file modified | +1 per file |
   | Each file in pre-flight reads / context loading | +1 per file |
   | Each new test to write | +0.5 per test |
   | Complex integration wiring (connecting to 3+ existing components) | +3 |
   | External API debugging (live API calls, WebSocket, SSE) | +3 |
   | Large single file (any new file expected to exceed ~150 lines) | +2 per file |

   Thresholds:
   - **0–8 (Low):** Proceed.
   - **9–13 (Medium):** Proceed with caution.
   - **14–17 (High):** Must split before proceeding.
   - **18+ (Critical):** Must split into 3+ sessions.

   When splitting, aim for each sub-session to: create at most 2 new files,
   read at most 6 context files, write at most 8 new tests, and score ≤13.

   Do not move to Phase B with any session scoring 14+.

   The Session Breakdown artifact must include the scoring table for each
   session (see template). When compaction occurs during implementation, log
   the session's planning score and the point of compaction in the close-out
   report. This calibrates future scoring — if the system consistently
   under-predicts, lower the thresholds.

   **Test count estimation guide:** When estimating per-session test counts,
   use ~5 tests per new file + ~3 tests per modified file + ~2 tests per new
   API endpoint as a baseline. Apply a 2× multiplier for sessions that create
   new infrastructure (DB schemas, API routes, WebSocket handlers) because
   integration tests accumulate. This prevents the chronic underestimation seen
   in Sprint 22 (85 estimated vs. 288 actual).

   **Frontend visual-review fix budget:** For frontend sessions that include
   visual review items, budget an additional 0.5-session fix allowance in the
   session breakdown. If the visual review discovers no issues, the slot is
   unused. If it discovers issues, the fix session is already planned and does
   not require an impromptu triage. This is cheaper than running unplanned fix
   sessions that bypass the standard prompt template. Mark these in the session
   breakdown as "Session [N]f (visual-review fixes) — contingency, 0.5 session."

6. **Config changes assessment** -- If this sprint adds or modifies config
   fields (YAML files + Pydantic models), explicitly list each new field and
   its corresponding Pydantic model field name. Verify the names match exactly.
   Add a regression checklist item: "New config fields verified against Pydantic
   model (no silently ignored keys)." This prevents the class of bug where
   Pydantic silently drops unrecognized fields and uses defaults instead of
   operator-specified values.

7. **Regression assessment** -- What existing functionality could this sprint
   break? What invariants must be preserved?

8. **Workflow mode assessment:**
   - Does this sprint warrant an Adversarial Review? (architectural decisions,
     data model changes, new integrations)
   - Does this sprint need the Iterative Judgment Loop? (visual/UI work)
   - Should we run Synthetic Stakeholder simulation? (API or UX design)

### Phase B: Checkpoint

Before generating any artifacts:

    "Before we generate the sprint package, produce a compact design summary
    that captures everything we have decided. If we lose context, this summary
    alone should be sufficient to regenerate all artifacts."

The design summary should follow the design-summary template (see templates/design-summary.md).
Save it immediately after generation.

### Phase C: Generate Spec-Level Artifacts

Generate the spec-level artifacts one at a time, in this order:

1. Sprint Spec (using templates/sprint-spec.md)
2. Specification by Contradiction (using templates/spec-by-contradiction.md)
3. Session Breakdown (list of sessions with scope, dependencies, and compaction
   risk score. Each session must include the scoring table showing points per
   factor and total. Any session scoring 14+ must be split before proceeding.
   Each session must list Creates / Modifies / Integrates columns.)
4. Sprint-Level Escalation Criteria
5. Sprint-Level Regression Checklist
6. Doc Update Checklist
7. If adversarial review is warranted: **Adversarial Review Input Package** --
   extract and assemble the specific architecture document sections, DEC entries,
   and any other context the adversarial reviewer will need into a single
   standalone document. The developer should be able to open the adversarial
   review conversation and paste exactly three documents: the Sprint Spec, the
   Specification by Contradiction, and this input package. Do not leave the
   architecture excerpt to the developer to assemble -- identify and extract the
   relevant sections during planning, when the context is fresh.

After each artifact: save it, confirm saved, then request the next.

**Do NOT generate implementation prompts or review prompts in this phase.**
These are downstream of the spec-level artifacts and should only be generated
after any adversarial review revisions are resolved (Phase D or Phase E).

If compaction occurs mid-generation:
1. Start a new conversation
2. Paste the design summary from Phase B
3. List which artifacts are already saved
4. Continue from where generation stopped

### Phase C-1: Adversarial Review Gate

If adversarial review was warranted (Phase A, step 8):

1. **Stop this conversation.** Do not proceed to prompt generation.
2. Run the adversarial-review protocol in a separate conversation (using the
   Adversarial Review Input Package from Phase C, step 7).
3. If the adversarial review produces required revisions:
   a. Open a third conversation (or continue in this one if context allows).
   b. Resolve each finding (Critical first, then Significant).
   c. Update the Sprint Spec, Specification by Contradiction, Session Breakdown,
      Escalation Criteria, Regression Checklist, and Doc Update Checklist as needed.
   d. Produce a brief Revision Rationale document logging each decision.
4. Proceed to Phase D with the final (post-revision) spec-level artifacts.

If adversarial review was NOT warranted: proceed directly to Phase D.

### Phase D: Generate Prompts

With finalized spec-level artifacts in hand, generate prompts:

1. **Review Context File** -- a single shared document containing:
   - Review instructions (read-only, follow review skill)
   - The full Sprint Spec (embedded, not referenced)
   - The full Specification by Contradiction (embedded)
   - The Sprint-Level Escalation Criteria (embedded)
   - The Sprint-Level Regression Checklist (embedded)

   This file is written once and referenced by all session review prompts.
   It should be saved with a clear name (e.g., `review-context.md`).

2. For each session:
   a. **Implementation Prompt** (using templates/implementation-prompt.md).
      The Sprint-Level Regression Checklist and Escalation Criteria should
      be embedded directly in each implementation prompt (the implementer
      does not have the review context file).

      If this sprint adds new config fields, include in the implementation
      prompt for the relevant session: "Write a test that loads the YAML
      config file and verifies all keys under the new section are recognized
      by the Pydantic model (no silently ignored fields)."

   b. **Tier 2 Review Prompt** (using templates/review-prompt.md) -- a
      **small, session-specific file** that:
      - Points Claude Code to the Review Context File by path
        (e.g., "Read `sprint-22/review-context.md` for the Sprint Spec,
        Spec by Contradiction, regression checklist, and escalation criteria.")
      - Contains the Tier 1 Close-Out Report placeholder (only blank field)
      - Contains the session-specific review scope (diff range, test command,
        files that should not have been modified)
      - Contains session-specific review focus items

   The developer's workflow for each review: paste the small session review
   prompt into Claude Code, paste the Tier 1 Close-Out Report into the
   placeholder. Claude Code reads the Review Context File itself. No other
   assembly required.

3. **Work Journal Handoff Prompt** -- a self-contained document that the
   developer pastes into a fresh Claude.ai conversation to create the
   Sprint Work Journal (see in-flight-triage.md). The handoff prompt
   must include:
   - Sprint goal and scope summary
   - Session breakdown table (session, scope, creates, modifies, score)
   - Session dependency chain
   - "Do not modify" file list
   - Issue category definitions (from in-flight-triage.md, summarized)
   - Escalation triggers (from Sprint-Level Escalation Criteria)
   - Reserved DEC/RSK/DEF numbers

   The developer opens the work journal conversation before starting
   Session 1 and brings issues to it throughout the sprint.

After each artifact: save it, confirm saved, then request the next.

### Phase E: Verify

After all artifacts are generated:

    "Review all generated artifacts against the design summary. Flag any
    inconsistencies, gaps, or mismatches between the spec and the prompts."

---

## Workflow Mode Integration

### If Adversarial Review is warranted:
Follow the Phase C-1 gate described above. The key principle: **spec-level
artifacts are generated before the adversarial review; prompts are generated
after.** This prevents generating prompts twice.

The Adversarial Review Input Package (Phase C, step 7) must be generated
during Phase C so the developer has everything needed to start the adversarial
review without additional preparation.

### If Iterative Judgment Loop is needed:
Modify the session breakdown:
- Plan shorter, more numerous sessions
- Budget 2-3x more sessions than equivalent backend work
- Include screenshot/visual verification steps in each implementation prompt
- Note specific visual elements to check after each session

### If Synthetic Stakeholder is warranted:
Run it during Phase A of this conversation:

    "Before we finalize the spec, roleplay as [a consumer of this API /
    a user of this interface / a developer integrating with this system].
    What would frustrate you? What would be missing? What would be confusing?"

Incorporate findings into the spec before moving to Phase B.

---

## Quality Checks

Before ending the conversation, verify:
- [ ] Every session prompt has a clear single objective
- [ ] Every session prompt includes pre-flight checks
- [ ] Every session prompt includes explicit file paths and scope boundaries
- [ ] Every session prompt includes "do not modify" constraints
- [ ] Every session prompt ends with close-out skill invocation
- [ ] Every session prompt embeds the Sprint-Level Regression Checklist and
      Escalation Criteria directly (implementer does not have review context file)
- [ ] Every session has a corresponding Tier 2 review prompt
- [ ] Review Context File contains full Sprint Spec, Spec by Contradiction,
      regression checklist, and escalation criteria
- [ ] Every review prompt references the Review Context File by path
- [ ] Every review prompt's only placeholder is the Tier 1 Close-Out Report
- [ ] No session has a compaction risk score of 14 or above (must be split)
- [ ] The regression checklist covers all critical invariants
- [ ] The escalation criteria are specific and evaluable (not vague)
- [ ] The doc update checklist covers every document affected by this sprint
- [ ] Numbering is correct (DEC/RSK/DEF ranges reserved if needed)
- [ ] If adversarial review was warranted: spec-level artifacts reflect all
      revisions; prompts were generated from post-revision specs
- [ ] If adversarial review was warranted: input package was generated with
      relevant architecture sections extracted (developer pastes, not assembles)
- [ ] Every session's Creates/Modifies/Integrates columns are filled in the
      Session Breakdown -- no module is created without a session that integrates it
- [ ] If new config fields are added: YAML field names verified against Pydantic
      model names; regression checklist includes config validation item
- [ ] Frontend sessions with visual review items have a budgeted fix slot
- [ ] Work journal handoff prompt is self-contained (no "paste X here" —
      all sprint context embedded)

---

## Artifact Summary

A complete sprint package contains:

**Spec-level artifacts (Phase C -- generated before adversarial review):**
1. Design Summary (compaction insurance)
2. Sprint Spec
3. Specification by Contradiction
4. Session Breakdown (with Creates/Modifies/Integrates per session)
5. Sprint-Level Escalation Criteria
6. Sprint-Level Regression Checklist
7. Doc Update Checklist
8. Adversarial Review Input Package (if warranted)
9. Revision Rationale (if adversarial review produced changes)

**Prompt-level artifacts (Phase D -- generated after adversarial review):**
10. Review Context File (single shared file)
11. Implementation Prompts (one per session)
12. Tier 2 Review Prompts (one per session, references Review Context File)
13. Work Journal Handoff Prompt (for in-flight triage conversation)

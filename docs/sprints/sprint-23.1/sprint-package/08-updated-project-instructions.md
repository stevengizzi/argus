# Updated Claude.ai Project Instruction Files

> These are the 5 Claude.ai project instruction files that need manual updating
> after Sprint 23.1 completes. Each section below contains the COMPLETE updated
> file content. Download this document, then copy-paste each section to replace
> the corresponding project instruction file.
>
> Alternatively, you can make the targeted edits described in
> `docs/sprints/sprint-23.1/source/modifications/all-modifications.md`.

---

## 1. implementation-prompt.md (Updated)

Changes: Added structured close-out requirement in Close-Out section,
added dynamic test baseline note in Pre-Flight section.

```markdown
# Template: Implementation Prompt

Fill in all bracketed sections. The structure of this prompt is designed to
front-load context, constrain scope, and end with the close-out skill invocation.

---

    # Sprint [N], Session [M]: [Session Title]

    ## Pre-Flight Checks
    Before making any changes:
    1. Read these files to load context:
       - [file path 1]
       - [file path 2]
       - [file path 3]
    2. Run the test suite: [exact test command]
       Expected: [N] tests, all passing
       Note: In autonomous mode, the expected test count is dynamically adjusted
       by the runner based on the previous session's actual results. The count
       above is the planning-time estimate.
    3. Verify you are on the correct branch: [branch name]
    4. [Any other pre-conditions]

    ## Objective
    [1-2 sentences: what this session accomplishes]

    ## Requirements
    [Numbered list of specific changes to make]
    1. In [file path], [specific change with detail]
    2. In [file path], [specific change with detail]
    3. [etc.]

    ## Constraints
    - Do NOT modify: [explicit list of files/modules/functions]
    - Do NOT change: [behaviors, interfaces, contracts to preserve]
    - [Any other constraints]

    ## Canary Tests (if applicable)
    Before making any changes, run the canary-test skill in .claude/skills/canary-test.md
    with these tests:
    - [Test 1: what to assert]
    - [Test 2: what to assert]

    ## Test Targets
    After implementation:
    - Existing tests: all must still pass
    - New tests to write: [list of new tests with what they assert]
    - Minimum new test count: [N]
    - Test command: [exact command]

    ## Config Validation (if this session adds config fields)
    [Include this section when the session adds or modifies YAML config fields
    that map to Pydantic models. Omit entirely for sessions with no config changes.]

    Write a test that loads the YAML config file and verifies all keys under
    the new section are recognized by the Pydantic model. Specifically:
    1. Load [config file path] and extract the [section] keys
    2. Compare against [PydanticModel].model_fields.keys()
    3. Assert no keys are present in YAML that are absent from the model
       (these would be silently ignored by Pydantic and use defaults instead
       of operator-specified values)

    Expected mapping:
    | YAML Key | Model Field |
    |----------|-------------|
    | [yaml_key] | [model_field] |

    ## Visual Review (if applicable)
    [Include this section for any session that modifies UI. Omit entirely for
    backend-only sessions. This tells the developer exactly what to check in
    the browser after the implementation session, separated from code-level
    checks that Claude Code can verify on its own.]

    The developer should visually verify the following after this session:
    1. [What to look at]: [Expected appearance or behavior]
    2. [What to look at]: [Expected appearance or behavior]
    [etc.]

    Verification conditions:
    - [State the app must be in for visual review -- e.g., "with AI enabled",
      "with no API key set", "with sample data loaded"]

    [PLANNING NOTE: When generating implementation prompts, include this section
    for any session that creates or modifies UI components, pages, layouts,
    animations, or user-facing states. The items should be things a human must
    check in a browser -- not things testable via automated tests or grep. Be
    specific about what to look at and what "correct" looks like. If a session
    is backend-only, omit this section entirely.]

    ## Definition of Done
    - [ ] All requirements implemented
    - [ ] All existing tests pass
    - [ ] New tests written and passing
    - [ ] Config validation test passing (if applicable)
    - [ ] Visual review items verified (if applicable)
    - [ ] [Any other completion criteria]

    ## Regression Checklist (Session-Specific)
    After implementation, verify each of these:
    | Check | How to Verify |
    |-------|---------------|
    | [invariant 1] | [command or assertion] |
    | [invariant 2] | [command or assertion] |

    ## Close-Out
    After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

    The close-out report MUST include a structured JSON appendix at the end,
    fenced with ```json:structured-closeout. See the close-out skill for the
    full schema and requirements.

    [OPTIONAL: After close-out, invoke the reviewer subagent:
    @reviewer -- provide the sprint spec, close-out report, and the regression
    checklist below.]

    ## Sprint-Level Regression Checklist (for Tier 2 reviewer)
    [Paste the sprint-level regression checklist here]

    ## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
    [Paste the sprint-level escalation criteria here]
```

---

## 2. review-prompt.md (Updated)

Changes: Added structured verdict requirement in Instructions section.

```markdown
# Template: Tier 2 Review Prompt

This is a small, session-specific file. The shared context (Sprint Spec,
Specification by Contradiction, regression checklist, escalation criteria) lives
in the Review Context File and is referenced by path -- not duplicated here.

---

    # Tier 2 Review: Sprint [N], Session [M]

    ## Instructions
    You are conducting a Tier 2 code review. This is a READ-ONLY session.
    Do NOT modify any files.

    Follow the review skill in .claude/skills/review.md.

    Your review report MUST include a structured JSON verdict at the end,
    fenced with ```json:structured-verdict. See the review skill for the
    full schema and requirements.

    ## Review Context
    Read the following file for the Sprint Spec, Specification by Contradiction,
    Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    [path to review-context.md]

    ## Tier 1 Close-Out Report
    [PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]

    ## Review Scope
    - Diff to review: git diff HEAD~1 (or specify the correct range)
    - Test command: [exact test command]
    - Files that should NOT have been modified: [list]

    ## Session-Specific Review Focus
    [Numbered list of things to check that are specific to this session --
    e.g., "Verify proposals persisted to DB, not memory-only" or
    "Verify WebSocket endpoint is /ws/v1/ai/chat, not SSE"]

    ## Visual Review (if applicable)
    [Include this section for any session that modifies UI. Omit entirely for
    backend-only sessions. These are checks the developer must perform in a
    browser -- they cannot be verified by code review or automated tests alone.]

    The developer should visually verify:
    1. [What to look at]: [Expected appearance or behavior]
    2. [What to look at]: [Expected appearance or behavior]
    [etc.]

    Verification conditions:
    - [State the app must be in for visual review -- e.g., "with AI enabled",
      "with no API key set", "with sample data loaded"]

    [PLANNING NOTE: When generating review prompts, include this section for
    any session that creates or modifies UI components, pages, layouts,
    animations, or user-facing states. Mirror the Visual Review items from the
    corresponding implementation prompt. The developer should be able to look
    at this section and know exactly what to open in a browser and what
    "correct" looks like, without reading the rest of the review prompt. If a
    session is backend-only, omit this section entirely.]

    [PLANNING NOTE: The review skill supports three verdicts: CLEAR (proceed),
    CONCERNS (medium issues, may need triage in autonomous mode), and ESCALATE
    (requires human). Session-specific review focus items should cover the
    scenarios most likely to produce CONCERNS for that particular session.]

    ## Additional Context
    [Any session-specific context the reviewer needs -- e.g., "This is attempt 2
    at fixing the auth bug, check if diagnostic-first was followed" or "This
    session follows Session 1 which set up the data model"]
```

---

## 3. design-summary.md (Updated)

Changes: Added Runner Compatibility section.

```markdown
# Template: Design Summary (Compaction Insurance)

This is the checkpoint artifact produced during sprint planning Phase B.
It must be compact and self-contained -- if context is lost, this document
alone must be sufficient to regenerate the full sprint package.

---

    # Sprint [N] Design Summary

    **Sprint Goal:** [1-2 sentences]

    **Session Breakdown:**
    - Session 1: [scope -- 1 sentence]
      - Creates: [new files]
      - Modifies: [existing files]
      - Integrates: [which prior session's output this wires in, or "N/A"]
    - Session 2: [scope -- 1 sentence]
      - Creates: [new files]
      - Modifies: [existing files]
      - Integrates: [which prior session's output this wires in]
    - Session [N]: [scope -- 1 sentence]
      - Creates: [new files]
      - Modifies: [existing files]
      - Integrates: [which prior session's output this wires in]
    [If frontend sessions with visual review items:]
    - Session [N]f: visual-review fixes — contingency, 0.5 session

    **Key Decisions:**
    - [Decision 1: what and why]
    - [Decision 2: what and why]

    **Scope Boundaries:**
    - IN: [what this sprint does]
    - OUT: [what this sprint does not do]

    **Regression Invariants:**
    - [Invariant 1: what must not break]
    - [Invariant 2: what must not break]

    **File Scope:**
    - Modify: [list of files/modules being changed]
    - Do not modify: [list of files/modules to protect]

    **Config Changes:**
    [If this sprint adds config fields, list each YAML field → Pydantic field mapping.
    If none, write "No config changes."]

    **Test Strategy:**
    - [What new tests, what coverage targets]
    - [Estimated test count using: ~5/new file + ~3/modified file + ~2/endpoint,
      with 2× multiplier for infrastructure sessions]

    **Runner Compatibility:**
    - Mode: [autonomous / human-in-the-loop / either]
    - Parallelizable sessions: [list, or "none"]
    - Estimated token budget: [rough estimate based on session count × avg tokens]
    - Runner-specific escalation notes: [any additional halting conditions]

    **Dependencies:**
    - [What must exist before sessions can run]

    **Escalation Criteria:**
    - [What should trigger Tier 3 review]

    **Doc Updates Needed:**
    - [Which documents need updating after this sprint]

    **Artifacts to Generate:**
    1. Sprint Spec
    2. Specification by Contradiction
    3. Session Breakdown (with Creates/Modifies/Integrates per session)
    4. Implementation Prompt x[N]
    5. Review Prompt x[N]
    6. Escalation Criteria
    7. Regression Checklist
    8. Doc Update Checklist
    9. Runner Configuration (if autonomous mode)
```

---

## 4. in-flight-triage.md (Updated)

Changes: Added "Autonomous Runner Mode" section after Anti-Patterns.

The file is long (134 lines). Rather than reproducing the entire file, here is
the section to APPEND at the very end, after the existing "Anti-Patterns" section:

```markdown
---

## Autonomous Runner Mode

When the sprint is executing under the autonomous runner, the in-flight triage
workflow changes as follows:

### What Changes
- The **Work Journal conversation** is replaced by the runner's `issues.jsonl`
  and auto-generated `work-journal.md`. Issues are classified automatically
  by the Tier 2.5 triage subagent.
- **Category 1 and 2 issues** with clear fixes are handled by auto-inserted
  fix sessions. The runner generates fix prompts from templates.
- **Category 3 Small issues** are handled by auto-inserted micro-fix sessions.
- **Category 3 Substantial and Category 4 issues** cause the runner to HALT
  and notify the developer.

### What Stays the Same
- The Category 1-4 classification system is unchanged
- Fix sessions still go through implementation → review → conformance
- Each fix has its own close-out report
- Doc sync still happens after all sessions complete
- The developer still reviews all accumulated issues post-sprint

### Anti-Patterns (Runner-Specific)
1. **Disabling Tier 2.5 triage to avoid halts.** The triage layer exists
   because autonomous execution cannot make architectural judgments. Disabling
   it converts "safe autonomous" into "reckless autonomous."
2. **Setting max_auto_fixes too high.** More than 3 auto-inserted fix sessions
   per sprint suggests the planning was insufficient. Halt and re-plan.
3. **Not reviewing the issues log post-sprint.** Auto-resolved issues still
   need human review to catch systematic patterns.
```

---

## 5. sprint-planning.md (Updated)

Changes: Added execution mode declaration in Phase A, runner compatibility
assessment in Phase A, parallelizable column in session breakdown, runner
quality checks, runner config artifact.

The file is long (326 lines). Here are the specific additions:

### Addition 0.5: At the beginning of Phase A, add step 0.5:

```markdown
0.5 **Execution mode declaration** -- Declare the intended execution mode:
    autonomous / human-in-the-loop / undecided.

    - **Autonomous:** Skip work journal handoff prompt in Phase D. Generate
      runner config as a sprint artifact. Parallelizable assessment in step
      5.5 is mandatory.
    - **Human-in-the-loop:** Skip runner config generation. Generate work
      journal handoff prompt. Parallelizable flags are informational only.
    - **Undecided (default):** Generate both work journal handoff and runner
      config. Safe default for sprints where the mode has not been decided.
```

### Addition 1: After Phase A step 5 (compaction risk assessment), add step 5.5:

```markdown
5.5 **Runner compatibility assessment** -- For each session:

   a. Confirm the session has machine-parseable acceptance criteria (testable
      assertions, not subjective judgments).

   b. Assign `parallelizable` flag (default: false). Set to true ONLY when:
      - The Creates list has 2+ clearly independent outputs
      - No two outputs modify the same files
      - The session is NOT already at compaction risk 14+
      Justify the flag in the session breakdown.

   c. Confirm the implementation prompt template includes the structured
      close-out requirement (referencing the close-out skill's structured
      appendix section).

   d. Confirm the review prompt template includes the structured verdict
      requirement (referencing the review skill's structured verdict section).
```

### Addition 2: Session Breakdown table adds `Parallelizable` column

In Phase C step 3, the session breakdown table should include:

```
| Session | Scope | Creates | Modifies | Integrates | Score | Parallelizable |
```

### Addition 3: Phase D Quality Checks, append these items:

```markdown
- [ ] Every implementation prompt includes structured close-out requirement
- [ ] Every review prompt includes structured verdict requirement
- [ ] Parallelizable flags are set with justification for all `true` values
- [ ] No session flagged as parallelizable also scores 14+ on compaction risk
- [ ] If autonomous mode planned: runner config has been reviewed
- [ ] If autonomous mode planned: session order in runner config matches
      session breakdown dependency chain
```

### Addition 4: Artifact Summary, add to prompt-level artifacts:

```markdown
14. Runner Configuration (runner-config.yaml, if autonomous mode planned)
```

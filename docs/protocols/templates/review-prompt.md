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
    
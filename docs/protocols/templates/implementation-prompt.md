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

    [OPTIONAL: After close-out, invoke the reviewer subagent:
    @reviewer -- provide the sprint spec, close-out report, and the regression
    checklist below.]

    ## Sprint-Level Regression Checklist (for Tier 2 reviewer)
    [Paste the sprint-level regression checklist here]

    ## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
    [Paste the sprint-level escalation criteria here]

# Template: Spec Conformance Check Prompt

This template is populated by the runner and invoked as a Claude Code subagent.
Placeholders in `{CURLY_BRACES}` are replaced at runtime.

---

    # Spec Conformance Check: Sprint {SPRINT}, After Session {SESSION}

    ## Instructions
    You are performing a spec conformance check. This is a READ-ONLY session.
    Do NOT modify any files.

    Your job: determine whether the cumulative changes across all completed
    sessions conform to the sprint spec and respect the spec-by-contradiction
    boundaries. This is NOT a code review (that already happened). This is a
    design-intent alignment check.

    ## Sprint Spec
    {SPRINT_SPEC}

    ## Specification by Contradiction
    {SPEC_BY_CONTRADICTION}

    ## Session Breakdown (What Was Planned)
    {SESSION_BREAKDOWN}

    ## Sessions Completed So Far
    {COMPLETED_SESSIONS_LIST}

    ## Cumulative Changes

    ### Files Created (cumulative across all completed sessions)
    {CUMULATIVE_FILES_CREATED}

    ### Files Modified (cumulative)
    {CUMULATIVE_FILES_MODIFIED}

    ### Cumulative Diff Summary
    {CUMULATIVE_DIFF_OR_SUMMARY}

    ## Current Session's Close-Out
    ```json
    {CURRENT_CLOSEOUT_JSON}
    ```

    ## Check These Dimensions

    1. **File Scope:** Compare the cumulative files created/modified against the
       session breakdown's Creates/Modifies columns. Flag any unexpected files
       (not planned) or missing files (planned but not created).

    2. **Spec-by-Contradiction Compliance:** Check every "Do NOT" constraint
       in the Specification by Contradiction. Was any violated?

    3. **Naming Consistency:** Are naming patterns consistent across sessions?
       (file names, function names, class names, config keys)

    4. **Integration Wiring:** For sessions that have "Integrates" in the
       session breakdown, verify the integration exists in the diff (imports,
       function calls, route registrations, etc.). Flag any "Creates" from
       prior sessions that should have been integrated by now but weren't.

    5. **Design Intent:** Based on the sprint spec's goal and deliverables,
       is the implementation trending toward achieving them? Or has it drifted
       in a direction that might deliver something different than intended?

    ## Output

    Provide your analysis, then output a structured JSON block:

    ```json:conformance-verdict
    {
      "schema_version": "1.0",
      "sprint": "{SPRINT}",
      "session": "{SESSION}",
      "cumulative_sessions_checked": [{COMPLETED_SESSIONS_ARRAY}],
      "verdict": "CONFORMANT | DRIFT-MINOR | DRIFT-MAJOR",
      "findings": [
        {
          "type": "FILE_SCOPE | SPEC_CONTRADICTION | NAMING | INTEGRATION | DESIGN_INTENT",
          "severity": "INFO | LOW | MEDIUM | HIGH",
          "description": "What was found",
          "details": "Specifics"
        }
      ],
      "file_scope_check": {
        "unexpected_files_created": [],
        "unexpected_files_modified": [],
        "expected_files_missing": []
      },
      "spec_by_contradiction_check": {
        "violations": [],
        "clean": true
      },
      "integration_check": {
        "verified": [],
        "missing": [],
        "not_yet_due": []
      },
      "drift_summary": "One-paragraph summary of conformance status"
    }
    ```

    ## Verdict Guidelines

    **CONFORMANT:** Everything aligns. Proceed with confidence.

    **DRIFT-MINOR:** Small deviations that don't affect sprint goals:
    - A helper function not in the plan but logically appropriate
    - Slightly different parameter naming than spec suggested
    - An extra test file for better organization
    These are acceptable. Log them but don't block progress.

    **DRIFT-MAJOR:** Deviations that could affect sprint goals or future sessions:
    - A module with a different interface than planned
    - A file on the "do not modify" list was changed
    - An out-of-scope feature was implemented
    - A planned integration is missing and should have happened by now
    - The implementation approach diverges significantly from the spec's intent
    These require human review. Recommend halting.

# Template: Tier 2.5 Triage Prompt

This template is populated by the runner and invoked as a Claude Code session.
Placeholders in `{CURLY_BRACES}` are replaced at runtime.

---

    # Tier 2.5 Automated Triage: Sprint {SPRINT}, Session {SESSION}

    ## Instructions
    You are performing automated issue triage. This is a READ-ONLY session.
    Do NOT modify any files. Do NOT run any tests. Do NOT make any code changes.

    Your job: classify the issues found during Session {SESSION} and recommend
    actions for each, following the category system defined below.

    ## Context

    ### Sprint Spec
    {SPRINT_SPEC}

    ### Specification by Contradiction
    {SPEC_BY_CONTRADICTION}

    ### Session Breakdown
    {SESSION_BREAKDOWN}

    ### Current Session's Structured Close-Out
    ```json
    {STRUCTURED_CLOSEOUT}
    ```

    ### Review Verdict (if applicable)
    ```json
    {STRUCTURED_VERDICT_OR_NULL}
    ```

    ### Session Dependency Chain
    Current session: {SESSION}
    Next sessions: {NEXT_SESSIONS}
    Sessions that depend on this session's output: {DEPENDENT_SESSIONS}

    ## Category Definitions

    **Category 1 (In-Session Bug):** Bug in the current session's own code.
    Typos, off-by-one, test failures. Should have been caught in-session.
    → Action: INSERT_FIX (minimal targeted fix)

    **Category 2 (Prior-Session Bug):** Bug in a prior session's code discovered
    during the current session.
    → Action: INSERT_FIX if it blocks downstream sessions. DEFER if nothing
    downstream depends on it.

    **Category 3 Small (Scope Gap — Small):** Extra config field, additional
    validation, one more test case. Belongs to the current session's logical scope.
    → Action: INSERT_FIX (micro-fix, minimal scope)

    **Category 3 Substantial (Scope Gap — Substantial):** New file, new test
    category, interface change, new API endpoint. Significantly beyond the
    session's planned scope.
    → Action: HALT (requires human judgment on scope and priority)

    **Category 4 (Feature Idea):** Improvement or optimization. Not a bug,
    not a gap. "Would be nice."
    → Action: DEFER (log as deferred observation, never insert a session)

    ## Decision Rules

    - When uncertain between INSERT_FIX and HALT, choose HALT (conservative)
    - If an issue requires a new DEC entry, that means HALT (DEC = human judgment)
    - If an issue affects files on the "do not modify" list, that means HALT
    - Maximum {MAX_AUTO_FIXES} fix sessions can be recommended per triage
    - Each fix session should touch at most 2 files and add at most 5 tests
    - Fix sessions must NOT change interfaces that downstream sessions depend on

    ## Required Output

    Produce your analysis, then output a structured JSON block at the end:

    ```json:triage-verdict
    {
      "schema_version": "1.0",
      "sprint": "{SPRINT}",
      "session": "{SESSION}",
      "issues": [
        {
          "description": "...",
          "source": "scope_gap | prior_session_bug | review_finding",
          "category": "CAT_1 | CAT_2 | CAT_3_SMALL | CAT_3_SUBSTANTIAL | CAT_4",
          "action": "INSERT_FIX | DEFER | HALT | LOG_WARNING",
          "rationale": "Why this classification",
          "fix_description": "What the fix session should do (if INSERT_FIX)",
          "blocks_sessions": ["S3a"],
          "defer_target": "Sprint 23.1 (if DEFER)"
        }
      ],
      "overall_recommendation": "PROCEED | INSERT_FIXES_THEN_PROCEED | HALT",
      "fix_sessions_needed": [
        {
          "fix_id": "{SESSION}-fix-1",
          "description": "...",
          "insert_before": "S3a",
          "scope": "Implement FMP pagination loop",
          "affected_files": ["argus/intelligence/fmp_client.py"]
        }
      ],
      "deferred_items": [
        {
          "description": "...",
          "target": "Sprint 23.1",
          "def_entry_needed": true
        }
      ]
    }
    ```

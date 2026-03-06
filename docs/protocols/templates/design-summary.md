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

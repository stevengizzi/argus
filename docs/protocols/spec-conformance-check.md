# Protocol: Spec Conformance Check

**Context:** Claude Code subagent invoked by the Autonomous Sprint Runner
**Referenced by:** DEC-283
**Frequency:** After each session receives CLEAR verdict
**Output:** Conformance verdict (CONFORMANT / DRIFT-MINOR / DRIFT-MAJOR)

---

## Overview

Individual session reviews verify that a session did what it was supposed to do.
The spec conformance check verifies that the *cumulative* result of all sessions
so far still matches the overall sprint design. This catches emergent drift —
small deviations that pass individual reviews but compound across sessions.

The conformance check is **read-only** — it never modifies files.

## When Invoked

After every session that receives a CLEAR (or CONCERNS-then-resolved) verdict,
before the git commit. Specifically, in the runner's execution loop:

```
CLEAR verdict → conformance check → {CONFORMANT → commit} | {DRIFT → warn/halt}
```

## Input Context

The conformance subagent receives:
1. The sprint spec
2. The spec-by-contradiction
3. The cumulative `git diff` from sprint start SHA to current HEAD
4. The session breakdown table (what each session was supposed to do)
5. The current session's structured close-out (for context on latest changes)

**Important:** The cumulative diff grows with each session. For long sprints,
this may become large. If the diff exceeds ~50KB, the conformance check should
focus on file-level changes (which files were created/modified) rather than
line-level diff content, and flag this limitation in its output.

## What It Checks

1. **File scope conformance:** Were only the planned files created and modified?
   Cross-reference the cumulative file list against the session breakdown's
   Creates/Modifies columns.

2. **Spec-by-contradiction violations:** Did any session violate the "do NOT"
   constraints? Check for modifications to protected files, optimization of
   areas marked "do NOT optimize," additions of features marked out-of-scope.

3. **Naming and convention consistency:** Are naming patterns consistent across
   sessions? (e.g., session 1 uses `snake_case` for a module but session 3
   introduces `camelCase` in the same module).

4. **Integration wiring:** For sessions that have an "Integrates" column in
   the session breakdown, verify the integration actually happened (the new
   module is imported and called from the expected location).

5. **Behavioral drift:** Are there patterns suggesting the implementation is
   diverging from the spec's intent? (e.g., the spec says "simple validation"
   but the implementation added a complex state machine).

## Output Schema

```json
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S3a",
  "cumulative_sessions_checked": ["S1a", "S1b", "S2a", "S3a"],
  "verdict": "CONFORMANT",
  "findings": [
    {
      "type": "FILE_SCOPE",
      "severity": "INFO",
      "description": "All files within planned scope",
      "details": null
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
    "verified": ["S1a output integrated in S2a", "S2a output integrated in S3a"],
    "missing": [],
    "not_yet_due": ["S3a output: integration in S4a (upcoming)"]
  },
  "drift_summary": "No significant drift detected. Implementation aligns with sprint spec."
}
```

## Verdict Definitions

**CONFORMANT:** The cumulative implementation matches the sprint spec. No
deviations detected. Runner proceeds.

**DRIFT-MINOR:** Small deviations detected that don't affect correctness or
sprint goals. Examples: slightly different variable naming than spec suggested,
an extra helper function not in the plan, a minor organizational difference.
Runner logs as WARNING, proceeds.

**DRIFT-MAJOR:** Significant deviation from spec that could affect sprint
goals or future sessions. Examples: a module was created with a different
interface than the spec defined, a file on the "do not modify" list was
changed, an out-of-scope feature was added. Runner halts.

## Runner Response

| Verdict | Config Setting | Runner Action |
|---------|---------------|---------------|
| CONFORMANT | — | Proceed, commit |
| DRIFT-MINOR | `drift_minor_action: warn` | Log WARNING notification, proceed, commit |
| DRIFT-MINOR | `drift_minor_action: halt` | Halt for human review |
| DRIFT-MAJOR | — (always halt) | Halt, notify HALTED |

## Performance Considerations

The conformance check adds one Claude Code invocation per session. To keep it
lightweight:
- Use a compact prompt (spec + spec-by-contradiction + file-level diff summary)
- For large diffs, summarize at file level rather than line level
- Target < 30 seconds per check
- If the check itself fails (timeout, no output), log as WARNING and proceed
  (the check is defense-in-depth, not a critical gate)

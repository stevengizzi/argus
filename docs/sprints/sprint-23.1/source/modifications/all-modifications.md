# Modifications to Existing Documents

This document specifies all changes needed to existing protocol, template,
skill, and reference documents to support dual-mode (autonomous + human-in-the-loop)
sprint execution.

Each modification is tagged with the source DEC for traceability.

---

## 1. sprint-planning.md Modifications

**Source:** DEC-278, DEC-289, DEC-296

### Phase A: Think — New Step 0.5 (Mode Declaration, DEC-296)

Add at the beginning of Phase A, before requirements clarification:

```
0.5 **Execution mode declaration** — Declare the intended execution mode:
    autonomous / human-in-the-loop / undecided.

    - **Autonomous:** Skip work journal handoff prompt in Phase D. Generate
      runner config as a sprint artifact. Parallelizable assessment in step
      5.5 is mandatory.
    - **Human-in-the-loop:** Skip runner config generation. Generate work
      journal handoff prompt. Parallelizable flags are informational only.
    - **Undecided (default):** Generate both work journal handoff and runner
      config. Safe default for sprints where the mode hasn't been decided.
```

### Phase A: Think — New Step 5.5 (after Compaction Risk Assessment)

Add after step 5 (compaction risk assessment):

```
5.5 **Runner compatibility assessment** — For each session:

   a. Confirm the session has machine-parseable acceptance criteria (testable
      assertions, not subjective judgments).

   b. Assign `parallelizable` flag (default: false). Set to true ONLY when:
      - The Creates list has 2+ clearly independent outputs
      - No two outputs modify the same files
      - The session is NOT already at compaction risk 14+
      Justify the flag in the session breakdown.

   c. Confirm the implementation prompt template includes the structured
      close-out marker (`<!-- STRUCTURED-CLOSEOUT -->`).

   d. Confirm the review prompt template includes the structured verdict
      marker (`<!-- STRUCTURED-VERDICT -->`).
```

### Phase A: Think — Step 6 Addition

Append to step 6 (config changes assessment):

```
   Also verify that any new config fields are documented in the runner
   config if they affect runner behavior (e.g., new notification channels,
   new triage thresholds).
```

### Phase C: Session Breakdown — New Column

The Session Breakdown artifact adds a `Parallelizable` column:

```
| Session | Scope | Creates | Modifies | Integrates | Score | Parallelizable |
|---------|-------|---------|----------|------------|-------|----------------|
| S1a | ... | ... | ... | ... | 8 | No |
| S2a | ... | ... | ... | ... | 11 | Yes (backend + frontend independent) |
```

### Phase D: Quality Checks — New Items

Add to the quality checks list:

```
- [ ] Every implementation prompt includes `<!-- STRUCTURED-CLOSEOUT -->` marker
- [ ] Every review prompt includes `<!-- STRUCTURED-VERDICT -->` marker
- [ ] Parallelizable flags are set with justification for all `true` values
- [ ] No session flagged as parallelizable also scores 14+ on compaction risk
- [ ] Runner config has been reviewed for this sprint's settings
- [ ] Session order in runner config matches session breakdown dependency chain
```

### Artifact Summary — Addition

Add to the "Prompt-level artifacts" section:

```
14. Runner Configuration (runner-config.yaml for this sprint)
```

---

## 2. implementation-prompt.md Modifications

**Source:** DEC-280, DEC-288

### Close-Out Section — Replacement

Replace the close-out section at the end of the template:

```
## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end.
This appendix follows the structured-closeout-schema and is fenced with:

    ```json:structured-closeout
    { ... }
    ```

The structured appendix must include: session identifier, verdict, test counts
(before/after/new/all_pass), files created and modified, scope additions,
scope gaps (with category and blocking info), prior-session bugs, deferred
observations, doc impacts, and DEC entries needed.

See docs/protocols/schemas/structured-closeout-schema.md for the full schema
and example.
```

### Pre-Flight Checks — Addition

Add note to pre-flight:

```
   Note: In autonomous mode, the expected test count is dynamically adjusted
   by the runner based on the previous session's actual results. The count
   below is the planning-time estimate.
```

---

## 3. review-prompt.md Modifications

**Source:** DEC-281

### Instructions Section — Addition

Append to the Instructions section:

```
Your review report MUST include a structured JSON verdict at the end.
This verdict follows the structured-review-verdict-schema and is fenced with:

    ```json:structured-verdict
    { ... }
    ```

The structured verdict must include: verdict enum (CLEAR/CONCERNS/ESCALATE),
findings array with severity and category, files reviewed, spec conformance
assessment, regression checklist results, and recommended actions.

See docs/protocols/schemas/structured-review-verdict-schema.md for the full
schema and example.
```

---

## 4. .claude/skills/close-out.md Modifications

**Source:** DEC-280

### New Section: Structured Appendix (add at end of skill)

```
## Structured Close-Out Appendix

After producing the human-readable close-out report above, append a machine-
parseable JSON block. This block is used by the autonomous runner for automated
decision-making and by the run-log for structured record-keeping.

Fence the block with:

    ```json:structured-closeout
    {
      "schema_version": "1.0",
      "sprint": "[sprint number]",
      "session": "[session ID]",
      "verdict": "COMPLETE | INCOMPLETE | BLOCKED",
      "tests": {
        "before": [N],
        "after": [N],
        "new": [N],
        "all_pass": true | false
      },
      "files_created": ["path1", "path2"],
      "files_modified": ["path1", "path2"],
      "files_should_not_have_modified": [],
      "scope_additions": [
        {"description": "...", "justification": "..."}
      ],
      "scope_gaps": [
        {
          "description": "...",
          "category": "SMALL_GAP | SUBSTANTIAL_GAP",
          "severity": "LOW | MEDIUM | HIGH",
          "blocks_sessions": ["S3a"],
          "suggested_action": "..."
        }
      ],
      "prior_session_bugs": [
        {
          "description": "...",
          "affected_session": "S1a",
          "affected_files": ["path"],
          "severity": "LOW | MEDIUM | HIGH",
          "blocks_sessions": []
        }
      ],
      "deferred_observations": ["observation 1", "observation 2"],
      "doc_impacts": [
        {"document": "architecture.md", "change_description": "..."}
      ],
      "dec_entries_needed": [
        {"title": "...", "context": "..."}
      ],
      "warnings": [],
      "implementation_notes": "Free-text notes about decisions made during implementation"
    }
    ```

Rules for the structured appendix:
- Always produce it, even in human-in-the-loop mode (for record-keeping)
- The verdict field must match the overall assessment in the human-readable report
- files_should_not_have_modified must be empty for a clean session
- Every scope gap must have a category (SMALL_GAP or SUBSTANTIAL_GAP)
- Prior-session bugs should identify the affected session by ID
- The appendix must be valid JSON (no trailing commas, proper quoting)
```

---

## 5. .claude/skills/review.md Modifications

**Source:** DEC-281

### Modification 5a: Add CONCERNS to Step 2 (Evaluate)

After the "Escalation Criteria Check" subsection in Step 2, add:

```
**Verdict Determination**
Based on all assessments above, determine the verdict:
- **CLEAR:** All categories PASS. No findings with severity HIGH or CRITICAL.
- **CONCERNS:** All critical functions work, but one or more MEDIUM-severity
  findings exist (correctness concerns, test coverage gaps, error handling
  issues that don't rise to spec violation or escalation).
- **ESCALATE:** ANY CRITICAL finding, ANY escalation criterion triggered,
  regression checklist failure, or "do not modify" constraint violation.
```

### Modification 5b: Update Step 3 (Produce Review Report)

Change the verdict line in the report template from:
```
**Verdict:** [CLEAR | ESCALATE]
```
to:
```
**Verdict:** [CLEAR | CONCERNS | ESCALATE]
```

And change the recommendation template from:
```
[If CLEAR: "Proceed to next session."
 If ESCALATE: specific description of what needs Tier 3 review and why.]
```
to:
```
[If CLEAR: "Proceed to next session."
 If CONCERNS: description of medium-severity concerns and recommended actions.
 If ESCALATE: specific description of what needs Tier 3 review and why.]
```

### Modification 5c: New Section — Structured Verdict (add at end of skill)

```
## Structured Review Verdict

After producing the human-readable review report above, append a machine-
parseable JSON block. This block is used by the autonomous runner for automated
decision-making.

Fence the block with:

    ```json:structured-verdict
    {
      "schema_version": "1.0",
      "sprint": "[sprint number]",
      "session": "[session ID]",
      "verdict": "CLEAR | CONCERNS | ESCALATE",
      "findings": [
        {
          "description": "...",
          "severity": "INFO | LOW | MEDIUM | HIGH | CRITICAL",
          "category": "SPEC_VIOLATION | SCOPE_BOUNDARY_VIOLATION | REGRESSION | TEST_COVERAGE_GAP | ERROR_HANDLING | PERFORMANCE | NAMING_CONVENTION | ARCHITECTURE | SECURITY | OTHER",
          "file": "path (optional)",
          "recommendation": "..."
        }
      ],
      "spec_conformance": {
        "status": "CONFORMANT | MINOR_DEVIATION | MAJOR_DEVIATION",
        "notes": "...",
        "spec_by_contradiction_violations": []
      },
      "files_reviewed": ["path1", "path2"],
      "files_not_modified_check": {
        "passed": true | false,
        "violations": []
      },
      "tests_verified": {
        "all_pass": true | false,
        "count": [N],
        "new_tests_adequate": true | false,
        "test_quality_notes": "..."
      },
      "regression_checklist": {
        "all_passed": true | false,
        "results": [
          {"check": "...", "passed": true | false, "notes": "..."}
        ]
      },
      "escalation_triggers": [],
      "recommended_actions": []
    }
    ```

Rules for the structured verdict:
- Always produce it, even in human-in-the-loop mode
- The verdict must match the overall assessment in the human-readable report
- CLEAR: no findings with severity HIGH or CRITICAL
- CONCERNS: one or more MEDIUM findings, no CRITICAL
- ESCALATE: any CRITICAL finding, or specific escalation criteria met
- files_not_modified_check.passed must be false if any protected file was changed
- regression_checklist must reflect actual test execution, not assumptions
```

---

## 5.5. .claude/agents/reviewer.md Modifications

**Source:** DEC-281

### Update Output section

Add CONCERNS to the output description:

```
## Output
Produce the review report as specified in the review skill, between
---BEGIN-REVIEW--- and ---END-REVIEW--- markers. Your verdict will be one of:
- CLEAR: No issues found, proceed to next session
- CONCERNS: Medium-severity issues that should be documented but don't block
- ESCALATE: Critical issues requiring Tier 3 architectural review
```

### Update Critical Reminders

Add:

```
- CONCERNS is for medium-severity findings that don't meet escalation criteria
  but should be documented. Use it when the implementation works but has
  non-trivial issues worth noting for the developer or Tier 2.5 triage.
- When in doubt between CLEAR and CONCERNS, prefer CONCERNS — false positives
  are cheap (triage handles them); missed issues are expensive.
```

---

## 6. in-flight-triage.md Modifications

**Source:** DEC-282, DEC-290

### New Section: Autonomous Runner Mode (add after "Anti-Patterns")

```
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
- The Category 1–4 classification system is unchanged
- Fix sessions still go through implementation → review → conformance
- Each fix has its own close-out report
- Doc sync still happens after all sessions complete
- The developer still reviews all accumulated issues post-sprint

### Anti-Patterns (Runner-Specific)
1. **Disabling Tier 2.5 triage to avoid halts.** The triage layer exists
   because autonomous execution can't make architectural judgments. Disabling
   it converts "safe autonomous" into "reckless autonomous."
2. **Setting max_auto_fixes too high.** More than 3 auto-inserted fix sessions
   per sprint suggests the planning was insufficient. Halt and re-plan.
3. **Not reviewing the issues log post-sprint.** Auto-resolved issues still
   need human review to catch systematic patterns.
```

---

## 7. design-summary.md Modifications

**Source:** DEC-278, DEC-289

### New Section (add after "Escalation Criteria")

```
**Runner Compatibility:**
- Mode: [autonomous / human-in-the-loop / either]
- Parallelizable sessions: [list, or "none"]
- Estimated token budget: [rough estimate based on session count × avg tokens]
- Runner-specific escalation notes: [any additional halting conditions]
```

---

## 8. project-knowledge.md Modifications

**Source:** DEC-278, DEC-290

### Workflow Section — Replace Two-Claude Architecture Paragraph

Replace:
```
**Two-Claude architecture:** Claude.ai (this instance) handles strategic design,
code review, documentation, and decisions. Claude Code handles implementation.
Git is the bridge.
```

With:
```
**Three-tier architecture:** Claude.ai handles strategic design, architectural
review, and planning. Claude Code handles implementation and review execution.
The Autonomous Sprint Runner (Python orchestrator) coordinates the execution
loop between Claude Code sessions, making deterministic proceed/halt decisions
based on structured output. Git is the bridge between all tiers.

In **autonomous mode**, the runner drives the full execution loop. Claude.ai is
invoked only for sprint planning, adversarial review, Tier 3 escalation
resolution, and strategic check-ins. In **human-in-the-loop mode**, the
developer manually drives sessions while the runner optionally provides
structured logging and record-keeping.
```

### Workflow Section — New Subsection

Add after the sprint methodology paragraph:

```
**Autonomous Runner (DEC-278):** Python-based orchestrator at
`scripts/sprint-runner.py`. Reads sprint package, invokes Claude Code CLI per
session, parses structured close-out and review verdicts, makes rule-based
proceed/halt decisions, and maintains full run-log on disk. Supports resume
from any checkpoint. Notifications via ntfy.sh (DEC-279). Tier 2.5 automated
triage for scope gaps and prior-session bugs (DEC-282). Spec conformance check
at session boundaries (DEC-283). Cost tracking with configurable ceiling
(DEC-287). Independent test verification (DEC-291), pre-session file validation
(DEC-292), compaction detection heuristic (DEC-293), and session boundary diff
validation (DEC-294) provide defense-in-depth between sessions. See
`docs/protocols/autonomous-sprint-runner.md`.
```

---

## 9. architecture.md Modifications

**Source:** DEC-278, DEC-284

### System Components — New Entry

Add to the system architecture component list:

```
### Sprint Runner (Autonomous Execution Layer)
- **Location:** `scripts/sprint-runner.py`
- **Purpose:** Orchestrates sprint execution by invoking Claude Code CLI
- **Dependencies:** Claude Code CLI, git, ntfy.sh (optional)
- **State:** `docs/sprints/sprint-{N}/run-log/run-state.json`
- **Config:** `config/runner.yaml`
- **Mode:** Autonomous (full loop) or human-in-the-loop (logging only)
- **Key protocols:** Tier 2.5 triage, spec conformance check, notification
```

### File Structure — Addition

Add to the file structure:

```
├── scripts/
│   └── sprint-runner.py              # Autonomous sprint orchestrator
├── config/
│   └── runner.yaml                   # Runner configuration
```

Add to `docs/sprints/sprint-{N}/`:
```
│   └── run-log/                       # Autonomous runner output (see run-log-spec)
```

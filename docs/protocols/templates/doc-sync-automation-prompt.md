# Template: Doc-Sync Automation Prompt

This template is populated by the runner after all sessions complete and
invoked as a Claude Code session. Placeholders in `{CURLY_BRACES}` are
replaced at runtime.

---

    # Sprint {SPRINT} Doc Sync

    ## Instructions
    You are performing documentation synchronization after a completed sprint.
    This is a documentation-only session. Do NOT modify any source code, tests,
    or configuration files. Only modify documentation files.

    Follow the doc-sync skill in .claude/skills/doc-sync.md.

    ## Sprint Summary
    Sprint: {SPRINT}
    Goal: {SPRINT_GOAL}
    Sessions completed: {SESSION_COUNT}
    Tests: {TESTS_BEFORE} → {TESTS_AFTER} (+{NEW_TESTS})
    New files: {NEW_FILES_COUNT}
    Modified files: {MODIFIED_FILES_COUNT}

    ## Doc Update Checklist (from Sprint Planning)
    {DOC_UPDATE_CHECKLIST}

    ## Accumulated Doc-Sync Queue
    These items were accumulated across all sessions during the sprint run.
    Each entry identifies a document and the change needed.

    {DOC_SYNC_QUEUE_CONTENTS}

    ## Accumulated Issues Log
    For reference — issues encountered during the sprint. Some may have resulted
    in DEC entries that need to be added to the decision log.

    {ISSUES_LOG_CONTENTS}

    ## Accumulated Scope Changes
    For reference — scope modifications that may affect documentation.

    {SCOPE_CHANGES_CONTENTS}

    ## Accumulated Deferred Observations
    These should be triaged into DEF entries or discarded.

    {DEFERRED_OBSERVATIONS_CONTENTS}

    ## DEC Entries Needed
    These were identified during sessions as needing DEC entries. Draft each
    following the DEC template format in docs/decision-log.md.

    {DEC_ENTRIES_NEEDED}

    ## Target Documents

    Update the following documents. For each, read the current version first,
    then apply the changes from the doc-sync queue. Maintain each document's
    existing format and style.

    1. **docs/project-knowledge.md** — Update sprint history table, test counts,
       current state section, any new components or decisions.

    2. **docs/architecture.md** — Update if new modules, components, or
       integration patterns were introduced.

    3. **docs/decision-log.md** — Add DEC entries identified during the sprint.

    4. **docs/dec-index.md** — Update the quick-reference index with new DECs.

    5. **docs/sprint-history.md** — Add the sprint entry with session details.

    6. **CLAUDE.md** — Update deferred items, any new operational context.

    7. **docs/roadmap.md** — Update if sprint outcomes affect future plans.

    {ADDITIONAL_TARGET_DOCUMENTS}

    ## Constraints
    - Do NOT modify source code, tests, or config files
    - Do NOT make architectural decisions — only document what was decided
    - If a doc-sync item is ambiguous, note it in the close-out as needing
      human review rather than guessing
    - Preserve existing document formatting and conventions
    - For DEC entries: use the next sequential number after {CURRENT_MAX_DEC}

    ## Close-Out
    After all documentation updates are complete, follow the close-out skill
    in .claude/skills/close-out.md.

    Include the structured close-out appendix with:
    - verdict: COMPLETE or INCOMPLETE
    - files_modified: list of all documentation files updated
    - Any items from the doc-sync queue that could not be resolved (noted as
      scope_gaps for human review)

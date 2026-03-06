# Protocol: Impromptu Triage

**Context:** Claude.ai conversation (brief) followed by Claude Code implementation
**Frequency:** As needed -- for unplanned work (hotfixes, urgent requests, mid-sprint discoveries)
**Output:** Scoped implementation prompt with full workflow compliance

---

## When to Use
When work arises outside the planned sprint cycle:
- Production hotfixes
- Urgent feature requests (CTO-driven, customer-facing)
- Scope expansions discovered mid-sprint
- Critical bugs found during non-development activities

The goal is to handle urgent work WITHOUT breaking documentation integrity
or skipping review infrastructure.

## Conversation Structure

### 1. Scope the Work

"I have unplanned work that needs to happen now:

[describe the issue/request]

Current sprint: Sprint [N] (in progress / between sprints)
Urgency: [HOTFIX (production down) / URGENT (needed this week) / DISCOVERED (found during sprint)]

Help me scope this into a minimal implementation that can be properly tracked."

### 2. Reserve Numbering

"What is the next available:
- DEC number: [check current max]
- RSK number: [check current max]
- DEF number: [check current max]
- Sprint sub-number: [e.g., if current sprint is 5, this becomes 5.5 or 5.75]"

Assign a sprint sub-number immediately. Never leave impromptu work unnumbered.

### 3. Impact Assessment

"Before we build the implementation prompt, assess:
1. What files will this touch?
2. What could this break? (regression risk assessment)
3. Does this conflict with any in-progress sprint work?
4. Does this change any existing decisions? (check DEC log)
5. Should any planned sprint work be deferred because of this?"

### 4. Generate Implementation Prompt

Generate a complete implementation prompt following the standard template
(templates/implementation-prompt.md), including:
- Pre-flight checks
- Explicit file paths and scope boundaries
- "Do not modify" constraints (especially important for mid-sprint work)
- Close-out skill invocation
- Canary tests if regression risk is high

### 5. Generate Tier 2 Review Prompt

Generate the review prompt. For impromptu work, Tier 2 review is MANDATORY
(higher regression risk than planned work).

---

## Execution

After the triage conversation:
1. Run the implementation prompt in Claude Code
2. Run Tier 2 review (manual session or subagent)
3. If ESCALATE: run Tier 3 review immediately (do not wait for sprint completion)
4. Run doc-sync BEFORE resuming planned sprint work

## Critical Rule
Doc sync happens before the next planned sprint session begins.
Never carry two unsynced states (impromptu work + planned work without
documentation reflecting both).

---

## Output

The triage conversation produces:
1. Sprint sub-number assignment
2. Impact assessment
3. Implementation prompt (with close-out)
4. Tier 2 review prompt
5. Notes on what planned work (if any) needs adjustment

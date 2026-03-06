# Protocol: Tier 3 Architectural Review

**Context:** Claude.ai conversation
**Frequency:** When triggered by Tier 2 escalation, sprint completion, or periodic cadence
**Output:** Architectural assessment, DEC/RSK entries, action items for next sprint

---

## When to Use

**Automatic triggers:**
- Tier 2 review verdict is ESCALATE
- A sprint has completed (all sessions done, all Tier 2 reviews done)
- Periodic cadence (every 3-4 sprints) for project health

**Not needed when:**
- Tier 2 verdict is CLEAR and the sprint is not yet complete -- proceed to next session

## Inputs

Gather before starting the conversation:
1. All Tier 1 close-out reports from the sprint (or the escalated session)
2. All Tier 2 review reports from the sprint (or the escalated session)
3. The Sprint Spec and Specification by Contradiction
4. Current project-knowledge.md and architecture.md

Do NOT provide raw transcripts. The structured reports are the review artifacts.

## Conversation Structure

### 1. Context Loading

"I need a Tier 3 architectural review. Here are the inputs:

Sprint Spec: [paste]
Tier 1 Close-Out(s): [paste]
Tier 2 Review(s): [paste]

Current architecture context: [paste relevant sections]"

### 2. If Triggered by ESCALATE

"The Tier 2 review escalated with these findings:
[paste the ESCALATE findings from the review report]

Evaluate:
1. Is this a real architectural concern or a false positive?
2. If real, what is the impact? (contained to this sprint / affects future sprints / systemic)
3. What is the recommended resolution?
4. Should any existing decisions be revised?"

### 3. Sprint-Level Review (for completed sprints)

"This sprint is complete. All sessions were [CLEAR / mixed]. Review:

1. Did the sprint achieve its stated goals? (check against Sprint Spec)
2. Did the implementation stay within the Specification by Contradiction boundaries?
3. Are there architectural implications from the judgment calls made across sessions?
4. Has the codebase moved in a direction consistent with the architecture document?
5. Were any decisions made during implementation that should be elevated to DECs?"

### 4. Cross-Sprint Concerns

"Looking beyond this sprint:
1. Does anything from this sprint affect upcoming sprint plans?
2. Are there emerging patterns across recent sprints? (growing debt, recurring issues)
3. Should the roadmap be adjusted based on what we learned?
4. Are any risks from the register materializing or becoming more likely?"

### 5. Documentation Reconciliation

"Based on this review:
1. What decisions need to be logged? (DEC entries)
2. What new risks were identified? (RSK entries)
3. What should be deferred? (DEF entries)
4. Does the architecture document need updating?
5. Does the project knowledge document need updating?"

---

## Output

The conversation should produce:
1. Review verdict: PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE
2. New DEC entries for any decisions made or revised
3. New RSK entries for any risks identified
4. Specific updates needed for project documents
5. Guidance for the next sprint planning conversation
6. If REVISE_PLAN: specific changes to the roadmap
7. If PAUSE_AND_INVESTIGATE: what needs investigation and a proposed approach

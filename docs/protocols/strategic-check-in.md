# Protocol: Strategic Check-In

**Context:** Claude.ai conversation
**Frequency:** Every 3-5 sprints, or after significant scope completion
**Output:** Roadmap adjustments, revised assumptions, updated risk assessment

---

## When to Use
- At the cadence specified above (every 3-5 sprints)
- After completing a major project phase or milestone
- When something feels off about project direction
- After a significant external change (dependency update, requirement shift)

## Conversation Structure

### 1. Progress Review

Start with:
"Let us do a strategic check-in for [Project Name]. Here is the current roadmap
and active decisions."

Paste the sprint-roadmap.md and active DECs from project-knowledge.md.

Work through:
- What have we accomplished since the last check-in?
- Are we on track relative to the original plan?
- What took longer or shorter than expected, and why?

### 2. Assumption Audit

List all foundational assumptions from Discovery and early DECs. For each:
- Is this assumption still valid?
- Has anything changed that makes it questionable?
- If we were starting today, would we make the same choice?

### 3. Scope Assessment

- Should the remaining scope expand, narrow, or stay the same?
- Are there features we planned that we should drop or defer?
- Are there features we did not plan that we now need?
- Has our understanding of the problem changed?

### 4. Velocity Calibration

Based on the last N sprints:
- How many sessions per sprint on average?
- How accurate were our session count estimates?
- What types of work take longer than expected?
- Are sessions staying within the compaction window?

Adjust future sprint planning accordingly.

### 5. Risk Register Review

Paste risk-register.md and evaluate:
- Are any OPEN risks now MITIGATED or CLOSED?
- Are there new risks that have emerged?
- Have any risk likelihoods or impacts changed?
- Are we accumulating deferred items faster than resolving them?

### 6. Decision Log Patterns

List recent DECs and look for:
- Patterns (repeatedly deferring the same type of work, etc.)
- Decisions that should be revisited
- Decisions that are creating friction

---

## Output

The conversation should produce:
1. Updated sprint roadmap (revised priorities, added/removed sprints)
2. New or revised DEC entries for any changed assumptions
3. Updated RSK entries (new risks, changed assessments, closures)
4. Velocity notes for future sprint planning
5. Specific action items for the next sprint planning conversation

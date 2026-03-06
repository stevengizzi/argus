# Protocol: In-Flight Triage

**Context:** Claude.ai conversation (Sprint Work Journal)
**Frequency:** Continuously during sprint execution
**Output:** Issue classification, fix prompts, close-out language, DEF entries

---

## When to Use
When anything unexpected arises during sprint implementation:
- A bug in the current session's code
- A bug discovered in a prior session's code
- The spec didn't account for something the implementation needs
- A feature idea or improvement occurs to you mid-session

## Setup

During sprint planning (Phase D of sprint-planning.md), a **Work Journal Handoff
Prompt** is generated alongside implementation and review prompts. This prompt
is pasted into a fresh Claude.ai conversation to create the Sprint Work Journal.
The work journal conversation persists for the duration of the sprint.

If the work journal conversation grows long enough to risk compaction, start a
fresh conversation with the handoff prompt plus a brief "issues so far" summary.

## Issue Categories

### Category 1: In-Session Bug
Small bugs in the current session's own code — typos, off-by-one errors, test
failures during implementation.

**Action:** Fix in the same implementation session. Mention in the close-out
report under standard findings. No additional process overhead.

**Example:** "My test for batch splitting is off by one — the assertion expects
3 batches but the code produces 2."

### Category 2: Prior-Session Bug
A bug in a prior session's code discovered during the current session.

**Action:**
1. Do NOT fix it in the current session — it is outside the session's scope.
2. Finish the current session. Note the bug in the close-out report under
   "Issues in prior sessions."
3. After the current session's Tier 2 review, run a **targeted fix prompt**
   before proceeding to the next session that depends on the broken code.
4. The fix prompt should be minimal: bug description, affected file, proposed
   fix, and regression test. It gets its own close-out.
5. If nothing downstream depends on the buggy code, the fix can be deferred
   to a post-sprint cleanup (Sprint N.1).

**Example:** "While implementing Session 3a, I noticed Session 1b's
build_viable_universe doesn't handle empty FMP responses — it crashes instead
of returning the fallback."

### Category 3: Scope Gap
The spec didn't account for something. The implementation needs something that
was not planned.

**Action depends on size:**

**Small scope gap** (extra config field, additional validation, one more test
case — belongs to the current session's logical change):
- Implement in the current session.
- Document the scope addition in the close-out report under "Scope additions."
- The Tier 2 reviewer will see it and evaluate whether it fits.

**Substantial scope gap** (new file, new test category, changes to files outside
the session's scope boundary, new API endpoint):
- Do NOT squeeze it into the current session.
- Note as "Discovered scope gap" in the close-out report.
- After the session's Tier 2 review, write a **focused follow-up prompt** to
  address it before proceeding to the next dependent session.
- If nothing downstream depends on it, it can wait until a post-sprint cleanup
  (Sprint N.1) or be added to Sprint N.5 scope.

**Example (small):** "The UniverseFilterConfig also needs a max_float field —
I'll add it alongside min_float since I'm already in config.py."

**Example (substantial):** "The FMP batch endpoint returns paginated results
with a nextPage token. We need a pagination loop, but that changes the
FMPReferenceClient interface significantly."

### Category 4: Feature Idea / Improvement
"This would be better if we also..." — not a bug, not required for the sprint
to function.

**Action:**
1. Do NOT build it.
2. Note it in the close-out report under "Deferred observations."
3. These accumulate through the sprint and get triaged during doc-sync:
   - Some become DEF entries
   - Some become Sprint N.5 or N+1 scope
   - Some get dropped as not worth the effort

**Example:** "The routing table could be updated incrementally instead of
rebuilt from scratch. Would be faster but doesn't matter until we have intraday
re-scanning."

---

## Work Journal Conversation Format

When bringing an issue to the work journal, include:
1. **Which session** you are currently in
2. **What you found** (error message, unexpected behavior, missing capability)
3. **Your instinct** on the category (the journal will confirm or reclassify)

The work journal will:
1. Classify the issue
2. Advise on the correct action
3. Draft whatever is needed (fix prompt, close-out language, DEF entry)
4. Maintain a running issue tracker for the sprint

---

## Anti-Patterns

1. **Fixing prior-session bugs in the current session.** This conflates two
   sessions' work in one close-out report and bypasses review for the fix.

2. **Fixing bugs inside a Tier 2 review prompt.** Reviews are read-only.
   Always. No exceptions.

3. **Batching unrelated fixes at sprint end.** Creates an untraceable blob of
   changes with no individual review coverage. Each fix needs its own prompt
   and close-out.

4. **Ignoring scope gaps and hoping they don't matter.** If you noticed it,
   it matters. Log it. The triage decision is "when to fix," not "whether to
   acknowledge."

5. **Building Category 4 ideas mid-sprint.** The sprint scope was planned for
   a reason. Feature ideas go in deferred observations, not in code.

# Protocol: Adversarial Review

**Context:** Claude.ai conversation (separate from sprint planning)
**Frequency:** When flagged during sprint planning
**Output:** "Confirmed -- proceed" or specific spec revisions

---

## When to Use
When sprint planning flags any of the following:
- The sprint makes architectural decisions that will be hard to reverse
- The sprint changes data models or database schemas
- The sprint introduces new integrations or external dependencies
- The sprint makes security-relevant changes
- The sprint changes core interfaces that other components depend on

## Pre-Requisites
- The Sprint Spec is complete (from the sprint-planning protocol)
- The Specification by Contradiction is complete
- The Architecture document is current

## Conversation Structure

### Opening Prompt

    "I need you to adversarially review this sprint spec. Your job is to find
    problems, not to be supportive. Here is the spec:

    [paste Sprint Spec]

    And here is what it explicitly does NOT do:

    [paste Specification by Contradiction]

    Current architecture context:

    [paste relevant Architecture sections or DEC entries]

    Try to break this design. Find the flaws."

### Probing Sequence

Work through these angles. Claude should pursue each aggressively:

**1. Assumption Mining**
    "What assumptions is this spec making that could be wrong? List every
    implicit assumption -- about data, about user behavior, about system state,
    about dependencies, about performance."

**2. Failure Mode Analysis**
    "What are the failure modes? For each component or operation in this spec,
    what happens when it fails? Are there cascade failures? Are there states
    that are hard to recover from?"

**3. Future Regret**
    "What will we regret about this design in 3 months? In 6 months? What
    doors does this close? What technical debt does this introduce?"

**4. Specification Gaps**
    "What is underspecified? Where will the implementer have to make judgment
    calls that could go wrong? What edge cases are not addressed?"

**5. Integration Stress**
    "How does this interact with existing systems? What existing behavior
    could this break? What existing assumptions does this violate?"

**6. Simulated Attack (if security-relevant)**
    "If someone wanted to exploit this design, how would they do it?
    What is the attack surface?"

### Resolution

After the adversarial review, one of two outcomes:

**Outcome A: No critical issues found**
    "Based on this review, are there any issues that would change the
    implementation approach? If not, confirm we should proceed."

Document the confirmation and any minor observations as notes in the sprint package.

**Outcome B: Issues found that require spec changes**
    "Summarize the issues that require spec changes, and propose specific
    revisions to the Sprint Spec."

Take the revisions back to a sprint planning conversation to update the affected
artifacts. If changes are minor, they can be applied directly. If changes are
structural, re-run Phase B and Phase C of the sprint-planning protocol.

---

## Evaluation Criteria

A good adversarial review:
- Finds at least one non-obvious concern (if it finds nothing, it was not aggressive enough)
- Distinguishes between "this is a real risk" and "this is a theoretical concern"
- Proposes concrete mitigations, not just abstract worries
- Does not water down its findings to be polite
- Focuses on the spec as designed, not on alternative architectures

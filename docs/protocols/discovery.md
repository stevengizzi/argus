# Protocol: Discovery

**Context:** Claude.ai conversation(s)
**Frequency:** Once per project, before sprint planning begins
**Output:** Foundational DEC entries, seeded Risk Register, confidence assessment

---

## When to Use
At the start of every new project, before planning Sprint 1. The depth of discovery
scales with domain familiarity. This protocol covers both variants.

## Step 1: Assess Domain Familiarity

Before diving in, calibrate the level of discovery needed:

    "I am starting a new project: [project description].

    My familiarity with this domain: [HIGH / MEDIUM / LOW]
    - HIGH: I have built similar systems before, tech stack is known
    - MEDIUM: Some new territory (new framework, new integration, new target)
    - LOW: Significant unknowns (new domain, unfamiliar infrastructure)

    Based on this assessment, what are the key unknowns we need to resolve
    before we can plan sprints with confidence?"

---

## Variant A: Familiar Domain (1 conversation)

For HIGH familiarity projects. Focus on what is different, not what is known.

### Conversation Flow

**1. Delta Analysis**
    "What is different about this project compared to similar past work?
    New dependencies? Different scale? New deployment target?"

**2. Stack Confirmation**
    "Here is my planned tech stack: [list]. Are there better alternatives
    for this specific project? Any known issues at our expected scale?"

**3. Risk Seeding**
    "Given this scope and stack, what are the most likely risks?
    Where could we get stuck?"

**4. Decision Logging**
    "Let us log the foundational decisions. Format each as a DEC entry:
    - Stack choice: [decision + rationale]
    - Repo structure: [decision + rationale]
    - Deployment target: [decision + rationale]
    - [any other foundational choices]"

### Output
- 3-8 DEC entries covering foundational choices
- 2-5 RSK entries covering known risks
- Confidence assessment: Ready to plan sprints

---

## Variant B: Unfamiliar Domain (2-5 conversations)

For LOW or MEDIUM familiarity projects. Invest heavily before committing.

### Conversation 1: Landscape Survey

    "I am building [description] and I am unfamiliar with [domain].
    I need a landscape survey before making any decisions.

    Help me understand:
    1. What are the standard approaches to building this kind of system?
    2. What are the key infrastructure components I will need?
    3. What are the major providers/services in this space?
    4. What are the common pitfalls for first-time builders?
    5. What would an experienced builder consider non-negotiable?"

Do NOT make decisions in this conversation. Gather information only.

### Conversation 2: Infrastructure Research

For each key infrastructure component identified in Conversation 1:

    "I need to evaluate [component category] for my project.
    My requirements: [specific requirements]
    My constraints: [budget, deployment target, team size, etc.]

    Compare the top 2-3 options. For each:
    - Capabilities and limitations
    - Pricing model
    - API quality and documentation
    - Community/support and lock-in risk
    - Integration complexity with my planned stack"

Produce a Decision Document for each major choice. Do not commit yet.

### Conversation 3: Validation (Critical)

    "Before I commit to any decisions, let us stress-test my assumptions.

    Here is what I am planning: [summary of planned approach]

    1. What could make this plan fundamentally wrong?
    2. What assumptions am I making about infrastructure / data / APIs / scale?
    3. Are there prerequisites I am missing?
    4. Is there a simpler approach I am overlooking?
    5. What is the cheapest experiment I could run to validate the riskiest assumption?"

This is the conversation that prevents ARGUS-style infrastructure pivots.

### Conversations 4-5 (if needed): Deep Dives

For specific areas that remain uncertain after Conversation 3. Common topics:
- Authentication/authorization approach
- Data pipeline architecture
- Third-party API evaluation (hands-on, not just docs)
- Deployment and DevOps strategy
- Performance and scaling analysis

### Output
- 10-25 DEC entries covering all foundational choices
- 5-15 RSK entries covering identified risks
- Decision Documents for major infrastructure choices
- Confidence assessment: Ready / Not ready to plan sprints

---

## Anti-Patterns

1. **Deciding before researching.** In unfamiliar domains, resist the urge to commit
   in Conversation 1. Gather first, decide later.

2. **Research without decisions.** Set a hard limit on discovery conversations and
   force a decision. Endless research is its own failure mode.

3. **Skipping validation.** Conversation 3 (Variant B) is the most valuable. It catches
   plan-level errors that are 10-100x more expensive to fix during implementation.

4. **Under-scoping familiar domains.** Even HIGH familiarity projects should run
   Variant A. "I have done this before" does not mean "no novel risks."

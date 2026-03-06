# Protocol: Retrofit Survey

**Context:** Claude.ai conversation(s) -- Phases 1-2 of the Project Retrofit Playbook
**Frequency:** Once per project being retrofitted
**Output:** Retrofit Assessment, draft DEC/RSK/DEF logs

---

## When to Use
When bringing an existing project (one without proper documentation) into the
metarepo workflow. This protocol covers the Survey and Excavation phases of the
Project Retrofit Playbook.

See the full Retrofit Playbook for the complete 5-phase process. This protocol
covers the conversation-driven portions (Phases 1-2).

## Phase 1: Survey

### Conversation 1: Codebase Inventory

Open a conversation with repo access:

"I need you to survey this codebase and produce an inventory. For each major
component or module, tell me:
1. What it does (inferred from code, not from any existing docs)
2. What it depends on and what depends on it
3. Its approximate size and complexity
4. Whether it has tests, and if so, whether they pass

Also identify: tech stack, repo structure, CI/CD configuration, and any
existing documentation with a currency assessment."

### Documentation Audit (if docs exist)

"For each existing document in this project, assess:
1. Is it current (matches the code)?
2. Is it complete?
3. Is it useful for Claude Code sessions?
4. What is missing?
Rate each: CURRENT / STALE / MISLEADING / ABSENT"

### Gap Analysis

"Based on your survey, identify what is missing for the Workflow Master Template v1.1.
For each required artifact, state: EXISTS_AND_CURRENT / EXISTS_BUT_STALE / MISSING"

Required artifacts: Project Knowledge, Decision Log, Risk Register, Deferred Items,
Sprint Roadmap, Architecture doc, CLAUDE.md, .claude/ directory.

### Survey Output: Retrofit Assessment Document

Compile findings into a structured Retrofit Assessment with: codebase inventory,
documentation status table, key findings, and estimated retrofit effort.

---

## Phase 2: Excavation

### Conversation 2: Decision Extraction

"I need to reconstruct the Decision Log for this project. There are decisions
embedded in this codebase that were never documented. Identify decisions in:

1. Architecture (why this structure, these components, this data flow?)
2. Stack (why these libraries, frameworks, versions?)
3. Data model (why this schema, what tradeoffs does it encode?)
4. API/interfaces (why these endpoints, these formats?)
5. Testing (what is tested, what is not, what was prioritized?)
6. Deployment (why this target, this CI/CD setup?)

For each decision: output in DEC-NNN format. Mark uncertain rationale with [INFERRED]."

IMPORTANT: The developer must review [INFERRED] entries and correct wrong assumptions.

### Conversation 3 (if needed): Risk and Debt Extraction

"Based on the survey and excavated decisions, identify:

Risks:
1. Technical debt embedded in the code
2. Dependency risks (outdated, unmaintained)
3. Coverage gaps in testing
4. Scaling concerns
5. Knowledge risks (hard-to-understand code)
Output each as RSK-NNN.

Deferred items:
1. TODO/FIXME/HACK comments
2. Known limitations in docs or comments
3. Incomplete features
4. Skipped tests
5. Missing error handling
Output each as DEF-NNN."

---

## Developer Review Checkpoint

Before proceeding to Phase 3 (Build) of the Retrofit Playbook:
- [ ] All [INFERRED] DEC entries reviewed and corrected/confirmed
- [ ] RSK entries reviewed for accuracy of impact/likelihood
- [ ] DEF entries reviewed -- any that are no longer relevant removed
- [ ] Retrofit Assessment reviewed for accuracy

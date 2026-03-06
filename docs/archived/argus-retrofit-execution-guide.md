# ARGUS Retrofit: Execution Guide v2

**What this is:** Paste-ready prompts and step-by-step procedure for retrofitting ARGUS.
**Where this happens:** The ARGUS Claude.ai project + Claude Code terminal.

---

## Before You Start

### Files to download from the metarepo project:

**Skills (5 files — go into ARGUS repo .claude/skills/):**
- close-out.md
- review.md
- diagnostic.md
- doc-sync.md
- canary-test.md

(bootstrap-repo.md is not needed — ARGUS already exists.)

**Agents (3 files — go into ARGUS repo .claude/agents/):**
- reviewer.md
- builder.md (future use — install now so it's ready)
- doc-sync-agent.md (future use — install now so it's ready)

**Rules (1 file — goes into ARGUS repo .claude/rules/):**
- universal.md (the Cross-Project Rule Library produced in this conversation)

**Protocols (8 files — go into ARGUS Claude.ai Project Knowledge):**
- sprint-planning.md
- adversarial-review.md
- discovery.md
- strategic-check-in.md
- codebase-health-audit.md
- retrofit-survey.md
- tier-3-review.md
- impromptu-triage.md

**Templates (6 files — go into ARGUS Claude.ai Project Knowledge):**
- sprint-spec.md
- spec-by-contradiction.md
- implementation-prompt.md
- design-summary.md
- review-prompt.md
- decision-entry.md

These are all existing metarepo files. They are copied verbatim — not regenerated.

### What the ARGUS project should already have:
- The current Project Knowledge document (the big one)
- The meta-analysis report

---

## Conversation R1: Survey and Triage

### What it does:
Reads the current ARGUS Project Knowledge, triages it into Tier A vs. Tier B, spot-checks the DECs, and produces the draft Tier A document.

### Open a new conversation in the ARGUS project. Paste this:

---

**START OF R1 PROMPT**

I'm retrofitting this project to use a new workflow system (the "metarepo" workflow). This is NOT an archaeology project — ARGUS already has extensive documentation and a 249-entry decision log. The retrofit is about restructuring and installing tooling, not creating docs from scratch.

Here's what I need you to do in this conversation:

**Phase 1: Read and assess the current Project Knowledge document.**

Read the full Project Knowledge document and produce a triage table. For every major section, classify it as:

- **TIER_A_KEEP**: Operational context that Claude Code needs in every session. Current architecture, active constraints, active rules, current status. This stays in Project Knowledge.
- **TIER_A_COMPRESS**: Information that belongs in Tier A but is currently too verbose. Needs to be condensed (e.g., the full DEC log should become a one-line-per-DEC index).
- **TIER_B_MOVE**: Historical context, rationale, evolution narrative, superseded decisions. Valuable but not needed for daily operations. Moves to repo docs.
- **ARCHIVE**: No longer relevant. Can be dropped entirely.

For each section, note its approximate size and the expected size after triage.

**Phase 2: DEC spot-check.**

From the decision log, read 10 DECs from each project phase:
- Phase A (Sprints 1-5): Check 10 DECs from this range
- Phase B (Sprints 6-11): Check 10 DECs
- Phase C (Sprints 12-13): Check 10 DECs
- Phase D (Sprints 14-20): Check 10 DECs
- Phase E (Sprints 21+): Check 10 DECs

For each batch, assess: Are they complete enough (decision + rationale at minimum)? Are superseded DECs properly marked? Any duplicate numbers or orphaned cross-references?

Report your findings as a summary per phase, not per DEC. I don't need 50 individual assessments — I need "Phase A DECs are [quality level], here's what's notable."

**Phase 3: Capture any post-meta-analysis decisions.**

Check if there are any decisions, changes, or developments from Sprint 21.5 or later (after March 3, 2026) that haven't been formally logged. If yes, draft DEC entries for them.

**Phase 4: Produce the draft Tier A document.**

Based on the triage, produce a DRAFT of the new compressed Tier A Project Knowledge document. This should include:
- Current system architecture (what exists now)
- Active constraints and rules
- Current phase/status
- Active risk register items (drop resolved ones)
- DEC index: one line per decision, format "DEC-NNN: [one-sentence summary]" for all 249+ entries
- Current sprint state and what's next

Target: roughly 50% or less of the current Project Knowledge size. This document needs to be compact because it will share Project Knowledge space with 14 protocol and template files that are part of the new workflow system.

**Phase 5: Produce a standalone DEC index.**

As part of the Tier A document, but also as a standalone artifact I can verify: produce the full DEC index. One line per DEC. Format: DEC-NNN: [decision summary]. All 249+ entries.

At the end, give me a summary of:
- Total estimated size reduction (current vs. proposed Tier A)
- Any issues found during the DEC spot-check
- Any missing decisions captured
- Your confidence level in the draft (high/medium/low) and what would need human review

**END OF R1 PROMPT**

---

### After R1 completes:

1. **Save the draft Tier A document** — copy it out of the conversation.
2. **Save the DEC index** — copy it out.
3. **Review the triage table** — make sure you agree with the Tier A/B/Archive classifications.
4. **Review any [INFERRED] or newly drafted DECs** — correct anything wrong.
5. **Note any issues flagged** — these feed into R2.

---

## Conversation R2: Finalize Tier A, Produce Tier B, Generate ARGUS-Specific Files

### What it does:
Finalizes the Tier A document, produces the Tier B repo docs, generates the ARGUS-specific files that can't be copied from the metarepo (CLAUDE.md, trading-strategies rules, DEC-250, refreshed risk register, new sprint plan).

### Important: R2 does NOT produce skills, agents, protocols, or templates. Those are copied from the metarepo verbatim. R2 only produces things specific to ARGUS.

### Open a new conversation in the ARGUS project. Paste this:

---

**START OF R2 PROMPT**

This is the second conversation of the ARGUS metarepo retrofit. In the previous conversation (R1), I produced a draft Tier A Project Knowledge document and a DEC index. I'm pasting them below.

[PASTE THE DRAFT TIER A DOCUMENT HERE]

[PASTE THE DEC INDEX HERE]

[IF R1 FLAGGED ISSUES, NOTE THEM HERE]

Here's what I need you to do in this conversation. IMPORTANT: I do NOT need you to generate skills, agents, protocols, or template files — those are being copied from a separate metarepo and are already written. I only need ARGUS-specific artifacts from you.

**Phase 1: Finalize the Tier A Project Knowledge document.**

Review the draft Tier A document against what you know about ARGUS. Verify:
- Does it accurately reflect the current system architecture?
- Are the active constraints and rules complete?
- Is any critical operational context missing that Claude Code would need?
- Is the DEC index accurate?

Make corrections and produce the FINAL Tier A document. Remember this document will share Project Knowledge space with 14 other files (8 protocols + 6 templates), so keep it tight.

**Phase 2: Produce the Tier B documentation package.**

Produce the following documents intended for the repo's docs/ directory:
- docs/decision-log.md — the full decision log with complete entries (all 249+ DECs in their original full format, preserving all rationale and alternatives)
- docs/sprint-history.md — a summary of all sprints (1 through 21.5+), what each accomplished, and key events
- docs/process-evolution.md — the Phase A through E narrative from the meta-analysis

These are human-readable historical records. They don't need to be token-efficient.

**Phase 3: Generate ARGUS-specific .claude/rules/ files.**

.claude/rules/trading-strategies.md — Extract any ARGUS-specific strategy constraints, backtesting rules, or trading-domain rules that are currently embedded in Project Knowledge but aren't already covered by backtesting.md. These are rules specific to ARGUS that would NOT apply to other projects. If backtesting.md already covers everything adequately, say so and skip this file.

(Note: .claude/rules/universal.md and .claude/rules/backtesting.md are already handled — universal.md is copied from metarepo, backtesting.md already exists.)

**Phase 4: Generate updated CLAUDE.md.**

Produce a new CLAUDE.md for the repo root that:
- Reflects the Tier A document (current architecture, status, active constraints)
- References the .claude/ directory structure (rules, skills, agents)
- Is optimized for Claude Code session context (dense, actionable, no history)

**Phase 5: DEC-250 and housekeeping.**

Produce DEC-250: "Metarepo workflow retrofit. Process transition point. All future sprints use the metarepo sprint-planning protocol, three-tier review system (close-out + Tier 2 reviewer + Tier 3 architectural review in Claude.ai), and universal rules from .claude/rules/universal.md. Sprint numbering continues from current (next sprint is 22). Documentation split into Tier A (Claude.ai Project Knowledge + .claude/) and Tier B (repo docs/). See docs/process-evolution.md for pre-retrofit history."

Refresh the risk register: list current RSK entries, mark any that are resolved, add any new ones discovered during this retrofit.

Produce a fresh sprint plan / roadmap from the current state forward. What's the next logical sprint for ARGUS? What are the next 3-5 priorities?

**END OF R2 PROMPT**

---

### After R2 completes:

1. **Save the final Tier A document.**
2. **Save the Tier B docs** (decision-log.md, sprint-history.md, process-evolution.md).
3. **Save trading-strategies.md** (if produced).
4. **Save the updated CLAUDE.md.**
5. **Save DEC-250, the refreshed risk register, and the sprint plan.**

---

## Step between R2 and R3: Load Project Knowledge

### What you do (manually, in ARGUS Claude.ai project settings):

1. **Replace** the old monolithic Project Knowledge document with the new Tier A document from R2.

2. **Add** the 8 protocol files as separate Project Knowledge documents:
   - sprint-planning.md
   - adversarial-review.md
   - discovery.md
   - strategic-check-in.md
   - codebase-health-audit.md
   - retrofit-survey.md
   - tier-3-review.md
   - impromptu-triage.md

3. **Add** the 6 template files as separate Project Knowledge documents:
   - sprint-spec.md
   - spec-by-contradiction.md
   - implementation-prompt.md
   - design-summary.md
   - review-prompt.md
   - decision-entry.md

After this step, the ARGUS Claude.ai project should have 15 Project Knowledge files: 1 Tier A document + 8 protocols + 6 templates.

Every future conversation in the ARGUS project will have access to all protocols and templates automatically. No more hunting through the metarepo to find the right file.

---

## Claude Code Session R3: File Installation

### What it does:
Installs all files into the ARGUS repo. Skills and agents are copied from the metarepo files you downloaded. ARGUS-specific files come from R2.

### In your terminal, start a Claude Code session. Paste this:

---

**START OF R3 PROMPT**

I'm installing the metarepo workflow system into this repo. This is a documentation and tooling installation only — do not modify any application code.

Create the following directory structure and files:

**From metarepo (I'll provide content for each):**

.claude/rules/universal.md:
[PASTE UNIVERSAL.MD CONTENT]

.claude/skills/close-out.md:
[PASTE CLOSE-OUT.MD CONTENT]

.claude/skills/review.md:
[PASTE REVIEW.MD CONTENT]

.claude/skills/diagnostic.md:
[PASTE DIAGNOSTIC.MD CONTENT]

.claude/skills/doc-sync.md:
[PASTE DOC-SYNC.MD CONTENT]

.claude/skills/canary-test.md:
[PASTE CANARY-TEST.MD CONTENT]

.claude/agents/reviewer.md:
[PASTE REVIEWER.MD CONTENT]

.claude/agents/builder.md:
[PASTE BUILDER.MD CONTENT]

.claude/agents/doc-sync-agent.md:
[PASTE DOC-SYNC-AGENT.MD CONTENT]

**From ARGUS retrofit R2:**

.claude/rules/trading-strategies.md:
[PASTE IF PRODUCED, OTHERWISE SKIP]

CLAUDE.md:
[PASTE UPDATED CLAUDE.MD FROM R2]

docs/decision-log.md:
[PASTE FROM R2]

docs/sprint-history.md:
[PASTE FROM R2]

docs/process-evolution.md:
[PASTE FROM R2]

**Do not touch:**
- .claude/rules/backtesting.md (already exists, keep as-is)
- Any application code, tests, or existing config files

After creating all files, run the test suite to verify nothing broke. Then commit with message: "[Retrofit] Install metarepo workflow system — DEC-250"

**END OF R3 PROMPT**

---

### After R3 completes:
1. Verify the commit looks right (only new files, no application changes).
2. Verify the test suite still passes.
3. Push.

---

## Conversation R4: Validation Sprint

### What it does:
Plans Sprint 22 using the full metarepo workflow. Proves the retrofit worked.

### Open a new conversation in the ARGUS project. Paste this:

---

**START OF R4 PROMPT**

This is the first sprint planning conversation under the new metarepo workflow. ARGUS was just retrofitted (DEC-250). The Project Knowledge has been restructured into Tier A, and the .claude/ directory is installed with universal rules, skills, and agents. You also have access to all 8 protocols and 6 templates as project knowledge.

Please plan Sprint 22 following the sprint-planning protocol:

1. **Review current state.** Read the Project Knowledge and the sprint plan. What is the highest-priority work?

2. **Sprint design.** Define the sprint scope, break it into sessions (target 1-3 sessions), and identify any architectural risks that warrant an adversarial review.

3. **Design summary checkpoint.** Before generating the full sprint package, produce a compact design summary (compaction insurance). I'll confirm before you proceed.

4. **Produce the sprint package** using the metarepo templates:
   - Sprint Spec (using the sprint-spec template)
   - Specification by Contradiction (using the spec-by-contradiction template)
   - For each session: Implementation Prompt (using the implementation-prompt template, which includes the close-out appendix referencing .claude/skills/close-out.md)
   - For each session: Tier 2 Review Prompt (using the review-prompt template, referencing .claude/agents/reviewer.md)
   - Doc Update Checklist
   - Regression Checklist
   - Escalation Criteria

If this sprint planning conversation runs smoothly with proper template usage and protocol adherence, the retrofit is validated.

**END OF R4 PROMPT**

---

## Full Procedure Summary

| Step | Where | What you do | Time |
|------|-------|-------------|------|
| Download | Metarepo | Download all 20 artifact files (5 skills, 3 agents, 1 rules, 8 protocols, 6 templates) | 5 min |
| R1 | ARGUS Claude.ai | Paste R1 prompt. Save outputs: draft Tier A, DEC index, triage table. Review and correct. | 45-60 min |
| Review | Your desk | Read the draft Tier A. Correct any [INFERRED] items. Note issues for R2. | 15-30 min |
| R2 | ARGUS Claude.ai | Paste R2 prompt with R1 outputs. Save: final Tier A, Tier B docs, CLAUDE.md, trading-strategies.md (if any), DEC-250, risk register, sprint plan. | 60-90 min |
| Load PK | ARGUS Claude.ai settings | Replace old Project Knowledge with Tier A. Add 8 protocol files + 6 template files as Project Knowledge. | 15-20 min |
| R3 | Terminal (Claude Code) | Paste R3 prompt with all file contents. Verify commit and tests. Push. | 15-20 min |
| R4 | ARGUS Claude.ai | Paste R4 prompt. Plan Sprint 22. Validate full workflow. | 30-45 min |

**Total estimated wall-clock time:** 3-5 hours across 1-2 sittings.

---

## What Goes Where (Complete Reference)

### ARGUS Repo (.claude/ directory)
```
.claude/
  rules/
    universal.md            <- copied from metarepo
    backtesting.md          <- already exists, untouched
    trading-strategies.md   <- generated in R2 (if needed)
  skills/
    close-out.md            <- copied from metarepo
    review.md               <- copied from metarepo
    diagnostic.md           <- copied from metarepo
    doc-sync.md             <- copied from metarepo
    canary-test.md          <- copied from metarepo
  agents/
    reviewer.md             <- copied from metarepo
    builder.md              <- copied from metarepo (future use)
    doc-sync-agent.md       <- copied from metarepo (future use)
```

### ARGUS Repo (docs/ directory)
```
docs/
  decision-log.md           <- generated in R2 (Tier B, full DEC history)
  sprint-history.md         <- generated in R2 (Tier B)
  process-evolution.md      <- generated in R2 (Tier B)
```

### ARGUS Claude.ai Project Knowledge (15 files)
```
[Tier A Project Knowledge]   <- generated in R2, replaces old monolithic doc

[Protocols — copied from metarepo]
sprint-planning.md
adversarial-review.md
discovery.md
strategic-check-in.md
codebase-health-audit.md
retrofit-survey.md
tier-3-review.md
impromptu-triage.md

[Templates — copied from metarepo]
sprint-spec.md
spec-by-contradiction.md
implementation-prompt.md
design-summary.md
review-prompt.md
decision-entry.md
```

---

## What Can Go Wrong

**R1 hits compaction before finishing the DEC index.** The DEC index for 249 entries is large. If compaction hits: save whatever was produced, open a fresh conversation, paste the partial index, and ask Claude to continue from where it left off.

**R2 is too large for one conversation.** R2 produces several artifacts, but fewer than v1 since skills/agents/protocols/templates are no longer generated here. If context gets tight: prioritize the Tier A document and CLAUDE.md. The Tier B docs can be produced in a follow-up conversation.

**The Tier A document is still too large.** If the compressed Project Knowledge plus 14 protocol/template files exceeds comfortable Project Knowledge limits: split the Tier A doc into two files (e.g., one for architecture + status, one for the DEC index). Or move the DEC index to its own Project Knowledge file.

**R3 prompt is too large.** You're pasting ~20 files into one prompt. If this exceeds Claude Code's context: split into two sessions. Session 1 installs .claude/ files. Session 2 installs docs/ files and CLAUDE.md.

**R4 reveals gaps.** This is the point of R4. If sprint planning surfaces missing context, missing rules, or broken references — fix them immediately rather than deferring. That's the validation working as intended.

**Protocol/template files add too much context.** If 15 Project Knowledge files proves to be too heavy: keep the most-used ones (sprint-planning, implementation-prompt, review-prompt, close-out, decision-entry) and paste the others on demand for less frequent activities. Start with all 15 and only trim if you observe context pressure.

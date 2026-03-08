# Sprint 23.1, Session 2: Modify Existing Files + DEC Entries

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-23.1/source/modifications/all-modifications.md`
   - `docs/sprints/sprint-23.1/source/decisions/dec-entries.md`
   - `.claude/skills/close-out.md` (current version, to understand where to add)
   - `.claude/skills/review.md` (current version)
   - `.claude/agents/reviewer.md` (current version)
   - `docs/project-knowledge.md` (find the Workflow section)
   - `docs/architecture.md` (find the System Components and File Structure sections)
   - `docs/decision-log.md` (find the last entry, should be DEC-277)
2. Run the test suite: `python -m pytest --tb=short -q && cd ui && npx vitest run && cd ..`
   Expected: ~2101 pytest + ~392 vitest, all passing
3. Verify S1 completed: `ls docs/protocols/autonomous-sprint-runner.md docs/guides/autonomous-process-guide.md`
   Expected: both files exist
4. Verify DEC references are correct: `grep "DEC-278" docs/sprints/sprint-23.1/source/decisions/dec-entries.md`
   Expected: matches found

## Objective
Modify 8 existing repo files to integrate the autonomous runner documentation:
update skills with structured output sections and CONCERNS verdict support,
update the reviewer agent, update reference docs with runner information, and
append 20 DEC entries (DEC-278 through DEC-297) to the decision log.

## Requirements

### 1. Modify `.claude/skills/close-out.md`

Append the "Structured Close-Out Appendix" section at the END of the file.
Content is specified in `all-modifications.md` section 4.

The section adds a `json:structured-closeout` JSON block requirement after the
human-readable close-out report. Include the full schema example, production
rules, and reference to the full schema file.

### 2. Modify `.claude/skills/review.md` (THREE changes)

**2a.** In Step 2 (Evaluate), after the "Escalation Criteria Check" subsection,
add a "Verdict Determination" subsection that defines CLEAR / CONCERNS / ESCALATE:
- CLEAR: All categories PASS, no HIGH or CRITICAL findings
- CONCERNS: One or more MEDIUM-severity findings, no CRITICAL
- ESCALATE: Any CRITICAL finding, any escalation criterion triggered, regression
  failure, or "do not modify" violation

Content specified in `all-modifications.md` section 5a.

**2b.** In Step 3 (Produce Review Report), change the verdict line from:
```
**Verdict:** [CLEAR | ESCALATE]
```
to:
```
**Verdict:** [CLEAR | CONCERNS | ESCALATE]
```

And update the recommendation template to include CONCERNS guidance.
Content specified in `all-modifications.md` section 5b.

**2c.** Append the "Structured Review Verdict" section at the END of the file.
Content specified in `all-modifications.md` section 5c. This adds a
`json:structured-verdict` JSON block requirement with CLEAR/CONCERNS/ESCALATE.

### 3. Modify `.claude/agents/reviewer.md`

Update the Output section to include CONCERNS as a verdict option.
Add to Critical Reminders: CONCERNS is for medium-severity findings,
prefer CONCERNS over CLEAR when in doubt.

Content specified in `all-modifications.md` section 5.5.

### 4. Modify `docs/project-knowledge.md`

Find the Workflow section (contains "Two-Claude architecture"). Replace the
"Two-Claude architecture" paragraph with the three-tier architecture description,
and add the "Autonomous Runner" subsection. Content specified in
`all-modifications.md` section 8.

Keep the existing "Sprint methodology" and "Review workflow" paragraphs
that follow — they remain accurate.

### 5. Modify `docs/architecture.md`

Add the Sprint Runner component entry and update the file structure section.
Content specified in `all-modifications.md` section 9.

### 6. Append DEC entries to `docs/decision-log.md`

Read all DEC entries from:
`docs/sprints/sprint-23.1/source/decisions/dec-entries.md`

Append all 20 entries (DEC-278 through DEC-297) to the end of
`docs/decision-log.md`, maintaining the existing format.

IMPORTANT: Verify that:
- The last existing entry is DEC-277
- The first new entry is DEC-278
- There are no numbering gaps: 278, 279, 280, ..., 296, 297
- There are no collisions with existing entries
- All cross-references use the correct numbers (DEC-278+)

The DEC entries cover:
- DEC-278: Autonomous Sprint Runner Architecture
- DEC-279: Notification via ntfy.sh
- DEC-280: Structured Close-Out Appendix
- DEC-281: Structured Review Verdict
- DEC-282: Tier 2.5 Automated Triage Layer
- DEC-283: Spec Conformance Check
- DEC-284: Run-Log Architecture
- DEC-285: Git Hygiene Protocol
- DEC-286: Runner Retry Policy (with exponential backoff)
- DEC-287: Cost Tracking and Ceiling
- DEC-288: Dynamic Test Baseline Patching
- DEC-289: Session Parallelizable Flag
- DEC-290: Claude.ai Role in Autonomous Mode
- DEC-291: Independent Test Verification
- DEC-292: Pre-Session File Existence Validation
- DEC-293: Compaction Detection Heuristic
- DEC-294: Session Boundary Diff Validation
- DEC-295: Exponential Retry Backoff
- DEC-296: Planning-Time Mode Declaration
- DEC-297: Review Context File Hash Verification

### 7. Update `docs/dec-index.md`

Append 20 new entries to the DEC index. Format should match existing entries:

```
| DEC-278 | Autonomous Sprint Runner Architecture | Active | Sprint 23.1 |
| DEC-279 | Notification via ntfy.sh | Active | Sprint 23.1 |
| DEC-280 | Structured Close-Out Appendix | Active | Sprint 23.1 |
| DEC-281 | Structured Review Verdict | Active | Sprint 23.1 |
| DEC-282 | Tier 2.5 Automated Triage Layer | Active | Sprint 23.1 |
| DEC-283 | Spec Conformance Check | Active | Sprint 23.1 |
| DEC-284 | Run-Log Architecture | Active | Sprint 23.1 |
| DEC-285 | Git Hygiene Protocol | Active | Sprint 23.1 |
| DEC-286 | Runner Retry Policy | Active | Sprint 23.1 |
| DEC-287 | Cost Tracking and Ceiling | Active | Sprint 23.1 |
| DEC-288 | Dynamic Test Baseline Patching | Active | Sprint 23.1 |
| DEC-289 | Session Parallelizable Flag | Active | Sprint 23.1 |
| DEC-290 | Claude.ai Role in Autonomous Mode | Active | Sprint 23.1 |
| DEC-291 | Independent Test Verification | Active | Sprint 23.1 |
| DEC-292 | Pre-Session File Existence Validation | Active | Sprint 23.1 |
| DEC-293 | Compaction Detection Heuristic | Active | Sprint 23.1 |
| DEC-294 | Session Boundary Diff Validation | Active | Sprint 23.1 |
| DEC-295 | Exponential Retry Backoff | Active | Sprint 23.1 |
| DEC-296 | Planning-Time Mode Declaration | Active | Sprint 23.1 |
| DEC-297 | Review Context File Hash Verification | Active | Sprint 23.1 |
```

### 8. Update `docs/sprint-history.md`

Add Sprint 23.1 entry. Use today's date for the sprint history table:

```
| 23.1 | Autonomous Runner Protocol Integration | 2101+392V | [today's date] | DEC-278–297 |
```

And add a scope entry:

```
### Sprint 23.1: Autonomous Runner Protocol Integration
- 15 new documentation files (protocols, schemas, templates, guides)
- Updated close-out and review skills with structured JSON output + CONCERNS verdict
- Updated reviewer agent with CONCERNS support
- 20 DEC entries (DEC-278–297) covering runner architecture and enhancements
- 2 sessions, documentation-only sprint
```

## Constraints
- Do NOT modify: any file under `argus/`, `tests/`, `ui/`, `scripts/`, `config/`
- Do NOT create: any new Python, TypeScript, or test files
- Do NOT alter existing close-out.md or review.md structure — only APPEND new
  sections (for structured output) and make TARGETED edits (for CONCERNS verdict)
- Do NOT modify DEC-277 or any existing DEC entry

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests: none
- Test command: `python -m pytest --tb=short -q && cd ui && npx vitest run`

## Definition of Done
- [ ] close-out.md has "Structured Close-Out Appendix" section
- [ ] review.md has "Verdict Determination" subsection in Step 2 (CLEAR/CONCERNS/ESCALATE)
- [ ] review.md Step 3 shows `[CLEAR | CONCERNS | ESCALATE]` (not just CLEAR/ESCALATE)
- [ ] review.md has "Structured Review Verdict" section at end
- [ ] reviewer.md mentions CONCERNS in Output and Critical Reminders
- [ ] project-knowledge.md references autonomous runner with three-tier architecture
- [ ] architecture.md has runner component
- [ ] decision-log.md has DEC-278 through DEC-297 (20 entries, no gaps)
- [ ] dec-index.md has 20 new entries
- [ ] sprint-history.md has Sprint 23.1 entry
- [ ] All existing tests pass
- [ ] No files modified outside `docs/` and `.claude/`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No source code modified | `git diff --name-only` shows only `docs/` and `.claude/` paths |
| close-out.md has new section | `grep "Structured Close-Out Appendix" .claude/skills/close-out.md` |
| review.md has CONCERNS in prose | `grep "CONCERNS" .claude/skills/review.md` shows matches in Step 2 AND Step 3 |
| review.md has structured section | `grep "Structured Review Verdict" .claude/skills/review.md` |
| reviewer.md has CONCERNS | `grep "CONCERNS" .claude/agents/reviewer.md` |
| DEC entries present | `grep "DEC-297" docs/decision-log.md` returns match |
| DEC index complete | `grep -c "Sprint 23.1" docs/dec-index.md` returns 20 |
| Sprint history updated | `grep "23.1" docs/sprint-history.md` returns match |
| All tests pass | pytest + vitest both pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
| Check | How to Verify |
|-------|---------------|
| No source code modified | `git diff --name-only` shows only `docs/` and `.claude/` paths |
| All pytest pass | `python -m pytest --tb=short -q` |
| All vitest pass | `cd ui && npx vitest run` |
| DEC numbering sequential | Verify DEC-278 through DEC-297 present, no gaps |
| No files outside docs/ and .claude/ | `git diff --name-only \| grep -v '^docs/' \| grep -v '^\\.claude/'` empty |
| New files from S1 still intact | Verify 5 protocol + 4 schema + 4 template + 2 guide files exist |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Escalate if:
1. Any file under `argus/`, `tests/`, `ui/`, `scripts/`, or `config/` is modified
2. DEC numbering collision detected
3. Existing skill file structure altered (not just extended)
4. Any existing test fails
5. Files created in wrong paths

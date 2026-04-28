# Doc-Sync Patch 11 — METAREPO: `protocols/tier-3-review.md`

**Repository:** `claude-workflow` metarepo (NOT the ARGUS repo).
**Local clone path:** `/home/claude/workflow/` (or wherever your local clone lives — typically a sibling dir to `argus`).

**Purpose:** Amend the Tier 3 review protocol's "Output" section to explicitly require "New DEF entries" as a fourth output category, parallel to the existing DEC and RSK entries. Currently the protocol mentions DEF entries in §5 ("Documentation Reconciliation") but the canonical Output schema does NOT enumerate them, which led to Sprint 31.91 Tier 3 review #1 nearly missing Concern C as a DEF candidate.

**Anchor verification (must hold before applying):**
- Line 1: `<!-- workflow-version: 1.0.0 -->`
- Line 2: `<!-- last-updated: 2026-03-12 -->`
- Line 3: `# Protocol: Tier 3 Architectural Review`
- Lines 6-7: `**Context:** Claude.ai conversation` / `**Frequency:** When triggered by Tier 2 escalation, sprint completion, or periodic cadence`
- Line 7 ends with: `**Output:** Architectural assessment, DEC/RSK entries, action items for next sprint`
- Line 83: `## Output`
- Lines 85-92: the existing Output enumeration ("The conversation should produce: 1. ... 7. ...")

---

## Patch A — Update the workflow-version and last-updated headers

### Find:

```
<!-- workflow-version: 1.0.0 -->
<!-- last-updated: 2026-03-12 -->
# Protocol: Tier 3 Architectural Review
```

### Replace with:

```
<!-- workflow-version: 1.0.1 -->
<!-- last-updated: 2026-04-27 -->
# Protocol: Tier 3 Architectural Review
```

---

## Patch B — Update the metadata block to include DEF entries in the Output summary

### Find:

```
**Context:** Claude.ai conversation
**Frequency:** When triggered by Tier 2 escalation, sprint completion, or periodic cadence
**Output:** Architectural assessment, DEC/RSK entries, action items for next sprint
```

### Replace with:

```
**Context:** Claude.ai conversation
**Frequency:** When triggered by Tier 2 escalation, sprint completion, or periodic cadence
**Output:** Architectural assessment, DEC/DEF/RSK entries, action items for next sprint
```

---

## Patch C — Expand the canonical Output enumeration

### Find:

```
## Output

The conversation should produce:
1. Review verdict: PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE
2. New DEC entries for any decisions made or revised
3. New RSK entries for any risks identified
4. Specific updates needed for project documents
5. Guidance for the next sprint planning conversation
6. If REVISE_PLAN: specific changes to the roadmap
7. If PAUSE_AND_INVESTIGATE: what needs investigation and a proposed approach
```

### Replace with:

```
## Output

The conversation should produce:
1. Review verdict: PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE
2. New DEC entries for any decisions made or revised in the sprint just reviewed
3. **New DEF entries for any items carrying forward to sprints other than the one just reviewed.** Tier 3 reviews frequently surface architectural commitments whose natural sprint home is downstream — for example: a follow-on cleanup that belongs to a later component-ownership refactor sprint; a contractual time-bounded fence that must be replaced by a runtime gate when a future reconnect-recovery sprint touches the relevant function; a schema extension forcing function for an in-flight session whose impl prompt was written before the schema gap was noticed. These DEF entries are the canonical mechanism for binding future sprint plans — they land in the project's CLAUDE.md (or equivalent canonical-context file) DEF table, which is the surface every future planner reads. Without explicit DEF entries, Tier-3-surfaced commitments rely on prose in the verdict artifact alone, which planners may or may not read. Enumerate every Tier 3 finding that has a sprint home other than the one just reviewed; file each as a DEF with sprint-gating text where appropriate.
4. New RSK entries for any risks identified (especially time-bounded contracts: docstring fences, lock-step constraints across files, etc.)
5. Specific updates needed for project documents (architecture.md, decision-log.md, dec-index.md, project-knowledge.md, pre-live-transition checklist, live-operations runbook, etc.)
6. Guidance for the next sprint planning conversation
7. **A stable repo verdict artifact** at `docs/sprints/<sprint-name>/tier-3-review-N-verdict.md` (where N is the review iteration within this sprint, starting at 1). This is the file that survives Claude.ai conversation rollover; without it, the verdict exists only in a transcript that may eventually be inaccessible. The verdict artifact should be condensed (~200-400 lines) and include: verdict, sessions reviewed with anchor commit, focus areas with caveats, additional concerns enumerated A through N, inherited follow-ups by sprint, any workflow protocol gaps surfaced. Cross-references to DEC/DEF/RSK entries written in this same review.
8. If REVISE_PLAN: specific changes to the roadmap
9. If PAUSE_AND_INVESTIGATE: what needs investigation and a proposed approach
```

---

## Application notes

- **Three find/replace operations:** version bump (Patch A) + metadata Output line (Patch B) + canonical Output enumeration (Patch C). The enumeration grows from 7 items to 9 items: items 3 and 7 are new (DEF entries; verdict artifact); items 4-9 are renumbered from 3-7.
- **Bold emphasis** on the two new items (DEF entries; verdict artifact) is intentional. These were the two gaps Sprint 31.91 Tier 3 review #1 surfaced. The bold makes them visually distinct from the existing items so a reviewer skim-reading the protocol can't miss them.
- **No change to §5 ("Documentation Reconciliation")** at lines 72-79. That section already mentions DEF entries (line 77). The amendment is to the Output schema at §"Output", which is the canonical "what does Tier 3 produce" enumeration that planners and reviewers read first.
- **Workflow-version bump** from 1.0.0 to 1.0.1 reflects the protocol amendment. The bump is small (no breaking changes; existing Tier 3 verdicts at v1.0.0 remain valid).
- **Origin attribution:** the patch text deliberately doesn't cite "Sprint 31.91 Concern C" inside the protocol document itself, because the metarepo is project-agnostic and shouldn't carry ARGUS-specific commit references. The ARGUS-side documentation (DEF-213 in CLAUDE.md, the verdict artifact) carries that attribution.
- **Commit message suggestion:**

  ```
  protocols(tier-3-review): require DEF entries + verdict artifact in output

  Workflow-version 1.0.0 → 1.0.1.

  Two changes to Output schema:
  - Item 3 (new): DEF entries for items carrying forward to sprints other
    than the one just reviewed. Sprint 31.91 Tier 3 review #1 surfaced
    that the prior schema named DECs/RSKs but not DEFs as canonical
    output, leading to a near-miss on a sprint-gating forcing function.
  - Item 7 (new): stable repo verdict artifact at
    docs/sprints/<sprint>/tier-3-review-N-verdict.md, survives Claude.ai
    transcript rollover.

  Renumbers items 3-7 → 4-9.
  ```

Apply with three surgical replacements. No other lines in `protocols/tier-3-review.md` are touched.

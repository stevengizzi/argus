# Documentation Update Protocol

> **See also:** [workflow/claude/skills/doc-sync.md](../skills/doc-sync.md) —
> this rule covers *per-session* doc hygiene (pre-commit audit). The `doc-sync`
> skill covers *post-sprint* comprehensive doc reconciliation (running numbering
> checks, compression, Work Journal paste). Both apply; neither replaces the
> other.

Argus maintains a family of living documents that must stay accurate as the
system evolves. The canonical index lives in [CLAUDE.md's Reference table](../../CLAUDE.md)
and currently covers roughly a dozen files: decision-log, dec-index,
sprint-history, sprint-campaign, roadmap, project-bible, project-knowledge,
architecture, risk-register, live-operations, pre-live-transition-checklist,
process-evolution, and the UX feature backlog. Outdated docs are worse than no
docs — they create false confidence. This protocol ensures docs stay in sync
with reality.

## When to Update

### After EVERY coding session
Before ending a session, perform a docs audit. Ask yourself:
1. Did I make any decisions that aren't in the Decision Log?
2. Did I discover any new assumptions or risks?
3. Did I change any interfaces, schemas, or APIs documented in Architecture?
4. Did I change any strategy rules documented in the Bible?
5. Does CLAUDE.md's "Current State" still reflect reality?
6. Did I resolve, open, or rename any DEF/DEC/RSK? (See Numbering Hygiene.)

If the answer to any of these is yes, either update the doc directly or output a clear flag:

```
## Docs Update Needed
- docs/decision-log.md: Add DEC-025 — chose websockets library over socket.io for Event Bus. Rationale: lighter weight, stdlib support in Python 3.11+.
- CLAUDE.md: Update Current State to "Phase 1 — Event Bus and BaseStrategy implemented. Working on Risk Manager."
```

### When creating a new module or file
- If it adds to or changes the project structure → update CLAUDE.md project structure section
- If it introduces a new interface → update docs/architecture.md
- If it requires new commands to run → update CLAUDE.md commands section

### When adding a dependency
- Update CLAUDE.md tech stack section
- Note in docs/decision-log.md if it was a meaningful choice (not for trivial packages)

### When a test reveals unexpected behavior
- If it challenges an assumption → update docs/risk-register.md
- If it changes how a component works → update docs/architecture.md

## How to Update

Follow the existing format in each document exactly. Each doc has its own template:
- Decision Log: DEC-XXX entries with date, decision, rationale, alternatives, status
- Risk Register: A-XXX for assumptions, R-XXX for risks, with all fields filled
- Architecture: Match existing section style and detail level
- Bible: Match existing section structure
- CLAUDE.md: Keep it dense. The file is routinely ~250–300 lines and that is
  acceptable — but every line earns its place. If a section exceeds ~5 bullets
  of detail, move detail to `docs/` or `.claude/rules/` and leave a pointer.

## Numbering Hygiene (DEF / DEC / RSK)

- **Verify next number before assignment.** Before assigning `DEC-NNN`, `DEF-NNN`,
  or `RSK-NNN`, check the current highest in the corresponding document. Do
  not assume your memory is current — scan. Duplicate numbers create
  cross-reference breakage that is painful to unwind. (Universal RULE-015.)
- **Resolved DEFs use `~~strikethrough~~` in CLAUDE.md's DEF table.** The
  canonical pattern is `| ~~DEF-NNN~~ | ~~Title~~ | — | **RESOLVED** (context) |`.
  Resolved rows are kept, not deleted — they preserve historical context and
  prevent number reuse. A doc-sync pass must not silently remove resolved
  rows.
- **DEC entries are permanent.** Once a DEC is assigned, its number is never
  reused. If a DEC is superseded, mark it `SUPERSEDED by DEC-NNN` in place;
  do not delete. Rationale: the decision log is append-only history, not
  current state.
- **Sprint-boundary reconciliation.** At sprint close, the doc-sync skill
  runs a duplicate-number check across decision-log / risk-register /
  CLAUDE.md DEF table. See [workflow/claude/skills/doc-sync.md](../skills/doc-sync.md)
  for the full reconciliation protocol.

## Work Journal Reconciliation

The sprint-campaign Work Journal on Claude.ai is the canonical record of
close-outs and Tier 2 reviews. When a coding session completes, the close-out
block (`---BEGIN-CLOSE-OUT---`) and review block (`---BEGIN-REVIEW---`) are
pasted into the Work Journal by the operator. The doc-sync skill uses those
blocks to reconcile CLAUDE.md / decision-log / sprint-history after the
sprint. Do NOT attempt to reconstruct sprint history from `git log` alone —
the Work Journal captures rationale the commit messages cannot.

## What NOT to Do

- Do not skip the docs audit because "it's a small change" — small changes compound
- Do not dump raw implementation details into the Bible — it's for concepts and rules, not code
- Do not let a single CLAUDE.md section balloon — compress or relocate as needed
- Do not update docs with speculative future plans — only document what IS, not what might be
- Do not delete strikethrough/resolved rows during a doc-sync pass
- Do not modify files in the `workflow/` submodule from within the ARGUS
  repository (Universal RULE-018). Those flow metarepo → project, not the
  reverse — including the doc-sync skill itself.

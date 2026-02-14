# Documentation Update Protocol

Argus has six living documents that must stay accurate as the system evolves. Outdated docs are worse than no docs — they create false confidence. This protocol ensures documentation stays in sync with reality.

## When to Update

### After EVERY coding session
Before ending a session, perform a docs audit. Ask yourself:
1. Did I make any decisions that aren't in the Decision Log?
2. Did I discover any new assumptions or risks?
3. Did I change any interfaces, schemas, or APIs documented in Architecture?
4. Did I change any strategy rules documented in the Bible?
5. Does CLAUDE.md's "Current State" still reflect reality?

If the answer to any of these is yes, either update the doc directly or output a clear flag:

```
## Docs Update Needed
- docs/DECISION_LOG.md: Add DEC-025 — chose websockets library over socket.io for Event Bus. Rationale: lighter weight, stdlib support in Python 3.11+.
- CLAUDE.md: Update Current State to "Phase 1 — Event Bus and BaseStrategy implemented. Working on Risk Manager."
```

### When creating a new module or file
- If it adds to or changes the project structure → update CLAUDE.md project structure section
- If it introduces a new interface → update docs/ARCHITECTURE.md
- If it requires new commands to run → update CLAUDE.md commands section

### When adding a dependency
- Update CLAUDE.md tech stack section
- Note in docs/DECISION_LOG.md if it was a meaningful choice (not for trivial packages)

### When a test reveals unexpected behavior
- If it challenges an assumption → update docs/RISK_REGISTER.md
- If it changes how a component works → update docs/ARCHITECTURE.md

## How to Update

Follow the existing format in each document exactly. Each doc has its own template:
- Decision Log: DEC-XXX entries with date, decision, rationale, alternatives, status
- Risk Register: A-XXX for assumptions, R-XXX for risks, with all fields filled
- Architecture: Match existing section style and detail level
- Bible: Match existing section structure
- CLAUDE.md: Keep it lean — if something needs more than 2 sentences, it belongs in docs/

## What NOT to Do

- Do not skip the docs audit because "it's a small change" — small changes compound
- Do not dump raw implementation details into the Bible — it's for concepts and rules, not code
- Do not let CLAUDE.md grow beyond ~150 lines — move detail to docs/ or .claude/rules/
- Do not update docs with speculative future plans — only document what IS, not what might be

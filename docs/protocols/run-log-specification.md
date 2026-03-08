# Reference: Run Log Specification

**Referenced by:** DEC-284
**Location:** `docs/sprints/sprint-{N}/run-log/`

---

## Overview

The run log is the complete audit trail for a sprint execution. Every byte
of output from every Claude Code invocation is preserved on disk immediately.
No LLM context ever holds full sprint history — the run log is the single
source of truth.

## Directory Structure

```
docs/sprints/sprint-{N}/run-log/
├── run-state.json                    # Orchestrator checkpoint (see run-state-schema)
├── runner-config.yaml                # Copy of config used for this run
├── session-S1a/
│   ├── implementation-output.md      # Full Claude Code transcript
│   ├── closeout-report.md            # Human-readable close-out (extracted)
│   ├── closeout-structured.json      # Machine-parseable close-out
│   ├── review-output.md              # Full Claude Code review transcript
│   ├── review-verdict.json           # Machine-parseable verdict
│   ├── conformance-output.md         # Spec conformance check output
│   ├── conformance-verdict.json      # Conformance structured result
│   └── git-diff.patch               # Exact diff this session produced
├── session-S1b/
│   └── ...
├── session-S2a/
│   └── ...
├── session-S2a-fix-1/                # Auto-inserted fix session
│   ├── implementation-output.md
│   ├── closeout-report.md
│   ├── closeout-structured.json
│   ├── review-output.md
│   ├── review-verdict.json
│   ├── conformance-output.md
│   ├── conformance-verdict.json
│   ├── git-diff.patch
│   └── fix-context.json             # Why this fix was inserted
├── triage/
│   ├── S2a-triage-input.json         # What the triage subagent received
│   ├── S2a-triage-output.json        # Triage verdict
│   └── ...
├── doc-sync/
│   ├── doc-sync-prompt.md            # Generated doc-sync prompt
│   └── doc-sync-output.md            # Claude Code doc-sync transcript
├── issues.jsonl                      # Append-only issue log
├── scope-changes.jsonl               # Append-only scope change log
├── doc-sync-queue.jsonl              # Accumulated doc update items
├── deferred-observations.jsonl       # Category 4 items accumulated
└── work-journal.md                   # Auto-generated narrative summary
```

## File Formats

### issues.jsonl

One JSON object per line, appended after each session. Records all issues
discovered across the sprint.

```jsonl
{"timestamp":"2026-03-07T14:30:00Z","session":"S2a","type":"scope_gap","category":"CAT_3_SMALL","description":"FMP needs max_retries config","action":"INSERT_FIX","resolved_by":"S2a-fix-1"}
{"timestamp":"2026-03-07T15:10:00Z","session":"S3a","type":"prior_session_bug","category":"CAT_2","description":"Catalyst init missing null check","action":"DEFER","defer_target":"Sprint 23.1"}
```

### scope-changes.jsonl

Tracks all scope modifications (additions, gaps, inserted sessions).

```jsonl
{"timestamp":"2026-03-07T14:30:00Z","session":"S2a","type":"addition","description":"Added max_retries to CatalystConfig","justification":"FMP API reliability"}
{"timestamp":"2026-03-07T14:35:00Z","session":"S2a","type":"fix_inserted","fix_id":"S2a-fix-1","description":"FMP pagination implementation","inserted_before":"S3a"}
```

### doc-sync-queue.jsonl

Accumulated list of document updates needed, consumed by the doc-sync session.

```jsonl
{"session":"S1a","document":"architecture.md","change":"Add intelligence/ module to file structure"}
{"session":"S2a","document":"decision-log.md","change":"DEC entry for FMP pagination strategy"}
{"session":"S3a","document":"project-knowledge.md","change":"Update monthly costs with FMP Premium"}
```

### deferred-observations.jsonl

Category 4 items — feature ideas, improvements, not bugs or gaps. The runner
enriches the plain string array from the structured close-out by adding
`timestamp` and `session` fields when writing to JSONL.

```jsonl
{"timestamp":"2026-03-07T14:30:00Z","session":"S2a","description":"Could batch FMP calls across symbols for efficiency"}
{"timestamp":"2026-03-07T16:00:00Z","session":"S4a","description":"Catalyst results could feed into Pattern Library visualization"}
```

### work-journal.md

Auto-generated narrative summary, appended after each session. Derived from
structured data — not an LLM generation. Format:

```markdown
# Sprint 23 Work Journal (Auto-Generated)

## Session S1a: NLP Catalyst Core
**Started:** 2026-03-07T14:00:00Z
**Verdict:** COMPLETE → CLEAR → CONFORMANT
**Tests:** 1977 → 2012 (+35)
**Files created:** argus/intelligence/catalyst.py, ...
**Files modified:** argus/config/system.yaml, ...
**Issues:** None
**Duration:** 12m 34s | **Cost est:** $2.40

---

## Session S2a: FMP Integration
**Started:** 2026-03-07T14:15:00Z
**Verdict:** COMPLETE → CLEAR → CONFORMANT
**Tests:** 2012 → 2039 (+27)
**Scope additions:** max_retries config field (justified)
**Scope gaps:** FMP pagination (SUBSTANTIAL — fix session inserted)
**Fix session inserted:** S2a-fix-1 (FMP pagination) before S3a
**Duration:** 15m 12s | **Cost est:** $3.10

---

## Session S2a-fix-1: FMP Pagination Fix
**Started:** 2026-03-07T14:35:00Z
**Inserted by:** Tier 2.5 triage (S2a scope gap)
...
```

### fix-context.json

Stored in each fix session's directory. Records why the fix was inserted.

```json
{
  "source_session": "S2a",
  "source_type": "scope_gap",
  "triage_category": "CAT_3_SMALL",
  "issue_description": "FMP news endpoint returns paginated results",
  "blocks_sessions": ["S3a"],
  "triage_recommendation": "Insert fix session to implement pagination loop"
}
```

## Retention and Git

- The entire run-log directory is committed to git after the sprint completes
- Run logs are never deleted (they are the audit trail)
- Large files (implementation-output.md can be lengthy) are acceptable in git
  for this purpose — these are text files that compress well
- If repo size becomes a concern, old run logs can be archived to a separate
  branch or compressed

## Write Guarantees

All file writes follow this pattern:

```python
def atomic_write(path: str, content: str):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp_path, path)
```

JSONL appends use file locking to prevent corruption from concurrent access
(though the runner is single-threaded, this guards against manual inspection
tools writing simultaneously).

## Mode Behavior

- **Autonomous mode:** Run log is produced automatically by the runner.
- **Human-in-the-loop mode:** The developer can optionally use the runner in
  logging-only mode to produce structured run logs while manually executing
  sessions. This provides the same audit trail without autonomous execution.

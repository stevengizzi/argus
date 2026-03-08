# Schema: Structured Close-Out Appendix

**Referenced by:** DEC-280
**Used by:** Runner (parsing), Tier 2.5 triage (input), doc-sync (input)
**Produced by:** Close-out skill (`.claude/skills/close-out.md`)

---

## Overview

The structured close-out is a JSON block appended to the end of the standard
human-readable close-out report. It provides machine-parseable session outcomes
for the autonomous runner. The human-readable report is always produced first
and remains the primary artifact for human review.

## Extraction

The JSON block is fenced with a labeled code fence for reliable extraction:

````
```json:structured-closeout
{ ... }
```
````

The runner extracts this block via regex: `` ```json:structured-closeout\n(.*?)\n``` ``
(dotall mode). If the block is absent, the session is classified as INCOMPLETE.

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StructuredCloseout",
  "type": "object",
  "required": [
    "schema_version",
    "sprint",
    "session",
    "verdict",
    "tests",
    "files_created",
    "files_modified",
    "scope_additions",
    "scope_gaps",
    "prior_session_bugs",
    "deferred_observations",
    "doc_impacts",
    "dec_entries_needed"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0",
      "description": "Schema version for forward compatibility"
    },
    "sprint": {
      "type": "string",
      "description": "Sprint identifier (e.g., '23', '23.5')"
    },
    "session": {
      "type": "string",
      "description": "Session identifier (e.g., 'S1a', 'S3b', 'S2-fix-1')"
    },
    "verdict": {
      "type": "string",
      "enum": ["COMPLETE", "INCOMPLETE", "BLOCKED"],
      "description": "COMPLETE: all requirements met. INCOMPLETE: partial completion (context limit, unexpected complexity). BLOCKED: cannot proceed without external resolution."
    },
    "tests": {
      "type": "object",
      "required": ["before", "after", "new", "all_pass"],
      "properties": {
        "before": {
          "type": "integer",
          "description": "Total test count before session (pytest + vitest combined)"
        },
        "after": {
          "type": "integer",
          "description": "Total test count after session"
        },
        "new": {
          "type": "integer",
          "description": "Number of new tests written in this session"
        },
        "all_pass": {
          "type": "boolean",
          "description": "Whether all tests pass after the session"
        },
        "pytest_count": {
          "type": "integer",
          "description": "pytest count after session (optional, for granularity)"
        },
        "vitest_count": {
          "type": "integer",
          "description": "vitest count after session (optional, for granularity)"
        }
      }
    },
    "files_created": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of new file paths created in this session"
    },
    "files_modified": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of existing file paths modified in this session"
    },
    "files_should_not_have_modified": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Files modified that were on the 'do not modify' list (empty if compliant)"
    },
    "scope_additions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["description"],
        "properties": {
          "description": { "type": "string" },
          "justification": { "type": "string" }
        }
      },
      "description": "Small scope items added to this session (Category: in-session additions)"
    },
    "scope_gaps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["description", "category", "severity"],
        "properties": {
          "description": {
            "type": "string",
            "description": "What the gap is"
          },
          "category": {
            "type": "string",
            "enum": ["SMALL_GAP", "SUBSTANTIAL_GAP"],
            "description": "SMALL_GAP: extra config field, validation, test case. SUBSTANTIAL_GAP: new file, new API endpoint, interface change."
          },
          "severity": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"],
            "description": "Impact on sprint success if unaddressed"
          },
          "blocks_sessions": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Session IDs that depend on this gap being resolved"
          },
          "suggested_action": {
            "type": "string",
            "description": "Recommended resolution (e.g., 'Insert fix session before S3a', 'Defer to post-sprint')"
          }
        }
      }
    },
    "prior_session_bugs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["description", "affected_session", "affected_files"],
        "properties": {
          "description": { "type": "string" },
          "affected_session": {
            "type": "string",
            "description": "Which prior session introduced the bug"
          },
          "affected_files": {
            "type": "array",
            "items": { "type": "string" }
          },
          "severity": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"]
          },
          "blocks_sessions": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "deferred_observations": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Category 4 items: feature ideas, improvements, not bugs or gaps"
    },
    "doc_impacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["document", "change_description"],
        "properties": {
          "document": {
            "type": "string",
            "description": "Document path or name (e.g., 'architecture.md', 'decision-log.md')"
          },
          "change_description": {
            "type": "string",
            "description": "What needs to change in the document"
          }
        }
      }
    },
    "dec_entries_needed": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "context"],
        "properties": {
          "title": { "type": "string" },
          "context": {
            "type": "string",
            "description": "Enough context for the DEC entry to be written later"
          }
        }
      }
    },
    "warnings": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Any non-blocking concerns or observations"
    },
    "implementation_notes": {
      "type": "string",
      "description": "Free-text notes about implementation decisions made during the session"
    }
  }
}
```

## Example

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S2a",
  "verdict": "COMPLETE",
  "tests": {
    "before": 1977,
    "after": 2012,
    "new": 35,
    "all_pass": true,
    "pytest_count": 2005,
    "vitest_count": 7
  },
  "files_created": [
    "argus/intelligence/catalyst.py",
    "argus/intelligence/catalyst_config.py",
    "tests/intelligence/test_catalyst.py"
  ],
  "files_modified": [
    "argus/config/system.yaml",
    "argus/config/models.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Added max_retries field to CatalystConfig",
      "justification": "FMP API occasionally returns 503; retry logic needed for reliability"
    }
  ],
  "scope_gaps": [
    {
      "description": "FMP news endpoint returns paginated results with nextPage token. Pagination loop not implemented.",
      "category": "SUBSTANTIAL_GAP",
      "severity": "HIGH",
      "blocks_sessions": ["S3a"],
      "suggested_action": "Insert fix session before S3a to implement pagination"
    }
  ],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Could batch FMP calls across symbols for efficiency — not needed now but worth considering for Sprint 24"
  ],
  "doc_impacts": [
    {
      "document": "architecture.md",
      "change_description": "Add intelligence/ module to architecture diagram and file structure"
    },
    {
      "document": "decision-log.md",
      "change_description": "DEC entry for FMP pagination strategy (if resolved in fix session)"
    }
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Used async httpx for FMP calls to match existing Databento async patterns."
}
```

## Validation Rules

The runner validates the structured close-out against these rules before acting:

1. `schema_version` must match the runner's expected version
2. `sprint` and `session` must match the current run context
3. `verdict` must be one of the enum values
4. `tests.after >= tests.before` (test count should not decrease) — if violated,
   log WARNING (tests may be legitimately removed or consolidated)
5. `tests.new == tests.after - tests.before` (consistency check) — if violated,
   log WARNING (not a hard failure; `implementation_notes` may explain removals)
6. `files_should_not_have_modified` must be empty for the session to be
   considered clean (non-empty triggers automatic ESCALATE regardless of verdict)
7. If `verdict` is COMPLETE but `scope_gaps` with `severity: HIGH` exist,
   the runner flags this for Tier 2.5 triage

**Note on verdict axes:** The structured close-out's verdict
(COMPLETE/INCOMPLETE/BLOCKED) measures session *completion status*. The
human-readable self-assessment (CLEAN/MINOR_DEVIATIONS/FLAGGED) measures
implementation *quality*. Both are produced; they are complementary, not
redundant. The runner acts on the structured verdict for proceed/halt decisions.

## Mode Behavior

- **Autonomous mode:** Runner extracts and validates this block automatically.
  Missing block = INCOMPLETE verdict. Invalid block = halt with notification.
- **Human-in-the-loop mode:** The structured block is still produced (for
  record-keeping and optional tooling) but the developer acts on the
  human-readable report as before.

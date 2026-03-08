# Schema: Structured Review Verdict

**Referenced by:** DEC-281
**Used by:** Runner (parsing), Tier 2.5 triage (input if CONCERNS)
**Produced by:** Review skill (`.claude/skills/review.md`)

---

## Overview

The structured review verdict is a JSON block appended to the end of the
standard human-readable review report. It provides a machine-parseable review
outcome for the autonomous runner. The human-readable report is always produced
first and remains the primary artifact for human review.

## Extraction

The JSON block is fenced with a labeled code fence:

````
```json:structured-verdict
{ ... }
```
````

The runner extracts via regex: `` ```json:structured-verdict\n(.*?)\n``` ``
(dotall mode). If the block is absent, the review is classified as INCOMPLETE
and the session is retried.

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StructuredReviewVerdict",
  "type": "object",
  "required": [
    "schema_version",
    "sprint",
    "session",
    "verdict",
    "findings",
    "spec_conformance",
    "files_reviewed",
    "tests_verified"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "sprint": {
      "type": "string",
      "description": "Sprint identifier"
    },
    "session": {
      "type": "string",
      "description": "Session identifier"
    },
    "verdict": {
      "type": "string",
      "enum": ["CLEAR", "CONCERNS", "ESCALATE"],
      "description": "CLEAR: no issues, proceed. CONCERNS: minor issues noted but not blocking. ESCALATE: issues require architectural review or human decision."
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["description", "severity", "category"],
        "properties": {
          "description": {
            "type": "string",
            "description": "What the finding is"
          },
          "severity": {
            "type": "string",
            "enum": ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
            "description": "INFO: observation. LOW: minor style/convention. MEDIUM: correctness concern. HIGH: likely bug or spec violation. CRITICAL: must fix before proceeding."
          },
          "category": {
            "type": "string",
            "enum": [
              "SPEC_VIOLATION",
              "SCOPE_BOUNDARY_VIOLATION",
              "REGRESSION",
              "TEST_COVERAGE_GAP",
              "ERROR_HANDLING",
              "PERFORMANCE",
              "NAMING_CONVENTION",
              "ARCHITECTURE",
              "SECURITY",
              "OTHER"
            ]
          },
          "file": {
            "type": "string",
            "description": "File path where the finding was observed (optional)"
          },
          "recommendation": {
            "type": "string",
            "description": "Suggested resolution"
          }
        }
      }
    },
    "spec_conformance": {
      "type": "object",
      "required": ["status", "notes"],
      "properties": {
        "status": {
          "type": "string",
          "enum": ["CONFORMANT", "MINOR_DEVIATION", "MAJOR_DEVIATION"],
          "description": "Overall conformance with sprint spec and spec-by-contradiction"
        },
        "notes": {
          "type": "string",
          "description": "Details on any deviations"
        },
        "spec_by_contradiction_violations": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Specific items from spec-by-contradiction that were violated"
        }
      }
    },
    "files_reviewed": {
      "type": "array",
      "items": { "type": "string" },
      "description": "All file paths examined during review"
    },
    "files_not_modified_check": {
      "type": "object",
      "required": ["passed", "violations"],
      "properties": {
        "passed": {
          "type": "boolean",
          "description": "Whether all 'do not modify' constraints were respected"
        },
        "violations": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Files that were modified but shouldn't have been"
        }
      }
    },
    "tests_verified": {
      "type": "object",
      "required": ["all_pass", "count"],
      "properties": {
        "all_pass": { "type": "boolean" },
        "count": {
          "type": "integer",
          "description": "Total test count observed by reviewer"
        },
        "new_tests_adequate": {
          "type": "boolean",
          "description": "Whether new test coverage meets the session's test targets"
        },
        "test_quality_notes": {
          "type": "string",
          "description": "Notes on test quality (trivial tests, missing edge cases, etc.)"
        }
      }
    },
    "regression_checklist": {
      "type": "object",
      "required": ["all_passed", "results"],
      "properties": {
        "all_passed": { "type": "boolean" },
        "results": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["check", "passed"],
            "properties": {
              "check": { "type": "string" },
              "passed": { "type": "boolean" },
              "notes": { "type": "string" }
            }
          }
        }
      }
    },
    "escalation_triggers": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Which escalation criteria were met (empty if verdict is CLEAR)"
    },
    "recommended_actions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Reviewer's recommended next steps (especially for CONCERNS/ESCALATE)"
    }
  }
}
```

## Example

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S2a",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "CatalystConfig.max_retries has no upper bound validation",
      "severity": "LOW",
      "category": "ERROR_HANDLING",
      "file": "argus/intelligence/catalyst_config.py",
      "recommendation": "Add validator with max_retries <= 10 in future sprint"
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All deliverables match sprint spec. Scope addition (max_retries) is justified.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/intelligence/catalyst.py",
    "argus/intelligence/catalyst_config.py",
    "argus/config/system.yaml",
    "argus/config/models.py",
    "tests/intelligence/test_catalyst.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 2012,
    "new_tests_adequate": true,
    "test_quality_notes": "Good coverage of happy path and error cases. Edge case for empty API response tested."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      { "check": "Existing strategies unaffected", "passed": true, "notes": "" },
      { "check": "Config validation test passes", "passed": true, "notes": "" },
      { "check": "API startup time < 5s", "passed": true, "notes": "3.2s measured" }
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": []
}
```

## Verdict Decision Rules (for Runner)

The runner acts on the verdict as follows:

| Verdict | Runner Action |
|---------|--------------|
| CLEAR, no HIGH/CRITICAL findings | Proceed to next session |
| CLEAR, but has HIGH findings | Flag as WARNING, proceed (findings logged) |
| CONCERNS | Invoke Tier 2.5 triage to classify findings |
| ESCALATE | Halt immediately, notify HALTED, await human resolution |

Additional automatic escalation (regardless of stated verdict):
- `files_not_modified_check.passed == false` → treat as ESCALATE
- `regression_checklist.all_passed == false` → treat as ESCALATE
- `spec_conformance.status == "MAJOR_DEVIATION"` → treat as ESCALATE

## Mode Behavior

- **Autonomous mode:** Runner extracts and acts on this block automatically.
- **Human-in-the-loop mode:** Block is produced for record-keeping. Developer
  reads the human-readable report and makes their own judgment.

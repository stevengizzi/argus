# Schema: Run State

**Referenced by:** DEC-284, DEC-285
**Used by:** Runner (state management, resume-from-checkpoint)
**Location:** `docs/sprints/sprint-{N}/run-log/run-state.json`

---

## Overview

The run-state file is the orchestrator's checkpoint. It tracks the current
position in the session loop, accumulated results, and everything needed to
resume from any interruption point. Updated after every significant state
transition (session start, session end, review end, triage end, fix insertion).

All writes are atomic (write to `.run-state.json.tmp`, then rename).

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RunState",
  "type": "object",
  "required": [
    "schema_version",
    "sprint",
    "mode",
    "status",
    "session_plan",
    "session_results",
    "git_state",
    "cost",
    "timestamps"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "sprint": {
      "type": "string",
      "description": "Sprint identifier (e.g., '23')"
    },
    "mode": {
      "type": "string",
      "enum": ["autonomous", "human-in-the-loop"],
      "description": "Execution mode for this run"
    },
    "status": {
      "type": "string",
      "enum": [
        "NOT_STARTED",
        "RUNNING",
        "HALTED",
        "COMPLETED",
        "COMPLETED_WITH_WARNINGS",
        "FAILED"
      ],
      "description": "Overall run status"
    },
    "halt_reason": {
      "type": "string",
      "description": "If status is HALTED: why. Null otherwise."
    },
    "current_session": {
      "type": "string",
      "description": "Session ID currently being executed (null if not running)"
    },
    "current_phase": {
      "type": "string",
      "enum": [
        "PRE_FLIGHT",
        "IMPLEMENTATION",
        "CLOSEOUT_PARSE",
        "REVIEW",
        "VERDICT_PARSE",
        "TRIAGE",
        "CONFORMANCE_CHECK",
        "GIT_COMMIT",
        "FIX_SESSION",
        "DOC_SYNC",
        "COMPLETE"
      ],
      "description": "Current phase within the active session"
    },
    "session_plan": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["session_id", "title", "status", "depends_on"],
        "properties": {
          "session_id": { "type": "string" },
          "title": { "type": "string" },
          "status": {
            "type": "string",
            "enum": [
              "PENDING",
              "RUNNING",
              "COMPLETE",
              "FAILED",
              "SKIPPED",
              "INSERTED"
            ]
          },
          "depends_on": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Session IDs this session depends on"
          },
          "parallelizable": {
            "type": "boolean",
            "default": false
          },
          "prompt_file": {
            "type": "string",
            "description": "Path to implementation prompt file"
          },
          "review_prompt_file": {
            "type": "string",
            "description": "Path to review prompt file"
          },
          "inserted_by": {
            "type": "string",
            "description": "If status is INSERTED: which session's triage created this fix session"
          }
        }
      },
      "description": "Ordered session plan (may grow if fix sessions are inserted)"
    },
    "session_results": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "implementation_verdict": {
            "type": "string",
            "enum": ["COMPLETE", "INCOMPLETE", "BLOCKED"]
          },
          "review_verdict": {
            "type": "string",
            "enum": ["CLEAR", "CONCERNS", "ESCALATE"]
          },
          "conformance_verdict": {
            "type": "string",
            "enum": ["CONFORMANT", "DRIFT-MINOR", "DRIFT-MAJOR"]
          },
          "triage_verdict": {
            "type": "string",
            "description": "Tier 2.5 triage result if invoked"
          },
          "retries": {
            "type": "integer",
            "description": "Number of retries for this session"
          },
          "retry_reasons": {
            "type": "array",
            "items": { "type": "string" }
          },
          "tests_before": { "type": "integer" },
          "tests_after": { "type": "integer" },
          "git_sha_before": { "type": "string" },
          "git_sha_after": { "type": "string" },
          "token_usage_estimate": { "type": "integer" },
          "cost_estimate_usd": { "type": "number" },
          "duration_seconds": { "type": "integer" },
          "fix_sessions_inserted": {
            "type": "array",
            "items": { "type": "string" },
            "description": "IDs of fix sessions inserted after this session's triage"
          },
          "output_size_bytes": {
            "type": "integer",
            "description": "Size of implementation output in bytes (DEC-293)"
          },
          "compaction_likely": {
            "type": "boolean",
            "description": "Whether output size exceeded compaction threshold (DEC-293)"
          },
          "compaction_risk_score": {
            "type": "integer",
            "description": "Planning-time compaction risk score for calibration"
          }
        }
      },
      "description": "Keyed by session_id"
    },
    "git_state": {
      "type": "object",
      "required": ["branch", "sprint_start_sha", "current_sha"],
      "properties": {
        "branch": {
          "type": "string",
          "description": "Git branch being used"
        },
        "sprint_start_sha": {
          "type": "string",
          "description": "Git SHA at the start of the sprint run"
        },
        "current_sha": {
          "type": "string",
          "description": "Git SHA after the last committed session"
        },
        "checkpoint_sha": {
          "type": "string",
          "description": "Git SHA of the pre-session checkpoint (for rollback)"
        }
      }
    },
    "cost": {
      "type": "object",
      "required": ["total_tokens_estimate", "total_cost_estimate_usd", "ceiling_usd"],
      "properties": {
        "total_tokens_estimate": {
          "type": "integer",
          "description": "Cumulative token estimate across all sessions"
        },
        "total_cost_estimate_usd": {
          "type": "number",
          "description": "Cumulative estimated cost in USD"
        },
        "ceiling_usd": {
          "type": "number",
          "description": "Cost ceiling from runner config (halt if exceeded)"
        }
      }
    },
    "test_baseline": {
      "type": "object",
      "required": ["initial", "current"],
      "properties": {
        "initial": {
          "type": "integer",
          "description": "Test count at sprint start (from pre-flight)"
        },
        "current": {
          "type": "integer",
          "description": "Test count after last completed session"
        }
      }
    },
    "issues_count": {
      "type": "object",
      "properties": {
        "scope_gaps": { "type": "integer" },
        "prior_session_bugs": { "type": "integer" },
        "deferred_observations": { "type": "integer" },
        "fix_sessions_inserted": { "type": "integer" },
        "warnings": { "type": "integer" }
      }
    },
    "timestamps": {
      "type": "object",
      "required": ["run_started", "last_updated"],
      "properties": {
        "run_started": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 UTC"
        },
        "last_updated": {
          "type": "string",
          "format": "date-time"
        },
        "run_completed": {
          "type": "string",
          "format": "date-time",
          "description": "Set when status transitions to COMPLETED or FAILED"
        }
      }
    },
    "review_context_hash": {
      "type": "string",
      "description": "SHA-256 hash of review context file at sprint start (DEC-297). Used to detect unexpected changes."
    },
    "notifications_sent": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "timestamp": { "type": "string", "format": "date-time" },
          "tier": { "type": "string", "enum": ["HALTED", "SESSION_COMPLETE", "PHASE_TRANSITION", "WARNING", "COMPLETED"] },
          "message": { "type": "string" },
          "channel": { "type": "string" }
        }
      }
    }
  }
}
```

## Resume Protocol

When the runner starts with an existing `run-state.json`:

1. Validate `schema_version` matches runner version
2. Check `status` — only resume if HALTED or RUNNING (crash recovery)
3. Validate `git_state.current_sha` matches actual `git rev-parse HEAD`
   - If mismatch: halt with error "Git state diverged from run-state"
4. Validate `test_baseline.current` by running test suite
   - If mismatch > 5: halt with error "Test count diverged"
   - If mismatch <= 5: warn and update (flaky test tolerance)
5. Resume from `current_session` at `current_phase`
   - If phase is IMPLEMENTATION: re-run the full session (idempotent via git rollback)
   - If phase is REVIEW or later: check if implementation output exists in run-log
   - If implementation output exists: proceed from REVIEW
   - If not: re-run from IMPLEMENTATION

## State Transitions

```
NOT_STARTED → RUNNING (first session starts)
RUNNING → HALTED (escalation, cost ceiling, retry exhaustion, manual pause)
RUNNING → COMPLETED (all sessions CLEAR, doc-sync done)
RUNNING → COMPLETED_WITH_WARNINGS (all sessions done but warnings accumulated)
RUNNING → FAILED (unrecoverable error)
HALTED → RUNNING (human resolves issue, runner resumes)
```

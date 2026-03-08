# Protocol: Tier 2.5 Automated Triage

**Context:** Claude Code subagent invoked by the Autonomous Sprint Runner
**Referenced by:** DEC-282
**Frequency:** When structured close-out contains scope_gaps or prior_session_bugs,
or when review verdict is CONCERNS
**Output:** Structured triage verdict with classifications and recommended actions

---

## Overview

Tier 2.5 sits between the automated Tier 2 review and human-driven Tier 3
review. It uses a Claude Code subagent (LLM judgment in a constrained context)
to classify issues that are too complex for regex rules but too routine for
human attention.

Tier 2.5 is **read-only** — it never modifies files.

## When Invoked

The runner invokes Tier 2.5 when:
1. Structured close-out contains non-empty `scope_gaps` array
2. Structured close-out contains non-empty `prior_session_bugs` array
3. Review verdict is `CONCERNS` (not CLEAR, not ESCALATE)
4. Structured close-out verdict is `COMPLETE` but review has HIGH-severity findings

## Input Context

The triage subagent receives:
1. The sprint spec (from sprint package)
2. The spec-by-contradiction (from sprint package)
3. The session breakdown (from sprint package)
4. The full structured close-out JSON for the current session
5. The structured review verdict JSON (if triggered by review)
6. The current session dependency chain (which sessions come next, what they need)

## Classification Rules

The triage subagent classifies each issue using the Category system from
in-flight-triage.md:

| Category | Definition | Auto Action |
|----------|-----------|-------------|
| **Category 1: In-Session Bug** | Bug in current session's own code — typo, off-by-one, test failure | Should have been fixed in-session. If it wasn't, insert a minimal fix session. |
| **Category 2: Prior-Session Bug** | Bug in a prior session's code discovered during current session | Insert targeted fix session if it blocks downstream sessions. Defer if nothing downstream depends on it. |
| **Category 3: Scope Gap (Small)** | Extra config field, additional validation, one more test case | Insert micro-fix session (same session scope, minimal changes). |
| **Category 3: Scope Gap (Substantial)** | New file, new test category, interface change, new API endpoint | **HALT** — requires human judgment on scope and priority. |
| **Category 4: Feature Idea** | Improvement, optimization, "would be nice" | Defer to post-sprint. Log as deferred observation. Never insert a session. |

## Decision Matrix

```
Issue Category + Severity → Action

Category 1, any severity         → Insert fix session (auto)
Category 2, blocks downstream    → Insert fix session (auto)
Category 2, no downstream impact → Defer to Sprint N.1 (log)
Category 3 Small, any severity   → Insert micro-fix session (auto)
Category 3 Substantial           → HALT for human
Category 4, any                  → Defer (log as deferred observation)

Review CONCERNS, LOW findings    → Log warnings, proceed
Review CONCERNS, MEDIUM findings → Insert fix session if specific fix is clear
Review CONCERNS, HIGH findings   → HALT for human
```

## Output Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TriageVerdict",
  "type": "object",
  "required": ["schema_version", "sprint", "session", "issues", "overall_recommendation"],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0" },
    "sprint": { "type": "string" },
    "session": { "type": "string" },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["description", "source", "category", "action", "rationale"],
        "properties": {
          "description": { "type": "string" },
          "source": {
            "type": "string",
            "enum": ["scope_gap", "prior_session_bug", "review_finding"],
            "description": "Where this issue came from"
          },
          "category": {
            "type": "string",
            "enum": ["CAT_1", "CAT_2", "CAT_3_SMALL", "CAT_3_SUBSTANTIAL", "CAT_4"]
          },
          "action": {
            "type": "string",
            "enum": ["INSERT_FIX", "DEFER", "HALT", "LOG_WARNING"]
          },
          "rationale": {
            "type": "string",
            "description": "Why this classification and action"
          },
          "fix_description": {
            "type": "string",
            "description": "If action is INSERT_FIX: what the fix session should do"
          },
          "blocks_sessions": {
            "type": "array",
            "items": { "type": "string" }
          },
          "defer_target": {
            "type": "string",
            "description": "If action is DEFER: Sprint N.1, DEF entry, etc."
          }
        }
      }
    },
    "overall_recommendation": {
      "type": "string",
      "enum": ["PROCEED", "INSERT_FIXES_THEN_PROCEED", "HALT"],
      "description": "Net recommendation for the runner"
    },
    "fix_sessions_needed": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "fix_id": { "type": "string" },
          "description": { "type": "string" },
          "insert_before": { "type": "string", "description": "Session ID to insert before" },
          "scope": { "type": "string" },
          "affected_files": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "deferred_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": { "type": "string" },
          "target": { "type": "string" },
          "def_entry_needed": { "type": "boolean" }
        }
      }
    }
  }
}
```

## Constraints

1. **Read-only.** The triage subagent never modifies files.
2. **Conservative bias.** When uncertain between INSERT_FIX and HALT, choose HALT.
   False halts waste developer time; false auto-fixes can introduce regressions.
3. **Max auto-fixes.** The runner enforces `triage.max_auto_fixes` from config.
   If this limit is reached, the runner halts regardless of triage recommendation.
4. **No DEC entries.** If the triage determines a DEC entry is needed, that
   automatically means HALT (DEC entries require human judgment per DEC-290).
5. **Audit trail.** Every triage invocation is logged to `issues.jsonl` with
   the full input and output for post-sprint review.

## Calibration

The triage prompt should be calibrated over time based on developer agreement
with its classifications. After each sprint, review the triage log:
- If the developer would have chosen differently, note why
- Adjust the triage prompt's examples and decision criteria accordingly
- Track agreement rate as a quality metric

Target agreement rate: >85% on Category classification, >90% on action.

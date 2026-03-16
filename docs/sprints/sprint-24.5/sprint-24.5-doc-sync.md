# Sprint 24.5 Doc Sync

## Instructions
You are performing documentation synchronization after a completed sprint.
This is a documentation-only session. Do NOT modify any source code, tests,
or configuration files. Only modify documentation files.

Follow the doc-sync skill in .claude/skills/doc-sync.md.

## Sprint Summary
Sprint: 24.5 — Strategy Observability + Operational Fixes
Goal: Give the user real-time and historical visibility into what every
strategy is "thinking" on every candle, so that paper trading validation days
produce actionable diagnostic data even when zero trades occur. Fix three
operational issues identified during live QA.
Sessions completed: 11 (S1, S2, S3, S3.5, S4, S4a-fix, S5, S5f, S5f-fix, S5f-fix2, S6)
Tests: pytest 2,709 → ~2,771 (+62 new), Vitest 503 → 523 (+20 new) — 82 new tests total
New files: 12 (6 source + 6 test)
Modified files: ~20

**Note:** The S6 review's full-suite run reported 2,768 pytest passed. Minor
variation from the arithmetic total (2,771) is likely test collection artifact
from xdist worker count. Verify the actual count with `python -m pytest --co -q | tail -1`
and use that number for project-knowledge.md.

## Doc Update Checklist (from Sprint Planning)

1. project-knowledge.md: Add Sprint 24.5 to sprint history table, update test
   counts, update current state, add telemetry/observability to architecture
   section and Quality Engine section notes.
2. architecture.md: Add Strategy Evaluation Telemetry subsection under Strategies.
   Document EvaluationEventStore, StrategyEvaluationBuffer, ring buffer pattern,
   REST endpoint, and Decision Stream frontend component.
3. decision-log.md: Add DEC-342.
4. dec-index.md: Add DEC-342 entry.
5. sprint-history.md: Add Sprint 24.5 with all 11 session details.
6. CLAUDE.md: Update deferred items if any new DEFs created. Update test counts.
7. roadmap.md: No changes expected — sprint was observability + operational fixes,
   no roadmap impact.

## Accumulated Doc-Sync Queue

### From S1 (Telemetry Infrastructure)
- **project-knowledge.md:** Add to Architecture > Key Components > Strategies:
  "BaseStrategy includes StrategyEvaluationBuffer (ring buffer, maxlen=1000) for
  diagnostic telemetry. record_evaluation() logs decision-point events with
  try/except guard (never raises). REST endpoint GET /api/v1/strategies/{id}/decisions
  returns buffer contents (JWT-protected). EvaluationEventStore provides SQLite
  persistence with 7-day retention and ET-date-based queries."
- **decision-log.md:** Add DEC-342 (see DEC Entries Needed below).
- **architecture.md:** Add Strategy Evaluation Telemetry to the Strategies section.

### From S2 (ORB Family Instrumentation)
- **architecture.md / strategy docs:** Note that all 4 strategies now emit
  evaluation events at every decision point (OR accumulation, finalization,
  exclusion checks, entry conditions, signal generation, quality scoring).

### From S3 (VWAP + AfMo Instrumentation)
- **Note for docs:** AfMo `_check_breakout_entry()` was restructured from
  sequential early-return to evaluate-all-then-check pattern to support 8
  individual CONDITION_CHECK events. Functionally equivalent (63 tests pass),
  but the method structure differs from the original. 3 of 8 AfMo conditions
  (body_ratio, spread_range, time_remaining) are informational-only — they
  emit PASS/FAIL but do not gate the signal.

### From S3.5 (Event Persistence)
- **architecture.md:** EvaluationEventStore in `strategies/telemetry_store.py`.
  SQLite persistence in the main DB file (WAL mode, separate connection).
  7-day retention with ET-date cleanup. Fire-and-forget async forwarding from
  buffer to store via `loop.create_task()`. REST endpoint supports `?date=`
  param for historical queries (routes to store for non-today dates, buffer
  for today). AppState.telemetry_store wired in server lifespan.

### From S4 + S4a (Frontend Decision Stream)
- **architecture.md / frontend section:** StrategyDecisionStream component in
  `features/orchestrator/`. TanStack Query hook (useStrategyDecisions) with
  3s polling. Color-coded event rows (PASS=green, FAIL=red, INFO=amber,
  signals=blue). Symbol filter, summary stats, expandable metadata. Slide-out
  panel on Orchestrator page with AnimatePresence animation + Esc key close.

### From S5 (Orchestrator Integration)
- **architecture.md / frontend:** "View Decisions" button on strategy cards
  opens slide-out panel. Optional `onViewDecisions` callback prop on
  StrategyOperationsCard and StrategyOperationsGrid for backward compatibility.

### From S5f + S5f-fix + S5f-fix2 (Visual Fixes)
- **No doc impact** — CSS fixes, MockStrategy dev-mode scaffolding, UX polish.
  These are implementation details, not architectural decisions.

### From S6 (Operational Fixes)
- **architecture.md / AI Layer:** Insight data now includes `session_status`
  (pre_market/open/closed), `session_elapsed_minutes` (from 9:30 ET), and
  `minutes_until_open`. Replaces previous binary open/closed market status.
- **architecture.md / Intelligence Layer:** Finnhub 403 responses downgraded
  from ERROR to WARNING with per-cycle request/403 counters and cycle summary
  log. FMP circuit breaker (DEC-323) now has dedicated test coverage.

## Accumulated Issues Log

| # | Session | Category | Description | Status |
|---|---------|----------|-------------|--------|
| 1 | S3 | Reviewer concern (MED) | AfMo `_check_breakout_entry()` restructured beyond additive | ACCEPTED — necessary for 8-condition spec |
| 2 | S3 | Reviewer concern (LOW) | 2 AfMo conditions (body_ratio, spread_range) informational-only | ACCEPTED |
| 3 | S3 | Reviewer concern (LOW) | time_remaining also informational-only | ACCEPTED |
| 4 | S4 | Cat 2 — Bug (MED) | StrategyDecisionsResponse type didn't match backend bare array | RESOLVED (S4a) |
| 5 | S4 | Info (LOW) | Summary stats counted from unfiltered events | RESOLVED (S4a) |
| 6 | S4 | Info (LOW) | Dual symbol filtering (client + server) | RESOLVED (S5f-fix2) — now client-only |
| 7 | S5-QA | Cat 4 (pre-existing) | 3-column container y-values misaligned | RESOLVED (S5f) |
| 8 | S5-QA | Cat 4 (pre-existing) | Strategy card heights inconsistent across rows | RESOLVED (S5f) |
| 9 | S5-QA | Cat 3 — Scope gap (MED) | MockStrategy missing eval_buffer in dev_state.py | RESOLVED (S5f-fix) |
| 10 | S5-QA | Cat 4 (LOW) | Dropdown chevron padding insufficient | RESOLVED (S5f) |
| 11 | S5-QA | Cat 4 — Design | UX brainstorm: slide-out vs alternatives | DEFERRED |
| 12 | S5f | Warning (LOW) | CardHeader min-h-10 is global — verify other pages | NOTED |
| 13 | S5f-QA | Cat 4 (LOW) | 3-column cards different heights | RESOLVED (S5f-fix) |
| 14 | S5f-QA | Cat 4 (LOW) | Esc key should close slide-out panel | RESOLVED (S5f-fix2) |
| 15 | S5f-QA | Cat 4 (MED) | Event row text truncation — two-line layout needed | RESOLVED (S5f-fix2) |
| 16 | S5f-fix2 | Cat 1 — Bug (MED) | Stagger animation left filtered-in items at opacity:0 | RESOLVED (S5f-fix2) |
| 17 | S5f-fix2 | Cat 1 — Bug (LOW) | Server-side symbol filter caused dropdown to lose options | RESOLVED (S5f-fix2) |
| 18 | S5f-fix2 | Cat 1 — Bug (LOW) | max-h-96 capped event list instead of filling panel | RESOLVED (S5f-fix2) |

## Accumulated Scope Changes

| Session | Change | Justification |
|---------|--------|---------------|
| S1 | +3 extra tests beyond minimum | Trivial coverage additions |
| S2 | +2 extra tests; per-failure-mode ENTRY_EVALUATION events | More diagnostic granularity |
| S3 | AfMo restructured to evaluate-all-then-check; 3 informational conditions added | Required to emit 8 individual CONDITION_CHECK events per spec |
| S3.5 | Added close() method to EvaluationEventStore | Resource cleanup for server lifespan |
| S4 | Error state rendering + 4 bonus tests | Graceful error handling |
| S5f | Fix 1 (404) partially resolved — backend root cause identified but blocked by constraint | MockStrategy missing eval_buffer; resolved in S5f-fix |
| S5f-fix2 | Removed stagger animation; removed server-side symbol filter; flex-fill event list | Bug fixes discovered during implementation |
| S6 | Optional candle-cache design doc skipped | Explicitly optional in spec |

## Accumulated Deferred Observations

1. **(S1)** The decisions endpoint returns raw dicts. A Pydantic response model
   (EvaluationEventResponse) could be added later without breaking callers.
2. **(S1)** BUFFER_MAX_SIZE=1000 is a code constant. Per-strategy configurability
   is possible since the buffer __init__ already accepts a maxlen parameter.
3. **(S5-QA)** UX brainstorm: the slide-out panel pattern for Decision Stream
   may not be the most discoverable UX. Alternatives discussed: inline accordion,
   dedicated section/tab, click-to-focus, wider drawer. Deferred until real
   usage patterns are observed during paper trading.
4. **(S5f)** CardHeader min-h-10 was applied globally. Visual check needed on
   other pages (Dashboard, Performance, etc.) to confirm no unintended spacing.
5. **(S6)** Optional candle-cache design doc not written. Low priority — can be
   written if/when candle caching becomes a sprint target.

## Work Journal Close-Out

> Generated by the Sprint 24.5 Work Journal conversation on 2026-03-16.

### Sprint Summary

- **Sprint:** 24.5 — Strategy Observability + Operational Fixes
- **Sessions:** S1, S2, S3, S3.5, S4, S4a-fix, S5, S5f, S5f-fix, S5f-fix2, S6
- **Tests:** pytest 2,709 → ~2,771 (+62), Vitest 503 → 523 (+20)
- **Review verdicts:** S1 CLEAR, S2 CLEAR, S3 CONCERNS (accepted), S3.5 CLEAR,
  S4 CONCERNS (resolved S4a), S5 CLEAR, S6 CLEAR

### DEF Numbers Assigned During Sprint

No DEF numbers were assigned during this sprint. All issues were resolved
in-sprint or logged as deferred observations.

**Important:** Do NOT create new DEF entries for any of the 18 tracked issues —
all actionable items were resolved during the sprint.

### DEC Numbers Tracked

| DEC # | Description | Session |
|-------|-------------|---------|
| DEC-342 | Strategy evaluation telemetry: in-memory ring buffer (maxlen=1000), no EventBus integration, ET naive timestamps per DEC-276, REST endpoint GET /strategies/{id}/decisions, SQLite persistence with 7-day retention | S1 + S3.5 |

### Resolved Items (do NOT create new DEF entries for these)

| Item | Resolution | Session |
|------|------------|---------|
| Response type mismatch (frontend wrapper vs backend bare array) | Changed frontend to EvaluationEvent[]; updated hook + test mocks | S4a |
| Summary stats from unfiltered events | Changed to derive from filteredEvents | S4a |
| Dual symbol filtering (client + server) | Removed server-side filter param; client-only | S5f-fix2 |
| 3-column container y-values misaligned | min-h-10 on CardHeader | S5f |
| Strategy card heights inconsistent | fullHeight + flex layout + mt-auto footer | S5f |
| MockStrategy missing eval_buffer | Added eval_buffer field + mock event seeding | S5f-fix |
| Dropdown chevron padding | pl-2 pr-8 on select element | S5f |
| 3-column card heights unequal | h-full flex flex-col + Card flex-1 on all 3 columns | S5f-fix |
| Esc key doesn't close panel | useEffect keydown listener in OrchestratorPage | S5f-fix2 |
| Event row text truncation | Two-line layout (time+symbol+result / event_type+reason) | S5f-fix2 |
| Stagger animation bug | Replaced motion.div stagger with plain div elements | S5f-fix2 |
| Server filter broke dropdown | Removed symbol param from hook API call | S5f-fix2 |
| Event list height capped | flex-1 min-h-0 replaces max-h-96 | S5f-fix2 |

### Outstanding Code-Level Items (not assigned DEF numbers)

| Item | Location | Severity | Source |
|------|----------|----------|--------|
| CardHeader min-h-10 is global — verify visual impact on other pages | ui/src/components/CardHeader.tsx | LOW | S5f |
| Pre-existing ruff issues in summary.py (E501, I001, B007, SIM102) on unmodified lines | argus/ai/summary.py | INFO | S6 |
| Pre-existing E402 ruff warnings in strategies.py (logger before imports) | argus/api/routes/strategies.py | INFO | S1 |

### Corrections Needed in Initial Doc-Sync Patch

None — Work Journal handoff was included in doc-sync prompt.

## DEC Entries Needed

### DEC-342: Strategy evaluation telemetry — in-memory ring buffer, no EventBus

**Context:** Sprint 24.5 S1 + S3.5. Strategy observability requires real-time
visibility into what each strategy evaluates on every candle.

**Decision:** Evaluation events are diagnostic-only and do NOT flow through the
EventBus. A `StrategyEvaluationBuffer(maxlen=1000)` ring buffer is attached to
`BaseStrategy`. Each strategy calls `record_evaluation()` at every decision point
(time window checks, condition evaluations, signal generation, quality scoring).
The method wraps its entire body in try/except — it never raises.

Timestamps use ET naive datetimes per DEC-276. Nine event types defined in
`EvaluationEventType` (StrEnum): TIME_WINDOW_CHECK, OPENING_RANGE_UPDATE,
STATE_TRANSITION, INDICATOR_STATUS, CONDITION_CHECK, ENTRY_EVALUATION,
SIGNAL_GENERATED, SIGNAL_REJECTED, QUALITY_SCORED. Three result types:
PASS, FAIL, INFO.

`EvaluationEventStore` provides SQLite persistence with 7-day retention
(ET-date-based cleanup). Fire-and-forget async forwarding from buffer to store
via `loop.create_task()`. REST endpoint `GET /api/v1/strategies/{id}/decisions`
returns buffer contents for today (or store contents for historical `?date=`
queries). JWT-protected.

Frontend: `StrategyDecisionStream` component with TanStack Query polling (3s),
color-coded two-line event rows, symbol filter, summary stats, expandable
metadata. Slide-out panel on Orchestrator page with Esc key close.

**Rationale:** EventBus is for system-critical events that drive execution logic.
Evaluation telemetry is high-volume diagnostic data (~200 events/candle across 4
strategies) that would flood the bus and subscribers. Ring buffer provides O(1)
append with bounded memory. SQLite persistence enables historical analysis without
growing the ring buffer.

**Alternatives considered:** EventBus integration (rejected — volume too high,
diagnostic-only); WebSocket streaming (deferred — REST polling sufficient for MVP);
per-strategy SQLite databases (rejected — single DB simpler, WAL mode handles
concurrent writes).

## Target Documents

Update the following documents. For each, read the current version first,
then apply the changes from the doc-sync queue. Maintain each document's
existing format and style.

1. **docs/project-knowledge.md** — Update sprint history table, test counts,
   current state section, add telemetry to architecture notes.

2. **docs/architecture.md** — Add Strategy Evaluation Telemetry subsection.
   Document EvaluationEventStore, ring buffer, REST endpoint, frontend
   Decision Stream, and operational fixes (insight clock, Finnhub 403).

3. **docs/decision-log.md** — Add DEC-342.

4. **docs/dec-index.md** — Add DEC-342 entry.

5. **docs/sprint-history.md** — Add Sprint 24.5 entry with all 11 sessions.

6. **CLAUDE.md** — Update test counts. No new DEF entries (all resolved in-sprint).
   Add deferred observations 1-5 if appropriate.

7. **docs/roadmap.md** — No changes expected. Sprint was observability +
   operational fixes with no roadmap impact.

## Constraints
- Do NOT modify source code, tests, or config files
- Do NOT make architectural decisions — only document what was decided
- If a doc-sync item is ambiguous, note it in the close-out as needing
  human review rather than guessing
- Preserve existing document formatting and conventions
- For DEC entries: use DEC-342 as assigned by the Work Journal. Next
  available after this sprint: DEC-343.
- No DEF numbers were assigned during this sprint. Next available: DEF-063.
- Items marked RESOLVED in the Work Journal must NOT appear as open DEF
  entries in CLAUDE.md or any other document.

## Close-Out
After all documentation updates are complete, follow the close-out skill
in .claude/skills/close-out.md.

Include the structured close-out appendix with:
- verdict: COMPLETE or INCOMPLETE
- files_modified: list of all documentation files updated
- Any items from the doc-sync queue that could not be resolved (noted as
  scope_gaps for human review)

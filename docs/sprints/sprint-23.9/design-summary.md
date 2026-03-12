# Sprint 23.9 Design Summary

**Sprint Goal:** Fix frontend intelligence hook spam (DEF-041), resolve Debrief
page 503 (DEF-043), rewrite tautological SEC Edgar timeout test (DEF-045), and
fix pre-existing xdist test failures (DEF-046). Fast-follow cleanup after Sprint
23.8 Intelligence Pipeline Live QA Fixes.

**Session Breakdown:**
- Session 1: Catalyst hook gating + SEC Edgar test rewrite + xdist fix + debrief investigation
  - Creates: None (possibly 1 new hook file if `usePipelineStatus` is extracted)
  - Modifies: `useCatalysts.ts` (or equivalent catalyst hooks), `useIntelligenceBriefings.ts`
    (same gating pattern), `test_sec_edgar.py` (~line 339-372), `test_main.py` (add markers
    or fix isolation)
  - Integrates: N/A — all items are independent fixes
- Session 2: Debrief 503 fix (based on Session 1 investigation)
  - Creates: None expected (possibly empty-state UI component)
  - Modifies: `argus/api/routes/debrief.py` (or equivalent route), possibly
    `argus/ai/daily_summary.py`, possibly Debrief page components for empty state
  - Integrates: Session 1's investigation findings (reported in close-out)

**Key Decisions:**
- DEC-329: Gate frontend catalyst/intelligence hooks on pipeline status from
  `/api/v1/health` endpoint. Use TanStack Query `enabled` option keyed to
  pipeline active status. No new backend endpoint needed.

**Scope Boundaries:**
- IN: Frontend hook gating for catalyst/intelligence queries; debrief 503 root
  cause + fix; SEC Edgar timeout test rewrite; xdist test isolation fix
- OUT: Backend catalyst endpoint changes; new API endpoints; pipeline
  performance optimization; request batching (consolidating per-symbol calls
  into bulk); debrief AI summary content quality; xdist collection discrepancy
  root cause (may resolve with DEF-046 fix)

**Regression Invariants:**
- All existing catalyst functionality works when `catalyst.enabled: true`
- Health endpoint response shape unchanged
- Intelligence briefings endpoint unaffected
- Debrief page loads without error (currently broken — this sprint fixes it)
- All 2,529 pytest + 435 Vitest tests pass (minus known xdist issues resolved by DEF-046)

**File Scope:**
- Modify: `argus/ui/src/hooks/useCatalysts.ts`, `argus/ui/src/hooks/useIntelligenceBriefings.ts`,
  `tests/intelligence/test_sec_edgar.py`, `tests/test_main.py`,
  `argus/api/routes/debrief.py`, possibly `argus/ai/daily_summary.py`,
  possibly `argus/ui/src/pages/Debrief/`
- Do not modify: `argus/api/routes/health.py`, `argus/intelligence/`,
  `argus/core/`, `argus/strategies/`, `argus/execution/`, `argus/data/`,
  `argus/config/system.yaml`, `argus/config/system_live.yaml`

**Config Changes:** No config changes.

**Test Strategy:**
- DEF-041: ~3-4 Vitest tests (hook disabled when pipeline inactive, hook enabled
  when pipeline active, briefing hooks follow same pattern)
- DEF-043: ~3-5 pytest tests (endpoint returns data when generator ready,
  endpoint returns empty result when no data, proper initialization wiring)
- DEF-045: ~1 rewritten pytest test (calls client.start(), inspects session timeout)
- DEF-046: ~0 new tests (fix is isolation/markers on existing tests)
- Estimated net new: ~8-10 tests

**Runner Compatibility:**
- Mode: human-in-the-loop (investigation results from Session 1 inform Session 2)
- Parallelizable sessions: none (Session 2 depends on Session 1 findings)
- Estimated token budget: ~80K (2 sessions × ~40K avg for fix-focused work)
- Runner-specific escalation notes: N/A (not autonomous)

**Dependencies:**
- Sprint 23.8 merged to main ✅
- `catalyst.enabled: true` in `system_live.yaml` for testing enabled path
- `ANTHROPIC_API_KEY` set (DailySummaryGenerator likely needs Claude API)

**Escalation Criteria:**
- If debrief 503 root cause involves architectural issues beyond the route handler
  (e.g., DailySummaryGenerator design is fundamentally broken), escalate to Tier 3
- If xdist failures trace to Event Bus or shared global state that implies a
  broader test isolation problem, escalate

**Doc Updates Needed:**
- `docs/decision-log.md` — DEC-329
- `docs/dec-index.md` — DEC-329
- `docs/sprint-history.md` — Sprint 23.9 entry
- `docs/project-knowledge.md` — test count update, sprint history table
- `CLAUDE.md` — test count, DEF closures (DEF-041, DEF-043, DEF-045, DEF-046)

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Review Context File
4. Implementation Prompt ×2
5. Review Prompt ×2
6. Doc Update Checklist

# Sprint 28, Session 6a: Frontend — Hooks + API Client + Recommendation Cards

## Pre-Flight Checks
1. Read: `argus/api/routes/learning.py` (S5 — API signatures), `argus/ui/src/hooks/` (existing TanStack Query patterns), `argus/ui/src/api/` (existing API client patterns), `argus/ui/src/components/` (existing card component patterns)
2. Run: `cd argus/ui && npm test` (Vitest baseline)
3. Verify correct branch, S5 merged

## Objective
Build the frontend data-fetching layer (TanStack Query hooks + typed API client) and the reusable recommendation card components.

## Requirements

1. **Create `argus/ui/src/api/learningApi.ts`:**
   - Typed API client functions for all 8 learning endpoints
   - TypeScript interfaces: `LearningReport`, `WeightRecommendation`, `ThresholdRecommendation`, `CorrelationResult`, `ConfigProposal`, `ConfigChangeEntry`
   - Response types matching backend Pydantic models

2. **Create `argus/ui/src/hooks/useLearningReport.ts`:**
   - `useLearningReport()` — fetches latest report via TanStack Query. Stale time: 5 minutes.
   - `useLearningReports(startDate, endDate)` — list with date filter
   - `useTriggerAnalysis()` — mutation hook for POST /trigger

3. **Create `argus/ui/src/hooks/useConfigProposals.ts`:**
   - `useConfigProposals(statusFilter?)` — fetches proposals list
   - `useApproveProposal()` — mutation with optimistic update + cache invalidation
   - `useDismissProposal()` — mutation
   - `useRevertProposal()` — mutation
   - All mutations invalidate both proposals and reports queries on success

4. **Create `argus/ui/src/components/learning/WeightRecommendationCard.tsx`:**
   - Displays: dimension name, current weight → recommended weight (delta with arrow), correlation values (trade + counterfactual), p-value, sample size, confidence badge (color-coded), source divergence warning if flagged
   - Approve button (with optional notes textarea that expands on click), Dismiss button
   - Approved state: green checkmark, notes displayed, revert button visible
   - Dismissed state: greyed out with notes
   - SUPERSEDED state: strikethrough with "superseded by newer report" label
   - Tailwind styling, consistent with existing ARGUS card patterns

5. **Create `argus/ui/src/components/learning/ThresholdRecommendationCard.tsx`:**
   - Displays: grade name, current threshold, recommended direction (raise/lower arrow), missed-opportunity rate, correct-rejection rate, sample size, confidence badge
   - Same approve/dismiss/notes UX as WeightRecommendationCard
   - Same state displays (approved, dismissed, superseded)

## Constraints
- Do NOT modify any existing page components (Performance, Dashboard) — that's S6b/S6c
- Do NOT create StrategyHealthBands, CorrelationMatrix, or Dashboard card — that's S6c
- Components should be self-contained and importable (no page-level dependencies)

## Test Targets
- Vitest: hook render tests (useLearningReport, useConfigProposals), card render tests (weight card, threshold card), approve/dismiss interaction tests, superseded state rendering
- Minimum: 5 Vitest tests
- Test command: `cd argus/ui && npm test`

## Visual Review
After implementation, visually verify in Storybook or test harness:
1. WeightRecommendationCard with MODERATE confidence data
2. ThresholdRecommendationCard with INSUFFICIENT_DATA confidence
3. Approve interaction: click → notes textarea → confirm → green state
4. Dismiss interaction: click → notes textarea → confirm → greyed state
5. SUPERSEDED state: strikethrough appearance

Verification conditions: Components can be viewed in isolation (no page integration yet)

## Definition of Done
- [ ] Typed API client with all 8 endpoints
- [ ] TanStack Query hooks with appropriate stale times and mutations
- [ ] WeightRecommendationCard with full state machine display
- [ ] ThresholdRecommendationCard with full state machine display
- [ ] Approve/dismiss UX with notes
- [ ] ≥5 Vitest tests
- [ ] Close-out to `docs/sprints/sprint-28/session-6a-closeout.md`
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. Verify TypeScript interfaces match backend Python models
2. Verify mutation hooks invalidate correct query keys
3. Verify confidence badge color mapping is correct
4. Verify SUPERSEDED state prevents approve/dismiss interactions
5. Verify notes are optional (approve without notes should work)

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*

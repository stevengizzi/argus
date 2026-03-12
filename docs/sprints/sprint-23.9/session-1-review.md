# Tier 2 Review: Sprint 23.9, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-23.9/review-context.md`

## Tier 1 Close-Out Report
[PASTE THE SESSION 1 CLOSE-OUT REPORT HERE]

## Review Scope
- Diff to review: `git diff main..HEAD`
- Test command (DEC-328 — non-final review, scoped tests):
  ```bash
  cd argus/ui && npx vitest run                                    # Full Vitest (frontend is the primary change)
  python -m pytest tests/intelligence/test_sec_edgar.py -x -q      # SEC Edgar test rewrite
  python -m pytest tests/test_main.py -n auto -x -q                # xdist fix verification
  ```
- Files that should NOT have been modified:
  - `argus/intelligence/` (any file)
  - `argus/core/`, `argus/strategies/`, `argus/execution/`, `argus/data/`
  - `argus/api/routes/health.py`
  - `argus/api/routes/debrief.py` (investigation only — no changes in Session 1)
  - `argus/config/system.yaml`, `argus/config/system_live.yaml`

## Session-Specific Review Focus
1. **Verify catalyst hooks are gated, not removed:** The TanStack Query `enabled`
   option should be used to conditionally prevent requests — the hooks themselves
   should still exist and work when pipeline is active. Confirm it's a gate, not
   a deletion.
2. **Verify fail-closed default:** If the health endpoint fails or is still
   loading, `isPipelineActive` should default to `false`, not `true`. This
   prevents request spam when health status is unknown.
3. **Verify briefing hooks follow same pattern:** Both catalyst and intelligence
   briefing hooks should use the same `isPipelineActive` signal. Check that the
   briefing hooks weren't missed.
4. **Verify SEC Edgar test calls start():** The rewritten test MUST call
   `await client.start()` and inspect `client._session.timeout`. If it still
   constructs its own ClientSession, the fix is invalid. Check that the CIK
   map refresh is properly mocked.
5. **Verify xdist fix is appropriate:** If tests were marked `no_xdist`, check
   that a comment explains why. If root cause was fixed, verify the fix doesn't
   introduce new shared state. Run `python -m pytest tests/test_main.py -n auto`
   to confirm.
6. **Verify debrief investigation completeness:** The close-out should contain a
   "Debrief 503 Investigation" section with: exact file/line, failing condition,
   recommended fix, frontend impact assessment. If this is missing or vague,
   flag as CONCERNS — Session 2 depends on it.

## Visual Review
The developer should visually verify:

1. **Dashboard with `catalyst.enabled: false`:** Network tab shows zero
   `/api/v1/catalysts/*` and `/api/v1/premarket/briefing/*` requests on page load.
2. **Dashboard with `catalyst.enabled: true`:** Catalyst and briefing requests
   fire normally, badges/data display correctly.
3. **No visual regression:** Dashboard renders cleanly in both states, no stuck
   spinners or error banners when pipeline is disabled.

Verification conditions:
- Backend running with `system_live.yaml`
- Test both `catalyst.enabled: true` and `false` states (requires config toggle + restart)

## Additional Context
This is Session 1 of a 2-session sprint. Session 1 bundles three independent
fixes plus a read-only investigation. The investigation findings directly
inform Session 2's implementation prompt, so completeness of the investigation
is a critical review concern. If the investigation section is missing, vague,
or contradicts what you see in the code, that's a CONCERNS verdict — Session 2
cannot proceed safely without reliable findings.

# Sprint 23.9 Review Context File

This file contains the shared review context for all Tier 2 reviews in Sprint
23.9. Individual review prompts reference this file by path rather than
duplicating its contents.

---

## Sprint Spec

See: `docs/sprints/sprint-23.9/sprint-spec.md`

**Quick summary:** Fix frontend intelligence hook spam (DEF-041), resolve Debrief
page 503 (DEF-043), rewrite tautological SEC Edgar timeout test (DEF-045), fix
xdist test failures (DEF-046). 2 sessions, no config changes, no new endpoints.

---

## Specification by Contradiction

See: `docs/sprints/sprint-23.9/spec-by-contradiction.md`

**Key exclusions the reviewer must enforce:**
- No backend catalyst endpoint changes
- No new API routes
- No modifications to `argus/intelligence/`, `argus/core/`, `argus/strategies/`,
  `argus/execution/`, `argus/data/`
- No modifications to health endpoint response shape
- No config file changes (`system.yaml`, `system_live.yaml`)
- Catalyst request volume when pipeline IS active is not optimized

---

## Sprint-Level Regression Checklist

After each session, verify ALL of the following:

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Health endpoint unchanged | `curl http://localhost:8000/api/v1/health` returns same shape as before sprint |
| 2 | Catalyst endpoint still works when enabled | With `catalyst.enabled: true`, `curl http://localhost:8000/api/v1/catalysts/AAPL` returns 200 |
| 3 | Intelligence briefing endpoint still works | `curl http://localhost:8000/api/v1/premarket/briefing/latest` returns 200 or 404 (not 503) |
| 4 | Debrief briefings endpoint responds | `curl http://localhost:8000/api/v1/debrief/briefings` returns 200 (after Session 2) |
| 5 | Frontend builds without errors | `cd argus/ui && npm run build` succeeds |
| 6 | All pytest tests pass | `python -m pytest -n auto -x -q` — count ≥ 2,529 |
| 7 | All Vitest tests pass | `cd argus/ui && npx vitest run` — count ≥ 435 |
| 8 | No ruff violations | `ruff check argus/ tests/` clean |
| 9 | No files outside scope modified | `git diff --name-only` shows only expected files |
| 10 | SEC Edgar timeout test is non-tautological | New test calls `client.start()` and inspects `client._session.timeout` |

---

## Sprint-Level Escalation Criteria

Escalate to Tier 3 (human review in Claude.ai) if ANY of the following:

1. **Architectural surprise in debrief 503:** Root cause involves more than the
   route handler + generator wiring (e.g., DailySummaryGenerator design is
   fundamentally incompatible with current app lifecycle)
2. **xdist failures trace to shared global state:** If the two test_main.py
   failures indicate a systemic test isolation problem beyond those two tests
3. **Health endpoint modification required:** If pipeline status cannot be
   determined from the existing health response without changing the endpoint
4. **Scope creep beyond 4 items:** Implementation touches files or behaviors
   explicitly listed in spec-by-contradiction as out of scope
5. **Test count regression:** Post-sprint test count drops below 2,529 pytest
   or 435 Vitest (net additions expected, not losses)

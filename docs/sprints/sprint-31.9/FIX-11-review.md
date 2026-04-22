---BEGIN-REVIEW---

**Reviewing:** FIX-11-backend-api (audit 2026-04-21 Phase 3) — argus/api/ REST/WS/auth cleanup (23 findings)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-21
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All out-of-scope touches (trade_logger.py, orchestrator.py, regime.py, vix_data_service.py, config.py, watchlist.py, 3 cascading test files, 3 extra Vitest files) are direct consequences of the Suggested Fix text in the findings themselves. No Rule-4 sensitive file touched. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls (F1-11, F1-18, F1-2 Option B) documented. Self-assessment MINOR_DEVIATIONS is honest and accurate. |
| Test Health | CONCERNS | 4,943 pytest passed / 2 failed (both pre-existing DEF-163 date-decay). 846 Vitest / 0 failed. 16 new regression tests all pass. **Net delta is −2** vs baseline 4,945 — this is spec-authorized by F1-2 Option B (18 dev_state tests deleted + 16 new = −2), but literally fails the "net delta >= 0" regression check. |
| Regression Checklist | PASS (with caveat) | 7/8 checks pass outright. Check 1 (pytest net delta >= 0) is literally failing but operator's session prompt pre-authorizes the −2 as F1-2 structural consequence. DEF-163 remains only pre-existing failure; no new regressions. 22 P1-F1 + 1 P1-F2 M09 back-annotations present. DEF-167, DEF-168, DEF-169 opened and referenced in commit. |
| Architectural Compliance | PASS | Public-accessor pattern (F1-3/F1-4) follows DEF-091 contract. Lifespan refactor uses LIFO teardown ordering (more correct than pre-FIX-11 forward order). State_desync drain-and-enqueue pattern is single-coroutine and deadlock-free. 501 replay response sequences AFTER 404 check so bad IDs still produce the right error. BarsResponse.source Literal is a public-API addition aligned with `api-conventions.md`. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL finding unaddressed (F1-1 and F1-2 both resolved correctly). No scope-boundary violation beyond spec-authorized touches. No Rule-4 file touched. Test failures match expected (2 × DEF-163). Audit back-annotation complete. Not a FIX-01 session → Step 1G N/A. |

### Findings

#### MEDIUM

**M1. F1-11 judgment call — suggested `is_dev_mode` field not added (watchlist.py:90).** Spec said "Add an explicit `is_dev_mode: bool = False` field on AppState, set True in `create_dev_state()`. Replace hasattr check." Implementer instead removed the `state.data_service is None` sentinel entirely and retained `getattr(state, "_mock_watchlist", None)` as a documented test-only monkey-patch. Justification is defensible: since F1-2 retired `--dev` mode in the same commit, a permanent `is_dev_mode` field would be a misleading abstraction on top of a test-only hook. However this is strictly a deviation from the spec text, and `tests/api/test_watchlist.py:297` still exercises the monkey-patch — so the pattern the finding flagged as fragile (getattr-based sentinel) survives in modified form. Acceptable as MINOR_DEVIATION, but worth documenting.

**M2. F1-18 judgment call — neither of the two suggested options taken (market.py:306).** Spec said "Either lift the 390 cap or enforce it as the hard parameter max." Implementer retained `synthetic_limit = min(limit, 390)` and justified the residual asymmetry via the new `source='synthetic'` flag from F1-1. The frontend can now gate off synthetic data entirely, so the asymmetry is less load-bearing — but strictly the spec asked for one of two fixes and got a third. Documented in commit message as "Synthetic-bars 390 cap retained; source='synthetic' flag signals asymmetry."

#### LOW

**L1. Pytest net delta is literally −2 against baseline 4,945.** `F1-2 Option B` retirement of `--dev` mode deleted 2 test files (18 tests total: `test_dev_state_patterns.py` = 6, `test_dev_state_dashboard.py` = 12), plus `test_valid_trade_returns_replay_data` was renamed to `test_valid_trade_returns_501_until_def029` (same count, different assertion). The +16 regression tests in `test_fix11_backend_api.py` do not fully offset the −18 deletions. Math: 4945 − 18 + 16 = 4943. The operator's session prompt explicitly pre-authorizes this as a "structural consequence of F1-2 Option (b) which the audit finding explicitly authorizes." I concur the −2 is spec-authorized and non-regressive — every deleted test exercised code that no longer exists. This is informational, not a defect.

**L2. Lifespan teardown ordering changed from forward-order to LIFO (server.py:650).** Pre-FIX-11: AI services torn down first, telemetry last. Post-FIX-11: HQS torn down first, AI last (teardowns reversed from init order). LIFO is the architecturally correct cleanup pattern (services that may depend on earlier init are freed first) and no dependency violations were identified — observatory_service does not reference telemetry_store at teardown, intelligence_pipeline does not reference ai_client at teardown, etc. No finding called this out as a concern. Informational.

**L3. `VIXDataService.attach_vix_service()` on `RegimeClassifierV2` does NOT re-instantiate calculators (regime.py:709).** The docstring correctly notes "Calculators are NOT re-instantiated here — constructor-time wiring remains the canonical path." This means `routes/vix.py` falls back to `vol_phase_calc=None` etc. if the classifier was built before the VIX service came up. At the time of `_init_vix_data_service` in the lifespan, `RegimeClassifierV2` has already been constructed by main.py (Phase 8.x) without VIX, so the calculators remain None. For this to surface vol regime info, `RegimeClassifierV2` must be built AFTER VIX. This is a pre-existing ordering dependency (not introduced by FIX-11) — worth being aware of when auditing the /vix/current response in production.

#### COSMETIC / INFORMATIONAL

**I1. `_mock_watchlist` pattern survives as a test-only hook (watchlist.py:90, test_watchlist.py:297).** Documented in the route comment and still used by `test_watchlist.py`. Not a bug — just noting the pattern persists.

**I2. F1-18 synthetic bars capped at 390 (market.py:306) is a functional quirk** but is now clearly signaled by `source="synthetic"`, so frontend can gate behind it. Not a defect.

### Recommendation

**CONCERNS.** Accept the session as complete and proceed to the next FIX. The two MEDIUM-level judgment calls (M1, M2) are defensible and accompanied by in-line commentary + commit-message rationale. The −2 pytest delta (L1) is spec-authorized and every deleted test was an exercise of code that no longer exists. The lifespan teardown-order change (L2) is architecturally preferable to pre-FIX-11 and no dependency violation was found.

Suggested follow-ups (NOT blocking):
- **For FIX-12 or later:** consider whether a Protocol-typed `state.test_watchlist_override: list[WatchlistItem] | None = None` field on AppState (optional, defaults None) would be cleaner than the `getattr(state, "_mock_watchlist", None)` monkey-patch preserved by M1.
- **For FIX-13-test-hygiene:** DEF-167 notes a broader Vitest date-decay scan is still pending — the 4 files touched by this session were spot fixes from the audit's explicit finding, not a comprehensive sweep.
- **For FIX-session that touches RegimeClassifierV2 / main.py init order:** verify that `routes/vix.py` still returns populated calculator classifications after the lifespan VIX init — the L3 observation suggests this may already be broken (pre-existing).

No Tier 3 architectural review required.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-11-backend-api",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "F1-11 judgment call: spec suggested adding `is_dev_mode: bool = False` field on AppState; implementer instead retained `_mock_watchlist` as a documented test-only monkey-patch and removed the `data_service is None` sentinel. Defensible (the field would be misleading after F1-2 retired --dev mode) but strictly a spec deviation. The fragile getattr-based pattern flagged by the original finding survives in modified form.",
      "severity": "MEDIUM",
      "category": "SPEC_VIOLATION",
      "file": "argus/api/routes/watchlist.py:90",
      "recommendation": "Accept as MINOR_DEVIATION per close-out. Consider a future Protocol-typed `test_watchlist_override` field on AppState if the test-hook pattern is ever cleaned up."
    },
    {
      "description": "F1-18 judgment call: spec said 'Either lift the 390 cap or enforce it as the hard parameter max.' Implementer retained `synthetic_limit = min(limit, 390)` and justified the residual asymmetry via the new F1-1 `source='synthetic'` flag. Neither of the two explicit options was taken, but the frontend can now gate synthetic data entirely, so the asymmetry is less load-bearing.",
      "severity": "MEDIUM",
      "category": "SPEC_VIOLATION",
      "file": "argus/api/routes/market.py:306",
      "recommendation": "Accept as MINOR_DEVIATION — documented in commit message. No follow-up required unless the synthetic-bar cap becomes a UX issue."
    },
    {
      "description": "Pytest net delta is literally −2 against baseline 4,945 (4945 − 18 deleted dev_state tests + 16 new FIX-11 regression tests = 4943). Spec-authorized by F1-2 Option B retirement of --dev mode. Every deleted test exercised code that no longer exists. Operator's session prompt pre-authorizes this as structural consequence.",
      "severity": "LOW",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/api/test_dev_state_patterns.py (deleted), tests/api/test_dev_state_dashboard.py (deleted)",
      "recommendation": "No action — spec-authorized deletion of tests for deleted code paths."
    },
    {
      "description": "Lifespan teardown ordering changed from forward-order (pre-FIX-11: AI first, telemetry last) to LIFO reverse-order (post-FIX-11: HQS first, AI last). LIFO is architecturally correct; no dependency violations identified. Not called out by any finding.",
      "severity": "LOW",
      "category": "ARCHITECTURE",
      "file": "argus/api/server.py:650",
      "recommendation": "Informational only. Monitor for any subsystem-interaction issues during next full-boot verification."
    },
    {
      "description": "`RegimeClassifierV2.attach_vix_service()` does NOT re-instantiate VIX calculators (`_vol_phase_calc`, `_vol_momentum_calc`, `_term_structure_calc`, `_vrp_calc`). If the classifier is constructed before the VIX service is available (which is the lifespan order today), the calculators remain None and `/vix/current` regime classifications are empty. This is a pre-existing ordering dependency, not introduced by FIX-11; the attach_vix_service docstring acknowledges this explicitly.",
      "severity": "LOW",
      "category": "ARCHITECTURE",
      "file": "argus/core/regime.py:709",
      "recommendation": "Verify /vix/current returns populated `regime.vol_regime_phase` etc. in a production session. If empty, file a DEF to make attach_vix_service re-wire calculators, or change main.py to build RegimeClassifierV2 after VIX."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "22/23 findings resolved with clear rationale. Two judgment calls (F1-11, F1-18) deviate from the exact suggested-fix wording but address the underlying concern. All CRITICAL findings (F1-1, F1-2) resolved correctly. All back-annotations present.",
    "spec_by_contradiction_violations": []
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Accept session as complete; proceed to next FIX.",
    "For FIX-12 or later: consider a Protocol-typed `test_watchlist_override` field on AppState (cleaner than the `_mock_watchlist` getattr pattern preserved by M1).",
    "For FIX-13-test-hygiene: DEF-167 broader Vitest date-decay scan still pending.",
    "Observation L3: verify `/vix/current` returns populated regime classifications in a production session. If empty, `RegimeClassifierV2.attach_vix_service()` needs to re-wire calculators, OR main.py must build the classifier after VIX init."
  ]
}
```

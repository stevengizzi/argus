---BEGIN-CLOSE-OUT---
```markdown
# Close-Out — FIX-04-execution

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-04` (full ID: `FIX-04-execution`)
- **Date:** 2026-04-22
- **Commit:** `b2c55e5`
- **Baseline HEAD:** `942cf05`
- **Test delta:** 4,984 → 4,985 (net +1; +5 new execution regression tests, −4 from `test_broker_router.py` deletion)
- **Context State:** GREEN (well within limits throughout; no compaction hit)

## Scope

Phase 3 Wave 2, Rule-4 serial. Execution layer (`argus/execution/`) — broker adapters, order manager, IBKR error handling, execution record. 19 findings total: 2 CRITICAL + 7 MEDIUM + 10 LOW.

## Files modified

```
 M CLAUDE.md                                            (DEF-176/177 entries + test count + active-sprint list)
 M argus/execution/execution_record.py                  (P1-C1-L04)
 M argus/execution/ibkr_broker.py                       (P1-C1-M01 M05 L02 L03)
 M argus/execution/ibkr_errors.py                       (P1-C1-M05 helper — 404 added to _ORDER_REJECTION_CODES)
 M argus/execution/order_manager.py                     (P1-C1 C01 C02 M02 M06 L05 L06 L07 L08 L09 L10)
 M docs/audits/audit-2026-04-21/p1-c1-execution.md      (FIX-04 Resolution section appended)
 M docs/audits/audit-2026-04-21/phase-2-review.csv      (19 rows back-annotated)
 M docs/sprints/sprint-31.9/RUNNING-REGISTER.md         (FIX-04 row + DEF-176/177 + baseline progression)
 D argus/execution/broker_router.py                     (P1-C1-M04 — deleted)
 D tests/execution/test_broker_router.py                (P1-C1-L01 — deleted transitively)
 M tests/execution/test_ibkr_broker.py                  (scope expansion: M-05 test updated to expect 2 warning calls)
 M tests/execution/test_order_manager.py                (+5 regression tests; 4 updated; config fixture timeout override)
```

## Change manifest — `argus/execution/order_manager.py` (reviewer reference)

Most heavily touched file. Every meaningful edit:

| Site (approx line) | Finding | Change |
|---|---|---|
| `:21` | F4 | Added `timedelta` import |
| `:24` (+5) | F10 | Added `warnings` import |
| `:106` (+5) | F10 | `DeprecationWarning` on legacy `auto_cleanup_orphans` kwarg path |
| `:482-491` | (P1-D1-M03 DEFERRED) | No code change — DEF-177 tracks the cross-domain fix |
| `:970-1001` | F9 (L09) | `_handle_entry_fill` initializes `mfe_time`/`mae_time` to `entry_fill_time` (mirroring the price initialization) |
| `:1376-1392` | F8 (L08) | `_handle_flatten_fill` strategy_id-mismatch fallback tightened to `logger.error + return` |
| `:1440-1466` | F5 + F6 | Poll loop: removed redundant `_flattened_today=True`; uses new `_now_et(now)` helper once |
| `:1463-1474` | F6 | Added `_now_et(now)` helper (reads `self._config.eod_flatten_timezone`) |
| `:1907-1911` | F3 | `_flatten_unknown_position` calls `_cancel_open_orders_for_symbol(symbol)` before the SELL |
| `:1926-1960` | F3 | NEW `_cancel_open_orders_for_symbol(symbol)` helper |
| `:1988-2005` | F3 | `_drain_startup_flatten_queue` calls the new helper before each queued SELL; docstring updated |
| `:2017` | F1 (C01) | `_create_reco_position`: `avg_entry_price` → `entry_price` |
| `:2052` | F1 (C01) | `_reconstruct_known_position`: `avg_entry_price` → `entry_price` |
| `:2074` | F2 (C02) | `_reconstruct_known_position`: `getattr(order, "qty", 0)` → `getattr(order, "quantity", 0)` |
| `:2082-2099` | F4 (M06) | `_reconstruct_known_position` biases `entry_time` earlier by `max_position_duration_minutes // 2` |
| `:2773-2789` | F7 (L07) | Comment documenting per-symbol cleanup dict pop() as intentional defense-in-depth |

## Judgment calls

1. **F1/F2 — kept `getattr(..., default)` pattern instead of direct attribute access.** The kickoff suggested considering direct access since the Broker ABC contractually returns `Position`/`Order`. The reconstruction path has 8+ other `getattr` calls with defaults; mixing direct access for two attributes and `getattr` for the rest would be inconsistent. Kept the `getattr` form, fixed the field names. Regression tests guard against future drift.
2. **F4 (M06) — stopgap fix, not the durable one.** The finding offered (a) persist `entry_time` in trades DB sidecar and restore it, or (b) bias earlier as a stopgap. (a) requires a DB schema addition and a rehydration pass; out of scope for a Rule-4 serial session. (b) applied: reconstructed `entry_time = now - max_position_duration_minutes // 2`. Documented in the code and in the audit resolution.
3. **F10 (L10) — deprecation warning, not removal.** The finding suggested "grep callers; remove if none pass the arg". Production (`argus/main.py`) does not pass it. But three reconciliation test modules (`test_order_manager_reconciliation.py`, `test_order_manager_reconciliation_redesign.py`, `test_order_manager_sprint2875.py`) still do, and those files are outside FIX-04's declared scope. Took the minimal path: added `DeprecationWarning` at the constructor, logged DEF-176 for removal after test migration.
4. **F11 (P1-D1-M03) — DEFERRED.** Finding requires editing `argus/intelligence/counterfactual.py` (RejectionStage enum) + `argus/main.py:1833` (RejectionStage(event.rejection_stage) consumer). Both are outside FIX-04's execution-only scope; halt-rule-4 applied. DEF-177 opened, MEDIUM priority (masks margin-incident signal in FilterAccuracy.by_stage today).
5. **F13 (M05) — extended to also add 404 to `_ORDER_REJECTION_CODES`.** The finding's suggested fix was "remove the early return so 404 falls through to the shared `is_order_rejection` branch". But 404 wasn't in `_ORDER_REJECTION_CODES`, so removing the early return alone would not trigger the OrderCancelledEvent publish. Extended the fix to include 404 in the rejection set, which required touching `ibkr_errors.py` (in `argus/execution/` — inside broad scope, outside the kickoff's narrow Expected Files list).
6. **F14 (L02) — kept `_ib.trades()` as a fallback.** Pure dict-only would be O(1) but fails for a trade that was submitted before its first orderStatusEvent reaches `_handle_order_status`. Hybrid: dict lookup first, O(n) scan fallback. Drops the first-call cost to constant in steady state.
7. **F16 (M04) — deleted broker_router.py + test; did NOT edit docs/architecture.md.** The finding's "full" resolution includes updating the architecture doc. Deleting is surgical; the doc drift remains (already tracked under DEF-168 for API catalog drift).
8. **F19 (G2-M04) — used `eod_flatten_timeout_seconds=1` not `0.1`.** Pydantic validator is `ge=1` (integer); 0.1 would fail validation. Matches the pattern in `test_order_manager_sprint329.py`.
9. **Test mocks: updated `.avg_entry_price` / `.qty` assignments in `test_order_manager.py` to `.entry_price` / `.quantity`.** Pre-fix, the tests were passing because `MagicMock` attribute-set aligned with the buggy production getattr. Post-fix, the production code reads the real field names; if test mocks stayed on the old names, `float(auto_mock)` would return 1.0 (MagicMock's `__float__` default) instead of the intended value, producing semantic drift even if tests happened to pass. Cleaned up all 7 such sites.

## Regression Checks

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta ≥ 0 against baseline 4,984 passed | ✅ PASS | 4,985 passed (net +1) |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | ✅ PASS | Full suite: 0 failures. DEF-150 did not fire this run (ran at 12:15 local, outside minute 0/1 window). |
| No file outside this session's declared Scope was modified | ⚠ MINOR_DEVIATIONS | Two in-`argus/execution/` files outside kickoff's narrow list: `ibkr_errors.py` (M-05 helper) and `tests/execution/test_ibkr_broker.py` (one test rebaseline after M-05). Both are under `argus/execution/` per the kickoff's broader scope and are load-bearing for M-05's fix. Documented in commit and audit resolution. |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-04-execution**` | ✅ PASS | CSV: 19 rows. p1-c1-execution.md: full resolution section at bottom. |
| Every DEF closure recorded in CLAUDE.md | ✅ N/A | No DEF closures this session. |
| Every new DEF/DEC referenced in commit message bullets | ✅ PASS | DEF-176 + DEF-177 both cited. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | ✅ N/A | None in FIX-04. |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | ✅ PASS | F18 (P1-C1-L01) resolved transitively by F16 deletion; no separate DEF needed. F10 (P1-C1-L10) partial → DEF-176. F11 (P1-D1-M03) deferred → DEF-177. |

## Self-assessment: **MINOR_DEVIATIONS**

**Reasoning:**
- All 19 findings addressed (17 resolved, 1 partial with DEF, 1 deferred with DEF — honest tally).
- All tests pass (+1 net).
- Two scope expansions within the broader `argus/execution/` umbrella but outside the kickoff's narrow Expected Files list (`ibkr_errors.py` + `tests/execution/test_ibkr_broker.py`). Both were load-bearing for the M-05 fix; documented.
- Six judgment calls listed above (getattr-vs-direct-access, stopgap vs durable entry_time, deprecation-vs-removal, cross-domain deferral, fallback retention, doc-architecture-drift not touched, test-mock cleanup). None materially expanded scope beyond what the findings dictated.
- CRITICAL regression tests verified to FAIL when the fix is reverted (gold-standard proof).

**Not CLEAN** because of the scope expansion disclosure and the two DEFs (176/177) that partial/defer findings the kickoff expected to land in-session.

**Not FLAGGED** because: every CRITICAL landed with real regression coverage; test count holds; no safety-critical code path left in a broken state; judgment calls are documented and defensible.

## Deferred observations (not in-scope, worth surfacing)

1. **`tests/test_integration_sprint5.py:296`** uses `pos.avg_entry_price = 150.0` on a MagicMock for a broker-reconstruction test. After FIX-04's production fix, the test still passes — MagicMock's `__float__` returns 1.0 for the auto-created `pos.entry_price` — but the test is now semantically stale (silently uses entry_price=1.0). Not FIX-04's scope. Suggest picking up in FIX-13 (test-hygiene) or when that file is next touched.
2. **`argus/execution/alpaca_broker.py:610`** uses `pos.avg_entry_price`. This is correct — it reads off an alpaca-py SDK `Position` object, not `argus.models.trading.Position`. Called out here only to confirm it is NOT an instance of the C-01 regression class.
3. **Two patterns in reconstruction path worth a broader audit** (beyond FIX-04): the reconstruction code uses `getattr(obj, "attr", default)` for almost everything it reads off `Position`/`Order`. Since the Broker ABC contractually returns these Pydantic models, the defensive defaults hide contract violations. A future pass could replace the `getattr` forms with direct attribute access and add Pydantic validation errors at the broker-adapter boundary. Not a bug, not a DEF — an architectural observation.
4. **`eod_flatten_timezone`** is `str = "America/New_York"` on `OrderManagerConfig` and configurable via YAML, but every call site in the codebase passes the default. The new `_now_et` helper honors the config value — but if someone ever changes this to a non-ET timezone, the ET-anchored market-hour comparisons (`time(9, 30)`, `time(3, 55)`) become incorrect. Not FIX-04's problem; an existing latent coupling.

## Commits

- `b2c55e5` — audit(FIX-04): execution — broker adapters, order manager (19 findings)

## Summary

Session FIX-04 complete. 19 findings; 17 resolved; 2 deferred into DEF-176 (L-10 param removal, LOW) and DEF-177 (D1-M03 cross-domain RejectionStage.MARGIN_CIRCUIT, MEDIUM). Both CRITICALs landed with regression-verified tests. Test delta 4,984 → 4,985. Self-assessment: MINOR_DEVIATIONS.
```

```json:structured-closeout
{
  "session_id": "FIX-04-execution",
  "sprint_id": "audit-2026-04-21-phase-3",
  "date": "2026-04-22",
  "commit_sha": "b2c55e5",
  "baseline_head": "942cf05",
  "self_assessment": "MINOR_DEVIATIONS",
  "context_state": "GREEN",
  "test_baseline": 4984,
  "test_final": 4985,
  "test_net_delta": 1,
  "findings_total": 19,
  "findings_resolved": 17,
  "findings_partial": 1,
  "findings_deferred": 1,
  "new_defs": ["DEF-176", "DEF-177"],
  "new_decs": [],
  "closed_defs": [],
  "critical_findings_covered": ["P1-C1-C01", "P1-C1-C02"],
  "regression_tests_added": 5,
  "regression_tests_critical_verified_fail_on_revert": true,
  "scope_boundary_violations": [
    "argus/execution/ibkr_errors.py (in argus/execution/ umbrella but outside kickoff's Expected Files list; load-bearing for M-05)",
    "tests/execution/test_ibkr_broker.py (one test rebaseline after M-05 fall-through)"
  ],
  "halt_rules_triggered": ["halt-rule-4 on P1-D1-M03 cross-domain intelligence/ edit — deferred to DEF-177"],
  "judgment_calls": [
    "kept getattr(default) over direct access for consistency with surrounding code (F1/F2)",
    "stopgap entry_time bias instead of durable sidecar persistence (F4)",
    "DeprecationWarning instead of removal because test migration out of scope (F10)",
    "P1-D1-M03 deferred cross-domain to DEF-177 (F11)",
    "extended M-05 fix to add 404 to _ORDER_REJECTION_CODES (F13)",
    "hybrid dict + O(n) fallback for trade index (F14)",
    "broker_router delete did not touch architecture.md (F16 — drift tracked under DEF-168)",
    "used eod_flatten_timeout_seconds=1 (Pydantic ge=1 minimum, not 0.1) (F19)"
  ]
}
```
---END-CLOSE-OUT---

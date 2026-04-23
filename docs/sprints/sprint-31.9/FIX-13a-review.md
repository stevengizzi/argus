---BEGIN-REVIEW---

# Tier 2 Review — FIX-13a-test-hygiene-tactical

**Commit:** `c9c8891` (main, pushed)
**Baseline:** `dfeeb63` (Stage 8 restructure)
**Date:** 2026-04-23
**Verdict:** **CLEAR**

## Scope Verification — 25 findings + 4 DEFs

### Resolved (15 tactical findings)

| Finding | ID | Implementation verified |
|---|---|---|
| F1 / F2 | P1-G1-L03 / P1-G2-L07 | `tests/accounting/__init__.py` + `tests/notifications/__init__.py` deleted (diff shows both as `**deleted**`). Single deletion resolves duplicate findings — correct. |
| F3 / F4 | P1-G1-M07 / DEF-150 | `tests/sprint_runner/test_notifications.py:313` — `(minute - 2) % 60` → `datetime.now(UTC) - timedelta(minutes=2)`. `timedelta` added to imports. One-line fix matches spec. |
| F6 | P1-G2-M07 | Lambda `__eq__` monkeypatch removed; `BrokerSource.IBKR` substituted (see Judgment Calls). Diff verified at `tests/strategies/test_shadow_mode.py:100-110`. |
| F10 | P1-G2-M09 | New `## Test Organization Style` section in `.claude/rules/testing.md` (7 added lines). |
| F12 | P1-G1-L02 | `tests/unit/` subtree removed: 3 files renamed into `tests/core/` + `tests/strategies/`, 3 `__init__.py` deleted, 2 `parents[3]→parents[2]` path adjustments. All visible in rename diffs. |
| F14 + F16 | P1-G1-M11 / P1-G1-M10 | `[tool.coverage.run]` + `[tool.coverage.report]` added to `pyproject.toml`. Spec-drift adjustment on `__main__.py` independently verified (`ls argus/api/__main__.py` → no such file) — consistent with DEF-169 `--dev` mode retirement. |
| F15 | P1-G1-M03 | New `tests/core/test_logging_config.py` — 6 tests across `JsonFormatter`, `ConsoleFormatter`, `setup_logging`. Handler cleanup properly wrapped in `try/finally`. |
| F19 | P1-G2-M08 | 8 `except Exception: pass` sites replaced. Diff confirms 4 `pytest.raises(WebSocketDisconnect)` with `ws.receive_json()` + `assert exc_info.value.code == 4001`, 3 narrowed to `except WebSocketDisconnect: break`, 1 route-disabled site narrowed to `(WebSocketDisconnect, RuntimeError)`. |

### Verify-Only (4 findings, RESOLVED-VERIFIED)

- **F17 / DEF-163:** attribution to IMPROMPTU-03 commit `354be7f` is accurate — DEF-163 is already strikethrough in CLAUDE.md.
- **F20:** SystemClock wall-clock tests confirmed legitimate. No change.
- **F22:** Audit claim of 9 `@patch` sites was stale — actual count is 6, all factory-wiring patches. No change.
- **F24:** Audit claim that `AfternoonMomentumStrategy` import was unused was stale — grep confirms usage. No change.

### Partial (1)

- **F25:** Module docstring added to `test_log_throttle.py` (intentional `time.sleep` usage). `test_lifespan_startup.py` already had in-test docstring. Matches spec.

### Deferred (8 findings, 9 IDs per split notice)

All 9 (F5, F7, F8, F9, F11, F13, F18, F21, F23) back-annotated as `DEFERRED TO FIX-13b-test-hygiene-refactors` with rationale. F5 CRITICAL deferral is explicit per operator-directed Stage 8 split — **NOT a scope gap**. 25/25 findings carry STATUS lines, confirmed via grep.

### Scope-added DEF closures (4)

- **DEF-150:** closed (fold of F3/F4).
- **DEF-167:** 3 named Vitest files (`TradesPage`, `PerformancePage`, `ResearchDocCard`) converted to dynamic dates. Scope carve-out for remaining ~55 mock-fixture files is rationalized in close-out and CLAUDE.md row.
- **DEF-171:** root-caused at `tests/execution/test_ibkr_broker.py:91` (`id(order) % 10000` collisions on low 13 bits under xdist). Replaced with fixture-scoped `itertools.count(1)`. Diff + CLAUDE.md strikethrough verified.
- **DEF-190:** `tests/conftest.py` prewarm via `pd.DataFrame({"_p": [Period('2024-01', freq='M')]}) → pa.Table.from_pandas(df)` — correctly forces `register_extension_type('pandas.period')` at module-import time. Regression guard at `tests/test_def190_pyarrow_eager_import.py` grep-asserts both `_prewarm_pyarrow_pandas_extensions` + `Period(` presence.
- **DEF-192:** PARTIAL — numpy invalid-cast closed at 3 call sites; async-mock + aiosqlite + websockets.legacy + TestBaseline deferred. CLAUDE.md row updated to reflect PARTIAL with explicit remainder enumeration.

## Judgment Call Evaluation

1. **F6 enum choice (`BrokerSource.IBKR`).** Independently verified — `BrokerSource` enum in `argus/core/config.py:431-434` contains ONLY `ALPACA/IBKR/SIMULATED` (no `DATABENTO`; that's a `DataSource`). Kickoff's `SIMULATED` would flip test semantics (`_process_signal()` checks `== BrokerSource.SIMULATED` for legacy-sizing bypass). `IBKR` correctly preserves non-SIMULATED execution path. **AGREE.**

2. **F19 behavioral tightening (route-disabled site).** The replacement `pytest.raises((WebSocketDisconnect, RuntimeError))` is a deliberate tightening that surfaces the previously-swallowed `pytest.fail()`. This is a latent Sprint 25 bug (correctly documented in `prior_session_bugs`). The tightening is the literal, minimal interpretation of F19's spec ("enumerate the two") and the side effect (exposing the silent-failure) is strictly positive. **AGREE.**

3. **F19 auth-rejection tests (add `ws.receive_json()` + code assertion).** Bare `pytest.raises(WebSocketDisconnect)` without a receive attempt does not observe the Starlette close — the test would be a no-op tautology. Close-out cites matching pattern at `tests/api/test_ai_ws.py:212` as precedent. **AGREE.**

4. **DEF-167 scope boundary (3 of ~55 files).** Only the 3 kickoff-named files were converted. Remaining Vitest hardcoded dates are fixture data with no decay surface (no assertion reads the specific value). Decision is documented in CLAUDE.md row and close-out `deferred_observations`. **AGREE** — pragmatic scope discipline consistent with RULE-007.

5. **DEF-190 prewarm strengthening.** Kickoff suggested bare `import pyarrow.pandas_compat`. Correctly identified that registration is lazy (happens on first DataFrame→Arrow conversion). The Period-dtype DataFrame conversion is the minimal forcing function. The regression guard explicitly asserts both `_prewarm_pyarrow_pandas_extensions` AND `Period(` presence — protecting against a future cosmetic edit that drops the conversion. **STRONG AGREE.**

6. **DEF-192 TestBaseline revert (RULE-018 violation).** The mid-session catch is commendable. Symlink-based edits to `workflow/` were detected and reverted before commit. Git diff on `workflow/` and `scripts/sprint_runner` paths confirms zero changes. CLAUDE.md DEF-192 row correctly documents the upstream-dependency blocker. **AGREE** — this is exemplary scope hygiene.

## Regression Verification

| Check | Result |
|---|---|
| pytest net delta ≥ 0 | PASS: 4,980 → 4,987 (+7) — all from `test_logging_config.py` (+6) + `test_def190_pyarrow_eager_import.py` (+1). |
| All tests passing | PASS (close-out self-reports 0 failures; test delta positive). |
| Vitest count unchanged | PASS: 859 → 859. |
| No scope-boundary violation | PASS: `git diff dfeeb63..c9c8891 -- workflow/ scripts/sprint_runner` returns empty. |
| No Rule-4 sensitive file touched | PASS: diff limited to `tests/`, `docs/audits/`, `docs/sprints/`, `.claude/rules/testing.md`, `CLAUDE.md`, `pyproject.toml`, `argus/backtest/vectorbt_afternoon_momentum.py` (DEF-192 numpy cast), `argus/ui/src/**` (DEF-167). All declared scope. |
| Every finding back-annotated | PASS: 25/25 STATUS lines verified via grep. 10 occurrences of "DEFERRED TO FIX-13b-test-hygiene-refactors" (9 STATUS + 1 split-notice header). |
| Every DEF closure recorded in CLAUDE.md | PASS: DEF-150, DEF-167, DEF-171, DEF-190 strikethrough with RESOLVED detail; DEF-192 updated with PARTIAL + remainder enumeration; "Last updated" bumped to 2026-04-23. |
| Zero new DEFs opened | PASS: grep shows no new DEF-NNN rows; Stage 8a barrier tracks FIX-13b scope per operator directive. |
| Warning count | MIXED (as documented): 39 → 40 final run; inter-run variance 26–40 due to intermittent async-mock warnings under xdist. Numpy cast category cleanly closed. Acceptable per kickoff Hazard 4. |

## Escalation Criteria Review

- CRITICAL finding incomplete? F5 is CRITICAL but **explicitly deferred** per operator-directed Stage 8 split — not a gap. No trigger.
- pytest net delta < 0? No (+7). No trigger.
- Scope-boundary violation? Detected mid-session, reverted before commit. Diff confirms zero `workflow/` changes. No trigger.
- Different test failures vs baseline? No — close-out reports 0 persistent failures; DEF-190 now resolved. No trigger.
- Back-annotation missing/incorrect? All 25/25 findings annotated with correct STATUS categories. No trigger.
- Rule-4 sensitive file? No — all changes in declared scope. No trigger.
- New DEF opened? No. No trigger.

**No escalation criteria triggered.**

## Verdict

**CLEAR.** FIX-13a is a disciplined tactical execution with exceptional scope hygiene. The mid-session RULE-018 catch-and-revert, the independently-verified spec-drift correction on `argus/api/__main__.py`, the strengthened DEF-190 prewarm mechanism over the kickoff suggestion, and the narrowed F19 WebSocket catches (which exposed a latent Sprint 25 silent-failure) all demonstrate the kind of judgment the campaign depends on. Every one of the 7 judgment calls is well-reasoned and documented in the close-out. Test delta is positive (+7), Vitest unchanged, no workflow submodule changes, no new DEFs, all 25 findings back-annotated, and all 4 scope-added DEFs (150/167/171/190) closed with the 5th (DEF-192) appropriately marked PARTIAL.

The +7 pytest delta is slightly above the close-out's own mentioned "+5 to +15 window" — the close-out self-flags this at line 121 and notes it is in-band. Confirmed.

One minor stylistic observation (non-blocking, not a concern): the DEF-190 prewarm helper swallows exceptions via bare `except Exception: pass`. Given the context (best-effort prewarm, with explicit comment), this is acceptable; a future cleanup could narrow to `except (ImportError, AttributeError, pa.lib.ArrowKeyError)` for precision but is not required.

Recommend proceeding to the Stage 8a barrier update to seal FIX-13a and scope FIX-13b.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-13a-test-hygiene-tactical",
  "verdict": "CLEAR",
  "commit_reviewed": "c9c8891",
  "baseline_head": "dfeeb63",
  "tests": {
    "before": 4980,
    "after": 4987,
    "delta": 7,
    "all_pass": true,
    "vitest_before": 859,
    "vitest_after": 859
  },
  "escalation_triggers": {
    "critical_finding_incomplete": false,
    "pytest_net_delta_negative": false,
    "scope_boundary_violation": false,
    "different_test_failures": false,
    "back_annotation_missing": false,
    "rule4_sensitive_file_touched": false,
    "new_def_opened": false
  },
  "findings_accounting": {
    "resolved": 15,
    "resolved_verified": 4,
    "partial": 1,
    "deferred_to_fix13b": 9,
    "total": 29,
    "note": "25 unique spec findings + 4 scope-added DEF closures. F7 and F8 listed separately in spec but deferred as a linked pair (close-out: 'F7/F8'). Split notice references deferral in header (10 grep hits for 'DEFERRED TO FIX-13b')."
  },
  "scope_violations": [],
  "judgment_calls_evaluated": [
    {"id": "F6_enum_choice", "verdict": "AGREE", "note": "BrokerSource.IBKR correctly preserves non-SIMULATED semantics. Independently verified enum values at argus/core/config.py:431-434 (no DATABENTO)."},
    {"id": "F19_route_disabled_narrowing", "verdict": "AGREE", "note": "Narrowing to (WebSocketDisconnect, RuntimeError) exposes a latent Sprint 25 silent-failure in a pytest.fail() call. Behavioral tightening is a strictly positive side effect of the literal F19 spec."},
    {"id": "F19_auth_rejection_pattern", "verdict": "AGREE", "note": "ws.receive_json() + 4001 assertion is required — Starlette TestClient does not raise on connect alone. Matches precedent at tests/api/test_ai_ws.py:212."},
    {"id": "DEF167_scope_carveout", "verdict": "AGREE", "note": "3 kickoff-named files converted; ~55 remaining files are mock-fixture data with no decay surface. Pragmatic RULE-007 scope discipline."},
    {"id": "DEF190_prewarm_strengthening", "verdict": "STRONG_AGREE", "note": "Kickoff's bare import was insufficient; Period-dtype conversion is the minimal forcing function. Regression guard asserts both helper + Period() presence."},
    {"id": "DEF192_TestBaseline_revert", "verdict": "AGREE", "note": "RULE-018 violation caught and reverted mid-session. Git diff confirms zero workflow/ changes. Blocker correctly documented in CLAUDE.md DEF-192 row."},
    {"id": "F14_spec_drift_argus_api_main", "verdict": "AGREE", "note": "Independently verified: argus/api/__main__.py does not exist (consistent with DEF-169 --dev mode retirement). Only setup_password.py in coverage omit is correct."}
  ],
  "concerns": [],
  "escalation_items": [],
  "notes": "Exemplary tactical session. Mid-session RULE-018 catch, spec-drift verifications, and proactive DEF-190 prewarm strengthening demonstrate strong judgment. +7 test delta within close-out's self-noted +5 to +15 window. Ready for Stage 8a barrier update and FIX-13b scoping.",
  "recommended_next_action": "Proceed to Stage 8a barrier update; scope FIX-13b-test-hygiene-refactors with the 8 deferred finding units (F5, F7+F8, F9, F11, F13, F18, F21, F23)."
}
```

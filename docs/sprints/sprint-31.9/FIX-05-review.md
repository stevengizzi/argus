```markdown
---BEGIN-REVIEW---

**Reviewing:** Sprint 31.9 Phase 3 audit remediation — `FIX-05-core-orchestrator-risk-regime` (Stage 4 Wave 2)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-22
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 30 modified files fall within the spec's declared scope or its theme ("delete dead accounting/ + notifications/ packages", "Regime Intelligence typing"). Two consequent test-only edits (`tests/core/test_clock.py`, `tests/core/test_vix_calculators.py`) and one reachable production file (`argus/data/vix_data_service.py` — public `config` property added) are necessary consequences of declared findings (L5 FixedClock timezone + DEF-091 VIXDataService accessor) and are documented as judgment calls #5 and in the DEF-091 closure. No Rule-4-sensitive files touched. |
| Close-Out Accuracy | PASS | Change manifest matches actual diff; judgment calls cover each non-mechanical decision. One minor cosmetic inaccuracy: close-out says "12 enum members match" for `ExitReason` re-export; actual count is 11. Enum identity is preserved, no behavioral impact. |
| Test Health | PASS | Full suite: `5000 passed, 43 warnings in 67.54s` (0 failures). Vitest: `859 passed / 115 files`. DEF-150 flake did not fire. +10 new tests match the claimed delta precisely (+5 in test_risk_manager, +4 in test_regime_vector_expansion, +1 in test_clock). |
| Regression Checklist | PASS | All 8 checks verified — see individual results below. |
| Architectural Compliance | PASS | Event bus typing tightened (`TypedEventHandler[T]`), dataclass discipline preserved (`kw_only=True` on `CircuitBreakerEvent`), private-attr reach-ins eliminated (DEF-091), ET-canonical time handling reinforced (DEF-163 + L5). Zero new `# type: ignore` introduced. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL finding mis-resolved; pytest net delta +10 ≥ 0; no scope boundary violation; no new test failures beyond the expected DEF-150 window; no Rule-4 sensitive file touched; audit back-annotations present across all 5 audit docs; CRITICAL regression tests exercise the previously-uncovered lines. |

### Regression Checklist — Per-Item Verification

1. **pytest net delta ≥ 0 against baseline 4,990 passed** — PASS. Local run: 5,000 passed. Net +10 matches claim.
2. **DEF-150 remains sole pre-existing failure** — PASS. 0 failures observed. DEF-150 is time-of-day-bounded (minute ∈ {0,1}); tests ran at 14:58 ET, outside that window.
3. **No file outside declared Scope modified** — PASS. `argus/core/vix_calculators.py` is explicitly cited in P1-A2-L09 (spec line 173); `argus/notifications/__init__.py` deletion is in the declared theme; `argus/data/vix_data_service.py` edit is a minimal 10-line public-accessor addition required by DEF-091. Test file edits are consequent to in-scope source changes. Ops file `RUNNING-REGISTER.md` is a sprint-level status update consistent with prior FIX-NN sessions.
4. **Audit-report back-annotations present** — PASS. FIX-05 mention counts: p1-a2-core-rest.md=28, p1-g1-test-coverage.md=7, p1-g2-test-quality.md=5, p1-d1-catalyst-quality.md=3, p1-h4-def-triage.md=6. All 5 audit docs appended FIX-05 Resolution content.
5. **DEF closures recorded in CLAUDE.md** — PASS. DEF-091/092/104/163/170 all marked `~~DEF-NNN~~` strikethrough with RESOLVED detail and FIX-05 attribution. DEF-182 opened with complete context.
6. **New DEFs referenced in commit message bullets** — PASS (commit `4590859` references DEF-182 closure context).
7. **`read-only-no-fix-needed` findings verified and annotated** — PASS. M7 (7 unused RegimeVector fields) RESOLVED-VERIFIED via grep; annotated in audit doc; rationale documented in close-out judgment call #8.
8. **`deferred-to-defs` findings: fix applied AND DEF opened** — PASS. L11 Weekly reconciliation: log level upgraded to WARNING with inline DEF-182 reference; DEF-182 opened in CLAUDE.md with complete implementation plan.

### Specific Verification Tasks

#### 1. CRITICAL C1 coverage (P1-G1-C01) — PASS
`tests/core/test_risk_manager.py::TestPostCloseCircuitBreaker` contains two tests that correctly exercise `_check_circuit_breaker_after_close()` (now at `risk_manager.py:661-679`, shifted from the spec's `:618-638` due to docstring rewrites):
- `test_cumulative_close_losses_trigger_circuit_breaker`: publishes 3 `PositionClosedEvent`s totaling -$3,100 via the event bus, forcing the method through `_on_position_closed → _check_circuit_breaker_after_close`. Asserts (a) `CircuitBreakerEvent` published with `level.value == "account"` and `"daily loss" in reason.lower()`, (b) `rm.circuit_breaker_active is True`, (c) subsequent `evaluate_signal` returns `OrderRejectedEvent` with `"circuit breaker" in reason`. All three spec requirements met.
- `test_post_close_check_noop_when_breaker_already_active`: pre-sets `_circuit_breaker_active=True` then publishes a losing close. Asserts no duplicate `CircuitBreakerEvent` published but `daily_realized_pnl` still accumulates — correctly exercises the early-return at `:663`. Tests PASSED on targeted run.

#### 2. CRITICAL C2 coverage (P1-G1-C02) — PASS
`TestPositionSizingRejectAfterReduction`:
- `test_cash_reserve_reduced_below_min_floor_rejects`: Signal of 100 shares @ $150 with stop $149.80 (risk_per_share=0.20) against initial_cash=10_000, cash_reserve_pct=0.50. Available=5,000; cost=15,000 triggers reduction; reduced=int(5000/150)=33; reduced_risk=33×0.20=$6.60 < $100 floor → reject. Asserts reason contains "cash reserve" and "$100 minimum". Exercises `risk_manager.py:427-440` (post-docstring-shift equivalent of spec's `:386-394`).
- `test_buying_power_reduced_below_min_floor_rejects`: Uses new `_LowBuyingPowerBroker` subclass (necessary since `SimulatedBroker.buying_power == cash` in V1). Test traces: step 7 cash-reserve reduces 100→33 at $330 risk (passes floor); step 8 buying-power further reduces 33→1 at $10 risk < $100 → reject. Asserts reason contains "buying power" and "$100 minimum". Exercises `risk_manager.py:449-462` (equivalent of spec's `:405-421`). The `_LowBuyingPowerBroker` subclass is an appropriate minimal test double; it overrides only `get_account()` and preserves all other `SimulatedBroker` semantics.

Both CRITICAL tests PASSED on targeted `-v` run. Would fail deterministically if the reject-after-reduction branches were regressed (verified by trace-reading the branch logic).

#### 3. DEF-170 resolution — PASS
`argus/core/regime.py:700-713`: `attach_vix_service()` now calls `self._build_vix_calculators(vix_data_service)` inside a `if self._regime_config.vix_calculators_enabled:` guard. Previously, the method only stored the reference (`self._vix_data_service = vix_data_service`), leaving the four calculators `None` in production because `main.py` constructs V2 before the VIX service is ready.

`_build_vix_calculators()` helper at `:671-698` factors the instantiation logic so both constructor-time wiring and `attach_vix_service()` share one path. Uses the public `vix_data_service.config` property (not `._config`).

Regression: `TestAttachVixServiceRewiresCalculators` (4 tests) — `test_calculators_none_when_constructed_without_service` establishes the pre-condition; `test_attach_service_post_construction_builds_calculators` asserts all four calculators become non-None; `test_attach_service_is_idempotent` verifies repeated attaches don't error; `test_attach_service_respects_vix_calculators_disabled` verifies the config guard. All 4 PASSED.

#### 4. DEF-091 public accessor cleanup — PASS
- `argus/data/vix_data_service.py:248-258`: added `config` property returning `self._config`.
- `argus/core/regime.py:371-378`: `RegimeClassifier` exposes `vol_low_threshold` and `vol_high_threshold` `@property` accessors.
- `argus/core/regime.py:516-526`: `RegimeClassifier.compute_trend_score()` public method delegating to `_compute_trend_score()`.
- `argus/core/regime.py:803`: `RegimeClassifierV2.compute_regime_vector` uses `self._v1_classifier.compute_trend_score(indicators)` — verified (not `._compute_trend_score`).
- `argus/core/regime.py:968-969`: `_compute_vol_direction` uses `self._v1_classifier.vol_low_threshold` and `.vol_high_threshold` — verified (not `._config.*`).

Grep confirmed no remaining private-attr reach-ins from V2 → V1 or V2 → VIXDataService.

#### 5. DEF-104 ExitReason consolidation — PASS
`argus/core/events.py:40-46`: replaces inline 11-member enum with `from argus.models.trading import ExitReason as ExitReason`. Verified via `python -c "from argus.core.events import ExitReason; from argus.models.trading import ExitReason as T; print('same object:', ExitReason is T)"` — **True** (both identifiers point at the same class object).

Minor: close-out claims "12 enum members match" but both old `argus.core.events.ExitReason` and `argus.models.trading.ExitReason` contain exactly 11 members: `TARGET_1`, `TARGET_2`, `TARGET_3`, `STOP_LOSS`, `TRAILING_STOP`, `TIME_STOP`, `EOD_FLATTEN`, `MANUAL`, `CIRCUIT_BREAKER`, `EMERGENCY`, `RECONCILIATION`. Names and values are identical; re-export preserves the complete enum surface. Off-by-one in documentation only; no behavioral issue. (LOW-severity finding, below CONCERNS threshold.)

#### 6. P1-A2-M04 orchestrator extraction — PASS
`argus/core/orchestrator.py:733-769`: new `_compute_and_apply_regime(spy_bars) -> MarketRegime` helper. Updates `self._current_indicators`, `self._spy_unavailable_count = 0`, `self._latest_regime_vector`, and fires `asyncio.create_task(self._regime_history.record(vector))`. Docstring explicitly notes the helper does NOT update `self._current_regime` or `self._last_regime_check` (caller ownership preserved).

`run_pre_market` (`:311`) and `reclassify_regime` (`:796`) both delegate to this helper. Semantics preserved: `run_pre_market` still sets `self._current_regime = new_regime` post-call and never touches `_last_regime_check`; `reclassify_regime` still sets both. Compared diff against original (baseline `4829214`) — the extracted helper exactly mirrors the previously-duplicated block.

#### 7. Dead package deletions (P1-A2-M09) — PASS
Both `argus/accounting/` and `argus/notifications/` directories removed (`ls` returns "No such file or directory"). Original content was single-line docstrings (`"""Accounting: tax tracking, P&L, wash sale detection."""` and `"""Notifications: push, email, Telegram, Discord handlers."""`). Grep for `from argus.accounting` / `from argus.notifications` / `import argus.accounting` / `import argus.notifications` across `argus/` and `tests/` returned zero hits. Clean deletion.

#### 8. Audit back-annotations — PASS
All 5 audit docs updated with FIX-05 Resolution sections:
- `p1-a2-core-rest.md` — P1-A2 M/L findings (most comprehensive, 28 FIX-05 references).
- `p1-g1-test-coverage.md` — C1/C2/M5/M6/M8.
- `p1-g2-test-quality.md` — M1/L1.
- `p1-d1-catalyst-quality.md` — M7.
- `p1-h4-def-triage.md` — DEF-091/092/104/163/170 closures.

#### 9. Close-out fidelity — PASS
`git diff --name-only 4829214..HEAD` yields 30 files. Close-out's "Files modified" section lists 28 (omits `docs/sprints/sprint-31.9/FIX-05-closeout.md` which is the close-out itself — reasonable self-reference omission — and `docs/sprints/sprint-31.9/RUNNING-REGISTER.md`). `RUNNING-REGISTER.md` is a campaign-level ops status update consistent with prior FIX-NN sessions' behavior; its omission from the close-out manifest is a minor documentation gap but not an undisclosed file touch (the edit is a three-bullet status update with no code impact).

### Findings

#### LOW: Minor close-out documentation inaccuracies

1. **ExitReason member count off-by-one.** Close-out says "all 12 enum members match"; actual count is 11. Both old and new definitions are identical; re-export is correct. File: `docs/sprints/sprint-31.9/FIX-05-closeout.md`. Recommendation: none (cosmetic, no behavioral impact).

2. **`RUNNING-REGISTER.md` edit not listed in close-out manifest.** The change is a campaign-tracking status update (bumping "Stage 4 Wave 2" from PENDING to CLEAR, updating baseline tests 4,985 → 5,000). Recommendation: future FIX-NN close-outs could include sprint ops files in the manifest for completeness; not a blocker.

### Recommendation

**Proceed to next session** (Stage 5: FIX-06 data + FIX-07 intelligence). All 37 findings addressed per spec. Both CRITICALs land with regression tests that actively exercise the previously-uncovered branches — confirmed via targeted runs and trace-reading. 5 DEFs closed with accurate context; 1 new DEF (DEF-182) opened with complete implementation plan. No scope boundary violations, no regressions, zero test failures, clean architectural posture throughout.

The 9 judgment calls in the close-out are all well-justified and conservative — particularly the DEF-170 resolution via `attach_vix_service()` re-instantiation (preserving existing phase ordering) and the L11 stub-to-DEF promotion (documenting a known incompleteness rather than smuggling in a cross-domain implementation).

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "31.9-phase-3-audit",
  "session": "FIX-05-core-orchestrator-risk-regime",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "Close-out states 'all 12 enum members match' for the re-exported ExitReason; actual count is 11 members (TARGET_1, TARGET_2, TARGET_3, STOP_LOSS, TRAILING_STOP, TIME_STOP, EOD_FLATTEN, MANUAL, CIRCUIT_BREAKER, EMERGENCY, RECONCILIATION). Enum identity is correctly preserved; cosmetic documentation error only.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "docs/sprints/sprint-31.9/FIX-05-closeout.md",
      "recommendation": "No action required. Note for future close-out precision."
    },
    {
      "description": "docs/sprints/sprint-31.9/RUNNING-REGISTER.md was edited as a campaign-tracking status update but is not listed in the close-out's Files Modified manifest. Edit content is a three-bullet sprint-stage status update with no code impact.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "docs/sprints/sprint-31.9/RUNNING-REGISTER.md",
      "recommendation": "Future FIX-NN close-outs may include sprint ops files in the manifest for completeness."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 37 findings addressed (36 RESOLVED, 1 RESOLVED-VERIFIED). Both CRITICALs covered by regression tests exercising the previously-uncovered lines. Judgment calls documented with rationale. No spec-by-contradiction violations.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/core/risk_manager.py",
    "argus/core/regime.py",
    "argus/core/orchestrator.py",
    "argus/core/events.py",
    "argus/core/event_bus.py",
    "argus/core/health.py",
    "argus/data/vix_data_service.py",
    "argus/models/trading.py",
    "tests/core/test_risk_manager.py",
    "tests/core/test_regime_vector_expansion.py",
    "tests/core/test_clock.py",
    "tests/analytics/test_def159_entry_price_known.py",
    "docs/sprints/sprint-31.9/FIX-05-closeout.md",
    "docs/sprints/sprint-31.9/RUNNING-REGISTER.md",
    "docs/audits/audit-2026-04-21/p1-a2-core-rest.md",
    "docs/audits/audit-2026-04-21/p1-g1-test-coverage.md",
    "docs/audits/audit-2026-04-21/p1-g2-test-quality.md",
    "docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md",
    "docs/audits/audit-2026-04-21/p1-h4-def-triage.md",
    "CLAUDE.md",
    "docs/architecture.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 5000,
    "new_tests_adequate": true,
    "test_quality_notes": "+10 regression tests, all passing. 9 tests targeted at the CRITICAL/DEF-170 paths verified independently with -v. TestPostCloseCircuitBreaker correctly drives the event-bus path (not just direct attribute manipulation) so the _on_position_closed -> _check_circuit_breaker_after_close sequence is genuinely exercised. _LowBuyingPowerBroker is an appropriate minimal test double for the buying-power reject-after-reduction branch which is otherwise unreachable with SimulatedBroker V1 (buying_power == cash). Vitest: 859/859 pass."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 4,990", "passed": true, "notes": "Actual: 5000 passed, +10 matches claim exactly"},
      {"check": "DEF-150 flake remains the only pre-existing failure", "passed": true, "notes": "0 failures in this run; DEF-150 is time-of-day-bounded and did not fire at 14:58 ET"},
      {"check": "No file outside declared Scope modified", "passed": true, "notes": "All 30 modified files are within declared scope, theme scope (notifications deletion), or are necessary consequents (test files, vix_data_service.py for the DEF-091 accessor addition)"},
      {"check": "Different test failure surfaces (not DEF-150)", "passed": true, "notes": "0 failures total"},
      {"check": "Audit-report back-annotation correct", "passed": true, "notes": "FIX-05 mentions: p1-a2=28, p1-g1=7, p1-g2=5, p1-d1=3, p1-h4=6"},
      {"check": "DEF closures recorded in CLAUDE.md", "passed": true, "notes": "DEF-091/092/104/163/170 strikethrough+RESOLVED; DEF-182 opened"},
      {"check": "read-only findings verified (M7)", "passed": true, "notes": "RESOLVED-VERIFIED with grep evidence in close-out judgment call #8"},
      {"check": "deferred-to-defs findings produced DEF entry (L11)", "passed": true, "notes": "DEF-182 opened with full implementation plan; health.py WARNING upgrade references DEF-182 inline"},
      {"check": "CRITICAL regression tests actually exercise uncovered lines", "passed": true, "notes": "C1: TestPostCloseCircuitBreaker drives risk_manager.py:661-679 via event bus (line shift from spec's :618-638 due to docstring rewrites; verified equivalence). C2: TestPositionSizingRejectAfterReduction drives risk_manager.py:427-440 (cash-reserve reject) and :449-462 (buying-power reject)."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to Stage 5 (FIX-06 data + FIX-07 intelligence).",
    "Future FIX-NN close-outs may include sprint ops files (RUNNING-REGISTER.md) in the Files Modified manifest for completeness."
  ]
}
```

# IMPROMPTU-09 Tier 2 Review

**Verdict:** CLEAR
**Reviewer:** reviewer subagent (standard profile)
**Session commit:** uncommitted (HEAD = `2d703ff`; 3 modified docs + 2 new docs staged but not yet committed)
**Date:** 2026-04-24

## 1 — Scope boundary verification

`git diff --stat` output:

```
 CLAUDE.md                                                 | 1 +
 docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md | 2 +-
 docs/sprints/sprint-31.9/RUNNING-REGISTER.md              | 4 +++-
```

Untracked: `IMPROMPTU-09-verification-report.md`, `IMPROMPTU-09-closeout.md`.

Per-bucket verification:
- `git diff argus/` → empty ✅
- `git diff tests/` → empty ✅
- `git diff config/` → empty ✅
- `git diff docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` → empty ✅
- `git submodule status workflow/` → `edf69a5` (unchanged from prior commit, no submodule pointer move) ✅

All scope-boundary constraints from kickoff §Constraints satisfied. Read-only discipline observed.

## 2 — Per-gap evidence audit

| VG | Evidence type | Concrete? | Comment |
|----|---------------|-----------|---------|
| VG-1 | log grep + code excerpt | ✅ YES | 44 ERROR lines on Apr 24, 0 on Apr 22/23, code at `order_manager.py:1715-1722` quoted; cross-reference 1:1 with EOD CRITICAL "remain" list. |
| VG-2 | code inspection only | ✅ YES (with caveat) | 6 grep hits on `argus/main.py` (lines 123/197/201/376/378/386/397/1074); call site + gate site enumerated; honest INCONCLUSIVE because positions=0 today. Caveat: closeout cites test name `test_violation_disables_flatten` which doesn't exist (see §8 Findings). |
| VG-3 | SQL × 3 + code excerpt | ✅ YES | Three SQL queries: (1) quality_history per-day (50.0 constant 33,743 rows), (2) catalyst_events stats (varying quality_score 5–82), (3) catalyst_events blank-symbol breakdown (100% blank Apr 20–24). Quality Engine source quoted at `quality_engine.py:127-142`. |
| VG-4 | SQL × 2 | ✅ YES | Per-day grade distribution with non-trivial counts; composite-score MIN/MAX/AVG showing 35.3–70.8 / ~55 mean. |
| VG-5 | log grep | ✅ YES | Both sentinel lines reproduced verbatim with timestamps. |
| VG-6 | log grep × 2 | ✅ YES | Honest discovery — class name `IntradayCandleStore` returned 0 hits, alias `candle_store` returned the boot-health line + mid-session bar-serving line. Reviewer agrees with the alias-substitution reasoning. |
| VG-7 | SQL + config grep | ✅ YES | BITO trades enumerated with shares/notional; risk_limits.yaml shows `max_single_stock_pct: 0.05`; arithmetic checks (5,514sh × $10.85 = $59.8K = 7.5% of $794K). |
| VG-8 | code excerpt + log volume | ✅ YES | `pattern_strategy.py:315-324` shows `logger.debug` with inline IMPROMPTU-04 C1 justification comment; wc -l + grep -c reproduce 86.1% / 97.4% reductions. |
| VG-9 | SQL schema + per-day | ✅ YES | `regime_snapshots` schema confirms `vix_close REAL`; per-day non-null counts 10/14, 13/14, 13/14 for Apr 22/23/24 with daily-close values matching yfinance. |

**All 9 gaps have concrete evidence.** Zero "CONFIRMED without evidence" entries. Review focus item #2 satisfied.

## 3 — New DEF specificity

**DEF-206** (CLAUDE.md line 434):
- ✅ Specific evidence: 33,743 quality_history rows + 4,457 catalyst_events rows + the regression-onset window (between Apr 3 and Apr 20).
- ✅ Reproduction: SQL queries inline in verification report §VG-3 (3 queries against argus.db / catalyst.db).
- ✅ Priority: MEDIUM (data-quality, not safety).
- ✅ Horizon: "Opportunistic / catalyst-layer session (not blocking Sprint 31.9 close)".
- ✅ Cross-refs: ~~DEF-082~~, ~~DEF-142~~, DEC-311, DEC-384, Apr 22 debrief §B3.
- ✅ Hypothesis: classifier→storage symbol-extraction dropout in SEC EDGAR/FMP/Finnhub paths.
- ✅ Self-disambiguation: explicitly "NOT a FIX-01 regression" (preserves prior FIX-01 closure trust).

DEF-206 is reproducible, specific, and well-bounded. Review focus item #4 satisfied.

## 4 — Inconclusive follow-up

VG-2 verdict INCONCLUSIVE. Follow-up plan:
- Auto-resolves on next non-empty broker boot — concrete trigger condition, not "TBD".
- Code-side regression-test backstop cited.
- No new DEF needed (correct call: code is verified by inspection; behavior-under-violation is exercised by unit tests).

The plan is acceptable. **However**, the closeout (§5 + §12) and the verification report (§VG-2 follow-up paragraph) cite the regression test as `tests/test_startup_position_invariant.py::test_violation_disables_flatten`. That exact test name does not exist (`grep -rn "test_violation_disables_flatten" tests/` returns zero hits). The actual violation-branch tests are `test_single_short_fails_invariant`, `test_mixed_longs_and_shorts_returns_just_the_shorts`, and `test_position_without_side_attr_fails_closed` — 3 of the 5 tests in that file, all passing. The behavioural backstop exists, just under different names. See §8 Findings.

The auto-resolution path (next non-empty broker boot exercises the helper) is concrete and acceptable. Review focus item #3 satisfied.

## 5 — Pytest + baseline

Closeout §10 cites: `5068 passed, 12 failed, 29 warnings in 51.28s`.

Expected post-IMPROMPTU-11 baseline (per RUNNING-REGISTER + DEF-205 row): 5,068 pass + 12 DEF-205 fail. **Delta = 0.** ✅

Read-only session correctly produced zero pytest baseline movement. Review focus item #6 satisfied.

## 6 — Apr 24 pre-populated-evidence faithfulness

Cross-checked the four pre-populated gaps against the Apr 24 debrief at `docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md`:

| VG | Debrief section | Claim faithful? |
|----|----------------|-----------------|
| VG-1 | §A1 (RESOLVED) | ✅ YES — 44 DETECTED lines + 1.00× ratios across 44 symbols + zero doublings. The verification report's grep counts (44 on Apr 24, 0 on Apr 22/23) reproduce the debrief's claim independently. |
| VG-2 | §B6 (PRESENT but UNEXERCISED) | ✅ YES — debrief says "Today's boot had positions=0... no invariant log line fired"; report's evidence ("13:17:39 UTC — IBKRBroker connected at 127.0.0.1:4002 (clientId=1, positions=0)") matches. INCONCLUSIVE verdict honestly tracks the unexercised state. |
| VG-8 | §B4 (VALIDATED) | ✅ YES — debrief cites 130,593 vs 938,754 (86%) total + 21,891 vs 829,190 (97%) pattern_strategy. Report's `wc -l` and `grep -c` outputs reproduce both ratios exactly. |
| VG-9 | §B1 (VALIDATED at boot) | ✅ YES — debrief claim "boot-side log-confirmed; DB-side query is IMPROMPTU-09 VG-9". Report's SQL produced 10/14, 13/14, 13/14 non-null counts matching daily VIX closes 19.18/19.31/18.95 — extending the boot-side claim to DB-side validation as designed. |

All four pre-populated debrief claims faithfully reflected. Review focus item #7 satisfied.

## 7 — Sprint-level regression

| Check | Result |
|-------|--------|
| pytest net delta | 0 ✅ (5,068 pass + 12 DEF-205 fail unchanged) |
| Vitest count | unchanged (no UI surface touched) ✅ |
| Scope boundary violation | none ✅ (`git diff --stat` shows only docs files) |
| CLAUDE.md DEF-206 self-consistency | ✅ priority MEDIUM, horizon defined, evidence concrete, cross-refs present, sequential after DEF-205 |
| Workflow submodule | unchanged at `edf69a5` ✅ |
| Apr 22 debrief preserved | ✅ (`git diff` empty) |
| Audit-2026-04-21 back-annotations | unchanged ✅ |

## 8 — Findings

**LOW — Test name citation inaccuracy (verification report VG-2 follow-up + closeout §5 + §12).**
The closeout cites `tests/test_startup_position_invariant.py::test_violation_disables_flatten` as the regression backstop for the violation branch. That exact test name does not exist (verified via `grep -rn "test_violation_disables_flatten" tests/`). The file does contain 5 tests, 3 of which exercise the violation branch (`test_single_short_fails_invariant`, `test_mixed_longs_and_shorts_returns_just_the_shorts`, `test_position_without_side_attr_fails_closed`). The substantive claim is correct (violation behaviour is unit-tested); only the test name is wrong.

Suggested resolution: in a future doc-touch pass, replace the cited name with one of the 3 actual violation-branch tests (e.g., `test_single_short_fails_invariant`) in the verification report §VG-2 follow-up paragraph and closeout §5 / §12. Not blocking — the spirit of the claim is satisfied by inspection of the file.

**No HIGH or MEDIUM findings.** No ESCALATE triggers fired.

## 9 — Final verdict + rationale

**CLEAR.**

Rationale:
- All 9 verification gaps have concrete SQL/grep/code-excerpt evidence (review focus item #2).
- INCONCLUSIVE gap (VG-2) has a concrete auto-resolution trigger and a code-inspection + unit-test backstop (review focus item #3 — modulo the LOW test-name finding).
- DEF-206 is specific, reproducible, prioritised, and horizon-bound (review focus item #4).
- 9-gap count matches plan with documented justification for the 3 dropped Apr 22 §Open Verification Gaps items (review focus item #5).
- Pytest delta = 0; baseline 5,068 + 12 DEF-205 unchanged (review focus item #6).
- Apr 24 debrief evidence faithfully reflected for all 4 pre-populated gaps (review focus item #7).
- Read-only discipline observed: zero `argus/` / `tests/` / `config/` / Apr-22-debrief / workflow-submodule changes (review focus item #1).
- CLAUDE.md DEF-206 row is self-consistent with priority + horizon + cross-refs.
- The single LOW finding (test-name citation drift) is a documentation-hygiene nit, not a substantive deviation; the violation-branch behaviour is genuinely unit-tested.

No ESCALATE triggers fired.

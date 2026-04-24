# IMPROMPTU-09 Close-Out — April 22/23/24 Debrief Verification Sweep

> **Session:** IMPROMPTU-09 (Sprint 31.9, Stage 9C)
> **Date:** 2026-04-24
> **Baseline commit (pre-session):** `2d703ff` (TEST-HYGIENE-01 kickoff insertion)
> **Session commit:** *pending this commit*
> **Verdict (self-assessment):** **CLEAN** — read-only discipline observed, all 9 gaps have concrete evidence, 1 new DEF opened with reproduction steps.
> **Context state:** GREEN — no compaction; moderate context use.

## 1 — Gap Count

**Planned:** 9 (8 from Apr 22 debrief + 1 from Apr 23 §B1).

**Actual:** 9, no deviation.

Mapping reconciled to the kickoff's pre-populated-by-Apr-24 hints:
VG-1 = A1 fire-test (IMPROMPTU-04 production behavior), VG-2 = startup
invariant, VG-3..VG-7 = five Apr 22 §Open Verification Gaps items,
VG-8 = C1 log downgrade, VG-9 = VIX DB-side verification.

Three items from Apr 22 §Open Verification Gaps were **not carried
forward** (and documented as such in §1 of the report): daily cost
ceiling for catalyst classifier (deferred to SPRINT-CLOSE doc pass), 11
`_init_*` lifespan phases (superseded by IMPROMPTU-07 path (b) closing
DEF-198), and end-to-end trace of AAL (superseded by IMPROMPTU-11's
IMSR trace). This reduced the candidate pool from 11 to the planned 9.

## 2 — Aggregate Result Table

| VG | Title | Conclusion | New DEF | Close DEF | Follow-up |
|----|-------|-----------|---------|-----------|-----------|
| VG-1 | A1 fix fires in production (44 × DETECTED UNEXPECTED SHORT) | **CONFIRMED** | — | — (DEF-199 closed earlier by IMPROMPTU-04) | none |
| VG-2 | Startup invariant present and exercisable | **INCONCLUSIVE** (present-by-inspection; unexercised today) | — | — | MONITOR (auto-resolves on next non-empty broker boot) |
| VG-3 | FIX-01 catalyst_quality non-constant | **REFUTED** (50.0 constant; 100% blank-symbol catalyst_events Apr 20–24) | **DEF-206** | — | Open DEF-206 — catalyst ingestion symbol-attachment audit |
| VG-4 | Quality grade distribution shift | **CONFIRMED** (7 grades, B+/B/B-/A- dominant) | — | — | none |
| VG-5 | First-event sentinels fire | **CONFIRMED** (NOK + SOXX at boot) | — | — | none |
| VG-6 | IntradayCandleStore init | **CONFIRMED** (via component alias `candle_store`) | — | — | none |
| VG-7 | BITO concentration 8% > 5% | **CONFIRMED** (Apr 22 BITO 5,514sh / $59.8K / 7.5%) | — (cross-ref DEF-195) | — | DEF-195 already open; noted per-signal-vs-aggregate fix lever |
| VG-8 | C1 log downgrade | **CONFIRMED** (86% total-line + 97% pattern_strategy reduction) | — | — | none |
| VG-9 | VIX dimensions in regime_history.db | **CONFIRMED** (10–13 of 11–14 snapshots/day non-null; daily close 19.18/19.31/18.95) | — | — | none |

**Aggregate:** 6 CONFIRMED, 1 REFUTED, 1 INCONCLUSIVE-but-present, 1 CONFIRMED-cross-referenced. **1 new DEF opened; 0 DEFs closed this session.**

## 3 — Newly Opened DEFs

- **DEF-206** — Catalyst ingestion stores events with blank `symbol` column; Quality Engine catalyst_quality stays at default 50.0. **MEDIUM** priority (data-quality / training-signal integrity; not trading-safety). Evidence: 33,743 quality_history rows Apr 22/23/24 exact constant 50.0; 4,457 catalyst_events rows Apr 20–24 all blank/NULL symbol; earlier Mar 30 – Apr 3 rows had populated symbols (e.g., NOA via finnhub). NOT a FIX-01 regression — upstream ingestion defect. Horizon: opportunistic / natural-fit in a catalyst-layer session; not blocking Sprint 31.9 close.

## 4 — Closed DEFs

None. DEF-199 (VG-1's related DEF) was already closed by IMPROMPTU-04 commit `0623801` on Apr 23. This session produced production-log evidence that reconfirms the closure against two post-fix paper sessions — but no DEF state transition happens here.

## 5 — Items Deferred

- **VG-2 startup invariant exercise against non-empty broker state** — MONITOR. Will auto-resolve on the next paper session that boots with any remaining broker position. No active tracking needed; the code path is validated by 3 of the 5 tests in `tests/test_startup_position_invariant.py` (`test_single_short_fails_invariant`, `test_mixed_longs_and_shorts_returns_just_the_shorts`, `test_position_without_side_attr_fails_closed`).
- **DEF-206 catalyst-ingestion audit** — deferred to an opportunistic catalyst-layer session. Not blocking Sprint 31.9 close.
- **Daily cost ceiling for catalyst classifier (original Apr 22 §Open Gaps row 3)** — not carried into VG-1..VG-9; can be validated during SPRINT-CLOSE doc pass as a one-line SQL check against `catalyst.db` spend ledger if the operator wants it recorded.

## 6 — Change Manifest

**Files added:**
- `docs/sprints/sprint-31.9/IMPROMPTU-09-verification-report.md` (NEW)
- `docs/sprints/sprint-31.9/IMPROMPTU-09-closeout.md` (this file, NEW)
- `docs/sprints/sprint-31.9/IMPROMPTU-09-review.md` (Tier 2, to be written after close-out)

**Files modified:**
- `CLAUDE.md` — DEF-206 row appended after DEF-205.
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — IMPROMPTU-09 row added under session-execution table; DEF-206 row appended under campaign-scoped DEF register; Stage 9C row updated to mark IMPROMPTU-09 ✅ CLEAR.
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — Stage 9C IMPROMPTU-09 row updated from ⏸ PENDING to ✅ CLEAR.

**Files NOT modified (read-only verification per scope):**
- Any `argus/` source file — `git diff argus/` empty.
- Any `config/` file — `git diff config/` empty.
- Any `tests/` file — `git diff tests/` empty.
- `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` — Apr 22 debrief triage preserved per constraint.
- Any `workflow/` submodule file — Universal RULE-018 respected.
- Any audit-2026-04-21 back-annotation — scope boundary observed.

## 7 — Judgment Calls

- **Gap enumeration:** chose to align with the kickoff's explicit pre-population hints (VG-1/2/8/9 = IMPROMPTU-04 production behaviors + Apr 23 VIX DB). This meant inferring a mapping rather than straight-reading Apr 22 §Open Verification Gaps row 1 through row 8. Documented the mapping + the 3 dropped items in §1 of the verification report with rationale. Alternative would have been to use the Apr 22 row order literally, which would have made the kickoff's "pre-populated 4 of 9" text inconsistent with reality. Chose clarity over literal row-order.
- **DEF-206 framing:** explicitly called out that the REFUTED VG-3 is NOT a FIX-01 regression — FIX-01 fixed the DB path (DEF-082) as designed. The catalyst_quality=50.0 result comes from a separate upstream bug (100% blank-symbol catalyst_events). This distinction matters for reviewer trust in prior FIX-01 work and matters for scoping DEF-206's fix session (catalyst ingestion, not storage).
- **VG-7 cross-reference:** observed the BITO 7.5% aggregate, confirmed it exceeds the 5% `max_single_stock_pct` limit, but chose NOT to open a new DEF because CLAUDE.md's DEF-195 already describes the BITO observation and has the fix routed to `post-31.9-reconnect-recovery-and-rejectionstage`. Added a design note (per-signal vs aggregate-symbol gate as the concrete lever) for the eventual session — this is context enrichment, not a duplicate DEF.
- **VG-6 component-alias:** grep for literal `IntradayCandleStore` returns 0 matches. Rather than flag this as INCONCLUSIVE, inspected log surface and found the component registers under its health-monitor alias `candle_store`. Confirmed via both boot health line and mid-session bar-serving line. The question ("does the component initialize?") is answered CONFIRMED via a different signature than Apr 22's expected grep.

## 8 — Scope Verification

Scope boundaries enumerated in the kickoff §Constraints:
- ✅ Did NOT modify any argus/ code.
- ✅ Did NOT modify any config/ file.
- ✅ Did NOT modify any tests/ file.
- ✅ Did NOT re-run any pattern sweep, revalidation, backtest, or paper session.
- ✅ Did NOT execute SQL that writes to any DB (all queries read-only).
- ✅ Did NOT edit the Apr 22 debrief triage document.
- ✅ Did NOT open DEFs speculatively — DEF-206 has concrete SQL evidence (33,743 + 4,457 rows across 3 databases).
- ✅ Did NOT close any DEF that wasn't already closed.
- ✅ Did NOT modify the `workflow/` submodule.
- ✅ Worked directly on `main` (no branch).

## 9 — Regression Checks

| Check | How Verified | Result |
|-------|--------------|--------|
| Verification report has 9 entries | Counted `## VG-N` headers in report | ✅ 9 |
| Each entry has method + evidence + conclusion + follow-up | Per-section read | ✅ all complete |
| No `argus/` code modified | `git diff argus/` | ✅ empty |
| No config modified | `git diff config/` | ✅ empty |
| No test modified | `git diff tests/` | ✅ empty |
| Summary aggregate matches per-entry conclusions | Manual sum: 6 confirmed / 1 refuted / 1 inconclusive / 1 cross-ref = 9 | ✅ matches |
| New DEF appears in CLAUDE.md AND RUNNING-REGISTER | `grep DEF-206 CLAUDE.md docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | ✅ both present |
| No DEF closed that wasn't already resolved | N/A (0 closed) | ✅ |
| Full pytest suite still passes post-session | `pytest --ignore=tests/test_main.py -n auto -q` | (see §10) |

## 10 — Test Baseline (Sanity Check Only)

Read-only session should produce zero pytest delta. Post-IMPROMPTU-11
baseline per RUNNING-REGISTER is **5,068 pass + 12 DEF-205 fail**. This
session's pytest run is a "nothing drifted" sanity check only; neither
baseline should move.

**Pytest result (actual):** `5068 passed, 12 failed, 29 warnings in 51.28s`
(exit 0 from the xdist runner; failures are the known DEF-205 date-decay
family in `tests/intelligence/test_filter_accuracy.py` × 11 +
`tests/api/test_counterfactual_api.py::TestCounterfactualAccuracyEndpoint::test_returns_200_with_data` × 1).

**Delta = 0** against the post-IMPROMPTU-11 baseline (5,068 pass + 12
DEF-205 fail). Read-only discipline confirmed: no code/config/test change
moved the pytest baseline in either direction.

## 11 — CI Verification

CI URL for the session commit will be attached once the commit lands and
GitHub Actions completes. Per Universal RULE-050, CI-green verification
is required for every session commit.

## 12 — Self-Assessment

**CLEAN**.

Rationale:
- All 9 gaps have concrete SQL/grep/code-inspection evidence captured in
  the verification report. No "CONFIRMED without evidence" entries.
- INCONCLUSIVE gap (VG-2) has a clear automatic resolution path (next
  non-empty boot exercises it) and a standing regression test — no
  unresolvable debt carried forward.
- REFUTED gap (VG-3) has concrete root-cause SQL (4,457 catalyst_events
  rows 100% blank-symbol across Apr 20–24, 33,743 quality_history rows
  exact constant 50.0) and DEF-206 is scoped with fix lever
  (ingestion-side symbol-attachment audit), cross-references, and priority.
- Zero code/config/test modified (`git diff argus/ tests/ config/` empty).
- Apr 22 debrief triage document preserved.
- Scope matches kickoff Definition of Done item-by-item.

Flags to reviewer: VG-2 reports INCONCLUSIVE because the violation branch
cannot be exercised by an Apr 24-style clean boot — this is the correct
verdict (the code is correct by inspection, but the behavior-under-violation
is only exercised by a non-empty-boot session). The regression test file
`tests/test_startup_position_invariant.py` exists with 5 tests; 3 of them
cover the violation branch: `test_single_short_fails_invariant`,
`test_mixed_longs_and_shorts_returns_just_the_shorts`, and
`test_position_without_side_attr_fails_closed`. The combination of
inspection + these unit tests satisfies the verification intent without a
behavioral log observation.

## 13 — Post-review fix

Tier 2 verdict: **CLEAR** with 1 LOW finding (non-blocking). Review
artifact at `docs/sprints/sprint-31.9/IMPROMPTU-09-review.md`.

- **LOW finding:** VG-2 follow-up cited `test_violation_disables_flatten`
  — that name does not exist. Actual violation-branch tests are
  `test_single_short_fails_invariant`, `test_mixed_longs_and_shorts_returns_just_the_shorts`,
  `test_position_without_side_attr_fails_closed` (3 of 5 in
  `tests/test_startup_position_invariant.py`). Substantive claim
  (regression test exists + exercises violation branch) correct; only the
  cited test name was wrong.
- **Fix:** updated the cited test names in VG-2 follow-up in both
  the verification report (§VG-2) and this close-out (§5 Items Deferred
  + §12 self-assessment). Post-review polish only; no substantive claim
  change.

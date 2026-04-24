# IMPROMPTU-11 Close-Out — A2/C12 Cascade Mechanism Diagnostic (DEF-204)

> Sprint 31.9, Stage 9C (Track B, safe-during-trading). **Read-only diagnostic.**
> Author: Claude Code (Opus 4.7, 1M context). Date: 2026-04-24.
> Diagnostic report: [docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md](IMPROMPTU-11-mechanism-diagnostic.md)
> Kickoff: [docs/sprints/sprint-31.9/IMPROMPTU-11-cascade-mechanism-diagnostic.md](IMPROMPTU-11-cascade-mechanism-diagnostic.md)

## Summary

DEF-204 mechanism IDENTIFIED to high-confidence. Apr 24's 44-symbol /
14,249-share gradual-drip cascade is a **multi-mechanism failure cluster**
with a single architectural root cause: ARGUS's exit-side accounting is
side-blind. Primary fill-side cause (~98% of blast radius) is bracket
children placed via `parentId` only with no explicit `ocaGroup`, combined
with redundant standalone SELL orders from trail/escalation paths that
share no OCA group with bracket children. Detection blindness across
three surfaces (reconcile orphan-loop one-direction-only; reconcile call
site strips side info; DEF-158 retry path side-blind) allows the drift to
accumulate silently for 6 hours per session. Fix scope routed to
`post-31.9-reconciliation-drift` named-horizon sprint, ~3 sessions.
DEF-204 remains OPEN — fix deferred per kickoff scope (adversarial review
+ non-safe-during-trading constraint apply). Zero code changes this
session (`git diff argus/ tests/ config/` empty).

## 1. Hypothesis Coverage

Kickoff §R1 required minimum 6 hypotheses; the diagnostic evaluates **8**
(the 6 required + 2 emergent: H7 redundant-standalone-SELL + H8
reconcile-call-site-strips-side).

| # | Hypothesis | Verdict | Evidence anchor |
|---|---|---|---|
| H1 | Partial-position bracket-leg accounting drift (no `ocaGroup` on bracket children + race-window cancels) | 🟢 LIKELY (DOMINANT) | Mass-balance: 2,225 broker fills − 899 entries − 679 ARGUS-recognized exits = ~647 unaccounted SELL fills; 17 of 44 EOD-shorts have ZERO trail/escalation activity → bracket-OCA-race alone produced their shorts |
| H2 | Silent reconciliation re-harmonization (orphan loop one-direction-only) | 🟢 LIKELY (DETECTION BLINDNESS) | `order_manager.py:3038-3039` skip-iteration guard processes only ARGUS-orphan direction; broker-orphan / phantom-short ignored after WARNING summary |
| H3 | Stop fill + late order cancel race | 🟢 LIKELY (subsumed under H1) | 67 stop cancels + 73 t1_target cancels + 99 t2 cancels — async cancel propagation creates race windows |
| H4 | Bracket target leg firing after position closed | 🟡 PARTIAL (visible-tip-of-iceberg) | 6 visible T1-orphan WARNINGs; many more racy fills go to silent `logger.debug("Fill for unknown order_id ...")` at `order_manager.py:592` |
| H5 | Manual flatten path with stale qty (DEF-158 side-blind) | 🟡 PARTIAL (1 instance today; full radius once H1 lands) | Only IMSR fired DEF-158 mismatch today; that single fire doubled IMSR's pre-existing -100 to -200 |
| H6 | Scanner re-entry on symbols with open shorts | 🟡 PARTIAL (consequence, not cause) | IMSR bracket 3 BUY 149 against pre-existing -200 short demonstrates the dynamic; symptom of H2 blindness, not separate mechanism |
| H7 | Redundant standalone SELL orders from trail+escalation, no OCA between them | 🟢 LIKELY (compounds H1 on 27 of 44 symbols) | 154 trail flattens + 347 escalation-stop updates = 501 standalone exit orders, none linked to bracket OCA; IMSR forensic trace at 12:11–12:15 |
| H8 | Periodic reconciliation strips side info before comparator runs | 🟢 LIKELY (architectural blindness compounding H2) | `argus/main.py:1520-1531` builds `dict[str, float]` of `abs(qty)` — `Position.shares` from `IBKRBroker` is `abs(int(ib_pos.position))` |

**Kickoff §R3 signature analysis (5 patterns):** Full table in §"What
signature analysis tells us" of the diagnostic report. **H1 + H2 +
compounded by H7 and H8 is the only combination that explains all five
patterns simultaneously.** H5 doubles where pre-existing short lives but
cannot create the initial short; H6 is downstream consequence.

## 2. IMSR Forensic Anchor (kickoff §R4)

Detailed lifecycle trace through three brackets at the diagnostic's
"Forensic anchor: IMSR" section. Mass-balance accounting from the trace:

| Source | Direction | Quantity | Cumulative broker position |
|---|---:|---:|---:|
| Bracket 1 parent fill (10:38:09) | BUY | 76 | +76 |
| Bracket 1 trail flatten (10:42:40) | SELL | 76 | 0 |
| Bracket 2 parent fill (11:51:07) | BUY | 200 | +200 |
| Bracket 2 escalation stop fire (12:15:04) | SELL | 200 | 0 |
| Bracket 2 trail flatten partial (12:15:04 → 12:17:09 timeout) | SELL | 100 (partial of 200) | -100 |
| **Bracket 2 DEF-158 retry SELL** (12:17:09) | **SELL** | **100** | **-200** |
| Bracket 3 parent fill (12:59:07) | BUY | 149 | -51 |
| Bracket 3 stop fire (13:03:13) | SELL | 149 | -200 |

The DEF-158 retry SELL at 12:17:09 is the critical doubling step:
`broker_qty = abs(int(getattr(bp, "shares", 0)))` at
[order_manager.py:2388](argus/execution/order_manager.py#L2388) reads
the broker -100 short as `100 long`, then `sell_qty = broker_qty` issues
SELL 100 → broker becomes -200.

Bracket 3's BUY 149 + Stop 149 nets to zero in ARGUS's view, but layers
onto the phantom -200, leaving IMSR at -200 short at EOD.

## 3. Top-3 Mechanism Ranking + Fix Direction (kickoff §R5)

| Rank | Mechanism cluster | Consistency score | Blast radius today |
|---|---|---|---|
| #1 | H1 + H7 (bracket children no `ocaGroup` + standalone trail/escalation SELLs not in OCA) | 5/5 patterns | ~14,000 of 14,249 EOD-short shares |
| #2 | H2 + H8 (reconcile only acts on ARGUS-orphan direction + call site strips side) | 4/5 patterns | Allows 6-hour silent accumulation |
| #3 | H5 (DEF-158 retry path side-blind, doubles pre-existing shorts) | 1/5 patterns | Doubles from -100 to -200 (IMSR; full radius once H1 lands) |

**Fix direction (single sprint, ~3 sessions, all three together):**

1. Set explicit `ocaGroup` + `ocaType=1` on bracket children at
   [argus/execution/ibkr_broker.py:736-769](argus/execution/ibkr_broker.py#L736-L769);
   thread an `oca_group_id` field through `ManagedPosition` so trail
   flatten / escalation stop / `_resubmit_stop_with_retry` SELLs all
   share the bracket's OCA group.
2. Change reconciliation contract from `dict[str, float]` to
   `dict[str, tuple[OrderSide, int]]`; extend orphan-direction guard at
   [argus/execution/order_manager.py:3038-3039](argus/execution/order_manager.py#L3038-L3039)
   to handle broker-orphan direction with CRITICAL alert + entry gate.
3. Apply IMPROMPTU-04's 3-branch side-check pattern to
   [`_check_flatten_pending_timeouts`](argus/execution/order_manager.py#L2384-L2406):
   read `pos.side` alongside `pos.shares`; if `side == OrderSide.SELL`
   abort retry with CRITICAL + alert.

## 4. P26 Retrospective Candidate (kickoff §R6)

Captured verbatim in the diagnostic's "Retrospective Candidate" section:

> **P26 candidate (for next campaign's RETRO-FOLD):** When validating a fix
> against a recurring symptom, verify against the mechanism signature (e.g.,
> 2.00× doubling ratio), not the symptom aggregate (e.g., "shorts at EOD").
> Yesterday's 2.00× math was the correct discriminator; without it, today's
> 44-symbol cascade would have been misattributed to DEF-199 regression and
> IMPROMPTU-04 would have been incorrectly reopened. Origin: Apr 24 debrief
> validation moment. Generalization: any fix-validation session should
> explicitly identify the mechanism signature before running the validation.

SPRINT-CLOSE will route to next campaign's RETRO-FOLD.

## 5. Files Modified

| File | Change | Type |
|---|---|---|
| [docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md](IMPROMPTU-11-mechanism-diagnostic.md) | NEW (the main deliverable) | doc |
| [CLAUDE.md](../../../CLAUDE.md) | DEF-204 entry refined with mechanism findings; **DEF-204 stays OPEN** | doc |
| [docs/sprints/sprint-31.9/RUNNING-REGISTER.md](RUNNING-REGISTER.md) | IMPROMPTU-11 row + Stage status updated | doc |
| [docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md](CAMPAIGN-COMPLETENESS-TRACKER.md) | Stage 9C IMPROMPTU-11 row → CLEAR + new "Reconciliation Drift" post-31.9 row | doc |
| [docs/sprints/sprint-31.9/IMPROMPTU-11-closeout.md](IMPROMPTU-11-closeout.md) | NEW (this file) | doc |
| [docs/sprints/sprint-31.9/IMPROMPTU-11-review.md](IMPROMPTU-11-review.md) | NEW (Tier 2 review) | doc |

**Production code untouched:** `git diff argus/ tests/ config/` is empty.
**Workflow untouched:** RULE-018 respected.

## 6. Regression Checklist Verification

| Check | Result |
|-------|--------|
| Minimum 6 hypotheses evaluated | ✅ 8 evaluated (H1–H8) |
| Each hypothesis has concrete evidence | ✅ All 8 anchor on grep output or direct code-path quote |
| IMSR case study present | ✅ Dedicated section with full lifecycle table + mass-balance |
| Top-3 ranking present | ✅ §"Top-3 ranking" + per-mechanism "what fix would look like" |
| P26 retrospective candidate present | ✅ §"Retrospective Candidate" with Origin + generalization |
| No `argus/` code modified | ✅ `git diff argus/` empty |
| No `config/` modified | ✅ `git diff config/` empty |
| No `tests/` modified | ✅ `git diff tests/` empty |
| Full pytest suite still passes | 🟡 5,068 passed / 12 pre-existing failures unrelated to this session — see §7 below |

## 7. Pre-existing Test Failures (NOT caused by this session)

The post-session pytest run reported 12 failures that **also fail on
clean main without IMPROMPTU-11's changes** (verified via `git stash` →
re-run → `git stash pop` cycle). Failures cluster in:

- `tests/intelligence/test_filter_accuracy.py` — 11 failures
- `tests/api/test_counterfactual_api.py::TestCounterfactualAccuracyEndpoint::test_returns_200_with_data` — 1 failure

**Root cause:** hardcoded `opened_at: str = "2026-03-25T10:00:00"` at
[tests/intelligence/test_filter_accuracy.py:36](tests/intelligence/test_filter_accuracy.py#L36)
falls outside the rolling 30-day default window of
`compute_filter_accuracy()`. Today is 2026-04-24, so 2026-03-25 is
exactly at the window boundary; bound-check semantics exclude the seed.
This is a **date-decay sibling of DEF-167** (Vitest hardcoded-date
family — that DEF was scoped to Vitest only and these pytest sites were
not converted).

**Disposition:** Out of scope for this read-only diagnostic session. The
operator and Tier 2 reviewer should treat the failures as pre-existing
on main and route them to a date-decay test-hygiene follow-on (open a
new DEF or attach to DEF-163's family). **No regression introduced by
IMPROMPTU-11.**

Test-count baseline trajectory: 5,080 → 5,080 (no test changes; same
total, but the 12 failures are now visible as failures rather than
passes — the date-decay tipping point was crossed between IMPROMPTU-10
seal and IMPROMPTU-11 start). pytest sanity invariant met: net delta = 0.

## 8. DEF-204 Disposition

**OPEN. Mechanism IDENTIFIED. Fix DEFERRED per kickoff scope.**

CLAUDE.md DEF-204 entry refined with the mechanism findings (file paths,
mass-balance evidence, IMSR forensic, fix scope) but the row stays in the
DEF table and is **not** strikethrough. Fix routed to
`post-31.9-reconciliation-drift` (new named-horizon sprint added to
CAMPAIGN-COMPLETENESS-TRACKER post-31.9 list).

The kickoff explicitly states: *"This session does NOT fix DEF-204. The
fix is scoped to the new post-31.9-reconciliation-drift named horizon
sprint where it can receive adversarial review and the safe-during-trading
constraint doesn't apply."* Followed.

## 9. Self-Assessment

**CLEAN.**

Justification:

- Read-only discipline maintained: zero `argus/` / `tests/` / `config/`
  modifications (`git diff` confirms).
- 8 hypotheses evaluated (kickoff required 6). Each backed by concrete
  grep output or direct code-path quote.
- IMSR forensic anchor traced through three brackets with mass-balance
  table. The DEF-158-retry doubling step is identified as the critical
  failure mode for IMSR specifically.
- Top-3 ranking with per-mechanism fix direction. #1 explains 5/5
  required patterns from kickoff §R3.
- P26 retrospective candidate captured verbatim with Origin citation +
  generalization.
- DEF-204 remains OPEN — fix scope routed to
  `post-31.9-reconciliation-drift`, not closed prematurely.
- DEF-199 framing preserved: today's debrief proves DEF-199 is closed and
  IMPROMPTU-04 is working; nothing in this diagnostic re-opens DEF-199.
- 12 pre-existing test failures observed but NOT caused by this session
  (verified via `git stash` cycle). Documented in §7 with root-cause
  attribution + DEF-167 family note.
- Apr 22 / Apr 23 / Apr 24 debrief documents untouched.
- `workflow/` submodule untouched.
- ≤6 files modified (all docs).

Green CI URL: pending push of this commit. Will be cited in the
operator-handoff line below once the run completes.

## 10. Operator Handoff

1. Close-out: this file (`docs/sprints/sprint-31.9/IMPROMPTU-11-closeout.md`).
2. Review: pending @reviewer subagent invocation.
3. Diagnostic report: `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`.
4. **Top-3 mechanisms (ranked by consistency):**
   - **#1** H1 + H7 — bracket children placed without `ocaGroup` + standalone SELL orders from trail/escalation paths share no OCA group with bracket children → multi-leg fill races. ~98% of blast radius (≈14,000 of 14,249 EOD-short shares).
   - **#2** H2 + H8 — `reconcile_positions()` orphan loop one-direction-only + main.py call site strips side info before reconciliation runs → broker-side phantom shorts silently accumulate for 6 hours per session.
   - **#3** H5 — `_check_flatten_pending_timeouts` (DEF-158 retry path) reads `abs(qty)` and issues SELL even when broker is short → actively doubles pre-existing shorts (IMSR -100 → -200 today).
5. **Recommended fix direction for `post-31.9-reconciliation-drift`:** 3 sessions in one sprint:
   - Session 1: explicit `ocaGroup`+`ocaType=1` on bracket children + thread `oca_group_id` through ManagedPosition so trail/escalation/resubmit-stop SELLs share the bracket's OCA group.
   - Session 2: side-aware reconciliation contract — change `dict[str, float]` to `dict[str, tuple[OrderSide, int]]` + handle broker-orphan direction with CRITICAL alert + entry gate.
   - Session 3: side-aware DEF-158 retry path mirroring IMPROMPTU-04 EOD Pass 1/2 fix (3-branch BUY→flatten / SELL→log+skip / unknown→log+skip).

   All three must land before next paper session resumes — partial fixes leave residual amplifiers (#3 alone amplifies any latent short; #2 alone reports correctly but doesn't prevent further drift).

6. Green CI URL: *pending commit + push*.

One-line summary:

`IMPROMPTU-11 complete. Close-out: CLEAN. Review: pending. Top mechanism: H1+H7 (bracket children placed without ocaGroup + standalone trail/escalation SELLs not in OCA). Fix routed to post-31.9-reconciliation-drift. Commits: pending. Report: docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md.`

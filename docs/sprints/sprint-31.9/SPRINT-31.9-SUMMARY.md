# Sprint 31.9: Campaign-Close — Sprint Summary

**Campaign:** Sprint 31.9 (Health & Hardening — derived from audit-2026-04-21 + Apr 22 paper-session debrief)
**Dates:** 2026-04-22 (Apr 22 paper-session that surfaced DEF-199) – 2026-04-24 (TEST-HYGIENE-01 + SPRINT-CLOSE-A)
**Final HEAD:** `e095a39` on `main` (post-SPRINT-CLOSE-A commit; pending push + green CI URL)
**Final test state:** 5,080 pytest / 866 Vitest / CI green (URL cited in closeout)
**Sessions run:** 11 named + 3 paper-session debriefs = 14 total

## What Sprint 31.9 Achieved

The campaign-close phase opened on 2026-04-22 with the discovery, in that day's paper-trading
debrief, that 51 of 51 untracked broker positions had ended exactly 2.00× short at EOD —
34,239 shares of unintended short exposure produced by a mathematical doubling signature
that pinned the bug to `_flatten_unknown_position()` in `argus/execution/order_manager.py`.
IMPROMPTU-04 landed the A1 fix the next morning (commit `0623801`): a side-check filter at
the EOD Pass 1/Pass 2 entry points that flattens BUY positions normally and routes
SELL/unknown positions to ERROR-log + skip, paired with a startup invariant
(`check_startup_position_invariant()`) that gates `OrderManager.reconstruct_from_broker()`
on any non-BUY broker side. Three subsequent paper sessions (Apr 22 pre-fix evidence,
Apr 23 post-fix observation, Apr 24 stress test) confirmed the fix detected and refused
44 of 44 unexpected shorts on Apr 24 with zero doublings. The mathematical signature
flipped from 2.00× (DEF-199 days) to 1.00× (post-fix days) — the cleanest possible
fix-validation outcome.

The Apr 24 debrief then surfaced a separate finding that DEF-199's resolution had been
masking a different upstream cascade: 14,249 unexpected shorts had still accumulated
across 44 symbols by EOD, gradually rather than via the doubling signature. IMPROMPTU-11
(Apr 24, read-only) traced 8 hypotheses against 2,225 broker fills and identified
**bracket children placed via `parentId` only with no explicit `ocaGroup`** + redundant
standalone SELL orders from trail-flatten and escalation-stop paths as ~98% of the blast
radius (H1+H7), plus side-blind reconciliation in 3 surfaces (H2+H8) that allowed
6-hour silent accumulation, plus the DEF-158 retry path (H5) that further doubles
pre-existing shorts via `abs(qty)` reads. The fix scope is concrete, three sessions, and
all-three-must-land-together — routed to a new named-horizon sprint
`post-31.9-reconciliation-drift` where adversarial review is required at every session
boundary. Paper trading continues in safe-mitigation mode (operator runs
`scripts/ibkr_close_all_positions.py` daily) until that sprint lands.

## Strategic Significance

- **A1 short-flip cascade fixed and validated in production.** IMPROMPTU-04's fix
  detected + refused 44/44 unexpected shorts on Apr 24 with zero doublings; the
  mathematical signature flipped from 2.00× (DEF-199 days) to 1.00× (post-fix days),
  confirming the mechanism was correctly identified.
- **DEF-204 mechanism IDENTIFIED.** IMPROMPTU-11 traced 8 hypotheses against 2,225
  broker fills and identified bracket-children-without-OCA + side-blind reconciliation
  as the dominant mechanisms (~98% of blast radius). Fix scope is 3 sessions,
  all-three-must-land-together, routed to new `post-31.9-reconciliation-drift`
  named horizon.
- **Mechanism-signature-vs-symptom-aggregate principle established.** Without
  yesterday's 2.00× math (preserved across debrief docs), today's 44-symbol cascade
  would have been misattributed as a DEF-199 regression. Captured as P26 retrospective
  candidate for next campaign's RETRO-FOLD.
- **CI discipline restored.** TEST-HYGIENE-01 closed DEF-205 (12 pytest date-decay
  failures), restoring the 5,080 baseline and ending a 6-commit CI-red streak that was
  correctly diagnosed as cosmetic but had masked any potential real regression for
  ~24 hours.

## Campaign Test Delta

| Metric | Pre-Campaign | Post-Campaign | Delta |
|---|---|---|---|
| pytest (`--ignore=tests/test_main.py`) | 4,934 | 5,080 | +146 |
| Vitest | 846 | 866 | +20 |
| Total | 5,780 | 5,946 | +166 |

`tests/test_main.py` tracked separately: 23 pass → 39 pass + 5 skip post-IMPROMPTU-06
(unchanged by IMPROMPTU-07/08/10/11/09/TEST-HYGIENE-01).

The +146 pytest delta covers the entire Sprint 31.9 campaign (pre-FIX-00 → post-TEST-HYGIENE-01).
The campaign-close phase alone (pre-IMPROMPTU-04 5,039 → post-TEST-HYGIENE-01 5,080) contributed
+41 pytest. Per-session deltas appear in the Session Index below.

## DEF Register Delta

| Metric | Count | Detail |
|---|---|---|
| DEFs opened during campaign-close phase | 6 | DEF-201, DEF-202, DEF-203, DEF-204, DEF-205, DEF-206 |
| DEFs closed during campaign-close phase | 19 | grep-verified against CLAUDE.md (see list below) |
| DEFs deferred to named horizons | 4 | DEF-201/DEF-202 → component-ownership; DEF-204 → reconciliation-drift; DEF-195/196 → reconnect-recovery (already pre-deferred) |
| DEFs MONITOR-only | 1 | DEF-203 — next `argus/core/risk_manager.py` touch |
| DEFs opportunistic | 1 | DEF-206 — next catalyst-layer touch |

**Closed during campaign-close phase (IMPROMPTU-04 onward), exact grep against CLAUDE.md:**
DEF-048, 049, 164, 166, 168, 169, 176, 179, 180, 181, 185, 189, 191, 193, 197, 198,
199, 200, 205. (19 total.)

> Note: the SPRINT-CLOSE-A kickoff cited an expected list of 24 closures, but five
> of those (DEF-152, 153, 154, 158, 161) were closed by earlier campaign sessions
> (Sprints 31.75 / 31.8 / 31.85, pre-IMPROMPTU-04). The exact-grep verification done
> at this session start is authoritative.

## DEC Delta

**0 new DECs.** All design decisions followed established patterns (DEC-345 store
separation, DEC-032 config-gating, DEC-372 retry caps, IMPROMPTU-04 EOD branch pattern
applied across DEF-204 fix scope). DEC range allocation for Sprint 31.9: none reserved,
none consumed.

## Campaign Lessons (P1–P25 + P26/P27 candidates)

P1–P25 were folded into the `claude-workflow` metarepo via RETRO-FOLD on 2026-04-23.
See [`RETRO-FOLD-closeout.md`](RETRO-FOLD-closeout.md) and
[`CAMPAIGN-COMPLETENESS-TRACKER.md`](CAMPAIGN-COMPLETENESS-TRACKER.md) for the full
per-lesson disposition table. Metarepo commits: `63be1b6` (principal fold) +
`ac3747a` (Origin-footnote normalization) + `edf69a5` (RULE-042/045 footnote tightening).
Submodule pointer advanced via argus commits `aa952f9` → `204462e` → `ec7e795`.

Two new retrospective candidates emerged after RETRO-FOLD (sealed) and are queued for
the next campaign's RETRO-FOLD pickup:

- **P26 candidate:** *When validating a fix against a recurring symptom, verify against
  the mechanism signature (e.g., 2.00× doubling ratio), not the symptom aggregate
  (e.g., "shorts at EOD").* Origin: Apr 24 debrief discrimination of DEF-199 (closed)
  vs DEF-204 (new). Captured in
  [`IMPROMPTU-11-mechanism-diagnostic.md`](IMPROMPTU-11-mechanism-diagnostic.md)
  §Retrospective Candidate.
- **P27 candidate:** *When CI turns red for a known cosmetic reason, explicitly log
  that assumption at each subsequent commit rather than treating it as silent ambient
  noise. The test is: "if a genuine regression slipped in, would I still notice?"*
  Origin: Sprint 31.9's 6-commit CI-red streak (cosmetic-only, but masked any potential
  real regression for ~24 hours). To capture in next campaign's RETRO-FOLD scope.
- **P28 candidate:** *Session implementers should treat kickoff statistics as
  directional input requiring grep-verification, not ground truth. Closeouts
  should explicitly disclose any kickoff-vs-actual discrepancies with attribution
  rather than quietly conform to the kickoff's stated numbers.* Origin:
  SPRINT-CLOSE-A-closeout's correction of the kickoff's "24 closed DEFs" figure
  to the grep-verified 19 (5 of the 24 — DEF-152/153/154/158/161 — were closed
  by earlier campaign sessions before IMPROMPTU-04 anchored the campaign-close
  window). The implementer flagged the discrepancy in the closeout via RULE-038
  grep-verify rather than silently propagating the wrong number to
  SPRINT-31.9-SUMMARY.md. Generalization: this extends RULE-038's grep-verify
  discipline into a closeout-level disclosure practice — distinct from RULE-038
  itself because it covers what to do when a discrepancy is found (the closeout
  reporting protocol), not just the verification step. To capture in next
  campaign's RETRO-FOLD scope.

- **P29 candidate:** *Architecturally-sealed documents (e.g.,
  `process-evolution.md` FROZEN markers, sealed sprint folders, ARCHIVE-banner
  files) require defensive verification at session start, not just trust in the
  kickoff's instructions to avoid them.* Origin: SPRINT-CLOSE-B's pre-flight
  check #5 explicitly grep-verified the FROZEN marker still existed before
  allowing the session to proceed. If a future operator removes the freeze
  marker, the kickoff's avoidance instruction would silently bypass an important
  architectural decision. Generalization: any session that operates near
  sealed/frozen documents should encode the seal as a verifiable assertion at
  session start. The verification protects against the seal being silently
  removed elsewhere. To capture in next campaign's RETRO-FOLD scope.

## Session Index

| # | Session | Verdict | Key DEF transitions | Test delta |
|---|---|---|---|---|
| 1 | IMPROMPTU-04 (A1 + C1 + startup invariant) | CLEAR (CONCERNS→resolved via IMPROMPTU-CI) | closed DEF-199 | +13 pytest |
| 2 | IMPROMPTU-CI (observatory_ws teardown race) | CLEAR | closed DEF-200, DEF-193; opened DEF-201 | +2 pytest |
| 3 | IMPROMPTU-05 (deps & infra) | CLEAR | closed DEF-179, 180, 181 | 0 |
| 4 | IMPROMPTU-06 (test-debt) | CLEAR (CONCERNS→resolved in-session) | closed DEF-048, 049, 166, 176, 185; DEF-192 PARTIAL extended | +3 (+16 in `test_main.py`) |
| 5 | IMPROMPTU-07 (doc-hygiene + UI) | CLEAR | closed DEF-164, 169, 189, 191, 198 + Apr 21 F-05/F-06/F-08 | +16 pytest / +7 Vitest |
| 6 | IMPROMPTU-08 (architecture.md catalog) | CLEAR (MINOR_DEVIATIONS) | closed DEF-168 | +4 pytest |
| 7 | IMPROMPTU-10 (evaluation.db retention) | CLEAR (CLEAN) | closed DEF-197 | +3 pytest |
| 8 | RETRO-FOLD (P1–P25 → metarepo) | CLEAR (+ LOW findings folded) | none (docs-only, cross-repo) | 0 |
| 9 | IMPROMPTU-11 (A2/C12 mechanism diagnostic) | CLEAR (CLEAN) | DEF-204 OPEN with mechanism IDENTIFIED; opened DEF-205 | 0 (read-only) |
| 10 | IMPROMPTU-09 (verification sweep, 9 gaps) | CLEAR | DEF-206 opened (REFUTED VG-3 → catalyst symbol-attachment defect) | 0 (read-only) |
| 11 | TEST-HYGIENE-01 (pytest date-decay) | CLEAR (CLEAN) | closed DEF-205 | +12 pytest |

3 paper-session debriefs (Apr 22, Apr 23, Apr 24) drove the campaign's discovery work
but produced only triage docs, no commits to argus runtime.

## Handoff to Post-31.9 Sprints

Four named-horizon sprints are now seeded with DISCOVERY.md stubs:

1. **post-31.9-component-ownership** (UPDATED, pre-existed at 138 lines from the
   2026-04-22 DEF-172/173/175 impromptu): DEF-175, DEF-182, DEF-201, DEF-202, DEF-014
   HealthMonitor; DEF-197 reference removed (resolved by IMPROMPTU-10); DEF-193
   acknowledged as RESOLVED. ~3 sessions estimated. See
   [`docs/sprints/post-31.9-component-ownership/DISCOVERY.md`](../post-31.9-component-ownership/DISCOVERY.md).
2. **post-31.9-reconnect-recovery-and-rejectionstage** (NEW): DEF-177, DEF-184, DEF-194,
   DEF-195, DEF-196, DEF-014 IBKR emitter TODOs, Apr 21 F-04. ~3 sessions estimated.
   Adversarial review for the reconnect-recovery sessions; standard Tier 2 for the
   RejectionStage enum work. See
   [`docs/sprints/post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md`](../post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md).
3. **post-31.9-alpaca-retirement** (NEW): DEF-178, DEF-183, DEF-014 Alpaca emitter TODO.
   ~1–2 sessions estimated; mechanical refactor. See
   [`docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md`](../post-31.9-alpaca-retirement/DISCOVERY.md).
4. **post-31.9-reconciliation-drift** (NEW, post-Apr-24 debrief): DEF-204 CRITICAL safety,
   mechanism IDENTIFIED via IMPROMPTU-11. ~3 sessions estimated, all-three-must-land-together.
   Adversarial review REQUIRED for all 3 sessions. See
   [`docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`](../post-31.9-reconciliation-drift/DISCOVERY.md).

Build-track queue position post-Sprint-31.9: per [`docs/roadmap.md`](../../roadmap.md),
Sprint 31B (Research Console / Variant Factory) is the next planned sprint. Operator
decides ordering of the 4 post-31.9 horizons against 31B based on safety priority —
DEF-204 (CRITICAL safety) likely takes precedence over Sprint 31B.

## Closing Statement

Sprint 31.9 closed on 2026-04-24. The campaign delivered a fully-validated A1
short-flip fix, a complete mechanism diagnosis for the underlying upstream cascade
(DEF-204), 25 P-lessons folded into the workflow metarepo, and 4 well-scoped post-31.9
sprints ready for planning. Paper trading continues in safe-mitigation mode (operator
runs `scripts/ibkr_close_all_positions.py` daily) until DEF-204's fix lands in the
post-31.9-reconciliation-drift sprint.

---

**Maintainer note:** This document is the canonical Sprint 31.9 summary. The
campaign-close plan ([`CAMPAIGN-CLOSE-PLAN.md`](CAMPAIGN-CLOSE-PLAN.md)), running
register ([`RUNNING-REGISTER.md`](RUNNING-REGISTER.md)), and completeness tracker
([`CAMPAIGN-COMPLETENESS-TRACKER.md`](CAMPAIGN-COMPLETENESS-TRACKER.md)) are
preserved in this directory as historical artifacts but should not be updated
further. Core project doc reconciliation (`docs/architecture.md`,
`docs/decision-log.md`, `docs/sprint-history.md`, etc.) is handled by SPRINT-CLOSE-B.

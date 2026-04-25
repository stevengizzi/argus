# Sprint 31.9 SPRINT-CLOSE-A — Campaign Artifacts + 4 DISCOVERY Stubs

> Drafted post-TEST-HYGIENE-01. Paste into a fresh Claude Code session on `main`.
> This prompt is **standalone** — do not read other session prompts in this campaign.
> **Ceremonial close, part A** — campaign-internal artifacts only.
>
> **Sibling session:** SPRINT-CLOSE-B (`docs/sprints/sprint-31.9/SPRINT-CLOSE-B-core-doc-sync.md`)
> handles core project-doc sync (`docs/architecture.md`, `docs/decision-log.md`,
> `docs/dec-index.md`, `docs/roadmap.md`, `docs/sprint-campaign.md`, `docs/sprint-history.md`,
> `docs/project-knowledge.md`, `docs/project-bible.md`, `docs/risk-register.md`).
> SPRINT-CLOSE-A produces the campaign summary that SPRINT-CLOSE-B references; run A first.
>
> **Why split:** the original combined SPRINT-CLOSE was estimated at 3–4 hours, with
> compaction risk HIGH. Splitting at the campaign-internal vs. project-wide boundary
> lets each session run in ~90 min and keeps each scope auditable.

## Scope

Sprint 31.9 was a 14-session campaign-close (run April 22 onward) that:
- Validated IMPROMPTU-04's A1 fix in production via 3 paper-session debriefs (Apr 22, 23, 24)
- Identified DEF-204's mechanism (cascade + accounting drift) — fix routed to a new named horizon
- Folded 25 P-lessons into the `claude-workflow` metarepo via RETRO-FOLD
- Resolved 21 DEFs and opened 6 new ones (DEF-201 through DEF-206)
- Restored CI green via TEST-HYGIENE-01 (DEF-205 closure)

This session produces the campaign-internal closing artifacts:
1. `SPRINT-31.9-SUMMARY.md` — canonical sprint summary
2. SEAL banners on `RUNNING-REGISTER.md` + `CAMPAIGN-COMPLETENESS-TRACKER.md`
3. ARCHIVE banner on `CAMPAIGN-CLOSE-PLAN.md`
4. **4 post-31.9 DISCOVERY.md stubs** (one is an UPDATE to existing file)

Core project docs (`docs/architecture.md`, `docs/decision-log.md`, `docs/sprint-history.md`, etc.) are handled by SPRINT-CLOSE-B.

**Files touched:**

NEW:
- `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- `docs/sprints/post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md`
- `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md`
- `docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`
- `docs/sprints/sprint-31.9/SPRINT-CLOSE-A-closeout.md`
- `docs/sprints/sprint-31.9/SPRINT-CLOSE-A-review.md`

MODIFIED (banners + content):
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — SEAL banner
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — SEAL banner
- `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` — ARCHIVE banner only (no content edits)
- `docs/sprints/post-31.9-component-ownership/DISCOVERY.md` — UPDATE (file pre-exists at 138 lines from Apr 22 impromptu): add DEF-182, DEF-193, DEF-202, DEF-014 HealthMonitor; remove DEF-197 reference (resolved by IMPROMPTU-10); preserve all other existing content

**Safety tag:** `safe-during-trading` — documentation only.

**Theme:** Campaign-internal seal. Produce the canonical summary that SPRINT-CLOSE-B will reference. Do NOT touch any `docs/*.md` outside `docs/sprints/sprint-31.9/`, `docs/sprints/post-31.9-*/`. Project-wide doc sync is SPRINT-CLOSE-B's scope.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
```

### 2. Campaign readiness check — all sessions CLEAR

The following 11 sessions must all be CLEAR before SPRINT-CLOSE-A runs:

```bash
ls docs/sprints/sprint-31.9/IMPROMPTU-*-closeout.md
ls docs/sprints/sprint-31.9/IMPROMPTU-*-review.md
ls docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md
ls docs/sprints/sprint-31.9/RETRO-FOLD-review.md
ls docs/sprints/sprint-31.9/TEST-HYGIENE-01-closeout.md
ls docs/sprints/sprint-31.9/TEST-HYGIENE-01-review.md
```

Required closeouts (in chronological order of landing):
- IMPROMPTU-04 (DEF-199 A1 fix + C1 log downgrade + startup invariant) — CLEAR
- IMPROMPTU-CI (DEF-200 + DEF-193 observatory_ws teardown race) — CLEAR
- IMPROMPTU-05 (deps & infra: DEF-179/180/181) — CLEAR
- IMPROMPTU-06 (test-debt: DEF-048/049/166/176/185 + DEF-192 PARTIAL) — CLEAR (CONCERNS→resolved in-session)
- IMPROMPTU-07 (doc-hygiene + UI: DEF-164/169/189/191/198 + Apr 21 F-05/F-06/F-08) — CLEAR
- IMPROMPTU-08 (architecture.md API catalog: DEF-168) — CLEAR (MINOR_DEVIATIONS, CONCERNS→resolved in-session)
- IMPROMPTU-10 (evaluation.db retention: DEF-197) — CLEAR (CLEAN)
- RETRO-FOLD (P1–P25 → claude-workflow metarepo, cross-repo session) — CLEAR (+ LOW-findings folded)
- IMPROMPTU-11 (A2/C12 cascade mechanism diagnostic: DEF-204 mechanism IDENTIFIED) — CLEAR (CLEAN)
- IMPROMPTU-09 (Apr 22/23/24 verification sweep, 9 gaps: DEF-206 opened) — CLEAR
- TEST-HYGIENE-01 (pytest date-decay fix: DEF-205) — CLEAR (CLEAN)

```bash
# Quick CLEAR verdict scan:
grep -l "Verdict.*CLEAR\|verdict.*CLEAR" docs/sprints/sprint-31.9/*-review.md
# Expected: 11 matches (one per session above)
```

If any review is CONCERNS or ESCALATE without a documented "resolved in-session" annotation, SPRINT-CLOSE-A does not run.

### 3. CI readiness

```bash
git log --oneline origin/main -1
# Expected: 3dd459c (Workflow-submodule pointer refresh) or later
# Capture SHA + CI URL from GitHub Actions
```

If CI is red (other than known DEF-205 failures, which TEST-HYGIENE-01 resolved), STOP. CI must be green for the most recent commit.

### 4. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Expected: 5,080 passed, 0 failed (post-TEST-HYGIENE-01)

cd ui && npx vitest run --reporter=dot 2>&1 | tail -5 && cd ..
# Expected: 866 passed
```

### 5. Branch & workspace

```bash
git checkout main && git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading

Read in this order:

1. **`docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md`** — master plan; use as skeleton for SPRINT-31.9-SUMMARY.md
2. **`docs/sprints/sprint-31.9/RUNNING-REGISTER.md`** — final session-history table + open-DEF ledger; pulls together what each session did
3. **`docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md`** — stage-by-stage completeness matrix + per-P# dispositions for the 25 P-lessons (RETRO-FOLD's output)
4. **All 11 session close-outs** (IMPROMPTU-04, CI, 05, 06, 07, 08, 10, 11, 09, RETRO-FOLD, TEST-HYGIENE-01) — each gives one row of the SPRINT-31.9-SUMMARY's session index
5. **3 paper-session debriefs:**
   - `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md`
   - `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md`
   - `docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md`
6. **`docs/sprints/post-31.9-component-ownership/DISCOVERY.md`** — pre-existing 138-line discovery doc from Apr 22 impromptu; SPRINT-CLOSE-A UPDATES this, does not replace
7. **`CLAUDE.md`** — current "Active sprint" pointer (mentions Sprint 31.9 ~implicitly via DEF entries; pointer updates happen in SPRINT-CLOSE-B)

**Do not read** the following — they are SPRINT-CLOSE-B's scope:
- `docs/architecture.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/roadmap.md`, `docs/sprint-campaign.md`, `docs/sprint-history.md`, `docs/project-knowledge.md`, `docs/project-bible.md`, `docs/risk-register.md`

## Final Campaign Statistics — Inputs

Collect these for SPRINT-31.9-SUMMARY.md. Verify each by independent grep/count, do not trust any single source:

- **Date range:** Apr 22, 2026 (campaign-close plan drafted) – {today's date}
- **Total sessions:** 11 named (IMPROMPTU-04/CI/05/06/07/08/10/11/09 + RETRO-FOLD + TEST-HYGIENE-01) + 3 paper-session debriefs (Apr 22/23/24) = **14 total**
- **Total commits on `main`:** count via `git log --oneline 0623801..HEAD | wc -l` where `0623801` is IMPROMPTU-04's first code commit
- **Pytest delta:** {pre-campaign} → 5,080 (post-TEST-HYGIENE-01). Pre-campaign baseline = pre-IMPROMPTU-04, which can be verified from CAMPAIGN-CLOSE-PLAN's "baseline" line. Expected: ~4,934 → 5,080 = +146.
- **Vitest delta:** {pre-campaign} → 866. Expected: 846 → 866 = +20 (per IMPROMPTU-07 closeout's Vitest row).
- **DECs added:** **0** (verified: campaign sessions logged "no new DECs" in their close-outs; established-pattern campaign).
- **DEFs opened:** 6 (DEF-201, DEF-202, DEF-203, DEF-204, DEF-205, DEF-206). Verified by grep against CLAUDE.md.
- **DEFs closed:** count via grep against CLAUDE.md for `~~DEF-` strikethrough that landed during the campaign window. Expected list: DEF-048, 049, 152, 153, 154, 158, 161, 164, 166, 168, 169, 176, 179, 180, 181, 185, 189, 191, 193, 197, 198, 199, 200, 205. (24 total — verify by exact grep.)
- **DEFs deferred to named horizons:** 4 (DEF-201 → component-ownership; DEF-202 → component-ownership; DEF-203 → MONITOR-only / next risk_manager.py touch; DEF-204 → reconciliation-drift). Plus DEF-206 → opportunistic catalyst-layer touch.
- **Workflow metarepo commits (from RETRO-FOLD):** 3 (`63be1b6` principal fold + `ac3747a` Origin-footnote normalization + `edf69a5` RULE-042/045 footnote tightening).
- **Submodule pointer advances on argus:** 3 (`aa952f9` → `ac3747a` via `204462e` → `edf69a5` via `ec7e795`).

## Objective

Produce 6 artifact files (1 summary + 4 DISCOVERY stubs + 1 closeout). Apply 3 banners (SEAL × 2 + ARCHIVE × 1). The SUMMARY is the canonical entry point future operators read first.

## Requirements

### Requirement 1: SPRINT-31.9-SUMMARY.md

Create `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` with this structure:

~~~markdown
# Sprint 31.9: Campaign-Close — Sprint Summary

**Campaign:** Sprint 31.9 (Health & Hardening — derived from audit-2026-04-21 + Apr 22 paper-session debrief)
**Dates:** {start date} – {end date}
**Final HEAD:** `{SHA}` on `origin/main`
**Final test state:** 5,080 pytest / 866 Vitest / CI green ({CI URL})
**Sessions run:** 11 named + 3 paper-session debriefs = 14 total

## What Sprint 31.9 Achieved

{2-paragraph narrative: (1) IMPROMPTU-04's A1 fix and the live-data validation arc that proved it through 3 paper sessions; (2) the discovery via Apr 24 debrief that A1 was masking a different upstream bug (DEF-204), and the IMPROMPTU-11 mechanism diagnosis that scoped the post-31.9-reconciliation-drift fix.}

## Strategic Significance

- **A1 short-flip cascade fixed and validated in production.** IMPROMPTU-04's fix detected + refused 44/44 unexpected shorts on Apr 24 with zero doublings; the mathematical signature flipped from 2.00× (DEF-199 days) to 1.00× (post-fix days), confirming the mechanism was correctly identified.
- **DEF-204 mechanism IDENTIFIED.** IMPROMPTU-11 traced 8 hypotheses against 2,225 broker fills and identified bracket-children-without-OCA + side-blind reconciliation as the dominant mechanisms (~98% of blast radius). Fix scope is 3 sessions, all-three-must-land-together, routed to new `post-31.9-reconciliation-drift` named horizon.
- **Mechanism-signature-vs-symptom-aggregate principle established.** Without yesterday's 2.00× math (preserved across debrief docs), today's 44-symbol cascade would have been misattributed as a DEF-199 regression. Captured as P26 retrospective candidate for next campaign's RETRO-FOLD.
- **CI discipline restored.** TEST-HYGIENE-01 closed DEF-205 (12 pytest date-decay failures), restoring 5,080 baseline and ending a 6-commit CI-red streak that was correctly diagnosed as cosmetic.

## Campaign Test Delta

| Metric | Pre-Campaign | Post-Campaign | Delta |
|---|---|---|---|
| pytest | 4,934 | 5,080 | +146 |
| Vitest | 846 | 866 | +20 |
| Total | 5,780 | 5,946 | +166 |

## DEF Register Delta

| Metric | Count |
|---|---|
| DEFs opened during campaign | 6 (DEF-201–206) |
| DEFs closed during campaign | 24 (verify by exact grep) |
| DEFs deferred to named horizons | 4 (component-ownership: 201, 202; reconciliation-drift: 204; reconnect-recovery-and-rejectionstage: 195, 196 — already pre-deferred) |
| DEFs MONITOR-only | 1 (DEF-203 — next risk_manager.py touch) |
| DEFs opportunistic | 1 (DEF-206 — next catalyst-layer touch) |

## DEC Delta

**0 new DECs.** All design decisions followed established patterns (DEC-345 store separation, DEC-300 config-gating, DEC-372 retry caps, IMPROMPTU-04 EOD pattern application). DEC range allocation for Sprint 31.9: none reserved, none consumed.

## Campaign Lessons (P1–P25 + P26/P27 candidates)

P1–P25 were folded into the `claude-workflow` metarepo via RETRO-FOLD on Apr 23. See `docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md` and `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` for the full per-lesson disposition table.

Two new retrospective candidates emerged after RETRO-FOLD (sealed) and are queued for next campaign's RETRO-FOLD pickup:

- **P26 candidate:** *When validating a fix against a recurring symptom, verify against the mechanism signature (e.g., 2.00× doubling ratio), not the symptom aggregate (e.g., "shorts at EOD").* Origin: Apr 24 debrief discrimination of DEF-199 (closed) vs DEF-204 (new). Captured in `IMPROMPTU-11-mechanism-diagnostic.md` §Retrospective Candidate.
- **P27 candidate:** *When CI turns red for a known cosmetic reason, explicitly log that assumption at each subsequent commit rather than treating it as silent ambient noise. The test is: "if a genuine regression slipped in, would I still notice?"* Origin: Sprint 31.9's 6-commit CI-red streak (cosmetic-only, but masked any potential real regression for ~24 hours). To capture in next campaign's RETRO-FOLD scope.

## Session Index

| # | Session | Verdict | Key DEF transitions | Test delta |
|---|---|---|---|---|
| 1 | IMPROMPTU-04 (A1 + C1 + startup invariant) | CLEAR (CONCERNS→resolved via IMPROMPTU-CI) | closed DEF-199 | {N} |
| 2 | IMPROMPTU-CI (observatory_ws teardown race) | CLEAR | closed DEF-200, DEF-193 | {N} |
| 3 | IMPROMPTU-05 (deps & infra) | CLEAR | closed DEF-179, 180, 181 | {N} |
| 4 | IMPROMPTU-06 (test-debt) | CLEAR (CONCERNS→resolved in-session) | closed DEF-048, 049, 166, 176, 185; DEF-192 PARTIAL extended | {N} |
| 5 | IMPROMPTU-07 (doc-hygiene + UI) | CLEAR | closed DEF-164, 169, 189, 191, 198 | {N} |
| 6 | IMPROMPTU-08 (architecture.md catalog) | CLEAR (MINOR_DEVIATIONS) | closed DEF-168 | +4 |
| 7 | IMPROMPTU-10 (evaluation.db retention) | CLEAR (CLEAN) | closed DEF-197 | +3 |
| 8 | RETRO-FOLD (P1–P25 → metarepo) | CLEAR (+ LOW findings folded) | none | 0 |
| 9 | IMPROMPTU-11 (A2/C12 mechanism diagnostic) | CLEAR (CLEAN) | DEF-204 OPEN with mechanism | 0 |
| 10 | IMPROMPTU-09 (verification sweep, 9 gaps) | CLEAR | DEF-206 opened | 0 |
| 11 | TEST-HYGIENE-01 (pytest date-decay) | CLEAR (CLEAN) | closed DEF-205 | +12 |

3 paper-session debriefs (Apr 22, 23, 24) drove the campaign's discovery work but produced only triage docs, no commits to argus runtime.

## Handoff to Post-31.9 Sprints

Four named-horizon sprints are now seeded with DISCOVERY.md stubs:

1. **post-31.9-component-ownership** (UPDATED, pre-existed at 138 lines): DEF-175, DEF-182, DEF-193, DEF-201, DEF-202, DEF-014 HealthMonitor. ~3 sessions estimated. See `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`.
2. **post-31.9-reconnect-recovery-and-rejectionstage** (NEW): DEF-177, DEF-184, DEF-194, DEF-195, DEF-196. ~3 sessions estimated. See `docs/sprints/post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md`.
3. **post-31.9-alpaca-retirement** (NEW): DEF-178, DEF-183, DEF-014 Alpaca emitter TODO. ~1–2 sessions estimated. See `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md`.
4. **post-31.9-reconciliation-drift** (NEW, post-Apr-24 debrief): DEF-204 critical-safety, mechanism IDENTIFIED via IMPROMPTU-11. ~3 sessions estimated, all-three-must-land-together. See `docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`.

Build-track queue position post-Sprint-31.9: per `docs/roadmap.md`, Sprint 31B is the next planned sprint. Operator decides ordering of the 4 post-31.9 horizons against 31B based on safety priority — DEF-204 (CRITICAL safety) likely takes precedence over Sprint 31B.

## Closing Statement

Sprint 31.9 closed on {date}. The campaign delivered a fully-validated A1 short-flip fix, a complete mechanism diagnosis for the underlying upstream cascade (DEF-204), 25 P-lessons folded into the workflow metarepo, and 4 well-scoped post-31.9 sprints ready for planning. Paper trading continues in safe-mitigation mode (operator runs `ibkr_close_all_positions.py` daily) until DEF-204's fix lands in the post-31.9-reconciliation-drift sprint.

---

**Maintainer note:** This document is the canonical Sprint 31.9 summary. The campaign-close plan (`CAMPAIGN-CLOSE-PLAN.md`) and running register (`RUNNING-REGISTER.md`) are preserved in this directory as historical artifacts but should not be updated further.
~~~

### Requirement 2: Seal RUNNING-REGISTER.md

Add at the very top of the file (before the `# Sprint 31.9 Running Register` heading), inside an HTML comment block visible at the top of any rendered view:

```
<!-- ⛔ SEALED: Sprint 31.9 closed on {date}. This document is now read-only history.
     Canonical summary: docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
     Do not update further. The next campaign's running register lives in its own directory. -->
```

Then update the `Last updated` banner ONE FINAL TIME to indicate the seal:

```
> **Last updated:** {date} — SPRINT-CLOSE-A SEAL. Sprint 31.9 closed. Final HEAD `{SHA}`. 
> Pytest 5,080 / Vitest 866 / CI green. 24 DEFs closed, 6 opened (4 deferred to named horizons, 1 MONITOR, 1 opportunistic). 
> 11 named sessions + 3 paper-session debriefs across {N} calendar days. See SPRINT-31.9-SUMMARY.md.
```

Verify every row in the Stage table reads `✅ COMPLETE` or `✅ CLEAR` — no PENDING, no PARTIAL.

### Requirement 3: Seal CAMPAIGN-COMPLETENESS-TRACKER.md

Add the same SEAL HTML comment at the very top:

```
<!-- ⛔ SEALED: Sprint 31.9 closed on {date}. All stages CLEAR. 
     Canonical summary: docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md -->
```

Confirm every Stage row in the Stage 9 sections (9A, 9B, 9C) shows `✅ CLEAR` and every per-P# disposition row shows `✅ landed`. No AMBER, no `⏸ PENDING`.

### Requirement 4: Archive CAMPAIGN-CLOSE-PLAN.md

Add ARCHIVE banner at very top:

```
<!-- 📦 ARCHIVED: This plan document was the working master during Sprint 31.9 campaign-close. 
     It has been superseded by SPRINT-31.9-SUMMARY.md. Preserved here for historical reference. 
     Do not update further. -->
```

No content changes. Banner only.

### Requirement 5: 4 DISCOVERY.md files (1 update + 3 new)

#### 5a. UPDATE `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`

The file pre-exists at 138 lines from the Apr 22 DEF-172/173 impromptu. **Preserve all existing content.** Make the following surgical additions:

- **At the top of the "DEF Cluster" section (or equivalent — find existing DEF-175 mention and use the same anchoring style):** add DEF-182 (weekly reconciliation stub), DEF-193 (Observatory WS disconnect detection — Note: status is RESOLVED via IMPROMPTU-CI; remove if already strikethrough elsewhere), DEF-201 (cross-loop aiosqlite fixture race — pre-31.9 IMPROMPTU-CI follow-on), DEF-202 (post-shutdown hang — subsumes Apr 22 §C7 + Apr 23 §C9), DEF-014 HealthMonitor subscription
- **Remove the DEF-197 reference** wherever it appears — DEF-197 was resolved by IMPROMPTU-10, not deferred to component-ownership
- **Append a new section** "## Post-Sprint-31.9 Updates" with: "(2026-04-{date}) IMPROMPTU-CI resolved DEF-193 and DEF-200; IMPROMPTU-10 resolved DEF-197 (originally queued here per Apr 23 plan); DEF-201, DEF-202 added per Apr 23/24 debriefs; DEF-014 HealthMonitor explicit-subscription work split out from the Apr 22 §C7 framing into DEF-202."

If the existing DISCOVERY.md uses different anchoring (e.g., a "DEF List" table), follow its structure.

#### 5b. NEW `docs/sprints/post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md`

Use the standard DISCOVERY.md template (see Template Block below).

- **Sprint Identity:** `post-31.9-reconnect-recovery-and-rejectionstage` (note the full name — the original SPRINT-CLOSE kickoff used a shorter incorrect name; the campaign-plan canonical name is the long form)
- **Theme:** Robust recovery posture after IBKR/Databento session-reset events, plus completion of `RejectionStage` enum work. Informed by Apr 22/23/24 cascade post-mortems.
- **DEF Cluster:**
  - DEF-177: `RejectionStage.MARGIN_CIRCUIT` enum addition
  - DEF-184: `RejectionStage` / `TrackingReason` split
  - DEF-194: IBKR stale position cache
  - DEF-195: `max_concurrent_positions` divergence + BITO 8% concentration (cross-references IMPROMPTU-09 VG-7 evidence)
  - DEF-196: 32+ DEC-372 stop-retry-exhaustion cascade events (Apr 22 + Apr 23 confirmed two independent triggers — material design input from Apr 23 debrief annotation)
  - DEF-014 IBKR emitter TODOs (`ibkr_broker.py:453,531`)
  - Apr 21 debrief F-04 (flatten-retry against non-existent positions)
- **Estimated session count:** ~3 sessions (per CAMPAIGN-CLOSE-PLAN)
- **Adversarial review:** Likely required for the reconnect-recovery sessions; standard Tier 2 sufficient for the RejectionStage enum work

#### 5c. NEW `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md`

- **Sprint Identity:** `post-31.9-alpaca-retirement`
- **Theme:** Fully retire AlpacaBroker incubator path. Per DEC-086, alpaca-py was retained at `[project.dependencies]` scope as an incubator-only path; this sprint moves it to `[project.optional-dependencies.incubator]` extras (DEF-178) and removes Alpaca-specific code/test paths from the main argus runtime (DEF-183).
- **DEF Cluster:**
  - DEF-178: `alpaca-py` to `[incubator]` extras
  - DEF-183: full Alpaca code+test retirement
  - DEF-014 Alpaca emitter TODO (`alpaca_data_service.py:593`)
- **Estimated session count:** ~1–2 sessions (smaller scope; mechanical refactor)
- **Adversarial review:** Standard Tier 2

#### 5d. NEW `docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`

This is the CRITICAL safety horizon. Seed thoroughly — it's the most important post-31.9 sprint.

- **Sprint Identity:** `post-31.9-reconciliation-drift`
- **Theme:** Fix DEF-204 — the upstream cascade mechanism that IMPROMPTU-04's A1 fix was masking. Mechanism IDENTIFIED in IMPROMPTU-11: bracket children placed via `parentId` only with no explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths (~98% of blast radius); plus side-blind reconciliation in 3 surfaces allowing 6-hour silent accumulation. **All-three-must-land-together** — partial fixes leave residual amplifiers.
- **DEF Cluster:** DEF-204 (CRITICAL safety, mechanism IDENTIFIED, fix scope concrete)
- **Estimated session count:** 3 sessions (concrete plan from IMPROMPTU-11 §Top-3 ranking):
  - Session 1: Set explicit `ocaGroup` + `ocaType=1` on bracket children at `argus/execution/ibkr_broker.py:736-769`. Thread `oca_group_id` through `ManagedPosition` so trail flatten, escalation stop, and `_resubmit_stop_with_retry` SELLs all share the bracket's OCA group.
  - Session 2: Change reconciliation contract from `dict[str, float]` to `dict[str, tuple[OrderSide, int]]`. Extend orphan-direction guard at `argus/execution/order_manager.py:3038-3039` to handle broker-orphan direction with CRITICAL alert + entry gate.
  - Session 3: Apply IMPROMPTU-04's 3-branch side-check pattern to `_check_flatten_pending_timeouts()` (DEF-158 retry path) at `argus/execution/order_manager.py:2384-2406`. Read `pos.side` alongside `pos.shares`; if `side == OrderSide.SELL` abort retry with CRITICAL + alert.
- **Adversarial review:** **REQUIRED** for all 3 sessions — order-manager and broker-side changes are non-trivial and safety-critical. Recommend full Tier 3 architectural review at session boundaries.
- **Operational mitigation in effect until fix lands:** Operator runs `scripts/ibkr_close_all_positions.py` at session close daily. ~14K shares/day of unintended short exposure; A1 fix correctly refuses amplification + escalates.
- **IMSR forensic anchor:** From IMPROMPTU-11 lifecycle trace — bracket 2 escalation-stop fill 200 + trail-flatten partial 100 racing → broker -100; DEF-158 retry SELL 100 (reads broker `abs(100)` as long quantity) → broker -200. The fix in Session 3 directly addresses this exact failure path.

Cross-references in this discovery: DEF-158 (dup-SELL prevention — the detection mechanism currently working correctly that DEF-204 work must NOT regress); DEF-196 (stop-retry cascade — different family, post-31.9-reconnect-recovery-and-rejectionstage scope).

#### Template Block (for 5b, 5c, 5d)

~~~markdown
# Sprint `{sprint-id}` Discovery Notes

> Discovery-grade seed doc. Written at Sprint 31.9 SPRINT-CLOSE-A on {date}.
> Enough context to start a planning conversation without re-reading the full Sprint 31.9 history.
> **Not a plan; not a spec.** Planning conversation produces the actual sprint package.

## Sprint Identity

- **Sprint ID:** `{sprint-id}`
- **Predecessor:** Sprint 31.9 (Health & Hardening campaign-close)
- **Build-track position:** {per-roadmap-position; for safety-critical sprints, may take precedence over Sprint 31B}
- **Discovery date:** {YYYY-MM-DD}

## Theme

{1–2 paragraph description of what this sprint accomplishes. Pull from the DEF cluster.}

## Deferred-Items Scope

DEFs explicitly queued for this sprint:

| DEF # | Title | Source | Notes |
|---|---|---|---|
| DEF-{N} | {title} | {source debrief / discovery / sprint} | {1-line note on scope/priority} |

Total: {N} DEFs in scope.

## Known Dependencies / Constraints

- {dependency 1}
- {dependency 2}

## Open Questions (for planning conversation)

- {question 1}
- {question 2}

## Context Pointers

- Sprint 31.9 summary: `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- Apr 22/23/24 debriefs (if applicable): `docs/sprints/sprint-31.9/debrief-2026-04-{22,23,24}-triage.md`
- Related DECs: `docs/decision-log.md` DEC-{N}, DEC-{M}
- Build-track queue: `docs/roadmap.md`

## Not-in-Scope

- {explicit exclusions}

## Pre-Planning Checklist

- [ ] All DEFs in scope still OPEN (verify CLAUDE.md)
- [ ] No dependencies blocked
- [ ] Build-track queue supports starting this sprint
- [ ] Sprint 31.9 SPRINT-CLOSE-B core-doc sync has landed (so docs reflect current state)
~~~

## Constraints

- **Do NOT modify** any argus runtime code or tests or configs. Doc-only.
- **Do NOT touch** any core project doc (`docs/architecture.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/roadmap.md`, `docs/sprint-campaign.md`, `docs/sprint-history.md`, `docs/project-knowledge.md`, `docs/project-bible.md`, `docs/risk-register.md`). These are SPRINT-CLOSE-B's scope.
- **Do NOT touch** any pre-existing close-out or review file. They are sealed historical records.
- **Do NOT touch** any debrief triage doc.
- **Do NOT touch** the `workflow/` submodule.
- **Do NOT plan** the 4 successor sprints. DISCOVERY stubs are seeds, not plans. Actual planning is a future conversation.
- **Do NOT open** new DEFs unless something genuinely new is discovered (rare at this stage; if it happens, document carefully).
- **Do NOT update** CLAUDE.md "Active sprint" pointer — that's SPRINT-CLOSE-B's first action.

## Test Targets

- pytest full suite unchanged at 5,080 (no code changes)
- Vitest unchanged at 866
- CI remains green

## Definition of Done

- [ ] `SPRINT-31.9-SUMMARY.md` created with all sections populated using verified statistics
- [ ] `RUNNING-REGISTER.md` SEAL banner applied + final `Last updated` written
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` SEAL banner applied
- [ ] `CAMPAIGN-CLOSE-PLAN.md` ARCHIVE banner applied (banner only, no content edits)
- [ ] `post-31.9-component-ownership/DISCOVERY.md` UPDATED with surgical additions (preserves all existing content)
- [ ] `post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md` NEW (with full canonical name)
- [ ] `post-31.9-alpaca-retirement/DISCOVERY.md` NEW
- [ ] `post-31.9-reconciliation-drift/DISCOVERY.md` NEW (concrete fix scope; CRITICAL safety annotated)
- [ ] Close-out at `docs/sprints/sprint-31.9/SPRINT-CLOSE-A-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/SPRINT-CLOSE-A-review.md`
- [ ] Final green CI URL cited

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| SPRINT-31.9-SUMMARY.md has all 8 sections | TOC check |
| Final HEAD SHA matches actual HEAD | `git rev-parse HEAD` cross-ref |
| Test counts in summary match actual baseline | pytest + Vitest run |
| 24 DEFs marked closed in summary match grep result | Cross-validate exact list |
| 4 DISCOVERY.md files exist (3 new + 1 updated) | `ls docs/sprints/post-31.9-*/DISCOVERY.md` shows 4 files |
| Existing component-ownership DISCOVERY.md content preserved | `wc -l` should be ~138 + N additions, never lower |
| post-31.9-reconnect-recovery-and-rejectionstage uses long name | Path matches CAMPAIGN-CLOSE-PLAN canonical name |
| RUNNING-REGISTER + TRACKER + CLOSE-PLAN have banners | grep for `<!-- ⛔ SEALED` and `<!-- 📦 ARCHIVED` |
| No core project doc modified | `git diff docs/architecture.md docs/decision-log.md docs/dec-index.md docs/roadmap.md docs/sprint-campaign.md docs/sprint-history.md docs/project-knowledge.md docs/project-bible.md docs/risk-register.md` empty |
| No `argus/` or `tests/` or `config/` modified | `git diff argus/ tests/ config/` empty |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/SPRINT-CLOSE-A-closeout.md`

Include:
1. **Final campaign statistics** (verified counts, not estimates)
2. **Files added** (6 new)
3. **Files modified** (4 — 3 banners + 1 surgical update)
4. **DEF count verification** (exact list from grep against CLAUDE.md)
5. **Banner application confirmation** (3 banners visible in their files)
6. **DISCOVERY stub completeness** (each has DEF cluster, theme, open questions populated, not placeholder)
7. **Final green CI URL**
8. **Closing statement** — one-paragraph reflection on the campaign
9. **Handoff note to SPRINT-CLOSE-B** — explicit list of what SPRINT-CLOSE-B still has to do (the 9 core project docs)

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Provide:
1. This kickoff
2. Close-out path
3. Diff range
4. Files that should NOT have been modified:
   - Any `argus/` code file
   - Any `config/` file
   - Any `tests/` file
   - Any pre-existing session close-out or review file
   - Any debrief triage doc
   - Any `workflow/` submodule file
   - **Any core project doc** (`docs/architecture.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/roadmap.md`, `docs/sprint-campaign.md`, `docs/sprint-history.md`, `docs/project-knowledge.md`, `docs/project-bible.md`, `docs/risk-register.md`) — these are SPRINT-CLOSE-B's scope

## Session-Specific Review Focus (for @reviewer)

1. **Verify SUMMARY statistics are evidence-backed.** Each number in SPRINT-31.9-SUMMARY.md must be reproducible from a grep, count, or test run. Spot-check the 24 DEFs-closed list (grep `~~DEF-` in CLAUDE.md against the campaign window).
2. **Verify SEAL banners visible.** Both RUNNING-REGISTER and CAMPAIGN-COMPLETENESS-TRACKER have HTML comment banners at the very top.
3. **Verify post-31.9-component-ownership preservation.** The pre-existing 138 lines must be intact; only additions allowed.
4. **Verify post-31.9-reconnect-recovery-and-rejectionstage uses the LONG name** matching CAMPAIGN-CLOSE-PLAN.
5. **Verify DEF clusters in each DISCOVERY.md are accurate.** Each DEF cited must exist as OPEN in CLAUDE.md (or RESOLVED with appropriate annotation).
6. **Verify no core project doc was modified.** This is the cleanest scope-boundary check between A and B.
7. **Verify no DEF closed during this session.** SPRINT-CLOSE-A is documentation-only; DEF state transitions should not happen here.
8. **Verify green CI URL** for the SPRINT-CLOSE-A commit.

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- Any core project doc modified
- SPRINT-31.9-SUMMARY.md uses placeholder text or has unverified statistics
- post-31.9-component-ownership DISCOVERY.md content reduced (only additions allowed)
- post-31.9-reconnect-recovery-and-rejectionstage uses short name `reconnect-recovery` instead of long name
- Any DISCOVERY.md is placeholder-only (no real DEF cluster)
- Any argus/tests/config/workflow file modified
- Full pytest broken
- DEF state transition occurred during this session

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Campaign statistics** (final pytest, Vitest, commits, DEFs closed, sessions)
4. **SPRINT-31.9-SUMMARY.md path** — operator reads this to confirm the canonical artifact
5. **4 DISCOVERY.md paths** — verify each with `ls`
6. **SPRINT-CLOSE-B kickoff path:** `docs/sprints/sprint-31.9/SPRINT-CLOSE-B-core-doc-sync.md` — operator runs this next
7. Final green CI URL
8. One-line summary: `Sprint 31.9 SPRINT-CLOSE-A complete. Campaign artifacts sealed. SPRINT-31.9-SUMMARY.md is canonical. 4 post-31.9 DISCOVERY stubs ready. Next: SPRINT-CLOSE-B (core-doc sync). CI: {URL}.`

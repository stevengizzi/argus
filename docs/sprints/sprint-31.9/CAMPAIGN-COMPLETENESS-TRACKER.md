# Sprint 31.9 + Post-31.9 Campaign — Completeness Tracker

<!-- last-updated: 2026-04-22 (Stage 6 complete, DEF-163 re-opened) -->
<!-- canonical-source: true — this is the single master tracker; hydrate new conversations from here -->

## Purpose

This document tracks EVERY outstanding item across Sprint 31.9 Health &
Hardening and the planned post-31.9 Component Ownership Consolidation sprint.
The definition of "campaign complete" is that every line in every table below
is either RESOLVED, PLANNED-WITH-SESSION-ASSIGNED, or EXPLICITLY-DEFERRED with
a named future sprint.

Zero orphans, zero "we'll get to it eventually" items.

When the entire tracker shows RESOLVED for every row, the campaign is complete
and this document can be archived to `docs/sprints/archive/`.

## Stage progress

| Stage | Sessions | Status | Date |
|---|---|---|---|
| Stage 1 | FIX-00, FIX-15, FIX-17, FIX-20, FIX-01, FIX-11 + sweep | ✅ CLEAR | Pre-campaign-sealing |
| Stage 2 | FIX-02, FIX-03, FIX-12, FIX-19, FIX-21 | ✅ CLEAR | Pre-campaign-sealing |
| Impromptu (2→3) | DEF-172, DEF-173, DEF-175 (opened) | ✅ CLEAR | Pre-campaign-sealing |
| Stage 3 Wave 1 | FIX-14, FIX-16 | ✅ CLEAR | 2026-04-21 |
| Stage 3 Wave 2 | FIX-04 | ✅ CLEAR (Rule-4, gold-standard proof) | 2026-04-21 |
| Stage 4 Wave 1 | FIX-10, FIX-18 | ✅ CLEAR | 2026-04-22 |
| Stage 4 Wave 2 | FIX-05 | ✅ CLEAR | 2026-04-22 |
| **Stage 4** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 5 Wave 1 | FIX-06 (data) | ✅ CLEAR | 2026-04-22 |
| Stage 5 Wave 2 | FIX-07 (intelligence/catalyst/quality) | ✅ CLEAR | 2026-04-22 |
| **Stage 5** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 6 | FIX-08 (experiments + learning loop, solo) | ✅ CLEAR | 2026-04-22 |
| **Stage 6** | **(complete)** | **✅ COMPLETE** | **2026-04-22** |
| Stage 7 | FIX-09 (docs/infra, solo) | ⏸ PENDING | TBD |
| Stage 8 | FIX-13 (test hygiene, solo) + IMPROMPTU-01 (scope TBD) | ⏸ PENDING | TBD |
| Stage 9A/B | IMPROMPTU-02 (scope TBD) | ⏸ PENDING | TBD |
| **Sprint 31.9** | | ⏸ IN PROGRESS | |
| Post-31.9 | Component Ownership Consolidation (DEF-175) | ⏸ PLANNED | After 31.9 closes |
| **Campaign** | | ⏸ IN PROGRESS | |

## CI infrastructure status

First fully passing CI at commit `793d4fd` (2026-04-22).
- pytest: ≈ 5,035 post-FIX-08 (CI `-m "not integration"`; conservative estimate accounting for DEF-150 flake variance — up from 4,977 at `793d4fd`)
- Vitest: 859 passed / 115 files
- Workflow: `.github/workflows/ci.yml`, Python 3.11.15, Node 20 (deprecation warning active — see DEF-181)
- Known flakes monitored in CI: DEF-150, DEF-163 (re-opened post-FIX-08), DEF-167, DEF-171
- CI-green milestone means zero-tolerance on flakes is enforceable going forward: any red CI run is a real bug until proven otherwise

**Post-Stage-6 expected counts:** CI pytest ≈ 5,035, Vitest 859.

## Sessions remaining (Sprint 31.9)

| Session | Scope (approximate finding count) | Solo? | Spec file |
|---|---|---|---|
| FIX-09 | docs / infra / backtest-engine (TBD) | Yes | `docs/audits/audit-2026-04-21/phase-3-prompts/FIX-09-docs-infra-backtest.md` |
| FIX-13 | test hygiene (DEF-150 + DEF-163 + DEF-167 + DEF-171) | Yes | `docs/audits/audit-2026-04-21/phase-3-prompts/FIX-13-test-hygiene.md` |
| IMPROMPTU-01 | scope TBD (verify from sprint-campaign.md) | TBD | TBD |
| IMPROMPTU-02 | scope TBD (verify from sprint-campaign.md) | TBD | TBD |

## Open DEF items — every known DEF with resolution assignment

### Will resolve within Sprint 31.9

| DEF | Title | Owner Session |
|---|---|---|
| DEF-150 | Time-of-day arithmetic flake (minute 0-1 window, 3.3%/hr) | FIX-13 |
| DEF-163 | Timezone-boundary bug in `test_get_todays_pnl_excludes_unrecoverable` (re-opened post-FIX-08; SQL-side `date()` UTC/ET mismatch) | FIX-13 |
| DEF-167 | Vitest hardcoded dates decay | FIX-13 (folded from original post-FIX-11 plan) |
| DEF-171 | ULID xdist race | FIX-13 (folded post-CI) |
| DEF-177 | `RejectionStage.MARGIN_CIRCUIT` addition | FIX-06 or cross-domain session |

### Will resolve in dedicated post-31.9 sprint

| DEF | Title | Owner |
|---|---|---|
| DEF-175 | Component ownership consolidation (lifespan phase duplication) | Post-31.9 sprint (2-3 sessions) |
| DEF-180 | Python lockfile via uv | Dedicated single-session sprint, post-31.9 |
| DEF-184 | RejectionStage → RejectionStage + TrackingReason split (coordinates with DEF-177) | Dedicated cross-domain session, post-31.9 |

### Opportunistic — no dedicated session, will fold into next touching session

| DEF | Title | Trigger |
|---|---|---|
| DEF-168 | `architecture.md` API catalog drift | If FIX-09 naturally touches API surfaces; otherwise scheduled post-campaign |
| DEF-174 | Tauri wrapper deprecated | When desktop-packaging decision is made |
| DEF-176 | `auto_cleanup_orphans` kwarg removal | Next Order Manager touch |
| DEF-178 | `alpaca-py` → `[incubator]` extras | Next dependency session |
| DEF-179 | `python-jose` → `PyJWT` migration | Next auth session |
| DEF-181 | Node 20 action deprecation (deadline 2026-06-02) | Before June 2, 2026; bump checkout/setup-python/setup-node |
| DEF-182 | Weekly Monday reconciliation stub (FIX-05 spawn) | Next ops/reconciliation session |
| DEF-183 | Full Alpaca code+test retirement (pairs with DEF-178) | Next execution-layer cleanup sprint |
| DEF-185 | Analytics-layer assert isinstance anti-pattern (5 sites, DEF-106 follow-on) | Next analytics-layer cleanup sprint |

### Monitor only — no action pending

| DEF | Title | Rationale |
|---|---|---|
| DEF-064 | Warm-up failure rate on mid-session boot | Unscheduled; observed but not triggering action |
| DEF-135 | Visual verification Shadow Trades/Experiments | Blocked on live-data accumulation (non-campaign) |
| DEF-169 | `--dev` mode retired | No action needed; informational |

### Already resolved during campaign (for completeness)

Closed by campaign sessions (grouped by closing session):

- FIX-21: DEF-097, DEF-162 (historical cache cron pair)
- IMPROMPTU-172-173-175: DEF-172 (RESOLVED-VERIFIED), DEF-173
- FIX-18: DEF-034, DEF-048, DEF-049, DEF-074, DEF-082, DEF-093, DEF-109, DEF-142
- FIX-05: **DEF-091, DEF-092, DEF-104, DEF-170** (DEF-163 was initially claimed but re-opened post-FIX-08 — SQL-side fix remains)
- FIX-06: DEF-032 (re-verified), DEF-037, DEF-165, DEF-014 (PARTIAL — emitter side), DEF-161 pending-action closed
- FIX-07: DEF-096, DEF-106
- FIX-08: DEF-107 (deleted raiseRec), DEF-123 (RESOLVED-VERIFIED)
- Campaign hotfixes (xdist + CI 4-bug): no DEFs closed directly; enabled CI-green milestone

## Audit finding completion

Total findings at audit-2026-04-21 start: (reference audit summary for base count).

- Stage 1-4 closed: see per-audit-doc "FIX-NN Resolution" sections in `docs/audits/audit-2026-04-21/*.md`
- Remaining findings by owner:
  - P1-A3 data: FIX-06
  - P1-A4 intelligence: FIX-07
  - P1-E backtest-engine: FIX-09
  - P1-F frontend: FIX-08
  - P1-G1/G2 test coverage/quality (unclosed): FIX-13
  - P1-H1a docs/registry drift: FIX-09 (mostly); DEF-168 is a separate sub-item
  - P1-H4 DEF triage: closes as the above DEFs close

## Process & retrospective items

Campaign-wide lessons to fold into `workflow/` metarepo protocols before closing Sprint 31.9:

| # | Lesson | Trigger |
|---|---|---|
| P1 | Dep-related Tier 2 reviews should include fresh-venv install check | xdist + seaborn misses |
| P2 | Marker-adding sessions should `pytest -m "<marker>" --collect-only` validate | FIX-18 added markers but no tests used them initially |
| P3 | Grep-audit test-vs-production import drift (`jwt` vs `jose` class) | FIX-18 test import gap |
| P4 | Pre-commit `git diff --name-only --cached` scope check | c3bc758 chimera Pass 3 incident |
| P5 | Read-only orphan verification → report → halt → operator confirms → edit | Prompt 1 chore pre-edit verification caught 3 errors |
| P6 | Always verify handoff document correctness against actual source | FIX-04 DEF-152 root-cause correction |
| P7 | Small-sample sweep conclusions are directional only | Sweep Impromptu 2026-04-03/05 |
| P8 | Zero-tolerance on CI flakes requires catalog completeness | Any new flake must get DEF'd immediately |
| P9 | `getattr(pos, "qty", 0)` vs `pos.shares` silent-zero pattern worth grep-audit | FIX-04 root cause |
| P10 | Test-delta count must equal new-test count exactly (no offsetting gains/losses) | Campaign rule, reinforced FIX-05 |
| P11 | Sprint ops files (RUNNING-REGISTER.md) should be in Files Modified manifest | Tier 2 nit on FIX-05 |
| P12 | Spec file-path drift is a confirmed pattern, not a one-off | FIX-04/06/07 all encountered findings where spec cited wrong file or stale line numbers. FIX-07 had 3 CSV-garbled line drifts + Finding 17 in wrong file (`position_sizer.py` vs actual `quality_engine.py`) + Finding 21 in wrong file (`models/trading.py` vs actual `intelligence/learning/models.py`). Kickoffs should include a mandatory grep-verification step at session start. |
| P13 | Stage/Session tracker nicknames can diverge from actual spec filenames. Future stage barriers should grep the actual spec filename before drafting kickoffs that trust the tracker label. | Stage 6 was tracker-nicknamed "frontend, solo" but FIX-08's actual spec is `FIX-08-intelligence-experiments-learning` — a backend session; frontend work was entirely in FIX-12 Stage 2. |
| P14 | DEF strikethroughs should not be made until the regression test in question has been run across multiple time windows. DEF closures for time-sensitive or timezone-involved tests should require at least one regression run in the failing window OR an explicit argument why the window no longer exists. | DEF-163's FIX-05 strikethrough was premature because the Python-side fix didn't exercise the SQL-side comparator, and the test's failure mode is time-of-day-bounded (~4h daily window). |

These become inputs to the campaign-close retrospective. They should be folded
into the `workflow/` metarepo protocols in a separate commit BEFORE Sprint 31.9
seals. Recommended: add them to the retrospective section of the final Sprint
31.9 summary doc.

## Acceptance criteria for "campaign complete"

Sprint 31.9 is complete when:
- [ ] Every session in "Sessions remaining" table has landed with CLEAR or MINOR_DEVIATIONS verdict
- [ ] Every DEF in "Will resolve within Sprint 31.9" table is strikethrough in CLAUDE.md
- [ ] CI remains green (4,992+ pytest, 859 Vitest, zero flakes firing during session runs)
- [ ] Every audit-2026-04-21 finding has a "FIX-NN Resolution" annotation in its audit doc
- [ ] Retrospective items (P1-P11) folded into `workflow/` metarepo
- [ ] Final Sprint 31.9 summary doc written
- [ ] RUNNING-REGISTER.md marked SEALED

Post-31.9 campaign is complete when:
- [ ] Component Ownership Consolidation sprint complete
- [ ] DEF-175 strikethrough in CLAUDE.md
- [ ] All "Opportunistic" DEFs have either fired their trigger session or been explicitly deferred to a NAMED post-campaign horizon
- [ ] All "Monitor only" DEFs have been re-evaluated for promotion or explicit close
- [ ] This tracker itself is moved to `docs/sprints/archive/sprint-31.9-campaign-tracker.md`

## How to update this doc

On close of any session that closes DEFs or lands findings:
1. Move resolved DEFs from "Open" → "Already resolved during campaign"
2. Update Stage progress table with the session verdict
3. Check off acceptance-criteria items if applicable
4. Update "last-updated" comment at top
5. Include this file in the session's docs commit if any changes

If a new DEF is opened, add it to the appropriate section based on ownership plan.
If a new session is added or removed, update Stage progress + Sessions remaining.
If a retrospective item is identified, append to the P# table.

## How to hydrate a fresh Claude.ai conversation

Paste at new-conversation-start:
1. This file (`CAMPAIGN-COMPLETENESS-TRACKER.md`)
2. Current `RUNNING-REGISTER.md`
3. Most recent FIX-NN close-out + Tier 2 review artifacts (the immediate prior session)
4. Next session's spec file from `docs/audits/audit-2026-04-21/phase-3-prompts/`

Project knowledge files (persistent in the Claude.ai project):
- `bootstrap-index.md` (workflow metarepo pointer)
- `ARGUS — Project Knowledge` (architecture + current state)
- `My Day Trading Manifesto` (personal context)

Starter prompt should reference the campaign HEAD SHA and the target session.
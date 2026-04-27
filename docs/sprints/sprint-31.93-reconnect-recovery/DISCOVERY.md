# Sprint `post-31.9-reconnect-recovery-and-rejectionstage` Discovery Notes

> Discovery-grade seed doc. Written at Sprint 31.9 SPRINT-CLOSE-A on 2026-04-24.
> Enough context to start a planning conversation without re-reading the full
> Sprint 31.9 history.
> **Not a plan; not a spec.** Planning conversation produces the actual sprint
> package.

## Sprint Identity

- **Sprint ID:** `post-31.9-reconnect-recovery-and-rejectionstage`
- **Predecessor:** Sprint 31.9 (Health & Hardening campaign-close)
- **Build-track position:** post-31.9 named horizon. Order against Sprint 31B
  and the other 3 post-31.9 horizons is operator-decided based on safety
  priority. This sprint's items are MEDIUM priority — none are CRITICAL safety,
  but the reconnect-recovery work materially reduces operational risk during
  IBKR/Databento session-reset events that have been observed on every paper
  trading day Apr 22–24.
- **Discovery date:** 2026-04-24

## Theme

Robust recovery posture after IBKR/Databento session-reset events, plus
completion of the `RejectionStage` enum work that FIX-04/FIX-07 declined to
land for halt-rule scope reasons. Informed by Apr 22/23/24 cascade post-mortems
which established that:

- IBKR's `ib_async` position cache can drift from broker state across reconnect
  (DEF-194), and ARGUS's `_managed_positions` count diverges silently from
  broker-side position count (DEF-195) — together producing untracked positions
  that bypass concentration limits and the `max_concurrent_positions` gate.
- DEC-372 stop-retry-exhaustion cascades fire from at least two independent
  triggers: network-disconnect-invalidated order IDs (Apr 22) AND routine
  high-signal-velocity broker-side cancel races (Apr 23). The fix must address
  both triggers, not just the network-event path (DEF-196).
- The `RejectionStage` enum currently mixes true pipeline rejections with
  routing decisions (`SHADOW`, `BROKER_OVERFLOW`) — conceptually misclassified
  in `FilterAccuracy.by_stage` reporting (DEF-184); and is missing a
  `MARGIN_CIRCUIT` discriminator that conflates margin-circuit rejections with
  ordinary risk-manager rejections in the same surface (DEF-177).

The two themes (reconnect-recovery + RejectionStage refactor) are bundled
because both touch the execution / intelligence boundary at overlapping call
sites (`order_manager.py`, `counterfactual.py`, `routes/counterfactual.py`,
`SignalRejectedEvent` emission paths).

## Deferred-Items Scope

DEFs explicitly queued for this sprint:

| DEF # | Title | Source | Notes |
|---|---|---|---|
| DEF-177 | `RejectionStage.MARGIN_CIRCUIT` enum addition | CLAUDE.md (FIX-04 deferral, P1-D1-M03) | MEDIUM. Cross-domain edit (`counterfactual.py` enum + `order_manager.py:485` emitter); coordinate with DEF-184 in one session because both touch `RejectionStage`. |
| DEF-184 | `RejectionStage` → `RejectionStage` + `TrackingReason` split | CLAUDE.md (FIX-07 deferral, P1-D1-L14) | LOW. `SHADOW` + `BROKER_OVERFLOW` are routing decisions, not filter rejections. Coordinate with DEF-177. Needs a `counterfactual_positions` schema migration. |
| DEF-194 | IBKR `ib_async` stale position cache after reconnect | CLAUDE.md (Apr 22 debrief §C2) | MEDIUM. `await self._ib.reqPositionsAsync()` before EOD Pass 2 query, OR `positions_last_updated` staleness check, OR pair with DEF-195. |
| DEF-195 | `max_concurrent_positions` divergence + BITO 8% concentration bypass | CLAUDE.md (Apr 22 §C3 + IMPROMPTU-09 VG-7 cross-reference) | MEDIUM/HIGH for live. Periodic reconciliation comparing `_managed_positions.count` vs `broker.get_positions().count`; concentration check must count broker-visible positions. |
| DEF-196 | 32+ DEC-372 stop-retry-exhaustion cascade events (two independent triggers — network + high-signal-velocity) | CLAUDE.md (Apr 22 §C4, materially extended by Apr 23 debrief §C4) | MEDIUM. Three composing fixes per CLAUDE.md DEF-196 entry: (1) reconnect-driven `reqOpenOrders()` rebuild; (2) longer first-retry delay post-reconnect; (3) **most important** — query broker position qty before MARKET emergency flatten and skip if 0 (defends both triggers). |
| DEF-014 IBKR emitter TODOs | `argus/execution/ibkr_broker.py:453,531` | CLAUDE.md (FIX-06 partial) | LOW. SystemAlertEvent emission for IBKR-side retry-exhaustion paths. Pairs with this sprint's broker-side reconnect work. |
| Apr 21 debrief F-04 | Flatten-retry loop against non-existent positions | Apr 21 debrief F-04 | LOW. Distinct from DEF-158 (resolved Sprint 31.8) + DEF-199 (resolved IMPROMPTU-04); pre-position-existence query before retry. |

Total: 7 items in scope.

## Known Dependencies / Constraints

- **Coordinate with `post-31.9-reconciliation-drift`.** DEF-195 (broker-state
  divergence) and DEF-196 (stop-retry cascade) overlap with DEF-204's
  reconciliation-drift fix in `argus/execution/order_manager.py`. The two
  sprints' fixes must not regress each other; recommend running
  `post-31.9-reconciliation-drift` first because DEF-204 is CRITICAL safety
  and its OCA-grouping changes will be visible to this sprint's reconnect
  work.
- **Cannot be safe-during-trading.** Order-manager and broker-side changes
  modify the live trading path. Sessions must run during market-closed hours
  with the operator's daily `ibkr_close_all_positions.py` mitigation still in
  place.
- **`RejectionStage` schema migration** (DEF-184) requires an idempotent
  `ALTER TABLE` on `counterfactual.db` and a frontend `/counterfactual/accuracy`
  consumer update.

## Open Questions (for planning conversation)

- Should DEF-177 + DEF-184 land in the same session as part of a single
  `RejectionStage` refactor, or split across two sessions to keep blast radius
  small?
- For DEF-196 fix option (3) (query broker qty before emergency flatten), how
  should the timeout be set on `await self._ib.reqPositionsAsync()` so that a
  hung broker query does not itself cascade?
- For DEF-195's periodic reconciliation, what threshold triggers the
  block-new-entries response — any divergence, or >N% / >M absolute? Should
  the block be auto-clearing or operator-clearing?
- Does Apr 21 F-04 collapse into DEF-195's reconciliation work, or does it
  warrant a dedicated session?

## Adversarial Review Profile

- **Adversarial Tier 2 review REQUIRED** for the reconnect-recovery sessions
  (DEF-194/195/196). Order-manager and broker-side changes are non-trivial and
  must be evaluated against the IMSR-style live-data anchors documented in the
  Apr 22/23/24 debriefs.
- **Standard Tier 2 review** sufficient for the `RejectionStage` enum work
  (DEF-177/184) — the change is bounded to a StrEnum + emitter refactor +
  schema migration with clear regression tests.

## Context Pointers

- Sprint 31.9 summary: `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- Apr 22 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md`
  (§C2 stale cache, §C3 divergence, §C4 stop-retry cascade)
- Apr 23 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md`
  (§C3 divergence at 70-symbol mismatch, §C4 stop-retry cascade with
  pre-outage trigger)
- Apr 24 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md`
  (signals raw upstream cascade ~2× worse than Apr 23 with lightest network
  stimulus — design input that DEF-196's fix must defend high-signal-velocity
  trigger)
- IMPROMPTU-09 verification report: `docs/sprints/sprint-31.9/IMPROMPTU-09-verification-report.md`
  (VG-7 BITO concentration evidence cross-references DEF-195)
- IMPROMPTU-04 closeout: `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` (the
  3-branch side-check pattern this sprint will continue applying)
- Related DECs: DEC-372 (stop retry caps), DEC-369 (broker-confirmed
  reconciliation), DEC-367 (margin circuit breaker), DEC-377 (reconciliation
  redesign)
- Build-track queue: `docs/roadmap.md`

## Not-in-Scope

- DEF-204 reconciliation-drift fix (lives in `post-31.9-reconciliation-drift`).
- Component ownership consolidation (lives in `post-31.9-component-ownership`).
- Alpaca-side emitter TODO (lives in `post-31.9-alpaca-retirement`).
- The OCA-grouping work on bracket children (DEF-204 Session 1 — different
  sprint).

## Pre-Planning Checklist

- [ ] All DEFs in scope still OPEN (verify CLAUDE.md)
- [ ] `post-31.9-reconciliation-drift` sprint completed first (recommended)
- [ ] No dependencies blocked
- [ ] Build-track queue supports starting this sprint
- [ ] Sprint 31.9 SPRINT-CLOSE-B core-doc sync has landed (so docs reflect current state)

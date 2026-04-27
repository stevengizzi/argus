# Sprint `post-31.9-reconciliation-drift` Discovery Notes

> Discovery-grade seed doc. Written at Sprint 31.9 SPRINT-CLOSE-A on 2026-04-24.
> Enough context to start a planning conversation without re-reading the full
> Sprint 31.9 history.
> **Not a plan; not a spec.** Planning conversation produces the actual sprint
> package.
>
> **CRITICAL SAFETY** — fix must land before live trading. Paper trading
> currently operates in safe-mitigation mode (operator runs
> `scripts/ibkr_close_all_positions.py` daily) until this sprint lands.

## Sprint Identity

- **Sprint ID:** `post-31.9-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (Health & Hardening campaign-close)
- **Build-track position:** post-31.9 named horizon. **Likely takes precedence
  over Sprint 31B and the other 3 post-31.9 horizons** because DEF-204 is
  CRITICAL safety. Operator confirms ordering at planning time.
- **Discovery date:** 2026-04-24

## Theme

Fix DEF-204 — the upstream cascade mechanism that IMPROMPTU-04's A1 fix was
**masking, not fixing**. On Apr 24 paper trading, 44 symbols / 14,249 shares
ended unintentionally short at EOD via gradual reconciliation-mismatch drift
(not the 2.00× DEF-199 doubling signature, which IMPROMPTU-04 correctly
prevented). IMPROMPTU-04's A1 fix detected and refused all 44 doublings safely;
the CRITICAL safety issue is that the upstream cascade producing the underlying
shorts is independent and requires its own mechanism fix.

IMPROMPTU-11 (Sprint 31.9 Stage 9C, 2026-04-24, read-only diagnostic) traced
8 hypotheses against 2,225 broker fills and identified the multi-mechanism
failure cluster, with a **single architectural root cause**: side-blind exit
accounting.

**Primary fill-side mechanism (~98% of blast radius — H1+H7):** bracket children
placed via `parentId` only at `argus/execution/ibkr_broker.py:736-769`, with
**no `ocaGroup` / `ocaType` set**, combined with redundant standalone SELL
orders from trail-flatten (`order_manager.py:2451`) and escalation-stop
(`order_manager.py:2552`) paths that share **no OCA group with the bracket
children** — produces multi-leg fill races. Mass-balance evidence: 2,225 broker
fills − 899 entries − 679 ARGUS-recognized exits = ~647 unaccounted SELL fills
routed to the silent `logger.debug("Fill for unknown order_id ...")` path at
`order_manager.py:592` (invisible at INFO+).

**Detection blindness (allows 6-hour silent accumulation — H2+H8):**
1. `reconcile_positions()` orphan loop at `order_manager.py:3038-3039` only
   handles ARGUS-orphan direction (`internal>0 + broker==0`) — silently ignores
   broker-orphan / phantom-short direction.
2. Call site at `main.py:1520-1531` strips side info before reconciliation runs
   (`qty = float(getattr(pos, "shares", 0))` returns absolute value via
   `Position.shares = abs(int(ib_pos.position))` at `ibkr_broker.py:937`).
3. `_check_flatten_pending_timeouts()` (the DEF-158 retry path) at
   `order_manager.py:2384-2406` reads `broker_qty = abs(int(getattr(bp, "shares", 0)))`
   and issues SELL even when broker is short — actively **doubles** pre-existing
   shorts (H5).

**IMSR forensic anchor:** Bracket 2 (BUY 200 @ 7.81 at 11:51:07) leaked −100
short via 12:15:04 escalation-stop fire (SELL 200) + simultaneous trail-flatten
partial fill (100); the DEF-158 retry at 12:17:09 then doubled to −200 by
SELLing 100 against the abs-qty=100 reading of the −100 short broker state.

The fix scope is concrete, **3 sessions, all-three-must-land-together** (partial
fixes leave residual amplifiers). **Adversarial Tier 2 review REQUIRED** at
every session boundary.

## Deferred-Items Scope

DEFs explicitly queued for this sprint:

| DEF # | Title | Source | Notes |
|---|---|---|---|
| DEF-204 | CRITICAL SAFETY — upstream cascade of unexpected shorts, independent of DEF-199 | CLAUDE.md; Apr 24 debrief §A2 + §C12; IMPROMPTU-11 mechanism diagnostic | **CRITICAL.** Mechanism IDENTIFIED, fix scope concrete (3 sessions below). |

Total: 1 DEF in scope, but the fix is structural and touches 3 surfaces.

## Concrete Fix Plan (from IMPROMPTU-11 §Top-3 ranking)

### Session 1: Bracket OCA grouping (primary fill-side fix, ~98% of blast radius)

- Set explicit `ocaGroup` + `ocaType=1` on bracket children at
  `argus/execution/ibkr_broker.py:736-769`. The `ocaGroup` value should be a
  per-bracket unique identifier (e.g., the parent order's ULID).
- Thread `oca_group_id` through `ManagedPosition` so the trail-flatten
  (`order_manager.py:2451`), escalation-stop (`order_manager.py:2552`), and
  `_resubmit_stop_with_retry` SELL orders all carry the **same** `ocaGroup`
  as their bracket's children. This makes IBKR cancel the redundant legs
  automatically when one fills.
- Regression tests must exercise the previously-leaking case: simulate an
  escalation-stop fill + simultaneous trail-flatten partial; assert
  end-state position is 0 and at most one SELL order is filled (the OCA
  group cancels the rest).

### Session 2: Side-aware reconciliation contract

- Change reconciliation contract from `dict[str, float]` to
  `dict[str, tuple[OrderSide, int]]`. Update the call site at
  `main.py:1520-1531` to pass side-and-shares, not abs-shares.
- Extend the orphan-direction guard at `order_manager.py:3038-3039` to handle
  the broker-orphan direction (broker has shares ARGUS doesn't track) with
  a **CRITICAL alert + entry gate** that blocks new entries until the operator
  acknowledges or the broker side reconciles to 0.
- Update `Position.shares = abs(int(ib_pos.position))` at
  `ibkr_broker.py:937` to preserve the broker-side sign in a separate
  `Position.broker_side: OrderSide` field; downstream consumers narrow on it.
- Regression tests must exercise the broker-orphan direction explicitly —
  inject a broker-side short with no ARGUS-side `_managed_positions` entry,
  assert reconciliation alerts and gates entries.

### Session 3: Side-aware DEF-158 retry path

- Apply IMPROMPTU-04's 3-branch side-check pattern to
  `_check_flatten_pending_timeouts()` (DEF-158 retry path) at
  `argus/execution/order_manager.py:2384-2406`. Read `pos.side` (or
  `pos.broker_side` from Session 2) alongside `pos.shares`; if
  `side == OrderSide.SELL` (broker has phantom short), abort retry with
  CRITICAL log + alert.
- The 3-branch pattern: `BUY` → SELL-flatten as today; `SELL` → ERROR + skip
  (cover manually via `scripts/ibkr_close_all_positions.py`); unknown side →
  ERROR + skip. Mirrors the IMPROMPTU-04 EOD Pass 1 / Pass 2 fix exactly.
- Regression test: inject a phantom broker short into the
  `flatten_pending_orders` queue; assert the retry path logs CRITICAL and does
  NOT issue a SELL.

## Cross-references (must NOT regress)

- **DEF-158** (dup-SELL prevention) — the detection mechanism currently
  working correctly that DEF-204 work must NOT regress. The Session 3 fix
  changes the retry path's response to phantom shorts, but must preserve
  DEF-158's normal-case dup-SELL prevention.
- **DEF-196** (32+ stop-retry-exhaustion cascade events) — different family,
  lives in `post-31.9-reconnect-recovery-and-rejectionstage`. The fix paths
  do not overlap, but Session 1's OCA-grouping work may surface DEF-196's
  Apr 23 high-signal-velocity trigger more clearly.
- **DEF-199** (RESOLVED IMPROMPTU-04) — the A1 fix at `order_manager.py:1707`
  + `:1684` is the mechanism that caught all 44 doublings on Apr 24 and is
  the only thing keeping paper trading safe today. **Do not modify the A1
  fix in this sprint.** The pattern is being applied (Session 3 mirrors the
  A1 3-branch logic) but the A1 fix itself stays untouched.

## Operational Mitigation in Effect Until Fix Lands

- Operator runs `scripts/ibkr_close_all_positions.py` at session close daily.
- ~14K shares/day of unintended short exposure observed on Apr 24; A1 fix
  correctly refuses amplification + escalates.
- Paper trading remains in this safe-mitigation mode throughout the sprint;
  do NOT re-enable live trading until all 3 sessions land + adversarial Tier 2
  reviews clear + at least 3 paper sessions confirm zero phantom-short
  accumulation.

## Adversarial Review Profile

- **Adversarial Tier 2 review REQUIRED** for all 3 sessions.
- Recommend full Tier 3 architectural review at session boundaries —
  order-manager and broker-side changes are non-trivial and safety-critical;
  the cost of a regression here is higher than for any normal sprint.
- Each session's regression tests must include both:
  (a) the originally-leaking case with revert-proof anchoring;
  (b) a sanity check that DEF-199's A1 fix still fires correctly post-change.

## Context Pointers

- Sprint 31.9 summary: `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- IMPROMPTU-11 mechanism diagnostic: `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`
  (8 hypotheses, IMSR forensic trace, top-3 ranking, mass-balance evidence)
- Apr 22 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` (DEF-199's 2.00× signature evidence)
- Apr 23 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md` (DEF-196's two-trigger evidence)
- Apr 24 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md` (DEF-204's gradual-drip 1.00× signature)
- IMPROMPTU-04 closeout: `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` (the 3-branch pattern Session 3 mirrors)
- Related DECs: DEC-369 (broker-confirmed reconciliation), DEC-377 (reconciliation redesign), DEC-372 (stop retry caps), DEC-371 (RECONCILIATION exit reason)
- Build-track queue: `docs/roadmap.md`

## Not-in-Scope

- DEF-194/195/196 reconnect-recovery work (lives in
  `post-31.9-reconnect-recovery-and-rejectionstage`).
- Component ownership consolidation (lives in `post-31.9-component-ownership`).
- Alpaca retirement (lives in `post-31.9-alpaca-retirement`).
- Re-enabling live trading — that decision lives outside this sprint after
  paper-trading evidence accumulates.

## Pre-Planning Checklist

- [ ] DEF-204 still OPEN in CLAUDE.md
- [ ] Operator's daily `ibkr_close_all_positions.py` mitigation still in place
- [ ] No dependencies blocked
- [ ] Build-track queue confirms this sprint runs **before** Sprint 31B per
      safety-priority precedence
- [ ] Sprint 31.9 SPRINT-CLOSE-B core-doc sync has landed (so docs reflect current state)
- [ ] Adversarial Tier 2 reviewer engaged for all 3 sessions

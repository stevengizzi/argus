# Sprint 31.92 — Unit 5 Spike v2 Re-Execution (Attempt 1) Close-Out

**Self-assessment:** HALT — Cat 3 substantial gap. Empirical finding falsifies DEC-390's H2/H4/H1 prescription at the broker-policy level. Tier 3 Review #3 escalation per DEC-390 sprint-close gate.

**Date:** 2026-04-30
**Anchor commit (pre-Unit-5):** `85eb511` (sprint-31.92 Unit 4 follow-on — fix stale module-level docstring (Tier 2 CONCERN-1))
**Operator-execution context:** Market open (regular trading hours), ARGUS down, IBKR paper Gateway up (account U24619949, clientId=1), pre-spike position sweep gate (Unit 3) confirmed flat, manual disconnect/reconnect performed during axis (ii) prompt before script crash.

---

## What was attempted

Operator-executed `scripts/spike_def204_round2_path1.py` with the post-Unit-3 + post-Unit-4 + post-CONCERN-1-docstring-fix code:

- **Cat A.1** — Mode A propagation measurement fix: `reqOpenOrders()` force-pull + 2.5s post-amend wait before sampling `t.order.auxPrice`.
- **Cat A.2** — Side-aware `_flatten()`: three-branch `signed_qty > 0 → SELL` / `signed_qty < 0 → SpikeShortPositionDetected raise` / `signed_qty == 0 → no-op`, plus pre-spike position-sweep refusal-to-start gate at `main_async()` start.
- **Cat B.1** — Axis (iii) deletion (verdict-side DEF: "axis (iii) bug class deleted; not measured").
- **Cat B.2** — Axis (ii) and axis (iv) demoted to informational; binding decision rests solely on Mode A + axis (i) + Mode D under DEC-390.
- **Cat B.3** — `isConnected()` fail-loud instrumentation on axes (ii)/(iv) per DEF-238.
- **DEC-390 binding rule encoding** — three-mechanism prescription (H2 PRIMARY DEFAULT / H4 hybrid / H1 cancel-and-await); Mode D as H1's hard gate; INCONCLUSIVE return when binding signal is unsatisfiable.

Expected outcome: clean JSON with `selected_mechanism` ∈ `{h2_amend, h4_hybrid, h1_cancel_and_await}` per DEC-390 rule.

---

## What happened

Mode A + axis (i) + axis (ii) ran before the spike crashed during axis (iv) due to an exhausted reconnect budget after the operator-initiated Gateway disconnect (intended behavior for axis (ii); harness gap that axis (iv) tried to run anyway → DEF-243).

### Substantive empirical finding

Every `modify_order` call against bracket stop children produced the following sequence:

```
[time + 0ms] [INFO] Order modified: [stop_ulid] — {'price': [new_price]}    ← API call accepted synchronously
[time + ~1-6ms] [ERROR] Error 10326, reqId [N]: OCA group revision is not allowed.
[time + ~1-6ms] [WARNING] IBKR error 10326: OCA group revision is not allowed.
[time + ~1-6ms] [INFO] Order cancelled: [stop_ulid]                          ← broker cancels the modified order
```

Verbatim representative excerpt from operator log (axis (ii) reconnect-window prompt sequence):

```
14:05:24.771 [INFO] Order modified: 01KQFS28KVH380Y8EXB5TZHBRM — {'price': 713.21}
14:05:24.777 [ERROR] Error 10326, reqId 1648: OCA group revision is not allowed.
14:05:24.777 [WARNING] IBKR error 10326: OCA group revision is not allowed.
14:05:24.777 [INFO] Order cancelled: 01KQFS28KVH380Y8EXB5TZHBRM
14:05:25.274 [ERROR] Error 10326, reqId 1648: OCA group revision is not allowed.
14:05:25.274 [WARNING] IBKR error 10326: OCA group revision is not allowed.
14:05:25.776 [ERROR] Error 10326, reqId 1648: OCA group revision is not allowed.
14:05:25.776 [WARNING] IBKR error 10326: OCA group revision is not allowed.
[... ~10 retry attempts repeating against the now-cancelled reqId 1648 ...]
```

Verbatim Mode A representative excerpt (sub-millisecond synchronous return, async cancel ~1-6ms later):

```
14:00:38.394 [INFO] Order modified: 01KQFR... — {'price': 712.99}    ← API call accepted
14:00:38.394 [ERROR] Error 10326, reqId 1392: OCA group revision is not allowed.
14:00:38.395 [INFO] Order cancelled: 01KQFR...                        ← broker cancels the stop
```

This pattern was consistent across:

- **Mode A**: 50 trials, 100% async-cancel rate.
- **Axis (i) concurrent_amends**: 30 trials × ~3 positions, 100% async-cancel rate.
- **Axis (ii) reconnect_window_amends**: pre-disconnect amends (e.g., reqId 1648 in the operator log), 100% async-cancel rate.

**Total observed: ~170 amends, 100% async-cancel rate, fully consistent. No exceptions.**

### Mechanism cause

Sprint 31.91 DEC-386 shipped explicit `ocaGroup` + `ocaType=1` threading on bracket children (entry + stop + target as OCA group members). IBKR's broker policy categorically refuses `modify_order` against any OCA group member: synchronous return is "accepted," then async error 10326 + cancel arrives via `errorEvent` callback ~1-6ms later. **This is broker-side policy, not a Sprint 31.92 implementation issue, and not a stress-condition failure.**

### Spike-harness measurement-gap (DEF-243)

`_amend_one()` in the spike harness checks only the synchronous return value of `modify_order`:

```python
res = await broker.modify_order(stop_ulid, {"price": new_aux})
if res.status == OrderStatus.REJECTED:
    return True, res.message or "REJECTED"
return False, None  # ← this branch fires for every OCA-rejected amend
```

Because IBKR returns `SUBMITTED` initially and emits error 10326 via async callback ~1-6ms later, `_amend_one` records every OCA-rejected amend as success. So:

- **Axis (i) Wilson UB** would have reported near-0% (all "succeeded") under this measurement, making OCA-categorical-rejection invisible in the JSON artifact (would look superficially like H2 territory).
- **Mode A `propagation_ok`** correctly reported `False` because Cat A.1's `reqOpenOrders()` + 2.5s wait DID sample the post-cancel state — the order had disappeared from `openTrades` by the sample time. So the DEC-390 rule output `INCONCLUSIVE` for the right reason (Mode A `propagation_ok` = False short-circuited the rule before axis (i) UB mattered) but framed it as *"propagation timing wrong"* rather than *"broker categorically rejects modify on OCA members."*

The empirical truth is fully captured in the operator log; the JSON artifact only encodes it indirectly. DEF-243 closes this measurement-gap so future spike runs can encode OCA-rejection signature directly in the JSON.

### Crash trajectory

After axis (ii) drained the reconnect budget (4 reconnect attempts exhausted at exponential backoff 1s/2s/4s/8s = 15s total), axis (iv) attempted to run anyway and crashed on `reqMktData` → `ConnectionError: Not connected`. The harness should have detected the disconnected-broker state before starting axis (iv) and either reconnected with a fresh budget or skipped gracefully — DEF-243 also notes this gap.

Crash-recovery JSON wrote the Cat B.2 schema correctly (`binding_axis_result: {}`, `informational_axes_results: {}`, `axis_i_wilson_ub: 100.0`, `status: INCONCLUSIVE`) but lost the Mode A + axis (i) data that DID complete pre-crash. The operator log contains the complete pre-crash evidence; the JSON does not.

Verbatim crash traceback (from operator log):

```
14:05:42.625 [INFO] === Mode B axis (iv) joint — up to 30 trials ===
14:05:42.626 [ERROR] Spike crashed mid-run: Not connected
Traceback (most recent call last):
  File "/Users/stevengizzi/coding-projects/argus/scripts/spike_def204_round2_path1.py", line 1380, in main_async
    AXIS_JOINT: await _axis_joint(
  File "/Users/stevengizzi/coding-projects/argus/scripts/spike_def204_round2_path1.py", line 798, in _axis_joint
    price = await _get_market_price(broker, s)
  File "/Users/stevengizzi/coding-projects/argus/scripts/spike_def204_round2_path1.py", line 323, in _get_market_price
    ticker = broker._ib.reqMktData(contract, "", False, False)
  File "/Users/stevengizzi/.pyenv/versions/3.11.8/lib/python3.11/site-packages/ib_async/ib.py", line 1415, in reqMktData
    reqId = self.client.getReqId()
  File "/Users/stevengizzi/.pyenv/versions/3.11.8/lib/python3.11/site-packages/ib_async/client.py", line 165, in getReqId
    raise ConnectionError("Not connected")
ConnectionError: Not connected
14:05:42.635 [INFO] Disconnected from IB Gateway
```

### Crash-recovery JSON artifact

Preserved verbatim at `docs/sprints/sprint-31.92-def-204-round-2/spike-v2-attempt-1-results.json`:

```json
{
  "status": "INCONCLUSIVE",
  "selected_mechanism": null,
  "inconclusive_reason": "spike crashed: Not connected",
  "h2_modify_order_p50_ms": 0.0,
  "h2_modify_order_p95_ms": 0.0,
  "h2_rejection_rate_pct": 0.0,
  "h2_deterministic_propagation": false,
  "binding_axis_result": {},
  "informational_axes_results": {},
  "axis_i_wilson_ub": 100.0,
  "h1_cancel_all_orders_p50_ms": 0.0,
  "h1_cancel_all_orders_p95_ms": 0.0,
  "h1_propagation_n_trials": 0,
  "h1_propagation_zero_conflict_in_100": false,
  "trial_count": 0,
  "spike_run_date": "2026-04-30T18:05:42.632831+00:00"
}
```

The empty `binding_axis_result` / `informational_axes_results` reflects the crash happening in `_axis_joint` before those collectors flushed. `axis_i_wilson_ub: 100.0` is the crash-recovery default, not a measured value.

---

## Implications for DEC-390

**H2 (`modify_order` PRIMARY DEFAULT) and H4 (hybrid amend) are structurally eliminated** by IBKR's OCA-immutability policy. This is not a stress-condition failure; it is a categorical rejection on every attempt. Both mechanisms depended on `modify_order` succeeding against the bracket stop child, which the broker refuses while the order is an OCA group member.

**H1 (cancel-and-resubmit-fresh-stop) remains theoretically viable** because it does not modify an OCA member — it cancels the bracket-grouped stop and creates a new stop outside the OCA bond. Mode D (cancel-then-immediate-SELL N=100 stress; the H1 hard gate per Decision 2 of DEC-390) was never reached due to the axis (iv) crash. **H1 is unstress-tested.**

**A fourth mechanism not enumerated in DEC-390 has surfaced:**

- (M4a) Cancel bracket entirely / submit fresh bracket — sidesteps OCA membership at the cost of bracket teardown.
- (M4b) Temporarily remove from OCA / modify / restore — itself an empirical question (does IBKR allow OCA-membership modification post-creation? — not characterized).

---

## Implications for DEC-386

DEC-386's OCA threading (Sprint 31.91 S2) closed DEF-204 Round 1 — that work was correct and is **not being relitigated**. However, the OCA threading has a downstream consequence: `modify_order` is broker-blocked against any bracket child. This consequence was not priced in at DEC-386 design time. Sprint 31.94 reconnect-recovery work will hit this same wall when it tries to re-amend stops post-reconnect (RSK-DEC390-31.94-COUPLING is now potentially under-scoped).

Tier 3 Review #3 should consider whether DEC-386 needs a follow-up RSK or DEF for the `modify_order` incompatibility, or whether the constraint is simply absorbed by whichever mechanism replaces H2/H4 in DEC-390's amendment.

---

## Cross-references

- **DEF-242** (NEW): DEC-390 H2/H4 paths empirically eliminated by DEC-386 OCA-immutability policy. Filed in CLAUDE.md DEF table at this commit.
- **DEF-243** (NEW): Spike harness `_amend_one()` async error 10326 capture gap + spike script file-logger gap + axis (iv) reconnect-budget-exhaustion guard gap. Filed in CLAUDE.md DEF table at this commit. Sprint 31.92 sprint-internal cleanup, post-Tier-3-#3.
- Tier 3 Review #2 verdict at `tier-3-review-2-verdict.md` § DEC-389 sprint-close gate (gate triggered by this finding; "DEC-390 cannot ship if spike v2 returns INCONCLUSIVE again or if Cat B work surfaces additional architectural concerns").
- Sprint 31.91 DEC-386 — the architectural commitment whose downstream consequence is the empirical finding.
- Sprint 31.92 Unit 3 close-out at `session-1a-closeout.md` (Cat A.1 + Cat A.2 origin).
- Sprint 31.92 Unit 4 commit `b758e5d` (Cat B.1 + Cat B.2 + Cat B.3 + DEC-390 rule encoding).
- Sprint 31.92 Unit 4 follow-on commit `85eb511` (Tier 2 CONCERN-1 docstring fix).
- Spike result JSON preserved at `spike-v2-attempt-1-results.json` (sprint folder, this commit).

---

## What this commit does NOT do

- Does NOT amend `docs/decision-log.md` — DEC-390 + DEC-391 remain RESERVED pending Tier 3 #3 disposition.
- Does NOT amend `docs/dec-index.md`.
- Does NOT amend `sprint-spec.md`, `spec-by-contradiction.md`, `falsifiable-assumption-inventory.md`, or `escalation-criteria.md`.
- Does NOT touch `docs/risk-register.md` (Tier 3 #3 may file new RSKs).
- Does NOT modify `scripts/spike_def204_round2_path1.py` (DEF-243 fixes deferred).
- Does NOT touch any production code under `argus/`.

This is **bookkeeping + escalation prep**, not a fix.

---

## Next steps

1. **This commit** lands the close-out + DEF-242 + DEF-243 + spike artifact preservation. No DEC-390 amendment, no spec amendment.
2. **Operator stands up Tier 3 Review #3** in a fresh Claude.ai conversation. Briefing prompt forthcoming from Sprint 31.92 Work Journal.
3. **Tier 3 #3 verdict** determines:
   (a) Which mechanism replaces H2/H4 in DEC-390 (likely H1 stress-tested at Mode D, OR a newly-enumerated M4a/M4b);
   (b) Whether DEC-386 needs a follow-up RSK/DEF for the `modify_order` incompatibility;
   (c) Whether Sprint 31.92 SbC needs structural amendment.
4. **Post-Tier-3-#3:** mid-sync per `protocols/mid-sprint-doc-sync.md` materializes the verdict's amendments. Then sprint resumes per the verdict's session-resumption guidance.

---

## Test gates

- **Pytest pre-flight + final close-out:** 5,337 (preserved; no production code touched in this commit). One xdist-only flake observed on the first pre-flight run (`tests/test_evaluation_telemetry_e2e.py::TestHealthWarning::test_health_no_warning_with_evaluations` — passes in isolation; passed on re-run); consistent with DEF-192-class xdist behavior, not a regression.
- **Vitest:** 913 (no UI change).
- **No spike script changes** in this commit.

---

## Self-assessment: HALT

**Category 3 substantial gap.** The empirical signal from this run conclusively eliminates two of DEC-390's three prescribed mechanisms (H2 + H4) at the broker-policy level. The third mechanism (H1) remains unstress-tested. Per `tier-3-review-2-verdict.md` § DEC-389 sprint-close gate, both gate triggers fired:

1. Spike v2 returned `INCONCLUSIVE`.
2. Cat B work surfaced an additional architectural concern (DEC-386 OCA-immutability eliminates H2/H4 categorically) beyond what DEC-390 framed.

**Sprint 31.92 scope is frozen pending Tier 3 Review #3 disposition.** Operator standing up Tier 3 #3 briefing separately.

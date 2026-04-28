# Sprint 31.91: Sprint-Level Regression Checklist

> **Phase C artifact 5/7.** Specific, testable items the @reviewer must verify
> at every Tier 2 review. Embedded into every implementation prompt so the
> implementer can self-check before close-out and the reviewer has explicit
> assertions to test against. Each item lists which sessions are responsible
> for verifying it.

## Critical Invariants (Must Hold After Every Session)

> Sprint 31.91 was revised across multiple passes:
> - 9 invariants / 4 sessions (original)
> - 17 invariants / 10 sessions (1st revision after Phase C-1 first pass)
> - 17 invariants / 12 sessions (Phase A revisit; H3 split)
> - 18 invariants / 17 sessions (2nd revision; alert observability all-in)
> - **22 invariants / 18 sessions (3rd revision; HIGH #1 5a-split + HIGH #5 spike-trigger
>   + MEDIUM #11 SimulatedBroker tautology grep-test + LOW #19 session-count
>   yellow-flag)**
>
> Invariants 1–13 unchanged from prior. Invariant 14 expanded to 19-row state
> matrix (one per session, with 5a split into 5a.1 + 5a.2). Invariant 15
> expanded for Session 1c reconstruct-safety + Session 0 alpaca ABC + Session
> 5b alpaca emitter behavioral (not textual) check. Invariants 16–20 carry
> forward from 2nd pass. **Invariants 21–22 added in 3rd revision** for
> SimulatedBroker OCA tautology guard and spike-script freshness.

### 1. DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD

**Test:** Inject a `Position(side=OrderSide.SELL, shares=100)` into the broker
mock; trigger EOD Pass 2 flatten; assert ERROR log "DETECTED UNEXPECTED SHORT
POSITION" present, assert `place_order` NOT called for that symbol with a SELL
order. Pre-existing test name: `test_short_position_is_not_flattened_by_pass2`
(in `tests/test_sprint329.py` or sibling).

**Verified at:** Every session's close-out. The A1 fix is on the do-not-modify
list; Tier 2 review must verify `git diff` shows no edits to
`order_manager.py:1670-1750`.

**Sessions:** ALL.

---

### 2. DEF-199 A1 EOD Pass 1 retry still respects side check

**Test:** Pre-existing `test_pass1_retry_skips_short_position`. Same shape as
above for the Pass 1 retry path.

**Verified at:** Every session's close-out.

**Sessions:** ALL.

---

### 3. DEF-158 dup-SELL prevention works for the ARGUS=N, IBKR=N normal case

**Test:** Setup `_flatten_pending` with order_id X; broker reports the symbol
with shares matching `position.shares_remaining`; trigger
`_check_flatten_pending_timeouts` retry; assert SELL placed for the correct
quantity (legacy behavior preserved). Pre-existing test:
`test_def158_flatten_qty_mismatch_uses_broker_qty` or sibling.

**Verified at:** Sessions 1a, 1b, 2a, 2b, 2c (the file is touched by 1b/2a/2b/2c
but not the DEF-158 logic). Session 3 modifies this exact function — the
ARGUS=N, IBKR=N case must still work after the 3-branch is added.

**Sessions:** Session 3 must explicitly include `test_def158_retry_long_position_flattens_normally`
in its definition of done (already specified in `session-breakdown.md`).

---

### 4. DEC-117 atomic bracket invariant: parent fails → all children cancelled

**Test:** Force the bracket children placement to raise mid-loop (after stop
placed, before T1 placed); assert the rollback at `ibkr_broker.py:783-805`
fires; assert parent order is cancelled.

**Verified at:** Sessions 1a (the only session that touches bracket placement
code).

**Sessions:** Session 1a's Tier 2 review explicitly verifies `git diff` on
`ibkr_broker.py:783-805` shows zero edits.

---

### 5. Existing 5,080 pytest baseline holds; new tests are additive only

**Test:** `pytest --ignore=tests/test_main.py -n auto -q` returns ≥5,080 passing
post-session (5,080 + new tests added in this session, minus none).

**Verified at:** Every session's close-out.

**Sessions:** ALL.

---

### 6. `tests/test_main.py` baseline holds (39 pass + 5 skip)

**Test:** `pytest tests/test_main.py -q` returns 39 pass + 5 skip (or higher
pass count if a session adds to it).

**Verified at:** Every session's close-out.

**Sessions:** ALL. Session 2a touches `main.py` and is the most likely site to
affect `test_main.py`; close-out must explicitly cite the count.

---

### 7. Vitest baseline holds at 866

**Test:** `npm test` (or equivalent) returns 866 passing.

**Verified at:** Every session's close-out.

**Sessions:** ALL. No frontend changes in this sprint; the count is unchanged
by definition. Verification catches accidental cascade if a backend change
broke a frontend test fixture.

---

### 8. Risk Manager check 0 (`share_count ≤ 0` rejection) unchanged

**Test:** Pre-existing test around `risk_manager.py:335` Check 0 logic; verify
Risk Manager still rejects `share_count <= 0` before any other check fires.

**Verified at:** Every session's close-out via `git diff` audit on
`argus/core/risk_manager.py` (should show zero edits across the entire sprint).

**Sessions:** ALL.

---

### 9. IMPROMPTU-04 startup invariant unchanged

**Test:** Pre-existing tests on `check_startup_position_invariant()` —
`test_single_short_fails_invariant`, `test_all_long_positions_returns_ok`,
`test_position_without_side_attr_fails_closed`.

**Verified at:** Every session's close-out via `git diff` on `main.py` startup
region (should show zero edits except Session 2a's reconciliation call site at
lines 1520-1531, which is BELOW the startup invariant region).

**Sessions:** ALL. Session 2a needs explicit verification that its `main.py`
edit is confined to lines 1520-1531 and does not touch the startup invariant.

---

### 10. DEC-367 margin circuit breaker unchanged

**Test:** Pre-existing margin-circuit tests around
`order_manager.py:_check_margin_circuit_*` paths.

**Verified at:** Every session's close-out via `git diff` on
`order_manager.py:1492` and surrounding margin-circuit logic.

**Sessions:** ALL. Session 2c's per-symbol entry gate MIRRORS the DEC-367
pattern shape but does NOT extend or modify the existing margin circuit;
verification confirms the two states are independent (a symbol can be in
both `_phantom_short_gated_symbols` and the margin-circuit set).

---

### 11. Sprint 29.5 EOD flatten circuit breaker unchanged

**Test:** Pre-existing EOD-flatten-circuit-breaker tests.

**Verified at:** Every session's close-out via `git diff` on the
EOD-flatten-circuit logic.

**Sessions:** ALL.

---

### 12. Pre-existing flakes did not regress

**Test:** Run the full suite 3× via `pytest -n auto --count=3` (if
pytest-repeat installed) OR run on CI 3 times across the session window;
verify each of DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 fails at the same
or LOWER frequency than baseline.

**Verified at:** Every session's CI run (RULE-050). The Tier 2 reviewer
explicitly cites the CI run URL in the verdict.

**Sessions:** ALL.

---

### 13. New config fields parse without warnings

**Test:** Load `config/system.yaml` and `config/system_live.yaml` via the
project's standard config loader; assert no Pydantic warnings about
unrecognized keys; assert all 3 new fields (`ibkr.bracket_oca_type`,
`reconciliation.broker_orphan_alert_enabled`,
`reconciliation.broker_orphan_entry_gate_enabled`) load with the expected
default values when the YAML omits them, AND with the YAML-specified values
when the YAML includes them.

**Verified at:** Sessions 1a (`bracket_oca_type`) and 2b/2c (the two
reconciliation flags). Each of those sessions writes a config-validation test
per the protocol's "New config fields verified against Pydantic model" item.

**Sessions:** 1a, 2b, 2c.

---

### 14. Monotonic-safety property holds at each session merge

**Test:** Verify the safety state matrix from the design summary at each merge:

| State | OCA bracket | OCA standalone (4) | Broker-only safety | Restart safety | Recon detects shorts | DEF-158 retry side-aware | Mass-balance validated | Alert observability |
|-------|---|---|---|---|---|---|---|---|
| After Session 0 | NO | NO | NO | NO | NO | NO | NO | NO |
| After Session 1a | YES | NO | NO | NO | NO | NO | NO | NO |
| After Session 1b | YES | YES | NO | NO | NO | NO | NO | NO |
| After Session 1c | YES | YES | YES | YES | NO | NO | NO | NO |
| After Session 2a | YES | YES | YES | YES | NO (typed only) | NO | NO | NO |
| After Session 2b.1 | YES | YES | YES | YES | partial (alert only) | NO | NO | NO |
| After Session 2b.2 | YES | YES | YES | YES | partial + side-aware reads (4 filter + 1 alert-align) | NO | NO | NO |
| After Session 2c.1 | YES | YES | YES | YES | full (alert + gate + persistence) | NO | NO | NO |
| After Session 2c.2 | YES | YES | YES | YES | full + auto-clear (5-cycle) | NO | NO | NO |
| After Session 2d | YES | YES | YES | YES | full + override API + audit + configurable threshold | NO | NO | NO |
| After Session 3 | YES | YES | YES | YES | full | YES | NO | NO |
| After Session 4 | YES | YES | YES | YES | full | YES | YES (script + IMSR replay) | NO |
| After Session 5a.1 | YES | YES | YES | YES | full | YES | YES | partial backend-1 (HealthMonitor consumer + REST + atomic+idempotent ack) |
| After Session 5a.2 | YES | YES | YES | YES | full | YES | YES | full backend (WebSocket + persistence + auto-resolution policy + retention/migration) |
| After Session 5b | YES | YES | YES | YES | full | YES | YES | full backend incl. IBKR emitters + E2E + behavioral Alpaca check |
| After Session 5c | YES | YES | YES | YES | full | YES | YES | partial UI (Dashboard banner only) |
| After Session 5d | YES | YES | YES | YES | full | YES | YES | partial UI (banner + toast + ack modal) |
| After Session 5e | YES | YES | YES | YES | full | YES | YES | full UI (Observatory panel + cross-page) |

Each row strictly safer than the row above. Verified by paper-session
debrief the day after each merge: phantom-short accumulation count must
be ≤ the prior row's count; alert observability features available in
the row's state must not regress.

**Verified at:** Every paper-session debrief (post-merge, daily).

**Sessions:** ALL — but verification is post-merge, not in-session.

---

### 15. No items on the do-not-modify list were touched

**Test:** `git diff <session-base>..<session-head>` audit against the
do-not-modify list:

- `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) — zero edits
- `argus/main.py` startup invariant region — zero edits except Session
  1c's scoped expansion of `reconstruct_from_broker()` body to add
  `cancel_all_orders(symbol)` calls (NOT the call-site gate in main.py),
  AND Session 2a's scoped reconciliation call-site edit at lines
  1505-1535, AND Session 2c.1's startup gate-state rehydration code,
  AND Session 5a.1's HealthMonitor consumer init
- `argus/models/trading.py` `Position` class (lines 153-173) — zero edits
- `argus/execution/alpaca_broker.py` — zero edits EXCEPT Session 0's
  `cancel_all_orders(symbol)` ABC compliance impl (DeprecationWarning;
  no other changes)
- **`argus/data/alpaca_data_service.py:593` Alpaca emitter TODO —
  zero edits** (verified by anti-regression test in Session 5b)
- `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` — zero edits
- `workflow/` submodule — zero edits

**Verified at:** Every session's close-out and Tier 2 review.

**Sessions:** ALL.

---

### 16. Bracket placement performance does not regress beyond documented bound

**Test:** Compare bracket-stop fill slippage on a post-Session-1a paper
session vs a pre-Sprint-31.91 baseline. Mean slippage on $7–15 share
universe should not degrade by more than $0.02 (the threshold from
Sprint Spec §"Performance Considerations").

**Verified at:** Session 4's pre-live-transition-checklist update; first
paper-session debrief after Session 1a merges; ongoing nightly check.

**Sessions:** Session 4 wires this into market-session-debrief.md Phase
7. Earlier sessions are observational only.

---

### 17. Mass-balance assertion at session debrief (categorized variance)

**Test:** `scripts/validate_session_oca_mass_balance.py
logs/argus_YYYYMMDD.jsonl` exits 0. Per H2 categorized variance:
zero `unaccounted_leak` rows per symbol per session.
`expected_partial_fill` and `eventual_consistency_lag` rows permitted
but logged.

**Verified at:** Every paper-session post-merge of Session 4. Live-enable
gate criterion requires 3+ paper sessions of clean mass-balance.

**Sessions:** Session 4 delivers the script and the live-enable criteria
in `pre-live-transition-checklist.md`.

---

### 18. Alert observability — frontend banner cross-page persistence

**Test:** While a critical alert is active, navigating between Command
Center pages (Dashboard → Trade Log → Performance → ... → Observatory)
preserves the banner's visibility on every page. Banner clears within
1s of acknowledgment OR auto-resolution, regardless of which page the
operator is on at the moment of clearance.

**Verified at:** Vitest integration test in Session 5e
(`AlertBanner persists across page navigation`); ongoing manual
verification during paper-session debriefs after Session 5e merges.

**Sessions:** Session 5e delivers this via Layout-level mounting.

---

### 19. Alert observability — WebSocket fan-out reconnect resilience

**Test:** Disconnect the WebSocket connection (simulated network failure)
while a critical alert is active. Frontend should:
1. Detect the disconnect within 5s
2. Fall back to TanStack Query polling of `GET /api/v1/alerts/active`
3. On WebSocket reconnect, refetch state via REST and resume WebSocket
4. Recover any alerts emitted during the disconnect window (no silent
   miss)

**Verified at:** Vitest test in Session 5c
(`useAlerts hook handles WebSocket reconnect with state refetch`);
end-to-end integration test in Session 5b covering the full disconnect-
reconnect-recover cycle.

**Sessions:** Session 5c delivers the frontend resilience; Session 5a.2
delivers the REST recovery endpoint.

---

### 20. Alert observability — acknowledgment audit-log persistence

**Test:** After operator acknowledges an alert via
`POST /api/v1/alerts/{alert_id}/acknowledge`, the audit-log entry
persists across ARGUS restart. Querying
`alert_acknowledgment_audit` table after restart returns the entry
with full payload (alert_id, operator_id, timestamp, reason, prior
state).

**Verified at:** pytest test in Session 5a.2
(`test_audit_log_entries_survive_restart`); manual verification during
post-Session-5a paper-session debrief.

**Sessions:** Session 5a.1 delivers the audit-log table; Session 5a.2 delivers persistence.

---

### 21. SimulatedBroker OCA-assertion tautology guard (per third-pass MEDIUM #11)

**Test:** Grep-based regression test that scans `tests/` for files
that import `SimulatedBroker` AND assert OCA-grouping behavior
(cancellation propagation, sibling-fill blocking, late-add rejection).
Such files must use IBKR mocks, not SimulatedBroker, because
SimulatedBroker's OCA implementation is a no-op acknowledgment of
`ocaGroup` / `ocaType`.

```python
def test_no_oca_assertion_uses_simulated_broker():
    """Anti-tautology guard (MEDIUM #11): tests asserting OCA behavior
    must use IBKR mocks. SimulatedBroker's OCA is a no-op
    acknowledgment, so any assertion of OCA-cancellation semantics
    against SimulatedBroker passes whether OCA is wired correctly or
    not. Future test authors who reach for SimulatedBroker because
    it's faster will produce false-passes.

    DEF-208 tracks the gap; spike script
    (scripts/spike_ibkr_oca_late_add.py) is the live-IBKR regression
    check that mitigates the gap.
    """
    import os, re
    forbidden = []
    for root, _, files in os.walk("tests"):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                src = fh.read()
            uses_sim = "SimulatedBroker" in src
            asserts_oca = bool(re.search(
                r"oca|OCA|ocaGroup|ocaType",
                src,
            ))
            if uses_sim and asserts_oca:
                # Allow-list: tests legitimately verifying SimulatedBroker
                # accepts the OCA fields without crashing (bookkeeping)
                if "# allow-oca-sim:" in src:
                    continue
                forbidden.append(path)
    assert not forbidden, (
        f"OCA-behavior tests must use IBKR mocks, not SimulatedBroker, "
        f"to avoid no-op tautology. Found in: {forbidden}. "
        f"Mark known-safe cases with `# allow-oca-sim: <reason>` comment."
    )
```

**Verified at:** Sprint pre-flight (before Session 0); every
backend session's CI run; sprint-final review.

**Sessions:** Lands in regression-checklist at Session 0 close-out;
enforced thereafter.

---

### 22. Spike script freshness (per third-pass HIGH #5)

**Test:** When ARGUS is in paper-trading mode, the most recent
`scripts/spike_ibkr_oca_late_add.py` result file
(`spike-results-YYYY-MM-DD.json`) must be dated within the last 30 days.
Operator runs the spike on the trigger registry events documented in
`docs/live-operations.md`:
- Before any live-trading transition (live-enable gate item)
- Before/after any `ib_async` library version upgrade
- Before/after any IBKR API version change (TWS/Gateway upgrade)
- Monthly during paper-trading windows (calendar reminder)

Failure to return `PATH_1_SAFE` invalidates the OCA-architecture seal
and triggers Tier 3 review.

```python
def test_spike_script_result_dated_within_30_days_in_paper_mode():
    """Spike script freshness guard (HIGH #5). Without a defined trigger
    + freshness check, the live-IBKR regression check is aspirational;
    a file in scripts/ that no one runs."""
    import os, json, datetime
    spike_dir = "scripts/spike-results"
    if not os.path.isdir(spike_dir):
        # No results yet — first-run case. Allowed pre-Session-1a.
        return
    files = sorted(
        f for f in os.listdir(spike_dir)
        if f.startswith("spike-results-") and f.endswith(".json")
    )
    if not files:
        return
    latest = files[-1]  # spike-results-YYYY-MM-DD.json (ISO with dashes)
    date_str = latest[len("spike-results-"):-len(".json")]
    latest_date = datetime.date.fromisoformat(date_str)
    age_days = (datetime.date.today() - latest_date).days
    assert age_days <= 30, (
        f"Spike script result is {age_days} days old "
        f"({latest}); must be ≤30 days in paper-trading mode. "
        f"Re-run scripts/spike_ibkr_oca_late_add.py and verify "
        f"PATH_1_SAFE."
    )
    with open(os.path.join(spike_dir, latest)) as fh:
        result = json.load(fh)
    assert result.get("verdict") == "PATH_1_SAFE", (
        f"Spike script returned {result.get('verdict')!r}, expected "
        f"PATH_1_SAFE. OCA-architecture seal invalidated; Tier 3 "
        f"review required."
    )
```

**Verified at:** Nightly cron / pre-paper-session check; enforced
permanently post-31.91.

**Sessions:** Land regression-checklist invariant at Session 4 (when
the live-enable gate first uses the spike-result freshness as a
gate item); enforced thereafter.

---

## Per-Session Regression Items (Session-Specific)

In addition to the 17 critical invariants above, each session has session-specific
regression items called out in the session breakdown's "Definition of Done"
section. The per-session items are not duplicated here; they are part of the
implementation prompt embedding pattern.

## Verification Pattern

Each Tier 2 review should produce a verdict report containing this regression
checklist as a table, with each item marked PASS / FAIL / N/A. The
reviewer-writes-file pattern (see Phase B decision) means this table lives in
the session's review report file (e.g., `session-1a-review.md`), produced by
the @reviewer subagent.

## Sprint-Close Final Verification

When Session 3 closes out, the operator runs ONE final paper session (not 3, as
the build-up evidence accumulates session-by-session). If that final paper
session shows zero phantom-short accumulation, the sprint can be sealed and
DEF-204 transitioned from OPEN to CLOSED.

The 3-paper-session evidence requirement (from DISCOVERY) is for re-enabling
LIVE trading consideration, which lives outside this sprint per SbC. Sprint
close-out is gated on:

- All 17 regression invariants verified at Session 4's Tier 2.
- Mass-balance script clean on the final paper-session log.
- IMSR replay test green.
- Final paper-session debrief shows zero phantom-short accumulation.
- DEF-204 transitioned to CLOSED in CLAUDE.md.
- DEF-208 + DEF-209 filed.
- DEC-385 + DEC-386 entries written.
- RSK-DEF-204 transitioned to CLOSED in risk-register.md.
- pre-live-transition-checklist.md includes the 3 live-enable gate
  criteria (mass-balance, zero alerts, disconnect-reconnect).

---

*End Sprint 31.91 Regression Checklist.*

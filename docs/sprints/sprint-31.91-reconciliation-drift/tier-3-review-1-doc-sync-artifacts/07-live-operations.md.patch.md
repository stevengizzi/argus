# Doc-Sync Patch 7 — `docs/live-operations.md`

**Purpose:** Add a new section near the end of the file (immediately before the file footer at line 680) covering: (1) the OCA architecture rollback procedure (`bracket_oca_type` flip is RESTART-REQUIRED); (2) the `_OCA_TYPE_BRACKET` lock-step constraint (Sprint 31.91 Session 1b Follow-Up #1); (3) the cancel-timeout failure-mode operator response (Sprint 31.91 Session 1c §"Failure Mode Documentation"); (4) the spike-script trigger registry (Sprint 31.91 regression invariant 22 / HIGH #5).

**Anchor verification (must hold before applying):**
- Line 678: `---`
- Line 680: `*End of Live Operations Guide v1.4*`
- The section just before the footer (lines 670-678) ends with content about cache-update / cache-consolidate cron timings.

---

## Patch — Insert new "Sprint 31.91 — OCA Architecture Operations" section before file footer

### Find:

```
**Expected runtime:**

- `populate --update`: ~5–15 min for one new month across the three datasets.
- `consolidate --resume`: ~2–5 min for just the symbols whose source row count changed. First-time full consolidation after Sprint 31.85 was ~45 min for ~24K symbols — `--resume` is dramatically faster on steady-state monthly deltas.

---

*End of Live Operations Guide v1.4*
```

### Replace with:

```
**Expected runtime:**

- `populate --update`: ~5–15 min for one new month across the three datasets.
- `consolidate --resume`: ~2–5 min for just the symbols whose source row count changed. First-time full consolidation after Sprint 31.85 was ~45 min for ~24K symbols — `--resume` is dramatically faster on steady-state monthly deltas.

---

## OCA Architecture Operations (Sprint 31.91 / DEC-386)

> Sprint 31.91 introduced a 4-layer OCA architecture closing DEF-204's primary mechanism. This section covers the operator-facing procedures: rollback, lock-step constraints, failure-mode response, and the spike-script trigger registry.

### Rollback procedure: `bracket_oca_type: 1 → 0` is RESTART-REQUIRED

If a paper-session debrief (or live monitoring) shows bracket-stop fill-slippage degradation beyond the documented 50–200ms cancellation propagation cost (mean slippage on $7–15 share universe degrades by >$0.05 vs pre-Sprint-31.91 baseline — escalation criterion A8 in Sprint 31.91 spec), evaluate rollback:

1. **STOP ARGUS** (`Ctrl+C` in the terminal, or `kill -SIGTERM <pid>`). Do NOT attempt mid-session config flip — it is explicitly unsupported per Sprint 31.91 Sprint Spec §"Performance Considerations" H1 disposition.
2. **Run operator daily flatten** (`scripts/ibkr_close_all_positions.py`) to ensure no positions exist at the broker before restart.
3. **Edit `config/system.yaml` AND `config/system_live.yaml`** — set `ibkr.bracket_oca_type: 0` in BOTH files. The config change must be visible in whichever YAML the runtime selects.
4. **Restart ARGUS**. Confirm at startup that `IBKRConfig.bracket_oca_type == 0` is logged.
5. **Verify behavior:** the Phase A spike script (`scripts/spike_ibkr_oca_late_add.py`) under `bracket_oca_type=0` should NOT return `PATH_1_SAFE` (because the OCA group is no longer set). This is expected; you have rolled back the OCA architecture.

**Rolling forward** (`0 → 1`) follows the same RESTART-REQUIRED procedure in reverse. Mid-session flip in either direction is unsupported.

### `_OCA_TYPE_BRACKET` constant lock-step

`argus/execution/order_manager.py` carries a module-level constant `_OCA_TYPE_BRACKET = 1` (Sprint 31.91 Session 1b). It mirrors `IBKRConfig.bracket_oca_type`'s default value because `OrderManager` does not currently have access to `IBKRConfig` (Sprint 31.92 component-ownership refactor will close this gap via DEF-212).

**Operator obligation when flipping `bracket_oca_type` to 0 for rollback:** the constant in `order_manager.py:82` should be updated to `0` in lock-step. **If you do not update it, the divergence is functionally a no-op** (standalone SELLs decorate with `ocaType=1` and an `oca_group_id` that has no other live OCA members at the broker, so cancellation is vacuous), but the architectural intent is silently violated. Two-file edit:

```
config/system.yaml:        ibkr.bracket_oca_type: 0
config/system_live.yaml:   ibkr.bracket_oca_type: 0
argus/execution/order_manager.py:82:  _OCA_TYPE_BRACKET: int = 0
```

This lock-step burden disappears once Sprint 31.92 lands DEF-212.

### Cancel-propagation timeout failure-mode response

**What it is:** Sprint 31.91 Session 1c added cancel-then-SELL gating to three broker-only paths (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`). On `CancelPropagationTimeout` (2-second budget exceeded for `cancel_all_orders(symbol, await_propagation=True)` to observe an empty filtered open-orders state), the SELL is **aborted** and a critical `SystemAlertEvent(alert_type="cancel_propagation_timeout")` is emitted.

**The intentional trade-off:** the position remains at the broker as a phantom long with no working stop. This is preferable to placing the SELL without verifying broker-side cancellation, which could create an unbounded phantom short on a runaway upside (asymmetric-risk argument; see Sprint 31.91 Sprint Spec §"Failure Mode Documentation" and DEC-386).

**Operator response when this alert fires:**

1. **Identify the symbol(s)** from the alert message (`f"cancel_all_orders did not propagate within timeout for {symbol} (shares={shares}, stage={stage})..."`). Today the alert is visible only in logs and via the event-bus debug surface — **the Command Center will not show it until Sprint 31.91 Session 5a.1 lands.** Until then, tail the structured log (`logs/argus_YYYYMMDD.jsonl`) for `cancel_propagation_timeout` events:

   ```bash
   grep -F '"alert_type": "cancel_propagation_timeout"' logs/argus_$(date +%Y%m%d).jsonl
   ```

2. **Manually flatten the affected symbol(s) before the next session begins:**

   ```bash
   python scripts/ibkr_close_all_positions.py --symbols PHANTOM,OTHER
   ```

   (Or run with no `--symbols` arg to flatten everything, which is the daily mitigation procedure already in place.)

3. **Investigate the underlying IBKR connectivity issue.** A `cancel_propagation_timeout` in steady-state operation indicates IBKR is taking >2s to acknowledge a cancellation — likely a network blip, IBKR Gateway lag, or a broker-side issue. Check the IBKR Gateway logs and connectivity metrics for the same time window.

4. **Do NOT attempt to bypass the abort by re-running the flatten without addressing the timeout.** The abort is the safety mechanism; bypassing it is what creates the phantom-short risk we're avoiding.

### Spike-script trigger registry (Sprint 31.91 regression invariant 22)

The Phase A spike script `scripts/spike_ibkr_oca_late_add.py` is the **live-IBKR regression check** that verifies IBKR continues to enforce ocaType=1 atomic cancellation pre-submit (the success signature is `PATH_1_SAFE`). Failure to return `PATH_1_SAFE` invalidates the OCA architecture seal and triggers Tier 3 review.

**Run the spike script before any of the following events:**

- [ ] **Before any live-trading transition.** Live-enable gate item per `pre-live-transition-checklist.md` §"Sprint 31.91 — OCA Architecture & Reconciliation Drift".
- [ ] **Before AND after any `ib_async` library version upgrade.** The spike's behavior depends on `ib_async`'s exception-string passthrough.
- [ ] **Before AND after any IBKR API version change** (TWS / IB Gateway upgrade). IBKR has historically modified Error 201 reason strings between versions.
- [ ] **Monthly during paper-trading windows.** Calendar reminder (any monthly cadence works; no enforced date). The most-recent result file (`scripts/spike-results/spike-results-YYYYMMDD.json`) must be ≤30 days old per regression invariant 22 — `tests/_regression_guards/test_spike_script_freshness.py` (lands at Session 4) enforces this in CI.

**How to run:**

```bash
# IB Gateway must be running and connected (paper account, port 4002).
python scripts/spike_ibkr_oca_late_add.py

# Result file is written to scripts/spike-results/spike-results-YYYYMMDD.json
# Verify the verdict:
jq '.overall_outcome' scripts/spike-results/spike-results-$(date +%Y-%m-%d).json
# Expected: "PATH_1_SAFE"
```

**If the verdict is anything other than `PATH_1_SAFE`** (e.g., `PATH_2_RACE`, `PATH_3_LATE_FILL`, or an explicit error): halt the trigger event (live transition / upgrade), and either roll back to `bracket_oca_type: 0` (RESTART-REQUIRED procedure above) or arrange Tier 3 architectural review of the new mechanism behavior.

### Operator daily flatten — current status

Daily `scripts/ibkr_close_all_positions.py` at session close **remains required** throughout the Sprint 31.91 sprint window. It becomes optional only after:

1. Sprint 31.91 sealed (all 18 sessions complete).
2. ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows + zero `phantom_short`/`phantom_short_retry_blocked`/`cancel_propagation_timeout` alerts.
3. Session 5a.1 (HealthMonitor consumer) landed so alerts are Command-Center-visible.
4. Pre-live paper stress test under live-config simulation passes.

See `docs/pre-live-transition-checklist.md` §"Sprint 31.91 — OCA Architecture & Reconciliation Drift" for the full gate list.

---

*End of Live Operations Guide v1.5*
*Last updated: 2026-04-27 (Sprint 31.91 Tier 3 review #1 doc-sync — OCA architecture operations section)*
```

---

## Application notes

- The patch adds roughly 100 lines, all in a single new section appended just before the file footer.
- Version footer bumped from v1.4 to v1.5.
- The four sub-sections cover the four operator-facing concerns surfaced by Sessions 0/1a/1b/1c + Tier 3:
  - Rollback procedure (RESTART-REQUIRED safety)
  - `_OCA_TYPE_BRACKET` lock-step (Session 1b Follow-Up #1)
  - Cancel-propagation timeout response (Session 1c failure-mode trade-off)
  - Spike-script trigger registry (regression invariant 22)
- The grep command in the cancel-timeout response section uses `logs/argus_YYYYMMDD.jsonl` — confirm this matches the actual log filename pattern in your environment. (CLAUDE.md uses this convention; the patch follows it.)

One surgical replacement. No other lines in `live-operations.md` are touched.
